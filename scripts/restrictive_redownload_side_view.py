# -*- coding: utf-8 -*-
"""
restrictive_redownload_side_view.py
====================================================
针对已下载车型中 w/h < 1.6 的疑似非正侧视图，
使用更严格的长宽比门禁（MIN_ASPECT=1.60）
进行重新下载，确保最终图片是水平长条形裁切的纯正90度正侧视图。

同时强制排除 autohome 4:3 标准模板图库（通过 URL 特征），
优先选择：
    * PNG 透明背景的官方媒体图
    * 已裁切为纯侧面车影的长图（无环境背景）
    * netcarshow / netcarbrands 等西方媒体图库（多为纯正侧视）

运行：
    cd d:\\API\\Evolution-Ai.Design
    python scripts\\restrictive_redownload_side_view.py
"""

from __future__ import annotations

import os, sys, io, re, json, time, hashlib, urllib.parse, pathlib, traceback
from pathlib import Path
from typing import Optional

CUR_DIR  = Path(__file__).resolve().parent
PROJECT  = CUR_DIR.parent
SRC_LOG  = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D = PROJECT / "public" / "brands"

# ---------  严格门禁  ---------
MIN_ASPECT      = 1.60   # 必须是长条形（16:10起）
MAX_ASPECT      = 3.60
MIN_WIDTH_PX    = 1200   # 至少 1200px 宽
MIN_FILE_BYTES  = 80_000 # 80KB

REQUEST_TIMEOUT = 18
MAX_RESULTS     = 32
USER_AGENT      = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

REQUEST_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en,zh-CN;q=0.7"}

# ---------  已确认车型 key → 中文名  ---------
# 用于 Bing 中文精准搜索
MODELS_ZH = {
    # 劳斯莱斯
    ("rolls-royce","phantom")        : ("劳斯莱斯幻影",      "Rolls-Royce Phantom luxury sedan official side view"),
    ("rolls-royce","ghost")          : ("劳斯莱斯古思特",    "Rolls-Royce Ghost sedan official side view"),
    ("rolls-royce","cullinan")       : ("劳斯莱斯库里南SUV", "Rolls-Royce Cullinan SUV official side view"),
    ("rolls-royce","wraith")         : ("劳斯莱斯魅影",      "Rolls-Royce Wraith coupe official side view"),
    # 宾利
    ("bentley","continental-gt")     : ("宾利欧陆GT",        "Bentley Continental GT coupe official side view"),
    ("bentley","continental-gtc")    : ("宾利欧陆GTC敞篷",   "Bentley Continental GTC convertible side view"),
    ("bentley","flying-spur")        : ("宾利飞驰",          "Bentley Flying Spur sedan official side view"),
    ("bentley","bentayga")           : ("宾利添越SUV",       "Bentley Bentayga SUV official side view"),
    # 布加迪
    ("bugatti","chiron")             : ("布加迪Chiron凯龙",  "Bugatti Chiron hypercar official side view"),
    ("bugatti","veyron")             : ("布加迪威龙",        "Bugatti Veyron supercar official side view"),
    ("bugatti","divo")               : ("布加迪Divo",        "Bugatti Divo hypercar official side view"),
    # 保时捷
    ("porsche","911")                : ("保时捷911 Carrera", "Porsche 911 Carrera coupe official side view"),
    ("porsche","taycan")             : ("保时捷Taycan电动",  "Porsche Taycan EV sedan official side view"),
    ("porsche","panamera")           : ("保时捷Panamera",    "Porsche Panamera sedan official side view"),
    ("porsche","cayenne")            : ("保时捷卡宴SUV",     "Porsche Cayenne SUV official side view"),
    ("porsche","macan")              : ("保时捷Macan紧凑SUV","Porsche Macan compact SUV official side view"),
    # 法拉利
    ("ferrari","sf90")               : ("法拉利SF90 Stradale","Ferrari SF90 Stradale supercar official side view"),
    ("ferrari","f8-tributo")         : ("法拉利F8 Tributo",  "Ferrari F8 Tributo supercar official side view"),
    ("ferrari","roma")               : ("法拉利Roma",        "Ferrari Roma GT coupe official side view"),
}

# 域名优先级白名单（越高越靠前）
DOMAIN_PRIORITY = {
    # 汽车媒体 - 提供大量纯正侧视媒体图
    "netcarshow.com":     105,
    "netcarbrands.com":   102,
    "caricos.com":        100,
    "autodata1.com":      98,
    # 品牌官网
    "rolls-roycemotorcars.com": 95,
    "bentleymotors.com":        95,
    "bugatti.com":              95,
    "porsche.com":              95,
    "ferrari.com":              95,
    # 媒体图
    "autoevolution.com": 90,
    "carwow.co.uk":       88,
    "topgear.com":        86,
    "motor1.com":         84,
    "motortrend.com":     82,
    # 维基共享（高清）
    "wikimedia.org":      70,
    "wikipedia.org":      70,
    # 专业汽车壁纸站
    "carpixel.net":       90,
    # 汽车之家 (中国) - 只允许非 product/ 路径
    "autohome.com.cn":    60,
}

