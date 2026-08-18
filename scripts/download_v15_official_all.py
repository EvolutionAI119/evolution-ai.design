#!/usr/bin/env python3
"""
v15: 官网方法论 —— 下载所有官方候选图，供逐张视觉验证
=====================================================
方法论纠正：
  - 之前用宽高比选图（1.78），但 3/4 角度图也是 1.78 → 选错
  - 现在下载所有官方候选图，不按宽高比筛选，全部保存供视觉验证
  - 来源：仅各品牌官网媒体库（BMW mediapool / Bugatti newsroom / Bentley motors / Porsche newsroom）

13款不合格车型：
  - Rolls-Royce: ghost, cullinan (BMW mediapool)
  - Bugatti: chiron, veyron, divo (bugatti-newsroom.imgix.net)
  - Bentley: continental-gt, continental-gtc, flying-spur, bentayga (bentleymotors.com)
  - Porsche: taycan (newsroom.porsche.com)
  - Ferrari: sf90, f8-tributo, roma (尝试多种官方源)
"""
import os, sys, json, time, ssl, io, re, hashlib
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
from PIL import Image

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15"
LOG_PATH = BASE / "scripts" / "_v15_download_log.json"
TIMEOUT = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=TIMEOUT, headers=None):
    hdr = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8"}
    if headers:
        hdr.update(headers)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            data = resp.read()
            return data
    except Exception:
        return None

def fetch_text(url, timeout=TIMEOUT):
    data = fetch(url, timeout)
    if data:
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return None
    return None

def get_md5(data):
    return hashlib.md5(data).hexdigest()[:12]

def save_image(data, out_path):
    """保存图片，返回 (w, h, kb) 或 None"""
    try:
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            im.convert("RGB").save(out_path, "JPEG", quality=90)
            kb = out_path.stat().st_size // 1024
            return w, h, kb
    except Exception:
        # 可能是 PNG/WebP，用 PIL 转换
        try:
            with Image.open(io.BytesIO(data)) as im:
                w, h = im.size
                im.convert("RGB").save(out_path, "JPEG", quality=90)
                kb = out_path.stat().st_size // 1024
                return w, h, kb
        except Exception:
            return None

def download_and_save(url, out_path, small_w=600):
    """下载图片并保存，返回元数据 dict。若 small_w 指定，用 imgix 参数下载小图。
    注意：不使用 fit=crop，保持原始宽高比以便判断视角。"""
    dl_url = url
    # 如果是 imgix URL，仅限宽缩放，保持原始比例（不加 fit=crop）
    if "imgix.net" in url and "?" not in url:
        dl_url = url + f"?w={small_w}"
    elif "imgix.net" in url and "w=" not in url:
        dl_url = url + f"&w={small_w}"

    data = fetch(dl_url, timeout=25)
    if not data or len(data) < 3000:
        return None
    result = save_image(data, out_path)
    if not result:
        return None
    w, h, kb = result
    return {"url": url, "dl_url": dl_url, "w": w, "h": h, "kb": kb, "md5": get_md5(data)}

# ====================================================================
# 1. Rolls-Royce: BMW mediapool (Ghost, Cullinan)
# ====================================================================
BMW_POOL = "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo={dok}&attachment=1&actEvent=image"

RR_DOKS = {
    "ghost": [
        "P90401223", "P90401224", "P90612626",
        "P90651071", "P90651072", "P90651074", "P90651076", "P90651078",
        "P90649576", "P90649577", "P90649578", "P90649579", "P90649580", "P90649581",
    ],
    "cullinan": [
        "P90549024", "P90549026", "P90549025",
        "P90403691", "P90403692", "P90403693", "P90403694", "P90403695",
        "P90403696", "P90403697", "P90403698", "P90403699", "P90403700",
        "P90403701", "P90403702", "P90403703", "P90403704", "P90403705",
        "P90403706", "P90403707", "P90403708", "P90403709", "P90403710",
        "P90403711", "P90403712", "P90403713", "P90403714", "P90403715",
        "P90403716", "P90403717", "P90403718", "P90403719", "P90403720",
        "P90403721", "P90403722", "P90403723",
    ],
}

