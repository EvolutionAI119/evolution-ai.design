#!/usr/bin/env python3
"""
v17: 下载 Ferrari Roma 候选图（多源策略）
==========================================
策略：
  1. vehiclesizes.com Roma 图片画廊（聚合官方图）
  2. Bing 图片搜索（中文+英文关键词，过滤汽车域名）
所有候选保存到 public/_candidates_v15/ferrari/roma/ 供视觉验证
"""
import os, sys, json, time, ssl, io, re, hashlib
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
from PIL import Image

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15" / "ferrari" / "roma"
LOG_PATH = BASE / "scripts" / "_roma_v17_log.json"
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
            return resp.read()
    except Exception:
        return None


def fetch_text(url, timeout=TIMEOUT, headers=None):
    data = fetch(url, timeout, headers=headers)
    if data:
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return None
    return None


def save_image(data, out_path):
    try:
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            im.convert("RGB").save(out_path, "JPEG", quality=90)
            kb = out_path.stat().st_size // 1024
            return w, h, kb
    except Exception:
        return None


# 汽车相关域名白名单（排除壁纸站/素材站）
CAR_DOMAINS = ["carbuzz", "autoevolution", "motor1", "topspeed", "caranddriver",
               "edmunds", "porsche", "bentley", "rolls-royce", "bugatti", "ferrari",
               "netcarshow", "automobile", "auto", "car", "drive", "motor", "wheel",
               "bitautoimg", "pcauto", "xcar", "sinaimg", "smzdm", "bitauto",
               "puxiang", "sohu", "ifeng", "autoimg", "vehiclesizes", "autoscout",
               "mobile01", "cncn", "autohome", "xcarimg", "gasgoo", "china"]

BAD_KEYWORDS = ["wallpaper", "background", "texture", "pattern", "icon", "logo",
                "shutterstock", "istockphoto", "gettyimages", "dreamstime",
                "pixabay", "pinterest", "pinimg", "jooinn", "freepik", "pngtree"]


def is_car_url(url):
    low = url.lower()
    if any(bad in low for bad in BAD_KEYWORDS):
        return False
    return any(d in low for d in CAR_DOMAINS)


def bing_image_search(query, num_results=30):
    """Bing 图片搜索，返回图片 URL 列表"""
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1&tsc=ImageHoverTitle"
    raw = fetch(url, timeout=15, headers={"Referer": "https://www.bing.com/"})
    if not raw:
        return []
    html = raw.decode("utf-8", errors="replace")
    # 多种正则匹配图片 URL
    img_urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
    img_urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
    img_urls += re.findall(r'imgurl=(https?[^&"\']+)', html)
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
        if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            result.append(u)
        if len(result) >= num_results:
            break
    return result


def extract_vehiclesizes_images(html):
    """从 vehiclesizes.com 页面提取图片 URL"""
    # 匹配图片画廊中的图片 URL
    patterns = [
        r'https://www\.vehiclesizes\.com/images/[^"\'<>\s]+\.(?:jpg|jpeg|png)',
        r'https://www\.vehiclesizes\.com/thm/[^"\'<>\s]+\.(?:jpg|jpeg|png)',
        r'src=["\']([^"\']*vehiclesizes[^"\']*\.(?:jpg|jpeg|png))["\']',
        r'data-src=["\']([^"\']*vehiclesizes[^"\']*\.(?:jpg|jpeg|png))["\']',
    ]
    urls = set()
    for pat in patterns:
        found = re.findall(pat, html, re.IGNORECASE)
        for u in found:
            urls.add(u)
    return list(urls)


