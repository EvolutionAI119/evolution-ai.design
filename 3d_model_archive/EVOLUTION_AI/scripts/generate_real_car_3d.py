"""
EVOLUTION AI - Real 3D Car Model Generator
Generates standard OBJ format for Blender/Maya/Three.js
"""

import numpy as np
import os
from datetime import datetime

class RealCar3DGenerator:
    def __init__(self):
        self.params = {
            'length': 4.95, 'width': 1.92, 'height': 1.42,
            'wheelbase': 2.89, 'front_overhang': 0.85, 'rear_overhang': 1.21,
            'ground_clearance': 0.12, 'hood_length': 1.15,
            'windshield_angle': 65, 'rear_window_angle': 28,
            'roof_height': 1.38, 'waist_height': 0.72,
            'track_width': 1.66, 'wheel_radius': 0.35, 'wheel_width': 0.25,
            'hood_drop': 0.08, 'trunk_drop': 0.12,
        }
        self.vertices = []
        self.normals = []
        self.faces = []

    def add_vertex(self, x, y, z):
        self.vertices.append((x, y, z))
        return len(self.vertices) - 1

    def add_face(self, v1, v2, v3, mat='body'):
        self.faces.append((v1+1, v2+1, v3+1, mat))

    def add_quad(self, v1, v2, v3, v4, mat='body'):
        self.add_face(v1, v2, v3, mat)
        self.add_face(v1, v3, v4, mat)

    def generate_hood(self, res=20):
        vm = {}
        for i in range(res + 1):
            u = i / res
            x = u * self.params['hood_length']
            for j in range(res + 1):
                v = j / res
                z = (v - 0.5) * self.params['width'] * 0.85
                y_base = self.params['waist_height']
                x_curve = np.sin(u * np.pi * 0.8) * self.params['hood_drop'] * 2
                z_curve = np.cos((v - 0.5) * np.pi * 2) * 0.03
                front_drop = self.params['hood_drop'] * np.exp(-u * 5)
                y = y_base + x_curve + z_curve - front_drop
                vm[(i, j)] = self.add_vertex(x, y, z)
        for i in range(res):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'hood')
        return vm

    def generate_windshield(self, res=15):
        vm = {}
        ang = np.radians(self.params['windshield_angle'])
        bx = self.params['hood_length']
        by = self.params['waist_height'] + 0.05
        h = self.params['roof_height'] - by
        w = self.params['width'] * 0.82
        for i in range(res + 1):
            u = i / res
            yo = u * h
            xo = -yo / np.tan(ang)
            for j in range(res + 1):
                v = j / res
                z = (v - 0.5) * w
                zc = np.cos((v - 0.5) * np.pi) * 0.02
                vm[(i,j)] = self.add_vertex(bx + xo, by + yo + zc, z)
        for i in range(res):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'glass')
        return vm

    def generate_roof(self, res=20):
        vm = {}
        bx = self.params['hood_length'] + (self.params['roof_height'] - self.params['waist_height']) / np.tan(np.radians(self.params['windshield_angle']))
        ex = self.params['length'] - self.params['rear_overhang'] - (self.params['roof_height'] - self.params['waist_height']) / np.tan(np.radians(self.params['rear_window_angle']))
        rl = ex - bx
        w = self.params['width'] * 0.78
        for i in range(res + 1):
            u = i / res
            x = bx + u * rl
            for j in range(res + 1):
                v = j / res
                z = (v - 0.5) * w
                arch = np.sin(u * np.pi) * 0.015
                sd = np.cos((v - 0.5) * np.pi * 2) * 0.02
                vm[(i,j)] = self.add_vertex(x, self.params['roof_height'] + arch + sd, z)
        for i in range(res):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'roof')
        return vm

    def generate_rear_window(self, res=15):
        vm = {}
        ang = np.radians(self.params['rear_window_angle'])
        ex = self.params['length'] - self.params['rear_overhang']
        by = self.params['roof_height']
        h = by - (self.params['waist_height'] + 0.1)
        w = self.params['width'] * 0.80
        for i in range(res + 1):
            u = i / res
            yo = u * h
            xo = yo / np.tan(ang)
            for j in range(res + 1):
                v = j / res
                z = (v - 0.5) * w
                zc = np.cos((v - 0.5) * np.pi) * 0.015
                vm[(i,j)] = self.add_vertex(ex - xo, by - yo + zc, z)
        for i in range(res):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'glass')
        return vm

    def generate_trunk(self, res=15):
        vm = {}
        sx = self.params['length'] - self.params['rear_overhang']
        tl = self.params['rear_overhang'] - 0.15
        w = self.params['width'] * 0.82
        for i in range(res + 1):
            u = i / res
            x = sx + u * tl
            for j in range(res + 1):
                v = j / res
                z = (v - 0.5) * w
                yb = self.params['waist_height'] + 0.05
                drop = np.sin(u * np.pi * 0.5) * self.params['trunk_drop']
                zc = np.cos((v - 0.5) * np.pi * 2) * 0.02
                vm[(i,j)] = self.add_vertex(x, yb - drop + zc, z)
        for i in range(res):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'trunk')
        return vm

    def generate_side(self, side='left', res=25):
        vm = {}
        z = self.params['width'] / 2 * (1 if side == 'left' else -1)
        px = [0, 0.15, 0.3, self.params['hood_length'] * 0.5, self.params['hood_length'],
              self.params['hood_length'] + 0.3, self.params['hood_length'] + 0.6,
              self.params['hood_length'] + 0.9, self.params['wheelbase'] * 0.4 + self.params['front_overhang'],
              self.params['wheelbase'] * 0.6 + self.params['front_overhang'],
              self.params['length'] - self.params['rear_overhang'] - 0.9,
              self.params['length'] - self.params['rear_overhang'] - 0.5,
              self.params['length'] - self.params['rear_overhang'],
              self.params['length'] - self.params['rear_overhang'] + self.params['rear_overhang'] * 0.4,
              self.params['length'] - self.params['rear_overhang'] + self.params['rear_overhang'] * 0.8,
              self.params['length'] - 0.05, self.params['length']]
        pyu = [self.params['ground_clearance'] + 0.35, self.params['ground_clearance'] + 0.45,
               self.params['waist_height'] - 0.05, self.params['waist_height'] + 0.1,
               self.params['waist_height'] + 0.15, self.params['waist_height'] + 0.2,
               self.params['waist_height'] + 0.5, self.params['roof_height'] - 0.1,
               self.params['roof_height'], self.params['roof_height'],
               self.params['roof_height'] - 0.05, self.params['waist_height'] + 0.5,
               self.params['waist_height'] + 0.15, self.params['waist_height'] + 0.1,
               self.params['waist_height'] + 0.05, self.params['ground_clearance'] + 0.4,
               self.params['ground_clearance'] + 0.3]
        pyl = [self.params['ground_clearance']] * 17
        for i in range(len(px)):
            for j in range(res + 1):
                v = j / res
                y = pyl[i] + (pyu[i] - pyl[i]) * v
                vm[(i, j)] = self.add_vertex(px[i], y, z)
        for i in range(len(px) - 1):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'body')
        return vm

    def generate_wheel(self, cx, cy, cz, res=20):
        vm = {}
        r = self.params['wheel_radius']
        w = self.params['wheel_width'] / 2
        for i in range(res + 1):
            th = i / res * 2 * np.pi
            for j in range(3):
                off = (j - 1) * w
                x = cx + r * np.cos(th)
                y = cy + r * np.sin(th)
                z = cz + off
                bulge = np.cos(th) * 0.02
                vm[(i, j)] = self.add_vertex(x, y + bulge, z)
        for i in range(res):
            for j in range(2):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'tire')
        return vm

    def generate_bumper(self, pos='front', res=15):
        vm = {}
        if pos == 'front':
            xs, xe = 0, 0.15
        else:
            xs, xe = self.params['length'] - 0.15, self.params['length']
        w = self.params['width'] * 0.9
        for i in range(res + 1):
            u = i / res
            x = xs + u * (xe - xs)
            for j in range(res + 1):
                v = j / res
                z = (v - 0.5) * w
                y = self.params['ground_clearance'] + 0.35 - np.cos(u * np.pi) * 0.05
                vm[(i, j)] = self.add_vertex(x, y, z)
        for i in range(res):
            for j in range(res):
                self.add_quad(vm[(i,j)], vm[(i+1,j)], vm[(i+1,j+1)], vm[(i,j+1)], 'bumper')
        return vm

    def export_obj(self, path):
        with open(path, 'w') as f:
            f.write("# EVOLUTION AI - Real 3D Car Model\n")
            f.write(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Length: {self.params['length']}m Width: {self.params['width']}m Height: {self.params['height']}m\n")
            f.write("mtllib car_materials.mtl\n\n")
            for v in self.vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write(f"\n# {len(self.vertices)} vertices\n\n")
            cur = None
            for face in self.faces:
                v1, v2, v3, mat = face
                if mat != cur:
                    f.write(f"usemtl {mat}\n")
                    cur = mat
                f.write(f"f {v1} {v2} {v3}\n")
        print(f"OBJ saved: {path} ({len(self.vertices)} vertices, {len(self.faces)} faces)")

    def export_mtl(self, path):
        mats = {
            'body': {'Kd': (0.17, 0.24, 0.31), 'Ks': (0.5, 0.5, 0.5), 'Ns': 96.0, 'd': 1.0},
            'hood': {'Kd': (0.17, 0.24, 0.31), 'Ks': (0.6, 0.6, 0.6), 'Ns': 128.0, 'd': 1.0},
            'roof': {'Kd': (0.17, 0.24, 0.31), 'Ks': (0.7, 0.7, 0.7), 'Ns': 128.0, 'd': 1.0},
            'trunk': {'Kd': (0.17, 0.24, 0.31), 'Ks': (0.5, 0.5, 0.5), 'Ns': 96.0, 'd': 1.0},
            'glass': {'Kd': (0.52, 0.76, 0.91), 'Ks': (0.9, 0.9, 0.9), 'Ns': 200.0, 'd': 0.7},
            'bumper': {'Kd': (0.1, 0.1, 0.1), 'Ks': (0.3, 0.3, 0.3), 'Ns': 64.0, 'd': 1.0},
            'tire': {'Kd': (0.11, 0.16, 0.2), 'Ks': (0.2, 0.2, 0.2), 'Ns': 32.0, 'd': 1.0},
        }
        with open(path, 'w') as f:
            f.write("# EVOLUTION AI - Car Materials\n\n")
            for name, mat in mats.items():
                f.write(f"newmtl {name}\n")
                f.write(f"Kd {mat['Kd'][0]:.6f} {mat['Kd'][1]:.6f} {mat['Kd'][2]:.6f}\n")
                f.write(f"Ks {mat['Ks'][0]:.6f} {mat['Ks'][1]:.6f} {mat['Ks'][2]:.6f}\n")
                f.write(f"Ns {mat['Ns']:.6f}\n")
                f.write(f"d {mat['d']:.6f}\n")
                f.write("illum 2\n\n")
        print(f"MTL saved: {path}")

    def generate(self):
        print("EVOLUTION AI - Real 3D Car Generation")
        print("=" * 50)
        print("Car Parameters:")
        for k, v in self.params.items():
            print(f"  {k}: {v}")
        print("\nGenerating components...")
        print("  [1/8] Hood")
        self.generate_hood(25)
        print("  [2/8] Windshield")
        self.generate_windshield(15)
        print("  [3/8] Roof")
        self.generate_roof(25)
        print("  [4/8] Rear Window")
        self.generate_rear_window(15)
        print("  [5/8] Trunk")
        self.generate_trunk(15)
        print("  [6/8] Left Side")
        self.generate_side('left', 30)
        print("  [7/8] Right Side")
        self.generate_side('right', 30)
        print("  [8/8] Wheels")
        fx = self.params['front_overhang'] + self.params['wheelbase'] * 0.35
        rx = self.params['front_overhang'] + self.params['wheelbase'] * 0.65
        wy = self.params['ground_clearance'] + self.params['wheel_radius']
        wz = self.params['width'] / 2 - 0.05
        self.generate_wheel(fx, wy, wz)
        self.generate_wheel(fx, wy, -wz)
        self.generate_wheel(rx, wy, wz)
        self.generate_wheel(rx, wy, -wz)
        print("  Front Bumper")
        self.generate_bumper('front', 15)
        print("  Rear Bumper")
        self.generate_bumper('rear', 15)
        print(f"\nDone! Vertices: {len(self.vertices)}, Faces: {len(self.faces)}")

def main():
    gen = RealCar3DGenerator()
    gen.generate()
    od = "output"
    os.makedirs(od, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    gen.export_obj(os.path.join(od, f"EVOLUTION_AI_REAL_CAR_{ts}.obj"))
    gen.export_mtl(os.path.join(od, "car_materials.mtl"))
    print("\nOpen in Blender:")
    print("  1. File > Import > Wavefront (.obj)")
    print("  2. Ensure MTL is in same folder")

if __name__ == '__main__':
    main()
