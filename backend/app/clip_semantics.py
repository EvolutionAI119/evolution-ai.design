"""
EVOLUTION-AI CLIP 语义特征提取器
=================================

用 CLIP 视觉-语言模型从设计纹样图中提取"风格语义"（运动感、豪华感、科技感等），
并映射为汽车参数覆盖，实现"看懂纹样的设计语言，自动调出对应的车身比例"。

架构：
  - 懒加载：首次调用时才加载 CLIP 权重（openai/clip-vit-base-patch32，约 605MB）
  - 优雅降级：torch/transformers/权重任一不可用时返回 available=False，
    上层自动回退到纯几何特征（texture_analyzer）
  - 双端复用：Web API 与 Rhino 插件共用本模块

风格轴（中文标签 + 英文 CLIP 提示词）：
  sportiness   运动感 ←→ 优雅感
  luxury       豪华感 ←→ 亲民感
  futurism     科技感 ←→ 复古感
  angularity   硬朗感 ←→ 圆润感
  minimalism   简约感 ←→ 繁复感
  organic      自然感 ←→ 几何感

依赖：torch, transformers（权重自动下载到 HF 缓存）
    pip install torch transformers
"""
from __future__ import annotations

import logging
import math
import os
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_ID = "openai/clip-vit-base-patch32"


def _model_cached(model_id: str) -> bool:
    """检查模型是否已在本地 HF 缓存中（避免联网版本校验超时）

    兼容 .bin 与 .safetensors 两种权重格式（transformers 4.57 优先用 safetensors）。
    """
    safe = model_id.replace("/", "--")
    hf_home = os.environ.get("HF_HOME") or str(Path.home() / ".cache" / "huggingface")
    cache_dir = Path(hf_home) / "hub" / f"models--{safe}"
    if not cache_dir.exists():
        return False
    has_bin = any(cache_dir.glob("snapshots/*/*.bin"))
    has_safetensors = any(cache_dir.glob("snapshots/*/*.safetensors"))
    return has_bin or has_safetensors


# 环境设置必须在 import transformers 之前（huggingface_hub 在导入期读取这些常量）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")  # 国内镜像回退
if _model_cached(MODEL_ID):
    # 权重已在本地：离线加载，跳过 HEAD 版本校验（否则在直连超时环境每次要多等 1~2 分钟）
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    logger.info(f"CLIP 权重已在本地缓存，使用离线模式加载 {MODEL_ID}")

# ============================================================
# 依赖检测（导入期，不加载权重）
# ============================================================

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# 全局单例（懒加载，线程安全）
_model = None
_processor = None
_load_lock = threading.Lock()
_load_error: Optional[str] = None

# CLIP 风格轴的文本嵌入缓存（加载模型后编码一次）
_text_emb_cache: Optional[dict] = None


def is_available() -> bool:
    """CLIP 是否可用（依赖齐全；权重在首次调用时下载/加载）"""
    return TORCH_AVAILABLE


def get_load_error() -> Optional[str]:
    """返回最近一次模型加载失败的原因（用于诊断）"""
    return _load_error


# ============================================================
# 风格轴定义：中文标签 + 英文 CLIP 提示词
# ============================================================

