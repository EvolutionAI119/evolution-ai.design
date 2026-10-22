"""RAG 接地演示：检索 sop_knowledge 后交给本地 LLM 回答

对比实验：同一问题
  A) 裸 LLM          —— 无检索
  B) RAG + LLM       —— 先检索真实 SOP 知识，再生成

用本地 bge-small-zh-v1.5（离线）+ Ollama qwen2.5:3b
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
import requests
from sentence_transformers import SentenceTransformer

OLLAMA = "http://127.0.0.1:11435"
MODEL = "qwen2.5:3b"
EMB = "BAAI/bge-small-zh-v1.5"

# ---------------------------------------------------------------- 知识库
# 真实 SOP 知识（来源：algorithm_model/car_modeling/sop_checklist.py 与
#              docs/ 中的 A 表面标准 SOP 13 项检查清单）
KB = [
    "SOP 检查项：基础大面简洁度。阈值 cp<=10x10，spans<=6x6，total<=100。"
    "超标即判定 FAIL。例如 body_upper_skin 曾出现 cp=30x20、spans=27x17、total=600 的超标情况。",
    "G0 连续性：相邻曲面在公共边界处的位置偏差，A 级曲面要求不超过 0.1mm，"
    "超过则出现可见缝隙（rating 记为 Small gap 或更大）。",
    "G1 连续性：相邻曲面在公共边界处的切向量夹角，阈值 1.0 度；"
    "超过 1 度为 G1 不通过，超过 5.0 度（g1_visual_deg）为视觉可见缺陷。",
    "斑马纹检测：将条纹图案投影到曲面上，观察条纹是否连续光顺。"
    "条纹断裂、错位或扭曲表示该处 G1 不连续；条纹间距突变表示曲率变化剧烈。",
    "G2 连续性：曲率连续，用于要求最高的 A 级表面区域（如车身侧围大面）。",
    "SOP 检查清单共 13 项，覆盖 18 个 NURBS 曲面零件。检查方式分自动检查与人工检查两类。",
    "角点插值误差（corner_interpolation_err）应为 0，表示曲面精确通过设计硬点。",
    "曲面到控制点最大偏差（max_surface_to_cp_dev）用于评估控制网格对曲面的控制精度。",
]


def retrieve(question: str, top_k: int = 3):
    """返回 [(相似度, 文档)]"""
    model = _get_model()
    qv = model.encode([question], normalize_embeddings=True)
    dv = model.encode(KB, normalize_embeddings=True)
    sims = (qv @ dv.T)[0]
    order = np.argsort(-sims)[:top_k]
    return [(float(sims[i]), KB[i]) for i in order]


_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(EMB, device="cpu")
    return _MODEL


def ask(question: str, context: str | None = None, timeout: int = 300) -> str:
    if context:
        prompt = (
            "你是汽车 A 级曲面工程专家。请严格依据下面提供的资料回答问题，"
            "不要引入资料之外的猜测。若资料不足，请明确说明。\n\n"
            f"【参考资料】\n{context}\n\n【问题】\n{question}"
        )
    else:
        prompt = f"你是汽车 A 级曲面工程专家。请回答问题：{question}"
    r = requests.post(
        f"{OLLAMA}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json().get("response", "").strip()


def main() -> None:
    question = sys.argv[1] if len(sys.argv) > 1 else "斑马纹检测如何判断曲面光顺性？"
    print(f"问题：{question}\n")

    print("=" * 68)
    print("【检索结果】bge-small-zh-v1.5（本地离线）")
    print("=" * 68)
    hits = retrieve(question, top_k=3)
    for score, doc in hits:
        print(f"  [{score:.3f}] {doc[:70]}...")

    print()
    print("=" * 68)
    print("【A】裸 LLM（无检索）")
    print("=" * 68)
    bare = ask(question)
    print(bare[:700])

    print()
    print("=" * 68)
    print("【B】RAG + LLM（注入检索到的真实 SOP 知识）")
    print("=" * 68)
    context = "\n".join(f"- {d}" for _, d in hits)
    grounded = ask(question, context=context)
    print(grounded[:700])

    print()
    print("=" * 68)
    print("【对比结论】")
    print("=" * 68)
    kw = ["断裂", "投影", "条纹", "G1", "错位", "曲率"]
    a_hit = [k for k in kw if k in bare]
    b_hit = [k for k in kw if k in grounded]
    print(f"  裸 LLM   命中专业关键词: {a_hit or '无'}")
    print(f"  RAG+LLM  命中专业关键词: {b_hit or '无'}")
    print(f"  长度: 裸 {len(bare)} 字 / RAG {len(grounded)} 字")


if __name__ == "__main__":
    main()
