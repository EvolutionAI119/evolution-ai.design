#!/usr/bin/env python3
"""
v14 - 为12个不合格车型用更多关键词重新搜索
=============================================
v13的问题：关键词太少，Bing返回的多是3/4角度图。
v14策略：每个车型用6+个多样化中文关键词，增加找到正侧视的概率。
"""
import json, os, re, sys, time, hashlib, ssl, urllib.parse, urllib.request
from pathlib import Path
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
from PIL import Image

# 12个不合格车型 + 多样化关键词
FAILED_CARS = [
    ("rolls-royce", "ghost", "劳斯莱斯 古思特", ["劳斯莱斯古思特 侧面图", "劳斯莱斯古思特 侧视图", "劳斯莱斯古思特 侧身", "劳斯莱斯古思特 侧面 官方图", "劳斯莱斯古思特 侧面 高清", "Rolls-Royce Ghost side profile"]),
    ("rolls-royce", "cullinan", "劳斯莱斯 库里南", ["劳斯莱斯库里南 侧面图", "劳斯莱斯库里南 侧视图", "劳斯莱斯库里南 侧身", "劳斯莱斯库里南 侧面 官方图", "劳斯莱斯库里南 侧面 高清", "Rolls-Royce Cullinan side profile"]),
    ("bentley", "continental-gt", "宾利 欧陆GT", ["宾利欧陆GT 侧面图", "宾利欧陆GT 侧视图", "宾利欧陆 侧面 官方图", "宾利欧陆 侧面 高清", "Bentley Continental GT side profile", "宾利欧陆GT 侧身"]),
    ("bentley", "continental-gtc", "宾利 欧陆GTC", ["宾利欧陆GTC 侧面图", "宾利欧陆GTC 侧视图", "宾利欧陆GTC 侧面 官方图", "Bentley Continental GTC side profile", "宾利欧陆敞篷 侧面", "宾利欧陆GTC 侧身"]),
    ("bentley", "flying-spur", "宾利 飞驰", ["宾利飞驰 侧面图", "宾利飞驰 侧视图", "宾利飞驰 侧身", "宾利飞驰 侧面 官方图", "宾利飞驰 侧面 高清", "Bentley Flying Spur side profile"]),
    ("bentley", "bentayga", "宾利 添越", ["宾利添越 侧面图", "宾利添越 侧视图", "宾利添越 侧身", "宾利添越 侧面 官方图", "宾利添越 侧面 高清", "Bentley Bentayga side profile"]),
    ("bugatti", "chiron", "布加迪 凯龙", ["布加迪凯龙 侧面图", "布加迪凯龙 侧视图", "布加迪凯龙 侧身", "布加迪凯龙 侧面 官方图", "Bugatti Chiron side profile", "布加迪Chiron 侧面"]),
    ("bugatti", "veyron", "布加迪 威航", ["布加迪威航 侧面图", "布加迪威航 侧视图", "布加迪威航 侧身", "布加迪威航 侧面 官方图", "Bugatti Veyron side profile", "布加迪威龙 侧面"]),
    ("bugatti", "divo", "布加迪 迪沃", ["布加迪迪沃 侧面图", "布加迪迪沃 侧视图", "布加迪迪沃 侧身", "布加迪迪沃 侧面 官方图", "Bugatti Divo side profile", "布加迪Divo 侧面"]),
    ("porsche", "taycan", "保时捷 Taycan", ["保时捷Taycan 侧面图", "保时捷Taycan 侧视图", "保时捷Taycan 侧身", "保时捷Taycan 侧面 官方图", "保时捷Taycan 侧面 高清", "Porsche Taycan side profile"]),
    ("ferrari", "sf90", "法拉利 SF90", ["法拉利SF90 侧面图", "法拉利SF90 侧视图", "法拉利SF90 侧身", "法拉利SF90 侧面 官方图", "Ferrari SF90 side profile", "法拉利SF90 侧面 高清"]),
    ("ferrari", "f8-tributo", "法拉利 F8", ["法拉利F8 侧面图", "法拉利F8 侧视图", "法拉利F8 侧身", "法拉利F8 Tributo 侧面 官方图", "Ferrari F8 Tributo side profile", "法拉利F8 侧面 高清"]),
]

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = ROOT / "scripts" / "_candidates_v14"
LOG_FILE = ROOT / "scripts" / "_v14_download_log.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

