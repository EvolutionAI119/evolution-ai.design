"""
EVOLUTION-AI 参数化纹理分析器
==============================

输入一张设计纹样图，提取其视觉特征（方向、圆润度、复杂度、对称性、色调），
并映射为汽车参数覆盖（overrides dict），实现"看纹样自动调参"。

可被两处调用：
  1. Web 后端 API（POST /texture/analyze）
  2. Rhino 插件（导入纹样图 → 自动改参 → 重新生成车身）

依赖：Pillow, numpy
    pip install Pillow numpy
"""
from __future__ import annotations

import io
import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============================================================
# 特征数据结构
# ============================================================

@dataclass
class TextureFeatures:
    """纹样图提取的视觉特征"""
    # 方向特征：0=横向为主, 1=纵向为主, 2=斜向, 3=无明显方向
    direction: float = 0.5  # 0.0~1.0, 越接近1越偏纵向
    direction_score: float = 0.0  # 方向显著性 0~1

    # 圆润度：0=全是尖角, 1=全是圆角/曲线
    roundness: float = 0.5

    # 复杂度/密度：0=极简, 1=极繁
    complexity: float = 0.5

    # 对称性：0=完全不对称, 1=完美左右对称
    symmetry: float = 0.5

    # 色调：0=冷色, 0.5=中性, 1=暖色
    warmth: float = 0.5

    # 亮度：0=暗, 1=亮
    brightness: float = 0.5

    # 饱和度：0=灰, 1=鲜艳
    saturation: float = 0.5

    # 主色（RGB 0~255）
    dominant_color: tuple = (128, 128, 128)

    # 原始尺寸
    image_size: tuple = (0, 0)


# ============================================================
# 目标部位定义
# ============================================================

# 每个部位对应影响哪些参数组和参数键
TARGET_REGIONS = {
    "整车": {
        "desc": "影响整体比例与造型风格",
        "params": [
            ("整车尺寸", "overall_length"),
            ("整车尺寸", "overall_width"),
            ("整车尺寸", "overall_height"),
            ("造型角度", "hood_angle"),
            ("造型角度", "windshield_angle"),
            ("造型角度", "rear_window_angle"),
            ("造型角度", "rear_slant_angle"),
            ("车身部件", "wheel_arch_radius"),
        ],
    },
    "引擎盖": {
        "desc": "影响发动机盖尺寸与角度",
        "params": [
            ("车身部件", "hood_length"),
            ("车身部件", "hood_width"),
            ("车身部件", "hood_height"),
            ("造型角度", "hood_angle"),
        ],
    },
    "车顶": {
        "desc": "影响车顶与风挡造型",
        "params": [
            ("车身部件", "roof_width"),
            ("车身部件", "roof_height"),
            ("车身部件", "windshield_width"),
            ("车身部件", "windshield_height"),
            ("造型角度", "windshield_angle"),
            ("造型角度", "rear_window_angle"),
            ("造型角度", "rear_slant_angle"),
        ],
    },
    "翼子板": {
        "desc": "影响轮拱与车轮",
        "params": [
            ("车身部件", "wheel_arch_radius"),
            ("车身部件", "wheel_diameter"),
            ("车身部件", "wheel_width"),
            ("整车尺寸", "track_width"),
        ],
    },
    "前脸": {
        "desc": "影响前保险杠、格栅、大灯",
        "params": [
            ("车身部件", "grille_width"),
            ("车身部件", "grille_height"),
            ("车身部件", "headlight_width"),
            ("车身部件", "headlight_height"),
            ("造型角度", "hood_angle"),
            ("比例参数", "overhang_front"),
        ],
    },
    "尾部": {
        "desc": "影响后保险杠、尾灯、行李箱",
        "params": [
            ("车身部件", "trunk_length"),
            ("车身部件", "trunk_width"),
            ("车身部件", "taillight_width"),
            ("车身部件", "taillight_height"),
            ("造型角度", "rear_slant_angle"),
            ("比例参数", "overhang_rear"),
        ],
    },
}


