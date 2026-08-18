"""
body_ends — 车头/车尾精细轮廓 NURBS 曲面

包含 5 类零件（与 grille.py / lights.py 参数对齐）：
  1. 前保险杠（4×4 CP, degree=3，外凸弧度）
  2. 前格栅（4×3 CP, degree=3×2，梯形凹陷）
  3. 前大灯（3×3 CP, degree=2，左右各一，略外凸）
  4. 后保险杠（4×4 CP, degree=3）
  5. 尾灯（3×3 CP, degree=2，左右各一）

所有曲面用 nurbs_surface_from_grid 生成 dict，可直接喂给 StepWriter
或 evaluate_surface_mesh 求值。
"""
import numpy as np
from typing import List, Tuple, Dict

from ..freeform.nurbs_core import nurbs_surface_from_grid


def build_front_bumper_nurbs(params) -> dict:
    """前保险杠 NURBS 曲面（车头端面，带外凸弧度）。

    4×4 CP / degree=3：y∈[-W/2, W/2], z∈[gc, gc+0.50]
    中部外凸 ~10cm，边缘 ~2cm，模拟保险杠立体造型。
    """
    x_front = -params.L / 2
    gc = params.ground_clearance
    half_w = params.W / 2

    y_pts = np.array([-half_w, -half_w / 3, half_w / 3, half_w])
    z_pts = np.array([gc, gc + 0.17, gc + 0.33, gc + 0.50])
    z_mid = gc + 0.25

    cp_grid = np.zeros((4, 4, 3))
    for i, y in enumerate(y_pts):
        y_frac = 1.0 - abs(y) / half_w  # 中部=1, 边缘=0
        for j, z in enumerate(z_pts):
            z_frac = max(0.0, 1.0 - abs(z - z_mid) / 0.25)  # 中高=1, 上下=0
            bulge = 0.08 * y_frac * z_frac
            cp_grid[i, j, 0] = x_front + 0.02 + bulge
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=3)


def build_grille_nurbs(params) -> dict:
    """前格栅 NURBS 曲面（梯形，凹陷于保险杠）。

    4×3 CP / degree=3×2：下宽 0.90, 上宽 0.60, 高 0.18m
    凹陷比保险杠前端后 6cm，中部额外凹 2cm。
    """
    x_front = -params.L / 2
    gc = params.ground_clearance
    z_bot = gc + 0.21
    z_top = gc + 0.39
    w_bot = 0.90
    w_top = 0.60

    z_pts = np.array([z_bot, (z_bot + z_top) / 2, z_top])
    cp_grid = np.zeros((4, 3, 3))
    for j, z in enumerate(z_pts):
        z_frac = (z - z_bot) / (z_top - z_bot)  # 0=下, 1=上
        half_w = w_bot / 2 * (1 - z_frac) + w_top / 2 * z_frac
        y_pts = np.linspace(-half_w, half_w, 4)
        for i, y in enumerate(y_pts):
            y_frac = 1.0 - abs(i - 1.5) / 1.5  # 中部=1, 边缘=0
            recess = 0.02 * y_frac
            cp_grid[i, j, 0] = x_front + 0.02 - 0.06 - recess
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=2)


def build_headlight_nurbs(params, side: str = 'right') -> dict:
    """前大灯 NURBS 曲面（3×3 CP / degree=2，略外凸）。

    Args:
        side: 'left' 或 'right'
    """
    hw = params.headlight_width
    hh = params.headlight_height
    x = -params.L / 2 + 0.10
    z_c = params.ground_clearance + 0.65
    half_w = params.W / 2
    y_c = half_w - hw / 2 - 0.05
    if side == 'left':
        y_c = -y_c

    y_pts = np.array([y_c - hw / 2, y_c, y_c + hw / 2])
    z_pts = np.array([z_c - hh / 2, z_c, z_c + hh / 2])

    cp_grid = np.zeros((3, 3, 3))
    for i in range(3):
        y_frac = 1.0 - abs(i - 1) / 1.0  # 中部=1, 边缘=0
        for j in range(3):
            z_frac = 1.0 - abs(j - 1) / 1.0
            bulge = 0.02 * y_frac * z_frac
            cp_grid[i, j, 0] = x + bulge
            cp_grid[i, j, 1] = y_pts[i]
            cp_grid[i, j, 2] = z_pts[j]

    return nurbs_surface_from_grid(cp_grid, degree_u=2, degree_v=2)


