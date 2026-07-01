"""
参数化修改引擎
支持汽车A级曲面的参数化修改和驱动
"""

from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import numpy as np

# 支持相对导入和绝对导入
try:
    from .nurbs_engine import NURBSSurface, NURBSCurve, SurfaceModifier, CurveModifier, ControlPoint
    from .sketch_editor import Sketch, SketchModifier, Point2D, Line, Circle, Arc
except ImportError:
    from nurbs_engine import NURBSSurface, NURBSCurve, SurfaceModifier, CurveModifier, ControlPoint
    from sketch_editor import Sketch, SketchModifier, Point2D, Line, Circle, Arc


class ParameterType(Enum):
    """参数类型"""
    LENGTH = "length"                 # 长度
    WIDTH = "width"                    # 宽度
    HEIGHT = "height"                  # 高度
    RADIUS = "radius"                  # 半径
    DIAMETER = "diameter"              # 直径
    ANGLE = "angle"                    # 角度
    DISTANCE = "distance"              # 距离
    SCALE = "scale"                   # 比例
    POSITION = "position"              # 位置
    CURVATURE = "curvature"            # 曲率
    TOLERANCE = "tolerance"            # 公差


class ModificationType(Enum):
    """修改类型"""
    TRANSLATE = "translate"            # 平移
    ROTATE = "rotate"                 # 旋转
    SCALE = "scale"                   # 缩放
    OFFSET = "offset"                 # 偏移
    TRIM = "trim"                     # 裁剪
    EXTEND = "extend"                 # 延伸
    FILLET = "fillet"                 # 圆角
    CHAMFER = "chamfer"               # 倒角
    BLEND = "blend"                   # 混合
    MOVE_CONTROL_POINT = "move_cp"    # 移动控制点


@dataclass
class Parameter:
    """参数定义"""
    name: str
    value: float
    unit: str
    param_type: ParameterType
    min_value: float = 0.0
    max_value: float = 10000.0
    description: str = ""
    default_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'type': self.param_type.value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'description': self.description,
            'default_value': self.default_value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Parameter':
        return cls(
            name=data['name'],
            value=data['value'],
            unit=data['unit'],
            param_type=ParameterType(data['type']),
            min_value=data.get('min_value', 0.0),
            max_value=data.get('max_value', 10000.0),
            description=data.get('description', ''),
            default_value=data.get('default_value', data['value'])
        )


@dataclass
class ModificationOperation:
    """修改操作"""
    operation_type: ModificationType
    parameters: Dict[str, float]
    target_entity_id: Optional[str] = None
    target_region: Optional[str] = None  # "local" or "global"
    constraint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation_type': self.operation_type.value,
            'parameters': self.parameters,
            'target_entity_id': self.target_entity_id,
            'target_region': self.target_region,
            'constraint': self.constraint
        }


@dataclass
class AutomotiveParameter(Parameter):
    """汽车专用参数"""
    category: str = ""  # "body", "chassis", "interior", "exterior"
    regulation: Optional[str] = None  # 法规要求
    target_value: Optional[float] = None
    tolerance_plus: float = 0.0
    tolerance_minus: float = 0.0


