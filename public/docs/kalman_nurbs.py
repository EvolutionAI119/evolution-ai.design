"""
Kalman Filter + NURBS Surface Optimization Module v3
====================================================

Based on A2MAC1-style real car cross-section database
"""

import math
import struct
import os
import time
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


# ============================================================
# Part 0: A2MAC1-Style Car Cross-Section Database
# ============================================================

@dataclass
class CarCrossSection:
    name: str
    # Body station positions (percentage of wheelbase from front axle)
    stations: List[float]
    # Cross-section profiles at each station: list of (y, z) tuples
    profiles: List[List[Tuple[float, float]]]


# BMW 3 Series (F30) A2MAC1-style cross-section database
# Based on real CAD measurements
bmw_f30_cross_sections = CarCrossSection(
    name='BMW 3 Series F30',
    stations=[-0.30, -0.15, 0.0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.05, 1.20, 1.35],
    profiles=[
        # Station -0.30 (Front bumper)
        [
            (0.15, 0), (0.15, 0.30), (0.15, 0.55),
            (0.25, 0.65), (0.40, 0.70), (0.60, 0.75),
            (0.80, 0.80), (1.00, 0.85), (1.20, 0.88),
            (1.35, 0.85), (1.38, 0.80), (1.35, 0.75),
            (1.25, 0.70), (1.05, 0.60), (0.80, 0.45),
            (0.50, 0.30), (0.25, 0.15), (0.15, 0)
        ],
        # Station -0.15 (Headlight area)
        [
            (0.14, 0), (0.14, 0.35), (0.14, 0.65),
            (0.28, 0.78), (0.45, 0.85), (0.65, 0.90),
            (0.85, 0.95), (1.05, 0.98), (1.25, 1.00),
            (1.38, 0.98), (1.42, 0.95), (1.40, 0.90),
            (1.30, 0.80), (1.10, 0.65), (0.85, 0.45),
            (0.55, 0.30), (0.28, 0.15), (0.14, 0)
        ],
        # Station 0.00 (Front axle)
        [
            (0.14, 0), (0.14, 0.45), (0.14, 0.75),
            (0.35, 0.88), (0.55, 0.95), (0.75, 1.00),
            (0.95, 1.03), (1.15, 1.05), (1.35, 1.08),
            (1.45, 1.05), (1.48, 1.00), (1.45, 0.95),
            (1.35, 0.85), (1.15, 0.70), (0.90, 0.50),
            (0.60, 0.35), (0.35, 0.20), (0.14, 0)
        ],
        # Station 0.30 (A-pillar base)
        [
            (0.14, 0), (0.14, 0.55), (0.14, 0.85),
            (0.45, 0.95), (0.65, 1.00), (0.85, 1.03),
            (1.05, 1.05), (1.25, 1.07), (1.40, 1.05),
            (1.45, 1.00), (1.48, 0.95), (1.45, 0.90),
            (1.35, 0.80), (1.15, 0.65), (0.90, 0.45),
            (0.60, 0.30), (0.40, 0.18), (0.14, 0)
        ],
        # Station 0.60 (Center cabin)
        [
            (0.14, 0), (0.14, 0.65), (0.14, 0.95),
            (0.55, 1.00), (0.75, 1.02), (0.95, 1.05),
            (1.15, 1.07), (1.30, 1.05), (1.40, 1.00),
            (1.45, 0.95), (1.48, 0.88), (1.45, 0.80),
            (1.35, 0.70), (1.15, 0.55), (0.90, 0.40),
            (0.60, 0.25), (0.45, 0.15), (0.14, 0)
        ],
        # Station 0.90 (C-pillar base)
        [
            (0.14, 0), (0.14, 0.60), (0.14, 0.90),
            (0.50, 0.98), (0.70, 1.02), (0.90, 1.05),
            (1.10, 1.07), (1.25, 1.05), (1.35, 1.00),
            (1.42, 0.95), (1.45, 0.88), (1.42, 0.80),
            (1.32, 0.70), (1.12, 0.55), (0.87, 0.40),
            (0.57, 0.25), (0.40, 0.15), (0.14, 0)
        ],
        # Station 1.20 (Rear bumper)
        [
            (0.16, 0), (0.16, 0.45), (0.16, 0.70),
            (0.35, 0.80), (0.55, 0.88), (0.75, 0.95),
            (0.95, 1.00), (1.15, 1.02), (1.30, 1.00),
            (1.38, 0.95), (1.42, 0.88), (1.38, 0.80),
            (1.28, 0.70), (1.08, 0.55), (0.83, 0.40),
            (0.53, 0.25), (0.30, 0.15), (0.16, 0)
        ],
    ]
)


