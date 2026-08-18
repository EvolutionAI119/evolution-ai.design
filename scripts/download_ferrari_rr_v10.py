#!/usr/bin/env python3
"""
v10: 下载 Ferrari(3款) 和 Rolls-Royce(4款) 的正侧视官图
==========================================
背景：Ferrari media.ferrari.com 返回 403；Rolls-Royce media 站无法访问；
      Wikimedia Commons API 在当前网络被屏蔽(SSL 握手超时)。
策略：
  - Rolls-Royce: 使用 BMW Group 媒体池官方下载链接
    (press.rolls-roycemotorcars.com 的图片来源，官方新闻社图)
  - Ferrari: media.ferrari.com 403 且 Wikimedia 被屏蔽后，使用 Bing 图片搜索
    抓取 automotive 站点托管的官方新闻稿正侧视图，按宽高比筛选
筛选规则：
  - 排除改装品牌 (novitec / mansory / spofec ...)
  - 排除错误变体 (sf90-xx / xx-stradale / assetto / spider ...)
  - 优先宽高比 1.5-2.0 (侧视图比例)，偏好 1.7-2.0
"""
import os, sys, json, time, ssl, io, re
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
from PIL import Image

# === 配置 ===
BASE = Path(r"d:\API\Evolution-Ai.Design\public\brands")
LOG_PATH = Path(r"d:\API\Evolution-Ai.Design\scripts\_ferrari_rr_v10_log.json")
TIMEOUT = 30
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# SSL 关闭验证
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# 改装/错误变体黑名单 (小写匹配)
TUNER_BLACKLIST = ["novitec", "mansory", "spofec", "manthey", "techart", "brabus",
                   "carlsson", "lorinser", "abt", "mtm", "gemballa", "edo", "mulliner"]
VARIANT_BLACKLIST = {
    "sf90": ["xx", "assetto", "spider", "stradale-xx"],
    "f8-tributo": ["spider", "pista", "competizione"],
    "roma": ["spider"],
    "phantom": ["drophead", "coupe", "regatta", "centenary"],  # 只要标准轿车
    "ghost": ["black-badge", "extended"],   # 标准版优先（无extended亦可接受）
    "cullinan": ["black-badge"],
    "wraith": ["black-badge", "dawn", "drophead"],
}
# 侧视图宽高比范围
ASPECT_MIN, ASPECT_MAX = 1.45, 2.10
ASPECT_IDEAL_LO, ASPECT_IDEAL_HI = 1.65, 2.05


def is_blacklisted(filename_lower, model):
    """检查文件名是否命中改装/错误变体黑名单"""
    for bad in TUNER_BLACKLIST:
        if bad in filename_lower:
            return True
    for bad in VARIANT_BLACKLIST.get(model, []):
        if bad in filename_lower:
            return True
    return False


def fetch(url, timeout=TIMEOUT, headers=None):
    """带 UA 的下载，返回 bytes；失败返回 None"""
    hdr = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdr.update(headers)
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            data = resp.read()
            return data
    except Exception as e:
        return None


def get_image_dims(data):
    """用 PIL 读取图片宽高，失败返回 None"""
    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.size  # (w, h)
    except Exception:
        return None


def aspect_score(w, h):
    """侧视图评分：越接近 1.8 越好；不在 1.45-2.10 范围返回 -1"""
    if h == 0:
        return -1
    ratio = w / h
    if ratio < ASPECT_MIN or ratio > ASPECT_MAX:
        return -1
    if ASPECT_IDEAL_LO <= ratio <= ASPECT_IDEAL_HI:
        # 理想区间：越接近 1.85 分越高
        return 100 - abs(ratio - 1.85) * 20
    return 50 - abs(ratio - 1.85) * 30  # 边缘可接受


def save_jpg(data, out_path):
    """保存为 JPG (统一格式)；若非 JPG 用 PIL 转换"""
    try:
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            im.save(out_path, "JPEG", quality=92)
            return im.size
    except Exception as e:
        # 直接写入原始 bytes 作为兜底
        with open(out_path, "wb") as f:
            f.write(data)
        return None


# ====================================================================
# Rolls-Royce: BMW Group 媒体池官方下载链接
# URL 模式: https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=PXXXX&attachment=1&actEvent=image
# ====================================================================
BMW_POOL = "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo={dok}&attachment=1&actEvent=image"

RR_DISPLAY = {
    "phantom":  "Rolls-Royce Phantom",
    "ghost":    "Rolls-Royce Ghost",
    "cullinan": "Rolls-Royce Cullinan",
    "wraith":   "Rolls-Royce Wraith",
}

