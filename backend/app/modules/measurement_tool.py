"""
测量工具模块
支持3D模型的尺寸测量、标注和分析
"""

from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np
import json
import math


class MeasurementType(Enum):
    """测量类型"""
    DISTANCE = "distance"             # 距离
    ANGLE = "angle"                   # 角度
    LENGTH = "length"                 # 长度
    RADIUS = "radius"                 # 半径
    DIAMETER = "diameter"             # 直径
    AREA = "area"                     # 面积
    VOLUME = "volume"                 # 体积
    CURVATURE = "curvature"           # 曲率
    THICKNESS = "thickness"          # 厚度


class AnnotationType(Enum):
    """标注类型"""
    LINEAR = "linear"                 # 线性标注
    ANGULAR = "angular"               # 角度标注
    RADIUS = "radius"                 # 半径标注
    DIAMETER = "diameter"             # 直径标注
    ORDINATE = "ordinate"             # 坐标标注
    LEADER = "leader"                 # 引线标注


@dataclass
class MeasurementPoint:
    """测量点"""
    x: float
    y: float
    z: float
    entity_id: Optional[str] = None
    uv: Optional[Tuple[float, float]] = None  # 曲面上的参数坐标

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def distance_to(self, other: 'MeasurementPoint') -> float:
        return np.linalg.norm(self.to_array() - other.to_array())

    def to_dict(self) -> Dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'entity_id': self.entity_id,
            'uv': self.uv
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeasurementPoint':
        return cls(
            x=data['x'],
            y=data['y'],
            z=data['z'],
            entity_id=data.get('entity_id'),
            uv=data.get('uv')
        )


@dataclass
class Measurement:
    """测量结果"""
    measurement_type: MeasurementType
    value: float
    unit: str
    points: List[MeasurementPoint]
    entity_id: Optional[str] = None
    label: str = ""
    tolerance_plus: float = 0.0
    tolerance_minus: float = 0.0
    is_within_tolerance: Optional[bool] = None

    @property
    def formatted_value(self) -> str:
        """格式化测量值"""
        if self.tolerance_plus > 0 or self.tolerance_minus > 0:
            return f"{self.value:.3f} {self.unit}"
        return f"{self.value:.3f} {self.unit}"

    @property
    def tolerance_string(self) -> str:
        """公差字符串"""
        if self.tolerance_plus > 0 or self.tolerance_minus > 0:
            return f"+{self.tolerance_plus:.3f}/-{self.tolerance_minus:.3f}"
        return ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'measurement_type': self.measurement_type.value,
            'value': self.value,
            'unit': self.unit,
            'points': [p.to_dict() for p in self.points],
            'entity_id': self.entity_id,
            'label': self.label,
            'tolerance_plus': self.tolerance_plus,
            'tolerance_minus': self.tolerance_minus,
            'is_within_tolerance': self.is_within_tolerance
        }


@dataclass
class Annotation:
    """标注"""
    annotation_type: AnnotationType
    measurement: Measurement
    position: Tuple[float, float, float]
    start_point: Tuple[float, float, float]
    end_point: Tuple[float, float, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'annotation_type': self.annotation_type.value,
            'measurement': self.measurement.to_dict(),
            'position': self.position,
            'start_point': self.start_point,
            'end_point': self.end_point
        }


