"""
accessories_nurbs — 车轮 + 后视镜 NURBS 曲面

车轮：轮胎圆柱面（9×2 CP / degree=3×1，首尾 CP 重合实现圆周闭合）
      4 轮布局：前左/前右/后左/后右，按轴距 + 轮距定位
后视镜：镜壳曲面（4×4 CP / degree=3，略外凸模拟壳体弧度）
        左右各一，位于 A 柱附近

与 wheels.py / mirrors.py 参数对齐。
"""
import numpy as np
from typing import List, Tuple

from ..freeform.nurbs_core import nurbs_surface_from_grid


def build_tire_nurbs(params, position: Tuple[float, float, float]) -> dict:
    """单个车轮轮胎 NURBS 曲面（圆柱面，轴沿 Y）。

    9×2 CP / degree=3×1：圆周 9 点（首尾重合闭合）× 宽度 2 点。
    轮胎半径 R=wheel_radius，宽度 W=wheel_width。

    Args:
        position: 车轮中心 (x, y, z)
    """
    R = params.wheel_radius
    W = params.wheel_width

    # 9 点圆周（endpoint=True，首尾重合实现位置连续）
    n_theta = 9
    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=True)
    y_pts = np.array([-W / 2, W / 2])

    cp_grid = np.zeros((n_theta, 2, 3))
    for i, theta in enumerate(thetas):
        for j, y in enumerate(y_pts):
            cp_grid[i, j, 0] = position[0] + R * np.cos(theta)
            cp_grid[i, j, 1] = position[1] + y
            cp_grid[i, j, 2] = position[2] + R * np.sin(theta)

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=1)


def build_hub_nurbs(params, position: Tuple[float, float, float]) -> dict:
    """轮毂 NURBS 曲面（圆柱面，半径 R×0.4，略凸出于轮胎外侧）。

    9×2 CP / degree=3×1。
    """
    R = params.wheel_radius * 0.4  # 轮毂半径
    W = params.wheel_width * 1.1   # 略宽于轮胎

    n_theta = 9
    thetas = np.linspace(0, 2 * np.pi, n_theta, endpoint=True)
    y_pts = np.array([-W / 2, W / 2])

    cp_grid = np.zeros((n_theta, 2, 3))
    for i, theta in enumerate(thetas):
        for j, y in enumerate(y_pts):
            cp_grid[i, j, 0] = position[0] + R * np.cos(theta)
            cp_grid[i, j, 1] = position[1] + y
            cp_grid[i, j, 2] = position[2] + R * np.sin(theta)

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=1)


def build_all_wheels_nurbs(params) -> List[Tuple[dict, str, tuple]]:
    """构建 4 个车轮 NURBS 曲面（轮胎 + 轮毂）。

    布局：前左 FL / 前右 FR / 后左 RL / 后右 RR
    x = ±wheelbase/2, y = ±(W/2 - 0.05), z = wheel_radius + 0.02
    """
    R = params.wheel_radius
    wb_half = params.wheelbase / 2
    wheel_y = params.W / 2 - 0.05
    wheel_z = R + 0.02

    positions = [
        (-wb_half, wheel_y, wheel_z),    # 前左 FL
        (-wb_half, -wheel_y, wheel_z),   # 前右 FR
        (wb_half, wheel_y, wheel_z),     # 后左 RL
        (wb_half, -wheel_y, wheel_z),    # 后右 RR
    ]
    labels = ['FL', 'FR', 'RL', 'RR']

    TIRE_BLACK = (25, 25, 30, 255)
    HUB_SILVER = (180, 180, 190, 255)

    items: List[Tuple[dict, str, tuple]] = []
    for pos, lab in zip(positions, labels):
        # 轮胎
        items.append((
            build_tire_nurbs(params, pos),
            f'wheel_{lab}_tire',
            TIRE_BLACK,
        ))
        # 轮毂
        items.append((
            build_hub_nurbs(params, pos),
            f'wheel_{lab}_hub',
            HUB_SILVER,
        ))
    return items


def build_mirror_shell_nurbs(params, side: str = 'right') -> dict:
    """后视镜镜壳 NURBS 曲面（4×4 CP / degree=3，略外凸）。

    镜壳尺寸：Y 0.12m × Z 0.10m，X 外凸 4cm。
    位于 A 柱附近（x = -L/2 + hood_length + 0.18）。

    Args:
        side: 'left' 或 'right'
    """
    mirror_x = -params.L / 2 + params.hood_length + 0.18
    mirror_y_base = params.W / 2 + 0.04
    mirror_z = params.ground_clearance + 1.05

    if side == 'left':
        mirror_y_base = -mirror_y_base

    # 4×4 CP：Y 方向 4 点 × Z 方向 4 点
    y_pts = np.linspace(-0.06, 0.06, 4) + mirror_y_base
    z_pts = np.linspace(-0.05, 0.05, 4) + mirror_z

    cp_grid = np.zeros((4, 4, 3))
    for i, y in enumerate(y_pts):
        y_frac = 1.0 - abs(i - 1.5) / 1.5  # 中部=1, 边缘=0
        for j, z in enumerate(z_pts):
            z_frac = 1.0 - abs(j - 1.5) / 1.5
            bulge = 0.04 * y_frac * z_frac  # 外凸 4cm
            cp_grid[i, j, 0] = mirror_x + bulge
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=3)


def build_all_mirrors_nurbs(params) -> List[Tuple[dict, str, tuple]]:
    """构建左右后视镜 NURBS 曲面。"""
    BODY_RED = (200, 30, 40, 255)
    return [
        (build_mirror_shell_nurbs(params, 'right'), 'mirror_R', BODY_RED),
        (build_mirror_shell_nurbs(params, 'left'), 'mirror_L', BODY_RED),
    ]


__all__ = [
    'build_tire_nurbs',
    'build_hub_nurbs',
    'build_all_wheels_nurbs',
    'build_mirror_shell_nurbs',
    'build_all_mirrors_nurbs',
]
