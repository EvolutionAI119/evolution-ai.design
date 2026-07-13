"""
Export final car body model to STL format for 3D printing verification.
Supports both ASCII and Binary STL formats.
"""

import struct
import math
import os
import numpy as np
from verify_algorithm import HardpointParams, derive_hardpoints, generate_car_body


def compute_face_normal(v0, v1, v2):
    """Compute unit normal of a triangle from 3 vertices."""
    e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
    e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
    nx = e1[1]*e2[2] - e1[2]*e2[1]
    ny = e1[2]*e2[0] - e1[0]*e2[2]
    nz = e1[0]*e2[1] - e1[1]*e2[0]
    length = math.sqrt(nx*nx + ny*ny + nz*nz)
    if length < 1e-10:
        return (0.0, 0.0, 1.0)
    return (nx/length, ny/length, nz/length)


def export_stl_ascii(vertices, indices, filepath):
    """Export mesh as ASCII STL file."""
    n_tri = len(indices) // 3
    with open(filepath, 'w') as f:
        f.write("solid car_body\n")
        for i in range(n_tri):
            i0 = indices[i*3]
            i1 = indices[i*3 + 1]
            i2 = indices[i*3 + 2]
            v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]
            nx, ny, nz = compute_face_normal(v0, v1, v2)
            f.write(f"  facet normal {nx:.6e} {ny:.6e} {nz:.6e}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}\n")
            f.write(f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}\n")
            f.write(f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid car_body\n")
    return n_tri


def export_stl_binary(vertices, indices, filepath):
    """Export mesh as Binary STL file (smaller, faster to load)."""
    n_tri = len(indices) // 3
    with open(filepath, 'wb') as f:
        # 80-byte header
        header = b'Binary STL - BMW 3 Series F30 Car Body Model'
        header = header + b'\0' * (80 - len(header))
        f.write(header)
        # Number of triangles
        f.write(struct.pack('<I', n_tri))
        # Triangle records
        for i in range(n_tri):
            i0 = indices[i*3]
            i1 = indices[i*3 + 1]
            i2 = indices[i*3 + 2]
            v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]
            nx, ny, nz = compute_face_normal(v0, v1, v2)
            f.write(struct.pack('<fff', nx, ny, nz))
            f.write(struct.pack('<fff', *v0))
            f.write(struct.pack('<fff', *v1))
            f.write(struct.pack('<fff', *v2))
            f.write(struct.pack('<H', 0))  # attribute byte count
    return n_tri


def compute_mesh_stats(vertices, indices):
    """Compute mesh quality statistics."""
    n_tri = len(indices) // 3
    n_vert = len(vertices)

    # Bounding box
    x_min, x_max = vertices[:, 0].min(), vertices[:, 0].max()
    y_min, y_max = vertices[:, 1].min(), vertices[:, 1].max()
    z_min, z_max = vertices[:, 2].min(), vertices[:, 2].max()

    # Surface area and volume (approximate)
    total_area = 0.0
    total_volume = 0.0
    min_edge = float('inf')
    max_edge = 0.0
    degenerate_count = 0

    for i in range(n_tri):
        i0, i1, i2 = indices[i*3], indices[i*3+1], indices[i*3+2]
        v0, v1, v2 = vertices[i0], vertices[i1], vertices[i2]

        # Edge lengths
        e0 = np.linalg.norm(v1 - v0)
        e1 = np.linalg.norm(v2 - v1)
        e2 = np.linalg.norm(v0 - v2)

        min_edge = min(min_edge, e0, e1, e2)
        max_edge = max(max_edge, e0, e1, e2)

        # Triangle area (cross product method)
        e1v = v1 - v0
        e2v = v2 - v0
        cross = np.cross(e1v, e2v)
        area = 0.5 * np.linalg.norm(cross)
        total_area += area

        if area < 1e-10:
            degenerate_count += 1

        # Signed volume (divergence theorem)
        total_volume += np.dot(v0, np.cross(v1, v2)) / 6.0

    return {
        'n_vertices': n_vert,
        'n_triangles': n_tri,
        'bbox_x': (x_min, x_max),
        'bbox_y': (y_min, y_max),
        'bbox_z': (z_min, z_max),
        'surface_area': total_area,
        'volume': abs(total_volume),
        'min_edge': min_edge,
        'max_edge': max_edge,
        'degenerate_triangles': degenerate_count,
    }


