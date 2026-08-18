#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_5_failed_v11.py
===================
重新下载 5 张此前内容/角度/背景错误的车型图片，强制要求：
  - 90 度正侧视（side profile，纯侧面）
  - 纯净 / 影棚背景（纯色或渐变；不允许户外/建筑/沙漠/展厅）
  - 原厂车（非改装）
  - 正确车型（非变体）

5 张失败图及问题：
  1. bugatti/chiron.jpg          — 之前是前 45 度活动照，需要 90 度正侧视官图
  2. bugatti/veyron.jpg          — 之前是 "20 周年" 图形不是车，需要 Veyron 正侧视官图
  3. ferrari/sf90.jpg            — 之前是户外沙漠场景，需要纯净背景正侧视
  4. ferrari/f8-tributo.jpg       — 之前是室内展厅照，需要纯净背景正侧视
  5. rolls-royce/cullinan.jpg    — 之前是内饰图，需要外观正侧视

下载方法：
  1. Bing 图片搜索（多关键词），按汽车站点优先排序
  2. 直接尝试官方媒体池候选 URL（BMW mediapool 用于 Rolls-Royce Cullinan）
  3. 每张图下载后立即用 PIL 检查尺寸+宽高比+背景纯度
  4. 不符合要求则尝试下一个候选，最多 10 个

要求：
  - User-Agent: Mozilla/5.0
  - SSL 验证关闭
  - 超时 30 秒
  - 侧视图宽高比 1.5-2.2
  - 日志：d:\\API\\Evolution-Ai.Design\\scripts\\_fix_5_log.json
