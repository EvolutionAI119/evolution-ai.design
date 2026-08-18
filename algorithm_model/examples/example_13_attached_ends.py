"""
Example 13 - Attached Ends (Grille/Headlight/Taillight G0)

对比独立构造 vs G0 接触 (自适应位置) 的间隙。
输出 STEP + PNG 四视角对比图 + 间隙验证报告。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends import (
    build_grille_nurbs, build_headlight_nurbs, build_taillight_nurbs,
)
from algorithm_model.car_modeling.body_ends_g1 import (
    build_front_bumper_g1, build_rear_bumper_g1,
)
from algorithm_model.car_modeling.body_ends_attached import (
    build_grille_attached, build_headlight_attached, build_taillight_attached,
    validate_attachment_gap,
)
from algorithm_model.freeform.nurbs_core import evaluate_surface_mesh
from algorithm_model.freeform.step_writer import StepWriter

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def surf_to_grid(surf, n_u=40, n_v=20):
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    g = pts.reshape(n_u, n_v, 3)
    return g[:, :, 0], g[:, :, 1], g[:, :, 2]


def main():
    print("=" * 70)
    print("Example 13 - Attached Ends (Grille/Headlight/Taillight G0)")
    print("=" * 70)

    params = CarParams()
    print("CarParams: L={} W={} H={}".format(params.L, params.W, params.H))

    # 1. 车身 + G1 保险杠
    print("\n[1] Build body + G1 bumpers...")
    body_surf = build_body_nurbs(params)
    front_bumper = build_front_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.08)
    rear_bumper = build_rear_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.06)

    # 2. 独立 vs G0 接触
    print("\n[2] Build grille/headlight/taillight (independent vs attached)...")
    grille_ind = build_grille_nurbs(params)
    headlight_R_ind = build_headlight_nurbs(params, "right")
    headlight_L_ind = build_headlight_nurbs(params, "left")
    taillight_R_ind = build_taillight_nurbs(params, "right")
    taillight_L_ind = build_taillight_nurbs(params, "left")

    grille_att = build_grille_attached(params, front_bumper, recess=0.06)
    headlight_R_att = build_headlight_attached(params, front_bumper, "right", bulge=0.02)
    headlight_L_att = build_headlight_attached(params, front_bumper, "left", bulge=0.02)
    taillight_R_att = build_taillight_attached(params, rear_bumper, "right", bulge=0.015)
    taillight_L_att = build_taillight_attached(params, rear_bumper, "left", bulge=0.015)

    # 3. 间隙验证
    print("\n[3] Gap validation (independent vs attached)...")
    print("\n  --- Independent construction ---")
    pairs_ind = [
        (front_bumper, grille_ind, "front_bumper", "grille_ind"),
        (front_bumper, headlight_R_ind, "front_bumper", "headlight_R_ind"),
        (rear_bumper, taillight_R_ind, "rear_bumper", "taillight_R_ind"),
    ]
    for a, b, na, nb in pairs_ind:
        r = validate_attachment_gap(a, b, na, nb, n_samples=40)
        print("    {}: min_gap={:.2f}mm  mean={:.2f}mm  contact={:.1%}".format(
            r["pair"], r["min_gap_mm"], r["mean_gap_mm"], r["contact_ratio"]))

    print("\n  --- G0 attached construction ---")
    pairs_att = [
        (front_bumper, grille_att, "front_bumper", "grille_att"),
        (front_bumper, headlight_R_att, "front_bumper", "headlight_R_att"),
        (front_bumper, headlight_L_att, "front_bumper", "headlight_L_att"),
        (rear_bumper, taillight_R_att, "rear_bumper", "taillight_R_att"),
        (rear_bumper, taillight_L_att, "rear_bumper", "taillight_L_att"),
    ]
    for a, b, na, nb in pairs_att:
        r = validate_attachment_gap(a, b, na, nb, n_samples=40)
        print("    {}: min_gap={:.2f}mm  mean={:.2f}mm  contact={:.1%}".format(
            r["pair"], r["min_gap_mm"], r["mean_gap_mm"], r["contact_ratio"]))

    # 4. STEP
    print("\n[4] Export STEP...")
    out_dir = os.path.join(_ROOT, "data", "step")
    os.makedirs(out_dir, exist_ok=True)

    w = StepWriter()
    w.add_surface_as_product(body_surf, name="body_upper_skin")
    w.add_surface_as_product(front_bumper, name="front_bumper_g1")
    w.add_surface_as_product(rear_bumper, name="rear_bumper_g1")
    w.add_surface_as_product(grille_att, name="grille_attached")
    w.add_surface_as_product(headlight_R_att, name="headlight_R_attached")
    w.add_surface_as_product(headlight_L_att, name="headlight_L_attached")
    w.add_surface_as_product(taillight_R_att, name="taillight_R_attached")
    w.add_surface_as_product(taillight_L_att, name="taillight_L_attached")
    step_path = os.path.join(out_dir, "body_attached_ends.step")
    n_ent = w.write_file(step_path)
    print("    STEP: {} ({} entities, {} bytes)".format(
        step_path, n_ent, os.path.getsize(step_path)))

    # 5. PNG 四视角对比图
    print("\n[5] Render PNG (4-view comparison)...")
    grids = {
        "body": surf_to_grid(body_surf, 40, 20),
        "front_bumper": surf_to_grid(front_bumper, 40, 8),
        "rear_bumper": surf_to_grid(rear_bumper, 40, 8),
        "grille": surf_to_grid(grille_att, 20, 15),
        "headlight_R": surf_to_grid(headlight_R_att, 15, 15),
        "headlight_L": surf_to_grid(headlight_L_att, 15, 15),
        "taillight_R": surf_to_grid(taillight_R_att, 15, 15),
        "taillight_L": surf_to_grid(taillight_L_att, 15, 15),
    }
    colors = {
        "body": "#c8323a", "front_bumper": "#c8323a", "rear_bumper": "#c8323a",
        "grille": "#1e1e23",
        "headlight_R": "#f0faff", "headlight_L": "#f0faff",
        "taillight_R": "#c81e32", "taillight_L": "#c81e32",
    }

    all_x = np.concatenate([g[0].ravel() for g in grids.values()])
    all_y = np.concatenate([g[1].ravel() for g in grids.values()])
    all_z = np.concatenate([g[2].ravel() for g in grids.values()])

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("Attached Ends G0 | body+G1 bumpers+grille+lights | 8 surfaces",
                 fontsize=13)
    views = [("Iso", 25, 50), ("Side", 0, 90), ("Front", 5, 0), ("Top", 90, 0)]
    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection="3d")
        for name, (Xs, Ys, Zs) in grids.items():
            ax.plot_surface(Xs, Ys, Zs, color=colors[name], alpha=0.9,
                            edgecolor="none")
        ax.set_title(title)
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.view_init(elev=elev, azim=azim)
        mr = max(all_x.max() - all_x.min(),
                 all_y.max() - all_y.min(),
                 all_z.max() - all_z.min()) / 2
        mx = (all_x.max() + all_x.min()) / 2
        my = (all_y.max() + all_y.min()) / 2
        mz = (all_z.max() + all_z.min()) / 2
        ax.set_xlim(mx - mr, mx + mr)
        ax.set_ylim(my - mr, my + mr)
        ax.set_zlim(mz - mr, mz + mr)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    png_path = os.path.join(out_dir, "body_attached_ends.png")
    plt.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("    PNG: {}".format(png_path))

    # 6. 尺寸
    print("\n[6] Dimensions:")
    print("    X: {:.3f}m (expect {})".format(all_x.max() - all_x.min(), params.L))
    print("    Y: {:.3f}m (expect {})".format(all_y.max() - all_y.min(), params.W))
    print("    Z: {:.3f}m (expect {})".format(all_z.max() - all_z.min(), params.H))

    print("\n" + "=" * 70)
    print("Done. Attached ends G0 validation complete.")
    print("  STEP:  {}".format(step_path))
    print("  PNG:   {}".format(png_path))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
