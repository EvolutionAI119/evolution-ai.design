"""
Example 15 - full_car_attached.step 曲面连续性最终检查 (纯 Python)

使用 ContinuityChecker 类进行 G0/G1 连续性分析：
  - finite-difference 法向量 (nurbs_core.evaluate_surface)
  - cKDTree 边界最近邻 + 4x4 边界组合最优匹配
输出 TXT + CSV 报告 + 四视角 PNG 对比图。

运行:
  cd D:\API\Evolution-Ai.Design
  python algorithm_model\examples\example_15_attached_continuity.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from algorithm_model.car_modeling import CarParams, ContinuityChecker
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends_g1 import (
    build_front_bumper_g1, build_rear_bumper_g1,
)
from algorithm_model.car_modeling.body_ends_attached import (
    build_grille_attached, build_headlight_attached, build_taillight_attached,
)
from algorithm_model.car_modeling.accessories_nurbs import (
    build_all_wheels_nurbs, build_all_mirrors_nurbs,
)
from algorithm_model.freeform.nurbs_core import evaluate_surface_mesh

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = os.path.join(_ROOT, "data", "step")
PNG_PATH = os.path.join(OUT_DIR, "continuity_attached_four_view.png")
PDF_PATH = os.path.join(OUT_DIR, "continuity_attached_four_view_highres.pdf")
REPORT_PDF_PATH = os.path.join(OUT_DIR, "continuity_attached_formal_report.pdf")

COLOR_MAP = {
    "body_upper_skin": "#c8323a", "front_bumper_g1": "#c8323a",
    "rear_bumper_g1": "#c8323a", "grille_attached": "#1e1e23",
    "headlight_R_attached": "#f0faff", "headlight_L_attached": "#f0faff",
    "taillight_R_attached": "#c81e32", "taillight_L_attached": "#c81e32",
    "wheel_FL_tire": "#19191e", "wheel_FR_tire": "#19191e",
    "wheel_RL_tire": "#19191e", "wheel_RR_tire": "#19191e",
    "wheel_FL_hub": "#b4b4be", "wheel_FR_hub": "#b4b4be",
    "wheel_RL_hub": "#b4b4be", "wheel_RR_hub": "#b4b4be",
    "mirror_R": "#c8323a", "mirror_L": "#c8323a",
}

# 设计意图验证规则: (pair, desc, expect_g0_mm, expect_g1_deg_or_None,
#                    want_g0_label, want_g1_label)
DESIGN_CHECKS = [
    ("body_upper_skin <-> front_bumper_g1",
     "G0+G1 严格连续 (共享边界+共线)", 0.0, 0.0, "<0.1mm", "<1deg"),
    ("body_upper_skin <-> rear_bumper_g1",
     "G0+G1 严格连续 (共享边界+共线)", 0.0, 0.0, "<0.1mm", "<1deg"),
    ("front_bumper_g1 <-> grille_attached",
     "G0 间隙 = recess 设计凹陷", 60.0, None, "≈recess", "N/A (凹陷)"),
    ("front_bumper_g1 <-> headlight_R_attached",
     "G0 间隙 ≈ headlight bulge", 20.0, None, "≈bulge", "N/A (外凸)"),
    ("front_bumper_g1 <-> headlight_L_attached",
     "G0 间隙 ≈ headlight bulge", 20.0, None, "≈bulge", "N/A (外凸)"),
    ("rear_bumper_g1 <-> taillight_R_attached",
     "G0 间隙 ≈ taillight bulge", 15.0, None, "≈bulge", "N/A (外凸)"),
    ("rear_bumper_g1 <-> taillight_L_attached",
     "G0 间隙 ≈ taillight bulge", 15.0, None, "≈bulge", "N/A (外凸)"),
]


def build_all_surfaces(params):
    """构造 full_car_attached 所有零件并返回 (name, surf) 列表。"""
    body_surf = build_body_nurbs(params)
    front_bumper = build_front_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.08)
    rear_bumper = build_rear_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.06)
    grille = build_grille_attached(params, front_bumper, recess=0.06)
    headlight_R = build_headlight_attached(params, front_bumper, "right", bulge=0.02)
    headlight_L = build_headlight_attached(params, front_bumper, "left", bulge=0.02)
    taillight_R = build_taillight_attached(params, rear_bumper, "right", bulge=0.015)
    taillight_L = build_taillight_attached(params, rear_bumper, "left", bulge=0.015)
    wheels = build_all_wheels_nurbs(params)
    mirrors = build_all_mirrors_nurbs(params)

    items = [
        ("body_upper_skin", body_surf),
        ("front_bumper_g1", front_bumper),
        ("rear_bumper_g1", rear_bumper),
        ("grille_attached", grille),
        ("headlight_R_attached", headlight_R),
        ("headlight_L_attached", headlight_L),
        ("taillight_R_attached", taillight_R),
        ("taillight_L_attached", taillight_L),
    ]
    for s, n, _ in wheels + mirrors:
        items.append((n, s))
    return items


def surf_to_grid(surf, n_u, n_v):
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    g = pts.reshape(n_u, n_v, 3)
    return g[:, :, 0], g[:, :, 1], g[:, :, 2]


def render_four_view(checker, png_path, pdf_path=None, dpi_png=120, dpi_pdf=300):
    """渲染四视角 PNG + 高清矢量 PDF，在 Iso 子图标注关键连续性指标。

    Parameters
    ----------
    checker : ContinuityChecker  已执行 analyze_all 的检查器
    png_path : str               PNG 输出路径（低 DPI 预览）
    pdf_path : str, optional     PDF 输出路径（矢量 + 高 DPI 栅格混合）
    dpi_png : int                PNG 输出 DPI，默认 120
    dpi_pdf : int                PDF 输出 DPI，默认 300（高清正式报告）
    """
    items = checker.items
    results = checker.results
    grids = {}
    for name, surf in items:
        n_u = 40 if "wheel" in name else 30
        n_v = 20
        grids[name] = surf_to_grid(surf, n_u, n_v)

    all_x = np.concatenate([g[0].ravel() for g in grids.values()])
    all_y = np.concatenate([g[1].ravel() for g in grids.values()])
    all_z = np.concatenate([g[2].ravel() for g in grids.values()])

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("Full Car Attached | Continuity Final Check | %d surfaces" % len(items),
                 fontsize=13)
    views = [("Iso (3/4 透视)", 25, 50), ("Side (侧面)", 0, 90),
             ("Front (车头正面)", 5, 0), ("Top (车顶俯视)", 90, 0)]
    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection="3d")
        for name, (Xs, Ys, Zs) in grids.items():
            ax.plot_surface(Xs, Ys, Zs, color=COLOR_MAP.get(name, "#888"),
                            alpha=0.9, edgecolor="none")
        ax.set_title(title)
        ax.set_xlabel("X (车长/m)"); ax.set_ylabel("Y (车宽/m)"); ax.set_zlabel("Z (车高/m)")
        ax.view_init(elev=elev, azim=azim)
        mr = max(all_x.max() - all_x.min(), all_y.max() - all_y.min(),
                 all_z.max() - all_z.min()) / 2
        mx = (all_x.max() + all_x.min()) / 2
        my = (all_y.max() + all_y.min()) / 2
        mz = (all_z.max() + all_z.min()) / 2
        ax.set_xlim(mx - mr, mx + mr)
        ax.set_ylim(my - mr, my + mr)
        ax.set_zlim(mz - mr, mz + mr)

        if idx == 1:
            g1_pairs = [r for r in results if r["rating"] == "G1 OK"]
            note_lines = ["Continuity Highlights:"]
            for r in g1_pairs:
                note_lines.append("  %s: G0=%.3fmm G1=%.2fdeg [G1 OK]" % (
                    r["pair"].split(" <-> ")[1][:16], r["min_gap_mm"], r["max_g1_deg"]))
            near = [r for r in results if "bumper" in r["pair"]
                    and 0.1 < r["min_gap_mm"] < 20.0]
            for r in near[:3]:
                a, b = r["pair"].split(" <-> ")
                short = (a[:12] + ".." + b[:12]) if len(a) + len(b) > 24 else r["pair"]
                note_lines.append("  %s: gap=%.2fmm (设计偏移)" % (short, r["min_gap_mm"]))
            ax.text2D(0.02, 0.98, "\n".join(note_lines), transform=ax.transAxes,
                      fontsize=8, verticalalignment="top",
                      bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                                edgecolor="#666", alpha=0.9))
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_dir = os.path.dirname(png_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    plt.savefig(png_path, dpi=dpi_png, bbox_inches="tight")
    if pdf_path:
        plt.savefig(pdf_path, dpi=dpi_pdf, format="pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    print("=" * 70)
    print("Example 15 - Full Car Attached Continuity Final Check")
    print("=" * 70)
    t0 = time.time()

    params = CarParams()
    print("CarParams: L=%.2f W=%.2f H=%.2f" % (params.L, params.W, params.H))

    # [1] 构造曲面
    print("\n[1] Build surfaces...")
    items = build_all_surfaces(params)
    print("    %d surfaces built in %.2fs" % (len(items), time.time() - t0))

    # [2] 初始化 ContinuityChecker 并批量分析
    print("\n[2] Analyze all pairs (ContinuityChecker)...")
    checker = ContinuityChecker(
        g0_thresh_mm=0.1,
        g1_thresh_deg=1.0,
        g1_visual_deg=5.0,
        n_samples=50,
        skip_patterns=["wheel_", "mirror_"],
    )
    checker.add_surfaces(items)
    results = checker.analyze_all()
    print("    %d pairs analyzed in %.2fs" % (len(results), time.time() - t0))

    # [3] 输出报告
    print("\n[3] Write reports...")
    txt, csv_p = checker.write_reports_with_design_checks(
        OUT_DIR, DESIGN_CHECKS, prefix="continuity_attached_final")
    print("    TXT: " + txt)
    print("    CSV: " + csv_p)

    # [4] 关键配对摘要
    print("\n[4] Key pairs summary:")
    key_list = ["body_upper_skin", "front_bumper_g1", "rear_bumper_g1",
                "grille_attached", "headlight_R_attached", "taillight_R_attached"]
    for r in results:
        in_key = any(k in r["pair"] for k in key_list)
        if in_key and not ("wheel_" in r["pair"] or "mirror_" in r["pair"]):
            print("  %-42s  G0=%.3fmm  G1=%.2fdeg  [%s]" % (
                r["pair"][:42], r["min_gap_mm"], r["max_g1_deg"], r["rating"]))

    # [5] 统计摘要
    print("\n[5] Statistics:")
    s = checker.summary()
    print("    Total pairs: %d  |  G0 pass: %d (%.1f%%)  |  G1 pass: %d (%.1f%%)  |  G0+G1: %d" % (
        s["total_pairs"], s["g0_pass"], s["g0_pass_pct"],
        s["g1_pass"], s["g1_pass_pct"], s["g0_g1_both"]))
    print("    Rating counts: " + str(s["rating_counts"]))

    # [6] 渲染四视角 PNG + 高清 PDF
    print("\n[6] Render PNG + High-res PDF (4-view)...")
    render_four_view(checker, PNG_PATH, pdf_path=PDF_PATH, dpi_png=120, dpi_pdf=300)
    print("    PNG (120dpi): " + PNG_PATH)
    print("    PDF (300dpi): " + PDF_PATH)

    print("\n" + "=" * 70)
    print("Done in %.2fs. Reports + 4-view PNG/PDF written to data/step/" % (time.time() - t0))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
