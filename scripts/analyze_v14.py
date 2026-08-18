#!/usr/bin/env python3
"""v14 候选图分析 + 复制最佳到 public/brands/"""
import json, shutil, sys
from pathlib import Path
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
from PIL import Image

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = ROOT / "scripts" / "_candidates_v14"
BRANDS_DIR = ROOT / "public" / "brands"

FAILED = [
    ("rolls-royce","ghost"),("rolls-royce","cullinan"),
    ("bentley","continental-gt"),("bentley","continental-gtc"),
    ("bentley","flying-spur"),("bentley","bentayga"),
    ("bugatti","chiron"),("bugatti","veyron"),("bugatti","divo"),
    ("porsche","taycan"),
    ("ferrari","sf90"),("ferrari","f8-tributo"),
]

def analyze(filepath):
    try:
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        if w < 600 or h < 300: return None
        asp = w / h
        if asp < 1.4 or asp > 2.3: return None
        corners = []
        for (cx, cy) in [(0,0),(w-30,0),(0,h-30),(w-30,h-30)]:
            region = [img.getpixel((x,y)) for x in range(cx,cx+30) for y in range(cy,cy+30)]
            r = sum(p[0] for p in region)//len(region)
            g = sum(p[1] for p in region)//len(region)
            b = sum(p[2] for p in region)//len(region)
            corners.append((r,g,b))
        max_diff = max(max(abs(corners[i][k]-corners[j][k]) for k in range(3)) for i in range(4) for j in range(i+1,4))
        return {"w":w,"h":h,"asp":round(asp,2),"max_diff":max_diff,"bg_pure":max_diff<60}
    except Exception:
        return None

results = []
for brand, model in FAILED:
    car_dir = CAND_DIR / brand / model
    if not car_dir.exists():
        print(f"MISS: {brand}/{model}")
        continue
    print(f"\n### {brand}/{model}")
    cands = []
    for f in sorted(car_dir.glob("cand_*.jpg")):
        a = analyze(f)
        if a:
            a["filename"] = f.name
            a["path"] = str(f)
            cands.append(a)
            if a["bg_pure"]:
                print(f"  PASS {f.name} {a['w']}x{a['h']} asp={a['asp']} diff={a['max_diff']}")

    # 按diff排序
    all_sorted = sorted(cands, key=lambda x: x["max_diff"])
    passed = [c for c in cands if c["bg_pure"]]

    if all_sorted:
        best = all_sorted[0]
        # 复制最佳到 public/brands/
        dst = BRANDS_DIR / brand / f"{model}.jpg"
        shutil.copy2(best["path"], dst)
        print(f"  >>> 复制: {best['filename']} diff={best['max_diff']} -> {dst.name}")
        results.append({"brand":brand,"model":model,"best":best["filename"],"diff":best["max_diff"],"pure":best["bg_pure"]})
    else:
        print(f"  >>> 无候选")
        results.append({"brand":brand,"model":model,"best":None,"diff":None,"pure":False})

print(f"\n{'='*60}")
print(f"统计:")
for r in results:
    pure = "纯净" if r["pure"] else "不纯净"
    print(f"  {r['brand']}/{r['model']}: {r['best']} diff={r['diff']} ({pure})")
