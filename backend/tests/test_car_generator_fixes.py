# -*- coding: utf-8 -*-
"""既有车身生成器的两项关键修正测试

对应本轮发现并修复的两个真实缺陷：
  1. **参数注入断链**：API 接受 `params_override` 但从未传给生成器
  2. **伪造质量声明**：`nurbs_quality.g2_continuous` 硬编码为 True

这两项都属于"声称而非测量 / 接口与实现不符"，必须有测试锁住。
"""
import numpy as np
import pytest

from app.car_generator import NURBSCarBodyGenerator


@pytest.fixture(scope="module")
def gen():
    return NURBSCarBodyGenerator()


def _hood(gen, **kw):
    car = gen.generate_complete_car(**kw)
    for c in car["components"]:
        if c.get("name") == "发动机盖" and "surface" in c:
            return np.array([[[p["x"], p["y"], p["z"]] for p in row]
                             for row in c["surface"]["control_points"]])
    raise AssertionError("未找到发动机盖曲面")


def _trunk(gen, **kw):
    car = gen.generate_complete_car(**kw)
    for c in car["components"]:
        if c.get("name") == "行李箱盖" and "surface" in c:
            return np.array([[[p["x"], p["y"], p["z"]] for p in row]
                             for row in c["surface"]["control_points"]])
    raise AssertionError("未找到行李箱盖曲面")


# ---------------------------------------------------------------------------
# 1. 参数注入
# ---------------------------------------------------------------------------
def test_resolve_overrides_maps_flat_keys_to_groups():
    """扁平参数名应能被解析到正确分组"""
    out = NURBSCarBodyGenerator.resolve_overrides(
        {"overall_length": 5500, "hood_length": 1500})
    assert "整车尺寸" in out and out["整车尺寸"]["overall_length"] == 5500
    assert "车身部件" in out and out["车身部件"]["hood_length"] == 1500


def test_resolve_overrides_ignores_unknown_keys():
    """未知参数名应被安全忽略，不抛异常"""
    out = NURBSCarBodyGenerator.resolve_overrides({"not_a_real_param": 1})
    assert out == {}
    assert NURBSCarBodyGenerator.resolve_overrides(None) == {}


# ---------------------------------------------------------------------------
# 1b. 前端字段名对接（前端 carPresets.js 与后端命名不一致）
# ---------------------------------------------------------------------------
FRONTEND_SEDAN = {
    "overall_length": 4950, "overall_width": 1880, "overall_height": 1460,
    "wheel_base": 2890, "track_width": 1600, "ground_clearance": 140,
    "hood_length": 1050, "roof_height": 550, "wheel_diameter": 680,
    "windshield_angle": 35, "rear_window_angle": 28, "rear_slant_angle": 18,
    "front_overhang": 950, "rear_overhang": 1110,
}


def test_all_frontend_fields_map_to_backend_params():
    """前端 14 个字段应**全部**能映射到后端参数（否则滑杆静默失效）"""
    out = NURBSCarBodyGenerator.resolve_overrides(FRONTEND_SEDAN)
    names = {k for items in out.values() for k in items}
    assert len(names) == len(FRONTEND_SEDAN), (
        f"仅 {len(names)}/{len(FRONTEND_SEDAN)} 个前端字段映射成功: {names}"
    )


def test_naming_differences_are_aliased():
    """纯命名差异必须被别名处理"""
    out = NURBSCarBodyGenerator.resolve_overrides(
        {"wheel_base": 2890, "front_overhang": 950, "rear_overhang": 1110})
    flat = {k: v for items in out.values() for k, v in items.items()}
    assert flat.get("wheelbase") == 2890
    assert flat.get("overhang_front") == 950
    assert flat.get("overhang_rear") == 1110
    assert "wheel_base" not in flat, "原名不应残留"


def test_roof_height_goes_to_roof_length_not_thickness():
    """**同名不同义陷阱**：前端 roof_height 是车顶纵向跨度，
    后端 roof_height 是车顶板厚度（30~100mm）。

    若按原名注入，850 会被当成板厚，量级错 10 倍以上。
    必须映射到 roof_length。
    """
    out = NURBSCarBodyGenerator.resolve_overrides({"roof_height": 850})
    flat = {k: v for items in out.values() for k, v in items.items()}
    assert flat.get("roof_length") == 850, f"未映射到 roof_length: {flat}"
    assert "roof_height" not in flat, "不应注入后端 roof_height（板厚语义）"


