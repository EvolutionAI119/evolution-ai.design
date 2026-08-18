#!/usr/bin/env python3
"""
v16: 下载 Ferrari Roma 候选图（仅 Roma）
==========================================
策略（按优先级）：
  1. Ferrari 官网页面 (en-EN/auto/roma.html, en-US/auto/ferrari-roma)
  2. Ferrari CDN 直接 URL (cdn.ferrari.com)
  3. WebSearch 找到的 Ferrari 新闻稿图片
所有候选保存到 public/_candidates_v15/ferrari/roma/ 供视觉验证
"""
import os, sys, json, time, ssl, io, re, hashlib
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
from PIL import Image

BASE = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = BASE / "public" / "_candidates_v15" / "ferrari" / "roma"
LOG_PATH = BASE / "scripts" / "_roma_v16_log.json"
TIMEOUT = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def fetch(url, timeout=TIMEOUT, headers=None):
    hdr = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8"}
    if headers:
        hdr.update(headers)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.read()
    except Exception:
        return None


def fetch_text(url, timeout=TIMEOUT):
    data = fetch(url, timeout)
    if data:
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return None
    return None


def save_image(data, out_path):
    try:
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            im.convert("RGB").save(out_path, "JPEG", quality=90)
            kb = out_path.stat().st_size // 1024
            return w, h, kb
    except Exception:
        return None


def extract_ferrari_urls(html):
    """从 Ferrari 页面提取图片 URL"""
    import html as html_mod
    html = html_mod.unescape(html)
    patterns = [
        r'https://[^"\'<>\s]*ferrari[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
        r'https://cdn[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
        r'https://images[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
        r'https://[^"\'<>\s]*\.akamaized[^"\'<>\s]*\.(?:jpg|jpeg|png|webp)',
    ]
    urls = set()
    for pat in patterns:
        found = re.findall(pat, html, re.IGNORECASE)
        for u in found:
            low = u.lower()
            if "icon" in low or "logo" in low or "sprite" in low:
                continue
            urls.add(u)
    return list(urls)


# Ferrari Roma 官方页面（多个区域，提高命中率）
FERRARI_ROMA_PAGES = [
    "https://www.ferrari.com/en-EN/auto/roma.html",
    "https://www.ferrari.com/en-US/auto/ferrari-roma",
    "https://www.ferrari.com/en-EN/magazine/articles/design/ferrari-roma",
    "https://www.ferrari.com/en-EN/magazine/articles/ferrari-roma-nuova-perfezione",
    "https://www.ferrari.com/en-EN/auto/ferrari-roma",
]

# 已知的 Ferrari CDN 图片 URL 模式（基于之前成功下载的经验）
KNOWN_CDN_URLS = [
    # Roma 官方侧视图常见 CDN URL
    "https://cdn.ferrari.com/cms/content/media-cms/media/5D7E52C5C6C0EF20C5A9C5E9F5E9C5E9F5E9C5E9.jpg",
]


def main():
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60, flush=True)
    print("v16: 下载 Ferrari Roma 候选图", flush=True)
    print("=" * 60, flush=True)

    all_urls = set()
    log = {"pages": [], "candidates": []}

    # 1. 从 Ferrari 官方页面提取图片 URL
    print("\n--- 阶段1: Ferrari 官方页面 ---", flush=True)
    for page_url in FERRARI_ROMA_PAGES:
        print(f"  尝试: {page_url}", flush=True)
        html = fetch_text(page_url, timeout=20)
        if not html:
            print(f"    无法获取", flush=True)
            log["pages"].append({"url": page_url, "status": "fetch_failed"})
            continue
        urls = extract_ferrari_urls(html)
        print(f"    提取到 {len(urls)} 个图片 URL", flush=True)
        all_urls.update(urls)
        log["pages"].append({"url": page_url, "status": "ok", "urls_found": len(urls)})
        time.sleep(0.5)

    print(f"\n官方页面共提取 {len(all_urls)} 个唯一 URL", flush=True)

    # 2. 下载候选图
    print("\n--- 阶段2: 下载候选图 ---", flush=True)
    cands = []
    idx = 0
    for url in sorted(all_urls):
        idx += 1
        out = CAND_DIR / f"cand_{idx:02d}.jpg"
        data = fetch(url, timeout=25)
        if not data or len(data) < 3000:
            print(f"  [{idx:02d}] 跳过(数据过小): {url[:80]}", flush=True)
            continue
        result = save_image(data, out)
        if not result:
            print(f"  [{idx:02d}] 跳过(格式错误): {url[:80]}", flush=True)
            continue
        w, h, kb = result
        md5 = hashlib.md5(data).hexdigest()[:12]
        cands.append({
            "url": url, "filename": out.name,
            "w": w, "h": h, "kb": kb, "md5": md5
        })
        print(f"  [{idx:02d}] {w}x{h} {kb}KB {url[:60]}", flush=True)
        time.sleep(0.3)
        if idx >= 30:
            break

    log["candidates"] = cands
    log["total_candidates"] = len(cands)

    # 保存日志
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60, flush=True)
    print(f"完成: 保存 {len(cands)} 张 Roma 候选图", flush=True)
    print(f"候选目录: {CAND_DIR}", flush=True)
    print(f"日志: {LOG_PATH}", flush=True)


if __name__ == "__main__":
    main()