RR_CANDIDATES = {
    # 来自 press.rolls-roycemotorcars.com 各新闻稿页面的图集
    "phantom": [
        # Phantom Regatta / centenary / Saint-Tropez 等官方图集
        "P90648617", "P90648618", "P90648619", "P90648609",
        "P90627488", "P90627492",
        "P90649582", "P90649583", "P90649584", "P90649585",
        "P90649567", "P90649569",
        "P90650490", "P90650487", "P90650482", "P90650480",
        "P90623189",
    ],
    "ghost": [
        # New Ghost (2020) 官方发布 + Series II (2025) + Savile Row
        "P90401223", "P90401224",
        "P90612626",
        "P90651071", "P90651072", "P90651074", "P90651076", "P90651078",
        "P90649576", "P90649577", "P90649578", "P90649579", "P90649580", "P90649581",
    ],
    "cullinan": [
        # Cullinan Desert Adventure (2020) + Cullinan Series II (2024) 官方图
        "P90549024", "P90549026", "P90549025",
        "P90403691", "P90403692", "P90403693", "P90403694", "P90403695",
        "P90403696", "P90403697", "P90403698", "P90403699", "P90403700",
        "P90403701", "P90403702", "P90403703", "P90403704", "P90403705",
        "P90403706", "P90403707", "P90403708", "P90403709", "P90403710",
        "P90403711", "P90403712", "P90403713", "P90403714", "P90403715",
        "P90403716", "P90403717", "P90403718", "P90403719", "P90403720",
        "P90403721", "P90403722", "P90403723",
    ],
    "wraith": [
        # Wraith Press Kit (2013 原厂发布图集) —— 含正侧视官图
        "P90115727", "P90115728", "P90115729", "P90115730", "P90115731",
        "P90115732", "P90115733", "P90115734", "P90115735", "P90115739",
        "P90115740", "P90115741", "P90115742", "P90115758", "P90115759",
        "P90115760", "P90115761", "P90115762", "P90115763", "P90115805",
        "P90133141", "P90133143", "P90133149", "P90133150",
        "P90141984", "P90141985", "P90141986", "P90141987", "P90141988",
        "P90141989", "P90141990", "P90141991", "P90141992",
    ],
}


def download_rolls_royce(model, out_path, log_entry):
    """从 BMW 媒体池下载 Rolls-Royce 官方图，挑选最佳侧视图。
    若媒体池未找到侧视图(宽高比不达标)，回退到 Bing 图片搜索。"""
    brand_dir = BASE / "rolls-royce"
    brand_dir.mkdir(parents=True, exist_ok=True)
    best = {"score": -1, "data": None, "dok": None, "dims": None, "url": None}
    tried = []
    for dok in RR_CANDIDATES[model]:
        url = BMW_POOL.format(dok=dok)
        data = fetch(url)
        if not data:
            tried.append({"dok": dok, "url": url, "status": "fetch_failed"})
            continue
        dims = get_image_dims(data)
        if not dims:
            tried.append({"dok": dok, "url": url, "status": "not_image",
                          "size": len(data)})
            continue
        w, h = dims
        sc = aspect_score(w, h)
        tried.append({"dok": dok, "url": url, "status": "ok",
                      "w": w, "h": h, "ratio": round(w / h, 3), "score": round(sc, 2)})
        if sc > best["score"]:
            best = {"score": sc, "data": data, "dok": dok, "dims": dims, "url": url}
            # 若找到理想区间的高分图，提前结束
            if sc >= 95:
                break
        time.sleep(0.2)
    log_entry["bmw_tried"] = tried
    log_entry["bmw_candidates_tried"] = len(tried)

    # BMW 媒体池未找到侧视图 → 回退 Bing 图片搜索
    if best["data"] is None or best["score"] < 0:
        display = RR_DISPLAY[model]
        query = "{} side profile official press image".format(display)
        urls = search_bing_images(query, count=35)
        log_entry["bing_query"] = query
        log_entry["bing_urls_total"] = len(urls)
        bing_tried = []
        excluded = 0
        bing_best = {"score": -1, "data": None, "url": None, "dims": None}
        for u in urls[:18]:
            u_lower = u.lower()
            if is_blacklisted(u_lower, model):
                excluded += 1
                continue
            data = fetch(u, timeout=20)
            if not data or len(data) < 10000:
                bing_tried.append({"url": u, "status": "fetch_failed_or_small"})
                continue
            dims = get_image_dims(data)
            if not dims:
                bing_tried.append({"url": u, "status": "not_image"})
                continue
            w, h = dims
            sc = aspect_score(w, h)
            bing_tried.append({"url": u, "status": "ok",
                               "w": w, "h": h, "ratio": round(w / h, 3), "score": round(sc, 2)})
            if sc < 0:
                continue
            if w >= 1200:
                sc += 8
            if sc > bing_best["score"]:
                bing_best = {"score": sc, "data": data, "url": u, "dims": dims}
                if sc >= 100:
                    break
            time.sleep(0.15)
        log_entry["bing_tried"] = bing_tried
        log_entry["bing_excluded"] = excluded
        if bing_best["data"] is not None and bing_best["score"] >= 0:
            best = {"score": bing_best["score"], "data": bing_best["data"],
                    "dok": None, "dims": bing_best["dims"], "url": bing_best["url"]}

    if best["data"] is not None and best["score"] >= 0:
        dims = save_jpg(best["data"], out_path)
        log_entry["status"] = "success"
        log_entry["source"] = "bmw_mediapool" if best["dok"] else "bing_image_search"
        if best["dok"]:
            log_entry["dok"] = best["dok"]
        log_entry["url"] = best["url"]
        log_entry["dims"] = list(best["dims"])
        log_entry["ratio"] = round(best["dims"][0] / best["dims"][1], 3)
        log_entry["score"] = round(best["score"], 2)
        return True
    log_entry["status"] = "no_side_profile_found"
    return False


