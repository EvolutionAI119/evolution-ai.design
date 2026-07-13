"""
Kalman + NURBS Optimization Verification Script
Compares original mesh vs NURBS surface quality
"""

import math
import os
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from verify_algorithm import HardpointParams, derive_hardpoints, generate_car_body
from kalman_nurbs import (
    generate_nurbs_car_body, analyze_nurbs_quality,
    kalman_smooth_profile, KalmanFilter1D, MultiVarKalmanFilter,
    NURBSSurface, bspline_basis_deboor
)


def compute_mesh_curvature(vertices, indices, k_neighbors=6):
    """Estimate discrete curvature from mesh connectivity."""
    from collections import defaultdict
    neighbors = defaultdict(list)
    n_tri = len(indices) // 3
    for i in range(n_tri):
        for j in range(3):
            v0 = indices[i*3 + j]
            v1 = indices[i*3 + (j+1) % 3]
            neighbors[v0].append(v1)

    curvatures = []
    for i in range(len(vertices)):
        nbrs = list(set(neighbors.get(i, [])))
        if len(nbrs) < 2:
            curvatures.append(0)
            continue
        # Laplacian curvature estimate
        p = vertices[i]
        avg = np.mean(vertices[nbrs], axis=0)
        lap = avg - p
        curvatures.append(np.linalg.norm(lap))

    return np.array(curvatures)