# --- 坏词过滤（排除 3/4 视角、内饰、前脸等） ---
BAD_KEYWORDS = [
    "interior","cockpit","cabin","内","内饰","中控台","仪表盘","座椅","方向盘",
    "front view","rear view","back view","前脸","车尾","后视图","正脸","尾部",
    "headlight","taillight","wheel-rim","rim","轮毂","轮胎","引擎盖细节",
    "threedquarters","three quarter","3/4","three-quarter","quarter-view",
    "45-degree","45度","斜","斜视图","倾侧",
    "faced","facing","迎面","head-on","迎面视角",
    "wallpaper","壁纸","live-photo","concept-art","插画","卡通","schematic","sketch","render",
    "racing-livery","改装","custom","police","taxi","ambulance",
    "die-cast","diecast","model-car","玩具","乐高","lego"
]
# URL 中包含这些路径段的（说明是汽车之家的图库分类页缩略图，极可能是3/4视角）
BAD_URL_HINTS = [
    "autohome.com.cn/photo/series",
    "autohome.com.cn/spec/",
    "cardfs/product",   # 汽车之家图库缩略图模板
    "bitauto.com/photo",
]
# URL 包含这些是好的（直接指向官方正侧视媒体库）
GOOD_URL_HINTS = [
    "netcarshow.com/cars/",
    "netcarbrands.com/cars/",
    "caricos.com/image/",
    "/side-view/",
    "/side_profile/",
    "side-profile",
    "_side_",
    "-side.",
    "transparent",
    "official-images",
    "press",
    "media",
    ".png",
    ".webp",
]

_re_local = re
_re_non_url = re.compile(r'[\x00-\x1f\x7f"]')

def clean_url(u: str) -> Optional[str]:
    if not isinstance(u, str): return None
    u = (u.replace("&amp;", "&").replace("&quot;", '"')
           .replace("&#39;", "'").replace("%2520", "%20").strip())
    u = _re_non_url.sub("", u)
    # 明确排除汽车之家图库缩略图（4:3模板）
    low = u.lower()
    for b in BAD_URL_HINTS:
        if b in low:
            return None
    if u.startswith(("http://","https://")) and len(u) >= 18:
        return u
    return None

def get_image_dimensions(data: bytes) -> Optional[tuple[int,int]]:
    """优先 Pillow 解析（兼容 WebP），失败再走手动解析。"""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            return im.size  # (w, h)
    except Exception:
        pass
    # ---- 手动兜底（JPEG / PNG / GIF） ----
    try:
        if len(data) >= 24 and data[:8] == b'\x89PNG\r\n\x1a\n':
            import struct
            w, h = struct.unpack(">II", data[16:24])
            return (w, h)
        if len(data) >= 6 and data[:2] == b'\xff\xd8':
            idx = 2
            while idx < len(data) - 9:
                b = data[idx]
                if b != 0xFF:
                    idx += 1; continue
                marker = data[idx+1]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4,0xC8,0xCC):
                    import struct
                    h, w = struct.unpack(">HH", data[idx+5:idx+9])
                    return (w, h)
                if 0xD0 <= marker <= 0xD9 or marker == 0xDA:
                    break
                if data[idx+2:idx+4]:
                    import struct
                    seg_len = struct.unpack(">H", data[idx+2:idx+4])[0]
                    idx += 2 + seg_len
                else:
                    idx += 1
        if len(data) >= 10 and data[:6] in (b'GIF87a', b'GIF89a'):
            import struct
            w, h = struct.unpack("<HH", data[6:10])
            return (w, h)
    except Exception:
        pass
    return None

def md5_of(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()

# =========================================================
#  Bing 图片搜索（Python）
# =========================================================
def bing_image_search(query: str, count: int = MAX_RESULTS) -> list[str]:
    """通过 Bing Images 搜索，返回候选 URL。"""
    import urllib.request
    q_url = urllib.parse.quote(query, safe="")
    # first 强制大图、照片、宽高比"宽"
    url = (f"https://www.bing.com/images/search?q={q_url}"
           f"&qft=+filterui:imagesize-large+filterui:photo-photo+filterui:aspect-wide"
           f"&form=IRFLTR&first=1&count={count}")
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
    })
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [Bing] 搜索失败: {e}")
        return []
    # 提取 murl= 中的真实图片 URL
    out: list[str] = []
    for m in re.finditer(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html):
        raw = m.group(1)
        cleaned = clean_url(urllib.parse.unquote(raw))
        if cleaned:
            out.append(cleaned)
    # 去重保序
    seen = set(); uniqs = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniqs.append(u)
    return uniqs[:count]

