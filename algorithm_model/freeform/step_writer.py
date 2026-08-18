"""
STEP AP214 Writer — 纯 Python NURBS 曲面 → STEP 文件序列化

将 nurbs_surface_from_grid() / SweptSurface.build() 输出的 NURBS dict
序列化为 ISO 10303-21 (STEP) AP214 文件，可被 FreeCAD / CAD 软件打开。

零外部依赖（仅 numpy），无需 OCCT/build123d。

实体链：
  CARTESIAN_POINT (控制点)
  → B_SPLINE_SURFACE_WITH_KNOTS (+ RATIONAL_B_SPLINE_SURFACE 若权重≠1，复实例化)
  → B_SPLINE_CURVE_WITH_KNOTS (4 条边界曲线) → EDGE_CURVE → EDGE_LOOP
  → FACE_OUTER_BOUND → ADVANCED_FACE → OPEN_SHELL → SHELL_BASED_SURFACE_MODEL
  → MANIFOLD_SURFACE_SHAPE_REPRESENTATION → PRODUCT_DEFINITION_SHAPE → PRODUCT

边界曲线几何正确性：对开放均匀节点向量，曲面边界 = 边界控制点列定义的 B 样条曲线，
故 ADVANCED_FACE 的 EDGE_CURVE 精确落在曲面上。
"""

from typing import Optional, List, Tuple
import numpy as np


def _compress_knots(knot_vector) -> Tuple[List[int], List[float]]:
    """展开节点向量 → (multiplicities, distinct_values)

    [0,0,0,0,0.25,0.5,0.75,1,1,1,1] → ([4,1,1,1,4],[0.,0.25,0.5,0.75,1.])
    """
    knots = [float(k) for k in knot_vector]
    mults, distinct = [], []
    i, n = 0, len(knots)
    while i < n:
        k = knots[i]
        m = 1
        while i + m < n and abs(knots[i + m] - k) < 1e-9:
            m += 1
        mults.append(m)
        distinct.append(k)
        i += m
    return mults, distinct


def _f(x) -> str:
    v = float(x)
    return '0.' if v == 0.0 else repr(v)


def _li(xs) -> str:
    return '(' + ','.join(str(int(x)) for x in xs) + ')'


def _lr(xs) -> str:
    return '(' + ','.join(_f(x) for x in xs) + ')'


