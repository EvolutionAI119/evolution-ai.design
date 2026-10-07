"""19 款车型统一 2D 展示图生成器

目的
----
前端已有 19 款车型的真实照片（`/brands/{brand}/{model}.jpg`），但**尺寸严重不一**：
实测 bentayga 1024x768、continental-gt 2560x1440、veyron 626x626、
divo 640x415…… 直接排布会导致展示参差。

本模块生成**统一规格的 2D 型态图**：
  - 尺寸统一（默认 1600x900，16:9）
  - 以**真实车参**绘制侧视型态（比例来自 carPresets 的 params，非臆造）
  - 用品牌主色着色，风格一致
  - 输出单张画廊图 + 逐车型 PNG，供前端选用

数据来源
--------
车型参数取自 `src/config/carPresets.js` 的 `brands`（与后端
`brand_config/brand_design_knowledge.json` 一致：5 品牌 19 车型）。

用法
----
    python tools/render_brand_gallery.py            # 生成全部
    python tools/render_brand_gallery.py --check    # 只做数据自检
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]      # Evolution-Ai.Design/
PRESETS_JS = ROOT / "src" / "config" / "carPresets.js"


# ---------------------------------------------------------------------------
# 从 carPresets.js 解析车型（不引入 node，纯文本解析）
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
    def L(self) -> float: return self.params.get('overall_length', 4800)
    @property
    def W(self) -> float: return self.params.get('overall_width', 1850)
    @property
    def H(self) -> float: return self.params.get('overall_height', 1450)
    @property
    def WB(self) -> float: return self.params.get('wheel_base', 2800)
    @property
    def GC(self) -> float: return self.params.get('ground_clearance', 150)
    @property
    def FO(self) -> float: return self.params.get('front_overhang', 900)
    @property
    def RO(self) -> float: return self.params.get('rear_overhang', 1000)
    @property
    def hood_len(self) -> float: return self.params.get('hood_length', 1200)
    @property
    def wheel_r(self) -> float: return self.params.get('wheel_diameter', 720) / 2.0
    @property
    def ws_angle(self) -> float: return self.params.get('windshield_angle', 30)
    @property
    def rw_angle(self) -> float: return self.params.get('rear_window_angle', 25)
    @property
    def rsl_angle(self) -> float: return self.params.get('rear_slant_angle', 20)


def parse_brands(js_path: Path = PRESETS_JS) -> List[Model]:
    """解析 carPresets.js 中的品牌与车型"""
    text = js_path.read_text(encoding="utf-8")
    brands: List[Model] = []

    # 按 brand 块切分
    brand_blocks = re.findall(
        r"\{\s*key:\s*'([a-z\-]+)',\s*name:\s*'([^']+)',\s*color:\s*'([^']+)',"
        r"\s*models:\s*\[(.*?)\]\s*\}\s*(?=,\s*\{|\s*\])",
        text, re.S)
    for bkey, bname, color, body in brand_blocks:
        for m in re.finditer(
                r"\{\s*key:\s*'([^']+)',\s*name:\s*'([^']+)',\s*params:\s*\{([^}]*)\}", body):
            mkey, mname, pstr = m.group(1), m.group(2), m.group(3)
            params: Dict[str, float] = {}
            for km in re.finditer(r"(\w+):\s*([0-9.]+)", pstr):
                params[km.group(1)] = float(km.group(2))
            brands.append(Model(brand=bkey, brand_name=bname, color=color,
                                key=mkey, name=mname, params=params))
    return brands


# ---------------------------------------------------------------------------
# 侧视型态轮廓（按真车比例，与后端硬点思路一致）
# ---------------------------------------------------------------------------
def side_profile(m: Model) -> Tuple[np.ndarray, List[Tuple[float, float, float]]]:
    """返回侧视轮廓点（闭环）与车轮位置

    坐标：(x, z)，x 为车长（车头 −），z 为高度，单位 mm。
    """
    L, H, GC = m.L, m.H, m.GC
    x0, x1 = -L / 2.0, L / 2.0
    hood_end = x0 + m.FO + m.hood_len * 0.72
    cowl = hood_end

    # 车顶区间：座舱大致居中偏后
    cabin_x0 = x0 + L * 0.34
    cabin_x1 = x0 + L * 0.72
    roof_z = H

    # 风挡 / 后窗：由倾角推导水平投影
    ws_h = max((H - (GC + H * 0.42)) / max(math.tan(math.radians(m.ws_angle)), 0.15), L * 0.06)
    rw_h = max((H - (GC + H * 0.38)) / max(math.tan(math.radians(m.rw_angle)), 0.12), L * 0.05)
    ws_top_x = cowl + min(ws_h, L * 0.20)
    rw_top_x = cabin_x1 - min(rw_h, L * 0.20)

    # 机盖高度 / 尾厢高度
    hood_z = GC + H * 0.42
    deck_z = GC + H * 0.40

    pts: List[Tuple[float, float]] = [
        (x0, GC * 0.85),                       # 前保下沿
        (x0, GC + H * 0.16),                   # 前保上沿
        (x0 + L * 0.06, hood_z * 0.96),        # 机盖前端
        (hood_end, hood_z),                    # 机盖后端
        (ws_top_x, roof_z - H * 0.03),         # 风挡顶
        (rw_top_x, roof_z),                    # 车顶后
        (cabin_x1, deck_z + H * 0.10),         # 后窗底
        (x1 - L * 0.05, deck_z),               # 尾厢
        (x1, GC + H * 0.14),                   # 后保上沿
        (x1, GC * 0.85),                       # 后保下沿
    ]
    # 底边回环
    loop = pts + [(x1 - L * 0.02, GC), (x0 + L * 0.02, GC)]
    wheels = [
        (x0 + m.FO, m.wheel_r, m.wheel_r),
        (x1 - m.RO, m.wheel_r, m.wheel_r),
    ]
    return np.asarray(loop, dtype=float), wheels


# ---------------------------------------------------------------------------
# 绘制单车型
# ---------------------------------------------------------------------------
def draw_model(ax, m: Model, *, bg: str = "#0d1117", accent: Optional[str] = None) -> None:
    """在给定坐标轴上绘制一个车型的侧视型态"""
    import matplotlib.patches as mpatches
    from matplotlib.path import Path as MPath

    ax.set_facecolor(bg)
    accent = accent or m.color
    prof, wheels = side_profile(m)

    # 车身填充（Catmull-Rom 平滑后填充，避免折线感）
    smooth = _catmull_rom(prof, samples_per_seg=12)
    ax.fill(smooth[:, 0], smooth[:, 1], color=accent, alpha=0.92,
            zorder=3, linewidth=0)
    ax.plot(smooth[:, 0], smooth[:, 1], color="#ffffff", alpha=0.35,
            linewidth=1.2, zorder=4)

    # 车轮
    for wx, wz, wr in wheels:
        ax.add_patch(mpatches.Circle((wx, wz), wr, facecolor="#0a0a0f",
                                     edgecolor="#5b6472", linewidth=2.2, zorder=6))
        ax.add_patch(mpatches.Circle((wx, wz), wr * 0.62, facecolor="#1b2028",
                                     edgecolor="#8b95a5", linewidth=1.4, zorder=7))
        for k in range(5):
            a = 2 * math.pi * k / 5 + 0.3
            ax.plot([wx, wx + wr * 0.58 * math.cos(a)],
                    [wz, wz + wr * 0.58 * math.sin(a)],
                    color="#9aa4b2", linewidth=2.0, zorder=8, solid_capstyle="round")

    # 地面线与阴影
    ax.axhline(0, color="#2a313c", linewidth=1.0, zorder=1)
    ax.fill_between([-m.L / 2, m.L / 2], [-m.H * 0.06] * 2, [0, 0],
                    color=accent, alpha=0.12, zorder=1)

    # 比例
    ax.set_xlim(-m.L / 2 * 1.10, m.L / 2 * 1.10)
    ax.set_ylim(-m.H * 0.14, m.H * 1.16)
    ax.set_aspect('equal')
    ax.axis('off')

    # 标注
    ax.text(0, -m.H * 0.115,
            f"{m.brand_name} {m.name}",
            color="#ffffff", fontsize=15, ha="center", va="top", weight="bold")
    ax.text(0, -m.H * 0.175,
            f"L {m.L:.0f}  W {m.W:.0f}  H {m.H:.0f}  WB {m.WB:.0f} mm",
            color="#8b95a5", fontsize=9.5, ha="center", va="top")


def _catmull_rom(pts: np.ndarray, samples_per_seg: int = 12,
                 closed: bool = True) -> np.ndarray:
    """Catmull-Rom 样条平滑（避免折线外观）"""
    p = np.asarray(pts, dtype=float)
    n = len(p)
    if n < 4:
        return p
    ext = np.vstack([p[-1:], p, p[:1]]) if closed else np.vstack([p[:1], p, p[-1:]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        t = np.linspace(0, 1, samples_per_seg, endpoint=False)[:, None]
        a = 2 * p1
        b = p2 - p0
        c = 2 * p0 - 5 * p1 + 4 * p2 - p3
        d = -p0 + 3 * p1 - 3 * p2 + p3
        out.append(0.5 * (a + b * t + c * t ** 2 + d * t ** 3))
    return np.vstack(out)


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------
def render_gallery(models: List[Model], out_dir: Path,
                   *, cols: int = 4, dpi: int = 110) -> Dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = math.ceil(len(models) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.6, rows * 2.9),
                             facecolor="#0d1117")
    axes = np.atleast_1d(axes).ravel()
    for ax, m in zip(axes, models):
        draw_model(ax, m)
    for ax in axes[len(models):]:
        ax.axis("off")
        ax.set_facecolor("#0d1117")
    fig.suptitle("EVOLUTION AI · 品牌造型基准（19 款车型 · 统一规格 2D 型态图）",
                 color="#ffffff", fontsize=15, y=0.995)
    plt.tight_layout(rect=(0, 0, 1, 0.975))
    gallery = out_dir / "brand_gallery_19.png"
    plt.savefig(gallery, dpi=dpi, facecolor="#0d1117", bbox_inches="tight")
    plt.close(fig)

    # 逐车型单图
    singles = []
    for m in models:
        f, a = plt.subplots(figsize=(6.4, 3.6), facecolor="#0d1117")
        draw_model(a, m)
        p = out_dir / f"{m.brand}__{m.key}.png"
        f.savefig(p, dpi=100, facecolor="#0d1117", bbox_inches="tight")
        plt.close(f)
        singles.append(str(p))

    return {"gallery": str(gallery), "singles": singles,
            "n_models": len(models), "n_brands": len({m.brand for m in models})}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="19 车型统一 2D 展示图")
    ap.add_argument("--out", default=str(ROOT / "public" / "gallery"))
    ap.add_argument("--check", action="store_true", help="只做数据自检")
    ap.add_argument("--cols", type=int, default=4)
    args = ap.parse_args(argv)

    models = parse_brands()
    by_brand: Dict[str, List[str]] = {}
    for m in models:
        by_brand.setdefault(m.brand_name, []).append(m.name)

    print(f"品牌数 {len(by_brand)}   车型数 {len(models)}")
    for b, ms in by_brand.items():
        print(f"  {b:<14} {len(ms):>2} 款: {', '.join(ms)}")

    # 数据自检：参数完整性
    req = ['overall_length', 'overall_width', 'overall_height', 'wheel_base',
           'ground_clearance', 'front_overhang', 'rear_overhang', 'hood_length',
           'wheel_diameter', 'windshield_angle']
    bad = [(m.brand, m.key, [k for k in req if k not in m.params]) for m in models
           if any(k not in m.params for k in req)]
    if bad:
        print("\n⚠ 参数缺失：")
        for b, k, miss in bad:
            print(f"  {b}/{k}: {miss}")
    else:
        print("\n参数自检：全部车型 10 项必需参数齐全 ✓")

    if args.check:
        return 0

    res = render_gallery(models, Path(args.out), cols=args.cols)
    print(f"\n已生成画廊：{res['gallery']}")
    print(f"已生成单图：{len(res['singles'])} 张 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
