"""检查4款失败车型的候选图过滤情况"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import (
    analyze_background, detect_complete_car, detect_car_direction,
    WHITE_BG_CONFIG, COMPLETE_CAR_CONFIG, DIRECTION_CONFIG
)

ROOT = Path(__file__).resolve().parent.parent

FAILED_CARS = [
    {"brand": "ferrari", "model": "sf90", "name": "Ferrari SF90"},
    {"brand": "porsche", "model": "cayenne", "name": "Porsche Cayenne"},
    {"brand": "bugatti", "model": "divo", "name": "Bugatti Divo"},
    {"brand": "bugatti", "model": "veyron", "name": "Bugatti Veyron"},
]


def main():
    print("=" * 100)
    print("  4款失败车型候选图分析")
    print("=" * 100)

    for car in FAILED_CARS:
        brand, model = car["brand"], car["model"]
        name = car["name"]
        car_dir = ROOT / "public" / "_bing_v2_candidates" / f"{brand}__{model}"

        if not car_dir.exists():
            print(f"\n  {name}: 候选目录不存在")
            continue

        imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
        print(f"\n  {name}: {len(imgs)}张候选图")

        white_passed = []
        complete_passed = []
        direction_correct = []

        for img_path in imgs:
            try:
                with Image.open(img_path) as im:
                    arr = np.array(im.convert("RGB"))
                white_info = analyze_background(arr, WHITE_BG_CONFIG)
                if not white_info["pass"]:
                    continue
                white_passed.append((img_path, white_info))

                complete_info = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
                if not complete_info["pass"]:
                    continue
                complete_passed.append((img_path, white_info, complete_info))

                # 方向检测
                dir_info = detect_car_direction(arr, DIRECTION_CONFIG)
                # 翻转图方向检测
                arr_flip = arr[:, ::-1, :].copy()
                dir_flip = detect_car_direction(arr_flip, DIRECTION_CONFIG)
                correct = (dir_info["direction"] == "left" and
                          dir_flip["direction"] == "right" and
                          dir_flip["flip_needed"] == True)
                if correct:
                    direction_correct.append((img_path, dir_info, dir_flip))
            except Exception as e:
                continue

        print(f"    通过纯白过滤: {len(white_passed)}/{len(imgs)}")
        print(f"    通过完整车身: {len(complete_passed)}/{len(imgs)}")
        print(f"    方向检测正确: {len(direction_correct)}/{len(complete_passed)}")

        if complete_passed:
            # 显示前5张通过的完整车身候选
            print(f"\n    通过完整车身的前5张:")
            for i, (img_path, w_info, c_info) in enumerate(complete_passed[:5]):
                arr = np.array(Image.open(img_path).convert("RGB"))
                dir_info = detect_car_direction(arr, DIRECTION_CONFIG)
                print(f"      [{i+1}] {img_path.name}: "
                      f"白{w_info['white_ratio']:.0f}% 车宽{c_info['width_ratio']:.0f}% "
                      f"方向{dir_info['direction']}({dir_info['confidence']:.0%},{dir_info.get('wheel_source','?')})")

        if direction_correct:
            print(f"\n    方向检测正确的候选:")
            for i, (img_path, dir_info, dir_flip) in enumerate(direction_correct[:3]):
                print(f"      [{i+1}] {img_path.name}: "
                      f"原图{dir_info['direction']}({dir_info['confidence']:.0%},{dir_info.get('wheel_source','?')}) "
                      f"翻转{dir_flip['direction']}({dir_flip['confidence']:.0%})")

    print()


if __name__ == "__main__":
    main()
