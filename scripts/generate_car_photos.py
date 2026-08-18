#!/usr/bin/env python3
"""
调用 text_to_image API 生成 19 张真车照片。
关键发现：API 根据 Accept header 返回不同内容：
  - Accept: text/html → 返回 markdown ![](CDN_URL)
  - Accept: image/*   → 返回占位 JPEG
所以必须用 Accept: text/html 获取 CDN URL，再下载图片。
"""

import os
import sys
import time
import urllib.request
import urllib.parse
import re
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDS_DIR = os.path.join(BASE_DIR, "public", "brands")

CARS = [
    ("rolls-royce", "phantom",    'Side profile view of a Rolls-Royce Phantom black luxury sedan, studio lighting, white background, photorealistic, high detail'),
    ("rolls-royce", "ghost",      'Side profile view of a Rolls-Royce Ghost silver luxury sedan, studio lighting, white background, photorealistic, high detail'),
    ("rolls-royce", "cullinan",   'Side profile view of a Rolls-Royce Cullinan black luxury SUV, studio lighting, white background, photorealistic, high detail'),
    ("rolls-royce", "wraith",     'Side profile view of a Rolls-Royce Wraith dark blue luxury coupe, studio lighting, white background, photorealistic, high detail'),
    ("bentley", "continental-gt",  'Side profile view of a Bentley Continental GT silver luxury coupe, studio lighting, white background, photorealistic, high detail'),
    ("bentley", "continental-gtc", 'Side profile view of a Bentley Continental GTC blue luxury convertible, studio lighting, white background, photorealistic, high detail'),
    ("bentley", "flying-spur",     'Side profile view of a Bentley Flying Spur black luxury sedan, studio lighting, white background, photorealistic, high detail'),
    ("bentley", "bentayga",        'Side profile view of a Bentley Bentayga white luxury SUV, studio lighting, white background, photorealistic, high detail'),
    ("bugatti", "chiron",  'Side profile view of a Bugatti Chiron blue black hypercar, studio lighting, white background, photorealistic, high detail'),
    ("bugatti", "veyron",  'Side profile view of a Bugatti Veyron silver blue hypercar, studio lighting, white background, photorealistic, high detail'),
    ("bugatti", "divo",    'Side profile view of a Bugatti Divo red black hypercar, studio lighting, white background, photorealistic, high detail'),
    ("porsche", "911",      'Side profile view of a Porsche 911 Carrera silver sports car, studio lighting, white background, photorealistic, high detail'),
    ("porsche", "taycan",   'Side profile view of a Porsche Taycan white electric sports sedan, studio lighting, white background, photorealistic, high detail'),
    ("porsche", "panamera", 'Side profile view of a Porsche Panamera black luxury sports sedan, studio lighting, white background, photorealistic, high detail'),
    ("porsche", "cayenne",  'Side profile view of a Porsche Cayenne red luxury SUV, studio lighting, white background, photorealistic, high detail'),
    ("porsche", "macan",    'Side profile view of a Porsche Macan blue compact luxury SUV, studio lighting, white background, photorealistic, high detail'),
    ("ferrari", "sf90",        'Side profile view of a Ferrari SF90 Stradale red hypercar, studio lighting, white background, photorealistic, high detail'),
    ("ferrari", "f8-tributo",  'Side profile view of a Ferrari F8 Tributo red supercar, studio lighting, white background, photorealistic, high detail'),
    ("ferrari", "roma",        'Side profile view of a Ferrari Roma grey grand tourer coupe, studio lighting, white background, photorealistic, high detail'),
]

API_URL = "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image"


def generate_one(brand, model, prompt):
    """两步下载：1) 用 Accept:text/html 获取 CDN URL  2) 从 CDN 下载图片"""
    brand_dir = os.path.join(BRANDS_DIR, brand)
    os.makedirs(brand_dir, exist_ok=True)
    out_path = os.path.join(brand_dir, f"{model}.jpg")

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{API_URL}?prompt={encoded_prompt}&image_size=landscape_4_3"

    # Step 1: 用 Accept: text/html 获取 CDN URL
    print(f"  Step 1: Get CDN URL...")
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "text/html, */*",
            "User-Agent": "Mozilla/5.0"
        })
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
        text = data.decode("utf-8", errors="replace")

        # 从 markdown ![](URL) 中提取 CDN URL
        m = re.search(r'!\[.*?\]\((https?://[^\s)]+)\)', text)
        if not m:
            # 也尝试直接匹配 URL
            m = re.search(r'(https?://[^\s"\'<>\)]+\.(?:jpg|jpeg|png|webp))', text, re.IGNORECASE)
        if not m:
            # 尝试任意 URL
            m = re.search(r'(https?://aka\.doubaocdn\.com/[^\s"\'<>\)]+)', text)

        if not m:
            print(f"  ERROR: No CDN URL found in response: {text[:200]}")
            return False

        cdn_url = m.group(1)
        print(f"  CDN URL: {cdn_url}")

        # Step 2: 从 CDN 下载图片
        time.sleep(1)
        print(f"  Step 2: Download image...")
        cdn_req = urllib.request.Request(cdn_url, headers={
            "Accept": "image/*",
            "User-Agent": "Mozilla/5.0"
        })
        cdn_resp = urllib.request.urlopen(cdn_req, timeout=60)
        img_data = cdn_resp.read()

        if len(img_data) < 1024:
            print(f"  ERROR: Image too small ({len(img_data)} bytes)")
            return False

        with open(out_path, "wb") as f:
            f.write(img_data)

        print(f"  OK: saved {out_path} ({len(img_data)/1024:.1f} KB)")
        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    # 先删除旧的占位图
    print("Cleaning old images...")
    for brand, model, _ in CARS:
        p = os.path.join(BRANDS_DIR, brand, f"{model}.jpg")
        if os.path.exists(p):
            os.remove(p)
    print(f"  Deleted all old .jpg files")

    print(f"\nGenerating {len(CARS)} car photos via text_to_image API (CDN mode)\n")

    success = 0
    failed = []

    for i, (brand, model, prompt) in enumerate(CARS, 1):
        print(f"[{i}/{len(CARS)}] {brand}/{model}")
        ok = generate_one(brand, model, prompt)
        if ok:
            success += 1
        else:
            failed.append(f"{brand}/{model}")
        if i < len(CARS):
            time.sleep(2)

    print(f"\n=== RESULT: {success}/{len(CARS)} succeeded ===")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    # 验证唯一性
    print("\n=== Uniqueness check ===")
    hashes = {}
    sizes = {}
    for brand, model, _ in CARS:
        p = os.path.join(BRANDS_DIR, brand, f"{model}.jpg")
        if os.path.exists(p):
            sizes[f"{brand}/{model}"] = os.path.getsize(p)
            with open(p, 'rb') as f:
                h = hashlib.md5(f.read()).hexdigest()
            hashes[f"{brand}/{model}"] = h
    unique = len(set(hashes.values()))
    print(f"Unique images: {unique}/{len(hashes)}")
    for k, s in sizes.items():
        print(f"  {k}: {s/1024:.1f} KB  hash={hashes[k][:8]}")
    if unique < len(hashes):
        from collections import defaultdict
        by_hash = defaultdict(list)
        for k, v in hashes.items():
            by_hash[v].append(k)
        for h, keys in by_hash.items():
            if len(keys) > 1:
                print(f"  DUPLICATE: {keys}")


if __name__ == "__main__":
    main()
