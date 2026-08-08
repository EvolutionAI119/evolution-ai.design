"""
Example 11 ? G1 ??????

???
  G0-only (body_ends_shared.py): ????, ??????
  G1 (body_ends_g1.py): v=1 ? G1 ??, ?????

???G1 ???? + STEP + PNG
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
from algorithm_model.car_modeling.body_ends_shared import (
    build_front_bumper_shared,
    build_rear_bumper_shared,
    validate_g0_continuity,
)
from algorithm_model.car_modeling.body_ends_g1 import (
    build_front_bumper_g1,
    build_rear_bumper_g1,
    validate_g1_continuity,
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
    print("Example 11 - G1 Tangent Continuity")
    print("=" * 70)

    params = CarParams()
    print("CarParams: L={} W={} H={}".format(params.L, params.W, params.H))

    # 1. ??
    print("\n[1] Build body...")
    body_surf = build_body_nurbs(params)

    # 2. G0-only vs G1 ???
    print("\n[2] Build bumpers (G0-only vs G1)...")
    g0_front = build_front_bumper_shared(params, body_surf)
    g0_rear = build_rear_bumper_shared(params, body_surf)
    g1_front = build_front_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.08)
    g1_rear = build_rear_bumper_g1(params, body_surf, g1_k=0.3, bulge=0.06)

    # 3. G0 + G1 ??
    print("\n[3] Continuity validation...")

    print("\n  --- G0 (positional) ---")
    for name, surf, end in [("G0_front", g0_front, "front"), ("G0_rear", g0_rear, "rear"),
                             ("G1_front", g1_front, "front"), ("G1_rear", g1_rear, "rear")]:
        r = validate_g0_continuity(body_surf, surf, end, n_samples=30)
        print("    {}: max_gap={:.6f}mm  pass={}".format(name, r["max_gap_mm"], r["g0_pass"]))

    print("\n  --- G1 (tangential, normal angle) ---")
    print("  [G0-only bumpers]")
    for name, surf, end in [("G0_front", g0_front, "front"), ("G0_rear", g0_rear, "rear")]:
        r = validate_g1_continuity(body_surf, surf, end, n_samples=50)
        print("    {}: max_angle={:.2f}deg  mean={:.2f}deg  G1_pass={}  visual={}".format(
            name, r["max_angle_deg"], r["mean_angle_deg"], r["g1_pass"], r["visual_smooth"]))

    print("  [G1 bumpers]")
    for name, surf, end in [("G1_front", g1_front, "front"), ("G1_rear", g1_rear, "rear")]:
        r = validate_g1_continuity(body_surf, surf, end, n_samples=50)
        print("    {}: max_angle={:.2f}deg  mean={:.2f}deg  G1_pass={}  visual={}".format(
            name, r["max_angle_deg"], r["mean_angle_deg"], r["g1_pass"], r["visual_smooth"]))

    # 4. STEP ??
    print("\n[4] Export STEP...")
    out_dir = os.path.join(_ROOT, "data", "step")
    os.makedirs(out_dir, exist_ok=True)

    w = StepWriter()
    w.add_surface_as_product(body_surf, name="body_upper_skin")
    w.add_surface_as_product(g1_front, name="front_bumper_g1")
    w.add_surface_as_product(g1_rear, name="rear_bumper_g1")
    step_path = os.path.join(out_dir, "body_g1_ends.step")
    n_ent = w.write_file(step_path)
    print("    STEP: {} ({} entities, {} bytes)".format(
        step_path, n_ent, os.path.getsize(step_path)))

    # 5. PNG ???
    print("\n[5] Render PNG...")
    grids = {
        "body": surf_to_grid(body_surf, 40, 20),
        "front_g1": surf_to_grid(g1_front, 40, 8),
        "rear_g1": surf_to_grid(g1_rear, 40, 8),
    }
    colors = {"body": "#c8323a", "front_g1": "#3a6fc8", "rear_g1": "#3ac86f"}

    all_x = np.concatenate([g[0].ravel() for g in grids.values()])
    all_y = np.concatenate([g[1].ravel() for g in grids.values()])
    all_z = np.concatenate([g[2].ravel() for g in grids.values()])

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("G1 Tangent Continuity | body + G1 bumpers", fontsize=13)
    views = [("Iso", 25, 50), ("Side", 0, 90), ("Front", 5, 0), ("Top", 90, 0)]
    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection="3d")
        for name, (Xs, Ys, Zs) in grids.items():
            ax.plot_surface(Xs, Ys, Zs, color=colors[name], alpha=0.9, edgecolor="none")
        ax.set_title(title)
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.view_init(elev=elev, azim=azim)
        mr = max(all_x.max()-all_x.min(), all_y.max()-all_y.min(), all_z.max()-all_z.min()) / 2
        mx = (all_x.max()+all_x.min())/2; my = (all_y.max()+all_y.min())/2; mz = (all_z.max()+all_z.min())/2
        ax.set_xlim(mx-mr, mx+mr); ax.set_ylim(my-mr, my+mr); ax.set_zlim(mz-mr, mz+mr)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    png_path = os.path.join(out_dir, "body_g1_ends.png")
    plt.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("    PNG: {}".format(png_path))

    # 6. ??
    g0_front_g1 = validate_g1_continuity(body_surf, g0_front, "front", 50)
    g1_front_g1 = validate_g1_continuity(body_surf, g1_front, "front", 50)
    g0_rear_g1 = validate_g1_continuity(body_surf, g0_rear, "rear", 50)
    g1_rear_g1 = validate_g1_continuity(body_surf, g1_rear, "rear", 50)

    print("\n" + "=" * 70)
    print("Summary:")
    print("  Front bumper normal angle: G0-only={:.2f}deg -> G1={:.2f}deg".format(
        g0_front_g1["max_angle_deg"], g1_front_g1["max_angle_deg"]))
    print("  Rear bumper normal angle:  G0-only={:.2f}deg -> G1={:.2f}deg".format(
        g0_rear_g1["max_angle_deg"], g1_rear_g1["max_angle_deg"]))
    if g1_front_g1["g1_pass"] and g1_rear_g1["g1_pass"]:
        print("  G1 continuity: PASS (max angle < 1deg)")
    elif g1_front_g1["visual_smooth"] and g1_rear_g1["visual_smooth"]:
        print("  G1 continuity: VISUAL SMOOTH (max angle < 5deg)")
    else:
        print("  G1 continuity: NEEDS TUNING (max angle >= 5deg)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

