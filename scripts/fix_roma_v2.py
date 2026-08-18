# -*- coding: utf-8 -*-
""" fix_roma_v2.py
先恢复旧图，再用更大量的搜索+更宽松的色差阈值找Roma正侧视图
"""
import hashlib, io, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

BRANDS_D = Path(__file__).resolve().parent.parent / "public" / "brands"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

OLD_MD5 = "75e48ea939f4"  # 原 Roma 图的MD5

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


def bing_image_search(query, num_results=50):
    # 搜索多页
    all_urls = []
    for first in [1, 51, 101]:
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&first={first}&tsc=ImageBasicHover"
        raw, _ = fetch_url(url, timeout=15)
        if not raw:
            continue
        html = raw.decode("utf-8", errors="replace")
        img_urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
        img_urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
        img_urls += re.findall(r'imgurl=(https?[^&"\']+)', html)
        all_urls.extend(img_urls)
        time.sleep(1)

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
        if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            result.append(u)
        if len(result) >= num_results:
            break
    return result


def analyze_bg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im_small = im.convert("RGB").resize((200, 150))
            pixels = list(im_small.getdata())
    except Exception:
        return "unknown", False, 0, 999
    W, H = 200, 150
    brightness = sum((r+g+b)/3 for r,g,b in pixels) / len(pixels)
    corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),(0,H//2),(W-1,H//2)]
    corner_colors = [pixels[y*W+x] for x,y in corners]
    max_diff = max(
        max(c[i] for c in corner_colors) - min(c[i] for c in corner_colors)
        for i in range(3)
    )
    sky = sum(1 for r,g,b in pixels if b > 150 and b > r + 30 and b > g + 10) / len(pixels)
    grass = sum(1 for r,g,b in pixels if g > 100 and g > r + 20 and g > b + 10) / len(pixels)
    dark = sum(1 for r,g,b in pixels if (r+g+b)/3 < 50) / len(pixels)
    light = sum(1 for r,g,b in pixels if (r+g+b)/3 > 220) / len(pixels)
    brown = sum(1 for r,g,b in pixels if r > 80 and r < 200 and g > 50 and g < r and b < g and r - b > 30) / len(pixels)
    if brown > 0.20 and brightness < 130:
        return "interior", False, brightness, max_diff
    if sky > 0.15 or grass > 0.10:
        return "outdoor", False, brightness, max_diff
    if dark > 0.30 or light > 0.30:
        return "studio", True, brightness, max_diff
    if max_diff < 80:  # 放宽标准，允许有一定渐变
        return "acceptable", True, brightness, max_diff
    return "complex_bg", False, brightness, max_diff


# 先恢复旧的 Roma 图（从下载日志找到HDQ源）
p = BRANDS_D / "ferrari" / "roma.jpg"
if not p.exists():
    print("恢复旧Roma图: 从HDQ下载")
    old_url = "https://images.hdqwalls.com/download/2020-ferrari-roma-4k-91-1600x900.jpg"
    raw = download_image(old_url)
    if raw:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        print(f"  恢复成功 {w}x{h}")
    else:
        print("  恢复失败")
else:
    print("Roma图已存在，无需恢复")

# 收集现有 MD5
EXISTING_MD5 = set()
for brand_dir in BRANDS_D.iterdir():
    if not brand_dir.is_dir():
        continue
    for img_file in brand_dir.glob("*.jpg"):
        try:
            EXISTING_MD5.add(hashlib.md5(img_file.read_bytes()).hexdigest()[:12])
        except Exception:
            pass

print(f"现有图片MD5数: {len(EXISTING_MD5)}")

# 更全面的搜索关键词
queries = [
    "Ferrari Roma 2020 side profile",
    "Ferrari Roma 侧面 高清",
    "法拉利 Roma 正侧视图",
    "Ferrari Roma side view white background",
    "Ferrari Roma 2021 side official photo",
    "Ferrari Roma 影棚 侧视",
    "Ferrari Roma side profile black background",
]

all_candidates = []
for q in queries:
    print(f"\nSearch: {q}")
    urls = bing_image_search(q, num_results=80)
    print(f"  Got {len(urls)} URLs")
    all_candidates.extend(urls)
    time.sleep(2)

seen = set()
unique = []
for u in all_candidates:
    if u not in seen:
        seen.add(u)
        unique.append(u)
print(f"\nTotal unique: {len(unique)}")

tried = 0
best_result = None  # (max_diff, w, h, bg_type, url, raw)
for url in unique:
    if tried >= 60:
        break
    tried += 1
    if tried % 15 == 0:
        print(f"\n  ... 进度 {tried}/{len(unique)}")
    time.sleep(0.5)
    raw = download_image(url)
    if not raw:
        continue
    raw_md5 = hashlib.md5(raw).hexdigest()[:12]
    if raw_md5 in EXISTING_MD5:
        continue
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception:
        continue
    if w < 1000:
        continue
    if len(raw) < 70_000:
        continue
    asp = w / h if h else 0
    if asp < 1.2 or asp > 2.5:
        continue
    bg_type, is_clean, bright, max_diff = analyze_bg(raw)
    if not is_clean:
        continue
    # 找色差最小的
    if best_result is None or max_diff < best_result[0]:
        best_result = (max_diff, w, h, bg_type, url, raw)
        print(f"\n[{tried}] ★ NEW BEST: {w}x{h} asp={asp:.2f} bg={bg_type} diff={max_diff}")
        print(f"  URL: {url[:100]}")
        # 立即保存
        p = BRANDS_D / "ferrari" / "roma.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        saved_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        EXISTING_MD5.add(saved_md5)
        EXISTING_MD5.add(raw_md5)

print("\n" + "=" * 60)
if best_result:
    score, w, h, bg_type, url, raw = best_result
    print(f"✓ 最佳结果: {w}x{h} bg={bg_type} 8点色差={score}")
    p = BRANDS_D / "ferrari" / "roma.jpg"
    print(f"  文件: {p} md5={hashlib.md5(p.read_bytes()).hexdigest()[:12]}")
else:
    print("⚠ 未找到比原图更好的，保留原图")
    p = BRANDS_D / "ferrari" / "roma.jpg"
    if p.exists():
        raw = p.read_bytes()
        bg_type, is_clean, bright, max_diff = analyze_bg(raw)
        with P.open(io.BytesIO(raw)) as im: w, h = im.size
        print(f"  当前Roma: {w}x{h} bg={bg_type} diff={max_diff}")
        print(f"  8点色差 {max_diff} >= 60，仍是复杂背景，但视角可能是正侧视")
