"""检查19款车品牌图的图片质量（是否满足完整车身+留白要求）"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import detect_complete_car, COMPLETE_CAR_CONFIG

ROOT = Path(__file__).resolve().parent.parent

ALL_CARS = [
    {"brand": "bentley", "model": "bentayga"},
    {"brand": "bentley", "model": "flying-spur"},
    {"brand": "bentley", "model": "continental-gtc"},
    {"brand": "bentley", "model": "continental-gt"},
    {"brand": "rolls-royce", "model": "cullinan"},
    {"brand": "rolls-royce", "model": "phantom"},
    {"brand": "rolls-royce", "model": "ghost"},
    {"brand": "rolls-royce", "model": "wraith"},
    {"brand": "ferrari", "model": "f8-tributo"},
    {"brand": "ferrari", "model": "sf90"},
    {"brand": "ferrari", "model": "roma"},
    {"brand": "porsche", "model": "911"},
    {"brand": "porsche", "model": "taycan"},
    {"brand": "porsche", "model": "macan"},
    {"brand": "porsche", "model": "cayenne"},
    {"brand": "porsche", "model": "panamera"},
    {"brand": "bugatti", "model": "divo"},
    {"brand": "bugatti", "model": "veyron"},
    {"brand": "bugatti", "model": "chiron"},
]


def main():
    print("=" * 90)
    print("  19款车品牌图质量检查")
    print("=" * 90)
    print(f"  {'车型':<30} {'尺寸':<12} {'车占比':<8} {'左留白':<6} {'右留白':<6} {'上留白':<6} {'下留白':<6} {'完整车身':<8}")
    print("-" * 90)

    good = 0
    bad = 0
    bad_cars = []

    for car in ALL_CARS:
        brand, model = car["brand"], car["model"]
        img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"
        if not img_path.exists():
            print(f"  {brand}/{model:<28} 图片不存在")
            continue

        with Image.open(img_path) as im:
            arr = np.array(im.convert("RGB"))
        h, w = arr.shape[:2]

        mask = ~np.all(arr > 230, axis=2)
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        y_idx = np.where(rows)[0]
        x_idx = np.where(cols)[0]
        y_min, y_max = y_idx[0], y_idx[-1]
        x_min, x_max = x_idx[0], x_idx[-1]
        car_w = x_max - x_min
        car_h = y_max - y_min

        width_ratio = car_w / w * 100
        left_margin = x_min
        right_margin = w - x_max - 1
        top_margin = y_min
        bottom_margin = h - y_max - 1

        info = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
        pass_check = info["pass"]

        status = "✅" if pass_check else "❌"
        if pass_check:
            good += 1
        else:
            bad += 1
            bad_cars.append(f"{brand}/{model}")

        name = f"{brand}/{model}"
        print(f"  {name:<30} {w}x{h:<8} {width_ratio:5.1f}%  {left_margin:<5} {right_margin:<5} {top_margin:<5} {bottom_margin:<5} {status}")

    print("-" * 90)
    print(f"  合格: {good}/19  不合格: {bad}/19")
    if bad_cars:
        print(f"  不合格车型: {', '.join(bad_cars)}")
        print(f"\n  ⚠️ 这些车型图片需要重新筛选替换（质量不达标导致方向检测失败）")


if __name__ == "__main__":
    main()
