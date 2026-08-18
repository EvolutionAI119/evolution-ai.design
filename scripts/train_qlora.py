"""
NURBS 专家模型 QLoRA 微调训练脚本

功能:
  - 加载全部训练数据（nurbs_surface + a_surface_quality + qlora_enhanced）
  - 使用 Qwen2.5-7B-Instruct 作为基础模型
  - 应用 QLoRA（4-bit 量化 + LoRA adapter）
  - 通过 SFTTrainer 执行监督微调
  - 输出 LoRA adapter 供 deploy_finetuned.py 部署

GPU 要求:
  - QLoRA 模式: NVIDIA GPU, VRAM >= 16GB (RTX 4080/A100/等)
  - LoRA 模式 (CPU fallback): 无 GPU 时自动降级为 fp32 LoRA, 仅支持小模型 (0.5B)

依赖:
  pip install torch transformers peft trl bitsandbytes accelerate
  pip install modelscope  # 国内模型下载

用法:
  # GPU QLoRA 微调 (推荐)
  python scripts/train_qlora.py --model Qwen/Qwen2.5-7B-Instruct --qlora

  # GPU LoRA 微调 (无量化, 需更多显存)
  python scripts/train_qlora.py --model Qwen/Qwen2.5-7B-Instruct

  # CPU LoRA 微调 (小模型, 无量化)
  python scripts/train_qlora.py --model Qwen/Qwen2.5-0.5B-Instruct --cpu

  # 自定义参数
  python scripts/train_qlora.py --epochs 5 --lora-r 32 --lora-alpha 64 --lr 2e-4

  # 指定数据文件
  python scripts/train_qlora.py --data data/training/qlora_enhanced_dataset.jsonl

输出:
  data/training/nurbs-qwen-lora/  (LoRA adapter)
"""
import os
import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional

# ── 兼容性修复: torch 2.4 缺少 DTensor (trl 1.9 需要) ──
try:
    import torch.distributed.tensor
    if not hasattr(torch.distributed.tensor, "DTensor"):
        torch.distributed.tensor.DTensor = type("DTensor", (), {})
except Exception:
    pass

# ── 项目路径 ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "data" / "training"
OUTPUT_DIR = TRAINING_DIR / "nurbs-qwen-lora"

# ── 系统提示词 (与 Modelfile 一致) ──────────────
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

# ── 默认训练数据文件 ────────────────────────────
DEFAULT_DATA_FILES = [
    "nurbs_surface_dataset.jsonl",
    "a_surface_quality_dataset.jsonl",
    "qlora_enhanced_dataset.jsonl",
]


# ════════════════════════════════════════════════
# Step 1: 数据加载与格式化
# ════════════════════════════════════════════════

def load_training_data(data_files: List[str]) -> List[Dict]:
    """加载全部 JSONL 训练数据，合并去重"""
    all_samples = []
    seen_prompts = set()

    for fname in data_files:
        fpath = TRAINING_DIR / fname
        if not fpath.exists():
            print(f"  ⚠ 跳过（文件不存在）: {fpath}")
            continue

        count = 0
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    prompt = sample.get("prompt", "")
                    completion = sample.get("completion", "")

                    # 去重（基于 prompt 文本）
                    if prompt in seen_prompts:
                        continue
                    seen_prompts.add(prompt)

                    all_samples.append({
                        "prompt": prompt,
                        "completion": completion,
                        "category": sample.get("category", "unknown"),
                        "source": fname,
                    })
                    count += 1
                except json.JSONDecodeError as e:
                    print(f"  ⚠ JSON 解析失败 ({fname}): {e}")

        print(f"  ✓ {fname}: {count} 条")

    print(f"\n  合计: {len(all_samples)} 条训练样本（去重后）")
    return all_samples


def format_chat_messages(samples: List[Dict]) -> List[Dict]:
    """将 prompt/completion 格式转换为 Qwen chat messages 格式"""
    formatted = []
    for s in samples:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": s["prompt"]},
            {"role": "assistant", "content": s["completion"]},
        ]
        formatted.append({"messages": messages, "category": s["category"]})
    return formatted


# ════════════════════════════════════════════════
# Step 2: 模型加载 (QLoRA / LoRA)
# ════════════════════════════════════════════════

def resolve_model_path(model_name: str) -> str:
    """通过 modelscope 下载或定位模型，返回本地路径"""
    try:
        from modelscope import snapshot_download
        print(f"  通过 ModelScope 定位模型: {model_name}")
        local_path = snapshot_download(model_name, cache_dir="D:/JZDSLx/hf_models")
        print(f"  ✓ 模型本地路径: {local_path}")
        return local_path
    except Exception as e:
        print(f"  ⚠ ModelScope 下载失败: {e}")
        print(f"  回退到 HuggingFace: {model_name}")
        return model_name


