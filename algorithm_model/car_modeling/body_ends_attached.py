"""
body_ends_attached - 格栅/大灯/尾灯与保险杠 G0 接触边界 (自适应位置)

设计意图：
  - 格栅 (grille): 与保险杠 v=1 边界 y/z 匹配，整体凹陷 recess (m)
  - 大灯 (headlight): 与保险杠 v=1 边界匹配，位置自适应保险杠范围
  - 尾灯 (taillight): 与后保险杠 v=1 边界匹配，位置自适应
"""
import numpy as np
from typing import Tuple

from scipy.spatial import cKDTree

from ..freeform.nurbs_core import nurbs_surface_from_grid, evaluate_surface


def _sample_boundary_curve(surf, edge, n=300, v_range=(0.0, 1.0)):
    """在曲面边界 dense 采样。"""
    t_min, t_max = v_range
    ts = np.linspace(t_min, t_max, n)
    pts = np.zeros((n, 3))
    for i, t in enumerate(ts):
        if edge == 'u0':
            u, v = 0.0, t
        elif edge == 'u1':
            u, v = 1.0, t
        elif edge == 'v0':
            u, v = t, 0.0
        elif edge == 'v1':
            u, v = t, 1.0
        else:
            raise ValueError("unknown edge: " + edge)
        pts[i] = evaluate_surface(surf, u, v)
    return pts


def _match_x_from_boundary(target_yz, boundary_pts):
    """对每个目标 (y, z)，找到 boundary 中 yz 最近的点的 x 坐标。"""
    bound_yz = boundary_pts[:, 1:3]
    tree = cKDTree(bound_yz)
    _, idxs = tree.query(target_yz, k=1)
    return boundary_pts[idxs, 0]


def build_grille_attached(params, bumper_surf, recess=0.06):
    """G0 接触前格栅：x 从保险杠 v=1 边界匹配，整体凹陷 recess。"""
    bumper_pts = _sample_boundary_curve(bumper_surf, 'v1', n=300)

    gc = params.ground_clearance
    z_bot, z_top = gc + 0.21, gc + 0.39
    w_bot, w_top = 0.90, 0.60

    z_pts = np.array([z_bot, (z_bot + z_top) / 2, z_top])

    targets = []
    for z in z_pts:
        z_frac = (z - z_bot) / (z_top - z_bot)
        half_w = w_bot / 2 * (1 - z_frac) + w_top / 2 * z_frac
        for y in np.linspace(-half_w, half_w, 4):
            targets.append([y, z])
    targets = np.array(targets)

    matched_x = _match_x_from_boundary(targets, bumper_pts)

    cp_grid = np.zeros((4, 3, 3))
    idx = 0
    for j, z in enumerate(z_pts):
        z_frac = (z - z_bot) / (z_top - z_bot)
        half_w = w_bot / 2 * (1 - z_frac) + w_top / 2 * z_frac
        y_pts = np.linspace(-half_w, half_w, 4)
        for i, y in enumerate(y_pts):
            cp_grid[i, j, 0] = matched_x[idx] - recess
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z
            idx += 1

    return nurbs_surface_from_grid(cp_grid, degree_u=3, degree_v=2)


def _adaptive_light_position(boundary_pts, side, hw, hh, z_frac=0.65):
    """从边界点自适应计算大灯/尾灯的 y_c, z_c。"""
    if side == 'right':
        side_pts = boundary_pts[boundary_pts[:, 1] > 0]
    else:
        side_pts = boundary_pts[boundary_pts[:, 1] < 0]

    if len(side_pts) == 0:
        side_pts = boundary_pts

    z_min = side_pts[:, 2].min()
    z_max = side_pts[:, 2].max()
    z_c = z_min + (z_max - z_min) * z_frac

    z_mask = np.abs(side_pts[:, 2] - z_c) < (z_max - z_min) * 0.2
    if z_mask.sum() > 0:
        y_max = np.abs(side_pts[z_mask, 1]).max()
    else:
        y_max = np.abs(side_pts[:, 1]).max()

    hw_actual = min(hw, y_max * 1.4)
    y_c = y_max - hw_actual / 2 - 0.03

    if side == 'left':
        y_c = -y_c

    return y_c, z_c, hw_actual


