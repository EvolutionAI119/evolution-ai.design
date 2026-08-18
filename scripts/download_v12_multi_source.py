#!/usr/bin/env python3
"""
v12 车型图重做脚本 - 新方法论
============================
教训：之前只筛宽高比，没视觉验证，导致下载了发动机铭牌/内饰/动漫插画。
新方法论：
1. 多源候选：Wikipedia API 主图 + Bing 图搜多张候选
2. 每车至少10张候选
3. 强制浏览器视觉验证（人工/子代理看图）
4. 不合格立即换源换关键词重试
5. 全部19张100%通过视觉验证才算完成
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

# 强制 stdout 行缓冲，确保实时输出
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

# 19 车型清单
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
CANDIDATES_DIR = ROOT / "scripts" / "_candidates"
LOG_FILE = ROOT / "scripts" / "_v12_download_log.json"

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
    "diagram", "blueprint", "drawing", "engine", "motor", "interior",
    "cockpit", "dashboard", "seat", "wheel", "wheelrim", "exhaust",
    "suspension", "transmission", "battery", "headlight", "taillight",
]


def http_get(url, timeout=20):
    """简单的 HTTP GET"""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,image/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        return data, r.geturl(), r.headers.get("Content-Type", "")


def fetch_text(url, timeout=20):
    """获取文本内容"""
    try:
        data, final_url, ct = http_get(url, timeout)
        return data.decode("utf-8", errors="ignore"), final_url, None
    except Exception as e:
        return None, url, str(e)


def is_url_clean(url):
    """检查URL是否不含改装/非内容关键词"""
    ul = url.lower()
    if any(x in ul for x in TUNER_BLACKLIST):
        return False
    if any(x in ul for x in BAD_KEYWORDS):
        return False
    return True


def fetch_wikipedia_candidates(title):
    """从 Wikipedia 获取候选图片URL"""
    candidates = []

    # 方法1: REST API 获取主图
    rest_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'))}"
    print(f"    [Wiki REST] {rest_url}", flush=True)
    data, _, err = fetch_text(rest_url, timeout=15)
    if not err and data:
        try:
            j = json.loads(data)
            if "originalimage" in j:
                candidates.append(
                    {
                        "url": j["originalimage"]["source"],
                        "source": "wikipedia_rest",
                        "w": j["originalimage"].get("width", 0),
                        "h": j["originalimage"].get("height", 0),
                    }
                )
            elif "thumbnail" in j:
                candidates.append(
                    {
                        "url": j["thumbnail"]["source"],
                        "source": "wikipedia_rest_thumb",
                        "w": j["thumbnail"].get("width", 0),
                        "h": j["thumbnail"].get("height", 0),
                    }
                )
        except Exception as e:
            print(f"    [Wiki REST] JSON 解析失败: {e}")

    # 方法2: 用 prop=pageimages 直接获取页面主图（避免 generator=images 太慢）
    api_url = (
        f"https://en.wikipedia.org/w/api.php?action=query"
        f"&titles={urllib.parse.quote(title)}"
        f"&prop=pageimages&piprop=original|thumbnail&pithumbsize=1500&format=json"
    )
    print(f"    [Wiki API] pageimages")
    data, _, err = fetch_text(api_url, timeout=15)
    if not err and data:
        try:
            j = json.loads(data)
            if "query" in j and "pages" in j["query"]:
                for page_id, page in j["query"]["pages"].items():
                    if "original" in page:
                        url = page["original"]["source"]
                        if re.search(r"\.(jpg|jpeg|png)(\?|$)", url, re.I) and is_url_clean(url):
                            candidates.append(
                                {
                                    "url": url,
                                    "source": "wikipedia_api_original",
                                    "w": page["original"].get("width", 0),
                                    "h": page["original"].get("height", 0),
                                }
                            )
                    elif "thumbnail" in page:
                        url = page["thumbnail"]["source"]
                        if re.search(r"\.(jpg|jpeg|png)(\?|$)", url, re.I) and is_url_clean(url):
                            candidates.append(
                                {
                                    "url": url,
                                    "source": "wikipedia_api_thumb",
                                    "w": page["thumbnail"].get("width", 0),
                                    "h": page["thumbnail"].get("height", 0),
                                }
                            )
        except Exception as e:
            print(f"    [Wiki API] JSON 解析失败: {e}")

    # 去重
    seen = set()
    unique = []
    for c in candidates:
        if c["url"] not in seen:
            seen.add(c["url"])
            unique.append(c)
    return unique


def fetch_bing_candidates(query, max_count=10):
    """从 Bing 图片搜索获取候选图片URL"""
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    print(f"    [Bing] {query}")
    html, _, err = fetch_text(url)
    if err:
        print(f"    [Bing] 失败: {err}")
        return []

    # 提取 murl
    murls = re.findall(r'"murl":"([^"]+)"', html)
    seen = set()
    candidates = []
    for u in murls:
        if u in seen:
            continue
        seen.add(u)
        if not re.search(r"\.(jpg|jpeg|png)(\?|$)", u, re.I):
            continue
        if not is_url_clean(u):
            continue
        candidates.append({"url": u, "source": "bing"})
        if len(candidates) >= max_count:
            break
    return candidates


def download_image(url, save_path, timeout=30):
    """下载图片"""
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
    """获取图片尺寸（用PIL）"""
    try:
        from PIL import Image

        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0)


def process_car(brand, model, title):
    """处理一个车型"""
    print(f"\n========== {brand}/{model} ({title}) ==========")

    candidates_dir = CANDIDATES_DIR / brand / model
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # 清空旧候选
    for f in candidates_dir.glob("*"):
        f.unlink()

    all_candidates = []

    # 1. Wikipedia 主图
    print(f"  [Step 1] Wikipedia 候选")
    wiki_cands = fetch_wikipedia_candidates(title)
    print(f"    Wikipedia 找到 {len(wiki_cands)} 个URL")
    for i, c in enumerate(wiki_cands[:5]):  # 最多5张Wiki候选
        save_path = candidates_dir / f"wiki_{i + 1}.jpg"
        size, md5, err = download_image(c["url"], save_path)
        if err:
            print(f"    [Wiki {i + 1}] 下载失败: {err}")
            continue
        w, h = get_image_size(save_path)
        asp = w / h if h > 0 else 0
        print(f"    [Wiki {i + 1}] {w}x{h} asp={asp:.2f} {size // 1024}KB")
        all_candidates.append(
            {
                "source": c["source"],
                "url": c["url"],
                "file": str(save_path),
                "filename": f"wiki_{i + 1}.jpg",
                "w": w,
                "h": h,
                "asp": asp,
                "size_kb": size // 1024,
                "md5": md5,
            }
        )

    # 2. Bing 图搜
    print(f"  [Step 2] Bing 图搜候选")
    queries = [
        f"{title} side profile white background",
        f"{title} side view official press image studio",
    ]
    bing_cands = []
    seen_urls = set(c["url"] for c in all_candidates)
    for q in queries:
        cands = fetch_bing_candidates(q, max_count=10)
        for c in cands:
            if c["url"] in seen_urls:
                continue
            seen_urls.add(c["url"])
            bing_cands.append(c)
        if len(bing_cands) >= 12:
            break
        time.sleep(1)

    print(f"    Bing 找到 {len(bing_cands)} 个URL")

    for i, c in enumerate(bing_cands[:8]):
        save_path = candidates_dir / f"bing_{i + 1}.jpg"
        size, md5, err = download_image(c["url"], save_path)
        if err:
            print(f"    [Bing {i + 1}] 下载失败: {err}")
            continue
        w, h = get_image_size(save_path)
        asp = w / h if h > 0 else 0
        print(f"    [Bing {i + 1}] {w}x{h} asp={asp:.2f} {size // 1024}KB")
        all_candidates.append(
            {
                "source": "bing",
                "url": c["url"],
                "file": str(save_path),
                "filename": f"bing_{i + 1}.jpg",
                "w": w,
                "h": h,
                "asp": asp,
                "size_kb": size // 1024,
                "md5": md5,
            }
        )

    return all_candidates


def main():
    print("=" * 60)
    print("v12 车型图重做脚本 - Wikipedia + Bing 多源候选")
    print("方法论：多源 + 强制视觉验证 + 不合格立即换源重试")
    print("=" * 60)

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
        time.sleep(0.5)

    # 保存日志
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n日志已保存: {LOG_FILE}")

    # 统计
    total = sum(r["candidates_count"] for r in all_results)
    print(f"\n总候选数: {total}")
    for r in all_results:
        print(f"  {r['brand']}/{r['model']}: {r['candidates_count']} 张候选")


if __name__ == "__main__":
    main()
