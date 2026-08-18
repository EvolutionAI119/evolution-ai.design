# -*- coding: utf-8 -*-
"""
hdqwalls_final_download_19cars.py
===================================
方案：
    images.hdqwalls.com 从本地 Python 可直接访问（无 SSL 超时）。
    hdqwalls 上几乎每个车型壁纸的 slug 都有规律。

    步骤：
      1. 我们手工枚举每个车型的 10~40 个可能 slug（按 hdqwalls 命名
         习惯：常见前缀 mansory-、spofec-、2021-...、修饰词-品牌-车型），
         再将 "side" / "profile" / "full-side" 等词加入候选 slug 中。
      2. 逐个访问 images.hdqwalls.com/download/<slug>-1600x900.jpg
         如果返回 jpeg 200 成功 & 尺寸合格(aspect 1.60~3.5, 宽≥1200, ≥70KB)，
         就采用，且 MD5 去重。
      3. 找不到的车型，在最后输出“需手工补漏的车型名清单”
"""
from __future__ import annotations
import os, sys, io, json, time, hashlib, urllib.request, ssl
from pathlib import Path
from typing import Optional

CUR_DIR   = Path(__file__).resolve().parent
PROJECT   = CUR_DIR.parent
LOG_FILE  = CUR_DIR / "_car_photos_download_log.json"
BRANDS_D  = PROJECT / "public" / "brands"