TUNER_BLACKLIST = ["novitec","mansory","techart","spofec","brabus","gemballa","carlsson","lorinser","abt","mtm","ruff","edo-competition","mulliner","bacalar","profilee"]
BAD_KEYWORDS = ["icon","logo","favicon","sprite","blank","pixel","tracking","1x1","placeholder","loader","spinner","social","share","arrow","menu","btn","button","badge","flag","avatar","coloring","涂色","食谱","recipe","面包","breed","cat-art"]

def fetch_text(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Accept": "text/html,application/xhtml+xml,image/*"})
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            return r.read().decode("utf-8", "ignore"), r.geturl(), None
    except Exception as e:
        return None, url, str(e)

def is_url_clean(url):
    ul = url.lower()
    return not any(x in ul for x in TUNER_BLACKLIST) and not any(x in ul for x in BAD_KEYWORDS)

def fetch_bing_murls(query, max_count=20):
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    html, _, err = fetch_text(url, timeout=15)
    if err:
        return []
    murls = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', html)
    murls = [u.replace("&amp;", "&") for u in murls]
    seen, candidates = set(), []
    for u in murls:
        if u in seen: continue
        seen.add(u)
        if not re.search(r"\.(jpg|jpeg|png)(\?|$|&)", u, re.I): continue
        if not is_url_clean(u): continue
        candidates.append(u)
        if len(candidates) >= max_count: break
    return candidates

def download_image(url, save_path, timeout=30):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bing.com/", "Accept": "image/*"})
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
            data = r.read()
        with open(save_path, "wb") as f:
            f.write(data)
        return len(data), hashlib.md5(data).hexdigest()[:12], None
    except Exception as e:
        return 0, "", str(e)

def get_image_size(filepath):
    try:
        with Image.open(filepath) as img:
            return img.size
    except Exception:
        return (0, 0)

def process_car(brand, model, cn_name, queries):
    print(f"\n========== {brand}/{model} ({cn_name}) ==========", flush=True)
    car_dir = CAND_DIR / brand / model
    car_dir.mkdir(parents=True, exist_ok=True)
    for f in car_dir.glob("*"):
        f.unlink()

    all_candidates = []
    seen_urls = set()
    cand_idx = 0

    for q in queries:
        murls = fetch_bing_murls(q, max_count=20)
        print(f"    [{q}] -> {len(murls)} URLs", flush=True)
        for u in murls:
            if u in seen_urls: continue
            seen_urls.add(u)
            cand_idx += 1
            save_path = car_dir / f"cand_{cand_idx:02d}.jpg"
            size, md5, err = download_image(u, save_path)
            if err: continue
            w, h = get_image_size(save_path)
            asp = w / h if h > 0 else 0
            if w >= 600 and h >= 300 and 1.4 <= asp <= 2.3:
                all_candidates.append({"url": u, "filename": f"cand_{cand_idx:02d}.jpg", "w": w, "h": h, "asp": round(asp,2), "size_kb": size//1024})
                print(f"    [{cand_idx}] {w}x{h} asp={asp:.2f} {size//1024}KB", flush=True)
            if len(all_candidates) >= 15:
                break
        if len(all_candidates) >= 15:
            break
        time.sleep(0.3)

    return all_candidates

def main():
    print("=" * 60, flush=True)
    print("v14 - 12不合格车型 多关键词重搜", flush=True)
    print("=" * 60, flush=True)
    CAND_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    for brand, model, cn_name, queries in FAILED_CARS:
        cands = process_car(brand, model, cn_name, queries)
        all_results.append({"brand": brand, "model": model, "cn_name": cn_name, "candidates_count": len(cands), "candidates": cands})

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n日志: {LOG_FILE}", flush=True)
    for r in all_results:
        print(f"  {r['brand']}/{r['model']}: {r['candidates_count']} 张", flush=True)

if __name__ == "__main__":
    main()
