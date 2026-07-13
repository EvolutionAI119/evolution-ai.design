"""
模型修改API路由
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from ..modules.nurbs_engine import NURBSSurface, NURBSCurve, ControlPoint, KnotVector
from ..modules.sketch_editor import Sketch, ConstraintType, EntityType
from ..modules.parametric_modifier import (
    ParametricModifier, AutomotiveParameterLibrary, ModificationType, ParameterType
)
from ..modules.measurement_tool import (
    MeasurementTool, SurfaceMeasurement, AutomotiveMeasurement,
    MeasurementPoint, MeasurementType, AnnotationType
)


router = APIRouter(prefix="/api/v1/modify", tags=["模型修改"])

# 全局修改引擎实例
modifier_engine = ParametricModifier()


# ============ 请求模型 ============

class ControlPointUpdate(BaseModel):
    """控制点更新"""
    surface_id: str
    i: int
    j: int
    x: float
    y: float
    z: float
    weight: Optional[float] = 1.0


class SurfaceModification(BaseModel):
    """曲面修改"""
    surface_id: str
    operation_type: str  # translate, scale, rotate, offset
    parameters: Dict[str, float]


class SketchModification(BaseModel):
    """草图修改"""
    sketch_id: str
    entity_id: int
    operation_type: str
    parameters: Dict[str, float]


class ParameterUpdate(BaseModel):
    """参数更新"""
    name: str
    value: float


class ParameterDrive(BaseModel):
    """参数驱动"""
    parameter_name: str
    target_entity: str
    scale_factor: Optional[float] = 1.0
    offset: Optional[float] = 0.0


class DistanceMeasurement(BaseModel):
    """距离测量"""
    point1: Dict[str, float]
    point2: Dict[str, float]
    label: Optional[str] = ""


class AngleMeasurement(BaseModel):
    """角度测量"""
    vertex: Dict[str, float]
    point1: Dict[str, float]
    point2: Dict[str, float]
    label: Optional[str] = ""


class CurvatureMeasurement(BaseModel):
    """曲率测量"""
    surface_id: str
    u: float
    v: float


class NURBSSurfaceCreate(BaseModel):
    """创建NURBS曲面"""
    degree_u: int = 3
    degree_v: int = 3
    control_points: List[List[Dict[str, float]]]
    surface_id: Optional[str] = None


class NURBSSurfaceUpdate(BaseModel):
    """更新NURBS曲面"""
    surface_id: str
    degree_u: Optional[int] = None
    degree_v: Optional[int] = None
    control_points: Optional[List[List[Dict[str, float]]]] = None


class SketchCreate(BaseModel):
    """创建草图"""
    name: str = "Sketch"
    sketch_id: Optional[str] = None


class SketchEntityAdd(BaseModel):
    """添加草图实体"""
    sketch_id: str
    entity_type: str  # line, circle, arc
    data: Dict[str, Any]


class SketchConstraintAdd(BaseModel):
    """添加草图约束"""
    sketch_id: str
    constraint_type: str
    entity_ids: List[int]
    value: Optional[float] = None


# ============ NURBS曲面API ============

@router.post("/surfaces/create")
async def create_nurbs_surface(data: NURBSSurfaceCreate):
    """创建NURBS曲面"""
    surface_id = data.surface_id or f"surface_{len(modifier_engine.surfaces)}"

    control_points = [
        [
            ControlPoint(cp['x'], cp['y'], cp['z'], cp.get('weight', 1.0))
            for cp in row
        ]
        for row in data.control_points
    ]

    surface = NURBSSurface(
        degree_u=data.degree_u,
        degree_v=data.degree_v,
        control_points=control_points
    )

    modifier_engine.add_surface(surface_id, surface)

    return {
        "success": True,
        "surface_id": surface_id,
        "surface_data": surface.to_dict()
    }


@router.get("/surfaces/{surface_id}")
async def get_surface(surface_id: str):
    """获取曲面信息"""
    if surface_id not in modifier_engine.surfaces:
        raise HTTPException(status_code=404, detail="Surface not found")

    surface = modifier_engine.surfaces[surface_id]
    return {
        "surface_id": surface_id,
        "surface_data": surface.to_dict()
    }


@router.post("/surfaces/{surface_id}/modify")
async def modify_surface(surface_id: str, modification: SurfaceModification):
    """修改曲面"""
    try:
        op_type = ModificationType(modification.operation_type)
        from ..modules.parametric_modifier import ModificationOperation
        operation = ModificationOperation(
            operation_type=op_type,
            parameters=modification.parameters
        )

        surface = modifier_engine.modify_surface(surface_id, operation)

        return {
            "success": True,
            "surface_id": surface_id,
            "surface_data": surface.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/surfaces/{surface_id}/control-point")
async def update_control_point(surface_id: str, update: ControlPointUpdate):
    """更新控制点"""
    modifier_engine.modify_control_point(
        surface_id,
        update.i,
        update.j,
        (update.x, update.y, update.z)
    )

    if update.weight is not None:
        modifier_engine.modify_control_point_weight(
            surface_id,
            update.i,
            update.j,
            update.weight
        )

    return {
        "success": True,
        "surface_id": surface_id,
        "control_point": {
            "i": update.i,
            "j": update.j,
            "position": (update.x, update.y, update.z),
            "weight": update.weight
        }
    }


@router.get("/surfaces/{surface_id}/evaluate")
async def evaluate_surface(
    surface_id: str,
    u: float = Query(0.5, ge=0, le=1),
    v: float = Query(0.5, ge=0, le=1)
):
    """评估曲面上的点"""
    if surface_id not in modifier_engine.surfaces:
        raise HTTPException(status_code=404, detail="Surface not found")

    surface = modifier_engine.surfaces[surface_id]
    point = surface.evaluate_point(u, v)
    normal = surface.evaluate_normal(u, v)
    curvature = surface.evaluate_curvature(u, v)

    return {
        "surface_id": surface_id,
        "u": u,
        "v": v,
        "point": point.tolist(),
        "normal": normal.tolist(),
        "curvature": curvature
    }


@router.delete("/surfaces/{surface_id}")
async def delete_surface(surface_id: str):
    """删除曲面"""
    if surface_id in modifier_engine.surfaces:
        del modifier_engine.surfaces[surface_id]
        return {"success": True, "message": f"Surface {surface_id} deleted"}
    raise HTTPException(status_code=404, detail="Surface not found")


# ============ 草图API ============

@router.post("/sketches/create")
async def create_sketch(data: SketchCreate):
    """创建草图"""
    sketch_id = data.sketch_id or f"sketch_{len(modifier_engine.sketches)}"
    sketch = Sketch(name=data.name)
    modifier_engine.add_sketch(sketch_id, sketch)

    return {
        "success": True,
        "sketch_id": sketch_id,
        "sketch_data": sketch.to_dict()
    }


@router.get("/sketches/{sketch_id}")
async def get_sketch(sketch_id: str):
    """获取草图信息"""
    if sketch_id not in modifier_engine.sketches:
        raise HTTPException(status_code=404, detail="Sketch not found")

    sketch = modifier_engine.sketches[sketch_id]
    return {
        "sketch_id": sketch_id,
        "sketch_data": sketch.to_dict()
    }


@router.post("/sketches/{sketch_id}/entities")
async def add_sketch_entity(sketch_id: str, entity_data: SketchEntityAdd):
    """添加草图实体"""
    if sketch_id not in modifier_engine.sketches:
        raise HTTPException(status_code=404, detail="Sketch not found")

    sketch = modifier_engine.sketches[sketch_id]

    if entity_data.entity_type == "line":
        entity = sketch.add_line(
            (entity_data.data['start']['x'], entity_data.data['start']['y']),
            (entity_data.data['end']['x'], entity_data.data['end']['y']),
            entity_data.data.get('construction', False)
        )
    elif entity_data.entity_type == "circle":
        entity = sketch.add_circle(
            (entity_data.data['center']['x'], entity_data.data['center']['y']),
            entity_data.data['radius']
        )
    elif entity_data.entity_type == "arc":
        entity = sketch.add_arc(
            (entity_data.data['center']['x'], entity_data.data['center']['y']),
            entity_data.data['radius'],
            entity_data.data['start_angle'],
            entity_data.data['end_angle']
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported entity type")

    return {
        "success": True,
        "entity": entity.to_dict()
    }


@router.post("/sketches/{sketch_id}/constraints")
async def add_sketch_constraint(sketch_id: str, constraint_data: SketchConstraintAdd):
    """添加草图约束"""
    if sketch_id not in modifier_engine.sketches:
        raise HTTPException(status_code=404, detail="Sketch not found")

    sketch = modifier_engine.sketches[sketch_id]
    constraint_type = ConstraintType(constraint_data.constraint_type)

    constraint = sketch.add_constraint(
        constraint_type,
        constraint_data.entity_ids,
        constraint_data.value
    )

    return {
        "success": True,
        "constraint": constraint.to_dict()
    }


@router.post("/sketches/{sketch_id}/modify")
async def modify_sketch(sketch_id: str, modification: SketchModification):
    """修改草图"""
    from ..modules.parametric_modifier import ModificationOperation

    op_type = ModificationType(modification.operation_type)
    operation = ModificationOperation(
        operation_type=op_type,
        parameters=modification.parameters,
        target_entity_id=str(modification.entity_id)
    )

    modifier_engine.modify_sketch(sketch_id, modification.entity_id, operation)

    return {
        "success": True,
        "sketch_id": sketch_id
    }


# ============ 参数API ============

@router.get("/parameters")
async def get_parameters():
    """获取所有参数"""
    return {
        "parameters": {
            k: v.to_dict()
            for k, v in modifier_engine.parameters.items()
        }
    }


@router.post("/parameters/add")
async def add_parameter(data: Dict[str, Any]):
    """添加参数"""
    from ..modules.parametric_modifier import Parameter

    param = Parameter(
        name=data['name'],
        value=data['value'],
        unit=data['unit'],
        param_type=ParameterType(data['type']),
        min_value=data.get('min_value', 0),
        max_value=data.get('max_value', 10000),
        description=data.get('description', '')
    )

    modifier_engine.add_parameter(param)

    return {
        "success": True,
        "parameter": param.to_dict()
    }


@router.post("/parameters/update")
async def update_parameter(data: ParameterUpdate):
    """更新参数值"""
    modifier_engine.set_parameter(data.name, data.value)
    param = modifier_engine.get_parameter(data.name)

    if param:
        return {
            "success": True,
            "parameter": param.to_dict()
        }
    raise HTTPException(status_code=404, detail="Parameter not found")


@router.post("/parameters/drive")
async def drive_with_parameter(data: ParameterDrive):
    """参数驱动"""
    modifier_engine.apply_parameter_drive(
        data.parameter_name,
        data.target_entity,
        {
            'scale_factor': data.scale_factor,
            'offset': data.offset
        }
    )

    return {
        "success": True,
        "message": f"Parameter {data.parameter_name} applied to {data.target_entity}"
    }


@router.get("/parameters/automotive")
async def get_automotive_parameters():
    """获取汽车标准参数"""
    lib = AutomotiveParameterLibrary()
    params = lib.get_automotive_parameters()

    return {
        "parameters": {
            k: v.to_dict()
            for k, v in params.items()
        }
    }


@router.post("/parameters/automotive/apply")
async def apply_automotive_parameter(param_name: str, value: float):
    """应用汽车参数"""
    lib = AutomotiveParameterLibrary()
    params = lib.get_automotive_parameters()

    if param_name not in params:
        raise HTTPException(status_code=404, detail="Parameter not found")

    modifier_engine.set_parameter(param_name, value)

    return {
        "success": True,
        "parameter": params[param_name].to_dict(),
        "applied_value": value
    }


# ============ 测量API ============

@router.post("/measurements/distance")
async def measure_distance(data: DistanceMeasurement):
    """测量距离"""
    tool = MeasurementTool()

    point1 = MeasurementPoint(
        data.point1['x'],
        data.point1['y'],
        data.point1['z']
    )
    point2 = MeasurementPoint(
        data.point2['x'],
        data.point2['y'],
        data.point2['z']
    )

    measurement = tool.measure_distance(point1, point2, data.label)

    return {
        "measurement": measurement.to_dict()
    }


@router.post("/measurements/angle")
async def measure_angle(data: AngleMeasurement):
    """测量角度"""
    tool = MeasurementTool()

    vertex = MeasurementPoint(
        data.vertex['x'],
        data.vertex['y'],
        data.vertex['z']
    )
    point1 = MeasurementPoint(
        data.point1['x'],
        data.point1['y'],
        data.point1['z']
    )
    point2 = MeasurementPoint(
        data.point2['x'],
        data.point2['y'],
        data.point2['z']
    )

    measurement = tool.measure_angle(vertex, point1, point2, data.label)

    return {
        "measurement": measurement.to_dict()
    }


@router.post("/measurements/curvature")
async def measure_curvature(data: CurvatureMeasurement):
    """测量曲面曲率"""
    if data.surface_id not in modifier_engine.surfaces:
        raise HTTPException(status_code=404, detail="Surface not found")

    surface = modifier_engine.surfaces[data.surface_id]
    sm = SurfaceMeasurement()

    curvature = sm.measure_curvature_at_point(surface, data.u, data.v)

    return {
        "surface_id": data.surface_id,
        "u": data.u,
        "v": data.v,
        "curvature": curvature
    }


@router.get("/measurements/summary")
async def get_measurement_summary():
    """获取测量摘要"""
    tool = MeasurementTool()
    return tool.get_summary()


# ============ 历史记录API ============

@router.get("/history")
async def get_history():
    """获取修改历史"""
    return {
        "history": [op.to_dict() for op in modifier_engine.history]
    }


@router.post("/history/undo")
async def undo_modification():
    """撤销修改"""
    modifier_engine.undo()
    return {
        "success": True,
        "message": "Modification undone"
    }


@router.post("/export")
async def export_state():
    """导出修改器状态"""
    return modifier_engine.export_parameters()


