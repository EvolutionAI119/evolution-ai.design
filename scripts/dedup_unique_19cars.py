# -*- coding: utf-8 -*-
"""
dedup_unique_19cars.py
==========================================
专门针对 19 款车型下载重复的问题：
  * 每个车型 **必须获得一张 MD5 完全唯一**的正侧视图（不能多车型共享同图）
  * 强制英文精确车型搜索  (Bugatti Chiron side view NOT just Bugatti)
  * 域名黑名单：排除 autoimg.cn / ifengimg / sinaimg 等返回「通用车型图」的聚合站
  * 已下载 MD5 全局排除：通过 set[str] 强制跳过相同文件
  * 严格门禁：aspect ≥ 1.60，宽 ≥ 1200，文件 ≥ 70KB
"""

from __future__ import annotations

import os, sys, io, re, json, time, hashlib, urllib.parse, urllib.request, ssl
from pathlib import Path
from typing import Optional

CUR_DIR  = Path(__file__).resolve().parent
PROJECT  = CUR_DIR.parent
LOG_FILE = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D = PROJECT / "public" / "brands"

# 门禁
MIN_ASPECT   = 1.60
MAX_ASPECT   = 3.60
MIN_WIDTH_PX = 1200
MIN_FILE_KB  = 70_000

REQ_TIMEOUT  = 18
UA           = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

# 19 款车型（中英双语精确搜索词）
CAR_LIST: list[tuple[str, str, str, str]] = [
    # brand, model,   Chinese description,            English precise search
    ("rolls-royce", "phantom",        "劳斯莱斯幻影 长轴距",    "Rolls-Royce Phantom VIII Extended Wheelbase side view profile press photo"),
    ("rolls-royce", "ghost",          "劳斯莱斯古思特",         "Rolls-Royce Ghost Series II sedan side view official photo"),
    ("rolls-royce", "cullinan",       "劳斯莱斯库里南 SUV",     "Rolls-Royce Cullinan SUV side view profile official press photo"),
    ("rolls-royce", "wraith",         "劳斯莱斯魅影 双门轿跑",   "Rolls-Royce Wraith 2-door coupe side view official photo"),
    ("bentley",     "continental-gt", "宾利欧陆 GT 第三代",     "Bentley Continental GT 3rd gen coupe side view official photo"),
    ("bentley",     "continental-gtc","宾利欧陆 GTC 敞篷",      "Bentley Continental GTC convertible side view official"),
    ("bentley",     "flying-spur",    "宾利飞驰 豪华轿车",      "Bentley Flying Spur sedan V8 W12 side view press photo"),
    ("bentley",     "bentayga",       "宾利添越 SUV",           "Bentley Bentayga SUV first generation side view press photo"),
    ("bugatti",     "chiron",         "布加迪 Chiron 凯龙 超跑", "Bugatti Chiron Super Sport 300+ side view profile press photo"),
    ("bugatti",     "veyron",         "布加迪威龙 16.4",         "Bugatti Veyron 16.4 Grand Sport side view photo"),
    ("bugatti",     "divo",           "布加迪 Divo 限量超跑",    "Bugatti Divo limited edition hypercar side view official photo"),
    ("porsche",     "911",            "保时捷 911 Carrera 992", "Porsche 911 Carrera Coupe 992 generation side view official press photo"),
    ("porsche",     "taycan",         "保时捷 Taycan Turbo S",   "Porsche Taycan Turbo S Cross Turismo side view press photo"),
    ("porsche",     "panamera",       "保时捷 Panamera 第二代",  "Porsche Panamera G2 Sport Turismo side view press photo"),
    ("porsche",     "cayenne",        "保时捷卡宴 Coupe",        "Porsche Cayenne Coupe side view official photo"),
    ("porsche",     "macan",          "保时捷 Macan 紧凑SUV",    "Porsche Macan Turbo side view official press photo"),
    ("ferrari",     "sf90",           "法拉利 SF90 Stradale",    "Ferrari SF90 Stradale Assetto Fiorano side view press photo"),
    ("ferrari",     "f8-tributo",     "法拉利 F8 Tributo",       "Ferrari F8 Tributo coupe side view official press photo"),
    ("ferrari",     "roma",           "法拉利 Roma GT",          "Ferrari Roma coupe side view profile official press photo"),
]

