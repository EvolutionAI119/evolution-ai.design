"""车身布局层 —— 以硬点为唯一事实来源，统一各零件的规范坐标

为什么需要这一层
----------------
`car_generator.py` 的 10 个曲面生成函数各自独立计算坐标，实测结果是：

| 现象 | 实测证据 |
|---|---|
| 轴约定错位 | 发动机盖把"高度"写进 Y、"车宽"写进 Z（已修） |
| 车头朝向不一致 | 前保在 X≈0、后保在 X=4600（同一端也重叠） |
| 区间重叠 | 车顶[2020,3110]、后风挡[1824,3110]、尾厢[1824,2824] |
| 左右未镜像 | left/right 门控制点逐元素相同 |
| 负高度 | 翼子板 Z∈[−183, 483]（伸到地面以下） |

**根因**：没有单一的布局来源，每个函数各算各的。

本模块提供**唯一布局来源**：从 `CarParams` 与硬点推导出规范的
X/Y/Z 区间，供各生成函数与校验使用。

规范坐标系
----------
    X = 车长，车头 −X / 车尾 +X，原点在车身中心
    Y = 车宽，左侧为正
    Z = 车高，地面为 0

硬点 → 分区（车身侧视图，X 自前向后）
------------------------------------
    front_x       = −L/2                   车头
    hood_end_x    = −L/2 + hood_length     机盖后缘 / 风挡根
    cabin_start_x                          座舱起点（取 hood_end 与 cabin 的较前值）
    cabin_end_x                            座舱终点 / 后窗根
    trunk_start_x                          尾厢起点
    rear_x        = +L/2                   车尾

Z 分区（自下而上）
------------------
    0                       地面
    ground_clearance        离地间隙（底盘下沿）
    waist                   腰线（车门窗下沿）
    roof                    车顶（最高面）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class Layout:
    """整车规范布局（单位与 CarParams 一致：mm）"""
    L: float
    W: float
    H: float
    GC: float
    WB: float
    TW: float
    FO: float          # 前悬
    RO: float          # 后悬
    waist: float       # 腰线高度
    roof: float        # 车顶高度

    # ---- X 分区（自前向后，车头为负）----
    front_x: float = 0.0
    axle_front_x: float = 0.0
    hood_end_x: float = 0.0
    cabin_start_x: float = 0.0
    cabin_end_x: float = 0.0
    trunk_start_x: float = 0.0
    axle_rear_x: float = 0.0
    rear_x: float = 0.0

    # ---- Y 半宽 ----
    half_w: float = 0.0
    half_track: float = 0.0
    fender_y: float = 0.0      # 翼子板外侧面（车身最宽处附近）

    # ---- Z 分区 ----
    z_ground: float = 0.0
    z_shoulder: float = 0.0    # 肩线
    z_roof: float = 0.0

    warnings: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    def x_span(self) -> Tuple[float, float]:
        return (self.front_x, self.rear_x)

    def as_dict(self) -> Dict[str, Any]:
        d = {k: round(v, 4) if isinstance(v, (int, float)) else v
             for k, v in self.__dict__.items() if k != 'warnings'}
        d['warnings'] = self.warnings
        return d

    def summary(self) -> str:
        return (f"L={self.L:.0f} W={self.W:.0f} H={self.H:.0f}  "
                f"X[{self.front_x:.0f},{self.rear_x:.0f}]  "
                f"Y[±{self.half_w:.0f}]  Z[{self.z_ground:.0f},{self.z_roof:.0f}]  "
                f"腰线={self.waist:.0f}")


def build_layout(params: Any, hardpoints: Optional[Dict[str, float]] = None) -> Layout:
    """从 CarParams（与可选硬点）构建规范布局

    **单位约定（重要）**：`_extract` 已把结果统一为**毫米**，且 `Layout` 的
    全部字段（L/W/H 与 x/z 分区）均为毫米。此前 `build_layout` 把米制的
    X 硬点与毫米制的 L 混用，导致 C5/C6 契约报出 "覆盖 4700000 mm" 的错值。

    `params` 兼容两种形态：
      - `CarParams` 数据类（属性访问，单位米）
      - `car_generator` 的参数字典（嵌套 dict，单位毫米）
    """
    L, W, H, GC, WB, TW, FO, RO, waist = _extract(params)

    # 半宽与轮距
    half_w = W / 2.0
    half_track = TW / 2.0

    # X 硬点：硬点优先；缺失则按前悬/后悬与机盖长推导
    # ⚠ 硬点可能以米制传入（来自算法层），故按与 L 同量级判定后换算为 mm
    hp = dict(hardpoints or {})
    if hp:
        scale = 1000.0 if max(abs(v) for v in hp.values() if isinstance(v, (int, float))) < 100 else 1.0
        hp = {k: float(v) * scale for k, v in hp.items() if isinstance(v, (int, float))}

    front_x = float(hp.get('front_x', -L / 2.0))
    rear_x = float(hp.get('rear_x', L / 2.0))
    hood_end_x = float(hp.get('hood_end_x', front_x + _hood_len(params)))
    cabin_end_x = float(hp.get('cabin_end_x', rear_x - L * 0.18))
    trunk_start_x = float(hp.get('trunk_start_x', cabin_end_x + L * 0.04))
    cabin_start_x = float(hp.get('cabin_start_x', hood_end_x))

    axle_front_x = front_x + FO
    axle_rear_x = rear_x - RO

    lay = Layout(
        L=L, W=W, H=H, GC=GC, WB=WB, TW=TW, FO=FO, RO=RO,
        waist=waist, roof=H,
        front_x=front_x, axle_front_x=axle_front_x,
        hood_end_x=hood_end_x, cabin_start_x=cabin_start_x,
        cabin_end_x=cabin_end_x, trunk_start_x=trunk_start_x,
        axle_rear_x=axle_rear_x, rear_x=rear_x,
        half_w=half_w, half_track=half_track, fender_y=half_w * 0.96,
        z_ground=0.0, z_shoulder=waist + (H - waist) * 0.25, z_roof=H,
    )
    _validate(lay)
    return lay


def _extract(params: Any) -> Tuple[float, ...]:
    """取出 L/W/H/GC/WB/TW/FO/RO/waist，**统一为毫米**

    兼容两套 CarParams：
      - `algorithm_model.car_modeling.car_params.CarParams`（字段 `WB`/`TW`/`FO`/`RO`）
      - `_archive/dirs/core/full_body.py.CarParams`（字段 `wheelbase`/`wheel_radius` 等）
    两套均为**米制**，故统一判定：L < 100 视为米制并 ×1000。
    """
    if hasattr(params, 'L') and hasattr(params, 'W'):
        L = float(getattr(params, 'L'))
        W = float(getattr(params, 'W'))
        H = float(getattr(params, 'H', 1.5))
        GC = float(getattr(params, 'ground_clearance', 0.15))
        # 字段名兼容：WB | wheelbase
        WB = getattr(params, 'WB', None)
        if WB is None:
            WB = getattr(params, 'wheelbase', L * 0.60)
        WB = float(WB)
        # 字段名兼容：TW | track_width
        TW = getattr(params, 'TW', None)
        if TW is None:
            TW = getattr(params, 'track_width', W * 0.86)
        TW = float(TW)
        FO = float(getattr(params, 'FO', L * 0.19))
        RO = float(getattr(params, 'RO', L * 0.22))
        waist_ratio = float(getattr(params, 'waist_line', 0.65))

        if L < 100:                     # 判定为米制 → 统一换算为 mm
            L, W, H, GC, WB, TW, FO, RO = (v * 1000.0 for v in
                                           (L, W, H, GC, WB, TW, FO, RO))
            # 腰线：既可能是"比例(0-1)"也可能是"绝对高度"
            waist = (GC + (H - GC) * waist_ratio) if waist_ratio <= 1.0 else waist_ratio
        else:                           # 已是毫米制
            waist = (GC + (H - GC) * waist_ratio) if waist_ratio <= 1.0 else waist_ratio
        return L, W, H, GC, WB, TW, FO, RO, waist

    # car_generator 参数字典（嵌套，毫米）
    def g(group: str, key: str, default: float = 0.0) -> float:
        try:
            return float(params[group][key]['value'])
        except Exception:
            return default

    L = g('整车尺寸', 'overall_length', 4800)
    W = g('整车尺寸', 'overall_width', 1850)
    H = g('整车尺寸', 'overall_height', 1450)
    GC = g('整车尺寸', 'ground_clearance', 150)
    WB = g('整车尺寸', 'wheelbase', 2800)
    TW = g('整车尺寸', 'track_width', 1600)
    FO = g('比例参数', 'overhang_front', L * 0.19)
    RO = g('比例参数', 'overhang_rear', L * 0.23)
    waist = GC + (H - GC) * 0.55
    return L, W, H, GC, WB, TW, FO, RO, waist


def _hood_len(params: Any) -> float:
    if hasattr(params, 'hood_length'):
        v = float(params.hood_length)
        return v * 1000.0 if v < 100 else v
    try:
        return float(params['车身部件']['hood_length']['value'])
    except Exception:
        return 1200.0


def _validate(lay: Layout) -> None:
    """自洽性校验：布局必须落在整车包络内且分区有序"""
    tol = max(lay.L, lay.W) * 0.02
    if lay.front_x < -lay.L / 2 - tol or lay.rear_x > lay.L / 2 + tol:
        lay.warnings.append(
            f"X 分区超出车长包络：[{lay.front_x:.0f},{lay.rear_x:.0f}] vs ±{lay.L/2:.0f}")
    order = [('front_x', lay.front_x), ('hood_end_x', lay.hood_end_x),
             ('cabin_start_x', lay.cabin_start_x), ('cabin_end_x', lay.cabin_end_x),
             ('trunk_start_x', lay.trunk_start_x), ('rear_x', lay.rear_x)]
    for (n1, v1), (n2, v2) in zip(order, order[1:]):
        if v2 < v1 - 1e-6:
            lay.warnings.append(f"X 分区顺序异常：{n1}={v1:.0f} > {n2}={v2:.0f}")
    if lay.axle_front_x > lay.axle_rear_x:
        lay.warnings.append("前轴位于后轴之后")
    if not (lay.GC <= lay.waist <= lay.z_roof):
        lay.warnings.append(f"腰线高度异常：GC={lay.GC:.0f} 腰线={lay.waist:.0f} 顶={lay.z_roof:.0f}")


# ---------------------------------------------------------------------------
# 各零件在规范坐标系下的目标区间（供生成函数与校验共用）
# ---------------------------------------------------------------------------
def part_boxes(lay: Layout) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """返回各零件在规范坐标系下的期望区间

    X/Y/Z 均给出 (min, max)。这是**布局契约**：
    生成函数的输出应落在此区间内（允许小幅工艺余量）。
    """
    hw = lay.half_w
    return {
        'hood': {
            # 机盖：从车头伸到风挡根；Z 在机盖高度带
            'X': (lay.front_x, lay.hood_end_x),
            'Y': (-hw * 0.95, hw * 0.95),
            'Z': (lay.waist * 0.35, lay.waist),
        },
        'windshield': {
            'X': (lay.hood_end_x, lay.cabin_start_x + (lay.cabin_end_x - lay.cabin_start_x) * 0.25),
            'Y': (-hw * 0.90, hw * 0.90),
            'Z': (lay.waist, lay.z_roof),
        },
        'roof': {
            'X': (lay.cabin_start_x + (lay.cabin_end_x - lay.cabin_start_x) * 0.25, lay.cabin_end_x),
            'Y': (-hw * 0.92, hw * 0.92),
            'Z': (lay.z_roof * 0.92, lay.z_roof),
        },
        'trunk': {
            'X': (lay.cabin_end_x, lay.rear_x),
            'Y': (-hw * 0.90, hw * 0.90),
            'Z': (lay.waist * 0.6, lay.waist * 1.15),
        },
        'bumper_front': {
            'X': (lay.front_x, lay.front_x + lay.L * 0.06),
            'Y': (-hw, hw),
            'Z': (lay.GC * 0.4, lay.GC + lay.H * 0.16),
        },
        'bumper_rear': {
            'X': (lay.rear_x - lay.L * 0.06, lay.rear_x),
            'Y': (-hw, hw),
            'Z': (lay.GC * 0.4, lay.GC + lay.H * 0.16),
        },
        'door_front': {
            'X': (lay.axle_front_x, (lay.axle_front_x + lay.axle_rear_x) / 2),
            'Y': (hw * 0.88, hw),          # 仅左侧；右侧由前端按 side 镜像
            'Z': (lay.GC, lay.waist + (lay.z_roof - lay.waist) * 0.55),
        },
        'door_rear': {
            'X': ((lay.axle_front_x + lay.axle_rear_x) / 2, lay.cabin_end_x + lay.L * 0.05),
            'Y': (hw * 0.88, hw),
            'Z': (lay.GC, lay.waist + (lay.z_roof - lay.waist) * 0.55),
        },
        'fender_front': {
            'X': (lay.axle_front_x - lay.L * 0.09, lay.axle_front_x + lay.L * 0.09),
            'Y': (hw * 0.80, hw),
            'Z': (lay.GC * 0.6, lay.GC + lay.H * 0.28),
        },
        'fender_rear': {
            'X': (lay.axle_rear_x - lay.L * 0.09, lay.axle_rear_x + lay.L * 0.09),
            'Y': (hw * 0.80, hw),
            'Z': (lay.GC * 0.6, lay.GC + lay.H * 0.28),
        },
    }


def check_against_layout(lay: Layout, component_boxes: Dict[str, Dict[str, List[float]]],
                         margin_ratio: float = 0.08) -> List[str]:
    """校验各零件实际区间是否落在布局契约内

    返回问题列表（空列表表示通过）。`component_boxes` 形如
    `{'hood': {'X': [min,max], 'Y': [...], 'Z': [...]}, ...}`
    """
    issues: List[str] = []
    want = part_boxes(lay)
    for name, box in component_boxes.items():
        ref = want.get(name)
        if ref is None:
            continue
        for axis, (lo, hi) in ref.items():
            got = box.get(axis)
            if not got or len(got) != 2:
                continue
            span = max(abs(hi - lo), 1.0)
            m = span * margin_ratio
            if got[0] < lo - m or got[1] > hi + m:
                issues.append(
                    f"{name}.{axis} 越界：实际[{got[0]:.0f},{got[1]:.0f}] "
                    f"期望[{lo:.0f},{hi:.0f}]（余量 {m:.0f}）")
    return issues
