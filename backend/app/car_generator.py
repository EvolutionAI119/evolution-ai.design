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
        """初始化车身坐标系关键尺寸与**统一硬点链**

        所有钣件共享同一组硬点（单一事实来源）：
        相邻钣件的边缘取自同一个锚点，从几何上消除缝隙。
        硬点采用 author 约定（x∈[0,L] 从前到后，y=高度，z=车宽），
        经 :meth:`_to_canonical` 统一变换到规范坐标系。
        """
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
        self._build_hardpoints()

    def _build_hardpoints(self):
        """计算全车硬点链（author 约定，mm）

        侧视轮廓链（x=纵向, y=高度），顺序自车头向车尾：
          A 鼻尖      B 引擎盖前缘   C 引擎盖后缘/风挡底(COWL)
          D 风挡顶     E 车顶后缘/后窗顶  F 后窗底/行李箱前缘  G 行李箱后缘
        各钣件的对应边必须严格落在这些锚点上。
        """
        L, W, H, GC = self.L, self.W, self.H, self.GC
        waist = self.waist
        hood_len = self._p('车身部件', 'hood_length')
        hood_ang = np.radians(self._p('造型角度', 'hood_angle'))
        # ---- 纵向 X 锚点 ----
        x_hood_f = 190                      # 固定锚点：机盖形状只由 hood_length 决定
        x_cowl = hood_len
        x_wstop = hood_len + 0.25 * (L * 0.82 - hood_len)
        x_cab_end = L * 0.82
        x_rwbot = L * 0.82 + 0.25 * (L - L * 0.82)
        # ---- 高度 Z 锚点（author y） ----
        z_skirt = GC * 0.8
        z_nose_top = GC + H * 0.12
        # 引擎盖前缘：由 hood_angle 从 COWL 反推（角度参数真正作用于几何）
        z_hood_f = waist - float(np.tan(hood_ang)) * (x_cowl - x_hood_f)
        z_hood_f = max(z_hood_f, waist * 0.4)
        z_wstop = H * 0.95
        z_roof_r = H * 0.94
        z_trunk_r = GC + (H - GC) * 0.52
        # ---- 侧视轮廓链（车身上边缘） ----
        self.hp = {
            'x_nose': 0.0, 'x_hood_f': x_hood_f, 'x_cowl': x_cowl,
            'x_wstop': x_wstop, 'x_cab_end': x_cab_end,
            'x_rwbot': x_rwbot, 'x_tail': L,
            'z_skirt': z_skirt, 'z_nose_top': z_nose_top,
            'z_hood_f': z_hood_f, 'z_cowl': waist,
            'z_wstop': z_wstop, 'z_roof_r': z_roof_r,
            'z_rwbot': waist, 'z_trunk_r': z_trunk_r,
        }
        # 上轮廓折线（author x, y高度）；A 鼻尖 → G 行李箱后缘
        self._top_chain = np.array([
            (0.0, z_nose_top), (x_hood_f, z_hood_f),
            (x_cowl, waist), (x_wstop, z_wstop),
            (x_cab_end, z_roof_r), (x_rwbot, waist),
            (L, z_trunk_r)
        ])
        # 车轴 X（author）与轮拱参数
        self._ax_f = self.FO
        self._ax_r = L - self.RO
        self._arch_R = self._p('车身部件', 'wheel_arch_radius')
        # 轮拱开口抛物线峰高：拱心边缘 570 略低于轮顶 600，
        # 既露出胎冠又处处让开门外的轮胎圆周（余量经逐点核算）。
        wheel_r = self._p('车身部件', 'wheel_diameter') / 2.0
        self._arch_H = wheel_r * 2.0 - 30.0

    # ---- 共享剖面函数（shell / 车门 / 翼子板共用，保证贴合） ----
    @staticmethod
    def _chain_lookup(x, chain):
        """折线上按 x 线性插值（chain 已按 x 升序）"""
        xs = chain[:, 0]
        if x <= xs[0]:
            return float(chain[0, 1])
        if x >= xs[-1]:
            return float(chain[-1, 1])
        i = int(np.searchsorted(xs, x) - 1)
        x0, y0 = chain[i]
        x1, y1 = chain[i + 1]
        t = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
        return float(y0 + t * (y1 - y0))

    def _silhouette_top(self, x):
        """车身上边缘高度（不含风挡/车顶抬高段的侧围轮廓）。

        侧围外蒙皮在乘员舱段只到腰线；引擎盖/行李箱段随钣件高度。
        """
        hp = self.hp
        if x < hp['x_hood_f']:          # 鼻尖 → 引擎盖前缘
            return self._chain_lookup(x, self._top_chain[:2])
        if x < hp['x_cowl']:            # 引擎盖侧缘
            return self._chain_lookup(x, self._top_chain[1:3])
        if x <= hp['x_rwbot']:          # 乘员舱：腰线
            return hp['z_cowl']
        return self._chain_lookup(x, self._top_chain[5:])  # 行李箱侧缘

    def _arch_lift(self, x):
        """轮拱开口下缘相对 GC 的抬升量（抛物线，开口处连续归 0）。

        采用 H·(1-(dx/R)²) 而非圆：在 dx=R 处抬升恰为 0，与裙边平滑相接；
        峰高 _arch_H 经核算处处高于轮胎圆周（含余量），杜绝穿模。
        前后拱取较大者。
        """
        H, R = self._arch_H, self._arch_R
        lift = 0.0
        for ax in (self._ax_f, self._ax_r):
            dx = abs(x - ax)
            if dx < R:
                lift = max(lift, H * (1.0 - (dx / R) ** 2))
        return float(lift)

    def _outer_half_width(self, x, z):
        """外蒙皮在(x,z)处的半宽（author z_lat）：含溜肩(tumblehome)与拱鼓"""
        gc, h, hw = self.GC, self.H, self.half_w
        ratio = min(max((z - gc) / (h - gc), 0.0), 1.0)
        base = hw * (0.985 - 0.05 * ratio)          # 上沿内收
        bulge = 16.0 * (self._arch_lift(x) / max(self._arch_H, 1.0))
        return base + bulge


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

    # 渲染采样密度（与控制点数量解耦）：按部件物理尺寸 + 目标边长自适应
    RENDER_TARGET_MM = 40.0   # 渲染网格目标边长（mm）
    RENDER_MIN_N = 12         # 每方向最少采样数
    RENDER_MAX_N = 64         # 每方向最多采样数

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

    def _render_count(self, size_mm):
        """按目标边长把部件物理尺寸换算为采样数（与控制点数量解耦）"""
        n = int(round(float(size_mm) / self.RENDER_TARGET_MM))
        return max(self.RENDER_MIN_N, min(self.RENDER_MAX_N, n))

    def _sample_grid(self, surface, size_u_mm, size_v_mm):
        """按物理尺寸自适应密度采样曲面（向量化批量求值）

        输出与 :meth:`_sample` 相同的 ``[[[x,y,z]]]`` 数值嵌套结构，
        下游 JSON 序列化与 GLB 网格构造无需改动。
        """
        nu = self._render_count(size_u_mm)
        nv = self._render_count(size_v_mm)
        grid = surface.evaluate_grid(np.linspace(0.0, 1.0, nu),
                                     np.linspace(0.0, 1.0, nv))
        # 与旧 _sample 相同的 [[[x,y,z]]] 数值嵌套结构（非 dict），
        # 保证 GLB np.array 构造与 JSON schema 不变
        return [[[float(p[0]), float(p[1]), float(p[2])] for p in row]
                for row in grid]

    def _make_surface(self, cp_grid, template_name, axes='author'):
        """从 CP 网格 + 模板名构建 NURBS 曲面（阶数取模板，节点按 CP 数生成）"""
        return self._build_surface(cp_grid, self.nurbs_templates[template_name],
                                   axes=axes)

    def _grid_component(self, name, ctype, cp_grid, template_name,
                        size_u, size_v, color, axes='author', **extra):
        """通用：CP 网格 → NURBS 曲面 → 自适应采样点 → 组件字典"""
        surf = self._make_surface(cp_grid, template_name, axes=axes)
        comp = {'name': name, 'type': ctype,
                'points': self._sample_grid(surf, size_u, size_v),
                'surface': surf.to_dict(), 'color': color,
                'position': {'x': 0, 'y': 0, 'z': 0}}
        comp.update(extra)
        return comp

    # ============ 部件生成 ============

    def generate_hood(self):
        """发动机盖"""
        hp = self.hp
        x0, x1 = hp['x_hood_f'], hp['x_cowl']
        z0, z1 = hp['z_hood_f'], hp['z_cowl']
        w0 = self.W * 0.82                    # 前缘窄
        w1 = self.W * 0.95                    # 后缘宽（与风挡底同宽）
        crown = self._p('车身部件', 'hood_height')
        nu, nv = 7, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                # 边缘严格落在轮廓线上（crown 只在横向中部隆起）
                z = z0 + u * (z1 - z0) + crown * np.sin(u * np.pi) * (1 - (2 * v - 1) ** 2)
                z_lat = (v - 0.5) * (w0 + u * (w1 - w0))
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component('发动机盖', 'hood', cps, 'hood',
                                    x1 - x0, w1, '#c0c0c0')

    def generate_windshield(self):
        """前风挡玻璃：底边=COWL（与引擎盖后缘共享），顶边=车顶板前缘"""
        hp = self.hp
        x0, x1 = hp['x_cowl'], hp['x_wstop']
        z0, z1 = hp['z_cowl'], hp['z_wstop']
        w_bot = self.W * 0.95
        w_top = self.W * 0.81
        nu, nv = 6, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                z = z0 + u * (z1 - z0)
                # 玻璃横向微弧，边缘为直线（与邻件共享）
                z += 25 * np.sin(u * np.pi) * (1 - (2 * v - 1) ** 2)
                z_lat = (v - 0.5) * (w_bot + u * (w_top - w_bot))
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component('前风挡玻璃', 'windshield', cps, 'windshield',
                                    np.hypot(x1 - x0, z1 - z0), w_bot,
                                    '#87CEEB', opacity=0.55)

    def generate_roof(self):
        """车顶：前缘=风挡顶，后缘=后窗顶（共享硬点）"""
        hp = self.hp
        x0, x1 = hp['x_wstop'], hp['x_cab_end']
        z0, z1 = hp['z_wstop'], hp['z_roof_r']
        w_front = self.W * 0.81
        w_rear = self.W * 0.76
        crown = max(self._p('车身部件', 'roof_height'), 30)
        nu, nv = 9, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                z = z0 + u * (z1 - z0) + crown * np.sin(u * np.pi) * (1 - (2 * v - 1) ** 2)
                z_lat = (v - 0.5) * (w_front + u * (w_rear - w_front))
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component('车顶', 'roof', cps, 'roof',
                                    x1 - x0, w_front, '#c0c0c0',
                                    roof_end_x=x1, roof_top_y=z0)

    def generate_rear_window(self):
        """后风挡玻璃：顶边=车顶后缘，底边=行李箱前缘（共享硬点）"""
        hp = self.hp
        x0, x1 = hp['x_cab_end'], hp['x_rwbot']
        z0, z1 = hp['z_roof_r'], hp['z_rwbot']
        w_top = self.W * 0.76
        w_bot = self.W * 0.85
        nu, nv = 6, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                z = z0 + u * (z1 - z0)
                z += 22 * np.sin(u * np.pi) * (1 - (2 * v - 1) ** 2)
                z_lat = (v - 0.5) * (w_top + u * (w_bot - w_top))
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component('后风挡玻璃', 'rear_window', cps, 'rear_window',
                                    np.hypot(x1 - x0, z1 - z0), w_bot,
                                    '#87CEEB', opacity=0.55,
                                    rear_window_bottom_x=x1,
                                    rear_window_bottom_y=z1)

    def generate_trunk(self):
        """行李箱盖：前缘=后窗底，后缘=车尾，与侧围上缘贴合"""
        hp = self.hp
        x0, x1 = hp['x_rwbot'], hp['x_tail']
        z0, z1 = hp['z_rwbot'], hp['z_trunk_r']
        w_front = self.W * 0.85
        w_rear = self.W * 0.86
        nu, nv = 7, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                z = z0 + u * (z1 - z0) + 55 * np.sin(u * np.pi) * (1 - (2 * v - 1) ** 2)
                z_lat = (v - 0.5) * (w_front + u * (w_rear - w_front))
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component('行李箱盖', 'trunk', cps, 'trunk',
                                    x1 - x0, w_rear, '#c0c0c0')

    def _door_mid_author(self):
        """B 柱/前后门分界 X（author）：前后轴中点"""
        return (self.FO + (self.L - self.RO)) / 2.0

    def generate_door_front(self, side='left'):
        """前门：前轴后 40mm → B 柱区前 30mm；下缘在轮拱区随拱抛物线开口"""
        sgn = 1.0 if side == 'left' else -1.0
        x0 = self.FO + 40
        x1 = self._door_mid_author() - 30
        z_top = self.waist * 0.97
        nu, nv = 8, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                # 拱区下缘抬起形成轮拱开口，其余处正常裙边（GC+100）
                z_bot = max(self.GC + 100, self.GC + self._arch_lift(x))
                z = z_bot + v * (z_top - z_bot)
                # 比外蒙皮外凸 4mm（装配间隙），曲面随 _outer_half_width 起伏
                z_lat = sgn * (self._outer_half_width(x, z) + 4)
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component(f'{side}前门', 'door', cps, 'door_front',
                                    x1 - x0, z_top - self.GC, '#c0c0c0',
                                    side=side)

    def generate_door_rear(self, side='left'):
        """后门：B 柱区后 30mm → 座舱终点后 5%L；下缘随后轮拱抛物线开口"""
        sgn = 1.0 if side == 'left' else -1.0
        x0 = self._door_mid_author() + 30
        x1 = self.L * 0.87
        z_top = self.waist * 0.97
        nu, nv = 8, 7
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = x0 + u * (x1 - x0)
                z_bot = max(self.GC + 100, self.GC + self._arch_lift(x))
                z = z_bot + v * (z_top - z_bot)
                z_lat = sgn * (self._outer_half_width(x, z) + 4)
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component(f'{side}后门', 'door', cps, 'door_rear',
                                    x1 - x0, z_top - self.GC, '#c0c0c0',
                                    side=side)

    # ------------------------------------------------------------------
    # 车身连续外蒙皮（最关键部件）：侧围整体 + 轮拱 + 鼻/尾卷包
    # ------------------------------------------------------------------
    def generate_body_shell(self, side='left'):
        """连续侧围外蒙皮：鼻尖 → 车尾；下缘随轮拱，鼻尾卷包封闭端面"""
        sgn = 1.0 if side == 'left' else -1.0
        hp = self.hp
        L, GC = self.L, self.GC

        def v_rows(low, up):
            row = []
            for j in range(7):
                v = j / 6.0
                x = low[0] + v * (up[0] - low[0])
                z = low[1] + v * (up[1] - low[1])
                row.append((x, z, sgn * self._outer_half_width(x, z)))
            return row

        grid = []
        # 鼻卷包（s=0 上下缘重合于鼻尖）
        for s in (0.0, 0.5, 1.0):
            low = (40 * s, hp['z_skirt'])
            up = (200 * s, hp['z_skirt'] + (hp['z_hood_f'] - hp['z_skirt']) * s * s)
            grid.append(v_rows(low, up))
        # 中段（去掉与卷包重合的两端）
        for x in np.linspace(200.0, L - 200.0, 20)[1:-1]:
            x = float(x)
            grid.append(v_rows((x, GC + self._arch_lift(x)),
                               (x, self._silhouette_top(x))))
        # 尾卷包
        for s in (1.0, 0.5, 0.0):
            low = (L - 40 * s, hp['z_skirt'])
            up = (L - 200 * s, hp['z_skirt'] + (hp['z_trunk_r'] - hp['z_skirt']) * s * s)
            grid.append(v_rows(low, up))

        return self._grid_component(f'{side}车身外蒙皮', 'body_shell', grid,
                                    'roof', L, self.H, '#c0c0c0')

    # ------------------------------------------------------------------
    # 侧窗玻璃（前/后）与 B 柱：填补腰线 → 车顶边的乘员舱侧面
    # ------------------------------------------------------------------
    def _greenhouse_grid(self, x0, x1, top_pts, sgn, nu=8, nv=5):
        """腰线→车顶侧 CP 网格。top_pts: 上沿折线 (x, 高度, 半宽)

        CP 站必须落在折线锚点上（斜率突变处有 CP 压制）：
        若只用均匀站，NURBS 会在锚点间过冲，侧窗上沿冒出车顶线呈锯齿。
        """
        z_low = self.waist * 0.98
        lat_low = self.half_w * 0.93
        top_z_chain, top_lat_chain = top_pts[:, [0, 1]], top_pts[:, [0, 2]]
        anchors = top_pts[:, 0]
        nu_per_seg = max(2, int(np.ceil(nu / max(len(anchors) - 1, 1))))
        xs = []
        for k in range(len(anchors) - 1):
            seg = np.linspace(anchors[k], anchors[k + 1], nu_per_seg)
            xs.extend(seg if k == 0 else seg[1:])
        grid = []
        for x in xs:
            x = float(x)
            z_top = self._chain_lookup(x, top_z_chain)
            lat_top = self._chain_lookup(x, top_lat_chain)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                z = z_low + v * (z_top - z_low)
                lat = lat_low + v * (lat_top - lat_low)
                row.append((x, z, sgn * lat))
            grid.append(row)
        return grid

    def generate_side_glass_front(self, side='left'):
        """前侧窗：COWL 后 40 → B 柱前 18；上沿跟风挡斜线后平接车顶"""
        hp = self.hp
        x0 = hp['x_cowl'] + 40
        x1 = self._door_mid_author() - 18
        top_pts = np.array([
            (x0, self._chain_lookup(x0, self._top_chain[2:4]), self.W * 0.95 * 0.5),
            (hp['x_wstop'], hp['z_wstop'], self.W * 0.81 * 0.5),
            (x1, hp['z_wstop'] - 2, self.W * 0.81 * 0.5)
        ])
        grid = self._greenhouse_grid(x0, x1, top_pts,
                                     1.0 if side == 'left' else -1.0)
        return self._grid_component(f'{side}前侧窗', 'side_glass', grid, 'roof',
                                    x1 - x0, hp['z_wstop'] - self.waist * 0.98,
                                    '#9fc5e8', opacity=0.5)

    def generate_side_glass_rear(self, side='left'):
        """后侧窗：B 柱后 18 → 后窗底前 40；上沿平接车顶后随 C 柱斜线"""
        hp = self.hp
        x0 = self._door_mid_author() + 18
        x1 = hp['x_rwbot'] - 40
        top_pts = np.array([
            (x0, hp['z_wstop'] - 3, self.W * 0.81 * 0.5),
            (hp['x_cab_end'], hp['z_roof_r'], self.W * 0.76 * 0.5),
            (x1, self._chain_lookup(x1, self._top_chain[4:6]), self.W * 0.85 * 0.5)
        ])
        grid = self._greenhouse_grid(x0, x1, top_pts,
                                     1.0 if side == 'left' else -1.0)
        return self._grid_component(f'{side}后侧窗', 'side_glass', grid, 'roof',
                                    x1 - x0, hp['z_roof_r'] - self.waist * 0.98,
                                    '#9fc5e8', opacity=0.5)

    def generate_b_pillar(self, side='left'):
        """B 柱：前后门/侧窗之间的窄竖条"""
        sgn = 1.0 if side == 'left' else -1.0
        mid = self._door_mid_author()
        x0, x1 = mid - 22, mid + 22
        z_bot, z_top = self.waist * 0.97, self.hp['z_wstop'] - 2
        lat_bot, lat_top = self.half_w * 0.93, self.W * 0.81 * 0.5
        cps = []
        for i in range(4):
            u = i / 3.0
            x = x0 + u * (x1 - x0)
            row = []
            for j in range(6):
                v = j / 5.0
                z = z_bot + v * (z_top - z_bot)
                lat = lat_bot + v * (lat_top - lat_bot)
                row.append((x, z, sgn * lat))
            cps.append(row)
        return self._grid_component(f'{side}B柱', 'b_pillar', cps, 'door_front',
                                    x1 - x0, z_top - z_bot, '#1a1a1a')

    def _bumper_grid(self, is_front):
        """垂直卷包保险杠 CP 网格：横向弧形 wrap，z 90→370"""
        nu, nv = 9, 6
        z0, z1 = 90, 370
        grid = []
        for i in range(nu):
            f = i / (nu - 1)
            lat = (f - 0.5) * 2 * self.half_w * 0.98
            wrap = (abs(lat) / self.half_w) ** 2 * 180
            x = 30 + wrap if is_front else self.L - 30 - wrap
            row = []
            for j in range(nv):
                g = j / (nv - 1)
                # 中部略高（微笑曲线）
                z = z0 + g * (z1 - z0) + 12 * (1 - (2 * f - 1) ** 2) * g
                row.append((x, z, lat))
            grid.append(row)
        return grid

    def generate_bumper_front(self):
        """前保险杠：鼻端垂直弧面"""
        grid = self._bumper_grid(True)
        return self._grid_component('前保险杠', 'bumper', grid, 'bumper_front',
                                    210, self.W, '#808080')

    def generate_bumper_rear(self):
        """后保险杠：尾端垂直弧面"""
        grid = self._bumper_grid(False)
        return self._grid_component('后保险杠', 'bumper', grid, 'bumper_rear',
                                    210, self.W, '#808080')

    def generate_headlight(self, side='left'):
        """前大灯：正面灯组 + 包角（夹格栅两侧，下缘坐保险杠顶）"""
        sgn = 1.0 if side == 'left' else -1.0
        cps = []
        for i in range(6):
            u = i / 5.0
            x = 40 + u * 150                    # 正面 → 包角向后扫
            lat = sgn * (280 + u * 360)         # 280 → 640
            row = []
            for j in range(4):
                v = j / 3.0
                z = 370 + v * 150
                row.append((x, z, lat))
            cps.append(row)
        return self._grid_component(f'{side}前大灯', 'headlight', cps,
                                    'bumper_front', 360, 150, '#ffffff',
                                    emissive='#cceeff')

    def generate_taillight(self, side='left'):
        """后尾灯：背面灯组 + 包角，下缘坐后保险杠顶"""
        sgn = 1.0 if side == 'left' else -1.0
        L = self.L
        cps = []
        for i in range(6):
            u = i / 5.0
            x = L - 40 - u * 150
            lat = sgn * (280 + u * 360)
            row = []
            for j in range(4):
                v = j / 3.0
                z = 370 + v * 170
                row.append((x, z, lat))
            cps.append(row)
        return self._grid_component(f'{side}后尾灯', 'taillight', cps,
                                    'bumper_rear', 360, 170, '#cc2200',
                                    emissive='#ff4400')

    def generate_grille(self):
        """进气格栅：正面横向板（lat ±300，z 130→340），中部前凸微弧"""
        cps = []
        for i in range(6):
            u = i / 5.0
            lat = (u - 0.5) * 600
            x = 12 + 26 * (lat / 300.0) ** 2    # 两侧随鼻弧向后收
            row = []
            for j in range(4):
                v = j / 3.0
                z = 130 + v * 210
                row.append((x, z, lat))
            cps.append(row)
        return self._grid_component('进气格栅', 'grille', cps, 'bumper_front',
                                    600, 210, '#1a1a1a')

    def generate_wheel(self, position='front', side='left'):
        """车轮（位置已归一到规范坐标系：X∈[-L/2,L/2]，Y=高度，Z=车宽）"""
        diameter = self._p('车身部件', 'wheel_diameter')
        width = self._p('车身部件', 'wheel_width')
        x_pos = self._ax_f if position == 'front' else self._ax_r
        z_pos = self.fwz if side == 'left' else -self.fwz
        return {'name': f'{side}{position}轮', 'type': 'wheel', 'radius': diameter / 2, 'width': width,
                'color': '#26262b', 'rim_color': '#9aa0a8',
                'position': {'x': x_pos - self.L / 2, 'y': self.GC + diameter / 2, 'z': z_pos}}

    def generate_mirror(self, side='left'):
        """后视镜（位置/尺寸元数据，不生成独立面片）"""
        return {'name': f'{side}后视镜', 'type': 'mirror',
                'width': self._p('车身部件', 'mirror_width'),
                'height': self._p('车身部件', 'mirror_height'),
                'depth': self._p('车身部件', 'mirror_depth'),
                'color': '#c0c0c0', 'glass_color': '#87CEEB',
                'position': {'x': self.hp['x_cowl'] - 80,
                             'y': self.waist + 60,
                             'z': (self.half_w + 30) * (1 if side == 'left' else -1)}}

    def generate_fender(self, position='front', side='left'):
        """翼子板：轮拱外覆圈，比外蒙皮外凸 15mm。

        内缘随拱抛物线但封顶 z=540（契约上限 556 内）；
        前翼子板后缘与前门切齐，避免与车门双板重叠。
        """
        ax = self._ax_f if position == 'front' else self._ax_r
        span_x = self.L * 0.09 - 8
        if position == 'front':
            x0, x1 = ax - span_x, self.FO + 40      # 后缘=前门起点
        else:
            x0, x1 = ax - span_x, ax + span_x
        z_top = 545
        cps = []
        for i in range(9):
            u = i / 8.0
            x = x0 + u * (x1 - x0)
            z_bot = self.GC * 0.6 + min(self._arch_lift(x), 450)
            sgn_lat = 1.0 if side == 'left' else -1.0
            row = []
            for j in range(6):
                v = j / 5.0
                z = z_bot + v * (z_top - z_bot)
                z_lat = sgn_lat * (self._outer_half_width(x, z) + 15)
                row.append((x, z, z_lat))
            cps.append(row)
        return self._grid_component(f'{side}{position}翼子板', 'fender', cps,
                                    'fender_front', x1 - x0, z_top - self.GC,
                                    '#c0c0c0')

    def generate_door_seam(self):
        """车门分缝（元数据）"""
        mid = self._door_mid_author()
        return {'name': '车门分缝', 'type': 'seam',
                'width': self._p('车身部件', 'door_seam_width'),
                'color': '#111111',
                'segments': [{'start': {'x': mid, 'y': 250, 'z': 0},
                              'end': {'x': mid, 'y': 1000, 'z': 0}}]}

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
        """按当前参数生成完整车身（实际生成逻辑）

        装配顺序（外到内/前到后）：连续外蒙皮 → 翼子板 → 保险杠 →
        灯具/格栅 → 上车身钣件链 → 车门 → 侧窗/B柱 → 车轮。
        """
        components = [
            # 连续车身外蒙皮（左右）
            self.generate_body_shell('left'), self.generate_body_shell('right'),
            # 翼子板（轮拱外覆）
            self.generate_fender('front', 'left'), self.generate_fender('front', 'right'),
            self.generate_fender('rear', 'left'), self.generate_fender('rear', 'right'),
            # 保险杠 / 格栅 / 灯具
            self.generate_bumper_front(), self.generate_bumper_rear(),
            self.generate_grille(),
            self.generate_headlight('left'), self.generate_headlight('right'),
            self.generate_taillight('left'), self.generate_taillight('right'),
            # 上车身钣件链（共享硬点边缘）
            self.generate_hood(), self.generate_windshield(), self.generate_roof(),
            self.generate_rear_window(), self.generate_trunk(),
            # 车门
            self.generate_door_front('left'), self.generate_door_front('right'),
            self.generate_door_rear('left'), self.generate_door_rear('right'),
            # 乘员舱侧窗 + B 柱
            self.generate_side_glass_front('left'), self.generate_side_glass_front('right'),
            self.generate_side_glass_rear('left'), self.generate_side_glass_rear('right'),
            self.generate_b_pillar('left'), self.generate_b_pillar('right'),
            # 后视镜（元数据）
            self.generate_mirror('left'), self.generate_mirror('right'),
            # 车轮
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

    #: GLB 导出 PBR 参数
    PBR_PAINT = {'metallicFactor': 0.9, 'roughnessFactor': 0.35}
    PBR_GLASS = {'metallicFactor': 0.0, 'roughnessFactor': 0.05}
    PBR_TIRE = {'metallicFactor': 0.1, 'roughnessFactor': 0.9}
    PBR_RIM = {'metallicFactor': 0.85, 'roughnessFactor': 0.3}

    def _build_trimesh_scene(self):
        """用trimesh从NURBS采样网格构建3D场景（平滑法线 + PBR材质）"""
        import trimesh
        from trimesh.visual.material import PBRMaterial
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
                        mesh.merge_vertices()
                        mesh.fix_normals()   # 平滑顶点法线（面片共享顶点）
                        pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                        mesh.apply_translation([pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)])
                        self._apply_pbr(mesh, comp, PBRMaterial)
                        scene.add_geometry(mesh, node_name=comp.get('name', 'part'))
            elif comp.get('type') == 'wheel' and 'radius' in comp:
                wheel = trimesh.creation.cylinder(
                    radius=comp['radius'], height=comp.get('width', 200),
                    sections=32)   # 轮胎细分提升
                # 圆柱默认轴朝 Z；车轮轴必须朝车宽 Y：绕 X 旋转 90°（Z→Y）
                wheel.apply_transform(np.array([
                    [1, 0, 0, 0], [0, 0, -1, 0],
                    [0, 1, 0, 0], [0, 0, 0, 1]]))
                pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                # 车轮位置已是规范坐标（generate_wheel 已减 L/2）；
                # author (x, y=高度, z=车宽) → canonical (X, Y=车宽, Z=高度)
                wheel.apply_translation([pos.get('x', 0),
                                         pos.get('z', 0), pos.get('y', 0)])
                wheel.fix_normals()
                rgb = self._hex_to_rgb(comp.get('rim_color', '#9aa0a8'))
                wheel.visual = trimesh.visual.TextureVisuals(
                    material=PBRMaterial(name='wheel',
                                         baseColorFactor=[*rgb, 1.0],
                                         doubleSided=True,
                                         **self.PBR_RIM))
                scene.add_geometry(wheel, node_name=comp.get('name', 'wheel'))
        return scene

    def _apply_pbr(self, mesh, comp, PBRMaterial):
        """为车身部件网格赋 PBR 材质（车漆或玻璃）"""
        import trimesh
        opacity = comp.get('opacity')
        is_glass = comp.get('type') in ('windshield', 'rear_window',
                                       'side_glass') or (
            opacity is not None and float(opacity) < 1.0)
        rgb = self._hex_to_rgb(comp.get('color', '#c0c0c0'))
        alpha = float(opacity) if is_glass and opacity is not None else 1.0
        params = self.PBR_GLASS if is_glass else self.PBR_PAINT
        mesh.visual = trimesh.visual.TextureVisuals(
            material=PBRMaterial(name=comp.get('name', 'part'),
                                 baseColorFactor=[*rgb, alpha],
                                 alphaMode='BLEND' if alpha < 1.0 else 'OPAQUE',
                                 doubleSided=True,
                                 **params))

    @staticmethod
    def _hex_to_rgb(color_hex):
        """'#rrggbb' → [r, g, b]，各通道 0~1；解析失败回退银灰"""
        try:
            h = str(color_hex).lstrip('#')
            return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        except Exception:
            return [0.75, 0.75, 0.75]

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