# ====================================================================
# Ferrari: Bing 图片搜索 (media.ferrari.com 403, Wikimedia 被屏蔽)
# 通过 Bing 抓取 automotive 站点托管的官方新闻稿正侧视图
# ====================================================================
BING_IMG_SEARCH = "https://www.bing.com/images/async?q={q}&first=1&count={n}"

FERRARI_DISPLAY = {
    "sf90":       "Ferrari SF90 Stradale",
    "f8-tributo": "Ferrari F8 Tributo",
    "roma":       "Ferrari Roma",
}

# 汽车站点白名单(优先)：能拿到官方新闻社图 / 高清正侧视图的来源
AUTO_SITES = [
    "autohome", "bitauto", "xcar", "pcauto", "puxiang", "igarage",
    "sinaimg", "zhimg", "ifengimg", "netease", "sohu", "qq.com", "163.com",
    "topspeed", "topspeedimages", "carbuzz", "netcarshow", "autocar",
    "ferrari", "imedia", "stellantis", "cloudfront", "akamaized",
    "166.net", "2008php", "streetexotics", "oto.com",
]
# 非汽车内容黑名单：旅游/风景/人物/电商/社交/文档等
BAD_KEYWORDS = [
    "recall", "pillsbury", "bread", "food", "recipe", "meal", "snack", "drink",
    "walmart", "amazon", "ebay", "etsy", "alibaba",
    "facebook", "twitter", "instagram", "pinterest", "tiktok",
    "youtube", "youtu.be", "vimeo",
    ".pdf", ".gif", ".svg", ".ico", ".webp",
    "avatar", "logo", "icon", "banner", "ad-",
    "adventures", "travel", "tourism", "vacation", "holiday", "hotel",
    "lake", "mountain", "beach", "sunset", "sunrise", "nature", "landscape",
    "canada", "switzerland", "norway", "iceland",
    "portrait", "selfie", "people", "person", "face",
    "cat", "dog", "animal", "bird", "fish", "horse",
]


