"""快速检查4款失败车型的图像布局"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import DIRECTION_CONFIG

ROOT = Path(__file__).resolve().parent.parent

FAILED_CARS = [
    {"brand": "ferrari", "model": "sf90"},
    {"brand": "porsche", "model": "cayenne"},
    {"brand": "bugatti", "model": "divo"},
    {"brand": "bugatti", "model": "veyron"},
    # 对比：通过的车型
    {"brand": "bentley", "model": "bentayga"},
    {"brand": "porsche", "model": "911"},
]

print("=" * 100)
print("  图像布局诊断")
print("=" * 100)

for car in FAILED_CARS:
    brand, model = car["brand"], car["model"]
    img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"

    if not img_path.exists():
        print(f"  ⚠️ {brand}/{model}: 图片不存在")
        continue

    with Image.open(img_path) as im:
        arr = np.array(im.convert("RGB"))

    h, w = arr.shape[:2]
    white_threshold = DIRECTION_CONFIG["white_threshold"]
    mask = ~np.all(arr > white_threshold, axis=2)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    y_indices = np.where(rows)[0]
    x_indices = np.where(cols)[0]
    y_min, y_max = y_indices[0], y_indices[-1]
    x_min, x_max = x_indices[0], x_indices[-1]

    # 检查底部是否触边
    bottom_touch = (y_max >= h - 5)
    top_margin = y_min
    bottom_margin = h - y_max - 1
    left_margin = x_min
    right_margin = w - x_max - 1

    # 检查底部100像素的暗像素分布
    bottom_strip = arr[max(0, y_max - 50):y_max + 1, x_min:x_max + 1]
    bottom_dark_ratio = (bottom_strip < 100).sum() / bottom_strip.size * 3

    # 检查底部最后一行的颜色
    last_row_with_car = arr[y_max, x_min:x_max + 1]
    last_row_brightness = last_row_with_car.mean()

    # 车身底部5像素的颜色分布
    bottom_5px = arr[max(0, y_max - 5):y_max + 1, x_min:x_max + 1]
    bottom_5px_mean = bottom_5px.mean()

    print(f"\n  {brand}/{model}:")
    print(f"    图像尺寸: {w}×{h}")
    print(f"    车辆边界: x[{x_min}-{x_max}] y[{y_min}-{y_max}]")
    print(f"    边距: 上{top_margin} 下{bottom_margin} 左{left_margin} 右{right_margin}")
    print(f"    底部触边: {'是 ❌' if bottom_touch else '否 ✅'}")
    print(f"    底部最后行平均亮度: {last_row_brightness:.0f}/255")
    print(f"    底部5像素平均亮度: {bottom_5px_mean:.0f}/255")
    print(f"    底部50像素暗像素比: {bottom_dark_ratio:.1%}")

    # 检查车轮是否在车身内部可见
    # 取车身中下部（y_min + 60% 到 y_max）
    car_height = y_max - y_min
    wheel_zone_y_start = y_min + int(car_height * 0.55)
    wheel_zone_y_end = y_max
    wheel_zone = arr[wheel_zone_y_start:wheel_zone_y_end + 1, x_min:x_max + 1]
    # 找非常暗的像素（车轮）
    very_dark = np.all(wheel_zone < 60, axis=2)
    # 按列统计暗像素
    dark_per_col = very_dark.sum(axis=0)
    # 找有明显暗像素聚集的列
    has_dark = dark_per_col > 3
    # 找连续段
    dark_segments = []
    in_seg = False
    seg_start = 0
    for i, hd in enumerate(has_dark):
        if hd and not in_seg:
            in_seg = True
            seg_start = i
        elif not hd and in_seg:
            in_seg = False
            if i - seg_start >= 5:
                dark_segments.append((seg_start, i, i - seg_start))
    if in_seg:
        dark_segments.append((seg_start, len(has_dark), len(has_dark) - seg_start))

    # 过滤过短段
    dark_segments = [s for s in dark_segments if s[2] >= 5]
    print(f"    车身下部暗区段数: {len(dark_segments)}")
    for i, (s, e, length) in enumerate(dark_segments[:6]):
        x_actual_start = x_min + s
        x_actual_end = x_min + e
        center = (x_actual_start + x_actual_end) / 2
        rel_pos = (center - x_min) / (x_max - x_min)
        print(f"      段{i+1}: x[{x_actual_start}-{x_actual_end}] 宽{length} 位置{rel_pos:.2f}(0=左端,1=右端)")

print()
