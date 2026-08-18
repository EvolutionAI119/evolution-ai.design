# -*- coding: utf-8 -*-
""" fix_complex_bg_cars.py
为复杂背景的7款车型寻找影棚正侧视图。
策略：
1. 使用中文关键词搜索（避免英文歧义如Wraith=cabin/ghost）
2. 优先接受白色/暗色影棚背景的图片
3. 拒绝户外图（天空/草地占比高）
4. 严格MD5去重（用raw bytes MD5）
"""
import hashlib, io, json, re, ssl, time, urllib.parse, urllib.request
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
    """分析背景类型，返回 (bg_type, is_clean_studio, brightness)"""
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


def verify_image(raw, min_w=1200):
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception:
        return False, 0, 0, "parse fail", ""
    if w < min_w:
        return False, w, h, f"width {w}", ""
    if len(raw) < 80_000:
        return False, w, h, f"size {len(raw)/1024:.0f}KB", ""
    asp = w / h if h else 0
    if asp < 1.2 or asp > 2.5:
        return False, w, h, f"asp {asp:.2f}", ""
    bg_type, is_clean, brightness = analyze_bg(raw)
    if not is_clean:
        return False, w, h, f"bg={bg_type}", bg_type
    return True, w, h, f"OK {w}x{h} asp={asp:.2f} bg={bg_type}", bg_type


# 当前已存在的 MD5 集合
EXISTING_MD5 = set()
for brand_dir in BRANDS_D.iterdir():
    if not brand_dir.is_dir():
        continue
    for img_file in brand_dir.glob("*.jpg"):
        try:
            EXISTING_MD5.add(hashlib.md5(img_file.read_bytes()).hexdigest()[:12])
        except Exception:
            pass


# 7款需要替换的车型（复杂背景或户外）
CARS_TO_FIX = [
    ("rolls-royce", "wraith", [
        "劳斯莱斯 魅影 正侧面 官方图",
        "劳斯莱斯 魅影 侧面 影棚",
        "Rolls-Royce Wraith 2018 side studio",
        "劳斯莱斯 魅影 2018 侧视",
    ]),
    ("porsche", "cayenne", [
        "保时捷 卡宴 正侧面 官方图",
        "保时捷 卡宴 侧面 影棚",
        "Porsche Cayenne 2021 side studio",
        "保时捷 卡宴 2021 侧视",
    ]),
    ("ferrari", "f8-tributo", [
        "法拉利 F8 Tributo 正侧面 官方图",
        "法拉利 F8 侧面 影棚",
        "Ferrari F8 Tributo side studio",
        "法拉利 F8 Tributo 侧视",
    ]),
    ("rolls-royce", "phantom", [
        "劳斯莱斯 幻影 正侧面 官方图",
        "劳斯莱斯 幻影 侧面 影棚",
        "Rolls-Royce Phantom side studio",
    ]),
    ("rolls-royce", "ghost", [
        "劳斯莱斯 古思特 正侧面 官方图",
        "劳斯莱斯 古思特 侧面 影棚",
        "Rolls-Royce Ghost side studio",
    ]),
    ("bugatti", "veyron", [
        "布加迪 威龙 正侧面 官方图",
        "布加迪 威航 侧面 影棚",
        "Bugatti Veyron side studio",
    ]),
    ("porsche", "macan", [
        "保时捷 Macan 正侧面 官方图",
        "保时捷 Macan 侧面 影棚",
        "Porsche Macan side studio",
    ]),
]


def search_and_download(brand, model, queries, max_tries=20):
    print(f"\n{'='*60}")
    print(f"[{brand}/{model}]")
    all_candidates = []
    for q in queries:
        print(f"  Search: {q}")
        urls = bing_image_search(q, num_results=30)
        all_candidates.extend(urls)
        time.sleep(2)
        if len(all_candidates) > 60:
            break

    # 去重
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
        ok, w, h, reason, bg = verify_image(raw)
        print(f"      {reason}")
        if not ok:
            continue
        # 保存
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
    for brand, model, queries in CARS_TO_FIX:
        ok = search_and_download(brand, model, queries)
        results.append((brand, model, ok))

    print("\n" + "=" * 60)
    solved = sum(1 for _, _, ok in results if ok)
    print(f"Solved {solved}/{len(CARS_TO_FIX)}")
    for brand, model, ok in results:
        print(f"  {'✓' if ok else '✗'} {brand}/{model}")


if __name__ == "__main__":
    main()
