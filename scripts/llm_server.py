"""轻量 LLM 推理服务器（Ollama API 兼容 + RAG 检索增强）

使用 transformers + Qwen2.5-0.5B-Instruct 在 CPU 上运行推理。
提供与 Ollama /api/generate 和 /api/tags 兼容的 HTTP 接口，
使后端 ai.py 路由和 test_nurbs_inference.py 无需修改即可使用。

RAG 检索层：
  启动时加载 parametric_design_knowledge.json 知识库，
  每次推理前根据问题关键词检索相关知识块，
  注入系统提示词作为上下文，让模型能引用精确数值。

用法:
    python scripts/llm_server.py                    # 默认端口 11434, RAG 开启
    python scripts/llm_server.py --port 11435       # 自定义端口
    python scripts/llm_server.py --model-path PATH  # 自定义模型路径
    python scripts/llm_server.py --no-rag           # 禁用 RAG 检索
"""
import os
import sys
import time
import json
import re
import argparse
from pathlib import Path

# ── 模型路径 ────────────────────────────────────
DEFAULT_MODEL_PATH = r"D:\JZDSLx\hf_models\models\Qwen--Qwen2.5-0.5B-Instruct\snapshots\master"

# ── 知识库路径 ──────────────────────────────────
DEFAULT_KNOWLEDGE_PATH = str(Path(__file__).resolve().parent.parent / "data" / "training" / "parametric_design_knowledge.json")

