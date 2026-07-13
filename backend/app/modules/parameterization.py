import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
from app.utils.logger import logger


class ParameterType(Enum):
    LENGTH = "长度"
    WIDTH = "宽度"
    HEIGHT = "高度"
    RADIUS = "半径"
    THICKNESS = "厚度"
    ANGLE = "角度"
    DIAMETER = "直径"
    COUNT = "数量"
    BOOLEAN = "布尔"
    STRING = "字符串"


class ParameterLevel(Enum):
    TOP_LEVEL = "整车级"
    SUB_SYSTEM = "子系统级"
    COMPONENT = "部件级"
    DETAIL = "细节级"


class Parameter:
    def __init__(
        self,
        name: str,
        value: Any,
        param_type: str,
        level: str,
        unit: str = "mm",
        description: str = "",
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        parent: Optional[str] = None,
        children: Optional[List[str]] = None
    ):
        self.name = name
        self.value = value
        self.param_type = param_type
        self.level = level
        self.unit = unit
        self.description = description
        self.min_value = min_value
        self.max_value = max_value
        self.parent = parent
        self.children = children or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'type': self.param_type,
            'level': self.level,
            'unit': self.unit,
            'description': self.description,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'parent': self.parent,
            'children': self.children
        }


class ParameterManager:
    def __init__(self, project_id: int = None):
        self.project_id = project_id
        self.parameters: Dict[str, Parameter] = {}
        self.relations: List[Dict] = []
        self._load_default_parameters()

    def _load_default_parameters(self):
        default_params = [
            Parameter("L_Overall_Length", 4800, ParameterType.LENGTH.value, ParameterLevel.TOP_LEVEL.value, "mm", "总长"),
            Parameter("W_Overall_Width", 1800, ParameterType.WIDTH.value, ParameterLevel.TOP_LEVEL.value, "mm", "总宽"),
            Parameter("H_Overall_Height", 1450, ParameterType.HEIGHT.value, ParameterLevel.TOP_LEVEL.value, "mm", "总高"),
            Parameter("W_Wheelbase", 2800, ParameterType.LENGTH.value, ParameterLevel.TOP_LEVEL.value, "mm", "轴距"),
            Parameter("R_Wheel_Front", 1550, ParameterType.WIDTH.value, ParameterLevel.TOP_LEVEL.value, "mm", "前轮距"),
            Parameter("R_Wheel_Rear", 1550, ParameterType.WIDTH.value, ParameterLevel.TOP_LEVEL.value, "mm", "后轮距"),
            Parameter("L_Hood_Length", 1200, ParameterType.LENGTH.value, ParameterLevel.SUB_SYSTEM.value, "mm", "发动机盖长度"),
            Parameter("W_Door_Width", 850, ParameterType.WIDTH.value, ParameterLevel.SUB_SYSTEM.value, "mm", "车门宽度"),
            Parameter("H_Roof_Height", 1200, ParameterType.HEIGHT.value, ParameterLevel.SUB_SYSTEM.value, "mm", "顶棚高度"),
            Parameter("R_Corner_Front", 50, ParameterType.RADIUS.value, ParameterLevel.COMPONENT.value, "mm", "前角半径"),
            Parameter("T_Skin_Thickness", 0.8, ParameterType.THICKNESS.value, ParameterLevel.COMPONENT.value, "mm", "蒙皮厚度"),
            Parameter("A_Draft_Angle", 3, ParameterType.ANGLE.value, ParameterLevel.COMPONENT.value, "°", "拔模角度"),
            Parameter("R_Min_Fillet", 0.8, ParameterType.RADIUS.value, ParameterLevel.COMPONENT.value, "mm", "最小圆角"),
        ]

        for param in default_params:
            self.parameters[param.name] = param

        logger.info(f"Loaded {len(self.parameters)} default parameters")

    def add_parameter(self, param: Parameter):
        self.parameters[param.name] = param
        logger.info(f"Added parameter: {param.name}")

    def get_parameter(self, name: str) -> Optional[Parameter]:
        return self.parameters.get(name)

    def update_parameter(self, name: str, value: Any) -> bool:
        if name in self.parameters:
            param = self.parameters[name]
            if param.min_value is not None and value < param.min_value:
                logger.warning(f"Value {value} below min {param.min_value} for {name}")
                return False
            if param.max_value is not None and value > param.max_value:
                logger.warning(f"Value {value} above max {param.max_value} for {name}")
                return False
            param.value = value
            logger.info(f"Updated parameter: {name} = {value}")
            return True
        return False

    def get_parameters_by_level(self, level: str) -> List[Parameter]:
        return [param for param in self.parameters.values() if param.level == level]

    def add_relation(self, expression: str, description: str = ""):
        relation = {
            'expression': expression,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        self.relations.append(relation)
        logger.info(f"Added relation: {expression}")

    def evaluate_relation(self, expression: str) -> Any:
        try:
            local_vars = {name: param.value for name, param in self.parameters.items()}
            result = eval(expression, {}, local_vars)
            return result
        except Exception as e:
            logger.error(f"Failed to evaluate expression '{expression}': {str(e)}")
            return None

    def validate_parameters(self) -> Dict[str, Any]:
        issues = []
        for name, param in self.parameters.items():
            if param.min_value is not None and param.value < param.min_value:
                issues.append({
                    'parameter': name,
                    'issue': f"Value {param.value} below minimum {param.min_value}",
                    'severity': '高'
                })
            if param.max_value is not None and param.value > param.max_value:
                issues.append({
                    'parameter': name,
                    'issue': f"Value {param.value} above maximum {param.max_value}",
                    'severity': '高'
                })

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'total_parameters': len(self.parameters),
            'valid_parameters': len(self.parameters) - len(issues)
        }

    def export_parameters(self, output_path: str) -> str:
        params_data = {
            'project_id': self.project_id,
            'export_time': datetime.now().isoformat(),
            'parameters': [param.to_dict() for param in self.parameters.values()],
            'relations': self.relations
        }

        output_file = Path(output_path) / "parameters.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(params_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Parameters exported to: {output_file}")
        return str(output_file)

    def import_parameters(self, input_path: str) -> bool:
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for param_data in data.get('parameters', []):
                param = Parameter(
                    name=param_data['name'],
                    value=param_data['value'],
                    param_type=param_data.get('type', '长度'),
                    level=param_data.get('level', '部件级'),
                    unit=param_data.get('unit', 'mm'),
                    description=param_data.get('description', ''),
                    min_value=param_data.get('min_value'),
                    max_value=param_data.get('max_value'),
                    parent=param_data.get('parent'),
                    children=param_data.get('children', [])
                )
                self.parameters[param.name] = param

            self.relations = data.get('relations', [])
            logger.info(f"Imported {len(self.parameters)} parameters")
            return True
        except Exception as e:
            logger.error(f"Failed to import parameters: {str(e)}")
            return False

    def get_param_tree(self) -> Dict[str, Any]:
        tree = {}
        for level in [ParameterLevel.TOP_LEVEL.value, ParameterLevel.SUB_SYSTEM.value,
                      ParameterLevel.COMPONENT.value, ParameterLevel.DETAIL.value]:
            level_params = self.get_parameters_by_level(level)
            if level_params:
                tree[level] = [param.to_dict() for param in level_params]
        return tree