def download_rolls_royce():
    """下载 Rolls-Royce Ghost 和 Cullinan 的所有 BMW mediapool 候选"""
    results = {}
    for model, doks in RR_DOKS.items():
        print(f"\n=== Rolls-Royce {model} ({len(doks)} doks) ===", flush=True)
        car_dir = CAND_DIR / "rolls-royce" / model
        car_dir.mkdir(parents=True, exist_ok=True)
        cands = []
        for i, dok in enumerate(doks, 1):
            url = BMW_POOL.format(dok=dok)
            out = car_dir / f"cand_{i:02d}_{dok}.jpg"
            meta = download_and_save(url, out, small_w=0)  # BMW mediapool 不用 imgix
            if meta:
                meta["dok"] = dok
                meta["filename"] = out.name
                cands.append(meta)
                print(f"  [{i:02d}] {dok} {meta['w']}x{meta['h']} {meta['kb']}KB", flush=True)
            else:
                print(f"  [{i:02d}] {dok} FAIL", flush=True)
            time.sleep(0.3)
        results[f"rolls-royce/{model}"] = cands
    return results

# ====================================================================
# 2. Bugatti: bugatti-newsroom.imgix.net (Chiron, Veyron, Divo)
# ====================================================================
BUGATTI_MODELS = {
    "chiron": "https://newsroom.bugatti.com/models/chiron",
    "veyron": "https://newsroom.bugatti.com/models/veyron",
    "divo": "https://newsroom.bugatti.com/models/divo",
}

# 排除变体关键词
BUGATTI_EXCLUDE = ["profilee", "centodieci", "la-voiture", "mistral", "bolide",
                   "tourbillon", "brouillard", "eb-110", "remise", "breakfast",
                   "episode", "looking-forward", "rolling-chassis", "roadster",
                   "singh", "solitaire", "destrier", "geneva-opening", "world-premiere"]

def extract_bugatti_urls(html):
    """从 Bugatti newsroom HTML 提取 imgix 图片 URL"""
    import html as html_mod
    html = html_mod.unescape(html)
    # 匹配 imgix URL（文件名可含空格和特殊字符）
    pattern = r'https://bugatti-newsroom\.imgix\.net/[a-f0-9-]+/[^"\'<>\s]+'
    urls = re.findall(pattern, html)
    # 去重，保持顺序
    seen = set()
    unique = []
    for u in urls:
        # 去掉 query 参数
        clean = u.split("?")[0]
        if clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return unique

def download_bugatti():
    """下载 Bugatti 3 款车的所有 newsroom 候选图"""
    results = {}
    for model, page_url in BUGATTI_MODELS.items():
        print(f"\n=== Bugatti {model} ===", flush=True)
        car_dir = CAND_DIR / "bugatti" / model
        car_dir.mkdir(parents=True, exist_ok=True)

        html = fetch_text(page_url)
        if not html:
            print(f"  无法获取页面: {page_url}", flush=True)
            results[f"bugatti/{model}"] = []
            continue

        urls = extract_bugatti_urls(html)
        print(f"  提取到 {len(urls)} 个图片 URL", flush=True)

        cands = []
        idx = 0
        for url in urls:
            url_lower = url.lower()
            # 排除变体和非侧视图
            if any(ex in url_lower for ex in BUGATTI_EXCLUDE):
                continue
            idx += 1
            # 用 imgix 下载 1200px 宽的小图用于验证
            out = car_dir / f"cand_{idx:02d}.jpg"
            meta = download_and_save(url, out, small_w=1200)
            if meta:
                meta["filename"] = out.name
                cands.append(meta)
                print(f"  [{idx:02d}] {meta['w']}x{meta['h']} {meta['kb']}KB {url.split('/')[-1][:40]}", flush=True)
            time.sleep(0.2)
            if idx >= 25:
                break
        results[f"bugatti/{model}"] = cands
        print(f"  保存 {len(cands)} 张候选", flush=True)
    return results

# ====================================================================
# 3. Bentley: bentleymotors.com (4 cars)
# ====================================================================
BENTLEY_MODELS = {
    "continental-gt": "https://www.bentleymotors.com/en/models/continental-gt.html",
    "continental-gtc": "https://www.bentleymotors.com/en/models/continental-gt/continental-gt.html",
    "flying-spur": "https://www.bentleymotors.com/en/models/flying-spur.html",
    "bentayga": "https://www.bentleymotors.com/en/models/bentayga.html",
}

def extract_bentley_urls(html):
    """从 Bentley 页面提取图片 URL"""
    import html as html_mod
    html = html_mod.unescape(html)
    # Bentley 图片通常在 /content/dam/ 路径下
    patterns = [
        r'https://www\.bentleymotors\.com/[^"\'<>\s]+\.(?:jpg|jpeg|png|webp)',
        r'/content/dam/[^"\'<>\s]+\.(?:jpg|jpeg|png|webp)',
        r'https://[^"\'<>\s]*bentley[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
    ]
    urls = set()
    for pat in patterns:
        found = re.findall(pat, html, re.IGNORECASE)
        for u in found:
            if u.startswith("/"):
                u = "https://www.bentleymotors.com" + u
            urls.add(u)
    # 过滤掉小图标/logo
    filtered = [u for u in urls if "icon" not in u.lower() and "logo" not in u.lower()
                and "sprite" not in u.lower()]
    return filtered