def search_bing_images(query, count=35):
    """Bing 图片搜索：返回去重后的 murl 列表(汽车站点优先)。
    提取两种模式：iusc class+m 属性 / 直接 murl json。"""
    url = BING_IMG_SEARCH.format(q=urllib.parse.quote(query), n=count)
    data = fetch(url, timeout=20, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    if not data:
        return []
    html = data.decode("utf-8", errors="replace")

    urls = []
    pat1 = re.compile(r'<a[^>]*class="iusc"[^>]*\sm="([^"]+)"', re.IGNORECASE)
    for m_str in pat1.findall(html):
        try:
            d = m_str.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
            obj = json.loads(d)
            murl = obj.get("murl")
            if murl and murl.startswith("http"):
                urls.append(murl)
        except Exception:
            continue
    if not urls:
        pat2 = re.compile(r'"murl":"(https?://[^"]+)"')
        urls = pat2.findall(html)

    # 过滤坏关键词 + 汽车站点优先排序
    auto, other = [], []
    for u in urls:
        lower = u.lower()
        if any(kw in lower for kw in BAD_KEYWORDS):
            continue
        if any(site in lower for site in AUTO_SITES):
            auto.append(u)
        else:
            other.append(u)
    seen, result = set(), []
    for u in auto + other:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result[:count]


def download_ferrari(model, out_path, log_entry):
    """通过 Bing 图片搜索下载 Ferrari 官方正侧视图，按宽高比筛选"""
    brand_dir = BASE / "ferrari"
    brand_dir.mkdir(parents=True, exist_ok=True)
    display = FERRARI_DISPLAY[model]
    query = "{} side profile official press image".format(display)
    urls = search_bing_images(query, count=35)
    log_entry["query"] = query
    log_entry["bing_urls_total"] = len(urls)

    best = {"score": -1, "data": None, "url": None, "dims": None}
    tried = []
    excluded = 0
    # 最多试前 18 个候选
    for u in urls[:18]:
        u_lower = u.lower()
        # URL 命中改装/错误变体黑名单 → 跳过
        if is_blacklisted(u_lower, model):
            excluded += 1
            continue
        data = fetch(u, timeout=20)
        if not data:
            tried.append({"url": u, "status": "fetch_failed"})
            continue
        if len(data) < 10000:
            tried.append({"url": u, "status": "too_small", "size": len(data)})
            continue
        dims = get_image_dims(data)
        if not dims:
            tried.append({"url": u, "status": "not_image", "size": len(data)})
            continue
        w, h = dims
        sc = aspect_score(w, h)
        tried.append({"url": u, "status": "ok",
                      "w": w, "h": h, "ratio": round(w / h, 3), "score": round(sc, 2)})
        if sc < 0:
            continue
        # 偏好更高分辨率(≥1200px 宽)
        if w >= 1200:
            sc += 8
        if sc > best["score"]:
            best = {"score": sc, "data": data, "url": u, "dims": dims}
            if sc >= 100:
                break
        time.sleep(0.15)
    log_entry["tried"] = tried
    log_entry["excluded_count"] = excluded
    log_entry["candidates_tried"] = len(tried)
    if best["data"] is not None and best["score"] >= 0:
        dims = save_jpg(best["data"], out_path)
        log_entry["status"] = "success"
        log_entry["source"] = "bing_image_search"
        log_entry["url"] = best["url"]
        log_entry["dims"] = list(best["dims"])
        log_entry["ratio"] = round(best["dims"][0] / best["dims"][1], 3)
        log_entry["score"] = round(best["score"], 2)
        return True
    log_entry["status"] = "no_side_profile_found"
    return False


# ====================================================================
# 主流程
# ====================================================================
CARS = [
    {"brand": "ferrari", "model": "sf90",       "fn": download_ferrari},
    {"brand": "ferrari", "model": "f8-tributo", "fn": download_ferrari},
    {"brand": "ferrari", "model": "roma",       "fn": download_ferrari},
    {"brand": "rolls-royce", "model": "phantom", "fn": download_rolls_royce},
    {"brand": "rolls-royce", "model": "ghost",   "fn": download_rolls_royce},
    {"brand": "rolls-royce", "model": "cullinan","fn": download_rolls_royce},
    {"brand": "rolls-royce", "model": "wraith",  "fn": download_rolls_royce},
]


def main():
    print("=" * 70)
    print("v10: Ferrari(3) + Rolls-Royce(4) 正侧视官图下载")
    print("=" * 70)
    results = {}
    for car in CARS:
        brand, model, fn = car["brand"], car["model"], car["fn"]
        out_dir = BASE / brand
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{model}.jpg"
        log_entry = {"brand": brand, "model": model,
                     "out_path": str(out_path), "started_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        print(f"\n[{brand}/{model}] 下载中 ...")
        ok = fn(model, out_path, log_entry)
        log_entry["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if ok:
            sz = out_path.stat().st_size if out_path.exists() else 0
            log_entry["file_size"] = sz
            print(f"  -> 成功: {out_path}  ({sz//1024} KB, ratio={log_entry.get('ratio')})")
        else:
            print(f"  -> 失败: {log_entry.get('status')}")
        results[f"{brand}/{model}"] = log_entry
        # 实时写日志(防止中途崩溃丢失)
        LOG_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    # 汇总
    print("\n" + "=" * 70)
    print("汇总:")
    ok_n = sum(1 for v in results.values() if v.get("status") == "success")
    print(f"  成功 {ok_n}/{len(CARS)}")
    for key, v in results.items():
        st = v.get("status")
        ratio = v.get("ratio")
        src = v.get("source", "")
        print(f"  {key:30s} {st:24s} ratio={ratio}  src={src}")
    print(f"\n日志: {LOG_PATH}")


if __name__ == "__main__":
    main()
