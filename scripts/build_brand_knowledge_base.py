#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品牌造型知识库构建工具
======================

从前端 carPresets.js（19 款车型的唯一数据源）提取参数，
合并手工维护的品牌设计语言元数据（领域知识），
计算车型级/品牌级造型量化指标，
输出 backend/config/brand_design_knowledge.json。

用法：
    python scripts/build_brand_knowledge_base.py
    python scripts/build_brand_knowledge_base.py --output 自定义路径.json

知识库用途：
  - Web 后端 /api/v1/brand-knowledge 查询接口
  - Rhino 插件按品牌 DNA 快速生成车型
  - CLIP 语义引擎：纹样风格 → 匹配品牌 → 参数生成
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

# ============================================================
# 路径
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
PRESETS_JS = ROOT / "src" / "config" / "carPresets.js"
DEFAULT_OUTPUT = ROOT / "backend" / "config" / "brand_design_knowledge.json"

# ============================================================
# 参数 Schema：carPresets.js 键名 → 后端规范键名 + 中文名 + 单位
# ============================================================

PARAM_SCHEMA = [
    # (JS键名, 规范键名, 中文名, 单位)
    ("overall_length",  "overall_length",   "整车长度",   "mm"),
    ("overall_width",   "overall_width",    "整车宽度",   "mm"),
    ("overall_height",  "overall_height",   "整车高度",   "mm"),
    ("wheel_base",      "wheelbase",        "轴距",       "mm"),
    ("track_width",     "track_width",      "轮距",       "mm"),
    ("ground_clearance","ground_clearance", "离地间隙",   "mm"),
    ("hood_length",     "hood_length",      "发动机盖长度","mm"),
    ("roof_height",     "roof_height",      "车顶纵向高度","mm"),
    ("wheel_diameter",  "wheel_diameter",   "轮胎直径",   "mm"),
    ("windshield_angle","windshield_angle", "前风挡角度", "deg"),
    ("rear_window_angle","rear_window_angle","后风挡角度","deg"),
    ("rear_slant_angle","rear_slant_angle", "后倾角度",   "deg"),
    ("front_overhang",  "overhang_front",   "前悬长度",   "mm"),
    ("rear_overhang",   "overhang_rear",    "后悬长度",   "mm"),
]

JS_TO_CANON = {js: canon for js, canon, _, _ in PARAM_SCHEMA}
CANON_TO_ZH = {canon: zh for _, canon, zh, _ in PARAM_SCHEMA}
CANON_TO_UNIT = {canon: unit for _, canon, _, unit in PARAM_SCHEMA}

# ============================================================
# 品牌设计语言元数据（领域知识，手工维护）
# semantic_profile 六轴 0~1，与 clip_semantics.SEMANTIC_AXES 对应
# ============================================================

