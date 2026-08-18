"""
诊断4款失败车型的方向检测失败原因
================================
可视化每款车的：
1. 原始图片（标注车辆边界框）
2. 底部轮廓曲线（标注车轮检测区域）
3. 列亮度曲线（标注暗区聚类）
4. 上轮廓曲线（标注左右非对称性）
5. 诊断结论（为什么方向检测失败）

失败车型：
- ferrari/sf90 (中置引擎超跑)
- porsche/cayenne (SUV)
- bugatti/divo (中置引擎超跑)
- bugatti/veyron (中置引擎超跑)
"""
import sys
import json
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import detect_car_direction, DIRECTION_CONFIG, _smooth_contour, _cluster_columns

ROOT = Path(__file__).resolve().parent.parent

FAILED_CARS = [
    {"brand": "ferrari", "model": "sf90", "layout": "中置引擎"},
    {"brand": "porsche", "model": "cayenne", "layout": "前置引擎SUV"},
    {"brand": "bugatti", "model": "divo", "layout": "中置引擎"},
    {"brand": "bugatti", "model": "veyron", "layout": "中置引擎"},
]


def diagnose_car(car):
    """诊断单款车"""
    brand, model = car["brand"], car["model"]
    img_path = ROOT / "public" / "brands" / brand / f"{model}.jpg"

    if not img_path.exists():
        return None

    with Image.open(img_path) as im:
        arr = np.array(im.convert("RGB"))

    h, w = arr.shape[:2]
    white_threshold = DIRECTION_CONFIG["white_threshold"]

    # 车辆mask
    mask = ~np.all(arr > white_threshold, axis=2)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    y_indices = np.where(rows)[0]
    x_indices = np.where(cols)[0]

    y_min, y_max = y_indices[0], y_indices[-1]
    x_min, x_max = x_indices[0], x_indices[-1]
    car_height = y_max - y_min
    car_width = x_max - x_min

    # 底部轮廓
    y_bottom = np.full(w, -1.0)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            y_bottom[x] = float(col_pixels[-1])

    window = max(3, int(car_width * DIRECTION_CONFIG["smooth_window_ratio"]))
    y_bottom_smooth = _smooth_contour(y_bottom, x_min, x_max, window)

    valid_bottom = y_bottom_smooth[x_min:x_max + 1]
    valid_bottom = valid_bottom[valid_bottom >= 0]
    max_y_bottom = float(np.max(valid_bottom)) if len(valid_bottom) > 0 else float(y_max)
    min_y_bottom = float(np.min(valid_bottom)) if len(valid_bottom) > 0 else float(y_min)

    dip_threshold = max_y_bottom - car_height * DIRECTION_CONFIG["wheel_dip_ratio"]
    is_wheel_bottom = y_bottom_smooth >= dip_threshold
    clusters_bottom = _cluster_columns(is_wheel_bottom, x_min, x_max,
                                        DIRECTION_CONFIG["wheel_cluster_gap"])
    min_wheel_w = max(3, int(car_width * DIRECTION_CONFIG["wheel_min_width_ratio"]))
    valid_bottom_clusters = [c for c in clusters_bottom if len(c) >= min_wheel_w]

    # 列亮度（底部60%以下）
    bottom_y_start = y_min + int(car_height * 0.6)
    col_brightness_data = []
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) == 0:
            col_brightness_data.append((x, None))
            continue
        bottom_pixels = col_pixels[col_pixels >= bottom_y_start]
        if len(bottom_pixels) < 2:
            col_brightness_data.append((x, None))
            continue
        col_brightness_data.append((x, float(arr[bottom_pixels, x].mean())))

    valid_bright = [(x, b) for x, b in col_brightness_data if b is not None]
    if valid_bright:
        bright_arr = np.array([b for _, b in valid_bright])
        median_b = float(np.median(bright_arr))
        adaptive_thr = median_b * 0.7
    else:
        median_b = 0
        adaptive_thr = 0

    # 上轮廓
    y_top = np.full(w, float(y_max + 1), dtype=float)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            y_top[x] = float(col_pixels[0])
    y_top_smooth = _smooth_contour(y_top, x_min, x_max, window)

    # 整列亮度（计算亮度重心）
    col_brightness_full = np.zeros(w)
    col_has_car = np.zeros(w, dtype=bool)
    for x in range(x_min, x_max + 1):
        col_pixels = np.where(mask[:, x])[0]
        if len(col_pixels) > 0:
            col_brightness_full[x] = float(arr[col_pixels, x].mean())
            col_has_car[x] = True

    body_center = (x_min + x_max) / 2.0
    bright_x = np.where(col_has_car[x_min:x_max + 1])[0] + x_min
    bright_vals = col_brightness_full[bright_x]
    if len(bright_vals) > 0 and bright_vals.sum() > 0:
        brightness_center = float(np.average(bright_x, weights=bright_vals))
    else:
        brightness_center = body_center

    # 运行算法获取完整结果
    result = detect_car_direction(arr, DIRECTION_CONFIG)

    return {
        "car": car,
        "img_path": str(img_path),
        "img_size": [w, h],
        "car_bbox": [int(x_min), int(y_min), int(x_max), int(y_max)],
        "car_width": int(car_width),
        "car_height": int(car_height),
        "body_center": float(body_center),
        "brightness_center": float(brightness_center),
        "brightness_shift": float(brightness_center - body_center),
        "y_bottom": y_bottom_smooth.tolist(),
        "y_top": y_top_smooth.tolist(),
        "x_min": int(x_min), "x_max": int(x_max),
        "max_y_bottom": float(max_y_bottom),
        "min_y_bottom": float(min_y_bottom),
        "bottom_range": float(max_y_bottom - min_y_bottom),
        "dip_threshold": float(dip_threshold),
        "valid_bottom_clusters": [[int(c[0]), int(c[-1]), len(c)] for c in valid_bottom_clusters],
        "median_brightness": float(median_b),
        "adaptive_thr": float(adaptive_thr),
        "col_brightness": [[x, b if b is not None else -1] for x, b in col_brightness_data],
        "result": result,
        "arr_shape": list(arr.shape),
    }


