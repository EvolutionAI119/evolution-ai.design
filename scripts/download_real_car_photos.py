#!/usr/bin/env python3
"""
从 Bing 图片搜索下载 19 款车型的真实照片。
Bing 图片搜索返回的 HTML 中，每张图片的元数据在 class="iusc" 的元素的 m 属性中（JSON 格式，含 murl 字段）。
"""
import urllib.request
import urllib.parse
import json
import re
import os
import time
import hashlib
import socket

socket.setdefaulttimeout(20)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDS_DIR = os.path.join(BASE_DIR, "public", "brands")

# 车型列表：使用中文搜索词（Bing 中文搜索更准确，避免英文歧义如 Rolls=面包卷）
CARS = [
    ("rolls-royce", "phantom",         "劳斯莱斯幻影 侧面照"),
    ("rolls-royce", "ghost",            "劳斯莱斯古思特 侧面照"),
    ("rolls-royce", "cullinan",         "劳斯莱斯库里南 侧面照"),
    ("rolls-royce", "wraith",           "劳斯莱斯魅影 侧面照"),
    ("bentley", "continental-gt",       "宾利欧陆GT 侧面照"),
    ("bentley", "continental-gtc",      "宾利欧陆GTC 敞篷 侧面照"),
    ("bentley", "flying-spur",          "宾利飞驰 侧面照"),
    ("bentley", "bentayga",             "宾利添越 SUV 侧面照"),
    ("bugatti", "chiron",               "布加迪Chiron 侧面照"),
    ("bugatti", "veyron",               "布加迪威龙 侧面照"),
    ("bugatti", "divo",                 "布加迪Divo 侧面照"),
    ("porsche", "911",                  "保时捷911 侧面照"),
    ("porsche", "taycan",               "保时捷Taycan 侧面照"),
    ("porsche", "panamera",             "保时捷Panamera 侧面照"),
    ("porsche", "cayenne",              "保时捷Cayenne SUV 侧面照"),
    ("porsche", "macan",                "保时捷Macan SUV 侧面照"),
    ("ferrari", "sf90",                 "法拉利SF90 侧面照"),
    ("ferrari", "f8-tributo",           "法拉利F8 侧面照"),
    ("ferrari", "roma",                 "法拉利Roma 侧面照"),
]

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return urllib.request.urlopen(req, timeout=timeout)

def search_bing_images(query, count=20):
    """从 Bing 图片搜索 async API 提取真实图片 URL。
    async API 返回简化的 HTML，图片 URL 在 m="..." 属性的 JSON 中（murl 字段）。
    """
    # 使用 async 接口，返回更简洁的 HTML
    url = f"https://www.bing.com/images/async?q={urllib.parse.quote(query)}&first=1&count=35"
    try:
        resp = http_get(url, timeout=20)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    Search error: {e}", flush=True)
        return []

    # async 接口的 HTML 中，每个图片项是 <a class="iusc" ... m="{...}">
    # m 属性是 JSON（&quot; 编码），包含 murl 字段
    pattern = re.compile(r'<a[^>]*class="iusc"[^>]*\sm="([^"]+)"', re.IGNORECASE)
    matches = pattern.findall(html)

    urls = []
    for m_str in matches:
        try:
            m_str_decoded = m_str.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
            m_data = json.loads(m_str_decoded)
            murl = m_data.get("murl")
            if murl and murl.startswith("http"):
                urls.append(murl)
        except (json.JSONDecodeError, ValueError):
            continue

    # 备用：直接匹配 murl 字段
    if not urls:
        pattern2 = re.compile(r'"murl":"(https?://[^"]+)"')
        urls = pattern2.findall(html)

    # 内容过滤：排除明显非汽车的 URL（如食物、面包、新闻文章等）
    BAD_KEYWORDS = [
        "recall", "pillsbury", "bread", "food", "recipe", "meal", "snack",
        "walmart", "amazon", "ebay", "etsy", "alibaba",
        "facebook", "twitter", "instagram", "pinterest", "tiktok",
        "youtube", "youtu.be", "vimeo",
        ".pdf", ".gif", ".svg", ".ico",
        "avatar", "logo", "icon", "banner", "ad-",
        "news", "article", "blog", "forum",
    ]
    GOOD_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

    filtered = []
    for u in urls:
        lower = u.lower()
        # 排除坏关键词
        if any(kw in lower for kw in BAD_KEYWORDS):
            continue
        # 优先保留有图片扩展名的 URL
        if any(lower.endswith(ext) for ext in GOOD_EXTENSIONS):
            filtered.append(u)
        elif any(ext in lower for ext in GOOD_EXTENSIONS):
            filtered.append(u)
        elif "image" in lower or "photo" in lower or "img" in lower or "pic" in lower:
            filtered.append(u)
        else:
            # 保留其他 URL 作为候选
            filtered.append(u)

    # 去重
    seen = set()
    unique = []
    for u in filtered:
        if u not in seen:
            seen.add(u)
            unique.append(u)

    return unique[:count]

