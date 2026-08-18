#!/usr/bin/env python3
"""独立测试 Bing 图片搜索"""
import urllib.request
import urllib.parse
import json
import re
import socket

socket.setdefaulttimeout(20)

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return urllib.request.urlopen(req, timeout=timeout)

def search_bing(query):
    url = f"https://www.bing.com/images/async?q={urllib.parse.quote(query)}&first=1&count=35"
    print(f"URL: {url}", flush=True)
    resp = http_get(url, timeout=20)
    html = resp.read().decode("utf-8", errors="replace")
    print(f"HTML length: {len(html)}", flush=True)

    # 方法1: <a class="iusc" ... m="{...}">
    pattern1 = re.compile(r'<a[^>]*class="iusc"[^>]*\sm="([^"]+)"', re.IGNORECASE)
    matches1 = pattern1.findall(html)
    print(f"Method 1 (a.iusc m=): {len(matches1)} matches", flush=True)

    # 方法2: class="iusc" 任意位置
    pattern2 = re.compile(r'class="iusc"[^>]*\sm="([^"]+)"', re.IGNORECASE)
    matches2 = pattern2.findall(html)
    print(f"Method 2 (iusc m=): {len(matches2)} matches", flush=True)

    # 方法3: 任何 m="..." 属性
    pattern3 = re.compile(r'\sm="(\{[^"]+\})"', re.IGNORECASE)
    matches3 = pattern3.findall(html)
    print(f"Method 3 (m={{...}}): {len(matches3)} matches", flush=True)

    # 方法4: 直接找 murl
    pattern4 = re.compile(r'"murl":"(https?://[^"]+)"')
    matches4 = pattern4.findall(html)
    print(f"Method 4 (murl direct): {len(matches4)} matches", flush=True)

    # 方法5: murl&quot;:&quot;
    pattern5 = re.compile(r'murl&quot;:&quot;(https?://[^&]+)&')
    matches5 = pattern5.findall(html)
    print(f"Method 5 (murl &quot;): {len(matches5)} matches", flush=True)

    # 显示前 3 个匹配
    for i, m in enumerate(matches1[:3], 1):
        decoded = m.replace("&quot;", '"').replace("&amp;", "&")
        try:
            data = json.loads(decoded)
            print(f"  M1[{i}] murl: {data.get('murl', '')[:100]}", flush=True)
        except:
            print(f"  M1[{i}] raw: {m[:100]}", flush=True)

    for i, m in enumerate(matches4[:3], 1):
        print(f"  M4[{i}]: {m[:100]}", flush=True)

# 测试 - 中文搜索词避免歧义
queries = [
    "劳斯莱斯幻影 侧面",
    "劳斯莱斯古思特 侧面",
    "劳斯莱斯库里南 侧面",
    "劳斯莱斯魅影 侧面",
    "宾利欧陆GT 侧面",
    "保时捷911 侧面",
    "法拉利Roma 侧面",
]

for q in queries:
    print(f"\n=== Query: {q} ===", flush=True)
    try:
        search_bing(q)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
