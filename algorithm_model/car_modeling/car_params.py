"""
CarParams — 整车参数数据类

字段命名以 body.py / glass.py / wheels.py / lights.py / seams.py / mirrors.py
等参数化截面模块实际使用的为准（L/W/H/hood_length/...）；同时通过 property
别名 length/width/height/waistline_ratio 兼容 assembler.py 的旧字段访问。

物理公式：overall_length = front_overhang + wheelbase + rear_overhang
         ≈ hood_length + cabin_length + trunk_length（区段近似）
"""
from dataclasses import dataclass, asdict, field
from typing import List


@dataclass
class CarParams:
    """整车 22 维参数（参数化造型 + 装配统计）。"""

    # --- 主尺寸 (m) ---
    L: float = 4.7        # 车长
    W: float = 1.85       # 车宽
    H: float = 1.45       # 车高
    wheelbase: float = 2.7

    # --- 区段长度 (m) ---
    hood_length: float = 1.1
    cabin_length: float = 2.2
    trunk_length: float = 1.0
    front_overhang: float = 0.9    # 前悬（assembler 用）
    rear_overhang: float = 1.1     # 后悬（assembler 用）

    # --- 高度 ---
    ground_clearance: float = 0.18

    # --- 造型 ---
    roof_arc: float = 0.5            # 车顶弧度因子
    windshield_rake: float = 28.0    # 前挡风倾角 (deg)
    rear_glass_angle: float = 25.0   # 后挡风倾角 (deg)
    waist_line: float = 0.75         # 腰线高度比例 (0-1)
    fender_prominence: float = 0.20  # 轮眉突出 (m)
    wheel_arch_bulge: float = 0.15   # 轮拱外凸 (m, assembler 用)

    # --- 玻璃 ---
    glass_darkness: float = 0.3      # 0=透明, 1=最深

    # --- 车轮 ---
    wheel_radius: float = 0.33
    wheel_width: float = 0.22
    wheel_spoke_count: int = 5

    # --- 灯 ---
    headlight_width: float = 0.45
    headlight_height: float = 0.12

    # ============================================================
    # property 别名：兼容 assembler.py 的旧字段访问（只读透传）
    # ============================================================
    @property
    def length(self) -> float:
        return self.L

    @length.setter
    def length(self, v: float) -> None:
        self.L = v

    @property
    def width(self) -> float:
        return self.W

    @width.setter
    def width(self, v: float) -> None:
        self.W = v

    @property
    def height(self) -> float:
        return self.H

    @height.setter
    def height(self, v: float) -> None:
        self.H = v

    @property
    def waistline_ratio(self) -> float:
        return self.waist_line

    @waistline_ratio.setter
    def waistline_ratio(self, v: float) -> None:
        self.waist_line = v

    # ============================================================
    # 校验 & 序列化
    # ============================================================
    def validate(self) -> List[str]:
        """返回参数错误消息列表；空列表表示全部合法。"""
        errors: List[str] = []
        checks = [
            (3.5 <= self.L <= 6.0,            f"L={self.L} 超出 [3.5, 6.0]"),
            (1.5 <= self.W <= 2.3,            f"W={self.W} 超出 [1.5, 2.3]"),
            (1.1 <= self.H <= 2.1,            f"H={self.H} 超出 [1.1, 2.1]"),
            (2.0 <= self.wheelbase <= 3.5,    f"wheelbase={self.wheelbase} 超出 [2.0, 3.5]"),
            (0.5 <= self.hood_length <= 2.0,  f"hood_length={self.hood_length} 超出 [0.5, 2.0]"),
            (1.0 <= self.cabin_length <= 3.5, f"cabin_length={self.cabin_length} 超出 [1.0, 3.5]"),
            (0.4 <= self.trunk_length <= 2.0, f"trunk_length={self.trunk_length} 超出 [0.4, 2.0]"),
            (0.05 <= self.ground_clearance <= 0.5,
             f"ground_clearance={self.ground_clearance} 超出 [0.05, 0.5]"),
            (0.0 <= self.roof_arc <= 1.5,     f"roof_arc={self.roof_arc} 超出 [0.0, 1.5]"),
            (15.0 <= self.windshield_rake <= 45.0,
             f"windshield_rake={self.windshield_rake} 超出 [15, 45]"),
            (10.0 <= self.rear_glass_angle <= 40.0,
             f"rear_glass_angle={self.rear_glass_angle} 超出 [10, 40]"),
            (0.5 <= self.waist_line <= 0.95,  f"waist_line={self.waist_line} 超出 [0.5, 0.95]"),
            (0.0 <= self.wheel_arch_bulge <= 0.4,
             f"wheel_arch_bulge={self.wheel_arch_bulge} 超出 [0.0, 0.4]"),
            (0.2 <= self.wheel_radius <= 0.5,
             f"wheel_radius={self.wheel_radius} 超出 [0.2, 0.5]"),
            (0.15 <= self.wheel_width <= 0.35,
             f"wheel_width={self.wheel_width} 超出 [0.15, 0.35]"),
            (3 <= self.wheel_spoke_count <= 12,
             f"wheel_spoke_count={self.wheel_spoke_count} 超出 [3, 12]"),
            (0.0 <= self.glass_darkness <= 1.0,
             f"glass_darkness={self.glass_darkness} 超出 [0.0, 1.0]"),
        ]
        for ok, msg in checks:
            if not ok:
                errors.append(msg)
        return errors

    def to_dict(self) -> dict:
        """返回所有字段（含别名）的字典。"""
        d = asdict(self)
        # 追加 property 别名，便于序列化消费方使用旧字段名
        d['length'] = self.L
        d['width'] = self.W
        d['height'] = self.H
        d['waistline_ratio'] = self.waist_line
        return d
