#!/usr/bin/env python3
"""验证所有 19 张车型图片"""
import os
import hashlib

BASE_DIR = "d:/API/Evolution-Ai.Design"
BRANDS_DIR = os.path.join(BASE_DIR, "public", "brands")

CARS = [
    ("rolls-royce", "phantom"), ("rolls-royce", "ghost"),
    ("rolls-royce", "cullinan"), ("rolls-royce", "wraith"),
    ("bentley", "continental-gt"), ("bentley", "continental-gtc"),
    ("bentley", "flying-spur"), ("bentley", "bentayga"),
    ("bugatti", "chiron"), ("bugatti", "veyron"), ("bugatti", "divo"),
    ("porsche", "911"), ("porsche", "taycan"), ("porsche", "panamera"),
    ("porsche", "cayenne"), ("porsche", "macan"),
    ("ferrari", "sf90"), ("ferrari", "f8-tributo"), ("ferrari", "roma"),
]

print(f"Verifying {len(CARS)} car images\n", flush=True)

hashes = {}
missing = []
sizes = {}

for brand, model in CARS:
    p = os.path.join(BRANDS_DIR, brand, f"{model}.jpg")
    if not os.path.exists(p):
        missing.append(f"{brand}/{model}")
        print(f"  MISSING: {brand}/{model}.jpg", flush=True)
        continue
    size = os.path.getsize(p)
    sizes[f"{brand}/{model}"] = size
    with open(p, "rb") as f:
        h = hashlib.md5(f.read()).hexdigest()
    hashes[f"{brand}/{model}"] = h
    # 检查图片大小是否合理
    status = "OK" if size > 20000 else "SMALL"
    print(f"  {status:5s} {brand}/{model}.jpg: {size/1024:.1f} KB  hash={h[:8]}", flush=True)

print(f"\n=== Summary ===", flush=True)
print(f"Total: {len(CARS)}", flush=True)
print(f"Found: {len(hashes)}", flush=True)
print(f"Missing: {len(missing)}", flush=True)
if missing:
    print(f"  Missing files: {missing}", flush=True)

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

# 检查小图片
small = [k for k, s in sizes.items() if s < 30000]
if small:
    print(f"\nSmall images (<30KB, might be thumbnails): {small}", flush=True)
