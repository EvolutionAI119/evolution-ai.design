"""
测试基于挡风玻璃/上轮廓斜率的方向检测
====================================
核心原理：挡风玻璃是车顶轮廓中最陡的上升段
- 挡风玻璃总是在车头侧
- 找到上轮廓y_top(x)的最陡下降段（y值减小最快=上升最快）
- 该段位置就是挡风玻璃位置
- 挡风玻璃在车身中心左侧 → 车头向左
- 挡风玻璃在车身中心右侧 → 车头向右

测试19款车，验证此方法对4款失败车型是否有效。
"""
import sys
import json
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import detect_car_direction, DIRECTION_CONFIG, _smooth_contour

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


def detect_windshield(arr, config=None):
    """
    基于挡风玻璃的方向检测
    ======================
    原理：
    1. 上轮廓y_top(x)描述车顶最高像素位置
    2. 挡风玻璃段是y_top下降最快的段（图像坐标中y减小=车身上升）
    3. 后窗段是y_top上升最快的段（车顶到尾部下降）
    4. 挡风玻璃位置 < 车身中心 → 车头在左
    5. 挡风玻璃位置 > 车身中心 → 车头在右

    返回：dict with windshield_x, rear_window_x, direction, confidence
    """
    if config is None:
        config = DIRECTION_CONFIG

    h, w = arr.shape[:2]
    white_threshold = config["white_threshold"]
    mask = ~np.all(arr > white_threshold, axis=2)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    y_indices = np.where(rows)[0]
    x_indices = np.where(cols)[0]

    if len(y_indices) < 20 or len(x_indices) < 20:
        return None

    y_min, y_max = y_indices[0], y_indices[-1]
    x_min, x_max = x_indices[0], x_indices[-1]
    car_height = y_max - y_min
    car_width = x_max - x_min

    # 上轮廓
    y_top = np.full(w, float(y_max + 1), dtype=float)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            y_top[x] = float(col_pixels[0])

    window = max(3, int(car_width * config["smooth_window_ratio"]))
    y_top_smooth = _smooth_contour(y_top, x_min, x_max, window)

    # 计算梯度（dy/dx）
    # y_top下降 = 车身上升（向车顶爬升）
    # y_top上升 = 车身下降（从车顶到尾部）
    dy_dx = np.zeros(w)
    for x in range(x_min + 1, x_max + 1):
        dy_dx[x] = y_top_smooth[x] - y_top_smooth[x - 1]

    # 平滑梯度
    grad_window = max(3, int(car_width * 0.02))
    dy_dx_smooth = dy_dx.copy()
    for x in range(x_min, x_max + 1):
        xl = max(x_min, x - grad_window)
        xr = min(x_max, x + grad_window)
        dy_dx_smooth[x] = float(np.mean(dy_dx[xl:xr + 1]))

    # 找最陡的下降段（挡风玻璃，dy/dx最负）
    # 用滑动窗口找一段连续下降最剧烈的区域
    ws = max(5, int(car_width * 0.10))  # 挡风玻璃宽度约车宽10%
    best_descent_pos = -1
    best_descent_val = 0  # 最负值
    best_ascent_pos = -1
    best_ascent_val = 0  # 最正值

    for x in range(x_min + ws, x_max - ws + 1):
        # 在[x-ws, x+ws]范围内找累积下降/上升
        left_y = y_top_smooth[x - ws]
        right_y = y_top_smooth[x + ws]
        diff = right_y - left_y  # 正=上升(车身下降)，负=下降(车身上升)
        if diff < best_descent_val:
            best_descent_val = diff
            best_descent_pos = x  # 挡风玻璃中心
        if diff > best_ascent_val:
            best_ascent_val = diff
            best_ascent_pos = x  # 后窗中心

    body_center = (x_min + x_max) / 2.0

    # 挡风玻璃判定
    if best_descent_pos < 0:
        return None

    windshield_x = best_descent_pos
    rear_window_x = best_ascent_pos if best_ascent_pos >= 0 else windshield_x

    # 方向判定：挡风玻璃在车身中心左侧 → 车头在左
    windshield_shift = windshield_x - body_center
    windshield_shift_ratio = windshield_shift / car_width

    # 后窗也作为参考：后窗在车身中心右侧 → 车头在左
    rear_shift = rear_window_x - body_center
    rear_shift_ratio = rear_shift / car_width

    # 综合判定
    # 挡风玻璃偏左 + 后窗偏右 → 强烈left信号
    # 挡风玻璃偏右 + 后窗偏左 → 强烈right信号
    score = 0
    if windshield_shift_ratio < -0.02:
        score -= 1
    elif windshield_shift_ratio > 0.02:
        score += 1

    if rear_shift_ratio > 0.02:
        score -= 1
    elif rear_shift_ratio < -0.02:
        score += 1

    if score < 0:
        direction = "left"
        confidence = min(1.0, 0.5 + abs(windshield_shift_ratio) * 5 + abs(rear_shift_ratio) * 3)
    elif score > 0:
        direction = "right"
        confidence = min(1.0, 0.5 + abs(windshield_shift_ratio) * 5 + abs(rear_shift_ratio) * 3)
    else:
        # 平票，用挡风玻璃位置裁决
        if windshield_shift < 0:
            direction = "left"
        else:
            direction = "right"
        confidence = 0.3

    return {
        "windshield_x": float(windshield_x),
        "rear_window_x": float(rear_window_x),
        "body_center": float(body_center),
        "windshield_shift": float(windshield_shift),
        "rear_shift": float(rear_shift),
        "windshield_shift_ratio": float(windshield_shift_ratio),
        "rear_shift_ratio": float(rear_shift_ratio),
        "direction": direction,
        "confidence": float(confidence),
        "best_descent_val": float(best_descent_val),
        "best_ascent_val": float(best_ascent_val),
    }


