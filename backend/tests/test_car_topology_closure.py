# -*- coding: utf-8 -*-
"""整车拓扑封闭性与装配关系测试

曲面造型完整封闭：每一条开口边必须有邻件边界或封闭板对接。
- 横向钣件链（风挡-车顶-后窗-行李箱）共享边采样点逐位重合
- cowl 阶差条 / A·C 柱楔 / 前脸·尾门封板 / 底盘托盘 / 轮拱内衬 就位且贴合
- 装配关系：门沿盖过玻璃底沿、内衬藏于蒙皮内侧、机盖总长==hood_length
"""
import numpy as np
import pytest

from app.car_generator import NURBSCarBodyGenerator


@pytest.fixture(scope="module")
def gen():
    return NURBSCarBodyGenerator()


@pytest.fixture(scope="module")
def car(gen):
    return gen.generate_complete_car()


def _by_name(car, name):
    for c in car["components"]:
        if c.get("name") == name:
            return c
    raise AssertionError(f"部件缺失: {name}")


def _cps(comp):
    """组件 NURBS 控制点 → np 数组 [nu, nv, 3]（规范坐标）"""
    rows = comp["surface"]["control_points"]
    return np.array([[[p["x"], p["y"], p["z"]] if isinstance(p, dict)
                      else list(p) for p in row] for row in rows], dtype=float)


# ---------------------------------------------------------------- 横向钣件链
def test_transverse_chain_edges_coincide(car):
    """风挡-车顶-后窗-行李箱共享边：nv 统一 + 同跨度 → 采样点逐位重合"""
    pairs = [("前风挡玻璃", "车顶"), ("车顶", "后风挡玻璃"),
             ("后风挡玻璃", "行李箱盖")]
    for a, b in pairs:
        ea = np.array(_by_name(car, a)["points"])[-1]   # a 末行
        eb = np.array(_by_name(car, b)["points"])[0]    # b 首行
        assert ea.shape == eb.shape, f"{a}-{b} 共享边采样数不一致"
        assert np.allclose(ea, eb, atol=0.5), \
            f"{a}-{b} 共享边未重合（最大偏差 " \
            f"{np.abs(ea - eb).max():.2f}mm）"


def test_hood_windshield_step_sealed_by_cowl(car, gen):
    """机盖后缘(±0.95hw)与风挡底(±0.90hw)的阶差由 cowl 封条覆盖"""
    L, hw = gen.L, gen.half_w
    hood_rear = np.array(_by_name(car, "发动机盖")["points"])[-1]
    ws_front = np.array(_by_name(car, "前风挡玻璃")["points"])[0]
    assert np.abs(hood_rear[:, 1]).max() == pytest.approx(hw * 0.95, abs=1)
    assert np.abs(ws_front[:, 1]).max() == pytest.approx(hw * 0.90, abs=1)
    for side in ("left", "right"):
        cowl = _by_name(car, f"{side}cowl封条")
        pts = np.array(cowl["points"]).reshape(-1, 3)
        sgn = 1.0 if side == "left" else -1.0
        lat = pts[:, 1] * sgn
        # 覆盖 [0.45W/2?? —— 半宽 0.45W*0.5?? 用生成值区间核对]
        assert lat.min() >= hw * 0.895, f"{side} cowl 内缘未接风挡底"
        assert lat.max() <= hw * 0.96 + 6 and lat.max() >= hw * 0.95, \
            f"{side} cowl 外缘未搭机盖后缘"
        assert np.abs(pts[:, 2] - gen.waist).max() <= 6, \
            f"{side} cowl 高度偏离腰线"
        # x 位于机盖后缘附近（±8mm）
        assert np.abs((pts[:, 0] + L / 2) - gen.hp["x_cowl"]).max() <= 8


# ---------------------------------------------------------------- 柱楔封角
def test_pillar_wedges_share_glass_and_window_edges(car, gen):
    """A/C 柱楔 CP 角点必须落在风挡/后窗侧缘角与侧窗下沿角上"""
    for side in ("left", "right"):
        sgn = 1.0 if side == "left" else -1.0
        a = _cps(_by_name(car, f"{side}A柱"))
        # CP 转置后末行 = 退化顶点行（风挡上侧角 p2），首行末点 = 玻璃前下角
        tip = a[3][0]
        assert abs(tip[0] - (gen.hp["x_wstop"] - gen.L / 2)) <= 2, f"A柱尖 {tip}"
        assert abs(tip[2] - gen.hp["z_wstop"]) <= 2
        foot = a[0][-1]
        assert abs(foot[0] - (gen.hp["x_cowl"] + 40 - gen.L / 2)) <= 2
        assert abs(foot[2] - gen.waist * 0.98) <= 2
        c = _cps(_by_name(car, f"{side}C柱"))
        tip_c = c[3][0]
        assert abs(tip_c[0] - (gen.hp["x_cab_end"] - gen.L / 2)) <= 2
        assert abs(tip_c[2] - gen.hp["z_roof_r"]) <= 2
        foot_c = c[0][-1]
        assert abs(foot_c[0] - (gen.hp["x_rwbot"] - 40 - gen.L / 2)) <= 2
        assert abs(foot_c[2] - gen.waist * 0.98) <= 2
        # 楔外缘贴风挡/后窗半宽带（0.45~0.46W）
        lats = np.abs(np.concatenate([a[:, :, 1].ravel(), c[:, :, 1].ravel()]))
        assert lats.min() >= gen.W * 0.44, "柱楔内缘缩入玻璃区"
        assert lats.max() <= gen.W * 0.47 + 2, "柱楔外缘超出窗带"