# 域名排除：这些都是中国门户汽车图床，对精确搜索总是返回相同通用占位图，必须排除
DOMAIN_BLACKLIST_SUBSTR = [
    "autoimg.cn",      # 汽车之家（cardfs/product 4:3模板 + 通用占位图）
    "bitautoimg.com",  # 易车
    "ifengimg.com",    # 凤凰汽车
    "sinaimg.cn",      # 新浪汽车
    "sinaimg.com",
    "auto123channel.com",  # 加拿大汽车频道，返回同一张通用图占位
    # 低质量图片站点
    "autohome.com.cn/upload/",
    "puxiang.com",     # 图床
    "nicovideo.jp",    # 视频缩略图
]

# 域名白名单（给高分）
DOMAIN_WHITELIST = {
    "netcarshow.com":         120,
    "netcarbrands.com":       118,
    "caricos.com":            115,
    "carpixel.net":           112,
    "wikimedia.org":          100,
    "wikipedia.org":          98,
    # 各品牌官方媒体库 / 官网
    "media.bugatti.com":      150,
    "bugatti.com":            140,
    "presskit.porsche.de":    150,
    "newsroom.porsche.com":   148,
    "porsche.com":            140,
    "media.rolls-roycemotorcars.com": 150,
    "rolls-roycemotorcars.com": 140,
    "bentleymedia.com":       150,
    "bentleymotors.com":      140,
    "media.ferrari.com":      150,
    "ferrari.com":            140,
    # 专业汽车媒体
    "autoevolution.com":      95,
    "motor1.com":             93,
    "topgear.com":            92,
    "carwow.co.uk":           90,
    "autocar.co.uk":          89,
    "edmunds.com":            87,
    "motortrend.com":         85,
    "carmagazine.co.uk":      84,
    "drivespark.com":         80,
}

BAD_WORDS = [
    "threedquarters","three quarter","three-quarter","quarter",
    "45-degree","front view","rear view","back view","head-on",
    "interior","cabin","cockpit","dashboard","dashboard-view",
    "facelift-spy","spyshot","rendering","teaser","sketch","drawing","illustration",
    "video","youtube","tiktok","vimeo","thumbnail","thumb_",
    "wallpaper","wide-body","custom","tuned","modified","race","livery","rally",
    "drone","aerial","bird's-eye","top-down","top-down-view","top-view",
    # 避免同车型不同配置重复
    "launch-edition","one-of-one","special","limited-edition",
]

GOOD_SIGNALS = [
    "/side-view","_side-view","side-view_","-side-view-","side-view.",
    "/side_profile","side-profile","profile-view","side-view-official",
    "_profile","/profile/","profile_photo","press-photo",
    "/press/","/media/","/newsroom/","presskit","press-release",
    "official-photo","official-image","hires","high-res","hi-res",
    ".png",".webp",
]

_ctrl_re = re.compile(r'[\x00-\x1f\x7f"]')


def clean_url(u):
    if not isinstance(u, str): return None
    u = (u.replace("&amp;", "&").replace("&quot;", '"')
           .replace("&#39;", "'").replace("%2520", "%20").strip())
    u = _ctrl_re.sub("", u)
    low = u.lower()
    for b in DOMAIN_BLACKLIST_SUBSTR:
        if b in low:
            return None
    if u.startswith(("http://", "https://")) and len(u) >= 20:
        return u
    return None