BRAND_METADATA = {
    "rolls-royce": {
        "zh_name": "劳斯莱斯",
        "country": "英国",
        "founded": 1906,
        "segment": "超豪华",
        "design_language": (
            "以帕特农神庙式进气格栅为核心图腾，配合欢庆女神立标、对开式马车车门、"
            "修长发动机盖与威严直立的高车顶线，营造庄重典雅、从容不迫的气场；"
            "追求永恒经典而非潮流，比例舒展、姿态沉稳。"
        ),
        "signature_features": [
            "帕特农神庙格栅", "欢庆女神立标", "马车式对开门",
            "长发动机盖", "高车顶线", "庄重直立姿态",
        ],
        "semantic_profile": {
            "sportiness": 0.20, "luxury": 0.96, "futurism": 0.38,
            "angularity": 0.50, "minimalism": 0.30, "organic": 0.32,
        },
    },
    "bentley": {
        "zh_name": "宾利",
        "country": "英国",
        "founded": 1919,
        "segment": "超豪华运动",
        "design_language": (
            "大尺寸矩阵式进气格栅与四眼圆灯构成经典前脸，长发动机盖下是力量与优雅的融合；"
            "饱满有力的英式肌肉曲面配合宽大车身，既有豪华GT的从容，又有深厚的运动底蕴；"
            "双翼B字标象征速度与精工。"
        ),
        "signature_features": [
            "矩阵格栅", "四眼圆灯", "长发动机盖",
            "双翼B标", "饱满肌肉曲面", "宽体姿态",
        ],
        "semantic_profile": {
            "sportiness": 0.55, "luxury": 0.90, "futurism": 0.45,
            "angularity": 0.60, "minimalism": 0.35, "organic": 0.42,
        },
    },
    "bugatti": {
        "zh_name": "布加迪",
        "country": "法国",
        "founded": 1909,
        "segment": "终极超跑",
        "design_language": (
            "马蹄形前格栅致敬品牌百年传承，侧面标志性C形线条环绕座舱；"
            "极致低矮的宽体姿态与中置引擎布局，配合流线型空气动力学车身，"
            "将机械性能推至物理极限，呈现工程艺术般的速度美学。"
        ),
        "signature_features": [
            "马蹄形格栅", "C形侧线", "极致低矮宽体",
            "中置引擎", "流线型车身", "外露机械美学",
        ],
        "semantic_profile": {
            "sportiness": 0.96, "luxury": 0.82, "futurism": 0.72,
            "angularity": 0.68, "minimalism": 0.28, "organic": 0.30,
        },
    },
    "porsche": {
        "zh_name": "保时捷",
        "country": "德国",
        "founded": 1931,
        "segment": "豪华运动",
        "design_language": (
            "蛙眼大灯与经典溜背曲线构成最具辨识度的侧影，后置/中置引擎布局决定了独特比例；"
            "宽体姿态搭配隆起轮拱，设计哲学是'永恒设计的渐进进化'——"
            "每一代都在传承中精准优化，功能与形式高度统一。"
        ),
        "signature_features": [
            "蛙眼大灯", "溜背曲线", "宽体姿态",
            "隆起轮拱", "后置引擎", "经典比例进化",
        ],
        "semantic_profile": {
            "sportiness": 0.90, "luxury": 0.70, "futurism": 0.65,
            "angularity": 0.55, "minimalism": 0.50, "organic": 0.45,
        },
    },
    "ferrari": {
        "zh_name": "法拉利",
        "country": "意大利",
        "founded": 1939,
        "segment": "超级跑车",
        "design_language": (
            "以激情四溢的曲面和空气动力学雕刻塑造攻击性姿态，长车头短车尾的经典后驱比例；"
            "意式美学让每个曲面都兼具功能与性感，线条从车头跃动至尾部，"
            "跃马标志象征赛道基因与纯粹驾驶激情。"
        ),
        "signature_features": [
            "激情曲面", "空气动力学雕刻", "长车头短车尾",
            "攻击性姿态", "跃马标志", "意式美学",
        ],
        "semantic_profile": {
            "sportiness": 0.93, "luxury": 0.75, "futurism": 0.60,
            "angularity": 0.70, "minimalism": 0.40, "organic": 0.52,
        },
    },
}

# ============================================================
# 车型元数据：中文名 + 车身类型
# ============================================================

MODEL_METADATA = {
    ("rolls-royce", "phantom"):       ("幻影", "豪华轿车"),
    ("rolls-royce", "ghost"):         ("古思特", "豪华轿车"),
    ("rolls-royce", "cullinan"):      ("库里南", "豪华SUV"),
    ("rolls-royce", "wraith"):        ("魅影", "豪华轿跑"),
    ("bentley", "continental-gt"):    ("欧陆GT", "豪华GT轿跑"),
    ("bentley", "continental-gtc"):   ("欧陆GTC", "敞篷GT"),
    ("bentley", "flying-spur"):       ("飞驰", "豪华轿车"),
    ("bentley", "bentayga"):          ("添越", "豪华SUV"),
    ("bugatti", "chiron"):            ("凯龙", "终极超跑"),
    ("bugatti", "veyron"):            ("威龙", "终极超跑"),
    ("bugatti", "divo"):              ("迪沃", "限量超跑"),
    ("porsche", "911"):               ("911", "运动跑车"),
    ("porsche", "taycan"):            ("Taycan", "电动轿跑"),
    ("porsche", "panamera"):          ("Panamera", "豪华轿跑"),
    ("porsche", "cayenne"):           ("Cayenne", "豪华SUV"),
    ("porsche", "macan"):             ("Macan", "中型SUV"),
    ("ferrari", "sf90"):              ("SF90 Stradale", "插混超跑"),
    ("ferrari", "f8-tributo"):        ("F8 Tributo", "中置超跑"),
    ("ferrari", "roma"):              ("Roma", "GT轿跑"),
}

