#!/usr/bin/env python3
"""v15b: 修复 Porsche/Bugatti/Ferrari 候选图下载
Porsche: 用 .imaging/mte/ URL 模式
Bugatti: 下载所有 imgix URL，不激进排除
Ferrari: 用 cdn.ferrari.com/cms/network/media/img/ URL"""
import ssl, urllib.request, re, json, time, io, hashlib
from pathlib import Path
from PIL import Image

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15"
LOG_PATH = BASE / "scripts" / "_v15b_download_log.json"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except Exception:
        return None

def fetch_text(url, timeout=25):
    data = fetch(url, timeout)
    if data:
        return data.decode("utf-8", errors="replace")
    return None

def get_md5(data):
    return hashlib.md5(data).hexdigest()[:12]

def save_image(data, out_path):
    try:
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            im.convert("RGB").save(out_path, "JPEG", quality=90)
            return w, h, out_path.stat().st_size // 1024
    except Exception:
        return None

# ====================================================================
# Porsche Taycan: 用 .imaging/mte/ URL
# ====================================================================
def download_porsche_taycan():
    print("\n=== Porsche Taycan (v15b) ===", flush=True)
    car_dir = CAND_DIR / "porsche" / "taycan"
    car_dir.mkdir(parents=True, exist_ok=True)

    pages = [
        "https://newsroom.porsche.com/en/2024/products/porsche-the-new-taycan-turbo-gt-35479.html",
        "https://newsroom.porsche.com/en/2024/products/porsche-rounds-off-second-taycan-generation-37832.html",
        "https://newsroom.porsche.com/en/press-kits/taycan.html",
        "https://newsroom.porsche.com/en/press-kits/taycan/Highlights.html",
    ]

    all_urls = set()
    for page_url in pages:
        html = fetch_text(page_url)
        if not html:
            print(f"  无法获取: {page_url.split('/')[-1][:40]}", flush=True)
            continue
        # 提取 .imaging/mte/ 图片 URL（相对路径）
        imaging = re.findall(r'(/\.imaging/mte/[^"\'<>\s]+)', html)
        # 也提取 data-src
        imaging += re.findall(r'data-src="(/\.imaging/mte/[^"]+)"', html)
        for u in imaging:
            full = "https://newsroom.porsche.com" + u
            all_urls.add(full)
        print(f"  {page_url.split('/')[-1][:40]} -> {len(imaging)} URLs", flush=True)

    print(f"  总计 {len(all_urls)} 个唯一图片 URL", flush=True)

    cands = []
    idx = 0
    for url in sorted(all_urls):
        idx += 1
        out = car_dir / f"cand_{idx:02d}.jpg"
        data = fetch(url, timeout=20)
        if not data or len(data) < 3000:
            continue
        meta = save_image(data, out)
        if meta:
            w, h, kb = meta
            cands.append({"url": url, "filename": out.name, "w": w, "h": h, "kb": kb})
            print(f"  [{idx:02d}] {w}x{h} {kb}KB", flush=True)
        time.sleep(0.2)
        if idx >= 30:
            break

    print(f"  保存 {len(cands)} 张候选", flush=True)
    return {"porsche/taycan": cands}

# ====================================================================
# Bugatti: 下载所有 imgix URL（宽松排除）
# ====================================================================
def download_bugatti():
    results = {}
    models = {
        "chiron": "https://newsroom.bugatti.com/models/chiron",
        "veyron": "https://newsroom.bugatti.com/models/veyron",
        "divo": "https://newsroom.bugatti.com/models/divo",
    }
    # 仅排除明显的非车图（PDF缩略图、技术规格、其他车型混入）
    EXCLUDE = ["technical-specifications", ".pdf", "presskit", "pressemitteilung",
               "tourbillon", "bolide", "mistral", "centodieci", "brouillard",
               "eb-110", "looking-forward", "rolling-chassis", "solitaire",
               "destrier", "singh", "winkelmann", "spengler", "steve-jenny",
               "las-vegas-concours", "broward", "geneva-opening"]

    for model, page_url in models.items():
        print(f"\n=== Bugatti {model} (v15b) ===", flush=True)
        car_dir = CAND_DIR / "bugatti" / model
        car_dir.mkdir(parents=True, exist_ok=True)
        # 清空旧候选
        for f in car_dir.glob("cand_*.jpg"):
            f.unlink()

        html = fetch_text(page_url)
        if not html:
            print(f"  无法获取页面", flush=True)
            results[f"bugatti/{model}"] = []
            continue

        # 提取所有 imgix URL
        import html as html_mod
        html = html_mod.unescape(html)
        urls = re.findall(r'https://bugatti-newsroom\.imgix\.net/[a-f0-9-]+/[^"\'<>\s?\&]+', html)
        # 去重
        seen = set()
        unique = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        print(f"  提取到 {len(unique)} 个唯一 URL", flush=True)

        cands = []
        idx = 0
        for url in unique:
            url_lower = url.lower()
            if any(ex in url_lower for ex in EXCLUDE):
                continue
            idx += 1
            # 用 imgix w=1200 下载（保持比例）
            dl_url = url + "?w=1200"
            out = car_dir / f"cand_{idx:02d}.jpg"
            data = fetch(dl_url, timeout=20)
            if not data or len(data) < 3000:
                continue
            meta = save_image(data, out)
            if meta:
                w, h, kb = meta
                fname = url.split("/")[-1][:40]
                cands.append({"url": url, "filename": out.name, "w": w, "h": h, "kb": kb})
                print(f"  [{idx:02d}] {w}x{h} {kb}KB {fname}", flush=True)
            time.sleep(0.2)
            if idx >= 30:
                break

        results[f"bugatti/{model}"] = cands
        print(f"  保存 {len(cands)} 张候选", flush=True)
    return results

