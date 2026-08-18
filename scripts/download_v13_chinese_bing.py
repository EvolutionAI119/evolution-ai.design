#!/usr/bin/env python3
"""
v13 车型图重做脚本 - 中文关键词 Bing 图搜
=========================================
教训：
1. 英文关键词搜索返回面包卷食谱（Bing把Rolls理解成面包卷）
2. 中文关键词搜索返回中国汽车媒体网站的车图（新浪/易车/太平洋汽车等）

新方法论：
1. 用中文关键词搜索 Bing 图片（"品牌 中文名 正侧视图"）
2. 从 murl 提取原图URL（HTML实体编码格式）
3. 每车用2-3个查询，下载最多12张候选
4. 强制浏览器视觉验证
5. 不合格立即换关键词重试
6. 全部19张100%通过视觉验证才算完成
"""

import json
import os
import re
import sys
import time
import hashlib
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from PIL import Image

# 19 车型清单（中文+英文）
CARS = [
    ("rolls-royce", "phantom", "劳斯莱斯 幻影"),
    ("rolls-royce", "ghost", "劳斯莱斯 古思特"),
    ("rolls-royce", "cullinan", "劳斯莱斯 库里南"),
    ("rolls-royce", "wraith", "劳斯莱斯 魅影"),
    ("bentley", "continental-gt", "宾利 欧陆GT"),
    ("bentley", "continental-gtc", "宾利 欧陆GTC"),
    ("bentley", "flying-spur", "宾利 飞驰"),
    ("bentley", "bentayga", "宾利 添越"),
    ("bugatti", "chiron", "布加迪 凯龙"),
    ("bugatti", "veyron", "布加迪 威航"),
    ("bugatti", "divo", "布加迪 迪沃"),
    ("porsche", "911", "保时捷 911"),
    ("porsche", "taycan", "保时捷 Taycan"),
    ("porsche", "panamera", "保时捷 帕拉梅拉"),
    ("porsche", "cayenne", "保时捷 卡宴"),
    ("porsche", "macan", "保时捷 Macan"),
    ("ferrari", "sf90", "法拉利 SF90"),
    ("ferrari", "f8-tributo", "法拉利 F8"),
    ("ferrari", "roma", "法拉利 Roma"),
]

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = ROOT / "scripts" / "_candidates_v13"
LOG_FILE = ROOT / "scripts" / "_v13_download_log.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# 改装品牌黑名单
TUNER_BLACKLIST = [
    "novitec", "mansory", "techart", "spofec", "brabus", "gemballa",
    "carlsson", "lorinser", "abt", "mtm", "ruff", "edo-competition",
    "mulliner", "bacalar", "profilee",
]

BAD_KEYWORDS = [
    "icon", "logo", "favicon", "sprite", "blank", "pixel", "tracking",
    "1x1", "placeholder", "loader", "spinner", "social", "share",
    "arrow", "menu", "btn", "button", "badge", "flag", "avatar",
    "coloring", "涂色", "食谱", "recipe", "面包", "breed", "cat-art",
]


def http_get(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,image/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        data = r.read()
        return data, r.geturl(), r.headers.get("Content-Type", "")


def fetch_text(url, timeout=15):
    try:
        data, final_url, ct = http_get(url, timeout)
        return data.decode("utf-8", errors="ignore"), final_url, None
    except Exception as e:
        return None, url, str(e)


def is_url_clean(url):
    ul = url.lower()
    if any(x in ul for x in TUNER_BLACKLIST):
        return False
    if any(x in ul for x in BAD_KEYWORDS):
        return False
    return True


def fetch_bing_murls(query, max_count=20):
    """从 Bing 图片搜索获取原图URL（中文关键词）"""
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    print(f"    [Bing] {query}", flush=True)
    html, _, err = fetch_text(url, timeout=15)
    if err:
        print(f"    [Bing] 失败: {err}", flush=True)
        return []

    # murl 字段用 HTML 实体编码
    murls = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', html)
    murls = [u.replace("&amp;", "&") for u in murls]

    seen = set()
    candidates = []
    for u in murls:
        if u in seen:
            continue
        seen.add(u)
        if not re.search(r"\.(jpg|jpeg|png)(\?|$|&)", u, re.I):
            continue
        if not is_url_clean(u):
            continue
        candidates.append(u)
        if len(candidates) >= max_count:
            break
    return candidates


def download_image(url, save_path, timeout=30):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Referer": "https://www.bing.com/",
                "Accept": "image/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            data = r.read()
        with open(save_path, "wb") as f:
            f.write(data)
        md5 = hashlib.md5(data).hexdigest()[:12]
        return len(data), md5, None
    except Exception as e:
        return 0, "", str(e)


def get_image_size(filepath):
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0)


def process_car(brand, model, cn_name):
    print(f"\n========== {brand}/{model} ({cn_name}) ==========", flush=True)

    car_dir = CAND_DIR / brand / model
    car_dir.mkdir(parents=True, exist_ok=True)
    for f in car_dir.glob("*"):
        f.unlink()

    all_candidates = []
    seen_urls = set()

    # 多个中文查询
    queries = [
        f"{cn_name} 正侧视图",
        f"{cn_name} 侧面 官方图",
        f"{cn_name} 侧面 高清",
    ]

    cand_idx = 0
    for q in queries:
        murls = fetch_bing_murls(q, max_count=20)
        print(f"    找到 {len(murls)} 个URL", flush=True)

        for u in murls:
            if u in seen_urls:
                continue
            seen_urls.add(u)
            cand_idx += 1
            save_path = car_dir / f"cand_{cand_idx:02d}.jpg"
            size, md5, err = download_image(u, save_path)
            if err:
                print(f"    [{cand_idx}] 下载失败: {err}", flush=True)
                continue
            w, h = get_image_size(save_path)
            asp = w / h if h > 0 else 0
            print(f"    [{cand_idx}] {w}x{h} asp={asp:.2f} {size // 1024}KB {u[:80]}", flush=True)
            all_candidates.append(
                {
                    "url": u,
                    "file": str(save_path),
                    "filename": f"cand_{cand_idx:02d}.jpg",
                    "w": w, "h": h, "asp": asp,
                    "size_kb": size // 1024, "md5": md5,
                }
            )
            if len(all_candidates) >= 12:
                break
        if len(all_candidates) >= 12:
            break
        time.sleep(0.3)

    return all_candidates


def main():
    print("=" * 60, flush=True)
    print("v13 车型图重做脚本 - 中文关键词 Bing 图搜", flush=True)
    print("=" * 60, flush=True)

    CAND_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for brand, model, cn_name in CARS:
        cands = process_car(brand, model, cn_name)
        all_results.append({
            "brand": brand, "model": model, "cn_name": cn_name,
            "candidates_count": len(cands), "candidates": cands,
        })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n日志已保存: {LOG_FILE}", flush=True)

    total = sum(r["candidates_count"] for r in all_results)
    print(f"\n总候选数: {total}", flush=True)
    for r in all_results:
        print(f"  {r['brand']}/{r['model']}: {r['candidates_count']} 张候选", flush=True)


if __name__ == "__main__":
    main()