def list_target_regions() -> list[str]:
    """返回所有可选目标部位"""
    return list(TARGET_REGIONS.keys())


_PARAMS_DEF_CACHE: Optional[dict] = None


def _load_params_def() -> dict:
    """加载汽车参数定义 {group: {key: meta}}（含缓存）

    供本模块与 clip_semantics 共用，统一配置文件定位逻辑。
    """
    global _PARAMS_DEF_CACHE
    if _PARAMS_DEF_CACHE is not None:
        return _PARAMS_DEF_CACHE

    config_path = Path(__file__).resolve().parent.parent / "config" / "automotive_parameters.json"
    if not config_path.exists():
        for p in [Path.cwd() / "config" / "automotive_parameters.json"]:
            if p.exists():
                config_path = p
                break

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    _PARAMS_DEF_CACHE = config["automotive_parameters"]
    return _PARAMS_DEF_CACHE


# ============================================================
# 图像特征提取
# ============================================================

def _load_image(image_source, max_size: int = 256) -> np.ndarray:
    """加载图片并缩放到 max_size，返回 RGB numpy 数组 (H, W, 3)"""
    if isinstance(image_source, (str, Path)):
        img = Image.open(image_source)
    elif isinstance(image_source, bytes):
        img = Image.open(io.BytesIO(image_source))
    elif isinstance(image_source, Image.Image):
        img = image_source
    else:
        raise TypeError(f"不支持的图像输入类型: {type(image_source)}")

    img = img.convert("RGB")
    # 等比缩放
    w, h = img.size
    scale = max_size / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    return np.array(img, dtype=np.float32) / 255.0


def _grayscale(arr: np.ndarray) -> np.ndarray:
    """RGB → 灰度"""
    return 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]


def _sobel_gradient(gray: np.ndarray):
    """Sobel 梯度，返回 (gx, gy, magnitude, angle)"""
    # Sobel 核
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)

    def conv2d(img, kernel):
        kh, kw = kernel.shape
        ph, pw = kh // 2, kw // 2
        padded = np.pad(img, ((ph, ph), (pw, pw)), mode="edge")
        out = np.zeros_like(img)
        for i in range(kh):
            for j in range(kw):
                out += padded[i:i + img.shape[0], j:j + img.shape[1]] * kernel[i, j]
        return out

    gx = conv2d(gray, kx)
    gy = conv2d(gray, ky)
    mag = np.sqrt(gx ** 2 + gy ** 2)
    angle = np.arctan2(gy, gx)  # -pi ~ pi
    return gx, gy, mag, angle