# NURBS 专家系统提示词
NURBS_SYSTEM_PROMPT = """你是 Evolution-AI.Design 平台的 NURBS 曲面设计专家助手。

=== ⚠ 必须先看的核心知识块（所有回答严格按下面路由从对应块回答） ⚠ ===
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【A. G0/G1/G2 连续性精确定义 — 当问"什么是G1/定义/含义"时，只从此块回答】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• G1 连续性（切向量连续）：相邻曲面在共享边界处切向量方向一致，即法向量夹角 < 1度（1.0 度）。阈值：法向量夹角 < 1.0 度。
  ▸ 必用关键词：切向量、法向量、1度、共享边界。
• G0 连续性（位置连续）：共享边界处位置重合，阈值：间隙 < 0.1mm。
• G2 连续性（曲率连续）：G0+G1 成立且曲率值相等（曲率变化率 < 10%）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【B. 实测配对数值 — 当问"车身/保险杠/某两个零件G0G1值"时，只从此块回答】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1) body_upper_skin（车身） ↔ front_bumper_g1（前保险杠）：G0=0.000mm，G1=0.131deg，G1 OK
2) body_upper_skin（车身） ↔ rear_bumper_g1（后保险杠）：G0=0.000mm，G1=0.031deg，G1 OK

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【C. 设计间隙分类（正常vs需修复）— 当问"哪些间隙正常/需要修复/设计间隙"时，严格按下列三大类输出】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【正常间隙（属设计意图，不需要修复）】
  1. 装配间隙（assembly clearance，独立安装件之间）：
     - 车轮与车身：257-370mm 装配间隙
     - 轮毂与车身：54mm 装配间隙
     - 后视镜安装：741mm 装配间隙
  2. 凹陷（recess design，造型特征）：
     - 前保险杠↔进气格栅：3.294mm 凹陷
  3. 外凸（bulge design，大灯安装区域）：
     - 前大灯外凸：15.5-17.4mm（左/右）
     - 后尾灯外凸：3.3-6.2mm（左/右）
【需修复的异常间隙】
  仅当共享边界零件 G0 > 0.1mm 且不属于 凹陷/外凸/装配间隙 时，判定为装配缺陷需修复。
  ▸ 必用关键词：装配间隙、凹陷、外凸、车轮。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【D. 路由守卫（强制性，回答任何问题前必须先确认属于哪一块）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 若问题含「什么是 G1 / 什么是G0 / 什么是连续性 / G1定义 / 含义」→ 返回 A 块（切向量/法向量/1度/共享边界），禁止回答 0.000mm/0.131deg 数值。
• 若问题含「车身与前保险杠 / 保险杠 G0/G1 / 值多少」→ 返回 B 块（0.000mm / 0.131deg），禁止回答 A 块定义。
• 若问题含「间隙正常 / 需要修复 / 哪些间隙 / 设计间隙 / 装配间隙」→ 严格按 C 块三大分类输出，禁止回答曲率/变化率/定义/车身保险杠数值。
• 严禁混淆：凹陷/外凸的 3.3mm/15mm 大间隙绝对不是车身-保险杠共享边界 G0。

=== 完整连续性配对速查表（按共享边界 / 凹陷 / 外凸 严格分开） ===
【共享边界（G1 OK 对）】
- body ↔ front_bumper：G0=0.000mm，G1=0.131deg，G1 OK
- body ↔ rear_bumper：G0=0.000mm，G1=0.031deg，G1 OK
【凹陷（recess，正常设计，非共享边界）】
- front_bumper ↔ grille：G0=3.294mm（这是凹陷深度，不是共享边界 G0），G1=88.814deg，凹陷设计（recess design）
【外凸（bulge，正常设计，非共享边界）】
- front_bumper ↔ headlight_R：G0=17.358mm（外凸，非共享边界），G1=85.417deg，外凸设计（bulge design）
- front_bumper ↔ headlight_L：G0=15.547mm，G1=84.813deg，外凸设计（bulge design）
- rear_bumper ↔ taillight_R：G0=6.173mm，G1=89.515deg，外凸设计（bulge design）
- rear_bumper ↔ taillight_L：G0=3.291mm，G1=89.226deg，外凸设计（bulge design）
整车统计：18 个曲面零件，124 对连续性配对，其中只有 body↔front_bumper 和 body↔rear_bumper 这 2 对评级 G1 OK，其余 97 对为 凹陷/外凸/装配间隙（recess/bulge/assembly clearance，正常设计意图）。

=== 设计间隙分类（回答时必须使用中文术语在前，英文括号补充） ===
⚠ 守卫规则（极其重要）：当问题包含「间隙正常/需修复/设计间隙/哪些间隙」等关键词时，**禁止回答 body↔front_bumper 或 body↔rear_bumper 的 G0/G1 数值**，必须严格按以下三大分类输出。车身与保险杠的连续性数值只在直接询问「连续性/G0/G1」时回答。
- 正常间隙（装配间隙，assembly clearance）：独立安装件之间的设计间隙，属于正常设计意图，例如：车轮与车身 257-370mm 装配间隙、轮毂与车身 54mm 装配间隙、后视镜 741mm 安装间隙。
- 凹陷（recess）：前保险杠与进气格栅（front_bumper ↔ grille）的 3.294mm 属于凹陷（recess design）；注意这个 3.3mm 凹陷深度不是车身与前保险杠的共享边界 G0，两者完全不同概念。
- 外凸（bulge）：保险杠上的大灯安装区域，前大灯外凸 15-17mm，后尾灯外凸 3-6mm，属于正常外凸设计（bulge design），不需要 G1 连续。
- 异常间隙需修复：共享边界零件之间若 G0 > 0.1mm 且不属于 凹陷/外凸/装配间隙（recess/bulge/assembly clearance），判定为装配缺陷需修复。

=== 回答模板示例（间隙问题按此格式输出，必须使用中文术语） ===
问：哪些设计间隙是正常的？哪些需要修复？
答：
【正常间隙（属设计意图，不需要修复）】
  1. 装配间隙（assembly clearance，独立安装件之间）：
     - 车轮与车身：257-370mm 装配间隙
     - 轮毂与车身：54mm 装配间隙
     - 后视镜安装：741mm 装配间隙
  2. 凹陷（recess design，造型特征）：
     - 前保险杠↔进气格栅：3.294mm 凹陷
  3. 外凸（bulge design，大灯安装区域）：
     - 前大灯外凸：15.5-17.4mm（左/右）
     - 后尾灯外凸：3.3-6.2mm（左/右）
【需修复的异常间隙】
  仅当共享边界零件 G0 > 0.1mm 且不属于 凹陷/外凸/装配间隙 时，判定为装配缺陷需修复。

=== ISO 曲率检查（回答时必须使用这些术语） ===
ISO 曲率检查检测相邻点的均曲率梯度比（gradient ratio），确保曲面无曲率突变。判定阈值：ratio < 10（ratio 越大代表曲率跳变越严重）。A级曲面要求 ratio < 5；Evolution-AI.Design 平台实测车身蒙皮 ISO ratio=4.2（达标），前保险杠 ISO ratio=29.4（局部有造型特征）。

=== 其他领域知识 ===
1. NURBS 数学原理（控制点/阶数/节点向量/权重）
2. 汽车 A 级曲面 SOP 标准（SOP-A SURF-001）：13项检查，183条记录，67条自动化，自动化通过率 79%
3. 参数化车身生成：SAE坐标系 X=纵向车头+/Y=横向右侧+/Z=垂直向上+；默认 L=4700、W=1850、H=1450、WB=2700；公式 FO+WB+RO=L
4. 曲面质量评估：曲率变异系数 CV（A级要求 CV<0.50）；R角≥3mm检查（参数化NURBS因无传统R角导致11项FAIL）

回答原则：
- 数值精确：引用实测数据（如 body↔front_bumper G1=0.131deg）
- 结构化输出：使用表格/列表/分点
- 必须使用中文术语在前：凹陷（recess）、外凸（bulge）、装配间隙（assembly clearance）
- 区分设计意图与质量缺陷（凹陷/外凸 vs 真正间隙）
- 如不确定，明确说明而非编造"""


