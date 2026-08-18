# -*- coding: utf-8 -*-
""" netcarshow_v4_final.py
V4 最终方案：解决7款剩余车型的正侧视图下载。
- 5秒延迟避免限速
- 日志直接写文件（不依赖tee）
- 多年份尝试 + 品牌页搜索 + 直接URL回退
- 严格只接受 Side_Profile URL（不退化到模糊匹配）
"""
import hashlib, io, json, re, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
LOG_FILE = CUR_DIR / "_v4_retry_log.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"


def fetch_html(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"    FETCH_ERR {type(e).__name__}: {str(e)[:80]}")
        return None


def download_img(url, timeout=30):
    if url.startswith("/"):
        url = BASE + url
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/", "Accept-Language": "en-US,en;q=0.9"})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        log(f"    DL_ERR {type(e).__name__}: {url[:80]}")
        return None


def find_side_profile(html):
    """严格提取 Side_Profile URL"""
    if not html:
        return []
    urls = re.findall(r'["\']([^"\']*Side_Profile[^"\']*\.jpg)["\']', html, re.I)
    return list(dict.fromkeys(urls))


def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=92, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw


LOG_LINES = []


def log(msg):
    print(msg, flush=True)
    LOG_LINES.append(msg)


def save_log():
    LOG_FILE.write_text("\n".join(LOG_LINES), encoding="utf-8")


# 7款失败车型：多年份URL + 品牌页
RETRY_7 = {
    ("rolls-royce", "wraith"): {
        "brand_page": "https://www.netcarshow.com/rolls-royce/",
        "urls": [
            "https://www.netcarshow.com/rolls-royce/2016-wraith/",
            "https://www.netcarshow.com/rolls-royce/2017-wraith/",
            "https://www.netcarshow.com/rolls-royce/2018-wraith/",
            "https://www.netcarshow.com/rolls-royce/2019-wraith/",
            "https://www.netcarshow.com/rolls-royce/2020-wraith/",
            "https://www.netcarshow.com/rolls-royce/2021-wraith/",
            "https://www.netcarshow.com/rolls-royce/2023-wraith/",
            "https://www.netcarshow.com/rolls-royce/2024-wraith_black_badge/",
        ],
    },
    ("bentley", "bentayga"): {
        "brand_page": "https://www.netcarshow.com/bentley/",
        "urls": [
            "https://www.netcarshow.com/bentley/2017-bentayga/",
            "https://www.netcarshow.com/bentley/2018-bentayga/",
            "https://www.netcarshow.com/bentley/2019-bentayga/",
            "https://www.netcarshow.com/bentley/2020-bentayga/",
            "https://www.netcarshow.com/bentley/2021-bentayga/",
            "https://www.netcarshow.com/bentley/2022-bentayga/",
            "https://www.netcarshow.com/bentley/2023-bentayga_ewb/",
            "https://www.netcarshow.com/bentley/2024-bentayga_ewb/",
        ],
    },
    ("bugatti", "chiron"): {
        "brand_page": "https://www.netcarshow.com/bugatti/",
        "urls": [
            "https://www.netcarshow.com/bugatti/2016-chiron/",
            "https://www.netcarshow.com/bugatti/2017-chiron/",
            "https://www.netcarshow.com/bugatti/2018-chiron/",
            "https://www.netcarshow.com/bugatti/2019-chiron/",
            "https://www.netcarshow.com/bugatti/2020-chiron/",
            "https://www.netcarshow.com/bugatti/2021-chiron/",
            "https://www.netcarshow.com/bugatti/2022-chiron/",
            "https://www.netcarshow.com/bugatti/2023-chiron/",
        ],
    },
    ("porsche", "911"): {
        "brand_page": "https://www.netcarshow.com/porsche/",
        "urls": [
            "https://www.netcarshow.com/porsche/2020-911_carrera/",
            "https://www.netcarshow.com/porsche/2020-911_carrera_s/",
            "https://www.netcarshow.com/porsche/2020-911_carrera_4s/",
            "https://www.netcarshow.com/porsche/2021-911_turbo/",
            "https://www.netcarshow.com/porsche/2021-911_turbo_s/",
            "https://www.netcarshow.com/porsche/2022-911_carrera_gts/",
            "https://www.netcarshow.com/porsche/2022-911_gt3/",
            "https://www.netcarshow.com/porsche/2023-911_gt3_rs/",
            "https://www.netcarshow.com/porsche/2024-911_carrera/",
        ],
    },
    ("porsche", "panamera"): {
        "brand_page": "https://www.netcarshow.com/porsche/",
        "urls": [
            "https://www.netcarshow.com/porsche/2017-panamera_turbo/",
            "https://www.netcarshow.com/porsche/2017-panamera_4s/",
            "https://www.netcarshow.com/porsche/2018-panamera_turbo_s_e-hybrid/",
            "https://www.netcarshow.com/porsche/2019-panamera/",
            "https://www.netcarshow.com/porsche/2020-panamera/",
            "https://www.netcarshow.com/porsche/2021-panamera_4_e-hybrid/",
            "https://www.netcarshow.com/porsche/2023-panamera/",
            "https://www.netcarshow.com/porsche/2024-panamera/",
        ],
    },
    ("porsche", "cayenne"): {
        "brand_page": "https://www.netcarshow.com/porsche/",
        "urls": [
            "https://www.netcarshow.com/porsche/2018-cayenne/",
            "https://www.netcarshow.com/porsche/2019-cayenne/",
            "https://www.netcarshow.com/porsche/2020-cayenne/",
            "https://www.netcarshow.com/porsche/2020-cayenne_coupe/",
            "https://www.netcarshow.com/porsche/2021-cayenne/",
            "https://www.netcarshow.com/porsche/2022-cayenne_turbo_gt/",
            "https://www.netcarshow.com/porsche/2023-cayenne/",
            "https://www.netcarshow.com/porsche/2024-cayenne/",
        ],
    },
    ("ferrari", "f8-tributo"): {
        "brand_page": "https://www.netcarshow.com/ferrari/",
        "urls": [
            "https://www.netcarshow.com/ferrari/2019-f8_tributo/",
            "https://www.netcarshow.com/ferrari/2020-f8_tributo/",
            "https://www.netcarshow.com/ferrari/2020-f8_spider/",
            "https://www.netcarshow.com/ferrari/2021-f8_tributo/",
        ],
    },
}