# 每个轴 = (中文标签, 正极提示词列表, 负极提示词列表)
# 分数 = sig(cos(img, pos) - cos(img, neg))，越接近 1 越偏正极风格
# 提示词原则：CLIP 对"具象视觉描述"远比对抽象形容词敏感，故全部用具体图案描述
SEMANTIC_AXES: dict[str, tuple[str, list[str], list[str]]] = {
    "sportiness": (
        "运动感",
        [
            "racing stripes and speed lines pattern",
            "dynamic diagonal stripes suggesting speed and motion",
            "checkered racing flag pattern",
            "sharp lightning bolt shapes on dark background",
            "aggressive sports car livery graphics",
        ],
        [
            "gentle floral pattern with soft petals",
            "soft pastel polka dots pattern",
            "delicate lace fabric pattern",
            "calm watercolor wash gradient",
            "quiet soft clouds pattern",
        ],
    ),
    "luxury": (
        "豪华感",
        [
            "gold ornament pattern on dark background",
            "baroque damask pattern in gold",
            "elegant gold filigree ornament",
            "royal velvet pattern with gold embroidery",
            "marble texture with golden veins",
        ],
        [
            "plain cardboard texture",
            "simple gray concrete wall texture",
            "cheap plastic pattern",
            "basic graph paper grid",
            "worn burlap sack texture",
        ],
    ),
    "futurism": (
        "科技感",
        [
            "futuristic circuit board pattern",
            "holographic tech interface pattern",
            "sci-fi HUD elements glowing on dark background",
            "neon cyberpunk grid with glowing lines",
            "digital pixel gradient pattern",
        ],
        [
            "ancient tribal ornament pattern",
            "victorian lace pattern",
            "vintage floral wallpaper pattern",
            "classical greek meander border pattern",
            "hand-drawn old parchment map pattern",
        ],
    ),
    "angularity": (
        "硬朗感",
        [
            "pattern of sharp triangles and jagged edges",
            "angular zigzag chevron pattern",
            "sharp broken glass shards pattern",
            "spiky thorn shapes pattern",
            "hard-edged angular metal plates pattern",
        ],
        [
            "pattern of smooth circles and bubbles",
            "soft rounded pebble stones pattern",
            "flowing smooth wave curves pattern",
            "round polka dots pattern",
            "fluffy soft cloud shapes pattern",
        ],
    ),
    "minimalism": (
        "简约感",
        [
            "minimalist pattern with a single thin line",
            "sparse pattern with mostly empty white space",
            "japanese zen minimal pattern",
            "plain background with one small geometric shape",
            "simple two-color minimalist design",
        ],
        [
            "extremely dense ornate pattern",
            "intricate persian carpet pattern",
            "busy mosaic with hundreds of tiny tiles",
            "maximalist baroque ornament covering everything",
            "cluttered kaleidoscope pattern with many details",
        ],
    ),
    "organic": (
        "自然感",
        [
            "pattern of leaves and vines",
            "flowing plant patterns with curving stems",
            "water ripples and wave patterns",
            "wood grain texture pattern",
            "seashell spiral patterns",
        ],
        [
            "pattern of perfect geometric squares and grids",
            "circuit board electronic pattern",
            "pattern of sharp repeated triangles",
            "brick wall pattern",
            "machine-made repeating tile pattern",
        ],
    ),
}

# CLIP 文本模板（具象提示词下用轻量模板，避免语义稀释）
_TEXT_TEMPLATES = [
    "{}",
    "a texture pattern, {}",
]


# ============================================================
# 语义特征数据结构
# ============================================================

@dataclass
class SemanticFeatures:
    """纹样图的 CLIP 语义特征：每轴 0~1（0.5=中性，>0.5 偏正极风格）"""
    # 风格轴分数
    sportiness: float = 0.5   # 运动感(1) ←→ 优雅感(0)
    luxury: float = 0.5       # 豪华感(1) ←→ 亲民感(0)
    futurism: float = 0.5     # 科技感(1) ←→ 复古感(0)
    angularity: float = 0.5   # 硬朗感(1) ←→ 圆润感(0)
    minimalism: float = 0.5   # 简约感(1) ←→ 繁复感(0)
    organic: float = 0.5      # 自然感(1) ←→ 几何感(0)

    # 语义显著度：各轴 |score-0.5|*2 的均值，0~1（越高说明纹样风格特征越鲜明）
    confidence: float = 0.0

    # 风格关键词（按显著度排序，供 UI 展示）：[("运动感", 0.83), ...]
    style_keywords: list = field(default_factory=list)

    # 模型信息
    model_id: str = MODEL_ID

    def axis_dict(self) -> dict:
        """返回 {中文标签: 分数} """
        out = {}
        for key, (label, _, _) in SEMANTIC_AXES.items():
            out[label] = getattr(self, key)
        return out