def extract_features(image_source, max_size: int = 256) -> TextureFeatures:
    """从纹样图提取视觉特征"""
    if not PIL_AVAILABLE:
        raise ImportError("需要 Pillow: pip install Pillow")

    arr = _load_image(image_source, max_size)
    h, w = arr.shape[:2]
    gray = _grayscale(arr)

    feat = TextureFeatures(image_size=(w, h))

    # ---- 1. 方向特征 ----
    gx, gy, mag, angle = _sobel_gradient(gray)
    # 只考虑梯度显著的像素
    threshold = np.mean(mag) + np.std(mag) * 0.5
    mask = mag > threshold
    if mask.sum() > 0:
        sig_angles = angle[mask]
        # 方向度量：cos²(angle) 衡量"纵向程度"
        # - 纵向条纹(垂直线) → 梯度水平 → angle≈0/π → cos²≈1 → direction≈1 ✓
        # - 横向条纹(水平线) → 梯度垂直 → angle≈π/2 → cos²≈0 → direction≈0 ✓
        feat.direction = float(np.mean(np.cos(sig_angles) ** 2))
        feat.direction_score = float(mask.sum() / (h * w))  # 边缘密度作为显著性

    # ---- 2. 圆润度（线方向的局部一致性，梯度加权）----
    # 把梯度方向 angle(-π~π) 转为线方向(0~π)
    line_angle = angle % math.pi
    line_angle[line_angle >= math.pi - 1e-6] = 0.0
    # 用梯度大小作为权重，非边缘像素(mag小)对方向一致性影响小
    cos2_full = np.cos(line_angle * 2)
    sin2_full = np.sin(line_angle * 2)
    w_full = mag  # 权重 = 梯度大小

    # 3x3 邻域加权平均
    def weighted_local_mean(values, weights):
        v_pad = np.pad(values, ((1, 1), (1, 1)), mode="constant", constant_values=0)
        w_pad = np.pad(weights, ((1, 1), (1, 1)), mode="constant", constant_values=0)
        v_sum = np.zeros_like(values)
        w_sum = np.zeros_like(weights)
        for di in range(-1, 2):
            for dj in range(-1, 2):
                v_sum += v_pad[1 + di:1 + di + h, 1 + dj:1 + dj + w] * w_pad[1 + di:1 + di + h, 1 + dj:1 + dj + w]
                w_sum += w_pad[1 + di:1 + di + h, 1 + dj:1 + dj + w]
        return v_sum / np.maximum(w_sum, 1e-6)

    mean_cos2 = weighted_local_mean(cos2_full, w_full)
    mean_sin2 = weighted_local_mean(sin2_full, w_full)
    # 也需要对 cos2^2 和 sin2^2 做加权平均来算方差
    mean_cos2_sq = weighted_local_mean(cos2_full ** 2, w_full)
    mean_sin2_sq = weighted_local_mean(sin2_full ** 2, w_full)
    var_cos2 = np.maximum(mean_cos2_sq - mean_cos2 ** 2, 0)
    var_sin2 = np.maximum(mean_sin2_sq - mean_sin2 ** 2, 0)
    # circular variance ≈ (var_cos2 + var_sin2) / 2（归一化到 0~1）
    circ_var = (var_cos2 + var_sin2) / 2.0

    edge_cv = circ_var[mask]
    if len(edge_cv) > 0:
        mean_cv = float(np.mean(edge_cv))
        # 直线/平滑曲线 mean_cv≈0；拐角处 mean_cv 大
        sharpness = min(mean_cv / 0.15, 1.0)
        feat.roundness = float(1.0 - sharpness)

    # ---- 3. 复杂度/密度 ----
    # 用边缘密度（梯度显著像素占比）
    feat.complexity = float(min(mask.sum() / (h * w) * 5, 1.0))

    # ---- 4. 对称性 ----
    # 左右镜像相似度
    if w >= 4:
        left = gray[:, :w // 2]
        right_flipped = np.fliplr(gray[:, w // 2 + (w % 2):])
        min_w = min(left.shape[1], right_flipped.shape[1])
        if min_w > 0:
            left_crop = left[:, :min_w]
            right_crop = right_flipped[:, :min_w]
            # 归一化互相关
            l_std = left_crop.std()
            r_std = right_crop.std()
            if l_std > 1e-6 and r_std > 1e-6:
                ncc = np.mean((left_crop - left_crop.mean()) * (right_crop - right_crop.mean())) / (l_std * r_std)
                feat.symmetry = float(max(0, min(1, (ncc + 1) / 2)))

    # ---- 5. 色调（冷暖）----
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # 暖色：R 高 B 低；冷色：B 高 R 低
    warmth = np.mean(r - b)  # -1~1
    feat.warmth = float(max(0, min(1, (warmth + 1) / 2)))

    # ---- 6. 亮度 ----
    feat.brightness = float(np.mean(gray))

    # ---- 7. 饱和度 ----
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    sat = np.where(max_c > 1e-6, (max_c - min_c) / np.maximum(max_c, 1e-6), 0)
    feat.saturation = float(np.mean(sat))

    # ---- 8. 主色 ----
    # 简单量化：把颜色分到 64 个 bin，取最多的
    quantized = (arr * 3).astype(int)  # 0~3
    flat = quantized.reshape(-1, 3)
    # 用唯一值统计
    colors, counts = np.unique(flat, axis=0, return_counts=True)
    top_idx = np.argmax(counts)
    top = colors[top_idx]
    feat.dominant_color = tuple(int(c * 255 / 3) for c in top)

    return feat


# ============================================================
# 特征 → 参数映射
# ============================================================

def features_to_overrides(
    features: TextureFeatures,
    target_region: str = "整车",
    intensity: float = 0.5,
) -> dict:
    """将纹样特征映射为汽车参数覆盖

    Args:
        features: 提取的纹样特征
        target_region: 目标部位（见 TARGET_REGIONS）
        intensity: 调参强度 0~1，0=不变，1=最大幅度

    Returns:
        overrides dict: {group: {key: value}}
    """
    if target_region not in TARGET_REGIONS:
        raise ValueError(f"未知目标部位: {target_region}，可选: {list(TARGET_REGIONS.keys())}")

    intensity = max(0.0, min(1.0, intensity))
    region = TARGET_REGIONS[target_region]

    # 加载默认参数定义（含 min/max 与默认值）
    params_def = _load_params_def()

    overrides = {}

    for group, key in region["params"]:
        if group not in params_def or key not in params_def[group]:
            continue
        meta = params_def[group][key]
        if "min_value" not in meta or "max_value" not in meta:
            continue

        cur = meta["value"]
        lo = meta["min_value"]
        hi = meta["max_value"]
        rng = hi - lo
        if rng <= 0:
            continue

        # 根据不同参数，用不同特征驱动
        new_val = cur

        # ====== 整车尺寸 ======
        if key == "overall_length":
            # 横向纹样(方向低) → 车长增加；纵向 → 车长减少
            factor = (0.5 - features.direction) * 2  # -1~1
            new_val = cur + factor * rng * 0.3 * intensity

        elif key == "overall_width":
            # 横向纹样 → 车宽增加
            factor = (0.5 - features.direction) * 2
            new_val = cur + factor * rng * 0.25 * intensity

        elif key == "overall_height":
            # 纵向纹样 → 车高增加
            factor = (features.direction - 0.5) * 2
            new_val = cur + factor * rng * 0.3 * intensity

        # ====== 造型角度 ======
        elif key == "hood_angle":
            # 圆润纹样 → 角度变小(平缓)；尖锐 → 角度变大
            factor = (0.5 - features.roundness) * 2
            new_val = cur + factor * rng * 0.4 * intensity

        elif key == "windshield_angle":
            # 纵向纹样 → 风挡更直立(角度大)；横向 → 更倾斜
            factor = (features.direction - 0.5) * 2
            new_val = cur + factor * rng * 0.3 * intensity

        elif key == "rear_window_angle":
            factor = (features.direction - 0.5) * 2
            new_val = cur + factor * rng * 0.3 * intensity

        elif key == "rear_slant_angle":
            # 圆润 → 后倾小；复杂 → 后倾大
            factor = (features.complexity - 0.5) * 2 - (0.5 - features.roundness)
            new_val = cur + factor * rng * 0.3 * intensity

        # ====== 车身部件 ======
        elif key == "wheel_arch_radius":
            # 圆润纹样 → 轮拱大
            factor = (features.roundness - 0.5) * 2
            new_val = cur + factor * rng * 0.4 * intensity

        elif key == "wheel_diameter":
            factor = (features.roundness - 0.5) * 2
            new_val = cur + factor * rng * 0.3 * intensity

        elif key == "wheel_width":
            factor = (0.5 - features.direction) * 2
            new_val = cur + factor * rng * 0.2 * intensity

        elif key == "track_width":
            factor = (0.5 - features.direction) * 2
            new_val = cur + factor * rng * 0.2 * intensity

        elif key in ("hood_length", "roof_width", "trunk_length", "trunk_width",
                     "grille_width", "headlight_width", "taillight_width"):
            # 横向纹样 → 宽度/长度增加
            factor = (0.5 - features.direction) * 2
            new_val = cur + factor * rng * 0.25 * intensity

        elif key in ("hood_height", "roof_height", "windshield_height", "rear_window_height",
                     "grille_height", "headlight_height", "taillight_height"):
            # 纵向纹样 → 高度增加
            factor = (features.direction - 0.5) * 2
            new_val = cur + factor * rng * 0.25 * intensity

        elif key == "windshield_width":
            factor = (0.5 - features.direction) * 2
            new_val = cur + factor * rng * 0.2 * intensity

        # ====== 比例参数 ======
        elif key == "overhang_front":
            factor = (features.complexity - 0.5) * 2
            new_val = cur + factor * rng * 0.3 * intensity

        elif key == "overhang_rear":
            factor = (features.complexity - 0.5) * 2
            new_val = cur + factor * rng * 0.3 * intensity

        # 限制范围
        new_val = max(lo, min(hi, new_val))
        # 取整（长度类）
        if meta.get("type") in ("length", "width", "height", "distance", "diameter", "radius"):
            new_val = round(new_val)
        else:
            new_val = round(new_val, 1)

        overrides.setdefault(group, {})[key] = new_val

    return overrides


# ============================================================
# 一键分析入口
# ============================================================

def analyze_texture(
    image_source,
    target_region: str = "整车",
    intensity: float = 0.5,
) -> dict:
    """一键分析：输入纹样图 + 目标部位 → 返回特征 + 参数覆盖

    Args:
        image_source: 图片路径 / bytes / PIL.Image
        target_region: 目标部位
        intensity: 调参强度 0~1

    Returns:
        {
            "features": {...},
            "target_region": "整车",
            "overrides": {...},
            "param_count": N,
        }
    """
    features = extract_features(image_source)
    overrides = features_to_overrides(features, target_region, intensity)

    return {
        "features": asdict(features),
        "target_region": target_region,
        "overrides": overrides,
        "param_count": sum(len(v) for v in overrides.values()),
    }


# ============================================================
# CLI 测试
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python texture_analyzer.py <图片路径> [目标部位] [强度0~1]")
        print(f"可选目标部位: {list_target_regions()}")
        sys.exit(0)

    img_path = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "整车"
    intensity = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

    if not Path(img_path).exists():
        print(f"图片不存在: {img_path}")
        sys.exit(1)

    result = analyze_texture(img_path, region, intensity)

    print("=" * 60)
    print(f"纹样图: {img_path}")
    print(f"目标部位: {region}")
    print(f"调参强度: {intensity}")
    print("-" * 60)
    print("【提取的视觉特征】")
    f = result["features"]
    print(f"  方向(0横~1纵):        {f['direction']:.3f}  (显著性 {f['direction_score']:.3f})")
    print(f"  圆润度(0尖~1圆):      {f['roundness']:.3f}")
    print(f"  复杂度(0简~1繁):      {f['complexity']:.3f}")
    print(f"  对称性(0~1):          {f['symmetry']:.3f}")
    print(f"  冷暖(0冷~1暖):        {f['warmth']:.3f}")
    print(f"  亮度:                 {f['brightness']:.3f}")
    print(f"  饱和度:               {f['saturation']:.3f}")
    print(f"  主色(RGB):            {f['dominant_color']}")
    print(f"  图像尺寸:             {f['image_size']}")
    print("-" * 60)
    print(f"【自动调参结果】（共 {result['param_count']} 项）")
    for group, items in result["overrides"].items():
        print(f"  [{group}]")
        for k, v in items.items():
            print(f"    {k} = {v}")
    print("=" * 60)
