#!/usr/bin/env python3
"""
聚焦筛选9款不合格车型的候选图
================================
对每款车，按背景纯净度(max_diff)排序，展示前8张最纯净的候选
不限制宽高比（之前1.6-2.1太严格），只排除明显不合格的（户外/内饰）
"""
from pathlib import Path
from PIL import Image
import io

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15"
OUT_HTML = BASE / "public" / "_preview_9cars_focus.html"

# 剩余7款不合格车型（Bentley GTC和Flying Spur已完成）
CARS = [
    ["rolls-royce","ghost","Rolls-Royce Ghost","3/4角度→需正侧视"],
    ["rolls-royce","cullinan","Rolls-Royce Cullinan","易车水印→需无水印正侧视"],
    ["bentley","bentayga","Bentley Bentayga","展厅+后45度→需影棚正侧视"],
    ["bugatti","veyron","Bugatti Veyron","户外街道→需影棚图"],
    ["bugatti","divo","Bugatti Divo","微博水印→需无水印图"],
    ["ferrari","sf90","Ferrari SF90","易车水印→需无水印图"],
    ["ferrari","f8-tributo","Ferrari F8 Tributo","3/4角度→需正侧视"],
]


def analyze_image(path):
    try:
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(path) as im:
            w, h = im.size
            kb = path.stat().st_size // 1024
            asp = w / h if h > 0 else 0
            im_small = im.convert("RGB").resize((200, 150))
            pixels = list(im_small.getdata())
            W, H = 200, 150
            brightness = sum((r+g+b)/3 for r,g,b in pixels) / len(pixels)
            corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),
                       (W//2,0),(W//2,H-1),(0,H//2),(W//2,H//2)]
            corner_colors = [pixels[y*W+x] for x,y in corners]
            max_diff = max(
                max(c[i] for c in corner_colors) - min(c[i] for c in corner_colors)
                for i in range(3)
            )
            sky = sum(1 for r,g,b in pixels if b > 150 and b > r + 30 and b > g + 10) / len(pixels)
            grass = sum(1 for r,g,b in pixels if g > 100 and g > r + 20 and g > b + 10) / len(pixels)
            dark = sum(1 for r,g,b in pixels if (r+g+b)/3 < 50) / len(pixels)
            light = sum(1 for r,g,b in pixels if (r+g+b)/3 > 220) / len(pixels)
            brown = sum(1 for r,g,b in pixels if r > 80 and r < 200 and g > 50 and g < r and b < g and r - b > 30) / len(pixels)

            if brown > 0.20 and brightness < 130:
                bg_type = "interior"; is_outdoor = False
            elif sky > 0.10 or grass > 0.08:
                bg_type = "outdoor"; is_outdoor = True
            elif dark > 0.30:
                bg_type = "dark_studio"; is_outdoor = False
            elif light > 0.30:
                bg_type = "white_studio"; is_outdoor = False
            elif max_diff < 40:
                bg_type = "clean_bg"; is_outdoor = False
            else:
                bg_type = "complex"; is_outdoor = False

            return {"w": w, "h": h, "kb": kb, "asp": asp,
                    "brightness": brightness, "max_diff": max_diff,
                    "bg_type": bg_type, "is_outdoor": is_outdoor,
                    "sky": sky, "grass": grass, "dark": dark, "light": light}
    except Exception:
        return None


html_parts = ["""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>9车聚焦候选</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-block{margin-bottom:30px;border:2px solid #e94560;border-radius:10px;padding:15px;background:#16213e}
.car-title{font-size:18px;color:#e94560;font-weight:bold;margin-bottom:3px}
.car-need{color:#f39c12;font-size:12px;margin-bottom:10px}
.candidates{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:10px}
.cand{background:#1a1a2e;border:2px solid #333;border-radius:6px;overflow:hidden}
.cand.studio{border-color:#2ecc71}
.cand.outdoor{border-color:#e94560}
.cand img{width:100%;height:160px;object-fit:contain;background:#000;display:block;cursor:pointer}
.cand .meta{padding:4px 6px;font-size:10px;color:#aaa}
.cand .fname{color:#e94560;font-weight:bold}
.cand .info{color:#888;margin-top:2px}
.cand .badge{display:inline-block;padding:1px 4px;border-radius:2px;font-size:9px;margin-left:3px}
.badge.studio{background:#2ecc71;color:#fff}
.badge.outdoor{background:#e94560;color:#fff}
.badge.complex{background:#666;color:#fff}
.badge.interior{background:#f39c12;color:#fff}
.big-view{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);z-index:1000;justify-content:center;align-items:center;flex-direction:column}
.big-view img{max-width:90%;max-height:80vh;object-fit:contain}
.big-view .close{position:absolute;top:20px;right:30px;color:#fff;font-size:30px;cursor:pointer}
.big-view .info{color:#fff;margin-top:10px;text-align:center}
</style></head><body>
<h1>7款剩余车型 - 聚焦候选选择</h1>
<div class="sub">按背景纯净度排序 | 绿色=影棚 红色=户外 灰色=复杂 橙色=内饰 | 点击图片查看大图</div>
<div id="root">
"""]

for brand, model, name, need in CARS:
    car_dir = CAND_DIR / brand / model
    if not car_dir.exists():
        html_parts.append(f'<div class="car-block"><div class="car-title">{name}</div><div class="car-need">{need}</div><div style="color:#888">无候选目录</div></div>\n')
        continue

    # 分析所有候选
    all_cands = []
    for f in sorted(car_dir.glob("cand_*.jpg")):
        info = analyze_image(f)
        if not info:
            continue
        # 排除太小和明显非侧视的
        if info["w"] < 600 or info["asp"] < 1.2 or info["asp"] > 3.0:
            continue
        all_cands.append((f.name, info))

    # 排序：影棚优先，然后按max_diff升序
    all_cands.sort(key=lambda x: (x[1]["is_outdoor"], x[1]["max_diff"]))

    # 取前5张（减少浏览器验证负担）
    top_cands = all_cands[:5]

    html_parts.append(f'<div class="car-block">\n')
    html_parts.append(f'<div class="car-title">{name}</div>\n')
    html_parts.append(f'<div class="car-need">需要: {need} | 候选总数: {len(all_cands)} | 展示前5张</div>\n')

    if not top_cands:
        html_parts.append('<div style="color:#e94560">无可用候选</div>\n')
        html_parts.append('</div>\n')
        continue

    html_parts.append('<div class="candidates">\n')
    for fname, info in top_cands:
        url = f"/_candidates_v15/{brand}/{model}/{fname}"
        bg_type = info["bg_type"]
        if bg_type in ("dark_studio", "white_studio", "clean_bg"):
            border_class = "studio"
            badge_class = "studio"
        elif bg_type == "outdoor":
            border_class = "outdoor"
            badge_class = "outdoor"
        elif bg_type == "interior":
            border_class = ""
            badge_class = "interior"
        else:
            border_class = ""
            badge_class = "complex"

        html_parts.append(f'<div class="cand {border_class}">')
        html_parts.append(f'<img src="{url}" loading="lazy" onclick="showBig(\'{url}\',\'{fname}\')" onerror="this.parentElement.style.display=\'none\'">')
        html_parts.append(f'<div class="meta"><span class="fname">{fname}</span>')
        html_parts.append(f'<span class="badge {badge_class}">{bg_type}</span></div>')
        html_parts.append(f'<div class="info">{info["w"]}x{info["h"]} asp={info["asp"]:.2f} diff={info["max_diff"]} {info["kb"]}KB</div></div>\n')
    html_parts.append('</div>\n</div>\n')

html_parts.append("""</div>
<div class="big-view" id="bigView" onclick="this.style.display='none'">
  <span class="close">×</span>
  <img id="bigImg" src="">
  <div class="info" id="bigInfo"></div>
</div>
<script>
function showBig(url, fname){
  document.getElementById('bigImg').src=url;
  document.getElementById('bigInfo').textContent=fname;
  document.getElementById('bigView').style.display='flex';
}
</script>
</body></html>""")

OUT_HTML.write_text("".join(html_parts), encoding="utf-8")
print(f"聚焦筛选完成")
print(f"预览页: {OUT_HTML}")
print(f"访问: http://localhost:5175/_preview_9cars_focus.html")
