"""NURBS 专家模型推理测试脚本

测试流程:
1. Ollama 服务连通性
2. 模型可用性
3. NURBS 知识问答准确性（10 道专项题）
4. 后端 API 集成验证

用法:
    python scripts/test_nurbs_inference.py                    # 测试 Ollama 直连
    python scripts/test_nurbs_inference.py --via-api           # 测试后端 API
    python scripts/test_nurbs_inference.py --model nurbs-expert  # 指定模型
"""
import sys
import json
import time
import argparse
import requests
from pathlib import Path

# ── 测试用例：10 道 NURBS 专项问答 ───────────────

TEST_CASES = [
    {
        "id": 1,
        "category": "nurbs_basics",
        "question": "什么是NURBS曲面的G1连续性？",
        "keywords": ["切向量", "法向量", "1度", "共享边界"],
        "min_score": 2,
    },
    {
        "id": 2,
        "category": "component_design",
        "question": "车身蒙皮(body_upper_skin)的控制点网格是多少？为什么？",
        "keywords": ["30", "20", "600", "车身", "复杂"],
        "min_score": 2,
    },
    {
        "id": 3,
        "category": "continuity",
        "question": "车身与前保险杠的G0和G1值分别是多少？",
        "keywords": ["0.000", "0.131"],
        "min_score": 2,
    },
    {
        "id": 4,
        "category": "sop",
        "question": "SOP检查项8的R角为什么在参数化NURBS车身中大量FAIL？",
        "keywords": ["参数化", "R角", "无传统", "FAIL", "11"],
        "min_score": 2,
    },
    {
        "id": 5,
        "category": "component_design",
        "question": "进气格栅(grille)的控制点结构是什么？",
        "keywords": ["4", "3", "12", "degree"],
        "min_score": 2,
    },
    {
        "id": 6,
        "category": "continuity",
        "question": "整车NURBS模型有多少个曲面零件？连续性配对有多少对？",
        "keywords": ["18", "124", "配对"],
        "min_score": 2,
    },
    {
        "id": 7,
        "category": "quality_assessment",
        "question": "什么是ISO曲率检查？阈值是多少？",
        "keywords": ["梯度", "ratio", "10", "曲率"],
        "min_score": 2,
    },
    {
        "id": 8,
        "category": "parametric_design",
        "question": "NURBS车身的坐标系是如何定义的？默认参数是什么？",
        "keywords": ["X", "Y", "Z", "4700", "1850", "1450"],
        "min_score": 3,
    },
    {
        "id": 9,
        "category": "sop",
        "question": "SOP检查的自动化覆盖率是多少？PASS率是多少？",
        "keywords": ["37%", "79%", "67", "53"],
        "min_score": 2,
    },
    {
        "id": 10,
        "category": "continuity",
        "question": "哪些设计间隙是正常的？哪些需要修复？",
        "keywords": ["装配间隙", "凹陷", "外凸", "recess", "bulge", "车轮"],
        "min_score": 3,
    },
]


def check_ollama(host: str) -> bool:
    """检查 Ollama 服务连通性"""
    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def get_models(host: str) -> list:
    """获取已安装的模型列表"""
    resp = requests.get(f"{host}/api/tags", timeout=5)
    return [m["name"] for m in resp.json().get("models", [])]