def image_dims(data):
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:
        pass
    try:
        if len(data) >= 24 and data[:8] == b'\x89PNG\r\n\x1a\n':
            import struct
            return struct.unpack(">II", data[16:24])
    except Exception: pass
    return None


def md5(b): return hashlib.md5(b).hexdigest()


def bing_search(query, first=1, count=50):
    q = urllib.parse.quote(query, safe="")
    url = (f"https://www.bing.com/images/search?q={q}"
           f"&qft=+filterui:imagesize-large+filterui:photo-photo+filterui:aspect-wide"
           f"&form=IRFLTR&first={first}&count={count}")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,zh-CN;q=0.7",
    })
    try:
        ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx) if ctx else urllib.request.HTTPSHandler)
        with opener.open(req, timeout=REQ_TIMEOUT) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [bing fail] {e}"); return []
    outs = []
    for m in re.finditer(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html):
        u = clean_url(urllib.parse.unquote(m.group(1)))
        if u:
            outs.append(u)
    seen = set(); u = []
    for x in outs:
        if x in seen: continue
        seen.add(x); u.append(x)
    return u


def url_score(u):
    low = u.lower()
    sc = 0
    for d, s in DOMAIN_WHITELIST.items():
        if d in low: sc = max(sc, s)
    for g in GOOD_SIGNALS:
        if g in low: sc += 20
    for b in BAD_WORDS:
        if b.lower() in low: sc -= 150
    return sc


def download(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    try:
        ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx) if ctx else urllib.request.HTTPSHandler)
        with opener.open(req, timeout=REQ_TIMEOUT) as r:
            d = r.read()
            return d if d and len(d) > 4000 else None
    except Exception:
        return None


def save_jpg(path: Path, raw: bytes, dims):
    try:
        from PIL import Image as PImage
        with PImage.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=92, optimize=True, progressive=True)
            final = bio.getvalue()
    except Exception:
        final = raw
    path.write_bytes(final)
    return len(final)


def build_queries(brand, model, zh, en_precise):
    return [
        # 精确英文（最优先）
        f"{en_precise}",
        # 精确英文 + 白名单网域
        f"{en_precise} site:netcarshow.com OR site:netcarbrands.com OR site:carpixel.net OR site:caricos.com",
        # 精确英文 + 官网媒体库
        f"{en_precise} press media official photo hires",
        # 中文辅助（如果英文找不到，使用中文精确关键词，但会排除国内门户图床）
        f"{zh} 正侧视图 专业汽车媒体 官方媒体图 宽屏 高清 非壁纸",
    ]


def load_log():
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list): return data
        except Exception:
            pass
    return []