"""
import os
import re
import json
import time
import ssl
import io
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path

from PIL import Image

# ====================================================================
# 配置
# ====================================================================
BASE_DIR = Path(r"d:\API\Evolution-Ai.Design\public\brands")
LOG_PATH = Path(r"d:\API\Evolution-Ai.Design\scripts\_fix_5_log.json")
TIMEOUT = 30
UA = "Mozilla/5.0"
MAX_CANDIDATES_PER_CAR = 10  # 每款车最多尝试 10 个候选 URL

# 侧视图宽高比范围（任务要求 1.5-2.2）
ASPECT_MIN, ASPECT_MAX = 1.5, 2.2
ASPECT_IDEAL_LO, ASPECT_IDEAL_HI = 1.65, 2.05
TARGET_ASPECT = 1.8

# 最小尺寸要求
MIN_WIDTH = 800
MIN_FILE_BYTES = 30_000  # 30KB

# SSL 关闭验证
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ====================================================================
# 改装 / 错误变体黑名单（小写匹配）
# 注意：不要使用过短/过通用的子串（如 "edo" 会误匹配 BMW 媒体池
# URL 路径 /edown/pressclub/，导致官方图被错误排除）
# ====================================================================
TUNER_BLACKLIST = [
    "novitec", "mansory", "spofec", "manthey", "techart", "brabus",
    "carlsson", "lorinser", "abt", "mtm", "gemballa",
    "edo-competition", "edocompetition", "edo_performance",
    "mulliner", "liberty-walk", "libertywalk", "overdose",
    "prior-design", "priordesign",
]

# 各车型的错误变体黑名单（小写匹配 URL）
VARIANT_BLACKLIST = {
    "chiron":   ["sport", "pur-sport", "pur sport", "super-sport", "super sport",
                 "centodieci", "profilee", "noire", "lego", "tourbillon",
                 "mistral", "bolide", "bbl", "golden", "remise", "breakfast",
                 "bts", "rolling-chassis", "eb-110", "eb110",
                 "world-premiere-presskit", "eps_ext", "eps-ext"],
    "veyron":   ["super-sport", "super sport", "grand-sport", "grand sport",
                 "vitesses", "vitesse", "lego", "remise", "breakfast",
                 "20th", "anniversary", "20-years", "20years", "eb-110", "eb110",
                 "brescia", "sang-bleu", "sang-bleu",
                 # 关键：排除 Bugatti 其他车型（Tourbillon/Bolide/Mistral/Chiron/Divo）
                 "tourbillon", "bolide", "mistral", "chiron", "divo",
                 "remi-south", "remisouth", "remire",
                 "world-premiere-presskit", "eps_ext", "eps-ext"],
    "sf90":     ["xx", "assetto", "spider", "stradale-xx", "laguna",
                 "challenge", "comps", "competizione"],
    "f8-tributo": ["spider", "pista", "competizione", "tributo-xx",
                   "portofino"],
    "cullinan": ["black-badge", "black badge", "series-ii", "series ii",
                 "desert", "adventure", "inspired", "fashion",
                 # 排除其他 Rolls 车型
                 "spectre", "phantom", "ghost", "wraith", "golden-sunflower",
                 "hongqi"],
}

# ====================================================================
# 汽车站点白名单（优先排序）
# ====================================================================
AUTO_SITES = [
    "autohome", "bitauto", "xcar", "pcauto", "puxiang", "igarage",
    "sinaimg", "zhimg", "ifengimg", "netease", "sohu", "qq.com", "163.com",
    "topspeed", "topspeedimages", "carbuzz", "netcarshow", "autocar",
    "ferrari", "imedia", "stellantis", "cloudfront", "akamaized",
    "166.net", "2008php", "streetexotics", "oto.com", "hearstapps",
    "bugatti-newsroom", "imgix", "mediapool.bmwgroup",
]

# 非汽车内容黑名单（URL 子串匹配）
BAD_KEYWORDS = [
    "recall", "pillsbury", "bread", "food", "recipe", "meal", "snack", "drink",
    "garlic", "butter", "honey", "roll-with", "rolls-with", "homemade",
    "walmart", "amazon", "ebay", "etsy", "alibaba",
    "facebook", "twitter", "instagram", "pinterest", "tiktok",
    "youtube", "youtu.be", "vimeo",
    ".pdf", ".gif", ".svg", ".ico", ".webp",
    "avatar", "logo", "icon", "banner", "ad-",
    "adventures", "travel", "tourism", "vacation", "holiday", "hotel",
    "lake", "mountain", "beach", "sunset", "sunrise", "nature", "landscape",
    "desert", "dune", "sand",
    "canada", "switzerland", "norway", "iceland",
    "portrait", "selfie", "people", "person", "face",
    "cat", "dog", "animal", "bird", "fish", "horse",
    "interior", "cockpit", "dashboard", "seat", "cabin", "steering",
    "wheel-1", "wheel1", "engine", "engine-bay", "exhaust",
    "20th", "anniversary", "badge", "emblem",
    # 非汽车内容站点（涂色书 / 矢量图 / 食谱 / 漫画）
    "coloring", "coloringtop", "coloring4free", "craftprofessional",
    "pngmart", "i2clipart", "clipart", "vectorstock", "bakingwithmaya",
    "manga", "clover", "reindeer", "outline", "transparent-image",
    "vector", "flower", "hongqi", "sunflower",
    # 壁纸站（多数为低质渲染图或非侧视）
    "4kwallpapers", "wallpapers.com", "wallpaper", "haowallpaper",
    "shetu66", "opic-oss", "588ku", "huaban", "pic.nximg",
    # 重复出现的前 3/4 视角来源（非侧视）
    "auto123channel", "msn-com.akamaized",
    # 1-Bugatti-Mistral-review / non-side-view
    "mistral-review", "remi-south", "remisouth",
]


# ====================================================================
# 5 款需要修复的车型配置
# ====================================================================
CARS = [
    {
        "brand": "bugatti",
        "model": "chiron",
        "display": "Bugatti Chiron",
        "queries": [
            "Bugatti Chiron side profile official press image studio",
            "Bugatti Chiron 正侧面 官方图 影棚",
            "Bugatti Chiron pure side view studio background",
            "Bugatti Chiron 2016 side profile press photo",
        ],
        # 直接尝试的官方候选 URL
        # 注意：原 v10 保存的 "01 BUGATTI BTS Episode 6.jpg" 是前 45° 活动照，
        # 已通过 blacklist 中的 "bts" 关键词过滤；不在此处提供直接 URL
        "direct_urls": [],
    },
    {
        "brand": "bugatti",
        "model": "veyron",
        "display": "Bugatti Veyron",
        "queries": [
            "Bugatti Veyron side profile official factory image",
            "Bugatti Veyron 16.4 正侧面 官方图",
            "Bugatti Veyron pure side view studio background",
            "Bugatti Veyron 2005 side profile press photo",
            "Bugatti Veyron EB 16.4 press photo side view",
        ],
        "direct_urls": [],
    },
    {
        "brand": "ferrari",
        "model": "sf90",
        "display": "Ferrari SF90 Stradale",
        "queries": [
            "Ferrari SF90 Stradale side profile official press image studio",
            "Ferrari SF90 Stradale 正侧面 官方图 影棚",
            "Ferrari SF90 Stradale pure side view studio background",
            "Ferrari SF90 Stradale 2019 side profile press photo",
        ],
        # 直接候选：来自历史日志中通过 side-view 文件名/比例判定的来源
        "direct_urls": [
            # 文件名明确含 "side-view"（oto.com gallery）
            "https://imgcdn.oto.com/large/gallery/exterior/10/2213/ferrari-sf90-stradale-side-view-691796.jpg",
        ],
    },
    {
        "brand": "ferrari",
        "model": "f8-tributo",
        "display": "Ferrari F8 Tributo",
        "queries": [
            "Ferrari F8 Tributo side profile official press image studio",
            "Ferrari F8 Tributo 正侧面 官方图 影棚",
            "Ferrari F8 Tributo pure side view studio background",
            "Ferrari F8 Tributo 2019 side profile press photo",
        ],
        # 直接候选：来自历史日志中比例达标的来源（但排除 2008php 室内展厅图）
        "direct_urls": [
            # igarage.my 历史记录 836x436 ratio=1.917
            "https://igarage.my/wp-content/uploads/2019/03/2019-Ferrari-F8-tributo-igarage-3.jpg",
        ],
    },
    {
        "brand": "rolls-royce",
        "model": "cullinan",
        "display": "Rolls-Royce Cullinan",
        "queries": [
            "Rolls-Royce Cullinan side profile exterior official press",
            "Rolls-Royce Cullinan 正侧面 外观 官方图",
            "Rolls-Royce Cullinan pure side view studio background",
            "Rolls-Royce Cullinan 2018 side profile press photo",
        ],
        # BMW Group 媒体池官方下载链接（Cullinan 官方图集）
        "direct_urls": [
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90549024&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90549026&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90549025&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403691&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403692&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403693&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403694&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403695&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403696&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403697&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403698&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403699&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403700&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403701&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403702&attachment=1&actEvent=image",
            "https://mediapool.bmwgroup.com/download/edown/pressclub/publicq?dokNo=P90403703&attachment=1&actEvent=image",
        ],
    },
]


# ====================================================================
# 通用工具
# ====================================================================
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
    except Exception:
        return None


def fetch_html(url, timeout=TIMEOUT):
    """获取页面 HTML，返回 (text, final_url, error)"""
    hdr = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            data = resp.read()
            enc = resp.headers.get_content_charset() or "utf-8"
            try:
                text = data.decode(enc, errors="replace")
            except Exception:
                text = data.decode("utf-8", errors="replace")
            return text, resp.url, None
    except Exception as e:
        return None, url, str(e)


def is_image_bytes(data):
    """快速校验是否为图片（JPEG/PNG/WEBP）"""
    if not data or len(data) < 1000:
        return False
    return (
        data[:2] == b"\xff\xd8"              # JPEG
        or data[:4] == b"\x89PNG"            # PNG
        or data[:4] == b"RIFF"              # WEBP
    )


def get_image_dims(data):
    """用 PIL 读取图片宽高，失败返回 None"""
    if not data:
        return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:
        return None


def aspect_score(w, h):
    """侧视图评分：越接近 1.8 越好；不在 1.5-2.2 范围返回 -1"""
    if not h:
        return -1
    ratio = w / h
    if ratio < ASPECT_MIN or ratio > ASPECT_MAX:
        return -1
    if ASPECT_IDEAL_LO <= ratio <= ASPECT_IDEAL_HI:
        # 理想区间：越接近 1.85 分越高
        return 100 - abs(ratio - 1.85) * 20
    return 50 - abs(ratio - 1.85) * 30  # 边缘可接受


def save_jpg(data, out_path):
    """保存为 JPG；若非 JPG 用 PIL 转换"""
    try:
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            im.save(out_path, "JPEG", quality=92, optimize=True, progressive=True)
            return im.size
    except Exception:
        # 兜底：直接写原始 bytes
        try:
            with open(out_path, "wb") as f:
                f.write(data)
        except Exception:
            pass
        return None


# ====================================================================
# 背景分析（参考 fix_complex_bg_cars.py 但更严格）
# ====================================================================
def analyze_bg(data):
    """
    分析背景类型，返回 (bg_type, is_clean_studio, brightness, detail)
    严格判定：
      - 拒绝户外（天空蓝/草地/沙漠棕黄）
      - 拒绝内饰（棕黄/暗色 dominate，可能是 leather/dashboard）
      - 接受：白色/浅色影棚、暗色影棚、单色/渐变背景
    """
    try:
        with Image.open(io.BytesIO(data)) as im:
            im_small = im.convert("RGB").resize((100, 100))
            pixels = list(im_small.getdata())
    except Exception:
        return "unknown", False, 0, {}

    n = len(pixels)
    brightness = sum((r + g + b) / 3 for r, g, b in pixels) / n

    # 各类像素占比
    sky = sum(1 for r, g, b in pixels
              if b > 150 and b > r + 30 and b > g + 10) / n
    grass = sum(1 for r, g, b in pixels
                if g > 100 and g > r + 20 and g > b + 10) / n
    dark = sum(1 for r, g, b in pixels if (r + g + b) / 3 < 50) / n
    light = sum(1 for r, g, b in pixels if (r + g + b) / 3 > 220) / n
    # 沙漠/沙土色：棕黄，r>b 显著，亮度中等
    sand = sum(1 for r, g, b in pixels
               if r > 130 and r < 230 and g > 90 and g < r and b < g
               and r - b > 35 and r < 220) / n
    # 内饰棕（皮革）：暗棕，r>b 显著，亮度较低
    leather = sum(1 for r, g, b in pixels
                  if r > 60 and r < 200 and g > 40 and g < r
                  and b < g and r - b > 30 and brightness < 130) / n

    # 四角颜色一致性（判定单色/渐变背景）
    corners = [pixels[0], pixels[99], pixels[9900], pixels[9999]]
    corner_max_diff = max(
        max(abs(c1[i] - c2[i]) for i in range(3))
        for c1 in corners for c2 in corners
    )

    detail = {
        "brightness": round(brightness, 1),
        "sky_pct": round(sky * 100, 1),
        "grass_pct": round(grass * 100, 1),
        "dark_pct": round(dark * 100, 1),
        "light_pct": round(light * 100, 1),
        "sand_pct": round(sand * 100, 1),
        "leather_pct": round(leather * 100, 1),
        "corner_max_diff": corner_max_diff,
    }

    # 严格判定：户外 / 沙漠 / 内饰一律拒绝
    if sky > 0.10 or grass > 0.08:
        return "outdoor", False, brightness, detail
    if sand > 0.15:
        return "desert", False, brightness, detail
    if leather > 0.20 and brightness < 130:
        return "interior", False, brightness, detail

    # 接受：白色/浅色影棚
    if light > 0.30:
        return "white_studio", True, brightness, detail
    # 接受：暗色影棚
    if dark > 0.30:
        return "dark_studio", True, brightness, detail
    # 接受：单色/渐变（四角差异小）
    if corner_max_diff < 60:
        return "clean_bg", True, brightness, detail
    # 边界：中等灰度的简单背景
    if corner_max_diff < 100 and brightness > 100 and brightness < 220:
        return "neutral_bg", True, brightness, detail

    return "complex_bg", False, brightness, detail


# ====================================================================
# 完整图片校验
# ====================================================================
def verify_image(data, model):
    """
    返回 (ok, w, h, reason, bg_type, score, detail)
    严格校验：
      - 是图片
      - 宽度 >= MIN_WIDTH，文件大小 >= MIN_FILE_BYTES
      - 宽高比 1.5-2.2
      - 背景是 studio/clean
    """
    if not is_image_bytes(data):
        return False, 0, 0, "not_image", "unknown", -1, {}
    if len(data) < MIN_FILE_BYTES:
        return False, 0, 0, f"too_small_{len(data)//1024}KB", "unknown", -1, {}

    dims = get_image_dims(data)
    if not dims:
        return False, 0, 0, "parse_fail", "unknown", -1, {}
    w, h = dims
    if w < MIN_WIDTH:
        return False, w, h, f"width_{w}", "unknown", -1, {}

    asp = w / h if h else 0
    if asp < ASPECT_MIN or asp > ASPECT_MAX:
        return False, w, h, f"aspect_{asp:.2f}", "unknown", -1, {}

    bg_type, is_clean, brightness, detail = analyze_bg(data)
    if not is_clean:
        return False, w, h, f"bg_{bg_type}", bg_type, -1, detail

    sc = aspect_score(w, h)
    if w >= 1200:
        sc += 5
    return True, w, h, f"OK {w}x{h} asp={asp:.2f} bg={bg_type}", bg_type, sc, detail


# ====================================================================
# Bing 图片搜索
# ====================================================================
BING_IMG_SEARCH = "https://www.bing.com/images/async?q={q}&first=1&count={n}"


def search_bing_images(query, count=35):
    """Bing 图片搜索：返回去重后的 murl 列表（汽车站点优先）"""
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
            d = (m_str.replace("&quot;", '"').replace("&amp;", "&")
                  .replace("&#39;", "'"))
            obj = json.loads(d)
            murl = obj.get("murl")
            if murl and murl.startswith("http"):
                urls.append(murl)
        except Exception:
            continue
    if not urls:
        pat2 = re.compile(r'"murl":"(https?://[^"]+)"')
        urls = pat2.findall(html)

    # 过滤坏关键词 + 汽车站点优先
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


def is_url_blacklisted(url_lower, model):
    """检查 URL 是否命中改装/错误变体黑名单"""
    for bad in TUNER_BLACKLIST:
        if bad in url_lower:
            return bad
    for bad in VARIANT_BLACKLIST.get(model, []):
        if bad in url_lower:
            return bad
    return None


# ====================================================================
# 单车型下载流程
# ====================================================================
def download_car(car):
    """处理一款车型：搜索 → 候选筛选 → 下载校验 → 保存"""
    brand, model = car["brand"], car["model"]
    display = car["display"]
    queries = car["queries"]
    direct_urls = car.get("direct_urls", [])

    out_dir = BASE_DIR / brand
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{model}.jpg"

    print(f"\n{'='*70}")
    print(f"[{brand}/{model}]  {display}")
    print(f"{'='*70}")
    print(f"  输出: {out_path}")

    log_entry = {
        "brand": brand,
        "model": model,
        "display": display,
        "out_path": str(out_path),
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": queries,
        "direct_urls": direct_urls,
        "tried": [],
        "status": "pending",
    }

    # 收集所有候选 URL
    all_candidates = list(direct_urls)  # 先放直接 URL（官方源优先）
    for q in queries:
        print(f"  Search: {q}")
        urls = search_bing_images(q, count=35)
        all_candidates.extend(urls)
        log_entry.setdefault("search_counts", []).append(
            {"query": q, "found": len(urls)})
        time.sleep(1.5)
        if len(all_candidates) > 80:
            break

    # 去重 + 黑名单过滤 + 排序（汽车站点优先）
    seen = set()
    auto, other = [], []
    excluded_count = 0
    excluded_examples = []
    for u in all_candidates:
        if u in seen:
            continue
        seen.add(u)
        u_lower = u.lower()
        bad = is_url_blacklisted(u_lower, model)
        if bad:
            excluded_count += 1
            if len(excluded_examples) < 5:
                excluded_examples.append({"url": u[:120], "reason": bad})
            continue
        if any(kw in u_lower for kw in BAD_KEYWORDS):
            excluded_count += 1
            continue
        if any(site in u_lower for site in AUTO_SITES):
            auto.append(u)
        else:
            other.append(u)

    candidates = auto + other
    log_entry["candidates_total"] = len(candidates)
    log_entry["excluded_count"] = excluded_count
    log_entry["excluded_examples"] = excluded_examples
    print(f"  候选总数: {len(candidates)}  排除: {excluded_count}")

    # 最多尝试 MAX_CANDIDATES_PER_CAR 个
    tried = 0
    best = {"score": -1, "data": None, "url": None, "dims": None}
    for url in candidates:
        if tried >= MAX_CANDIDATES_PER_CAR:
            break
        tried += 1
        print(f"  [{tried}/{MAX_CANDIDATES_PER_CAR}] {url[:100]}")
        time.sleep(0.5)
        data = fetch(url, timeout=TIMEOUT, headers={
            "Referer": "https://www.bing.com/",
        })
        if not data:
            log_entry["tried"].append({"url": url, "status": "fetch_failed"})
            continue
        if not is_image_bytes(data):
            log_entry["tried"].append({
                "url": url, "status": "not_image",
                "size": len(data), "head_hex": data[:4].hex() if data else ""})
            continue

        ok, w, h, reason, bg_type, score, detail = verify_image(data, model)
        log_entry["tried"].append({
            "url": url,
            "status": "ok" if ok else "rejected",
            "w": w, "h": h,
            "ratio": round(w / h, 3) if h else 0,
            "size_kb": len(data) // 1024,
            "bg_type": bg_type,
            "score": round(score, 2),
            "reason": reason,
            "detail": detail,
        })
        print(f"      {reason}  size={len(data)//1024}KB")
        if not ok:
            continue

        # 累计最佳（评分最高）
        if score > best["score"]:
            best = {"score": score, "data": data, "url": url, "dims": (w, h)}
            # 找到理想区间的高分图，提前结束
            if score >= 100:
                print(f"      ★ 理想候选，提前结束")
                break

    log_entry["candidates_tried"] = tried

    # 保存最佳
    if best["data"] is not None and best["score"] >= 0:
        dims = save_jpg(best["data"], out_path)
        if dims is None:
            dims = best["dims"]
        md5 = hashlib.md5(out_path.read_bytes()).hexdigest()[:12]
        log_entry["status"] = "success"
        log_entry["source"] = "direct_url" if best["url"] in direct_urls else "bing_image_search"
        log_entry["url"] = best["url"]
        log_entry["dims"] = list(dims)
        log_entry["ratio"] = round(dims[0] / dims[1], 3) if dims[1] else 0
        log_entry["score"] = round(best["score"], 2)
        log_entry["md5"] = md5
        log_entry["file_size"] = out_path.stat().st_size
        log_entry["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"  💾 SAVED  {dims[0]}x{dims[1]} ratio={dims[0]/dims[1]:.2f} "
              f"score={best['score']:.1f}  md5={md5}")
        print(f"      {out_path}")
        return True, log_entry

    log_entry["status"] = "no_side_profile_found"
    log_entry["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"  ✗ 失败: 未找到合格侧视图")
    return False, log_entry


# ====================================================================
# 主流程
# ====================================================================
def main():
    print("=" * 70)
    print("v11: 重新下载 5 张失败的车型正侧视官图")
    print("=" * 70)
    print(f"目标车型: {[c['model'] for c in CARS]}")
    print(f"宽高比范围: {ASPECT_MIN}-{ASPECT_MAX} (理想 {ASPECT_IDEAL_LO}-{ASPECT_IDEAL_HI})")
    print(f"每车最多尝试: {MAX_CANDIDATES_PER_CAR} 个候选")
    print(f"UA: {UA}")
    print(f"超时: {TIMEOUT}s  SSL 验证: 关闭")
    print(f"日志: {LOG_PATH}")

    results = {}
    # 中途崩溃也保留已完成的日志
    LOG_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    for car in CARS:
        try:
            ok, log_entry = download_car(car)
        except Exception as e:
            import traceback
            print(f"\n  异常: {e}")
            traceback.print_exc()
            log_entry = {
                "brand": car["brand"], "model": car["model"],
                "status": f"error:{e}",
                "out_path": str(BASE_DIR / car["brand"] / f"{car['model']}.jpg"),
            }
            ok = False
        results[f"{car['brand']}/{car['model']}"] = log_entry
        # 实时写日志
        LOG_PATH.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8")
        time.sleep(1.5)

    # 汇总
    print("\n" + "=" * 70)
    print("汇总:")
    ok_n = sum(1 for v in results.values() if v.get("status") == "success")
    print(f"  成功 {ok_n}/{len(CARS)}")
    for key, v in results.items():
        st = v.get("status", "unknown")
        ratio = v.get("ratio")
        src = v.get("source", "")
        tried = v.get("candidates_tried", 0)
        print(f"  {key:30s} {st:24s} ratio={ratio}  tried={tried}  src={src}")
    print(f"\n日志: {LOG_PATH}")


if __name__ == "__main__":
    main()
