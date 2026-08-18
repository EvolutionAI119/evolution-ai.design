# -*- coding: utf-8 -*-
""" fix_macan_only.py
专门修复macan - 之前误下载了抽象背景图。
使用更精确的关键词，避免HD/wallpaper等触发非车图。
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


# 黑名单域名（已知返回非车图）
BAD_DOMAINS = [
    "jooinn.com", "pixabay.com", "pngtree.com", "freepik.com", "wallhere.com",
    "pinterest.com", "pinimg.com", "abstract", "background", "wallpaper",
    "shutterstock.com", "istockphoto.com", "gettyimages.com", "dreamstime.com",
    "color", "gradient", "texture", "pattern",
]


def is_likely_car_image(url):
    """检查URL是否可能是车图（基于域名和路径关键词）"""
    u = url.lower()
    # 拒绝已知非车图域名
    for bad in BAD_DOMAINS:
        if bad in u:
            return False
    # 优先接受车相关域名
    car_domains = ["carbuzz", "autoevolution", "motor1", "topspeed", "caranddriver",
                   "edmunds", "porsche", "bentley", "rolls-royce", "bugatti", "ferrari",
                   "netcarshow", "automobile", "auto", "car", "drive", "motor", "wheel",
                   "bitautoimg", "pcauto", "xcar", "sinaimg", "smzdm", "bitauto",
                   "puxiang", "sohu", "ifeng", "qq.com", "1688", "taobao", "jd.com",
                   "autoimg", "cn", "com"]
    return any(d in u for d in car_domains)


def verify_image(raw, url, min_w=1400):
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
    bg_type, is_clean, brightness = analyze_bg(raw)
    if not is_clean:
        return False, w, h, f"bg={bg_type}"
    return True, w, h, f"OK {w}x{h} asp={asp:.2f} bg={bg_type}"


def main():
    brand, model = "porsche", "macan"
    # 先删除当前错误的图
    p = BRANDS_D / brand / (model + ".jpg")
    if p.exists():
        old_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        EXISTING_MD5.discard(old_md5)
        print(f"Delete wrong image: {p}")
        p.unlink()

    # 更精确的搜索关键词（避免HD/wallpaper等触发非车图）
    queries = [
        "Porsche Macan 2022 side profile official",
        "Porsche Macan 侧面 官方图",
        "保时捷Macan 侧面 2022",
        "Porsche Macan 2023 side view",
        "Porsche Macan 2021 press photo side",
    ]

    all_candidates = []
    for q in queries:
        print(f"\nSearch: {q}")
        urls = bing_image_search(q, num_results=30)
        # 过滤：必须是车相关URL
        car_urls = [u for u in urls if is_likely_car_image(u)]
        print(f"  Got {len(urls)} URLs, {len(car_urls)} car-related")
        all_candidates.extend(car_urls)
        time.sleep(2)

    # 去重
    seen = set()
    unique = []
    for u in all_candidates:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    print(f"\nTotal unique car-related: {len(unique)}")

    tried = 0
    for url in unique:
        if tried >= 30:
            break
        tried += 1
        print(f"\n[{tried}] {url[:90]}")
        time.sleep(1)
        raw = download_image(url)
        if not raw:
            continue
        raw_md5 = hashlib.md5(raw).hexdigest()[:12]
        if raw_md5 in EXISTING_MD5:
            print(f"  MD5 dup, skip")
            continue
        ok, w, h, reason = verify_image(raw, url, min_w=1080)
        print(f"  {reason}")
        if not ok:
            continue
        # 保存
        p = BRANDS_D / brand / (model + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        saved_md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        print(f"  💾 SAVED md5={saved_md5}")
        return True

    print("\n❌ All candidates failed")
    return False


if __name__ == "__main__":
    main()
