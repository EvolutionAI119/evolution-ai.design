# -*- coding: utf-8 -*-
""" download_vehiclesizes_v8.py
从 vehiclesizes.com 下载19款车的正侧视图。
vehiclesizes.com 有按角度标注的图片库（"side profile", "side view"）。
URL模式: /cars/{brand}/{model}/{model-body-year}/images/
"""
import hashlib, io, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
BASE = "https://www.vehiclesizes.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

# 19款车型在 vehiclesizes.com 上的 model slug
CARS = [
    ("rolls-royce", "phantom",         "rolls-royce", "phantom"),
    ("rolls-royce", "ghost",            "rolls-royce", "ghost"),
    ("rolls-royce", "cullinan",         "rolls-royce", "cullinan"),
    ("rolls-royce", "wraith",           "rolls-royce", "wraith"),
    ("bentley",     "continental-gt",   "bentley",     "continental"),
    ("bentley",     "continental-gtc",  "bentley",     "continental"),
    ("bentley",     "flying-spur",      "bentley",     "flying-spur"),
    ("bentley",     "bentayga",         "bentley",     "bentayga"),
    ("bugatti",     "chiron",           "bugatti",     "chiron"),
    ("bugatti",     "veyron",           "bugatti",     "veyron"),
    ("bugatti",     "divo",             "bugatti",     "divo"),
    ("porsche",     "911",              "porsche",     "911"),
    ("porsche",     "taycan",           "porsche",     "taycan"),
    ("porsche",     "panamera",         "porsche",     "panamera"),
    ("porsche",     "cayenne",          "porsche",     "cayenne"),
    ("porsche",     "macan",            "porsche",     "macan"),
    ("ferrari",     "sf90",             "ferrari",     "sf90-stradale"),
    ("ferrari",     "f8-tributo",       "ferrari",     "f8-tributo"),
    ("ferrari",     "roma",             "ferrari",     "roma"),
]

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    ctx = ssl._create_unverified_context()
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {str(e)[:60]}", flush=True)
        return None

def download(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    ctx = ssl._create_unverified_context()
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=92, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw

def find_generation_links(html, model_slug):
    """从车型主页找到各代车型的链接"""
    # 链接格式: /cars/{brand}/{model}/{generation}/
    pattern = r'href\s*=\s*["\'](/cars/[^"\']*' + re.escape(model_slug) + r'[^"\']*/)["\']'
    links = re.findall(pattern, html, re.I)
    # 去重，排除 /images/ 和 /#full-size 链接
    clean = []
    seen = set()
    for l in links:
        l = l.split("#")[0]
        if "/images/" in l:
            continue
        if l in seen:
            continue
        seen.add(l)
        clean.append(l)
    return clean

def find_side_images(html):
    """从图片库页面提取side profile图片URL"""
    # 找所有thumbnail图片URL，筛选含 "side" 的
    all_imgs = re.findall(r'src\s*=\s*["\'](https?://[^"\']*\.jpg)["\']', html, re.I)
    # 也找 thm/ 格式的缩略图
    thm_imgs = re.findall(r'(https?://[^"\']*\/thm\/[^"\']*\.jpg)', html, re.I)
    all_imgs.extend(thm_imgs)

    # 筛选含 "side" 的URL
    side_imgs = [u for u in all_imgs if "side" in u.lower()]
    # 如果没有side，找含 "profile" 的
    if not side_imgs:
        side_imgs = [u for u in all_imgs if "profile" in u.lower()]

    # 去重
    return list(dict.fromkeys(side_imgs))

def convert_to_fullsize(thm_url):
    """将缩略图URL转为全尺寸URL: /thm/ → /images/"""
    return thm_url.replace("/thm/", "/images/")

def main():
    results = []
    for idx, (brand, model, vs_brand, vs_model) in enumerate(CARS, 1):
        print(f"\n[{idx}/19] {brand}/{model}", flush=True)

        # 1. 访问车型主页
        model_url = f"{BASE}/cars/{vs_brand}/{vs_model}/"
        print(f"  Page: {model_url}", flush=True)
        html = fetch(model_url)
        if not html:
            results.append({"brand": brand, "model": model, "status": "FAIL", "reason": "model page fetch fail"})
            continue

        # 2. 找各代车型链接
        gen_links = find_generation_links(html, vs_model)
        print(f"  Found {len(gen_links)} generation links", flush=True)

        if not gen_links:
            # 尝试直接访问 images 页面
            gen_links = [f"/cars/{vs_brand}/{vs_model}/"]

        # 3. 对每个代，尝试找图片库
        side_imgs = []
        for gen_link in gen_links[:5]:  # 只试前5代
            gen_url = BASE + gen_link if gen_link.startswith("/") else gen_link
            if not gen_url.endswith("/"):
                gen_url += "/"

            # 尝试 images 子页面
            images_url = gen_url + "images/"
            print(f"  Try: {images_url}", flush=True)
            time.sleep(1)
            img_html = fetch(images_url)
            if not img_html:
                continue

            found = find_side_images(img_html)
            if found:
                print(f"    Found {len(found)} side images!", flush=True)
                side_imgs.extend(found)
                break  # 找到就够了

        if not side_imgs:
            # 尝试从主页面直接找图片
            found = find_side_images(html)
            if found:
                side_imgs = found
                print(f"  Found {len(side_imgs)} side images from main page", flush=True)

        if not side_imgs:
            print(f"  ❌ No side images found", flush=True)
            results.append({"brand": brand, "model": model, "status": "FAIL", "reason": "no side images"})
            continue

        # 4. 下载side profile图片（优先全尺寸，回退缩略图）
        best = None
        for img_url in side_imgs[:5]:
            # 先尝试全尺寸
            full_url = convert_to_fullsize(img_url)
            print(f"  Download: {full_url[:80]}", flush=True)
            time.sleep(0.5)
            raw = download(full_url)
            if not raw or len(raw) < 20_000:
                # 回退到缩略图
                raw = download(img_url)
            if not raw or len(raw) < 20_000:
                continue
            try:
                with P.open(io.BytesIO(raw)) as im:
                    w, h = im.size
            except Exception:
                continue
            print(f"    {w}x{h} {len(raw)//1024}KB", flush=True)
            if w >= 600:
                best = (raw, w, h, img_url)
                if w >= 1000:
                    break  # 足够大了

        if not best:
            print(f"  ❌ All downloads failed", flush=True)
            results.append({"brand": brand, "model": model, "status": "FAIL", "reason": "download fail"})
            continue

        # 5. 保存
        raw, w, h, src = best
        p = BRANDS_D / brand / (model + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        md5 = hashlib.md5(final).hexdigest()[:10]
        print(f"  💾 SAVED {w}x{h} md5={md5} {len(final)//1024}KB", flush=True)
        results.append({"brand": brand, "model": model, "status": "OK",
                        "width": w, "height": h, "md5": md5, "src": src[:150]})

    # 总结
    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"\n{'='*60}", flush=True)
    print(f"Result: {ok}/19 OK, {19-ok} failed", flush=True)
    for r in results:
        if r["status"] == "OK":
            print(f"  ✓ {r['brand']}/{r['model']} {r['width']}x{r['height']} md5={r['md5']}", flush=True)
        else:
            print(f"  ✗ {r['brand']}/{r['model']} ({r.get('reason','unknown')})", flush=True)

if __name__ == "__main__":
    main()
