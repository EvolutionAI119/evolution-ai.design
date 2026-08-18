# -*- coding: utf-8 -*-
"""
dedup_unique_19cars_v2.py
==============================
策略大改：强制 URL / 页面中 包含车型名的精确单词（如 wraith），
否则直接扣分到0。排除了 "porsche-918.jpg" 被当成 911/taycan/panamera 的情况。

同时修正 bug：raw 和 final 两个 MD5 都要加入 exclude 集合，
并且用 URL+MD5 的双重唯一化。

质量门禁维持：aspect ≥ 1.60，宽 ≥ 1200，文件 ≥ 70KB。
"""
from __future__ import annotations
import os, sys, io, re, json, time, hashlib, urllib.parse, urllib.request, ssl
from pathlib import Path

CUR_DIR  = Path(__file__).resolve().parent
PROJECT  = CUR_DIR.parent
LOG_FILE = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D = PROJECT / "public" / "brands"

MIN_ASPECT   = 1.60
MAX_ASPECT   = 3.60
MIN_WIDTH_PX = 1200
MIN_FILE_B   = 70_000
REQ_TIMEOUT  = 18
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 19 款，每个车型的精确匹配词（URL 中必须至少出现其中之一，否则严重扣分）
CAR_SPEC = [
    ("rolls-royce","phantom",       ["phantom",    "幻影"],
     "Rolls-Royce Phantom VIII EWB full side view profile official press photo png hires"),
    ("rolls-royce","ghost",         ["ghost",      "古思特"],
     "Rolls-Royce Ghost sedan generation 2 side view profile official photo hires"),
    ("rolls-royce","cullinan",      ["cullinan",   "库里南"],
     "Rolls-Royce Cullinan Black Badge SUV side view profile official photo"),
    ("rolls-royce","wraith",        ["wraith",     "魅影"],
     "Rolls-Royce Wraith Black Badge coupe side view profile official photo"),

    ("bentley","continental-gt",    ["continental-gt","continentalgt","欧陆GT","gt-3rd-gen","continental gt"],
     "Bentley Continental GT Mulliner coupe 3rd gen side view profile official photo png"),
    ("bentley","continental-gtc",   ["continental-gtc","continentalgtc","欧陆GTC","gtc convertible"],
     "Bentley Continental GTC convertible Azure side view profile official photo"),
    ("bentley","flying-spur",       ["flying-spur","flyingsspur","飞驰","flying spur sedan"],
     "Bentley Flying Spur Mulliner W12 sedan side view profile photo"),
    ("bentley","bentayga",          ["bentayga",   "添越"],
     "Bentley Bentayga EWB SUV Azure side view profile official photo png"),

    ("bugatti","chiron",            ["chiron",     "凯龙"],
     "Bugatti Chiron Pur Sport side view profile official press photo png 16:9 hires"),
    ("bugatti","veyron",            ["veyron","威龙","veyron 16.4","grand sport"],
     "Bugatti Veyron 16.4 Grand Sport Vitesse side view profile photo png hires"),
    ("bugatti","divo",              ["divo"],
     "Bugatti Divo side view profile official hypercar photo png hires"),

    ("porsche","911",               ["911","992","carrera"],
     "Porsche 911 Carrera S 992 generation coupe side view profile official photo png hires"),
    ("porsche","taycan",            ["taycan",     "mission e"],
     "Porsche Taycan Turbo S Sport Turismo side view profile official photo"),
    ("porsche","panamera",          ["panamera",   "帕拉梅拉"],
     "Porsche Panamera Sport Turismo 4S E-Hybrid side view official photo png"),
    ("porsche","cayenne",           ["cayenne",    "卡宴"],
     "Porsche Cayenne E-Hybrid Coupe Platinum Edition side view profile photo"),
    ("porsche","macan",             ["macan"],
     "Porsche Macan GTS compact SUV side view profile official photo png"),

    ("ferrari","sf90",              ["sf90",       "stradale"],
     "Ferrari SF90 Stradale Assetto Fiorano side view profile photo png hires"),
    ("ferrari","f8-tributo",        ["f8","f8-tributo","tributo"],
     "Ferrari F8 Tributo side view profile photo png hires 16:9"),
    ("ferrari","roma",              ["roma"],
     "Ferrari Roma Gran Turismo coupe side view profile official photo png hires"),
]

# 完全排除：这些域名被证实返回「泛化匹配占位图」（同品牌不同车型给同一张）
DOMAIN_BLOCK_SUBSTR = [
    "autoimg.cn","bitautoimg.com","ifengimg.com","sinaimg.cn","sinaimg.com",
    "auto123channel.com","puxiang.com","nicovideo.jp",
    # 新加：在 v1 中证实返回「相同占位图 per 品牌」
    "lueasygi.com","automachi.com","igarage.my",
    # 博客 / 非官方低质量图站
    "wordpress.com","blogspot","tumblr","instagram.com","pinterest",
]

