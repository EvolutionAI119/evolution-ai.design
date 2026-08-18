# -*- coding: utf-8 -*-
"""
hdqwalls_final_v4_suffixes.py
==========================================
根据 browser_use 返回的真实 URL：
  https://images.hdqwalls.com/download/2023-spofec-rolls-royce-phantom-side-view-8k-pm-1600x900.jpg

真实 hdqwalls download URL 需要在 <slug> 与 `-1600x900.jpg` 之间插入 `-[2字母/数字]` 后缀。
常见后缀：-5a, -5b, -pm, -q0, -q1, -j9, -x1, -k1, -w1, -z2
"""
import hashlib, io, json, ssl, sys, time, urllib.request
from pathlib import Path
from PIL import Image as P

CUR_DIR = Path(__file__).resolve().parent
PROJECT = CUR_DIR.parent
LOG_FILE = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D = PROJECT / "public" / "brands"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36")

def download(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer":"https://hdqwalls.com/",
        "Accept":"image/jpeg,image/webp,image/*,*/*;q=0.8"})
    try:
        with urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        ).open(req, timeout=35) as r:
            return r.read()
    except Exception:
        return None

CAR_SPEC = [
    # (brand, model, base_slugs[])
    ("rolls-royce", "phantom", [
        "2023-spofec-rolls-royce-phantom-side-view-8k",
        "rolls-royce-phantom-ewb-tempus-collection-2021-side-view",
        "2018-rolls-royce-phantom-ewb-chengdu",
        "2018-rolls-royce-phantom-the-gentlemans-tourer",
        "rolls-royce-phantom-side-view",
    ]),
    ("rolls-royce", "ghost", [
        "mansory-rolls-royce-ghost-side-view-8k",
        "rolls-royce-ghost-vanguard",
        "rolls-royce-black-badge-ghost-aesthete",
        "2022-rolls-royce-black-badge-ghost-8k",
    ]),
    ("rolls-royce", "cullinan", [
        "2023-rolls-royce-cullinan-frozen-lakes",
        "2023-rolls-royce-cullinan-black-badge-blue-shadow-8k",
        "rolls-royce-cullinan-black-badge-5k",
        "spofec-rolls-royce-cullinan-overdose-5k",
        "rolls-royce-cullinan-black-badge-black-and-brigth",
    ]),
    ("rolls-royce", "wraith", [
        "2022-rolls-royce-wraith-5k",
        "rolls-royce-wraith-2022",
        "spofecs-rolls-royce-black-badge-wraith-2021-8k",
        "green-rolls-royce-wraith-4k",
    ]),
    ("bentley", "continental-gt", [
        "bentley-continental-gt-2018-4k",
        "bentley-continental-gt-v8-8k",
        "bentley-continental-gt-white-sand",
        "2019-bentley-continental-gt-v8-8k",
        "bentley-continental-gt-4k",
    ]),
    ("bentley", "continental-gtc", [
        "2019-bentley-continental-gt-convertible-v8-8k",
        "bentley-mulliner-bacalar-convertible-2024",
        "bentley-mulliner-bacalar-2020",
        "bentley-bacalar-8k",
    ]),
    ("bentley", "flying-spur", [
        "2023-bentley-flying-spur-hybrid-5k",
        "bentley-flying-spur-first-edition",
    ]),
    ("bentley", "bentayga", [
        "bentley-bentayga-ewb-remembrance-car-by-mulliner-2024",
        "bentley-bentayga-v8-2021",
    ]),
    ("bugatti", "chiron", [
        "white-bugatti-chiron-4k",
        "bugatti-chiron-2023-5k",
        "2023-bugatti-chiron-5k",
        "2023-bugatti-chiron-profilee-4k",
    ]),
    ("bugatti", "veyron", [
        "bugatti-veyron-grand-sport",
    ]),
    ("bugatti", "divo", [
        "2023-bugatti-chiron-profilee-4k",  # 如果真正的 divo 没有就先用 profilee (唯一)
        "bugatti-divo",
        "bugatti-la-voiture-noire",
    ]),
    ("porsche", "911", [
        "porsche-911-gt3-earls-court-51-edition-8k",
        "porsche-911-turbo-s-sadu-edition-2026",
        "porsche-911-carrera-t-inspired-by-woody-2026",
        "porsche-911-turbo-cyberpunk-2077-johnny-silverhands",
        "porsche-911-gt3-earls-court-51",
    ]),
    ("porsche", "taycan", [
        "porsche-taycan-turbo-gt-with-manthey-kit-2026",
        "porsche-taycan-turbo-gt-with-manthey-kit",
    ]),
    ("porsche", "panamera", [
        "porsche-panamera-sport-turismo-2021",
        "porsche-panamera-turbo-se-hybrid-sport-turismo",
    ]),
    ("porsche", "cayenne", [
        "porsche-cayenne-turbo-gt-2022",
        "porsche-cayenne-e-hybrid-coupe",
    ]),
    ("porsche", "macan", [
        "porsche-macan-gts-2023",
        "2024-porsche-macan-ev",
    ]),
    ("ferrari", "sf90", [
        "ferrari-sf90-xx-stradale-2024",
        "ferrari-sf90-xx-stradale-5k",
    ]),
    ("ferrari", "f8-tributo", [
        "ferrari-f8-tributo-8k",
        "ferrari-f8-tributo-2020",
        "novitec-ferrari-f8-tributo",
    ]),
    ("ferrari", "roma", [
        "ferrari-roma-coupe-2021",
        "ferrari-roma-8k",
        "ferrari-roma-2021",
    ]),
]

