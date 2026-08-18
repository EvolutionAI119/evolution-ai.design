"""
Example 14 - Full Car with G1 Bumpers + Attached Ends

集成 G1 保险杠 + G0 接触格栅/大灯/尾灯 + 车轮/后视镜。
输出 STEP + GLB + PNG + 连续性验证。
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
import trimesh

from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends_g1 import (
    build_front_bumper_g1, build_rear_bumper_g1,
    validate_g1_continuity,
)
from algorithm_model.car_modeling.body_ends_attached import (
    build_grille_attached, build_headlight_attached, build_taillight_attached,
    validate_attachment_gap,
)
from algorithm_model.car_modeling.body_ends_shared import validate_g0_continuity
from algorithm_model.car_modeling.accessories_nurbs import (
    build_all_wheels_nurbs, build_all_mirrors_nurbs,
)
from algorithm_model.freeform.nurbs_core import evaluate_surface_mesh
from algorithm_model.freeform.step_writer import StepWriter

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

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
RGBA_MAP = {
    "body_upper_skin": (200,32,40,255), "front_bumper_g1": (200,32,40,255),
    "rear_bumper_g1": (200,32,40,255), "grille_attached": (30,30,35,255),
    "headlight_R_attached": (240,250,255,255), "headlight_L_attached": (240,250,255,255),
    "taillight_R_attached": (200,30,50,255), "taillight_L_attached": (200,30,50,255),
    "wheel_FL_tire": (25,25,30,255), "wheel_FR_tire": (25,25,30,255),
    "wheel_RL_tire": (25,25,30,255), "wheel_RR_tire": (25,25,30,255),
    "wheel_FL_hub": (180,180,190,255), "wheel_FR_hub": (180,180,190,255),
    "wheel_RL_hub": (180,180,190,255), "wheel_RR_hub": (180,180,190,255),
    "mirror_R": (200,32,40,255), "mirror_L": (200,32,40,255),
}


def surf_to_mesh(surf, n_u, n_v, color):
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    faces = []
    for i in range(n_u-1):
        for j in range(n_v-1):
            a = i*n_v+j; b = i*n_v+j+1; c = (i+1)*n_v+j; d = (i+1)*n_v+j+1
            faces.append([a,c,b]); faces.append([b,c,d])
    m = trimesh.Trimesh(vertices=pts, faces=np.array(faces,dtype=np.int64), process=True)
    m.visual.face_colors = color
    return m


def surf_to_grid(surf, n_u, n_v):
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    g = pts.reshape(n_u, n_v, 3)
    return g[:,:,0], g[:,:,1], g[:,:,2]


def main():
    print("=" * 70)
    print("Example 14 - Full Car Attached (G1 bumpers + G0 ends)")
    print("=" * 70)

    params = CarParams()
    print("CarParams: L={} W={} H={}".format(params.L, params.W, params.H))

    # 1. 构造所有曲面
    print("\n[1] Build surfaces...")
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

    all_surfs = [
        (body_surf, "body_upper_skin"),
        (front_bumper, "front_bumper_g1"),
        (rear_bumper, "rear_bumper_g1"),
        (grille, "grille_attached"),
        (headlight_R, "headlight_R_attached"),
        (headlight_L, "headlight_L_attached"),
        (taillight_R, "taillight_R_attached"),
        (taillight_L, "taillight_L_attached"),
    ]
    all_surfs += [(s, n) for s, n, _ in wheels + mirrors]
    print("    Total: {} surfaces".format(len(all_surfs)))

    # 2. 连续性验证
    print("\n[2] Continuity validation...")
    print("  --- Body <-> Bumpers (G0 + G1) ---")
    for end, bumper in [("front", front_bumper), ("rear", rear_bumper)]:
        g0 = validate_g0_continuity(body_surf, bumper, end, 30)
        g1 = validate_g1_continuity(body_surf, bumper, end, 50)
        print("    {}: G0 gap={:.6f}mm pass={} | G1 angle={:.2f}deg pass={}".format(
            end, g0["max_gap_mm"], g0["g0_pass"], g1["max_angle_deg"], g1["g1_pass"]))

    print("  --- Bumpers <-> Ends (G0 contact) ---")
    end_pairs = [
        (front_bumper, grille, "front_bumper", "grille"),
        (front_bumper, headlight_R, "front_bumper", "headlight_R"),
        (front_bumper, headlight_L, "front_bumper", "headlight_L"),
        (rear_bumper, taillight_R, "rear_bumper", "taillight_R"),
        (rear_bumper, taillight_L, "rear_bumper", "taillight_L"),
    ]
    for a, b, na, nb in end_pairs:
        r = validate_attachment_gap(a, b, na, nb, n_samples=40)
        print("    {}: min_gap={:.2f}mm  contact={:.1%}".format(
            r["pair"], r["min_gap_mm"], r["contact_ratio"]))

    # 3. GLB
    print("\n[3] Build GLB...")
    meshes = []
    for surf, name in all_surfs:
        n_u = 40 if "wheel" in name else 30
        n_v = 20
        m = surf_to_mesh(surf, n_u, n_v, RGBA_MAP.get(name, (180,180,180,255)))
        meshes.append(m)
    scene = trimesh.Scene(meshes)
    out_dir = os.path.join(_ROOT, "data", "step")
    os.makedirs(out_dir, exist_ok=True)
    glb_path = os.path.join(out_dir, "full_car_attached.glb")
    scene.export(glb_path)
    tv = sum(len(m.vertices) for m in meshes)
    tf = sum(len(m.faces) for m in meshes)
    print("    GLB: {} ({} verts, {} faces)".format(glb_path, tv, tf))

    # 4. PNG 四视角
    print("\n[4] Render PNG...")
    grids = {}
    for surf, name in all_surfs:
        n_u = 40 if "wheel" in name else 30
        n_v = 20
        grids[name] = surf_to_grid(surf, n_u, n_v)

    all_x = np.concatenate([g[0].ravel() for g in grids.values()])
    all_y = np.concatenate([g[1].ravel() for g in grids.values()])
    all_z = np.concatenate([g[2].ravel() for g in grids.values()])

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("Full Car Attached | G1 bumpers + G0 ends | {} surfaces".format(
        len(all_surfs)), fontsize=13)
    views = [("Iso", 25, 50), ("Side", 0, 90), ("Front", 5, 0), ("Top", 90, 0)]
    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection="3d")
        for name, (Xs, Ys, Zs) in grids.items():
            ax.plot_surface(Xs, Ys, Zs, color=COLOR_MAP.get(name, "#888"),
                            alpha=0.9, edgecolor="none")
        ax.set_title(title)
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
        ax.view_init(elev=elev, azim=azim)
        mr = max(all_x.max()-all_x.min(), all_y.max()-all_y.min(), all_z.max()-all_z.min())/2
        mx=(all_x.max()+all_x.min())/2; my=(all_y.max()+all_y.min())/2; mz=(all_z.max()+all_z.min())/2
        ax.set_xlim(mx-mr,mx+mr); ax.set_ylim(my-mr,my+mr); ax.set_zlim(mz-mr,mz+mr)
    plt.tight_layout(rect=[0,0,1,0.95])
    png_path = os.path.join(out_dir, "full_car_attached.png")
    plt.savefig(png_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("    PNG: {}".format(png_path))

    # 5. STEP
    print("\n[5] Export STEP...")
    w = StepWriter()
    for surf, name in all_surfs:
        w.add_surface_as_product(surf, name=name)
    step_path = os.path.join(out_dir, "full_car_attached.step")
    n_ent = w.write_file(step_path)
    print("    STEP: {} ({} entities, {} bytes)".format(
        step_path, n_ent, os.path.getsize(step_path)))

    # 6. 尺寸
    print("\n[6] Dimensions:")
    print("    X: {:.3f}m (expect {})".format(all_x.max()-all_x.min(), params.L))
    print("    Y: {:.3f}m (expect {})".format(all_y.max()-all_y.min(), params.W))
    print("    Z: {:.3f}m (expect {})".format(all_z.max()-all_z.min(), params.H))

    print("\n" + "=" * 70)
    print("Done. Full car attached assembly complete.")
    print("  GLB:  {}".format(glb_path))
    print("  PNG:  {}".format(png_path))
    print("  STEP: {}".format(step_path))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