def download_bentley():
    """下载 Bentley 4 款车的候选图"""
    results = {}
    for model, page_url in BENTLEY_MODELS.items():
        print(f"\n=== Bentley {model} ===", flush=True)
        car_dir = CAND_DIR / "bentley" / model
        car_dir.mkdir(parents=True, exist_ok=True)

        html = fetch_text(page_url)
        if not html:
            print(f"  无法获取页面: {page_url}", flush=True)
            results[f"bentley/{model}"] = []
            continue

        urls = extract_bentley_urls(html)
        print(f"  提取到 {len(urls)} 个图片 URL", flush=True)

        cands = []
        idx = 0
        for url in urls:
            idx += 1
            out = car_dir / f"cand_{idx:02d}.jpg"
            data = fetch(url, timeout=20)
            if not data or len(data) < 5000:
                continue
            meta = save_image(data, out)
            if meta:
                w, h, kb = meta
                cands.append({"url": url, "filename": out.name, "w": w, "h": h, "kb": kb, "md5": get_md5(data)})
                print(f"  [{idx:02d}] {w}x{h} {kb}KB", flush=True)
            time.sleep(0.2)
            if idx >= 20:
                break
        results[f"bentley/{model}"] = cands
        print(f"  保存 {len(cands)} 张候选", flush=True)
    return results

# ====================================================================
# 4. Porsche Taycan: newsroom.porsche.com
# ====================================================================
PORSCHE_TAYCAN_PAGES = [
    "https://newsroom.porsche.com/en/2024/products/porsche-the-new-taycan-turbo-gt-35479.html",
    "https://newsroom.porsche.com/en/2024/products/porsche-rounds-off-second-taycan-generation-37832.html",
    "https://newsroom.porsche.com/en/2026/products/new-innovations-for-taycan-model-year-update-42861.html",
    "https://newsroom.porsche.com/en/press-kits/taycan.html",
    "https://newsroom.porsche.com/en/press-kits/taycan/Highlights.html",
    "https://newsroom.porsche.com/en/2024/products/porsche-taycan-turbo-s-and-taycan-4s-35488.html",
    "https://newsroom.porsche.com/en/2020/products/porsche-taycan-turbo-s-18289.html",
    "https://newsroom.porsche.com/en/2019/products/porsche-taycan-18957.html",
]

def extract_porsche_urls(html):
    """从 Porsche newsroom 页面提取 /dam/jcr: 图片 URL"""
    import html as html_mod
    html = html_mod.unescape(html)
    pattern = r'https://newsroom\.porsche\.com/dam/jcr:[a-f0-9-]+/[^"\'<>\s]+\.(?:jpg|jpeg|png)'
    urls = re.findall(pattern, html, re.IGNORECASE)
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

def download_porsche_taycan():
    """下载 Porsche Taycan 的所有 newsroom 候选图"""
    print(f"\n=== Porsche Taycan ===", flush=True)
    car_dir = CAND_DIR / "porsche" / "taycan"
    car_dir.mkdir(parents=True, exist_ok=True)

    all_urls = set()
    for page_url in PORSCHE_TAYCAN_PAGES:
        html = fetch_text(page_url)
        if not html:
            print(f"  无法获取: {page_url}", flush=True)
            continue
        urls = extract_porsche_urls(html)
        print(f"  {page_url.split('/')[-1][:40]} -> {len(urls)} URLs", flush=True)
        all_urls.update(urls)
        time.sleep(0.3)

    print(f"  总计 {len(all_urls)} 个唯一图片 URL", flush=True)

    cands = []
    idx = 0
    for url in sorted(all_urls):
        idx += 1
        out = car_dir / f"cand_{idx:02d}.jpg"
        data = fetch(url, timeout=25)
        if not data or len(data) < 5000:
            continue
        meta = save_image(data, out)
        if meta:
            w, h, kb = meta
            cands.append({"url": url, "filename": out.name, "w": w, "h": h, "kb": kb, "md5": get_md5(data)})
            print(f"  [{idx:02d}] {w}x{h} {kb}KB {url.split('/')[-1][:40]}", flush=True)
        time.sleep(0.3)
        if idx >= 30:
            break

    print(f"  保存 {len(cands)} 张候选", flush=True)
    return {"porsche/taycan": cands}

