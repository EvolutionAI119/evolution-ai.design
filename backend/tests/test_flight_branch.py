# -*- coding: utf-8 -*-
"""平稳垂直起降（VTOL）飞行分支测试

覆盖：前端五字段直通（resolve_overrides）、默认关闭（几何零改动）、
飞行包线公式可复现、越界钳位、参数覆盖无副作用。
几何本体不受飞行分支影响 —— 封闭化普查（44 NURBS/51 组件）由
test_car_topology_closure.py 继续守护。
"""
import math

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


# ============ 反重力飞控系统（五项技术目标） ============
# 与前端 src/utils/flightPhysics.js 同公式：场升力份额 / 能耗模型 / 姿态 / 延迟

@pytest.fixture(scope="module")
def fc_default(gen):
    return gen.flight_envelope()["flight_control"]


def test_flight_control_energy_model_reproducible(gen, fc_default):
    """能耗模型公式可复现：P_base=55·(m/t)^1.2、场份额 s=2.6η_e+1.8η_cdm（钳位 0.75）"""
    mass_kg = gen.flight_envelope()["curb_mass_kg"]
    eta_e = float(gen._p("飞行参数", "exotic_drive_ratio"))
    eta_c = float(gen._p("飞行参数", "dark_matter_ratio"))
    share = min(2.6 * eta_e + 1.8 * eta_c, 0.75)
    assert fc_default["field_lift_share"] == pytest.approx(share, abs=1e-3)
    p_base = 55.0 * (mass_kg / 1000.0) ** 1.2
    assert fc_default["base_power_kw"] == pytest.approx(p_base, abs=0.05)
    p_hover = p_base * (1 - share) ** 1.5 + 12.0 * mass_kg * share / 1000.0
    assert fc_default["hover_power_kw"] == pytest.approx(p_hover, abs=0.05)


def test_flight_control_endurance_target_3x(gen, fc_default):
    """目标 3：默认预设续航倍数 ≥3（同电量 vs 同量级传统动力基准）"""
    assert fc_default["endurance_multiple"] >= 3.0
    assert fc_default["endurance_antigravity_h"] > fc_default["endurance_base_h"]
    # 换算自洽：时长比 = 倍数
    assert fc_default["endurance_antigravity_h"] / fc_default["endurance_base_h"] == \
        pytest.approx(fc_default["endurance_multiple"], abs=0.02)


def test_flight_control_no_energy_peaks(gen, fc_default):
    """目标 4：全工况峰值因子 ≤1.25（起飞峰值/转向差动均受界，无明显能耗峰值）"""
    assert fc_default["peak_factor"] <= 1.25
    assert fc_default["takeoff_peak_kw"] > fc_default["hover_power_kw"]   # 峰值在起飞（如实的物理）
    assert fc_default["turn_power_kw"] == pytest.approx(
        fc_default["hover_power_kw"] * 1.05, abs=0.05)


def test_flight_control_attitude_and_latency(gen, fc_default):
    """目标 1+5：姿态 ±2° 包络（过阻尼无超调）与响应延迟 ≤100ms"""
    zeta = 1.0 + 0.6 * float(gen._p("飞行参数", "dark_matter_ratio"))
    tau = 1000.0 / (zeta * 2.0 * math.pi * 2.5)
    assert fc_default["attitude_time_constant_ms"] == pytest.approx(tau, abs=0.1)
    assert fc_default["attitude_recovery_ms"] == pytest.approx(tau * math.log(4.0), abs=0.1)
    assert fc_default["control_latency_ms"] <= 100.0
    assert fc_default["attitude_limit_deg"] == 2.0


def test_flight_control_turn_360(gen, fc_default):
    """目标 2：360° 原地转向 = 1.875·360/45°/s = 15s（峰值角速度舒适限内）"""
    assert fc_default["full_turn_s"] == pytest.approx(15.0, abs=0.01)
    assert fc_default["turn_peak_rate_dps"] == 45.0


def test_flight_control_targets_all_met_default(gen, fc_default):
    """默认预设下五项技术目标全部达标（targets_met 全真）"""
    assert all(fc_default["targets_met"].values()), fc_default["targets_met"]


def test_flight_control_extreme_params_reported_honestly(gen):
    """极端调参（η 归零）→ 达标判定如实转假，不虚假报告"""
    car = gen.generate_complete_car(params_override={
        "enable_vtol": True, "exotic_drive_ratio": 0.0, "dark_matter_ratio": 0.0})
    fc = car["flight_envelope"]["flight_control"]
    assert fc["field_lift_share"] == 0.0
    assert fc["endurance_multiple"] == pytest.approx(1.0, abs=0.01)   # 退化为传统动力
    assert fc["targets_met"]["endurance_3x"] is False
    assert fc["targets_met"]["attitude_2deg"] is True                  # 姿态不受 η 影响
    # 几何仍零改动
    assert car["total_surfaces"] == 51