# ---------------------------------------------------------------- 底部封闭
def test_underbody_closes_bottom_and_meets_shell(gen, car):
    """底盘托盘：u 站/模板/缘 CP 与蒙皮同源 → 底缘采样**逐位重合**"""
    L = gen.L
    floor = _by_name(car, "底盘托盘")
    pts = np.array(floor["points"])           # [nu, nv, 3]
    assert pts[:, :, 0].min() <= L / 2 - 60 + 5, "托盘未及车头"
    assert pts[:, :, 0].max() >= -(L / 2 - 60) - 5, "托盘未及车尾"
    assert pts[:, :, 2].min() >= 100, "托盘中央低于预期（z=115）"
    # 侧缘与左蒙皮底缘同线：x/z 逐位重合；|lat| = 蒙皮 + 3mm 设计外扩
    shell_edge = np.array(_by_name(car, "left车身外蒙皮")["points"])[:, 0]
    for col in (pts[:, 0], pts[:, -1]):
        assert col.shape == shell_edge.shape, "托盘缘站数与蒙皮不一致"
        assert np.allclose(col[:, 0], shell_edge[:, 0], atol=0.5) and \
            np.allclose(col[:, 2], shell_edge[:, 2], atol=0.5), \
            "托盘缘 x/z 未与蒙皮底缘重合"
        assert np.allclose(np.abs(col[:, 1]), np.abs(shell_edge[:, 1]) + 3,
                           atol=0.5), "托盘缘半宽 ≠ 蒙皮 + 3mm"


# ---------------------------------------------------------------- 端面封闭
def test_front_and_rear_faces_sealed(gen, car):
    """前脸封板顶接机盖前缘/底接保险杠顶；尾门封板顶接行李箱后缘"""
    nose = np.array(_by_name(car, "前脸封板")["points"]).reshape(-1, 3)
    assert np.abs(nose[:, 2].max() - (gen.hp["z_hood_f"] - 2)) <= 6
    assert np.abs(nose[:, 2].min() - 374) <= 6
    tail = np.array(_by_name(car, "尾门封板")["points"]).reshape(-1, 3)
    assert np.abs(tail[:, 2].max() - (gen.hp["z_trunk_r"] - 2)) <= 6
    assert np.abs(tail[:, 2].min() - 374) <= 6
    # 尾门板位于车尾端面（wrap 圆角前收 ≤230）；前脸板顶行中心后倾贴
    # 机盖前缘、端部随鼻弧后收（流线化 rake+wrap，见流线型测试）
    assert tail[:, 0].min() >= gen.L / 2 - 230
    nose_top = nose[nose[:, 2] > nose[:, 2].max() - 8]
    assert nose_top[:, 0].min() >= -gen.L / 2 + 60, "前脸顶行中心前伸越界"
    assert nose_top[:, 0].max() <= -gen.L / 2 + 240, "前脸顶行端部 wrap 后收越界"


def test_nose_deck_plus_hood_equals_hood_length(gen, car):
    """机盖总长（鼻端面板 + 机盖）== hood_length 参数（尺寸正确性）"""
    L = gen.L
    deck = np.array(_by_name(car, "鼻端面板")["points"]).reshape(-1, 3)
    hood = np.array(_by_name(car, "发动机盖")["points"]).reshape(-1, 3)
    x_lo = min(deck[:, 0].min(), hood[:, 0].min()) + L / 2
    x_hi = hood[:, 0].max() + L / 2
    assert x_lo <= 5, "鼻端面板应从车头 0 起"
    assert (x_hi - x_lo) == pytest.approx(
        gen._p("车身部件", "hood_length"), abs=8)


# ---------------------------------------------------------------- 流线型
def test_plan_taper_streamlined(gen, car):
    """俯视收窄：舱区恒 1.0（契约锚点不动），鼻/尾单调收窄且体现到蒙皮"""
    hp = gen.hp
    assert gen._plan_taper(hp['x_cowl']) == pytest.approx(1.0)
    assert gen._plan_taper((hp['x_cowl'] + hp['x_rwbot']) / 2) == pytest.approx(1.0)
    assert gen._plan_taper(hp['x_rwbot']) == pytest.approx(1.0)
    assert gen._plan_taper(0.0) < 0.97
    assert gen._plan_taper(gen.L) < 0.99
    assert gen._plan_taper(0.0) < gen._plan_taper(300.0) < 1.0
    assert gen._plan_taper(gen.L) < gen._plan_taper(gen.L - 300.0) < 1.0
    shell = np.array(_by_name(car, "left车身外蒙皮")["points"])
    lat = np.abs(shell[:, :, 1])
    x = shell[:, :, 0] + gen.L / 2
    nose_lat = lat[x < 120.0].max()
    cabin_lat = lat[(x > hp['x_cowl'] + 100) & (x < hp['x_rwbot'] - 100)].max()
    assert nose_lat < cabin_lat * 0.975, \
        f"鼻部蒙皮未体现收窄 {nose_lat:.1f} vs 舱段 {cabin_lat:.1f}"


