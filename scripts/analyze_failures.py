"""失败用例深度分析 — 逐题输出、关键词命中、根因归类"""
import json
from pathlib import Path

results_path = Path("data/training/test_results.json")
results = json.loads(results_path.read_text(encoding="utf-8"))

# 10 道测试用例的完整定义（与 test_nurbs_inference.py 一致）
TEST_CASES = [
    {
        "id": 1, "category": "nurbs_basics",
        "question": "什么是NURBS曲面的G1连续性？",
        "keywords": ["切向量", "法向量", "1度", "共享边界"],
        "min_score": 2,
        "actual_answer": "在NURBS曲面上，G1连续性是指曲线或表面上的相邻两点之间的弯曲程度是相同的。换句话说，如果两个相邻点的弯曲度相同，则称它们为G1连续。具体来说，对于一个平面NURBS曲面，G1连续性的判断方法如下：1. **计算相邻点的弯曲角度**：首先，我们需要找到两个相邻点的位置坐标。然后，分别计算...",
    },
    {
        "id": 2, "category": "component_design",
        "question": "车身蒙皮(body_upper_skin)的控制点网格是多少？为什么？",
        "keywords": ["30", "20", "600", "车身", "复杂"],
        "min_score": 2,
        "pass": True,
    },
    {
        "id": 3, "category": "continuity",
        "question": "车身与前保险杠的G0和G1值分别是多少？",
        "keywords": ["0.000", "0.131"],
        "min_score": 2,
        "actual_answer": "在您的问题中，您提到的是车身与前保险杠之间的几何参数。具体来说：1. **G0** 是指车身与前保险杠之间最宽处的最大距离。2. **G1** 是指车身与前保险杠之间最小的距离。这些值通常通过测量或计算得出，并且是汽车设计中的重要参数之一。如果您需要具体的数值，请提供更多的上下文信息或者直...",
    },
    {
        "id": 4, "category": "sop",
        "question": "SOP检查项8的R角为什么在参数化NURBS车身中大量FAIL？",
        "keywords": ["参数化", "R角", "无传统", "FAIL", "11"],
        "min_score": 2,
        "pass": True,
    },
    {
        "id": 5, "category": "component_design",
        "question": "进气格栅(grille)的控制点结构是什么？",
        "keywords": ["4", "3", "12", "degree"],
        "min_score": 2,
        "pass": True,
    },
    {
        "id": 6, "category": "continuity",
        "question": "整车NURBS模型有多少个曲面零件？连续性配对有多少对？",
        "keywords": ["18", "124", "配对"],
        "min_score": 2,
        "actual_answer": "整车NURBS模型中包含多个曲面零件。具体数量可能因车型和设计需求而异，但通常会涉及至少一个曲面零件。关于连续性配对的数量，这取决于具体的车辆设计要求以及所使用的NURBS曲线类型。例如：1. **G0/G1连续性**：用于定义车辆轮廓的一系列连续的曲面。2. **G2连续性**：用于定义...",
    },
    {
        "id": 7, "category": "quality_assessment",
        "question": "什么是ISO曲率检查？阈值是多少？",
        "keywords": ["梯度", "ratio", "10", "曲率"],
        "min_score": 2,
        "actual_answer": "ISO曲率检查是一种用于检测曲面几何形状是否符合特定标准的技术。它通过比较曲面上不同位置的曲率来判断曲面的质量和一致性。ISO曲率检查的阈值通常由制造商或相关标准组织设定，以确保曲面在实际应用中能够满足预期的功能要求。常见的ISO曲率检查阈值包括：1. ISO 2000：对于平面曲面，该阈值...",
    },
    {
        "id": 8, "category": "parametric_design",
        "question": "NURBS车身的坐标系是如何定义的？默认参数是什么？",
        "keywords": ["X", "Y", "Z", "4700", "1850", "1450"],
        "min_score": 3,
        "actual_answer": "在NURBS（Non-uniform Rational B-Spline）模型中，坐标系通常由一组控制点和一个或多个节点来定义。这些控制点是用于描述曲线、面和体的基本形状的点，而节点则是连接这些控制点的线段。### 默认参数1. **控制点数量**：NURBS模型中的控制点数量取...",
    },
    {
        "id": 9, "category": "sop",
        "question": "SOP检查的自动化覆盖率是多少？PASS率是多少？",
        "keywords": ["37%", "79%", "67", "53"],
        "min_score": 2,
        "actual_answer": "对不起，我无法提供关于SOP检查自动化覆盖率和PASS率的具体信息。这些指标通常由专业的汽车工程师或测试团队来确定，并且可能受到多种因素的影响，包括使用的工具、测试环境等。如果你需要了解某个特定车型的SOP检查自动化覆盖...",
    },
    {
        "id": 10, "category": "continuity",
        "question": "哪些设计间隙是正常的？哪些需要修复？",
        "keywords": ["装配间隙", "凹陷", "外凸", "recess", "bulge", "车轮"],
        "min_score": 3,
        "actual_answer": "在汽车A级曲面设计中，常见的设计间隙包括但不限于：1. **正常间隙**：这些间隙通常是在设计过程中通过调整参数来实现的。例如，通过改变曲面的形状、厚度或材料选择等方法来减少或消除间隙。2. **真间隙**：如果间隙过大，可能会影响车辆的安全性能和舒适度。因此，在设计时应尽量避免设置较大的间...",
    },
]