if __name__ == '__main__':
    print("=" * 70)
    print("  BMW 3 Series (F30) - STL Export for 3D Printing Verification")
    print("=" * 70)

    # Generate high-resolution mesh
    p = HardpointParams()
    h = derive_hardpoints(p)

    print(f"\n  Car dimensions: L={p.L}m x W={p.W}m x H={p.H}m")
    print(f"  Wheelbase: {p.WB}m")
    print(f"  Key hardpoints:")
    print(f"    A-pillar: base=({h.aBaseX:.3f}, {h.waistY:.3f}) top=({h.aTopX:.3f}, {h.aTopY:.3f})")
    print(f"    C-pillar: base=({h.cBaseX:.3f}, {h.cBaseY:.3f}) top=({h.cTopX:.3f}, {h.cTopY:.3f})")
    print(f"    Roof peak: ({h.roofPeakX:.3f}, {h.roofY:.3f})")

    # Generate mesh at different resolutions
    resolutions = [
        ("Standard", 80, 64),
        ("High", 160, 128),
        ("Ultra", 240, 192),
    ]

    for label, nS, nC in resolutions:
        print(f"\n--- {label} Resolution ({nS}x{nC}) ---")
        verts, idx, _ = generate_car_body(p, nS=nS, nC=nC)

        # Compute stats
        stats = compute_mesh_stats(verts, idx)
        print(f"  Vertices: {stats['n_vertices']}")
        print(f"  Triangles: {stats['n_triangles']}")
        print(f"  Bounding box: X[{stats['bbox_x'][0]:.3f}, {stats['bbox_x'][1]:.3f}] "
              f"Y[{stats['bbox_y'][0]:.3f}, {stats['bbox_y'][1]:.3f}] "
              f"Z[{stats['bbox_z'][0]:.3f}, {stats['bbox_z'][1]:.3f}]")
        print(f"  Surface area: {stats['surface_area']:.4f} m²")
        print(f"  Volume: {stats['volume']:.4f} m³ ({stats['volume']*1000:.1f} liters)")
        print(f"  Edge length: min={stats['min_edge']*1000:.2f}mm, max={stats['max_edge']*1000:.2f}mm")
        print(f"  Degenerate triangles: {stats['degenerate_triangles']}")

        # Export binary STL
        stl_path = f"car_body_{label.lower()}.stl"
        n_tri = export_stl_binary(verts, idx, stl_path)
        file_size = os.path.getsize(stl_path)
        print(f"  Exported: {stl_path} ({file_size/1024:.1f} KB, {n_tri} triangles)")

    # Also export ASCII STL for standard resolution (for inspection)
    print(f"\n--- ASCII STL Export (Standard) ---")
    verts, idx, _ = generate_car_body(p, nS=80, nC=64)
    stl_ascii_path = "car_body_standard_ascii.stl"
    n_tri = export_stl_ascii(verts, idx, stl_ascii_path)
    file_size = os.path.getsize(stl_ascii_path)
    print(f"  Exported: {stl_ascii_path} ({file_size/1024:.1f} KB, {n_tri} triangles)")

    print("\n" + "=" * 70)
    print("  STL Export Complete")
    print("  Files ready for 3D printing slicer (Cura, PrusaSlicer, etc.)")
    print("  Recommended: car_body_standard.stl for FDM printing")
    print("  Recommended: car_body_high.stl for SLA/resin printing")
    print("=" * 70)