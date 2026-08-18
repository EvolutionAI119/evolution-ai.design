"""
NURBS 专家模型自动化部署管线

完整流程:
  LoRA adapter → 合并 → GGUF 转换 → 量化 → Ollama 部署 → 验证测试

用法:
    python scripts/deploy_finetuned.py                      # 全流程（合并+GGUF+部署+测试）
    python scripts/deploy_finetuned.py --skip-merge         # 跳过合并（已有 merged_model）
    python scripts/deploy_finetuned.py --skip-convert       # 跳过 GGUF 转换（已有 .gguf）
    python scripts/deploy_finetuned.py --quantize q4_k_m    # 量化为 Q4_K_M
    python scripts/deploy_finetuned.py --base-only          # 仅部署基础模型（无微调）
    python scripts/deploy_finetuned.py --verify-only        # 仅运行验证测试
    python scripts/deploy_finetuned.py --ollama-path PATH   # 指定 Ollama 安装路径

环境变量:
    NURBS_LORA_PATH     LoRA adapter 路径 (默认 data/training/nurbs-qwen-lora)
    NURBS_BASE_MODEL    基础模型名 (默认 Qwen/Qwen2.5-0.5B-Instruct)
    NURBS_MODEL_NAME    Ollama 模型名 (默认 nurbs-expert)
    LLAMA_CPP_PATH      llama.cpp 目录路径
"""
import os
import sys
import shutil
import argparse
import subprocess
import time
from pathlib import Path

# ── 项目路径 ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "data" / "training"
MERGED_DIR = TRAINING_DIR / "merged"

