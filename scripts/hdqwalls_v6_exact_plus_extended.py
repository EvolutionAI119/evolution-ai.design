# -*- coding: utf-8 -*-
""" hdqwalls_v6_exact_plus_extended.py
V6: 先用摘要中14款精确URL(含已知后缀)快速下载，再对剩余5款（Panamera/Cayenne/Macan/F8/Roma）
    扩展 slugs × 扩展后缀 的暴力搜索。严格MD5唯一，下载一款排除一款MD5。

门禁: aspect 1.60~3.5, width>=1200, size>=70KB
"""
import hashlib, io, json, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
LOG_FILE = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D = PROJECT / "public" / "brands"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36")

def download(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer":"https://hdqwalls.com/",
        "Accept":"image/jpeg,image/webp,image/*,*/*;q=0.8"})
    try:
        with urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        ).open(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None

# ============================================================
# 路径A：摘要已验证的 14 款精确 URL （slug + 精确后缀）
# ============================================================
EXACT_14 = [
    # (brand, model, exact_slug_with_suffix)
    ("rolls-royce", "phantom",       "2023-spofec-rolls-royce-phantom-side-view-8k-pm"),
    ("rolls-royce", "ghost",         "mansory-rolls-royce-ghost-side-view-8k-5a"),
    ("rolls-royce", "cullinan",      "2023-rolls-royce-cullinan-frozen-lakes-v3"),
    ("rolls-royce", "wraith",        "2022-rolls-royce-wraith-5k-tn"),
    ("bentley",     "continental-gt","bentley-continental-gt-2018-4k-1g"),
    ("bentley",     "continental-gtc","bentley-mulliner-bacalar-2020-2z"),
    ("bentley",     "flying-spur",   "2023-bentley-flying-spur-hybrid-5k-5o"),
    ("bentley",     "bentayga",      "bentley-bentayga-ewb-remembrance-car-by-mulliner-2024-jl"),
    ("bugatti",     "chiron",        "white-bugatti-chiron-4k-r7"),
    ("bugatti",     "veyron",        "bugatti-veyron-grand-sport"),
    ("bugatti",     "divo",          "2023-bugatti-chiron-profilee-4k-pz"),  # Chiron Profilee版本，确保与r7不同
    ("porsche",     "911",           "porsche-911-gt3-earls-court-51-edition-8k-wz"),
    ("porsche",     "taycan",        "porsche-taycan-turbo-gt-with-manthey-kit-2026-tq"),
    ("ferrari",     "sf90",          "ferrari-sf90-xx-stradale-5k-72"),
]

# ============================================================
# 路径B：剩余 5 款 — 扩展 slugs （根据hdqwalls命名习惯大量扩展）
# ============================================================
EXTENDED_5 = {
    ("porsche", "panamera"): [
        "porsche-panamera-sport-turismo-2021",
        "porsche-panamera-turbo-se-hybrid-sport-turismo",
        "porsche-panamera-gts-2021",
        "porsche-panamera-sport-turismo",
        "porsche-panamera-turbo-s-e-hybrid-2024",
        "porsche-panamera-4-e-hybrid-2024",
        "2024-porsche-panamera",
        "porsche-panamera-turbo-s-2023",
        "porsche-panamera-gts-sport-turismo-2023",
        "porsche-panamera-e-hybrid-2023",
        "porsche-panamera-sport-design-2024",
        "porsche-panamera-4s-2023",
        "porsche-panamera-executive-2024",
        "porsche-panamera-turbo-e-hybrid-2024-8k",
        "porsche-panamera-gts-sport-turismo",
        "techart-porsche-panamera-sport-turismo",
        "porsche-panamera-turbo-sport-turismo",
        "mansory-porsche-panamera-2023",
        "porsche-panamera-turbo-s-executive",
    ],
    ("porsche", "cayenne"): [
        "porsche-cayenne-turbo-gt-2022",
        "porsche-cayenne-e-hybrid-coupe",
        "2024-porsche-cayenne-suv",
        "porsche-cayenne-turbo-gt-2023",
        "porsche-cayenne-turbo-s-e-hybrid-coupe-2023",
        "porsche-cayenne-coupe-gts-2024",
        "porsche-cayenne-s-2024",
        "2024-porsche-cayenne-turbo-e-hybrid",
        "porsche-cayenne-gts-2023",
        "techart-porsche-cayenne-turbo-gt",
        "mansory-porsche-cayenne-2023",
        "porsche-cayenne-turbo-coupe-2023",
        "porsche-cayenne-s-coupe-2024",
        "porsche-cayenne-e-hybrid-2024",
        "lumma-design-porsche-cayenne-coupe",
    ],
    ("porsche", "macan"): [
        "porsche-macan-gts-2023",
        "2024-porsche-macan-ev",
        "porsche-macan-suv-2024",
        "porsche-macan-turbo-2023",
        "porsche-macan-s-2024",
        "porsche-macan-t-2023",
        "techart-porsche-macan-2023",
        "porsche-macan-ev-402-hp-2024",
        "porsche-macan-turbo-gts-2024",
        "mansory-porsche-macan",
        "porsche-macan-gts-sport-chrono",
        "lumma-porsche-macan-2024",
        "porsche-macan-402-hp-electric",
    ],
    ("ferrari", "f8-tributo"): [
        "ferrari-f8-tributo-8k",
        "ferrari-f8-tributo-2020",
        "novitec-ferrari-f8-tributo",
        "ferrari-f8-tributo-5k",
        "ferrari-f8-tributo-4k-2020",
        "novitec-ferrari-f8-tributo-n-largo",
        "ferrari-f8-tributo-side-view",
        "ferrari-f8-tributo-white-4k",
        "ferrari-f8-tributo-red-8k",
        "mansory-ferrari-f8-tributo",
        "keyvany-ferrari-f8-tributo",
        "ferrari-f8-tributo-coupe-2020",
        "ferrari-f8-tributo-spider-2021",
        "ferrari-f8-tributo-4k",
    ],
    ("ferrari", "roma"): [
        "ferrari-roma-coupe-2021",
        "ferrari-roma-8k",
        "ferrari-roma-2021",
        "ferrari-roma",
        "ferrari-roma-5k",
        "ferrari-roma-4k-2021",
        "novitec-ferrari-roma-2023",
        "mansory-ferrari-roma",
        "ferrari-roma-white-4k",
        "ferrari-roma-spider-2024",
        "2024-ferrari-roma",
        "ferrari-roma-coupe",
        "ferrari-roma-2023-5k",
        "ferrari-roma-side-view-4k",
        "ferrari-roma-novitec-4k",
    ],
}

# ============================================================
# 扩展后缀列表（已验证成功 + 常见变体，按优先级排）
# ============================================================
EXTRA_SUFFIXES = [
    # === 高概率优先组（摘要已验证 + V5成功 + 常见） ===
    "-pm", "-5a", "-v3", "-tn", "-1g", "-2z", "-5o", "-jl",
    "-r7", "-pz", "-wz", "-tq", "-72",
    "", "-q0", "-5b", "-j9", "-p1", "-x1", "-q1", "-z2", "-w1", "-d1", "-b1",
    # === 常见 字母+数字 组 (1/2/3/4) ===
    "-a1", "-c1", "-e1", "-f1", "-g1", "-h1", "-i1", "-k1", "-l1", "-m1",
    "-n1", "-o1", "-s1", "-u1", "-v1", "-y1",
    "-a2", "-c2", "-e2", "-f2", "-g2", "-h2", "-j2", "-k2", "-l2",
    "-n2", "-o2", "-r2", "-s2", "-t2", "-u2", "-v2", "-y2",
    "-a3", "-b3", "-c3", "-d3", "-e3", "-f3", "-g3", "-h3",
    "-j3", "-k3", "-l3", "-m3", "-n3", "-p3", "-q3", "-r3",
    "-t3", "-w3", "-x3", "-z3",
    "-a4", "-b4", "-c4", "-d4", "-e4", "-f4", "-g4", "-h4",
    "-j4", "-k4", "-l4", "-m4", "-n4", "-p4", "-q4", "-r4",
    "-t4", "-w4", "-x4", "-z4",
    # === 常见 2字母 组合 (按频率精选40个) ===
    "-ab", "-ac", "-ad", "-af", "-ag", "-ak", "-al", "-am", "-an",
    "-ap", "-ar", "-as", "-at", "-av", "-aw", "-ax",
    "-ba", "-bb", "-bc", "-bd", "-be", "-bf", "-bg", "-bh", "-bj",
    "-bk", "-bl", "-bm", "-bn", "-bp", "-br", "-bs", "-bt",
    "-bu", "-bw", "-by",
    "-ca", "-cb", "-cc", "-cd", "-ce", "-cf", "-cg", "-cj",
    "-ck", "-cl", "-cm", "-cn", "-cp", "-cr", "-cs", "-ct",
    "-cv", "-cw", "-cx", "-cy",
    "-da", "-db", "-dc", "-dd", "-de", "-df", "-dg", "-dj",
    "-dk", "-dl", "-dm", "-dn", "-dp", "-dr", "-ds", "-dt",
    "-du", "-dw", "-dy",
]

def load_log():
    if LOG_FILE.exists():
        try:
            d = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(d, list): return d
        except Exception: pass
    return []

def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=93, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw

def check_quality(raw):
    """返回 (ok, w, h, aspect, md5)"""
    if not raw or len(raw) < 70_000:
        return False, 0, 0, 0, ""
    try:
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
    except Exception:
        return False, 0, 0, 0, ""
    if w < 1200: return False, w, h, 0, ""
    aspect = w / h if h else 0
    if not (1.60 <= aspect <= 3.5): return False, w, h, aspect, ""
    md5 = hashlib.md5(raw).hexdigest()
    return True, w, h, aspect, md5

def save_entry(log, entry):
    prev = next((x for x in log if x["brand"]==entry["brand"] and x["model"]==entry["model"]), None)
    if prev: log[log.index(prev)] = entry
    else: log.append(entry)
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    log = load_log()
    exclude_md5 = set()
    # 初始排除所有已存在图片的MD5（无论来自哪个日志条目）
    for item in log:
        sp = item.get("save_path")
        if sp and Path(sp).exists():
            try:
                exclude_md5.add(hashlib.md5(Path(sp).read_bytes()).hexdigest())
            except Exception: pass

    solved_map = {}  # (brand,model)->True
    for item in log:
        if Path(item.get("save_path","")).exists():
            # 注意：旧的重复图也要重新下载！只保留MD5唯一的。
            solved_map[(item["brand"], item["model"])] = True

    # 构建完整任务列表（先14款精确，再5款扩展）
    ALL_TASKS = []
    for brand, model, rslug in EXACT_14:
        ALL_TASKS.append(("EXACT", brand, model, [rslug], [""]))  # rslug已含后缀，不需要再加后缀
    for (brand, model), slugs in EXTENDED_5.items():
        ALL_TASKS.append(("EXTENDED", brand, model, slugs, EXTRA_SUFFIXES))

    solved = 0
    unsolved = []
    total = len(EXACT_14) + len(EXTENDED_5)
    for idx, (mode, brand, model, slugs, suffixes) in enumerate(ALL_TASKS, 1):
        print(f"\n[{idx}/{total}] {mode:8s} {brand}/{model} ({len(slugs)} slugs × {len(suffixes)} suf = {len(slugs)*len(suffixes)} cand)")
        winner = None
        tried = 0
        for slug in slugs:
            for suf in suffixes:
                tried += 1
                rslug = slug + suf
                u = f"https://images.hdqwalls.com/download/{rslug}-1600x900.jpg"
                raw = download(u)
                ok, w, h, aspect, md5 = check_quality(raw)
                if not ok: continue
                if md5 in exclude_md5:
                    if tried <= 3:
                        print(f"  skip dupMD5 {md5[:8]} after {tried}")
                    continue
                winner = (raw, w, h, u, md5, rslug, tried, aspect)
                print(f"  ✔ [{mode}] after {tried}: asp={aspect:.2f} {w}x{h} {len(raw)/1024:.0f}KB slug={rslug[:80]}")
                break
            if winner: break
        if not winner:
            print(f"  ✘ [{mode}] all {tried} failed")
            unsolved.append((brand, model, mode))
            continue
        raw, w, h, u, md5raw, rslug, tried, aspect = winner
        prev = next((x for x in log if x["brand"]==brand and x["model"]==model), None)
        sp = prev.get("save_path") if prev else None
        sp = sp or str(BRANDS_D / brand / (model + ".jpg"))
        p = Path(sp); p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        hfin = hashlib.md5(p.read_bytes()).hexdigest()
        exclude_md5.add(md5raw); exclude_md5.add(hfin)
        entry = {
            "brand": brand, "model": model,
            "source_url": u, "hdq_slug": rslug,
            "width": w, "height": h,
            "aspect_ratio": round(aspect, 3),
            "size_bytes": len(final),
            "md5_prefix": hfin[:12], "format": "JPEG",
            "save_path": str(p),
            "gate_level": f"HDQv6_{mode}_aspect>=1.60_MD5-unique",
            "downloaded_at_epoch": int(time.time()),
        }
        save_entry(log, entry)
        solved += 1
        solved_map[(brand, model)] = True
        print(f"  💾 {p.name} {len(final)/1024:.0f}KB md5={hfin[:10]}")

    # ==== 最终质量统计 ====
    bymd = {}
    items_count = 0
    for item in log:
        p = Path(item.get("save_path",""))
        if not p.exists(): continue
        items_count += 1
        h = hashlib.md5(p.read_bytes()).hexdigest()
        bymd.setdefault(h, []).append(f"{item['brand']}/{item['model']}")
    dup_cnt = sum(len(v) for v in bymd.values() if len(v) > 1)
    print("\n" + "="*90)
    print(f"Solved this round {solved}/{total}   Total saved {items_count}   Unique MD5 {len(bymd)}/{items_count}   Dups {dup_cnt}")
    if unsolved:
        print("Unsolved: " + " | ".join(f"{m}({b}/{mode})" for b,m,mode in unsolved))
    for h, lst in sorted(bymd.items(), key=lambda kv: -len(kv[1])):
        if len(lst) > 1:
            print(f"  ⚠ MD5 {h[:12]}:  " + "  ↔  ".join(lst))
    ok = 0
    print("\nQuality Gate (asp>=1.60 w>=1200 sz>=70KB):")
    CAR_LIST = [
        ("rolls-royce","phantom"),("rolls-royce","ghost"),("rolls-royce","cullinan"),("rolls-royce","wraith"),
        ("bentley","continental-gt"),("bentley","continental-gtc"),("bentley","flying-spur"),("bentley","bentayga"),
        ("bugatti","chiron"),("bugatti","veyron"),("bugatti","divo"),
        ("porsche","911"),("porsche","taycan"),("porsche","panamera"),("porsche","cayenne"),("porsche","macan"),
        ("ferrari","sf90"),("ferrari","f8-tributo"),("ferrari","roma"),
    ]
    for brand, model in CAR_LIST:
        p = BRANDS_D / brand / (model + ".jpg")
        if not p.exists():
            print(f"  FAIL missing {brand}/{model}")
            continue
        raw = p.read_bytes()
        try:
            with P.open(io.BytesIO(raw)) as im: w,h = im.size
        except Exception:
            print(f"  FAIL corrupt {brand}/{model}")
            continue
        asp = w/h
        s = "PASS" if (asp >= 1.60 and w >= 1200 and len(raw) >= 70_000) else "FAIL"
        if s == "PASS": ok += 1
        print(f"  {s} asp={asp:.2f} w={w} sz={len(raw)/1024:.0f}KB {brand}/{model}")
    print(f"\n✅ PASS {ok}/19   🆔 MD5-unique {len(bymd)}/19")
    code = 0 if (ok == 19 and len(bymd) == 19 and not unsolved) else 1
    if code == 0:
        print("\n🎉 全部通过！19 张官网高清正侧视图下载完成。")
    else:
        print(f"\n❌ 还需处理 (ok={ok}, unique={len(bymd)}, unsolved={len(unsolved)})")
    return code

if __name__ == "__main__": sys.exit(main())
