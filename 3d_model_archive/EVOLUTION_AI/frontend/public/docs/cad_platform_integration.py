"""
CAD Platform Open-Source API Integration Module
================================================
Unified interface integrating Open CASCADE (OCCT), openNURBS (rhino3dm),
NURBS-Python (geomdl), and CadQuery/build123d for automotive surface modeling.

Installation:
    pip install cadquery-ocp rhino3dm geomdl numpy

Optional:
    conda install -c conda-forge pythonocc-core   # Full OCCT bindings
    pip install build123d                           # Alternative to CadQuery
"""

from __future__ import annotations
import os
import struct
import numpy as np
from typing import List, Tuple, Optional, Dict, Any, Union
from dataclasses import dataclass, field

# ============================================================
# Part 0: Platform Detection & Import
# ============================================================

_CAD_BACKENDS = {}

def _try_import(module_name: str, package_name: str = None):
    """Try to import a module, return None if not available."""
    try:
        mod = __import__(module_name)
        _CAD_BACKENDS[module_name] = mod
        return mod
    except ImportError:
        return None

# Core dependencies (always available)
_numpy = np

# Optional CAD backends
_ocp = _try_import('OCP')
_cadquery = _try_import('cadquery')
_rhino3dm = _try_import('rhino3dm')
_geomdl = _try_import('geomdl')
_build123d = _try_import('build123d')


def get_available_backends() -> Dict[str, bool]:
    """Return dict of available CAD backends."""
    return {
        'OCP (Open CASCADE)': _ocp is not None,
        'CadQuery': _cadquery is not None,
        'rhino3dm (openNURBS)': _rhino3dm is not None,
        'geomdl (NURBS-Python)': _geomdl is not None,
        'build123d': _build123d is not None,
    }


def print_backend_status():
    """Print status of all CAD backends."""
    backends = get_available_backends()
    print("=" * 60)
    print("  CAD Platform Backend Status")
    print("=" * 60)
    for name, available in backends.items():
        status = "AVAILABLE" if available else "NOT INSTALLED"
        print(f"  {name:30s} {status}")
    print("=" * 60)


# ============================================================
# Part 1: Unified NURBS Surface Interface
# ============================================================

@dataclass
class NURBSSurfaceData:
    """Unified NURBS surface data container."""
    control_points: np.ndarray      # (n_u, n_v, 3)
    degree_u: int = 3
    degree_v: int = 3
    weights: Optional[np.ndarray] = None  # (n_u, n_v)
    knots_u: Optional[np.ndarray] = None
    knots_v: Optional[np.ndarray] = None

    def __post_init__(self):
        if self.weights is None:
            n_u, n_v, _ = self.control_points.shape
            self.weights = np.ones((n_u, n_v))
        if self.knots_u is None:
            self.knots_u = self._generate_knots(self.control_points.shape[0], self.degree_u)
        if self.knots_v is None:
            self.knots_v = self._generate_knots(self.control_points.shape[1], self.degree_v)

    @staticmethod
    def _generate_knots(n_ctrl: int, degree: int) -> np.ndarray:
        m = n_ctrl + degree + 1
        knots = np.zeros(m)
        knots[-(degree + 1):] = 1.0
        n_interior = n_ctrl - degree - 1
        if n_interior > 0:
            for j in range(1, n_interior + 1):
                knots[degree + j] = j / (n_interior + 1)
        return knots


