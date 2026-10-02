"""NURBS驱动汽车车身生成器：基于NURBS曲面生成车身全部部件，支持GLB/STL/OBJ/STEP导出"""
import os
import json
import numpy as np
from pathlib import Path

from .nurbs import NURBSSurface, ControlPoint


class NURBSCarBodyGenerator:
    """车身生成器：读取汽车参数配置，生成各部件NURBS曲面并支持导出"""

    def __init__(self, config_path=None, config_override=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'automotive_parameters.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        # 应用参数覆盖：支持两种格式
        #   1) 分组格式 {group: {key: value}}   —— 显式指定分组
        #   2) **扁平格式 {key: value}**        —— 自动查找参数所在分组
        # 扁平格式是 API `params_override` 的形状（Dict[str, float]），
        # 因此这里必须支持，否则接口传参与几何之间会断开。
        if config_override:
            groups = self.config['automotive_parameters']
            for group, items in config_override.items():
                if group in groups and isinstance(items, dict):
                    # 分组格式
                    for key, val in items.items():
                        if isinstance(val, dict):      # 容错：{key: {'value': v}}
                            val = val.get('value')
                        if key in groups[group] and val is not None:
                            groups[group][key]['value'] = val
                elif group in self._flat_index(groups):
                    # 扁平格式：group 实为参数名
                    gname = self._flat_index(groups)[group]
                    if not isinstance(items, dict):
                        self.config['automotive_parameters'][gname][group]['value'] = items
        self.params = self.config['automotive_parameters']
        self.components_cfg = self.config['car_body_components']
        self.nurbs_templates = self.config['nurbs_surface_templates']
        self._init_coords()

    @staticmethod
    def _flat_index(groups):
        """建立 {参数名: 所属分组} 索引，供扁平格式覆盖使用"""
        idx = {}
        for gname, items in groups.items():
            for key in items:
                idx.setdefault(key, gname)
        return idx

    #: 前端字段名 → 后端配置参数名
    #:
    #: 前端 `src/config/carPresets.js` 与后端 `config/automotive_parameters.json`
    #: 的命名并不一致，且部分字段语义不同。此前两者从未对接，
    #: 导致即使传参也无法命中，参数滑杆与几何脱节。
    #:
    #: 映射原则（以**几何语义**为准，而非字面相同）：
    #:   wheel_base / front_overhang / rear_overhang 为纯命名差异，直接映射；
    #:   roof_height **两者同名但语义完全不同**（前端=车顶纵向跨度 550~1000，
    #:   后端 roof_height=车顶板厚度 30~100），若按原名注入会把 850 当成
    #:   板厚、量级错 10 倍以上，故映射到语义对应的 roof_length；
    #:   rear_slant_angle 与 c_pillar_angle 同为 C 柱倾角，做同义映射。
    PARAM_ALIASES = {
        "wheel_base": "wheelbase",
        "front_overhang": "overhang_front",
        "rear_overhang": "overhang_rear",
        "roof_height": "roof_length",
        "rear_slant_angle": "c_pillar_angle",
    }

    #: 这些前端字段名**必须强制走别名**，即使后端存在同名参数。
    #: 用于处理"同名不同义"的陷阱（当前为 roof_height）。
    FORCE_ALIAS = frozenset({"roof_height"})

    @staticmethod
    def resolve_overrides(overrides):
        """把扁平参数覆盖解析为分组格式

        同时处理**前端与后端参数名不一致**的问题（见 `PARAM_ALIASES`
        与 `FORCE_ALIAS`）。公开此方法便于路由层与测试单独验证，
        无需构造生成器。
        """
        if not overrides:
            return {}
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'config', 'automotive_parameters.json')
        with open(cfg_path, 'r', encoding='utf-8') as f:
            groups = json.load(f)['automotive_parameters']
        idx = {}
        for gname, items in groups.items():
            for key in items:
                idx.setdefault(key, gname)
        out = {}
        for k, v in overrides.items():
            if k in NURBSCarBodyGenerator.FORCE_ALIAS:
                name = NURBSCarBodyGenerator.PARAM_ALIASES.get(k)
            else:
                name = k if k in idx else NURBSCarBodyGenerator.PARAM_ALIASES.get(k)
            if name is None:
                continue
            g = idx.get(name)
            if g:
                out.setdefault(g, {})[name] = v
        return out

    def _init_coords(self):
        """初始化车身坐标系关键尺寸"""
        s = self.params['整车尺寸']
        p = self.params['比例参数']
        self.L = s['overall_length']['value']
        self.W = s['overall_width']['value']
        self.H = s['overall_height']['value']
        self.WB = s['wheelbase']['value']
        self.TW = s['track_width']['value']
        self.GC = s['ground_clearance']['value']
        self.FO = p['overhang_front']['value']
        self.RO = p['overhang_rear']['value']
        self.waist = self.GC + (self.H - self.GC) * 0.55
        self.half_w = self.W / 2.0
        self.fwx = self.FO + self.GC
        self.rwx = self.L - self.RO
        self.fwz = self.TW / 2

    def _p(self, group, key):
        return self.params[group][key]['value']

    # ------------------------------------------------------------------
    # 坐标规范化（关键修复）
    # ------------------------------------------------------------------
    # 问题：多数 `generate_*` 生成函数使用的心智模型是
    #          (x = 车长, y = 高度, z = 车宽)
    #       即把**高度写在 Y、宽度写在 Z**，导致曲面被建在 Y-Z 平面里
    #       （渲染出来是一片竖立的板），且各零件互不对齐。
    #
    #       实测证据（修复前）：发动机盖 X∈[200,1500]、Y∈[228.7,475.8]
    #       （这其实是高度）、Z∈[±750]（这其实是车宽）。
    #
    # 规范坐标系：
    #   X = 车长，车头 −X / 车尾 +X，原点在车身中心
    #   Y = 车宽，左侧为正
    #   Z = 车高，地面为 0
    #
    # 作者 `(x, y, z)` → 规范 `(X, Y, Z)`：
    #   X = x − L/2      （把 [0,L] 平移到 [−L/2,+L/2]，统一车头朝向）
    #   Y = z            （作者的 z 实为车宽）
    #   Z = y            （作者的 y 实为高度）
    #
    # ⚠ 刻意**不做启发式自动判定**：曾按"Z 有负值 且 Y 全为正"判断是否
    #   需要转换，但车门曲面的 Z 退化为 0（宽度未展开），判定失败、漏转。
    #   故改为由每个生成函数**显式声明** `axes='author' | 'canonical'`。
    CANONICAL_AXES = True

    def _build_surface(self, cps_3d, template, axes='author'):
        """从3D控制点列表构建NURBS曲面

        Args:
            cps_3d:   控制点网格
            template: NURBS 模板（阶数等）
            axes:     'author'    —— 作者约定 (x=车长, y=高度, z=车宽)，需转换
                      'canonical' —— 已是规范约定，直接使用
        """
        if self.CANONICAL_AXES and axes == 'author':
            cps_3d = self._to_canonical(cps_3d)
        cps = [[ControlPoint(x, y, z, 1.0) for x, y, z in row] for row in cps_3d]
        return NURBSSurface(degree_u=template['degree_u'],
                            degree_v=template['degree_v'],
                            control_points=cps)

    def _to_canonical(self, cps_3d):
        """作者约定 → 规范约定：X = x − L/2，Y = z，Z = y"""
        L = float(self.L)
        return [[(x - L / 2.0, z, y) for (x, y, z) in row] for row in cps_3d]

    def _sample(self, surface, num_u, num_v):
        """采样NURBS曲面为点云"""
        pts = []
        for i in range(num_u):
            u = i / (num_u - 1) if num_u > 1 else 0
            row = []
            for j in range(num_v):
                v = j / (num_v - 1) if num_v > 1 else 0
                row.append(surface.evaluate_point(u, v).tolist())
            pts.append(row)
        return pts

    # ============ 部件生成 ============

    def generate_hood(self):
        """发动机盖"""
        t = self.nurbs_templates['hood']
        length = self._p('车身部件', 'hood_length')
        width = self._p('车身部件', 'hood_width')
        height = self._p('车身部件', 'hood_height')
        angle = np.radians(self._p('造型角度', 'hood_angle'))
        nu, nv = t['num_u'], t['num_v']
        # author 坐标：x 从车头开始（0 ~ length），y 为高度（引擎盖高度），z 为车宽
        # Z 契约 [waist*0.35, waist]：cy_base 取 waist*0.55，保证 height 项下探后仍 ≥ waist*0.35
        cx_start, cy_base = 0, self.waist * 0.55
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * length
                y = cy_base + height * np.sin(u * np.pi) * np.cos(v * np.pi) + u * np.tan(angle) * length * 0.3
                z = (v - 0.5) * width
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '发动机盖', 'type': 'hood', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0', 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_windshield(self):
        """前风挡玻璃"""
        t = self.nurbs_templates['windshield']
        width = self._p('车身部件', 'windshield_width')
        nu, nv = t['num_u'], t['num_v']
        # author 坐标：底边在 hood_end(x=hood_length, y=waist)，
        # 顶边在 cabin 前 25% 处(x=hood_len+0.25*(0.82L-hood_len), y=H*0.96)。
        # 与布局契约 windshield.{X,Z} 对齐。
        hood_len = self._p('车身部件', 'hood_length')
        cabin_end = self.L * 0.82
        x_bot = hood_len
        x_top = hood_len + 0.25 * (cabin_end - hood_len)
        y_bot = self.waist
        y_top = self.H * 0.96
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x_bot + u * (x_top - x_bot)
                y = y_bot + u * (y_top - y_bot)
                z = (v - 0.5) * width * (1 - u * 0.15)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '前风挡玻璃', 'type': 'windshield', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#87CEEB', 'opacity': 0.6, 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_roof(self):
        """车顶"""
        t = self.nurbs_templates['roof']
        width = self._p('车身部件', 'roof_width')
        nu, nv = t['num_u'], t['num_v']

        # author 坐标：与布局契约 roof.{X,Z} 对齐
        # X: [cabin_start+25%cabin, cabin_end] → author [hood_len+0.25*(0.82L-hood_len), 0.82L]
        # Z: [0.92H, H] → y 在 [0.92H, 0.98H] 微拱
        hood_len = self._p('车身部件', 'hood_length')
        cabin_end = self.L * 0.82
        cx_start = hood_len + 0.25 * (cabin_end - hood_len)
        roof_len = cabin_end - cx_start

        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * roof_len
                y = self.H * (0.92 + 0.06 * (0.5 + 0.5 * np.cos((u - 0.5) * np.pi * 2)))
                z = (v - 0.5) * width * (1 - u * 0.2)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '车顶', 'type': 'roof', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0', 'position': {'x': 0, 'y': 0, 'z': 0},
                'roof_end_x': cx_start + roof_len, 'roof_top_y': self.H * 0.98}

    def generate_rear_window(self):
        """后风挡玻璃"""
        t = self.nurbs_templates['rear_window']
        width = self._p('车身部件', 'rear_window_width')
        height = self._p('车身部件', 'rear_window_height')
        rear_window_angle = np.radians(self._p('造型角度', 'rear_window_angle'))
        nu, nv = t['num_u'], t['num_v']

        windshield_top_x = self.FO + self.WB * 0.4
        windshield_top_y = self.GC + 900
        trunk_start_x = self.L - self.RO - self._p('车身部件', 'trunk_length') * 0.3

        max_roof_length = trunk_start_x - windshield_top_x
        slant_factor = min(max(self._p('造型角度', 'rear_slant_angle') / 60.0, 0), 1)
        roof_len = max(max_roof_length * (1 - slant_factor * 0.7), 800)

        rear_window_top_x = windshield_top_x + roof_len
        rear_window_top_y = windshield_top_y

        rear_window_bottom_x = rear_window_top_x - height / np.tan(rear_window_angle)
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
        surf = self._build_surface(cps, t)
        return {'name': '后风挡玻璃', 'type': 'rear_window', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#87CEEB', 'opacity': 0.6, 'position': {'x': 0, 'y': 0, 'z': 0},
                'rear_window_bottom_x': rear_window_bottom_x, 'rear_window_bottom_y': rear_window_bottom_y}

    def generate_trunk(self):
        """行李箱盖"""
        t = self.nurbs_templates['trunk']
        width = self._p('车身部件', 'trunk_width')
        nu, nv = t['num_u'], t['num_v']

        # author 坐标：与布局契约 trunk.{X,Z} 对齐
        # X: [cabin_end, L] = [0.82L, L]；Z: [waist*0.6, waist*1.15]
        cx_start = self.L * 0.82
        cx_end = self.L
        cy_base = self.waist * 0.75  # 基准高度，exp 项向下衰减至 waist*0.6 附近

        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * (cx_end - cx_start)
                y = cy_base + 80 * np.exp(-u * 4) * np.cos(v * np.pi)
                z = (v - 0.5) * width
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '行李箱盖', 'type': 'trunk', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0', 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_door_front(self, side='left'):
        """前门"""
        t = self.nurbs_templates['door_front']
        length = self._p('车身部件', 'door_front_length')
        height = self._p('车身部件', 'door_front_height')
        nu, nv = t['num_u'], t['num_v']
        cx_start = self.FO  # 前门从前轴位置开始
        cy_base = self.GC
        z_base = self.half_w * 0.92  # 贴近车身侧面（契约 Y∈[0.88hw, hw]）
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                cps_row = (cx_start + u * length, cy_base + v * height,
                           z_base if side == 'left' else -z_base)
                row.append(cps_row)
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': f'{side}前门', 'type': 'door', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0',
                'position': {'x': 0, 'y': 0, 'z': 0}, 'side': side}

    def generate_door_rear(self, side='left'):
        """后门"""
        t = self.nurbs_templates['door_rear']
        length = self._p('车身部件', 'door_rear_length')
        height = self._p('车身部件', 'door_rear_height')
        nu, nv = t['num_u'], t['num_v']
        cx_start = self.L * 0.50  # 后门约在 50%~70% 车长
        cy_base = self.GC
        z_base = self.half_w * 0.90
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                row.append((cx_start + u * length, cy_base + v * height,
                            z_base if side == 'left' else -z_base))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': f'{side}后门', 'type': 'door', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0',
                'position': {'x': 0, 'y': 0, 'z': 0}, 'side': side}

    def generate_bumper_front(self):
        """前保险杠"""
        t = self.nurbs_templates['bumper_front']
        width = self._p('整车尺寸', 'overall_width')
        nu, nv = t['num_u'], t['num_v']
        length, height = 200, 250
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = u * length  # 从车头向内延伸
                y = height * (1 - np.cos(u * np.pi)) * 0.5 + self.GC * 0.4
                z = (v - 0.5) * width * (0.85 + u * 0.15)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '前保险杠', 'type': 'bumper', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#808080', 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_bumper_rear(self):
        """后保险杠"""
        t = self.nurbs_templates['bumper_rear']
        width = self._p('整车尺寸', 'overall_width')
        nu, nv = t['num_u'], t['num_v']
        length, height = 200, 250
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = self.L - length + u * length  # 车尾向内延伸
                y = height * (1 - np.cos(u * np.pi)) * 0.5 + self.GC * 0.4
                z = (v - 0.5) * width * (0.85 + (1 - u) * 0.15)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '后保险杠', 'type': 'bumper', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#808080', 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_headlight(self, side='left'):
        """前大灯"""
        height = self._p('车身部件', 'headlight_height')
        depth = 80
        pts = []
        for i in range(5):
            row = []
            for j in range(4):
                row.append([i * (depth / 4), height * (1 - j / 3), 0])
            pts.append(row)
        z_offset = 400 if side == 'left' else -400
        return {'name': f'{side}前大灯', 'type': 'headlight', 'points': pts, 'color': '#ffffff',
                'emissive': '#00ffff', 'position': {'x': 300, 'y': 400, 'z': z_offset}}

    def generate_taillight(self, side='left'):
        """后尾灯"""
        height = self._p('车身部件', 'taillight_height')
        depth = 60
        pts = []
        for i in range(4):
            row = []
            for j in range(5):
                row.append([i * (depth / 3), height * (1 - j / 4), 0])
            pts.append(row)
        z_offset = 400 if side == 'left' else -400
        return {'name': f'{side}后尾灯', 'type': 'taillight', 'points': pts, 'color': '#ff0000',
                'emissive': '#ff4400', 'position': {'x': self.L - 150, 'y': 400, 'z': z_offset}}

    def generate_grille(self):
        """进气格栅"""
        height = self._p('车身部件', 'grille_height')
        depth = 50
        pts = []
        for i in range(3):
            row = []
            for j in range(8):
                row.append([i * (depth / 2), height * (1 - j / 7), 0])
            pts.append(row)
        return {'name': '进气格栅', 'type': 'grille', 'points': pts, 'color': '#1a1a1a',
                'position': {'x': 100, 'y': 300, 'z': 0}}

    def generate_wheel(self, position='front', side='left'):
        """车轮"""
        diameter = self._p('车身部件', 'wheel_diameter')
        width = self._p('车身部件', 'wheel_width')
        x_pos = self.fwx if position == 'front' else self.rwx
        z_pos = self.fwz if side == 'left' else -self.fwz
        return {'name': f'{side}{position}轮', 'type': 'wheel', 'radius': diameter / 2, 'width': width,
                'color': '#222222', 'rim_color': '#666666',
                'position': {'x': x_pos, 'y': self.GC + diameter / 2, 'z': z_pos}}

    def generate_mirror(self, side='left'):
        """后视镜"""
        width = self._p('车身部件', 'mirror_width')
        height = self._p('车身部件', 'mirror_height')
        depth = self._p('车身部件', 'mirror_depth')
        z_offset = 470 if side == 'left' else -470
        return {'name': f'{side}后视镜', 'type': 'mirror', 'width': width, 'height': height, 'depth': depth,
                'color': '#c0c0c0', 'glass_color': '#87CEEB',
                'position': {'x': 2600, 'y': 850, 'z': z_offset}}

    def generate_fender(self, position='front', side='left'):
        """翼子板"""
        t = self.nurbs_templates['fender_front']
        radius = self._p('车身部件', 'wheel_arch_radius')
        nu, nv = t['num_u'], t['num_v']
        x_center = self.fwx if position == 'front' else self.rwx
        # author 坐标：y 为高度（GC 以上），z 为车宽（半宽 80%~100% 区间）
        z_center = self.half_w * 0.90 if side == 'left' else -self.half_w * 0.90
        y_base = self.GC * 0.8  # 保证最低点在地面以上
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                theta, phi = u * np.pi, v * np.pi
                x = x_center + radius * np.cos(theta) * 0.6
                y = y_base + radius * (0.5 + 0.5 * np.sin(theta)) * (0.7 + 0.3 * np.cos(phi))
                z = z_center + radius * np.sin(theta) * np.sin(phi) * 0.3
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': f'{side}{position}翼子板', 'type': 'fender', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0', 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_pillar(self, pillar_type='A', side='left'):
        """立柱"""
        heights = {'A': 1000, 'B': 900, 'C': 800}
        x_positions = {'A': 1700, 'B': 3000, 'C': 4000}
        height = heights[pillar_type]
        width = 60
        pts = []
        for i in range(3):
            row = []
            for j in range(10):
                row.append([i * (width / 2), height * (1 - j / 9), 0])
            pts.append(row)
        z_offset = 430 if side == 'left' else -430
        return {'name': f'{side}{pillar_type}柱', 'type': 'pillar', 'points': pts, 'color': '#1a1a1a',
                'position': {'x': x_positions[pillar_type], 'y': 200, 'z': z_offset}}

    def generate_door_seam(self):
        """车门分缝"""
        seam_width = self._p('车身部件', 'door_seam_width')
        return {'name': '车门分缝', 'type': 'seam', 'width': seam_width, 'color': '#111111',
                'segments': [{'start': {'x': 3200, 'y': 250, 'z': 0}, 'end': {'x': 3200, 'y': 1000, 'z': 0}}]}

    def generate_complete_car(self, params_override=None):
        """生成完整车身模型

        Args:
            params_override: 可选的参数覆盖，支持两种格式：
                - 扁平 {参数名: 值}，如 {"overall_length": 5500}
                - 分组 {分组: {参数名: 值}}
            传入时会**临时应用**并重建坐标，生成完毕后恢复原参数，
            因此同一实例可反复以不同参数生成。
        """
        if params_override:
            return self._generate_with_override(params_override)
        return self._generate_current()

    def _generate_with_override(self, params_override):
        """临时应用参数覆盖后生成，并恢复原状态"""
        import copy as _copy
        backup = _copy.deepcopy(self.params)
        try:
            flat = NURBSCarBodyGenerator.resolve_overrides(params_override)
            # 若已是分组格式（resolve 无命中），退回原样处理
            applied = flat or params_override
            for group, items in applied.items():
                if group in self.params and isinstance(items, dict):
                    for key, val in items.items():
                        if isinstance(val, dict):
                            val = val.get('value')
                        if key in self.params[group] and val is not None:
                            self.params[group][key]['value'] = val
            self._init_coords()
            return self._generate_current()
        finally:
            self.params = backup
            self._init_coords()

    def _generate_current(self):
        """按当前参数生成完整车身（实际生成逻辑）"""
        components = [
            self.generate_bumper_front(), self.generate_grille(),
            self.generate_headlight('left'), self.generate_headlight('right'),
            self.generate_hood(), self.generate_windshield(), self.generate_roof(),
            self.generate_rear_window(), self.generate_trunk(), self.generate_bumper_rear(),
            self.generate_taillight('left'), self.generate_taillight('right'),
            self.generate_door_front('left'), self.generate_door_front('right'),
            self.generate_door_rear('left'), self.generate_door_rear('right'),
            self.generate_mirror('left'), self.generate_mirror('right'),
            self.generate_pillar('A', 'left'), self.generate_pillar('A', 'right'),
            self.generate_pillar('B', 'left'), self.generate_pillar('B', 'right'),
            self.generate_pillar('C', 'left'), self.generate_pillar('C', 'right'),
            self.generate_fender('front', 'left'), self.generate_fender('front', 'right'),
            self.generate_fender('rear', 'left'), self.generate_fender('rear', 'right'),
            self.generate_wheel('front', 'left'), self.generate_wheel('front', 'right'),
            self.generate_wheel('rear', 'left'), self.generate_wheel('rear', 'right'),
            self.generate_door_seam()
        ]
        nurbs_count = sum(1 for c in components if 'surface' in c)
        cp_total = sum(sum(len(r) for r in c['surface']['control_points'])
                       for c in components if 'surface' in c and 'control_points' in c['surface'])
        return {
            'name': '完整车身',
            'components': components,
            'parameters': self.params,
            'total_surfaces': len(components),
            'nurbs_quality': self._measure_nurbs_quality(components, nurbs_count,
                                                         cp_total),
        }

    def _measure_nurbs_quality(self, components, nurbs_count, cp_total,
                               n_samples=3):
        """**实测**各曲面的曲率质量，取代此前的硬编码 `g2_continuous: True`

        此前该字段是常量 True，未做任何几何计算——属于"声称而非测量"。
        本方法用真实曲率管线（形状算子解主曲率）逐曲面测量，并据实汇报：

          - `g2_continuous`：**仅当所有曲面均为可计算的非退化非平面曲面时**才为
            True；存在平面（曲率恒为 0，无法与相邻曲面满足曲率比 1±0.2）或
            无法测量时，如实置为 False。
          - `curvature`：逐曲面的中位曲率与代表半径，供人工复核。

        测量失败不会影响生成（由 try 兜底），失败原因会记录在 `measure_error`。
        """
        info = {
            'g2_continuous': False,
            'surface_count': nurbs_count,
            'control_points_total': cp_total,
            'measured': True,
            'n_flat_surfaces': 0,
            'n_unmeasurable': 0,
            'curvature': {},
        }
        try:
            from .iges_nurbs import NurbsSurface
            from .nurbs_curvature import analyze_iges_surface
        except Exception as exc:                       # 依赖不可用则如实说明
            info['measured'] = False
            info['measure_error'] = f"曲率管线不可用: {type(exc).__name__}: {exc}"
            return info

        n_ok = 0
        for comp in components:
            s = comp.get('surface')
            if not s or 'control_points' not in s:
                continue
            name = comp.get('name') or comp.get('type') or '?'
            try:
                cps = np.array([[[p['x'], p['y'], p['z']] for p in row]
                                for row in s['control_points']], dtype=float)
                wts = np.array([[p.get('weight', 1.0) for p in row]
                                for row in s['control_points']], dtype=float)
                ns = NurbsSurface(
                    surface_id=0, k1=cps.shape[0] - 1, k2=cps.shape[1] - 1,
                    m1=int(s['degree_u']), m2=int(s['degree_v']),
                    knots_u=np.asarray(s['knot_vector_u'], dtype=float),
                    knots_v=np.asarray(s['knot_vector_v'], dtype=float),
                    weights=wts.reshape(-1), control_points=cps,
                    u_range=None, v_range=None,
                    pd_line_start=0, pd_line_end=0, n_params=0)
                r = analyze_iges_surface(ns, n_samples=n_samples,
                                         do_corner_check=False)
                if not r.get('ok'):
                    info['n_unmeasurable'] += 1
                    continue
                k = r.get('k_abs_median') or 0.0
                if k <= 1e-9:
                    info['n_flat_surfaces'] += 1
                info['curvature'][name] = {
                    'k_abs_median': k,
                    'r_median_mm': r.get('r_median_mm'),
                    'is_singly_curved': r.get('is_singly_curved'),
                }
                n_ok += 1
            except Exception as exc:
                info['n_unmeasurable'] += 1
                info.setdefault('measure_warnings', []).append(
                    f"{name}: {type(exc).__name__}: {exc}")

        info['n_measured'] = n_ok
        # 据实判定：有平面或测不出 → 不能声称 G2
        info['g2_continuous'] = bool(
            n_ok > 0 and info['n_flat_surfaces'] == 0
            and info['n_unmeasurable'] == 0)
        info['note'] = (
            'G2 声明依据：所有曲面均非平面且可测；'
            '平面曲率恒为 0，无法与相邻曲面满足曲率比 1±0.2（SOP-A SURF-001 §5.2）'
        )
        return info

    def export_car_data(self, output_path=None):
        """导出汽车数据到JSON文件"""
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'car_body_data.json')
        car = self.generate_complete_car()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(car, f, ensure_ascii=False, indent=2)
        return car

    # ============ 网格导出 ============

    def _build_trimesh_scene(self):
        """用trimesh从NURBS点云构建3D场景"""
        import trimesh
        car = self.generate_complete_car()
        scene = trimesh.Scene()
        for comp in car['components']:
            if 'points' in comp and comp['points']:
                pts = np.array(comp['points'], dtype=np.float64)
                if pts.ndim == 3:
                    nu, nv, _ = pts.shape
                    vertices = pts.reshape(-1, 3)
                    faces = []
                    for i in range(nu - 1):
                        for j in range(nv - 1):
                            v0, v1 = i * nv + j, i * nv + (j + 1)
                            v2, v3 = (i + 1) * nv + j, (i + 1) * nv + (j + 1)
                            faces.append([v0, v1, v2]); faces.append([v1, v3, v2])
                    if faces:
                        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                        pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                        mesh.apply_translation([pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)])
                        self._apply_color(mesh, comp.get('color', '#c0c0c0'))
                        scene.add_geometry(mesh, node_name=comp.get('name', 'part'))
            elif comp.get('type') == 'wheel' and 'radius' in comp:
                wheel = trimesh.creation.cylinder(radius=comp['radius'], height=comp.get('width', 200))
                pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                wheel.apply_translation([pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)])
                self._apply_color(wheel, comp.get('rim_color', '#666666'))
                scene.add_geometry(wheel, node_name=comp.get('name', 'wheel'))
        return scene

    @staticmethod
    def _apply_color(mesh, color_hex):
        try:
            h = color_hex.lstrip('#')
            mesh.visual.face_colors = [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [255]
        except Exception:
            pass

    def export_glb(self, output_path: str) -> str:
        data = self._build_trimesh_scene().export(file_type='glb')
        Path(output_path).write_bytes(data)
        return output_path

    def export_stl(self, output_path: str) -> str:
        import trimesh
        scene = self._build_trimesh_scene()
        meshes = [g for g in scene.geometry.values() if hasattr(g, 'faces')]
        if meshes:
            data = trimesh.util.concatenate(meshes).export(file_type='stl')
        else:
            data = b'solid empty\nendsolid empty\n'
        Path(output_path).write_bytes(data if isinstance(data, bytes) else data.encode())
        return output_path

    def export_obj(self, output_path: str) -> str:
        data = self._build_trimesh_scene().export(file_type='obj')
        Path(output_path).write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
        return output_path

    def export_step(self, output_path: str) -> str:
        """导出STEP格式（基于NURBS数据生成AP214）"""
        car = self.generate_complete_car()
        lines = [
            "ISO-10303-21;", "HEADER;",
            "FILE_DESCRIPTION(('EVOLUTION AI NURBS Car Body Model'),'2;1');",
            "FILE_NAME('car_model.step','2026-07-01T00:00:00',('EVOLUTION AI'),('EVOLUTION AI'),'',' ','');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
            "ENDSEC;", "DATA;",
            "#1=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));",
            "#2=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));",
            "#3=(NAMED_UNIT(*)SOLID_ANGLE_UNIT()SI_UNIT($,.STERADIAN.));",
            "#4=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.01),#1,'distance_accuracy_value','confusion accuracy');",
        ]
        eid = 5
        for comp in car['components']:
            name = comp.get('name', 'unknown')
            if 'surface' in comp:
                surf = comp['surface']
                cps = surf.get('control_points', [])
                if cps:
                    cp_ids = []
                    for row in cps[:4]:
                        for cp in row[:4]:
                            lines.append(f"#{eid}=CARTESIAN_POINT('',({cp['x']:.4f},{cp['y']:.4f},{cp['z']:.4f}));")
                            cp_ids.append(eid); eid += 1
                    if cp_ids:
                        refs = ','.join(f'#{p}' for p in cp_ids)
                        nu = min(len(cps), 4); nv = min(len(cps[0]) if cps else 4, 4)
                        lines.append(f"#{eid}=B_SPLINE_SURFACE_WITH_KNOTS('',{surf.get('degree_u',3)},{surf.get('degree_v',3)},({nu},{nv}),({refs}),.UNSPECIFIED.,.F.,.F.,.F.,(4,4),(4,4),.UNSPECIFIED.);")
                        eid += 1
                        lines.append(f"#{eid}=ADVANCED_FACE('{name}',(#{eid-1}),.F.);"); eid += 1
            elif comp.get('type') == 'wheel':
                pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                lines.append(f"#{eid}=CARTESIAN_POINT('',({pos.get('x',0):.4f},{pos.get('y',0):.4f},{pos.get('z',0):.4f}));"); eid += 1
                lines.append(f"#{eid}=AXIS2_PLACEMENT_3D('',#{eid-1},$,$);"); eid += 1
                lines.append(f"#{eid}=CYLINDRICAL_SURFACE('',#{eid-1},{comp.get('radius',300):.4f});"); eid += 1
                lines.append(f"#{eid}=ADVANCED_FACE('{name}',(#{eid-1}),.T.);"); eid += 1
        lines += ["ENDSEC;", "END-ISO-10303-21;"]
        Path(output_path).write_text('\n'.join(lines), encoding='utf-8')
        return output_path
