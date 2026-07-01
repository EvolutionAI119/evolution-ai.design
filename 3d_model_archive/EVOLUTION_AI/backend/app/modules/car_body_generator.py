"""
EVOLUTION AI - 完整汽车造型生成器
生成包含所有车身部件的汽车模型
"""

import numpy as np
import json
import os
import struct
from pathlib import Path

class CarBodyGenerator:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '../../config/automotive_parameters.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.params = self.config['automotive_parameters']
        self.components = self.config['car_body_components']
        self.nurbs_templates = self.config['nurbs_surface_templates']
        
    def generate_hood(self):
        """生成发动机盖曲面"""
        template = self.nurbs_templates['hood']
        width = self.params['车身部件']['hood_width']['value']
        length = self.params['车身部件']['hood_length']['value']
        height = self.params['车身部件']['hood_height']['value']
        angle = np.radians(self.params['造型角度']['hood_angle']['value'])
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = u * length
                y = height * np.sin(u * np.pi) * np.cos(v * np.pi)
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '发动机盖',
            'type': 'hood',
            'points': points.tolist(),
            'color': '#c0c0c0',
            'position': {'x': 0, 'y': 0, 'z': 0}
        }
    
    def generate_windshield(self):
        """生成前风挡玻璃"""
        template = self.nurbs_templates['windshield']
        width = self.params['车身部件']['windshield_width']['value']
        height = self.params['车身部件']['windshield_height']['value']
        angle = np.radians(self.params['造型角度']['windshield_angle']['value'])
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = -height * np.sin(angle) * (1 - u)
                y = height * np.cos(angle) * (1 - u)
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '前风挡玻璃',
            'type': 'windshield',
            'points': points.tolist(),
            'color': '#87CEEB',
            'opacity': 0.6,
            'position': {'x': 1300, 'y': 0, 'z': 0}
        }
    
    def generate_roof(self):
        """生成车顶曲面"""
        template = self.nurbs_templates['roof']
        width = self.params['车身部件']['roof_width']['value']
        length = self.params['车身部件']['roof_length']['value']
        height = self.params['车身部件']['roof_height']['value']
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = u * length
                y = height * np.cos((u - 0.5) * np.pi * 2) * 0.5
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '车顶',
            'type': 'roof',
            'points': points.tolist(),
            'color': '#c0c0c0',
            'position': {'x': 1300, 'y': 800, 'z': 0}
        }
    
    def generate_rear_window(self):
        """生成后风挡玻璃"""
        template = self.nurbs_templates['rear_window']
        width = self.params['车身部件']['rear_window_width']['value']
        height = self.params['车身部件']['rear_window_height']['value']
        angle = np.radians(self.params['造型角度']['rear_window_angle']['value'])
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = u * height * np.sin(angle)
                y = -height * np.cos(angle) * u
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '后风挡玻璃',
            'type': 'rear_window',
            'points': points.tolist(),
            'color': '#87CEEB',
            'opacity': 0.6,
            'position': {'x': 2800, 'y': 1250, 'z': 0}
        }
    
    def generate_trunk(self):
        """生成行李箱盖"""
        template = self.nurbs_templates['trunk']
        width = self.params['车身部件']['trunk_width']['value']
        length = self.params['车身部件']['trunk_length']['value']
        height = 30
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = u * length
                y = height * np.exp(-u * 3)
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '行李箱盖',
            'type': 'trunk',
            'points': points.tolist(),
            'color': '#c0c0c0',
            'position': {'x': 2900, 'y': 600, 'z': 0}
        }
    
    def generate_door_front(self, side='left'):
        """生成前门"""
        template = self.nurbs_templates['door_front']
        length = self.params['车身部件']['door_front_length']['value']
        height = self.params['车身部件']['door_front_height']['value']
        seam = self.params['车身部件']['door_seam_width']['value']
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = u * length
                y = v * height
                z = 0
                
                points[i, j] = [x, y, z]
        
        z_offset = 420 if side == 'left' else -420
        
        return {
            'name': f'{side}前门',
            'type': 'door',
            'points': points.tolist(),
            'color': '#c0c0c0',
            'position': {'x': 1500, 'y': 200, 'z': z_offset},
            'side': side
        }
    
    def generate_door_rear(self, side='left'):
        """生成后门"""
        template = self.nurbs_templates['door_rear']
        length = self.params['车身部件']['door_rear_length']['value']
        height = self.params['车身部件']['door_rear_height']['value']
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = u * length
                y = v * height
                z = 0
                
                points[i, j] = [x, y, z]
        
        z_offset = 420 if side == 'left' else -420
        
        return {
            'name': f'{side}后门',
            'type': 'door',
            'points': points.tolist(),
            'color': '#c0c0c0',
            'position': {'x': 2700, 'y': 250, 'z': z_offset},
            'side': side
        }
    
    def generate_bumper_front(self):
        """生成前保险杠"""
        template = self.nurbs_templates['bumper_front']
        width = self.params['整车尺寸']['overall_width']['value']
        height = 250
        length = 200
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = -length * (1 - u)
                y = height * (1 - np.cos(u * np.pi)) * 0.5
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '前保险杠',
            'type': 'bumper',
            'points': points.tolist(),
            'color': '#808080',
            'position': {'x': 0, 'y': 100, 'z': 0}
        }
    
    def generate_bumper_rear(self):
        """生成后保险杠"""
        template = self.nurbs_templates['bumper_rear']
        width = self.params['整车尺寸']['overall_width']['value']
        height = 250
        length = 200
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                x = length * u
                y = height * (1 - np.cos(u * np.pi)) * 0.5
                z = (v - 0.5) * width
                
                points[i, j] = [x, y, z]
        
        return {
            'name': '后保险杠',
            'type': 'bumper',
            'points': points.tolist(),
            'color': '#808080',
            'position': {'x': 4600, 'y': 100, 'z': 0}
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
            'position': {'x': 4400, 'y': 400, 'z': z_offset}
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
        
        x_pos = 900 if position == 'front' else 3700
        z_pos = 420 if side == 'left' else -420
        
        return {
            'name': f'{side}{position}轮',
            'type': 'wheel',
            'radius': diameter / 2,
            'width': width,
            'color': '#222222',
            'rim_color': '#666666',
            'position': {'x': x_pos, 'y': diameter / 2, 'z': z_pos}
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
        """生成翼子板/轮拱"""
        template = self.nurbs_templates['fender_front']
        radius = self.params['车身部件']['wheel_arch_radius']['value']
        
        num_u, num_v = template['num_u'], template['num_v']
        points = np.zeros((num_u, num_v, 3))
        
        for i in range(num_u):
            u = i / (num_u - 1)
            for j in range(num_v):
                v = j / (num_v - 1)
                
                theta = u * np.pi
                phi = v * np.pi
                
                x = radius * np.cos(theta)
                y = radius * np.sin(theta) * np.cos(phi)
                z = radius * np.sin(theta) * np.sin(phi)
                
                points[i, j] = [x, y, z]
        
        x_pos = 800 if position == 'front' else 3600
        z_pos = 440 if side == 'left' else -440
        
        return {
            'name': f'{side}{position}翼子板',
            'type': 'fender',
            'points': points.tolist(),
            'color': '#c0c0c0',
            'position': {'x': x_pos, 'y': 300, 'z': z_pos}
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
                {'start': {'x': 2600, 'y': 250, 'z': 0}, 'end': {'x': 2600, 'y': 1000, 'z': 0}}
            ]
        }
    
    def generate_complete_car(self):
        """生成完整汽车模型"""
        car = {
            'name': '完整车身',
            'components': [],
            'parameters': self.params,
            'total_surfaces': 0
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
        
        return car

    # ============ 网格导出方法 ============

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
                    # 构建三角面片：每个 (i,j) 网格单元拆为 2 个三角形
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
        # 合并场景中所有网格
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
            "FILE_DESCRIPTION(('EVOLUTION AI Car Body Model'),'2;1');",
            "FILE_NAME('car_model.step','2026-07-01T00:00:00',('EVOLUTION AI'),('EVOLUTION AI'),'',' ','');",
            "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));",
            "ENDSEC;",
            "DATA;",
        ]
        entity_id = 1

        # 定义单位
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

            if 'points' in comp and comp['points']:
                pts = np.array(comp['points'], dtype=np.float64)
                if pts.ndim == 3:
                    nu, nv, _ = pts.shape
                    # 用 B_SPLINE_SURFACE_WITH_KNOTS 表示
                    control_points = []
                    for i in range(min(nu, 4)):
                        for j in range(min(nv, 4)):
                            p = pts[i, j]
                            pid = entity_id
                            lines.append(f"#{pid}=CARTESIAN_POINT('',({p[0]:.4f},{p[1]:.4f},{p[2]:.4f}));")
                            control_points.append(pid)
                            entity_id += 1

                    surface_id = entity_id
                    cp_refs = ','.join(f'#{p}' for p in control_points)
                    lines.append(f"#{surface_id}=B_SPLINE_SURFACE_WITH_KNOTS('',3,3,({min(nu,4)},{min(nv,4)}),({cp_refs}),.UNSPECIFIED.,.F.,.F.,.F.,({4},{4}),({4},{4}),.UNSPECIFIED.);")
                    entity_id += 1

                    # 高级面
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
    generator = CarBodyGenerator()
    car = generator.export_car_data()
    
    print("\n汽车部件清单:")
    for comp in car['components']:
        print(f"  • {comp['name']}")