# ====================================================================
# Ferrari: 用 cdn.ferrari.com CMS URL
# ====================================================================
FERRARI_PAGES = {
    "sf90": [
        "https://www.ferrari.com/en-IN/auto/sf90-stradale",
        "https://www.ferrari.com/en-EN/auto/sf90-stradale",
    ],
    "f8-tributo": [
        "https://www.ferrari.com/en-IN/auto/f8-tributo",
        "https://www.ferrari.com/en-EN/auto/f8-tributo",
    ],
    "roma": [
        "https://www.ferrari.com/en-IN/auto/roma",
        "https://www.ferrari.com/en-EN/auto/roma",
    ],
}

def download_ferrari():
    results = {}
    for model, pages in FERRARI_PAGES.items():
        print(f"\n=== Ferrari {model} (v15b) ===", flush=True)
        car_dir = CAND_DIR / "ferrari" / model
        car_dir.mkdir(parents=True, exist_ok=True)
        for f in car_dir.glob("cand_*.jpg"):
            f.unlink()

        all_urls = set()
        for page_url in pages:
            html = fetch_text(page_url, timeout=20)
            if not html:
                print(f"  无法获取: {page_url}", flush=True)
                continue
            # 提取 cdn.ferrari.com 图片 URL
            import html as html_mod
            html = html_mod.unescape(html)
            cdn_urls = re.findall(r'https://cdn\.ferrari\.com/cms/network/media/img/[^"\'<>\s]+', html)
            for u in cdn_urls:
                # 去掉 query 参数
                clean = u.split("?")[0]
                all_urls.add(clean)
            print(f"  {page_url.split('/')[-1]} -> {len(cdn_urls)} URLs", flush=True)

        print(f"  总计 {len(all_urls)} 个唯一 CDN URL", flush=True)

        cands = []
        idx = 0
        for url in sorted(all_urls):
            # 跳过小图标/social media 图
            url_lower = url.lower()
            if any(x in url_lower for x in ["facebook", "instagram", "linkedin", "tiktok",
                                             "twitch", "twitter", "youtube", "logo", "icon",
                                             "emissions", "wltp", "thumb-"]):
                continue
            idx += 1
            # 用高分辨率下载: ?width=1920
            dl_url = url + "?width=1920"
            out = car_dir / f"cand_{idx:02d}.jpg"
            data = fetch(dl_url, timeout=20)
            if not data or len(data) < 5000:
                # 尝试不带参数
                data = fetch(url, timeout=20)
                if not data or len(data) < 5000:
                    continue
            meta = save_image(data, out)
            if meta:
                w, h, kb = meta
                name = url.split("-")[-1][:40] if "-" in url else url.split("/")[-1][:40]
                cands.append({"url": url, "filename": out.name, "w": w, "h": h, "kb": kb})
                print(f"  [{idx:02d}] {w}x{h} {kb}KB {name}", flush=True)
            time.sleep(0.2)
            if idx >= 20:
                break

        results[f"ferrari/{model}"] = cands
        print(f"  保存 {len(cands)} 张候选", flush=True)
    return results

# ====================================================================
def main():
    all_results = {}
    print("=" * 60, flush=True)
    print("v15b: 修复 Porsche/Bugatti/Ferrari 候选下载", flush=True)
    print("=" * 60, flush=True)

    try:
        all_results.update(download_porsche_taycan())
    except Exception as e:
        print(f"Porsche 出错: {e}", flush=True)

    try:
        all_results.update(download_bugatti())
    except Exception as e:
        print(f"Bugatti 出错: {e}", flush=True)

    try:
        all_results.update(download_ferrari())
    except Exception as e:
        print(f"Ferrari 出错: {e}", flush=True)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60, flush=True)
    print("v15b 下载完成:", flush=True)
    total = 0
    for key, cands in all_results.items():
        print(f"  {key}: {len(cands)} 张", flush=True)
        total += len(cands)
    print(f"  总计: {total} 张", flush=True)

if __name__ == "__main__":
    main()