def domain_score(url: str) -> int:
    low = url.lower()
    score = 0
    for d, s in DOMAIN_PRIORITY.items():
        if d in low:
            score = max(score, s)
    for g in GOOD_URL_HINTS:
        if g in low:
            score += 15
    for b in BAD_URL_HINTS:
        if b in low:
            score -= 100
    return score

def has_bad_keywords(url: str, query: str = "") -> bool:
    t = (url + " " + query).lower()
    for k in BAD_KEYWORDS:
        if k.lower() in t:
            return True
    return False

def download_once(url: str) -> Optional[bytes]:
    import urllib.request, ssl
    ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
    req = urllib.request.Request(url, headers=REQUEST_HEADERS)
    try:
        opener_kwargs = {"context": ctx} if ctx is not None else {}
        import urllib.request as _ur
        opener = _ur.build_opener(_ur.HTTPSHandler(context=ctx) if ctx else _ur.HTTPSHandler)
        with opener.open(req, timeout=REQUEST_TIMEOUT) as r:
            data = r.read()
            if data and len(data) > 4000:
                return data
    except Exception as e:
        pass
    return None

# =========================================================
#  主流程
# =========================================================
def load_existing_log() -> list:
    if SRC_LOG.exists():
        try:
            data = json.loads(SRC_LOG.read_text(encoding="utf-8"))
            if isinstance(data, list): return data
            if isinstance(data, dict):
                out = []
                for k, v in data.items():
                    v = dict(v)
                    if "/" in k and "brand" not in v:
                        b, m = k.split("/", 1)
                        v.setdefault("brand", b); v.setdefault("model", m)
                    out.append(v)
                return out
        except Exception:
            pass
    return []

def _info_wh(info: dict) -> tuple[int,int]:
    for wkey, hkey in (("width","height"),("width_px","height_px")):
        if isinstance(info.get(wkey), int) and isinstance(info.get(hkey), int):
            return (info[wkey], info[hkey])
    wh = info.get("width_height")
    if isinstance(wh, (list, tuple)) and len(wh) >= 2:
        return (int(wh[0]), int(wh[1]))
    return (0, 0)