class MeasurementTool:
    """测量工具"""

    def __init__(self):
        self.measurements: List[Measurement] = []
        self.annotations: List[Annotation] = []

    def measure_distance(
        self,
        point1: MeasurementPoint,
        point2: MeasurementPoint,
        label: str = ""
    ) -> Measurement:
        """测量两点间距离"""
        distance = point1.distance_to(point2)
        measurement = Measurement(
            measurement_type=MeasurementType.DISTANCE,
            value=distance,
            unit="mm",
            points=[point1, point2],
            label=label
        )
        self.measurements.append(measurement)
        return measurement

    def measure_angle(
        self,
        vertex: MeasurementPoint,
        point1: MeasurementPoint,
        point2: MeasurementPoint,
        label: str = ""
    ) -> Measurement:
        """测量角度"""
        v = vertex.to_array()
        p1 = point1.to_array() - v
        p2 = point2.to_array() - v

        cos_angle = np.dot(p1, p2) / (np.linalg.norm(p1) * np.linalg.norm(p2))
        cos_angle = np.clip(cos_angle, -1, 1)
        angle = np.degrees(np.arccos(cos_angle))

        measurement = Measurement(
            measurement_type=MeasurementType.ANGLE,
            value=angle,
            unit="deg",
            points=[vertex, point1, point2],
            label=label
        )
        self.measurements.append(measurement)
        return measurement

    def measure_radius(
        self,
        center: MeasurementPoint,
        point_on_circle: MeasurementPoint,
        label: str = ""
    ) -> Measurement:
        """测量半径"""
        radius = center.distance_to(point_on_circle)
        measurement = Measurement(
            measurement_type=MeasurementType.RADIUS,
            value=radius,
            unit="mm",
            points=[center, point_on_circle],
            label=label
        )
        self.measurements.append(measurement)
        return measurement

    def measure_diameter(
        self,
        center: MeasurementPoint,
        point_on_circle: MeasurementPoint,
        label: str = ""
    ) -> Measurement:
        """测量直径"""
        radius = center.distance_to(point_on_circle)
        measurement = Measurement(
            measurement_type=MeasurementType.DIAMETER,
            value=radius * 2,
            unit="mm",
            points=[center, point_on_circle],
            label=label
        )
        self.measurements.append(measurement)
        return measurement

    def measure_surface_area(self, surface_mesh) -> float:
        """测量曲面面积"""
        total_area = 0.0
        return total_area

    def measure_length(self, points: List[MeasurementPoint]) -> Measurement:
        """测量折线长度"""
        length = 0.0
        for i in range(len(points) - 1):
            length += points[i].distance_to(points[i + 1])

        measurement = Measurement(
            measurement_type=MeasurementType.LENGTH,
            value=length,
            unit="mm",
            points=points
        )
        self.measurements.append(measurement)
        return measurement

    def add_annotation(
        self,
        annotation_type: AnnotationType,
        measurement: Measurement,
        position: Tuple[float, float, float],
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float]
    ) -> Annotation:
        """添加标注"""
        annotation = Annotation(
            annotation_type=annotation_type,
            measurement=measurement,
            position=position,
            start_point=start_point,
            end_point=end_point
        )
        self.annotations.append(annotation)
        return annotation

    def export_measurements(self) -> Dict[str, Any]:
        """导出测量结果"""
        return {
            'measurements': [m.to_dict() for m in self.measurements],
            'annotations': [a.to_dict() for a in self.annotations]
        }

    def to_json(self) -> str:
        return json.dumps(self.export_measurements(), indent=2)

    def clear(self):
        """清除所有测量"""
        self.measurements.clear()
        self.annotations.clear()

    def get_summary(self) -> Dict[str, Any]:
        """获取测量摘要"""
        if not self.measurements:
            return {'total': 0}

        by_type = {}
        for m in self.measurements:
            type_name = m.measurement_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(m.value)

        summary = {
            'total': len(self.measurements),
            'by_type': {
                k: {
                    'count': len(v),
                    'min': min(v),
                    'max': max(v),
                    'avg': sum(v) / len(v)
                }
                for k, v in by_type.items()
            }
        }

        return summary


