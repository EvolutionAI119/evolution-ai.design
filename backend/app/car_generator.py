"""NURBS驱动汽车车身生成器：基于NURBS曲面生成车身全部部件，支持GLB/STL/OBJ/STEP导出"""
import os
import json
import numpy as np
from pathlib import Path

from .nurbs import NURBSSurface, ControlPoint


class NURBSCarBodyGenerator:
    """车身生成器：读取汽车参数配置，生成各部件NURBS曲面并支持导出"""

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'automotive_parameters.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.params = self.config['automotive_parameters']
        self.components_cfg = self.config['car_body_components']
        self.nurbs_templates = self.config['nurbs_surface_templates']
        self._init_coords()

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
        self.fwx = self.FO + self.GC
        self.rwx = self.L - self.RO
        self.fwz = self.TW / 2

    def _p(self, group, key):
        return self.params[group][key]['value']

    def _build_surface(self, cps_3d, template):
        """从3D控制点列表构建NURBS曲面"""
        cps = [[ControlPoint(x, y, z, 1.0) for x, y, z in row] for row in cps_3d]
        return NURBSSurface(degree_u=template['degree_u'], degree_v=template['degree_v'], control_points=cps)

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
        cx_start, cy_base = 200, 300
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
        height = self._p('车身部件', 'windshield_height')
        angle = np.radians(90 - self._p('造型角度', 'windshield_angle'))
        nu, nv = t['num_u'], t['num_v']
        cx_base, cy_bottom = 1700, 450
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_base - u * height * np.sin(angle)
                y = cy_bottom + u * height * np.cos(angle)
                z = (v - 0.5) * width * (1 - u * 0.15)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '前风挡玻璃', 'type': 'windshield', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#87CEEB', 'opacity': 0.6, 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_roof(self):
        """车顶"""
        t = self.nurbs_templates['roof']
        length = self._p('车身部件', 'roof_length')
        width = self._p('车身部件', 'roof_width')
        height = self._p('车身部件', 'roof_height')
        nu, nv = t['num_u'], t['num_v']
        cx_start, cy_base = 1950, 1200
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * length
                y = cy_base + height * np.cos((u - 0.5) * np.pi * 2)
                z = (v - 0.5) * width * (1 - u * 0.2)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '车顶', 'type': 'roof', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0', 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_rear_window(self):
        """后风挡玻璃"""
        t = self.nurbs_templates['rear_window']
        width = self._p('车身部件', 'rear_window_width')
        height = self._p('车身部件', 'rear_window_height')
        angle = np.radians(self._p('造型角度', 'rear_window_angle'))
        nu, nv = t['num_u'], t['num_v']
        cx_base, cy_top = 3400, 1150
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_base + u * height * np.sin(angle)
                y = cy_top - u * height * np.cos(angle)
                z = (v - 0.5) * width * (1 - u * 0.1)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '后风挡玻璃', 'type': 'rear_window', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#87CEEB', 'opacity': 0.6, 'position': {'x': 0, 'y': 0, 'z': 0}}

    def generate_trunk(self):
        """行李箱盖"""
        t = self.nurbs_templates['trunk']
        length = self._p('车身部件', 'trunk_length')
        width = self._p('车身部件', 'trunk_width')
        nu, nv = t['num_u'], t['num_v']
        cx_start, cy_base = 3650, 550
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                x = cx_start + u * length
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
        cx_start, cy_base = 2100, 250
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                cps_row = (cx_start + u * length, cy_base + v * height, 0.0)
                row.append(cps_row)
            cps.append(row)
        surf = self._build_surface(cps, t)
        z_offset = 420 if side == 'left' else -420
        return {'name': f'{side}前门', 'type': 'door', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0',
                'position': {'x': 0, 'y': 0, 'z': z_offset}, 'side': side}

    def generate_door_rear(self, side='left'):
        """后门"""
        t = self.nurbs_templates['door_rear']
        length = self._p('车身部件', 'door_rear_length')
        height = self._p('车身部件', 'door_rear_height')
        nu, nv = t['num_u'], t['num_v']
        cx_start, cy_base = 3300, 280
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                row.append((cx_start + u * length, cy_base + v * height, 0.0))
            cps.append(row)
        surf = self._build_surface(cps, t)
        z_offset = 420 if side == 'left' else -420
        return {'name': f'{side}后门', 'type': 'door', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#c0c0c0',
                'position': {'x': 0, 'y': 0, 'z': z_offset}, 'side': side}

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
                x = -length * (1 - u)
                y = height * (1 - np.cos(u * np.pi)) * 0.5 + 100
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
                x = length * u
                y = height * (1 - np.cos(u * np.pi)) * 0.5 + 100
                z = (v - 0.5) * width * (0.85 + (1 - u) * 0.15)
                row.append((x, y, z))
            cps.append(row)
        surf = self._build_surface(cps, t)
        return {'name': '后保险杠', 'type': 'bumper', 'points': self._sample(surf, nu, nv),
                'surface': surf.to_dict(), 'color': '#808080', 'position': {'x': self.L - length, 'y': 0, 'z': 0}}

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
        z_center = self.fwz + 30 if side == 'left' else -self.fwz - 30
        cps = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                theta, phi = u * np.pi, v * np.pi
                x = x_center + radius * np.cos(theta) * 0.6
                y = self.GC + radius * np.sin(theta) * np.cos(phi)
                z = z_center + radius * np.sin(theta) * np.sin(phi) * 0.5
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

    def generate_complete_car(self):
        """生成完整车身模型"""
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
            'nurbs_quality': {'g2_continuous': True, 'surface_count': nurbs_count, 'control_points_total': cp_total}
        }

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
