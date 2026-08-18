"""
国内可访问方案：从 cn.bing.com 图片搜索下载4款失败车的正侧视图
策略：
1. 关键词带"side profile official"或"侧面 官图"
2. 用PIL分析宽高比和背景纯净度，过滤明显不合格的
3. 自动生成预览页供视觉验证
"""
import urllib.request, urllib.parse, ssl, re, os, time, json, hashlib, io
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ROOT = Path(r"d:\API\Evolution-Ai.Design")
OUT_DIR = ROOT / "public" / "_bing_v2_candidates"
OUT_DIR.mkdir(exist_ok=True)
# 清空旧内容
import shutil
for f in OUT_DIR.glob("*"):
    if f.is_file(): f.unlink()
    elif f.is_dir(): shutil.rmtree(f)

CARS = [
    {"brand": "bentley", "model": "bentayga", "name": "Bentley Bentayga",
     "queries": [
         "Bentley Bentayga side profile official photo",
         "Bentley Bentayga 2023 side view white background",
         "宾利 添越 侧面 官方图片 纯色背景",
         "Bentley Bentayga Side Profile netcarshow",
     ]},
    {"brand": "bentley", "model": "flying-spur", "name": "Bentley Flying Spur",
     "queries": [
         "Bentley Flying Spur side profile official photo",
         "Bentley Flying Spur 2020 side view white background",
         "宾利 飞驰 侧面 官方图片 纯色背景",
         "Bentley Flying Spur Side Profile netcarshow",
     ]},
    {"brand": "bentley", "model": "continental-gtc", "name": "Bentley Continental GTC",
     "queries": [
         "Bentley Continental GTC side profile official photo",
         "Bentley Continental GTC convertible side view white background",
         "宾利 欧陆 GTC 敞篷 侧面 官方图片",
         "Bentley Continental GTC Side Profile netcarshow",
     ]},
    {"brand": "rolls-royce", "model": "cullinan", "name": "Rolls-Royce Cullinan",
     "queries": [
         "Rolls-Royce Cullinan side profile official photo",
         "Rolls-Royce Cullinan 2020 side view white background",
         "劳斯莱斯 库里南 侧面 官方图片 纯色背景",
         "Rolls-Royce Cullinan Side Profile netcarshow",
     ]},
]


def fetch(url, timeout=20, referer=None):
    h = {"User-Agent": UA, "Accept": "image/*,*/*"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX))
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def bing_search_images(query, count=30):
    """从cn.bing.com搜索图片，返回图片URL列表"""
    urls = []
    # 用cn.bing.com，国内可访问
    search_url = f"https://cn.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1&count={count}"
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": UA})
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    Bing search ERR: {e}")
        return urls
    
    # 多种模式提取murl
    patterns = [
        r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&',
        r'"murl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"',
        r'imgurl=(https?://[^&]+?\.(?:jpg|jpeg|png))',
        r'"mediaurl":"(https?://[^"]+?\.(?:jpg|jpeg|png))"',
        r'data-src="(https?://[^"]+?\.(?:jpg|jpeg|png))"',
    ]
    seen = set()
    for p in patterns:
        for m in re.finditer(p, html):
            u = m.group(1)
            # 排除bing自己的缩略图
            if "bing.com" in u or "msn.com" in u or "th?id=" in u:
                continue
            if u in seen:
                continue
            seen.add(u)
            urls.append(u)
    return urls


