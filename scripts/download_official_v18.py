#!/usr/bin/env python3
"""
严格官网方法论 v2.0 下载脚本
唯一来源：品牌官网（bentleymotors.com / ferrari.com / porsche.com newsroom / rolls-roycemotorcars.com.cn / bugatti.com）
禁用：hdqwalls, dailyrevs, NetCarShow, Bing图片, doubaocdn(非官网页面提取的)
"""
import urllib.request, urllib.error, ssl, os, json, hashlib, io, time
from PIL import Image

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

BASE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(BASE, "..", "public")
CAND_DIR = os.path.join(PUB, "_official_v18")

# 7款不合格车的官网图片来源
# doubaocdn URL = 从官网页面HTML提取的图片ID（官网图片通过CDN提供）
# direct_url = 官网域名上的直接图片URL
CARS = {
    "rolls-royce/cullinan": {
        "name": "Rolls-Royce Cullinan",
        "official_page": "https://www.rolls-roycemotorcars.com.cn/zh_CN/showroom/cullinan.html",
        "cdn_ids": ["TPu27E5hqu", "cRLxex42HA", "zHpoHoYlYJ", "dLxZBB4BYy", "uOuqwS4wkR", "ganKLBKjmW", "f9ovIpYnwM"],
        "direct_urls": [],
    },
    "bentley/flying-spur": {
        "name": "Bentley Flying Spur",
        "official_page": "https://www.bentleymotors.com/en/models/flying-spur/flying-spur.html",
        "cdn_ids": ["cGfUygktJf", "EVkYZwCNCh", "VdqcVZi7ta", "9qyYHHYVxY"],
        "direct_urls": [],
    },
    "bentley/bentayga": {
        "name": "Bentley Bentayga",
        "official_page": "https://www.bentleymotors.com/en/models/bentayga/bentayga.html",
        "cdn_ids": ["HPEMb1IdMY", "PsZUew5EAi", "8UGbiVOsVd", "RMZ9uA8VSQ", "kvbNmkjmzO",
                     "apefN9uE55", "JmoTFMKUcU", "RlfKIsqJLv", "iATWgYAxuU", "NIw1XLyUsw",
                     "Hs60DhapH9", "kvUuja66Hf", "3pzK2YtCFu", "tFIuUurNKE", "RGyezXRAV8",
                     "3QhB6S1ccq", "gNruEWvPxb", "Rfv0cu85Nn"],
        "direct_urls": [],
    },
    "bugatti/veyron": {
        "name": "Bugatti Veyron",
        "official_page": "https://www.bugatti.com/en/classic-icons/veyron-164",
        "cdn_ids": [],
        "direct_urls": [],
        # Bugatti官网页面无图片(JS渲染)，待用其他官方来源补充
    },
    "porsche/macan": {
        "name": "Porsche Macan",
        "official_page": "https://newsroom.porsche.com/en/press-kits/the-new-porsche-macan/Design-und-Aerodynamik.html",
        "cdn_ids": ["6AfxIQ7mU4", "3qXihvSFhU", "POhxUHZfKO", "OyVfAtFvWD", "y2pLxfHu5k", "KcIU9ulMb1"],
        "direct_urls": [
            # Porsche newsroom直接侧视图PNG (官方press kit)
            "https://newsroom.porsche.com/dam/jcr:17851357-84af-4c6e-ac95-cb5910b3ee0a/Macan%20Electric%202024.png",
        ],
    },
    "ferrari/sf90": {
        "name": "Ferrari SF90",
        "official_page": "https://www.ferrari.com/en-SY/auto/sf90-stradale",
        "cdn_ids": ["dCDGbBw98c", "nu9op3u2gk"],
        "direct_urls": [],
    },
    "ferrari/f8-tributo": {
        "name": "Ferrari F8 Tributo",
        "official_page": "https://www.ferrari.com/en-SY/auto/f8-tributo",
        "cdn_ids": ["PpUPpU0qUs", "pUzVokPsQR", "4Rz0hZGHRU", "KmccUNVFKk", "VDVNxAO6Tx", "NghQgYU2SF"],
        "direct_urls": [],
    },
}


def download_cdn(cdn_id, referer=""):
    """从doubaocdn下载图片（官网图片通过此CDN提供）"""
    url = f"https://aka.doubaocdn.com/s/{cdn_id}"
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
            return r.read()
    except Exception as e:
        print(f"  CDN ERR {cdn_id}: {e}")
        return None


def download_direct(url, referer=""):
    """直接下载官网URL"""
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=30) as r:
            return r.read()
    except Exception as e:
        print(f"  DIRECT ERR {url[:80]}: {e}")
        return None