def main():
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60, flush=True)
    print("v17: 下载 Ferrari Roma 候选图（多源）", flush=True)
    print("=" * 60, flush=True)

    all_urls = set()
    log = {"sources": [], "candidates": []}

    # 1. vehiclesizes.com Roma 图片画廊
    print("\n--- 阶段1: vehiclesizes.com ---", flush=True)
    vs_pages = [
        "https://www.vehiclesizes.com/cars/ferrari/roma/roma-coupe-2020/images/",
        "https://www.vehiclesizes.com/cars/ferrari/roma/roma-coupe-2020/images/85445-sleek-side-profile-matte-gray-sports-coupe",
        "https://www.vehiclesizes.com/cars/ferrari/roma/roma-coupe-2020/images/18226-ferrari-roma-aerodynamic-front-end-sleek-headlights-grille",
    ]
    for page_url in vs_pages:
        print(f"  尝试: {page_url}", flush=True)
        html = fetch_text(page_url, timeout=20)
        if not html:
            print(f"    无法获取", flush=True)
            continue
        urls = extract_vehiclesizes_images(html)
        # 过滤缩略图，保留大图（/images/ 路径而非 /thm/）
        big_urls = [u for u in urls if "/images/" in u and "/thm/" not in u]
        # 如果没有大图，用缩略图但替换路径
        if not big_urls:
            for u in urls:
                if "/thm/" in u:
                    big = u.replace("/thm/", "/images/")
                    big_urls.append(big)
        print(f"    提取到 {len(big_urls)} 个图片 URL", flush=True)
        all_urls.update(big_urls)
        log["sources"].append({"source": "vehiclesizes", "url": page_url, "urls_found": len(big_urls)})
        time.sleep(0.5)

    # 2. Bing 图片搜索
    print("\n--- 阶段2: Bing 图片搜索 ---", flush=True)
    queries = [
        "Ferrari Roma 2020 side profile studio",
        "Ferrari Roma 正侧视 官图",
        "法拉利 Roma 侧面 影棚",
        "Ferrari Roma 2020 press photo side view",
        "Ferrari Roma side profile official",
    ]
    for q in queries:
        print(f"  搜索: {q}", flush=True)
        urls = bing_image_search(q, num_results=30)
        car_urls = [u for u in urls if is_car_url(u)]
        print(f"    获取 {len(urls)} → {len(car_urls)} 汽车相关", flush=True)
        all_urls.update(car_urls)
        log["sources"].append({"source": "bing", "query": q, "urls_found": len(car_urls)})
        time.sleep(2)

    print(f"\n总计 {len(all_urls)} 个唯一 URL", flush=True)

    # 3. 下载所有候选图
    print("\n--- 阶段3: 下载候选图 ---", flush=True)
    cands = []
    idx = 0
    seen_md5 = set()
    for url in sorted(all_urls):
        idx += 1
        out = CAND_DIR / f"cand_{idx:02d}.jpg"
        data = fetch(url, timeout=25, headers={"Referer": "https://www.bing.com/"})
        if not data or len(data) < 5000:
            continue
        md5 = hashlib.md5(data).hexdigest()[:12]
        if md5 in seen_md5:
            continue
        seen_md5.add(md5)
        result = save_image(data, out)
        if not result:
            continue
        w, h, kb = result
        # 基本尺寸过滤
        if w < 600 or h < 400:
            print(f"  [{idx:02d}] 跳过(太小 {w}x{h}): {url[:60]}", flush=True)
            continue
        asp = w / h if h else 0
        cands.append({
            "url": url, "filename": out.name,
            "w": w, "h": h, "kb": kb, "md5": md5, "asp": round(asp, 2)
        })
        print(f"  [{idx:02d}] {w}x{h} asp={asp:.2f} {kb}KB", flush=True)
        time.sleep(0.3)
        if idx >= 50:
            break

    log["candidates"] = cands
    log["total_candidates"] = len(cands)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60, flush=True)
    print(f"完成: 保存 {len(cands)} 张 Roma 候选图", flush=True)
    print(f"候选目录: {CAND_DIR}", flush=True)
    print(f"日志: {LOG_PATH}", flush=True)


if __name__ == "__main__":
    main()
