# -*- coding: utf-8 -*-
"""fix_11_side_profile.py
从 NetCarShow 下载11款不合格车型的 Side_Profile（正侧视）官图。
NetCarShow 的 Side_Profile 视图是官方制造商官图，保证正侧视角度。
若 NetCarShow 不可达，回退到 Bing 中文关键词搜索 + 候选筛选。
"""
import hashlib, io, json, re, ssl, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image as P

CUR = Path(__file__).resolve().parent
PROJECT = CUR.parent
BRANDS = PROJECT / "public" / "brands"
TMP = CUR / "_fix11_tmp"
TMP.mkdir(exist_ok=True)
LOG = {}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
BASE = "https://www.netcarshow.com"
CTX = ssl._create_unverified_context()

# 11款不合格车型 (brand, model, netcarshow_url, bing_query)
CARS = [
    ("rolls-royce", "ghost",          "https://www.netcarshow.com/rolls-royce/2021-ghost/",                 "劳斯莱斯古思特 正侧面 官图"),
    ("rolls-royce", "cullinan",       "https://www.netcarshow.com/rolls-royce/2020-cullinan/",               "劳斯莱斯库里南 正侧面 官图"),
    ("bentley",     "continental-gtc","https://www.netcarshow.com/bentley/2019-continental_gt_convertible/", "宾利欧陆GT敞篷 正侧面 官图"),
    ("bentley",     "flying-spur",    "https://www.netcarshow.com/bentley/2020-flying_spur/",                "宾利飞驰 正侧面 官图"),
    ("bentley",     "bentayga",       "https://www.netcarshow.com/bentley/2021-bentayga/",                   "宾利添越 正侧面 官图"),
    ("bugatti",     "veyron",         "https://www.netcarshow.com/bugatti/2005-veyron/",                     "布加迪威航 正侧面 官图"),
    ("bugatti",     "divo",           "https://www.netcarshow.com/bugatti/2019-divo/",                        "布加迪迪沃 正侧面 官图"),
    ("porsche",     "cayenne",        "https://www.netcarshow.com/porsche/2020-cayenne/",                     "保时捷卡宴 正侧面 官图"),
    ("porsche",     "macan",          "https://www.netcarshow.com/porsche/2021-macan/",                       "保时捷Macan 正侧面 官图"),
    ("ferrari",     "sf90",           "https://www.netcarshow.com/ferrari/2020-sf90_stradale/",               "法拉利SF90 正侧面 官图"),
    ("ferrari",     "f8-tributo",     "https://www.netcarshow.com/ferrari/2019-f8_tributo/",                  "法拉利F8 正侧面 官图"),
]


def fetch(url, timeout=20, referer=None):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"    FETCH_ERR {type(e).__name__}: {str(e)[:80]}")
        return None


def extract_side_urls(html):
    """提取 Side_Profile 缩略图URL 和 1280 大图URL"""
    sides = re.findall(r'["\']([^"\']*Side_Profile[^"\']*\.jpg)["\']', html, re.I)
    sides = list(dict.fromkeys(sides))
    # 也找 1280 大图
    bigs = re.findall(r'["\']([^"\']*-1280[^"\']*\.jpg)["\']', html, re.I)
    bigs = list(dict.fromkeys(bigs))
    return sides, bigs


def download_img(url, timeout=25):
    if url.startswith("/"):
        url = BASE + url
    raw = fetch(url, timeout=timeout, referer=BASE + "/")
    return raw


def save_jpg(raw, path):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=92, optimize=True, progressive=True)
            path.write_bytes(bio.getvalue())
            return im.size
    except Exception:
        path.write_bytes(raw)
        return (0, 0)


