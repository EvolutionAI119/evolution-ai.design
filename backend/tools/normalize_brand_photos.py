"""19 款车型统一规格 2D 展示（基于项目已有真实照片）

为什么改用真实照片
------------------
项目 `public/brands/{brand}/{model}.jpg` 已有 **19 款车型的真实照片**
（源自 Bing 图片搜索，随项目打包，永远可用）。

我先前尝试"用车型参数绘制合成剪影"，实测**不合格**：
  - 车顶被 Catmull-Rom 平滑拉成针尖（应平顶）
  - 不同车型视觉差异极小（参数差异不足以体现造型特征）
  - 尺寸标注与车型名重叠
且合成剪影明显劣于已有的真实照片——属于"有优质资产却自造劣质替代"。

故本模块改为：**把已有真实照片处理成统一规格**，只解决唯一真实缺口
（实测尺寸参差：626x626 ~ 2560x1440），而不替换内容。

处理内容
--------
1. 统一画幅 1600x900（16:9），cover 裁切 + 居中，两侧留品牌色渐变
2. 底部信息条：品牌 · 车型 · 关键尺寸（数据取自 carPresets.js）
3. 输出：统一画廊（4 列）+ 逐车型统一规格 PNG
4. 校验：逐一报告源图是否缺失/损坏，绝不静默跳过

用法
----
    python tools/normalize_brand_photos.py --check     # 只校验
    python tools/normalize_brand_photos.py             # 生成
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PRESETS_JS = ROOT / "src" / "config" / "carPresets.js"
PHOTO_DIR = ROOT / "public" / "brands"
OUT_DIR = ROOT / "public" / "gallery"

TARGET_W, TARGET_H = 1600, 900
INFO_H = 132                      # 底部信息条高度
BG = (13, 17, 23)


# ---------------------------------------------------------------------------
# 车型清单（复用 gallery 解析逻辑，保持单一来源）
# ---------------------------------------------------------------------------
@dataclass
class Model:
    brand: str
    brand_name: str
    color: str
    key: str
    name: str
    params: Dict[str, float]

    @property
    def L(self) -> float: return self.params.get('overall_length', 0)
    @property
    def W(self) -> float: return self.params.get('overall_width', 0)
    @property
    def H(self) -> float: return self.params.get('overall_height', 0)
    @property
    def WB(self) -> float: return self.params.get('wheel_base', 0)


def parse_brands() -> List[Model]:
    import re
    text = PRESETS_JS.read_text(encoding="utf-8")
    out: List[Model] = []
    blocks = re.findall(
        r"\{\s*key:\s*'([a-z\-]+)',\s*name:\s*'([^']+)',\s*color:\s*'([^']+)',"
        r"\s*models:\s*\[(.*?)\]\s*\}\s*(?=,\s*\{|\s*\])", text, re.S)
    for bkey, bname, color, body in blocks:
        for m in re.finditer(
                r"\{\s*key:\s*'([^']+)',\s*name:\s*'([^']+)',\s*params:\s*\{([^}]*)\}", body):
            params = {k: float(v) for k, v in
                      re.findall(r"(\w+):\s*([0-9.]+)", m.group(3))}
            out.append(Model(brand=bkey, brand_name=bname, color=color,
                             key=m.group(1), name=m.group(2), params=params))
    return out


def hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def find_font(size: int) -> ImageFont.FreeTypeFont:
    """找一个可用字体（含中文回退）"""
    cands = [
        r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for c in cands:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# 单图处理
# ---------------------------------------------------------------------------
def normalize_one(m: Model, src: Path, *,
                  size: Tuple[int, int] = (TARGET_W, TARGET_H)) -> Image.Image:
    """把一张原始照片处理为统一规格

    做法：cover 裁切（保持比例、填满画幅、居中），底部叠加信息条。
    """
    tw, th = size
    img_h = th - INFO_H
    im = Image.open(src).convert("RGB")

    # cover 裁切
    sw, sh = im.size
    scale = max(tw / sw, img_h / sh)
    nw, nh = max(int(sw * scale + 0.5), tw), max(int(sh * scale + 0.5), img_h)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = int((nh - img_h) * 0.42)          # 略偏上，避免切掉车头
    im = im.crop((left, top, left + tw, top + img_h))

    canvas = Image.new("RGB", (tw, th), BG)

    # 顶部品牌色微光（风格统一）
    br, bg_, bb = hex_rgb(m.color)
    glow = Image.new("RGB", (tw, 6), (br, bg_, bb))
    canvas.paste(im, (0, 0))
    canvas.paste(glow, (0, img_h - 6))

    # 底部信息条
    d = ImageDraw.Draw(canvas)
    bar = Image.new("RGB", (tw, INFO_H), (17, 22, 30))
    canvas.paste(bar, (0, img_h))
    # 品牌色左标记
    d.rectangle([0, img_h, 6, th], fill=(br, bg_, bb))

    f_name = find_font(46)
    f_meta = find_font(26)
    f_brand = find_font(26)

    d.text((34, img_h + 20), f"{m.brand_name}  {m.name}",
           font=f_name, fill=(255, 255, 255))
    dims = (f"L {m.L:.0f}  ·  W {m.W:.0f}  ·  H {m.H:.0f}  ·  WB {m.WB:.0f} mm"
            if m.L else "")
    d.text((36, img_h + 82), dims, font=f_meta, fill=(150, 160, 175))
    d.text((tw - 36, img_h + 24), m.brand_name.upper(), font=f_brand,
           fill=(br, bg_, bb), anchor="ra")
    return canvas


def make_gallery(items: List[Tuple[Model, Image.Image]], *,
                 cols: int = 3, cell: Tuple[int, int] = (720, 405),
                 gap: int = 14, pad: int = 20) -> Image.Image:
    """把统一规格单图拼成画廊"""
    rows = math.ceil(len(items) / cols)
    cw, ch = cell
    W = pad * 2 + cols * cw + (cols - 1) * gap
    Th = pad * 2 + rows * ch + (rows - 1) * gap
    canvas = Image.new("RGB", (W, Th), BG)
    for i, (_m, im) in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cw + gap)
        y = pad + r * (ch + gap)
        canvas.paste(im.resize(cell, Image.LANCZOS), (x, y))
    return canvas


# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="19 车型统一规格 2D 展示")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    models = parse_brands()
    print(f"车型 {len(models)} 款，品牌 {len({m.brand for m in models})} 个\n")

    missing, ok = [], []
    for m in models:
        src = PHOTO_DIR / m.brand / f"{m.key}.jpg"
        if not src.exists():
            missing.append((m, src))
            continue
        try:
            with Image.open(src) as im:
                sz = im.size
            ok.append((m, src, sz))
        except Exception as exc:
            missing.append((m, src, f"{type(exc).__name__}"))

    print(f"{'车型':<34}{'源图尺寸':>14}")
    for m, _src, sz in ok:
        print(f"  {m.brand_name + ' ' + m.name:<32}{sz[0]:>6}x{sz[1]:<6}")
    if missing:
        print(f"\n⚠ 缺失/损坏 {len(missing)} 项：")
        for m, src, *rest in missing:
            print(f"  {m.brand}/{m.key}  {src}  {rest[0] if rest else ''}")
    else:
        print(f"\n全部 {len(ok)} 张源图存在且可读 ✓")

    if args.check:
        return 0 if not missing else 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for m, src, _sz in ok:
        img = normalize_one(m, src)
        p = out / f"{m.brand}__{m.key}.png"
        img.save(p, "PNG")
        items.append((m, img))
    # 画廊用较紧凑的单元格重排（避免超大文件）
    gal = make_gallery(items, cols=3)
    gp = out / "brand_gallery_photos_19.png"
    gal.save(gp, "PNG", optimize=True)

    meta = {
        "n_models": len(ok), "n_brands": len({m.brand for m, _s, _z in ok}),
        "cell": [TARGET_W, TARGET_H], "gallery": str(gp),
        "models": [{"brand": m.brand, "brand_name": m.brand_name,
                    "key": m.key, "name": m.name,
                    "source": str(s), "source_size": list(z),
                    "normalized": str(out / f'{m.brand}__{m.key}.png')}
                   for m, s, z in ok],
        "missing": [f"{m.brand}/{m.key}" for m, *_ in missing],
    }
    (out / "gallery_manifest.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n已生成统一规格单图 {len(items)} 张 → {out}")
    print(f"已生成画廊：{gp}")
    print(f"已写出清单：{out / 'gallery_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