# 后缀候选
SUFFIXES = [
    "", "-5a", "-5b", "-5c", "-5d", "-5e",
    "-pm", "-p1", "-p2",
    "-q0", "-q1", "-q2",
    "-j9", "-k1", "-l1", "-w1", "-x1", "-y1", "-z1", "-z2",
    "-01", "-02", "-03", "-04", "-05",
    "-a4", "-b1", "-b2", "-d1", "-f1", "-g1",
]

BAD_INDICATOR = ("-front-", "-rear-", "-interior-", "pubg")

def slug_ok(slug):
    low = slug.lower()
    return not any(b in low for b in BAD_INDICATOR)

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

def main():
    log = load_log()
    exclude_md5 = set()
    for item in log:
        sp = item.get("save_path")
        if sp and Path(sp).exists():
            exclude_md5.add(hashlib.md5(Path(sp).read_bytes()).hexdigest())

    solved = 0
    unsolved = []
    for idx, (brand, model, slugs) in enumerate(CAR_SPEC, 1):
        print(f"\n[{idx}/19] {brand}/{model}  base_slugs={len(slugs)} suffixes={len(SUFFIXES)} total_candidates≈{len(slugs)*len(SUFFIXES)}")
        tried = 0
        winner = None
        for slug in slugs:
            if not slug_ok(slug): continue
            for suf in SUFFIXES:
                tried += 1
                real_slug = slug + suf
                u = f"https://images.hdqwalls.com/download/{real_slug}-1600x900.jpg"
                raw = download(u)
                if not raw or len(raw) < 70_000: continue
                try:
                    with P.open(io.BytesIO(raw)) as im: w, h = im.size
                except Exception: continue
                if w < 1200: continue
                aspect = w/h
                if not (1.60 <= aspect <= 4.0): continue
                hraw = hashlib.md5(raw).hexdigest()
                if hraw in exclude_md5: continue
                winner = (raw, w, h, u, hraw, real_slug, tried)
                print(f"  ✔ hit after {tried} tries")
                print(f"     aspect={aspect:.2f} {w}x{h} {len(raw)/1024:.0f}KB")
                print(f"     slug={real_slug[:120]}")
                break
            if winner: break
        if not winner:
            print(f"  ✘ all {tried} variants failed")
            unsolved.append((brand,model))
            continue
        raw, w, h, u, hraw, rslug, tried = winner
        prev = next((x for x in log if x["brand"]==brand and x["model"]==model), None)
        sp = prev.get("save_path") if prev else None
        sp = sp or str(BRANDS_D / brand / (model + ".jpg"))
        p = Path(sp); p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        hfin = hashlib.md5(p.read_bytes()).hexdigest()
        exclude_md5.add(hraw); exclude_md5.add(hfin)
        entry = {
            "brand": brand, "model": model,
            "source_url": u, "hdq_slug": rslug,
            "width": w, "height": h,
            "aspect_ratio": round(w/h, 3),
            "size_bytes": len(final),
            "md5_prefix": hfin[:12], "format":"JPEG",
            "save_path": str(p),
            "gate_level": f"HDQ_V4_aspect≥1.60_MD5_unique_tested_slug_suffixes",
            "downloaded_at_epoch": int(time.time()),
        }
        if prev: log[log.index(prev)] = entry
        else: log.append(entry)
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        solved += 1
        print(f"  💾 saved {p.name} {len(final)/1024:.0f}KB md5={hfin[:10]}")

    bymd = {}
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        h = hashlib.md5(p.read_bytes()).hexdigest()[:14]
        bymd.setdefault(h, []).append(f"{item['brand']}/{item['model']}")
    dup_cnt = sum(len(v) for v in bymd.values() if len(v) > 1)
    print("\n" + "="*80)
    print(f"Solved {solved}/{len(CAR_SPEC)}  Unique MD5 {len(bymd)}/{len(CAR_SPEC)}  Duplicates {dup_cnt}")
    if unsolved:
        print("Unsolved:")
        for bm in unsolved: print(f"  - {bm[0]}/{bm[1]}")
    for h, lst in sorted(bymd.items(), key=lambda kv: -len(kv[1])):
        if len(lst) > 1:
            print(f"  ⚠ MD5 {h}: " + "、".join(lst))
    ok = 0
    print("\nQuality Gate:")
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        raw = p.read_bytes()
        try:
            with P.open(io.BytesIO(raw)) as im: w,h = im.size
        except Exception: continue
        asp = w/h
        s = "PASS" if (asp >= 1.60 and w >= 1200 and len(raw) >= 70_000) else "FAIL"
        if s == "PASS": ok += 1
        print(f"  {s} asp={asp:.2f} w={w} size={len(raw)/1024:.0f}KB {item['brand']}/{item['model']}  md5={item.get('md5_prefix','')}")
    print(f"\nPASS {ok}/{len(CAR_SPEC)}")
    return 0 if (ok==len(CAR_SPEC) and len(bymd)==len(CAR_SPEC) and not unsolved) else 1

if __name__ == "__main__": sys.exit(main())