def generate_html_report(diags):
    """生成HTML诊断报告"""
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>方向检测失败车型诊断报告</title>",
        "<style>",
        "body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}",
        "h1{text-align:center;color:#f39c12}",
        ".sub{text-align:center;color:#888;margin-bottom:20px}",
        ".car-card{background:#16213e;border-radius:10px;padding:20px;margin-bottom:30px}",
        ".car-title{color:#3498db;font-size:20px;margin-bottom:10px}",
        ".layout-tag{background:#e74c3c;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;margin-left:10px}",
        ".metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-bottom:15px}",
        ".metric{background:#1a1a2e;padding:10px;border-radius:5px}",
        ".metric-label{color:#888;font-size:12px}",
        ".metric-value{color:#2ecc71;font-size:16px;font-weight:bold}",
        ".metric-value.bad{color:#e74c3c}",
        ".metric-value.warn{color:#f39c12}",
        ".chart{background:#1a1a2e;border-radius:5px;padding:15px;margin-bottom:10px}",
        ".chart-title{color:#3498db;margin-bottom:5px}",
        ".conclusion{background:#3a0a0a;border-radius:5px;padding:15px;margin-top:10px}",
        ".conclusion.good{background:#0a3a0a}",
        "canvas{display:block;background:#000}",
        "</style></head><body>",
        "<h1>方向检测失败车型诊断报告</h1>",
        "<div class='sub'>4款失败车型的详细特征分析</div>",
    ]

    for diag in diags:
        if diag is None:
            continue
        car = diag["car"]
        result = diag["result"]
        r = result

        html_parts.append(f"<div class='car-card'>")
        html_parts.append(f"<div class='car-title'>{car['brand']}/{car['model']}"
                          f"<span class='layout-tag'>{car['layout']}</span></div>")

        # 关键指标
        conf_class = "good" if r["confidence"] >= 0.5 else "bad"
        wheel_class = "good" if r["wheel_source"] != "none(unreliable)" else "bad"
        bright_shift_class = "warn" if abs(diag["brightness_shift"]) < 10 else "good"

        html_parts.append(f"""
<div class='metrics'>
  <div class='metric'><div class='metric-label'>检测结果</div><div class='metric-value {conf_class}'>{r['direction']} ({r['confidence']:.0%})</div></div>
  <div class='metric'><div class='metric-label'>期望方向</div><div class='metric-value'>left (车头向左)</div></div>
  <div class='metric'><div class='metric-label'>车轮检测</div><div class='metric-value {wheel_class}'>{r['wheel_source']}</div></div>
  <div class='metric'><div class='metric-label'>车身尺寸</div><div class='metric-value'>{diag['car_width']}×{diag['car_height']}</div></div>
  <div class='metric'><div class='metric-label'>底部轮廓幅度</div><div class='metric-value {'' if diag['bottom_range'] > diag['car_height']*0.05 else 'bad'}'>{diag['bottom_range']:.0f}px (车高{diag['car_height']*0.05:.0f}px阈值)</div></div>
  <div class='metric'><div class='metric-label'>亮度重心偏移</div><div class='metric-value {bright_shift_class}'>{diag['brightness_shift']:+.0f}px ({'偏左' if diag['brightness_shift']<0 else '偏右'})</div></div>
  <div class='metric'><div class='metric-label'>左/右悬垂</div><div class='metric-value'>{r['left_overhang']}/{r['right_overhang']}</div></div>
</div>""")

        # 诊断结论
        reasons = []
        if r["wheel_source"] == "none(unreliable)":
            reasons.append("• 车轮检测失败（底部轮廓+亮度都无法可靠检测车轮）")
        if diag["bottom_range"] < diag["car_height"] * 0.05:
            reasons.append(f"• 底部轮廓过于平坦（幅度{diag['bottom_range']:.0f}px<{diag['car_height']*0.05:.0f}px），无法定位车轮触地点")
        if r["wheel_source"] == "brightness" and r["direction"] != "left":
            reasons.append("• 亮度检测到车轮但方向判定错误，可能误将阴影/暗区识别为车轮")
        if abs(diag["brightness_shift"]) < 10:
            reasons.append(f"• 亮度重心偏移极小（{diag['brightness_shift']:.0f}px），亮度特征不可靠")
        else:
            if diag["brightness_shift"] > 0 and car["layout"] == "中置引擎":
                reasons.append(f"• 亮度重心偏右({diag['brightness_shift']:.0f}px)，但中置引擎车后部更亮（引擎盖），导致误判")

        valid_clusters = diag["valid_bottom_clusters"]
        if len(valid_clusters) < 2:
            reasons.append(f"• 底部轮廓只找到{len(valid_clusters)}个有效聚类（需要2个：前轮+后轮）")
        else:
            cluster_info = ", ".join([f"聚类{i+1}:x[{c[0]}-{c[1]}]宽{c[2]}" for i, c in enumerate(valid_clusters)])
            reasons.append(f"• 底部找到{len(valid_clusters)}个聚类：{cluster_info}")

        # 最终结论
        if "中置引擎" in car["layout"]:
            conclusion = "中置引擎超跑特征：底部轮廓不明显（无清晰车轮触地），亮度分布异常（后部引擎舱更亮），算法默认假设失效"
        elif "SUV" in car["layout"]:
            conclusion = "SUV特征：车身较高，底部阴影区域大，可能误检阴影为车轮"
        else:
            conclusion = "未知失败原因"

        html_parts.append(f"<div class='conclusion'>")
        html_parts.append(f"<div style='color:#f39c12;font-weight:bold;margin-bottom:5px'>诊断结论</div>")
        for reason in reasons:
            html_parts.append(f"<div style='color:#eee;margin-bottom:3px'>{reason}</div>")
        html_parts.append(f"<div style='color:#888;margin-top:10px;font-style:italic'>{conclusion}</div>")
        html_parts.append(f"</div>")

        # 可视化图表
        x_min, x_max = diag["x_min"], diag["x_max"]
        car_width = diag["car_width"]
        max_y = diag["arr_shape"][0]
        img_w = diag["img_size"][0]

        # 底部轮廓图
        html_parts.append(f"<div class='chart'>")
        html_parts.append(f"<div class='chart-title'>底部轮廓曲线 y_bottom(x)（红色虚线=车轮检测阈值 dip_threshold）</div>")
        html_parts.append(f"<canvas id='bottom_{car['brand']}_{car['model']}' width='800' height='200'></canvas>")
        html_parts.append(f"<script>")
        html_parts.append(f"""
(function(){{
  const canvas = document.getElementById('bottom_{car['brand']}_{car['model']}');
  const ctx = canvas.getContext('2d');
  const y_bottom = {json.dumps(diag['y_bottom'])};
  const x_min = {x_min}, x_max = {x_max};
  const max_y = {max_y};
  const dip_thr = {diag['dip_threshold']};
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  // 网格
  ctx.strokeStyle = '#333'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {{
    const y = H * i / 4;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }}
  // dip_threshold线
  ctx.strokeStyle = '#e74c3c'; ctx.setLineDash([5,5]);
  const y_dip = (dip_thr / max_y) * H;
  ctx.beginPath(); ctx.moveTo(0, y_dip); ctx.lineTo(W, y_dip); ctx.stroke();
  ctx.setLineDash([]);
  // 车身范围
  ctx.fillStyle = 'rgba(52,152,219,0.1)';
  ctx.fillRect((x_min/{img_w})*W, 0, ((x_max-x_min)/{img_w})*W, H);
  // 底部轮廓
  ctx.strokeStyle = '#2ecc71'; ctx.lineWidth = 2;
  ctx.beginPath();
  let first = true;
  for (let x = 0; x < y_bottom.length; x++) {{
    if (y_bottom[x] < 0) continue;
    const px = (x / {img_w}) * W;
    const py = (y_bottom[x] / max_y) * H;
    if (first) {{ ctx.moveTo(px, py); first = false; }}
    else ctx.lineTo(px, py);
  }}
  ctx.stroke();
  // 车轮聚类
  const clusters = {json.dumps(diag['valid_bottom_clusters'])};
  clusters.forEach((c, i) => {{
    const x0 = (c[0] / {img_w}) * W, x1 = (c[1] / {img_w}) * W;
    ctx.fillStyle = i === 0 ? 'rgba(231,76,60,0.4)' : 'rgba(243,156,18,0.4)';
    ctx.fillRect(x0, 0, x1 - x0, H);
  }});
}})();
""")
        html_parts.append(f"</script></div>")

        # 列亮度图
        html_parts.append(f"<div class='chart'>")
        html_parts.append(f"<div class='chart-title'>列亮度曲线（红色虚线=自适应阈值 median*0.7）</div>")
        html_parts.append(f"<canvas id='bright_{car['brand']}_{car['model']}' width='800' height='200'></canvas>")
        html_parts.append(f"<script>")
        html_parts.append(f"""
(function(){{
  const canvas = document.getElementById('bright_{car['brand']}_{car['model']}');
  const ctx = canvas.getContext('2d');
  const col_bright = {json.dumps(diag['col_brightness'])};
  const x_min = {x_min}, x_max = {x_max};
  const W = canvas.width, H = canvas.height;
  const adaptive_thr = {diag['adaptive_thr']};
  const median_b = {diag['median_brightness']};
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  // 网格
  ctx.strokeStyle = '#333';
  for (let i = 0; i <= 4; i++) {{
    const y = H * i / 4;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }}
  // 自适应阈值线
  ctx.strokeStyle = '#e74c3c'; ctx.setLineDash([5,5]);
  const y_thr = H - (adaptive_thr / 255) * H;
  ctx.beginPath(); ctx.moveTo(0, y_thr); ctx.lineTo(W, y_thr); ctx.stroke();
  // 中值线
  ctx.strokeStyle = '#888';
  const y_med = H - (median_b / 255) * H;
  ctx.beginPath(); ctx.moveTo(0, y_med); ctx.lineTo(W, y_med); ctx.stroke();
  ctx.setLineDash([]);
  // 车身范围
  ctx.fillStyle = 'rgba(52,152,219,0.1)';
  ctx.fillRect((x_min/{img_w})*W, 0, ((x_max-x_min)/{img_w})*W, H);
  // 亮度曲线
  ctx.strokeStyle = '#3498db'; ctx.lineWidth = 2;
  ctx.beginPath();
  let first = true;
  for (const [x, b] of col_bright) {{
    if (b < 0) {{ first = true; continue; }}
    const px = (x / {img_w}) * W;
    const py = H - (b / 255) * H;
    if (first) {{ ctx.moveTo(px, py); first = false; }}
    else ctx.lineTo(px, py);
  }}
  ctx.stroke();
  // 亮度重心
  const bc_x = ({diag['brightness_center']} / {img_w}) * W;
  const body_c_x = ({diag['body_center']} / {img_w}) * W;
  ctx.strokeStyle = '#f39c12'; ctx.lineWidth = 1; ctx.setLineDash([3,3]);
  ctx.beginPath(); ctx.moveTo(bc_x, 0); ctx.lineTo(bc_x, H); ctx.stroke();
  ctx.strokeStyle = '#888';
  ctx.beginPath(); ctx.moveTo(body_c_x, 0); ctx.lineTo(body_c_x, H); ctx.stroke();
  ctx.setLineDash([]);
}})();
""")
        html_parts.append(f"</script></div>")

        # 上轮廓图
        html_parts.append(f"<div class='chart'>")
        html_parts.append(f"<div class='chart-title'>上轮廓曲线 y_top(x)（橙色=车顶高位区域）</div>")
        html_parts.append(f"<canvas id='top_{car['brand']}_{car['model']}' width='800' height='200'></canvas>")
        html_parts.append(f"<script>")
        html_parts.append(f"""
(function(){{
  const canvas = document.getElementById('top_{car['brand']}_{car['model']}');
  const ctx = canvas.getContext('2d');
  const y_top = {json.dumps(diag['y_top'])};
  const x_min = {x_min}, x_max = {x_max};
  const max_y = {max_y};
  const y_min = {diag['car_bbox'][1]};
  const car_height = {diag['car_height']};
  const upper_thr = y_min + car_height * {DIRECTION_CONFIG['upper_ratio']};
  const W = canvas.width, H = canvas.height;
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = '#333';
  for (let i = 0; i <= 4; i++) {{
    const y = H * i / 4;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }}
  // upper_threshold线
  ctx.strokeStyle = '#f39c12'; ctx.setLineDash([5,5]);
  const y_thr = (upper_thr / max_y) * H;
  ctx.beginPath(); ctx.moveTo(0, y_thr); ctx.lineTo(W, y_thr); ctx.stroke();
  ctx.setLineDash([]);
  // 车身范围
  ctx.fillStyle = 'rgba(52,152,219,0.1)';
  ctx.fillRect((x_min/{img_w})*W, 0, ((x_max-x_min)/{img_w})*W, H);
  // 上轮廓
  ctx.strokeStyle = '#2ecc71'; ctx.lineWidth = 2;
  ctx.beginPath();
  let first = true;
  for (let x = 0; x < y_top.length; x++) {{
    if (y_top[x] > max_y) continue;
    const px = (x / {img_w}) * W;
    const py = (y_top[x] / max_y) * H;
    if (first) {{ ctx.moveTo(px, py); first = false; }}
    else ctx.lineTo(px, py);
  }}
  ctx.stroke();
}})();
""")
        html_parts.append(f"</script></div>")

        # 原图缩略图
        html_parts.append(f"<div class='chart'>")
        html_parts.append(f"<div class='chart-title'>原图（标注车辆边界框）</div>")
        html_parts.append(f"<img src='/_preview_diag_{car['brand']}_{car['model']}.jpg' style='max-width:100%;border:1px solid #333'/>")
        html_parts.append(f"</div>")

        html_parts.append("</div>")  # car-card

    html_parts.append("</body></html>")

    return "".join(html_parts)


