# -*- coding: utf-8 -*-
"""download_dailyrevs.py - 下载dailyrevs CDN图片并创建预览页"""
import hashlib, io, ssl, urllib.request, json
from pathlib import Path
from PIL import Image as P

CUR = Path(__file__).resolve().parent
TMP = CUR / "_dailyrevs_tmp"
TMP.mkdir(exist_ok=True)
PUBLIC = CUR.parent / "public"
PREVIEW = PUBLIC / "_dailyrevs_preview"
PREVIEW.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
CTX = ssl._create_unverified_context()

# 从dailyrevs.com WebFetch结果提取的CDN URL
CARS = {
    "Rolls-Royce Cullinan": [
        "maeiLSjAAl",  # xcar 正侧（左）
    ],
    "Bentley Flying Spur": [
        "mIYdouxyf2","47wjbqOZOh","NjQIvXe2eF","nNGBE6pEI8","2niKmlV7Ni",
        "iE7thF37cg","P56RbgU5ej","VZHU8KVKAo","vv55Hd7MlT","B5LwKsR7Te",
        "6tXE3ctF8c","HVtQ20Y77c","I7UyBTLoxa","eH6dKgOVj9","ltlXExVK5x",
        "Gq4eBJ6sTq","1zl3VQh2j4",
    ],
    "Bentley Bentayga": [
        "ZbeqELYK72","TZsOtwvNgx","lUUDH8UKvy","cgJ8W6sBMG","uwmvjCUMJe",
        "wLpaeNipOU","C7AA71pZxl","rttbu1ywtV","8ewbYRBu66","o69AxeFMtP",
        "fS1Q4ZAlZb",
    ],
    "Bugatti Divo": [
        "1tMT5Nuazl","x2a4ytzBJE","CeDOdyaTGG","5ihtgbgbF9","foap5bL7D6",
        "2OVTVhPmlP","ObyOuSFJvm","T4KMUkK6ue","a5ZILipUSg","hK5YqZSRfi",
        "jwJrJVSAAU","U0fsuiT6l7","U2xuFUNfup","S2uP2GpIeV","E32OCBNs3A",
        "XVJKUzgoOx","qSqObenVNL","3VeSUCVKf7","uWxqjEMRoi","OnQzNDQrtk",
        "4VGm5ppdRh","6OZtlCGdhZ",
    ],
    "Ferrari SF90": [
        "FdDvAE7FJH","qT2VP1zq9c","5eCzGUNR7z","CbWtdeFxot","APlDqSX61q",
        "oH4Ujny7qZ","88bom6eVDD","Hp1UgrsWQw","GOAboR21cs","nywyqaCuUh",
        "7lUs2Nr7lM","Aaodi5dWV2","4PrzVrNUun","v7vUQUZCwK","NKcgtjGk1J",
        "v2xmZ1e06m","4MASB9Otm6","NNOx5QXk7R","xy8yWW8R5d",
    ],
}


def download(cdn_id):
    url = f"https://aka.doubaocdn.com/s/{cdn_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.dailyrevs.com/"})
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=15) as r:
            return r.read()
    except Exception:
        return None


def analyze(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
            asp = w/h if h else 0
            im_s = im.convert("RGB").resize((200,150))
            px = list(im_s.getdata())
            W,H = 200,150
            corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),(0,H//2),(W-1,H//2)]
            cc = [px[y*W+x] for x,y in corners]
            max_diff = max(max(c[i] for c in cc)-min(c[i] for c in cc) for i in range(3))
            sky = sum(1 for r,g,b in px if b>150 and b>r+30 and b>g+10)/len(px)
            grass = sum(1 for r,g,b in px if g>100 and g>r+20 and g>b+10)/len(px)
            dark = sum(1 for r,g,b in px if (r+g+b)/3<50)/len(px)
            light = sum(1 for r,g,b in px if (r+g+b)/3>220)/len(px)
            return {"w":w,"h":h,"asp":round(asp,2),"max_diff":max_diff,
                    "sky":round(sky,3),"grass":round(grass,3),
                    "dark":round(dark,3),"light":round(light,3)}
    except Exception:
        return None


car_data = []
for car_name, ids in CARS.items():
    cands = []
    for i, cdn_id in enumerate(ids):
        raw = download(cdn_id)
        if not raw or len(raw) < 10000:
            print(f"  {car_name} #{i} {cdn_id}: 下载失败或太小")
            continue
        info = analyze(raw)
        if not info:
            continue
        fname = f"{car_name.replace(' ','_')}_{i:02d}_{cdn_id}.jpg"
        # 保存到preview目录
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=90)
            (PREVIEW / fname).write_bytes(bio.getvalue())
        cands.append({"url": f"/_dailyrevs_preview/{fname}", "id": cdn_id, **info})
        # 标记可能的正侧视（宽高比1.5-2.5 + 背景纯净）
        likely = "★" if (1.5 <= info["asp"] <= 2.5 and info["max_diff"] < 80 and info["sky"] < 0.1 and info["grass"] < 0.08) else ""
        print(f"  {car_name} #{i} {cdn_id}: {info['w']}x{info['h']} asp={info['asp']} diff={info['max_diff']} sky={info['sky']} {likely}")
    car_data.append({"name": car_name, "cands": cands})
    print(f"{car_name}: {len(cands)} 张下载成功\n")

# 生成预览页
html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>dailyrevs候选图扫描</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#e94560;font-weight:bold;font-size:16px;margin-bottom:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px}
.card{background:#0f0f1e;border:2px solid #333;border-radius:6px;overflow:hidden}
.card.likely{border-color:#2ecc71}
.card img{width:100%;height:160px;object-fit:contain;background:#000;display:block;cursor:pointer}
.info{padding:3px;font-size:9px;color:#888;text-align:center}
.info .likely{color:#2ecc71;font-weight:bold}
</style></head><body>
<h1>dailyrevs候选图视觉扫描</h1>
<div class="sub">绿框=可能正侧视(宽高比1.5-2.5+背景纯净) | 点击放大 | 找出真正的90°正侧视+纯净背景图</div>
<div id="root"></div>
<script>
const DATA=""" + json.dumps(car_data, ensure_ascii=False) + """;
const root=document.getElementById('root');
DATA.forEach(car=>{
  const sec=document.createElement('div');sec.className='car-section';
  const t=document.createElement('div');t.className='car-title';
  t.textContent=car.name+' ('+car.cands.length+'张)';sec.appendChild(t);
  const g=document.createElement('div');g.className='grid';
  car.cands.forEach(c=>{
    const likely=(c.asp>=1.5&&c.asp<=2.5&&c.max_diff<80&&c.sky<0.1&&c.grass<0.08);
    const card=document.createElement('div');
    card.className='card'+(likely?' likely':'');
    const img=document.createElement('img');img.src=c.url;img.loading='lazy';
    img.onclick=()=>window.open(c.url,'_blank');
    img.onerror=()=>{card.style.opacity='0.3'};
    card.appendChild(img);
    const info=document.createElement('div');info.className='info';
    info.innerHTML=(likely?'<span class="likely">★</span> ':'')+
      c.w+'x'+c.h+' asp='+c.asp+' diff='+c.max_diff+' '+c.id;
    card.appendChild(info);g.appendChild(card);
  });
  sec.appendChild(g);root.appendChild(sec);
});
</script></body></html>"""

(PUBLIC / "_preview_dailyrevs.html").write_text(html, encoding="utf-8")
print(f"\n预览页: http://localhost:5173/_preview_dailyrevs.html")