# ============================================================
# 从 carPresets.js 提取
# ============================================================

_BRAND_RE = re.compile(
    r"\{\s*key:\s*'([^']+)',\s*name:\s*'([^']+)',\s*color:",
)
_MODEL_RE = re.compile(
    r"\{\s*key:\s*'([^']+)',\s*name:\s*'([^']+)',\s*params:\s*\{([^}]+)\}"
)
_PAIR_RE = re.compile(r"(\w+)\s*:\s*(-?\d+(?:\.\d+)?)")


def extract_brands_from_js(js_text: str) -> list[dict]:
    """解析 carPresets.js，返回 [{key, en_name, models:[{key, name, params:{canon:val}}]}]

    做法：按品牌块位置切分，在每段内提取车型，保证车型归属正确。
    """
    # 找所有品牌块的位置
    brand_matches = list(_BRAND_RE.finditer(js_text))
    if not brand_matches:
        raise RuntimeError("carPresets.js 中未找到品牌定义")

    brands = []
    for i, bm in enumerate(brand_matches):
        brand_key = bm.group(1)
        brand_en_name = bm.group(2)
        seg_start = bm.start()
        seg_end = brand_matches[i + 1].start() if i + 1 < len(brand_matches) else len(js_text)
        segment = js_text[seg_start:seg_end]

        models = []
        for mm in _MODEL_RE.finditer(segment):
            model_key = mm.group(1)
            model_en_name = mm.group(2)
            params_body = mm.group(3)
            raw_params = dict(_PAIR_RE.findall(params_body))

            # 转换为规范键名 + 数值
            params = {}
            for js_key, val_str in raw_params.items():
                canon = JS_TO_CANON.get(js_key)
                if canon is None:
                    continue
                val = float(val_str)
                params[canon] = int(val) if val == int(val) else val
            models.append({
                "key": model_key,
                "name": model_en_name,
                "params": params,
            })

        brands.append({
            "key": brand_key,
            "name": brand_en_name,
            "models": models,
        })
    return brands


# ============================================================
# 造型量化指标
# ============================================================

def compute_model_metrics(p: dict) -> dict:
    """计算单车型衍生造型指标（全部为无量纲比率，便于跨品牌比较）"""
    L, W, H = p["overall_length"], p["overall_width"], p["overall_height"]
    wb = p["wheelbase"]
    return {
        # 高宽比：越小越低趴（超跑≈0.6，SUV≈0.9）
        "height_width_ratio": round(H / W, 4),
        # 长宽比：越大越修长（豪华车特征）
        "length_width_ratio": round(L / W, 4),
        # 轴距占车长比例：越大车内空间越舒展
        "wheelbase_ratio": round(wb / L, 4),
        # 前后悬比：<1 前悬短（运动），>1 前悬长（豪华）
        "overhang_ratio": round(p["overhang_front"] / p["overhang_rear"], 4),
        # 轮胎直径/车高：越大轮子视觉占比越强（运动）
        "wheel_height_ratio": round(p["wheel_diameter"] / H, 4),
        # 离地间隙率
        "clearance_ratio": round(p["ground_clearance"] / H, 4),
        # 发动机盖占车长比例：越大越偏后驱/超跑姿态
        "hood_length_ratio": round(p["hood_length"] / L, 4),
        # 姿态指数 W/H：越大越低趴宽体（超跑≈1.65，豪华车≈1.2，SUV≈1.1）
        "stance_index": round(W / H, 4),
    }