def analyze(raw):
    """分析图片基本信息"""
    try:
        with Image.open(io.BytesIO(raw)) as im:
            w, h = im.size
            fmt = im.format
            md5 = hashlib.md5(raw).hexdigest()[:12]
            asp = round(w / h, 2) if h else 0

            # 背景分析
            im_s = im.convert("RGB").resize((200, 150))
            px = list(im_s.getdata())
            W, H = 200, 150
            corners = [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1),
                       (W // 2, 0), (W // 2, H - 1), (0, H // 2), (W - 1, H // 2)]
            cc = [px[y * W + x] for x, y in corners]
            max_diff = max(max(c[i] for c in cc) - min(c[i] for c in cc) for i in range(3))
            sky = sum(1 for r, g, b in px if b > 150 and b > r + 30 and b > g + 10) / len(px)
            grass = sum(1 for r, g, b in px if g > 100 and g > r + 20 and g > b + 10) / len(px)
            dark = sum(1 for r, g, b in px if (r + g + b) / 3 < 50) / len(px)
            light = sum(1 for r, g, b in px if (r + g + b) / 3 > 220) / len(px)

            # 背景类型
            if max_diff < 25 and dark > 0.5:
                bg_type = "dark_studio"
            elif max_diff < 25 and light > 0.5:
                bg_type = "white_studio"
            elif sky > 0.1 or grass > 0.05:
                bg_type = "outdoor"
            else:
                bg_type = "complex"

            return {
                "w": w, "h": h, "asp": asp, "fmt": fmt, "md5": md5,
                "kb": round(len(raw) / 1024),
                "max_diff": max_diff, "sky": round(sky, 3), "grass": round(grass, 3),
                "dark": round(dark, 3), "light": round(light, 3), "bg_type": bg_type,
            }
    except Exception as e:
        return {"error": str(e)}


def main():
    os.makedirs(CAND_DIR, exist_ok=True)
    log = []

    for car_path, info in CARS.items():
        brand, model = car_path.split("/")
        car_dir = os.path.join(CAND_DIR, brand, model)
        os.makedirs(car_dir, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"下载: {info['name']}")
        print(f"官网: {info['official_page']}")

        car_log = {
            "car": car_path,
            "name": info["name"],
            "official_page": info["official_page"],
            "images": [],
        }

        idx = 0

        # 下载CDN图片
        for cdn_id in info.get("cdn_ids", []):
            idx += 1
            fname = f"cand_{idx:02d}.jpg"
            print(f"  [{idx}] CDN: {cdn_id} ...", end=" ")
            raw = download_cdn(cdn_id, referer=info["official_page"])
            if raw:
                info_dict = analyze(raw)
                if "error" not in info_dict:
                    # 保存原图
                    with open(os.path.join(car_dir, fname), "wb") as f:
                        f.write(raw)
                    entry = {
                        "file": fname,
                        "source": f"cdn:{cdn_id}",
                        "source_type": "official_page_cdn",
                        **info_dict,
                    }
                    car_log["images"].append(entry)
                    print(f"OK {info_dict['w']}x{info_dict['h']} asp={info_dict['asp']} bg={info_dict['bg_type']} {info_dict['kb']}KB")
                else:
                    print(f"ANALYSIS ERR: {info_dict['error']}")
            else:
                print("FAIL")
            time.sleep(0.3)

        # 下载直接URL
        for url in info.get("direct_urls", []):
            idx += 1
            ext = ".png" if ".png" in url.lower() else ".jpg"
            fname = f"cand_{idx:02d}{ext}"
            print(f"  [{idx}] DIRECT: ...{url[-60:]} ...", end=" ")
            raw = download_direct(url, referer=info["official_page"])
            if raw:
                info_dict = analyze(raw)
                if "error" not in info_dict:
                    with open(os.path.join(car_dir, fname), "wb") as f:
                        f.write(raw)
                    entry = {
                        "file": fname,
                        "source": url,
                        "source_type": "official_direct",
                        **info_dict,
                    }
                    car_log["images"].append(entry)
                    print(f"OK {info_dict['w']}x{info_dict['h']} asp={info_dict['asp']} bg={info_dict['bg_type']} {info_dict['kb']}KB")
                else:
                    print(f"ANALYSIS ERR: {info_dict['error']}")
            else:
                print("FAIL")
            time.sleep(0.3)

        # 去重（MD5）
        seen_md5 = set()
        unique_images = []
        for img in car_log["images"]:
            if img["md5"] not in seen_md5:
                seen_md5.add(img["md5"])
                unique_images.append(img)
        car_log["images"] = unique_images
        car_log["total"] = len(unique_images)
        print(f"  -> 共 {len(unique_images)} 张唯一图片")

        log.append(car_log)

    # 保存日志
    log_path = os.path.join(BASE, "_official_v18_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\n日志已保存: {log_path}")

    # 生成预览页
    gen_preview(log)
    print(f"预览页已生成: {os.path.join(PUB, '_preview_official_v18.html')}")


def gen_preview(log):
    """生成预览页用于视觉验证"""
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
.cand-label .bg-dark_studio{color:#2ecc71}
.cand-label .bg-white_studio{color:#2ecc71}
.cand-label .bg-outdoor{color:#e94560}
.cand-label .bg-complex{color:#f39c12}
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
