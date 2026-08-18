# -*- coding: utf-8 -*-
""" restore_hdq_sideview.py
从 HDQ 恢复 911 和 panamera（原本就是正侧视），并清除错误下载的图片。
"""
import hashlib, io, ssl, urllib.request
from pathlib import Path
from PIL import Image as P

BRANDS_D = Path(__file__).resolve().parent.parent / "public" / "brands"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

# 需要从 HDQ 恢复的图片（这些原本就是正侧视）
RESTORE = {
    ("porsche", "911"):      "https://images.hdqwalls.com/download/porsche-911-gt3-earls-court-51-edition-8k-wz-1600x900.jpg",
    ("porsche", "panamera"): "https://images.hdqwalls.com/download/techart-porsche-panamera-sport-turismo-grand-gt-side-view-5m-1600x900.jpg",
    ("porsche", "cayenne"):  "https://images.hdqwalls.com/download/2021-porsche-cayenne-gts-coupe-5k-3y-1600x900.jpg",
}

# 错误下载需要删除的图片（同图重复）
DELETE = [
    # cayenne 不需要预先删除，因为已经被前面的脚本删除了
]


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl._create_unverified_context()
    with urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx)).open(req, timeout=25) as r:
        return r.read()


def write_jpg(raw):
    try:
        with P.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            bio = io.BytesIO()
            im.save(bio, "JPEG", quality=92, optimize=True, progressive=True)
            return bio.getvalue()
    except Exception:
        return raw


def main():
    # 先删除错误覆盖的图片
    for brand, model in DELETE:
        p = BRANDS_D / brand / (model + ".jpg")
        if p.exists():
            print(f"Delete (will re-download): {p}")
            p.unlink()

    # 从 HDQ 恢复
    for (brand, model), url in RESTORE.items():
        print(f"\n[{brand}/{model}]")
        print(f"  Download: {url}")
        try:
            raw = download(url)
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            continue
        try:
            with P.open(io.BytesIO(raw)) as im:
                w, h = im.size
        except Exception as e:
            print(f"  ✗ parse fail: {e}")
            continue
        print(f"  📐 {w}x{h} {len(raw)/1024:.0f}KB")
        p = BRANDS_D / brand / (model + ".jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        final = write_jpg(raw)
        p.write_bytes(final)
        md5 = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        print(f"  💾 SAVED {p.name} md5={md5}")


if __name__ == "__main__":
    main()