def generate_preview_images(diags):
    """生成标注车辆边界框的预览图"""
    for diag in diags:
        if diag is None:
            continue
        car = diag["car"]
        img = Image.open(diag["img_path"]).convert("RGB")
        # 缩放到最大宽度800
        max_w = 800
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)))

        arr = np.array(img)
        # 画车辆边界框
        x_min = int(diag["car_bbox"][0] * img.width / diag["img_size"][0])
        y_min = int(diag["car_bbox"][1] * img.height / diag["img_size"][1])
        x_max = int(diag["car_bbox"][2] * img.width / diag["img_size"][0])
        y_max = int(diag["car_bbox"][3] * img.height / diag["img_size"][1])

        # 画框
        for y in range(y_min, min(y_min + 3, arr.shape[0])):
            for x in range(x_min, x_max + 1):
                arr[y, x] = [0, 255, 0]
        for y in range(max(y_max - 3, 0), y_max + 1):
            for x in range(x_min, x_max + 1):
                arr[y, x] = [0, 255, 0]
        for x in range(x_min, min(x_min + 3, arr.shape[1])):
            for y in range(y_min, y_max + 1):
                arr[y, x] = [0, 255, 0]
        for x in range(max(x_max - 3, 0), x_max + 1):
            for y in range(y_min, y_max + 1):
                arr[y, x] = [0, 255, 0]

        # 画亮度重心位置
        bc_x = int(diag["brightness_center"] * img.width / diag["img_size"][0])
        body_c_x = int(diag["body_center"] * img.width / diag["img_size"][0])
        # 黄色=亮度重心，白色=车身中心
        for y in range(0, arr.shape[0], 4):
            arr[y, bc_x] = [255, 200, 0]
            arr[y, body_c_x] = [255, 255, 255]

        # 画车轮检测聚类
        for i, c in enumerate(diag["valid_bottom_clusters"]):
            cx0 = int(c[0] * img.width / diag["img_size"][0])
            cx1 = int(c[1] * img.width / diag["img_size"][0])
            color = [255, 0, 0] if i == 0 else [255, 165, 0]
            for x in range(cx0, cx1 + 1):
                for y_off in [0, 1, 2]:
                    y_pos = arr.shape[0] - 1 - y_off
                    if y_pos >= 0:
                        arr[y_pos, x] = color

        Image.fromarray(arr).save(ROOT / "public" / f"_preview_diag_{car['brand']}_{car['model']}.jpg", quality=90)


def main():
    print("=" * 80)
    print("  方向检测失败车型诊断")
    print("=" * 80)

    diags = []
    for car in FAILED_CARS:
        print(f"\n  诊断 {car['brand']}/{car['model']} ({car['layout']})...")
        diag = diagnose_car(car)
        if diag:
            r = diag["result"]
            print(f"    检测结果: {r['direction']} (置信度 {r['confidence']:.0%})")
            print(f"    车轮源: {r['wheel_source']}")
            print(f"    底部幅度: {diag['bottom_range']:.0f}px")
            print(f"    亮度偏移: {diag['brightness_shift']:+.0f}px")
            print(f"    底部聚类数: {len(diag['valid_bottom_clusters'])}")
            diags.append(diag)
        else:
            print(f"    图片不存在")

    # 生成HTML报告
    html = generate_html_report(diags)
    out = ROOT / "public" / "_diagnose_failed_cars.html"
    out.write_text(html, encoding="utf-8")
    print(f"\n  HTML报告: http://localhost:5173/_diagnose_failed_cars.html")

    # 生成预览图
    generate_preview_images(diags)
    print(f"  预览图已生成")

    return 0


if __name__ == "__main__":
    sys.exit(main())