def test_nose_tail_panels_sculpted(gen, car):
    """前脸/尾门封板流线化：顶部收窄 + rake 斜背 + 端部 wrap 圆角

    CP 网格转置后**行=横向、列=纵向**（自底向顶），故取列而非行。
    """
    nose = _cps(_by_name(car, "前脸封板"))
    nose_bot, nose_top = nose[:, 0], nose[:, -1]
    assert np.abs(nose_top[:, 1]).max() < np.abs(nose_bot[:, 1]).max(), \
        "前脸顶部未收窄（仍有方角外撅）"
    cx_top = nose_top[np.abs(nose_top[:, 1]).argmin(), 0]
    cx_bot = nose_bot[np.abs(nose_bot[:, 1]).argmin(), 0]
    assert cx_top - cx_bot >= 30, "前脸顶部未后倾（rake）"
    corner_top = nose_top[np.abs(nose_top[:, 1]).argmax(), 0]
    assert corner_top - cx_top >= 80, "前脸端部未随鼻弧后收（wrap）"
    tail = _cps(_by_name(car, "尾门封板"))
    tail_bot, tail_top = tail[:, 0], tail[:, -1]
    assert np.abs(tail_top[:, 1]).max() < np.abs(tail_bot[:, 1]).max(), \
        "尾门顶部未收窄"
    cx_top = tail_top[np.abs(tail_top[:, 1]).argmin(), 0]
    cx_bot = tail_bot[np.abs(tail_bot[:, 1]).argmin(), 0]
    assert cx_bot - cx_top >= 20, "尾门顶部未前收（kammback）"


# ---------------------------------------------------------------- 装配关系
def test_door_sill_overlaps_glass_bottom(gen, car):
    """门顶沿(z=waist*0.995, lat=outer+4)必须盖过侧窗下沿(z=waist*0.98)"""
    for side in ("left", "right"):
        sgn = 1.0 if side == "left" else -1.0
        glass = np.array(_by_name(car, f"{side}前侧窗")["points"]).reshape(-1, 3)
        door = np.array(_by_name(car, f"{side}前门")["points"]).reshape(-1, 3)
        assert door[:, 2].max() >= glass[:, 2].min() - 1, \
            f"{side} 门顶低于玻璃底，出现窗台缝"
        door_top_lat = np.abs(door[door[:, 2] > door[:, 2].max() - 15, 1])
        glass_bot_lat = np.abs(glass[glass[:, 2] < glass[:, 2].min() + 15, 1])
        assert door_top_lat.mean() > glass_bot_lat.mean(), \
            f"{side} 玻璃比门顶更外凸"


def test_arch_liners_inside_shell(gen, car):
    """4 个轮拱内衬藏于蒙皮内侧 ≥40mm，且覆盖拱高"""
    liners = [c for c in car["components"] if c.get("type") == "arch_liner"]
    assert len(liners) == 4
    for c in liners:
        pts = np.array(c["points"]).reshape(-1, 3)
        for p in pts[::5]:
            limit = gen._outer_half_width(p[0] + gen.L / 2, p[2]) - 40
            assert abs(p[1]) <= limit, \
                f"{c['name']} 内衬外露 @z={p[2]:.0f}"
        assert pts[:, 2].max() >= gen.GC + gen._arch_H - 30, \
            f"{c['name']} 未盖到拱顶"


def test_interior_shelves_block_see_through(car):
    """cowl 台 / parcel 台存在且为不透明内饰件"""
    for name in ("cowl内饰台", "后parcel台"):
        comp = _by_name(car, name)
        assert "opacity" not in comp, f"{name} 不应透明"


def test_surface_and_component_census(car):
    """封闭化后组件普查：44 NURBS 面 / 51 组件（防回归清单漂移）"""
    nurbs = [c for c in car["components"] if "surface" in c]
    assert len(nurbs) == 44, f"NURBS 面数 {len(nurbs)} ≠ 44"
    assert len(car["components"]) == 51
    for t, n in (("underbody", 1), ("nose_deck", 1), ("cowl", 2),
                 ("nose_panel", 1), ("tailgate", 1), ("pillar", 4),
                 ("arch_liner", 4), ("interior", 2), ("body_shell", 2),
                 ("fender", 4), ("door", 4), ("side_glass", 4)):
        got = sum(1 for c in car["components"] if c.get("type") == t)
        assert got == n, f"type={t} 期望 {n} 实际 {got}"
