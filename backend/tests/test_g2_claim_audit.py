# -*- coding: utf-8 -*-
"""验证「degree>=3 就代表 G2 连续」这一断言是错的

背景
----
Coze 云盘内的 `industrial_car_body_generator.py` 的 `generate_topology_validation()`
用如下方式判定 182 对相邻曲面的 G1/G2：

    g1_pass = True; g2_pass = True          # 硬编码
    if s1.u_degree < 3 or s1.v_degree < 3:  # 只检查阶数
        g1_pass = False; g2_pass = False

即「三阶以上曲面 ⇒ G1/G2 连续」。该推理在几何上不成立：
**曲面自身的次数只决定其内部光滑性，与两张独立曲面之间的连续性无关。**

本测试用解析曲面证明这一点：两张都是三次（甚至更高次）的曲面，
其曲率可以完全不同，因此必然不满足 G2。
"""
import math

import pytest

np = pytest.importorskip("numpy")

from app.geometry_curvature import (  # noqa: E402
    check_g2_curvature,
    principal_curvatures,
)


def _cyl(R):
    """圆柱面（双三次曲面即可精确表示）：主曲率 1/R 与 0"""
    return lambda u, v: np.array([R * math.cos(u), R * math.sin(u), v])


def _sph(R):
    """球面：主曲率 1/R 与 1/R"""
    return lambda u, v: np.array([R * math.cos(v) * math.cos(u),
                                  R * math.cos(v) * math.sin(u),
                                  R * math.sin(v)])


def test_same_degree_different_curvature_is_not_g2():
    """两个「高阶」曲面曲率不同 → 必须判 G2 不通过

    这正是原实现无法发现的情形：它只看 degree，两者都是 3 阶就判通过。
    """
    a = principal_curvatures(_cyl(1.5), 0.5, 0.3)      # κ = 1/1.5 = 0.6667
    b = principal_curvatures(_cyl(4.0), 0.5, 0.3)      # κ = 1/4.0 = 0.25
    r = check_g2_curvature(a["k1"], b["k1"])

    assert not r.passed, "曲率不同却判 G2 通过 —— 说明判定逻辑有误"
    assert r.curvature_ratio == pytest.approx(0.6667 / 0.25, rel=1e-3)


def test_sphere_vs_cylinder_is_not_g2():
    """球面与圆柱面：即使都可为三次曲面，曲率不同 → 不满足 G2"""
    s = principal_curvatures(_sph(2.0), 0.7, 0.4)
    c = principal_curvatures(_cyl(2.0), 0.5, 0.3)
    # 球面 κ1 = 0.5；圆柱 κ1 = 0.5（相同）但 κ2 不同
    r1 = check_g2_curvature(s["k1"], c["k1"])
    r2 = check_g2_curvature(s["k2"], c["k2"])
    # 至少有一个主方向曲率不同 → 整体不可能 G2 连续
    assert not (r1.passed and r2.passed), (
        "球面与圆柱不可能 G2 连续：κ2 一个为 0.5 一个为 0"
    )


def test_flat_vs_curved_not_g2():
    """平整面 vs 弯曲面：曲率变化无限大 → 不满足 G2"""
    flat = principal_curvatures(lambda u, v: np.array([u, v, 0.0]), 0.3, 0.5)
    curved = principal_curvatures(_cyl(1.0), 0.5, 0.3)
    r = check_g2_curvature(flat["k1"], curved["k1"])
    assert not r.passed


def test_same_surface_adjacent_points_is_g2():
    """同一曲面相邻点必须判 G2 通过（曲率连续）——对照组"""
    fn = _cyl(2.0)
    a = principal_curvatures(fn, 0.5, 0.3)
    b = principal_curvatures(fn, 0.5, 0.301)
    r = check_g2_curvature(a["k1"], b["k1"])
    assert r.passed
    assert r.curvature_ratio == pytest.approx(1.0, abs=1e-3)


def test_degree_alone_cannot_imply_g2():
    """把「只看阶数」与「真实曲率」并置，凸显前者不可用

    两张曲面取相同阶数（3 阶，B 样条可精确表示圆柱/球面），
    但真实曲率差 2.67 倍 → 真实判定必须拒绝。
    """
    a = principal_curvatures(_cyl(1.5), 0.5, 0.3)
    b = principal_curvatures(_cyl(4.0), 0.5, 0.3)
    deg_a = deg_b = 3          # 同为三次

    # 原实现的逻辑：阶数都 ≥3 → 判通过
    legacy_g2 = not (deg_a < 3 or deg_b < 3)
    # 真实判定
    real_g2 = check_g2_curvature(a["k1"], b["k1"]).passed

    assert legacy_g2 is True, "复现原实现的结论"
    assert real_g2 is False, "真实曲率判定必须拒绝"
    assert legacy_g2 != real_g2, "两者必须不同——证明原实现不可信"
