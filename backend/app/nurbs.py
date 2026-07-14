"""NURBS曲面引擎：实现B样条基函数(De Boor-Cox递推)与NURBS曲线/曲面求值"""
import json
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple


@dataclass
class ControlPoint:
    """控制点：三维坐标 + 权重"""
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
    values: List[float] = field(default_factory=list)

    def normalize(self) -> 'KnotVector':
        if not self.values:
            return self
        lo, hi = min(self.values), max(self.values)
        if hi - lo < 1e-10:
            return KnotVector([0.0] * len(self.values))
        return KnotVector([(v - lo) / (hi - lo) for v in self.values])

    def to_json(self) -> str:
        return json.dumps(self.values)

    @classmethod
    def from_json(cls, json_str: str):
        return cls(json.loads(json_str))


def _create_uniform_knot_vector(num_control: int, degree: int) -> KnotVector:
    """创建均匀节点矢量（num_control 为最后一个控制点索引）"""
    n, p = num_control, degree
    knots = [0.0] * (p + 1)
    num_internal = n - p
    if num_internal > 0:
        for i in range(1, num_internal + 1):
            knots.append(i / (num_internal + 1))
    knots += [1.0] * (p + 1)
    return KnotVector(knots)


def _basis_function(i: int, k: int, u: float, knots: List[float]) -> float:
    """De Boor-Cox 递推计算 B 样条基函数 N_{i,k}(u)"""
    if i + k + 1 >= len(knots):
        return 0.0
    if k == 0:
        if knots[i] <= u < knots[i + 1] or (u >= 1.0 and i == len(knots) - 2):
            return 1.0
        return 0.0
    result = 0.0
    denom1 = knots[i + k] - knots[i]
    if denom1 > 1e-10:
        result += (u - knots[i]) / denom1 * _basis_function(i, k - 1, u, knots)
    denom2 = knots[i + k + 1] - knots[i + 1]
    if denom2 > 1e-10:
        result += (knots[i + k + 1] - u) / denom2 * _basis_function(i + 1, k - 1, u, knots)
    return result


