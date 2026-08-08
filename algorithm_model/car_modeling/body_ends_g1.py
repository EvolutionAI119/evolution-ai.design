"""
body_ends_g1 ? G1 ??????? NURBS ??

G1 ???????????????????

?????
  ??? u=0 ??: n_body = dS_body/du x dS_body/dv
  ???? v=0 ??: n_bumper = dS_bumper/du x dS_bumper/dv
  ????: dS_body/dv = dS_bumper/du (??????????)
  ? T = dS_body/dv = dS_bumper/du

  n_body = dS_body/du x T
  n_bumper = T x dS_bumper/dv

  G1 ?? n_bumper k* n_body:
    T x dS_bumper/dv = k * (dS_body/du x T) = -k * (T x dS_body/du)
    T x (dS_bumper/dv + k * dS_body/du) = 0
  ???: dS_bumper/dv = -k * dS_body/du  (???)

???v=1 ???? = body_u0 - k * (body_u1 - body_u0)
  ????: k > 0, ???? = -dS_body/du (????)
  ????: k > 0, ???? = +dS_body/du (????, ? body[-1]-body[-2])
"""
import numpy as np
from typing import Tuple

from ..freeform.nurbs_core import nurbs_surface_from_grid, evaluate_surface


def _surface_normal_fd(surf, u, v, h=1e-4):
    """??????????? (????????)?"""
    hu = hv = max(h, 1e-5)
    if u - hu < 0.0:
        su = (evaluate_surface(surf, u + hu, v) - evaluate_surface(surf, u, v)) / hu
    elif u + hu > 1.0:
        su = (evaluate_surface(surf, u, v) - evaluate_surface(surf, u - hu, v)) / hu
    else:
        su = (evaluate_surface(surf, u + hu, v) - evaluate_surface(surf, u - hu, v)) / (2 * hu)
    if v - hv < 0.0:
        sv = (evaluate_surface(surf, u, v + hv) - evaluate_surface(surf, u, v)) / hv
    elif v + hv > 1.0:
        sv = (evaluate_surface(surf, u, v) - evaluate_surface(surf, u, v - hv)) / hv
    else:
        sv = (evaluate_surface(surf, u, v + hv) - evaluate_surface(surf, u, v - hv)) / (2 * hv)
    n = np.cross(su, sv)
    norm = np.linalg.norm(n)
    if norm < 1e-12:
        return np.array([0.0, 0.0, 1.0])
    return n / norm


def build_front_bumper_g1(params, body_surf, n_v=4, g1_k=0.3, bulge=0.08):
    """G1 ?????????

    v=0 ?: ?? u=0 ?? (??, G0)
    v=1 ?: body_u0 - g1_k * (body_u1 - body_u0) (G1 ??, ??????)
    v=2..n_v-1: ????

    Args:
        g1_k: G1 ????, ?? v=1 ??????
        bulge: v=n_v-1 ?????? (m)
    """
    body_cps = np.asarray(body_surf["control_points"])
    body_u0 = body_cps[0, :, :].copy()   # (n_profile, 3) ????
    body_u1 = body_cps[1, :, :].copy()   # ???? u ?????

    n_u = body_u0.shape[0]
    half_w = params.W / 2
    cp_grid = np.zeros((n_u, n_v, 3))

    for i in range(n_u):
        pt = body_u0[i]
        tangent = body_u1[i] - body_u0[i]  # dS_body/du ??
        y_frac = 1.0 - abs(pt[1]) / half_w if half_w > 0 else 0.0

        # v=0: ???? (G0)
        cp_grid[i, 0, :] = pt

        # v=1: G1 ?? - ??????
        cp_grid[i, 1, :] = pt - g1_k * tangent

        # v=2..n_v-1: ???? (? G1 ?????? x ??)
        for j in range(2, n_v):
            t = (j - 1) / max(n_v - 2, 1)  # 0..1
            # ? G1 ??????????
            g1_component = (1 - t) * (-g1_k * tangent)
            bulge_component = t * np.array([-bulge * y_frac, 0, 0])
            cp_grid[i, j, :] = pt + g1_component + bulge_component

    deg_u = min(3, n_u - 1)
    deg_v = min(3, n_v - 1)
    return nurbs_surface_from_grid(cp_grid, degree_u=deg_u, degree_v=deg_v)


def build_rear_bumper_g1(params, body_surf, n_v=4, g1_k=0.3, bulge=0.06):
    """G1 ?????????

    v=0 ?: ?? u=1 ?? (??, G0)
    v=1 ?: body_uN + g1_k * (body_uN - body_uN-1) (G1 ??, ?????)
    """
    body_cps = np.asarray(body_surf["control_points"])
    body_uN = body_cps[-1, :, :].copy()   # u=1 ??
    body_uN1 = body_cps[-2, :, :].copy()  # u=N-1 ?

    n_u = body_uN.shape[0]
    half_w = params.W / 2
    cp_grid = np.zeros((n_u, n_v, 3))

    for i in range(n_u):
        pt = body_uN[i]
        tangent = body_uN[i] - body_uN1[i]  # dS_body/du ? u=1 ? (???? x+)
        y_frac = 1.0 - abs(pt[1]) / half_w if half_w > 0 else 0.0

        # v=0: ???? (G0)
        cp_grid[i, 0, :] = pt

        # v=1: G1 ?? - ????? (?????? = x+, ? dS/du ??)
        cp_grid[i, 1, :] = pt + g1_k * tangent

        # v=2..n_v-1: ????
        for j in range(2, n_v):
            t = (j - 1) / max(n_v - 2, 1)
            g1_component = (1 - t) * (g1_k * tangent)
            bulge_component = t * np.array([bulge * y_frac, 0, 0])
            cp_grid[i, j, :] = pt + g1_component + bulge_component

    deg_u = min(3, n_u - 1)
    deg_v = min(3, n_v - 1)
    return nurbs_surface_from_grid(cp_grid, degree_u=deg_u, degree_v=deg_v)


def validate_g1_continuity(body_surf, bumper_surf, end="front", n_samples=50):
    """?? G1 ???: ?????????

    G1 ??: max_angle < 1 deg
    ????: max_angle < 5 deg
    """
    u_body = 0.0 if end == "front" else 1.0
    v_bumper = 0.0

    angles = []
    for t in np.linspace(0.02, 0.98, n_samples):
        n_body = _surface_normal_fd(body_surf, u_body, t)
        n_bumper = _surface_normal_fd(bumper_surf, t, v_bumper)
        cos_a = float(np.clip(np.dot(n_body, n_bumper), -1.0, 1.0))
        ang = float(np.degrees(np.arccos(cos_a)))
        if ang > 90.0:
            ang = 180.0 - ang
        angles.append(ang)

    angles = np.array(angles)
    return {
        "end": end,
        "n_samples": n_samples,
        "max_angle_deg": float(angles.max()),
        "mean_angle_deg": float(angles.mean()),
        "g1_pass": bool(angles.max() < 1.0),
        "visual_smooth": bool(angles.max() < 5.0),
    }


__all__ = [
    "build_front_bumper_g1",
    "build_rear_bumper_g1",
    "validate_g1_continuity",
]

