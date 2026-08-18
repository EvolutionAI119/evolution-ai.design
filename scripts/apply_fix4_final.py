"""把4款车的PASS候选图复制到品牌目录（PNG转JPG）"""
import shutil
from pathlib import Path
from PIL import Image
import io

ROOT = Path(r"d:\API\Evolution-Ai.Design")
SRC = ROOT / "public" / "_bing_v2_candidates"
DST = ROOT / "public" / "brands"

# 4款车的PASS候选
PASSES = [
    ("bentley", "bentayga", "6bd7cf90.jpg"),
    ("bentley", "flying-spur", "cdfb4cdd.png"),  # PNG需转JPG
    ("bentley", "continental-gtc", "ef038bdc.jpg"),
    ("rolls-royce", "cullinan", "98f9f64d.jpg"),
]

for brand, model, fname in PASSES:
    src = SRC / f"{brand}__{model}" / fname
    dst = DST / brand / f"{model}.jpg"
    
    if fname.endswith(".png"):
        # PNG转JPG
        with Image.open(src) as im:
            # 转RGB（PNG可能有RGBA）
            if im.mode in ("RGBA", "P"):
                im = im.convert("RGB")
            im.save(dst, "JPEG", quality=92)
        print(f"PNG→JPG: {brand}/{model}.jpg ({src.stat().st_size//1024}KB → {dst.stat().st_size//1024}KB)")
    else:
        shutil.copy2(src, dst)
        print(f"Copy: {brand}/{model}.jpg ({dst.stat().st_size//1024}KB)")

print("\n=== 4款车图片已替换 ===")
