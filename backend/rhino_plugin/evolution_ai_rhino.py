# -*- coding: utf-8 -*-
"""
EVOLUTION-AI × Rhino 插件 MVP
==============================

在 Rhino 8 (Script Editor / CPython 3) 中直接运行的参数化汽车车身生成器。

功能：
  - 读取 automotive_parameters.json（与 Web 后端共用同一份参数定义）
  - 用 Rhino.Geometry.NurbsSurface 生成工业级 NURBS 曲面（而非我们的 numpy 实现）
  - Eto UI 面板：滑条 / 数值框 实时改参，几何毫秒级更新
  - 支持导入 / 导出参数快照（与 Web 端的 import_export API 格式兼容）

使用方法（Rhino 8）：
  1. 打开 Rhino 8 → Tools → Script Editor (或按 Ctrl+Alt+N)
  2. 新建 Python 3 脚本，粘贴本文件全部内容
  3. 点击 Run（或 F5）
  4. 在弹出的 EVOLUTION-AI 面板里拖动滑条即可实时改车身比例

依赖：
  - Rhino 8（含 CPython 3 运行时）
  - 无需安装任何第三方包（仅用标准库 json/math + Rhino.Geometry + Eto）

作者：EVOLUTION-AI.DESIGN
"""

import json
import math
import os
import sys
from pathlib import Path

# ============================================================
# 把 backend/app 加入 sys.path，以便导入 texture_analyzer
# ============================================================
_BACKEND_APP = Path(__file__).resolve().parent.parent / "app" if "__file__" in dir() else None
if _BACKEND_APP and _BACKEND_APP.exists():
    sys.path.insert(0, str(_BACKEND_APP))

try:
    from texture_analyzer import analyze_texture, list_target_regions, TextureFeatures
    TEXTURE_AVAILABLE = True
except ImportError:
    TEXTURE_AVAILABLE = False


# ============================================================
# Rhino 运行时导入（在 Rhino 外部运行时给出友好提示）
# ============================================================
try:
    import Rhino
    import rhinoscriptsyntax as rs
    import scriptcontext as sc
    from Rhino.Geometry import (
        Point3d, Vector3d, Plane, NurbsSurface, Brep, Mesh,
        Cylinder, Circle, Interval,
    )
    import Eto
    import Eto.Forms as forms
    import Eto.Drawing as drawing
    RHINO_AVAILABLE = True
except ImportError:
    RHINO_AVAILABLE = False
    # 非 Rhino 环境下提供占位模块，让脚本可被导入（用于测试参数/数学逻辑）
    class _DummyModule:
        def __getattr__(self, name):
            # 返回一个可继承的占位类
            class _DummyCls:
                def __init__(self, *a, **k):
                    pass
                def __getattr__(self, n):
                    return _DummyCls()
                def __call__(self, *a, **k):
                    return _DummyCls()
            return _DummyCls
    forms = _DummyModule()
    drawing = _DummyModule()
    print("[WARNING] 未检测到 Rhino 运行时。本脚本需在 Rhino 8 Script Editor 中运行。")


# ============================================================
# 常量
# ============================================================

# 参数 JSON 路径（与后端共用同一份）
SCRIPT_DIR = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
PARAMS_JSON = SCRIPT_DIR / "config" / "automotive_parameters.json"

