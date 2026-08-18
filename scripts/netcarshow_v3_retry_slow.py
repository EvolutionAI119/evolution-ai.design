# -*- coding: utf-8 -*-
""" netcarshow_v3_retry_slow.py
V3: 带延迟重试7款失败车型。
- 每次请求间隔3秒，避免限速
- 对于wraith等没有Side_Profile的车型，访问品牌列表页找其他年份
- 对于bentayga（找到Side_Profile但下载失败），直接重试下载
"""
import hashlib, io, re, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"

def fetch_html(url, timeout=35):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None

def download_img(url, timeout=35):
    if url.startswith("/"):
        url = BASE + url
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

def find_side_profile(html):
    if not html: return []
    urls = re.findall(r'["\']([^"\']*Side_Profile[^"\']*\.jpg)["\']', html, re.I)
    return list(dict.fromkeys(urls))

def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=93, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw

# 7款失败车型的备选URL + 品牌列表页
RETRY_7 = {
    ("rolls-royce", "wraith"): {
        "brand_page": "https://www.netcarshow.com/rolls-royce/",
        "urls": [
            "https://www.netcarshow.com/rolls-royce/2016-wraith/",
            "https://www.netcarshow.com/rolls-royce/2017-wraith/",
            "https://www.netcarshow.com/rolls-royce/2020-wraith/",
            "https://www.netcarshow.com/rolls-royce/2023-wraith/",
        ],
    },
    ("bentley", "bentayga"): {
        "brand_page": "https://www.netcarshow.com/bentley/",
        "urls": [
            "https://www.netcarshow.com/bentley/2023-bentayga_ewb/",  # 之前找到了Side_Profile但下载失败
            "https://www.netcarshow.com/bentley/2021-bentayga/",
            "https://www.netcarshow.com/bentley/2022-bentayga/",
            "https://www.netcarshow.com/bentley/2018-bentayga/",
        ],
    },
    ("bugatti", "chiron"): {
        "brand_page": "https://www.netcarshow.com/bugatti/",
        "urls": [
            "https://www.netcarshow.com/bugatti/2016-chiron/",
            "https://www.netcarshow.com/bugatti/2017-chiron/",
            "https://www.netcarshow.com/bugatti/2018-chiron/",
            "https://www.netcarshow.com/bugatti/2020-chiron/",
            "https://www.netcarshow.com/bugatti/2023-chiron/",
        ],
    },
    ("porsche", "911"): {
        "brand_page": "https://www.netcarshow.com/porsche/",
        "urls": [
            "https://www.netcarshow.com/porsche/2020-911_carrera/",
            "https://www.netcarshow.com/porsche/2020-911_carrera_s/",
            "https://www.netcarshow.com/porsche/2022-911_carrera/",
            "https://www.netcarshow.com/porsche/2023-911_gt3/",
            "https://www.netcarshow.com/porsche/2020-911_turbo_s/",
        ],
    },
    ("porsche", "panamera"): {
        "brand_page": "https://www.netcarshow.com/porsche/",
        "urls": [
            "https://www.netcarshow.com/porsche/2017-panamera_turbo/",
            "https://www.netcarshow.com/porsche/2019-panamera/",
            "https://www.netcarshow.com/porsche/2020-panamera/",
            "https://www.netcarshow.com/porsche/2024-panamera/",
        ],
    },
    ("porsche", "cayenne"): {
        "brand_page": "https://www.netcarshow.com/porsche/",
        "urls": [
            "https://www.netcarshow.com/porsche/2018-cayenne/",
            "https://www.netcarshow.com/porsche/2020-cayenne/",
            "https://www.netcarshow.com/porsche/2021-cayenne/",
            "https://www.netcarshow.com/porsche/2023-cayenne/",
        ],
    },
    ("ferrari", "f8-tributo"): {
        "brand_page": "https://www.netcarshow.com/ferrari/",
        "urls": [
            "https://www.netcarshow.com/ferrari/2020-f8_tributo/",
            "https://www.netcarshow.com/ferrari/2019-f8_tributo/",
            "https://www.netcarshow.com/ferrari/2020-f8_spider/",
            "https://www.netcarshow.com/ferrari/2021-f8_tributo/",
        ],
    },
}

