# -*- coding: utf-8 -*-
""" netcarshow_final_v5.py
彻底重置：从 NetCarShow Side_Profile 重新下载全部19款正侧视官图。

方法论改进：
1. 唯一来源 = NetCarShow Side_Profile（不使用Bing/HDQwalls/cgmodel）
2. 每款车型提供多年份URL回退
3. 8秒请求间隔避免限速
4. 严格只接受URL含 "Side_Profile" 的图片
5. 下载后记录完整元数据日志
"""
import hashlib, io, json, re, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
LOG_FILE = CUR_DIR / "_v5_final_log.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"
DELAY = 8  # 秒

def fetch_html(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    ctx = ssl._create_unverified_context()
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    FETCH_ERR {type(e).__name__}: {str(e)[:80]}", flush=True)
        return None

def download_img(url, timeout=30):
    if url.startswith("/"):
        url = BASE + url
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": BASE + "/",
        "Accept-Language": "en-US,en;q=0.9",
    })
    ctx = ssl._create_unverified_context()
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"    DL_ERR {type(e).__name__}: {url[:80]}", flush=True)
        return None

def find_side_profile_urls(html):
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

# ============================================================
# 全部19款车型的 NetCarShow URL（多年份回退）
# ============================================================
ALL_CARS = [
    ("rolls-royce", "phantom", [
        "https://www.netcarshow.com/rolls-royce/2023-phantom_series_ii/",
        "https://www.netcarshow.com/rolls-royce/2018-phantom/",
        "https://www.netcarshow.com/rolls-royce/2020-phantom/",
        "https://www.netcarshow.com/rolls-royce/2021-phantom/",
        "https://www.netcarshow.com/rolls-royce/2022-phantom/",
    ]),
    ("rolls-royce", "ghost", [
        "https://www.netcarshow.com/rolls-royce/2021-ghost/",
        "https://www.netcarshow.com/rolls-royce/2020-ghost/",
        "https://www.netcarshow.com/rolls-royce/2019-ghost/",
        "https://www.netcarshow.com/rolls-royce/2018-ghost/",
        "https://www.netcarshow.com/rolls-royce/2023-ghost_extended/",
    ]),
    ("rolls-royce", "cullinan", [
        "https://www.netcarshow.com/rolls-royce/2020-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2019-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2021-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2022-cullinan/",
        "https://www.netcarshow.com/rolls-royce/2023-cullinan/",
    ]),
    ("rolls-royce", "wraith", [
        "https://www.netcarshow.com/rolls-royce/2016-wraith/",
        "https://www.netcarshow.com/rolls-royce/2017-wraith/",
        "https://www.netcarshow.com/rolls-royce/2018-wraith/",
        "https://www.netcarshow.com/rolls-royce/2019-wraith/",
        "https://www.netcarshow.com/rolls-royce/2020-wraith/",
        "https://www.netcarshow.com/rolls-royce/2021-wraith/",
        "https://www.netcarshow.com/rolls-royce/2023-wraith/",
    ]),
    ("bentley", "continental-gt", [
        "https://www.netcarshow.com/bentley/2019-continental_gt/",
        "https://www.netcarshow.com/bentley/2020-continental_gt/",
        "https://www.netcarshow.com/bentley/2021-continental_gt/",
        "https://www.netcarshow.com/bentley/2022-continental_gt_speed/",
        "https://www.netcarshow.com/bentley/2023-continental_gt/",
    ]),
    ("bentley", "continental-gtc", [
        "https://www.netcarshow.com/bentley/2019-continental_gt_convertible/",
        "https://www.netcarshow.com/bentley/2020-continental_gt_convertible/",
        "https://www.netcarshow.com/bentley/2021-continental_gt_convertible/",
        "https://www.netcarshow.com/bentley/2023-continental_gtc/",
    ]),
    ("bentley", "flying-spur", [
        "https://www.netcarshow.com/bentley/2020-flying_spur/",
        "https://www.netcarshow.com/bentley/2021-flying_spur/",
        "https://www.netcarshow.com/bentley/2022-flying_spur/",
        "https://www.netcarshow.com/bentley/2023-flying_spur/",
        "https://www.netcarshow.com/bentley/2024-flying_spur/",
    ]),
    ("bentley", "bentayga", [
        "https://www.netcarshow.com/bentley/2017-bentayga/",
        "https://www.netcarshow.com/bentley/2018-bentayga/",
        "https://www.netcarshow.com/bentley/2019-bentayga/",
        "https://www.netcarshow.com/bentley/2020-bentayga/",
        "https://www.netcarshow.com/bentley/2021-bentayga/",
        "https://www.netcarshow.com/bentley/2022-bentayga/",
        "https://www.netcarshow.com/bentley/2023-bentayga_ewb/",
    ]),
    ("bugatti", "chiron", [
        "https://www.netcarshow.com/bugatti/2016-chiron/",
        "https://www.netcarshow.com/bugatti/2017-chiron/",
        "https://www.netcarshow.com/bugatti/2018-chiron/",
        "https://www.netcarshow.com/bugatti/2019-chiron/",
        "https://www.netcarshow.com/bugatti/2020-chiron/",
        "https://www.netcarshow.com/bugatti/2021-chiron/",
        "https://www.netcarshow.com/bugatti/2022-chiron/",
        "https://www.netcarshow.com/bugatti/2023-chiron/",
    ]),
    ("bugatti", "veyron", [
        "https://www.netcarshow.com/bugatti/2005-veyron/",
        "https://www.netcarshow.com/bugatti/2006-veyron/",
        "https://www.netcarshow.com/bugatti/2008-veyron/",
        "https://www.netcarshow.com/bugatti/2010-veyron/",
        "https://www.netcarshow.com/bugatti/2011-veyron_super_sport/",
        "https://www.netcarshow.com/bugatti/2013-veyron_grand_sport_vitesse/",
    ]),
    ("bugatti", "divo", [
        "https://www.netcarshow.com/bugatti/2019-divo/",
        "https://www.netcarshow.com/bugatti/2020-divo/",
        "https://www.netcarshow.com/bugatti/2021-divo/",
    ]),
    ("porsche", "911", [
        "https://www.netcarshow.com/porsche/2020-911_carrera/",
        "https://www.netcarshow.com/porsche/2020-911_carrera_s/",
        "https://www.netcarshow.com/porsche/2020-911_carrera_4s/",
        "https://www.netcarshow.com/porsche/2021-911_turbo/",
        "https://www.netcarshow.com/porsche/2021-911_turbo_s/",
        "https://www.netcarshow.com/porsche/2022-911_carrera_gts/",
        "https://www.netcarshow.com/porsche/2022-911_gt3/",
        "https://www.netcarshow.com/porsche/2023-911_gt3_rs/",
        "https://www.netcarshow.com/porsche/2024-911_carrera/",
    ]),
    ("porsche", "taycan", [
        "https://www.netcarshow.com/porsche/2020-taycan_turbo_s/",
        "https://www.netcarshow.com/porsche/2020-taycan_turbo/",
        "https://www.netcarshow.com/porsche/2020-taycan_4s/",
        "https://www.netcarshow.com/porsche/2021-taycan/",
        "https://www.netcarshow.com/porsche/2022-taycan/",
        "https://www.netcarshow.com/porsche/2023-taycan/",
        "https://www.netcarshow.com/porsche/2024-taycan/",
    ]),
    ("porsche", "panamera", [
        "https://www.netcarshow.com/porsche/2021-panamera_4_e-hybrid/",
        "https://www.netcarshow.com/porsche/2017-panamera_turbo/",
        "https://www.netcarshow.com/porsche/2017-panamera_4s/",
        "https://www.netcarshow.com/porsche/2019-panamera/",
        "https://www.netcarshow.com/porsche/2020-panamera/",
        "https://www.netcarshow.com/porsche/2023-panamera/",
        "https://www.netcarshow.com/porsche/2024-panamera/",
    ]),
    ("porsche", "cayenne", [
        "https://www.netcarshow.com/porsche/2019-cayenne/",
        "https://www.netcarshow.com/porsche/2018-cayenne/",
        "https://www.netcarshow.com/porsche/2020-cayenne/",
        "https://www.netcarshow.com/porsche/2020-cayenne_coupe/",
        "https://www.netcarshow.com/porsche/2021-cayenne/",
        "https://www.netcarshow.com/porsche/2023-cayenne/",
    ]),
    ("porsche", "macan", [
        "https://www.netcarshow.com/porsche/2022-macan/",
        "https://www.netcarshow.com/porsche/2021-macan/",
        "https://www.netcarshow.com/porsche/2020-macan/",
        "https://www.netcarshow.com/porsche/2019-macan/",
        "https://www.netcarshow.com/porsche/2018-macan/",
        "https://www.netcarshow.com/porsche/2016-macan/",
        "https://www.netcarshow.com/porsche/2024-macan/",
    ]),
    ("ferrari", "sf90", [
        "https://www.netcarshow.com/ferrari/2020-sf90_stradale/",
        "https://www.netcarshow.com/ferrari/2021-sf90_stradale/",
        "https://www.netcarshow.com/ferrari/2022-sf90_stradale/",
        "https://www.netcarshow.com/ferrari/2023-sf90_xx_stradale/",
    ]),
    ("ferrari", "f8-tributo", [
        "https://www.netcarshow.com/ferrari/2019-f8_tributo/",
        "https://www.netcarshow.com/ferrari/2020-f8_tributo/",
        "https://www.netcarshow.com/ferrari/2021-f8_tributo/",
        "https://www.netcarshow.com/ferrari/2020-f8_spider/",
    ]),
    ("ferrari", "roma", [
        "https://www.netcarshow.com/ferrari/2020-roma/",
        "https://www.netcarshow.com/ferrari/2021-roma/",
        "https://www.netcarshow.com/ferrari/2022-roma/",
        "https://www.netcarshow.com/ferrari/2023-roma/",
    ]),
]