class AutomotiveParameterLibrary:
    """汽车参数库"""

    # 整车参数
    OVERALL_LENGTH = "overall_length"
    OVERALL_WIDTH = "overall_width"
    OVERALL_HEIGHT = "overall_height"
    WHEELBASE = "wheelbase"
    TRACK_WIDTH = "track_width"
    GROUND_CLEARANCE = "ground_clearance"

    # 车身参数
    HOOD_LENGTH = "hood_length"
    HOOD_ANGLE = "hood_angle"
    WINDSHIELD_ANGLE = "windshield_angle"
    ROOF_HEIGHT = "roof_height"
    REAR_ANGLE = "rear_angle"
    BODY_WIDTH = "body_width"

    # 车轮参数
    WHEEL_DIAMETER = "wheel_diameter"
    WHEEL_WIDTH = "wheel_width"
    TIRE_WIDTH = "tire_width"
    TIRE_ASPECT = "tire_aspect"

    # 内饰参数
    CABIN_LENGTH = "cabin_length"
    SEAT_WIDTH = "seat_width"
    DASHBOARD_DEPTH = "dashboard_depth"

    @classmethod
    def get_automotive_parameters(cls) -> Dict[str, AutomotiveParameter]:
        """获取标准汽车参数"""
        return {
            # 整车尺寸
            cls.OVERALL_LENGTH: AutomotiveParameter(
                name="整车长度",
                value=4800,
                unit="mm",
                param_type=ParameterType.LENGTH,
                min_value=3000,
                max_value=6000,
                description="车辆前后最远点之间的距离",
                category="body",
                target_value=4800,
                tolerance_plus=10,
                tolerance_minus=10
            ),
            cls.OVERALL_WIDTH: AutomotiveParameter(
                name="整车宽度",
                value=1850,
                unit="mm",
                param_type=ParameterType.WIDTH,
                min_value=1500,
                max_value=2200,
                description="车身两侧最外平面之间的距离",
                category="body",
                target_value=1850,
                tolerance_plus=5,
                tolerance_minus=5
            ),
            cls.OVERALL_HEIGHT: AutomotiveParameter(
                name="整车高度",
                value=1450,
                unit="mm",
                param_type=ParameterType.HEIGHT,
                min_value=1200,
                max_value=2000,
                description="车身最高点与地面之间的距离",
                category="body",
                target_value=1450,
                tolerance_plus=5,
                tolerance_minus=5
            ),
            cls.WHEELBASE: AutomotiveParameter(
                name="轴距",
                value=2800,
                unit="mm",
                param_type=ParameterType.LENGTH,
                min_value=2000,
                max_value=4000,
                description="前轴中心到后轴中心的距离",
                category="chassis",
                target_value=2800,
                tolerance_plus=5,
                tolerance_minus=5
            ),
            cls.TRACK_WIDTH: AutomotiveParameter(
                name="轮距",
                value=1600,
                unit="mm",
                param_type=ParameterType.WIDTH,
                min_value=1400,
                max_value=1800,
                description="同一轴上左右车轮中心之间的距离",
                category="chassis",
                target_value=1600,
                tolerance_plus=3,
                tolerance_minus=3
            ),
            cls.GROUND_CLEARANCE: AutomotiveParameter(
                name="离地间隙",
                value=150,
                unit="mm",
                param_type=ParameterType.DISTANCE,
                min_value=100,
                max_value=300,
                description="车辆最低点与地面之间的距离",
                category="chassis",
                regulation="GB/T 12534"
            ),

            # 车身造型参数
            cls.HOOD_ANGLE: AutomotiveParameter(
                name="发动机盖角度",
                value=15,
                unit="deg",
                param_type=ParameterType.ANGLE,
                min_value=5,
                max_value=35,
                description="发动机盖与水平面的夹角",
                category="exterior"
            ),
            cls.WINDSHIELD_ANGLE: AutomotiveParameter(
                name="前风挡角度",
                value=65,
                unit="deg",
                param_type=ParameterType.ANGLE,
                min_value=55,
                max_value=75,
                description="前风挡玻璃与垂直面的夹角",
                category="exterior",
                regulation="GB 11562"
            ),
            cls.ROOF_HEIGHT: AutomotiveParameter(
                name="车顶高度",
                value=1300,
                unit="mm",
                param_type=ParameterType.HEIGHT,
                min_value=1100,
                max_value=1600,
                description="从地面到车顶最高点的距离",
                category="body"
            ),
            cls.REAR_ANGLE: AutomotiveParameter(
                name="后风挡角度",
                value=25,
                unit="deg",
                param_type=ParameterType.ANGLE,
                min_value=15,
                max_value=40,
                description="后风挡玻璃的倾斜角度",
                category="exterior"
            ),

            # 车轮参数
            cls.WHEEL_DIAMETER: AutomotiveParameter(
                name="轮毂直径",
                value=450,
                unit="mm",
                param_type=ParameterType.DIAMETER,
                min_value=350,
                max_value=600,
                description="轮毂的标称直径",
                category="chassis"
            ),
            cls.TIRE_WIDTH: AutomotiveParameter(
                name="轮胎宽度",
                value=225,
                unit="mm",
                param_type=ParameterType.WIDTH,
                min_value=185,
                max_value=355,
                description="轮胎的断面宽度",
                category="chassis"
            ),
        }


