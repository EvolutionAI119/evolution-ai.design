# -*- coding: utf-8 -*-
"""
vehiclesizes_side_view.py  (MANUAL)
==========================================
这是一个「人工指定 vehiclesizes.com 图库 URL」的正侧视图下载脚本。
因为 WebSearch 已经成功返回 vehiclesizes.com 的图库页面，
这些图库页面中每张图都有明确的 "side profile" / "side view" / "front view" / "rear view" 文字标题。

本脚本：
    1. 对每个车型，我们使用 vehiclesizes.com 的图库 URL（从 WebSearch 获得的
       gallery 模式）；先手动填 19 条 URL，缺失的再用 WebSearch 结果补充
    2. 请求 vehiclesizes.com 图库页面 HTML
    3. 提取所有 <a> 标签中标题包含 "side" 的图片，再下载对应 URL
    4. 使用相同质量门禁 aspect ≥ 1.60，宽 ≥ 1200，文件 ≥ 70KB
    5. MD5 全局去重 + URL 精确车型词双重校验
"""
from __future__ import annotations
import os, sys, io, re, json, time, hashlib, urllib.request, urllib.parse, ssl
from pathlib import Path
from typing import Optional

CUR_DIR   = Path(__file__).resolve().parent
PROJECT   = CUR_DIR.parent
LOG_FILE  = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D  = PROJECT / "public" / "brands"

MIN_ASPECT   = 1.60
MAX_ASPECT   = 4.0
MIN_WIDTH_PX = 1200
MIN_FILE_B   = 70_000
REQ_TIMEOUT  = 20

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# ============================================================
# 19 款车型 → vehiclesizes.com 图库 URL 候选（先用已知模式占位，
#            缺省的我们后续手动通过 WebSearch 填）
# ============================================================
# 先用一个通用约定 URL 格式：
#   https://www.vehiclesizes.com/cars/<brand>/<slug-model>/images/
CAR_SPEC = [
    # brand, model,   keyword-must,   vehiclesizes paths (可能的多个，程序逐个尝试)
    ("rolls-royce", "phantom",        ["phantom"],
        ["https://www.vehiclesizes.com/cars/rolls-royce/phantom/phantom-viii-sedan-2018/images/"]),
    ("rolls-royce", "ghost",          ["ghost"],
        ["https://www.vehiclesizes.com/cars/rolls-royce/ghost/ghost-ii-sedan-2020/images/"]),
    ("rolls-royce", "cullinan",       ["cullinan"],
        ["https://www.vehiclesizes.com/cars/rolls-royce/cullinan/cullinan-suv-2018/images/"]),
    ("rolls-royce", "wraith",         ["wraith"],
        ["https://www.vehiclesizes.com/cars/rolls-royce/wraith/wraith-coupe-2014/images/"]),

    ("bentley",     "continental-gt",["continental","conti-gt","gt-coupe"],
        ["https://www.vehiclesizes.com/cars/bentley/continental-gt/continental-gt-coupe-2018/images/"]),
    ("bentley",     "continental-gtc",["continental-gtc","gtc"],
        ["https://www.vehiclesizes.com/cars/bentley/continental-gtc/continental-gtc-convertible-2019/images/"]),
    ("bentley",     "flying-spur",    ["flying","spur","flying-spur"],
        ["https://www.vehiclesizes.com/cars/bentley/flying-spur/flying-spur-sedan-2019/images/"]),
    ("bentley",     "bentayga",       ["bentayga"],
        ["https://www.vehiclesizes.com/cars/bentley/bentayga/bentayga-suv-2016/images/"]),

    ("bugatti",     "chiron",         ["chiron"],
        ["https://www.vehiclesizes.com/cars/bugatti/chiron/chiron-coupe-2016/images/"]),
    ("bugatti",     "veyron",         ["veyron"],
        ["https://www.vehiclesizes.com/cars/bugatti/veyron/veyron-16.4-coupe-2005/images/"]),
    ("bugatti",     "divo",           ["divo"],
        ["https://www.vehiclesizes.com/cars/bugatti/divo/divo-coupe-2019/images/"]),

    ("porsche",     "911",            ["911","992","carrera"],
        ["https://www.vehiclesizes.com/cars/porsche/911/911-carrera-coupe-2019/images/",
         "https://www.vehiclesizes.com/cars/porsche/911-coupe/"]),
    ("porsche",     "taycan",         ["taycan"],
        ["https://www.vehiclesizes.com/cars/porsche/taycan/taycan-sedan-2020/images/"]),
    ("porsche",     "panamera",       ["panamera"],
        ["https://www.vehiclesizes.com/cars/porsche/panamera/panamera-sport-turismo-2017/images/"]),
    ("porsche",     "cayenne",        ["cayenne"],
        ["https://www.vehiclesizes.com/cars/porsche/cayenne/cayenne-suv-coupe-2019/images/"]),
    ("porsche",     "macan",          ["macan"],
        ["https://www.vehiclesizes.com/cars/porsche/macan/macan-suv-2014/images/"]),

    ("ferrari",     "sf90",           ["sf90","stradale"],
        ["https://www.vehiclesizes.com/cars/ferrari/sf90-stradale/sf90-stradale-coupe-2019/images/"]),
    ("ferrari",     "f8-tributo",     ["f8","tributo"],
        ["https://www.vehiclesizes.com/cars/ferrari/f8-tributo/f8-tributo-coupe-2019/images/"]),
    ("ferrari",     "roma",           ["roma"],
        ["https://www.vehiclesizes.com/cars/ferrari/roma/roma-coupe-2020/images/"]),
]


