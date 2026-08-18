#!/usr/bin/env python3
"""测试不同图片源的网络可达性"""
import urllib.request
import socket

# 临时延长超时
socket.setdefaulttimeout(15)

SOURCES = [
    ("Wikimedia API", "https://commons.wikimedia.org/w/api.php?action=query&format=json"),
    ("Wikipedia EN", "https://en.wikipedia.org/w/api.php?action=query&format=json"),
    ("Wikipedia ZH", "https://zh.wikipedia.org/w/api.php?action=query&format=json"),
    ("Unsplash", "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=400"),
    ("Pexels", "https://www.pexels.com/"),
    ("GitHub", "https://raw.githubusercontent.com/"),
    ("Bing", "https://www.bing.com/"),
    ("Baidu", "https://www.baidu.com/"),
    ("Trae API", "https://trae-api-cn.mchost.guru/"),
    ("Doubaocdn", "https://aka.doubaocdn.com/"),
]

for name, url in SOURCES:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"[OK]   {name:20s} {resp.status} {resp.headers.get('Content-Type', '')[:40]}", flush=True)
    except Exception as e:
        msg = str(e)[:60]
        print(f"[FAIL] {name:20s} {msg}", flush=True)
