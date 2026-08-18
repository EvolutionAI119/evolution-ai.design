"""检查Bugatti候选图的车身检测详情"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import (
    analyze_background, detect_complete_car,
    WHITE_BG_CONFIG, COMPLETE_CAR_CONFIG, WHITE_DIR
)

ROOT = Path(__file__).resolve().parent.parent

CARS = [
    {"brand": "bugatti", "model": "divo"},
    {"brand": "bugatti", "model": "veyron"},
]

for car in CARS:
    brand, model = car["brand"], car["model"]
    white_dir = WHITE_DIR / f"{brand}__{model}"
    print(f"\n  {brand}/{model}:")
    if not white_dir.exists():
        print(f"    目录不存在")
        continue
    imgs = sorted(list(white_dir.glob("*.jpg")) + list(white_dir.glob("*.png")))
    for img_path in imgs:
        with Image.open(img_path) as im:
            arr = np.array(im.convert("RGB"))
        h, w = arr.shape[:2]
        white_info = analyze_background(arr, WHITE_BG_CONFIG)
        car_info = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
        print(f"    {img_path.name}: {w}×{h} asp={white_info['asp']:.2f}")
        print(f"      白: {white_info['white_ratio']:.0f}% 通过={white_info['pass']}")
        print(f"      车身: 通过={car_info['pass']}")
        print(f"      车身原因: {car_info['reasons']}")
        if "width_ratio" in car_info:
            print(f"      车宽比: {car_info['width_ratio']:.0f}% 车高比: {car_info['height_ratio']:.0f}%")
            print(f"      边距: 上{car_info['top_margin']} 下{car_info['bottom_margin']} 左{car_info['left_margin']} 右{car_info['right_margin']}")
