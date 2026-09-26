# -*- coding: utf-8 -*-
"""
控制线构建器
============

将知识库车型的 14 项规范参数转换为车身比例控制线：

  侧视（XZ 平面，车头朝 +X，地面 Z=0，单位 mm）：
    - 整车包络矩形（长×高）
    - 前后轮圆（含胎壁直径，触地）
    - 轴距连线
    - 车身侧影轮廓线（前保→引擎盖→风挡→车顶→后窗→尾厢→后保→车底）
    - 离地间隙参考线
  俯视（XY 平面，Z=0）：
    - 整车矩形（长×宽）
    - 前后轮距参考线

注意：侧影轮廓中引擎盖/风挡/车顶的高度位置由总高按经验比例推导，
属于「比例参考模板」，用于与设计师现有模型做比例对标与快改，
不代表精确的真实曲面。

坐标计算（compute_layout）不依赖 Rhino，可独立单测；
build_geometry() 依赖 Rhino.Geometry，仅在 Rhino 进程内可用。
"""
from __future__ import annotations

import math

# ============================================================
# 图层定义：键 → (图层名, RGB)
# ============================================================
LAYERS = {
    "envelope": ("EVO-包络参考", (120, 120, 120)),
    "wheels":   ("EVO-车轮",     (30, 30, 30)),
    "profile":  ("EVO-侧影轮廓", (40, 90, 220)),
    "top":      ("EVO-俯视参考", (30, 150, 90)),
    "labels":   ("EVO-标注",     (200, 60, 60)),
}


# ============================================================
# 1. 纯坐标计算
# ============================================================

def compute_layout(params: dict, scale: float = 1.0) -> dict:
    """计算全部控制线的关键坐标

    Args:
        params: 知识库车型 params（14 键，单位 mm / 度）
        scale: 整体放缩系数

    Returns:
        坐标字典（值为 (x, z) 或 (x, y) 的点坐标，按侧视/俯视分组）
    """
    s = float(scale)
    L = params["overall_length"] * s
    W = params["overall_width"] * s
    H = params["overall_height"] * s
    of_f = params["overhang_front"] * s
    of_r = params["overhang_rear"] * s
    track = params["track_width"] * s
    clr = params["ground_clearance"] * s
    hood_len = params["hood_length"] * s
    roof_len = params.get("roof_height", 350) * s   # 知识库中为车顶纵向长度
    tire_r = params["wheel_diameter"] * s / 2.0

    # 车中心位于原点，车头朝 +X
    x_front = L / 2.0
    x_rear = -L / 2.0
    x_axle_f = x_front - of_f                        # 前轴
    x_axle_r = -(x_front - of_r)                     # 后轴

    # ---- 侧影轮廓关键点（高度为经验比例，属参考模板）----
    z_hood_f = H * 0.52          # 引擎盖前端高度
    z_cowl = H * 0.63           # 引擎盖末端 / 风挡根部（cowl）
    z_roof = H * 0.96           # 车顶最高点
    z_deck = H * 0.58           # 尾厢盖高度

    x_hood_f = x_axle_f + of_f * 0.45
    x_cowl = x_front - hood_len

    # 风挡：知识库角度 26(直立)~50(大躺)，约定为相对垂直方向的倾角
    wa = max(20.0, min(55.0, params["windshield_angle"]))
    x_ws_top = x_cowl - (z_roof - z_cowl) * math.tan(math.radians(wa))

    # 车顶：风挡顶 → 后移 roof_len
    x_roof_rear = x_ws_top - roof_len

    # 后窗：rear_window_angle 同样按相对垂直方向的倾角处理
    rwa = max(10.0, min(60.0, params["rear_window_angle"]))
    x_deck = x_roof_rear - (z_roof - z_deck) * math.tan(math.radians(rwa))
    # 防止尾厢点穿过后保（大倾角小车的钳制）
    x_deck = max(x_deck, x_rear + of_r * 0.25)

    profile = [
        (x_front, clr),              # 前保下
        (x_hood_f, z_hood_f),        # 引擎盖前
        (x_cowl, z_cowl),            # 风挡根
        (x_ws_top, z_roof),          # 风挡顶
        (x_roof_rear, z_roof),       # 车顶后
        (x_deck, z_deck),            # 尾厢
        (x_rear, H * 0.45),          # 后保上
        (x_rear, clr),               # 后保下
    ]

    return {
        "scale": s,
        "L": L, "W": W, "H": H,
        "side": {
            "x_front": x_front, "x_rear": x_rear,
            "rect": [(x_rear, 0.0), (x_front, 0.0),
                     (x_front, H), (x_rear, H)],
            "ground": [(x_rear, 0.0), (x_front, 0.0)],
            "clearance": [(x_rear, clr), (x_front, clr)],
            "axle_line": [(x_axle_r, tire_r), (x_axle_f, tire_r)],
            "wheels": [(x_axle_r, tire_r, tire_r),
                       (x_axle_f, tire_r, tire_r)],
            "profile": profile,
        },
        "top": {
            "rect": [(-L / 2, -W / 2), (L / 2, -W / 2),
                     (L / 2, W / 2), (-L / 2, W / 2)],
            "track_lines": [
                (x_axle_f, -track / 2, track / 2),
                (x_axle_r, -track / 2, track / 2),
            ],
        },
    }