def search_brand_page(brand, keyword):
    """从品牌列表页搜索车型URL"""
    brand_page = f"https://www.netcarshow.com/{brand}/"
    html = fetch_html(brand_page)
    if not html:
        return []
    # 搜索包含关键词的URL
    pattern = r'href\s*=\s*["\']([^"\']*' + re.escape(keyword) + r'[^"\']*)["\']'
    urls = re.findall(pattern, html, re.I)
    return list(dict.fromkeys(urls))

def try_download(brand, model, page_url):
    """从一个NetCarShow页面URL下载Side_Profile图片"""
    print(f"  → {page_url}", flush=True)
    html = fetch_html(page_url)
    if not html:
        return None

    side_urls = find_side_profile_urls(html)
    if not side_urls:
        # 页面有图片但没有Side_Profile
        all_imgs = re.findall(r'["\'](/[^"\']*\.jpg)["\']', html)
        print(f"    no Side_Profile (page has {len(all_imgs)} jpgs)", flush=True)
        return None

    print(f"    ✔ Found {len(side_urls)} Side_Profile URL(s)", flush=True)
    for su in side_urls:
        time.sleep(3)
        raw = download_img(su)
        if not raw or len(raw) < 30_000:
            print(f"    ✗ download fail (sz={len(raw) if raw else 0})", flush=True)
            continue
        try:
            with P.open(io.BytesIO(raw)) as im:
                w, h = im.size
        except Exception:
            continue
        print(f"    📐 {w}x{h} {len(raw)/1024:.0f}KB", flush=True)
        if w >= 1000:
            return (raw, w, h, su, page_url)

    return None

