"""
Example 10 ? ???? G0 ?????

???
  ?? (body_ends.py): ?????????? 21-24mm
  ?? (body_ends_shared.py): ????????? < 1nm (?? 0)

???
  - G0 ???????
  - STEP ???? (?? + ???????)
  - PNG ??????
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
from mpl_toolkits.mplot3d import Axes3D  # noqa

from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends import build_front_bumper_nurbs, build_rear_bumper_nurbs
from algorithm_model.car_modeling.body_ends_shared import (
    build_front_bumper_shared,
    build_rear_bumper_shared,
    validate_g0_continuity,
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
    print("Example 10 - Shared Boundary G0 Continuity")
    print("=" * 70)

    params = CarParams()
    print("CarParams: L={} W={} H={}".format(params.L, params.W, params.H))

    # 1. ????
    print("\n[1] Build body NURBS...")
    body_surf = build_body_nurbs(params)
    cps = np.asarray(body_surf["control_points"])
    print("    body CP shape: {}".format(cps.shape))

    # 2. ?????????? vs ?????
    print("\n[2] Build bumpers (old independent vs new shared)...")
    old_front = build_front_bumper_nurbs(params)
    old_rear = build_rear_bumper_nurbs(params)
    new_front = build_front_bumper_shared(params, body_surf)
    new_rear = build_rear_bumper_shared(params, body_surf)
    print("    old front bumper CP: {}".format(np.asarray(old_front["control_points"]).shape))
    print("    new front bumper CP: {}".format(np.asarray(new_front["control_points"]).shape))

    # 3. G0 ?????
    print("\n[3] G0 continuity validation...")

    # ???? example_9 ???????????????
    from algorithm_model.examples.example_9_continuity_check import analyze_pair
    old_front_r = analyze_pair(body_surf, old_front, "body", "old_front", n_sample=30)
    old_rear_r = analyze_pair(body_surf, old_rear, "body", "old_rear", n_sample=30)

    # ???????????
    new_front_r = validate_g0_continuity(body_surf, new_front, "front", n_samples=50)
    new_rear_r = validate_g0_continuity(body_surf, new_rear, "rear", n_samples=50)

    print("\n  [Old - independent bumper]")
    print("    front: min_gap={:.3f}mm  max_gap={:.3f}mm".format(
        old_front_r["min_gap_m"] * 1000, old_front_r["max_gap_mm"]))
    print("    rear:  min_gap={:.3f}mm  max_gap={:.3f}mm".format(
        old_rear_r["min_gap_m"] * 1000, old_rear_r["max_gap_mm"]))

    print("\n  [New - shared boundary]")
    print("    front: max_gap={:.6f}mm  mean_gap={:.6f}mm  G0_pass={}".format(
        new_front_r["max_gap_mm"], new_front_r["mean_gap_mm"], new_front_r["g0_pass"]))
    print("    rear:  max_gap={:.6f}mm  mean_gap={:.6f}mm  G0_pass={}".format(
        new_rear_r["max_gap_mm"], new_rear_r["mean_gap_mm"], new_rear_r["g0_pass"]))

    # 4. ?? STEP
    print("\n[4] Export STEP...")
    out_dir = os.path.join(_ROOT, "data", "step")
    os.makedirs(out_dir, exist_ok=True)

    w = StepWriter()
    w.add_surface_as_product(body_surf, name="body_upper_skin")
    w.add_surface_as_product(new_front, name="front_bumper_shared")
    w.add_surface_as_product(new_rear, name="rear_bumper_shared")
    step_path = os.path.join(out_dir, "body_shared_ends.step")
    n_ent = w.write_file(step_path)
    print("    STEP: {} ({} entities, {} bytes)".format(
        step_path, n_ent, os.path.getsize(step_path)))

    # 5. PNG ???
    print("\n[5] Render PNG...")
    grids = {
        "body": surf_to_grid(body_surf, 40, 20),
        "front": surf_to_grid(new_front, 40, 8),
        "rear": surf_to_grid(new_rear, 40, 8),
    }
    colors = {"body": "#c8323a", "front": "#3a6fc8", "rear": "#3ac86f"}

    all_x = np.concatenate([g[0].ravel() for g in grids.values()])
    all_y = np.concatenate([g[1].ravel() for g in grids.values()])
    all_z = np.concatenate([g[2].ravel() for g in grids.values()])

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("Shared Boundary G0 Continuity  |  body + shared bumpers", fontsize=13)
    views = [("Iso", 25, 50), ("Side", 0, 90), ("Front", 5, 0), ("Top", 90, 0)]
    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection="3d")
        for name, (Xs, Ys, Zs) in grids.items():
            ax.plot_surface(Xs, Ys, Zs, color=colors[name], alpha=0.9, edgecolor="none")
        ax.set_title(title)
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.view_init(elev=elev, azim=azim)
        mr = max(all_x.max()-all_x.min(), all_y.max()-all_y.min(), all_z.max()-all_z.min()) / 2
        mx, my, mz = (all_x.max()+all_x.min())/2, (all_y.max()+all_y.min())/2, (all_z.max()+all_z.min())/2
        ax.set_xlim(mx-mr, mx+mr); ax.set_ylim(my-mr, my+mr); ax.set_zlim(mz-mr, mz+mr)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    png_path = os.path.join(out_dir, "body_shared_ends.png")
    plt.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("    PNG: {}".format(png_path))

    # 6. ??
    print("\n" + "=" * 70)
    print("Summary:")
    print("  Old (independent): front min_gap={:.1f}mm, rear min_gap={:.1f}mm".format(
        old_front_r["min_gap_m"] * 1000, old_rear_r["min_gap_m"] * 1000))
    print("  New (shared):      front max_gap={:.4f}mm, rear max_gap={:.4f}mm".format(
        new_front_r["max_gap_mm"], new_rear_r["max_gap_mm"]))
    if new_front_r["g0_pass"] and new_rear_r["g0_pass"]:
        print("  G0 continuity: PASS (gap < 1nm)")
    else:
        print("  G0 continuity: CHECK (gap > 1nm)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