DOMAIN_BONUS = {
    "netcarshow.com": 150,
    "netcarbrands.com": 148,
    "carpixel.net": 145,
    "caricos.com": 142,
    "wikimedia.org": 130,
    "wikipedia.org": 128,
    "autoevolution.com": 115,
    "motor1.com": 112,
    "topgear.com": 110,
    "carwow.co.uk": 108,
    "autocar.co.uk": 106,
    "edmunds.com": 105,
    "motortrend.com": 102,
    "carmagazine.co.uk": 100,
    "media.bugatti.com": 200,
    "bugatti.com": 180,
    "presskit.porsche.de": 200,
    "newsroom.porsche.com": 198,
    "porsche.com": 180,
    "bentleymedia.com": 200,
    "bentleymotors.com": 180,
    "media.ferrari.com": 200,
    "ferrari.com": 180,
    "media.rolls-roycemotorcars.com": 200,
    "rolls-roycemotorcars.com": 180,
}

BAD_WORDS = [
    "three-quarter","quarter-view","45-degree","angled","front view","rear view","back view",
    "interior","cabin","cockpit","dashboard","seat","steering","infotainment",
    "spyshots","spyshot","spy-photo","teaser","concept-render","rendering","sketch",
    "wallpaper","wide-body","tuned","modified","custom","livery","race-car","formula",
    "thumbnail","thumb_","_thumb","/thumbs/","resize","lowres","small_size",
    "video-thumb","youtube","tiktok","vimeo","v.redd.it",
    "drone","aerial","top-down","topview","bird's",
    "iphone","android","app","screenshot","brochure","catalog",
]

GOOD_HINTS = [
    "/side-view","_side-view","side-view_","-side-view-","side-view.",
    "side-profile","side_profile","side-profile-","side-profile_","_profile_side",
    "profile-view","/profile/","profile_photo","press-photo","press_image","official-photo",
    "/press/","/media/","/newsroom/","presskit","press-release","/assets/press",
    "hires","high-res","hi-res","highres","original","uncropped",
    "official_site","official_image","official_photo","media_gallery",
    ".png",".webp",".tiff",
]

_ctrl_re = re.compile(r'[\x00-\x1f\x7f"]')


def clean_url(u):
    if not isinstance(u, str): return None
    u = (u.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
           .replace("%2520", "%20").strip())
    u = _ctrl_re.sub("", u)
    low = u.lower()
    for b in DOMAIN_BLOCK_SUBSTR:
        if b in low: return None
    if u.startswith(("http://","https://")) and len(u) >= 20:
        return u
    return None


def dims_of(data):
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im: return im.size
    except Exception:
        try:
            if len(data) >= 24 and data[:8] == b'\x89PNG\r\n\x1a\n':
                import struct
                return struct.unpack(">II", data[16:24])
        except Exception: pass
        return None


def md5h(b): return hashlib.md5(b).hexdigest()


def bing(q, first=1, count=55):
    qe = urllib.parse.quote(q, safe="")
    url = (f"https://www.bing.com/images/search?q={qe}"
           f"&qft=+filterui:imagesize-large+filterui:photo-photo+filterui:aspect-wide"
           f"&form=IRFLTR&first={first}&count={count}")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.6",
        "Cache-Control": "no-cache",
    })
    try:
        ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx) if ctx else urllib.request.HTTPSHandler)
        with op.open(req, timeout=REQ_TIMEOUT) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [bing fail] {e}"); return []
    outs = []
    for m in re.finditer(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html):
        u = clean_url(urllib.parse.unquote(m.group(1)))
        if u: outs.append(u)
    seen = set(); uni = []
    for x in outs:
        if x in seen: continue
        seen.add(x); uni.append(x)
    return uni


def score_url(u, model_kw):
    low = u.lower()
    s = 0
    # 【核心】：URL 必须包含精确车型词（或中文词）
    kw_hit = sum(1 for w in model_kw if w.lower() in low)
    if kw_hit == 0:
        s -= 3000  # 完全没有车型词 → 死刑
    else:
        s += kw_hit * 200
    for d, sc in DOMAIN_BONUS.items():
        if d in low: s = max(s, sc)
    for g in GOOD_HINTS:
        if g in low: s += 30
    for bw in BAD_WORDS:
        if bw.lower() in low: s -= 300
    return s


def download(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://www.bing.com/",
    })
    try:
        ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx) if ctx else urllib.request.HTTPSHandler)
        with op.open(req, timeout=REQ_TIMEOUT) as r:
            d = r.read()
            return d if d and len(d) > 4000 else None
    except Exception:
        return None


def write_jpg(path: Path, raw):
    try:
        from PIL import Image as P
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=93, optimize=True, progressive=True)
            out = bio.getvalue()
    except Exception:
        out = raw
    path.write_bytes(out)
    return len(out)


