# -*- coding: utf-8 -*-
"""gen_fix11_preview.py"""
import json, shutil
from pathlib import Path

TMP = Path(__file__).resolve().parent / "_fix11_tmp"
PUBLIC = Path(__file__).resolve().parent.parent / "public"

CARS = [
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

preview_dir = PUBLIC / "_fix11_preview"
preview_dir.mkdir(exist_ok=True)

car_data = []
for brand, model, name in CARS:
    prefix = f"{brand}_{model}"
    cands = []
    for f in sorted(TMP.glob(f"{prefix}*.jpg")):
        shutil.copy2(f, preview_dir / f.name)
        is_final = f.name == f"{prefix}.jpg"
        cands.append({"url": f"/_fix11_preview/{f.name}", "file": f.name, "is_final": is_final})
    cands.sort(key=lambda x: not x["is_final"])
    car_data.append({"brand": brand, "model": model, "name": name, "cands": cands})

html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>10款车新候选验证</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#e94560;font-weight:bold;font-size:16px;margin-bottom:10px}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:10px}
.cand-card{background:#0f0f1e;border:2px solid #333;border-radius:8px;overflow:hidden}
.cand-card.final{border-color:#e94560}
.cand-card img{width:100%;height:200px;object-fit:contain;background:#000;display:block;cursor:pointer}
.cand-label{padding:5px;font-size:10px;color:#888;text-align:center}
.cand-label .final{color:#e94560;font-weight:bold}
</style></head><body>
<h1>10款车新候选图视觉验证</h1>
<div class="sub">红框=子代理选定final | 点击放大 | 标准：正侧视+纯净背景+车型正确+无水印+非改装</div>
<div id="root"></div>
<script>
const DATA=""" + json.dumps(car_data, ensure_ascii=False) + """;
const root=document.getElementById('root');
DATA.forEach(car=>{
  const sec=document.createElement('div');sec.className='car-section';
  const t=document.createElement('div');t.className='car-title';
  t.textContent=car.name+' ('+car.cands.length+'张)';sec.appendChild(t);
  const g=document.createElement('div');g.className='cand-grid';
  car.cands.forEach(c=>{
    const card=document.createElement('div');
    card.className='cand-card'+(c.is_final?' final':'');
    const img=document.createElement('img');img.src=c.url;img.loading='lazy';
    img.onclick=()=>window.open(c.url,'_blank');
    img.onerror=()=>{card.style.opacity='0.3'};
    card.appendChild(img);
    const l=document.createElement('div');l.className='cand-label';
    l.innerHTML=c.is_final?'<span class="final">★ FINAL</span> '+c.file:c.file;
    card.appendChild(l);g.appendChild(card);
  });
  sec.appendChild(g);root.appendChild(sec);
});
</script></body></html>"""

(PUBLIC / "_preview_fix11.html").write_text(html, encoding="utf-8")
print("预览页: http://localhost:5173/_preview_fix11.html")