# ============================================================
# 2. Rhino 几何构建
# ============================================================

def build_geometry(layout: dict):
    """由 compute_layout 的结果构建 Rhino 几何对象

    Returns:
        {图层键: [GeometryBase, ...]}
    """
    import Rhino

    out = {k: [] for k in LAYERS}

    def p3_side(p):
        return Rhino.Geometry.Point3d(p[0], 0.0, p[1])

    def p3_top(p):
        return Rhino.Geometry.Point3d(p[0], p[1], 0.0)

    def add_polyline_3d(layer_key, points3d, closed=False):
        """points3d 为 (x, y, z) 三元组列表"""
        poly = Rhino.Geometry.Polyline(
            [Rhino.Geometry.Point3d(*p) for p in points3d])
        if closed:
            poly.Add(poly[0])
        out[layer_key].append(poly.ToPolylineCurve())

    def side_xy_to_xyz(points):
        """侧视 2D 点 (x, z) → 3D (x, 0, z)，即 XZ 竖直平面"""
        return [(p[0], 0.0, p[1]) for p in points]

    side = layout["side"]

    # 包络矩形 / 地面 / 离地间隙 / 轴距线（侧视 XZ 平面，Y=0）
    add_polyline_3d("envelope", side_xy_to_xyz(side["rect"]), closed=True)
    add_polyline_3d("envelope", side_xy_to_xyz(side["ground"]))
    add_polyline_3d("envelope", side_xy_to_xyz(side["clearance"]))
    add_polyline_3d("envelope", side_xy_to_xyz(side["axle_line"]))

    # 车轮圆（圆平面法向 = Y 轴，即在 XZ 平面内）
    y_axis = Rhino.Geometry.Vector3d(0.0, 1.0, 0.0)
    for cx, cz, r in side["wheels"]:
        plane = Rhino.Geometry.Plane(Rhino.Geometry.Point3d(cx, 0.0, cz), y_axis)
        circle = Rhino.Geometry.Circle(plane, r)
        # ArcCurve 是 GeometryBase，可统一走 doc.Objects.Add
        out["wheels"].append(Rhino.Geometry.ArcCurve(circle))

    # 侧影轮廓（闭合，位于 XZ 竖直平面）
    add_polyline_3d("profile", side_xy_to_xyz(side["profile"]), closed=True)

    # 俯视矩形（XY 平面，Z=0）
    add_polyline_3d("top", [(*p, 0.0) for p in layout["top"]["rect"]], closed=True)
    for x, y0, y1 in layout["top"]["track_lines"]:
        add_polyline_3d("top", [(x, y0, 0.0), (x, y1, 0.0)])

    return out


def build_label(model: dict, layout: dict):
    """构建一个文本标注（车型名 + 关键参数），返回 Rhino TextEntity"""
    import Rhino

    p = model["params"]
    text = (
        f"{model['brand_zh_name']} {model['zh_name']}\n"
        f"长 {p['overall_length']} × 宽 {p['overall_width']} × 高 {p['overall_height']} mm\n"
        f"轴距 {p['wheelbase']}  前悬 {p['overhang_front']}  后悬 {p['overhang_rear']}\n"
        f"放缩 ×{layout['scale']:.2f}"
    )
    te = Rhino.Geometry.TextEntity()
    te.PlainText = text
    te.TextHeight = 55.0
    origin = Rhino.Geometry.Point3d(-layout["L"] / 2, 0.0, layout["H"] + 120.0)
    # 标注立于 XZ 竖直平面：X 轴为阅读方向，Z 轴为上行方向（法向=Y）
    te.Plane = Rhino.Geometry.Plane(
        origin,
        Rhino.Geometry.Vector3d.XAxis,
        Rhino.Geometry.Vector3d.ZAxis,
    )
    return te
