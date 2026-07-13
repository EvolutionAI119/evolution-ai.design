"""
Mesh Smoothing for STL Models
Implements Laplacian and Taubin smoothing (equivalent to Blender's Smooth modifier)
Also generates a Blender Python script for GUI-based smoothing

Algorithms:
  - Laplacian smoothing: moves each vertex toward the average of its neighbors
  - Taubin smoothing: alternates positive/negative lambda to preserve volume
  - Boundary preservation: locks edge vertices to maintain hard edges
"""

import math
import struct
import os
import time
import numpy as np


def read_stl_binary(filepath):
    """Read binary STL file, return vertices and triangle indices."""
    with open(filepath, 'rb') as f:
        header = f.read(80)
        n_tri = struct.unpack('<I', f.read(4))[0]

        vertex_map = {}
        vertices = []
        indices = []

        for _ in range(n_tri):
            f.read(12)  # normal (recompute later)
            tri_verts = []
            for _ in range(3):
                x, y, z = struct.unpack('<fff', f.read(12))
                key = (round(x, 8), round(y, 8), round(z, 8))
                if key not in vertex_map:
                    vertex_map[key] = len(vertices)
                    vertices.append([x, y, z])
                tri_verts.append(vertex_map[key])
            f.read(2)  # attribute byte count
            indices.extend(tri_verts)

    return np.array(vertices, dtype=np.float64), np.array(indices, dtype=np.int32)


def write_stl_binary(vertices, indices, filepath):
    """Write binary STL file."""
    n_tri = len(indices) // 3
    with open(filepath, 'wb') as f:
        header = b'Smoothed BMW 3 Series F30 Car Body - Taubin Smoothed'
        header = header + b'\0' * (80 - len(header))
        f.write(header)
        f.write(struct.pack('<I', n_tri))
        for i in range(n_tri):
            i0, i1, i2 = indices[i*3], indices[i*3+1], indices[i*3+2]
            v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]
            e1 = v1 - v0
            e2 = v2 - v0
            n = np.cross(e1, e2)
            length = np.linalg.norm(n)
            if length > 1e-10:
                n /= length
            else:
                n = np.array([0.0, 0.0, 1.0])
            f.write(struct.pack('<fff', *n))
            f.write(struct.pack('<fff', *v0))
            f.write(struct.pack('<fff', *v1))
            f.write(struct.pack('<fff', *v2))
            f.write(struct.pack('<H', 0))


def build_adjacency(vertices, indices):
    """Build vertex adjacency list (neighbors for each vertex)."""
    n_vert = len(vertices)
    neighbors = [set() for _ in range(n_vert)]

    n_tri = len(indices) // 3
    for i in range(n_tri):
        i0, i1, i2 = indices[i*3], indices[i*3+1], indices[i*3+2]
        neighbors[i0].add(i1); neighbors[i0].add(i2)
        neighbors[i1].add(i0); neighbors[i1].add(i2)
        neighbors[i2].add(i0); neighbors[i2].add(i1)

    # Convert to sorted lists for consistent ordering
    return [sorted(n) for n in neighbors]


