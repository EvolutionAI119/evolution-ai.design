#!/usr/bin/env python3
"""测试图片源 - 输出到文件避免 stdout 卡住"""
import urllib.request
import urllib.parse
import json
import re
import socket
import sys

socket.setdefaulttimeout(15)

OUTPUT = "d:/API/Evolution-Ai.Design/_test_imgs/sources_result.txt"
out_lines = []

def log(msg):
    print(msg, flush=True)
    out_lines.append(msg)

def get(url, headers=None, timeout=15):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout)

# Test 1: Openverse API
log("=== Test 1: Openverse API ===")
q = "Rolls-Royce Phantom"
url = f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(q)}&page_size=3"
log(f"URL: {url}")
try:
    resp = get(url, timeout=15)
    data = json.loads(resp.read().decode("utf-8"))
    log(f"  Result count: {data.get('result_count', 0)}")
    for item in data.get("results", [])[:3]:
        log(f"    - {item.get('title', '')[:50]}")
        log(f"      URL: {item.get('url', '')[:100]}")
        log(f"      Thumb: {item.get('thumbnail', '')[:100]}")
except Exception as e:
    log(f"  ERROR: {e}")

# Test 2: Bing 图片搜索
log("\n=== Test 2: Bing Image Search ===")
q = "Rolls-Royce Phantom side view"
url = f"https://www.bing.com/images/search?q={urllib.parse.quote(q)}&form=HDRSC2"
log(f"URL: {url}")
try:
    resp = get(url, timeout=15)
    html = resp.read().decode("utf-8", errors="replace")
    log(f"  HTML length: {len(html)}")
    matches = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&', html)
    log(f"  Found {len(matches)} image URLs")
    for m in matches[:3]:
        log(f"    - {m[:120]}")
except Exception as e:
    log(f"  ERROR: {e}")

# 写入文件
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
log(f"\nResults written to: {OUTPUT}")
