"""
品牌造型知识库查询模块
======================

加载 backend/config/brand_design_knowledge.json（由
scripts/build_brand_knowledge_base.py 生成），提供四类能力：

  1. 信息查询：品牌 / 车型 / 设计语言 / 造型指标
  2. 语义匹配：CLIP 六轴风格分数 → 最匹配品牌与推荐车型
  3. 参数检索：给定汽车参数 → 最相似的真实车型
  4. 参数转换：知识库车型参数 → automotive_parameters.json 兼容 overrides
     （两套参数体系存在定义差异，此处做线性经验映射，见下方说明）

被 Web API、Rhino 插件（经 API）、clip_semantics 共用。
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

# ============================================================
# 路径与加载
# ============================================================

KB_PATH = Path(__file__).resolve().parent.parent / "config" / "brand_design_knowledge.json"

# 六语义轴顺序（与 clip_semantics.SEMANTIC_AXES 的 key 一致）
SEMANTIC_AXES = ["sportiness", "luxury", "futurism", "angularity", "minimalism", "organic"]


@lru_cache(maxsize=1)
def _load() -> dict:
    if not KB_PATH.exists():
        raise FileNotFoundError(
            f"品牌造型知识库不存在: {KB_PATH}，"
            f"请先运行 python scripts/build_brand_knowledge_base.py"
        )
    return json.loads(KB_PATH.read_text(encoding="utf-8"))


def reload_knowledge_base() -> dict:
    """强制重新加载（知识库重建后调用）"""
    _load.cache_clear()
    return _load()


# ============================================================
# 1. 信息查询
# ============================================================

def list_brands() -> list[dict]:
    """品牌概览列表"""
    kb = _load()
    return [{
        "key": b["key"],
        "name": b["name"],
        "zh_name": b["zh_name"],
        "country": b["country"],
        "segment": b["segment"],
        "model_count": b["model_count"],
        "semantic_profile": b["semantic_profile"],
        "styling_metrics": b["styling_metrics"],
        "signature_features": b["signature_features"],
    } for b in kb["brands"]]


def get_brand(brand_key: str) -> Optional[dict]:
    """品牌完整信息（含全部车型）"""
    for b in _load()["brands"]:
        if b["key"] == brand_key:
            return b
    return None


def get_model(brand_key: str, model_key: str) -> Optional[dict]:
    """单车型完整信息"""
    b = get_brand(brand_key)
    if not b:
        return None
    for m in b["models"]:
        if m["key"] == model_key:
            return {"brand_key": b["key"], "brand_name": b["name"],
                    "brand_zh_name": b["zh_name"], **m}
    return None


def all_models() -> list[dict]:
    """拍平全部 19 款车型（附品牌信息）"""
    out = []
    for b in _load()["brands"]:
        for m in b["models"]:
            out.append({
                "brand_key": b["key"], "brand_name": b["name"],
                "brand_zh_name": b["zh_name"], **m,
            })
    return out


# ============================================================
# 2. 语义匹配（CLIP 六轴 → 品牌）
# ============================================================

def _euclidean(a: dict, b: dict) -> float:
    return math.sqrt(sum((a.get(k, 0.5) - b.get(k, 0.5)) ** 2 for k in SEMANTIC_AXES))


def match_brand_by_semantic(axis_scores: dict) -> list[dict]:
    """按六轴风格分数匹配品牌，按距离升序返回

    Args:
        axis_scores: {"sportiness":..,"luxury":..,"futurism":..,
                      "angularity":..,"minimalism":..,"organic":..}（0~1）

    Returns:
        [{"brand_key","zh_name","distance","similarity"}, ...]
        similarity = 1/(1+distance)，0~1
    """
    ranked = []
    for b in _load()["brands"]:
        d = _euclidean(axis_scores, b["semantic_profile"])
        ranked.append({
            "brand_key": b["key"],
            "zh_name": b["zh_name"],
            "name": b["name"],
            "distance": round(d, 4),
            "similarity": round(1.0 / (1.0 + d), 4),
        })
    ranked.sort(key=lambda x: x["distance"])
    return ranked


def recommend_models_by_semantic(axis_scores: dict, top_n: int = 5) -> list[dict]:
    """语义匹配 → 推荐车型

    策略：品牌匹配距离作为先验，车型按
    |品牌距离 + 0.3*(车型姿态与语义的偏差)| 综合排序。
    """
    brand_rank = match_brand_by_semantic(axis_scores)
    brand_dist = {r["brand_key"]: r["distance"] for r in brand_rank}

    # 车型姿态偏差：运动感强 → 低 stance 偏差用 metrics 的 height_width_ratio 衡量
    sport = axis_scores.get("sportiness", 0.5)
    # 期望高宽比：sport=1→约0.60，sport=0→约0.90
    expected_hw = 0.90 - sport * 0.30

    scored = []
    for m in all_models():
        hw_bias = abs(m["metrics"]["height_width_ratio"] - expected_hw)
        score = brand_dist[m["brand_key"]] + 0.3 * hw_bias
        scored.append({
            "brand_key": m["brand_key"],
            "brand_zh_name": m["brand_zh_name"],
            "model_key": m["key"],
            "zh_name": m["zh_name"],
            "body_type": m["body_type"],
            "image_path": m["image_path"],
            "score": round(score, 4),
            "similarity": round(1.0 / (1.0 + score), 4),
        })
    scored.sort(key=lambda x: x["score"])
    return scored[:top_n]


# ============================================================
# 3. 参数相似车型检索
# ============================================================

# 参与相似检索的参数键（排除定义不一致的 roof_height）
_RETRIEVAL_KEYS = [
    "overall_length", "overall_width", "overall_height", "wheelbase",
    "track_width", "ground_clearance", "hood_length", "wheel_diameter",
    "windshield_angle", "rear_window_angle", "rear_slant_angle",
    "overhang_front", "overhang_rear",
]


def _param_bounds() -> dict:
    """全体车型各参数 min/max（用于归一化）"""
    models = all_models()
    bounds = {}
    for k in _RETRIEVAL_KEYS:
        vals = [m["params"][k] for m in models if k in m["params"]]
        bounds[k] = (min(vals), max(vals))
    return bounds


def find_similar_models(params: dict, top_n: int = 5) -> list[dict]:
    """按给定参数找最相似的真实车型（min-max 归一化欧氏距离）

    Args:
        params: {规范键名: 值}，只提供部分键亦可（缺失维度不参与距离，
                但会按已提供维度归一化）
    """
    provided = [k for k in _RETRIEVAL_KEYS if k in params]
    if not provided:
        return []

    bounds = _param_bounds()

    def norm(k, v):
        lo, hi = bounds[k]
        return (v - lo) / (hi - lo) if hi > lo else 0.0

    query_vec = {k: norm(k, params[k]) for k in provided}

    scored = []
    for m in all_models():
        d2 = sum((norm(k, m["params"][k]) - query_vec[k]) ** 2 for k in provided)
        d = math.sqrt(d2 / len(provided))  # 维度归一，结果对维度数不敏感
        scored.append({
            "brand_key": m["brand_key"],
            "brand_zh_name": m["brand_zh_name"],
            "model_key": m["key"],
            "zh_name": m["zh_name"],
            "body_type": m["body_type"],
            "image_path": m["image_path"],
            "distance": round(d, 4),
            "similarity": round(1.0 / (1.0 + d), 4),
        })
    scored.sort(key=lambda x: x["distance"])
    return scored[:top_n]


# ============================================================
# 4. 车型参数 → automotive_parameters.json overrides
# ============================================================
#
# 两套参数体系的定义差异（重要）：
#   - windshield_angle：
#       知识库 25~50 = 风挡倾斜程度（越大越躺，超跑≈50）
#       JSON    55~75 = 越大越直立（90°-该角用于几何，见 car_generator）
#     经验线性映射：知识库26→75（直），知识库50→55（躺）
#   - wheel_diameter：
#       知识库 680~780 = 含胎壁的轮胎整体直径
#       JSON    350~600 = 轮毂直径
#     线性映射：知识库680→350，780→600
#   - roof_height：知识库为车顶纵向长度(300~900)，JSON 为车顶弧高(30~100)，
#     语义不一致，不映射。
# ============================================================

# 参数键 → automotive_parameters.json 的分组
_PARAM_GROUP = {
    "overall_length": "整车尺寸", "overall_width": "整车尺寸",
    "overall_height": "整车尺寸", "wheelbase": "整车尺寸",
    "track_width": "整车尺寸", "ground_clearance": "整车尺寸",
    "hood_length": "车身部件", "wheel_diameter": "车身部件",
    "windshield_angle": "造型角度", "rear_window_angle": "造型角度",
    "rear_slant_angle": "造型角度",
    "overhang_front": "比例参数", "overhang_rear": "比例参数",
}

# 各参数在 JSON 体系中的可接受范围（用于钳制；与 automotive_parameters.json 对齐）
_JSON_BOUNDS = {
    "overall_length": (3000, 6000), "overall_width": (1500, 2200),
    "overall_height": (1200, 2000), "wheelbase": (2000, 4000),
    "track_width": (1400, 1800), "ground_clearance": (100, 300),
    "hood_length": (1000, 1600), "wheel_diameter": (350, 600),
    "windshield_angle": (55, 75), "rear_window_angle": (10, 60),
    "rear_slant_angle": (5, 60),
    # overhang 无显式 min/max，不钳制
}


def _remap_windshield_angle(v: float) -> float:
    """知识库倾斜角(26直~50躺) → JSON 角(75直~55躺)"""
    return 75.0 - (v - 26.0) * (20.0 / 24.0)


def _remap_wheel_diameter(v: float) -> float:
    """知识库轮胎整体直径(680~780) → JSON 轮毂直径(350~600)"""
    return 350.0 + (v - 680.0) * (250.0 / 100.0)


def _clamp(key: str, v: float) -> float:
    bounds = _JSON_BOUNDS.get(key)
    if bounds:
        v = max(bounds[0], min(bounds[1], v))
    return v


def model_to_config_overrides(brand_key: str, model_key: str,
                              scale_factor: float = 1.0) -> dict:
    """将知识库车型参数转换为 automotive_parameters.json 兼容 overrides

    Args:
        brand_key, model_key: 车型定位
        scale_factor: 整体尺寸放缩系数（0.9~1.1），作用于长度/宽度/高度/轴距

    Returns:
        {"整车尺寸": {...}, "车身部件": {...}, ...}
    """
    m = get_model(brand_key, model_key)
    if m is None:
        raise ValueError(f"车型不存在: {brand_key}/{model_key}")

    src = m["params"]
    overrides: dict[str, dict] = {}

    def put(key, val, round_int: bool = True):
        if key in _JSON_BOUNDS:
            val = _clamp(key, val)
        val = int(round(val)) if round_int else round(val, 1)
        overrides.setdefault(_PARAM_GROUP[key], {})[key] = val

    # 尺寸类（支持整体放缩）
    size_keys = [
        "overall_length", "overall_width", "overall_height", "wheelbase",
        "track_width", "ground_clearance", "hood_length",
        "overhang_front", "overhang_rear",
    ]
    for k in size_keys:
        put(k, src[k] * scale_factor)

    # 特殊转换
    put("wheel_diameter", _remap_wheel_diameter(src["wheel_diameter"]))
    put("windshield_angle", _remap_windshield_angle(src["windshield_angle"]),
        round_int=False)

    # 角度（直接映射 + 钳制）
    put("rear_window_angle", src["rear_window_angle"], round_int=False)
    put("rear_slant_angle", src["rear_slant_angle"], round_int=False)

    return overrides


# ============================================================
# CLI 自检
# ============================================================

if __name__ == "__main__":
    print(f"知识库: {KB_PATH}")
    kb = _load()
    print(f"版本 {kb['version']}：{kb['brand_count']} 品牌 / {kb['model_count']} 车型\n")

    print("品牌语义画像与姿态指数：")
    for b in list_brands():
        sp = b["semantic_profile"]
        print(f"  {b['zh_name']:4s} 运动{sp['sportiness']:.2f} 豪华{sp['luxury']:.2f} "
              f"姿态{b['styling_metrics']['stance_index']:.2f}")

    print("\n语义匹配测试（假设纹样提取：运动0.9/豪华0.7/科技0.6）：")
    test_scores = {"sportiness": 0.9, "luxury": 0.7, "futurism": 0.6,
                   "angularity": 0.6, "minimalism": 0.4, "organic": 0.4}
    for r in match_brand_by_semantic(test_scores)[:3]:
        print(f"  {r['zh_name']} distance={r['distance']} sim={r['similarity']}")

    print("\n参数映射示例（porsche/911 → automotive overrides）：")
    ov = model_to_config_overrides("porsche", "911")
    for g, items in ov.items():
        print(f"  [{g}] {items}")