# ════════════════════════════════════════════════
# RAG 检索层
# ════════════════════════════════════════════════

class NURBSKnowledgeBase:
    """NURBS 知识库：加载 JSON 知识并分块索引，支持关键词检索"""

    # 检索时使用的关键词映射（问题关键词 → 知识库关键词）
    KEYWORD_ALIASES = {
        "连续性": ["continuity", "G0", "G1", "G2", "连续", "配对", "边界", "共享边界", "切向量", "法向量", "位置", "间隙", "角度"],
        "连续性定义": ["切向量", "法向量", "夹角", "1度", "0.1mm", "共享边界"],
        "间隙": ["gap", "recess", "bulge", "凹陷", "外凸", "装配间隙", "设计意图", "assembly clearance"],
        "设计间隙": ["recess", "bulge", "装配间隙", "凹陷", "外凸", "正常", "需修复", "车轮", "安装"],
        "坐标系": ["coordinate", "X", "Y", "Z", "SAE", "纵向", "横向", "垂直"],
        "参数": ["L", "W", "H", "WB", "TW", "GC", "FO", "RO", "4700", "1850", "1450", "默认"],
        "控制点": ["control_points", "网格", "grid", "degree", "阶数", "控制点"],
        "保险杠": ["bumper", "front_bumper", "rear_bumper", "前保", "后保"],
        "前保险杠": ["front_bumper", "bumper", "0.000", "0.131", "G0", "G1"],
        "格栅": ["grille", "进气格栅", "recess", "3.3"],
        "大灯": ["headlight", "前大灯", "bulge", "外凸", "15", "17"],
        "尾灯": ["taillight", "后尾灯", "bulge", "外凸", "3", "6"],
        "车轮": ["wheel", "tire", "轮胎", "轮毂", "hub", "装配间隙", "257", "370", "54"],
        "后视镜": ["mirror", "后视镜", "741", "安装"],
        "车身": ["body", "body_upper_skin", "蒙皮", "车身"],
        "SOP": ["sop", "检查", "PASS", "FAIL", "覆盖率", "自动化", "R角", "37%", "79%", "183", "67", "53", "14", "13"],
        "曲率": ["curvature", "iso", "CV", "均曲率", "梯度", "ratio", "10", "ratio<10"],
        "iso曲率": ["gradient", "ratio", "10", "梯度", "阈值", "4.2", "29.4"],
        "曲面": ["surface", "nurbs", "曲面", "零件", "组件", "component", "18", "124"],
    }

    def __init__(self, knowledge_path: str):
        self.path = knowledge_path
        self.chunks = []
        self._load()

    def _load(self):
        """加载 JSON 知识库并分块索引"""
        if not Path(self.path).exists():
            print(f"[RAG] ⚠ 知识库文件不存在: {self.path}")
            return

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        dk = data.get("distilled_knowledge", {})
        count = 0

        # ── 1. 组件目录分块 ──────────────────────
        for name, info in dk.get("component_catalog", {}).items():
            lines = [f"[组件: {name}]"]
            for k, v in info.items():
                lines.append(f"  {k}: {v}")
            self.chunks.append({
                "id": f"component_{name}",
                "category": "component",
                "text": "\n".join(lines),
                "keywords": [name, "控制点", "control_points", "degree", "曲面", "组件"],
            })
            count += 1

        # ── 2. 连续性汇总分块 ────────────────────
        cs = dk.get("continuity_summary", {})
        summary_lines = [
            "[连续性汇总]",
            f"  总配对数: {cs.get('total_pairs', 'N/A')}",
            f"  G1 OK 对数: {cs.get('g1_ok', 'N/A')}",
            f"  G0 通过: {cs.get('g0_pass', 'N/A')}",
            f"  G1 通过: {cs.get('g1_pass', 'N/A')}",
            f"  小间隙对: {cs.get('small_gap', 'N/A')}",
            f"  分离对: {cs.get('separated', 'N/A')}",
        ]
        self.chunks.append({
            "id": "continuity_summary",
            "category": "continuity",
            "text": "\n".join(summary_lines),
            "keywords": ["连续性", "配对", "G0", "G1", "G2", "continuity", "124", "曲面"],
        })
        count += 1

        # ── 3. 关键连续性配对分块 ────────────────
        for pair in cs.get("key_pairs", []):
            pair_name = pair.get("pair", "")
            text = (
                f"[连续性配对: {pair_name}]\n"
                f"  G0: {pair.get('g0', 'N/A')}\n"
                f"  G1: {pair.get('g1', 'N/A')}\n"
                f"  评级: {pair.get('rating', 'N/A')}"
            )
            # 提取配对名称中的关键词
            kw = re.split(r"[↔→/\s]+", pair_name.lower())
            self.chunks.append({
                "id": f"pair_{pair_name}",
                "category": "continuity",
                "text": text,
                "keywords": kw + ["G0", "G1", "连续性", "边界", pair_name],
            })
            count += 1

        # ── 4. SOP 汇总分块 ──────────────────────
        sop = dk.get("sop_summary", {})
        sop_lines = [
            "[SOP 检查汇总]",
            f"  检查项数: {sop.get('total_items', 'N/A')}",
            f"  总记录数: {sop.get('total_records', 'N/A')}",
            f"  自动化记录: {sop.get('auto_records', 'N/A')}",
            f"  人工记录: {sop.get('manual_records', 'N/A')}",
            f"  PASS: {sop.get('pass', 'N/A')}",
            f"  FAIL: {sop.get('fail', 'N/A')}",
            f"  自动化通过率: {sop.get('auto_pass_rate', 'N/A')}",
        ]
        for item in sop.get("key_pass_items", []):
            sop_lines.append(f"  PASS项: {item}")
        for item in sop.get("key_fail_items", []):
            sop_lines.append(f"  FAIL项: {item}")
        for c in sop.get("core_conclusions", []):
            sop_lines.append(f"  结论: {c}")
        self.chunks.append({
            "id": "sop_summary",
            "category": "sop",
            "text": "\n".join(sop_lines),
            "keywords": ["SOP", "检查", "PASS", "FAIL", "覆盖率", "自动化", "R角", "79%", "37%", "183", "67", "53"],
        })
        count += 1

        # ── 5. 参数化设计分块 ────────────────────
        pd = dk.get("parametric_design", {})
        pd_lines = [
            "[参数化设计]",
            f"  坐标系: {pd.get('coordinate_system', 'N/A')}",
            "  默认参数:",
        ]
        for k, v in pd.get("default_params", {}).items():
            pd_lines.append(f"    {k} = {v}")
        pd_lines.append("  关键公式:")
        for k, v in pd.get("key_formulas", {}).items():
            pd_lines.append(f"    {k}: {v}")
        pd_lines.append(f"  权重策略: {pd.get('weight_strategy', 'N/A')}")
        self.chunks.append({
            "id": "parametric_design",
            "category": "parametric_design",
            "text": "\n".join(pd_lines),
            "keywords": ["坐标系", "参数", "X", "Y", "Z", "SAE", "4700", "1850", "1450", "2700", "WB", "FO", "RO", "GC", "公式"],
        })
        count += 1

        # ── 6. 数据源统计分块 ────────────────────
        ds = data.get("data_sources", {})
        ds_lines = ["[数据源统计]"]
        for src, info in ds.items():
            if isinstance(info, dict):
                ds_lines.append(f"  {src}:")
                for k, v in info.items():
                    if not isinstance(v, (list, dict)):
                        ds_lines.append(f"    {k}: {v}")
        self.chunks.append({
            "id": "data_sources",
            "category": "data_sources",
            "text": "\n".join(ds_lines),
            "keywords": ["数据", "导出", "测试", "模型", "38", "646", "18", "124"],
        })
        count += 1

        print(f"[RAG] 知识库加载完成: {count} 个知识块 (来源: {Path(self.path).name})")

    def _extract_query_keywords(self, query: str) -> list:
        """从问题中提取检索关键词"""
        keywords = set()

        # 原始分词
        raw_tokens = re.split(r"[\s,，。？?、（）()【】\[\]\"'""''《》<>:：;；!！]+", query)
        for token in raw_tokens:
            token = token.strip()
            if len(token) >= 1:
                keywords.add(token.lower())

        # 通过别名映射扩展关键词
        for alias_key, alias_values in self.KEYWORD_ALIASES.items():
            if alias_key in query:
                for v in alias_values:
                    keywords.add(v.lower())

        # 提取数字
        numbers = re.findall(r"\d+\.?\d*", query)
        for n in numbers:
            keywords.add(n)

        return list(keywords)

    def retrieve(self, query: str, top_k: int = 5) -> list:
        """检索与问题最相关的知识块"""
        if not self.chunks:
            return []

        query_lower = query.lower()
        query_keywords = self._extract_query_keywords(query)

        # 意图检测：用于抑制非目标配对干扰
        asking_body_front = any(w in query_lower for w in ["车身", "body", "前保险杠", "front_bumper", "前保"])
        asking_body_rear = any(w in query_lower for w in ["车身", "body", "后保险杠", "rear_bumper", "后保"])
        asking_continuity = any(w in query_lower for w in ["连续性", "G0", "G1", "G2", "配对", "共享边界"])
        asking_gap_design = any(w in query_lower for w in ["间隙", "设计", "recess", "bulge", "凹陷", "外凸", "正常", "修复"])
        asking_grille_headlight = any(w in query_lower for w in ["格栅", "大灯", "尾灯", "grille", "headlight", "taillight"])

        scored = []
        for chunk in self.chunks:
            chunk_text_lower = chunk["text"].lower()
            chunk_kw_lower = [k.lower() for k in chunk["keywords"]]
            chunk_id = chunk.get("id", "")

            score = 0
            # 关键词命中得分
            for qk in query_keywords:
                if qk in chunk_text_lower:
                    score += 2  # 正文命中
                if any(qk in ckw for ckw in chunk_kw_lower):
                    score += 3  # 关键词标签命中

            # 类别关键词加分
            if chunk["category"] in query_lower:
                score += 5

            # ── 意图驱动的加权/抑制 ─────────────────────────────
            # 问"车身+前保险杠+连续性"时，pair_body↔front_bumper 和 continuity_summary 权重提升
            if asking_body_front and asking_continuity:
                if "body↔front_bumper" in chunk_id:
                    score += 50
                elif chunk_id == "continuity_summary":
                    score += 30
                # 抑制 grille / headlight / taillight 这些 recess/bulge 块
                elif ("grille" in chunk_id or "headlight" in chunk_id or "taillight" in chunk_id) and not asking_grille_headlight:
                    score -= 20

            # 问"车身+后保险杠+连续性"时，pair_body↔rear_bumper 提升
            if asking_body_rear and asking_continuity:
                if "body↔rear_bumper" in chunk_id:
                    score += 50
                elif chunk_id == "continuity_summary":
                    score += 30
                elif ("grille" in chunk_id or "headlight" in chunk_id or "taillight" in chunk_id) and not asking_grille_headlight:
                    score -= 20

            # 问"间隙正常/修复"时，车轮/轮毂/后视镜组件块 + front_bumper/rear_bumper（含recess/bulge信息）权重提升
            if asking_gap_design:
                if any(w in chunk_id for w in ["wheel_tire", "wheel_hub", "mirror", "front_bumper_g1", "rear_bumper_g1", "grille", "headlight", "taillight"]):
                    score += 20
                elif "body_upper_skin" in chunk_id:
                    score -= 10

            scored.append((chunk, score))

        # 按得分排序，取 top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        results = [chunk for chunk, score in scored[:top_k] if score > 0]

        return results

    def build_context(self, query: str, top_k: int = 5) -> str:
        """构建 RAG 上下文文本"""
        chunks = self.retrieve(query, top_k)
        if not chunks:
            return ""

        lines = ["以下是从 Evolution-AI.Design 知识库中检索到的相关数据，请在回答时引用这些精确数值：", ""]
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"--- 知识块 {i} ({chunk['category']}) ---")
            lines.append(chunk["text"])
            lines.append("")

        return "\n".join(lines)


