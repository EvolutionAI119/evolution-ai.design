"""侧玻璃 tumblehome / 桶面三参数接入 NURBS 生成链路的回归测试

前端 Designer 三滑块（side_glass_angle / glass_barrel_angle / glass_barrel_radius）
经扁平 resolve_overrides 直通后端几何，公式与前端 src/utils/carGlass.js 一致：
inset(t) = t·span·tan(tilt) + R·(1−cos(β·t))，t 按 [0,1] 钳位。
"""
import numpy as np
import pytest

from app.car_generator import NURBSCarBodyGenerator


def resolve(**overrides):
    return NURBSCarBodyGenerator.resolve_overrides(overrides)


def _comp_pts(car, name):
    for c in car["components"]:
        if c.get("name") == name and "surface" in c:
            return np.array([[[p["x"], p["y"], p["z"]] for p in row]
                             for row in c["surface"]["control_points"]])
    raise AssertionError(f"未找到部件 {name}")


def test_resolve_overrides_accepts_frontend_glass_params():
    """前端扁平字段名直通后端分组（无需别名）"""
    out = resolve(side_glass_angle=26, glass_barrel_angle=10, glass_barrel_radius=900)
    assert out["造型角度"]["side_glass_angle"] == 26
    assert out["造型角度"]["glass_barrel_angle"] == 10
    assert out["车身部件"]["glass_barrel_radius"] == 900


def test_default_tilt_drives_greenhouse_narrowing():
    """默认 18°/8°/1200：腰线零内收，顶沿内收 = span·tan + R(1−cosβ)"""
    gen = NURBSCarBodyGenerator()
    assert gen._tilt_deg == pytest.approx(18.0)
    assert gen._barrel_deg == pytest.approx(8.0)
    assert gen._barrel_R == pytest.approx(1200.0)
    assert gen._greenhouse_inset(gen.waist) == pytest.approx(0.0, abs=1e-9)
    inset_top = (gen._gh_span * np.tan(np.radians(18.0))
                 + 1200.0 * (1.0 - np.cos(np.radians(8.0))))
    assert gen._greenhouse_inset(gen.hp['z_wstop']) == pytest.approx(inset_top, rel=1e-9)
    # 18° 时顶沿内收远超 100mm，前视梯形车肩肉眼可辨
    assert gen._greenhouse_lat(gen.hp['z_wstop']) < gen._greenhouse_lat(gen.waist) - 100


def test_override_tilt_changes_side_glass_surface():
    """倾角覆盖真实改变侧窗曲面：lat(z_wstop) 差 = span·(tan30°−tan10°)"""
    g10 = NURBSCarBodyGenerator(config_override=resolve(side_glass_angle=10))
    g30 = NURBSCarBodyGenerator(config_override=resolve(side_glass_angle=30))
    lat10 = g10._greenhouse_lat(g10.hp['z_wstop'])
    lat30 = g30._greenhouse_lat(g30.hp['z_wstop'])
    expected = g10._gh_span * (np.tan(np.radians(30.0)) - np.tan(np.radians(10.0)))
    assert (lat10 - lat30) == pytest.approx(expected, rel=1e-6)


def test_barrel_bulges_glass_outward_at_mid():
    """桶面使玻璃中段半宽大于端点线性插值（鼓肚）；零桶面退化为严格线性"""
    gb = NURBSCarBodyGenerator(config_override=resolve(
        glass_barrel_angle=12, glass_barrel_radius=900))
    z0, z1 = gb.waist, gb.hp['z_wstop']
    zm = (z0 + z1) / 2.0
    mid = gb._greenhouse_lat(zm)
    linear = (gb._greenhouse_lat(z0) + gb._greenhouse_lat(z1)) / 2.0
    assert mid > linear

    g0 = NURBSCarBodyGenerator(config_override=resolve(glass_barrel_angle=0))
    assert g0._greenhouse_lat(zm) == pytest.approx(
        (g0._greenhouse_lat(z0) + g0._greenhouse_lat(z1)) / 2.0, rel=1e-9)