# 如果脚本放在 rhino_plugin/ 子目录，往上找
if not PARAMS_JSON.exists():
    for parent in [SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
        candidate = parent / "config" / "automotive_parameters.json"
        if candidate.exists():
            PARAMS_JSON = candidate
            break

# Rhino 图层名
LAYER_PREFIX = "EVOLUTION-AI"
PARAMS_LAYER = f"{LAYER_PREFIX}::Parameters"


# ============================================================
# 参数管理
# ============================================================

class CarParams:
    """汽车参数容器：从 JSON 加载，支持覆盖，提供便捷取值"""

    def __init__(self, json_path=None, overrides=None):
        if json_path is None:
            json_path = PARAMS_JSON
        with open(json_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.params = self.config["automotive_parameters"]
        # 应用覆盖
        if overrides:
            for group, items in overrides.items():
                if group in self.params:
                    for key, val in items.items():
                        if key in self.params[group]:
                            self.params[group][key]["value"] = val
        self._init_coords()

    def _init_coords(self):
        """初始化车身坐标系关键尺寸（与 car_generator.py 保持一致）"""
        s = self.params["整车尺寸"]
        p = self.params["比例参数"]
        self.L = s["overall_length"]["value"]
        self.W = s["overall_width"]["value"]
        self.H = s["overall_height"]["value"]
        self.WB = s["wheelbase"]["value"]
        self.TW = s["track_width"]["value"]
        self.GC = s["ground_clearance"]["value"]
        self.FO = p["overhang_front"]["value"]
        self.RO = p["overhang_rear"]["value"]
        self.fwx = self.FO + self.GC
        self.rwx = self.L - self.RO
        self.fwz = self.TW / 2

    def p(self, group, key):
        """取参数值"""
        return self.params[group][key]["value"]

    def meta(self, group, key):
        """取参数元数据（min/max/unit/name/category）"""
        return self.params[group][key]

    def to_overrides(self):
        """导出当前所有参数覆盖值（与 Web 端 snapshot 格式兼容）"""
        out = {}
        for group, items in self.params.items():
            out[group] = {k: v["value"] for k, v in items.items()}
        return out

    def all_params_flat(self):
        """展开为 (group, key, meta) 列表，供 UI 生成滑条"""
        flat = []
        for group, items in self.params.items():
            for key, meta in items.items():
                flat.append((group, key, meta))
        return flat


# ============================================================
# 几何生成器（核心：把 car_generator.py 的数学逻辑迁移到 Rhino.Geometry）
# ============================================================

class RhinoCarBodyGenerator:
    """基于 Rhino.Geometry 的车身生成器

    与后端 NURBSCarBodyGenerator 的数学逻辑完全一致，
    但输出是 Rhino.Geometry.NurbsSurface 等原生对象，可直接加入文档。
    """

    def __init__(self, params: CarParams):
        self.p = params

    # ---------- 工具方法 ----------

    @staticmethod
    def _deg(deg):
        return math.radians(deg)

    @staticmethod
    def _create_nurbs_surface(cps_2d, degree_u=3, degree_v=3):
        """从控制点二维列表创建 Rhino NURBS 曲面

        cps_2d: 二维列表，cps_2d[i][j] = (x, y, z) 元组
        """
        nu = len(cps_2d)
        nv = len(cps_2d[0]) if nu > 0 else 0
        if nu < 2 or nv < 2:
            return None
        # Rhino 的 NurbsSurface.Create 需要 degree+1 个控制点
        # 如果控制点不够，自动降阶
        du = min(degree_u, nu - 1)
        dv = min(degree_v, nv - 1)
        # 转换为 Point3d 二维数组
        points = [[Point3d(x, y, z) for (x, y, z) in row] for row in cps_2d]
        surf = NurbsSurface.Create(points, du, dv)
        return surf

    # ---------- 部件生成 ----------

    def generate_hood(self):
        """发动机盖"""
        length = self.p.p("车身部件", "hood_length")
        width = self.p.p("车身部件", "hood_width")
        height = self.p.p("车身部件", "hood_height")
        angle = self._deg(self.p.p("造型角度", "hood_angle"))
        nu, nv = 8, 6
        cx_start, cy_base = 200, 300
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * length
                y = cy_base + height * math.sin(u * math.pi) * math.cos(v * math.pi) + u * math.tan(angle) * length * 0.3
                z = (v - 0.5) * width
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "发动机盖", "#c0c0c0"

    def generate_windshield(self):
        """前风挡玻璃"""
        width = self.p.p("车身部件", "windshield_width")
        height = self.p.p("车身部件", "windshield_height")
        angle = self._deg(90 - self.p.p("造型角度", "windshield_angle"))
        nu, nv = 6, 6
        cx_base, cy_bottom = 1700, 450
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_base - u * height * math.sin(angle)
                y = cy_bottom + u * height * math.cos(angle)
                z = (v - 0.5) * width * (1 - u * 0.15)
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "前风挡玻璃", "#87CEEB"

    def generate_roof(self):
        """车顶"""
        width = self.p.p("车身部件", "roof_width")
        height = self.p.p("车身部件", "roof_height")
        nu, nv = 10, 6

        windshield_top_x = self.p.FO + self.p.WB * 0.4
        windshield_top_y = self.p.GC + 900
        trunk_start_x = self.p.L - self.p.RO - self.p.p("车身部件", "trunk_length") * 0.3
        max_roof_length = trunk_start_x - windshield_top_x
        slant_factor = min(max(self.p.p("造型角度", "rear_slant_angle") / 60.0, 0), 1)
        roof_len = max(max_roof_length * (1 - slant_factor * 0.7), 800)

        cx_start = windshield_top_x
        cy_base = windshield_top_y
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * roof_len
                y = cy_base + height * math.cos((u - 0.5) * math.pi * 2)
                z = (v - 0.5) * width * (1 - u * 0.2)
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "车顶", "#c0c0c0"

    def generate_rear_window(self):
        """后风挡玻璃"""
        width = self.p.p("车身部件", "rear_window_width")
        height = self.p.p("车身部件", "rear_window_height")
        rear_window_angle = self._deg(self.p.p("造型角度", "rear_window_angle"))
        nu, nv = 6, 6

        windshield_top_x = self.p.FO + self.p.WB * 0.4
        windshield_top_y = self.p.GC + 900
        trunk_start_x = self.p.L - self.p.RO - self.p.p("车身部件", "trunk_length") * 0.3
        max_roof_length = trunk_start_x - windshield_top_x
        slant_factor = min(max(self.p.p("造型角度", "rear_slant_angle") / 60.0, 0), 1)
        roof_len = max(max_roof_length * (1 - slant_factor * 0.7), 800)

        rear_window_top_x = windshield_top_x + roof_len
        rear_window_top_y = windshield_top_y
        rear_window_bottom_x = rear_window_top_x - height / math.tan(rear_window_angle)
        rear_window_bottom_y = rear_window_top_y - height

        cx_base = rear_window_top_x
        cy_top = rear_window_top_y
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_base - u * (rear_window_top_x - rear_window_bottom_x)
                y = cy_top - u * height
                z = (v - 0.5) * width * (1 - u * 0.1)
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "后风挡玻璃", "#87CEEB"

    def generate_trunk(self):
        """行李箱盖"""
        length = self.p.p("车身部件", "trunk_length")
        width = self.p.p("车身部件", "trunk_width")
        nu, nv = 6, 6

        windshield_top_x = self.p.FO + self.p.WB * 0.4
        windshield_top_y = self.p.GC + 900
        trunk_start_x = self.p.L - self.p.RO - length * 0.3
        max_roof_length = trunk_start_x - windshield_top_x
        slant_factor = min(max(self.p.p("造型角度", "rear_slant_angle") / 60.0, 0), 1)
        roof_len = max(max_roof_length * (1 - slant_factor * 0.7), 800)

        rear_window_top_x = windshield_top_x + roof_len
        rear_window_angle = self._deg(self.p.p("造型角度", "rear_window_angle"))
        rear_window_height = self.p.p("车身部件", "rear_window_height")
        rear_window_bottom_x = rear_window_top_x - rear_window_height / math.tan(rear_window_angle)

        cx_start = rear_window_bottom_x
        cy_base = windshield_top_y - rear_window_height + 50
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * length
                y = cy_base + 80 * math.exp(-u * 4) * math.cos(v * math.pi)
                z = (v - 0.5) * width
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "行李箱盖", "#c0c0c0"

    def generate_bumper_front(self):
        """前保险杠"""
        width = self.p.p("整车尺寸", "overall_width")
        nu, nv = 6, 8
        length, height = 200, 250
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = -length * (1 - u)
                y = height * (1 - math.cos(u * math.pi)) * 0.5 + 100
                z = (v - 0.5) * width * (0.85 + u * 0.15)
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "前保险杠", "#808080"

    def generate_bumper_rear(self):
        """后保险杠"""
        width = self.p.p("整车尺寸", "overall_width")
        nu, nv = 6, 8
        length, height = 200, 250
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = length * u
                y = height * (1 - math.cos(u * math.pi)) * 0.5 + 100
                z = (v - 0.5) * width * (0.85 + (1 - u) * 0.15)
                row.append((x, y, z))
            cps.append(row)
        return self._create_nurbs_surface(cps), "后保险杠", "#808080"

    def generate_fender(self, position="front", side="left"):
        """翼子板"""
        radius = self.p.p("车身部件", "wheel_arch_radius")
        nu, nv = 8, 6
        x_center = self.p.fwx if position == "front" else self.p.rwx
        z_center = self.p.fwz + 30 if side == "left" else -self.p.fwz - 30
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                theta, phi = u * math.pi, v * math.pi
                x = x_center + radius * math.cos(theta) * 0.6
                y = self.p.GC + radius * math.sin(theta) * math.cos(phi)
                z = z_center + radius * math.sin(theta) * math.sin(phi) * 0.5
                row.append((x, y, z))
            cps.append(row)
        name = f"{side}{position}翼子板"
        return self._create_nurbs_surface(cps), name, "#c0c0c0"

    def generate_wheel(self, position="front", side="left"):
        """车轮（用 Rhino Cylinder 原生几何）"""
        diameter = self.p.p("车身部件", "wheel_diameter")
        width = self.p.p("车身部件", "wheel_width")
        x_pos = self.p.fwx if position == "front" else self.p.rwx
        z_pos = self.p.fwz if side == "left" else -self.p.fwz
        y_pos = self.p.GC + diameter / 2
        radius = diameter / 2
        # 圆柱轴沿 Z 方向
        circle = Circle(Plane(Point3d(x_pos, y_pos, z_pos), Vector3d(0, 0, 1)), radius)
        cylinder = Cylinder(circle, width)
        brep = cylinder.ToBrep(True, True)
        name = f"{side}{position}轮"
        return brep, name, "#222222"

    def generate_door(self, side="left", front=True):
        """车门（简化为平面曲面）"""
        if front:
            length = self.p.p("车身部件", "door_front_length")
            height = self.p.p("车身部件", "door_front_height")
            cx_start, cy_base = 2100, 250
            name = f"{side}前门"
        else:
            length = self.p.p("车身部件", "door_rear_length")
            height = self.p.p("车身部件", "door_rear_height")
            cx_start, cy_base = 3300, 280
            name = f"{side}后门"
        nu, nv = 4, 4
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                row.append((cx_start + u * length, cy_base + v * height, 0.0))
            cps.append(row)
        return self._create_nurbs_surface(cps), name, "#c0c0c0"

    def generate_complete_car(self):
        """生成完整车身，返回 [(geometry, name, color), ...] 列表"""
        parts = []
        # 曲面类部件
        surf_generators = [
            self.generate_bumper_front,
            self.generate_hood,
            self.generate_windshield,
            self.generate_roof,
            self.generate_rear_window,
            self.generate_trunk,
            self.generate_bumper_rear,
        ]
        for gen in surf_generators:
            geom, name, color = gen()
            if geom is not None:
                parts.append((geom, name, color))
        # 翼子板（4个）
        for pos in ["front", "rear"]:
            for side in ["left", "right"]:
                geom, name, color = self.generate_fender(pos, side)
                if geom is not None:
                    parts.append((geom, name, color))
        # 车门（4个）
        for front in [True, False]:
            for side in ["left", "right"]:
                geom, name, color = self.generate_door(side, front)
                if geom is not None:
                    parts.append((geom, name, color))
        # 车轮（4个）
        for pos in ["front", "rear"]:
            for side in ["left", "right"]:
                geom, name, color = self.generate_wheel(pos, side)
                if geom is not None:
                    parts.append((geom, name, color))
        return parts


# ============================================================
# Rhino 文档操作
# ============================================================

def _hex_to_argb(hex_color, alpha=255):
    """#RRGGBB → (A, R, G, B)"""
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (alpha, r, g, b)


def _ensure_layer(name, color_hex=None):
    """确保图层存在，返回 layer index"""
    doc = sc.doc
    idx = doc.Layers.FindName(name, True)
    if idx < 0:
        layer = Rhino.DocObjects.Layer()
        layer.Name = name
        if color_hex:
            a, r, g, b = _hex_to_argb(color_hex)
            layer.Color = drawing.Color.FromArgb(a, r, g, b)
        idx = doc.Layers.Add(layer)
    return idx


def _delete_layer_recursive(name):
    """删除图层及其所有对象"""
    doc = sc.doc
    layer = doc.Layers.FindName(name, True)
    if layer:
        # 删除该图层下所有对象
        settings = Rhino.DocObjects.ObjectEnumeratorSettings()
        settings.LayerIndexFilter = layer.Index
        settings.ActiveObjects = True
        objs = doc.Objects.GetObjectList(settings)
        for obj in objs:
            doc.Objects.Delete(obj, True)
        # 删除图层
        doc.Layers.Delete(layer, True)


def clear_evolution_objects():
    """清理上一次生成的 EVOLUTION-AI 图层和对象"""
    doc = sc.doc
    # 找到所有以 LAYER_PREFIX 开头的图层
    to_delete = []
    for layer in doc.Layers:
        if layer.Name.startswith(LAYER_PREFIX) or layer.FullPath.startswith(LAYER_PREFIX):
            to_delete.append(layer.FullPath)
    for full_path in to_delete:
        _delete_layer_recursive(full_path)


def add_geometry_to_doc(parts, layer_name=LAYER_PREFIX):
    """把生成的几何加入 Rhino 文档"""
    doc = sc.doc
    _ensure_layer(layer_name)

    added = []
    for geom, name, color_hex in parts:
        # 每个部件一个子图层
        part_layer = f"{layer_name}::{name}"
        _ensure_layer(part_layer, color_hex)

        a, r, g, b = _hex_to_argb(color_hex)
        color = drawing.Color.FromArgb(a, r, g, b)

        # 创建对象属性
        attrs = doc.CreateDefaultAttributes()
        attrs.LayerIndex = doc.Layers.FindName(part_layer, True).Index
        attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
        attrs.ObjectColor = color

        # 添加几何
        if isinstance(geom, NurbsSurface):
            id_ = doc.Objects.AddSurface(geom, attrs)
        elif isinstance(geom, Brep):
            id_ = doc.Objects.AddBrep(geom, attrs)
        else:
            id_ = doc.Objects.Add(geom, attrs)
        added.append(id_)

    doc.Views.Redraw()
    return added


def build_and_render(params: CarParams):
    """清空旧对象 → 生成新几何 → 加入文档"""
    clear_evolution_objects()
    gen = RhinoCarBodyGenerator(params)
    parts = gen.generate_complete_car()
    ids = add_geometry_to_doc(parts)
    return len(ids)


# ============================================================
# Eto UI 面板
# ============================================================

class EvolutionAIPanel(forms.Form):
    """EVOLUTION-AI 参数控制面板"""

    def __init__(self, params: CarParams):
        super().__init__()
        self.params = params
        self.Title = "EVOLUTION-AI | 参数化车身设计"
        self.ClientSize = drawing.Size(420, 700)

        # 保存每个滑条的引用，方便取值
        self.sliders = {}  # (group, key) -> (slider, label, value_label)

        self._build_ui()
        self._render()  # 初始渲染

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(5, 3)
        layout.Padding = drawing.Padding(10)

        # ===== 顶部标题 =====
        title = forms.Label()
        title.Text = "EVOLUTION-AI.DESIGN"
        title.Font = drawing.Font(None, 16, drawing.FontStyle.Bold)
        layout.AddRow(title)

        subtitle = forms.Label()
        subtitle.Text = "参数化汽车车身设计 · Rhino 插件 MVP"
        subtitle.TextColor = drawing.Color.FromArgb(120, 120, 120)
        layout.AddRow(subtitle)
        layout.AddRow(None)  # 空行

        # ===== 操作按钮 =====
        btn_row = forms.StackLayout()
        btn_row.Orientation = forms.Orientation.Horizontal
        btn_row.Spacing = 5

        self.btn_render = forms.Button(Text="重新生成")
        self.btn_render.Click += self._on_render
        btn_row.Items.Add(self.btn_render)

        self.btn_export = forms.Button(Text="导出参数快照")
        self.btn_export.Click += self._on_export
        btn_row.Items.Add(self.btn_export)

        self.btn_import = forms.Button(Text="导入参数快照")
        self.btn_import.Click += self._on_import
        btn_row.Items.Add(self.btn_import)

        self.btn_reset = forms.Button(Text="重置默认")
        self.btn_reset.Click += self._on_reset
        btn_row.Items.Add(self.btn_reset)

        layout.AddRow(btn_row)
        layout.AddRow(None)

        # ===== 参数分组：用 TabControl 按 category 分组 =====
        self.tabs = forms.TabControl()

        # 按 group 分组
        groups = {}
        for group_name, items in self.params.params.items():
            groups[group_name] = list(items.items())

        for group_name, items in groups.items():
            tab = forms.TabPage()
            tab.Text = group_name

            tab_layout = forms.DynamicLayout()
            tab_layout.Spacing = drawing.Size(3, 2)
            tab_layout.Padding = drawing.Padding(8)

            for key, meta in items:
                # 跳过无 min/max 的参数（如比例参数里的 ratio）
                if "min_value" not in meta or "max_value" not in meta:
                    continue
                min_v = meta["min_value"]
                max_v = meta["max_value"]
                cur_v = meta["value"]
                unit = meta.get("unit", "")

                # 名称 + 当前值
                name_label = forms.Label()
                name_label.Text = f"{meta['name']} ({unit})"
                name_label.Width = 140

                val_label = forms.Label()
                val_label.Text = f"{cur_v:.1f}"
                val_label.Width = 60
                val_label.TextAlignment = forms.TextAlignment.Right

                # 数值输入框
                num_box = forms.NumericUpDown()
                num_box.DecimalPlaces = 1
                num_box.MinValue = min_v
                num_box.MaxValue = max_v
                num_box.Value = cur_v
                num_box.Width = 80

                # 滑条
                slider = forms.Slider()
                slider.MinValue = 0
                slider.MaxValue = 1000
                slider.Value = int((cur_v - min_v) / (max_v - min_v) * 1000) if max_v > min_v else 0
                slider.Width = 160

                # 绑定事件
                slider.ValueChanged += self._make_slider_handler(group_name, key, min_v, max_v, val_label, num_box)
                num_box.ValueChanged += self._make_numeric_handler(group_name, key, min_v, max_v, val_label, slider)

                self.sliders[(group_name, key)] = (slider, val_label, num_box)

                row = forms.StackLayout()
                row.Orientation = forms.Orientation.Horizontal
                row.Spacing = 4
                row.Items.Add(name_label)
                row.Items.Add(slider)
                row.Items.Add(num_box)
                row.Items.Add(val_label)
                tab_layout.AddRow(row)

            scroll = forms.Scrollable()
            scroll.Content = tab_layout
            tab.Content = scroll
            self.tabs.Pages.Add(tab)

        # ===== 纹理设计 TabPage =====
        self._build_texture_tab()

        layout.AddRow(self.tabs)

        # ===== 底部状态 =====
        self.status = forms.Label()
        self.status.Text = "就绪"
        self.status.TextColor = drawing.Color.FromArgb(0, 128, 0)
        layout.AddRow(None)
        layout.AddRow(self.status)

        self.Content = layout

    def _make_slider_handler(self, group, key, min_v, max_v, val_label, num_box):
        def handler(sender, e):
            ratio = sender.Value / 1000.0
            val = min_v + ratio * (max_v - min_v)
            # 精度处理：整数参数取整，角度保留1位
            meta = self.params.meta(group, key)
            if meta.get("type") in ("length", "width", "height", "distance", "diameter", "radius"):
                val = round(val)
            else:
                val = round(val, 1)
            self.params.params[group][key]["value"] = val
            val_label.Text = f"{val:.1f}"
            num_box.Value = val
            self.params._init_coords()
        return handler

    def _make_numeric_handler(self, group, key, min_v, max_v, val_label, slider):
        def handler(sender, e):
            val = sender.Value
            val = max(min_v, min(max_v, val))
            self.params.params[group][key]["value"] = val
            val_label.Text = f"{val:.1f}"
            ratio = (val - min_v) / (max_v - min_v) if max_v > min_v else 0
            slider.Value = int(ratio * 1000)
            self.params._init_coords()
        return handler

    def _on_render(self, sender, e):
        self._render()

    def _render(self):
        try:
            count = build_and_render(self.params)
            self.status.Text = f"✅ 已生成 {count} 个几何对象"
            self.status.TextColor = drawing.Color.FromArgb(0, 128, 0)
        except Exception as ex:
            self.status.Text = f"❌ 生成失败: {str(ex)[:60]}"
            self.status.TextColor = drawing.Color.FromArgb(200, 0, 0)

    # ====== 纹理设计相关 ======

    def _build_texture_tab(self):
        """构建纹理设计 TabPage"""
        tab = forms.TabPage()
        tab.Text = "🎨 纹理设计"

        layout = forms.DynamicLayout()
        layout.Spacing = drawing.Size(5, 4)
        layout.Padding = drawing.Padding(10)

        # 说明
        desc = forms.Label()
        desc.Text = "导入设计纹样图，系统自动分析视觉特征并调整选定部位的参数"
        desc.TextColor = drawing.Color.FromArgb(80, 80, 80)
        layout.AddRow(desc)
        layout.AddRow(None)

        if not TEXTURE_AVAILABLE:
            warn = forms.Label()
            warn.Text = "⚠ texture_analyzer 模块不可用，请确保 backend/app/texture_analyzer.py 存在"
            warn.TextColor = drawing.Color.FromArgb(200, 100, 0)
            layout.AddRow(warn)
            scroll = forms.Scrollable()
            scroll.Content = layout
            tab.Content = scroll
            self.tabs.Pages.Add(tab)
            return

        # 导入纹样图按钮
        self.texture_path = None
        self.btn_load_texture = forms.Button(Text="📁 导入纹样图")
        self.btn_load_texture.Click += self._on_load_texture
        layout.AddRow(self.btn_load_texture)

        self.lbl_texture_path = forms.Label()
        self.lbl_texture_path.Text = "未选择纹样图"
        self.lbl_texture_path.TextColor = drawing.Color.FromArgb(120, 120, 120)
        layout.AddRow(self.lbl_texture_path)

        layout.AddRow(None)

        # 目标部位
        region_label = forms.Label()
        region_label.Text = "目标部位："
        self.ddl_region = forms.DropDown()
        for region in list_target_regions():
            self.ddl_region.Items.Add(region)
        self.ddl_region.SelectedIndex = 0
        region_row = forms.StackLayout()
        region_row.Orientation = forms.Orientation.Horizontal
        region_row.Spacing = 5
        region_row.Items.Add(region_label)
        region_row.Items.Add(self.ddl_region)
        layout.AddRow(region_row)

        # 调参强度
        intensity_label = forms.Label()
        intensity_label.Text = "调参强度："
        self.slider_intensity = forms.Slider()
        self.slider_intensity.MinValue = 0
        self.slider_intensity.MaxValue = 100
        self.slider_intensity.Value = 50
        self.slider_intensity.Width = 200
        self.lbl_intensity_val = forms.Label()
        self.lbl_intensity_val.Text = "0.50"
        self.slider_intensity.ValueChanged += self._on_intensity_changed
        intensity_row = forms.StackLayout()
        intensity_row.Orientation = forms.Orientation.Horizontal
        intensity_row.Spacing = 5
        intensity_row.Items.Add(intensity_label)
        intensity_row.Items.Add(self.slider_intensity)
        intensity_row.Items.Add(self.lbl_intensity_val)
        layout.AddRow(intensity_row)

        layout.AddRow(None)

        # 自动调参按钮
        self.btn_auto_params = forms.Button(Text="✨ 自动调参并重新生成")
        self.btn_auto_params.Click += self._on_auto_params
        layout.AddRow(self.btn_auto_params)

        layout.AddRow(None)

        # 特征显示
        feat_label = forms.Label()
        feat_label.Text = "【纹样特征分析】"
        feat_label.Font = drawing.Font(None, 10, drawing.FontStyle.Bold)
        layout.AddRow(feat_label)

        self.lbl_features = forms.Label()
        self.lbl_features.Text = "（导入纹样图后自动分析）"
        self.lbl_features.TextColor = drawing.Color.FromArgb(80, 80, 80)
        layout.AddRow(self.lbl_features)

        scroll = forms.Scrollable()
        scroll.Content = layout
        tab.Content = scroll
        self.tabs.Pages.Add(tab)

    def _on_intensity_changed(self, sender, e):
        val = sender.Value / 100.0
        self.lbl_intensity_val.Text = f"{val:.2f}"

    def _on_load_texture(self, sender, e):
        try:
            dlg = forms.OpenFileDialog()
            dlg.Title = "选择设计纹样图"
            dlg.Filters = [
                forms.FileFilter("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff"),
            ]
            if dlg.ShowDialog(self) == forms.DialogResult.Ok:
                self.texture_path = dlg.FileName
                self.lbl_texture_path.Text = f"已选择: {Path(dlg.FileName).name}"
                self.lbl_texture_path.TextColor = drawing.Color.FromArgb(0, 100, 0)
                # 立即分析并显示特征
                self._analyze_and_show_features()
        except Exception as ex:
            self.status.Text = f"❌ 导入纹样图失败: {str(ex)[:50]}"

    def _analyze_and_show_features(self):
        """分析纹样图并显示特征（不修改参数）"""
        try:
            if not self.texture_path or not Path(self.texture_path).exists():
                return
            from texture_analyzer import extract_features
            feat = extract_features(self.texture_path)
            self.lbl_features.Text = (
                f"方向(0横~1纵): {feat.direction:.2f}  显著性: {feat.direction_score:.2f}\n"
                f"圆润度(0尖~1圆): {feat.roundness:.2f}\n"
                f"复杂度(0简~1繁): {feat.complexity:.2f}\n"
                f"对称性(0~1): {feat.symmetry:.2f}\n"
                f"冷暖(0冷~1暖): {feat.warmth:.2f}  亮度: {feat.brightness:.2f}  饱和度: {feat.saturation:.2f}\n"
                f"主色(RGB): {feat.dominant_color}"
            )
            self.status.Text = "✅ 纹样特征分析完成"
        except Exception as ex:
            self.status.Text = f"❌ 特征分析失败: {str(ex)[:50]}"

    def _on_auto_params(self, sender, e):
        """根据纹样图自动调参并重新生成"""
        try:
            if not self.texture_path or not Path(self.texture_path).exists():
                self.status.Text = "⚠ 请先导入纹样图"
                return
            region = self.ddl_region.SelectedValue
            if not region:
                region = list_target_regions()[0]
            intensity = self.slider_intensity.Value / 100.0

            result = analyze_texture(self.texture_path, target_region=region, intensity=intensity)
            overrides = result["overrides"]
            feat = result["features"]

            # 应用参数覆盖
            for group, items in overrides.items():
                if group in self.params.params:
                    for key, val in items.items():
                        if key in self.params.params[group]:
                            self.params.params[group][key]["value"] = val
            self.params._init_coords()

            # 同步 UI
            self._sync_ui_from_params()

            # 更新特征显示
            self.lbl_features.Text = (
                f"方向(0横~1纵): {feat['direction']:.2f}  显著性: {feat['direction_score']:.2f}\n"
                f"圆润度(0尖~1圆): {feat['roundness']:.2f}\n"
                f"复杂度(0简~1繁): {feat['complexity']:.2f}\n"
                f"对称性(0~1): {feat['symmetry']:.2f}\n"
                f"冷暖(0冷~1暖): {feat['warmth']:.2f}  亮度: {feat['brightness']:.2f}  饱和度: {feat['saturation']:.2f}\n"
                f"主色(RGB): {feat['dominant_color']}"
            )

            # 重新生成几何
            self._render()
            self.status.Text = (
                f"✅ 已根据纹样自动调整 {result['param_count']} 个参数 (部位:{region}, 强度:{intensity:.2f})"
            )
        except Exception as ex:
            self.status.Text = f"❌ 自动调参失败: {str(ex)[:50]}"
            import traceback
            traceback.print_exc()

    def _on_export(self, sender, e):
        """导出参数快照为 JSON（与 Web 端 snapshot 格式兼容）"""
        try:
            dlg = forms.SaveFileDialog()
            dlg.Title = "导出参数快照"
            dlg.Filters = [forms.FileFilter("JSON 文件", "*.json")]
            if dlg.ShowDialog(self) == forms.DialogResult.Ok:
                snap = self.params.to_overrides()
                with open(dlg.FileName, "w", encoding="utf-8") as f:
                    json.dump(snap, f, ensure_ascii=False, indent=2)
                self.status.Text = f"✅ 已导出: {Path(dlg.FileName).name}"
        except Exception as ex:
            self.status.Text = f"❌ 导出失败: {str(ex)[:60]}"

    def _on_import(self, sender, e):
        """从参数快照 JSON 导入"""
        try:
            dlg = forms.OpenFileDialog()
            dlg.Title = "导入参数快照"
            dlg.Filters = [forms.FileFilter("JSON 文件", "*.json")]
            if dlg.ShowDialog(self) == forms.DialogResult.Ok:
                with open(dlg.FileName, "r", encoding="utf-8") as f:
                    overrides = json.load(f)
                # 应用到 params
                for group, items in overrides.items():
                    if group in self.params.params:
                        for key, val in items.items():
                            if key in self.params.params[group]:
                                self.params.params[group][key]["value"] = val
                self.params._init_coords()
                self._sync_ui_from_params()
                self._render()
                self.status.Text = f"✅ 已导入: {Path(dlg.FileName).name}"
        except Exception as ex:
            self.status.Text = f"❌ 导入失败: {str(ex)[:60]}"

    def _on_reset(self, sender, e):
        """重置为 JSON 默认值"""
        try:
            self.params = CarParams()  # 重新加载
            self._sync_ui_from_params()
            self._render()
            self.status.Text = "✅ 已重置为默认参数"
        except Exception as ex:
            self.status.Text = f"❌ 重置失败: {str(ex)[:60]}"

    def _sync_ui_from_params(self):
        """把 params 的值同步到 UI 控件"""
        for (group, key), (slider, val_label, num_box) in self.sliders.items():
            meta = self.params.meta(group, key)
            if "min_value" not in meta:
                continue
            min_v = meta["min_value"]
            max_v = meta["max_value"]
            cur_v = meta["value"]
            num_box.Value = cur_v
            val_label.Text = f"{cur_v:.1f}"
            ratio = (cur_v - min_v) / (max_v - min_v) if max_v > min_v else 0
            slider.Value = int(max(0, min(1000, ratio * 1000)))


# ============================================================
# 主入口
# ============================================================

def main():
    if not RHINO_AVAILABLE:
        print("[ERROR] 本脚本必须在 Rhino 8 Script Editor 中运行。")
        print("        请打开 Rhino 8 → Ctrl+Alt+N → 粘贴本脚本 → Run")
        return

    if not PARAMS_JSON.exists():
        print(f"[ERROR] 找不到参数配置文件: {PARAMS_JSON}")
        print("        请确保 automotive_parameters.json 在 config/ 目录下")
        return

    # 加载参数
    params = CarParams(PARAMS_JSON)
    print(f"[INFO] 已加载 {sum(len(v) for v in params.params.values())} 个参数")
    print(f"[INFO] 参数文件: {PARAMS_JSON}")

    # 生成初始车身
    count = build_and_render(params)
    print(f"[INFO] 已生成 {count} 个几何对象到图层 {LAYER_PREFIX}")

    # 显示 UI 面板
    panel = EvolutionAIPanel(params)
    panel.Show()

    return panel


if __name__ == "__main__":
    result = main()