def download_image(url, out_path, timeout=25):
    """下载图片，返回是否成功"""
    try:
        resp = http_get(url, timeout=timeout)
        data = resp.read()
        if len(data) < 5000:
            return False, f"Too small: {len(data)} bytes"
        # 简单验证是否是图片（检查 magic bytes）
        if not (data[:2] == b"\xff\xd8" or data[:4] == b"\x89PNG" or data[:4] == b"RIFF"):
            return False, "Not an image"
        with open(out_path, "wb") as f:
            f.write(data)
        return True, f"{len(data)/1024:.1f} KB"
    except Exception as e:
        return False, str(e)[:80]

def main():
    # 清理旧的 jpg 文件
    print("Cleaning old .jpg files...", flush=True)
    for brand, model, _ in CARS:
        p = os.path.join(BRANDS_DIR, brand, f"{model}.jpg")
        if os.path.exists(p):
            os.remove(p)

    print(f"\nDownloading {len(CARS)} real car photos from Bing\n", flush=True)

    success = 0
    failed = []
    results = []
    used_urls = set()       # 已使用的图片 URL（URL 去重）
    used_hashes = set()     # 已使用图片的 MD5（内容去重）

    for i, (brand, model, query) in enumerate(CARS, 1):
        print(f"[{i}/{len(CARS)}] {brand}/{model}", flush=True)
        print(f"  Query: {query}", flush=True)

        brand_dir = os.path.join(BRANDS_DIR, brand)
        os.makedirs(brand_dir, exist_ok=True)
        out_path = os.path.join(brand_dir, f"{model}.jpg")

        # 搜索图片
        urls = search_bing_images(query, count=20)
        print(f"  Found {len(urls)} candidate URLs", flush=True)

        if not urls:
            print(f"  ERROR: No image URLs found", flush=True)
            failed.append(f"{brand}/{model}")
            continue

        # 尝试每个 URL，直到成功下载一个未使用过的有效图片
        downloaded = False
        attempts = min(15, len(urls))  # 最多尝试前 15 个
        for j, url in enumerate(urls[:attempts]):
            # URL 去重
            if url in used_urls:
                print(f"  Skip [{j+1}]: URL already used by another model", flush=True)
                continue
            print(f"  Try [{j+1}/{attempts}]: {url[:80]}...", flush=True)
            ok, msg = download_image(url, out_path)
            if not ok:
                print(f"  FAIL: {msg}", flush=True)
                time.sleep(0.5)
                continue
            # 内容去重：计算 MD5
            with open(out_path, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
            if h in used_hashes:
                print(f"  SKIP: Image content duplicate (hash={h[:8]})", flush=True)
                os.remove(out_path)
                time.sleep(0.3)
                continue
            # 接受这张图片
            print(f"  OK: {msg}  hash={h[:8]}", flush=True)
            used_urls.add(url)
            used_hashes.add(h)
            results.append((brand, model, url, os.path.getsize(out_path)))
            downloaded = True
            success += 1
            break

        if not downloaded:
            # 删除可能残留的无效文件
            if os.path.exists(out_path):
                os.remove(out_path)
            print(f"  ERROR: All candidates failed or duplicate", flush=True)
            failed.append(f"{brand}/{model}")

        # 间隔，避免被限制
        time.sleep(1)

    print(f"\n=== RESULT: {success}/{len(CARS)} succeeded ===", flush=True)
    if failed:
        print(f"Failed: {', '.join(failed)}", flush=True)

    # 唯一性检查
    print("\n=== Uniqueness check ===", flush=True)
    hashes = {}
    for brand, model, _, _ in results:
        p = os.path.join(BRANDS_DIR, brand, f"{model}.jpg")
        if os.path.exists(p):
            with open(p, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
            hashes[f"{brand}/{model}"] = h
    unique = len(set(hashes.values()))
    print(f"Unique images: {unique}/{len(hashes)}", flush=True)
    if unique < len(hashes):
        from collections import defaultdict
        by_hash = defaultdict(list)
        for k, v in hashes.items():
            by_hash[v].append(k)
        for h, keys in by_hash.items():
            if len(keys) > 1:
                print(f"  DUPLICATE: {keys} (hash={h[:8]})", flush=True)

    # 文件列表
    print("\n=== Final files ===", flush=True)
    for brand, model, _, size in results:
        print(f"  {brand}/{model}.jpg: {size/1024:.1f} KB", flush=True)

if __name__ == "__main__":
    main()