def aggregate_brand(models: list[dict]) -> tuple[dict, dict]:
    """品牌级聚合：参数范围(mean/min/max) + 造型指标均值"""
    param_keys = [canon for _, canon, _, _ in PARAM_SCHEMA]

    param_ranges = {}
    for canon in param_keys:
        vals = [m["params"][canon] for m in models if canon in m["params"]]
        if not vals:
            continue
        param_ranges[canon] = {
            "mean": round(statistics.mean(vals), 1),
            "min": min(vals),
            "max": max(vals),
        }

    metric_keys = list(models[0]["metrics"].keys())
    metric_means = {}
    for mk in metric_keys:
        vals = [m["metrics"][mk] for m in models if mk in m["metrics"]]
        metric_means[mk] = round(statistics.mean(vals), 4)

    return param_ranges, metric_means


# ============================================================
# 组装知识库
# ============================================================

def build_knowledge_base() -> dict:
    js_text = PRESETS_JS.read_text(encoding="utf-8")
    raw_brands = extract_brands_from_js(js_text)

    total_models = sum(len(b["models"]) for b in raw_brands)

    brand_entries = []
    for rb in raw_brands:
        bkey = rb["key"]
        meta = BRAND_METADATA.get(bkey)
        if meta is None:
            raise RuntimeError(f"缺少品牌元数据: {bkey}")

        model_entries = []
        for rm in rb["models"]:
            mkey = rm["key"]
            zh_name, body_type = MODEL_METADATA.get((bkey, mkey), (mkey, ""))
            metrics = compute_model_metrics(rm["params"])
            model_entries.append({
                "key": mkey,
                "name": rm["name"],
                "zh_name": zh_name,
                "body_type": body_type,
                "params": rm["params"],
                "metrics": metrics,
                "image_path": f"/brands/{bkey}/{mkey}.jpg",
            })

        param_ranges, metric_means = aggregate_brand(model_entries)

        brand_entries.append({
            "key": bkey,
            "name": rb["name"],
            "zh_name": meta["zh_name"],
            "country": meta["country"],
            "founded": meta["founded"],
            "segment": meta["segment"],
            "design_language": meta["design_language"],
            "signature_features": meta["signature_features"],
            "semantic_profile": meta["semantic_profile"],
            "model_count": len(model_entries),
            "param_ranges": param_ranges,
            "styling_metrics": metric_means,
            "models": model_entries,
        })

    return {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "description": "EVOLUTION-AI 品牌造型知识库：5 品牌 19 款车型的参数、造型指标与设计语言",
        "param_schema": [
            {"key": canon, "name": zh, "unit": unit}
            for _, canon, zh, unit in PARAM_SCHEMA
        ],
        "metric_schema": [
            {"key": "height_width_ratio", "name": "高宽比", "desc": "越小越低趴"},
            {"key": "length_width_ratio", "name": "长宽比", "desc": "越大越修长"},
            {"key": "wheelbase_ratio", "name": "轴距占比", "desc": "轴距/车长"},
            {"key": "overhang_ratio", "name": "前后悬比", "desc": "<1偏运动，>1偏豪华"},
            {"key": "wheel_height_ratio", "name": "轮径车高比", "desc": "越大轮子越醒目"},
            {"key": "clearance_ratio", "name": "离地间隙率", "desc": "离地间隙/车高"},
            {"key": "hood_length_ratio", "name": "引擎盖占比", "desc": "越大越偏超跑姿态"},
            {"key": "stance_index", "name": "姿态指数", "desc": "宽/高，越大越低趴宽体"},
        ],
        "brand_count": len(brand_entries),
        "model_count": total_models,
        "brands": brand_entries,
    }


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="构建品牌造型知识库")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"输出路径（默认 {DEFAULT_OUTPUT}）")
    args = parser.parse_args()

    if not PRESETS_JS.exists():
        raise SystemExit(f"找不到车型数据源: {PRESETS_JS}")

    kb = build_knowledge_base()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(kb, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    print(f"✅ 知识库已生成: {args.output}")
    print(f"   品牌数: {kb['brand_count']}，车型数: {kb['model_count']}")
    for b in kb["brands"]:
        print(f"   - {b['zh_name']}({b['name']}): {b['model_count']} 款，"
              f"姿态指数均值 {b['styling_metrics']['stance_index']}")


if __name__ == "__main__":
    main()