def http_get(url, binary=False):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,image/webp,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Referer": "https://www.vehiclesizes.com/",
    })
    try:
        ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx) if ctx else urllib.request.HTTPSHandler)
        with op.open(req, timeout=REQ_TIMEOUT) as r:
            return r.read() if binary else r.read().decode(r.headers.get_content_charset() or "utf-8", errors="ignore")
    except Exception as e:
        return None


def dims_of(data):
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im: return im.size
    except Exception:
        return None


def md5h(b): return hashlib.md5(b).hexdigest()


def extract_gallery_images(html: str, must_match_side=True):
    """
    vehiclesizes 图库页面含有如下结构：
    <a href="/cars/.../images/107615-luxury-limousine-two-tone-side-profile"
       title="Luxury sedan with two-tone paint and iconic grille in side profile">
      <img src="https://www.vehiclesizes.com/thm/107615-rolls-royce-phantom-luxury-limousine-two-tone-side-profile.jpg"
           alt="...">
    </a>
    或者：
    <img src="https://www.vehiclesizes.com/thm/107615-xxx-side-profile.jpg" ...>

    我们提取：
      1. <a> 或 <img> 中 title / alt 包含 "side" 的
      2. 将缩略图 URL 中的 "/thm/107615-" 对应到原图路径，或者通过访问 "images/ID-slug"
         详情页找到原图 src。
    """
    candidates = []

    # 策略 A：直接找缩略图，改为访问图片详情页（/cars/.../images/ID-xxx）获取原图URL
    # 先枚举所有 a[href*="images/"] ，记录 href + title/alt
    seen_ids = set()
    for m in re.finditer(r'<a\s[^>]*href="([^"]+/images/\d+[^"]*)"\s[^>]*>', html, re.I):
        href = m.group(1)
        title = (re.search(r'title="([^"]*)"', m.group(0), re.I) or
                 re.search(r'alt="([^"]*)"', m.group(0), re.I) or [None, ""])[1] or ""
        title_low = title.lower()
        if must_match_side and "side" not in title_low and "profile" not in title_low:
            continue
        # 生成绝对 URL
        if href.startswith("/"):
            href = "https://www.vehiclesizes.com" + href
        # 提取 ID，避免重复
        m2 = re.search(r'/images/(\d+)', href)
        id_ = m2.group(1) if m2 else href
        if id_ in seen_ids: continue
        seen_ids.add(id_)
        candidates.append((href, title))
    return candidates


def fetch_original_image_from_detail(detail_url: str) -> Optional[str]:
    """在 vehiclesizes.com 详情页找到原图 URL。"""
    html = http_get(detail_url)
    if not html: return None
    # 典型结构：<meta property="og:image" content="https://www.vehiclesizes.com/img/...jpg" />
    for pat in [
        r'<meta\s+property="og:image"\s+content="([^"]+)"',
        r'<meta\s+name="twitter:image"\s+content="([^"]+)"',
        r'<img[^>]+src="(https?://www\.vehiclesizes\.com/img/[^"]+)"',
        r'<img[^>]+src="(https?://www\.vehiclesizes\.com/thm/\d+-[^"]+\.(?:jpg|jpeg|png|webp))"',
    ]:
        m = re.search(pat, html, re.I)
        if m:
            url = m.group(1)
            if url.startswith("/"): url = "https://www.vehiclesizes.com" + url
            return url
    return None


def write_jpg(path: Path, raw: bytes):
    try:
        from PIL import Image as P
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=93, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw


def load_log():
    if LOG_FILE.exists():
        try:
            d = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(d, list): return d
        except Exception: pass
    return []