def main():
    results = []
    solved = 0
    failed = []

    for idx, (brand, model, url_list) in enumerate(ALL_CARS, 1):
        print(f"\n{'='*60}", flush=True)
        print(f"[{idx}/19] {brand}/{model}", flush=True)
        result = None

        # 1. 尝试预定义URL
        for page_url in url_list:
            time.sleep(DELAY)
            result = try_download(brand, model, page_url)
            if result:
                break

        # 2. 品牌页搜索回退
        if not result:
            keyword = model.replace("-", "_")
            print(f"\n  Search brand page for '{keyword}'...", flush=True)
            time.sleep(DELAY)
            found_urls = search_brand_page(brand, keyword)
            print(f"  Found {len(found_urls)} URLs on brand page", flush=True)
            for fu in found_urls[:5]:
                if not fu.startswith("http"):
                    fu = BASE + fu
                if not fu.endswith("/"):
                    fu = fu + "/"
                time.sleep(DELAY)
                result = try_download(brand, model, fu)
                if result:
                    break

        if result:
            raw, w, h, src_url, page_url = result
            p = BRANDS_D / brand / (model + ".jpg")
            p.parent.mkdir(parents=True, exist_ok=True)
            final = write_jpg(raw)
            p.write_bytes(final)
            md5 = hashlib.md5(p.read_bytes()).hexdigest()
            print(f"  💾 SAVED {w}x{h} md5={md5[:10]}", flush=True)
            results.append({
                "brand": brand, "model": model,
                "page_url": page_url, "img_url": src_url,
                "width": w, "height": h,
                "md5": md5[:12], "size_kb": len(final) // 1024,
                "status": "OK"
            })
            solved += 1
        else:
            print(f"  ❌ ALL FAILED for {brand}/{model}", flush=True)
            failed.append((brand, model))
            results.append({
                "brand": brand, "model": model,
                "status": "FAILED"
            })

    # 保存日志
    LOG_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'='*60}", flush=True)
    print(f"RESULT: {solved}/19 solved, {len(failed)} failed", flush=True)
    if failed:
        print("Failed: " + " | ".join(f"{b}/{m}" for b, m in failed), flush=True)
    print(f"Log: {LOG_FILE}", flush=True)
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
