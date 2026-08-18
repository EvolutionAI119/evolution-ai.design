"""分析候选图过滤失败的原因"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from car_image_filter_pipeline import (
    analyze_background, detect_complete_car,
    WHITE_BG_CONFIG, COMPLETE_CAR_CONFIG
)

ROOT = Path(__file__).resolve().parent.parent

CARS = [
    {"brand": "bugatti", "model": "divo", "name": "Bugatti Divo"},
    {"brand": "bugatti", "model": "veyron", "name": "Bugatti Veyron"},
]


def main():
    print("=" * 100)
    print("  候选图过滤失败原因分析")
    print("=" * 100)

    for car in CARS:
        brand, model = car["brand"], car["model"]
        name = car["name"]
        car_dir = ROOT / "public" / "_bing_v2_candidates" / f"{brand}__{model}"

        if not car_dir.exists():
            print(f"\n  {name}: 目录不存在")
            continue

        imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
        print(f"\n  {name}: {len(imgs)}张")

        # 统计失败原因
        reason_counts = {}
        for img_path in imgs:
            try:
                with Image.open(img_path) as im:
                    arr = np.array(im.convert("RGB"))
                info = analyze_background(arr, WHITE_BG_CONFIG)
                if info["pass"]:
                    reason = "PASS"
                else:
                    reason = " + ".join(info["reasons"][:2])  # 只取前2个原因
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            except Exception as e:
                reason = f"ERR: {e}"
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

        # 显示原因分布
        print(f"    失败原因分布:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"      {count:3d}张: {reason[:100]}")

        # 找最接近通过的几张（白色占比最高的）
        closest = []
        for img_path in imgs:
            try:
                with Image.open(img_path) as im:
                    arr = np.array(im.convert("RGB"))
                info = analyze_background(arr, WHITE_BG_CONFIG)
                closest.append((img_path, info))
            except Exception:
                continue
        closest.sort(key=lambda x: -x[1]["white_ratio"])

        print(f"\n    白色占比最高的5张:")
        for i, (img_path, info) in enumerate(closest[:5]):
            h, w = info["w"], info["h"]
            print(f"      [{i+1}] {img_path.name}: "
                  f"白{info['white_ratio']:.0f}% 亮度{info['brightness']:.0f} "
                  f"角std{info['corner_std']:.0f} 角差{info['corner_brightness_diff']:.0f} "
                  f"尺寸{w}×{h} asp{info['asp']:.2f}")
            if info["reasons"] != ["ALL PASS"]:
                print(f"          原因: {', '.join(info['reasons'])}")

    # 生成HTML预览
    print("\n  生成HTML预览...")
    generate_html_preview()
    print("  HTML: http://localhost:5173/_candidates_failed_analysis.html")


def generate_html_preview():
    """生成候选图预览，方便人工查看"""
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>候选图分析</title>",
        "<style>",
        "body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}",
        "h1{text-align:center;color:#f39c12}",
        ".car-section{background:#16213e;border-radius:10px;padding:15px;margin-bottom:30px}",
        ".car-title{color:#3498db;font-size:20px;margin-bottom:10px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}",
        ".cand{background:#1a1a2e;border-radius:5px;overflow:hidden}",
        ".cand img{width:100%;height:140px;object-fit:contain;background:#fff;display:block}",
        ".cand-info{padding:5px;font-size:11px}",
        ".pass{color:#2ecc71} .fail{color:#e74c3c} .reason{color:#888}",
        "</style></head><body>",
        "<h1>3款中置引擎超跑候选图分析</h1>",
    ]

    for car in CARS:
        brand, model = car["brand"], car["model"]
        name = car["name"]
        car_dir = ROOT / "public" / "_bing_v2_candidates" / f"{brand}__{model}"

        html_parts.append(f"<div class='car-section'>")
        html_parts.append(f"<div class='car-title'>{name}</div>")
        html_parts.append(f"<div class='grid'>")

        if car_dir.exists():
            imgs = sorted(list(car_dir.glob("*.jpg")) + list(car_dir.glob("*.png")))
            # 按白色占比排序
            scored = []
            for img_path in imgs:
                try:
                    with Image.open(img_path) as im:
                        arr = np.array(im.convert("RGB"))
                    info = analyze_background(arr, WHITE_BG_CONFIG)
                    scored.append((img_path, info))
                except Exception:
                    continue
            scored.sort(key=lambda x: -x[1]["white_ratio"])

            for img_path, info in scored:
                rel_path = f"/_bing_v2_candidates/{brand}__{model}/{img_path.name}"
                status = "pass" if info["pass"] else "fail"
                status_icon = "✅" if info["pass"] else "❌"
                reasons = ", ".join(info["reasons"][:2]) if info["reasons"] != ["ALL PASS"] else "PASS"
                html_parts.append(f"""
<div class='cand'>
  <img src='{rel_path}' loading='lazy' onclick='window.open(this.src)'>
  <div class='cand-info'>
    <span class='{status}'>{status_icon} 白{info['white_ratio']:.0f}% 亮{info['brightness']:.0f}</span><br>
    <span class='reason'>{img_path.name} {info['w']}×{info['h']}</span><br>
    <span class='reason'>{reasons}</span>
  </div>
</div>""")
        else:
            html_parts.append("<div>目录不存在</div>")

        html_parts.append("</div></div>")

    html_parts.append("</body></html>")
    out = ROOT / "public" / "_candidates_failed_analysis.html"
    out.write_text("".join(html_parts), encoding="utf-8")


if __name__ == "__main__":
    main()
