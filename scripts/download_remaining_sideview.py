# -*- coding: utf-8 -*-
"""download_remaining_sideview.py - 下载剩余车型的Side View图"""
import io, ssl, urllib.request
from pathlib import Path
from PIL import Image as P

CUR = Path(__file__).resolve().parent
PREVIEW = CUR.parent / "public" / "_dailyrevs_preview"
PREVIEW.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
CTX = ssl._create_unverified_context()

# 从搜索结果中提取的标注"Side View"的CDN URL
SIDE_VIEW_IDS = {
    "Bugatti_Veyron": ["vWw0cfZlsu"],  # dailyrevs "Displaying Side View"
}

def download(cdn_id):
    url = f"https://aka.doubaocdn.com/s/{cdn_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.dailyrevs.com/"})
    try:
        with urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)).open(req, timeout=15) as r:
            return r.read()
    except Exception as e:
        print(f"  ERR {cdn_id}: {e}")
        return None

for name, ids in SIDE_VIEW_IDS.items():
    for cdn_id in ids:
        raw = download(cdn_id)
        if not raw:
            continue
        with P.open(io.BytesIO(raw)) as im:
            w, h = im.size
            im2 = im.convert("RGB")
            bio = io.BytesIO()
            im2.save(bio, "JPEG", quality=90)
            fname = f"{name}_sideview_{cdn_id}.jpg"
            (PREVIEW / fname).write_bytes(bio.getvalue())
            print(f"  {name} {cdn_id}: {w}x{h} -> {fname}")
