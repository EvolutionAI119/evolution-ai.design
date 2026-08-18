# -*- coding: utf-8 -*-
""" fix_specific_cars.py
针对性问题修复：
1. continental-gt: 误下载了内饰图，需要重新下载外观正侧视
2. wraith: 还是 HDQ 户外图，需要找正侧视
3. 检查其它图片是否真的有问题
"""
import hashlib, io, json, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"


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
    except Exception as e:
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
    """Bing图片搜索，返回解码后的URL列表"""
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


def is_likely_interior(raw):
    """检测图片是否为内饰图（基于棕色皮革和暗度）"""
    try:
        with P.open(io.BytesIO(raw)) as im:
            im_small = im.convert("RGB").resize((100, 100))
            pixels = list(im_small.get_flattened_data() if hasattr(im_small, 'get_flattened_data') else im_small.getdata())
    except Exception:
        return False
    brown = sum(1 for r,g,b in pixels if r > 80 and r < 200 and g > 50 and g < r and b < g and r - b > 30)
    return brown / len(pixels) > 0.20


def get_image_md5(raw):
    return hashlib.md5(raw).hexdigest()[:12]


def verify_image_basic(raw, min_w=1000):
    """基本质量验证"""
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception as e:
        return False, 0, 0, f"parse fail: {e}"
    if w < min_w:
        return False, w, h, f"width too small {w}"
    if len(raw) < 50_000:
        return False, w, h, f"file too small {len(raw)/1024:.0f}KB"
    asp = w / h if h else 0
    if asp < 1.2 or asp > 2.5:
        return False, w, h, f"aspect {asp:.2f} out of range"
    if is_likely_interior(raw):
        return False, w, h, "looks like interior"
    return True, w, h, f"OK {w}x{h} asp={asp:.2f} {len(raw)/1024:.0f}KB"


# 已存在 MD5（防止重复下载同一张图）
EXISTING_MD5 = set()
for brand_dir in BRANDS_D.iterdir():
    if not brand_dir.is_dir():
        continue
    for img_file in brand_dir.glob("*.jpg"):
        try:
            EXISTING_MD5.add(hashlib.md5(img_file.read_bytes()).hexdigest()[:12])
        except Exception:
            pass


def search_and_download(brand, model, queries, prefer_side_url=True, max_tries=15):
    """通过Bing搜索并下载图片"""
    print(f"\n{'='*60}")
    print(f"[{brand}/{model}]")

    all_candidates = []
    for q in queries:
        print(f"  Search: {q}")
        urls = bing_image_search(q, num_results=30)
        # URL含side/profile优先
        side_urls = [u for u in urls if any(k in u.lower() for k in ["side", "profile", "lateral", "侧面", "侧视"])]
        side_urls = [u for u in side_urls if not any(k in u.lower() for k in ["front", "rear", "interior", "dashboard", "wheel", "detail", "engine", "3-4", "34", "quarter"])]
        other_urls = [u for u in urls if u not in side_urls]
        all_candidates.extend([(u, "side") for u in side_urls])
        all_candidates.extend([(u, "other") for u in other_urls])
        time.sleep(2)
        if len(all_candidates) > 30:
            break

    # 去重
    seen = set()
    unique = []
    for u, t in all_candidates:
        if u not in seen:
            seen.add(u)
            unique.append((u, t))

    print(f"  Total: {len(unique)} ({sum(1 for _,t in unique if t=='side')} side URLs)")

    tried = 0
    for url, tag in unique:
        if tried >= max_tries:
            break
        tried += 1
        marker = "[SIDE]" if tag == "side" else "[OTHER]"
        print(f"  {marker} {url[:90]}")
        time.sleep(1)
        raw = download_image(url)
        if not raw:
            continue
        # 检查 MD5 重复（包括刚下载的）
        raw_md5 = get_image_md5(raw)
        if raw_md5 in EXISTING_MD5:
            print(f"    MD5 dup {raw_md5}, skip")
            continue
        ok, w, h, reason = verify_image_basic(raw)
        print(f"    {reason}")
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
        print(f"    💾 SAVED {p.name} md5={saved_md5}")
        return True
    return False


def main():
    results = []

    # 1. continental-gt: 内饰图，重新搜索正侧视
    # 用中文搜索避免歧义
    ok = search_and_download("bentley", "continental-gt", [
        "Bentley Continental GT 2019 正侧视 官图",
        "Bentley Continental GT side profile photo",
        "Bentley Continental GT 侧面 官方",
        "宾利 欧陆 GT 正侧视图",
    ])
    results.append(("bentley", "continental-gt", ok))

    # 2. wraith: HDQ户外图，搜索正侧视
    ok = search_and_download("rolls-royce", "wraith", [
        "Rolls-Royce Wraith 正侧视 官图",
        "劳斯莱斯 魅影 侧面 官方",
        "Rolls-Royce Wraith 2018 side profile",
        "Rolls-Royce Wraith 正侧面",
    ])
    results.append(("rolls-royce", "wraith", ok))

    # 输出结果
    print("\n" + "=" * 60)
    for brand, model, ok in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {brand}/{model}")


if __name__ == "__main__":
    main()
