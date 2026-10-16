# -*- coding: utf-8 -*-
"""平稳垂直起降（VTOL）飞行分支测试

覆盖：前端五字段直通（resolve_overrides）、默认关闭（几何零改动）、
飞行包线公式可复现、越界钳位、参数覆盖无副作用。
几何本体不受飞行分支影响 —— 封闭化普查（44 NURBS/51 组件）由
test_car_topology_closure.py 继续守护。
"""
import numpy as np
import pytest

from app.car_generator import NURBSCarBodyGenerator


@pytest.fixture(scope="module")
def gen():
    return NURBSCarBodyGenerator()


def test_resolve_overrides_accepts_frontend_flight_params():
    """前端五字段（与 carPresets.js 同名）应直通 飞行参数 组"""
    out = NURBSCarBodyGenerator.resolve_overrides({
        "enable_vtol": True, "hover_altitude": 1900,
        "exotic_drive_ratio": 0.2, "dark_matter_ratio": 0.25,
        "lift_fan_count": 6,
    })
    assert "飞行参数" in out
    flat = out["飞行参数"]
    assert flat["enable_vtol"] is True
    assert flat["hover_altitude"] == 1900
    assert flat["exotic_drive_ratio"] == 0.2
    assert flat["dark_matter_ratio"] == 0.25
    assert flat["lift_fan_count"] == 6


def test_default_vtol_disabled(gen):
    """默认关闭：包线在但 enabled=False，几何零改动"""
    car = gen.generate_complete_car()
    env = car["flight_envelope"]
    assert env["enabled"] is False
    assert car["total_surfaces"] == 51 and len(
        [c for c in car["components"] if "surface" in c]) == 44


def test_envelope_mass_formula_reproducible(gen):
    """整备质量 = 120 kg/m³ × 包络体积（公式可复现，不接受无法溯源的数字）"""
    env = gen.flight_envelope()
    H = float(gen._p("整车尺寸", "overall_height"))
    expect = gen.L * gen.W * H / 1e9 * 120.0
    assert env["curb_mass_kg"] == pytest.approx(expect, abs=0.1)


def test_envelope_physics_default(gen):
    """默认 η_dark=0.15 / η_cdm=0.2：g_eff、推重比、阻尼比与公式一致"""
    env = gen.flight_envelope()
    assert env["effective_gravity"] == pytest.approx(9.81 * 0.9475, abs=1e-3)
    assert env["thrust_to_weight"] == pytest.approx(1.0 / 0.9475, abs=1e-3)
    assert env["damping_ratio"] == pytest.approx(1.12, abs=1e-3)
    # 物理自洽：起飞推力 = 1.2 × 悬浮推力；推重比 ≥ 1（悬浮充要）
    assert env["thrust_takeoff_kn"] == pytest.approx(env["thrust_required_kn"] * 1.2, abs=0.05)
    assert env["thrust_to_weight"] >= 1.0
    assert env["vertigo_free"] is True   # ζ≥1 过阻尼 → 无超调无眩晕


def test_enabled_override_changes_only_envelope(gen):
    """开启后 enabled=True、g_eff 按新 η 变化；几何与关闭时完全一致"""
    a = gen.generate_complete_car()
    b = gen.generate_complete_car(params_override={
        "enable_vtol": True, "exotic_drive_ratio": 0.25})
    assert b["flight_envelope"]["enabled"] is True
    assert b["flight_envelope"]["effective_gravity"] == pytest.approx(
        9.81 * (1 - 0.35 * 0.25), abs=1e-3)
    # 几何零改动：组件数与 NURBS 面数一致
    assert a["total_surfaces"] == b["total_surfaces"]
    # 几何零改动：发动机盖控制点逐位重合
    def hood(car):
        for c in car["components"]:
            if c.get("name") == "发动机盖" and "surface" in c:
                return np.array([[[p["x"], p["y"], p["z"]] for p in row]
                                 for row in c["surface"]["control_points"]])
        raise AssertionError("未找到发动机盖")
    assert np.allclose(hood(a), hood(b))


def test_extreme_flight_params_are_clamped(gen):
    """η_dark=5 / hover=99999 / fans=99 全部钳位到安全界"""
    car = gen.generate_complete_car(params_override={
        "enable_vtol": True, "exotic_drive_ratio": 5.0,
        "hover_altitude": 99999, "lift_fan_count": 99,
        "dark_matter_ratio": -1})
    env = car["flight_envelope"]
    assert env["effective_gravity"] == pytest.approx(9.81 * 0.895, abs=1e-3)
    assert env["hover_altitude_mm"] == 3000
    assert env["lift_fans"] == 8
    assert env["damping_ratio"] == 1.0   # 负配比钳回 0 → 临界阻尼（仍无眩晕）


def test_override_is_stateless(gen):
    """飞行参数覆盖必须无副作用：生成后包线恢复默认"""
    e0 = gen.flight_envelope()
    gen.generate_complete_car(params_override={
        "enable_vtol": True, "hover_altitude": 2500, "exotic_drive_ratio": 0.3})
    e1 = gen.flight_envelope()
    assert e0 == e1