# ── 默认配置 ────────────────────────────────────
DEFAULT_LORA_PATH = os.getenv("NURBS_LORA_PATH", str(TRAINING_DIR / "nurbs-qwen-lora"))
DEFAULT_BASE_MODEL = os.getenv("NURBS_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
DEFAULT_MODEL_NAME = os.getenv("NURBS_MODEL_NAME", "nurbs-expert")
DEFAULT_LLAMA_CPP = os.getenv("LLAMA_CPP_PATH", str(PROJECT_ROOT / "llama.cpp"))

# NURBS 系统提示词
SYSTEM_PROMPT = """你是 Evolution-AI.Design 平台的 NURBS 曲面设计专家助手，精通以下领域：
1. NURBS 数学原理（控制点/阶数/节点向量/权重）
2. 汽车 A 级曲面 SOP 标准（SOP-A SURF-001）
3. G0/G1/G2 连续性分析与共享边界技术
4. 参数化车身生成（L/W/H/WB/GC 驱动控制点）
5. 曲面质量评估（均曲率/CV/ISO 曲率/R 角）

回答原则：
- 数值精确：引用实测数据（如 body↔front_bumper G1=0.131deg）
- 结构化输出：使用表格/列表/分点
- 区分设计意图与质量缺陷（recess/bulge vs 真正间隙）
- 如不确定，明确说明而非编造"""

# 量化选项
QUANTIZE_MAP = {
    "q4_0": "Q4_0",
    "q4_k_m": "Q4_K_M",
    "q4_k_s": "Q4_K_S",
    "q5_0": "Q5_0",
    "q5_k_m": "Q5_K_M",
    "q5_k_s": "Q5_K_S",
    "q8_0": "Q8_0",
    "f16": "F16",
    "f32": "F32",
}


class Color:
    """终端颜色"""
    HEADER = "\033[95m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def log(step, msg, color=Color.CYAN):
    """带步骤标识的日志输出"""
    print(f"{color}[{step}]{Color.END} {msg}")


def log_ok(msg):
    print(f"{Color.GREEN}  ✓{Color.END} {msg}")


def log_fail(msg):
    print(f"{Color.RED}  ✗{Color.END} {msg}")


def log_warn(msg):
    print(f"{Color.YELLOW}  ⚠{Color.END} {msg}")


def banner(title):
    """打印分隔横幅"""
    line = "═" * 60
    print(f"\n{Color.HEADER}╔{line}╗{Color.END}")
    print(f"{Color.HEADER}║{title:^60}{Color.END}")
    print(f"{Color.HEADER}╚{line}╝{Color.END}")


# ════════════════════════════════════════════════
# Step 0: 环境检查
# ════════════════════════════════════════════════

def check_prerequisites(args):
    """检查所有依赖是否就绪"""
    banner("Step 0: 环境检查")
    results = {}

    # Python 包
    log("0.1", "检查 Python 依赖...")
    required = {
        "torch": "torch",
        "transformers": "transformers",
        "peft": "peft (LoRA 合并)",
        "accelerate": "accelerate",
    }
    if not args.skip_convert:
        required["gguf"] = "gguf (GGUF 写入)"

    for pkg, desc in required.items():
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "unknown")
            log_ok(f"{pkg} ({ver}) — {desc}")
            results[pkg] = True
        except ImportError:
            if pkg in ("peft",) and args.base_only:
                log_warn(f"{pkg} 未安装（--base-only 模式可跳过）")
                results[pkg] = False
            elif pkg in ("gguf",) and args.skip_convert:
                results[pkg] = True
            else:
                log_fail(f"{pkg} 未安装 — {desc}")
                log_warn(f"  安装: pip install {pkg}")
                results[pkg] = False

    # Ollama
    log("0.2", "检查 Ollama...")
    ollama_cmd = find_ollama(args.ollama_path)
    if ollama_cmd:
        try:
            ver = subprocess.check_output([ollama_cmd, "--version"], capture_output=True, text=True, timeout=5)
            log_ok(f"Ollama: {ver.strip()}")
            results["ollama"] = True
        except Exception:
            log_warn("Ollama 已找到但无法获取版本")
            results["ollama"] = True
    else:
        log_warn("Ollama 未安装 — 将使用 llm_server.py 作为替代推理引擎")
        results["ollama"] = False
    results["ollama_cmd"] = ollama_cmd

    # llama.cpp（GGUF 转换需要）
    if not args.skip_convert and not args.base_only:
        log("0.3", "检查 llama.cpp...")
        llama_cpp_path = Path(DEFAULT_LLAMA_CPP)
        convert_script = llama_cpp_path / "convert_hf_to_gguf.py"
        if convert_script.exists():
            log_ok(f"llama.cpp: {llama_cpp_path}")
            results["llama_cpp"] = True
            results["llama_cpp_path"] = str(llama_cpp_path)
        else:
            log_warn(f"llama.cpp 未找到: {llama_cpp_path}")
            log_warn("  尝试自动下载...")
            downloaded = download_llama_cpp(llama_cpp_path)
            results["llama_cpp"] = downloaded
            results["llama_cpp_path"] = str(llama_cpp_path) if downloaded else None
            if not downloaded:
                log_fail("无法获取 llama.cpp，GGUF 转换将跳过")
    else:
        results["llama_cpp"] = True
        results["llama_cpp_path"] = DEFAULT_LLAMA_CPP

    # 检查训练数据
    log("0.4", "检查训练数据...")
    train_file = TRAINING_DIR / "nurbs_surface_dataset.jsonl"
    quality_file = TRAINING_DIR / "a_surface_quality_dataset.jsonl"
    if train_file.exists() and quality_file.exists():
        count1 = sum(1 for _ in open(train_file, encoding="utf-8") if _.strip())
        count2 = sum(1 for _ in open(quality_file, encoding="utf-8") if _.strip())
        log_ok(f"训练数据: {count1} + {count2} = {count1 + count2} 条样本")
    else:
        log_warn("训练数据文件缺失（仅影响微调，不影响部署）")

    return results