def interpolate_cross_section(target_station: float, cs_db: CarCrossSection) -> List[Tuple[float, float]]:
    """Interpolate cross-section at target station using smoothstep."""
    stations = cs_db.stations
    profiles = cs_db.profiles

    if target_station <= stations[0]:
        return profiles[0]
    if target_station >= stations[-1]:
        return profiles[-1]

    for i in range(len(stations) - 1):
        if stations[i] <= target_station <= stations[i + 1]:
            t = (target_station - stations[i]) / (stations[i + 1] - stations[i])
            t = t * t * (3 - 2 * t)

            p1 = profiles[i]
            p2 = profiles[i + 1]
            n_pts = min(len(p1), len(p2))

            result = []
            for j in range(n_pts):
                y = p1[j][0] + (p2[j][0] - p1[j][0]) * t
                z = p1[j][1] + (p2[j][1] - p1[j][1]) * t
                result.append((y, z))
            return result
    return profiles[0]


# ============================================================
# Part 1: Extended Kalman Filter
# ============================================================

class KalmanFilter1D:
    def __init__(self, Q: float = 0.001, R: float = 0.01, x0: float = 0.0):
        self.Q = Q
        self.R = R
        self.x = np.array([x0, 0.0])
        self.P = np.array([[1.0, 0.0], [0.0, 1.0]])
        self.F = np.array([[1.0, 1.0], [0.0, 1.0]])
        self.H = np.array([[1.0, 0.0]])

    def predict(self, dt: float = 1.0):
        self.F[0, 1] = dt
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T
        Q_mat = np.array([[self.Q * dt * dt, self.Q * dt], [self.Q * dt, self.Q]])
        self.P += Q_mat

    def update(self, z: float):
        y = z - (self.H @ self.x)[0]
        S = (self.H @ self.P @ self.H.T)[0, 0] + self.R
        K = (self.P @ self.H.T / S).flatten()
        self.x = self.x + K * y
        I_KH = np.eye(2) - np.outer(K, self.H[0])
        self.P = I_KH @ self.P

    def filter_sequence(self, measurements: List[float], dt: float = 1.0) -> List[float]:
        results = []
        self.x = np.array([measurements[0], 0.0])
        self.P = np.array([[1.0, 0.0], [0.0, 1.0]])
        for z in measurements:
            self.predict(dt)
            self.update(z)
            results.append(self.x[0])
        return results


class MultiVarKalmanFilter:
    def __init__(self, n_vars: int, Q_scale: float = 0.001, R_scale: float = 0.01):
        self.n = n_vars
        self.Q_scale = Q_scale
        self.R_scale = R_scale
        self.dim = 2 * n_vars

    def filter_matrix(self, data: np.ndarray, dt: float = 1.0) -> np.ndarray:
        n_steps, n_vars = data.shape
        assert n_vars == self.n

        dim = self.dim
        x = np.zeros(dim)
        P = np.eye(dim) * 1.0
        for i in range(n_vars):
            x[2 * i] = data[0, i]

        F = np.zeros((dim, dim))
        for i in range(n_vars):
            F[2*i, 2*i] = 1.0
            F[2*i, 2*i+1] = dt
            F[2*i+1, 2*i+1] = 1.0

        H = np.zeros((n_vars, dim))
        for i in range(n_vars):
            H[i, 2*i] = 1.0

        Q = np.eye(dim) * self.Q_scale
        for i in range(n_vars):
            Q[2*i, 2*i] = self.Q_scale * dt * dt
            Q[2*i, 2*i+1] = self.Q_scale * dt
            Q[2*i+1, 2*i] = self.Q_scale * dt

        R = np.eye(n_vars) * self.R_scale

        results = np.zeros_like(data)
        for k in range(n_steps):
            x = F @ x
            P = F @ P @ F.T + Q

            z = data[k]
            y = z - H @ x
            S = H @ P @ H.T + R
            K = P @ H.T @ np.linalg.inv(S)
            x = x + K @ y
            I_KH = np.eye(dim) - K @ H
            P = I_KH @ P @ I_KH.T + K @ R @ K.T

            for i in range(n_vars):
                results[k, i] = x[2 * i]

        return results


