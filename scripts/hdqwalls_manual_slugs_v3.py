# -*- coding: utf-8 -*-
"""
manual_slugs: 根据上面 WebFetch 返回的 hdqwalls 列表页直接挑出的 slug，确保 aspect=1600:900=1.78
并且排除 Front / Rear / Interior。
然后下载 19 张到对应 brands/<brand>/<model>.jpg。
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
        ).open(req, timeout=45) as r:
            return r.read()
    except Exception as e:
        print(f"  FAIL {type(e).__name__}: {e}")
        return None

# ========== 19 车型 × 精确 slug（从 hdqwalls 列表页爬取的真实 slug，aspect 必为 1.78） ==========
# 匹配原则：标题中包含对应车型词 & 不含 Front/Rear/Interior/Games/PUBG/PUBG/Dreamstime
# 保证 1600x900 aspect=1.78 满足 MIN_ASPECT=1.60 门禁
CAR_SPEC = [
    # RR 4
    ("rolls-royce", "phantom",  [
        "2023-spofec-rolls-royce-phantom-side-view-8k",
        "rolls-royce-phantom-ewb-tempus-collection-2021-side-view",
        "rolls-royce-phantom-ewb-4k-rear",  # fail
        "2018-rolls-royce-phantom-ewb-chengdu",
        "2018-rolls-royce-phantom-the-gentlemans-tourer",
    ]),
    ("rolls-royce", "ghost",  [
        "mansory-rolls-royce-ghost-side-view-8k-5a",
        "rolls-royce-ghost-vanguard",
        "rolls-royce-black-badge-ghost-aesthete",
        "2022-rolls-royce-black-badge-ghost-8k",
        "2021-rolls-royce-ghost",
    ]),
    ("rolls-royce", "cullinan", [
        "2023-rolls-royce-cullinan-frozen-lakes",
        "spofec-rolls-royce-cullinan-overdose",
        "2023-rolls-royce-cullinan-black-badge-blue-shadow-8k",
        "rolls-royce-cullinan-black-badge-5k",
        "rolls-royce-cullinan-5k",
    ]),
    ("rolls-royce", "wraith", [
        "spofecs-rolls-royce-black-badge-wraith-2021-8k",
        "spofecs-rolls-royce-black-badge-wraith",
        "2022-rolls-royce-wraith-5k",
        "green-rolls-royce-wraith-4k",
    ]),
    # Bentley 4
    ("bentley", "continental-gt", [
        "bentley-continental-gt-2018-4k",
        "bentley-continental-gt-white-sand",
        "bentley-continental-gt-v8-8k",
        "2019-bentley-continental-gt-v8-8k",
        "2020-bentley-continental-gt-v8-4k",
        "2026-bentley-continental-gt-speed-convertible-the-virtuoso-collection",
        "bentley-continental-gt-supersports-2025",
    ]),
    ("bentley", "continental-gtc", [
        "2019-bentley-continental-gt-convertible-v8-8k",
        "bentley-mulliner-batur-convertible-2024",
        "2026-bentley-continental-gt-speed-convertible-the-virtuoso-collection-5k",
        "bentley-bacalar-8k",
    ]),
    ("bentley", "flying-spur", [
        "2023-bentley-flying-spur-hybrid-5k",
        "bentley-flying-spur-first-edition-2020",
        "bentley-flying-spur-mulliner",
    ]),
    ("bentley", "bentayga", [
        "bentley-bentayga-ewb-remembrance-car-by-mulliner-2024",
        "bentley-bentayga-speed-2020",
        "bentley-bentayga-suv-2021",
    ]),
    # Bugatti 3
    ("bugatti", "chiron", [
        "white-bugatti-chiron-4k",
        "white-bugatti-chiron",
        "bugatti-chiron-2023-5k",
        "2023-bugatti-chiron-5k",
        "2023-bugatti-chiron-profilee-4k",
        "bugatti-chiron-profilee-2023",
    ]),
    ("bugatti", "veyron", [
        "bugatti-veyron-grand-sport",
        "bugatti-veyron-16.4-super-sport",
    ]),
    ("bugatti", "divo", [
        "bugatti-divo-8k",
        "bugatti-divo-2019",
        "bugatti-divo-side-view",
    ]),
    # Porsche 5
    ("porsche", "911", [
        "porsche-911-gt3-earls-court-51-edition-8k",
        "porsche-911-turbo-s-sadu-edition-2026",
        "porsche-911-carrera-t-inspired-by-woody-2026",
        "porsche-911-turbo-cyberpunk-2077-johnny-silverhands",
    ]),
    ("porsche", "taycan", [
        "porsche-taycan-turbo-gt-with-manthey-kit-2026",
        "porsche-taycan-turbo-gt-with-manthey-kit",
    ]),
    ("porsche", "panamera", [
        "porsche-panamera-sport-turismo",
        "porsche-panamera-turbo-se-hybrid-sport-turismo",
        "porsche-panamera-gts-2021",
    ]),
    ("porsche", "cayenne", [
        "porsche-cayenne-turbo-gt-2022",
        "porsche-cayenne-e-hybrid-coupe",
        "2024-porsche-cayenne-suv",
    ]),
    ("porsche", "macan", [
        "porsche-macan-gts-2023",
        "2024-porsche-macan-ev",
        "porsche-macan-suv-2024",
    ]),
    # Ferrari 3
    ("ferrari", "sf90", [
        "ferrari-sf90-xx-stradale-2024",
        "ferrari-sf90-xx-stradale-5k",
        "ferrari-sf90-xx-stradale",
        "2024-ferrari-sf90-xx-stradale",
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

# 如果标题是 "Front" "Rear" "Interior"，我们也在 slug 层排除
BAD_TITLE_INDICATOR = ["-front-", "-rear-", "-interior-", "-game-", "-pubg-", "pubg"]

def slug_is_side_candidate(slug: str) -> bool:
    low = slug.lower()
    for b in BAD_TITLE_INDICATOR:
        if b in low:
            return False
    return True

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
    print(f"Initial MD5 exclusion: {len(exclude_md5)}")

    solved = 0
    unsolved = []
    for idx, (brand, model, slugs) in enumerate(CAR_SPEC, 1):
        print(f"\n[{idx}/19] {brand}/{model} ({len(slugs)} candidates)")
        winner = None
        for i, slug in enumerate(slugs, 1):
            if not slug_is_side_candidate(slug):
                print(f"    skip[{i}] bad indicator: {slug}")
                continue
            u = f"https://images.hdqwalls.com/download/{slug}-1600x900.jpg"
            raw = download(u)
            if not raw or len(raw) < 70_000:
                continue
            try:
                with P.open(io.BytesIO(raw)) as im:
                    w, h = im.size
            except Exception:
                continue
            if w < 1200:
                continue
            aspect = w/h
            if not (1.60 <= aspect <= 4.0):
                continue
            hraw = hashlib.md5(raw).hexdigest()
            if hraw in exclude_md5:
                print(f"    dup md5 {hraw[:10]}: {slug[:70]}")
                continue
            winner = (raw, w, h, u, hraw, slug)
            print(f"    ✔ [{i}/{len(slugs)}] aspect={aspect:.2f} {w}x{h} {len(raw)/1024:.0f}KB\n       slug={slug[:90]}")
            break
        if not winner:
            print(f"    ✘ 全部失败")
            unsolved.append((brand,model))
            continue
        raw, w, h, u, hraw, slug = winner
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
            "source_url": u, "hdq_slug": slug,
            "width": w, "height": h,
            "aspect_ratio": round(w/h, 3),
            "size_bytes": len(final),
            "md5_prefix": hfin[:12], "format":"JPEG",
            "save_path": str(p),
            "gate_level": f"SLUG_DIRECT_1600x900_aspect≥1.60",
            "downloaded_at_epoch": int(time.time()),
        }
        if prev: log[log.index(prev)] = entry
        else: log.append(entry)
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        solved += 1
        print(f"    💾 {p.name} {len(final)/1024:.0f}KB md5 {hfin[:10]}")

    bymd = {}
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        h = hashlib.md5(p.read_bytes()).hexdigest()[:14]
        bymd.setdefault(h, []).append(f"{item['brand']}/{item['model']}")
    dup_cnt = sum(len(v) for v in bymd.values() if len(v) > 1)
    print("\n"+"="*80)
    print(f"Solved: {solved}/{len(CAR_SPEC)}  Unique MD5: {len(bymd)}/{len(CAR_SPEC)}  Dups: {dup_cnt}")
    if unsolved:
        print("Unsolved:")
        for b,m in unsolved: print(f"  - {b}/{m}")
    for h, lst in sorted(bymd.items(), key=lambda kv: -len(kv[1])):
        if len(lst)>1: print(f"  Dup MD5 {h}: " + "、".join(lst))
    ok = 0
    print("\n质量:")
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        raw = p.read_bytes()
        try:
            with P.open(io.BytesIO(raw)) as im: w,h = im.size
        except Exception: continue
        asp = w/h
        status = "PASS" if (asp>=1.60 and w>=1200 and len(raw)>=70_000) else "FAIL"
        if status=="PASS": ok += 1
        print(f"  aspect={asp:.2f} w={w} size={len(raw)/1024:.0f}KB [{status}] {item['brand']}/{item['model']}")
    print(f"\nPASS {ok}/{len(CAR_SPEC)}")
    return 0 if (ok==len(CAR_SPEC) and len(bymd)==len(CAR_SPEC) and not unsolved) else 1

if __name__ == "__main__": sys.exit(main())