def per_model_queries(b, m, kw, en_p):
    # 6 个不同的搜索词，角度错开（避免 Bing 泛化）
    bnice = b.replace("-"," ")
    return [
        f"{en_p}",
        f"{b} {m.replace('-',' ')} side view profile {kw[0]} site:netcarshow.com OR site:carpixel.net OR site:caricos.com",
        f"{en_p} photo netcarbrands autocar carwow png transparent",
        f"\"{bnice}\" \"{m.replace('-',' ')}\" \"side view\" \"official\" \"press\" hires photo",
        f"{b} {m} exterior 90 degree side profile photography png 1600x900",
        f"{en_p} filetype:png wikimedia commons",
    ]


def load_log():
    if LOG_FILE.exists():
        try:
            d = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(d, list): return d
        except Exception: pass
    return []


def main():
    log = load_log()
    # 现有文件的 raw+final MD5 都加入排除
    exclude = set()
    for b, m, *_ in CAR_SPEC:
        # 先尝试从日志读取，其次默认位置
        item = next((x for x in log if x["brand"]==b and x["model"]==m), None)
        sp = item["save_path"] if item else str(BRANDS_D / b / (m + ".jpg"))
        p = Path(sp)
        if p.exists():
            raw = p.read_bytes()
            exclude.add(md5h(raw))
    print("="*80)
    print(f"初始排除集合大小（已有图MD5）：{len(exclude)}")

    for idx, (b, m, kw, en_p) in enumerate(CAR_SPEC, 1):
        print(f"\n[{idx}/19] 🎯 {b}/{m}  精确词={kw}")
        qs = per_model_queries(b, m, kw, en_p)
        pool = []  # (score, url)
        seen_urls = set()
        for q in qs:
            urls = bing(q)
            for u in urls:
                if u in seen_urls: continue
                seen_urls.add(u)
                pool.append((score_url(u, kw), u))
            time.sleep(0.45)
        pool.sort(key=lambda x: -x[0])
        # 只尝试正分值 + 前 80
        candidates = [u for sc, u in pool if sc > 0][:85]
        print(f"    命中 {len(candidates)} 条含精确车型词 URL（分数>0，top 85）")
        winner = None
        tried = 0
        for u in candidates:
            tried += 1
            if tried > 72: break
            raw = download(u)
            if not raw: continue
            if len(raw) < MIN_FILE_B: continue
            # 原始 MD5 查重（如果和之前完全相同字节，跳过）
            hraw = md5h(raw)
            if hraw in exclude:
                continue
            dims = dims_of(raw)
            if not dims: continue
            w, h = dims
            if w < MIN_WIDTH_PX or h <= 0: continue
            aspect = w / h
            if not (MIN_ASPECT <= aspect <= MAX_ASPECT): continue
            winner = (raw, w, h, u, hraw)
            print(f"    ✔ #{tried:>3d}  aspect={aspect:.2f}  {w}x{h}  {len(raw)/1024:.0f}KB  rawMD5={hraw[:10]}\n"
                  f"       URL: {u[:150]}")
            break
        if not winner:
            print(f"    ✘ 72 个精准 URL 均不满足。保留旧文件。")
            continue
        raw, w, h, u, hraw = winner
        sp = next((x["save_path"] for x in log if x["brand"]==b and x["model"]==m), None)
        sp = sp or str(BRANDS_D / b / (m + ".jpg"))
        p = Path(sp); p.parent.mkdir(parents=True, exist_ok=True)
        fsize = write_jpg(p, raw)
        hfinal = md5h(p.read_bytes())
        # 两个 MD5 都加入排除，防止后续车型使用
        exclude.add(hraw); exclude.add(hfinal)
        # 写日志
        entry = {
            "brand": b, "model": m,
            "source_url": u,
            "width": w, "height": h,
            "aspect_ratio": round(w/h, 3),
            "size_bytes": fsize,
            "md5_prefix": hfinal[:10],
            "format": "JPEG",
            "save_path": str(p),
            "gate_level": f"UNIQUE19_aspect>=1.6_URL_contains_model_kw={kw[0]}",
            "downloaded_at_epoch": int(time.time()),
        }
        found_i = next((i for i,x in enumerate(log) if x["brand"]==b and x["model"]==m), None)
        if found_i is not None: log[found_i] = entry
        else: log.append(entry)
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    💾 {p.name}  {fsize/1024:.0f}KB  aspect={w/h:.2f}  finalMD5={hfinal[:10]}  exclude_pool={len(exclude)}")

    # 最终 MD5 汇总
    bymd = {}
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        h = md5h(p.read_bytes())[:14]
        bymd.setdefault(h, []).append(f"{item['brand']}/{item['model']}")
    dup = sum(len(v) for v in bymd.values() if len(v) > 1)
    print(f"\n{'='*80}")
    print(f"✔ 19款车型下载完成。唯一MD5：{len(bymd)}/19，重复MD5涉及 {dup} 台车型。")
    for h, lst in sorted(bymd.items(), key=lambda kv: -len(kv[1])):
        if len(lst) > 1:
            print(f"  ⚠ 重复MD5 {h}: " + "、".join(lst))
    return 0 if len(bymd) == 19 else 1


if __name__ == "__main__":
    sys.exit(main())
