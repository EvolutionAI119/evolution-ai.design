#!/usr/bin/env python3
"""
v12b 车型图重做脚本 - 纯 Bing 多源候选
=====================================
教训：
1. 之前只筛宽高比，没视觉验证，导致下载了发动机铭牌/内饰/动漫插画
2. Wikipedia API 在国内被墙，urllib 超时
3. Bing 图片搜索页面的 murl 字段用 HTML 实体编码（&quot;）

新方法论：
1. 只用 Bing 图搜（已验证可访问）
2. 用正确的 murl&quot;:&quot; 模式提取原图URL
3. 每车用2个查询，下载最多8张候选
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
import urllib.parse
import urllib.request
from pathlib import Path

# 强制 stdout 行缓冲
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

CARS = [
    ("rolls-royce", "phantom", "Rolls-Royce Phantom"),
    ("rolls-royce", "ghost", "Rolls-Royce Ghost"),
    ("rolls-royce", "cullinan", "Rolls-Royce Cullinan"),
    ("rolls-royce", "wraith", "Rolls-Royce Wraith"),
    ("bentley", "continental-gt", "Bentley Continental GT"),
    ("bentley", "continental-gtc", "Bentley Continental GTC"),
    ("bentley", "flying-spur", "Bentley Flying Spur"),
    ("bentley", "bentayga", "Bentley Bentayga"),
    ("bugatti", "chiron", "Bugatti Chiron"),
    ("bugatti", "veyron", "Bugatti Veyron"),
    ("bugatti", "divo", "Bugatti Divo"),
    ("porsche", "911", "Porsche 911"),
    ("porsche", "taycan", "Porsche Taycan"),
    ("porsche", "panamera", "Porsche Panamera"),
    ("porsche", "cayenne", "Porsche Cayenne"),
    ("porsche", "macan", "Porsche Macan"),
    ("ferrari", "sf90", "Ferrari SF90"),
    ("ferrari", "f8-tributo", "Ferrari F8 Tributo"),
    ("ferrari", "roma", "Ferrari Roma"),
]

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CANDIDATES_DIR = ROOT / "scripts" / "_candidates_v12"
LOG_FILE = ROOT / "scripts" / "_v12b_download_log.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 改装品牌黑名单
TUNER_BLACKLIST = [
    "novitec", "mansory", "techart", "spofec", "brabus", "gemballa",
    "carlsson", "lorinser", "abt", "mtm", "ruff", "edo-competition",
    "mulliner", "bacalar", "profilee", "sport-turismo",
    "xx-stradale", "xx stradale", "assetto", "competizione",
]

# 非内容图片关键词
BAD_KEYWORDS = [
    "icon", "logo", "favicon", "sprite", "blank", "pixel", "tracking",
    "1x1", "placeholder", "loader", "spinner", "social", "share",
    "arrow", "menu", "btn", "button", "badge", "flag", "avatar",
]


def http_get(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Accept": "text/html,application/xhtml+xml,image/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
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


def fetch_bing_murls(query, max_count=15):
    """从 Bing 图片搜索获取原图URL（murl字段，HTML实体编码）"""
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    print(f"    [Bing] {query}", flush=True)
    html, _, err = fetch_text(url, timeout=15)
    if err:
        print(f"    [Bing] 失败: {err}", flush=True)
        return []

    # murl 字段用 HTML 实体编码
    murls = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', html)
    # 备用模式
    if not murls:
        murls = re.findall(r'"murl":"([^"]+)"', html)

    seen = set()
    candidates = []
    for u in murls:
        # HTML 实体解码
        u = u.replace("&amp;", "&")
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
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        with open(save_path, "wb") as f:
            f.write(data)
        md5 = hashlib.md5(data).hexdigest()[:12]
        return len(data), md5, None
    except Exception as e:
        return 0, "", str(e)


def get_image_size(filepath):
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0)


def process_car(brand, model, title):
    print(f"\n========== {brand}/{model} ({title}) ==========", flush=True)

    candidates_dir = CANDIDATES_DIR / brand / model
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # 清空旧候选
    for f in candidates_dir.glob("*"):
        f.unlink()

    all_candidates = []
    seen_urls = set()

    # 多个查询关键词
    queries = [
        f"{title} side profile white background",
        f"{title} side view official press image",
        f"{title} 正侧视图 官图",
    ]

    cand_idx = 0
    for q in queries:
        murls = fetch_bing_murls(q, max_count=15)
        print(f"    找到 {len(murls)} 个URL", flush=True)

        for u in murls:
            if u in seen_urls:
                continue
            seen_urls.add(u)
            cand_idx += 1
            save_path = candidates_dir / f"cand_{cand_idx:02d}.jpg"
            size, md5, err = download_image(u, save_path)
            if err:
                print(f"    [{cand_idx}] 下载失败: {err}", flush=True)
                continue
            w, h = get_image_size(save_path)
            asp = w / h if h > 0 else 0
            print(f"    [{cand_idx}] {w}x{h} asp={asp:.2f} {size // 1024}KB {u[:80]}", flush=True)
            all_candidates.append(
                {
                    "source": "bing",
                    "url": u,
                    "file": str(save_path),
                    "filename": f"cand_{cand_idx:02d}.jpg",
                    "w": w,
                    "h": h,
                    "asp": asp,
                    "size_kb": size // 1024,
                    "md5": md5,
                }
            )
            if len(all_candidates) >= 10:
                break
        if len(all_candidates) >= 10:
            break
        time.sleep(0.5)

    return all_candidates


def main():
    print("=" * 60, flush=True)
    print("v12b 车型图重做脚本 - 纯 Bing 多源候选", flush=True)
    print("方法论：Bing 多关键词 + 强制视觉验证 + 不合格立即重试", flush=True)
    print("=" * 60, flush=True)

    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for brand, model, title in CARS:
        cands = process_car(brand, model, title)
        all_results.append(
            {
                "brand": brand,
                "model": model,
                "title": title,
                "candidates_count": len(cands),
                "candidates": cands,
            }
        )

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n日志已保存: {LOG_FILE}", flush=True)

    total = sum(r["candidates_count"] for r in all_results)
    print(f"\n总候选数: {total}", flush=True)
    for r in all_results:
        print(f"  {r['brand']}/{r['model']}: {r['candidates_count']} 张候选", flush=True)


if __name__ == "__main__":
    main()