# 归类
CAUSE_CATEGORIES = {
    "LACK_PLATFORM_SPECIFIC_KNOWLEDGE": "❌ 缺乏 Evolution-AI.Design 平台特定数据（实测数值、统计数据）",
    "WRONG_DEFINITION": "❌ 概念定义错误（混淆了 G0/G1 含义）",
    "LACK_VOCABULARY": "❌ 缺乏专业词汇（recess/bulge/装配间隙/梯度比等）",
    "REFUSAL_TO_ANSWER": "❌ 模型拒绝回答（'无法提供具体信息'）",
}

print("=" * 80)
print("  NURBS Expert Inference — Failure Analysis (7/10 FAILED)")
print("=" * 80)

failed = [tc for tc in TEST_CASES if not tc.get("pass", False)]
for idx, tc in enumerate(failed, 1):
    # 逐个关键词检查
    keyword_hits = []
    for kw in tc["keywords"]:
        hit = kw.lower() in tc.get("actual_answer", "").lower()
        keyword_hits.append((kw, hit))
    hits = sum(1 for _, h in keyword_hits if h)

    # 归类根因
    answer = tc.get("actual_answer", "")
    causes = []
    if "无法提供" in answer or "对不起" in answer:
        causes.append(CAUSE_CATEGORIES["REFUSAL_TO_ANSWER"])
    if hits < tc["min_score"] and tc["category"] in ("continuity", "sop", "parametric_design") and any(k in answer for k in ["可能因", "取决于具体", "通常由"]):
        causes.append(CAUSE_CATEGORIES["LACK_PLATFORM_SPECIFIC_KNOWLEDGE"])
    if tc["id"] == 3 and ("最宽处" in answer or "最小的距离" in answer):
        causes.append(CAUSE_CATEGORIES["WRONG_DEFINITION"])
    if not any(kw in answer for kw in ["recess", "bulge", "凹陷", "外凸", "装配间隙", "梯度"]) and tc["id"] in (7, 10):
        causes.append(CAUSE_CATEGORIES["LACK_VOCABULARY"])
    if not causes and hits < tc["min_score"]:
        causes.append(CAUSE_CATEGORIES["LACK_PLATFORM_SPECIFIC_KNOWLEDGE"])

    # 打印
    print(f"\n{'─' * 80}")
    print(f"  ❌ [{idx}/7] 题 {tc['id']} — {tc['category']}")
    print(f"{'─' * 80}")
    print(f"  问题:   {tc['question']}")
    print(f"  分值:   {hits}/{len(tc['keywords'])} keywords | 需要 ≥ {tc['min_score']}")
    print(f"  耗时:   {results['results'][tc['id']-1]['duration']:.1f}s | "
          f"Tokens: {results['results'][tc['id']-1]['tokens']}")

    print(f"\n  关键词命中:")
    for kw, hit in keyword_hits:
        mark = "✓" if hit else "✗"
        color = "\033[92m" if hit else "\033[91m"
        end = "\033[0m"
        print(f"    {color}{mark}{end} {kw}")

    print(f"\n  模型回答 (截断):")
    answer_preview = answer[:300].replace("\n", " ")
    print(f"    \"{answer_preview}...\"")

    print(f"\n  根因分析:")
    for cause in causes:
        print(f"    {cause}")

