# -*- coding: utf-8 -*-
"""filter_top_candidates.py
对11款不合格车的所有候选图进行像素分析+MD5去重，选出每款top 8候选，
生成聚焦预览页供人工视觉验证。
"""
import hashlib, io, json
from pathlib import Path
from PIL import Image as P

CUR = Path(__file__).resolve().parent
PROJECT = CUR.parent
PUBLIC = PROJECT / "public"

CARS = [
    ("rolls-royce", "ghost",           "Rolls-Royce Ghost"),
    ("rolls-royce", "cullinan",        "Rolls-Royce Cullinan"),
    ("bentley",     "continental-gtc", "Bentley Continental GTC"),
    ("bentley",     "flying-spur",     "Bentley Flying Spur"),
    ("bentley",     "bentayga",        "Bentley Bentayga"),
    ("bugatti",     "veyron",          "Bugatti Veyron"),
    ("bugatti",     "divo",            "Bugatti Divo"),
    ("porsche",     "cayenne",         "Porsche Cayenne"),
    ("porsche",     "macan",           "Porsche Macan"),
    ("ferrari",     "sf90",            "Ferrari SF90"),
    ("ferrari",     "f8-tributo",      "Ferrari F8 Tributo"),
]

CAND_DIRS = ["_candidates_v13", "_candidates_v14", "_candidates_v12", "_candidates", "_best_v13"]
P.MAX_IMAGE_PIXELS = None


def analyze(path):
    try:
        raw = path.read_bytes()
        md5 = hashlib.md5(raw).hexdigest()[:12]
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
            asp = w / h if h else 0
            kb = len(raw) // 1024
            im_s = im.convert("RGB").resize((200, 150))
            px = list(im_s.get_flattened_data() if hasattr(im_s, 'get_flattened_data') else im_s.getdata())
            W, H = 200, 150
            # 4角+边缘像素差异
            corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),(0,H//2),(W-1,H//2)]
            cc = [px[y*W+x] for x,y in corners]
            max_diff = max(max(c[i] for c in cc)-min(c[i] for c in cc) for i in range(3))
            sky = sum(1 for r,g,b in px if b>150 and b>r+30 and b>g+10)/len(px)
            grass = sum(1 for r,g,b in px if g>100 and g>r+20 and g>b+10)/len(px)
            dark = sum(1 for r,g,b in px if (r+g+b)/3<50)/len(px)
            light = sum(1 for r,g,b in px if (r+g+b)/3>220)/len(px)
            brown = sum(1 for r,g,b in px if 80<r<200 and 50<g<r and b<g and r-b>30)/len(px)

            # 判断背景类型
            if brown > 0.20:
                bg_type = "interior"
                bg_score = -100
            elif sky > 0.10 or grass > 0.08:
                bg_type = "outdoor"
                bg_score = -50
            elif dark > 0.30:
                bg_type = "dark_studio"
                bg_score = 100 - max_diff
            elif light > 0.30:
                bg_type = "white_studio"
                bg_score = 100 - max_diff
            elif max_diff < 40:
                bg_type = "clean_bg"
                bg_score = 100 - max_diff
            else:
                bg_type = "complex"
                bg_score = -max_diff

            # 综合评分：宽高比接近1.8(正侧视典型) + 背景纯净 + 尺寸大
            asp_score = 0
            if 1.6 <= asp <= 2.2:
                asp_score = 50
            elif 1.4 <= asp <= 2.5:
                asp_score = 20

            size_score = min(kb / 10, 50)  # 最大50分，每10KB得1分

            total = bg_score + asp_score + size_score

            return {
                "w": w, "h": h, "asp": round(asp, 2), "kb": kb, "md5": md5,
                "max_diff": max_diff, "sky": round(sky, 3), "grass": round(grass, 3),
                "dark": round(dark, 3), "light": round(light, 3),
                "bg_type": bg_type, "bg_score": round(bg_score, 1),
                "asp_score": asp_score, "size_score": round(size_score, 1),
                "total": round(total, 1),
            }
    except Exception as e:
        return None


car_results = []
for brand, model, name in CARS:
    all_cands = []
    seen_md5 = set()
    for d in CAND_DIRS:
        car_dir = PUBLIC / d / brand / model
        if not car_dir.exists():
            continue
        for f in sorted(car_dir.glob("*.jpg")):
            info = analyze(f)
            if not info:
                continue
            if info["md5"] in seen_md5:
                continue
            seen_md5.add(info["md5"])
            rel = f"/{d}/{brand}/{model}/{f.name}"
            all_cands.append({"url": rel, "dir": d, "file": f.name, **info})

    # 按总分排序，取top 8
    all_cands.sort(key=lambda x: x["total"], reverse=True)
    top = all_cands[:8]
    car_results.append({"brand": brand, "model": model, "name": name, "total": len(all_cands), "top": top})
    print(f"{name}: {len(all_cands)}去重后 → top8 最高分={top[0]['total'] if top else 'N/A'}")

# 生成预览页
html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>11款车 Top8候选视觉筛选</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#e94560;font-weight:bold;font-size:16px;margin-bottom:10px}
.cand-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.cand-card{background:#0f0f1e;border:2px solid #333;border-radius:8px;overflow:hidden}
.cand-card img{width:100%;height:140px;object-fit:contain;background:#000;display:block;cursor:pointer}
.cand-info{padding:4px;font-size:9px;color:#aaa;text-align:center}
.cand-info .score{color:#2ecc71;font-weight:bold}
.cand-info .bg{color:#e94560}
.cand-info .asp{color:#f0a030}
</style></head><body>
<h1>11款车 Top8候选视觉筛选</h1>
<div class="sub">已按 背景纯净度+宽高比+尺寸 评分排序 | 请人工确认：正侧视+车型正确+无水印</div>
<div id="root"></div>
<script>
const DATA = """ + json.dumps(car_results, ensure_ascii=False) + """;
const root = document.getElementById('root');
DATA.forEach(car => {
  const sec = document.createElement('div');
  sec.className = 'car-section';
  const title = document.createElement('div');
  title.className = 'car-title';
  title.textContent = `${car.name} (${car.total}去重候选, 展示top8)`;
  sec.appendChild(title);
  const grid = document.createElement('div');
  grid.className = 'cand-grid';
  car.top.forEach((c, i) => {
    const card = document.createElement('div');
    card.className = 'cand-card';
    const img = document.createElement('img');
    img.src = c.url;
    img.loading = 'lazy';
    img.onclick = () => window.open(c.url, '_blank');
    img.onerror = () => { card.style.opacity = '0.3'; };
    card.appendChild(img);
    const info = document.createElement('div');
    info.className = 'cand-info';
    info.innerHTML = `#${i+1} <span class="score">${c.total}</span> <span class="bg">${c.bg_type}</span> <span class="asp">${c.asp}</span> ${c.w}x${c.h}`;
    card.appendChild(info);
    grid.appendChild(card);
  });
  sec.appendChild(grid);
  root.appendChild(sec);
});
</script></body></html>"""

out = PUBLIC / "_preview_11_top8.html"
out.write_text(html, encoding="utf-8")
print(f"\n预览页: http://localhost:5173/_preview_11_top8.html")

# 保存分析结果
(CUR / "_filter_top8_log.json").write_text(json.dumps(car_results, indent=2, ensure_ascii=False), encoding="utf-8")
