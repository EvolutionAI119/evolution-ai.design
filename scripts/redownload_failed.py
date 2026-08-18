#!/usr/bin/env python3
"""重新下载有问题的 4 张图片：Porsche Taycan, Ferrari SF90/F8/Roma"""
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

# 只重新下载这 4 张
RETRY_CARS = [
    ("porsche", "taycan",        "保时捷Taycan 电动车 侧面"),
    ("ferrari", "sf90",          "法拉利SF90 Stradale 超跑 侧面"),
    ("ferrari", "f8-tributo",    "法拉利F8 Tributo 超跑 侧面"),
    ("ferrari", "roma",          "法拉利Roma GT跑车 侧面"),
]

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return urllib.request.urlopen(req, timeout=timeout)

def search_bing_images(query, count=20):
    url = f"https://www.bing.com/images/async?q={urllib.parse.quote(query)}&first=1&count=35"
    try:
        resp = http_get(url, timeout=20)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    Search error: {e}", flush=True)
        return []

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

    if not urls:
        pattern2 = re.compile(r'"murl":"(https?://[^"]+)"')
        urls = pattern2.findall(html)

    BAD_KEYWORDS = [
        "recall", "pillsbury", "bread", "food", "recipe", "meal", "snack",
        "walmart", "amazon", "ebay", "etsy", "alibaba",
        "facebook", "twitter", "instagram", "pinterest", "tiktok",
        "youtube", "youtu.be", "vimeo",
        ".pdf", ".gif", ".svg", ".ico",
        "avatar", "logo", "icon", "banner", "ad-",
    ]

    filtered = []
    for u in urls:
        lower = u.lower()
        if any(kw in lower for kw in BAD_KEYWORDS):
            continue
        filtered.append(u)

    seen = set()
    unique = []
    for u in filtered:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[:count]

def download_image(url, out_path, timeout=25):
    try:
        resp = http_get(url, timeout=timeout)
        data = resp.read()
        if len(data) < 5000:
            return False, f"Too small: {len(data)} bytes"
        if not (data[:2] == b"\xff\xd8" or data[:4] == b"\x89PNG" or data[:4] == b"RIFF"):
            return False, "Not an image"
        with open(out_path, "wb") as f:
            f.write(data)
        return True, f"{len(data)/1024:.1f} KB"
    except Exception as e:
        return False, str(e)[:80]

def main():
    print(f"Re-downloading {len(RETRY_CARS)} problematic images\n", flush=True)

    # 读取已有图片的 hash（排除要重新下载的）
    used_hashes = set()
    used_urls = set()
    for brand_dir in os.listdir(BRANDS_DIR):
        bpath = os.path.join(BRANDS_DIR, brand_dir)
        if not os.path.isdir(bpath):
            continue
        for fname in os.listdir(bpath):
            if not fname.endswith(".jpg"):
                continue
            fpath = os.path.join(bpath, fname)
            # 跳过要重新下载的
            model_key = fname[:-4]
            if any(brand == brand_dir and model_key == model for brand, model, _ in RETRY_CARS):
                continue
            with open(fpath, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
            used_hashes.add(h)

    success = 0
    failed = []

    for i, (brand, model, query) in enumerate(RETRY_CARS, 1):
        print(f"[{i}/{len(RETRY_CARS)}] {brand}/{model}", flush=True)
        print(f"  Query: {query}", flush=True)

        brand_dir = os.path.join(BRANDS_DIR, brand)
        os.makedirs(brand_dir, exist_ok=True)
        out_path = os.path.join(brand_dir, f"{model}.jpg")

        urls = search_bing_images(query, count=25)
        print(f"  Found {len(urls)} candidate URLs", flush=True)

        if not urls:
            print(f"  ERROR: No image URLs found", flush=True)
            failed.append(f"{brand}/{model}")
            continue

        downloaded = False
        attempts = min(20, len(urls))
        for j, url in enumerate(urls[:attempts]):
            if url in used_urls:
                continue
            print(f"  Try [{j+1}/{attempts}]: {url[:80]}...", flush=True)
            ok, msg = download_image(url, out_path)
            if not ok:
                print(f"  FAIL: {msg}", flush=True)
                time.sleep(0.5)
                continue
            with open(out_path, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
            if h in used_hashes:
                print(f"  SKIP: Duplicate content (hash={h[:8]})", flush=True)
                os.remove(out_path)
                time.sleep(0.3)
                continue
            print(f"  OK: {msg}  hash={h[:8]}", flush=True)
            used_urls.add(url)
            used_hashes.add(h)
            downloaded = True
            success += 1
            break

        if not downloaded:
            if os.path.exists(out_path):
                os.remove(out_path)
            print(f"  ERROR: All candidates failed or duplicate", flush=True)
            failed.append(f"{brand}/{model}")

        time.sleep(1)

    print(f"\n=== RESULT: {success}/{len(RETRY_CARS)} succeeded ===", flush=True)
    if failed:
        print(f"Failed: {', '.join(failed)}", flush=True)

if __name__ == "__main__":
    main()