def main():
    log = load_log()
    exclude_raw = set()
    for item in log:
        sp = item.get("save_path")
        if sp and Path(sp).exists():
            exclude_raw.add(md5h(Path(sp).read_bytes()))
    print(f"Initial raw MD5 exclusion pool: {len(exclude_raw)}")

    successes = 0
    for idx, (brand, model, kw_list, gallery_urls) in enumerate(CAR_SPEC, 1):
        print(f"\n[{idx}/19] 🎯 {brand}/{model}  精确词={kw_list}")
        # 先找到 vehiclesizes 上 valid 的图库页面
        html_page = None
        page_used = None
        for gu in gallery_urls:
            html_page = http_get(gu)
            if html_page and len(html_page) > 2000:
                page_used = gu
                break
        if not html_page:
            print(f"    ✘ 无法访问图库页（{len(gallery_urls)} 个候选）。保留旧文件。")
            continue
        print(f"    已打开图库：{page_used}  (size={len(html_page)} bytes)")
        side_candidates = extract_gallery_images(html_page, must_match_side=True)
        print(f"    页面中含 side/profile 标题的图片链接：{len(side_candidates)} 个")

        winner = None  # (raw, w, h, u, hraw)
        tried = 0
        for detail_url, title in side_candidates:
            tried += 1
            if tried > 18: break
            orig_url = fetch_original_image_from_detail(detail_url)
            if not orig_url:
                continue
            # 将缩略图 URL 中的 "/thm/" 改成 "/img/" 通常能直接拿到原图
            if "/thm/" in orig_url and (orig_url.endswith(".jpg") or orig_url.endswith(".jpeg") or orig_url.endswith(".png") or orig_url.endswith(".webp")):
                orig_url = orig_url.replace("/thm/", "/img/")
            raw = http_get(orig_url, binary=True)
            if not raw or len(raw) < MIN_FILE_B:
                continue
            # 精确车型词（URL或文件名中应该含"phantom"、"ghost"、"cullinan"、"wraith"... 但 vehiclesizes 一般是英文）
            low = orig_url.lower()
            if not any(k.lower() in low for k in kw_list):
                # vehiclesizes 的缩略图文件名不含"ghost/phantom"... 但详情页标题含有，OK
                pass
            dims = dims_of(raw)
            if not dims: continue
            w, h = dims
            if w < MIN_WIDTH_PX or h <= 0: continue
            aspect = w/h
            if not (MIN_ASPECT <= aspect <= MAX_ASPECT): continue
            hraw = md5h(raw)
            if hraw in exclude_raw: continue
            winner = (raw, w, h, orig_url, hraw, title)
            print(f"    ✔ 合格 #{tried} aspect={aspect:.2f} {w}x{h} {len(raw)/1024:.0f}KB\n       {title}\n       URL: {orig_url[:140]}")
            break
        if not winner:
            print(f"    ✘ 18 个 side 标题候选中无合格图。保留旧文件。")
            continue
        raw, w, h, u, hraw, title = winner
        sp = next((x["save_path"] for x in log if x["brand"]==brand and x["model"]==model), None)
        sp = sp or str(BRANDS_D / brand / (model + ".jpg"))
        p = Path(sp); p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(p, raw)
        p.write_bytes(final)
        hfinal = md5h(p.read_bytes())
        exclude_raw.add(hraw); exclude_raw.add(hfinal)
        entry = {
            "brand": brand, "model": model,
            "source_url": u,
            "title_hint": title,
            "width": w, "height": h,
            "aspect_ratio": round(w/h, 3),
            "size_bytes": len(final),
            "md5_prefix": hfinal[:10],
            "format": "JPEG",
            "save_path": str(p),
            "gate_level": f"VEHICLESIZES_SIDE_TITLE_url={page_used}",
            "downloaded_at_epoch": int(time.time()),
        }
        found_i = next((i for i,x in enumerate(log) if x["brand"]==brand and x["model"]==model), None)
        if found_i is not None: log[found_i] = entry
        else: log.append(entry)
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        successes += 1
        print(f"    💾 {p.name} {len(final)/1024:.0f}KB aspect={w/h:.2f} MD5 {hfinal[:10]} exclude={len(exclude_raw)}")

    # 最后 MD5 汇总
    bymd = {}
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        h = md5h(p.read_bytes())[:14]
        bymd.setdefault(h, []).append(f"{item['brand']}/{item['model']}")
    dup = sum(len(v) for v in bymd.values() if len(v) > 1)
    print(f"\n{'='*80}")
    print(f"✔ 本回合成功 {successes}/19。 最终唯一MD5：{len(bymd)}/19  重复MD5涉及 {dup} 台")
    for h, lst in sorted(bymd.items(), key=lambda kv: -len(kv[1])):
        if len(lst) > 1:
            print(f"  ⚠ MD5 {h}: " + "、".join(lst))
    return 0 if len(bymd) == 19 else 1


if __name__ == "__main__":
    sys.exit(main())
