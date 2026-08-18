"""
body_ends_shared ? ???????? NURBS ?? (G0 ??)

???????? v=0 ??????? u=0/u=1 ??????
?? G0 ???? (???? = 0)?

????
  u ???????? (??? v ????)?n_profile ???? (??????)
  v ???????? (v=0, ??) ??? (v=n_v-1)
  v=0 ? = ?? u=0 (?) ? u=1 (?) ????? (????)
  v=1..n_v-1 ??x ?????y/z ?? v=0 ?

G0 ?????? v=0 ???? = ?????????????
clamped open-uniform ???? (??????)??????????
"""
import numpy as np
from typing import Tuple

from ..freeform.nurbs_core import nurbs_surface_from_grid, evaluate_surface


def extract_body_end_curve(body_surf: dict, end: str = "front") -> np.ndarray:
    """???? u=0 (front) ? u=1 (rear) ?????????

    Args:
        body_surf: build_body_nurbs ??? NURBS dict
        end: "front" (u=0, ??) ? "rear" (u=1, ??)

    Returns:
        (n_profile, 3) ??????????? (??->??->??)
    """
    cps = np.asarray(body_surf["control_points"])
    if end == "front":
        return cps[0, :, :].copy()
    elif end == "rear":
        return cps[-1, :, :].copy()
    else:
        raise ValueError("end must be 'front' or 'rear'")


def build_front_bumper_shared(params, body_surf: dict,
                              n_v: int = 4, bulge: float = 0.08) -> dict:
    """???????? NURBS ?? (G0 ??)?

    v=0 ? = ?? u=0 ????? (??)?
    v=1..n_v-1 ??x ???????y/z ?? v=0 ??

    Args:
        params: CarParams
        body_surf: ?? NURBS ??
        n_v: v ?????? (????)
        bulge: ????? (m)???????

    Returns:
        NURBS dict (n_profile, n_v, 3)
    """
    body_end_cps = extract_body_end_curve(body_surf, "front")
    n_u = body_end_cps.shape[0]
    half_w = params.W / 2
    x_front = -params.L / 2

    cp_grid = np.zeros((n_u, n_v, 3))
    for i in range(n_u):
        pt = body_end_cps[i]
        y, z = pt[1], pt[2]
        y_frac = 1.0 - abs(y) / half_w if half_w > 0 else 0.0

        # v=0: ????? (??)
        cp_grid[i, 0, :] = pt

        # v=1..n_v-1: x ????
        for j in range(1, n_v):
            t = j / (n_v - 1)
            # ????v=0 ? 0?v=n_v-1 ? bulge*y_frac
            b = bulge * y_frac * t
            cp_grid[i, j, 0] = x_front - b  # ???? (x ??)
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z

    deg_u = min(3, n_u - 1)
    deg_v = min(3, n_v - 1)
    return nurbs_surface_from_grid(cp_grid, degree_u=deg_u, degree_v=deg_v)


def build_rear_bumper_shared(params, body_surf: dict,
                             n_v: int = 4, bulge: float = 0.06) -> dict:
    """???????? NURBS ?? (G0 ??)?

    v=0 ? = ?? u=1 ????? (??)?
    v=1..n_v-1 ??x ???????
    """
    body_end_cps = extract_body_end_curve(body_surf, "rear")
    n_u = body_end_cps.shape[0]
    half_w = params.W / 2
    x_rear = params.L / 2

    cp_grid = np.zeros((n_u, n_v, 3))
    for i in range(n_u):
        pt = body_end_cps[i]
        y, z = pt[1], pt[2]
        y_frac = 1.0 - abs(y) / half_w if half_w > 0 else 0.0

        cp_grid[i, 0, :] = pt

        for j in range(1, n_v):
            t = j / (n_v - 1)
            b = bulge * y_frac * t
            cp_grid[i, j, 0] = x_rear + b  # ???? (x ??)
            cp_grid[i, j, 1] = y
            cp_grid[i, j, 2] = z

    deg_u = min(3, n_u - 1)
    deg_v = min(3, n_v - 1)
    return nurbs_surface_from_grid(cp_grid, degree_u=deg_u, degree_v=deg_v)


def validate_g0_continuity(body_surf: dict, bumper_surf: dict,
                           end: str = "front", n_samples: int = 50) -> dict:
    """?? G0 ???????? vs ??? v=0 ???

    ??????? + clamped ?????????? = 0?
    ????????????

    Args:
        body_surf: ?? NURBS ??
        bumper_surf: ??? NURBS ??
        end: "front" (?? u=0) ? "rear" (?? u=1)
        n_samples: ????

    Returns:
        dict: max_gap_mm, mean_gap_mm, samples
    """
    u_body = 0.0 if end == "front" else 1.0
    v_bumper = 0.0  # ??? v=0 ? = ????

    gaps = []
    for t in np.linspace(0.0, 1.0, n_samples):
        pt_body = evaluate_surface(body_surf, u_body, t)
        pt_bumper = evaluate_surface(bumper_surf, t, v_bumper)
        gap = float(np.linalg.norm(pt_body - pt_bumper))
        gaps.append(gap)

    gaps = np.array(gaps)
    return {
        "end": end,
        "n_samples": n_samples,
        "max_gap_mm": float(gaps.max()) * 1000.0,
        "mean_gap_mm": float(gaps.mean()) * 1000.0,
        "g0_pass": bool(gaps.max() < 1e-6),  # < 1nm ???? G0
    }


__all__ = [
    "extract_body_end_curve",
    "build_front_bumper_shared",
    "build_rear_bumper_shared",
    "validate_g0_continuity",
]