def compute_edge_sharpness(vertices, indices, threshold=30.0):
    """Compute edge sharpness based on dihedral angle between adjacent faces.
    Returns set of vertex indices that are on sharp edges (crease edges)."""
    # Build face adjacency for each edge
    edge_faces = {}
    n_tri = len(indices) // 3
    for i in range(n_tri):
        i0, i1, i2 = indices[i*3], indices[i*3+1], indices[i*3+2]
        for e in [(min(i0,i1), max(i0,i1)),
                  (min(i1,i2), max(i1,i2)),
                  (min(i0,i2), max(i0,i2))]:
            if e not in edge_faces:
                edge_faces[e] = []
            edge_faces[e].append(i)

    # Compute dihedral angles
    sharp_vertices = set()
    cos_threshold = math.cos(math.radians(threshold))

    for edge, face_ids in edge_faces.items():
        if len(face_ids) != 2:
            # Boundary edge - mark as sharp
            sharp_vertices.add(edge[0])
            sharp_vertices.add(edge[1])
            continue

        # Compute face normals
        f0, f1 = face_ids
        normals = []
        for fi in [f0, f1]:
            i0 = indices[fi*3]
            i1 = indices[fi*3+1]
            i2 = indices[fi*3+2]
            e1 = vertices[i1] - vertices[i0]
            e2 = vertices[i2] - vertices[i0]
            n = np.cross(e1, e2)
            length = np.linalg.norm(n)
            if length > 1e-10:
                n /= length
            normals.append(n)

        # Dihedral angle
        dot = np.dot(normals[0], normals[1])
        dot = max(-1.0, min(1.0, dot))
        angle = math.degrees(math.acos(dot))

        if angle > threshold:
            sharp_vertices.add(edge[0])
            sharp_vertices.add(edge[1])

    return sharp_vertices


def laplacian_smooth(vertices, neighbors, sharp_verts, lambda_val=0.5):
    """One iteration of Laplacian smoothing.
    lambda_val: smoothing factor (0=no change, 1=full average)
    sharp_verts: set of vertex indices to keep fixed (sharp edges)
    """
    new_verts = vertices.copy()
    for i in range(len(vertices)):
        if i in sharp_verts or len(neighbors[i]) == 0:
            continue
        avg = np.mean(vertices[neighbors[i]], axis=0)
        new_verts[i] = vertices[i] + lambda_val * (avg - vertices[i])
    return new_verts


def taubin_smooth(vertices, neighbors, sharp_verts, lambda_val=0.5, mu_val=-0.53, iterations=10):
    """Taubin smoothing - volume-preserving mesh smoothing.
    Alternates between positive (shrink) and negative (inflate) steps.
    Equivalent to Blender's Smooth modifier with higher quality.

    lambda_val: shrink factor (positive, typically 0.3-0.7)
    mu_val: inflate factor (negative, typically -0.5 to -0.6)
    iterations: number of shrink-inflate cycles
    """
    verts = vertices.copy()
    for it in range(iterations):
        # Shrink step
        verts = laplacian_smooth(verts, neighbors, sharp_verts, lambda_val)
        # Inflate step
        verts = laplacian_smooth(verts, neighbors, sharp_verts, mu_val)
    return verts


def compute_mesh_quality(vertices, indices):
    """Compute mesh quality metrics."""
    n_tri = len(indices) // 3
    min_angle = 180.0
    max_angle = 0.0
    min_aspect = float('inf')
    total_area = 0.0
    degenerate = 0

    for i in range(n_tri):
        i0, i1, i2 = indices[i*3], indices[i*3+1], indices[i*3+2]
        v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]

        e0 = v1 - v0
        e1 = v2 - v1
        e2 = v0 - v2

        l0 = np.linalg.norm(e0)
        l1 = np.linalg.norm(e1)
        l2 = np.linalg.norm(e2)

        # Triangle area
        cross = np.cross(e0, -e2)
        area = 0.5 * np.linalg.norm(cross)
        total_area += area

        if area < 1e-12:
            degenerate += 1
            continue

        # Angles
        a0 = math.degrees(math.acos(max(-1, min(1, np.dot(e0, -e2) / (l0 * l2 + 1e-15)))))
        a1 = math.degrees(math.acos(max(-1, min(1, np.dot(-e0, e1) / (l0 * l1 + 1e-15)))))
        a2 = 180.0 - a0 - a1

        min_angle = min(min_angle, a0, a1, a2)
        max_angle = max(max_angle, a0, a1, a2)

        # Aspect ratio (4*area / (longest_edge^2 * sqrt(3)))
        longest = max(l0, l1, l2)
        aspect = 4.0 * area / (longest * longest * math.sqrt(3) + 1e-15)
        min_aspect = min(min_aspect, aspect)

    return {
        'min_angle': min_angle,
        'max_angle': max_angle,
        'min_aspect_ratio': min_aspect,
        'surface_area': total_area,
        'degenerate': degenerate,
    }


