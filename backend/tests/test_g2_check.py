"""G2 曲率连续性检测测试

覆盖：
- 格式转换：car_generator NURBS dict → nurbs_core dict
- 空模型/缺数据场景（最常见的真实场景）
- 两平面（曲率均 0 → G2 通过）
- 报告结构完整性
"""
import json

import pytest

np = pytest.importorskip("numpy")

from app.g2_check import (
    ADJACENT_PAIRS,
    _car_surface_to_nurbs_dict,
    _default_knots,
    _extract_named_surfaces,
    run_g2_check,
    run_g2_check_from_model,
)


# ---------------------------------------------------------------------------
# 构造最小 NURBS 曲面（flat plane 作为可复用的测试夹具）
# ---------------------------------------------------------------------------
def _flat_plane(name: str, z: float = 0.0, n_u: int = 4, n_v: int = 4):
    """返回 car_generator 格式的平面 NURBS 曲面 dict"""
    cps = [[{"x": float(i), "y": float(j), "z": z, "weight": 1.0}
            for j in range(n_v)]
           for i in range(n_u)]
    return {
        "name": name,
        "type": "panel",
        "surface": {
            "degree_u": 3,
            "degree_v": 3,
            "control_points": cps,
            "knot_vector_u": _default_knots(n_u, 3).tolist(),
            "knot_vector_v": _default_knots(n_v, 3).tolist(),
        },
        "color": "#c0c0c0",
    }


def _spherical_surface(name: str, radius: float = 2.0, n_u: int = 8, n_v: int = 8):
    """球面（全方向 κ=1/R，无法通过选边回避曲率差异）"""
    import math
    cps = []
    for i in range(n_u):
        u = 2 * math.pi * i / max(n_u - 1, 1)
        row = []
        for j in range(n_v):
            v = math.pi * j / max(n_v - 1, 1) - math.pi / 2
            row.append({
                "x": radius * math.cos(v) * math.cos(u),
                "y": radius * math.cos(v) * math.sin(u),
                "z": radius * math.sin(v),
                "weight": 1.0,
            })
        cps.append(row)
    return {
        "name": name,
        "type": "panel",
        "surface": {
            "degree_u": 3,
            "degree_v": 3,
            "control_points": cps,
            "knot_vector_u": _default_knots(n_u, 3).tolist(),
            "knot_vector_v": _default_knots(n_v, 3).tolist(),
        },
        "color": "#c0c0c0",
    }


# ---------------------------------------------------------------------------
# 单元测试：格式转换
# ---------------------------------------------------------------------------
def test_surface_conversion_preserves_geometry():
    """转换后 nurbs_core 求值应与原始 car_generator 预期一致（平面 z=5）"""
    raw = _flat_plane("test", z=5.0, n_u=4, n_v=4)
    converted = _car_surface_to_nurbs_dict(raw["surface"])
    assert converted is not None
    assert converted["n"] == (4, 4)
    assert converted["degree"] == (3, 3)
    assert converted["control_points"].shape == (4, 4, 3)
    # 所有控制点 z 应为 5.0
    assert converted["control_points"][:, :, 2].max() == pytest.approx(5.0, abs=1e-9)
    assert converted["weights"].shape == (4, 4)


def test_default_knots_shape():
    """clamped 均匀节点矢量长度应为 n + p + 1"""
    for n, p in [(4, 3), (6, 3), (10, 3)]:
        kv = _default_knots(n, p)
        assert len(kv) == n + p + 1
        assert kv[0] == 0.0 and kv[-1] == 1.0


def test_extract_named_surfaces_filters_correctly():
    """只有带 surface + control_points 的组件才应被提取"""
    car = {
        "components": [
            {"name": "有曲面", "surface": _flat_plane("有曲面")["surface"]},
            {"name": "无曲面"},
            {"name": "有points但无surface", "points": []},
        ]
    }
    out = _extract_named_surfaces(car)
    assert set(out) == {"有曲面"}


# ---------------------------------------------------------------------------
# 集成测试：G2 检测
# ---------------------------------------------------------------------------
def test_g2_check_two_flat_planes_pass():
    """两平面（曲率均为 0）→ G2 应通过（平坦视为连续）"""
    # 在 ADJACENT_PAIRS 中找一对名称，构造对应组件
    name_a, name_b, seam = ADJACENT_PAIRS[0]
    car = {
        "components": [
            _flat_plane(name_a, z=0.0, n_u=5, n_v=5),
            _flat_plane(name_b, z=0.0, n_u=5, n_v=5),
        ]
    }
    r = run_g2_check(car)
    assert "overall_g2_pass" in r
    assert r["n_pairs"] == len(ADJACENT_PAIRS)
    # 只有这一对完成了评估（其余缺数据）
    evaluated = [p for p in r["pairs"] if p["status"] != "no_data"]
    assert len(evaluated) == 1
    assert evaluated[0]["g2_pass"] is True
    assert evaluated[0]["status"] == "pass"


def test_g2_check_missing_surfaces_marked_no_data():
    """缺数据时必须报 no_data，不得静默视为通过"""
    car = {"components": []}
    r = run_g2_check(car)
    assert r["n_no_data"] == len(ADJACENT_PAIRS)
    assert r["n_pass"] == 0
    assert r["overall_g2_pass"] is False
    for p in r["pairs"]:
        assert p["status"] == "no_data"
        assert p["g2_pass"] is None


def test_g2_check_from_empty_json_returns_error():
    """car_data_json 为空时应返回明确错误，不抛异常"""
    r = run_g2_check_from_model("")
    assert "error" in r
    assert "无车身数据" in r["error"]
    assert r["overall_g2_pass"] is None


def test_g2_check_report_structure():
    """报告结构必须包含全部预期字段"""
    name_a, name_b, seam = ADJACENT_PAIRS[0]
    car = {
        "components": [
            _flat_plane(name_a, z=0.0, n_u=5, n_v=5),
            _flat_plane(name_b, z=0.0, n_u=5, n_v=5),
        ]
    }
    r = run_g2_check(car)
    assert set(r) >= {
        "overall_g2_pass", "n_pairs", "n_pass", "n_fail",
        "n_no_data", "pass_rate", "pairs", "threshold", "standard",
    }
    pair = r["pairs"][0]
    assert set(pair) >= {
        "pair", "seam", "g2_pass", "curvature_ratio",
        "detail", "status",
    }


def test_g2_different_radius_spheres_fail():
    """不同半径球面（κ=1/R1 vs κ=1/R2）→ 曲率比超标，应 FAIL

    用 R=1.5 与 R=4.0：曲率比 = 4.0/1.5 ≈ 2.67，远超 1.2 上限。
    球面全方向曲率相同，无法通过选边回避差异。
    """
    name_a, name_b, seam = ADJACENT_PAIRS[0]
    car = {
        "components": [
            _spherical_surface(name_a, radius=1.5, n_u=8, n_v=8),
            _spherical_surface(name_b, radius=4.0, n_u=8, n_v=8),
        ]
    }
    r = run_g2_check(car)
    evaluated = [p for p in r["pairs"] if p["status"] != "no_data"]
    assert len(evaluated) >= 1
    assert evaluated[0]["g2_pass"] is False
    assert evaluated[0]["curvature_ratio"] is not None
    assert evaluated[0]["curvature_ratio"] > 1.2