class NURBSCurve:
    """NURBS曲线"""

    def __init__(self, degree: int = 3,
                 control_points: Optional[List[ControlPoint]] = None,
                 knot_vector: Optional[KnotVector] = None):
        self.degree = degree
        self.control_points = control_points or []
        self.knot_vector = knot_vector or KnotVector([])
        if control_points and not knot_vector:
            self.knot_vector = _create_uniform_knot_vector(len(control_points) - 1, degree)

    def evaluate_point(self, t: float) -> np.ndarray:
        """计算曲线上参数 t 处的点"""
        point = np.zeros(3)
        weight_sum = 0.0
        for i, cp in enumerate(self.control_points):
            basis = _basis_function(i, self.degree, t, self.knot_vector.values)
            w = basis * cp.weight
            point += w * np.array([cp.x, cp.y, cp.z])
            weight_sum += w
        if weight_sum > 1e-10:
            point /= weight_sum
        return point

    def compute_length(self, num_samples: int = 100) -> float:
        """近似计算曲线长度"""
        t_values = np.linspace(0, 1, num_samples)
        prev = self.evaluate_point(t_values[0])
        length = 0.0
        for t in t_values[1:]:
            cur = self.evaluate_point(t)
            length += np.linalg.norm(cur - prev)
            prev = cur
        return length

    def to_dict(self) -> Dict[str, Any]:
        return {
            'degree': self.degree,
            'control_points': [{'x': cp.x, 'y': cp.y, 'z': cp.z, 'weight': cp.weight}
                               for cp in self.control_points],
            'knot_vector': self.knot_vector.values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NURBSCurve':
        cps = [ControlPoint(cp['x'], cp['y'], cp['z'], cp.get('weight', 1.0))
               for cp in data['control_points']]
        return cls(degree=data['degree'], control_points=cps,
                   knot_vector=KnotVector(data['knot_vector']))


class NURBSSurface:
    """NURBS曲面"""

    def __init__(self, degree_u: int = 3, degree_v: int = 3,
                 control_points: Optional[List[List[ControlPoint]]] = None,
                 knot_vector_u: Optional[KnotVector] = None,
                 knot_vector_v: Optional[KnotVector] = None):
        self.degree_u = degree_u
        self.degree_v = degree_v
        self.control_points = control_points or []
        self.knot_vector_u = knot_vector_u or KnotVector([])
        self.knot_vector_v = knot_vector_v or KnotVector([])
        if control_points:
            n = len(self.control_points) - 1
            m = len(self.control_points[0]) - 1 if n >= 0 else 0
            if not self.knot_vector_u.values:
                self.knot_vector_u = _create_uniform_knot_vector(n, self.degree_u)
            if not self.knot_vector_v.values:
                self.knot_vector_v = _create_uniform_knot_vector(m, self.degree_v)

    def evaluate_point(self, u: float, v: float) -> np.ndarray:
        """计算曲面上的点 (u, v)"""
        point = np.zeros(3)
        weight_sum = 0.0
        for i in range(len(self.control_points)):
            bu = _basis_function(i, self.degree_u, u, self.knot_vector_u.values)
            for j in range(len(self.control_points[0])):
                bv = _basis_function(j, self.degree_v, v, self.knot_vector_v.values)
                cp = self.control_points[i][j]
                w = bu * bv * cp.weight
                point += w * np.array([cp.x, cp.y, cp.z])
                weight_sum += w
        if weight_sum > 1e-10:
            point /= weight_sum
        return point

    def evaluate_normal(self, u: float, v: float) -> np.ndarray:
        """计算曲面法向量"""
        eps = 0.001
        du = self.evaluate_point(u + eps, v) - self.evaluate_point(u - eps, v)
        dv = self.evaluate_point(u, v + eps) - self.evaluate_point(u, v - eps)
        normal = np.cross(du, dv)
        norm = np.linalg.norm(normal)
        if norm > 1e-10:
            normal /= norm
        return normal

    def evaluate_curvature(self, u: float, v: float) -> Dict[str, float]:
        """计算曲率"""
        eps = 0.001
        p = self.evaluate_point(u, v)
        puu = (self.evaluate_point(u + eps, v) - 2 * p + self.evaluate_point(u - eps, v)) / (eps ** 2)
        pvv = (self.evaluate_point(u, v + eps) - 2 * p + self.evaluate_point(u, v - eps)) / (eps ** 2)
        normal = self.evaluate_normal(u, v)
        k1 = float(np.dot(puu, normal))
        k2 = float(np.dot(pvv, normal))
        return {
            'gaussian_curvature': k1 * k2,
            'mean_curvature': (k1 + k2) / 2,
            'principal_curvature_1': k1,
            'principal_curvature_2': k2
        }

    def modify_control_point(self, i: int, j: int, new_position: Tuple[float, float, float]):
        if 0 <= i < len(self.control_points) and 0 <= j < len(self.control_points[0]):
            self.control_points[i][j].x, self.control_points[i][j].y, self.control_points[i][j].z = new_position

    def modify_control_point_weight(self, i: int, j: int, new_weight: float):
        if 0 <= i < len(self.control_points) and 0 <= j < len(self.control_points[0]):
            self.control_points[i][j].weight = max(0.01, new_weight)

    def translate(self, dx: float, dy: float, dz: float):
        for row in self.control_points:
            for cp in row:
                cp.x += dx; cp.y += dy; cp.z += dz

    def scale(self, sx: float, sy: float, sz: float, center: Optional[Tuple[float, float, float]] = None):
        cx, cy, cz = center or (0, 0, 0)
        for row in self.control_points:
            for cp in row:
                cp.x = cx + (cp.x - cx) * sx
                cp.y = cy + (cp.y - cy) * sy
                cp.z = cz + (cp.z - cz) * sz

    def rotate(self, angle: float, axis: str = 'z', center: Optional[Tuple[float, float, float]] = None):
        cx, cy, cz = center or (0, 0, 0)
        rad = np.radians(angle)
        c, s = np.cos(rad), np.sin(rad)
        for row in self.control_points:
            for cp in row:
                x, y, z = cp.x - cx, cp.y - cy, cp.z - cz
                if axis == 'z':
                    cp.x, cp.y, cp.z = x * c - y * s + cx, x * s + y * c + cy, z + cz
                elif axis == 'x':
                    cp.x, cp.y, cp.z = x + cx, y * c - z * s + cy, y * s + z * c + cz
                else:
                    cp.x, cp.y, cp.z = x * c + z * s + cx, y + cy, -x * s + z * c + cz

    def to_dict(self) -> Dict[str, Any]:
        return {
            'degree_u': self.degree_u,
            'degree_v': self.degree_v,
            'control_points': [[{'x': cp.x, 'y': cp.y, 'z': cp.z, 'weight': cp.weight}
                                for cp in row] for row in self.control_points],
            'knot_vector_u': self.knot_vector_u.values,
            'knot_vector_v': self.knot_vector_v.values
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NURBSSurface':
        cps = [[ControlPoint(cp['x'], cp['y'], cp['z'], cp.get('weight', 1.0))
                for cp in row] for row in data['control_points']]
        return cls(degree_u=data['degree_u'], degree_v=data['degree_v'],
                   control_points=cps,
                   knot_vector_u=KnotVector(data['knot_vector_u']),
                   knot_vector_v=KnotVector(data['knot_vector_v']))

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'NURBSSurface':
        return cls.from_dict(json.loads(json_str))
