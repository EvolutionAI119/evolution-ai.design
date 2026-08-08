"""
Example 8 — Phase 3 整车 NURBS 装配

14 零件装配（18 个 NURBS 曲面）：
  车身（1）+ 前后保险杠（2）+ 格栅（1）+ 大灯×2 + 尾灯×2
  + 4 轮（轮胎+轮毂 ×4 = 8）+ 后视镜×2

输出：
  - GLB 三维装配模型（多色，Windows 3D 查看器）
  - PNG 四视角图（matplotlib）
  - STEP 装配文件（18 产品，CAD 软件）

运行：
  cd D:\\API\\Evolution-Ai.Design
  python algorithm_model\\examples\\example_8_full_car.py
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
from algorithm_model.car_modeling.accessories_nurbs import (
    build_all_wheels_nurbs,
    build_all_mirrors_nurbs,
)
from algorithm_model.freeform.nurbs_core import evaluate_surface_mesh
from algorithm_model.freeform.step_writer import StepWriter

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# matplotlib 颜色映射
COLOR_MAP = {
    'body_upper_skin': '#c8323a',
    'front_bumper': '#c8323a',
    'rear_bumper': '#c8323a',
    'grille': '#1e1e23',
    'headlight_R': '#f0faff',
    'headlight_L': '#f0faff',
    'taillight_R': '#c81e32',
    'taillight_L': '#c81e32',
    'wheel_FL_tire': '#19191e',
    'wheel_FR_tire': '#19191e',
    'wheel_RL_tire': '#19191e',
    'wheel_RR_tire': '#19191e',
    'wheel_FL_hub': '#b4b4be',
    'wheel_FR_hub': '#b4b4be',
    'wheel_RL_hub': '#b4b4be',
    'wheel_RR_hub': '#b4b4be',
    'mirror_R': '#c8323a',
    'mirror_L': '#c8323a',
}


def surf_to_mesh(surf: dict, n_u: int = 30, n_v: int = 20,
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


def surf_to_grid(surf: dict, n_u: int = 30, n_v: int = 20):
    """NURBS 曲面 → (X, Y, Z) 网格。"""
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    grid = pts.reshape(n_u, n_v, 3)
    return grid[:, :, 0], grid[:, :, 1], grid[:, :, 2]


def main():
    print('=' * 60)
    print('Phase 3: 整车 NURBS 装配 (14 零件)')
    print('=' * 60)

    params = CarParams()
    print(f'CarParams: L={params.L} W={params.W} H={params.H} '
          f'wheelbase={params.wheelbase} wheel_R={params.wheel_radius}')

    # 1. 构造所有 NURBS 曲面
    body_surf = build_body_nurbs(params)
    ends = build_all_ends_nurbs(params)
    wheels = build_all_wheels_nurbs(params)
    mirrors = build_all_mirrors_nurbs(params)

    # 汇总：车身(1) + 端面(7) + 车轮(8) + 后视镜(2) = 18 曲面
    all_surfs = [(body_surf, 'body_upper_skin', (200, 32, 40, 255))]
    all_surfs += ends + wheels + mirrors

    # 零件分类统计
    n_body = 1
    n_ends = len(ends)
    n_wheels = len(wheels)
    n_mirrors = len(mirrors)
    print(f'\n[1] NURBS 曲面构造完成: {len(all_surfs)} 曲面')
    print(f'    车身: {n_body}  端面: {n_ends}  车轮: {n_wheels}(4轮×2)  后视镜: {n_mirrors}')
    for surf, name, _ in all_surfs:
        cps = np.asarray(surf['control_points'])
        print(f'    {name:22s} CP {str(cps.shape):16s} degree={surf["degree"]}')

    # 2. trimesh 装配 → GLB
    meshes = []
    for surf, name, rgba in all_surfs:
        # 车轮圆柱面用更多周向采样
        n_u = 40 if 'wheel' in name else 30
        n_v = 20
        m = surf_to_mesh(surf, n_u=n_u, n_v=n_v, color=rgba)
        meshes.append(m)
    scene = trimesh.Scene(meshes)

    out_dir = os.path.join(_ROOT, 'data', 'step')
    os.makedirs(out_dir, exist_ok=True)

    glb_path = os.path.join(out_dir, 'full_car_nurbs.glb')
    scene.export(glb_path)
    total_v = sum(len(m.vertices) for m in meshes)
    total_f = sum(len(m.faces) for m in meshes)
    print(f'\n[2] GLB 整车装配: {glb_path}')
    print(f'    {len(meshes)} 曲面, {total_v} 顶点, {total_f} 面')

    # 3. matplotlib 四视角 PNG
    # 预计算所有网格（避免重复求值）
    grids = {}
    for surf, name, _ in all_surfs:
        n_u = 40 if 'wheel' in name else 30
        n_v = 20
        grids[name] = surf_to_grid(surf, n_u=n_u, n_v=n_v)

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(
        f'Phase 3 整车 NURBS 装配  |  L={params.L} W={params.W} H={params.H}  |  '
        f'14 零件 / {len(all_surfs)} 曲面',
        fontsize=13,
    )

    views = [
        ('Iso (等轴)', 25, 50),
        ('Side (侧视)', 0, 90),
        ('Front (前视)', 5, 0),
        ('Top (俯视)', 90, 0),
    ]

    # 计算全局包围盒
    all_x = np.concatenate([g[0].ravel() for g in grids.values()])
    all_y = np.concatenate([g[1].ravel() for g in grids.values()])
    all_z = np.concatenate([g[2].ravel() for g in grids.values()])

    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection='3d')
        for surf, name, _ in all_surfs:
            Xs, Ys, Zs = grids[name]
            ax.plot_surface(
                Xs, Ys, Zs,
                color=COLOR_MAP.get(name, '#888888'),
                alpha=0.90, edgecolor='none', linewidth=0,
            )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel('X (车长)')
        ax.set_ylabel('Y (车宽)')
        ax.set_zlabel('Z (车高)')
        ax.view_init(elev=elev, azim=azim)

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
    png_path = os.path.join(out_dir, 'full_car_nurbs.png')
    plt.savefig(png_path, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'\n[3] PNG 四视角图: {png_path}')

    # 4. STEP 整车装配（18 产品）
    w = StepWriter()
    for surf, name, _ in all_surfs:
        w.add_surface_as_product(surf, name=name)
    step_path = os.path.join(out_dir, 'full_car_nurbs.step')
    n_ent = w.write_file(step_path)
    step_size = os.path.getsize(step_path)
    print(f'\n[4] STEP 整车装配: {step_path}')
    print(f'    {len(all_surfs)} 产品, {n_ent} 实体, {step_size:,} bytes')

    # 5. 整车尺寸验证
    print(f'\n[5] 整车尺寸验证:')
    print(f'    车长 X: {all_x.max() - all_x.min():.3f}m  (期望 {params.L}m)')
    print(f'    车宽 Y: {all_y.max() - all_y.min():.3f}m  (期望 {params.W}m)')
    print(f'    车高 Z: {all_z.max() - all_z.min():.3f}m  (期望 {params.H}m)')

    print('\n' + '=' * 60)
    print('Phase 3 整车 NURBS 装配完成')
    print('查看方式：')
    print(f'  - 双击 {os.path.basename(glb_path)} 用 Windows "3D 查看器" 交互旋转')
    print(f'  - 双击 {os.path.basename(png_path)} 查看四视角截图')
    print(f'  - STEP 文件可用 FreeCAD/Onshape 打开查看装配')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