def analyze_image(raw):
    """分析图片：宽高比、背景类型"""
    if not HAS_PIL:
        return {"size_kb": round(len(raw) / 1024)}
    try:
        with Image.open(io.BytesIO(raw)) as im:
            w, h = im.size
            asp = round(w / h, 2) if h else 0
            # 4角像素相似度
            try:
                rgb_im = im.convert("RGB")
                corners = [
                    rgb_im.getpixel((5, 5)),
                    rgb_im.getpixel((max(1, w-6), 5)),
                    rgb_im.getpixel((5, max(1, h-6))),
                    rgb_im.getpixel((max(1, w-6), max(1, h-6))),
                ]
                max_diff = 0
                for i in range(len(corners)):
                    for j in range(i+1, len(corners)):
                        diff = sum(abs(a-b) for a, b in zip(corners[i], corners[j]))
                        max_diff = max(max_diff, diff)
                avg = tuple(sum(c[i] for c in corners)//4 for i in range(3))
                brightness = sum(avg) / 3
                if max_diff < 30:
                    if brightness < 60:
                        bg = "dark_studio"
                    elif brightness > 200:
                        bg = "white_studio"
                    else:
                        bg = "gray_studio"
                else:
                    bg = "complex"
            except Exception:
                bg = "unknown"
                max_diff = -1
            return {"w": w, "h": h, "asp": asp, "bg": bg, "bg_diff": max_diff,
                    "size_kb": round(len(raw) / 1024)}
    except Exception as e:
        return {"error": str(e), "size_kb": round(len(raw) / 1024)}


def download_car(car):
    name = car["name"]
    print(f"\n=== {name} ===")
    car_dir = OUT_DIR / f"{car['brand']}__{car['model']}"
    car_dir.mkdir(exist_ok=True)
    
    all_imgs = []
    seen_md5 = set()
    
    for query in car["queries"]:
        print(f"  Query: {query}")
        img_urls = bing_search_images(query, count=30)
        print(f"    Found {len(img_urls)} URLs")
        
        for img_url in img_urls:
            # 过滤明显不合适的URL
            url_lower = img_url.lower()
            if any(x in url_lower for x in ["logo", "icon", "thumb", "avatar", "emoji"]):
                continue
            
            raw = fetch(img_url, timeout=15, referer="https://cn.bing.com/")
            if not raw or len(raw) < 25_000:
                continue
            
            md5 = hashlib.md5(raw).hexdigest()[:8]
            if md5 in seen_md5:
                continue
            seen_md5.add(md5)
            
            info = analyze_image(raw)
            # 基础过滤
            w = info.get("w", 0)
            h = info.get("h", 0)
            asp = info.get("asp", 0)
            if w < 600 or h < 300:
                continue
            if asp < 1.0 or asp > 3.5:  # 太窄或太宽
                continue
            
            ext = "jpg"
            if ".png" in img_url.lower():
                ext = "png"
            elif ".jpeg" in img_url.lower():
                ext = "jpg"
            fname = f"{md5}.{ext}"
            (car_dir / fname).write_bytes(raw)
            
            info["file"] = fname
            info["url"] = img_url
            info["query"] = query
            info["md5"] = md5
            all_imgs.append(info)
            print(f"    Saved {fname} {w}x{h} asp={asp} bg={info.get('bg','?')} ({len(raw)//1024}KB)")
            time.sleep(0.15)
        
        time.sleep(0.5)
    
    print(f"  {name}: {len(all_imgs)} images")
    return all_imgs


def main():
    all_results = {}
    for car in CARS:
        all_results[car["name"]] = download_car(car)
    
    log = OUT_DIR / "_bing_v2_log.json"
    log.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 生成预览页 - 按车型分组，按背景纯净度排序
    html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Bing V2 候选图视觉验证</title>
<style>
body{background:#0f0f1e;color:#eee;font-family:sans-serif;margin:0;padding:20px}
h1{text-align:center;margin-bottom:10px}
.sub{text-align:center;color:#888;margin-bottom:20px;font-size:13px}
.car-section{background:#16213e;border:2px solid #e94560;border-radius:10px;padding:15px;margin-bottom:20px}
.car-title{color:#e94560;font-weight:bold;font-size:18px;margin-bottom:10px}
.cand-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px}
.cand-card{background:#000;border-radius:6px;overflow:hidden;cursor:pointer;border:1px solid #333}
.cand-card img{width:100%;height:150px;object-fit:contain;display:block;background:#000}
.cand-label{padding:5px;font-size:10px;color:#aaa;text-align:center}
.tag{display:inline-block;padding:2px 5px;border-radius:3px;margin:0 2px;font-size:9px}
.tag.bg-ok{background:#2ecc71;color:#000}
.tag.bg-bad{background:#e94560}
.tag.asp-ok{background:#3498db;color:#000}
.tag.asp-bad{background:#e94560}
</style></head><body>
<h1>Bing V2 候选图视觉验证</h1>
<div class="sub">判断标准：正侧视(90°) + 纯净背景 + 车型正确 + 无水印 + 非改装 | 点击图片放大</div>
"""
    for car, imgs in all_results.items():
        # 按背景纯净度+宽高比排序
        def score(c):
            s = 0
            if c.get("bg") in ("dark_studio", "white_studio", "gray_studio"):
                s += 1000
                s += (50 - min(c.get("bg_diff", 999), 50)) * 5
            asp = c.get("asp", 0)
            if 1.4 <= asp <= 2.3:
                s += 500
                s += (100 - abs(asp - 1.7) * 50)
            if c.get("w", 0) >= 1080:
                s += 200
            elif c.get("w", 0) >= 800:
                s += 100
            return s
        imgs_sorted = sorted(imgs, key=score, reverse=True)
        
        # 找到文件夹名
        car_folder = ""
        for c in CARS:
            if c["name"] == car:
                car_folder = f"{c['brand']}__{c['model']}"
                break
        
        html += f'<div class="car-section">\n'
        html += f'  <div class="car-title">{car} ({len(imgs_sorted)} 张)</div>\n'
        html += f'  <div class="cand-grid">\n'
        for c in imgs_sorted:
            bg_ok = c.get("bg") in ("dark_studio", "white_studio", "gray_studio")
            asp_ok = 1.4 <= c.get("asp", 0) <= 2.3
            src_url = f"/_bing_v2_candidates/{car_folder}/{c['file']}"
            html += f'    <div class="cand-card">\n'
            html += f'      <img src="{src_url}" loading="lazy" onclick="window.open(this.src)" onerror="this.style.display=\'none\'">\n'
            html += f'      <div class="cand-label">{c.get("w","?")}x{c.get("h","?")} {c.get("size_kb","?")}KB '
            html += f'<span class="tag {"asp-ok" if asp_ok else "asp-bad"}">asp={c.get("asp","?")}</span>'
            html += f'<span class="tag {"bg-ok" if bg_ok else "bg-bad"}">{c.get("bg","?")}</span>'
            html += f'</div>\n    </div>\n'
        html += f'  </div>\n</div>\n'
    
    html += "</body></html>"
    out = ROOT / "public" / "_preview_bing_v2.html"
    out.write_text(html, encoding="utf-8")
    
    total = sum(len(v) for v in all_results.values())
    print(f"\n=== 完成 ===")
    print(f"总计: {total} 张图")
    print(f"预览页: http://localhost:5173/_preview_bing_v2.html")


if __name__ == "__main__":
    main()