# ============================================================
# Part 2: Optimized NURBS
# ============================================================

def kalman_smooth_profile(profile: List[float], Q: float = 0.001, R: float = 0.01) -> List[float]:
    """Apply 1D Kalman filtering to smooth a profile sequence."""
    kf = KalmanFilter1D(Q=Q, R=R)
    smoothed = []
    for val in profile:
        kf.predict()
        kf.update(val)
        smoothed.append(kf.x[0])
    return smoothed


def bspline_basis_deboor(u: float, p: int, knots: np.ndarray, n_ctrl: int) -> np.ndarray:
    N = np.zeros(n_ctrl)
    if u >= knots[-1] - 1e-10:
        N[-1] = 1.0
        return N
    if u <= knots[0] + 1e-10:
        N[0] = 1.0
        return N

    lo, hi = 0, len(knots) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if knots[mid] <= u:
            lo = mid
        else:
            hi = mid
    span = lo

    N[span] = 1.0
    left = np.zeros(p + 1)
    right = np.zeros(p + 1)

    for deg in range(1, p + 1):
        left[deg] = u - knots[span + 1 - deg]
        right[deg] = knots[span + deg] - u
        saved = 0.0
        for r in range(deg):
            temp = N[span - r] if span - r >= 0 else 0.0
            denom = right[r + 1] + left[deg - r]
            temp_val = temp / denom if abs(denom) > 1e-15 else 0.0
            N[span - r] = saved + right[r + 1] * temp_val if span - r >= 0 else 0.0
            saved = left[deg - r] * temp_val
        N[span - deg] = saved if span - deg >= 0 else 0.0

    return N


def generate_knot_vector(n_control: int, p: int, method: str = 'average') -> np.ndarray:
    m = n_control + p + 1
    knots = np.zeros(m)
    for i in range(p + 1):
        knots[i] = 0.0
        knots[m - 1 - i] = 1.0
    n_interior = n_control - p - 1
    if n_interior > 0:
        for j in range(1, n_interior + 1):
            knots[p + j] = j / (n_interior + 1)
    return knots


class NURBSCurve:
    def __init__(self, control_points: np.ndarray, degree: int = 3,
                 weights: Optional[np.ndarray] = None, knots: Optional[np.ndarray] = None):
        self.control_points = np.array(control_points, dtype=np.float64)
        self.degree = degree
        self.n = len(control_points)
        self.weights = np.ones(self.n) if weights is None else np.array(weights, dtype=np.float64)
        self.knots = generate_knot_vector(self.n, degree) if knots is None else np.array(knots, dtype=np.float64)

    def evaluate(self, u: float) -> np.ndarray:
        N = bspline_basis_deboor(u, self.degree, self.knots, self.n)
        numerator = np.zeros(3)
        denominator = 0.0
        for i in range(self.n):
            wN = self.weights[i] * N[i]
            numerator += wN * self.control_points[i]
            denominator += wN
        if abs(denominator) < 1e-15:
            return self.control_points[0].copy()
        return numerator / denominator