def main():
    # 1. 从现有日志里找出哪些图片 w/h < MIN_ASPECT，或不存在
    log_list = load_existing_log()
    to_refresh: list[tuple[str,str,str]] = []  # (brand, model, save_path)
    print("=" * 80)
    print(f"扫描现有下载结果（共 {len(log_list)} 条），筛选需要严格重下载的 w/h<{MIN_ASPECT} 的车型：")
    for info in log_list:
        brand = info.get("brand")
        model = info.get("model")
        fp    = info.get("save_path") or (str(BRANDS_D / f"{brand}/{model}.jpg") if brand and model else None)
        wh    = _info_wh(info)
        size  = info.get("file_size_bytes") or info.get("size_bytes") or 0
        aspect = (wh[0]/wh[1]) if wh[1] else 0.0
        mark = ""
        if brand and model and (aspect < MIN_ASPECT or not fp or not Path(fp).exists()):
            mark = " ⚠ 需要重下载"
            to_refresh.append((brand, model, fp))
        if brand and model:
            print(f"  {brand+ '/' + model:<35s} w/h={aspect:.2f}  {wh[0]}x{wh[1]}  {size/1024:.0f}KB{mark}")
    print()
    if not to_refresh:
        print("✔ 所有已下载图片均 w/h ≥ 1.6，无需重下载")
        return 0

    print(f"\n共 {len(to_refresh)} 款需要严格模式重下载（长宽比≥{MIN_ASPECT}，宽≥{MIN_WIDTH_PX}，文件≥{MIN_FILE_BYTES//1000}KB）：")
    for b,m,_ in to_refresh:
        print(f"  · {b}/{m}")

    # 2. 依次重下载
    replaced = 0
    for idx, (brand, model, old_path) in enumerate(to_refresh, 1):
        zh, en = MODELS_ZH.get((brand,model), (model, f"{brand} {model} official side view"))
        print(f"\n[{idx}/{len(to_refresh)}] 🔁 {brand}/{model}（{zh}）…")

        queries = [
            f"{zh} 正侧视图 官方 高清 png 透明背景 site:netcarshow.com OR site:netcarbrands.com OR site:caricos.com",
            f"{zh} 正侧视图 官方 高清 side view profile 宽屏 PNG",
            f"{en} site:netcarshow.com/cars OR site:carpixel.net side profile wide",
            f"{en} side view PNG transparent official press media",
            f"{en} official side view high resolution 3440x1440",
            f"{zh} 侧视图 纯正侧面 90度 官方媒体图",
        ]

        all_candidates: list[tuple[int,str]] = []  # (score, url)
        for q in queries:
            urls = bing_image_search(q, count=MAX_RESULTS)
            for u in urls:
                if has_bad_keywords(u, q):
                    continue
                all_candidates.append((domain_score(u), u))
            # 轻微节流
            time.sleep(0.35)

        # 按分数排序，去重 URL
        all_candidates.sort(key=lambda x: -x[0])
        seen = set(); ranked = []
        for sc, u in all_candidates:
            if u in seen: continue
            seen.add(u)
            ranked.append(u)
        print(f"    候选 URL：{len(ranked)} 个（已去重、已过滤坏词）")

        winner = None
        tried = 0
        for u in ranked:
            tried += 1
            if tried > 55: break
            data = download_once(u)
            if not data:
                continue
            if len(data) < MIN_FILE_BYTES:
                continue
            dims = get_image_dimensions(data)
            if not dims:
                continue
            w, h = dims
            if w < MIN_WIDTH_PX:
                continue
            if h <= 0: continue
            aspect = w / h
            if not (MIN_ASPECT <= aspect <= MAX_ASPECT):
                continue
            # 合格！
            print(f"    ✔ 合格 URL {tried}: w={w} h={h} aspect={aspect:.2f} size={len(data)/1024:.0f}KB\n       {u[:120]}")
            winner = (data, w, h, u)
            break

        if winner is None:
            print(f"    ✘ 所有候选未通过严格门禁（MIN_ASPECT={MIN_ASPECT}）。保留旧图。")
            continue

        # 3. 写盘（用严格门禁的新图覆盖旧图）
        data, w, h, u = winner
        save_path = Path(old_path) if old_path else (BRANDS_D / brand / (model + ".jpg"))
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果原始是 PNG/WebP，保持无损；否则统一存为 JPEG quality=92
        ext = save_path.suffix.lower() or ".jpg"
        pil_kwargs = {}
        final_bytes: bytes
        try:
            from PIL import Image as PImage
            with PImage.open(io.BytesIO(data)) as im:
                im = im.convert("RGB") if ext in (".jpg",".jpeg") else im
                bio = io.BytesIO()
                fmt = "JPEG" if ext in (".jpg",".jpeg") else ("PNG" if ext==".png" else "WEBP")
                if fmt == "JPEG":
                    im.save(bio, fmt, quality=92, optimize=True, progressive=True)
                else:
                    im.save(bio, fmt)
                final_bytes = bio.getvalue()
        except Exception:
            final_bytes = data

        save_path.write_bytes(final_bytes)
        # 更新日志 list（按 brand/model 覆盖原条目，保持 list 格式）
        found = False
        for i, item in enumerate(log_list):
            if item.get("brand") == brand and item.get("model") == model:
                log_list[i] = {
                    **item,
                    "source_url": u,
                    "width": w, "height": h,
                    "aspect_ratio": round(w/h, 3),
                    "size_bytes": len(final_bytes),
                    "md5_prefix": md5_of(final_bytes)[:8],
                    "format": "JPEG" if ext in (".jpg",".jpeg") else ("PNG" if ext==".png" else "WEBP"),
                    "save_path": str(save_path),
                    "gate_level": "STRICT_SIDEVIEW_aspect>=1.6",
                    "downloaded_at_epoch": int(time.time()),
                }
                found = True
                break
        if not found:
            log_list.append({
                "brand": brand, "model": model,
                "source_url": u,
                "width": w, "height": h,
                "aspect_ratio": round(w/h, 3),
                "size_bytes": len(final_bytes),
                "md5_prefix": md5_of(final_bytes)[:8],
                "format": "JPEG" if ext in (".jpg",".jpeg") else ("PNG" if ext==".png" else "WEBP"),
                "save_path": str(save_path),
                "gate_level": "STRICT_SIDEVIEW_aspect>=1.6",
                "downloaded_at_epoch": int(time.time()),
            })
        SRC_LOG.write_text(json.dumps(log_list, ensure_ascii=False, indent=2), encoding="utf-8")
        replaced += 1
        print(f"    💾 已保存 {save_path}  size={len(final_bytes)/1024:.0f}KB  w={w} h={h} aspect={w/h:.2f}")

    print(f"\n{'='*80}")
    print(f"✔ 严格模式重下载完成：替换 {replaced}/{len(to_refresh)} 张图片。")
    print(f"日志：{SRC_LOG}")
    return 0 if replaced == len(to_refresh) else 1

if __name__ == "__main__":
    sys.exit(main())