def generate_blender_script(input_stl, output_stl, smooth_iterations=5, crease_angle=30):
    """Generate a Blender Python script that can be run with:
    blender --background --python blender_smooth.py
    """
    script = f'''"""
Blender Mesh Smoothing Script
Run with: blender --background --python blender_smooth.py
"""
import bpy

# Clean default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import STL
bpy.ops.import_mesh.stl(filepath=r"{input_stl}")
obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

# Add Smooth modifier (Laplacian)
bpy.ops.object.modifier_add(type='SMOOTH')
smooth_mod = obj.modifiers[-1]
smooth_mod.iterations = {smooth_iterations}
smooth_mod.factor = 0.5

# Add Subdivision Surface for finer detail
bpy.ops.object.modifier_add(type='SUBSURF')
subsurf = obj.modifiers[-1]
subsurf.levels = 1
subsurf.render_levels = 2
subsurf.subdivision_type = 'CATMULL_CLARK'

# Shade smooth
bpy.ops.object.shade_smooth()

# Apply modifiers
bpy.ops.object.modifier_apply(modifier=smooth_mod.name)
bpy.ops.object.modifier_apply(modifier=subsurf.name)

# Export STL
bpy.ops.export_mesh.stl(filepath=r"{output_stl}", use_selection=True)

print(f"Blender smoothing complete: {output_stl}")
'''
    return script


