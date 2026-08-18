# -*- coding: utf-8 -*-
""" netcarshow_side_profile.py
从 NetCarShow.com 下载19款车型的 Side_Profile（正侧视图）官图。
NetCarShow的图片URL格式：
  缩略图: /{Brand}-{Model}-{Year}-Side_Profile.{hash}.jpg
  1280大图: /{Brand}-{Model}-{Year}-1280-{hash}.jpg

策略：
1. 访问每个车型的详情页 HTML
2. 用正则提取 Side_Profile 图片URL
3. 同时提取对应的 1280px 大图URL
4. 下载并验证质量
"""
import hashlib, io, json, re, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
LOG_FILE = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D = PROJECT / "public" / "brands"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"

def fetch_html(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    FETCH_ERR {type(e).__name__}: {e}")
        return None

def download_img(url, timeout=25):
    if url.startswith("/"):
        url = BASE + url
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"    DL_ERR {type(e).__name__}: {url[:80]}")
        return None

def extract_side_profile(html):
    """从车型详情页HTML中提取 Side_Profile 图片URL和对应的1280px大图URL"""
    # 查找所有图片URL对（缩略图 + 1280大图）
    # 格式: /Brand-Model-Year-Side_Profile.hash.jpg  和  /Brand-Model-Year-1280-hash.jpg
    side_profile_urls = re.findall(r'["\']([^"\']*Side_Profile[^"\']*\.jpg)["\']', html, re.I)
    # 去重
    side_profile_urls = list(dict.fromkeys(side_profile_urls))

    # 也查找所有1280px大图URL
    big_imgs = re.findall(r'["\'](https?://[^"\']*1280[^"\']*\.jpg)["\']', html, re.I)
    big_imgs += re.findall(r'["\'](/[^"\']*1280[^"\']*\.jpg)["\']', html, re.I)
    big_imgs = list(dict.fromkeys(big_imgs))

    return side_profile_urls, big_imgs

# ============================================================
# 19款车型的 NetCarShow URL
# 格式: (brand, model, netcarshow_url)
# ============================================================
CAR_URLS = [
    # Rolls-Royce
    ("rolls-royce", "phantom",    "https://www.netcarshow.com/rolls-royce/2023-phantom_series_ii/"),
    ("rolls-royce", "ghost",      "https://www.netcarshow.com/rolls-royce/2021-ghost/"),
    ("rolls-royce", "cullinan",   "https://www.netcarshow.com/rolls-royce/2020-cullinan/"),
    ("rolls-royce", "wraith",     "https://www.netcarshow.com/rolls-royce/2016-wraith/"),
    # Bentley
    ("bentley",     "continental-gt",  "https://www.netcarshow.com/bentley/2019-continental_gt/"),
    ("bentley",     "continental-gtc", "https://www.netcarshow.com/bentley/2019-continental_gt_convertible/"),
    ("bentley",     "flying-spur",     "https://www.netcarshow.com/bentley/2020-flying_spur/"),
    ("bentley",     "bentayga",        "https://www.netcarshow.com/bentley/2021-bentayga/"),
    # Bugatti
    ("bugatti",     "chiron",     "https://www.netcarshow.com/bugatti/2016-chiron/"),
    ("bugatti",     "veyron",     "https://www.netcarshow.com/bugatti/2005-veyron/"),
    ("bugatti",     "divo",       "https://www.netcarshow.com/bugatti/2019-divo/"),
    # Porsche
    ("porsche",     "911",        "https://www.netcarshow.com/porsche/2020-911_carrera/"),
    ("porsche",     "taycan",     "https://www.netcarshow.com/porsche/2020-taycan_turbo_s/"),
    ("porsche",     "panamera",   "https://www.netcarshow.com/porsche/2021-panamera_4_e-hybrid/"),
    ("porsche",     "cayenne",    "https://www.netcarshow.com/porsche/2019-cayenne/"),
    ("porsche",     "macan",      "https://www.netcarshow.com/porsche/2022-macan/"),
    # Ferrari
    ("ferrari",     "sf90",       "https://www.netcarshow.com/ferrari/2020-sf90_stradale/"),
    ("ferrari",     "f8-tributo", "https://www.netcarshow.com/ferrari/2019-f8_tributo/"),
    ("ferrari",     "roma",       "https://www.netcarshow.com/ferrari/2020-roma/"),
]

def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=93, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw

def main():
    solved = 0; failed = []
    for idx, (brand, model, page_url) in enumerate(CAR_URLS, 1):
        print(f"\n[{idx}/19] {brand}/{model}")
        print(f"  Page: {page_url}")
        html = fetch_html(page_url)
        if not html:
            # 尝试备用URL（去掉下划线等变体）
            print(f"  ❌ 页面无法访问")
            failed.append((brand, model, "page fetch fail"))
            continue

        side_urls, big_urls = extract_side_profile(html)
        print(f"  Found {len(side_urls)} Side_Profile imgs, {len(big_urls)} 1280px imgs")

        if not side_urls:
            # 如果没有Side_Profile，尝试搜索所有图片URL中包含 "Side" 的
            all_imgs = re.findall(r'["\'](/[^"\']*\.jpg)["\']', html)
            side_candidates = [u for u in all_imgs if "side" in u.lower()]
            print(f"  Side candidates: {side_candidates[:5]}")
            if side_candidates:
                side_urls = side_candidates
            else:
                print(f"  ❌ 未找到Side_Profile图片")
                failed.append((brand, model, "no side profile"))
                continue

        # 尝试下载Side_Profile图片（缩略图可能已经够大）
        winner = None
        for su in side_urls:
            raw = download_img(su)
            if not raw or len(raw) < 30_000:
                continue
            try:
                with P.open(io.BytesIO(raw)) as im: w, h = im.size
            except Exception:
                continue
            print(f"  Side_Profile: {w}x{h} {len(raw)/1024:.0f}KB  url={su[:80]}")
            if w >= 1000:  # 缩略图可能就是大图
                winner = (raw, w, h, su)
                break

        # 如果缩略图不够大，尝试1280px大图
        if not winner and big_urls:
            for bu in big_urls[:5]:  # 只试前5个
                raw = download_img(bu)
                if not raw or len(raw) < 50_000:
                    continue
                try:
                    with P.open(io.BytesIO(raw)) as im: w, h = im.size
                except Exception:
                    continue
                print(f"  1280px: {w}x{h} {len(raw)/1024:.0f}KB  url={bu[:80]}")
                if w >= 1200:
                    winner = (raw, w, h, bu)
                    break

        if not winner:
            print(f"  ❌ 所有图片下载失败或尺寸不足")
            failed.append((brand, model, "download fail"))
            continue

        raw, w, h, src_url = winner
        aspect = w / h if h else 0
        print(f"  ✔ {w}x{h} asp={aspect:.2f} {len(raw)/1024:.0f}KB")

        # 保存
        p = BRANDS_D / brand / (model + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        md5 = hashlib.md5(p.read_bytes()).hexdigest()
        print(f"  💾 {p}  md5={md5[:10]}")
        solved += 1

    print("\n" + "="*80)
    print(f"Solved {solved}/19  Failed {len(failed)}")
    if failed:
        print("Failed: " + " | ".join(f"{b}/{m}({r})" for b,m,r in failed))
    return 0 if not failed else 1

if __name__ == "__main__": sys.exit(main())