def find_ollama(custom_path=None):
    """查找 Ollama 可执行文件"""
    if custom_path:
        if Path(custom_path).exists():
            return custom_path
    # 检查 PATH
    ollama = shutil.which("ollama")
    if ollama:
        return ollama
    # 常见安装路径
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
        Path("/usr/local/bin/ollama"),
        Path("/usr/bin/ollama"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def download_llama_cpp(target_path: Path) -> bool:
    """尝试下载 llama.cpp"""
    # 尝试从 modelscope 下载
    try:
        log("0.3", "尝试从 ModelScope 下载 llama.cpp...")
        from modelscope import snapshot_download
        # 搜索 llama.cpp 镜像（可能不存在，则尝试 git clone）
        model_dir = snapshot_download("AI-ModelScope/llama.cpp", cache_dir=str(target_path.parent))
        if model_dir:
            # 软链接或复制到目标路径
            if not target_path.exists():
                shutil.copytree(model_dir, str(target_path))
            log_ok(f"llama.cpp 下载完成: {target_path}")
            return True
    except Exception as e:
        log_warn(f"ModelScope 下载失败: {e}")

    # 尝试 git clone
    try:
        log("0.3", "尝试 git clone llama.cpp...")
        subprocess.check_call(
            ["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp", str(target_path)],
            timeout=60,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if target_path.exists():
            log_ok(f"llama.cpp 克隆完成: {target_path}")
            return True
    except Exception as e:
        log_warn(f"git clone 失败: {e}")

    return False


# ════════════════════════════════════════════════
# Step 1: 合并 LoRA adapter
# ════════════════════════════════════════════════

def merge_lora(lora_path: str, output_dir: str, base_model: str) -> str:
    """合并 LoRA adapter 到基础模型，返回合并后模型路径"""
    banner("Step 1: 合并 LoRA Adapter")

    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    merged_path = os.path.join(output_dir, "merged_model")
    os.makedirs(merged_path, exist_ok=True)

    # 检查是否已合并
    if Path(merged_path, "config.json").exists():
        log_ok(f"已存在合并模型: {merged_path}（跳过）")
        return merged_path

    lora_p = Path(lora_path)
    if not lora_p.exists():
        log_fail(f"LoRA adapter 不存在: {lora_path}")
        log_warn("  使用 --base-only 模式部署基础模型")
        return None

    # 加载基础模型
    log("1.1", f"加载基础模型: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model, dtype=torch.float32)

    # 加载 LoRA
    log("1.2", f"加载 LoRA adapter: {lora_path}")
    model = PeftModel.from_pretrained(model, lora_path)

    # 合并
    log("1.3", "合并 LoRA 权重...")
    model = model.merge_and_unload()

    # 保存
    log("1.4", f"保存合并模型: {merged_path}")
    model.save_pretrained(merged_path, safe_serialization=True)
    tokenizer.save_pretrained(merged_path)

    params = sum(p.numel() for p in model.parameters()) / 1e9
    log_ok(f"合并完成: {params:.1f}B params → {merged_path}")

    return merged_path


# ════════════════════════════════════════════════
# Step 2: GGUF 转换
# ════════════════════════════════════════════════

def convert_to_gguf(hf_model_path: str, output_dir: str, llama_cpp_path: str) -> str:
    """将 HuggingFace 模型转换为 GGUF 格式"""
    banner("Step 2: GGUF 转换")

    gguf_path = os.path.join(output_dir, "nurbs_expert.gguf")

    # 检查是否已转换
    if Path(gguf_path).exists():
        size = Path(gguf_path).stat().st_size / 1e9
        log_ok(f"已存在 GGUF 文件: {gguf_path} ({size:.1f} GB)（跳过）")
        return gguf_path

    convert_script = Path(llama_cpp_path) / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        log_fail(f"转换脚本不存在: {convert_script}")
        return None

    log("2.1", f"转换: {hf_model_path} → GGUF")
    log("2.2", f"脚本: {convert_script}")

    cmd = [
        sys.executable, str(convert_script),
        hf_model_path,
        "--outfile", gguf_path,
    ]
    log("2.3", f"执行: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            size = Path(gguf_path).stat().st_size / 1e9
            log_ok(f"GGUF 转换完成: {gguf_path} ({size:.1f} GB)")
            return gguf_path
        else:
            log_fail("GGUF 转换失败")
            log_warn(f"stderr: {result.stderr[:500]}")
            return None
    except subprocess.TimeoutExpired:
        log_fail("GGUF 转换超时（10 分钟）")
        return None


# ════════════════════════════════════════════════
# Step 3: 量化（可选）
# ════════════════════════════════════════════════

def quantize_gguf(gguf_path: str, quant_type: str, llama_cpp_path: str) -> str:
    """量化 GGUF 模型"""
    banner(f"Step 3: 量化 ({quant_type})")

    quant_type_upper = QUANTIZE_MAP.get(quant_type.lower(), quant_type.upper())
    quantized_path = gguf_path.replace(".gguf", f"_{quant_type}.gguf")

    if Path(quantized_path).exists():
        size = Path(quantized_path).stat().st_size / 1e9
        log_ok(f"已存在量化文件: {quantized_path} ({size:.1f} GB)（跳过）")
        return quantized_path

    # 查找 quantize 工具
    quantize_bin = None
    for name in ["llama-quantize", "quantize", "llama-quantize.exe", "quantize.exe"]:
        p = Path(llama_cpp_path) / name
        if p.exists():
            quantize_bin = str(p)
            break
        # 也检查 build 子目录
        for build_dir in ["build", "build/Release", "bin", "out"]:
            p2 = Path(llama_cpp_path) / build_dir / name
            if p2.exists():
                quantize_bin = str(p2)
                break
        if quantize_bin:
            break

    if not quantize_bin:
        log_fail("llama-quantize 未找到，跳过量化")
        log_warn("  请先编译 llama.cpp: cd llama.cpp && make")
        log_warn("  或使用 Windows: cd llama.cpp && cmake -B build && cmake --build build")
        return gguf_path  # 返回未量化版本

    log("3.1", f"量化: {quant_type_upper}")
    log("3.2", f"工具: {quantize_bin}")

    cmd = [quantize_bin, gguf_path, quantized_path, quant_type_upper]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            orig_size = Path(gguf_path).stat().st_size / 1e9
            quant_size = Path(quantized_path).stat().st_size / 1e9
            log_ok(f"量化完成: {quant_size:.1f} GB (原始: {orig_size:.1f} GB, 压缩率: {quant_size/orig_size*100:.0f}%)")
            return quantized_path
        else:
            log_fail("量化失败")
            log_warn(f"stderr: {result.stderr[:500]}")
            return gguf_path
    except subprocess.TimeoutExpired:
        log_fail("量化超时")
        return gguf_path


# ════════════════════════════════════════════════
# Step 4: 创建 Modelfile 并部署到 Ollama
# ════════════════════════════════════════════════

def create_modelfile(gguf_path: str, model_name: str, output_dir: str) -> str:
    """生成 Ollama Modelfile"""
    banner("Step 4: 创建 Modelfile")

    modelfile_path = os.path.join(output_dir, "Modelfile.deploy")
    abs_gguf = os.path.abspath(gguf_path)

    content = f"""# Auto-generated by deploy_finetuned.py
# Model: {model_name}
# GGUF: {abs_gguf}
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

FROM {abs_gguf}

SYSTEM \"\"\"{SYSTEM_PROMPT}\"\"\"

PARAMETER temperature 0.3
PARAMETER top_p 0.85
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
"""

    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(content)

    log_ok(f"Modelfile 生成: {modelfile_path}")
    return modelfile_path


def deploy_to_ollama(modelfile_path: str, model_name: str, ollama_cmd: str) -> bool:
    """部署模型到 Ollama"""
    banner("Step 4.2: 部署到 Ollama")

    # 确保 Ollama 服务运行
    log("4.2.1", "检查 Ollama 服务...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            log_ok("Ollama 服务运行中")
        else:
            log_warn("Ollama 服务异常，尝试启动...")
            subprocess.Popen([ollama_cmd, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
    except Exception:
        log_warn("Ollama 服务未运行，尝试启动...")
        subprocess.Popen([ollama_cmd, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

    # 创建模型
    log("4.2.2", f"创建 Ollama 模型: {model_name}")
    cmd = [ollama_cmd, "create", model_name, "-f", modelfile_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            log_ok(f"模型 {model_name} 创建成功")
            # 显示模型列表
            list_result = subprocess.run([ollama_cmd, "list"], capture_output=True, text=True, timeout=10)
            print(list_result.stdout)
            return True
        else:
            log_fail(f"模型创建失败: {result.stderr[:300]}")
            return False
    except subprocess.TimeoutExpired:
        log_fail("模型创建超时")
        return False


def deploy_to_llm_server(model_path: str, port: int = 11434) -> bool:
    """使用 llm_server.py 替代 Ollama 部署（无 Ollama 时的 fallback）"""
    banner("Step 4.2: 部署到 llm_server.py (Ollama 替代)")

    server_script = PROJECT_ROOT / "scripts" / "llm_server.py"
    if not server_script.exists():
        log_fail(f"llm_server.py 不存在: {server_script}")
        return False

    # 检查端口是否已占用（可能已有服务运行）
    import requests
    try:
        resp = requests.get(f"http://localhost:{port}/api/tags", timeout=3)
        if resp.status_code == 200:
            log_ok(f"端口 {port} 已有推理服务运行（复用）")
            return True
    except Exception:
        pass

    log("4.2.1", f"启动 llm_server.py (端口 {port})...")
    log("4.2.2", f"模型路径: {model_path}")

    # 在后台启动
    proc = subprocess.Popen(
        [sys.executable, str(server_script), "--port", str(port), "--model-path", model_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # 等待服务就绪（最多 60s）
    log("4.2.3", "等待模型加载...")
    for i in range(30):
        time.sleep(2)
        try:
            resp = requests.get(f"http://localhost:{port}/api/tags", timeout=3)
            if resp.status_code == 200:
                log_ok(f"llm_server.py 启动成功 (端口 {port}, 耗时 {(i+1)*2}s)")
                return True
        except Exception:
            continue

    # 超时，检查进程是否已退出
    if proc.poll() is not None:
        out = proc.stdout.read().decode("utf-8", errors="replace")[:500] if proc.stdout else ""
        log_fail(f"llm_server.py 进程已退出 (code={proc.returncode})")
        log_warn(f"输出: {out}")
    else:
        log_fail(f"llm_server.py 60s 内未就绪")
        proc.terminate()

    return False


# ════════════════════════════════════════════════
# Step 5: 验证测试
# ════════════════════════════════════════════════

def run_verification(model_name: str, host: str = "http://localhost:11434") -> dict:
    """运行验证测试"""
    banner("Step 5: 验证测试")

    test_script = PROJECT_ROOT / "scripts" / "test_nurbs_inference.py"
    if not test_script.exists():
        log_fail(f"测试脚本不存在: {test_script}")
        return {"pass_rate": 0}

    log("5.1", f"运行: python {test_script} --host {host} --model {model_name}")
    cmd = [sys.executable, str(test_script), "--host", host, "--model", model_name]
    try:
        result = subprocess.run(cmd, timeout=600, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr[:500])

        # 解析结果
        import json
        results_file = TRAINING_DIR / "test_results.json"
        if results_file.exists():
            with open(results_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except subprocess.TimeoutExpired:
        log_fail("测试超时（10 分钟）")
    except Exception as e:
        log_fail(f"测试失败: {e}")

    return {"pass_rate": 0}


# ════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NURBS 专家模型自动化部署管线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全流程：合并 LoRA → GGUF → 部署 → 测试
  python scripts/deploy_finetuned.py

  # 仅部署基础模型（无微调）
  python scripts/deploy_finetuned.py --base-only

  # 量化部署（Q4_K_M，减小模型体积）
  python scripts/deploy_finetuned.py --quantize q4_k_m

  # 跳过已完成的步骤
  python scripts/deploy_finetuned.py --skip-merge --skip-convert

  # 仅运行验证测试
  python scripts/deploy_finetuned.py --verify-only
        """,
    )
    parser.add_argument("--lora", default=DEFAULT_LORA_PATH, help="LoRA adapter 路径")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help="基础模型名")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="Ollama 模型名")
    parser.add_argument("--output", default=str(MERGED_DIR), help="输出目录")
    parser.add_argument("--quantize", choices=list(QUANTIZE_MAP.keys()), default=None,
                        help="量化类型 (q4_k_m, q5_k_m, q8_0, f16 等)")
    parser.add_argument("--skip-merge", action="store_true", help="跳过 LoRA 合并步骤")
    parser.add_argument("--skip-convert", action="store_true", help="跳过 GGUF 转换步骤")
    parser.add_argument("--skip-deploy", action="store_true", help="跳过部署步骤")
    parser.add_argument("--skip-verify", action="store_true", help="跳过验证测试")
    parser.add_argument("--base-only", action="store_true", help="仅部署基础模型（不合并 LoRA）")
    parser.add_argument("--verify-only", action="store_true", help="仅运行验证测试")
    parser.add_argument("--ollama-path", default=None, help="Ollama 可执行文件路径")
    parser.add_argument("--port", type=int, default=11434, help="推理服务端口")
    args = parser.parse_args()

    banner("NURBS Expert Model — Automated Deployment Pipeline")
    print(f"  基础模型: {args.base_model}")
    print(f"  LoRA路径: {args.lora}")
    print(f"  模型名称: {args.model_name}")
    print(f"  输出目录: {args.output}")
    print(f"  量化类型: {args.quantize or 'none'}")
    print(f"  模式:     {'base-only' if args.base_only else 'full-pipeline'}")
    print()

    start_time = time.time()

    # ── Step 0: 环境检查 ────────────────────────
    env = check_prerequisites(args)
    if not env.get("torch") or not env.get("transformers"):
        log_fail("核心依赖缺失，无法继续")
        sys.exit(1)

    # ── verify-only 模式 ────────────────────────
    if args.verify_only:
        host = f"http://localhost:{args.port}"
        run_verification(args.model_name, host)
        return

    # ── Step 1: 合并 LoRA ───────────────────────
    hf_model_path = None
    if not args.skip_merge and not args.base_only:
        if env.get("peft"):
            hf_model_path = merge_lora(args.lora, args.output, args.base_model)
        else:
            log_warn("peft 未安装，跳过 LoRA 合并")
            args.base_only = True

    if args.base_only or hf_model_path is None:
        # 使用基础模型路径（从 modelscope 下载）
        log("1.0", f"使用基础模型: {args.base_model}")
        try:
            from modelscope import snapshot_download
            hf_model_path = snapshot_download(args.base_model, cache_dir="D:/JZDSLx/hf_models")
            log_ok(f"基础模型路径: {hf_model_path}")
        except Exception as e:
            log_fail(f"无法获取基础模型: {e}")
            sys.exit(1)

    # ── Step 2: GGUF 转换 ───────────────────────
    gguf_path = None
    if not args.skip_convert:
        if env.get("llama_cpp"):
            gguf_path = convert_to_gguf(hf_model_path, args.output, env["llama_cpp_path"])
        else:
            log_warn("llama.cpp 不可用，跳过 GGUF 转换")
            log_warn("将直接使用 HuggingFace 格式部署")

    # ── Step 3: 量化 ────────────────────────────
    if gguf_path and args.quantize:
        gguf_path = quantize_gguf(gguf_path, args.quantize, env.get("llama_cpp_path", DEFAULT_LLAMA_CPP))

    # ── Step 4: 部署 ────────────────────────────
    deploy_success = False
    if not args.skip_deploy:
        if gguf_path:
            # GGUF → Ollama 或 llm_server
            modelfile_path = create_modelfile(gguf_path, args.model_name, args.output)
            if env.get("ollama"):
                deploy_success = deploy_to_ollama(modelfile_path, args.model_name, env["ollama_cmd"])
            else:
                # Fallback: 使用 llm_server.py（需要 HF 格式，不是 GGUF）
                log_warn("Ollama 未安装，使用 llm_server.py 替代")
                log_warn("注意: llm_server.py 使用 HuggingFace 格式，非 GGUF")
                deploy_success = deploy_to_llm_server(hf_model_path, args.port)
        else:
            # 无 GGUF，直接用 llm_server.py
            log_warn("无 GGUF 文件，使用 llm_server.py 部署 HuggingFace 模型")
            deploy_success = deploy_to_llm_server(hf_model_path, args.port)

    # ── Step 5: 验证 ────────────────────────────
    if not args.skip_verify and deploy_success:
        host = f"http://localhost:{args.port}"
        results = run_verification(args.model_name, host)

        # 最终报告
        banner("部署完成 — 最终报告")
        elapsed = time.time() - start_time
        print(f"  总耗时:     {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  基础模型:   {args.base_model}")
        print(f"  LoRA合并:   {'✓' if hf_model_path and not args.base_only else '✗'}")
        print(f"  GGUF转换:   {'✓' if gguf_path else '✗'}")
        print(f"  量化:       {args.quantize or 'none'}")
        print(f"  部署方式:   {'Ollama' if env.get('ollama') and gguf_path else 'llm_server.py'}")
        print(f"  测试通过率: {results.get('pass_rate', 0):.0f}% ({results.get('passed', 0)}/{results.get('total', 10)})")
        print()
        if results.get("pass_rate", 0) >= 80:
            print(f"  {Color.GREEN}✓ 优秀 — 模型已就绪{Color.END}")
        elif results.get("pass_rate", 0) >= 60:
            print(f"  {Color.YELLOW}△ 合格 — 部分知识需补充{Color.END}")
        else:
            print(f"  {Color.RED}✗ 需改进 — 建议用更多数据微调{Color.END}")
    elif args.skip_verify:
        banner("部署完成（跳过验证）")
        print(f"  手动验证: python scripts/test_nurbs_inference.py --model {args.model_name}")


if __name__ == "__main__":
    main()