def generate(host: str, model: str, prompt: str) -> dict:
    """调用 Ollama 生成"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 4096},
    }
    resp = requests.post(f"{host}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def generate_via_api(base_url: str, question: str) -> dict:
    """通过后端 API 调用"""
    resp = requests.post(
        f"{base_url}/api/v1/ai/chat",
        json={"question": question},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def score_answer(answer: str, keywords: list) -> int:
    """关键词匹配评分（每个关键词 1 分）"""
    score = 0
    answer_lower = answer.lower()
    for kw in keywords:
        if kw.lower() in answer_lower:
            score += 1
    return score


def run_tests(args):
    """运行全部测试"""
    host = args.host
    model = args.model
    api_url = args.api_url
    via_api = args.via_api

    print("=" * 60)
    print("  NURBS Expert Model - Inference Test")
    print("=" * 60)

    # Step 1: 连通性检查
    if via_api:
        print("\n[1/3] 检查后端 API 连通性...")
        try:
            resp = requests.get(f"{api_url}/api/v1/ai/health", timeout=5)
            health = resp.json()
            print(f"  状态: {health.get('status', 'unknown')}")
            print(f"  Ollama: {health.get('ollama', 'unknown')}")
            print(f"  模型就绪: {health.get('model_ready', False)}")
            if not health.get("model_ready"):
                print("  ⚠ 模型未就绪，请先运行: .\\scripts\\setup_ollama.ps1")
                return
        except requests.ConnectionError:
            print(f"  ✗ 后端服务未启动: {api_url}")
            print(f"  请运行: cd backend && python -m uvicorn app.main:app --reload")
            return
    else:
        print("\n[1/3] 检查 Ollama 服务连通性...")
        if not check_ollama(host):
            print(f"  ✗ Ollama 服务未启动: {host}")
            print(f"  请运行: ollama serve")
            return
        print(f"  ✓ Ollama 服务运行中")

        models = get_models(host)
        print(f"  已安装模型: {models}")
        if model not in models:
            print(f"  ✗ 模型 {model} 未安装")
            print(f"  请运行: .\\scripts\\setup_ollama.ps1")
            return
        print(f"  ✓ 使用模型: {model}")

    # Step 2: 推理测试
    print(f"\n[2/3] 推理测试 ({len(TEST_CASES)} 道专项问答)...")
    print("-" * 60)

    results = []
    total_score = 0
    max_score = 0

    for tc in TEST_CASES:
        question = tc["question"]
        print(f"\n  [{tc['id']}/{len(TEST_CASES)}] [{tc['category']}]")
        print(f"  Q: {question}")

        try:
            start = time.time()
            if via_api:
                data = generate_via_api(api_url, question)
                answer = data.get("answer", "")
                duration = data.get("duration_sec", 0)
                tokens = data.get("eval_count", 0)
            else:
                data = generate(host, model, question)
                answer = data.get("response", "")
                duration = round(data.get("total_duration", 0) / 1e9, 2)
                tokens = data.get("eval_count", 0)
            elapsed = time.time() - start
        except Exception as e:
            print(f"  ✗ 请求失败: {e}")
            results.append({"id": tc["id"], "pass": False, "score": 0, "error": str(e)})
            continue

        # 评分
        score = score_answer(answer, tc["keywords"])
        max_score += tc["min_score"]
        total_score += min(score, tc["min_score"])
        passed = score >= tc["min_score"]

        # 预览
        preview = answer[:150].replace("\n", " ") + ("..." if len(answer) > 150 else "")
        print(f"  A: {preview}")
        print(f"  关键词命中: {score}/{len(tc['keywords'])} | 需要: {tc['min_score']} | {'✓ PASS' if passed else '✗ FAIL'}")
        print(f"  耗时: {duration}s | Token数: {tokens}")

        results.append({
            "id": tc["id"],
            "category": tc["category"],
            "pass": passed,
            "score": score,
            "min_score": tc["min_score"],
            "duration": duration,
            "tokens": tokens,
        })

    # Step 3: 汇总
    print("\n" + "=" * 60)
    print("  测试汇总")
    print("=" * 60)

    passed = sum(1 for r in results if r.get("pass"))
    failed = len(results) - passed
    pass_rate = (passed / len(results) * 100) if results else 0
    avg_duration = sum(r.get("duration", 0) for r in results) / len(results) if results else 0
    avg_tokens = sum(r.get("tokens", 0) for r in results) / len(results) if results else 0

    print(f"  通过: {passed}/{len(TEST_CASES)} ({pass_rate:.0f}%)")
    print(f"  失败: {failed}")
    print(f"  关键词得分: {total_score}/{max_score}")
    print(f"  平均耗时: {avg_duration:.2f}s")
    print(f"  平均Token: {avg_tokens:.0f}")

    # 按类别统计
    print(f"\n  按类别统计:")
    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"pass": 0, "total": 0}
        categories[cat]["total"] += 1
        if r.get("pass"):
            categories[cat]["pass"] += 1

    for cat, stats in sorted(categories.items()):
        print(f"    {cat:25s}: {stats['pass']}/{stats['total']}")

    # 判定
    print(f"\n  总体评价: ", end="")
    if pass_rate >= 80:
        print("✓ 优秀 - 模型已掌握 NURBS 核心知识", flush=True)
    elif pass_rate >= 60:
        print("△ 合格 - 基本掌握，部分知识需补充", flush=True)
    else:
        print("✗ 不合格 - 建议增加训练数据或使用微调模型", flush=True)

    # 保存结果
    result_path = Path("data/training/test_results.json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({
            "model": model,
            "via_api": via_api,
            "pass_rate": pass_rate,
            "passed": passed,
            "total": len(TEST_CASES),
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {result_path}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NURBS 专家模型推理测试")
    parser.add_argument("--host", default="http://localhost:11434",
                        help="Ollama 服务地址")
    parser.add_argument("--model", default="nurbs-expert",
                        help="模型名称")
    parser.add_argument("--api-url", default="http://localhost:8000",
                        help="后端 API 地址（--via-api 模式）")
    parser.add_argument("--via-api", action="store_true",
                        help="通过后端 API 测试（而非直连 Ollama）")
    args = parser.parse_args()

    run_tests(args)
