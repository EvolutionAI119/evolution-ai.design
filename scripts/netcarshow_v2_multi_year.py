# -*- coding: utf-8 -*-
""" netcarshow_v2_multi_year.py
V2: 为10款失败的车型尝试多个年份/型号备选URL，找到有Side_Profile的页面。
已成功的9款跳过，仅处理失败的10款。
"""
import hashlib, io, re, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"

def fetch_html(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None

def download_img(url, timeout=30):
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
    """提取Side_Profile图片URL"""
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

# 10款失败车型的备选URL（按优先级排列）
FAILED_10 = {
    ("rolls-royce", "ghost"): [
        "https://www.netcarshow.com/rolls-royce/2021-ghost/",
        "https://www.netcarshow.com/rolls-royce/2020-ghost/",
        "https://www.netcarshow.com/rolls-royce/2022-ghost/",
        "https://www.netcarshow.com/rolls-royce/2025-ghost_black_badge_series_ii/",
    ],
    ("rolls-royce", "cullinan"): [
        "https://www.netcarshow.com/rolls-royce/2019-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2022-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2023-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2020-cullinan_black_badge/",
    ],
    ("rolls-royce", "wraith"): [
        "https://www.netcarshow.com/rolls-royce/2018-wraith/",
        "https://www.netcarshow.com/rolls-royce/2019-wraith/",
        "https://www.netcarshow.com/rolls-royce/2021-wraith/",
        "https://www.netcarshow.com/rolls-royce/2022-wraith_black_badge/",
    ],
    ("bentley", "continental-gt"): [
        "https://www.netcarshow.com/bentley/2018-continental_gt/",
        "https://www.netcarshow.com/bentley/2020-continental_gt/",
        "https://www.netcarshow.com/bentley/2021-continental_gt_speed/",
        "https://www.netcarshow.com/bentley/2023-continental_gt_s/",
    ],
    ("bentley", "bentayga"): [
        "https://www.netcarshow.com/bentley/2016-bentayga/",
        "https://www.netcarshow.com/bentley/2017-bentayga/",
        "https://www.netcarshow.com/bentley/2019-bentayga/",
        "https://www.netcarshow.com/bentley/2020-bentayga/",
        "https://www.netcarshow.com/bentley/2023-bentayga_ewb/",
    ],
    ("bugatti", "chiron"): [
        "https://www.netcarshow.com/bugatti/2017-chiron/",
        "https://www.netcarshow.com/bugatti/2018-chiron/",
        "https://www.netcarshow.com/bugatti/2019-chiron/",
        "https://www.netcarshow.com/bugatti/2020-chiron/",
        "https://www.netcarshow.com/bugatti/2022-chiron_super_sport/",
    ],
    ("porsche", "911"): [
        "https://www.netcarshow.com/porsche/2020-911_carrera_s/",
        "https://www.netcarshow.com/porsche/2022-911_carrera/",
        "https://www.netcarshow.com/porsche/2023-911_gt3/",
        "https://www.netcarshow.com/porsche/2016-911_carrera/",
        "https://www.netcarshow.com/porsche/2020-911_turbo_s/",
    ],
    ("porsche", "panamera"): [
        "https://www.netcarshow.com/porsche/2017-panamera_turbo/",
        "https://www.netcarshow.com/porsche/2019-panamera/",
        "https://www.netcarshow.com/porsche/2020-panamera/",
        "https://www.netcarshow.com/porsche/2024-panamera/",
        "https://www.netcarshow.com/porsche/2021-panamera_turbo_s/",
    ],
    ("porsche", "cayenne"): [
        "https://www.netcarshow.com/porsche/2018-cayenne/",
        "https://www.netcarshow.com/porsche/2020-cayenne/",
        "https://www.netcarshow.com/porsche/2021-cayenne/",
        "https://www.netcarshow.com/porsche/2023-cayenne/",
        "https://www.netcarshow.com/porsche/2019-cayenne_coupe/",
    ],
    ("ferrari", "f8-tributo"): [
        "https://www.netcarshow.com/ferrari/2020-f8_tributo/",
        "https://www.netcarshow.com/ferrari/2021-f8_tributo/",
        "https://www.netcarshow.com/ferrari/2020-f8_spider/",
        "https://www.netcarshow.com/ferrari/2019-f8_tributo/",
    ],
}

def main():
    solved = 0; still_failed = []
    for (brand, model), urls in FAILED_10.items():
        print(f"\n[{brand}/{model}] Trying {len(urls)} URLs...")
        found = False
        for page_url in urls:
            html = fetch_html(page_url)
            if not html:
                print(f"  ✗ {page_url} (fetch fail)")
                time.sleep(0.5)
                continue
            side_urls = find_side_profile(html)
            if not side_urls:
                # 检查HTML中是否有任何图片
                all_imgs = re.findall(r'["\'](/[^"\']*\.jpg)["\']', html)
                has_imgs = len([i for i in all_imgs if "1280" in i or "Side" in i])
                print(f"  ✗ {page_url} (no Side_Profile, {has_imgs} other imgs)")
                time.sleep(0.3)
                continue

            print(f"  ✔ {page_url} → {len(side_urls)} Side_Profile")
            # 下载第一张Side_Profile
            for su in side_urls:
                raw = download_img(su)
                if not raw or len(raw) < 30_000:
                    continue
                try:
                    with P.open(io.BytesIO(raw)) as im: w, h = im.size
                except Exception:
                    continue
                print(f"    {w}x{h} {len(raw)/1024:.0f}KB  url={su[:80]}")
                if w >= 1000:
                    p = BRANDS_D / brand / (model + ".jpg")
                    p.parent.mkdir(parents=True, exist_ok=True)
                    final = write_jpg(raw)
                    p.write_bytes(final)
                    md5 = hashlib.md5(p.read_bytes()).hexdigest()
                    print(f"    💾 {p.name} md5={md5[:10]}")
                    solved += 1
                    found = True
                    break
            if found:
                break
            time.sleep(0.3)

        if not found:
            still_failed.append((brand, model))
            print(f"  ❌ ALL URLs FAILED for {brand}/{model}")

    print("\n" + "="*80)
    print(f"Solved {solved}/{len(FAILED_10)}   Still failed: {len(still_failed)}")
    if still_failed:
        print("Still failed: " + " | ".join(f"{b}/{m}" for b,m in still_failed))
    return 0 if not still_failed else 1

if __name__ == "__main__": sys.exit(main())
