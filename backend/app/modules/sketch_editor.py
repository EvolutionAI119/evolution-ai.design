"""
SKETCH草图编辑器
支持2D草图的创建、编辑和约束
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import math
import json


class ConstraintType(Enum):
    """约束类型"""
    COINCIDENT = "coincident"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    TANGENT = "tangent"
    EQUAL_LENGTH = "equal_length"
    EQUAL_RADIUS = "equal_radius"
    SYMMETRIC = "symmetric"
    FIXED = "fixed"
    DISTANCE = "distance"
    ANGLE = "angle"


class EntityType(Enum):
    """实体类型"""
    POINT = "point"
    LINE = "line"
    ARC = "arc"
    CIRCLE = "circle"
    SPLINE = "spline"


@dataclass
class Point2D:
    """2D点"""
    x: float
    y: float
    id: int = 0

    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {'x': self.x, 'y': self.y, 'id': self.id}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Point2D':
        return cls(data['x'], data['y'], data.get('id', 0))


@dataclass
class Line:
    """直线段"""
    start: Point2D
    end: Point2D
    id: int = 0

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point2D:
        return Point2D(
            (self.start.x + self.end.x) / 2,
            (self.start.y + self.end.y) / 2
        )

    @property
    def angle(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.degrees(math.atan2(dy, dx))

    @property
    def is_horizontal(self) -> bool:
        return abs(self.end.y - self.start.y) < 1e-6

    @property
    def is_vertical(self) -> bool:
        return abs(self.end.x - self.start.x) < 1e-6

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'line',
            'id': self.id,
            'start': self.start.to_dict(),
            'end': self.end.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Line':
        return cls(
            start=Point2D.from_dict(data['start']),
            end=Point2D.from_dict(data['end']),
            id=data['id']
        )


@dataclass
class Arc:
    """圆弧"""
    center: Point2D
    radius: float
    start_angle: float
    end_angle: float
    id: int = 0

    @property
    def start_point(self) -> Point2D:
        rad = math.radians(self.start_angle)
        return Point2D(
            self.center.x + self.radius * math.cos(rad),
            self.center.y + self.radius * math.sin(rad)
        )

    @property
    def end_point(self) -> Point2D:
        rad = math.radians(self.end_angle)
        return Point2D(
            self.center.x + self.radius * math.cos(rad),
            self.center.y + self.radius * math.sin(rad)
        )

    @property
    def arc_length(self) -> float:
        angle_diff = self.end_angle - self.start_angle
        if angle_diff < 0:
            angle_diff += 360
        return math.radians(angle_diff) * self.radius

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'arc',
            'id': self.id,
            'center': self.center.to_dict(),
            'radius': self.radius,
            'start_angle': self.start_angle,
            'end_angle': self.end_angle
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Arc':
        return cls(
            center=Point2D.from_dict(data['center']),
            radius=data['radius'],
            start_angle=data['start_angle'],
            end_angle=data['end_angle'],
            id=data['id']
        )


@dataclass
class Circle:
    """圆"""
    center: Point2D
    radius: float
    id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'circle',
            'id': self.id,
            'center': self.center.to_dict(),
            'radius': self.radius
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Circle':
        return cls(
            center=Point2D.from_dict(data['center']),
            radius=data['radius'],
            id=data['id']
        )


@dataclass
class Constraint:
    """几何约束"""
    type: ConstraintType
    entity_ids: List[int]
    value: Optional[float] = None
    id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'entity_ids': self.entity_ids,
            'value': self.value,
            'id': self.id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Constraint':
        return cls(
            type=ConstraintType(data['type']),
            entity_ids=data['entity_ids'],
            value=data.get('value'),
            id=data['id']
        )


@dataclass
class SketchEntity:
    """草图实体"""
    entity_type: EntityType
    data: Any
    construction: bool = False
    visible: bool = True
    id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'entity_type': self.entity_type.value,
            'construction': self.construction,
            'visible': self.visible,
            'id': self.id
        }
        if hasattr(self.data, 'to_dict'):
            result['data'] = self.data.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SketchEntity':
        entity_type = EntityType(data['entity_type'])
        entity_data = data['data']
        if entity_type == EntityType.LINE:
            loaded_data = Line.from_dict(entity_data)
        elif entity_type == EntityType.ARC:
            loaded_data = Arc.from_dict(entity_data)
        elif entity_type == EntityType.CIRCLE:
            loaded_data = Circle.from_dict(entity_data)
        else:
            loaded_data = entity_data
        return cls(
            entity_type=entity_type,
            data=loaded_data,
            construction=data.get('construction', False),
            visible=data.get('visible', True),
            id=data['id']
        )


class Sketch:
    """草图编辑器"""

    def __init__(self, name: str = "Sketch"):
        self.name = name
        self.entities: List[SketchEntity] = []
        self.constraints: List[Constraint] = []
        self._next_id = 1

    def _get_next_id(self) -> int:
        id = self._next_id
        self._next_id += 1
        return id

    def add_line(self, start: Tuple[float, float], end: Tuple[float, float], construction: bool = False) -> SketchEntity:
        """添加直线"""
        line = Line(
            start=Point2D(start[0], start[1]),
            end=Point2D(end[0], end[1]),
            id=self._get_next_id()
        )
        entity = SketchEntity(
            entity_type=EntityType.LINE,
            data=line,
            construction=construction,
            id=line.id
        )
        self.entities.append(entity)
        return entity

    def add_circle(self, center: Tuple[float, float], radius: float) -> SketchEntity:
        """添加圆"""
        circle = Circle(
            center=Point2D(center[0], center[1]),
            radius=radius,
            id=self._get_next_id()
        )
        entity = SketchEntity(
            entity_type=EntityType.CIRCLE,
            data=circle,
            id=circle.id
        )
        self.entities.append(entity)
        return entity

    def add_arc(self, center: Tuple[float, float], radius: float, start_angle: float, end_angle: float) -> SketchEntity:
        """添加圆弧"""
        arc = Arc(
            center=Point2D(center[0], center[1]),
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            id=self._get_next_id()
        )
        entity = SketchEntity(
            entity_type=EntityType.ARC,
            data=arc,
            id=arc.id
        )
        self.entities.append(entity)
        return entity

    def add_constraint(self, constraint_type: ConstraintType, entity_ids: List[int], value: Optional[float] = None) -> Constraint:
        """添加几何约束"""
        constraint = Constraint(
            type=constraint_type,
            entity_ids=entity_ids,
            value=value,
            id=self._get_next_id()
        )
        self.constraints.append(constraint)
        return constraint

    def get_entity(self, entity_id: int) -> Optional[SketchEntity]:
        """获取实体"""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def remove_entity(self, entity_id: int):
        """删除实体"""
        self.entities = [e for e in self.entities if e.id != entity_id]
        self.constraints = [c for c in self.constraints if entity_id not in c.entity_ids]

    def move_entity(self, entity_id: int, dx: float, dy: float):
        """移动实体"""
        entity = self.get_entity(entity_id)
        if not entity:
            return
        if entity.entity_type == EntityType.LINE:
            line: Line = entity.data
            line.start.x += dx
            line.start.y += dy
            line.end.x += dx
            line.end.y += dy
        elif entity.entity_type == EntityType.CIRCLE:
            circle: Circle = entity.data
            circle.center.x += dx
            circle.center.y += dy
        elif entity.entity_type == EntityType.ARC:
            arc: Arc = entity.data
            arc.center.x += dx
            arc.center.y += dy

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'entities': [e.to_dict() for e in self.entities],
            'constraints': [c.to_dict() for c in self.constraints]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Sketch':
        sketch = cls(name=data['name'])
        sketch.entities = [SketchEntity.from_dict(e) for e in data['entities']]
        sketch.constraints = [Constraint.from_dict(c) for c in data['constraints']]
        sketch._next_id = max([e.id for e in sketch.entities] or [0]) + 1
        return sketch

    @classmethod
    def from_json(cls, json_str: str) -> 'Sketch':
        return cls.from_dict(json.loads(json_str))


class SketchModifier:
    """草图修改工具"""

    def __init__(self, sketch: Sketch):
        self.sketch = sketch

    def scale(self, factor: float, center: Tuple[float, float] = (0, 0)):
        """缩放"""
        cx, cy = center
        for entity in self.sketch.entities:
            if entity.entity_type == EntityType.LINE:
                line: Line = entity.data
                line.start.x = cx + (line.start.x - cx) * factor
                line.start.y = cy + (line.start.y - cy) * factor
                line.end.x = cx + (line.end.x - cx) * factor
                line.end.y = cy + (line.end.y - cy) * factor
            elif entity.entity_type == EntityType.CIRCLE:
                circle: Circle = entity.data
                circle.center.x = cx + (circle.center.x - cx) * factor
                circle.center.y = cy + (circle.center.y - cy) * factor
                circle.radius *= factor
            elif entity.entity_type == EntityType.ARC:
                arc: Arc = entity.data
                arc.center.x = cx + (arc.center.x - cx) * factor
                arc.center.y = cy + (arc.center.y - cy) * factor
                arc.radius *= factor

    def rotate(self, angle_deg: float, center: Tuple[float, float] = (0, 0)):
        """旋转"""
        cx, cy = center
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        for entity in self.sketch.entities:
            if entity.entity_type == EntityType.LINE:
                line: Line = entity.data
                self._rotate_point(line.start, cx, cy, cos_a, sin_a)
                self._rotate_point(line.end, cx, cy, cos_a, sin_a)
            elif entity.entity_type == EntityType.CIRCLE:
                circle: Circle = entity.data
                self._rotate_point(circle.center, cx, cy, cos_a, sin_a)
            elif entity.entity_type == EntityType.ARC:
                arc: Arc = entity.data
                self._rotate_point(arc.center, cx, cy, cos_a, sin_a)
                arc.start_angle += angle_deg
                arc.end_angle += angle_deg

    def _rotate_point(self, point: Point2D, cx: float, cy: float, cos_a: float, sin_a: float):
        """旋转点"""
        x, y = point.x - cx, point.y - cy
        point.x = cx + x * cos_a - y * sin_a
        point.y = cy + x * sin_a + y * cos_a

    def translate(self, dx: float, dy: float):
        """平移"""
        for entity in self.sketch.entities:
            if entity.entity_type == EntityType.LINE:
                line: Line = entity.data
                line.start.x += dx
                line.start.y += dy
                line.end.x += dx
                line.end.y += dy
            elif entity.entity_type == EntityType.CIRCLE:
                circle: Circle = entity.data
                circle.center.x += dx
                circle.center.y += dy
            elif entity.entity_type == EntityType.ARC:
                arc: Arc = entity.data
                arc.center.x += dx
                arc.center.y += dy
