#!/usr/bin/env python3
"""
从 Wikipedia REST API 下载 19 款车型的真实照片。
Wikipedia 文章的 infobox 图片通常是该车型的官方照片。
"""
import os
import sys
import time
import urllib.request
import json
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANDS_DIR = os.path.join(BASE_DIR, "public", "brands")

# (brand_dir, model_file, wikipedia_page_title)
CARS = [
    ("rolls-royce", "phantom",    "Rolls-Royce_Phantom"),
    ("rolls-royce", "ghost",      "Rolls-Royce_Ghost"),
    ("rolls-royce", "cullinan",   "Rolls-Royce_Cullinan"),
    ("rolls-royce", "wraith",     "Rolls-Royce_Wraith_(2013)"),
    ("bentley", "continental-gt",  "Bentley_Continental_GT"),
    ("bentley", "continental-gtc", "Bentley_Continental_GT"),
    ("bentley", "flying-spur",     "Bentley_Flying_Spur"),
    ("bentley", "bentayga",        "Bentley_Bentayga"),
    ("bugatti", "chiron",  "Bugatti_Chiron"),
    ("bugatti", "veyron",  "Bugatti_Veyron"),
    ("bugatti", "divo",    "Bugatti_Divo"),
    ("porsche", "911",      "Porsche_911"),
    ("porsche", "taycan",   "Porsche_Taycan"),
    ("porsche", "panamera", "Porsche_Panamera"),
    ("porsche", "cayenne",  "Porsche_Cayenne"),
    ("porsche", "macan",    "Porsche_Macan"),
    ("ferrari", "sf90",        "Ferrari_SF90_Stradale"),
    ("ferrari", "f8-tributo",  "Ferrari_F8_Tributo"),
    ("ferrari", "roma",        "Ferrari_Roma"),
]

UA = "EvolutionAiDesign/1.0 (educational project; contact: dev@evolution-ai.design)"

def get_wiki_image(page_title):
    """通过 Wikipedia REST API 获取页面主图 URL"""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": UA
    })
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    # 优先取 originalimage，其次 thumbnail
    orig = data.get("originalimage", {})
    if orig and orig.get("source"):
        return orig["source"], orig.get("width", 0), orig.get("height", 0)
    thumb = data.get("thumbnail", {})
    if thumb and thumb.get("source"):
        return thumb["source"], thumb.get("width", 0), thumb.get("height", 0)
    return None, 0, 0


def download_image(url, out_path):
    """下载图片到文件"""
    req = urllib.request.Request(url, headers={
        "Accept": "image/*",
        "User-Agent": UA
    })
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read()
    if len(data) < 1024:
        return False, 0
    with open(out_path, "wb") as f:
        f.write(data)
    return True, len(data)


def main():
    print(f"Downloading {len(CARS)} car photos from Wikipedia\n")

    success = 0
    failed = []
    hashes = {}

    for i, (brand, model, page) in enumerate(CARS, 1):
        print(f"[{i}/{len(CARS)}] {brand}/{model}  (wiki: {page})")
        brand_dir = os.path.join(BRANDS_DIR, brand)
        os.makedirs(brand_dir, exist_ok=True)
        out_path = os.path.join(brand_dir, f"{model}.jpg")

        try:
            # Step 1: 获取图片 URL
            img_url, w, h = get_wiki_image(page)
            if not img_url:
                print(f"  ERROR: No image found for {page}")
                failed.append(f"{brand}/{model}")
                continue
            print(f"  Image: {w}x{h}  URL: {img_url[:80]}...")

            # Step 2: 下载图片
            # 对于 continental-gtc，如果和 continental-gt 是同一页面，需要跳过重复
            ok, size = download_image(img_url, out_path)
            if ok:
                print(f"  OK: saved {out_path} ({size/1024:.1f} KB)")
                with open(out_path, "rb") as f:
                    hashes[f"{brand}/{model}"] = hashlib.md5(f.read()).hexdigest()
                success += 1
            else:
                print(f"  ERROR: Download failed")
                failed.append(f"{brand}/{model}")

        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append(f"{brand}/{model}")

        if i < len(CARS):
            time.sleep(1)

    print(f"\n=== RESULT: {success}/{len(CARS)} succeeded ===")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    # 唯一性检查
    print("\n=== Uniqueness check ===")
    unique = len(set(hashes.values()))
    print(f"Unique images: {unique}/{len(hashes)}")
    if unique < len(hashes):
        from collections import defaultdict
        by_hash = defaultdict(list)
        for k, v in hashes.items():
            by_hash[v].append(k)
        for h, keys in by_hash.items():
            if len(keys) > 1:
                print(f"  DUPLICATE: {keys}")
                # 对于重复的，标记需要后续处理
    else:
        print("All images are unique!")


if __name__ == "__main__":
    main()