def build_rear_bumper_nurbs(params) -> dict:
    """后保险杠 NURBS 曲面（车尾端面，带外凸弧度）。

    4×4 CP / degree=3：y∈[-W/2, W/2], z∈[gc, gc+0.45]
    """
    x_rear = params.L / 2
    gc = params.ground_clearance
    half_w = params.W / 2

    y_pts = np.array([-half_w, -half_w / 3, half_w / 3, half_w])
    z_pts = np.array([gc, gc + 0.15, gc + 0.30, gc + 0.45])
    z_mid = gc + 0.22

    cp_grid = np.zeros((4, 4, 3))
    for i, y in enumerate(y_pts):
        y_frac = 1.0 - abs(y) / half_w
        for j, z in enumerate(z_pts):
            z_frac = max(0.0, 1.0 - abs(z - z_mid) / 0.22)
            bulge = 0.06 * y_frac * z_frac
            cp_grid[i, j, 0] = x_rear - 0.02 - bulge  # 车尾向后凸
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=3)


def build_taillight_nurbs(params, side: str = 'right') -> dict:
    """尾灯 NURBS曲面（3×3 CP / degree=2，略外凸）。

    Args:
        side: 'left' 或 'right'
    """
    tw = 0.35
    th = 0.10
    x = params.L / 2 - 0.10
    z_c = params.ground_clearance + 0.70
    half_w = params.W / 2
    y_c = half_w - tw / 2 - 0.05
    if side == 'left':
        y_c = -y_c

    y_pts = np.array([y_c - tw / 2, y_c, y_c + tw / 2])
    z_pts = np.array([z_c - th / 2, z_c, z_c + th / 2])

    cp_grid = np.zeros((3, 3, 3))
    for i in range(3):
        y_frac = 1.0 - abs(i - 1) / 1.0
        for j in range(3):
            z_frac = 1.0 - abs(j - 1) / 1.0
            bulge = 0.015 * y_frac * z_frac
            cp_grid[i, j, 0] = x + bulge
            cp_grid[i, j, 1] = y_pts[i]
            cp_grid[i, j, 2] = z_pts[j]

    return nurbs_surface_from_grid(cp_grid, degree_u=2, degree_v=2)


def build_all_ends_nurbs(params) -> List[Tuple[dict, str, Tuple[int, int, int, int]]]:
    """构建全部车头/车尾 NURBS 曲面。

    Returns:
        [(surf, name, rgba), ...] 列表，rgba 用于 trimesh 可视化着色
    """
    RED = (200, 32, 40, 255)      # 车身红
    DARK = (30, 30, 35, 255)      # 格栅深灰
    WHITE = (240, 250, 255, 255)  # 大灯白
    AMBER = (255, 240, 200, 255)  # 大灯暖黄
    DARK_RED = (200, 30, 50, 255) # 尾灯暗红
    BRIGHT_RED = (255, 100, 120, 255)  # 尾灯亮红

    items: List[Tuple[dict, str, Tuple[int, int, int, int]]] = [
        (build_front_bumper_nurbs(params), 'front_bumper', RED),
        (build_grille_nurbs(params), 'grille', DARK),
        (build_headlight_nurbs(params, 'right'), 'headlight_R', WHITE),
        (build_headlight_nurbs(params, 'left'), 'headlight_L', WHITE),
        (build_rear_bumper_nurbs(params), 'rear_bumper', RED),
        (build_taillight_nurbs(params, 'right'), 'taillight_R', DARK_RED),
        (build_taillight_nurbs(params, 'left'), 'taillight_L', DARK_RED),
    ]
    return items


__all__ = [
    'build_front_bumper_nurbs',
    'build_grille_nurbs',
    'build_headlight_nurbs',
    'build_rear_bumper_nurbs',
    'build_taillight_nurbs',
    'build_all_ends_nurbs',
]
