# -*- coding: utf-8 -*-
""" download_sideview_v6.py
方法论文档：
  OLD: Bing搜索 → 像素分析 → 宣布成功（错误率95%）
  NEW: 浏览器搜索Google Images → 下载候选 → 浏览器逐张视觉验证 → 只接受验证通过的图

本脚本负责步骤1-2：搜索+下载候选
步骤3-4由浏览器验证脚本完成
"""
import hashlib, io, json, os, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
CANDIDATES_D = CUR_DIR / "_candidates"
CANDIDATES_D.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

# 19款车型搜索关键词（精确搜索官方正侧视图）
CARS = [
    ("rolls-royce", "phantom",         "Rolls-Royce Phantom side profile press photo"),
    ("rolls-royce", "ghost",            "Rolls-Royce Ghost side profile press photo"),
    ("rolls-royce", "cullinan",         "Rolls-Royce Cullinan side profile press photo"),
    ("rolls-royce", "wraith",           "Rolls-Royce Wraith side profile press photo"),
    ("bentley",     "continental-gt",   "Bentley Continental GT side profile press photo"),
    ("bentley",     "continental-gtc",  "Bentley Continental GTC convertible side profile press photo"),
    ("bentley",     "flying-spur",      "Bentley Flying Spur side profile press photo"),
    ("bentley",     "bentayga",         "Bentley Bentayga side profile press photo"),
    ("bugatti",     "chiron",           "Bugatti Chiron side profile press photo"),
    ("bugatti",     "veyron",           "Bugatti Veyron side profile press photo"),
    ("bugatti",     "divo",             "Bugatti Divo side profile press photo"),
    ("porsche",     "911",              "Porsche 911 Carrera side profile press photo"),
    ("porsche",     "taycan",           "Porsche Taycan side profile press photo"),
    ("porsche",     "panamera",         "Porsche Panamera side profile press photo"),
    ("porsche",     "cayenne",          "Porsche Cayenne side profile press photo"),
    ("porsche",     "macan",            "Porsche Macan side profile press photo"),
    ("ferrari",     "sf90",             "Ferrari SF90 Stradale side profile press photo"),
    ("ferrari",     "f8-tributo",       "Ferrari F8 Tributo side profile press photo"),
    ("ferrari",     "roma",             "Ferrari Roma side profile press photo"),
]

# 可信汽车媒体域名白名单
GOOD_DOMAINS = [
    "carbuzz.com", "autoevolution.com", "motor1.com", "topspeed.com",
    "caranddriver.com", "edmunds.com", "motortrend.com", "autoblog.com",
    "motortrend.com", "automobilemag.com", "roadandtrack.com",
    "netcarshow.com", "automachi.com", "autohome.com.cn",
    "pcauto.com.cn", "bitauto.com", "xcar.com.cn",
    "porsche.com", "bentleymotors.com", "rolls-roycemotorcars.com",
    "bugatti.com", "ferrari.com",
    "smzdm.com", "ifeng.com", "sohu.com", "sina.com.cn",
    "wikimedia.org", "wikipedia.org",
    "imgur.com", "flickr.com",
    "press.porsche.com", "media.ferrari.com", "media.bugatti.com",
    "carmodelslist.com", "supercars.net", "conceptcarz.com",
    "autodata1.com", "auto-types.com",
]

# 不可信域名黑名单
BAD_DOMAINS = [
    "jooinn.com", "pixabay.com", "pngtree.com", "freepik.com", "wallhere.com",
    "pinterest.com", "pinimg.com", "shutterstock.com", "istockphoto.com",
    "gettyimages.com", "dreamstime.com", "alamy.com", "depositphotos.com",
    "abstract", "background", "wallpaper", "texture", "pattern", "gradient",
    "cgmodel.com", "3dmodel", "render", "wallpaper", "hdqwalls.com",
    "wallpapers.com", "wallpaperaccess.com", "wallpaperflare.com",
    "usedcars", "forsale", "autotrader", "cars.com", "cargurus",
]

def fetch_url(url, timeout=20, headers=None):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    ctx = ssl._create_unverified_context()
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read(), r.geturl()
    except Exception:
        return None, None

def bing_image_search(query, num_results=50):
    """Bing图片搜索，返回图片URL列表"""
    all_urls = []
    for first in [1, 51, 101]:
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&first={first}&tsc=ImageBasicHover"
        raw, _ = fetch_url(url, timeout=15)
        if not raw:
            print(f"    Bing search fetch failed for first={first}", flush=True)
            continue
        html = raw.decode("utf-8", errors="replace")
        # 多种正则模式提取图片URL
        img_urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
        img_urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
        img_urls += re.findall(r'imgurl=(https?[^&"\']+)', html)
        print(f"    first={first}: {len(img_urls)} URLs from page ({len(html)} bytes)", flush=True)
        all_urls.extend(img_urls)
        time.sleep(2)

    seen = set()
    result = []
    for u in all_urls:
        u = urllib.parse.unquote(u).strip()
        if u in seen:
            continue
        seen.add(u)
        if not u.startswith("http"):
            continue
        low = u.lower()
        if not any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            continue
        result.append(u)
        if len(result) >= num_results:
            break
    return result