# ====================================================================
# 5. Ferrari: 尝试多种官方源
# ====================================================================
# Ferrari media.ferrari.com 403，尝试 ferrari.com 新闻稿页面
FERRARI_PAGES = {
    "sf90": [
        "https://www.ferrari.com/en-EN/magazine/articles/innovation/ferrari-sf90-stradale",
        "https://www.ferrari.com/en-EN/auto/sf90-stradale.html",
    ],
    "f8-tributo": [
        "https://www.ferrari.com/en-EN/magazine/articles/f8-tributo",
        "https://www.ferrari.com/en-EN/auto/f8-tributo.html",
    ],
    "roma": [
        "https://www.ferrari.com/en-EN/magazine/articles/design/ferrari-roma",
        "https://www.ferrari.com/en-EN/auto/roma.html",
    ],
}

def extract_ferrari_urls(html):
    """从 Ferrari 页面提取图片 URL"""
    import html as html_mod
    html = html_mod.unescape(html)
    patterns = [
        r'https://[^"\'<>\s]*ferrari[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
        r'https://cdn[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
        r'https://images[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
    ]
    urls = set()
    for pat in patterns:
        found = re.findall(pat, html, re.IGNORECASE)
        for u in found:
            if "icon" not in u.lower() and "logo" not in u.lower():
                urls.add(u)
    return list(urls)

def download_ferrari():
    """尝试从 Ferrari 官网下载候选图"""
    results = {}
    for model, pages in FERRARI_PAGES.items():
        print(f"\n=== Ferrari {model} ===", flush=True)
        car_dir = CAND_DIR / "ferrari" / model
        car_dir.mkdir(parents=True, exist_ok=True)

        all_urls = set()
        for page_url in pages:
            html = fetch_text(page_url, timeout=20)
            if not html:
                print(f"  无法获取: {page_url}", flush=True)
                continue
            urls = extract_ferrari_urls(html)
            print(f"  {page_url.split('/')[-1][:30]} -> {len(urls)} URLs", flush=True)
            all_urls.update(urls)
            time.sleep(0.3)

        cands = []
        idx = 0
        for url in sorted(all_urls):
            idx += 1
            out = car_dir / f"cand_{idx:02d}.jpg"
            data = fetch(url, timeout=20)
            if not data or len(data) < 5000:
                continue
            meta = save_image(data, out)
            if meta:
                w, h, kb = meta
                cands.append({"url": url, "filename": out.name, "w": w, "h": h, "kb": kb, "md5": get_md5(data)})
                print(f"  [{idx:02d}] {w}x{h} {kb}KB", flush=True)
            time.sleep(0.2)
            if idx >= 15:
                break

        results[f"ferrari/{model}"] = cands
        print(f"  保存 {len(cands)} 张候选", flush=True)
    return results

# ====================================================================
# 主流程
# ====================================================================
def main():
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    all_results = {}

    print("=" * 60, flush=True)
    print("v15: 官网方法论 —— 下载所有官方候选图", flush=True)
    print("=" * 60, flush=True)

    # 1. Rolls-Royce
    try:
        all_results.update(download_rolls_royce())
    except Exception as e:
        print(f"Rolls-Royce 下载出错: {e}", flush=True)

    # 2. Bugatti
    try:
        all_results.update(download_bugatti())
    except Exception as e:
        print(f"Bugatti 下载出错: {e}", flush=True)

    # 3. Bentley
    try:
        all_results.update(download_bentley())
    except Exception as e:
        print(f"Bentley 下载出错: {e}", flush=True)

    # 4. Porsche Taycan
    try:
        all_results.update(download_porsche_taycan())
    except Exception as e:
        print(f"Porsche Taycan 下载出错: {e}", flush=True)

    # 5. Ferrari
    try:
        all_results.update(download_ferrari())
    except Exception as e:
        print(f"Ferrari 下载出错: {e}", flush=True)

    # 保存日志
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # 汇总
    print("\n" + "=" * 60, flush=True)
    print("下载完成汇总:", flush=True)
    total = 0
    for key, cands in all_results.items():
        print(f"  {key}: {len(cands)} 张候选", flush=True)
        total += len(cands)
    print(f"  总计: {total} 张候选", flush=True)
    print(f"  日志: {LOG_PATH}", flush=True)
    print(f"  候选目录: {CAND_DIR}", flush=True)

if __name__ == "__main__":
    main()
