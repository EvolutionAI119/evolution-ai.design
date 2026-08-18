#!/usr/bin/env python3
"""快速测试改进后的 Bing 图片搜索"""
import sys
sys.path.insert(0, "d:/API/Evolution-Ai.Design/scripts")
from download_real_car_photos import search_bing_images

queries = [
    "Rolls-Royce Phantom VIII 2018 saloon side profile",
    "Bugatti Chiron 2016 hypercar side profile",
    "Ferrari Roma 2020 coupe side profile",
]

for q in queries:
    print(f"\n=== Query: {q} ===", flush=True)
    urls = search_bing_images(q, count=10)
    print(f"Found {len(urls)} URLs:", flush=True)
    for i, u in enumerate(urls[:5], 1):
        print(f"  [{i}] {u[:120]}", flush=True)