MIN_ASPECT   = 1.60
MAX_ASPECT   = 4.0
MIN_WIDTH_PX = 1200
MIN_FILE_B   = 70_000
REQ_TIMEOUT  = 30

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# ============================================================
# 19 款车型候选 slugs （每个给 10-40 个候选，按 hdqwalls 已有命名习惯）
# ============================================================
CAR_SPEC = [
    # (brand, model, slug_candidates)
    ("rolls-royce", "phantom", [
        "2023-spofec-rolls-royce-phantom-side-view-8k",
        "rolls-royce-phantom-ewb-tempus-collection-2021-side-view",
        "2018-rolls-royce-phantom-the-gentlemans-tourer",
        "rolls-royce-phantom-ewb-tempus-collection-2021-side",
        "rolls-royce-phantom-side-view-8k",
        "rolls-royce-phantom-side-profile",
        "2024-rolls-royce-phantom-viii",
        "spofec-rolls-royce-phantom-2023",
        "rolls-royce-phantom-ewb-2017",
        "satin-of-light-rolls-royce-phantom-viii",
        "rolls-royce-phantom-viii-2024",
        "rolls-royce-phantom-side-5a",
        "rolls-royce-phantom-full-side",
        "rolls-royce-phantom-mansory",
    ]),
    ("rolls-royce", "ghost", [
        "mansory-rolls-royce-ghost-side-view-8k-5a",
        "rolls-royce-ghost-mansory-side",
        "2021-rolls-royce-ghost",
        "rolls-royce-black-badge-ghost-2021",
        "rolls-royce-ghost-5k",
        "mansory-rolls-royce-ghost-2021-8k",
        "2021-mansory-rolls-royce-ghost-8k",
        "rolls-royce-ghost-zenith-collection-2019",
        "rolls-royce-ghost-side-view-8k",
        "rolls-royce-ghost-side-profile-5k",
    ]),
    ("rolls-royce", "cullinan", [
        "mansory-rolls-royce-cullinan-side",
        "rolls-royce-cullinan-side-view-8k",
        "rolls-royce-cullinan-black-badge",
        "spofec-rolls-royce-cullinan-overdose",
        "urban-automotive-rolls-royce-cullinan",
        "2025-mansory-rolls-royce-cullinan",
        "mansory-rolls-royce-cullinan-8k-2025",
        "white-rolls-royce-cullinan-8k-2020",
        "2019-rolls-royce-cullinan-4k",
        "rolls-royce-cullinan-vossen-wheels",
    ]),
    ("rolls-royce", "wraith", [
        "rolls-royce-wraith-side-view-8k",
        "ares-design-rolls-royce-wraith-front",
        "2019-rolls-royce-wraith-black-and-bright-8k",
        "rolls-royce-wraith-black-badge",
        "rolls-royce-wraith-mansory",
        "rolls-royce-wraith-coupe-side",
        "rolls-royce-wraith-side-profile",
    ]),
    # Bentley
    ("bentley", "continental-gt", [
        "bentley-continental-gt-side-view",
        "2022-bentley-continental-gt-speed",
        "mansory-bentley-continental-gt",
        "bentley-continental-gt-mulliner-8k",
        "bentley-continental-gt-side-profile",
        "2021-bentley-continental-gt-5k",
        "bentley-continental-gt-coupe-side-view",
    ]),
    ("bentley", "continental-gtc", [
        "bentley-continental-gtc-side-view",
        "bentley-continental-gtc-convertible",
        "mansory-bentley-continental-gtc",
        "2022-bentley-continental-gtc-8k",
        "bentley-continental-gtc-side-profile",
    ]),
    ("bentley", "flying-spur", [
        "bentley-flying-spur-side-view",
        "mansory-bentley-flying-spur",
        "2023-bentley-flying-spur-mulliner",
        "bentley-flying-spur-side-profile",
        "2021-bentley-flying-spur-8k",
        "bentley-flying-spur-mansory-side",
    ]),
    ("bentley", "bentayga", [
        "bentley-bentayga-side-view",
        "mansory-bentley-bentayga",
        "2022-bentley-bentayga-suv-8k",
        "bentley-bentayga-side-profile",
        "bentley-bentayga-speed",
    ]),
    # Bugatti
    ("bugatti", "chiron", [
        "bugatti-chiron-side-view",
        "bugatti-chiron-pur-sport-side",
        "2020-bugatti-chiron-super-sport-300plus",
        "mansory-bugatti-chiron",
        "bugatti-chiron-side-profile-8k",
        "bugatti-chiron-sport-5k",
        "bugatti-chiron-full-side",
    ]),
    ("bugatti", "veyron", [
        "bugatti-veyron-side-view",
        "bugatti-veyron-16.4-super-sport",
        "bugatti-veyron-grand-sport",
        "bugatti-veyron-side-profile",
        "bugatti-veyron-side-8k",
    ]),
    ("bugatti", "divo", [
        "bugatti-divo-side-view",
        "2019-bugatti-divo",
        "bugatti-divo-side-profile-8k",
        "bugatti-divo-side",
        "bugatti-divo-5k",
    ]),
    # Porsche
    ("porsche", "911", [
        "porsche-911-carrera-side-view",
        "porsche-911-turbo-s-side",
        "2022-porsche-911-gt3-side",
        "mansory-porsche-911-side",
        "porsche-911-carrera-s-992-side",
        "porsche-911-gt3-rs",
        "porsche-911-side-profile",
    ]),
    ("porsche", "taycan", [
        "porsche-taycan-side-view",
        "porsche-taycan-turbo-s-side",
        "2022-porsche-taycan-gts",
        "mansory-porsche-taycan",
        "porsche-taycan-side-profile-5k",
    ]),
    ("porsche", "panamera", [
        "porsche-panamera-side-view",
        "porsche-panamera-turbo-s-e-hybrid",
        "mansory-porsche-panamera",
        "2021-porsche-panamera-sport-turismo",
        "porsche-panamera-side-profile",
        "porsche-panamera-side",
    ]),
    ("porsche", "cayenne", [
        "porsche-cayenne-side-view",
        "mansory-porsche-cayenne",
        "2022-porsche-cayenne-turbo-gt",
        "porsche-cayenne-side-profile-8k",
        "porsche-cayenne-coupe-side",
    ]),
    ("porsche", "macan", [
        "porsche-macan-side-view",
        "porsche-macan-turbo-side",
        "2024-porsche-macan-ev",
        "mansory-porsche-macan",
        "porsche-macan-side-profile-5k",
    ]),
    # Ferrari
    ("ferrari", "sf90", [
        "ferrari-sf90-stradale-side-view",
        "ferrari-sf90-stradale-side-profile",
        "mansory-ferrari-sf90-stradale",
        "ferrari-sf90-spider-side",
        "2021-ferrari-sf90-stradale-5k",
        "ferrari-sf90-full-side",
    ]),
    ("ferrari", "f8-tributo", [
        "ferrari-f8-tributo-side-view",
        "ferrari-f8-tributo-side-profile",
        "mansory-ferrari-f8-tributo",
        "2020-ferrari-f8-tributo",
        "ferrari-f8-spider-side",
        "ferrari-f8-tributo-side",
    ]),
    ("ferrari", "roma", [
        "ferrari-roma-side-view",
        "ferrari-roma-side-profile",
        "mansory-ferrari-roma",
        "2021-ferrari-roma",
        "ferrari-roma-coupe-side",
    ]),
]


def http_get_binary(url: str) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://hdqwalls.com/",
        "Accept": "image/webp,image/jpeg,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.7",
    })
    ctx = ssl._create_unverified_context()
    try:
        op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        with op.open(req, timeout=REQ_TIMEOUT) as r:
            return r.read()
    except Exception:
        return None


def dims_of(data: bytes):
    try:
        from PIL import Image as P
        with P.open(io.BytesIO(data)) as im: return im.size
    except Exception:
        return None


def md5h(b: bytes) -> str: return hashlib.md5(b).hexdigest()


def write_jpg(path: Path, raw: bytes) -> bytes:
    try:
        from PIL import Image as P
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=93, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw


def load_log():
    if LOG_FILE.exists():
        try:
            d = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            if isinstance(d, list): return d
        except Exception: pass
    return []


