#!/usr/bin/env python3
"""把每个车型 diff 最低的候选复制到 public/brands/"""
import shutil, json, sys
from pathlib import Path
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
from PIL import Image

ROOT = Path(r"d:\API\Evolution-Ai.Design")
CAND_DIR = ROOT / "scripts" / "_candidates_v13"
BRANDS_DIR = ROOT / "public" / "brands"

# 每个车型的最佳候选文件名（从 analyze_v13.py 输出获取）
BEST = {
    "rolls-royce/phantom": "cand_02.jpg",
    "rolls-royce/ghost": "cand_06.jpg",
    "rolls-royce/cullinan": "cand_12.jpg",
    "rolls-royce/wraith": "cand_12.jpg",
    "bentley/continental-gt": "cand_09.jpg",
    "bentley/continental-gtc": "cand_12.jpg",
    "bentley/flying-spur": "cand_05.jpg",
    "bentley/bentayga": "cand_05.jpg",
    "bugatti/chiron": "cand_09.jpg",
    "bugatti/veyron": "cand_15.jpg",
    "bugatti/divo": "cand_03.jpg",
    "porsche/911": "cand_04.jpg",
    "porsche/taycan": "cand_11.jpg",
    "porsche/panamera": "cand_02.jpg",
    "porsche/cayenne": "cand_03.jpg",
    "porsche/macan": "cand_09.jpg",
    "ferrari/sf90": "cand_12.jpg",
    "ferrari/f8-tributo": "cand_13.jpg",
    "ferrari/roma": "cand_01.jpg",
}

for car_path, cand_file in BEST.items():
    brand, model = car_path.split("/")
    src = CAND_DIR / brand / model / cand_file
    dst = BRANDS_DIR / brand / f"{model}.jpg"
    if not src.exists():
        print(f"MISS: {src}")
        continue
    shutil.copy2(src, dst)
    # 确认尺寸
    with Image.open(dst) as img:
        w, h = img.size
    print(f"OK: {brand}/{model}.jpg <- {cand_file} ({w}x{h})")

print(f"\n完成: {len(BEST)} 张图已复制到 public/brands/")