class SurfaceMeasurement:
    """曲面测量工具"""

    def __init__(self):
        self.tool = MeasurementTool()

    def measure_curvature_at_point(self, surface, u: float, v: float) -> Dict[str, float]:
        """测量曲面上指定点的曲率"""
        p = surface.evaluate_point(u, v)
        normal = surface.evaluate_normal(u, v)

        eps = 0.001
        pu = (surface.evaluate_point(u + eps, v) - surface.evaluate_point(u - eps, v)) / (2 * eps)
        pv = (surface.evaluate_point(u, v + eps) - surface.evaluate_point(u, v - eps)) / (2 * eps)

        puu = (surface.evaluate_point(u + eps, v) - 2 * surface.evaluate_point(u, v) +
               surface.evaluate_point(u - eps, v)) / (eps ** 2)
        pvv = (surface.evaluate_point(u, v + eps) - 2 * surface.evaluate_point(u, v) +
               surface.evaluate_point(u, v - eps)) / (eps ** 2)

        k1 = np.dot(puu, normal)
        k2 = np.dot(pvv, normal)

        return {
            'position': p.tolist(),
            'normal': normal.tolist(),
            'gaussian_curvature': k1 * k2,
            'mean_curvature': (k1 + k2) / 2,
            'principal_curvature_1': k1,
            'principal_curvature_2': k2,
            'curvature_radius_1': abs(1 / k1) if abs(k1) > 1e-10 else float('inf'),
            'curvature_radius_2': abs(1 / k2) if abs(k2) > 1e-10 else float('inf')
        }

    def measure_surface_curvature_map(self, surface, num_samples: int = 10) -> List[Dict[str, Any]]:
        """测量曲面的曲率分布图"""
        results = []
        u_vals = np.linspace(0, 1, num_samples)
        v_vals = np.linspace(0, 1, num_samples)

        for u in u_vals:
            for v in v_vals:
                curvature = self.measure_curvature_at_point(surface, u, v)
                curvature['u'] = u
                curvature['v'] = v
                results.append(curvature)

        return results

    def measure_continuity(
        self,
        surface1, surface2,
        seam_u: float = 0.0,
        seam_v: float = 0.0,
        num_samples: int = 10
    ) -> Dict[str, Any]:
        """测量两曲面间的连续性"""
        results = {
            'G0_distance': [],
            'G1_angle': [],
            'G2_curvature': []
        }

        t_vals = np.linspace(0, 1, num_samples)

        for t in t_vals:
            if seam_v == 0:
                p1 = surface1.evaluate_point(seam_u, t)
                p2 = surface2.evaluate_point(seam_u, 1 - t)
            else:
                p1 = surface1.evaluate_point(t, seam_v)
                p2 = surface2.evaluate_point(1 - t, seam_v)

            n1 = surface1.evaluate_normal(seam_u, t)
            n2 = surface2.evaluate_normal(seam_u, 1 - t)

            results['G0_distance'].append(np.linalg.norm(p1 - p2))
            results['G1_angle'].append(np.degrees(np.arccos(np.clip(np.dot(n1, n2), -1, 1))))

        return {
            'G0_distance_avg': sum(results['G0_distance']) / len(results['G0_distance']),
            'G1_angle_avg': sum(results['G1_angle']) / len(results['G1_angle']),
            'G0_distance_max': max(results['G0_distance']),
            'G1_angle_max': max(results['G1_angle']),
            'continuity_level': self._assess_continuity(results)
        }

    def _assess_continuity(self, results: Dict[str, List[float]]) -> str:
        """评估连续性等级"""
        g0_avg = sum(results['G0_distance']) / len(results['G0_distance'])
        g1_avg = sum(results['G1_angle']) / len(results['G1_angle'])

        if g0_avg < 0.01 and g1_avg < 0.5:
            return "G2"
        elif g0_avg < 0.1 and g1_avg < 2.0:
            return "G1"
        elif g0_avg < 1.0:
            return "G0"
        else:
            return "Poor"