if __name__ == '__main__':
    input_file = "car_body_ultra.stl"
    output_smooth = "car_body_ultra_smooth.stl"
    output_blender = "car_body_blender_smooth.stl"
    blender_script = "blender_smooth.py"

    print("=" * 70)
    print("  Mesh Smoothing - BMW 3 Series (F30) Car Body")
    print("=" * 70)

    # Read STL
    print(f"\n  Reading: {input_file}")
    t0 = time.perf_counter()
    vertices, indices = read_stl_binary(input_file)
    t1 = time.perf_counter()
    print(f"  Loaded {len(vertices)} vertices, {len(indices)//3} triangles ({t1-t0:.2f}s)")

    # Build adjacency
    print("\n  Building adjacency graph...")
    t0 = time.perf_counter()
    neighbors = build_adjacency(vertices, indices)
    t1 = time.perf_counter()
    print(f"  Adjacency built ({t1-t0:.2f}s)")

    # Compute edge sharpness
    print("\n  Computing edge sharpness (crease angle=30°)...")
    t0 = time.perf_counter()
    sharp_verts = compute_edge_sharpness(vertices, indices, threshold=30.0)
    t1 = time.perf_counter()
    print(f"  Sharp vertices: {len(sharp_verts)} / {len(vertices)} ({len(sharp_verts)/len(vertices)*100:.1f}%)")
    print(f"  Computed ({t1-t0:.2f}s)")

    # Quality before smoothing
    print("\n  --- Mesh Quality BEFORE Smoothing ---")
    q_before = compute_mesh_quality(vertices, indices)
    print(f"  Min angle: {q_before['min_angle']:.1f}°")
    print(f"  Max angle: {q_before['max_angle']:.1f}°")
    print(f"  Min aspect ratio: {q_before['min_aspect_ratio']:.4f}")
    print(f"  Surface area: {q_before['surface_area']:.4f} m²")
    print(f"  Degenerate triangles: {q_before['degenerate']}")

    # Apply Taubin smoothing with different parameters
    smoothing_configs = [
        ("Light", 0.3, -0.35, 5),
        ("Medium", 0.5, -0.53, 10),
        ("Strong", 0.6, -0.6, 15),
    ]

    for label, lam, mu, iters in smoothing_configs:
        print(f"\n  --- Taubin Smoothing: {label} (λ={lam}, μ={mu}, iters={iters}) ---")
        t0 = time.perf_counter()
        smoothed = taubin_smooth(vertices, neighbors, sharp_verts, lam, mu, iters)
        t1 = time.perf_counter()
        print(f"  Smoothing time: {t1-t0:.2f}s")

        # Quality after smoothing
        q_after = compute_mesh_quality(smoothed, indices)
        print(f"  Min angle: {q_after['min_angle']:.1f}° (was {q_before['min_angle']:.1f}°)")
        print(f"  Max angle: {q_after['max_angle']:.1f}° (was {q_before['max_angle']:.1f}°)")
        print(f"  Min aspect ratio: {q_after['min_aspect_ratio']:.4f} (was {q_before['min_aspect_ratio']:.4f})")
        print(f"  Surface area: {q_after['surface_area']:.4f} m² (was {q_before['surface_area']:.4f} m²)")
        area_change = (q_after['surface_area'] - q_before['surface_area']) / q_before['surface_area'] * 100
        print(f"  Area change: {area_change:+.2f}%")

        # Compute max vertex displacement
        displacements = np.linalg.norm(smoothed - vertices, axis=1)
        max_disp = displacements.max()
        mean_disp = displacements.mean()
        print(f"  Max displacement: {max_disp*1000:.2f}mm")
        print(f"  Mean displacement: {mean_disp*1000:.2f}mm")

        # Export
        if label == "Medium":
            out_path = output_smooth
        else:
            out_path = f"car_body_ultra_{label.lower()}_smooth.stl"

        write_stl_binary(smoothed, indices, out_path)
        file_size = os.path.getsize(out_path)
        print(f"  Exported: {out_path} ({file_size/1024:.1f} KB)")

    # Generate Blender script
    print(f"\n  Generating Blender Python script...")
    blender_script_content = generate_blender_script(
        os.path.abspath(output_smooth),
        os.path.abspath(output_blender),
        smooth_iterations=5,
        crease_angle=30
    )
    with open(blender_script, 'w') as f:
        f.write(blender_script_content)
    print(f"  Saved: {blender_script}")
    print(f"  Usage: blender --background --python {blender_script}")

    # Generate comparison visualization
    print(f"\n  Generating comparison visualization...")
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    # Load medium smoothed for comparison
    verts_smooth, _ = read_stl_binary(output_smooth)

    # Regenerate original mesh from algorithm for consistent vertex ordering
    from verify_algorithm import generate_car_body, HardpointParams, derive_hardpoints
    p_vis = HardpointParams()
    verts_orig, idx_orig, _ = generate_car_body(p_vis, nS=240, nC=192)
    nS_vis = 240
    nC_vis = 192

    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('Mesh Smoothing Comparison - BMW 3 Series (F30)\n'
                 'Taubin Smoothing (Volume-Preserving)', fontsize=14, fontweight='bold')

    # Extract side profiles from algorithm-generated mesh
    right_top = list(range(0, (nS_vis + 1) * (nC_vis + 1), nC_vis + 1))
    right_mid = list(range(nC_vis // 2, (nS_vis + 1) * (nC_vis + 1), nC_vis + 1))

    # For smoothed mesh, extract side profile by X-sorting unique X positions
    # Use the original mesh topology to map smoothed vertices
    # Build adjacency from original mesh and apply smoothing to original vertices
    neighbors_vis = build_adjacency(verts_orig, idx_orig)
    sharp_vis = compute_edge_sharpness(verts_orig, idx_orig, threshold=30.0)
    verts_smooth_vis = taubin_smooth(verts_orig, neighbors_vis, sharp_vis, 0.5, -0.53, 10)

    # Panel 1: Before smoothing - side view
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.plot(verts_orig[right_top, 0], verts_orig[right_top, 1],
             'b-', linewidth=1.5, label='Original')
    ax1.set_title('(a) Original Mesh - Side View')
    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect('equal')
    ax1.legend(fontsize=8)

    # Panel 2: After smoothing - side view
    ax2 = fig.add_subplot(2, 3, 2)
    ax2.plot(verts_smooth_vis[right_top, 0], verts_smooth_vis[right_top, 1],
             'r-', linewidth=1.5, label='Smoothed (Taubin)')
    ax2.set_title('(b) Smoothed Mesh - Side View')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.grid(True, alpha=0.3)
    ax2.set_aspect('equal')
    ax2.legend(fontsize=8)

    # Panel 3: Overlay comparison
    ax3 = fig.add_subplot(2, 3, 3)
    ax3.plot(verts_orig[right_top, 0], verts_orig[right_top, 1],
             'b-', linewidth=2, alpha=0.5, label='Original')
    ax3.plot(verts_smooth_vis[right_top, 0], verts_smooth_vis[right_top, 1],
             'r-', linewidth=2, alpha=0.7, label='Smoothed')
    ax3.set_title('(c) Overlay Comparison')
    ax3.set_xlabel('X (m)')
    ax3.set_ylabel('Y (m)')
    ax3.grid(True, alpha=0.3)
    ax3.set_aspect('equal')
    ax3.legend(fontsize=8)

    # Panel 4: Displacement map
    ax4 = fig.add_subplot(2, 3, 4)
    displacements_vis = np.linalg.norm(verts_smooth_vis - verts_orig, axis=1)
    sc = ax4.scatter(verts_orig[:, 0], verts_orig[:, 1], c=displacements_vis * 1000,
                     cmap='hot', s=0.5, alpha=0.5)
    plt.colorbar(sc, ax=ax4, label='Displacement (mm)')
    ax4.set_title('(d) Vertex Displacement Map')
    ax4.set_xlabel('X (m)')
    ax4.set_ylabel('Y (m)')
    ax4.set_aspect('equal')

    # Panel 5: Top view comparison
    ax5 = fig.add_subplot(2, 3, 5)
    ax5.plot(verts_orig[right_mid, 0], verts_orig[right_mid, 2],
             'b-', linewidth=1.5, alpha=0.5, label='Original')
    ax5.plot(verts_smooth_vis[right_mid, 0], verts_smooth_vis[right_mid, 2],
             'r-', linewidth=1.5, alpha=0.7, label='Smoothed')
    ax5.set_title('(e) Top View Comparison')
    ax5.set_xlabel('X (m)')
    ax5.set_ylabel('Z (m)')
    ax5.grid(True, alpha=0.3)
    ax5.set_aspect('equal')
    ax5.legend(fontsize=8)

    # Panel 6: Quality metrics comparison
    ax6 = fig.add_subplot(2, 3, 6)
    metrics = ['Min Angle\n(°)', 'Max Angle\n(°)', 'Aspect\nRatio', 'Area\n(m²)']
    q_orig = compute_mesh_quality(verts_orig, idx_orig)
    before_vals = [q_orig['min_angle'], q_orig['max_angle'],
                   q_orig['min_aspect_ratio'] * 100, q_orig['surface_area']]
    q_smoothed = compute_mesh_quality(verts_smooth_vis, idx_orig)
    after_vals = [q_smoothed['min_angle'], q_smoothed['max_angle'],
                  q_smoothed['min_aspect_ratio'] * 100, q_smoothed['surface_area']]

    x_pos = np.arange(len(metrics))
    width = 0.35
    bars1 = ax6.bar(x_pos - width/2, before_vals, width, label='Before', color='steelblue', alpha=0.8)
    bars2 = ax6.bar(x_pos + width/2, after_vals, width, label='After', color='coral', alpha=0.8)
    ax6.set_xticks(x_pos)
    ax6.set_xticklabels(metrics, fontsize=8)
    ax6.set_title('(f) Quality Metrics Comparison')
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('smoothing_comparison.png', dpi=200, bbox_inches='tight')
    print(f"  Saved: smoothing_comparison.png")

    print("\n" + "=" * 70)
    print("  Smoothing Complete!")
    print(f"  Primary output: {output_smooth}")
    print(f"  Blender script: {blender_script}")
    print("=" * 70)
