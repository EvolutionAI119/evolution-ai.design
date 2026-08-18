"""
Example 9 ? NURBS ????????? Python??? FreeCAD?

?? full_car_nurbs.step ?? NURBS ?????????
  - G0 (????): ???????????? (mm)
  - G1 (????): ???????????? (?)

???????? ?S/?u, ?S/?v ? ??
???G0?0.1mm ???? / G1?1? ???? / G1?5? ????
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from scipy.spatial import cKDTree

from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import build_body_nurbs
from algorithm_model.car_modeling.body_ends import build_all_ends_nurbs
from algorithm_model.car_modeling.accessories_nurbs import (
    build_all_wheels_nurbs,
    build_all_mirrors_nurbs,
)
from algorithm_model.freeform.nurbs_core import evaluate_surface


def surface_normal(surf, u, v, h=1e-4):
    """????????? (u,v) ?????????????????"""
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


def boundary_curve_points(surf, edge, n=30):
    """???????????edge ? {u0,u1,v0,v1}??? (pts, params)?"""
    pts = np.zeros((n, 3))
    params = np.zeros((n, 2))
    for i, t in enumerate(np.linspace(0.0, 1.0, n)):
        if edge == "u0":
            u, v = 0.0, t
        elif edge == "u1":
            u, v = 1.0, t
        elif edge == "v0":
            u, v = t, 0.0
        elif edge == "v1":
            u, v = t, 1.0
        else:
            raise ValueError("unknown edge: " + edge)
        pts[i] = evaluate_surface(surf, u, v)
        params[i] = [u, v]
    return pts, params


def all_boundary_points(surf, n=30):
    out = {}
    for edge in ["u0", "u1", "v0", "v1"]:
        out[edge] = boundary_curve_points(surf, edge, n)
    return out


def analyze_pair(surf_a, surf_b, name_a, name_b, n_sample=40, g0_threshold=5e-3):
    """????????????? G0/G1 ????

    g0_threshold: ??"??"????? (m)?5mm
    """
    bounds_a = all_boundary_points(surf_a, n_sample)
    bounds_b = all_boundary_points(surf_b, n_sample)

    per_edge = []
    global_min_dists = []
    contact_pairs = []

    for ea, (pts_a, params_a) in bounds_a.items():
        all_b_pts = []
        all_b_params = []
        all_b_edge = []
        for eb, (pts_b, params_b) in bounds_b.items():
            for k in range(len(pts_b)):
                all_b_pts.append(pts_b[k])
                all_b_params.append(params_b[k])
                all_b_edge.append(eb)
        all_b_pts = np.array(all_b_pts)
        tree = cKDTree(all_b_pts)
        dists, idxs = tree.query(pts_a, k=1)

        for i in range(len(pts_a)):
            global_min_dists.append(dists[i])
            if dists[i] < g0_threshold:
                u_a, v_a = params_a[i]
                n_a = surface_normal(surf_a, u_a, v_a)
                j = idxs[i]
                u_b, v_b = all_b_params[j]
                n_b = surface_normal(surf_b, u_b, v_b)
                cos_a = float(np.clip(np.dot(n_a, n_b), -1.0, 1.0))
                ang = float(np.degrees(np.arccos(cos_a)))
                if ang > 90.0:
                    ang = 180.0 - ang
                contact_pairs.append((dists[i], ang, ea, all_b_edge[j]))

        for eb, (pts_b, params_b) in bounds_b.items():
            tree_eb = cKDTree(pts_b)
            d_eb, _ = tree_eb.query(pts_a, k=1)
            per_edge.append({
                "edge_a": ea, "edge_b": eb,
                "min_gap": float(d_eb.min()), "max_gap": float(d_eb.max()),
                "mean_gap": float(d_eb.mean()),
                "contact_count": int((d_eb < g0_threshold).sum()),
            })

    min_gap = float(min(global_min_dists)) if global_min_dists else float("inf")
    best_ep = min(per_edge, key=lambda e: e["min_gap"])
    max_gap = best_ep["max_gap"]
    best_edge_pair = best_ep["edge_a"] + "<->" + best_ep["edge_b"]
    if contact_pairs:
        angs = [p[1] for p in contact_pairs]
        max_ang = float(max(angs))
        mean_ang = float(np.mean(angs))
        ratio = len(contact_pairs) / (4 * n_sample)
    else:
        max_ang = float("nan")
        mean_ang = float("nan")
        ratio = 0.0

    return {
        "pair_name": name_a + " <-> " + name_b,
        "min_gap_m": min_gap, "max_gap_m": max_gap,
        "max_gap_mm": max_gap * 1000.0,
        "max_angle_deg": max_ang, "mean_angle_deg": mean_ang,
        "contact_ratio": ratio, "contact_count": len(contact_pairs),
        "per_edge": per_edge,
        "best_edge_pair": best_edge_pair,
    }


def _fmt(v, fmt_str=".3f"):
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return "N/A"
    return format(v, fmt_str)


def print_report(results, out_path):
    """?????????????"""
    lines = []
    lines.append("=" * 78)
    lines.append("NURBS ?????????")
    lines.append("  ????: full_car_nurbs.step (18 ?? / 14 ??)")
    lines.append("  ??: ? Python (??????? + KDTree ???)")
    lines.append("  ??: G0 <= 0.1mm ???? / G1 <= 1? ???? / G1 <= 5? ????")
    lines.append("=" * 78)

    lines.append("")
    lines.append("[??] ???????? (???????):")
    lines.append("-" * 78)
    lines.append("{:<32} {:>12} {:>13} {:>9} {:>8}".format(
        "???", "max_gap(mm)", "max_angle(deg)", "contact%", "??"))
    lines.append("-" * 78)

    sorted_res = sorted(results, key=lambda r: r["max_gap_m"])
    for r in sorted_res:
        gap_mm = r["max_gap_mm"]
        ang = r["max_angle_deg"]
        if np.isnan(ang):
            rating = "??"
        elif gap_mm < 0.1 and ang < 1.0:
            rating = "G1 OK"
        elif gap_mm < 0.1 and ang < 5.0:
            rating = "G0 OK"
        elif gap_mm < 1.0:
            rating = "??G0"
        elif gap_mm < 10.0:
            rating = "???"
        else:
            rating = "??"
        lines.append("{:<32} {:>12} {:>13} {:>8}% {:>8}".format(
            r["pair_name"], _fmt(gap_mm, ">12.3f"), _fmt(ang, ">13.2f"),
            format(r["contact_ratio"] * 100, ".1f"), rating))
    lines.append("-" * 78)

    lines.append("")
    lines.append("[??] ??????????:")
    lines.append("=" * 78)
    for r in sorted_res:
        lines.append("")
        lines.append("* " + r["pair_name"])
        lines.append("  ????: {} mm  ????: {} mm  ???: {:.1f}%  ????: {}".format(
            _fmt(r["min_gap_m"] * 1000), _fmt(r["max_gap_mm"]),
            r["contact_ratio"] * 100, r["contact_count"]))
        lines.append("  ?????: ?? {} deg  ?? {} deg".format(
            _fmt(r["max_angle_deg"], ".2f"), _fmt(r["mean_angle_deg"], ".2f")))
        best = min(r["per_edge"], key=lambda e: e["min_gap"])
        worst = max(r["per_edge"], key=lambda e: e["max_gap"])
        lines.append("  ?????: {}<->{}  min={:.3f}mm  contact={}/40".format(
            best["edge_a"], best["edge_b"], best["min_gap"] * 1000, best["contact_count"]))
        lines.append("  ?????: {}<->{}  max={:.3f}mm".format(
            worst["edge_a"], worst["edge_b"], worst["max_gap"] * 1000))

    lines.append("")
    lines.append("=" * 78)
    lines.append("[??]")
    body_pairs = [r for r in results if "body_upper_skin" in r["pair_name"]]
    g0_pass = sum(1 for r in body_pairs if r["max_gap_mm"] < 0.1)
    g1_pass = sum(1 for r in body_pairs
                  if r["max_gap_mm"] < 0.1 and not np.isnan(r["max_angle_deg"])
                  and r["max_angle_deg"] < 1.0)
    lines.append("  ??????: {}".format(len(body_pairs)))
    lines.append("  G0 ?? (<0.1mm): {}/{}".format(g0_pass, len(body_pairs)))
    lines.append("  G1 ?? (<1deg):   {}/{}".format(g1_pass, len(body_pairs)))
    lines.append("")
    lines.append("  ?: ??/??????????? (????)??????????")
    lines.append("  ?: ??/???????????????? (????)?")
    lines.append("=" * 78)

    report = "\n".join(lines)
    print(report)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print("")
    print("?????: " + out_path)


def main():
    print("=" * 78)
    print("Example 9 ? NURBS ??????? (? Python ?? FreeCAD)")
    print("=" * 78)

    params = CarParams()
    print("CarParams: L={} W={} H={} gc={}".format(
        params.L, params.W, params.H, params.ground_clearance))

    print("\n[1] ?? NURBS ??...")
    body_surf = build_body_nurbs(params)
    ends = build_all_ends_nurbs(params)
    wheels = build_all_wheels_nurbs(params)
    mirrors = build_all_mirrors_nurbs(params)

    all_surfs = {"body_upper_skin": body_surf}
    for surf, name, _ in ends + wheels + mirrors:
        all_surfs[name] = surf
    print("    ? {} ??".format(len(all_surfs)))

    pairs_to_check = [
        ("body_upper_skin", "front_bumper"),
        ("body_upper_skin", "rear_bumper"),
        ("front_bumper", "grille"),
        ("front_bumper", "headlight_R"),
        ("front_bumper", "headlight_L"),
        ("rear_bumper", "taillight_R"),
        ("rear_bumper", "taillight_L"),
        ("body_upper_skin", "wheel_FL_tire"),
    ]

    print("\n[2] ?? {} ???...".format(len(pairs_to_check)))
    results = []
    for name_a, name_b in pairs_to_check:
        if name_a not in all_surfs or name_b not in all_surfs:
            print("    ?? {}<->{} (????)".format(name_a, name_b))
            continue
        print("    ?? {} <-> {} ...".format(name_a, name_b), end=" ", flush=True)
        r = analyze_pair(all_surfs[name_a], all_surfs[name_b], name_a, name_b)
        results.append(r)
        print("max_gap={:.3f}mm  max_angle={} deg  contact={:.1f}%".format(
            r["max_gap_mm"], _fmt(r["max_angle_deg"], ".2f"),
            r["contact_ratio"] * 100))

    print("\n[3] ????...")
    out_dir = os.path.join(_ROOT, "data", "step")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "continuity_report.txt")
    print_report(results, report_path)

    print("\n[4] ????????...")
    nv_path = os.path.join(out_dir, "continuity_normals.npz")
    body = all_surfs["body_upper_skin"]
    sample_us = np.linspace(0.05, 0.95, 8)
    sample_vs = np.linspace(0.05, 0.95, 8)
    nv_pts = []
    nv_dirs = []
    for u in sample_us:
        for v in sample_vs:
            nv_pts.append(evaluate_surface(body, u, v))
            nv_dirs.append(surface_normal(body, u, v))
    np.savez(nv_path, points=np.array(nv_pts), normals=np.array(nv_dirs), allow_pickle=False)
    print("    {} ({} ???)".format(nv_path, len(nv_pts)))

    print("\n" + "=" * 78)
    print("?????????????? G0/G1 ?????:")
    print("  " + report_path)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        _err = os.path.join(_ROOT, "data", "step", "_ex9_error.txt")
        with open(_err, "w", encoding="utf-8") as _f:
            _f.write("ERROR: {}\n\n{}".format(e, traceback.format_exc()))
        print("ERROR: " + str(e), file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
