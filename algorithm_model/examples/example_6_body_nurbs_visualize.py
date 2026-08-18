"""
Example 6 — Phase 2 车身 NURBS 曲面可视化

输出两种可查看格式：
  1. PNG 多视角图（matplotlib）：等轴 / 侧视 / 前视 / 俯视
     → data/step/body_nurbs_visual.png
  2. GLB 三维模型（trimesh）：可用 Windows 自带"3D 查看器"交互旋转
     → data/step/body_nurbs_surface.glb

运行：
  cd D:\\API\\Evolution-Ai.Design
  python algorithm_model\\examples\\example_6_body_nurbs_visualize.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import matplotlib
matplotlib.use('Agg')  # 无 GUI 后端，直接保存图片
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

# 中文字体配置（Windows SimHei / Microsoft YaHei）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import trimesh

from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.freeform.nurbs_core import evaluate_surface_mesh


def build_surface_mesh(surf: dict, n_u: int = 50, n_v: int = 50) -> trimesh.Trimesh:
    """把 NURBS 曲面求值为三角网格（用于 GLB 导出）。"""
    pts, _ = evaluate_surface_mesh(surf, n_u=n_u, n_v=n_v)
    grid = pts.reshape(n_u, n_v, 3)

    # 构造三角面索引（每格 2 个三角形）
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
    mesh.visual.face_colors = [200, 32, 40, 255]  # 经典红
    return mesh


def main():
    # 1. 构造车身 NURBS 曲面
    params = CarParams()
    surf = build_body_nurbs(params, n_stations=30, n_profile=20)
    cps = np.asarray(surf['control_points'])  # (30, 20, 3)

    # 2. 曲面求值网格点
    pts, _ = evaluate_surface_mesh(surf, n_u=50, n_v=50)
    grid = pts.reshape(50, 50, 3)
    Xs, Ys, Zs = grid[:, :, 0], grid[:, :, 1], grid[:, :, 2]

    # 控制点网格
    CpX, CpY, CpZ = cps[:, :, 0], cps[:, :, 1], cps[:, :, 2]

    print(f'控制点网格: {cps.shape}')
    print(f'求值曲面: 50x50 = {len(pts)} 点')
    print(f'X 范围: [{Xs.min():.3f}, {Xs.max():.3f}]  (车长)')
    print(f'Y 范围: [{Ys.min():.3f}, {Ys.max():.3f}]  (车宽)')
    print(f'Z 范围: [{Zs.min():.3f}, {Zs.max():.3f}]  (车高)')

    # 3. matplotlib 4 视角 PNG
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(
        f'Phase 2 车身 NURBS 曲面  |  L={params.L} W={params.W} H={params.H}  |  '
        f'30x20 CP, degree=3',
        fontsize=13,
    )

    views = [
        ('Iso (等轴)', 30, 45),
        ('Side (侧视)', 0, 90),
        ('Front (前视)', 0, 0),
        ('Top (俯视)', 90, 0),
    ]

    for idx, (title, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, idx, projection='3d')
        # 求值曲面（车身真实形状）
        ax.plot_surface(
            Xs, Ys, Zs,
            color='#c8323a', alpha=0.85, edgecolor='none', linewidth=0,
        )
        # 控制点网格（线框）
        ax.plot_wireframe(
            CpX, CpY, CpZ,
            color='#1f3a93', alpha=0.25, linewidth=0.5,
        )
        ax.scatter(CpX, CpY, CpZ, c='#1f3a93', s=3, alpha=0.5)

        ax.set_title(title, fontsize=11)
        ax.set_xlabel('X (车长)')
        ax.set_ylabel('Y (车宽)')
        ax.set_zlabel('Z (车高)')
        ax.view_init(elev=elev, azim=azim)

        # 等比例坐标轴
        max_range = max(
            Xs.max() - Xs.min(),
            Ys.max() - Ys.min(),
            Zs.max() - Zs.min(),
        ) / 2
        mid_x = (Xs.max() + Xs.min()) / 2
        mid_y = (Ys.max() + Ys.min()) / 2
        mid_z = (Zs.max() + Zs.min()) / 2
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_dir = os.path.join(_ROOT, 'data', 'step')
    os.makedirs(out_dir, exist_ok=True)

    png_path = os.path.join(out_dir, 'body_nurbs_visual.png')
    plt.savefig(png_path, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'\n[1] PNG 多视角图: {png_path}')

    # 4. GLB 三维模型（Windows 3D 查看器可打开）
    mesh = build_surface_mesh(surf, n_u=50, n_v=50)
    glb_path = os.path.join(out_dir, 'body_nurbs_surface.glb')
    mesh.export(glb_path)
    print(f'[2] GLB 三维模型: {glb_path}  ({len(mesh.vertices)} 顶点, {len(mesh.faces)} 面)')

    # 5. 同时导出 STL（兼容性更好）
    stl_path = os.path.join(out_dir, 'body_nurbs_surface.stl')
    mesh.export(stl_path)
    print(f'[3] STL 三角网格: {stl_path}')

    print('\n查看方式：')
    print(f'  - 双击 {os.path.basename(glb_path)} 用 Windows "3D 查看器" 交互旋转')
    print(f'  - 或双击 {os.path.basename(png_path)} 查看四视角截图')
    return 0


if __name__ == '__main__':
    sys.exit(main())