class UnifiedNURBSSurface:
    """
    Unified NURBS surface with multi-backend evaluation.
    Supports: native Python, geomdl, OCCT, rhino3dm.
    """

    def __init__(self, data: NURBSSurfaceData):
        self.data = data
        self._geomdl_surface = None
        self._occt_surface = None

    # --- Native Python Evaluation (always available) ---

    @staticmethod
    def _bspline_basis(u: float, p: int, knots: np.ndarray, n_ctrl: int) -> np.ndarray:
        """Cox-de Boor recursion for B-spline basis functions."""
        N = np.zeros(n_ctrl)
        if u <= knots[0]:
            N[0] = 1.0
            return N
        if u >= knots[-1]:
            N[-1] = 1.0
            return N

        # Find knot span
        span = 0
        for i in range(n_ctrl - 1):
            if knots[i] <= u < knots[i + 1]:
                span = i
                break
        else:
            span = n_ctrl - 1

        N[span] = 1.0
        left = np.zeros(p + 1)
        right = np.zeros(p + 1)

        for d in range(1, p + 1):
            left[d] = u - knots[span + 1 - d]
            right[d] = knots[span + d] - u
            saved = 0.0
            for r in range(d, -1, -1):
                denom = right[r + 1] + left[d - r]
                if abs(denom) < 1e-15:
                    temp = 0.0
                else:
                    temp = N[span - r] / denom
                N[span - r] = saved + right[r + 1] * temp
                saved = left[d - r] * temp

        return N

    def evaluate(self, u: float, v: float) -> np.ndarray:
        """Evaluate NURBS surface at (u, v) using native Python."""
        d = self.data
        Nu = self._bspline_basis(u, d.degree_u, d.knots_u, d.control_points.shape[0])
        Nv = self._bspline_basis(v, d.degree_v, d.knots_v, d.control_points.shape[1])

        point = np.zeros(3)
        w_sum = 0.0
        for i in range(d.control_points.shape[0]):
            for j in range(d.control_points.shape[1]):
                w = d.weights[i, j] * Nu[i] * Nv[j]
                point += w * d.control_points[i, j]
                w_sum += w

        if abs(w_sum) > 1e-15:
            point /= w_sum
        return point

    def evaluate_grid(self, n_u: int, n_v: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Evaluate NURBS surface on a grid."""
        d = self.data
        u_vals = np.linspace(0.0, 1.0, n_u)
        v_vals = np.linspace(0.0, 1.0, n_v)

        # Precompute basis functions
        Nu_all = np.zeros((n_u, d.control_points.shape[0]))
        Nv_all = np.zeros((n_v, d.control_points.shape[1]))
        for i, u in enumerate(u_vals):
            Nu_all[i] = self._bspline_basis(u, d.degree_u, d.knots_u, d.control_points.shape[0])
        for j, v in enumerate(v_vals):
            Nv_all[j] = self._bspline_basis(v, d.degree_v, d.knots_v, d.control_points.shape[1])

        X = np.zeros((n_u, n_v))
        Y = np.zeros((n_u, n_v))
        Z = np.zeros((n_u, n_v))

        for i in range(n_u):
            for j in range(n_v):
                point = np.zeros(3)
                w_sum = 0.0
                for ci in range(d.control_points.shape[0]):
                    for cj in range(d.control_points.shape[1]):
                        w = d.weights[ci, cj] * Nu_all[i, ci] * Nv_all[j, cj]
                        point += w * d.control_points[ci, cj]
                        w_sum += w
                if abs(w_sum) > 1e-15:
                    point /= w_sum
                X[i, j] = point[0]
                Y[i, j] = point[1]
                Z[i, j] = point[2]

        return X, Y, Z

    def to_mesh(self, n_u: int = 80, n_v: int = 64) -> Tuple[np.ndarray, np.ndarray]:
        """Convert NURBS surface to triangle mesh."""
        X, Y, Z = self.evaluate_grid(n_u, n_v)
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

    # --- geomdl Backend ---

    def _init_geomdl(self):
        """Initialize geomdl (NURBS-Python) backend."""
        if self._geomdl_surface is not None:
            return
        if _geomdl is None:
            raise ImportError("geomdl not installed. Run: pip install geomdl")

        from geomdl import BSpline
        from geomdl import utilities as gutils

        surf = BSpline.Surface()
        surf.degree_u = self.data.degree_u
        surf.degree_v = self.data.degree_v

        ctrl_pts = []
        for i in range(self.data.control_points.shape[0]):
            for j in range(self.data.control_points.shape[1]):
                pt = self.data.control_points[i, j].tolist()
                pt.append(float(self.data.weights[i, j]))
                ctrl_pts.append(pt)

        surf.ctrlpts2d = ctrl_pts
        surf.knotvector_u = self.data.knots_u.tolist()
        surf.knotvector_v = self.data.knots_v.tolist()
        surf.sample_size = 80

        self._geomdl_surface = surf

    def evaluate_geomdl(self, n_samples: int = 80) -> np.ndarray:
        """Evaluate using geomdl backend (higher quality tessellation)."""
        self._init_geomdl()
        self._geomdl_surface.sample_size = n_samples
        self._geomdl_surface.evaluate()
        return np.array(self._geomdl_surface.evalpts)

    # --- OCCT/CadQuery Backend ---

    def _init_occt(self):
        """Initialize Open CASCADE backend via OCP."""
        if self._occt_surface is not None:
            return
        if _ocp is None:
            raise ImportError("OCP not installed. Run: pip install cadquery-ocp")

        from OCP.TColgp import TColgp_Array2OfPnt
        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.GeomAPI import GeomAPI_Interpolate
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.gp import gp_Pnt

        d = self.data
        n_u, n_v, _ = d.control_points.shape

        # Create OCCT NURBS surface
        poles = TColgp_Array2OfPnt(1, n_u, 1, n_v)
        for i in range(n_u):
            for j in range(n_v):
                pt = d.control_points[i, j]
                poles.SetValue(i + 1, j + 1, gp_Pnt(float(pt[0]), float(pt[1]), float(pt[2])))

        from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
        from OCP.Geom import Geom_BezierSurface, Geom_BSplineSurface
        from OCP.BSplCLib import BSplCLib

        knots_u_occt = TColStd_Array1OfReal(1, len(d.knots_u))
        knots_v_occt = TColStd_Array1OfReal(1, len(d.knots_v))
        for i, k in enumerate(d.knots_u):
            knots_u_occt.SetValue(i + 1, float(k))
        for i, k in enumerate(d.knots_v):
            knots_v_occt.SetValue(i + 1, float(k))

        # Compute multiplicities from knot vector
        def _knot_mults(knots):
            unique_knots = []
            mults = []
            for k in knots:
                if len(unique_knots) == 0 or abs(k - unique_knots[-1]) > 1e-10:
                    unique_knots.append(k)
                    mults.append(1)
                else:
                    mults[-1] += 1
            return unique_knots, mults

        uk, um = _knot_mults(d.knots_u)
        vk, vm = _knot_mults(d.knots_v)

        knots_u2 = TColStd_Array1OfReal(1, len(uk))
        knots_v2 = TColStd_Array1OfReal(1, len(vk))
        mults_u = TColStd_Array1OfInteger(1, len(um))
        mults_v = TColStd_Array1OfInteger(1, len(vm))

        for i, (k, m) in enumerate(zip(uk, um)):
            knots_u2.SetValue(i + 1, float(k))
            mults_u.SetValue(i + 1, m)
        for i, (k, m) in enumerate(zip(vk, vm)):
            knots_v2.SetValue(i + 1, float(k))
            mults_v.SetValue(i + 1, m)

        # Weights
        from OCP.TColStd import TColStd_Array2OfReal
        weights_occt = TColStd_Array2OfReal(1, n_u, 1, n_v)
        for i in range(n_u):
            for j in range(n_v):
                weights_occt.SetValue(i + 1, j + 1, float(d.weights[i, j]))

        # Create rational B-spline surface
        self._occt_surface = Geom_BSplineSurface(
            poles, weights_occt,
            knots_u2, mults_u, knots_v2, mults_v,
            d.degree_u, d.degree_v
        )

    def export_step_occt(self, filepath: str, tolerance: float = 0.001):
        """Export to STEP using OCCT (highest quality)."""
        self._init_occt()
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
        from OCP.Interface import Interface_Static
        from OCP.IFSelect import IFSelect_RetDone

        face = BRepBuilderAPI_MakeFace(self._occt_surface, tolerance).Face()
        writer = STEPControl_Writer()
        Interface_Static.SetCVal("write.step.schema", "AP214")
        writer.Transfer(face, STEPControl_AsIs)
        status = writer.Write(filepath)
        if status != IFSelect_RetDone:
            raise RuntimeError(f"STEP export failed with status {status}")
        print(f"STEP exported via OCCT: {filepath}")

    def export_iges_occt(self, filepath: str):
        """Export to IGES using OCCT."""
        self._init_occt()
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
        from OCP.IGESControl import IGESControl_Writer
        from OCP.Interface import Interface_Static

        face = BRepBuilderAPI_MakeFace(self._occt_surface, 0.001).Face()
        writer = IGESControl_Writer("MM", 0)
        writer.AddFace(face)
        writer.Write(filepath)
        print(f"IGES exported via OCCT: {filepath}")

    # --- rhino3dm (openNURBS) Backend ---

    def export_3dm(self, filepath: str):
        """Export to Rhino .3dm format using rhino3dm."""
        if _rhino3dm is None:
            raise ImportError("rhino3dm not installed. Run: pip install rhino3dm")

        import rhino3dm

        d = self.data
        file3dm = rhino3dm.File3dm()

        # Create NURBS surface in rhino3dm
        n_u, n_v, _ = d.control_points.shape
        ns = rhino3dm.NurbsSurface(3, True, d.degree_u + 1, d.degree_v + 1, n_u, n_v)

        # Set control points and weights
        for i in range(n_u):
            for j in range(n_v):
                pt = d.control_points[i, j]
                ns.Points[i][j] = rhino3dm.Point4d(
                    float(pt[0]), float(pt[1]), float(pt[2]),
                    float(d.weights[i, j])
                )

        # Set knot vectors
        for i, k in enumerate(d.knots_u):
            ns.KnotsU[i] = float(k)
        for i, k in enumerate(d.knots_v):
            ns.KnotsV[i] = float(k)

        if ns.IsValid:
            file3dm.Objects.AddSurface(ns)
        else:
            print("Warning: rhino3dm NURBS surface validation failed, attempting mesh export")
            # Fallback: export as mesh
            vertices, indices = self.to_mesh()
            mesh = rhino3dm.CommonObject()
            for v in vertices:
                mesh.Vertices.Add(float(v[0]), float(v[1]), float(v[2]))
            for i in range(0, len(indices), 3):
                mesh.Faces.AddFace(int(indices[i]), int(indices[i+1]), int(indices[i+2]))
            file3dm.Objects.AddMesh(mesh)

        file3dm.Write(filepath, 7)  # version 7
        print(f"3DM exported via rhino3dm: {filepath}")

    # --- Native Export (always available, no dependencies) ---

    def export_stl(self, filepath: str, n_u: int = 80, n_v: int = 64):
        """Export to binary STL (always available)."""
        vertices, indices = self.to_mesh(n_u, n_v)
        with open(filepath, 'wb') as f:
            f.write(b'\x00' * 80)  # header
            f.write(struct.pack('<I', len(indices) // 3))
            for i in range(0, len(indices), 3):
                v0, v1, v2 = vertices[indices[i]], vertices[indices[i+1]], vertices[indices[i+2]]
                e1 = v1 - v0
                e2 = v2 - v0
                normal = np.cross(e1, e2)
                norm = np.linalg.norm(normal)
                if norm > 1e-15:
                    normal /= norm
                f.write(struct.pack('<3f', *normal))
                for v in [v0, v1, v2]:
                    f.write(struct.pack('<3f', *v))
                f.write(struct.pack('<H', 0))
        print(f"STL exported: {filepath}")

    def export_iges_native(self, filepath: str):
        """Export to IGES Type 128 (native Python, no dependencies)."""
        d = self.data
        n_u, n_v, _ = d.control_points.shape
        lines = []

        # Global section
        lines.append("                                                                        S      1")
        lines.append("1H,,1H;,7HIGES.N,                                                           G      1")
        lines.append(f"7HIGES.N,32HEVOLUTION AI Automotive NURBS,1.0,                             G      2")
        lines.append(f"32,308,15,7HIGES.N,                                                        G      3")

        # Directory entry for Type 128
        de_start = len(lines) + 1
        pd_start = de_start + 2
        lines.append(f"128,{de_start},0,1,0,0,0,0,                                               D{de_start:6d}")
        lines.append(f"128,0,0,1,0,0,0,0,                                                        D{de_start+1:6d}")

        # Parameter data
        p_lines = []
        p_lines.append(f"128,{d.degree_u},{d.degree_v},0,0,1,1,{n_u},{n_v},")
        # Knot vectors
        knots_u_str = ','.join(f'{k:.8f}' for k in d.knots_u)
        knots_v_str = ','.join(f'{k:.8f}' for k in d.knots_v)
        p_lines.append(f"{knots_u_str},")
        p_lines.append(f"{knots_v_str},")
        # Weights
        for i in range(n_u):
            w_str = ','.join(f'{d.weights[i,j]:.6f}' for j in range(n_v))
            p_lines.append(f"{w_str},")
        # Control points
        for i in range(n_u):
            for j in range(n_v):
                pt = d.control_points[i, j]
                p_lines.append(f"{pt[0]:.8f},{pt[1]:.8f},{pt[2]:.8f},")
        # U/V range
        p_lines.append("0.0,1.0,0.0,1.0,")

        # Format parameter lines
        for idx, pl in enumerate(p_lines):
            lines.append(f"{pl:72s}P{pd_start+idx:6d}")

        # Terminate section
        lines.append(f"S{1}G{4}D{2}P{len(p_lines)}                                        T      1")

        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        print(f"IGES exported (native): {filepath}")

    def export_step_native(self, filepath: str):
        """Export to STEP AP214 (native Python, no dependencies)."""
        d = self.data
        n_u, n_v, _ = d.control_points.shape

        # Compute knot multiplicities
        def _knot_mults(knots):
            unique_k = []
            mults = []
            for k in knots:
                if len(unique_k) == 0 or abs(k - unique_k[-1]) > 1e-10:
                    unique_k.append(float(k))
                    mults.append(1)
                else:
                    mults[-1] += 1
            return unique_k, mults

        uk, um = _knot_mults(d.knots_u)
        vk, vm = _knot_mults(d.knots_v)

        entity_id = 1

        def next_id():
            nonlocal entity_id
            eid = entity_id
            entity_id += 1
            return eid

        lines = []
        lines.append("ISO-10303-21;")
        lines.append("HEADER;")
        lines.append("FILE_DESCRIPTION(('EVOLUTION AI Automotive NURBS'),'2;1');")
        lines.append(f"FILE_NAME('{os.path.basename(filepath)}','2026-06-23T00:00:00',('EVOLUTION AI'),('EVOLUTION AI'),'',' ','');")
        lines.append("FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));")
        lines.append("ENDSEC;")
        lines.append("DATA;")

        # Length unit
        length_unit_id = next_id()
        lines.append(f"#{length_unit_id}=SI_UNIT(.METRE.,.MILLI.);")

        # Cartesian points for control points
        cp_ids = np.zeros((n_u, n_v), dtype=int)
        for i in range(n_u):
            for j in range(n_v):
                pt = d.control_points[i, j]
                eid = next_id()
                cp_ids[i, j] = eid
                lines.append(f"#{eid}=CARTESIAN_POINT('',({pt[0]:.8f},{pt[1]:.8f},{pt[2]:.8f}));")

        # Control points list
        cp_list_id = next_id()
        cp_refs = ','.join(f'#{cp_ids[i,j]}' for i in range(n_u) for j in range(n_v))
        lines.append(f"#{cp_list_id}=LIST_OF_CARTESIAN_POINTS('',({cp_refs}));")

        # Knot multiplicities
        um_id = next_id()
        lines.append(f"#{um_id}=LIST_OF_INTEGERS('',({','.join(str(m) for m in um)}));")
        vm_id = next_id()
        lines.append(f"#{vm_id}=LIST_OF_INTEGERS('',({','.join(str(m) for m in vm)}));")

        # Knot values
        uk_id = next_id()
        lines.append(f"#{uk_id}=LIST_OF_REALS('',({','.join(f'{k:.8f}' for k in uk)}));")
        vk_id = next_id()
        lines.append(f"#{vk_id}=LIST_OF_REALS('',({','.join(f'{k:.8f}' for k in vk)}));")

        # Weights
        w_list_id = next_id()
        w_refs = ','.join(f'{d.weights[i,j]:.6f}' for i in range(n_u) for j in range(n_v))
        lines.append(f"#{w_list_id}=LIST_OF_REALS('',({w_refs}));")

        # B-spline surface with knots
        bsurf_id = next_id()
        lines.append(f"#{bsurf_id}=B_SPLINE_SURFACE_WITH_KNOTS('',{d.degree_u},{d.degree_v},#{cp_list_id},.UNSPECIFIED.,.F.,.F.,.F.,#{um_id},#{vm_id},#{uk_id},#{vk_id});")

        # Rational surface
        rsurf_id = next_id()
        lines.append(f"#{rsurf_id}=RATIONAL_B_SPLINE_SURFACE('',#{w_list_id},#{bsurf_id});")

        # Advanced face
        face_id = next_id()
        lines.append(f"#{face_id}=ADVANCED_FACE('',(#{next_id()}),#{rsurf_id},.F.);")

        lines.append("ENDSEC;")
        lines.append("END-ISO-10303-21;")

        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        print(f"STEP exported (native): {filepath}")

    # --- Unified Export ---

    def export(self, filepath: str, backend: str = 'auto', **kwargs):
        """
        Export NURBS surface to file. Auto-detects format from extension.

        Args:
            filepath: Output file path
            backend: 'auto', 'native', 'occt', 'rhino3dm', 'geomdl'
            kwargs: Additional arguments passed to the specific exporter
        """
        ext = os.path.splitext(filepath)[1].lower()

        if backend == 'auto':
            # Prefer OCCT for STEP/IGES if available, else native
            if ext in ('.step', '.stp'):
                if _ocp is not None:
                    backend = 'occt'
                else:
                    backend = 'native'
            elif ext == '.iges' or ext == '.igs':
                if _ocp is not None:
                    backend = 'occt'
                else:
                    backend = 'native'
            elif ext == '.3dm':
                backend = 'rhino3dm'
            elif ext == '.stl':
                backend = 'native'
            else:
                backend = 'native'

        if ext in ('.step', '.stp'):
            if backend == 'occt':
                self.export_step_occt(filepath, **kwargs)
            else:
                self.export_step_native(filepath)
        elif ext in ('.iges', '.igs'):
            if backend == 'occt':
                self.export_iges_occt(filepath)
            else:
                self.export_iges_native(filepath)
        elif ext == '.3dm':
            self.export_3dm(filepath)
        elif ext == '.stl':
            self.export_stl(filepath, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {ext}")


# ============================================================
# Part 2: CadQuery Integration (Parametric Solid Modeling)
# ============================================================

class CadQueryIntegration:
    """
    Integration with CadQuery for parametric solid modeling.
    Uses OCCT kernel for B-Rep operations.
    """

    @staticmethod
    def is_available() -> bool:
        return _cadquery is not None

    @staticmethod
    def create_car_body_solid(params: dict) -> Any:
        """
        Create a car body solid using CadQuery parametric modeling.

        Args:
            params: Dict with L, W, H, WB, FO, RO, GC, WR, TW, AA, CA keys
        """
        if _cadquery is None:
            raise ImportError("CadQuery not installed. Run: pip install cadquery")

        import cadquery as cq

        L = params.get('L', 4.84)
        W = params.get('W', 1.83)
        H = params.get('H', 1.45)
        WB = params.get('WB', 2.96)
        FO = params.get('FO', 0.92)
        RO = params.get('RO', 0.96)
        GC = params.get('GC', 0.14)
        WR = params.get('WR', 0.335)

        # Main body block
        body = (cq.Workplane("XY")
                .box(L, W, H * 0.55, centered=(True, True, False))
                .translate((0, 0, GC + H * 0.05)))

        # Cabin block (narrower, taller)
        cabin_w = W * 0.85
        cabin_h = H * 0.45
        cabin = (cq.Workplane("XY")
                 .box(WB * 0.75, cabin_w, cabin_h, centered=(True, True, False))
                 .translate((FO + WB * 0.15, 0, GC + H * 0.55)))

        # Union
        result = body.union(cabin)

        # Fillet edges for smooth transitions
        try:
            result = result.edges("|Z").fillet(0.03)
        except Exception:
            pass

        return result

    @staticmethod
    def export_step(result: Any, filepath: str):
        """Export CadQuery result to STEP."""
        if _cadquery is None:
            raise ImportError("CadQuery not installed")
        import cadquery as cq
        cq.exporters.export(result, filepath, cq.exporters.ExportTypes.STEP)
        print(f"STEP exported via CadQuery: {filepath}")

    @staticmethod
    def export_stl(result: Any, filepath: str, tolerance: float = 0.001):
        """Export CadQuery result to STL."""
        if _cadquery is None:
            raise ImportError("CadQuery not installed")
        import cadquery as cq
        cq.exporters.export(result, filepath, cq.exporters.ExportTypes.STL,
                           tolerance=tolerance, angularTolerance=0.1)
        print(f"STL exported via CadQuery: {filepath}")


# ============================================================
# Part 3: rhino3dm Integration (NURBS Geometry & 3DM Format)
# ============================================================

class Rhino3dmIntegration:
    """
    Integration with rhino3dm (openNURBS) for NURBS geometry
    and .3dm format read/write.
    """

    @staticmethod
    def is_available() -> bool:
        return _rhino3dm is not None

    @staticmethod
    def create_nurbs_surface(control_points: np.ndarray, degree: int = 3,
                             weights: np.ndarray = None) -> Any:
        """Create a NURBS surface in rhino3dm."""
        if _rhino3dm is None:
            raise ImportError("rhino3dm not installed. Run: pip install rhino3dm")

        import rhino3dm

        n_u, n_v, _ = control_points.shape
        ns = rhino3dm.NurbsSurface(3, True, degree + 1, degree + 1, n_u, n_v)

        for i in range(n_u):
            for j in range(n_v):
                pt = control_points[i, j]
                w = float(weights[i, j]) if weights is not None else 1.0
                ns.Points[i][j] = rhino3dm.Point4d(
                    float(pt[0]), float(pt[1]), float(pt[2]), w
                )

        return ns

    @staticmethod
    def read_3dm(filepath: str) -> Any:
        """Read a .3dm file and return the model."""
        if _rhino3dm is None:
            raise ImportError("rhino3dm not installed. Run: pip install rhino3dm")

        import rhino3dm
        return rhino3dm.File3dm.Read(filepath)

    @staticmethod
    def write_3dm(model: Any, filepath: str, version: int = 7):
        """Write a .3dm model to file."""
        model.Write(filepath, version)
        print(f"3DM written: {filepath}")


# ============================================================
# Part 4: geomdl Integration (Pure Python NURBS)
# ============================================================

class GeomdlIntegration:
    """
    Integration with geomdl (NURBS-Python) for pure Python
    NURBS curve and surface operations.
    """

    @staticmethod
    def is_available() -> bool:
        return _geomdl is not None

    @staticmethod
    def create_nurbs_surface(control_points: np.ndarray, degree_u: int = 3,
                              degree_v: int = 3, weights: np.ndarray = None) -> Any:
        """Create a NURBS surface using geomdl."""
        if _geomdl is None:
            raise ImportError("geomdl not installed. Run: pip install geomdl")

        from geomdl import BSpline

        surf = BSpline.Surface()
        surf.degree_u = degree_u
        surf.degree_v = degree_v

        ctrl_pts = []
        for i in range(control_points.shape[0]):
            for j in range(control_points.shape[1]):
                pt = control_points[i, j].tolist()
                if weights is not None:
                    pt.append(float(weights[i, j]))
                else:
                    pt.append(1.0)
                ctrl_pts.append(pt)

        surf.ctrlpts2d = ctrl_pts
        return surf

    @staticmethod
    def evaluate_surface(surf: Any, n_samples: int = 80) -> np.ndarray:
        """Evaluate geomdl surface and return points array."""
        surf.sample_size = n_samples
        surf.evaluate()
        return np.array(surf.evalpts)

    @staticmethod
    def export_obj(surf: Any, filepath: str, n_samples: int = 80):
        """Export geomdl surface to OBJ format."""
        from geomdl import exchange_obj
        surf.sample_size = n_samples
        surf.evaluate()
        exchange_obj.export_surface(surf, filepath)
        print(f"OBJ exported via geomdl: {filepath}")


# ============================================================
# Part 5: Unified CAD Manager
# ============================================================

class CADManager:
    """
    Unified CAD platform manager.
    Provides a single entry point for all CAD operations.
    """

    def __init__(self):
        self.backends = get_available_backends()
        self._nurbs_surface = None

    def status(self) -> Dict[str, bool]:
        """Return available backends."""
        return self.backends

    def print_status(self):
        """Print backend status."""
        print_backend_status()

    def create_nurbs_surface(self, control_points: np.ndarray,
                              degree_u: int = 3, degree_v: int = 3,
                              weights: np.ndarray = None) -> UnifiedNURBSSurface:
        """Create a unified NURBS surface."""
        data = NURBSSurfaceData(
            control_points=control_points,
            degree_u=degree_u,
            degree_v=degree_v,
            weights=weights
        )
        self._nurbs_surface = UnifiedNURBSSurface(data)
        return self._nurbs_surface

    def export(self, surface: UnifiedNURBSSurface, filepath: str,
               backend: str = 'auto', **kwargs):
        """Export surface to file with auto-detection."""
        surface.export(filepath, backend=backend, **kwargs)

    def batch_export(self, surface: UnifiedNURBSSurface,
                     output_dir: str, formats: List[str] = None,
                     basename: str = 'car_body'):
        """
        Export surface to multiple formats.

        Args:
            surface: NURBS surface to export
            output_dir: Output directory
            formats: List of extensions ['.stl', '.step', '.igs', '.3dm']
            basename: Base filename
        """
        if formats is None:
            formats = ['.stl', '.step', '.igs']

        os.makedirs(output_dir, exist_ok=True)

        for fmt in formats:
            filepath = os.path.join(output_dir, basename + fmt)
            try:
                surface.export(filepath)
            except ImportError as e:
                print(f"  Skipped {fmt}: {e}")
            except Exception as e:
                print(f"  Error exporting {fmt}: {e}")

    # --- CadQuery Operations ---

    def create_solid_body(self, params: dict) -> Any:
        """Create a solid body using CadQuery."""
        return CadQueryIntegration.create_car_body_solid(params)

    def export_solid_step(self, solid: Any, filepath: str):
        """Export CadQuery solid to STEP."""
        CadQueryIntegration.export_step(solid, filepath)

    def export_solid_stl(self, solid: Any, filepath: str, tolerance: float = 0.001):
        """Export CadQuery solid to STL."""
        CadQueryIntegration.export_stl(solid, filepath, tolerance)

    # --- Rhino3dm Operations ---

    def read_rhino_file(self, filepath: str) -> Any:
        """Read a Rhino .3dm file."""
        return Rhino3dmIntegration.read_3dm(filepath)

    def write_rhino_file(self, model: Any, filepath: str, version: int = 7):
        """Write a Rhino .3dm file."""
        Rhino3dmIntegration.write_3dm(model, filepath, version)


# ============================================================
# Part 6: Convenience Functions
# ============================================================

def create_cad_manager() -> CADManager:
    """Create and return a CAD manager instance."""
    return CADManager()


def quick_export_nurbs(control_points: np.ndarray, output_dir: str,
                       basename: str = 'car_body',
                       degree: int = 3,
                       weights: np.ndarray = None,
                       formats: List[str] = None):
    """
    Quick export NURBS surface to multiple formats.

    Example:
        >>> pts = np.random.rand(20, 32, 3)  # 20x32 control points
        >>> quick_export_nurbs(pts, './output', formats=['.stl', '.step'])
    """
    mgr = create_cad_manager()
    surface = mgr.create_nurbs_surface(control_points, degree, degree, weights)
    mgr.batch_export(surface, output_dir, formats, basename)
    return surface


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    print_backend_status()

    # Demo: create a simple NURBS surface and export
    n_u, n_v = 10, 16
    control_points = np.zeros((n_u, n_v, 3))
    for i in range(n_u):
        for j in range(n_v):
            u = i / (n_u - 1)
            v = j / (n_v - 1)
            control_points[i, j] = [
                u * 4.84,                          # X: 0 to 4.84m
                0.14 + (1.45 - 0.14) * u * (1 - u) * 4,  # Y: car height profile
                (v - 0.5) * 1.83                    # Z: -0.915 to 0.915m
            ]

    mgr = create_cad_manager()
    surface = mgr.create_nurbs_surface(control_points)
    mgr.batch_export(surface, './cad_output')