# 汇总
print("\n" + "=" * 80)
print("  根因汇总")
print("=" * 80)
cause_counts = {k: 0 for k in CAUSE_CATEGORIES}
for tc in failed:
    answer = tc.get("actual_answer", "")
    if "无法提供" in answer or "对不起" in answer:
        cause_counts["REFUSAL_TO_ANSWER"] += 1
    hits = sum(1 for kw in tc["keywords"] if kw.lower() in answer.lower())
    if hits < tc["min_score"] and tc["id"] == 3 and ("最宽处" in answer or "最小的距离" in answer):
        cause_counts["WRONG_DEFINITION"] += 1
    if (not any(kw in answer for kw in ["recess", "bulge", "凹陷", "外凸"])) and tc["id"] == 10:
        cause_counts["LACK_VOCABULARY"] += 1
    if (not any(kw in answer for kw in ["梯度", "ratio", "10"])) and tc["id"] == 7:
        cause_counts["LACK_VOCABULARY"] += 1
    counts_remaining = sum(v for k, v in cause_counts.items() if k != "LACK_PLATFORM_SPECIFIC_KNOWLEDGE")
    cause_counts["LACK_PLATFORM_SPECIFIC_KNOWLEDGE"] = 7 - counts_remaining

for cause_key, desc in CAUSE_CATEGORIES.items():
    count = cause_counts[cause_key]
    if count > 0:
        bar = "█" * count + "░" * (7 - count)
        pct = count / 7 * 100
        print(f"\n  {bar} ({count}/7, {pct:.0f}%)")
        print(f"  {desc}")

# 分类统计
print("\n" + "=" * 80)
print("  按类别失败分布")
print("=" * 80)
cat_fail = {}
for tc in failed:
    cat = tc["category"]
    cat_fail[cat] = cat_fail.get(cat, 0) + 1

cat_total = {}
for tc in TEST_CASES:
    cat_total[tc["category"]] = cat_total.get(tc["category"], 0) + 1

for cat in sorted(cat_fail.keys()):
    f = cat_fail[cat]
    t = cat_total[cat]
    print(f"\n  {cat:25s}: {f}/{t} failed ({f/t*100:.0f}%)")
    print(f"    失败题目: {', '.join(str(tc['id']) for tc in failed if tc['category']==cat)}")

# 改进建议
print("\n" + "=" * 80)
print("  改进建议")
print("=" * 80)

suggestions = [
    ("1. 微调注入平台特定数据",
     "所有 7 道失败题目都涉及 Evolution-AI.Design 的实测数值",
     "将 52 条 JSONL 数据通过 QLoRA 微调注入模型（重点：数值精确记忆）"),
    ("2. 引入 RAG 检索层",
     "G0=0.000mm、G1=0.131deg、18曲面/124配对、37%/79%等具体数字难以记忆",
     "从 parametric_design_knowledge.json 做精确数值检索，作为 LLM 上下文补充"),
    ("3. 修正系统提示词中的 G0/G1 定义",
     "题 3 模型把 G0 误定义为最宽距离、G1 误定义为最小距离",
     "系统提示词中加入 G0/G1 定义的明确示例: G0=距离(mm), G1=角度(deg)"),
    ("4. 加入专业词汇增强训练",
     "题 10 未命中装配间隙/recess/bulge；题 7 未命中梯度/ratio",
     "训练数据中增加术语定义的样本；或在 prompt 中要求使用中文+英文术语"),
    ("5. 避免无法回答的拒答模式",
     "题 9 直接回答无法提供具体信息（虽然有 30% SOP 统计知识）",
     "系统提示词中加入: 如果是关于 Evolution-AI.Design 平台的数字, 务必从训练数据中尝试回忆"),
    ("6. 升级到 7B 模型 + 微调",
     "当前 0.5B 模型容量太小（30% → 预期 7B+QLoRA → 80%+）",
     "用 deploy_finetuned.py 完整管线：QLoRA 微调 Qwen2.5-7B"),
]

for title, problem, solution in suggestions:
    print(f"\n  👉 {title}")
    print(f"     问题: {problem}")
    print(f"     方案: {solution}")

# 预期提升效果
print("\n" + "=" * 80)
print("  预期提升效果")
print("=" * 80)
baseline = 30
for label, expected in [
    ("当前基线 (0.5B 基础模型)", "30%"),
    ("+ RAG 检索精确数值", "60-70%"),
    ("+ QLoRA 微调 7B 模型 (52 条数据)", "70-80%"),
    ("+ 微调 + RAG 混合", "80-90%"),
    ("+ 参数 sweep 数据 + 500 条样本", "90%+"),
]:
    print(f"  {label:40s}: {expected}")
print()
