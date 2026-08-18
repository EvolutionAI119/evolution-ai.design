# -*- coding: utf-8 -*-
""" download_candidates_v7.py
不做域名过滤，直接下载所有候选，浏览器视觉验证后选择最佳。
每款车用包含车型名的精确查询，确保不同车型返回不同结果。
"""
import hashlib, io, json, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
BRANDS_D = PROJECT / "public" / "brands"
CAND_D = CUR_DIR / "_candidates"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

# 精确搜索词：年份+品牌+车型+侧视图
CARS = [
    ("rolls-royce", "phantom",         "2020 Rolls-Royce Phantom side profile"),
    ("rolls-royce", "ghost",            "2021 Rolls-Royce Ghost side profile"),
    ("rolls-royce", "cullinan",         "2020 Rolls-Royce Cullinan side profile"),
    ("rolls-royce", "wraith",           "2016 Rolls-Royce Wraith side profile"),
    ("bentley",     "continental-gt",   "2019 Bentley Continental GT side profile"),
    ("bentley",     "continental-gtc",  "2020 Bentley Continental GTC side profile"),
    ("bentley",     "flying-spur",      "2020 Bentley Flying Spur side profile"),
    ("bentley",     "bentayga",         "2020 Bentley Bentayga side profile"),
    ("bugatti",     "chiron",           "2016 Bugatti Chiron side profile"),
    ("bugatti",     "veyron",           "2005 Bugatti Veyron side profile"),
    ("bugatti",     "divo",             "2019 Bugatti Divo side profile"),
    ("porsche",     "911",              "2020 Porsche 911 Carrera side profile"),
    ("porsche",     "taycan",           "2020 Porsche Taycan side profile"),
    ("porsche",     "panamera",         "2020 Porsche Panamera side profile"),
    ("porsche",     "cayenne",          "2019 Porsche Cayenne side profile"),
    ("porsche",     "macan",            "2020 Porsche Macan side profile"),
    ("ferrari",     "sf90",             "2020 Ferrari SF90 Stradale side profile"),
    ("ferrari",     "f8-tributo",       "2019 Ferrari F8 Tributo side profile"),
    ("ferrari",     "roma",             "2020 Ferrari Roma side profile"),
]

BAD_KEYWORDS = ["abstract", "wallpaper", "texture", "pattern", "gradient",
                "cgmodel", "3dmodel", "render", "hdqwall", "wallpaperaccess"]

def fetch_url(url, timeout=20):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    req = urllib.request.Request(url, headers=h)
    ctx = ssl._create_unverified_context()
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

def download_img(url, timeout=20):
    try:
        h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
             "Referer": "https://www.bing.com/"}
        req = urllib.request.Request(url, headers=h)
        ctx = ssl._create_unverified_context()
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

def bing_search(query, max_results=80):
    all_urls = []
    for first in [1, 51]:
        url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&first={first}&tsc=ImageBasicHover"
        raw = fetch_url(url, timeout=15)
        if not raw:
            continue
        html = raw.decode("utf-8", errors="replace")
        urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
        urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
        all_urls.extend(urls)
        time.sleep(1.5)

    seen = set()
    result = []
    for u in all_urls:
        u = urllib.parse.unquote(u).strip()
        if u in seen or not u.startswith("http"):
            continue
        seen.add(u)
        low = u.lower()
        if not any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            continue
        # 排除明显坏域名
        if any(b in low for b in BAD_KEYWORDS):
            continue
        result.append(u)
        if len(result) >= max_results:
            break
    return result

def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=88, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw

def main():
    results = {}
    global_md5 = set()

    for idx, (brand, model, query) in enumerate(CARS, 1):
        print(f"\n[{idx}/19] {brand}/{model}", flush=True)

        # 清理候选目录
        car_dir = CAND_D / brand / model
        if car_dir.exists():
            for f in car_dir.glob("*.jpg"):
                f.unlink()
        car_dir.mkdir(parents=True, exist_ok=True)

        urls = bing_search(query)
        print(f"  {len(urls)} URLs found", flush=True)

        candidates = []
        for ci, url in enumerate(urls):
            if len(candidates) >= 8:
                break
            # URL中必须包含品牌或车型关键词（排除明显不相关）
            low_url = url.lower()
            car_kw = model.lower().replace("-", "")
            brand_kw = brand.lower().replace("-", "")
            # 放宽：不强制URL包含关键词，因为很多图片URL不含车型名

            time.sleep(0.3)
            raw = download_img(url)
            if not raw or len(raw) < 40_000:
                continue
            try:
                with P.open(io.BytesIO(raw)) as im:
                    w, h = im.size
            except Exception:
                continue
            if w < 600:
                continue
            asp = w / h if h else 0
            if asp < 1.1 or asp > 3.0:
                continue

            final = write_jpg(raw)
            md5 = hashlib.md5(final).hexdigest()[:10]
            if md5 in global_md5:
                continue
            global_md5.add(md5)

            cand_path = car_dir / f"cand_{len(candidates):02d}.jpg"
            cand_path.write_bytes(final)
            candidates.append({
                "idx": len(candidates),
                "url": url[:200],
                "w": w, "h": h, "asp": round(asp, 2),
                "kb": len(final) // 1024,
                "md5": md5,
                "file": str(cand_path.relative_to(PROJECT)).replace("\\", "/"),
            })
            print(f"  [{len(candidates)-1}] {w}x{h} asp={asp:.2f} {len(final)//1024}KB", flush=True)

        results[f"{brand}/{model}"] = candidates
        print(f"  → {len(candidates)} candidates", flush=True)

    # 保存JSON
    (CAND_D / "_info.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # 生成预览HTML
    html_lines = [
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Candidates</title>',
        '<style>',
        'body{background:#1a1a2e;color:#eee;font-family:sans-serif;margin:0;padding:20px}',
        '.car{margin-bottom:25px;border:1px solid #444;padding:12px;border-radius:8px}',
        '.car h2{color:#e94560;font-size:16px;margin:0 0 8px}',
        '.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}',
        '.c{background:#16213e;border-radius:4px;overflow:hidden;padding:4px;text-align:center}',
        '.c img{width:100%;height:100px;object-fit:contain;background:#000}',
        '.c .i{font-size:9px;color:#888;margin-top:2px}',
        '.c .sel{font-size:10px;color:#0f0;font-weight:bold}',
        '</style></head><body>',
        '<h1>候选图预览 - 选择最佳正侧视图</h1>',
    ]
    for idx, (brand, model, query) in enumerate(CARS, 1):
        key = f"{brand}/{model}"
        cands = results.get(key, [])
        html_lines.append(f'<div class="car"><h2>{idx}. {brand}/{model} ({len(cands)})</h2><div class="grid">')
        for c in cands:
            html_lines.append(
                f'<div class="c"><img src="/{c["file"]}">'
                f'<div class="i">{c["w"]}x{c["h"]} a={c["asp"]} {c["kb"]}KB</div>'
                f'<div class="i">#{c["idx"]} md5={c["md5"]}</div></div>'
            )
        html_lines.append('</div></div>')

    html_lines.append('</body></html>')
    (PROJECT / "public" / "_candidates_preview.html").write_text(
        "\n".join(html_lines), encoding="utf-8")

    total = sum(len(v) for v in results.values())
    print(f"\n{'='*60}", flush=True)
    print(f"Total: {total} candidates for 19 cars", flush=True)
    print(f"Preview: http://localhost:5173/_candidates_preview.html", flush=True)

if __name__ == "__main__":
    main()
