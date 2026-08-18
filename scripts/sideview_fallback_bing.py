# -*- coding: utf-8 -*-
""" sideview_fallback_bing.py
备选方案：使用 Bing 图片搜索为7款剩余车型寻找正侧视图。
- 搜索关键词包含 "side view" / "side profile" / "正侧视"
- 严格过滤：URL必须包含 "side" 或 "profile" 关键词
- 长宽比 1.2~2.0（兼容留白官图）
- 横向分辨率 ≥ 1200px
- 文件大小 ≥ 80KB
- MD5去重
"""
import hashlib, io, json, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
LOG_FILE = CUR_DIR / "_sideview_fallback_log.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

# 7款需要替换的车型 + 搜索关键词
CARS_7 = [
    ("rolls-royce", "wraith", [
        "Rolls-Royce Wraith 2018 side profile official",
        "Rolls-Royce Wraith 正侧视图 官方",
        "Rolls-Royce Wraith side view press photo",
    ]),
    ("bentley", "bentayga", [
        "Bentley Bentayga 2021 side profile official",
        "Bentley Bentayga 正侧视图 官方",
        "Bentley Bentayga side view press photo",
    ]),
    ("bugatti", "chiron", [
        "Bugatti Chiron 2018 side profile official",
        "Bugatti Chiron 正侧视图 官方",
        "Bugatti Chiron side view press photo",
    ]),
    ("porsche", "911", [
        "Porsche 911 992 Carrera side profile official",
        "Porsche 911 992 正侧视图 官方",
        "Porsche 911 Carrera side view press photo",
    ]),
    ("porsche", "panamera", [
        "Porsche Panamera 2021 side profile official",
        "Porsche Panamera 正侧视图 官方",
        "Porsche Panamera side view press photo",
    ]),
    ("porsche", "cayenne", [
        "Porsche Cayenne 2021 side profile official",
        "Porsche Cayenne 正侧视图 官方",
        "Porsche Cayenne side view press photo",
    ]),
    ("ferrari", "f8-tributo", [
        "Ferrari F8 Tributo 2020 side profile official",
        "Ferrari F8 Tributo 正侧视图 官方",
        "Ferrari F8 Tributo side view press photo",
    ]),
]

# 已存在的MD5集合（用于去重）
EXISTING_MD5 = set()
for brand_dir in BRANDS_D.iterdir():
    if not brand_dir.is_dir():
        continue
    for img_file in brand_dir.glob("*.jpg"):
        try:
            EXISTING_MD5.add(hashlib.md5(img_file.read_bytes()).hexdigest()[:12])
        except Exception:
            pass


def fetch_url(url, timeout=20, headers=None):
    """通用URL获取，自动处理重定向"""
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


def bing_image_search(query, num_results=20):
    """通过Bing图片搜索获取图片URL列表"""
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1&tsc=ImageHoverTitle"
    raw, _ = fetch_url(url, timeout=15)
    if not raw:
        return []

    html = raw.decode("utf-8", errors="replace")
    # Bing 图片搜索结果中的图片URL通常在 murl 参数中
    img_urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
    # 也尝试 mediaurl
    img_urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
    # Bing 图片搜索结果也可能在 imgurl= 或 &p= 参数中
    img_urls += re.findall(r'imgurl=(https?[^&"\']+)', html)
    # 去重 + URL解码
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
        if ".jpg" in low or ".jpeg" in low or ".png" in low or ".webp" in low:
            result.append(u)
        if len(result) >= num_results:
            break
    return result


def download_image(url, timeout=25):
    """下载图片，返回bytes或None"""
    try:
        raw, final_url = fetch_url(url, timeout=timeout, headers={"Referer": "https://www.bing.com/"})
        return raw
    except Exception as e:
        print(f"    DL_ERR: {type(e).__name__}: {str(e)[:80]}")
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


def is_side_view_url(url):
    """判断URL是否暗示正侧视"""
    u = url.lower()
    side_kw = ["side", "profile", "lateral", "sideview", "side_view", "side-profile"]
    bad_kw = ["front", "rear", "interior", "dashboard", "wheel", "detail", "engine", "3-4", "34", "quarter"]
    has_side = any(k in u for k in side_kw)
    has_bad = any(k in u for k in bad_kw)
    return has_side and not has_bad


def verify_image(raw, brand, model):
    """验证图片质量。返回 (ok, w, h, reason)"""
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
            fmt = im.format
    except Exception as e:
        return False, 0, 0, f"parse fail: {e}"

    if w < 1000:
        return False, w, h, f"width too small {w}"
    if len(raw) < 50_000:
        return False, w, h, f"file too small {len(raw)/1024:.0f}KB"

    asp = w / h if h else 0
    # 正侧视长宽比1.2~2.5（允许留白）
    if asp < 1.2 or asp > 2.5:
        return False, w, h, f"aspect {asp:.2f} out of range"

    md5 = hashlib.md5(raw).hexdigest()[:12]
    if md5 in EXISTING_MD5:
        return False, w, h, f"MD5 duplicate {md5}"

    return True, w, h, f"OK {w}x{h} asp={asp:.2f} {len(raw)/1024:.0f}KB md5={md5}"


def process_car(brand, model, queries):
    """处理一辆车：尝试多个搜索查询"""
    print(f"\n{'='*60}")
    print(f"[{brand}/{model}]")

    # 收集所有候选URL
    all_candidates = []
    for q in queries:
        print(f"  Search: {q}")
        urls = bing_image_search(q, num_results=25)
        print(f"    Got {len(urls)} URLs")
        # 优先：URL含side/profile
        side_urls = [u for u in urls if is_side_view_url(u)]
        other_urls = [u for u in urls if u not in side_urls]
        all_candidates.extend([(u, "side_url") for u in side_urls])
        all_candidates.extend([(u, "other_url") for u in other_urls])
        time.sleep(2)

    # 去重
    seen = set()
    unique_candidates = []
    for u, tag in all_candidates:
        if u not in seen:
            seen.add(u)
            unique_candidates.append((u, tag))

    print(f"  Total unique candidates: {len(unique_candidates)} ({sum(1 for _,t in unique_candidates if t=='side_url')} side URLs)")

    # 尝试下载并验证
    for url, tag in unique_candidates:
        if tag == "side_url":
            print(f"  [SIDE] {url[:100]}")
        else:
            # 只试前5个非side URL
            if sum(1 for u, t in unique_candidates[:unique_candidates.index((url, tag))] if t == "other_url") >= 5:
                continue
            print(f"  [OTHER] {url[:100]}")

        time.sleep(1)
        raw = download_image(url)
        if not raw:
            continue

        ok, w, h, reason = verify_image(raw, brand, model)
        print(f"    {reason}")
        if not ok:
            continue

        # 保存
        p = BRANDS_D / brand / (model + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        EXISTING_MD5.add(md5)
        print(f"    💾 SAVED {p.name}")
        return True, url, w, h

    return False, None, 0, 0


def main():
    results = []
    for brand, model, queries in CARS_7:
        ok, url, w, h = process_car(brand, model, queries)
        results.append({"brand": brand, "model": model, "ok": ok, "url": url, "w": w, "h": h})

    # 写日志
    LOG_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    solved = sum(1 for r in results if r["ok"])
    print(f"Solved {solved}/{len(CARS_7)}")
    for r in results:
        status = "✓" if r["ok"] else "✗"
        print(f"  {status} {r['brand']}/{r['model']}")
    return 0 if solved == len(CARS_7) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