def filter_urls(urls):
    """过滤URL：白名单优先，黑名单排除"""
    good = []
    other = []
    for u in urls:
        low = u.lower()
        if any(b in low for b in BAD_DOMAINS):
            continue
        if any(g in low for g in GOOD_DOMAINS):
            good.append(u)
        else:
            other.append(u)
    return good + other

def download_image(url, timeout=20):
    try:
        raw, _ = fetch_url(url, timeout=timeout, headers={"Referer": "https://www.bing.com/"})
        return raw
    except Exception:
        return None

def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=90, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw

def main():
    results = {}
    global_md5 = set()  # 跨车型去重
    for idx, (brand, model, query) in enumerate(CARS, 1):
        print(f"\n[{idx}/19] {brand}/{model}: {query}", flush=True)

        # 清理候选目录
        car_dir = CANDIDATES_D / brand / model
        if car_dir.exists():
            for f in car_dir.glob("*.jpg"):
                f.unlink()
        car_dir.mkdir(parents=True, exist_ok=True)

        # 搜索
        urls = bing_image_search(query, num_results=50)
        filtered = filter_urls(urls)
        print(f"  Search: {len(urls)} results → {len(filtered)} filtered", flush=True)

        # 下载候选（跳过已出现的MD5）
        candidates = []
        for ci, url in enumerate(filtered[:30]):
            time.sleep(0.5)
            raw = download_image(url)
            if not raw or len(raw) < 50_000:
                continue
            try:
                with P.open(io.BytesIO(raw)) as im:
                    w, h = im.size
            except Exception:
                continue
            if w < 800:
                continue
            asp = w / h if h else 0
            if asp < 1.2 or asp > 2.5:
                continue

            # 跨车型MD5去重
            final = write_jpg(raw)
            md5 = hashlib.md5(final).hexdigest()[:10]
            if md5 in global_md5:
                print(f"  [{ci}] {w}x{h} DUP md5={md5} (skip)", flush=True)
                continue
            global_md5.add(md5)

            # 保存候选
            cand_path = car_dir / f"cand_{ci:02d}.jpg"
            cand_path.write_bytes(final)
            candidates.append({
                "index": ci,
                "url": url[:150],
                "width": w,
                "height": h,
                "aspect": round(asp, 2),
                "size_kb": len(final) // 1024,
                "md5": md5,
                "file": str(cand_path.relative_to(PROJECT)),
            })
            print(f"  [{ci}] {w}x{h} asp={asp:.2f} {len(final)//1024}KB md5={md5}", flush=True)
            if len(candidates) >= 5:
                break

        results[f"{brand}/{model}"] = candidates
        print(f"  → {len(candidates)} candidates saved", flush=True)

    # 保存候选信息
    info_file = CANDIDATES_D / "_candidates_info.json"
    info_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'='*60}", flush=True)
    print(f"Candidates saved to: {CANDIDATES_D}", flush=True)
    print(f"Info: {info_file}", flush=True)

    # 生成预览页面
    html = ['<!DOCTYPE html><html><head><meta charset="utf-8"><title>Candidates</title>',
            '<style>body{background:#1a1a2e;color:#eee;font-family:sans-serif;margin:0;padding:20px}',
            '.car-section{margin-bottom:30px;border:1px solid #333;padding:15px;border-radius:8px}',
            '.car-title{font-size:18px;color:#e94560;font-weight:bold;margin-bottom:10px}',
            '.cand-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}',
            '.cand{background:#16213e;border-radius:4px;overflow:hidden;padding:5px;text-align:center}',
            '.cand img{width:100%;height:120px;object-fit:contain;background:#000;border-radius:2px}',
            '.cand .info{font-size:10px;color:#aaa;margin-top:4px}',
            '</style></head><body><h1>19款车候选图预览（每款5张）</h1>']

    for (brand, model, query) in CARS:
        key = f"{brand}/{model}"
        cands = results.get(key, [])
        html.append(f'<div class="car-section">')
        html.append(f'<div class="car-title">{idx}. {brand}/{model} ({len(cands)} candidates)</div>')
        html.append(f'<div class="cand-grid">')
        for c in cands:
            rel_path = c["file"].replace("\\", "/")
            html.append(f'<div class="cand"><img src="/{rel_path}"><div class="info">{c["width"]}x{c["height"]} asp={c["aspect"]}</div></div>')
        html.append('</div></div>')

    html.append('</body></html>')
    preview = PROJECT / "public" / "_candidates_preview.html"
    preview.write_text("\n".join(html), encoding="utf-8")
    print(f"Preview: http://localhost:5173/_candidates_preview.html", flush=True)

if __name__ == "__main__":
    main()
