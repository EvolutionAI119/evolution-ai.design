#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试汽车之家 autohome 车型图库接口 + Bing 正侧视过滤 + 官网高清关键词"""
import urllib.request
import urllib.parse
import re
import socket
import time

socket.setdefaulttimeout(15)

def http_get(url, timeout=15, referer=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout)

def test(name, url, timeout=15, referer=None):
    print(f"\n=== {name} ===", flush=True)
    print(f"  URL: {url}", flush=True)
    try:
        resp = http_get(url, timeout=timeout, referer=referer)
        ct = resp.headers.get('Content-Type', '')
        data = resp.read()
        print(f"  OK: {resp.status}  {ct[:50]}  Size={len(data)} bytes", flush=True)
        # 如果是 HTML，搜索关键字
        if 'html' in ct.lower() and len(data) < 200000:
            text = data.decode("utf-8", errors="replace")
            # 搜索 car.autohome.com.cn 中常见的图片标签
            for kw in ["正侧视", "侧视", "侧面", "外观", "车身外观", "官方图", "press kit", "press photo", "media"]:
                if kw in text:
                    print(f"  关键词命中: '{kw}'", flush=True)
            # 提取前 5 个图片 URL
            img_urls = re.findall(r'https?://[^"\']+\.(?:jpg|jpeg|png|webp)', text, re.IGNORECASE)
            unique_imgs = list(dict.fromkeys(img_urls))[:5]
            print(f"  前5个图片URL:", flush=True)
            for u in unique_imgs:
                print(f"    {u[:100]}", flush=True)
        # 如果是图片
        elif 'image' in ct.lower():
            print(f"  图片 magic: {data[:8].hex()}", flush=True)
        return True, data
    except Exception as e:
        print(f"  FAIL: {str(e)[:120]}", flush=True)
        return False, None

# 1. 汽车之家首页
test("Autohome 首页", "https://www.autohome.com.cn/")

# 2. 搜索：汽车之家 劳斯莱斯幻影 图库
test("Autohome 幻影图库", "https://car.autohome.com.cn/pic/series/3155.html#pvareaid=101382", referer="https://www.autohome.com.cn/")

# 3. 汽车之家 搜索接口
time.sleep(1)
search_query = urllib.parse.quote("劳斯莱斯幻影 正侧视 官方图")
test("Autohome 搜索", f"https://sou.autohome.com.cn/zonghe?q={search_query}&entry=421216&s=1&t=0", referer="https://www.autohome.com.cn/")

# 4. Bing 正侧视 + 官网过滤
time.sleep(1)
bing_q = urllib.parse.quote("保时捷911 正侧视 官方图 site:porsche.com OR site:netcarshow.com")
test("Bing 正侧视+官网", f"https://www.bing.com/images/async?q={bing_q}&first=1&count=20")

# 5. NetCarShow 网站（专业汽车媒体图库，含大量正侧视官方图）
time.sleep(1)
test("NetCarShow Porsche 911", "https://www.netcarshow.com/porsche/911_turbo_s/")
