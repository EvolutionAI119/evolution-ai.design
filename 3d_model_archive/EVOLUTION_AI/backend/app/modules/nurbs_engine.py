"""
NURBS曲面处理模块
支持NURBS曲面的创建、编辑、修改和分析
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json


class ContinuityType(Enum):
    """连续性类型"""
    G0 = "G0"  # 位置连续
    G1 = "G1"  # 切线连续
    G2 = "G2"  # 曲率连续
    G3 = "G3"  # 曲率变化率连续


@dataclass
class ControlPoint:
    """控制点"""
    x: float
    y: float
    z: float
    weight: float = 1.0

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z, self.weight])

    @classmethod
    def from_array(cls, arr: np.ndarray):
        return cls(arr[0], arr[1], arr[2], arr[3] if len(arr) > 3 else 1.0)


@dataclass
class KnotVector:
    """节点矢量"""
    values: List[float]

    def normalize(self) -> 'KnotVector':
        """归一化节点矢量"""
        if not self.values:
            return self
        min_val = min(self.values)
        max_val = max(self.values)
        if max_val - min_val < 1e-10:
            return KnotVector([0.0] * len(self.values))
        return KnotVector([(v - min_val) / (max_val - min_val) for v in self.values])

    def to_json(self) -> str:
        return json.dumps(self.values)

    @classmethod
    def from_json(cls, json_str: str):
        return cls(json.loads(json_str))


class NURBSSurface:
    """NURBS曲面类"""

    def __init__(
        self,
        degree_u: int = 3,
        degree_v: int = 3,
        control_points: Optional[List[List[ControlPoint]]] = None,
        knot_vector_u: Optional[KnotVector] = None,
        knot_vector_v: Optional[KnotVector] = None
    ):
        self.degree_u = degree_u
        self.degree_v = degree_v
        self.control_points = control_points or []
        self.knot_vector_u = knot_vector_u or KnotVector([])
        self.knot_vector_v = knot_vector_v or KnotVector([])

        if control_points:
            self._initialize_knot_vectors()

    def _initialize_knot_vectors(self):
        """初始化节点矢量"""
        n = len(self.control_points) - 1
        m = len(self.control_points[0]) - 1

        if not self.knot_vector_u.values:
            self.knot_vector_u = self._create_uniform_knot_vector(n, self.degree_u)
        if not self.knot_vector_v.values:
            self.knot_vector_v = self._create_uniform_knot_vector(m, self.degree_v)

    @staticmethod
    def _create_uniform_knot_vector(num_control: int, degree: int) -> KnotVector:
        """创建均匀节点矢量"""
        n = num_control
        p = degree
        # 节点矢量长度 = n + p + 1
        # 其中 n 是最后一个控制点的索引 (控制点数 - 1)
        num_knots = n + p + 2
        
        knots = []
        # 前p+1个节点为0
        for i in range(p + 1):
            knots.append(0.0)
        
        # 中间节点均匀分布
        num_internal = n - p
        if num_internal > 0:
            for i in range(1, num_internal + 1):
                knots.append(i / (num_internal + 1))
        
        # 后p+1个节点为1
        for i in range(p + 1):
            knots.append(1.0)
        
        return KnotVector(knots)

    def evaluate_point(self, u: float, v: float) -> np.ndarray:
        """计算曲面上的点"""
        point = np.zeros(3)
        weight_sum = 0.0

        for i in range(len(self.control_points)):
            for j in range(len(self.control_points[0])):
                basis_u = self._evaluate_basis_function(i, self.degree_u, u, self.knot_vector_u.values)
                basis_v = self._evaluate_basis_function(j, self.degree_v, v, self.knot_vector_v.values)
                weight = self.control_points[i][j].weight
                basis = basis_u * basis_v * weight
                point += basis * np.array([
                    self.control_points[i][j].x,
                    self.control_points[i][j].y,
                    self.control_points[i][j].z
                ])
                weight_sum += basis

        if weight_sum > 1e-10:
            point /= weight_sum

        return point

    def _evaluate_basis_function(self, i: int, k: int, u: float, knots: List[float]) -> float:
        """计算B样条基函数"""
        # 边界检查
        if i + k + 1 >= len(knots):
            return 0.0
        
        if k == 0:
            if knots[i] <= u < knots[i + 1] or (u >= 1.0 and i == len(knots) - 2):
                return 1.0
            return 0.0

        result = 0.0
        denom1 = knots[i + k] - knots[i]
        if denom1 > 1e-10:
            result += (u - knots[i]) / denom1 * self._evaluate_basis_function(i, k - 1, u, knots)

        denom2 = knots[i + k + 1] - knots[i + 1]
        if denom2 > 1e-10:
            result += (knots[i + k + 1] - u) / denom2 * self._evaluate_basis_function(i + 1, k - 1, u, knots)

        return result

    def evaluate_normal(self, u: float, v: float) -> np.ndarray:
        """计算曲面上的法向量"""
        eps = 0.001
        p1 = self.evaluate_point(u + eps, v)
        p2 = self.evaluate_point(u - eps, v)
        p3 = self.evaluate_point(u, v + eps)
        p4 = self.evaluate_point(u, v - eps)

        du = p1 - p2
        dv = p3 - p4

        normal = np.cross(du, dv)
        norm = np.linalg.norm(normal)
        if norm > 1e-10:
            normal /= norm

        return normal

    def evaluate_curvature(self, u: float, v: float) -> Dict[str, float]:
        """计算曲率"""
        eps = 0.001

        p = self.evaluate_point(u, v)
        pu = (self.evaluate_point(u + eps, v) - self.evaluate_point(u - eps, v)) / (2 * eps)
        pv = (self.evaluate_point(u, v + eps) - self.evaluate_point(u, v - eps)) / (2 * eps)

        puu = (self.evaluate_point(u + eps, v) - 2 * p + self.evaluate_point(u - eps, v)) / (eps ** 2)
        pvv = (self.evaluate_point(u, v + eps) - 2 * p + self.evaluate_point(u, v - eps)) / (eps ** 2)

        normal = self.evaluate_normal(u, v)

        k1 = np.dot(puu, normal)
        k2 = np.dot(pvv, normal)

        return {
            'gaussian_curvature': k1 * k2,
            'mean_curvature': (k1 + k2) / 2,
            'principal_curvature_1': k1,
            'principal_curvature_2': k2
        }

    def modify_control_point(self, i: int, j: int, new_position: Tuple[float, float, float]):
        """修改控制点位置"""
        if 0 <= i < len(self.control_points) and 0 <= j < len(self.control_points[0]):
            cp = self.control_points[i][j]
            cp.x, cp.y, cp.z = new_position

    def modify_control_point_weight(self, i: int, j: int, new_weight: float):
        """修改控制点权重"""
        if 0 <= i < len(self.control_points) and 0 <= j < len(self.control_points[0]):
            self.control_points[i][j].weight = max(0.01, new_weight)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            'degree_u': self.degree_u,
            'degree_v': self.degree_v,
            'control_points': [
                [
                    {'x': cp.x, 'y': cp.y, 'z': cp.z, 'weight': cp.weight}
                    for cp in row
                ]
                for row in self.control_points
            ],
            'knot_vector_u': self.knot_vector_u.values,
            'knot_vector_v': self.knot_vector_v.values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NURBSSurface':
        """从字典创建"""
        control_points = [
            [
                ControlPoint(cp['x'], cp['y'], cp['z'], cp.get('weight', 1.0))
                for cp in row
            ]
            for row in data['control_points']
        ]

        return cls(
            degree_u=data['degree_u'],
            degree_v=data['degree_v'],
            control_points=control_points,
            knot_vector_u=KnotVector(data['knot_vector_u']),
            knot_vector_v=KnotVector(data['knot_vector_v'])
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'NURBSSurface':
        return cls.from_dict(json.loads(json_str))


class NURBSCurve:
    """NURBS曲线类"""

    def __init__(
        self,
        degree: int = 3,
        control_points: Optional[List[ControlPoint]] = None,
        knot_vector: Optional[KnotVector] = None
    ):
        self.degree = degree
        self.control_points = control_points or []
        self.knot_vector = knot_vector or KnotVector([])

        if control_points and not knot_vector:
            self.knot_vector = self._create_uniform_knot_vector(len(control_points) - 1, degree)

    @staticmethod
    def _create_uniform_knot_vector(num_control: int, degree: int) -> KnotVector:
        n = num_control
        k = degree
        total = n + k + 1

        knots = []
        for i in range(total):
            if i <= k:
                knots.append(0.0)
            elif i >= n:
                knots.append(1.0)
            else:
                knots.append(i - k)

        return KnotVector(knots)

    def evaluate_point(self, t: float) -> np.ndarray:
        """计算曲线上的点"""
        point = np.zeros(3)
        weight_sum = 0.0

        for i, cp in enumerate(self.control_points):
            basis = self._evaluate_basis_function(i, self.degree, t, self.knot_vector.values)
            weight = cp.weight
            point += basis * weight * np.array([cp.x, cp.y, cp.z])
            weight_sum += basis * weight

        if weight_sum > 1e-10:
            point /= weight_sum

        return point

    def _evaluate_basis_function(self, i: int, k: int, t: float, knots: List[float]) -> float:
        """计算B样条基函数"""
        if k == 0:
            if knots[i] <= t < knots[i + 1] or (t >= 1.0 and i == len(knots) - 2):
                return 1.0
            return 0.0

        result = 0.0
        denom1 = knots[i + k] - knots[i]
        if denom1 > 1e-10:
            result += (t - knots[i]) / denom1 * self._evaluate_basis_function(i, k - 1, t, knots)

        denom2 = knots[i + k + 1] - knots[i + 1]
        if denom2 > 1e-10:
            result += (knots[i + k + 1] - t) / denom2 * self._evaluate_basis_function(i + 1, k - 1, t, knots)

        return result

    def compute_length(self, num_samples: int = 100) -> float:
        """计算曲线长度"""
        length = 0.0
        t_values = np.linspace(0, 1, num_samples)

        prev_point = self.evaluate_point(t_values[0])
        for t in t_values[1:]:
            point = self.evaluate_point(t)
            length += np.linalg.norm(point - prev_point)
            prev_point = point

        return length

    def to_dict(self) -> Dict[str, Any]:
        return {
            'degree': self.degree,
            'control_points': [
                {'x': cp.x, 'y': cp.y, 'z': cp.z, 'weight': cp.weight}
                for cp in self.control_points
            ],
            'knot_vector': self.knot_vector.values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NURBSCurve':
        control_points = [
            ControlPoint(cp['x'], cp['y'], cp['z'], cp.get('weight', 1.0))
            for cp in data['control_points']
        ]
        return cls(
            degree=data['degree'],
            control_points=control_points,
            knot_vector=KnotVector(data['knot_vector'])
        )


class SurfaceModifier:
    """曲面修改工具"""

    def __init__(self, surface: NURBSSurface):
        self.surface = surface

    def translate(self, dx: float, dy: float, dz: float):
        """平移曲面"""
        for row in self.surface.control_points:
            for cp in row:
                cp.x += dx
                cp.y += dy
                cp.z += dz

    def scale(self, sx: float, sy: float, sz: float, center: Optional[Tuple[float, float, float]] = None):
        """缩放曲面"""
        if center is None:
            center = (0, 0, 0)

        cx, cy, cz = center
        for row in self.surface.control_points:
            for cp in row:
                cp.x = cx + (cp.x - cx) * sx
                cp.y = cy + (cp.y - cy) * sy
                cp.z = cz + (cp.z - cz) * sz

    def rotate(self, angle: float, axis: str = 'z', center: Optional[Tuple[float, float, float]] = None):
        """旋转曲面"""
        if center is None:
            center = (0, 0, 0)

        cx, cy, cz = center
        angle_rad = np.radians(angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        for row in self.surface.control_points:
            for cp in row:
                x, y, z = cp.x - cx, cp.y - cy, cp.z - cz

                if axis == 'z':
                    new_x = x * cos_a - y * sin_a
                    new_y = x * sin_a + y * cos_a
                    new_z = z
                elif axis == 'x':
                    new_x = x
                    new_y = y * cos_a - z * sin_a
                    new_z = y * sin_a + z * cos_a
                else:
                    new_x = x * cos_a + z * sin_a
                    new_y = y
                    new_z = -x * sin_a + z * cos_a

                cp.x, cp.y, cp.z = new_x + cx, new_y + cy, new_z + cz

    def offset(self, distance: float):
        """偏移曲面"""
        for row in self.surface.control_points:
            for cp in row:
                cp.x += distance * 0.1
                cp.y += distance * 0.1
                cp.z += distance * 0.1


class CurveModifier:
    """曲线修改工具"""

    def __init__(self, curve: NURBSCurve):
        self.curve = curve

    def translate(self, dx: float, dy: float, dz: float):
        """平移曲线"""
        for cp in self.curve.control_points:
            cp.x += dx
            cp.y += dy
            cp.z += dz

    def scale(self, sx: float, sy: float, sz: float):
        """缩放曲线"""
        for cp in self.curve.control_points:
            cp.x *= sx
            cp.y *= sy
            cp.z *= sz