def load_model_and_tokenizer(model_name: str, use_qlora: bool, cpu_mode: bool):
    """加载基础模型和 tokenizer"""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    print(f"\n[2/5] 加载基础模型: {model_name}")

    # 通过 modelscope 定位模型（国内网络优化）
    model_path = resolve_model_path(model_name)

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # 模型加载配置
    if use_qlora and not cpu_mode:
        # QLoRA: 4-bit 量化
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        print("  ✓ QLoRA 模式: 4-bit NF4 量化")
    elif cpu_mode:
        # CPU: fp32
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float32,
            device_map="cpu",
            trust_remote_code=True,
        )
        print("  ✓ CPU 模式: fp32 (无量化)")
    else:
        # GPU LoRA: fp16
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        print("  ✓ GPU LoRA 模式: fp16 (无量化)")

    # 启用 gradient checkpointing 节省显存
    if not cpu_mode:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()

    print(f"  ✓ 模型参数量: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B")
    return model, tokenizer


# ════════════════════════════════════════════════
# Step 3: LoRA 配置
# ════════════════════════════════════════════════

def setup_lora(model, lora_r: int, lora_alpha: int, lora_dropout: float):
    """配置并应用 LoRA adapter"""
    from peft import LoraConfig, get_peft_model, TaskType

    # Qwen2.5 的注意力层名称: q_proj, k_proj, v_proj, o_proj
    # MLP 层: gate_proj, up_proj, down_proj
    target_modules = [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ]

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
        bias="none",
    )

    model = get_peft_model(model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  ✓ LoRA 配置: r={lora_r}, alpha={lora_alpha}, dropout={lora_dropout}")
    print(f"  ✓ 可训练参数: {trainable / 1e6:.2f}M / {total / 1e9:.2f}B ({trainable / total * 100:.2f}%)")

    return model


# ════════════════════════════════════════════════
# Step 4: 训练
# ════════════════════════════════════════════════

def train(model, tokenizer, formatted_data: List[Dict], args):
    """使用 SFTTrainer 执行监督微调"""
    from transformers import TrainingArguments
    from trl import SFTTrainer, SFTConfig

    print(f"\n[4/5] 开始训练...")
    print(f"  训练样本: {len(formatted_data)}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Max sequence length: {args.max_seq_len}")

    # 准备数据集（SFTTrainer 期望 messages 格式）
    import datasets
    ds = datasets.Dataset.from_list([
        {"messages": d["messages"]} for d in formatted_data
    ])

    # SFT 配置
    sft_config = SFTConfig(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        max_length=args.max_seq_len,
        logging_steps=5,
        save_strategy="epoch",
        save_total_limit=3,
        bf16=not args.cpu and not args.qlora,  # bf16 仅在 GPU LoRA 模式
        fp16=args.qlora,  # QLoRA 用 fp16
        tf32=not args.cpu,
        report_to="none",
        dataset_text_field=None,  # 使用 messages 格式
        packing=False,
    )

    # 创建 Trainer
    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=ds,
        processing_class=tokenizer,
    )

    # 训练
    import time
    start = time.time()
    result = trainer.train()
    elapsed = time.time() - start

    print(f"\n  ✓ 训练完成!")
    print(f"  耗时: {elapsed:.0f}s ({elapsed / 60:.1f} min)")
    print(f"  训练损失: {result.training_loss:.4f}")
    print(f"  总步数: {result.global_step}")

    return trainer


# ════════════════════════════════════════════════
# Step 5: 保存 LoRA adapter
# ════════════════════════════════════════════════

