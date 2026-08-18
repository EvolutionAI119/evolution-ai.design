# -*- coding: utf-8 -*-
""" fix_v3_final.py
最后修复：
1. veyron: 误下载了Chiron图，需要真正的Veyron
2. bentayga: 1024x684太小，需要更大图
3. macan: 1280x720太低，需要更大图
"""
import hashlib, io, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


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


def download_image(url, timeout=25):
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
            im.save(bio, "JPEG", quality=92, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw


def bing_image_search(query, num_results=30):
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1&tsc=ImageHoverTitle"
    raw, _ = fetch_url(url, timeout=15)
    if not raw:
        return []
    html = raw.decode("utf-8", errors="replace")
    img_urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
    img_urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
    img_urls += re.findall(r'imgurl=(https?[^&"\']+)', html)
    seen = set()
    result = []
    for u in img_urls:
        u = urllib.parse.unquote(u).strip()
        if u in seen:
            continue
        seen.add(u)
        if not u.startswith("http"):
            continue
        low = u.lower()
        if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            result.append(u)
        if len(result) >= num_results:
            break
    return result


def analyze_bg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im_small = im.convert("RGB").resize((100, 100))
            pixels = list(im_small.getdata())
    except Exception:
        return "unknown", False, 0
    brightness = sum((r+g+b)/3 for r,g,b in pixels) / len(pixels)
    corners = [pixels[0], pixels[99], pixels[9900], pixels[9999]]
    corner_std = max(max(abs(c1[i]-c2[i]) for i in range(3)) for c1 in corners for c2 in corners)
    sky = sum(1 for r,g,b in pixels if b > 150 and b > r + 30 and b > g + 10) / len(pixels)
    grass = sum(1 for r,g,b in pixels if g > 100 and g > r + 20 and g > b + 10) / len(pixels)
    dark = sum(1 for r,g,b in pixels if (r+g+b)/3 < 50) / len(pixels)
    light = sum(1 for r,g,b in pixels if (r+g+b)/3 > 220) / len(pixels)
    brown = sum(1 for r,g,b in pixels if r > 80 and r < 200 and g > 50 and g < r and b < g and r - b > 30) / len(pixels)
    if brown > 0.20 and brightness < 130:
        return "interior", False, brightness
    if sky > 0.15 or grass > 0.10:
        return "outdoor", False, brightness
    if dark > 0.30:
        return "dark_studio", True, brightness
    if light > 0.30:
        return "white_studio", True, brightness
    if corner_std < 50:
        return "clean_bg", True, brightness
    return "complex_bg", False, brightness


# 已存在MD5
EXISTING_MD5 = set()
for brand_dir in BRANDS_D.iterdir():
    if not brand_dir.is_dir():
        continue
    for img_file in brand_dir.glob("*.jpg"):
        try:
            EXISTING_MD5.add(hashlib.md5(img_file.read_bytes()).hexdigest()[:12])
        except Exception:
            pass


def url_contains_wrong_car(url, brand, model):
    """检查URL是否包含错误的车型关键词"""
    u = url.lower()
    # Veyron的URL不应该包含chiron
    if model == "veyron" and "chiron" in u:
        return True
    if model == "chiron" and "veyron" in u:
        return True
    # 通用：URL不应包含其他品牌
    return False


def verify_image(raw, brand, model, url, min_w=1400):
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception:
        return False, 0, 0, "parse fail"
    if w < min_w:
        return False, w, h, f"width {w}"
    if len(raw) < 100_000:
        return False, w, h, f"size {len(raw)/1024:.0f}KB"
    asp = w / h if h else 0
    if asp < 1.2 or asp > 2.5:
        return False, w, h, f"asp {asp:.2f}"
    if url_contains_wrong_car(url, brand, model):
        return False, w, h, f"wrong car in URL"
    bg_type, is_clean, brightness = analyze_bg(raw)
    if not is_clean:
        return False, w, h, f"bg={bg_type}"
    return True, w, h, f"OK {w}x{h} asp={asp:.2f} bg={bg_type}"


# 需要修复的3款车型
CARS_TO_FIX = [
    ("bugatti", "veyron", [
        "Bugatti Veyron 16.4 side view",
        "Bugatti Veyron 2010 正侧面",
        "布加迪 威龙 16.4 侧面 官图",
        "Bugatti Veyron Grand Sport side",
        "Bugatti Veyron 2008 profile",
    ], 1600),
    ("bentley", "bentayga", [
        "Bentley Bentayga 2021 正侧面 官图",
        "Bentley Bentayga 侧面 影棚 高清",
        "宾利 添越 侧面 官方图",
        "Bentley Bentayga 2022 side profile HD",
    ], 1400),
    ("porsche", "macan", [
        "Porsche Macan 2022 正侧面 官图",
        "Porsche Macan 侧面 影棚 高清",
        "保时捷 Macan 侧面 官方图",
        "Porsche Macan 2023 side profile HD",
    ], 1400),
]


def search_and_download(brand, model, queries, min_w, max_tries=25):
    print(f"\n{'='*60}")
    print(f"[{brand}/{model}] (min_width={min_w})")
    all_candidates = []
    for q in queries:
        print(f"  Search: {q}")
        urls = bing_image_search(q, num_results=30)
        # 过滤掉明显错误的URL
        filtered = [u for u in urls if not url_contains_wrong_car(u, brand, model)]
        all_candidates.extend(filtered)
        time.sleep(2)
        if len(all_candidates) > 80:
            break

    seen = set()
    unique = []
    for u in all_candidates:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    print(f"  Total unique: {len(unique)}")

    tried = 0
    for url in unique:
        if tried >= max_tries:
            break
        tried += 1
        print(f"  [{tried}] {url[:90]}")
        time.sleep(1)
        raw = download_image(url)
        if not raw:
            continue
        raw_md5 = hashlib.md5(raw).hexdigest()[:12]
        if raw_md5 in EXISTING_MD5:
            print(f"      MD5 dup, skip")
            continue
        ok, w, h, reason = verify_image(raw, brand, model, url, min_w=min_w)
        print(f"      {reason}")
        if not ok:
            continue
        p = BRANDS_D / brand / (model + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        saved_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        EXISTING_MD5.add(saved_md5)
        EXISTING_MD5.add(raw_md5)
        print(f"      💾 SAVED md5={saved_md5}")
        return True
    return False


def main():
    results = []
    for brand, model, queries, min_w in CARS_TO_FIX:
        # 先删除当前文件（让EXISTING_MD5重新计算）
        p = BRANDS_D / brand / (model + ".jpg")
        if p.exists():
            try:
                old_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
                EXISTING_MD5.discard(old_md5)  # 允许覆盖
            except Exception:
                pass
        ok = search_and_download(brand, model, queries, min_w)
        results.append((brand, model, ok))

    print("\n" + "=" * 60)
    solved = sum(1 for _, _, ok in results if ok)
    print(f"Solved {solved}/{len(CARS_TO_FIX)}")
    for brand, model, ok in results:
        print(f"  {'✓' if ok else '✗'} {brand}/{model}")


if __name__ == "__main__":
    main()
