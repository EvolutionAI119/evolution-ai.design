#!/usr/bin/env python3
"""
智能筛选 v15 候选图：背景纯净度 + 宽高比双重筛选
=====================================================
之前的问题：仅按宽高比和尺寸筛选，结果大量户外图、3/4角度图、内饰图混入。
正确方法：
  1. 背景纯净度分析：4角像素相似度、天空/草地/户外像素占比
  2. 宽高比强筛选：1.7-2.1（正侧视典型比例，排除3/4角度）
  3. 排除内饰图（棕色像素占比高 + 亮度低）
  4. 排除户外图（天空蓝/草地绿像素占比高）
输出聚焦预览页，只展示通过双重筛选的候选
"""
import json
from pathlib import Path
from PIL import Image
import io

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15"
OUT_HTML = BASE / "public" / "_preview_v15_smart.html"

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


def analyze_image_detailed(path):
    """详细分析图片：宽高比、背景纯净度、视角类型"""
    try:
        # 防止 DecompressionBombError
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(path) as im:
            w, h = im.size
            kb = path.stat().st_size // 1024
            asp = w / h if h > 0 else 0

            # 缩放为小图用于分析
            im_small = im.convert("RGB").resize((200, 150))
            pixels = list(im_small.getdata())
            W, H = 200, 150

            # 1. 亮度
            brightness = sum((r+g+b)/3 for r,g,b in pixels) / len(pixels)

            # 2. 4角+边缘像素差异（背景纯净度）
            corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),
                       (W//2,0),(W//2,H-1),(0,H//2),(W//2,H//2),
                       (W//4,0),(3*W//4,0),(W//4,H-1),(3*W//4,H-1)]
            corner_colors = [pixels[y*W+x] for x,y in corners]
            max_diff = max(
                max(c[i] for c in corner_colors) - min(c[i] for c in corner_colors)
                for i in range(3)
            )

            # 3. 天空像素（蓝色，b>r+30, b>g+10, b>150）
            sky = sum(1 for r,g,b in pixels if b > 150 and b > r + 30 and b > g + 10) / len(pixels)
            # 4. 草地像素（绿色，g>r+20, g>b+10, g>100）
            grass = sum(1 for r,g,b in pixels if g > 100 and g > r + 20 and g > b + 10) / len(pixels)
            # 5. 暗色像素（影棚暗背景）
            dark = sum(1 for r,g,b in pixels if (r+g+b)/3 < 50) / len(pixels)
            # 6. 亮色像素（白色影棚）
            light = sum(1 for r,g,b in pixels if (r+g+b)/3 > 220) / len(pixels)
            # 7. 棕色像素（内饰）
            brown = sum(1 for r,g,b in pixels if r > 80 and r < 200 and g > 50 and g < r and b < g and r - b > 30) / len(pixels)

            # 判断背景类型
            if brown > 0.20 and brightness < 130:
                bg_type = "interior"
                is_clean = False
            elif sky > 0.10 or grass > 0.08:
                bg_type = "outdoor"
                is_clean = False
            elif dark > 0.30:
                bg_type = "dark_studio"
                is_clean = max_diff < 60  # 暗色影棚，角像素差异小
            elif light > 0.30:
                bg_type = "white_studio"
                is_clean = max_diff < 60  # 白色影棚
            elif max_diff < 40:
                bg_type = "clean_bg"
                is_clean = True
            else:
                bg_type = "complex_bg"
                is_clean = False

            return {
                "w": w, "h": h, "kb": kb, "asp": asp,
                "brightness": brightness, "max_diff": max_diff,
                "sky": sky, "grass": grass, "dark": dark, "light": light, "brown": brown,
                "bg_type": bg_type, "is_clean": is_clean
            }
    except Exception as e:
        return None


def is_side_profile(asp, bg_info):
    """判断是否为正侧视：
    - 宽高比 1.7-2.1（正侧视典型比例）
    - 宽高比 1.5-1.7 也可能，但需更严格背景检查
    - 排除 < 1.4（通常是3/4角度或正面）
    """
    if asp < 1.4 or asp > 2.3:
        return False
    # 正侧视通常 1.6-2.1
    if 1.6 <= asp <= 2.1:
        return True
    return False


def is_qualified(asp, bg_info, w):
    """综合判断是否合格：
    1. 宽高比 1.6-2.1（正侧视）
    2. 背景纯净（影棚）
    3. 宽度 >= 800px
    4. 非内饰、非户外
    """
    if not is_side_profile(asp, bg_info):
        return False, "asp_out_of_range"
    if not bg_info["is_clean"]:
        return False, f"bg_{bg_info['bg_type']}"
    if w < 800:
        return False, "too_small"
    return True, "qualified"


# 生成 HTML
html_parts = ["""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>v15 智能筛选候选</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.summary{text-align:center;margin-bottom:20px;padding:10px;background:#16213e;border-radius:8px}
.car-block{margin-bottom:30px;border:1px solid #444;border-radius:10px;padding:15px;background:#16213e}
.car-title{font-size:18px;color:#e94560;font-weight:bold;margin-bottom:5px}
.car-info{color:#888;font-size:12px;margin-bottom:10px}
.candidates{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
.cand{background:#1a1a2e;border:2px solid #333;border-radius:6px;overflow:hidden}
.cand.qualified{border-color:#2ecc71}
.cand img{width:100%;height:160px;object-fit:contain;background:#000;display:block;cursor:pointer}
.cand .meta{padding:4px 6px;font-size:10px;color:#aaa}
.cand .fname{color:#e94560;font-weight:bold}
.cand .info{color:#888;margin-top:2px}
.cand .badge{display:inline-block;padding:1px 4px;border-radius:2px;font-size:9px;margin-left:3px}
.badge.qualified{background:#2ecc71;color:#fff}
.badge.outdoor{background:#e94560;color:#fff}
.badge.interior{background:#f39c12;color:#fff}
.badge.complex{background:#666;color:#fff}
.badge.studio{background:#3498db;color:#fff}
.big-view{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);z-index:1000;justify-content:center;align-items:center;flex-direction:column}
.big-view img{max-width:90%;max-height:80vh;object-fit:contain}
.big-view .close{position:absolute;top:20px;right:30px;color:#fff;font-size:30px;cursor:pointer}
.big-view .info{color:#fff;margin-top:10px;text-align:center}
</style></head><body>
<h1>v15 智能筛选候选（背景纯净+正侧视比例）</h1>
<div class="sub">绿色边框=通过双重筛选 | 点击图片查看大图 | 红色=户外 橙色=内饰 灰色=复杂背景</div>
<div id="root">
"""]

total_qualified = 0
total_analyzed = 0
summary_lines = []

for brand, model, name in CARS:
    car_dir = CAND_DIR / brand / model
    if not car_dir.exists():
        html_parts.append(f'<div class="car-block"><div class="car-title">{name}</div><div class="car-info">无候选目录</div></div>\n')
        continue

    qualified = []
    others = []
    for f in sorted(car_dir.glob("cand_*.jpg")):
        info = analyze_image_detailed(f)
        if not info:
            continue
        total_analyzed += 1
        ok, reason = is_qualified(info["asp"], info, info["w"])
        if ok:
            qualified.append((f.name, info))
            total_qualified += 1
        else:
            # 只保留可能接近的（宽高比1.4-2.3，排除明显不合格的）
            if 1.4 <= info["asp"] <= 2.3 and info["w"] >= 600:
                others.append((f.name, info, reason))

    summary_lines.append(f"{name}: {len(qualified)} 合格 / {len(others)} 边缘")
    html_parts.append(f'<div class="car-block">\n')
    html_parts.append(f'<div class="car-title">{name}</div>\n')
    html_parts.append(f'<div class="car-info">{len(qualified)} 张通过双重筛选 | {len(others)} 张边缘候选</div>\n')

    if not qualified and not others:
        html_parts.append('<div class="car-info" style="color:#e94560">无任何合格候选</div>\n')
        html_parts.append('</div>\n')
        continue

    html_parts.append('<div class="candidates">\n')
    # 先展示合格的
    for fname, info in qualified:
        url = f"/_candidates_v15/{brand}/{model}/{fname}"
        bg_badge = f'<span class="badge studio">{info["bg_type"]}</span>'
        html_parts.append(f'<div class="cand qualified">')
        html_parts.append(f'<img src="{url}" loading="lazy" onclick="showBig(\'{url}\',\'{fname}\')" onerror="this.parentElement.style.display=\'none\'">')
        html_parts.append(f'<div class="meta"><span class="fname">{fname}</span>')
        html_parts.append(f'<span class="badge qualified">✓合格</span>{bg_badge}</div>')
        html_parts.append(f'<div class="info">{info["w"]}x{info["h"]} asp={info["asp"]:.2f} diff={info["max_diff"]} {info["kb"]}KB</div></div>\n')

    # 再展示边缘的（按 max_diff 排序，差异小的在前）
    others.sort(key=lambda x: x[1]["max_diff"])
    for fname, info, reason in others[:8]:  # 最多展示8张边缘
        url = f"/_candidates_v15/{brand}/{model}/{fname}"
        if "outdoor" in reason:
            badge_class = "outdoor"
        elif "interior" in reason:
            badge_class = "interior"
        elif "complex" in reason:
            badge_class = "complex"
        else:
            badge_class = "complex"
        bg_badge = f'<span class="badge {badge_class}">{info["bg_type"]}</span>'
        html_parts.append(f'<div class="cand">')
        html_parts.append(f'<img src="{url}" loading="lazy" onclick="showBig(\'{url}\',\'{fname}\')" onerror="this.parentElement.style.display=\'none\'">')
        html_parts.append(f'<div class="meta"><span class="fname">{fname}</span>{bg_badge}</div>')
        html_parts.append(f'<div class="info">{info["w"]}x{info["h"]} asp={info["asp"]:.2f} diff={info["max_diff"]} {reason}</div></div>\n')
    html_parts.append('</div>\n</div>\n')

# 汇总
html_parts.append(f'<div class="summary">')
html_parts.append(f'<strong>汇总: {total_qualified}/{total_analyzed} 张通过双重筛选</strong><br>')
for line in summary_lines:
    html_parts.append(f'{line}<br>')
html_parts.append('</div>\n')

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
print(f"智能筛选完成: {total_qualified}/{total_analyzed} 张通过双重筛选")
print(f"预览页: {OUT_HTML}")
print(f"访问: http://localhost:5175/_preview_v15_smart.html")
print("\n各车型汇总:")
for line in summary_lines:
    print(f"  {line}")