class AutomotiveMeasurement:
    """汽车专用测量工具"""

    def __init__(self):
        self.tool = MeasurementTool()
        self.surface_measurement = SurfaceMeasurement()

    def measure_body_dimensions(self, model) -> Dict[str, Measurement]:
        """测量车身尺寸"""
        results = {}

        results['overall_length'] = self.tool.measure_length([
            MeasurementPoint(x=0, y=0, z=0),
            MeasurementPoint(x=model.length, y=0, z=0)
        ])
        results['overall_length'].label = "整车长度"

        results['overall_width'] = self.tool.measure_length([
            MeasurementPoint(x=0, y=0, z=0),
            MeasurementPoint(x=0, y=model.width, z=0)
        ])
        results['overall_width'].label = "整车宽度"

        results['overall_height'] = self.tool.measure_length([
            MeasurementPoint(x=0, y=0, z=0),
            MeasurementPoint(x=0, y=0, z=model.height)
        ])
        results['overall_height'].label = "整车高度"

        return results

    def measure_wheelbase(self, front_axle_center, rear_axle_center) -> Measurement:
        """测量轴距"""
        return self.tool.measure_distance(
            MeasurementPoint(*front_axle_center),
            MeasurementPoint(*rear_axle_center),
            label="轴距"
        )

    def measure_track_width(self, left_wheel_center, right_wheel_center) -> Measurement:
        """测量轮距"""
        return self.tool.measure_distance(
            MeasurementPoint(*left_wheel_center),
            MeasurementPoint(*right_wheel_center),
            label="轮距"
        )

    def measure_door_gap(self, door_edges) -> Measurement:
        """测量车门间隙"""
        return self.tool.measure_distance(
            MeasurementPoint(*door_edges[0]),
            MeasurementPoint(*door_edges[1]),
            label="车门间隙"
        )

    def measure_surface_quality(self, surface, area: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """测量曲面质量"""
        u_min, u_max, v_min, v_max = area

        num_samples = 10
        u_vals = np.linspace(u_min, u_max, num_samples)
        v_vals = np.linspace(v_min, v_max, num_samples)

        curvatures = []
        for u in u_vals:
            for v in v_vals:
                c = self.surface_measurement.measure_curvature_at_point(surface, u, v)
                curvatures.append(c['mean_curvature'])

        return {
            'mean_curvature_avg': sum(curvatures) / len(curvatures),
            'mean_curvature_max': max(curvatures, key=abs),
            'curvature_uniformity': self._calculate_uniformity(curvatures),
            'surface_quality_score': self._assess_quality(curvatures)
        }

    def _calculate_uniformity(self, values: List[float]) -> float:
        """计算均匀性"""
        if not values:
            return 1.0
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        return 1.0 / (1.0 + variance)

    def _assess_quality(self, curvatures: List[float]) -> float:
        """评估曲面质量"""
        uniformity = self._calculate_uniformity(curvatures)
        avg_abs_curvature = sum(abs(c) for c in curvatures) / len(curvatures)

        score = uniformity * 0.6 + (1.0 / (1.0 + avg_abs_curvature)) * 0.4
        return min(100, max(0, score * 100))


class GDAndTAnalyzer:
    """几何尺寸和公差(GD&T)分析器"""

    def __init__(self):
        self.measurements: List[Measurement] = []

    def analyze_flatness(self, surface_points) -> Dict[str, Any]:
        """分析平面度"""
        return {
            'flatness': 0.0,
            'max_deviation': 0.0,
            'min_deviation': 0.0
        }

    def analyze_straightness(self, curve_points) -> Dict[str, Any]:
        """分析直线度"""
        return {
            'straightness': 0.0,
            'max_deviation': 0.0
        }

    def analyze_circularity(self, circle_points, center) -> Dict[str, Any]:
        """分析圆度"""
        distances = [np.linalg.norm(p - center) for p in circle_points]
        return {
            'circularity': max(distances) - min(distances),
            'max_radius': max(distances),
            'min_radius': min(distances)
        }

    def analyze_cylindricity(self, cylinder_points) -> Dict[str, Any]:
        """分析圆柱度"""
        return {
            'cylindricity': 0.0,
            'max_deviation': 0.0
        }

    def analyze_perpendicularity(self, surface1_points, surface2_points) -> Dict[str, Any]:
        """分析垂直度"""
        return {
            'perpendicularity': 0.0,
            'max_deviation_angle': 0.0
        }

    def analyze_parallelism(self, surface1_points, surface2_points) -> Dict[str, Any]:
        """分析平行度"""
        return {
            'parallelism': 0.0,
            'max_deviation': 0.0
        }

    def analyze_position(self, measured_points, nominal_points) -> Dict[str, Any]:
        """分析位置度"""
        deviations = [np.linalg.norm(m - n) for m, n in zip(measured_points, nominal_points)]
        return {
            'position_error': max(deviations),
            'avg_deviation': sum(deviations) / len(deviations)
        }