def main():
    log = load_log()
    # 初始化 MD5 排除池（从已有图片文件读）
    exclude_md5 = set()
    for item in log:
        sp = item.get("save_path")
        if sp and Path(sp).exists():
            exclude_md5.add(md5h(Path(sp).read_bytes()))
    print(f"Initial MD5 exclusion pool: {len(exclude_md5)}")

    unsolved = []
    successes = 0
    for idx, (brand, model, slug_cands) in enumerate(CAR_SPEC, 1):
        print(f"\n[{idx}/19] 🎯 {brand}/{model}  ({len(slug_cands)} slug 候选)")
        # 为避免"同一车型重复下载同一图"，对已成功的 log 记录先跳过
        prev_entry = next((x for x in log if x["brand"]==brand and x["model"]==model), None)
        if prev_entry and Path(prev_entry["save_path"]).exists():
            # 仍允许覆盖，不跳
            pass
        winner = None
        tried = 0
        for slug in slug_cands:
            tried += 1
            u = f"https://images.hdqwalls.com/download/{slug}-1600x900.jpg"
            raw = http_get_binary(u)
            if not raw or len(raw) < MIN_FILE_B:
                continue
            dims = dims_of(raw)
            if not dims: continue
            w, h = dims
            if w < MIN_WIDTH_PX or h <= 0: continue
            aspect = w / h
            if not (MIN_ASPECT <= aspect <= MAX_ASPECT):
                continue
            hraw = md5h(raw)
            if hraw in exclude_md5:
                print(f"    🗑 duplicate MD5 {hraw[:10]} for slug={slug[:60]}")
                continue
            winner = (raw, w, h, u, hraw, slug, tried)
            print(f"    ✔ #{tried} aspect={aspect:.2f} {w}x{h} {(len(raw)/1024):.0f}KB\n       slug={slug[:90]}\n       URL: {u[:140]}")
            break
        if not winner:
            print(f"    ✘ 所有 {len(slug_cands)} 个候选全部失败（404/尺寸不够/重复）。需手工补漏。")
            unsolved.append((brand,model))
            continue
        raw, w, h, u, hraw, slug, tried = winner
        # 记录 / 保存
        sp = (prev_entry or {}).get("save_path") or str(BRANDS_D / brand / (model + ".jpg"))
        p = Path(sp); p.parent.mkdir(parents=True, exist_ok=True)
        final_bytes = write_jpg(p, raw)
        p.write_bytes(final_bytes)
        hfin = md5h(p.read_bytes())
        exclude_md5.add(hraw); exclude_md5.add(hfin)
        entry = {
            "brand": brand, "model": model,
            "source_url": u,
            "hdq_slug": slug,
            "width": w, "height": h,
            "aspect_ratio": round(w/h, 3),
            "size_bytes": len(final_bytes),
            "md5_prefix": hfin[:12],
            "format": "JPEG",
            "save_path": str(p),
            "gate_level": f"HDQv2_MIN_ASPECT=1.60_MIN_W=1200",
            "downloaded_at_epoch": int(time.time()),
        }
        if prev_entry:
            log[log.index(prev_entry)] = entry
        else:
            log.append(entry)
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        successes += 1
        print(f"    💾 saved {p.name} {(len(final_bytes)/1024):.0f}KB aspect={w/h:.2f} MD5 {hfin[:10]}")

    # MD5 唯一性总览
    by_md5 = {}
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        h = md5h(p.read_bytes())[:14]
        by_md5.setdefault(h, []).append(f"{item['brand']}/{item['model']}")
    dup_count = sum(len(v) for v in by_md5.values() if len(v) > 1)
    print("\n" + "=" * 80)
    print(f"✔ 本回合成功下载 {successes}/{len(CAR_SPEC)} 台")
    print(f"✔ 最终唯一 MD5 {len(by_md5)}/{len(CAR_SPEC)}； 重复MD5涉及 {dup_count} 台")
    if unsolved:
        print(f"⚠ 需手工补漏（{len(unsolved)} 台）：")
        for b,m in unsolved: print(f"    - {b}/{m}")
    for h, lst in sorted(by_md5.items(), key=lambda kv: -len(kv[1])):
        if len(lst) > 1:
            print(f"  ⚠ MD5 {h}: " + "、".join(lst))
    # 打印每台详细质量
    print("\n质量总览（aspect≥1.60 才合格）:")
    ok = 0
    for item in log:
        p = Path(item["save_path"])
        if not p.exists(): continue
        dims = dims_of(p.read_bytes())
        if dims is None: continue
        w,h = dims
        asp = w/h
        pasp = "✔" if asp >= 1.60 else "✗"
        pw = "✔" if w >= 1200 else "✗"
        psize = "✔" if len(p.read_bytes()) >= MIN_FILE_B else "✗"
        status = "PASS" if (asp>=1.60 and w>=1200 and len(p.read_bytes())>=MIN_FILE_B) else "FAIL"
        print(f"  {pasp}aspect={asp:.2f}  {pw}w={w}  {psize}size={len(p.read_bytes())/1024:.0f}KB  [{status}] {item['brand']}/{item['model']}  md5={item.get('md5_prefix','')}")
        if status == "PASS": ok += 1
    print(f"\n质量合格 PASS {ok}/{len(CAR_SPEC)}")
    return 0 if (ok==len(CAR_SPEC) and len(by_md5)==len(CAR_SPEC) and not unsolved) else 1

if __name__ == "__main__":
    sys.exit(main())