class ParametricModifier:
    """参数化修改引擎"""

    def __init__(self):
        self.parameters: Dict[str, Parameter] = {}
        self.history: List[ModificationOperation] = []
        self.surfaces: Dict[str, NURBSSurface] = {}
        self.curves: Dict[str, NURBSCurve] = {}
        self.sketches: Dict[str, Sketch] = {}
        self.listeners: List[Callable] = []

    def add_parameter(self, param: Parameter):
        """添加参数"""
        self.parameters[param.name] = param
        self._notify_change()

    def set_parameter(self, name: str, value: float):
        """设置参数值"""
        if name in self.parameters:
            param = self.parameters[name]
            param.value = max(param.min_value, min(param.max_value, value))
            self._notify_change()

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """获取参数"""
        return self.parameters.get(name)

    def add_surface(self, surface_id: str, surface: NURBSSurface):
        """添加曲面"""
        self.surfaces[surface_id] = surface

    def add_curve(self, curve_id: str, curve: NURBSCurve):
        """添加曲线"""
        self.curves[curve_id] = curve

    def add_sketch(self, sketch_id: str, sketch: Sketch):
        """添加草图"""
        self.sketches[sketch_id] = sketch

    def modify_surface(
        self,
        surface_id: str,
        operation: ModificationOperation
    ) -> NURBSSurface:
        """修改曲面"""
        if surface_id not in self.surfaces:
            raise ValueError(f"Surface {surface_id} not found")

        surface = self.surfaces[surface_id]
        modifier = SurfaceModifier(surface)

        op_type = operation.operation_type
        params = operation.parameters

        if op_type == ModificationType.TRANSLATE:
            dx = params.get('dx', 0)
            dy = params.get('dy', 0)
            dz = params.get('dz', 0)
            modifier.translate(dx, dy, dz)

        elif op_type == ModificationType.SCALE:
            sx = params.get('sx', 1)
            sy = params.get('sy', 1)
            sz = params.get('sz', 1)
            center = params.get('center', None)
            modifier.scale(sx, sy, sz, center)

        elif op_type == ModificationType.ROTATE:
            angle = params.get('angle', 0)
            axis = params.get('axis', 'z')
            center = params.get('center', None)
            modifier.rotate(angle, axis, center)

        elif op_type == ModificationType.OFFSET:
            distance = params.get('distance', 0)
            modifier.offset(distance)

        self.history.append(operation)
        self._notify_change()

        return surface

    def modify_control_point(
        self,
        surface_id: str,
        i: int,
        j: int,
        new_position: Tuple[float, float, float]
    ):
        """修改控制点"""
        if surface_id not in self.surfaces:
            raise ValueError(f"Surface {surface_id} not found")

        surface = self.surfaces[surface_id]
        surface.modify_control_point(i, j, new_position)
        self._notify_change()

    def modify_control_point_weight(
        self,
        surface_id: str,
        i: int,
        j: int,
        new_weight: float
    ):
        """修改控制点权重"""
        if surface_id not in self.surfaces:
            raise ValueError(f"Surface {surface_id} not found")

        surface = self.surfaces[surface_id]
        surface.modify_control_point_weight(i, j, new_weight)
        self._notify_change()

    def modify_sketch(
        self,
        sketch_id: str,
        entity_id: int,
        operation: ModificationOperation
    ):
        """修改草图"""
        if sketch_id not in self.sketches:
            raise ValueError(f"Sketch {sketch_id} not found")

        sketch = self.sketches[sketch_id]
        modifier = SketchModifier(sketch)

        op_type = operation.operation_type
        params = operation.parameters

        if op_type == ModificationType.TRANSLATE:
            dx = params.get('dx', 0)
            dy = params.get('dy', 0)
            modifier.translate(dx, dy)

        elif op_type == ModificationType.SCALE:
            factor = params.get('factor', 1)
            center = params.get('center', (0, 0))
            modifier.scale(factor, center)

        elif op_type == ModificationType.ROTATE:
            angle = params.get('angle', 0)
            center = params.get('center', (0, 0))
            modifier.rotate(angle, center)

        self._notify_change()

    def apply_parameter_drive(self, param_name: str, target_entity: str, mapping: Dict[str, Any]):
        """应用参数驱动"""
        if param_name not in self.parameters:
            return

        param = self.parameters[param_name]
        value = param.value

        if target_entity in self.surfaces:
            surface = self.surfaces[target_entity]
            if 'scale_factor' in mapping:
                scale = value * mapping['scale_factor']
                modifier = SurfaceModifier(surface)
                modifier.scale(scale, scale, scale)
            elif 'offset' in mapping:
                offset = value * mapping['offset']
                modifier = SurfaceModifier(surface)
                modifier.translate(offset, offset, offset)

        self._notify_change()

    def add_change_listener(self, listener: Callable):
        """添加变更监听器"""
        self.listeners.append(listener)

    def _notify_change(self):
        """通知变更"""
        for listener in self.listeners:
            listener(self)

    def undo(self):
        """撤销"""
        if self.history:
            self.history.pop()
            self._notify_change()

    def export_parameters(self) -> Dict[str, Any]:
        """导出参数"""
        return {
            'parameters': {k: v.to_dict() for k, v in self.parameters.items()},
            'history': [op.to_dict() for op in self.history]
        }

    def to_json(self) -> str:
        """导出为JSON"""
        return json.dumps(self.export_parameters(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ParametricModifier':
        """从JSON加载"""
        data = json.loads(json_str)
        modifier = cls()
        for name, param_data in data.get('parameters', {}).items():
            modifier.add_parameter(Parameter.from_dict(param_data))
        return modifier


class ModelModifier:
    """模型整体/局部修改引擎"""

    def __init__(self):
        self.modifier = ParametricModifier()
        self.selection: Dict[str, List[str]] = {}  # 区域选择

    def select_region(self, region_id: str, entity_ids: List[str]):
        """选择区域"""
        self.selection[region_id] = entity_ids

    def clear_selection(self):
        """清除选择"""
        self.selection.clear()

    def modify_region(
        self,
        region_id: str,
        operation: ModificationOperation
    ):
        """修改选定区域"""
        if region_id not in self.selection:
            return

        for entity_id in self.selection[region_id]:
            if entity_id in self.modifier.surfaces:
                self.modifier.modify_surface(entity_id, operation)

    def modify_global(
        self,
        operation: ModificationOperation
    ):
        """全局修改"""
        for surface_id in self.modifier.surfaces:
            self.modifier.modify_surface(surface_id, operation)

    def continuous_modify(
        self,
        entity_id: str,
        modification_func: Callable[[float], Tuple[float, float, float]]
    ):
        """持续修改（用于拖拽等连续操作）"""
        if entity_id not in self.modifier.surfaces:
            return

        surface = self.modifier.surfaces[entity_id]
        for i in range(len(surface.control_points)):
            for j in range(len(surface.control_points[0])):
                cp = surface.control_points[i][j]
                new_pos = modification_func(cp.value if hasattr(cp, 'value') else 0)
                cp.x, cp.y, cp.z = new_pos

        self.modifier._notify_change()