def test_frontend_payload_changes_geometry(gen):
    """**端到端**：用前端真实载荷应真正改变几何"""
    a = _hood(gen)
    b = _hood(gen, params_override=dict(FRONTEND_SEDAN))
    assert not np.allclose(a, b), "前端载荷未改变几何"


def test_schema_accepts_frontend_field_names():
    """`CarGenerateRequest` 必须接受前端发送的 car_type / params / color

    Pydantic 会**静默忽略**未知字段，此前 params 就是这样被丢掉的。
    """
    from app.schemas import CarGenerateRequest
    r = CarGenerateRequest(car_type="sedan", params={"overall_length": 4950},
                           color="#000000")
    assert r.params_override == {"overall_length": 4950}, (
        "params 未被映射到 params_override"
    )


def test_schema_params_override_takes_precedence():
    """同时给出时 params_override 优先，其余从 params 补齐"""
    from app.schemas import CarGenerateRequest
    r = CarGenerateRequest(params={"a": 1, "b": 2}, params_override={"b": 9})
    assert r.params_override == {"a": 1, "b": 9}


def test_different_car_types_produce_different_geometry(gen):
    """不同车型参数必须产生不同几何（前端车型切换应有效）"""
    sedan = {"overall_length": 4950, "hood_length": 1050}
    suv = {"overall_length": 5050, "hood_length": 1150}
    a = _hood(gen, params_override=sedan)
    b = _hood(gen, params_override=suv)
    assert not np.allclose(a, b)


def test_flat_override_actually_changes_geometry(gen):
    """**核心**：扁平格式覆盖必须真正改变几何（此前 API 传参完全无效）"""
    a = _hood(gen)
    b = _hood(gen, params_override={"overall_length": 5500, "hood_length": 1500})
    assert not np.allclose(a, b), "传入参数后几何未变化 —— 参数链路仍断"


def test_override_without_affecting_hood_only_moves_trunk(gen):
    """只改 overall_length 时：机盖**形状**不变（由 hood_length 决定）且居中，
    尾箱随之移动。

    注意：坐标已统一为**车身中心为原点**，故改车长会使所有零件在 X 上整体
    平移。因此这里比较的是机盖的**跨度**（形状），而非绝对 X 位置。
    """
    h0, t0 = _hood(gen), _trunk(gen)
    h1, t1 = _hood(gen, params_override={"overall_length": 5500}), \
        _trunk(gen, params_override={"overall_length": 5500})

    span0 = float(h0[:, :, 0].max() - h0[:, :, 0].min())
    span1 = float(h1[:, :, 0].max() - h1[:, :, 0].min())
    assert span0 == pytest.approx(span1, abs=1.0), (
        f"机盖跨度随车长改变（{span0} → {span1}），说明 hood_length 未生效"
    )
    # 机盖应居中于新的车身坐标系
    assert h1[:, :, 0].mean() == pytest.approx(-(5500 / 2 - 200 - span1 / 2),
                                              abs=span1 * 0.6)
    # 尾箱应相对机盖后移（X 增大）
    assert float(t1[:, :, 0].mean()) > float(t0[:, :, 0].mean()), \
        "车长增加后尾箱未后移"


def test_all_parts_use_canonical_axes(gen):
    """所有曲面必须落在规范坐标系内：X≈[−L/2,L/2]，Y≈[−W/2,W/2]，Z≥0

    这是坐标规范化的**核心验收**——此前发动机盖被建在 Y-Z 平面
    （高度写在 Y、宽度写在 Z），渲染成一片竖板。
    """
    car = gen.generate_complete_car()
    L, W = float(gen.L), float(gen.W)
    tol = 0.12
    for c in car["components"]:
        s = c.get("surface")
        if not s or "control_points" not in s:
            continue
        pts = np.array([[p["x"], p["y"], p["z"]] for row in s["control_points"]
                        for p in row])
        name = c.get("name")
        # X 落在 ±L/2 加余量内
        assert pts[:, 0].min() > -L / 2 * (1 + tol), f"{name} X 过小"
        assert pts[:, 0].max() < L / 2 * (1 + tol), f"{name} X 过大"
        # Y 不得超过车宽
        assert abs(pts[:, 1]).max() < W / 2 * (1 + tol), \
            f"{name} Y={abs(pts[:,1]).max():.0f} 超过半宽 {W/2:.0f}（轴可能仍错位）"
        # Z 不得为负（地下）
        assert pts[:, 2].min() > -float(gen.GC) * 0.5, \
            f"{name} Z 最低 {pts[:,2].min():.0f} 伸入地面以下"