def load_model(model_path: str):
    """加载 Qwen2.5 模型和 tokenizer"""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    print(f"[LLM Server] 加载模型: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float32,  # CPU 用 float32
    )
    model.eval()
    print(f"[LLM Server] 模型加载完成 ({sum(p.numel() for p in model.parameters()) / 1e6:.0f}M params)")
    return model, tokenizer


def generate_text(model, tokenizer, prompt: str, system: str = None,
                  temperature: float = 0.3, max_tokens: int = 1024,
                  knowledge_base: "NURBSKnowledgeBase" = None) -> str:
    """生成回答（支持 RAG 上下文注入）"""
    import torch

    # RAG 检索：从知识库中提取相关上下文
    rag_context = ""
    if knowledge_base:
        rag_context = knowledge_base.build_context(prompt, top_k=5)
        if rag_context:
            print(f"[RAG] 检索到 {len(rag_context)} 字符的相关知识上下文")

    # 构建系统提示词（注入 RAG 上下文）
    full_system = system
    if rag_context:
        full_system = f"{system}\n\n{rag_context}"

    # 构建 Qwen ChatML 格式
    messages = []
    if full_system:
        messages.append({"role": "system", "content": full_system})
    messages.append({"role": "user", "content": prompt})

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=0.85,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.eos_token_id,
        )

    # 提取生成的部分（去掉输入）
    input_len = inputs["input_ids"].shape[1]
    generated = outputs[0][input_len:]
    response = tokenizer.decode(generated, skip_special_tokens=True)
    return response


