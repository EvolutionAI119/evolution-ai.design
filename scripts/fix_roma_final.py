# -*- coding: utf-8 -*-
""" fix_roma_final.py
替换 Ferrari Roma 为更纯净背景的正侧视图
"""
import hashlib, io, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

BRANDS_D = Path(__file__).resolve().parent.parent / "public" / "brands"
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
    if dark > 0.30:
        return "dark_studio", True, brightness, max_diff
    if light > 0.30:
        return "white_studio", True, brightness, max_diff
    if max_diff < 50:
        return "clean_bg", True, brightness, max_diff
    return "complex_bg", False, brightness, max_diff


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


# 黑名单域名
BAD_DOMAINS = [
    "jooinn.com", "pixabay.com", "pngtree.com", "freepik.com", "wallhere.com",
    "pinterest.com", "pinimg.com", "abstract", "background", "wallpaper",
    "shutterstock.com", "istockphoto.com", "gettyimages.com", "dreamstime.com",
    "color", "gradient", "texture", "pattern", "texture",
]

CAR_DOMAINS = ["carbuzz", "autoevolution", "motor1", "topspeed", "caranddriver",
               "edmunds", "porsche", "bentley", "rolls-royce", "bugatti", "ferrari",
               "netcarshow", "automobile", "auto", "car", "drive", "motor", "wheel",
               "bitautoimg", "pcauto", "xcar", "sinaimg", "smzdm", "bitauto",
               "puxiang", "sohu", "ifeng", "autoimg"]


def is_likely_car(url):
    u = url.lower()
    for b in BAD_DOMAINS:
        if b in u:
            return False
    return any(d in u for d in CAR_DOMAINS)


# 删除旧的
p = BRANDS_D / "ferrari" / "roma.jpg"
if p.exists():
    old_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
    EXISTING_MD5.discard(old_md5)
    print(f"Delete old roma image: md5={old_md5}")
    p.unlink()

queries = [
    "Ferrari Roma 2020 正侧视 影棚",
    "Ferrari Roma 2020 side profile studio",
    "法拉利 Roma 侧面 官图 影棚",
    "Ferrari Roma 2020 press photo side",
    "Ferrari Roma white studio side view",
]

all_candidates = []
for q in queries:
    print(f"\nSearch: {q}")
    urls = bing_image_search(q, num_results=30)
    car_urls = [u for u in urls if is_likely_car(u)]
    print(f"  Got {len(urls)} → {len(car_urls)} car-related")
    all_candidates.extend(car_urls)
    time.sleep(2)

seen = set()
unique = [u for u in all_candidates if u not in seen and not seen.add(u)]
print(f"\nTotal unique: {len(unique)}")

tried = 0
best_result = None  # (max_diff, ok, w, h, bg_type, url, raw)
for url in unique:
    if tried >= 40:
        break
    tried += 1
    print(f"\n[{tried}] {url[:90]}")
    time.sleep(1)
    raw = download_image(url)
    if not raw:
        continue
    raw_md5 = hashlib.md5(raw).hexdigest()[:12]
    if raw_md5 in EXISTING_MD5:
        print(f"  MD5 dup")
        continue
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception:
        continue
    if w < 1080:
        print(f"  width {w} < 1080, skip")
        continue
    if len(raw) < 100_000:
        continue
    asp = w / h if h else 0
    if asp < 1.2 or asp > 2.5:
        print(f"  asp {asp:.2f}, skip")
        continue
    bg_type, is_clean, bright, max_diff = analyze_bg(raw)
    print(f"  📐 {w}x{h} asp={asp:.2f} | bg={bg_type} (diff={max_diff}) | bright={bright:.0f}")
    if not is_clean:
        continue
    # 记录最佳（色差最小）
    score = max_diff  # 越小越好
    if best_result is None or score < best_result[0]:
        best_result = (score, w, h, bg_type, url, raw)
        print(f"  ★ NEW BEST: diff={max_diff}")
        # 立即保存这个候选
        p = BRANDS_D / "ferrari" / "roma.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        saved_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        EXISTING_MD5.add(saved_md5)
        EXISTING_MD5.add(raw_md5)

print("\n" + "="*60)
if best_result:
    score, w, h, bg_type, url, raw = best_result
    print(f"✓ 最佳结果: {w}x{h} bg={bg_type} diff={score}")
    print(f"  URL: {url[:100]}")
    p = BRANDS_D / "ferrari" / "roma.jpg"
    print(f"  文件: {p} md5={hashlib.md5(p.read_bytes()).hexdigest()[:12]}")
else:
    print("✗ 所有候选都不纯净，未替换")