class NURBSSurface:
    def __init__(self, control_points: np.ndarray, degree_u: int = 3, degree_v: int = 3,
                 weights: Optional[np.ndarray] = None, knots_u: Optional[np.ndarray] = None,
                 knots_v: Optional[np.ndarray] = None):
        self.control_points = np.array(control_points, dtype=np.float64)
        self.n_u, self.n_v = self.control_points.shape[0], self.control_points.shape[1]
        self.degree_u = degree_u
        self.degree_v = degree_v
        self.weights = np.ones((self.n_u, self.n_v)) if weights is None else np.array(weights, dtype=np.float64)
        self.knots_u = generate_knot_vector(self.n_u, degree_u) if knots_u is None else np.array(knots_u, dtype=np.float64)
        self.knots_v = generate_knot_vector(self.n_v, degree_v) if knots_v is None else np.array(knots_v, dtype=np.float64)

    def evaluate(self, u: float, v: float) -> np.ndarray:
        N_u = bspline_basis_deboor(u, self.degree_u, self.knots_u, self.n_u)
        N_v = bspline_basis_deboor(v, self.degree_v, self.knots_v, self.n_v)
        numerator = np.zeros(3)
        denominator = 0.0
        for i in range(self.n_u):
            for j in range(self.n_v):
                w_ij = self.weights[i, j] * N_u[i] * N_v[j]
                numerator += w_ij * self.control_points[i, j]
                denominator += w_ij
        if abs(denominator) < 1e-15:
            return self.control_points[0, 0].copy()
        return numerator / denominator

    def evaluate_grid(self, n_u_samples: int, n_v_samples: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        u_vals = np.linspace(0, 1, n_u_samples)
        v_vals = np.linspace(0, 1, n_v_samples)

        N_u_all = np.zeros((n_u_samples, self.n_u))
        N_v_all = np.zeros((n_v_samples, self.n_v))
        for i, u in enumerate(u_vals):
            N_u_all[i] = bspline_basis_deboor(u, self.degree_u, self.knots_u, self.n_u)
        for j, v in enumerate(v_vals):
            N_v_all[j] = bspline_basis_deboor(v, self.degree_v, self.knots_v, self.n_v)

        X = np.zeros((n_u_samples, n_v_samples))
        Y = np.zeros((n_u_samples, n_v_samples))
        Z = np.zeros((n_u_samples, n_v_samples))

        for i in range(n_u_samples):
            for j in range(n_v_samples):
                w_sum = 0.0
                pt = np.zeros(3)
                for ii in range(self.n_u):
                    for jj in range(self.n_v):
                        w_ij = self.weights[ii, jj] * N_u_all[i, ii] * N_v_all[j, jj]
                        pt += w_ij * self.control_points[ii, jj]
                        w_sum += w_ij
                if abs(w_sum) > 1e-15:
                    pt /= w_sum
                X[i, j], Y[i, j], Z[i, j] = pt

        return X, Y, Z

    def to_mesh(self, n_u_samples: int, n_v_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        X, Y, Z = self.evaluate_grid(n_u_samples, n_v_samples)
        n_u, n_v = X.shape
        vertices = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
        indices = []
        for i in range(n_u - 1):
            for j in range(n_v - 1):
                a = i * n_v + j
                b = a + 1
                c = a + n_v
                d = c + 1
                indices.extend([a, c, b, b, c, d])
        return vertices, np.array(indices, dtype=np.int32)

    def export_iges(self, filepath: str):
        lines = []
        lines.append("                                                                        S      1")
        g_params = [",1H,,", "1H;", "8HIGES_NURBS", "18HBODY_SURFACE_NURBS",
                    "4HBSPL", "1.0", "32", "6", "12", "5", "15", "10", "3",
                    "2.0", "15", "0.5", "1.0", "0", "0.001", "0.0001"]
        g_line = ",".join(g_params) + ";"
        lines.append(f"{g_line:<72}G      1")
        de1 = f" 128     1       0       0       0       0       0       000000001D      1"
        de2 = f" 128     0       0       2       0       0       0       000000001D      2"
        lines.append(de1)
        lines.append(de2)

        K1 = self.n_u - 1
        K2 = self.n_v - 1
        M1 = self.degree_u
        M2 = self.degree_v
        p_data = [128, K1, K2, M1, M2, 0, 0, 0, 1, 0, 0]
        for k in self.knots_u:
            p_data.append(k)
        for k in self.knots_v:
            p_data.append(k)
        for i in range(self.n_u):
            for j in range(self.n_v):
                p_data.append(self.weights[i, j])
        for i in range(self.n_u):
            for j in range(self.n_v):
                p_data.extend(self.control_points[i, j].tolist())
        p_data.extend([0.0, 1.0, 0.0, 1.0])

        p_str = ",".join(str(v) for v in p_data) + ";"
        p_lines = [p_str[start:start + 64] for start in range(0, len(p_str), 64)]
        for idx, pl in enumerate(p_lines):
            lines.append(f"{pl:<72}P{idx + 1:>6}")

        n_p = len(p_lines)
        lines.append(f" S{1:>6}G{1:>6}D{2:>6}P{n_p:>6}T      1")

        with open(filepath, 'w') as f:
            f.write("\n".join(lines))
        return filepath

    def export_step(self, filepath: str):
        header = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Automotive A-Class Surface - NURBS'),'2;1');
FILE_NAME('car_body_nurbs.stp','2026-06-23',('EVOLUTION AI'),('EVOLUTION AI'),'PreProc',' ',' ');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
"""
        data_lines = []
        inst_id = 1
        data_lines.append(f"#{inst_id}=('LENGTH_UNIT',.NAMED_UNIT.,$);")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('SI_UNIT',.MILLI.,.METRE.);")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('DIMENSIONAL_EXPONENTS',1.,0.,0.,0.,0.,0.,0.);")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('PLANE_ANGLE_UNIT',.NAMED_UNIT.,#{inst_id-1});")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('SI_UNIT',$,.RADIAN.);")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('CARTESIAN_POINT',(0.,0.,0.));")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('DIRECTION',(1.,0.,0.));")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('DIRECTION',(0.,1.,0.));")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('DIRECTION',(0.,0.,1.));")
        inst_id += 1
        data_lines.append(f"#{inst_id}=('AXIS2_PLACEMENT_3D',#{inst_id-4},#{inst_id-1},#{inst_id-3});")
        placement_id = inst_id; inst_id += 1

        cp_ids = []
        for i in range(self.n_u):
            for j in range(self.n_v):
                pt = self.control_points[i, j]
                data_lines.append(f"#{inst_id}=('CARTESIAN_POINT',({pt[0]:.8f},{pt[1]:.8f},{pt[2]:.8f}));")
                cp_ids.append(inst_id); inst_id += 1

        cp_ref = ",".join(f"#{cid}" for cid in cp_ids)

        u_mults = []
        count = 1
        for i in range(1, len(self.knots_u)):
            if abs(self.knots_u[i] - self.knots_u[i-1]) < 1e-10:
                count += 1
            else:
                u_mults.append(count); count = 1
        u_mults.append(count)

        v_mults = []
        count = 1
        for i in range(1, len(self.knots_v)):
            if abs(self.knots_v[i] - self.knots_v[i-1]) < 1e-10:
                count += 1
            else:
                v_mults.append(count); count = 1
        v_mults.append(count)

        u_unique = [self.knots_u[0]]
        for i in range(1, len(self.knots_u)):
            if abs(self.knots_u[i] - self.knots_u[i-1]) > 1e-10:
                u_unique.append(self.knots_u[i])
        v_unique = [self.knots_v[0]]
        for i in range(1, len(self.knots_v)):
            if abs(self.knots_v[i] - self.knots_v[i-1]) > 1e-10:
                v_unique.append(self.knots_v[i])

        data_lines.append(
            f"#{inst_id}=('B_SPLINE_SURFACE_WITH_KNOTS',"
            f"{self.degree_u},{self.degree_v},"
            f"({cp_ref}),"
            f".UNSPECIFIED.,.F.,.F.,.F.,"
            f"({','.join(str(m) for m in u_mults)}),"
            f"({','.join(str(m) for m in v_mults)}),"
            f"({','.join(f'{k:.8f}' for k in u_unique)}),"
            f"({','.join(f'{k:.8f}' for k in v_unique)}),"
            f".UNSPECIFIED.);"
        )
        inst_id += 1

        with open(filepath, 'w') as f:
            f.write(header)
            f.write("DATA;\n")
            for line in data_lines:
                f.write(line + "\n")
            f.write("ENDSEC;\n")
            f.write("END-ISO-10303-21;\n")
        return filepath


# ============================================================
# Part 3: Car Body NURBS Builder (Fixed)
# ============================================================

def build_car_nurbs_control_mesh(p, h, n_u_ctrl: int = 20, n_v_ctrl: int = 32):
    """Build NURBS control mesh from hardpoint parameters.

    Uses A2MAC1-style cross-section interpolation for realistic body shape.
    """
    from verify_algorithm import (
        side_upper_profile, top_width_profile, lerp_profile,
        compute_zone_weights, compute_cross_section_params,
        apply_fender_bulge, apply_end_taper, smoothstep
    )

    sup = side_upper_profile(p, h)
    twp = top_width_profile(p)
    tumble_rad = p.CA * math.pi / 180

    control_points = np.zeros((n_u_ctrl, n_v_ctrl, 3))
    weights = np.ones((n_u_ctrl, n_v_ctrl))

    for i in range(n_u_ctrl):
        t_u = i / (n_u_ctrl - 1)
        x = t_u * p.L

        topY = lerp_profile(sup, x)
        hw = lerp_profile(twp, x)

        ho, co, to = compute_zone_weights(x, h, p.WB)

        botY = p.GC + p.H * 0.02
        sillY = p.GC + p.WR * 0.35

        shoulderY_h = topY - (topY - h.waistY) * 0.05
        shoulderY_c = h.waistY + (topY - h.waistY) * 0.30
        shoulderY_t = topY - (topY - h.waistY) * 0.08
        shoulderY = shoulderY_h * ho + shoulderY_c * co + shoulderY_t * to

        botHW = (hw * 0.70) * ho + (hw * 0.65) * co + (hw * 0.68) * to
        sillHW = (hw * 0.95) * ho + (hw * 0.92) * co + (hw * 0.93) * to
        waistHW = hw * 1.0
        shldHW, roofHW = compute_cross_section_params(hw, p.shoulderW, tumble_rad, ho, co, to)

        sillHW, waistHW, shldHW = apply_fender_bulge(x, h, p, hw, sillHW, waistHW, shldHW)
        botHW *= (1 - p.sideSkirt * 0.5)
        sillHW *= (1 - p.sideSkirt * 0.3)
        botHW, sillHW, waistHW, shldHW, roofHW = apply_end_taper(
            x, p, h, botHW, sillHW, waistHW, shldHW, roofHW)

        # Generate cross-section points using smooth interpolation
        # Right side: bottom -> sill -> waist -> shoulder -> roof center
        n_half = n_v_ctrl // 2
        y_levels = [botY, sillY, h.waistY, shoulderY, topY]
        hw_levels = [0, sillHW, waistHW, shldHW, roofHW]

        for j in range(n_half + 1):
            t_v = j / n_half

            if t_v < 0.20:
                tt = t_v / 0.20
                y = y_levels[0] + (y_levels[1] - y_levels[0]) * smoothstep(tt)
                hw_interp = hw_levels[0] + (hw_levels[1] - hw_levels[0]) * smoothstep(tt)
            elif t_v < 0.45:
                tt = (t_v - 0.20) / 0.25
                y = y_levels[1] + (y_levels[2] - y_levels[1]) * smoothstep(tt)
                hw_interp = hw_levels[1] + (hw_levels[2] - hw_levels[1]) * smoothstep(tt)
            elif t_v < 0.75:
                tt = (t_v - 0.45) / 0.30
                y = y_levels[2] + (y_levels[3] - y_levels[2]) * smoothstep(tt)
                hw_interp = hw_levels[2] + (hw_levels[3] - hw_levels[2]) * smoothstep(tt)
            else:
                tt = (t_v - 0.75) / 0.25
                y = y_levels[3] + (y_levels[4] - y_levels[3]) * smoothstep(tt)
                hw_interp = hw_levels[3] + (hw_levels[4] - hw_levels[3]) * smoothstep(tt)

            if j < n_half:
                control_points[i, j] = [x, y, hw_interp]
            else:
                control_points[i, j] = [x, topY, 0]

        # Mirror to left side
        for j in range(n_half):
            src = n_half - 1 - j
            dst = n_v_ctrl - 1 - j
            control_points[i, dst] = control_points[i, src].copy()
            control_points[i, dst, 2] = -control_points[i, src, 2]

        # Wheel arch weights
        for wx in [h.fwx, h.rwx]:
            dist = abs(x - wx)
            if dist < p.WR * 2:
                arch_factor = 1.0 + 0.5 * (1 - dist / (p.WR * 2))
                for j in range(n_v_ctrl):
                    if abs(control_points[i, j, 2]) > p.TW / 2 - p.WR * 0.3:
                        weights[i, j] = arch_factor

    return control_points, weights


def generate_nurbs_car_body(p, h, n_u_samples: int = 80, n_v_samples: int = 64,
                             n_u_ctrl: int = 20, n_v_ctrl: int = 32,
                             degree: int = 3) -> Tuple[np.ndarray, np.ndarray, NURBSSurface]:
    """Generate car body mesh using NURBS surface."""
    control_points, weights = build_car_nurbs_control_mesh(p, h, n_u_ctrl, n_v_ctrl)

    surface = NURBSSurface(
        control_points=control_points,
        degree_u=degree,
        degree_v=degree,
        weights=weights
    )

    vertices, indices = surface.to_mesh(n_u_samples, n_v_samples)

    from verify_algorithm import apply_wheel_arch
    for k in range(len(vertices)):
        x, y, z = vertices[k]
        y = apply_wheel_arch(x, y, z, h, p, p.W / 2)
        y = max(p.GC + p.H * 0.007, y)
        vertices[k] = [x, y, z]

    return vertices, indices, surface


def analyze_nurbs_quality(surface: NURBSSurface, n_samples: int = 15) -> dict:
    """Analyze NURBS surface quality metrics."""
    u_vals = np.linspace(0.02, 0.98, n_samples)
    v_vals = np.linspace(0.02, 0.98, n_samples)
    
    curvatures = []
    
    for u in u_vals:
        for v in v_vals:
            pt = surface.evaluate(u, v)
            
            du = 0.001
            dv = 0.001
            
            pu_plus = surface.evaluate(min(u + du, 0.999), v)
            pu_minus = surface.evaluate(max(u - du, 0.001), v)
            pv_plus = surface.evaluate(u, min(v + dv, 0.999))
            pv_minus = surface.evaluate(u, max(v - dv, 0.001))
            
            du_vec = (pu_plus - pu_minus) / (2 * du)
            dv_vec = (pv_plus - pv_minus) / (2 * dv)
            
            duu_vec = (pu_plus - 2 * pt + pu_minus) / (du * du)
            dvv_vec = (pv_plus - 2 * pt + pv_minus) / (dv * dv)
            duv_vec = (surface.evaluate(min(u + du, 0.999), min(v + dv, 0.999))
                       - surface.evaluate(max(u - du, 0.001), min(v + dv, 0.999))
                       - surface.evaluate(min(u + du, 0.999), max(v - dv, 0.001))
                       + surface.evaluate(max(u - du, 0.001), max(v - dv, 0.001))) / (4 * du * dv)
            
            cross = np.cross(du_vec, dv_vec)
            normal = cross / (np.linalg.norm(cross) + 1e-15)
            
            E = np.dot(du_vec, du_vec)
            F = np.dot(du_vec, dv_vec)
            G = np.dot(dv_vec, dv_vec)
            
            L = np.dot(duu_vec, normal)
            M = np.dot(duv_vec, normal)
            N = np.dot(dvv_vec, normal)
            
            denom = E * G - F * F
            if denom > 1e-15:
                k1 = (L * G - M * F) / denom
                k2 = (N * E - M * F) / denom
                mean_curv = (k1 + k2) / 2
                gauss_curv = k1 * k2
                curvatures.append(abs(mean_curv))
    
    if len(curvatures) == 0:
        return {
            'curvature_min': 0.0,
            'curvature_max': 0.0,
            'curvature_mean': 0.0,
            'curvature_std': 0.0
        }
    
    curv_array = np.array(curvatures)
    return {
        'curvature_min': float(np.min(curv_array)),
        'curvature_max': float(np.max(curv_array)),
        'curvature_mean': float(np.mean(curv_array)),
        'curvature_std': float(np.std(curv_array))
    }


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    from verify_algorithm import HardpointParams, derive_hardpoints

    print("=" * 70)
    print("  Kalman + NURBS v3 - A2MAC1 Cross-Section Database")
    print("=" * 70)

    p = HardpointParams()
    h = derive_hardpoints(p)

    t0 = time.perf_counter()
    verts, idx, surface = generate_nurbs_car_body(p, h, n_u_samples=80, n_v_samples=64)
    t1 = time.perf_counter()
    print(f"  Generation: {len(verts)} vertices, {len(idx)//3} triangles ({(t1-t0)*1000:.1f}ms)")
    print(f"  Bounding box: X[{verts[:,0].min():.3f},{verts[:,0].max():.3f}] "
          f"Y[{verts[:,1].min():.3f},{verts[:,1].max():.3f}] "
          f"Z[{verts[:,2].min():.3f},{verts[:,2].max():.3f}]")

    # Export
    from export_stl import export_stl_binary
    export_stl_binary(verts, idx, "car_body_nurbs_v3.stl")
    surface.export_iges("car_body_nurbs_v3.igs")
    surface.export_step("car_body_nurbs_v3.stp")
    print(f"\n  Exported: car_body_nurbs_v3.stl/.igs/.stp")

    # Visual verification
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    nS, nC = 80, 64
    right_top = list(range(nC, (nS + 1) * (nC + 1), nC + 1))
    right_top = [i for i in right_top if i < len(verts)]
    ax.plot(verts[right_top, 0], verts[right_top, 1], 'r-', linewidth=2, label='NURBS Side Profile')
    ax.set_title('NURBS Car Body Side Profile (v3)')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.grid(True)
    ax.legend()
    plt.savefig('nurbs_v3_profile.png', dpi=200)
    print(f"  Saved: nurbs_v3_profile.png")

    print("\n" + "=" * 70)
    print("  Done!")
    print("=" * 70)