def save_adapter(trainer, model, tokenizer):
    """保存 LoRA adapter 和训练元信息"""
    print(f"\n[5/5] 保存 LoRA adapter...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 保存 adapter
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    # 保存训练元信息
    meta = {
        "base_model": trainer.args.output_dir,
        "lora_config": {
            "r": getattr(model, "r", "unknown"),
            "alpha": getattr(model, "alpha", "unknown"),
        },
        "training_samples": len(trainer.train_dataset),
        "system_prompt": SYSTEM_PROMPT[:200] + "...",
    }
    with open(OUTPUT_DIR / "training_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 列出输出文件
    files = list(OUTPUT_DIR.glob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file()) / 1e6
    print(f"  ✓ 输出目录: {OUTPUT_DIR}")
    print(f"  ✓ 文件数: {len(files)}")
    print(f"  ✓ 总大小: {total_size:.1f} MB")
    for f in sorted(files):
        if f.is_file():
            print(f"    {f.name} ({f.stat().st_size / 1e3:.0f} KB)")

    print(f"\n  下一步: 运行部署脚本")
    print(f"  python scripts/deploy_finetuned.py --lora {OUTPUT_DIR}")


# ════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════

def main():
    global OUTPUT_DIR
    parser = argparse.ArgumentParser(
        description="NURBS 专家模型 QLoRA 微调训练",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct",
                        help="基础模型 (默认 Qwen/Qwen2.5-7B-Instruct)")
    parser.add_argument("--data", nargs="*", default=None,
                        help="训练数据文件 (默认加载全部 3 个 JSONL)")
    parser.add_argument("--output", default=str(OUTPUT_DIR),
                        help="LoRA adapter 输出目录")
    parser.add_argument("--qlora", action="store_true",
                        help="使用 QLoRA (4-bit 量化, 需要 GPU + bitsandbytes)")
    parser.add_argument("--cpu", action="store_true",
                        help="CPU 模式 (fp32, 仅适合小模型)")
    parser.add_argument("--epochs", type=int, default=5,
                        help="训练轮数 (默认 5)")
    parser.add_argument("--batch-size", type=int, default=4,
                        help="批次大小 (默认 4)")
    parser.add_argument("--grad-accum", type=int, default=4,
                        help="梯度累积步数 (默认 4, 等效 batch=16)")
    parser.add_argument("--lr", type=float, default=2e-4,
                        help="学习率 (默认 2e-4)")
    parser.add_argument("--lora-r", type=int, default=16,
                        help="LoRA rank (默认 16)")
    parser.add_argument("--lora-alpha", type=int, default=32,
                        help="LoRA alpha (默认 32, 推荐 alpha=2*r)")
    parser.add_argument("--lora-dropout", type=float, default=0.05,
                        help="LoRA dropout (默认 0.05)")
    parser.add_argument("--max-seq-len", type=int, default=2048,
                        help="最大序列长度 (默认 2048)")
    args = parser.parse_args()

    OUTPUT_DIR = Path(args.output)

    # ── 打印配置 ────────────────────────────────
    print("=" * 60)
    print("  NURBS Expert Model — QLoRA Fine-tuning")
    print("=" * 60)
    print(f"  基础模型:     {args.model}")
    print(f"  输出目录:     {OUTPUT_DIR}")
    print(f"  训练模式:     {'QLoRA (4-bit)' if args.qlora else 'CPU fp32' if args.cpu else 'GPU fp16 LoRA'}")
    print(f"  Epochs:       {args.epochs}")
    print(f"  Batch:        {args.batch_size} x {args.grad_accum} = {args.batch_size * args.grad_accum}")
    print(f"  Learning rate:{args.lr}")
    print(f"  LoRA r/alpha: {args.lora_r}/{args.lora_alpha} (dropout={args.lora_dropout})")
    print(f"  Max seq len:  {args.max_seq_len}")
    print()

    # ── 环境检查 ────────────────────────────────
    import torch
    cuda_available = torch.cuda.is_available()
    print(f"[0/5] 环境检查")
    print(f"  PyTorch: {torch.__version__}")
    print(f"  CUDA: {'✓ ' + torch.cuda.get_device_name(0) if cuda_available else '✗ 不可用'}")

    if args.qlora and not cuda_available:
        print("\n  ✗ QLoRA 需要 GPU + CUDA, 但当前环境不可用")
        print("  建议: 使用 --cpu 模式 (仅小模型) 或在 GPU 服务器上运行")
        sys.exit(1)

    # 检查依赖包
    missing = []
    for pkg in ["transformers", "peft", "trl", "accelerate"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if args.qlora:
        try:
            import bitsandbytes
        except ImportError:
            missing.append("bitsandbytes")
    if missing:
        print(f"\n  ✗ 缺少依赖: {', '.join(missing)}")
        print(f"  安装: pip install {' '.join(missing)}")
        sys.exit(1)
    print("  ✓ 依赖检查通过")

    # ── Step 1: 加载数据 ────────────────────────
    print(f"\n[1/5] 加载训练数据")
    data_files = args.data if args.data else DEFAULT_DATA_FILES
    samples = load_training_data(data_files)
    if not samples:
        print("  ✗ 无训练数据")
        sys.exit(1)

    # 类别分布
    from collections import Counter
    cats = Counter(s["category"] for s in samples)
    print(f"\n  类别分布:")
    for cat, cnt in cats.most_common():
        print(f"    {cat:25s}: {cnt}")

    # 格式化为 chat messages
    formatted_data = format_chat_messages(samples)

    # ── Step 2: 加载模型 ────────────────────────
    model, tokenizer = load_model_and_tokenizer(args.model, args.qlora, args.cpu)

    # ── Step 3: LoRA 配置 ───────────────────────
    print(f"\n[3/5] 配置 LoRA adapter")
    model = setup_lora(model, args.lora_r, args.lora_alpha, args.lora_dropout)

    # ── Step 4: 训练 ────────────────────────────
    trainer = train(model, tokenizer, formatted_data, args)

    # ── Step 5: 保存 ────────────────────────────
    save_adapter(trainer, model, tokenizer)

    print("\n" + "=" * 60)
    print("  ✓ QLoRA 微调完成!")
    print("=" * 60)
    print(f"\n  部署命令:")
    print(f"  python scripts/deploy_finetuned.py --lora {OUTPUT_DIR}")
    print(f"\n  验证命令:")
    print(f"  python scripts/test_nurbs_inference.py --model nurbs-expert")


if __name__ == "__main__":
    main()