class StepWriter:
    """STEP AP214 文件写入器"""

    def __init__(self):
        self._data: List[str] = []
        self._next_id = 1

    def _id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    def _emit(self, eid: int, body: str):
        self._data.append(f"#{eid} = {body};")

    # ---------- 几何基元 ----------
    def cartesian_point(self, x, y, z) -> int:
        i = self._id()
        self._emit(i, f"CARTESIAN_POINT('',({_f(x)},{_f(y)},{_f(z)}))")
        return i

    def direction(self, dx, dy, dz) -> int:
        i = self._id()
        self._emit(i, f"DIRECTION('',({_f(dx)},{_f(dy)},{_f(dz)}))")
        return i

    def axis2_placement_3d(self, origin_id, axis_id, ref_id) -> int:
        i = self._id()
        self._emit(i, f"AXIS2_PLACEMENT_3D('',#{origin_id},#{axis_id},#{ref_id})")
        return i

    def vertex_point(self, point_id) -> int:
        i = self._id()
        self._emit(i, f"VERTEX_POINT('',#{point_id})")
        return i

    def edge_curve(self, v1, v2, curve_id) -> int:
        i = self._id()
        self._emit(i, f"EDGE_CURVE('',#{v1},#{v2},#{curve_id},.T.)")
        return i

    def oriented_edge(self, edge_id, orient=True) -> int:
        i = self._id()
        self._emit(i, f"ORIENTED_EDGE('',*,*,#{edge_id},{'.T.' if orient else '.F.'})")
        return i

    def edge_loop(self, oriented_edges) -> int:
        i = self._id()
        self._emit(i, f"EDGE_LOOP('',({','.join(f'#{e}' for e in oriented_edges)}))")
        return i

    def face_outer_bound(self, loop_id, same_sense=True) -> int:
        i = self._id()
        self._emit(i, f"FACE_OUTER_BOUND('',#{loop_id},{'.T.' if same_sense else '.F.'})")
        return i

    # ---------- B-spline 曲线（边界）----------
    def bspline_curve(self, cp_ids: List[int], degree: int,
                      knot_vector, weights: Optional[List[float]] = None) -> int:
        """degree/控制点数/knots 严格遵循 ISO 10303-42 b_spline_curve 属性序。"""
        mults, distinct = _compress_knots(knot_vector)
        deg = min(int(degree), len(cp_ids) - 1)
        cp_refs = ','.join(f'#{c}' for c in cp_ids)
        bsp_body = (f"B_SPLINE_CURVE_WITH_KNOTS('',{deg},({cp_refs}),"
                    f".UNSPECIFIED.,.F.,.F.,{_li(mults)},{_lr(distinct)},.UNSPECIFIED.)")
        bsp = self._id()
        rational = weights is not None and any(abs(w - 1.0) > 1e-9 for w in weights)
        if rational:
            rat_body = f"RATIONAL_B_SPLINE_CURVE('',({_lr(weights)}))"
            self._data.append(f"#{bsp} = ({bsp_body} + {rat_body});")
        else:
            self._emit(bsp, bsp_body)
        return bsp

    # ---------- B-spline 曲面 ----------
    def _nurbs_surface(self, surf: dict) -> Tuple[int, np.ndarray]:
        """写曲面实体（复实例化处理有理），返回 (surface_id, cp_ids[n_u,n_v])。"""
        cps = np.asarray(surf['control_points'])   # (n_u, n_v, 3)
        weights = np.asarray(surf['weights'])
        p, q = int(surf['degree'][0]), int(surf['degree'][1])
        ku, kv = np.asarray(surf['knots_u']), np.asarray(surf['knots_v'])
        n_u, n_v = cps.shape[0], cps.shape[1]

        cp_ids = np.zeros((n_u, n_v), dtype=int)
        for i in range(n_u):
            for j in range(n_v):
                cp_ids[i, j] = self.cartesian_point(cps[i, j, 0], cps[i, j, 1], cps[i, j, 2])

        cp_lists = ','.join(
            '(' + ','.join(f'#{cp_ids[i, j]}' for j in range(n_v)) + ')'
            for i in range(n_u)
        )
        mu, du = _compress_knots(ku)
        mv, dv = _compress_knots(kv)
        bsp = self._id()
        bsp_body = (f"B_SPLINE_SURFACE_WITH_KNOTS('',{p},{q},({cp_lists}),"
                    f".UNSPECIFIED.,.F.,.F.,.F.,"
                    f"{_li(mu)},{_li(mv)},{_lr(du)},{_lr(dv)},.UNSPECIFIED.)")
        rational = bool(np.any(np.abs(weights - 1.0) > 1e-9))
        if rational:
            wl = ','.join('(' + ','.join(_f(weights[i, j]) for j in range(n_v)) + ')'
                          for i in range(n_u))
            rat_body = f"RATIONAL_B_SPLINE_SURFACE('',({wl}))"
            self._data.append(f"#{bsp} = ({bsp_body} + {rat_body});")
        else:
            self._emit(bsp, bsp_body)
        return bsp, cp_ids

    def _advanced_face(self, surf: dict, surface_id: int, cp_ids: np.ndarray) -> int:
        """用 4 条边界 B 样条曲线构造 EDGE_LOOP → ADVANCED_FACE。

        边界与曲面精确对应（开放均匀节点向量下曲面过边界控制点）：
          bottom : v=0, u:0→1   控制 P[:,0],     deg p, knots_u
          right  : u=1, v:0→1   控制 P[-1,:],    deg q, knots_v
          top    : v=1, u:1→0   控制 P[:,-1]逆向, deg p, knots_u
          left   : u=0, v:1→0   控制 P[0,:]逆向,  deg q, knots_v
        """
        n_u, n_v = cp_ids.shape
        p, q = int(surf['degree'][0]), int(surf['degree'][1])
        ku, kv = surf['knots_u'], surf['knots_v']

        c_bot = self.bspline_curve([cp_ids[i, 0] for i in range(n_u)], p, ku)
        c_rgt = self.bspline_curve([cp_ids[n_u - 1, j] for j in range(n_v)], q, kv)
        c_top = self.bspline_curve([cp_ids[i, n_v - 1] for i in range(n_u - 1, -1, -1)], p, ku)
        c_lft = self.bspline_curve([cp_ids[0, j] for j in range(n_v - 1, -1, -1)], q, kv)

        v1 = self.vertex_point(cp_ids[0, 0])
        v2 = self.vertex_point(cp_ids[n_u - 1, 0])
        v3 = self.vertex_point(cp_ids[n_u - 1, n_v - 1])
        v4 = self.vertex_point(cp_ids[0, n_v - 1])

        e1 = self.edge_curve(v1, v2, c_bot)
        e2 = self.edge_curve(v2, v3, c_rgt)
        e3 = self.edge_curve(v3, v4, c_top)
        e4 = self.edge_curve(v4, v1, c_lft)
        oe = [self.oriented_edge(e) for e in (e1, e2, e3, e4)]
        loop = self.edge_loop(oe)
        bound = self.face_outer_bound(loop, True)

        face = self._id()
        self._emit(face, f"ADVANCED_FACE('',(#{bound}),#{surface_id},.T.)")
        return face

    # ---------- 产品/表示上下文 ----------
    def _context(self) -> Tuple[int, int]:
        ac = self._id()
        self._emit(ac, "APPLICATION_CONTEXT('automotive design')")
        apd = self._id()
        self._emit(apd,
                   f"APPLICATION_PROTOCOL_DEFINITION('international standard',"
                   f"'automotive_design',2003,#{ac})")
        length = self._id()
        self._emit(length, "(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.))")
        plane = self._id()
        self._emit(plane, "(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.))")
        solid = self._id()
        self._emit(solid, "(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT())")
        unc = self._id()
        self._emit(unc, f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-06),#{length},'','')")
        ctx = self._id()
        self._emit(ctx,
                   f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)"
                   f"GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{unc}))"
                   f"GLOBAL_UNIT_ASSIGNED_CONTEXT((#{length},#{plane},#{solid}))"
                   f"REPRESENTATION_CONTEXT('Context','3D'))")
        return ctx, ac

    def _product(self, name: str, ac: int) -> int:
        pctx = self._id()
        self._emit(pctx, f"PRODUCT_CONTEXT('',#{ac},'mechanical')")
        prod = self._id()
        self._emit(prod, f"PRODUCT('{name}','{name}','',#{pctx})")
        pdf = self._id()
        self._emit(pdf, f"PRODUCT_DEFINITION_FORMATION('','',#{prod})")
        pdc = self._id()
        self._emit(pdc, f"PRODUCT_DEFINITION_CONTEXT('part definition',#{ac},'design')")
        pd = self._id()
        self._emit(pd, f"PRODUCT_DEFINITION('design','',#{pdf},#{pdc})")
        pds = self._id()
        self._emit(pds, f"PRODUCT_DEFINITION_SHAPE('','',#{pd})")
        return pds

    # ---------- 高层入口 ----------
    def add_surface_as_product(self, surf: dict, name: str = 'surface') -> int:
        """写一个完整可被 CAD 软件显示的 NURBS 曲面产品，返回 surface 实体 ID。"""
        surface_id, cp_ids = self._nurbs_surface(surf)
        face_id = self._advanced_face(surf, surface_id, cp_ids)
        shell = self._id()
        self._emit(shell, f"OPEN_SHELL('',(#{face_id},))")
        sbm = self._id()
        self._emit(sbm, f"SHELL_BASED_SURFACE_MODEL('',(#{shell},))")
        ctx, ac = self._context()
        origin = self.cartesian_point(0., 0., 0.)
        az = self.direction(0., 0., 1.)
        ax = self.direction(1., 0., 0.)
        axis = self.axis2_placement_3d(origin, az, ax)
        rep = self._id()
        self._emit(rep, f"MANIFOLD_SURFACE_SHAPE_REPRESENTATION('',(#{sbm},#{axis}),#{ctx})")
        pds = self._product(name, ac)
        sdr = self._id()
        self._emit(sdr, f"SHAPE_DEFINITION_REPRESENTATION(#{pds},#{rep})")
        return surface_id

    # ---------- 文件输出 ----------
    def write_file(self, filename: str, description: str = 'EVOLUTION AI NURBS surface') -> int:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        header = (
            "ISO-10303-21;\n"
            "HEADER;\n"
            f"FILE_DESCRIPTION(('{description}'),'2;1');\n"
            f"FILE_NAME('{filename}','{now}',('EVOLUTION-AI'),('EVOLUTION-AI'),"
            "'step_writer.py','EVOLUTION-AI','');\n"
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\n"
            "ENDSEC;\n"
            "DATA;\n"
        )
        body = '\n'.join(self._data) + '\n'
        footer = "ENDSEC;\nEND-ISO-10303-21;\n"
        with open(filename, 'w', encoding='ascii') as f:
            f.write(header + body + footer)
        return len(self._data)


def write_nurbs_surface_step(surf: dict, filename: str, name: str = 'surface') -> dict:
    """便捷接口：NURBS dict → STEP 文件。返回统计信息。"""
    w = StepWriter()
    w.add_surface_as_product(surf, name)
    n = w.write_file(filename)
    return {'file': filename, 'entity_count': n}
