#!/usr/bin/env python3
"""
v13 候选图自动筛选 + 复制最佳候选到 public/
================================================
1. 分析每张候选图的尺寸、宽高比、背景纯净度
2. 筛选出宽高比1.5-2.2 + 背景纯净(diff<60) 的候选
3. 按背景纯净度排序
4. 复制每个车型最可能合格的5张到 public/_best_v13/{brand}/{model}/
"""

import json
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from PIL import Image

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = ROOT / "scripts" / "_candidates_v13"
BEST_DIR = ROOT / "public" / "_best_v13"

CARS = [
    ("rolls-royce", "phantom"), ("rolls-royce", "ghost"),
    ("rolls-royce", "cullinan"), ("rolls-royce", "wraith"),
    ("bentley", "continental-gt"), ("bentley", "continental-gtc"),
    ("bentley", "flying-spur"), ("bentley", "bentayga"),
    ("bugatti", "chiron"), ("bugatti", "veyron"), ("bugatti", "divo"),
    ("porsche", "911"), ("porsche", "taycan"), ("porsche", "panamera"),
    ("porsche", "cayenne"), ("porsche", "macan"),
    ("ferrari", "sf90"), ("ferrari", "f8-tributo"), ("ferrari", "roma"),
]


def analyze_image(filepath):
    try:
        img = Image.open(filepath).convert("RGB")
        w, h = img.size
        if w < 600 or h < 300:
            return None
        asp = w / h
        if asp < 1.4 or asp > 2.3:
            return None

        # 4角 30x30 区域
        corners = []
        for (cx, cy) in [(0, 0), (w - 30, 0), (0, h - 30), (w - 30, h - 30)]:
            region = []
            for x in range(cx, cx + 30):
                for y in range(cy, cy + 30):
                    region.append(img.getpixel((x, y)))
            r = sum(p[0] for p in region) // len(region)
            g = sum(p[1] for p in region) // len(region)
            b = sum(p[2] for p in region) // len(region)
            corners.append((r, g, b))

        max_diff = 0
        for i in range(4):
            for j in range(i + 1, 4):
                diff = max(
                    abs(corners[i][0] - corners[j][0]),
                    abs(corners[i][1] - corners[j][1]),
                    abs(corners[i][2] - corners[j][2]),
                )
                max_diff = max(max_diff, diff)

        return {
            "w": w, "h": h, "asp": round(asp, 2),
            "max_diff": max_diff,
            "bg_pure": max_diff < 60,
        }
    except Exception:
        return None


def main():
    print("=" * 60)
    print("v13 候选图自动筛选")
    print("=" * 60)

    BEST_DIR.mkdir(parents=True, exist_ok=True)
    # 清空旧数据
    if BEST_DIR.exists():
        shutil.rmtree(BEST_DIR)
    BEST_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for brand, model in CARS:
        car_dir = CAND_DIR / brand / model
        if not car_dir.exists():
            continue

        print(f"\n### {brand}/{model}")
        cands = []
        for f in sorted(car_dir.glob("cand_*.jpg")):
            a = analyze_image(f)
            if a:
                a["filename"] = f.name
                a["path"] = str(f)
                cands.append(a)
                status = "PASS" if a["bg_pure"] else "fail"
                print(f"  {f.name}: {status} {a['w']}x{a['h']} asp={a['asp']} diff={a['max_diff']}")

        # 筛选 + 排序
        passed = [c for c in cands if c["bg_pure"]]
        passed.sort(key=lambda x: x["max_diff"])

        # 即使没有通过的，也取前5张（按diff排序）
        all_sorted = sorted(cands, key=lambda x: x["max_diff"])
        top5 = passed[:5] if len(passed) >= 5 else (passed + [c for c in all_sorted if c not in passed])[:5]

        # 复制到 public/_best_v13/
        best_dir = BEST_DIR / brand / model
        best_dir.mkdir(parents=True, exist_ok=True)
        for i, c in enumerate(top5):
            src = Path(c["path"])
            dst = best_dir / f"best_{i+1:02d}_{c['filename']}"
            shutil.copy2(src, dst)

        best_info = top5[0] if top5 else None
        if best_info:
            print(f"  >>> 最佳: {best_info['filename']} diff={best_info['max_diff']}")
        else:
            print(f"  >>> 无合格候选")

        results.append({
            "brand": brand, "model": model,
            "passed": len(passed),
            "best_diff": best_info["max_diff"] if best_info else None,
            "best_file": best_info["filename"] if best_info else None,
            "top5_copied": len(top5),
        })

    # 统计
    total_pass = sum(r["passed"] for r in results)
    print(f"\n{'='*60}")
    print(f"统计:")
    print(f"  背景纯净候选: {total_pass}")
    print(f"  有合格候选的车型: {sum(1 for r in results if r['passed'] > 0)}/19")
    for r in results:
        print(f"  {r['brand']}/{r['model']}: 通过{r['passed']}张, 最佳diff={r['best_diff']}, 复制{r['top5_copied']}张")


if __name__ == "__main__":
    main()
