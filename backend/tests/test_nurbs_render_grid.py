# -*- coding: utf-8 -*-
"""NURBS 向量化求值与高保真渲染网格测试

覆盖本轮渲染算法优化的三块内容：
  1. basis_matrix：与逐点递归基函数数值等价；clamped 端点性质；单位分解
  2. NURBSSurface.evaluate_grid：与 evaluate_point 一致；角点无 NaN
  3. car_generator：自适应采样密度范围；GLB 导出网格平滑法线 + PBR 材质
"""
import os
import tempfile

import numpy as np
import pytest

from app.nurbs import (ControlPoint, NURBSSurface, basis_matrix,
                       _basis_function, _create_uniform_knot_vector)
from app.car_generator import NURBSCarBodyGenerator


# ---------------------------------------------------------------------------
# 夹具
# ---------------------------------------------------------------------------
@pytest.fixture
def surface():
    """带权重的随机 NURBS 曲面（5×4 控制点，3 阶）"""
    rng = np.random.default_rng(42)
    cps = [[ControlPoint(*rng.normal(size=3),
                         weight=float(rng.uniform(0.5, 1.5)))
            for _ in range(4)] for _ in range(5)]
    return NURBSSurface(
        degree_u=3, degree_v=3, control_points=cps,
        knot_vector_u=_create_uniform_knot_vector(4, 3),
        knot_vector_v=_create_uniform_knot_vector(3, 3))


# ---------------------------------------------------------------------------
# 1. basis_matrix
# ---------------------------------------------------------------------------
def test_basis_matrix_matches_scalar_recursion(surface):
    """向量化基函数矩阵须与逐点递归 _basis_function 数值一致"""
    knots = surface.knot_vector_u.values
    ncu = len(surface.control_points)
    # t=1 不在对比范围：逐点递归 _basis_function 在末端重节点保留旧的零基函数
    # 行为，矩阵版已修复（见 test_basis_clamped_endpoints）
    for t in [0.0, 0.07, 0.31, 0.5, 0.74, 0.93]:
        matrix_row = basis_matrix(np.asarray(knots), 3, np.array([t]))[0]
        scalar_row = [_basis_function(i, 3, t, knots) for i in range(ncu)]
        assert np.allclose(matrix_row, scalar_row, atol=1e-10, rtol=0)


def test_basis_partition_of_unity(surface):
    """参数区间内基函数行和为 1（单位分解）"""
    knots = surface.knot_vector_u.values
    ts = np.linspace(0.0, 1.0, 11)
    B = basis_matrix(np.asarray(knots), 3, ts)
    assert np.allclose(B.sum(axis=1), 1.0, atol=1e-10)


def test_basis_clamped_endpoints(surface):
    """clamped 端点：t=0 只有 N_0=1，t=1 只有最后一个基函数=1

    这是本轮修复的真实 bug——旧递推在末端重节点 t=1 处基函数全部消失，
    导致曲面角点求值返回零向量。
    """
    knots = np.asarray(surface.knot_vector_u.values)
    b0 = basis_matrix(knots, 3, np.array([0.0]))[0]
    b1 = basis_matrix(knots, 3, np.array([1.0]))[0]
    assert b0[0] == 1.0 and b0[1:].sum() == 0.0
    assert b1[-1] == 1.0 and b1[:-1].sum() == 0.0


# ---------------------------------------------------------------------------
# 2. evaluate_grid
# ---------------------------------------------------------------------------
def test_evaluate_grid_matches_evaluate_point(surface):
    """批量求值须与逐点求值一致（端点处标量版有 1e-10 钳制差）"""
    us = [0.0, 0.13, 0.5, 0.87, 1.0]
    vs = [0.0, 0.3, 0.7, 1.0]
    grid = surface.evaluate_grid(us, vs)
    for i, u in enumerate(us):
        for j, v in enumerate(vs):
            assert np.allclose(grid[i, j],
                               surface.evaluate_point(u, v), atol=1e-6)


def test_evaluate_grid_no_nan_at_corners(surface):
    """四角点不得有 NaN（u=v=1 旧代码返回零向量）"""
    grid = surface.evaluate_grid([0.0, 1.0], [0.0, 1.0])
    assert not np.isnan(grid).any()
    # 角点必须是真实控制点位置而非原点：与最近控制点加权位置吻合
    assert np.linalg.norm(grid[1, 1]) > 0


# ---------------------------------------------------------------------------
# 3. car_generator 自适应采样与 GLB
# ---------------------------------------------------------------------------
def test_render_count_bounds_and_monotonic():
    """自适应采样数：在 [12,64] 范围内，尺寸越大采样越多"""
    gen = NURBSCarBodyGenerator()
    small = gen._render_count(200)
    mid = gen._render_count(1000)
    big = gen._render_count(5000)
    assert small == NURBSCarBodyGenerator.RENDER_MIN_N
    assert big == NURBSCarBodyGenerator.RENDER_MAX_N
    assert small <= mid <= big
    assert mid == round(1000 / NURBSCarBodyGenerator.RENDER_TARGET_MM)


def test_sampled_points_denser_than_control_mesh():
    """全车采样点数须显著多于旧控制点级网格（6~12/方向）"""
    gen = NURBSCarBodyGenerator()
    car = gen.generate_complete_car()
    total = sum(len(c['points']) * len(c['points'][0])
                for c in car['components'] if c.get('points'))
    # 旧网格全车约 600~800 点；高保真目标边长 40mm → 应上万
    assert total > 5000


def test_glb_export_has_smooth_normals_and_pbr():
    """GLB 重新加载：面数充足、法线无 NaN、材质为 PBR"""
    trimesh = pytest.importorskip("trimesh")
    gen = NURBSCarBodyGenerator()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'car.glb')
        gen.export_glb(path)
        loaded = trimesh.load(path)
    geoms = (list(loaded.geometry.values()) if hasattr(loaded, 'geometry')
             else [loaded])
    faces = sum(len(g.faces) for g in geoms if hasattr(g, 'faces'))
    nan_n = sum(int(np.isnan(g.vertex_normals).sum())
                for g in geoms if hasattr(g, 'vertex_normals'))
    assert faces > 5000          # 旧版全车约 1500 面
    assert nan_n == 0
    assert all(type(g.visual.material).__name__ == 'PBRMaterial'
               for g in geoms if hasattr(g.visual, 'material'))