# ============================================================
# 模型加载与单例
# ============================================================

def _load_model():
    """懒加载 CLIP 模型与处理器（线程安全）"""
    global _model, _processor, _load_error
    if _model is not None:
        return True
    if not TORCH_AVAILABLE:
        _load_error = "torch/transformers 未安装"
        return False
    with _load_lock:
        if _model is not None:
            return True
        try:
            logger.info(f"正在加载 CLIP 模型: {MODEL_ID}（首次运行需下载约 605MB）")
            _processor = CLIPProcessor.from_pretrained(MODEL_ID, use_fast=True)
            _model = CLIPModel.from_pretrained(MODEL_ID)
            _model.eval()
            logger.info("CLIP 模型加载完成")
            return True
        except Exception as e:
            _load_error = str(e)
            logger.warning(f"CLIP 模型加载失败: {e}")
            return False


def _encode_texts(texts: list[str]):
    """批量编码文本 → 归一化嵌入 (N, D) tensor"""
    inputs = _processor(text=texts, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        feats = _model.get_text_features(**inputs)
    return torch.nn.functional.normalize(feats, dim=-1)


def _get_text_embeddings() -> dict:
    """编码全部风格轴的正负极提示词，返回 {axis: (pos_emb, neg_emb)}（缓存）"""
    global _text_emb_cache
    if _text_emb_cache is not None:
        return _text_emb_cache
    cache = {}
    for axis, (_, pos_prompts, neg_prompts) in SEMANTIC_AXES.items():
        # 模板展开
        pos_texts = [t.format(p) for p in pos_prompts for t in _TEXT_TEMPLATES]
        neg_texts = [t.format(n) for n in neg_prompts for t in _TEXT_TEMPLATES]
        pos_emb = _encode_texts(pos_texts).mean(dim=0)
        neg_emb = _encode_texts(neg_texts).mean(dim=0)
        pos_emb = torch.nn.functional.normalize(pos_emb, dim=-1)
        neg_emb = torch.nn.functional.normalize(neg_emb, dim=-1)
        cache[axis] = (pos_emb, neg_emb)
    _text_emb_cache = cache
    return cache


# ============================================================
# 图像语义提取
# ============================================================

def extract_semantic_features(image_source) -> Optional[SemanticFeatures]:
    """从纹样图提取 CLIP 语义特征

    Args:
        image_source: PIL.Image / 图片路径 / bytes

    Returns:
        SemanticFeatures；模型不可用时返回 None
    """
    if not _load_model():
        return None

    from PIL import Image
    import io

    if isinstance(image_source, (str, Path)):
        img = Image.open(image_source)
    elif isinstance(image_source, bytes):
        img = Image.open(io.BytesIO(image_source))
    elif isinstance(image_source, Image.Image):
        img = image_source
    else:
        raise TypeError(f"不支持的图像输入类型: {type(image_source)}")

    img = img.convert("RGB")

    # 图像嵌入
    inputs = _processor(images=img, return_tensors="pt")
    with torch.no_grad():
        img_emb = _model.get_image_features(pixel_values=inputs["pixel_values"])
    img_emb = torch.nn.functional.normalize(img_emb, dim=-1)[0]  # (D,)

    # 各轴打分
    text_embs = _get_text_embeddings()
    sem = SemanticFeatures()
    raw_scores = {}
    for axis, (pos_emb, neg_emb) in text_embs.items():
        cos_pos = float(torch.dot(img_emb, pos_emb))
        cos_neg = float(torch.dot(img_emb, neg_emb))
        # 差值 → sigmoid 归一化到 0~1（温度系数 30：CLIP 余弦差通常只有 0.01~0.1，需放大区分度）
        diff = (cos_pos - cos_neg) * 30.0
        score = 1.0 / (1.0 + math.exp(-diff))
        setattr(sem, axis, round(score, 4))
        raw_scores[axis] = score

    # 语义显著度：各轴偏离 0.5 的平均幅度
    deviations = [abs(s - 0.5) * 2 for s in raw_scores.values()]
    sem.confidence = round(sum(deviations) / len(deviations), 4)

    # 风格关键词：按显著度排序
    kws = []
    for axis, (label, _, _) in SEMANTIC_AXES.items():
        s = raw_scores[axis]
        # 偏正极 → 正极标签；偏负极 → 负极标签
        if s >= 0.5:
            kws.append((label, round(s, 3)))
        else:
            neg_label = _negative_label(axis)
            kws.append((neg_label, round(1.0 - s, 3)))
    kws.sort(key=lambda x: -x[1])
    sem.style_keywords = kws

    return sem


def _negative_label(axis: str) -> str:
    """返回轴的负极中文标签"""
    neg_labels = {
        "sportiness": "优雅感", "luxury": "亲民感", "futurism": "复古感",
        "angularity": "圆润感", "minimalism": "繁复感", "organic": "几何感",
    }
    return neg_labels.get(axis, axis)


# ============================================================
# 语义 → 参数映射
# ============================================================

def semantic_to_overrides(
    sem: SemanticFeatures,
    target_region: str = "整车",
    intensity: float = 0.5,
) -> dict:
    """将 CLIP 语义分数映射为汽车参数覆盖

    映射哲学（与几何特征映射互补）：
      - 几何特征 = 纹样的"形状证据"（直接、精确）
      - 语义特征 = 纹样的"设计语言意图"（间接、整体）
      - 语义映射强度约为几何映射的 60%，避免喧宾夺主

    Args:
        sem: CLIP 语义特征
        target_region: 目标部位（复用 texture_analyzer.TARGET_REGIONS）
        intensity: 调参强度 0~1

    Returns:
        overrides: {group: {key: value}}
    """
    try:
        from .texture_analyzer import TARGET_REGIONS, _load_params_def
    except ImportError:
        from texture_analyzer import TARGET_REGIONS, _load_params_def

    if target_region not in TARGET_REGIONS:
        raise ValueError(f"未知目标部位: {target_region}")

    intensity = max(0.0, min(1.0, intensity))
    params_def = _load_params_def()
    region = TARGET_REGIONS[target_region]

    overrides = {}
    for group, key in region["params"]:
        if group not in params_def or key not in params_def[group]:
            continue
        meta = params_def[group][key]
        if "min_value" not in meta or "max_value" not in meta:
            continue

        cur, lo, hi = meta["value"], meta["min_value"], meta["max_value"]
        rng = hi - lo
        if rng <= 0:
            continue

        # 每个参数最多受 2 个语义轴驱动，系数为轴对该参数的方向权重
        # 权重 > 0：轴分数越高 → 参数越大；< 0：轴分数越高 → 参数越小
        drivers = _param_semantic_drivers(key)
        if not drivers:
            continue

        # 加权求和：sum(weight * (score - 0.5) * 2)，结果 -1~1
        drive = 0.0
        for axis, w in drivers:
            drive += w * (getattr(sem, axis) - 0.5) * 2.0
        drive = max(-1.0, min(1.0, drive))

        # 语义映射强度 0.18（约为几何映射 0.25~0.4 的 60%）
        new_val = cur + drive * rng * 0.18 * intensity

        new_val = max(lo, min(hi, new_val))
        if meta.get("type") in ("length", "width", "height", "distance", "diameter", "radius"):
            new_val = round(new_val)
        else:
            new_val = round(new_val, 1)

        overrides.setdefault(group, {})[key] = new_val

    return overrides


def _param_semantic_drivers(key: str) -> list[tuple[str, float]]:
    """定义每个参数受哪些语义轴驱动及方向权重

    设计依据（汽车造型语义学）：
      - 运动感 → 车更低更宽、风挡更斜、轮子更大
      - 豪华感 → 车更长更宽、姿态更沉稳（高度略降）
      - 科技感 → 风挡/后窗更斜、后倾更大、悬垂收紧
      - 硬朗感 → 引擎盖角度更翘、轮拱更紧、格栅更大
      - 简约感 → 格栅/灯具更收敛、部件更精致小巧
      - 自然感 → 轮拱更圆润饱满、曲面更柔和
    """
    D = {
        # ===== 整车尺寸 =====
        "overall_length":   [("luxury", 0.8), ("sportiness", 0.4)],
        "overall_width":    [("sportiness", 0.8), ("luxury", 0.5)],
        "overall_height":   [("sportiness", -0.9), ("luxury", -0.3)],
        "wheelbase":        [("luxury", 0.8)],
        "track_width":      [("sportiness", 0.7)],
        # ===== 造型角度 =====
        "hood_angle":       [("angularity", 0.6), ("sportiness", -0.4)],
        "windshield_angle": [("sportiness", 0.7), ("futurism", 0.5)],
        "rear_window_angle": [("futurism", 0.6), ("sportiness", 0.4)],
        "rear_slant_angle": [("futurism", 0.7), ("sportiness", 0.3)],
        # ===== 车身部件 =====
        "wheel_arch_radius": [("organic", 0.7), ("angularity", -0.5)],
        "wheel_diameter":   [("sportiness", 0.7), ("angularity", 0.3)],
        "wheel_width":      [("sportiness", 0.5)],
        "grille_width":     [("angularity", 0.6), ("luxury", 0.3)],
        "grille_height":    [("angularity", 0.5), ("minimalism", -0.4)],
        "headlight_width":  [("minimalism", -0.5), ("angularity", 0.3)],
        "headlight_height": [("minimalism", -0.5)],
        "taillight_width":  [("minimalism", -0.4), ("futurism", 0.3)],
        "taillight_height": [("minimalism", -0.4)],
        "hood_length":      [("luxury", 0.5), ("sportiness", 0.3)],
        "hood_width":       [("sportiness", 0.5)],
        "hood_height":      [("organic", 0.4)],
        "roof_width":       [("luxury", 0.4)],
        "roof_height":      [("sportiness", -0.6)],
        "windshield_width": [("luxury", 0.4)],
        "windshield_height": [("sportiness", -0.4)],
        "rear_window_width": [("luxury", 0.3)],
        "rear_window_height": [("futurism", -0.3)],
        "trunk_length":     [("luxury", 0.5)],
        "trunk_width":      [("luxury", 0.4)],
        # ===== 比例参数 =====
        "overhang_front":   [("angularity", 0.4), ("luxury", 0.3)],
        "overhang_rear":    [("futurism", -0.4), ("luxury", 0.3)],
    }
    return D.get(key, [])


def _semantic_drive_strength(key: str, sem: SemanticFeatures) -> float:
    """计算语义特征对某参数的综合驱动强度（-1~1，绝对值越大驱动越强）"""
    drivers = _param_semantic_drivers(key)
    drive = 0.0
    for axis, w in drivers:
        drive += w * (getattr(sem, axis) - 0.5) * 2.0
    return max(-1.0, min(1.0, drive))


# ============================================================
# 融合分析入口（几何 + 语义）
# ============================================================

def analyze_with_semantics(
    image_source,
    target_region: str = "整车",
    intensity: float = 0.5,
    semantic_weight: float = 0.4,
) -> dict:
    """几何特征 + CLIP 语义特征融合分析

    融合策略：
      - geometric_overrides 由 texture_analyzer 的形状特征生成
      - semantic_overrides 由 CLIP 风格分数生成
      - 最终 = geo * (1-w) + sem * w（逐参数加权融合）

    Args:
        image_source: 图片路径 / bytes / PIL.Image
        target_region: 目标部位
        intensity: 调参强度 0~1
        semantic_weight: 语义权重 0~1（默认 0.4；0=纯几何，1=纯语义）

    Returns:
        {
          "features": {...},          # 几何特征（7 维）
          "semantic": {...} | None,   # 语义特征（可用时）
          "target_region": ...,
          "overrides": {...},         # 融合后的参数覆盖
          "param_count": N,
        }
    """
    try:
        from .texture_analyzer import analyze_texture
    except ImportError:
        # 顶层模块加载（Rhino 插件 / 测试脚本）时无包上下文
        from texture_analyzer import analyze_texture

    # 1. 几何分析（一定可用）
    geo_result = analyze_texture(image_source, target_region, intensity)

    # 2. 语义分析（CLIP 可用时）
    sem_features = extract_semantic_features(image_source) if TORCH_AVAILABLE else None

    if sem_features is None:
        return {
            "features": geo_result["features"],
            "semantic": None,
            "semantic_available": False,
            "target_region": target_region,
            "overrides": geo_result["overrides"],
            "param_count": geo_result["param_count"],
        }

    sem_overrides = semantic_to_overrides(sem_features, target_region, intensity)

    # 3. 融合：final = geo*(1-w) + sem*w（按参数插值）
    # 冲突仲裁：当某参数被语义轴"强驱动"（|drive|>0.5）且语义显著（confidence>0.3）时，
    # 几何特征对斜向等歧义纹样常误判方向（如锯齿被判"纵向"），此时以语义为准，权重提升到 0.75
    w = max(0.0, min(1.0, semantic_weight))
    geo_ov = geo_result["overrides"]
    fused = {}
    all_groups = set(geo_ov) | set(sem_overrides)
    for g in all_groups:
        geo_items = geo_ov.get(g, {})
        sem_items = sem_overrides.get(g, {})
        all_keys = set(geo_items) | set(sem_items)
        for k in all_keys:
            if k in geo_items and k in sem_items:
                w_k = w
                if sem_features.confidence > 0.3:
                    drive = _semantic_drive_strength(k, sem_features)
                    if abs(drive) > 0.5:
                        w_k = max(w, 0.75)
                fused.setdefault(g, {})[k] = round(
                    geo_items[k] * (1 - w_k) + sem_items[k] * w_k, 1
                )
            elif k in geo_items:
                fused.setdefault(g, {})[k] = geo_items[k]
            else:
                fused.setdefault(g, {})[k] = sem_items[k]

    return {
        "features": geo_result["features"],
        "semantic": asdict(sem_features),
        "semantic_available": True,
        "target_region": target_region,
        "overrides": fused,
        "param_count": sum(len(v) for v in fused.values()),
    }


# ============================================================
# CLI 测试
# ============================================================

if __name__ == "__main__":
    import sys

    if not TORCH_AVAILABLE:
        print("torch/transformers 未安装: pip install torch transformers")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("用法: python clip_semantics.py <图片路径>")
        sys.exit(0)

    print(f"可用性: {is_available()}")
    sem = extract_semantic_features(sys.argv[1])
    if sem is None:
        print(f"语义提取失败: {get_load_error()}")
        sys.exit(1)

    print("=" * 60)
    print("【CLIP 语义特征】")
    for axis, (label, _, _) in SEMANTIC_AXES.items():
        s = getattr(sem, axis)
        neg = _negative_label(axis)
        bar = "#" * int(s * 30)
        print(f"  {label}({axis}) {s:.3f}  [{bar}{' ' * (30 - len(bar))}] ←→ {neg}")
    print(f"  显著度: {sem.confidence:.3f}")
    print(f"  风格关键词: {sem.style_keywords}")
    print("=" * 60)

    ov = semantic_to_overrides(sem, "整车", 0.6)
    print(f"【语义调参结果】({sum(len(v) for v in ov.values())} 项)")
    for g, items in ov.items():
        for k, v in items.items():
            print(f"  {g}.{k} = {v}")
