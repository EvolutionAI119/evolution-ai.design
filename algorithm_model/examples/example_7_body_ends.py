"""
Example 7 — 车头/车尾精细轮廓装配可视化 (Phase 3 前奏)

装配内容：
  1. 车身上半蒙皮（build_body_nurbs，红色）
  2. 前保险杠（build_front_bumper_nurbs，红色，外凸）
  3. 前格栅（build_grille_nurbs，深灰，梯形凹陷）
  4. 前大灯 ×2（build_headlight_nurbs，白色）
  5. 后保险杠（build_rear_bumper_nurbs，红色）
  6. 尾灯 ×2（build_taillight_nurbs，暗红）

输出：
  - GLB 三维模型（trimesh 装配，多色，Windows 3D 查看器）
  - PNG 四视角图（matplotlib）
  - STEP 装配文件（多产品，CAD 软件）

运行：
  cd D:\\API\\Evolution-Ai.Design
  python algorithm_model\\examples\\example_7_body_ends.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import trimesh

from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends import build_all_ends_nurbs
from algorithm_model.freeform.nurbs_core import evaluate_surface_mesh
from algorithm_model.freeform.step_writer import StepWriter

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def surf_to_mesh(surf: dict, n_u: int = 30, n_v: int = 30,
                 color: tuple = (200, 32, 40, 255)) -> trimesh.Trimesh:
    """NURBS 曲面 → trimesh 三角网格（着色）。"""
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    faces = []
    for i in range(n_u - 1):
        for j in range(n_v - 1):
            a = i * n_v + j
            b = i * n_v + j + 1
            c = (i + 1) * n_v + j
            d = (i + 1) * n_v + j + 1
            faces.append([a, c, b])
            faces.append([b, c, d])
    mesh = trimesh.Trimesh(
        vertices=pts,
        faces=np.array(faces, dtype=np.int64),
        process=True,
    )
    mesh.visual.face_colors = color
    return mesh


def surf_to_grid(surf: dict, n_u: int = 40, n_v: int = 40):
    """NURBS 曲面 → (X, Y, Z) 网格（matplotlib plot_surface 用）。"""
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    grid = pts.reshape(n_u, n_v, 3)
    return grid[:, :, 0], grid[:, :, 1], grid[:, :, 2]


def main():
    print('=' * 60)
    print('Example 7: 车头/车尾精细轮廓装配')
    print('=' * 60)

    params = CarParams()
    print(f'CarParams: L={params.L} W={params.W} H={params.H}')

    # 1. 构造所有 NURBS 曲面
    body_surf = build_body_nurbs(params)
    ends = build_all_ends_nurbs(params)  # [(surf, name, rgba), ...]

    all_surfs = [('body_upper_skin', body_surf, (200, 32, 40, 255))]
    for surf, name, rgba in ends:
        all_surfs.append((name, surf, rgba))

    print(f'\n[1] NURBS 曲面构造完成: {len(all_surfs)} 个零件')
    for name, surf, _ in all_surfs:
        cps = np.asarray(surf['control_points'])
        print(f'    {name:20s} CP {cps.shape}  degree={surf["degree"]}')

    # 2. trimesh 装配 → GLB
    meshes = []
    for name, surf, rgba in all_surfs:
        m = surf_to_mesh(surf, n_u=30, n_v=30, color=rgba)
        meshes.append(m)
    scene = trimesh.Scene(meshes)

    out_dir = os.path.join(_ROOT, 'data', 'step')
    os.makedirs(out_dir, exist_ok=True)

    glb_path = os.path.join(out_dir, 'body_with_ends.glb')
    scene.export(glb_path)
    total_v = sum(len(m.vertices) for m in meshes)
    total_f = sum(len(m.faces) for m in meshes)
    print(f'\n[2] GLB 装配模型: {glb_path}')
    print(f'    {len(meshes)} 零件, {total_v} 顶点, {total_f} 面')

    # 3. matplotlib 四视角 PNG
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(
        f'车头/车尾精细轮廓装配  |  L={params.L} W={params.W} H={params.H}  |  '
        f'{len(all_surfs)} NURBS 零件',
        fontsize=13,
    )

    views = [
        ('Iso (等轴)', 25, 50),
        ('Front (前视)', 5, 90),   # 看车头
        ('Rear (后视)', 5, -90),   # 看车尾
        ('Top (俯视)', 90, 0),
    ]

    color_map = {
        'body_upper_skin': '#c8323a',
        'front_bumper': '#c8323a',
        'rear_bumper': '#c8323a',
        'grille': '#1e1e23',
        'headlight_R': '#f0faff',
        'headlight_L': '#f0faff',
        'taillight_R': '#c81e32',
        'taillight_L': '#c81e32',
    }

    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection='3d')
        for name, surf, _ in all_surfs:
            Xs, Ys, Zs = surf_to_grid(surf, n_u=40, n_v=40)
            ax.plot_surface(
                Xs, Ys, Zs,
                color=color_map.get(name, '#888888'),
                alpha=0.90, edgecolor='none', linewidth=0,
            )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel('X (车长)')
        ax.set_ylabel('Y (车宽)')
        ax.set_zlabel('Z (车高)')
        ax.view_init(elev=elev, azim=azim)

        # 等比例坐标轴
        all_x = np.concatenate([surf_to_grid(s)[0].ravel() for _, s, _ in all_surfs])
        all_y = np.concatenate([surf_to_grid(s)[1].ravel() for _, s, _ in all_surfs])
        all_z = np.concatenate([surf_to_grid(s)[2].ravel() for _, s, _ in all_surfs])
        max_range = max(
            all_x.max() - all_x.min(),
            all_y.max() - all_y.min(),
            all_z.max() - all_z.min(),
        ) / 2
        mid_x = (all_x.max() + all_x.min()) / 2
        mid_y = (all_y.max() + all_y.min()) / 2
        mid_z = (all_z.max() + all_z.min()) / 2
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    png_path = os.path.join(out_dir, 'body_with_ends.png')
    plt.savefig(png_path, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'\n[3] PNG 四视角图: {png_path}')

    # 4. STEP 装配（多产品）
    w = StepWriter()
    for name, surf, _ in all_surfs:
        w.add_surface_as_product(surf, name=name)
    step_path = os.path.join(out_dir, 'body_with_ends.step')
    n_ent = w.write_file(step_path)
    step_size = os.path.getsize(step_path)
    print(f'\n[4] STEP 装配文件: {step_path}')
    print(f'    {len(all_surfs)} 产品, {n_ent} 实体, {step_size:,} bytes')

    print('\n' + '=' * 60)
    print('查看方式：')
    print(f'  - 双击 {os.path.basename(glb_path)} 用 Windows "3D 查看器" 交互旋转')
    print(f'  - 双击 {os.path.basename(png_path)} 查看四视角截图')
    print(f'  - STEP 文件可用 FreeCAD/Onshape 打开查看装配')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
