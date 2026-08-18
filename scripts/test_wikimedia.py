#!/usr/bin/env python3
"""测试 Wikimedia Commons API 是否可访问"""
import urllib.request
import urllib.parse
import json

# 测试搜索 API
search_url = "https://commons.wikimedia.org/w/api.php"
params = {
    "action": "query",
    "list": "search",
    "srsearch": "Rolls-Royce Phantom",
    "srnamespace": "6",
    "srlimit": "3",
    "format": "json",
}
url = f"{search_url}?{urllib.parse.urlencode(params)}"
print(f"Test 1: Search API\n  URL: {url}")
try:
    req = urllib.request.Request(url, headers={"User-Agent": "CarDesignBot/1.0 (educational project)"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode("utf-8"))
    print(f"  OK: {len(data.get('query', {}).get('search', []))} results")
    for item in data.get("query", {}).get("search", [])[:3]:
        print(f"    - {item['title']}")
except Exception as e:
    print(f"  ERROR: {e}")

# 测试 Special:FilePath
print(f"\nTest 2: Special:FilePath (redirect to actual image)")
fp_url = "https://commons.wikimedia.org/wiki/Special:FilePath/Rolls-Royce%20Phantom%20II%20front%203.JPG?width=400"
print(f"  URL: {fp_url}")
try:
    req = urllib.request.Request(fp_url, headers={"User-Agent": "CarDesignBot/1.0 (educational project)"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read()
    print(f"  Final URL: {resp.geturl()}")
    print(f"  Content-Type: {resp.headers.get('Content-Type')}")
    print(f"  Size: {len(data)} bytes")
    print(f"  First bytes: {data[:20].hex()}")
except Exception as e:
    print(f"  ERROR: {e}")
