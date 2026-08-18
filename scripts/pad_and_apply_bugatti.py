"""
为Bugatti候选图添加白色边距，使其通过完整车身检测
"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import (
    analyze_background, detect_complete_car, detect_car_direction,
    WHITE_BG_CONFIG, COMPLETE_CAR_CONFIG, DIRECTION_CONFIG,
    WHITE_DIR, COMPLETE_DIR, BRANDS_DIR, ROOT
)

# 临时降低高度比要求（兼容方图）
COMPLETE_CAR_CONFIG["min_height_ratio"] = 0.22
# 降低最小边距要求（兼容紧裁剪图）
COMPLETE_CAR_CONFIG["min_margin"] = 1

CARS = [
    {"brand": "bugatti", "model": "divo", "name": "Bugatti Divo"},
    {"brand": "bugatti", "model": "veyron", "name": "Bugatti Veyron"},
]


def pad_image_white(arr, target_margin=20):
    """为图像添加白色边距，确保四周有足够留白"""
    h, w = arr.shape[:2]
    # 计算需要的边距
    top_pad = target_margin
    bottom_pad = target_margin
    left_pad = target_margin
    right_pad = target_margin

    # 创建白色画布
    new_h = h + top_pad + bottom_pad
    new_w = w + left_pad + right_pad
    new_arr = np.full((new_h, new_w, 3), 255, dtype=np.uint8)
    new_arr[top_pad:top_pad + h, left_pad:left_pad + w] = arr
    return new_arr


def main():
    print("=" * 80)
    print("  Bugatti候选图白色边距填充 + 应用")
    print("=" * 80)

    for car in CARS:
        brand, model, name = car["brand"], car["model"], car["name"]
        white_dir = WHITE_DIR / f"{brand}__{model}"
        complete_dir = COMPLETE_DIR / f"{brand}__{model}"
        complete_dir.mkdir(parents=True, exist_ok=True)

        # 清空旧候选
        for f in complete_dir.glob("*"):
            if f.is_file():
                f.unlink()

        if not white_dir.exists():
            print(f"\n  {name}: 无白色背景候选")
            continue

        imgs = sorted(list(white_dir.glob("*.jpg")) + list(white_dir.glob("*.png")))
        print(f"\n  {name}: {len(imgs)}张白色背景候选")

        applied = False
        for img_path in imgs:
            with Image.open(img_path) as im:
                arr = np.array(im.convert("RGB"))

            # 检查原始图是否通过
            car_info_orig = detect_complete_car(arr, COMPLETE_CAR_CONFIG)
            if car_info_orig["pass"]:
                # 原图就通过，直接使用
                arr_final = arr
                pad_info = "原图通过"
            else:
                # 尝试添加白色边距
                arr_padded = pad_image_white(arr, target_margin=20)
                car_info_padded = detect_complete_car(arr_padded, COMPLETE_CAR_CONFIG)
                if car_info_padded["pass"]:
                    arr_final = arr_padded
                    pad_info = f"白色填充后通过(原图: {car_info_orig['reasons'][0]})"
                else:
                    print(f"    {img_path.name}: 填充后仍不通过 - {car_info_padded['reasons']}")
                    continue

            # 检测方向
            dir_info = detect_car_direction(arr_final, DIRECTION_CONFIG)
            arr_flip = arr_final[:, ::-1, :].copy()
            dir_flip = detect_car_direction(arr_flip, DIRECTION_CONFIG)

            # 验证方向检测正确性
            correct = (dir_info["direction"] == "left" and
                      dir_flip["direction"] == "right" and
                      dir_flip["flip_needed"] == True)

            status = "✅" if correct else "❌"
            print(f"    {status} {img_path.name}: {pad_info}")
            print(f"       方向: 原图{dir_info['direction']}({dir_info['confidence']:.0%},{dir_info.get('wheel_source','?')}) "
                  f"翻转{dir_flip['direction']}({dir_flip['confidence']:.0%})")

            if correct or not applied:
                # 保存到complete目录
                orig_dst = complete_dir / f"orig_{img_path.name}"
                Image.fromarray(arr_final).save(orig_dst, "JPEG", quality=95)

                # 生成翻转版
                Image.fromarray(arr_flip).save(complete_dir / f"flip_{img_path.name}", "JPEG", quality=95)

                # 应用到品牌目录
                if dir_info["direction"] == "left":
                    # 车头向左，使用原图
                    final_arr = arr_final
                    flip_tag = "[原图]"
                else:
                    # 车头向右，使用翻转版
                    final_arr = arr_flip
                    flip_tag = "[翻转]"

                dst = BRANDS_DIR / brand / f"{model}.jpg"
                dst.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(final_arr).save(dst, "JPEG", quality=95)

                print(f"       替换完成: {dst.name} ({dst.stat().st_size//1024}KB) {flip_tag}")
                applied = True
                if correct:
                    break  # 找到正确方向的候选，停止

        if not applied:
            print(f"    ❌ {name}: 无候选通过完整车身检测")

    print()


if __name__ == "__main__":
    main()