def main():
    print("=" * 100)
    print("  挡风玻璃方向检测 - 全量测试（19款车）")
    print("=" * 100)

    results = []
    passed = 0
    failed = 0

    for car in ALL_CARS:
        brand, model = car["brand"], car["model"]
        img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"

        if not img_path.exists():
            print(f"  ⚠️ 跳过 {brand}/{model} - 图片不存在")
            continue

        with Image.open(img_path) as im:
            arr = np.array(im.convert("RGB"))

        # 原图
        ws_orig = detect_windshield(arr)
        # 翻转图
        arr_flip = arr[:, ::-1, :].copy()
        ws_flip = detect_windshield(arr_flip)

        if ws_orig is None or ws_flip is None:
            print(f"  ❌ {brand}/{model}: 检测失败")
            failed += 1
            results.append({
                "car": f"{brand}/{model}",
                "ws_orig_dir": "none",
                "ws_flip_dir": "none",
                "ws_orig_shift": 0,
                "ws_flip_shift": 0,
                "pass": False,
            })
            continue

        pass_orig = ws_orig["direction"] == "left"
        pass_flip = ws_flip["direction"] == "right"
        both_pass = pass_orig and pass_flip

        if both_pass:
            passed += 1
            status = "✅"
        else:
            failed += 1
            status = "❌"

        results.append({
            "car": f"{brand}/{model}",
            "ws_orig_dir": ws_orig["direction"],
            "ws_orig_conf": ws_orig["confidence"],
            "ws_orig_shift": ws_orig["windshield_shift_ratio"],
            "ws_orig_rear_shift": ws_orig["rear_shift_ratio"],
            "ws_flip_dir": ws_flip["direction"],
            "ws_flip_conf": ws_flip["confidence"],
            "ws_flip_shift": ws_flip["windshield_shift_ratio"],
            "ws_flip_rear_shift": ws_flip["rear_shift_ratio"],
            "pass": both_pass,
            "status": status,
        })

        print(f"  {status} {brand}/{model:<25} "
              f"原图:{ws_orig['direction']}({ws_orig['confidence']:.0%},ws_shift={ws_orig['windshield_shift_ratio']:+.3f},rear_shift={ws_orig['rear_shift_ratio']:+.3f}) "
              f"翻转:{ws_flip['direction']}({ws_flip['confidence']:.0%},ws_shift={ws_flip['windshield_shift_ratio']:+.3f})")

    total = len(results)
    print(f"\n{'=' * 100}")
    print(f"  测试结果: {passed}/{total} 通过 ({passed/total*100:.0f}%)")
    print(f"  失败: {failed}")
    print(f"{'=' * 100}")

    if failed > 0:
        print(f"\n  ❌ 失败车型:")
        for r in results:
            if not r["pass"]:
                print(f"    {r['car']}: 原图={r.get('ws_orig_dir','?')} 翻转={r.get('ws_flip_dir','?')}")

    # 生成HTML报告
    html = generate_html(results, passed, failed, total)
    out = ROOT / "public" / "_test_windshield_report.html"
    out.write_text(html, encoding="utf-8")
    print(f"\n  HTML报告: http://localhost:5173/_test_windshield_report.html")

    return 0 if failed == 0 else 1


def generate_html(results, passed, failed, total):
    rows = ""
    for i, r in enumerate(results):
        row_class = "pass-row" if r["pass"] else "fail-row"
        status = "✅" if r["pass"] else "❌"
        rows += f"""<tr class="{row_class}">
<td>{i+1}</td><td>{r['car']}</td>
<td>{r.get('ws_orig_dir','?')}</td>
<td>{r.get('ws_orig_conf',0):.0%}</td>
<td>{r.get('ws_orig_shift',0):+.3f}</td>
<td>{r.get('ws_orig_rear_shift',0):+.3f}</td>
<td>{r.get('ws_flip_dir','?')}</td>
<td>{r.get('ws_flip_conf',0):.0%}</td>
<td>{r.get('ws_flip_shift',0):+.3f}</td>
<td>{r.get('ws_flip_rear_shift',0):+.3f}</td>
<td>{status}</td>
</tr>
"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>挡风玻璃方向检测报告</title>
<style>
body{{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}}
h1{{text-align:center;color:#2ecc71}}
.sub{{text-align:center;color:#888;margin-bottom:20px}}
.summary{{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px;text-align:center;font-size:18px}}
.pass{{color:#2ecc71}} .fail{{color:#e74c3c}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;text-align:left;border-bottom:1px solid #333}}
th{{background:#1a1a2e;color:#3498db}}
.pass-row{{background:#0a3a0a}} .fail-row{{background:#3a0a0a}}
</style></head><body>
<h1>挡风玻璃方向检测报告</h1>
<div class="sub">原理：挡风玻璃=上轮廓最陡下降段，位置相对车身中心判定方向</div>
<div class="summary">
  <span class="{'pass' if failed==0 else 'fail'}">通过 {passed}/{total} ({passed/total*100:.0f}%)</span> |
  <span class="fail">失败 {failed}</span>
</div>
<table>
<tr><th>#</th><th>车型</th>
<th>原图方向</th><th>原图置信度</th><th>原图ws_shift</th><th>原图rear_shift</th>
<th>翻转方向</th><th>翻转置信度</th><th>翻转ws_shift</th><th>翻转rear_shift</th>
<th>结果</th></tr>
{rows}
</table>
</body></html>"""


if __name__ == "__main__":
    sys.exit(main())
