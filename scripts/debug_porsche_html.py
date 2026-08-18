#!/usr/bin/env python3
"""调试 Porsche/Bugatti 页面 HTML 结构，找出图片 URL 模式"""
import ssl, urllib.request, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

def analyze(name, url):
    print(f"\n=== {name} ===")
    html = fetch(url)
    if not html:
        return
    print(f"HTML length: {len(html)}")

    # dam/jcr patterns
    jcr = re.findall(r'/dam/jcr:[a-f0-9-]+/', html)
    print(f"dam/jcr paths: {len(jcr)}")
    for p in jcr[:3]:
        print(f"  {p}")

    # Full image URLs with dam/jcr
    full_jcr = re.findall(r'https://newsroom\.porsche\.com/dam/jcr:[a-f0-9-]+/[^"\'<>\s]+', html)
    print(f"Full dam/jcr URLs: {len(full_jcr)}")
    for u in full_jcr[:3]:
        print(f"  {u[:120]}")

    # img src
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    print(f'img src: {len(imgs)}')
    for s in imgs[:5]:
        print(f"  {s[:120]}")

    # data-src
    datasrc = re.findall(r'data-src="([^"]+)"', html)
    print(f"data-src: {len(datasrc)}")
    for s in datasrc[:5]:
        print(f"  {s[:120]}")

    # srcset
    srcset = re.findall(r'srcset="([^"]+)"', html)
    print(f"srcset: {len(srcset)}")
    for s in srcset[:3]:
        print(f"  {s[:150]}")

    # Any image-like URL
    all_imgs = re.findall(r'https?://[^"\'<>\s]+\.(?:jpg|jpeg|png|webp)', html, re.IGNORECASE)
    print(f"All image URLs: {len(all_imgs)}")
    for u in all_imgs[:5]:
        print(f"  {u[:120]}")

# Porsche Taycan pages
analyze("Porsche Taycan Turbo GT", "https://newsroom.porsche.com/en/2024/products/porsche-the-new-taycan-turbo-gt-35479.html")
analyze("Porsche Taycan 2019 launch", "https://newsroom.porsche.com/en/2019/products/porsche-taycan-18957.html")

# Bugatti
analyze("Bugatti Chiron newsroom", "https://newsroom.bugatti.com/models/chiron")

# Ferrari
analyze("Ferrari SF90 (en-IN)", "https://www.ferrari.com/en-IN/auto/sf90-stradale")