def build_headlight_attached(params, bumper_surf, side='right', bulge=0.02):
    """G0 接触前大灯：x 从保险杠 v=1 边界匹配，位置自适应。"""
    bumper_pts = _sample_boundary_curve(bumper_surf, 'v1', n=400)

    hw = params.headlight_width
    hh = params.headlight_height
    y_c, z_c, hw_actual = _adaptive_light_position(
        bumper_pts, side, hw, hh, z_frac=0.65)

    y_pts = np.array([y_c - hw_actual / 2, y_c, y_c + hw_actual / 2])
    z_pts = np.array([z_c - hh / 2, z_c, z_c + hh / 2])

    targets = []
    for y in y_pts:
        for z in z_pts:
            targets.append([y, z])
    targets = np.array(targets)

    matched_x = _match_x_from_boundary(targets, bumper_pts)

    cp_grid = np.zeros((3, 3, 3))
    idx = 0
    for i, y in enumerate(y_pts):
        for j, z in enumerate(z_pts):
            cp_grid[i, j, 0] = matched_x[idx] + bulge
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z
            idx += 1

    return nurbs_surface_from_grid(cp_grid, degree_u=2, degree_v=2)


def build_taillight_attached(params, bumper_surf, side='right', bulge=0.015):
    """G0 接触尾灯：x 从后保险杠 v=1 边界匹配，位置自适应。"""
    bumper_pts = _sample_boundary_curve(bumper_surf, 'v1', n=400)

    tw = 0.35
    th = 0.10
    y_c, z_c, tw_actual = _adaptive_light_position(
        bumper_pts, side, tw, th, z_frac=0.7)

    y_pts = np.array([y_c - tw_actual / 2, y_c, y_c + tw_actual / 2])
    z_pts = np.array([z_c - th / 2, z_c, z_c + th / 2])

    targets = []
    for y in y_pts:
        for z in z_pts:
            targets.append([y, z])
    targets = np.array(targets)

    matched_x = _match_x_from_boundary(targets, bumper_pts)

    cp_grid = np.zeros((3, 3, 3))
    idx = 0
    for i, y in enumerate(y_pts):
        for j, z in enumerate(z_pts):
            cp_grid[i, j, 0] = matched_x[idx] + bulge
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z
            idx += 1

    return nurbs_surface_from_grid(cp_grid, degree_u=2, degree_v=2)


def validate_attachment_gap(surf_a, surf_b, name_a, name_b,
                             n_samples=50, g0_threshold=1e-3):
    """验证两个曲面之间的最小间隙 (G0 接触验证)。"""
    bounds_a = []
    for edge in ['u0', 'u1', 'v0', 'v1']:
        pts = _sample_boundary_curve(surf_a, edge, n=n_samples)
        bounds_a.append(pts)
    bounds_a = np.array(bounds_a).reshape(-1, 3)

    bounds_b = []
    for edge in ['u0', 'u1', 'v0', 'v1']:
        pts = _sample_boundary_curve(surf_b, edge, n=n_samples)
        bounds_b.append(pts)
    bounds_b = np.array(bounds_b).reshape(-1, 3)

    tree_b = cKDTree(bounds_b)
    dists, _ = tree_b.query(bounds_a, k=1)

    return {
        "pair": name_a + " <-> " + name_b,
        "min_gap_mm": float(dists.min()) * 1000.0,
        "max_gap_mm": float(dists.max()) * 1000.0,
        "mean_gap_mm": float(dists.mean()) * 1000.0,
        "g0_pass": bool(dists.min() < g0_threshold),
        "contact_ratio": float((dists < g0_threshold).mean()),
    }


__all__ = [
    'build_grille_attached',
    'build_headlight_attached',
    'build_taillight_attached',
    'validate_attachment_gap',
]