if __name__ == '__main__':
    print("=" * 70)
    print("  Kalman + NURBS Optimization Verification")
    print("=" * 70)

    p = HardpointParams()
    h = derive_hardpoints(p)

    # ---- 1. Kalman Filter Demonstration ----
    print("\n--- 1. Kalman Filter Parameter Smoothing ---")
    np.random.seed(42)

    # Generate test: smooth a noisy hardpoint profile
    from verify_algorithm import side_upper_profile, top_width_profile, lerp_profile
    sup = side_upper_profile(p, h)
    twp = top_width_profile(p)

    # Sample topY profile with noise
    x_samples = np.linspace(0, p.L, 100)
    topY_clean = [lerp_profile(sup, x) for x in x_samples]
    topY_noisy = [y + 0.02 * (2 * np.random.random() - 1) for y in topY_clean]
    topY_smoothed = kalman_smooth_profile(topY_noisy, Q=0.0003, R=0.002)

    mse_noisy = np.mean([(n - c) ** 2 for n, c in zip(topY_noisy, topY_clean)])
    mse_smoothed = np.mean([(s - c) ** 2 for s, c in zip(topY_smoothed, topY_clean)])
    improvement = (1 - mse_smoothed / mse_noisy) * 100 if mse_noisy > 0 else 0
    print(f"  TopY profile - Noisy MSE: {mse_noisy:.6f}, Smoothed MSE: {mse_smoothed:.6f}")
    print(f"  Noise reduction: {improvement:.1f}%")

    # ---- 2. Generate Both Models ----
    print("\n--- 2. Model Generation ---")
    t0 = time.perf_counter()
    verts_orig, idx_orig, _ = generate_car_body(p, nS=80, nC=64)
    t1 = time.perf_counter()
    print(f"  Original: {len(verts_orig)} vertices, {len(idx_orig)//3} triangles ({(t1-t0)*1000:.1f}ms)")

    t0 = time.perf_counter()
    verts_nurbs, idx_nurbs, surface = generate_nurbs_car_body(
        p, h, n_u_samples=80, n_v_samples=64, n_u_ctrl=20, n_v_ctrl=32, degree=3)
    t1 = time.perf_counter()
    print(f"  NURBS:    {len(verts_nurbs)} vertices, {len(idx_nurbs)//3} triangles ({(t1-t0)*1000:.1f}ms)")

    # ---- 3. Bounding Box Comparison ----
    print("\n--- 3. Bounding Box Comparison ---")
    for label, v in [("Original", verts_orig), ("NURBS", verts_nurbs)]:
        xr = (v[:, 0].min(), v[:, 0].max())
        yr = (v[:, 1].min(), v[:, 1].max())
        zr = (v[:, 2].min(), v[:, 2].max())
        print(f"  {label}: X[{xr[0]:.3f}, {xr[1]:.3f}] Y[{yr[0]:.3f}, {yr[1]:.3f}] Z[{zr[0]:.3f}, {zr[1]:.3f}]")

    # ---- 4. Surface Quality Comparison ----
    print("\n--- 4. Surface Quality ---")

    # Original mesh curvature
    curv_orig = compute_mesh_curvature(verts_orig, idx_orig)
    curv_nurbs = compute_mesh_curvature(verts_nurbs, idx_nurbs)

    print(f"  Original curvature: mean={np.mean(curv_orig):.4f}, std={np.std(curv_orig):.4f}, max={np.max(curv_orig):.4f}")
    print(f"  NURBS curvature:    mean={np.mean(curv_nurbs):.4f}, std={np.std(curv_nurbs):.4f}, max={np.max(curv_nurbs):.4f}")

    # NURBS analytical quality
    quality = analyze_nurbs_quality(surface, n_samples=15)
    print(f"  NURBS analytical: curvature range=[{quality['curvature_min']:.4f}, {quality['curvature_max']:.4f}]")
    print(f"  NURBS analytical: curvature mean={quality['curvature_mean']:.4f}, std={quality['curvature_std']:.4f}")

    # ---- 5. Export All Formats ----
    print("\n--- 5. Export Summary ---")
    from export_stl import export_stl_binary

    exports = {
        'car_body_nurbs.stl': ('STL (Polygon)', verts_nurbs, idx_nurbs),
    }

    for fname, (fmt, v, i) in exports.items():
        n_tri = export_stl_binary(v, i, fname)
        size = os.path.getsize(fname)
        print(f"  {fname}: {size/1024:.1f} KB, {n_tri} triangles [{fmt}]")

    # IGES and STEP
    iges_path = "car_body_nurbs.igs"
    step_path = "car_body_nurbs.stp"
    surface.export_iges(iges_path)
    surface.export_step(step_path)
    print(f"  {iges_path}: {os.path.getsize(iges_path)/1024:.1f} KB [IGES Type 128]")
    print(f"  {step_path}: {os.path.getsize(step_path)/1024:.1f} KB [STEP AP214]")

    # ---- 6. Visualization ----
    print("\n--- 6. Generating Comparison Visualization ---")

    fig = plt.figure(figsize=(20, 14))
    fig.suptitle('Kalman Filter + NURBS Surface Optimization\n'
                 'BMW 3 Series (F30) A-Class Surface Comparison',
                 fontsize=14, fontweight='bold')

    # Panel 1: Kalman Filter Demo
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.plot(x_samples, topY_clean, 'g-', linewidth=2, label='True', alpha=0.8)
    ax1.plot(x_samples, topY_noisy, 'b.', markersize=2, alpha=0.3, label='Noisy')
    ax1.plot(x_samples, topY_smoothed, 'r-', linewidth=1.5, label='Kalman Smoothed')
    ax1.set_title('(a) Kalman Filter Parameter Smoothing')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('TopY (m)')
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Panel 2: Original Side Profile
    ax2 = fig.add_subplot(2, 3, 2)
    nS_orig, nC_orig = 80, 64
    right_top_orig = list(range(0, (nS_orig + 1) * (nC_orig + 1), nC_orig + 1))
    ax2.plot(verts_orig[right_top_orig, 0], verts_orig[right_top_orig, 1],
             'b-', linewidth=1.5, label='Original')
    ax2.set_title('(b) Original Mesh - Side Profile')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    ax2.legend(fontsize=8)

    # Panel 3: NURBS Side Profile
    ax3 = fig.add_subplot(2, 3, 3)
    nS_nurbs, nC_nurbs = 80, 64
    right_top_nurbs = list(range(0, (nS_nurbs + 1) * (nC_nurbs + 1), nC_nurbs + 1))
    right_top_nurbs = [i for i in right_top_nurbs if i < len(verts_nurbs)]
    ax3.plot(verts_nurbs[right_top_nurbs, 0], verts_nurbs[right_top_nurbs, 1],
             'r-', linewidth=1.5, label='NURBS')
    ax3.set_title('(c) NURBS Surface - Side Profile')
    ax3.set_xlabel('X (m)')
    ax3.set_ylabel('Y (m)')
    ax3.grid(True, alpha=0.3)
    ax3.set_aspect('equal')
    ax3.legend(fontsize=8)

    # Panel 4: Overlay Comparison
    ax4 = fig.add_subplot(2, 3, 4)
    ax4.plot(verts_orig[right_top_orig, 0], verts_orig[right_top_orig, 1],
             'b-', linewidth=2, alpha=0.5, label='Original')
    ax4.plot(verts_nurbs[right_top_nurbs, 0], verts_nurbs[right_top_nurbs, 1],
             'r-', linewidth=2, alpha=0.7, label='NURBS')
    ax4.set_title('(d) Overlay Comparison')
    ax4.set_xlabel('X (m)')
    ax4.set_ylabel('Y (m)')
    ax4.grid(True, alpha=0.3)
    ax4.set_aspect('equal')
    ax4.legend(fontsize=8)

    # Panel 5: Curvature Comparison
    ax5 = fig.add_subplot(2, 3, 5)
    bins = np.linspace(0, max(np.percentile(curv_orig, 99), np.percentile(curv_nurbs, 99)), 50)
    ax5.hist(curv_orig, bins=bins, alpha=0.5, label='Original', color='steelblue', density=True)
    ax5.hist(curv_nurbs, bins=bins, alpha=0.5, label='NURBS', color='coral', density=True)
    ax5.set_title('(e) Curvature Distribution')
    ax5.set_xlabel('Discrete Curvature')
    ax5.set_ylabel('Density')
    ax5.legend(fontsize=8)
    ax5.grid(True, alpha=0.3)

    # Panel 6: Quality Metrics
    ax6 = fig.add_subplot(2, 3, 6)
    metrics = ['Vertices', 'Triangles', 'Y Max\n(m)', 'Curv.\nStd', 'Curv.\nMax']
    orig_vals = [len(verts_orig), len(idx_orig)//3,
                 verts_orig[:, 1].max(), np.std(curv_orig), np.percentile(curv_orig, 99)]
    nurbs_vals = [len(verts_nurbs), len(idx_nurbs)//3,
                  verts_nurbs[:, 1].max(), np.std(curv_nurbs), np.percentile(curv_nurbs, 99)]

    x_pos = np.arange(len(metrics))
    width = 0.35
    ax6.bar(x_pos - width/2, orig_vals, width, label='Original', color='steelblue', alpha=0.8)
    ax6.bar(x_pos + width/2, nurbs_vals, width, label='NURBS', color='coral', alpha=0.8)
    ax6.set_xticks(x_pos)
    ax6.set_xticklabels(metrics, fontsize=8)
    ax6.set_title('(f) Quality Metrics Comparison')
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('kalman_nurbs_comparison.png', dpi=200, bbox_inches='tight')
    print(f"  Saved: kalman_nurbs_comparison.png")

    print("\n" + "=" * 70)
    print("  Verification Complete!")
    print("=" * 70)
