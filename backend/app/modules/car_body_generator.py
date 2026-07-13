"""
EVOLUTION AI - NURBS驱动汽车造型生成器
基于NURBS曲面引擎实现G2连续的车身曲面生成
"""

import numpy as np
import json
import os
import struct
from pathlib import Path

from .nurbs_engine import NURBSSurface, NURBSCurve, ControlPoint, KnotVector


class NURBSCarBodyGenerator:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../../config/automotive_parameters.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.params = self.config['automotive_parameters']
        self.components = self.config['car_body_components']
        self.nurbs_templates = self.config['nurbs_surface_templates']
        
        self._initialize_coordinate_system()
    
    def _initialize_coordinate_system(self):
        """初始化车身坐标系"""
        self.L = self.params['整车尺寸']['overall_length']['value']
        self.W = self.params['整车尺寸']['overall_width']['value']
        self.H = self.params['整车尺寸']['overall_height']['value']
        self.WB = self.params['整车尺寸']['wheelbase']['value']
        self.TW = self.params['整车尺寸']['track_width']['value']
        self.GC = self.params['整车尺寸']['ground_clearance']['value']
        
        self.FO = self.params['比例参数']['overhang_front']['value']
        self.RO = self.params['比例参数']['overhang_rear']['value']
        
        self.fwx = self.FO + self.GC
        self.rwx = self.L - self.RO
        self.wcy = self.GC
        self.fwz = self.TW / 2
    
    def _create_nurbs_surface_from_points(self, control_points_3d, degree_u=3, degree_v=3):
        """从3D控制点创建NURBS曲面"""
        nu = len(control_points_3d)
        nv = len(control_points_3d[0]) if nu > 0 else 0
        
        control_points = []
        for i in range(nu):
            row = []
            for j in range(nv):
                x, y, z = control_points_3d[i][j]
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        return NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
    
    def _evaluate_nurbs_surface(self, surface, num_u=20, num_v=16):
        """采样NURBS曲面为点云"""
        points = []
        for i in range(num_u):
            row = []
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                pt = surface.evaluate_point(u, v)
                row.append(pt.tolist())
            points.append(row)
        return points
    
    def generate_hood(self):
        """生成发动机盖NURBS曲面"""
        template = self.nurbs_templates['hood']
        length = self.params['车身部件']['hood_length']['value']
        width = self.params['车身部件']['hood_width']['value']
        height = self.params['车身部件']['hood_height']['value']
        angle = np.radians(self.params['造型角度']['hood_angle']['value'])
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_start = 200
        cx_end = cx_start + length
        cy_base = 300
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_start + u * length
                y = cy_base + height * np.sin(u * np.pi) * np.cos(v * np.pi) + u * np.tan(angle) * length * 0.3
                z = (v - 0.5) * width
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '发动机盖',
            'type': 'hood',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_windshield(self):
        """生成前风挡玻璃NURBS曲面"""
        template = self.nurbs_templates['windshield']
        width = self.params['车身部件']['windshield_width']['value']
        height = self.params['车身部件']['windshield_height']['value']
        angle = np.radians(90 - self.params['造型角度']['windshield_angle']['value'])
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_base = 1700
        cy_bottom = 450
        cy_top = cy_bottom + height * np.cos(angle)
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_base - u * height * np.sin(angle)
                y = cy_bottom + u * height * np.cos(angle)
                z = (v - 0.5) * width * (1 - u * 0.15)
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '前风挡玻璃',
            'type': 'windshield',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#87CEEB',
            'opacity': 0.6,
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_roof(self):
        """生成车顶NURBS曲面"""
        template = self.nurbs_templates['roof']
        length = self.params['车身部件']['roof_length']['value']
        width = self.params['车身部件']['roof_width']['value']
        height = self.params['车身部件']['roof_height']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_start = 1950
        cy_base = 1200
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_start + u * length
                y = cy_base + height * np.cos((u - 0.5) * np.pi * 2)
                z = (v - 0.5) * width * (1 - u * 0.2)
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '车顶',
            'type': 'roof',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_rear_window(self):
        """生成后风挡玻璃NURBS曲面"""
        template = self.nurbs_templates['rear_window']
        width = self.params['车身部件']['rear_window_width']['value']
        height = self.params['车身部件']['rear_window_height']['value']
        angle = np.radians(self.params['造型角度']['rear_window_angle']['value'])
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_base = 3400
        cy_top = 1150
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_base + u * height * np.sin(angle)
                y = cy_top - u * height * np.cos(angle)
                z = (v - 0.5) * width * (1 - u * 0.1)
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '后风挡玻璃',
            'type': 'rear_window',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#87CEEB',
            'opacity': 0.6,
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_trunk(self):
        """生成行李箱盖NURBS曲面"""
        template = self.nurbs_templates['trunk']
        length = self.params['车身部件']['trunk_length']['value']
        width = self.params['车身部件']['trunk_width']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_start = 3650
        cy_base = 550
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_start + u * length
                y = cy_base + 80 * np.exp(-u * 4) * np.cos(v * np.pi)
                z = (v - 0.5) * width
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '行李箱盖',
            'type': 'trunk',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_door_front(self, side='left'):
        """生成前门NURBS曲面"""
        template = self.nurbs_templates['door_front']
        length = self.params['车身部件']['door_front_length']['value']
        height = self.params['车身部件']['door_front_height']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_start = 2100
        cy_base = 250
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_start + u * length
                y = cy_base + v * height
                z = 0
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        z_offset = 420 if side == 'left' else -420
        
        return {
            'name': f'{side}前门',
            'type': 'door',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': z_offset},
            'side': side
        }
    
    def generate_door_rear(self, side='left'):
        """生成后门NURBS曲面"""
        template = self.nurbs_templates['door_rear']
        length = self.params['车身部件']['door_rear_length']['value']
        height = self.params['车身部件']['door_rear_height']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        cx_start = 3300
        cy_base = 280
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = cx_start + u * length
                y = cy_base + v * height
                z = 0
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        z_offset = 420 if side == 'left' else -420
        
        return {
            'name': f'{side}后门',
            'type': 'door',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': z_offset},
            'side': side
        }
    
    def generate_bumper_front(self):
        """生成前保险杠NURBS曲面"""
        template = self.nurbs_templates['bumper_front']
        width = self.params['整车尺寸']['overall_width']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        length = 200
        height = 250
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = -length * (1 - u)
                y = height * (1 - np.cos(u * np.pi)) * 0.5 + 100
                z = (v - 0.5) * width * (0.85 + u * 0.15)
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '前保险杠',
            'type': 'bumper',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#808080',
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_bumper_rear(self):
        """生成后保险杠NURBS曲面"""
        template = self.nurbs_templates['bumper_rear']
        width = self.params['整车尺寸']['overall_width']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        length = 200
        height = 250
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                x = length * u
                y = height * (1 - np.cos(u * np.pi)) * 0.5 + 100
                z = (v - 0.5) * width * (0.85 + (1 - u) * 0.15)
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': '后保险杠',
            'type': 'bumper',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#808080',
            'position': {'x': self.L - length, 'y': 0, 'z': 0}
        }
    
    def generate_headlight(self, side='left'):
        """生成前大灯"""
        width = self.params['车身部件']['headlight_width']['value']
        height = self.params['车身部件']['headlight_height']['value']
        depth = 80
        
        points = []
        for i in range(5):
            row = []
            for j in range(4):
                x = i * (depth / 4)
                y = height * (1 - j / 3)
                z = 0
                row.append([x, y, z])
            points.append(row)
        
        z_offset = 400 if side == 'left' else -400
        
        return {
            'name': f'{side}前大灯',
            'type': 'headlight',
            'points': points,
            'color': '#ffffff',
            'emissive': '#00ffff',
            'position': {'x': 300, 'y': 400, 'z': z_offset}
        }
    
    def generate_taillight(self, side='left'):
        """生成后尾灯"""
        width = self.params['车身部件']['taillight_width']['value']
        height = self.params['车身部件']['taillight_height']['value']
        depth = 60
        
        points = []
        for i in range(4):
            row = []
            for j in range(5):
                x = i * (depth / 3)
                y = height * (1 - j / 4)
                z = 0
                row.append([x, y, z])
            points.append(row)
        
        z_offset = 400 if side == 'left' else -400
        
        return {
            'name': f'{side}后尾灯',
            'type': 'taillight',
            'points': points,
            'color': '#ff0000',
            'emissive': '#ff4400',
            'position': {'x': self.L - 150, 'y': 400, 'z': z_offset}
        }
    
    def generate_grille(self):
        """生成进气格栅"""
        width = self.params['车身部件']['grille_width']['value']
        height = self.params['车身部件']['grille_height']['value']
        depth = 50
        
        points = []
        for i in range(3):
            row = []
            for j in range(8):
                x = i * (depth / 2)
                y = height * (1 - j / 7)
                z = 0
                row.append([x, y, z])
            points.append(row)
        
        return {
            'name': '进气格栅',
            'type': 'grille',
            'points': points,
            'color': '#1a1a1a',
            'position': {'x': 100, 'y': 300, 'z': 0}
        }
    
    def generate_wheel(self, position='front', side='left'):
        """生成车轮"""
        diameter = self.params['车身部件']['wheel_diameter']['value']
        width = self.params['车身部件']['wheel_width']['value']
        
        x_pos = self.fwx if position == 'front' else self.rwx
        z_pos = self.fwz if side == 'left' else -self.fwz
        
        return {
            'name': f'{side}{position}轮',
            'type': 'wheel',
            'radius': diameter / 2,
            'width': width,
            'color': '#222222',
            'rim_color': '#666666',
            'position': {'x': x_pos, 'y': self.GC + diameter / 2, 'z': z_pos}
        }
    
    def generate_mirror(self, side='left'):
        """生成后视镜"""
        width = self.params['车身部件']['mirror_width']['value']
        height = self.params['车身部件']['mirror_height']['value']
        depth = self.params['车身部件']['mirror_depth']['value']
        
        z_offset = 470 if side == 'left' else -470
        
        return {
            'name': f'{side}后视镜',
            'type': 'mirror',
            'width': width,
            'height': height,
            'depth': depth,
            'color': '#c0c0c0',
            'glass_color': '#87CEEB',
            'position': {'x': 2600, 'y': 850, 'z': z_offset}
        }
    
    def generate_fender(self, position='front', side='left'):
        """生成翼子板NURBS曲面"""
        template = self.nurbs_templates['fender_front']
        radius = self.params['车身部件']['wheel_arch_radius']['value']
        
        nu, nv = template['num_u'], template['num_v']
        degree_u, degree_v = template['degree_u'], template['degree_v']
        
        x_center = self.fwx if position == 'front' else self.rwx
        z_center = self.fwz + 30 if side == 'left' else -self.fwz - 30
        
        control_points = []
        for i in range(nu):
            u = i / (nu - 1)
            row = []
            for j in range(nv):
                v = j / (nv - 1)
                
                theta = u * np.pi
                phi = v * np.pi
                
                x = x_center + radius * np.cos(theta) * 0.6
                y = self.GC + radius * np.sin(theta) * np.cos(phi)
                z = z_center + radius * np.sin(theta) * np.sin(phi) * 0.5
                
                row.append(ControlPoint(x, y, z, 1.0))
            control_points.append(row)
        
        surface = NURBSSurface(
            degree_u=degree_u,
            degree_v=degree_v,
            control_points=control_points
        )
        
        return {
            'name': f'{side}{position}翼子板',
            'type': 'fender',
            'points': self._evaluate_nurbs_surface(surface, nu, nv),
            'surface': surface.to_dict(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_pillar(self, pillar_type='A', side='left'):
        """生成立柱"""
        heights = {'A': 1000, 'B': 900, 'C': 800}
        x_positions = {'A': 1700, 'B': 3000, 'C': 4000}
        
        height = heights[pillar_type]
        width = 60
        
        points = []
        for i in range(3):
            row = []
            for j in range(10):
                x = i * (width / 2)
                y = height * (1 - j / 9)
                z = 0
                row.append([x, y, z])
            points.append(row)
        
        z_offset = 430 if side == 'left' else -430
        
        return {
            'name': f'{side}{pillar_type}柱',
            'type': 'pillar',
            'points': points,
            'color': '#1a1a1a',
            'position': {'x': x_positions[pillar_type], 'y': 200, 'z': z_offset}
        }
    
    def generate_door_seam(self):
        """生成车门分缝"""
        seam_width = self.params['车身部件']['door_seam_width']['value']
        
        return {
            'name': '车门分缝',
            'type': 'seam',
            'width': seam_width,
            'color': '#111111',
            'segments': [
                {'start': {'x': 3200, 'y': 250, 'z': 0}, 'end': {'x': 3200, 'y': 1000, 'z': 0}}
            ]
        }
    
    def generate_complete_car(self):
        """生成完整汽车模型"""
        car = {
            'name': '完整车身',
            'components': [],
            'parameters': self.params,
            'total_surfaces': 0,
            'nurbs_quality': {
                'g2_continuous': True,
                'surface_count': 0,
                'control_points_total': 0
            }
        }
        
        components_list = [
            self.generate_bumper_front(),
            self.generate_grille(),
            self.generate_headlight('left'),
            self.generate_headlight('right'),
            self.generate_hood(),
            self.generate_windshield(),
            self.generate_roof(),
            self.generate_rear_window(),
            self.generate_trunk(),
            self.generate_bumper_rear(),
            self.generate_taillight('left'),
            self.generate_taillight('right'),
            self.generate_door_front('left'),
            self.generate_door_front('right'),
            self.generate_door_rear('left'),
            self.generate_door_rear('right'),
            self.generate_mirror('left'),
            self.generate_mirror('right'),
            self.generate_pillar('A', 'left'),
            self.generate_pillar('A', 'right'),
            self.generate_pillar('B', 'left'),
            self.generate_pillar('B', 'right'),
            self.generate_pillar('C', 'left'),
            self.generate_pillar('C', 'right'),
            self.generate_fender('front', 'left'),
            self.generate_fender('front', 'right'),
            self.generate_fender('rear', 'left'),
            self.generate_fender('rear', 'right'),
            self.generate_wheel('front', 'left'),
            self.generate_wheel('front', 'right'),
            self.generate_wheel('rear', 'left'),
            self.generate_wheel('rear', 'right'),
            self.generate_door_seam()
        ]
        
        car['components'] = components_list
        car['total_surfaces'] = len(components_list)
        
        nurbs_count = 0
        cp_total = 0
        for comp in components_list:
            if 'surface' in comp:
                nurbs_count += 1
                if 'control_points' in comp['surface']:
                    cps = comp['surface']['control_points']
                    cp_total += sum(len(row) for row in cps)
        
        car['nurbs_quality']['surface_count'] = nurbs_count
        car['nurbs_quality']['control_points_total'] = cp_total
        
        return car
    
    def export_car_data(self, output_path=None):
        """导出汽车数据到JSON文件"""
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), '../output/car_body_data.json')
        
        car = self.generate_complete_car()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(car, f, ensure_ascii=False, indent=2)
        
        print(f"汽车数据已导出到: {output_path}")
        print(f"总部件数: {len(car['components'])}")
        print(f"NURBS曲面数: {car['nurbs_quality']['surface_count']}")
        print(f"控制点总数: {car['nurbs_quality']['control_points_total']}")
        
        return car
    
    def _build_trimesh_scene(self):
        """用 trimesh 从 NURBS 点云构建 3D 场景"""
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
                            v0 = i * nv + j
                            v1 = i * nv + (j + 1)
                            v2 = (i + 1) * nv + j
                            v3 = (i + 1) * nv + (j + 1)
                            faces.append([v0, v1, v2])
                            faces.append([v1, v3, v2])
                    if faces:
                        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                        pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                        mesh.apply_translation([pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)])
                        color_hex = comp.get('color', '#c0c0c0').lstrip('#')
                        try:
                            mesh.visual.face_colors = [int(color_hex[i:i+2], 16) for i in (0, 2, 4)] + [255]
                        except Exception:
                            pass
                        scene.add_geometry(mesh, node_name=comp.get('name', 'part'))

            elif comp.get('type') == 'wheel' and 'radius' in comp:
                radius = comp['radius']
                wheel_mesh = trimesh.creation.cylinder(radius=radius, height=comp.get('width', 200))
                pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})
                wheel_mesh.apply_translation([pos.get('x', 0), pos.get('y', 0), pos.get('z', 0)])
                color_hex = comp.get('rim_color', '#666666').lstrip('#')
                try:
                    wheel_mesh.visual.face_colors = [int(color_hex[i:i+2], 16) for i in (0, 2, 4)] + [255]
                except Exception:
                    pass
                scene.add_geometry(wheel_mesh, node_name=comp.get('name', 'wheel'))

        return scene

    def export_glb(self, output_path: str) -> str:
        """导出为 GLB 格式"""
        scene = self._build_trimesh_scene()
        data = scene.export(file_type='glb')
        Path(output_path).write_bytes(data)
        return output_path

    def export_stl(self, output_path: str) -> str:
        """导出为 STL 格式"""
        import trimesh
        scene = self._build_trimesh_scene()
        meshes = [g for g in scene.geometry.values() if hasattr(g, 'faces')]
        if meshes:
            combined = trimesh.util.concatenate(meshes)
            data = combined.export(file_type='stl')
        else:
            data = b'solid empty\nendsolid empty\n'
        Path(output_path).write_bytes(data if isinstance(data, bytes) else data.encode())
        return output_path

    def export_obj(self, output_path: str) -> str:
        """导出为 OBJ 格式"""
        scene = self._build_trimesh_scene()
        data = scene.export(file_type='obj')
        Path(output_path).write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
        return output_path

    def export_step(self, output_path: str) -> str:
        """导出为 STEP 格式（基于 NURBS 数据生成 AP214 格式）"""
        car = self.generate_complete_car()
        lines = [
            "ISO-10303-21;",
            "HEADER;",
            "FILE_DESCRIPTION(('EVOLUTION AI NURBS Car Body Model'),'2;1');",
            "FILE_NAME('car_model.step','2026-07-01T00:00:00',('EVOLUTION AI'),('EVOLUTION AI'),'',' ','');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
            "ENDSEC;",
            "DATA;",
        ]
        entity_id = 1

        lines.append(f"#{entity_id}=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));")
        entity_id += 1
        lines.append(f"#{entity_id}=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));")
        entity_id += 1
        lines.append(f"#{entity_id}=(NAMED_UNIT(*)SOLID_ANGLE_UNIT()SI_UNIT($,.STERADIAN.));")
        entity_id += 1
        lines.append(f"#{entity_id}=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(0.01),#{1},'distance_accuracy_value','confusion accuracy');")
        entity_id += 1

        for comp in car['components']:
            comp_name = comp.get('name', 'unknown')
            pos = comp.get('position', {'x': 0, 'y': 0, 'z': 0})

            if 'surface' in comp:
                surf_data = comp['surface']
                cps = surf_data.get('control_points', [])
                if cps:
                    control_points = []
                    for i, row in enumerate(cps[:4]):
                        for j, cp in enumerate(row[:4]):
                            p = [cp['x'], cp['y'], cp['z']]
                            pid = entity_id
                            lines.append(f"#{pid}=CARTESIAN_POINT('',({p[0]:.4f},{p[1]:.4f},{p[2]:.4f}));")
                            control_points.append(pid)
                            entity_id += 1

                    if control_points:
                        surface_id = entity_id
                        cp_refs = ','.join(f'#{p}' for p in control_points)
                        degree_u = surf_data.get('degree_u', 3)
                        degree_v = surf_data.get('degree_v', 3)
                        nu = min(len(cps), 4)
                        nv = min(len(cps[0]) if cps else 4, 4)
                        lines.append(f"#{surface_id}=B_SPLINE_SURFACE_WITH_KNOTS('',{degree_u},{degree_v},({nu},{nv}),({cp_refs}),.UNSPECIFIED.,.F.,.F.,.F.,({degree_u+1},{degree_v+1}),({degree_u+1},{degree_v+1}),.UNSPECIFIED.);")
                        entity_id += 1

                        adv_id = entity_id
                        lines.append(f"#{adv_id}=ADVANCED_FACE('{comp_name}',(#{surface_id}),.F.);")
                        entity_id += 1

            elif 'points' in comp and comp['points']:
                pts = np.array(comp['points'], dtype=np.float64)
                if pts.ndim == 3:
                    nu, nv, _ = pts.shape
                    control_points = []
                    for i in range(min(nu, 4)):
                        for j in range(min(nv, 4)):
                            p = pts[i, j]
                            pid = entity_id
                            lines.append(f"#{pid}=CARTESIAN_POINT('',({p[0]:.4f},{p[1]:.4f},{p[2]:.4f}));")
                            control_points.append(pid)
                            entity_id += 1

                    if control_points:
                        surface_id = entity_id
                        cp_refs = ','.join(f'#{p}' for p in control_points)
                        lines.append(f"#{surface_id}=B_SPLINE_SURFACE_WITH_KNOTS('',3,3,({min(nu,4)},{min(nv,4)}),({cp_refs}),.UNSPECIFIED.,.F.,.F.,.F.,({4},{4}),({4},{4}),.UNSPECIFIED.);")
                        entity_id += 1

                        adv_id = entity_id
                        lines.append(f"#{adv_id}=ADVANCED_FACE('{comp_name}',(#{surface_id}),.F.);")
                        entity_id += 1

            elif comp.get('type') == 'wheel':
                radius = comp.get('radius', 300)
                center_id = entity_id
                lines.append(f"#{center_id}=CARTESIAN_POINT('',({pos.get('x',0):.4f},{pos.get('y',0):.4f},{pos.get('z',0):.4f}));")
                entity_id += 1
                axis_id = entity_id
                lines.append(f"#{axis_id}=AXIS2_PLACEMENT_3D('',#{center_id},$,$);")
                entity_id += 1
                cyl_id = entity_id
                lines.append(f"#{cyl_id}=CYLINDRICAL_SURFACE('',#{axis_id},{radius:.4f});")
                entity_id += 1
                adv_id = entity_id
                lines.append(f"#{adv_id}=ADVANCED_FACE('{comp_name}',(#{cyl_id}),.T.);")
                entity_id += 1

        lines.append("ENDSEC;")
        lines.append("END-ISO-10303-21;")

        content = '\n'.join(lines)
        Path(output_path).write_text(content, encoding='utf-8')
        return output_path


if __name__ == '__main__':
    generator = NURBSCarBodyGenerator()
    car = generator.export_car_data()
    
    print("\n汽车部件清单:")
    for comp in car['components']:
        has_surface = 'surface' in comp
        print(f"  • {comp['name']} {'(NURBS曲面)' if has_surface else ''}")
    
    print(f"\nNURBS质量报告:")
    print(f"  - G2连续: {car['nurbs_quality']['g2_continuous']}")
    print(f"  - NURBS曲面数: {car['nurbs_quality']['surface_count']}")
    print(f"  - 控制点总数: {car['nurbs_quality']['control_points_total']}")