def test_shared_edges_stay_coplanar_under_override():
    """大倾角+桶面覆盖下共享边仍共面：B柱顶=侧窗顶、风挡顶=车顶前缘

    部件存储为 canonical 坐标（x=车长, y=横向, z=高度），横向取 index 1。
    """
    gen = NURBSCarBodyGenerator(config_override=resolve(
        side_glass_angle=28, glass_barrel_angle=12, glass_barrel_radius=900))
    car = gen.generate_complete_car()
    z_top = gen.hp['z_wstop'] - 2

    glass = _comp_pts(car, 'left前侧窗')       # (nu x, nv z)，j=nv-1 为顶沿
    pillar = _comp_pts(car, 'leftB柱')          # (4 x, 6 z)，j=5 为顶沿
    # 前侧窗末行（x1 处）上沿 = z_wstop-2，与 B 柱顶同面；首行上沿在 A 柱斜坡上
    assert abs(glass[-1][-1][1]) == pytest.approx(gen._greenhouse_lat(z_top), abs=0.5)
    assert abs(glass[-1][-1][2]) == pytest.approx(z_top, abs=0.5)
    assert abs(pillar[0][-1][1]) == pytest.approx(gen._greenhouse_lat(z_top), abs=0.5)

    ws = _comp_pts(car, '前风挡玻璃')           # (nu, nv)，末行 u=1 顶边
    roof = _comp_pts(car, '车顶')               # 首行 u=0 前缘
    assert abs(ws[-1][0][1]) == pytest.approx(gen._greenhouse_lat(gen.hp['z_wstop']), abs=0.5)
    assert abs(roof[0][0][1]) == pytest.approx(gen._greenhouse_lat(gen.hp['z_wstop']), abs=0.5)
    # A 柱楔顶点（退化末行全为 p2）与侧窗/车顶前缘同面
    ap = _comp_pts(car, 'leftA柱')
    assert abs(ap[-1][0][1]) == pytest.approx(
        gen._greenhouse_lat(gen.hp['z_wstop']), abs=0.5)


def test_extreme_params_are_clamped():
    """越界覆盖被防御性钳位（与前端 UI 范围一致）"""
    gen = NURBSCarBodyGenerator(config_override=resolve(
        side_glass_angle=100, glass_barrel_angle=50, glass_barrel_radius=50))
    assert gen._tilt_deg == pytest.approx(40.0)
    assert gen._barrel_deg == pytest.approx(20.0)
    assert gen._barrel_R == pytest.approx(400.0)


def test_complete_car_remains_closed_under_big_tilt():
    """40° 极限倾角下整车封闭化普查不变（44 NURBS 面 / 51 组件）"""
    gen = NURBSCarBodyGenerator(config_override=resolve(side_glass_angle=40))
    car = gen.generate_complete_car()
    nurbs = [c for c in car["components"] if "surface" in c]
    assert len(nurbs) == 44
    assert len(car["components"]) == 51
    glass = [c for c in car["components"] if c.get("type") == "side_glass"]
    assert len(glass) == 4
    for g in glass:
        lat = np.array([[p["y"] for p in row]
                        for row in g["surface"]["control_points"]])
        # 行=x（沿车长）、列=z（窗台→上沿）：底沿恒等于玻璃底沿基准
        assert np.abs(lat[:, 0]).max() <= gen._glass_lat_low + 1e-6
        # 上沿逐行不高于底沿（内收随高度单调，tumblehome 真实作用于曲面）
        assert (np.abs(lat[:, -1]) <= np.abs(lat[:, 0]) + 1e-6).all()
    # 前侧窗末行上沿（z_wstop−2 全高处）达到公式内收（40° 时 > 400mm）
    front = _comp_pts(car, 'left前侧窗')
    z_top = gen.hp['z_wstop'] - 2
    assert abs(front[-1][-1][1]) == pytest.approx(gen._greenhouse_lat(z_top), abs=0.5)
