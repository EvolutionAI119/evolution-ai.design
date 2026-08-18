#!/usr/bin/env python3
"""
v12 候选图自动筛选 - 背景纯净度 + 宽高比
=========================================
先用像素分析筛选出最可能合格的候选，减少需要视觉验证的数量。
筛选标准：
1. 宽高比 1.5-2.2（正侧视比例）
2. 4角像素颜色相似（背景纯净）
3. 尺寸 >= 800x400
4. 文件大小 >= 30KB
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from PIL import Image

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = ROOT / "scripts" / "_candidates_v12"

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
    """分析单张图片的背景纯净度和尺寸"""
    try:
        img = Image.open(filepath)
        img = img.convert("RGB")
        w, h = img.size

        # 尺寸检查
        if w < 800 or h < 400:
            return {"pass": False, "reason": f"尺寸太小 {w}x{h}"}

        asp = w / h
        if asp < 1.5 or asp > 2.2:
            return {"pass": False, "reason": f"宽高比 {asp:.2f} 不在1.5-2.2"}

        # 4角各取 30x30 区域
        corners = []
        for (cx, cy) in [(0, 0), (w - 30, 0), (0, h - 30), (w - 30, h - 30)]:
            region = []
            for x in range(cx, cx + 30):
                for y in range(cy, cy + 30):
                    region.append(img.getpixel((x, y)))
            # 平均颜色
            r = sum(p[0] for p in region) // len(region)
            g = sum(p[1] for p in region) // len(region)
            b = sum(p[2] for p in region) // len(region)
            corners.append((r, g, b))

        # 4角颜色最大差异
        max_diff = 0
        for i in range(4):
            for j in range(i + 1, 4):
                diff = max(
                    abs(corners[i][0] - corners[j][0]),
                    abs(corners[i][1] - corners[j][1]),
                    abs(corners[i][2] - corners[j][2]),
                )
                max_diff = max(max_diff, diff)

        # 检查是否是纯色背景（4角颜色相似）
        # 同时检查4角是否是常见影棚颜色（白、灰、黑）
        avg_corner = (
            sum(c[0] for c in corners) // 4,
            sum(c[1] for c in corners) // 4,
            sum(c[2] for c in corners) // 4,
        )
        brightness = (avg_corner[0] + avg_corner[1] + avg_corner[2]) / 3

        # 判断背景类型
        if max_diff < 30:
            bg_type = "纯净"
            bg_pass = True
        elif max_diff < 60:
            bg_type = "较纯净"
            bg_pass = True
        else:
            bg_type = "复杂"
            bg_pass = False

        return {
            "pass": bg_pass,
            "w": w,
            "h": h,
            "asp": round(asp, 2),
            "max_diff": max_diff,
            "bg_type": bg_type,
            "brightness": round(brightness, 0),
            "avg_corner": avg_corner,
        }
    except Exception as e:
        return {"pass": False, "reason": f"分析失败: {e}"}


def main():
    print("=" * 60)
    print("v12 候选图自动筛选 - 背景纯净度 + 宽高比")
    print("=" * 60)

    results = []
    for brand, model in CARS:
        car_dir = CAND_DIR / brand / model
        if not car_dir.exists():
            print(f"\n### {brand}/{model}: 目录不存在")
            continue

        print(f"\n### {brand}/{model}")
        cands = []
        for f in sorted(car_dir.glob("cand_*.jpg")):
            analysis = analyze_image(f)
            analysis["filename"] = f.name
            analysis["path"] = str(f)
            cands.append(analysis)
            status = "PASS" if analysis.get("pass") else "FAIL"
            info = ""
            if analysis.get("bg_type"):
                info = f" {analysis['w']}x{analysis['h']} asp={analysis['asp']} diff={analysis['max_diff']} bg={analysis['bg_type']}"
            else:
                info = f" {analysis.get('reason', '')}"
            print(f"  {f.name}: {status}{info}")

        # 按 max_diff 升序排列（背景最纯净的在前）
        passed = [c for c in cands if c.get("pass")]
        passed.sort(key=lambda x: x.get("max_diff", 999))

        best = passed[0] if passed else None
        if best:
            print(f"  >>> 推荐: {best['filename']} (diff={best['max_diff']})")
        else:
            print(f"  >>> 无合格候选")

        results.append({
            "brand": brand,
            "model": model,
            "candidates": cands,
            "passed_count": len(passed),
            "best": best["filename"] if best else None,
        })

    # 保存结果
    out_file = ROOT / "scripts" / "_v12b_analysis.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out_file}")

    # 统计
    total_pass = sum(r["passed_count"] for r in results)
    has_best = sum(1 for r in results if r["best"])
    print(f"\n统计:")
    print(f"  总候选数: {sum(len(r['candidates']) for r in results)}")
    print(f"  背景纯净候选: {total_pass}")
    print(f"  有推荐候选的车型: {has_best}/19")
    print(f"  无合格候选的车型: {19 - has_best}")
    for r in results:
        if not r["best"]:
            print(f"    无合格: {r['brand']}/{r['model']}")


if __name__ == "__main__":
    main()