def search_brand_page(brand_page, keyword):
    """在品牌列表页搜索包含关键词的车型URL"""
    html = fetch_html(brand_page)
    if not html: return []
    # 查找所有车型URL
    car_urls = re.findall(r'href\s*=\s*["\']([^"\']+' + re.escape(keyword) + r'[^"\']*)["\']', html, re.I)
    return list(dict.fromkeys(car_urls))

def main():
    solved = 0; still_failed = []
    for (brand, model), spec in RETRY_7.items():
        print(f"\n{'='*60}")
        print(f"[{brand}/{model}]")
        found = False

        # 先尝试预定义的URL
        for page_url in spec["urls"]:
            print(f"  Try: {page_url}")
            time.sleep(3)  # 关键：3秒延迟
            html = fetch_html(page_url)
            if not html:
                print(f"    ✗ fetch fail")
                continue
            side_urls = find_side_profile(html)
            if not side_urls:
                all_imgs = re.findall(r'["\'](/[^"\']*\.jpg)["\']', html)
                has_imgs = len([i for i in all_imgs if "1280" in i or "Side" in i])
                print(f"    ✗ no Side_Profile ({has_imgs} other imgs)")
                continue

            print(f"    ✔ Found {len(side_urls)} Side_Profile!")
            for su in side_urls:
                time.sleep(2)
                raw = download_img(su)
                if not raw or len(raw) < 30_000:
                    print(f"    ✗ download fail (sz={len(raw) if raw else 0})")
                    continue
                try:
                    with P.open(io.BytesIO(raw)) as im: w, h = im.size
                except Exception:
                    continue
                print(f"    📐 {w}x{h} {len(raw)/1024:.0f}KB")
                if w >= 1000:
                    p = BRANDS_D / brand / (model + ".jpg")
                    p.parent.mkdir(parents=True, exist_ok=True)
                    final = write_jpg(raw)
                    p.write_bytes(final)
                    md5 = hashlib.md5(p.read_bytes()).hexdigest()
                    print(f"    💾 {p.name} md5={md5[:10]}")
                    solved += 1; found = True
                    break
            if found: break

        # 如果预定义URL全部失败，尝试从品牌列表页搜索
        if not found:
            keyword = model.replace("-", "_")
            print(f"\n  Searching brand page for '{keyword}'...")
            time.sleep(3)
            found_urls = search_brand_page(spec["brand_page"], keyword)
            print(f"  Found {len(found_urls)} matching URLs on brand page")
            for fu in found_urls[:5]:
                if not fu.startswith("http"):
                    fu = BASE + fu
                if not fu.endswith("/"):
                    fu = fu + "/"
                print(f"  Try brand-discovered: {fu}")
                time.sleep(3)
                html = fetch_html(fu)
                if not html:
                    print(f"    ✗ fetch fail")
                    continue
                side_urls = find_side_profile(html)
                if not side_urls:
                    print(f"    ✗ no Side_Profile")
                    continue
                print(f"    ✔ Found {len(side_urls)} Side_Profile!")
                for su in side_urls:
                    time.sleep(2)
                    raw = download_img(su)
                    if not raw or len(raw) < 30_000:
                        continue
                    try:
                        with P.open(io.BytesIO(raw)) as im: w, h = im.size
                    except Exception:
                        continue
                    print(f"    📐 {w}x{h} {len(raw)/1024:.0f}KB")
                    if w >= 1000:
                        p = BRANDS_D / brand / (model + ".jpg")
                        p.parent.mkdir(parents=True, exist_ok=True)
                        final = write_jpg(raw)
                        p.write_bytes(final)
                        md5 = hashlib.md5(p.read_bytes()).hexdigest()
                        print(f"    💾 {p.name} md5={md5[:10]}")
                        solved += 1; found = True
                        break
                if found: break

        if not found:
            still_failed.append((brand, model))
            print(f"  ❌ ALL FAILED for {brand}/{model}")

    print("\n" + "="*80)
    print(f"Solved {solved}/{len(RETRY_7)}   Still failed: {len(still_failed)}")
    if still_failed:
        print("Still failed: " + " | ".join(f"{b}/{m}" for b,m in still_failed))
    return 0 if not still_failed else 1

if __name__ == "__main__": sys.exit(main())
