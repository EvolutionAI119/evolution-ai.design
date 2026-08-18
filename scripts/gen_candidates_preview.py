# -*- coding: utf-8 -*-
"""gen_candidates_preview.py
统计11款不合格车的所有候选图，生成预览页供视觉筛选。
"""
import json
from pathlib import Path

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

# 收集每款车的候选图
car_data = []
for brand, model, name in CARS:
    cands = []
    for d in CAND_DIRS:
        car_dir = PUBLIC / d / brand / model
        if not car_dir.exists():
            continue
        for f in sorted(car_dir.glob("*.jpg")):
            rel = f"/{d}/{brand}/{model}/{f.name}"
            cands.append({"url": rel, "dir": d, "file": f.name})
    car_data.append({"brand": brand, "model": model, "name": name, "cands": cands})
    print(f"{name}: {len(cands)} candidates")

# 生成预览页
html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>11款不合格车候选图筛选</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#e94560;font-weight:bold;font-size:16px;margin-bottom:10px}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.cand-card{background:#0f0f1e;border:2px solid #333;border-radius:8px;overflow:hidden;cursor:pointer;transition:border-color 0.2s}
.cand-card:hover{border-color:#e94560}
.cand-card.selected{border-color:#2ecc71}
.cand-card img{width:100%;height:160px;object-fit:contain;background:#000;display:block}
.cand-label{padding:5px;font-size:10px;color:#888;text-align:center}
.cand-label .src{color:#e94560}
.current{background:#1a1a2e;border:2px dashed #e94560;border-radius:8px;padding:10px;margin-bottom:10px}
.current img{width:100%;height:180px;object-fit:contain;background:#000;border-radius:6px}
.current-label{color:#e94560;font-size:12px;text-align:center;margin-top:5px}
</style></head><body>
<h1>11款不合格车候选图视觉筛选</h1>
<div class="sub">标准：正侧视(90°) + 纯净背景(影棚) + 车型正确 + 无水印 | 点击选中 → 记录最佳候选</div>
<div id="root"></div>
<div id="result" style="margin-top:20px;padding:15px;background:#16213e;border-radius:8px;white-space:pre-wrap;font-size:12px"></div>
<script>
const DATA = """ + json.dumps(car_data, ensure_ascii=False) + """;

const selected = {};

function build() {
  const root = document.getElementById('root');
  DATA.forEach(car => {
    const sec = document.createElement('div');
    sec.className = 'car-section';

    const title = document.createElement('div');
    title.className = 'car-title';
    title.textContent = `${car.name} (${car.cands.length} 候选)`;
    sec.appendChild(title);

    // 当前部署的图
    const cur = document.createElement('div');
    cur.className = 'current';
    const curImg = document.createElement('img');
    curImg.src = `/brands/${car.brand}/${car.model}.jpg`;
    curImg.onerror = () => { curImg.style.display='none'; };
    cur.appendChild(curImg);
    const curLabel = document.createElement('div');
    curLabel.className = 'current-label';
    curLabel.textContent = '当前部署(不合格)';
    cur.appendChild(curLabel);
    sec.appendChild(cur);

    // 候选图
    const grid = document.createElement('div');
    grid.className = 'cand-grid';
    car.cands.forEach(c => {
      const card = document.createElement('div');
      card.className = 'cand-card';
      const img = document.createElement('img');
      img.src = c.url;
      img.loading = 'lazy';
      img.onerror = () => { card.style.display='none'; };
      card.appendChild(img);
      const label = document.createElement('div');
      label.className = 'cand-label';
      label.innerHTML = `<span class="src">${c.dir}</span> ${c.file}`;
      card.appendChild(label);
      card.onclick = () => {
        card.classList.toggle('selected');
        if (card.classList.contains('selected')) {
          selected[`${car.brand}/${car.model}`] = c.url;
        } else {
          delete selected[`${car.brand}/${car.model}`];
        }
        updateResult();
      };
      grid.appendChild(card);
    });
    sec.appendChild(grid);
    root.appendChild(sec);
  });
}

function updateResult() {
  const el = document.getElementById('result');
  const lines = ['选中结果：'];
  for (const [k,v] of Object.entries(selected)) {
    lines.push(`${k} → ${v}`);
  }
  lines.push(`\\n共选中 ${Object.keys(selected).length}/11`);
  el.textContent = lines.join('\\n');
}

build();
updateResult();
</script></body></html>"""

out = PUBLIC / "_preview_11candidates.html"
out.write_text(html, encoding="utf-8")
print(f"\n预览页已生成: {out}")
print(f"访问: http://localhost:5173/_preview_11candidates.html")
