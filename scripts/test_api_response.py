#!/usr/bin/env python3
"""快速测试 text_to_image API 的实际响应"""
import urllib.request
import urllib.parse
import hashlib
import os

API_URL = "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image"
TESTS = [
    "Rolls-Royce Phantom side view",
    "Bugatti Chiron side view",
    "Ferrari Roma side view",
]

os.makedirs("d:/API/Evolution-Ai.Design/_test_imgs", exist_ok=True)

for i, prompt in enumerate(TESTS, 1):
    url = f"{API_URL}?prompt={urllib.parse.quote(prompt)}&image_size=landscape_4_3"
    print(f"\n[{i}] {prompt}")
    print(f"    URL: {url}")
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0"
        })
        resp = urllib.request.urlopen(req, timeout=60)
        data = resp.read()
        print(f"    Content-Type: {resp.headers.get('Content-Type')}")
        print(f"    Size: {len(data)} bytes")
        print(f"    First bytes (hex): {data[:20].hex()}")
        print(f"    MD5: {hashlib.md5(data).hexdigest()}")
        out = f"d:/API/Evolution-Ai.Design/_test_imgs/test_{i}.jpg"
        with open(out, "wb") as f:
            f.write(data)
        print(f"    Saved: {out}")
    except Exception as e:
        print(f"    ERROR: {e}")