def analyze(raw):
    """分析图片：宽高比、背景纯净度"""
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
            asp = w / h if h else 0
            im_s = im.convert("RGB").resize((200, 150))
            px = list(im_s.getdata())
            W, H = 200, 150
            corners = [(0,0),(W-1,0),(0,H-1),(W-1,H-1),(W//2,0),(W//2,H-1),(0,H//2),(W-1,H//2)]
            cc = [px[y*W+x] for x,y in corners]
            max_diff = max(max(c[i] for c in cc)-min(c[i] for c in cc) for i in range(3))
            sky = sum(1 for r,g,b in px if b>150 and b>r+30 and b>g+10)/len(px)
            grass = sum(1 for r,g,b in px if g>100 and g>r+20 and g>b+10)/len(px)
            dark = sum(1 for r,g,b in px if (r+g+b)/3<50)/len(px)
            light = sum(1 for r,g,b in px if (r+g+b)/3>220)/len(px)
            return {"w":w,"h":h,"asp":asp,"max_diff":max_diff,
                    "sky":sky,"grass":grass,"dark":dark,"light":light}
    except Exception:
        return None


def try_netcarshow(brand, model, ncs_url):
    """尝试从 NetCarShow 下载 Side_Profile 图"""
    print(f"  [NetCarShow] {brand}/{model}")
    html = fetch(ncs_url, timeout=20)
    if not html:
        print("    HTML获取失败")
        return None
    html = html.decode("utf-8", errors="replace")
    sides, bigs = extract_side_urls(html)
    print(f"    Side_Profile URLs: {len(sides)}, 1280 URLs: {len(bigs)}")
    # 优先下载 1280 大图（如果有对应的 side profile）
    for big in bigs:
        if "side_profile" in big.lower() or "side" in big.lower():
            raw = download_img(big)
            if raw and len(raw) > 30000:
                print(f"    下载1280大图成功 {len(raw)} bytes")
                return raw
    # 否则下载 side_profile 缩略图
    for s in sides:
        raw = download_img(s)
        if raw and len(raw) > 30000:
            print(f"    下载side_profile图成功 {len(raw)} bytes")
            return raw
    return None


def bing_search(query, num=20):
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1"
    raw = fetch(url, timeout=15)
    if not raw:
        return []
    html = raw.decode("utf-8", errors="replace")
    urls = re.findall(r'murl["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
    urls += re.findall(r'mediaurl=(https?[^&"\']+)', html)
    urls += re.findall(r'imgurl=(https?[^&"\']+)', html)
    seen = set()
    out = []
    for u in urls:
        u = urllib.parse.unquote(u).strip()
        if u in seen or not u.startswith("http"):
            continue
        seen.add(u)
        low = u.lower()
        if any(e in low for e in [".jpg",".jpeg",".png",".webp"]):
            out.append(u)
        if len(out) >= num:
            break
    return out


def try_bing(brand, model, query):
    """Bing搜索回退方案"""
    print(f"  [Bing] {brand}/{model}: {query}")
    urls = bing_search(query)
    print(f"    候选URL: {len(urls)}")
    BAD = ["wallpaper","hdqwalls","shutterstock","istockphoto","gettyimages",
           "dreamstime","pixabay","pinterest","pinimg","freepik","pngtree"]
    cands = []
    for u in urls:
        low = u.lower()
        if any(b in low for b in BAD):
            continue
        raw = fetch(u, timeout=20, referer="https://www.bing.com/")
        if not raw or len(raw) < 25000:
            continue
        info = analyze(raw)
        if not info:
            continue
        # 正侧视宽高比 1.5-2.5
        if info["asp"] < 1.4 or info["asp"] > 2.6:
            continue
        # 排除户外
        if info["sky"] > 0.15 or info["grass"] > 0.10:
            continue
        cands.append((raw, info, u))
        print(f"    候选 {len(cands)}: {info['w']}x{info['h']} asp={info['asp']:.2f} diff={info['max_diff']} {u[:60]}")
        if len(cands) >= 5:
            break
    if not cands:
        return None
    # 选背景最纯净的（max_diff最小）
    cands.sort(key=lambda x: x[1]["max_diff"])
    best = cands[0]
    print(f"    最佳: diff={best[1]['max_diff']} {best[2][:60]}")
    return best[0]


def main():
    for brand, model, ncs_url, bing_q in CARS:
        print(f"\n=== {brand}/{model} ===")
        key = f"{brand}/{model}"
        entry = {"brand": brand, "model": model, "status": "pending"}

        # 方案1: NetCarShow
        raw = try_netcarshow(brand, model, ncs_url)
        source = "netcarshow"

        # 方案2: Bing回退
        if not raw:
            print(f"  NetCarShow失败，尝试Bing...")
            raw = try_bing(brand, model, bing_q)
            source = "bing"

        if not raw:
            entry["status"] = "failed"
            print(f"  !! 全部失败")
            LOG[key] = entry
            continue

        # 保存到临时目录
        tmp_path = TMP / f"{brand}_{model}.jpg"
        size = save_jpg(raw, tmp_path)
        info = analyze(tmp_path.read_bytes())
        md5 = hashlib.md5(tmp_path.read_bytes()).hexdigest()[:12]

        entry.update({
            "status": "downloaded",
            "source": source,
            "tmp_path": str(tmp_path),
            "size": list(size),
            "md5": md5,
            "info": info,
        })
        print(f"  => 保存 {size} md5={md5} source={source}")
        if info:
            print(f"     asp={info['asp']:.2f} diff={info['max_diff']} sky={info['sky']:.3f} grass={info['grass']:.3f}")
        LOG[key] = entry
        time.sleep(1)

    out = CUR / "_fix11_log.json"
    out.write_text(json.dumps(LOG, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n日志已保存: {out}")
    ok = sum(1 for v in LOG.values() if v["status"] == "downloaded")
    print(f"完成: {ok}/11 下载成功")


if __name__ == "__main__":
    main()