def test_part_boxes_match_layout_contract(gen):
    """各零件应落在 `car_layout.part_boxes` 定义的布局契约内

    这是"整车能否拼成一辆车"的可判定标准；越界项会被列出。
    """
    from app.car_layout import build_layout, check_against_layout

    lay = build_layout(gen.params)
    name_map = {
        "发动机盖": "hood", "前风挡玻璃": "windshield", "车顶": "roof",
        "行李箱盖": "trunk", "前保险杠": "bumper_front",
        "后保险杠": "bumper_rear", "left前门": "door_front",
        "left后门": "door_rear", "leftfront翼子板": "fender_front",
        "leftrear翼子板": "fender_rear",
    }
    car = gen.generate_complete_car()
    boxes = {}
    for c in car["components"]:
        s = c.get("surface")
        nm = name_map.get(c.get("name"))
        if not s or not nm or "control_points" not in s:
            continue
        a = np.array([[p["x"], p["y"], p["z"]] for row in s["control_points"]
                      for p in row])
        boxes[nm] = {"X": [a[:, 0].min(), a[:, 0].max()],
                     "Y": [a[:, 1].min(), a[:, 1].max()],
                     "Z": [a[:, 2].min(), a[:, 2].max()]}
    issues = check_against_layout(lay, boxes)
    assert not issues, "零件越出布局契约：\n  " + "\n  ".join(issues)


def test_override_is_stateless(gen):
    """参数覆盖必须无副作用：生成后实例参数应恢复"""
    a = _hood(gen)
    _ = _hood(gen, params_override={"overall_length": 5500, "hood_length": 1500})
    c = _hood(gen)
    assert np.allclose(a, c), "参数覆盖后状态未恢复（有副作用）"


def test_grouped_override_format_still_works(gen):
    """分组格式（原有用法）必须保持可用，避免破坏既有调用方"""
    a = _hood(gen)
    b = _hood(gen, params_override={"车身部件": {"hood_length": 1500}})
    assert not np.allclose(a, b)


# ---------------------------------------------------------------------------
# 2. 实测质量声明
# ---------------------------------------------------------------------------
def test_quality_is_measured_not_hardcoded(gen):
    """质量块必须带有测量痕迹，不能是常量"""
    q = gen.generate_complete_car()["nurbs_quality"]
    assert q.get("measured") is True, "质量声明未标记为已测量"
    assert "n_measured" in q and q["n_measured"] > 0, "未报告已测量曲面数"
    assert "curvature" in q and isinstance(q["curvature"], dict)
    assert len(q["curvature"]) == q["n_measured"]


def test_g2_claim_is_false_when_flat_surfaces_exist(gen):
    """存在平面时必须如实否定 G2 声明

    平面曲率恒为 0，无法与相邻曲面满足曲率比 1±0.2（SOP-A SURF-001 §5.2）。
    此前实现硬编码 `g2_continuous: True`，与此矛盾。
    """
    q = gen.generate_complete_car()["nurbs_quality"]
    if q.get("n_flat_surfaces", 0) > 0:
        assert q["g2_continuous"] is False, (
            f"存在 {q['n_flat_surfaces']} 个平面却仍声称 G2 连续"
        )


def test_g2_claim_logic_is_consistent(gen):
    """g2_continuous 必须与平面/不可测计数自洽"""
    q = gen.generate_complete_car()["nurbs_quality"]
    expected = bool(q["n_measured"] > 0
                    and q["n_flat_surfaces"] == 0
                    and q["n_unmeasurable"] == 0)
    assert q["g2_continuous"] is expected, (
        f"G2 判定与计数不自洽：{q}"
    )


def test_curvature_values_are_physical(gen):
    """实测曲率半径应落在合理工程区间内"""
    q = gen.generate_complete_car()["nurbs_quality"]
    for name, v in q["curvature"].items():
        assert v["k_abs_median"] >= 0.0
        if v["r_median_mm"] is not None:
            # 车身曲面半径从几十毫米（小过渡）到上万毫米（近平面）
            assert 1.0 <= v["r_median_mm"] <= 1e6, (
                f"{name} 曲率半径异常: {v['r_median_mm']} mm"
            )