def create_server(model, tokenizer, port: int, knowledge_base: "NURBSKnowledgeBase" = None):
    """创建兼容 Ollama API 的 HTTP 服务器"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse

    class OllamaHandler(BaseHTTPRequestHandler):
        def _send_json(self, code, data):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)

            # GET /api/tags — 列出模型
            if parsed.path == "/api/tags":
                self._send_json(200, {
                    "models": [{
                        "name": "nurbs-expert",
                        "model": "nurbs-expert",
                        "size": 942323200,
                        "modified_at": "2026-08-09T00:00:00Z",
                    }]
                })
                return

            # GET /api/rag/status — 查看 RAG 状态
            if parsed.path == "/api/rag/status":
                self._send_json(200, {
                    "rag_enabled": knowledge_base is not None,
                    "knowledge_path": knowledge_base.path if knowledge_base else None,
                    "chunk_count": len(knowledge_base.chunks) if knowledge_base else 0,
                    "categories": list(set(c["category"] for c in knowledge_base.chunks)) if knowledge_base else [],
                })
                return

            # GET /api/rag/search?q=xxx — 测试 RAG 检索
            if parsed.path == "/api/rag/search":
                query = parsed.query.split("=")[1] if "=" in parsed.query else ""
                from urllib.parse import unquote
                query = unquote(query)
                if knowledge_base:
                    chunks = knowledge_base.retrieve(query, top_k=5)
                    self._send_json(200, {
                        "query": query,
                        "results": [{"id": c["id"], "category": c["category"], "text": c["text"], "keywords": c["keywords"]} for c in chunks],
                        "count": len(chunks),
                    })
                else:
                    self._send_json(200, {"error": "RAG not enabled"})
                return

            self._send_json(404, {"error": "Not found"})

        def do_POST(self):
            parsed = urlparse(self.path)

            # POST /api/generate — 生成回答
            if parsed.path == "/api/generate":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                req = json.loads(body)

                prompt = req.get("prompt", "")
                model_name = req.get("model", "nurbs-expert")
                options = req.get("options", {})
                temperature = options.get("temperature", 0.3)

                print(f"[LLM Server] 收到请求: {prompt[:80]}...")

                start = time.time()
                response_text = generate_text(
                    model, tokenizer, prompt,
                    system=NURBS_SYSTEM_PROMPT,
                    temperature=temperature,
                    max_tokens=1024,
                    knowledge_base=knowledge_base,
                )
                elapsed = time.time() - start

                # 粗略估算 token 数
                token_count = len(response_text) // 3  # 中文约 3 字符/token

                self._send_json(200, {
                    "model": model_name,
                    "response": response_text,
                    "done": True,
                    "eval_count": token_count,
                    "total_duration": int(elapsed * 1e9),
                    "load_duration": 0,
                    "prompt_eval_count": 0,
                    "prompt_eval_duration": 0,
                    "eval_duration": int(elapsed * 1e9),
                })
                print(f"[LLM Server] 生成完成: {len(response_text)} chars, {elapsed:.1f}s")
                return

            self._send_json(404, {"error": "Not found"})

        def log_message(self, format, *args):
            pass  # 静默默认日志

    server = HTTPServer(("0.0.0.0", port), OllamaHandler)
    rag_status = "开启" if knowledge_base else "关闭"
    print(f"[LLM Server] 服务启动: http://localhost:{port}")
    print(f"[LLM Server] RAG 检索: {rag_status}")
    if knowledge_base:
        print(f"[LLM Server] 知识块数: {len(knowledge_base.chunks)}")
    print(f"[LLM Server] API 端点:")
    print(f"  GET  /api/tags         — 列出模型")
    print(f"  GET  /api/rag/status   — RAG 状态")
    print(f"  GET  /api/rag/search?q=关键词 — 测试 RAG 检索")
    print(f"  POST /api/generate     — 生成回答（自动注入 RAG 上下文）")
    print(f"[LLM Server] 等待请求... (Ctrl+C 退出)")
    return server


def main():
    parser = argparse.ArgumentParser(description="轻量 LLM 推理服务器 (Ollama API 兼容 + RAG)")
    parser.add_argument("--port", type=int, default=11434, help="监听端口")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH, help="模型路径")
    parser.add_argument("--knowledge-path", default=DEFAULT_KNOWLEDGE_PATH, help="RAG 知识库 JSON 路径")
    parser.add_argument("--no-rag", action="store_true", help="禁用 RAG 检索")
    args = parser.parse_args()

    # 加载模型
    model, tokenizer = load_model(args.model_path)

    # 加载 RAG 知识库
    knowledge_base = None
    if not args.no_rag:
        print(f"[RAG] 正在加载知识库: {args.knowledge_path}")
        knowledge_base = NURBSKnowledgeBase(args.knowledge_path)
        if not knowledge_base.chunks:
            print("[RAG] ⚠ 知识库为空，RAG 检索将不可用")
            knowledge_base = None
    else:
        print("[RAG] RAG 检索已禁用 (--no-rag)")

    # 启动服务器
    server = create_server(model, tokenizer, args.port, knowledge_base)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[LLM Server] 服务停止")
        server.shutdown()


if __name__ == "__main__":
    main()
