#!/usr/bin/env python3
"""预筛 v15 候选图：按宽高比和尺寸过滤，创建聚焦预览页"""
import json
from pathlib import Path
from PIL import Image
import io

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15"
OUT_HTML = BASE / "public" / "_preview_v15_filtered.html"

CARS = [
    ["rolls-royce","ghost","Rolls-Royce Ghost"],
    ["rolls-royce","cullinan","Rolls-Royce Cullinan"],
    ["bugatti","chiron","Bugatti Chiron"],
    ["bugatti","veyron","Bugatti Veyron"],
    ["bugatti","divo","Bugatti Divo"],
    ["bentley","continental-gt","Bentley Continental GT"],
    ["bentley","continental-gtc","Bentley Continental GTC"],
    ["bentley","flying-spur","Bentley Flying Spur"],
    ["bentley","bentayga","Bentley Bentayga"],
    ["porsche","taycan","Porsche Taycan"],
    ["ferrari","sf90","Ferrari SF90"],
    ["ferrari","f8-tributo","Ferrari F8 Tributo"],
    ["ferrari","roma","Ferrari Roma"],
]

def analyze_image(path):
    try:
        with Image.open(path) as im:
            w, h = im.size
            kb = path.stat().st_size // 1024
            asp = w / h if h > 0 else 0
            return w, h, kb, asp
    except Exception:
        return None

# 预筛条件：宽高比 1.4-2.3（横向，可能为侧视），宽度>=600，大小>=30KB
def is_promising(w, h, kb, asp):
    if asp < 1.4 or asp > 2.3:
        return False
    if w < 600:
        return False
    if kb < 30:
        return False
    return True

html_parts = ["""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>v15 预筛候选</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-block{margin-bottom:30px;border:1px solid #444;border-radius:10px;padding:15px;background:#16213e}
.car-title{font-size:18px;color:#e94560;font-weight:bold;margin-bottom:5px}
.car-info{color:#888;font-size:12px;margin-bottom:10px}
.candidates{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.cand{background:#1a1a2e;border:2px solid #333;border-radius:6px;overflow:hidden}
.cand img{width:100%;height:140px;object-fit:contain;background:#000;display:block}
.cand .meta{padding:4px 6px;font-size:10px;color:#aaa}
.cand .fname{color:#e94560;font-weight:bold}
.cand .dims{color:#0f3460;background:#eee;padding:1px 3px;border-radius:2px;margin-left:4px}
.good{border-color:#2ecc71}
</style></head><body>
<h1>v15 预筛候选（宽高比 1.4-2.3）</h1>
<div class="sub">已按宽高比和尺寸预筛 | 绿色边框=宽高比 1.6-2.1（更可能是正侧视）</div>
<div id="root">
"""]

total_promising = 0
total_all = 0

for brand, model, name in CARS:
    car_dir = CAND_DIR / brand / model
    if not car_dir.exists():
        html_parts.append(f'<div class="car-block"><div class="car-title">{name}</div><div class="car-info">无候选目录</div></div>\n')
        continue

    cands = []
    for f in sorted(car_dir.glob("cand_*.jpg")):
        info = analyze_image(f)
        if not info:
            continue
        total_all += 1
        w, h, kb, asp = info
        if is_promising(w, h, kb, asp):
            cands.append((f.name, w, h, kb, asp))
            total_promising += 1

    html_parts.append(f'<div class="car-block">\n')
    html_parts.append(f'<div class="car-title">{name}</div>\n')
    html_parts.append(f'<div class="car-info">{len(cands)} 张预筛候选</div>\n')

    if not cands:
        html_parts.append('<div class="car-info" style="color:#e94560">无合格预筛候选</div>\n')
        html_parts.append('</div>\n')
        continue

    html_parts.append('<div class="candidates">\n')
    for fname, w, h, kb, asp in cands:
        good_class = " good" if 1.6 <= asp <= 2.1 else ""
        url = f"/_candidates_v15/{brand}/{model}/{fname}"
        html_parts.append(f'<div class="cand{good_class}">')
        html_parts.append(f'<img src="{url}" loading="lazy" onerror="this.parentElement.style.display=\'none\'">')
        html_parts.append(f'<div class="meta"><span class="fname">{fname}</span>')
        html_parts.append(f'<span class="dims">{w}x{h} asp={asp:.2f} {kb}KB</span></div></div>\n')
    html_parts.append('</div>\n</div>\n')

html_parts.append("</div></body></html>")

OUT_HTML.write_text("".join(html_parts), encoding="utf-8")
print(f"预筛完成: {total_promising}/{total_all} 张候选通过预筛")
print(f"预览页: {OUT_HTML}")
print(f"访问: http://localhost:5176/_preview_v15_filtered.html")
