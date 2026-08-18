#!/usr/bin/env python3
"""
NetCarShow Side_Profile 下载器（v16）
======================================
从 NetCarShow.com 下载13款不合格车型的 Side_Profile（正侧视图）
保存到 public/_candidates_v15/{brand}/{model}/netcarshow_side.jpg 供视觉验证

NetCarShow 专门提供各车型的正侧视图，是最可靠的正侧视来源。
"""
import hashlib, io, json, re, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
CAND_DIR = PROJECT / "public" / "_candidates_v15"
LOG_FILE = CUR_DIR / "_netcarshow_v16_log.json"

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
    side_profile_urls = re.findall(r'["\']([^"\']*Side_Profile[^"\']*\.jpg)["\']', html, re.I)
    side_profile_urls = list(dict.fromkeys(side_profile_urls))

    big_imgs = re.findall(r'["\'](https?://[^"\']*1280[^"\']*\.jpg)["\']', html, re.I)
    big_imgs += re.findall(r'["\'](/[^"\']*1280[^"\']*\.jpg)["\']', html, re.I)
    big_imgs = list(dict.fromkeys(big_imgs))

    return side_profile_urls, big_imgs


# 13款不合格车型的 NetCarShow URL
CAR_URLS = [
    # Rolls-Royce
    ("rolls-royce", "ghost",      "https://www.netcarshow.com/rolls-royce/2021-ghost/"),
    ("rolls-royce", "cullinan",   "https://www.netcarshow.com/rolls-royce/2020-cullinan/"),
    # Bugatti
    ("bugatti",     "chiron",     "https://www.netcarshow.com/bugatti/2016-chiron/"),
    ("bugatti",     "veyron",     "https://www.netcarshow.com/bugatti/2005-veyron/"),
    ("bugatti",     "divo",       "https://www.netcarshow.com/bugatti/2019-divo/"),
    # Bentley
    ("bentley",     "continental-gt",  "https://www.netcarshow.com/bentley/2019-continental_gt/"),
    ("bentley",     "continental-gtc", "https://www.netcarshow.com/bentley/2019-continental_gt_convertible/"),
    ("bentley",     "flying-spur",     "https://www.netcarshow.com/bentley/2020-flying_spur/"),
    ("bentley",     "bentayga",        "https://www.netcarshow.com/bentley/2021-bentayga/"),
    # Porsche
    ("porsche",     "taycan",     "https://www.netcarshow.com/porsche/2020-taycan_turbo_s/"),
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
    log = {"results": []}
    solved = 0; failed = []

    print("=" * 60, flush=True)
    print("NetCarShow Side_Profile 下载器 (v16)", flush=True)
    print("=" * 60, flush=True)

    for idx, (brand, model, page_url) in enumerate(CAR_URLS, 1):
        print(f"\n[{idx}/13] {brand}/{model}", flush=True)
        print(f"  Page: {page_url}", flush=True)

        html = fetch_html(page_url)
        if not html:
            print(f"  ✗ 页面无法访问", flush=True)
            failed.append((brand, model, "page fetch fail"))
            log["results"].append({"brand": brand, "model": model, "status": "fetch_fail"})
            continue

        side_urls, big_urls = extract_side_profile(html)
        print(f"  Found {len(side_urls)} Side_Profile imgs, {len(big_urls)} 1280px imgs", flush=True)

        if not side_urls:
            # 搜索所有包含 "side" 的图片URL
            all_imgs = re.findall(r'["\'](/[^"\']*\.jpg)["\']', html)
            side_candidates = [u for u in all_imgs if "side" in u.lower()]
            print(f"  Side candidates: {side_candidates[:5]}", flush=True)
            if side_candidates:
                side_urls = side_candidates
            else:
                print(f"  ✗ 未找到Side_Profile图片", flush=True)
                failed.append((brand, model, "no side profile"))
                log["results"].append({"brand": brand, "model": model, "status": "no_side_profile"})
                continue

        # 尝试下载Side_Profile图片
        winner = None
        for su in side_urls:
            raw = download_img(su)
            if not raw or len(raw) < 30_000:
                continue
            try:
                with P.open(io.BytesIO(raw)) as im: w, h = im.size
            except Exception:
                continue
            print(f"  Side_Profile: {w}x{h} {len(raw)/1024:.0f}KB", flush=True)
            if w >= 1000:
                winner = (raw, w, h, su)
                break

        # 如果缩略图不够大，尝试1280px大图
        if not winner and big_urls:
            for bu in big_urls[:5]:
                raw = download_img(bu)
                if not raw or len(raw) < 50_000:
                    continue
                try:
                    with P.open(io.BytesIO(raw)) as im: w, h = im.size
                except Exception:
                    continue
                print(f"  1280px: {w}x{h} {len(raw)/1024:.0f}KB", flush=True)
                if w >= 1200:
                    winner = (raw, w, h, bu)
                    break

        if not winner:
            print(f"  ✗ 所有图片下载失败或尺寸不足", flush=True)
            failed.append((brand, model, "download fail"))
            log["results"].append({"brand": brand, "model": model, "status": "download_fail"})
            continue

        raw, w, h, src_url = winner
        aspect = w / h if h else 0
        print(f"  ✓ {w}x{h} asp={aspect:.2f} {len(raw)/1024:.0f}KB", flush=True)

        # 保存到候选目录
        car_dir = CAND_DIR / brand / model
        car_dir.mkdir(parents=True, exist_ok=True)
        out_path = car_dir / "netcarshow_side.jpg"
        final = write_jpg(raw)
        out_path.write_bytes(final)
        md5 = hashlib.md5(final).hexdigest()[:12]
        print(f"  💾 {out_path}  md5={md5}", flush=True)

        log["results"].append({
            "brand": brand, "model": model, "status": "ok",
            "path": str(out_path), "w": w, "h": h, "asp": round(aspect, 2),
            "md5": md5, "src_url": src_url
        })
        solved += 1
        time.sleep(1)

    # 保存日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60, flush=True)
    print(f"Solved {solved}/13  Failed {len(failed)}", flush=True)
    if failed:
        print("Failed: " + " | ".join(f"{b}/{m}({r})" for b,m,r in failed), flush=True)
    print(f"日志: {LOG_FILE}", flush=True)


if __name__ == "__main__":
    main()