def save_log(lst):
    LOG_FILE.write_text(json.dumps(lst, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    log = load_log()
    existing_sp = {}  # brand/model → 当前条目（用于读取已保存图片以便建立全局 MD5 排除表）
    for item in log:
        existing_sp[(item["brand"], item["model"])] = item

    # 先建立所有当前保存的文件的 MD5 全局排除集合
    md5_exclude = set()
    print("=" * 80)
    print("扫描现有 19 张图，建立全局 MD5 排除集合：")
    for b, m, zh, en in CAR_LIST:
        sp = existing_sp.get((b,m), {}).get("save_path") or str(BRANDS_D / b / (m + ".jpg"))
        p = Path(sp)
        if p.exists():
            h = md5(p.read_bytes())
            print(f"  {b+ '/' + m:<32s} MD5 {h[:12]}  size={p.stat().st_size/1024:.0f}KB")
            md5_exclude.add(h)
        else:
            print(f"  {b+ '/' + m:<32s} 文件不存在，需要首次下载")
    print(f"\n当前已有唯一 MD5：{len(md5_exclude)} 个。新下载必须全部不同。\n")

    successes = 0
    for idx, (brand, model, zh, en) in enumerate(CAR_LIST, 1):
        print(f"\n[{idx}/19] 🎯 {brand}/{model}（{zh}）")
        queries = build_queries(brand, model, zh, en)
        ranked = []  # url list（按分数降序）
        tried_urls = set()
        for q in queries:
            urls = bing_search(q)
            scored = []
            for u in urls:
                if u in tried_urls: continue
                # 额外检查：关键词匹配
                lowu = u.lower()
                lowq = q.lower()
                penalty = 0
                # 如果搜索词包含具体车型英文单词，URL 中至少包含一个
                en_kw_list = [w.lower() for w in re.split(r'[\s\-]+', en) if len(w) >= 5]
                if en_kw_list:
                    match = sum(1 for w in en_kw_list if w in lowu)
                    if match == 0:
                        penalty -= 80   # URL 不含任何精确车型词：严重扣分
                sc = url_score(u) + penalty
                scored.append((sc, u))
                tried_urls.add(u)
            scored.sort(key=lambda x: -x[0])
            ranked.extend([u for _, u in scored])
            time.sleep(0.4)

        # 取 top 80 URL 尝试下载（去重）
        seen = set(); candidates = []
        for u in ranked:
            if u in seen: continue
            seen.add(u); candidates.append(u)
        candidates = candidates[:85]
        print(f"    候选 {len(candidates)} 条 URL，尝试下载中…")

        winner = None
        tried_n = 0
        for u in candidates:
            tried_n += 1
            if tried_n > 75:
                break
            raw = download(u)
            if not raw or len(raw) < MIN_FILE_KB:
                continue
            dims = image_dims(raw)
            if not dims: continue
            w, h = dims
            if w < MIN_WIDTH_PX or h <= 0: continue
            aspect = w / h
            if not (MIN_ASPECT <= aspect <= MAX_ASPECT): continue
            h_now = md5(raw)
            if h_now in md5_exclude:
                continue   # 必须唯一！
            winner = (raw, w, h, u, h_now)
            print(f"    ✔ #{tried_n} OK  w={w} h={h} aspect={aspect:.2f} size={len(raw)/1024:.0f}KB\n       MD5 {h_now[:12]} (NEW)")
            print(f"       URL: {u[:150]}")
            break
        if not winner:
            print(f"    ✘ 所有候选均未通过唯一性/长宽比门禁。跳过。")
            continue
        raw, w, h, u, hh = winner
        sp = existing_sp.get((brand,model), {}).get("save_path") or str(BRANDS_D / brand / (model + ".jpg"))
        p = Path(sp)
        p.parent.mkdir(parents=True, exist_ok=True)
        final_size = save_jpg(p, raw, (w,h))
        # 最终保存后 MD5（因为 convert 成 JPEG 后字节可能变了）
        final_md5 = md5(p.read_bytes())
        md5_exclude.add(final_md5)
        # 写回日志
        new_entry = {
            "brand": brand, "model": model,
            "source_url": u, "width": w, "height": h,
            "aspect_ratio": round(w/h, 3),
            "size_bytes": final_size,
            "md5_prefix": final_md5[:10],
            "format": "JPEG",
            "save_path": str(p),
            "gate_level": "STRICT_UNIQUE_19CARS_aspect>=1.6_md5unique",
            "downloaded_at_epoch": int(time.time()),
        }
        found_i = None
        for i, it in enumerate(log):
            if it.get("brand")==brand and it.get("model")==model:
                found_i = i; break
        if found_i is not None:
            log[found_i] = new_entry
        else:
            log.append(new_entry)
        save_log(log)
        successes += 1
        print(f"    💾 保存成功 {brand}/{model} → {p.name}  [{final_size/1024:.0f}KB]  aspect={w/h:.2f}  MD5 {final_md5[:10]}")

    print(f"\n{'='*80}")
    print(f"✔ 完成：19款中成功 {successes} 款。最终唯一图片：{len(md5_exclude)} 张。")
    return 0 if successes == 19 else 1


if __name__ == "__main__":
    sys.exit(main())