def search_brand_page(brand_page, keyword):
    html = fetch_html(brand_page)
    if not html:
        return []
    car_urls = re.findall(r'href\s*=\s*["\']([^"\']+' + re.escape(keyword) + r'[^"\']*)["\']', html, re.I)
    return list(dict.fromkeys(car_urls))


def try_download_side(brand, model, page_url):
    """尝试从一个页面URL下载Side_Profile图片。成功返回True。"""
    log(f"  Try: {page_url}")
    time.sleep(5)  # 5秒延迟
    html = fetch_html(page_url)
    if not html:
        log(f"    ✗ fetch fail")
        return False
    side_urls = find_side_profile(html)
    if not side_urls:
        all_imgs = re.findall(r'["\'](/[^"\']*\.jpg)["\']', html)
        log(f"    ✗ no Side_Profile (page has {len(all_imgs)} jpgs)")
        return False

    log(f"    ✔ Found {len(side_urls)} Side_Profile!")
    for su in side_urls:
        time.sleep(3)
        raw = download_img(su)
        if not raw or len(raw) < 30_000:
            log(f"    ✗ download fail (sz={len(raw) if raw else 0})")
            continue
        try:
            with P.open(io.BytesIO(raw)) as im:
                w, h = im.size
        except Exception:
            continue
        log(f"    📐 {w}x{h} {len(raw)/1024:.0f}KB")
        if w >= 1000:
            p = BRANDS_D / brand / (model + ".jpg")
            p.parent.mkdir(parents=True, exist_ok=True)
            final = write_jpg(raw)
            p.write_bytes(final)
            md5 = hashlib.md5(p.read_bytes()).hexdigest()
            log(f"    💾 {p.name} md5={md5[:10]}")
            return True
    return False


def main():
    solved = 0
    still_failed = []
    for (brand, model), spec in RETRY_7.items():
        log(f"\n{'='*60}")
        log(f"[{brand}/{model}]")
        found = False

        # 1. 预定义URL
        for page_url in spec["urls"]:
            if try_download_side(brand, model, page_url):
                solved += 1
                found = True
                break

        # 2. 品牌页搜索
        if not found:
            keyword = model.replace("-", "_")
            log(f"\n  Searching brand page for '{keyword}'...")
            time.sleep(5)
            found_urls = search_brand_page(spec["brand_page"], keyword)
            log(f"  Found {len(found_urls)} matching URLs on brand page")
            for fu in found_urls[:8]:
                if not fu.startswith("http"):
                    fu = BASE + fu
                if not fu.endswith("/"):
                    fu = fu + "/"
                if try_download_side(brand, model, fu):
                    solved += 1
                    found = True
                    break

        if not found:
            still_failed.append((brand, model))
            log(f"  ❌ ALL FAILED for {brand}/{model}")

    log("\n" + "=" * 80)
    log(f"Solved {solved}/{len(RETRY_7)}   Still failed: {len(still_failed)}")
    if still_failed:
        log("Still failed: " + " | ".join(f"{b}/{m}" for b, m in still_failed))
    save_log()
    return 0 if not still_failed else 1


if __name__ == "__main__":
    sys.exit(main())
