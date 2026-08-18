#!/usr/bin/env python3
"""下载Bugatti Veyron官网图片 + 生成聚焦预览页"""
import urllib.request, ssl, os, json, hashlib, io
from PIL import Image

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

BASE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(BASE, "..", "public")
CAND_DIR = os.path.join(PUB, "_official_v18")

# Bugatti Veyron官网图片ID（从newsroom.bugatti.com和bugatti.com页面提取）
BUGATTI_VEYRON_IDS = [
    "hZhvvgfYC7",  # newsroom.bugatti.com - 15 years of Veyron
    "N7JhvRVXCK",  # bugatti.com - Bernar Venet
    "kBvLoetX3q",  # bugatti.com - L'Or Blanc
    "iwxLyMLEbD",  # newsroom.bugatti.com - social media
    "me2bjdxqGz",  # newsroom.bugatti.com - 15 years began
    "BcoabLqmmV",  # newsroom.bugatti.com - social media
    "4NlBKuwlL6",  # newsroom.bugatti.com - Targa Florio
    "3bWtOjzfY9",  # bugatti.com - Veyron technology
]

def download_cdn(cdn_id, referer="https://www.bugatti.com/en/classic-icons/veyron-164"):
    url = f"https://aka.doubaocdn.com/s/{cdn_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
            return r.read()
    except Exception as e:
        print(f"  ERR {cdn_id}: {e}")
        return None

def analyze(raw):
    try:
        with Image.open(io.BytesIO(raw)) as im:
            w, h = im.size
            md5 = hashlib.md5(raw).hexdigest()[:12]
            asp = round(w / h, 2) if h else 0
            im_s = im.convert("RGB").resize((200, 150))
            px = list(im_s.getdata())
            W, H = 200, 150
            corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),(0,H//2),(W-1,H//2)]
            cc = [px[y*W+x] for x,y in corners]
            max_diff = max(max(c[i] for c in cc)-min(c[i] for c in cc) for i in range(3))
            dark = sum(1 for r,g,b in px if (r+g+b)/3<50)/len(px)
            light = sum(1 for r,g,b in px if (r+g+b)/3>220)/len(px)
            sky = sum(1 for r,g,b in px if b>150 and b>r+30 and b>g+10)/len(px)
            if max_diff < 25 and dark > 0.5: bg = "dark_studio"
            elif max_diff < 25 and light > 0.5: bg = "white_studio"
            elif sky > 0.1: bg = "outdoor"
            else: bg = "complex"
            return {"w":w,"h":h,"asp":asp,"md5":md5,"kb":round(len(raw)/1024),
                    "max_diff":max_diff,"dark":round(dark,3),"light":round(light,3),
                    "sky":round(sky,3),"bg_type":bg}
    except Exception as e:
        return {"error": str(e)}

def main():
    car_dir = os.path.join(CAND_DIR, "bugatti", "veyron")
    os.makedirs(car_dir, exist_ok=True)
    
    print("下载Bugatti Veyron官网图片...")
    images = []
    for i, cdn_id in enumerate(BUGATTI_VEYRON_IDS, 1):
        print(f"  [{i}] {cdn_id} ...", end=" ")
        raw = download_cdn(cdn_id)
        if raw:
            info = analyze(raw)
            if "error" not in info:
                fname = f"cand_{i:02d}.jpg"
                with open(os.path.join(car_dir, fname), "wb") as f:
                    f.write(raw)
                images.append({"file": fname, "source": f"cdn:{cdn_id}", **info})
                print(f"OK {info['w']}x{info['h']} asp={info['asp']} bg={info['bg_type']} {info['kb']}KB")
            else:
                print(f"ERR: {info['error']}")
        else:
            print("FAIL")
    
    print(f"\n共下载 {len(images)} 张Bugatti Veyron图片")
    
    # 更新日志
    log_path = os.path.join(BASE, "_official_v18_log.json")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
        for car in log:
            if car["car"] == "bugatti/veyron":
                car["images"] = images
                car["total"] = len(images)
                break
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    
    # 重新生成预览页
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
        gen_preview(log)
        print("预览页已更新")

def gen_preview(log):
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>官网图片候选验证 v18</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{margin-bottom:30px;background:#16213e;border-radius:10px;padding:15px}
.car-title{color:#e94560;font-size:18px;font-weight:bold;margin-bottom:5px}
.car-source{color:#888;font-size:11px;margin-bottom:10px;word-break:break-all}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.cand-card{background:#0f0f1e;border:2px solid #333;border-radius:8px;overflow:hidden;cursor:pointer;transition:border-color 0.2s}
.cand-card:hover{border-color:#e94560}
.cand-card img{width:100%;height:180px;object-fit:contain;background:#000;display:block}
.cand-label{padding:6px 8px;font-size:11px;color:#aaa}
.tag{display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;margin-right:3px}
.tag.asp-ok{background:#2ecc71;color:#000}
.tag.asp-bad{background:#e94560;color:#fff}
.tag.bg-ok{background:#2ecc71;color:#000}
.tag.bg-bad{background:#e94560;color:#fff}
</style></head><body>
<h1>官网图片候选验证 v18</h1>
<div class="sub">来源：品牌官网 | 标准：正侧视(90°) + 纯净背景(影棚) + 车型正确 + 无水印 + 非改装<br>点击图片放大查看</div>
<div id="root"></div>
<script>
const DATA = """ + json.dumps(log, ensure_ascii=False) + """;
const root = document.getElementById('root');
DATA.forEach(car => {
  const sec = document.createElement('div');
  sec.className = 'car-section';
  const t = document.createElement('div');
  t.className = 'car-title';
  t.textContent = car.name + ' (' + car.total + '张)';
  sec.appendChild(t);
  const src = document.createElement('div');
  src.className = 'car-source';
  src.textContent = '官网: ' + car.official_page;
  sec.appendChild(src);
  const g = document.createElement('div');
  g.className = 'cand-grid';
  car.images.forEach(c => {
    const card = document.createElement('div');
    card.className = 'cand-card';
    const img = document.createElement('img');
    const imgPath = '/_official_v18/' + car.car + '/' + c.file;
    img.src = imgPath;
    img.loading = 'lazy';
    img.onclick = () => window.open(imgPath, '_blank');
    img.onerror = () => { img.style.display='none'; };
    card.appendChild(img);
    const l = document.createElement('div');
    l.className = 'cand-label';
    const aspOk = c.asp >= 1.2 && c.asp <= 2.5;
    const bgOk = c.bg_type === 'dark_studio' || c.bg_type === 'white_studio';
    l.innerHTML = `${c.file} ${c.w}x${c.h} ${c.kb}KB ` +
      `<span class="tag ${aspOk?'asp-ok':'asp-bad'}">asp=${c.asp}</span>` +
      `<span class="tag ${bgOk?'bg-ok':'bg-bad'}">${c.bg_type}</span>`;
    card.appendChild(l);
    g.appendChild(card);
  });
  sec.appendChild(g);
  root.appendChild(sec);
});
</script></body></html>"""
    with open(os.path.join(PUB, "_preview_official_v18.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
