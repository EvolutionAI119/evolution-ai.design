"""模型修改API路由：NURBS曲面管理与参数化修改"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from ..database import ParameterRecord, get_db
from ..nurbs import NURBSSurface, ControlPoint

router = APIRouter(prefix="/api/v1/modify", tags=["模型修改"])

# 全局曲面存储（参数已迁移至数据库 parameter_records 表持久化）
_surfaces: Dict[str, NURBSSurface] = {}
_history: List[Dict[str, Any]] = []


class ControlPointUpdate(BaseModel):
    surface_id: str
    i: int
    j: int
    x: float
    y: float
    z: float
    weight: Optional[float] = 1.0


class SurfaceModification(BaseModel):
    surface_id: str
    operation_type: str  # translate, scale, rotate
    parameters: Dict[str, float]


class NURBSSurfaceCreate(BaseModel):
    degree_u: int = 3
    degree_v: int = 3
    control_points: List[List[Dict[str, float]]]
    surface_id: Optional[str] = None


class ParameterUpdate(BaseModel):
    name: str
    value: float


class DistanceMeasurement(BaseModel):
    point1: Dict[str, float]
    point2: Dict[str, float]
    label: Optional[str] = ""


class AngleMeasurement(BaseModel):
    vertex: Dict[str, float]
    point1: Dict[str, float]
    point2: Dict[str, float]
    label: Optional[str] = ""


# ============ NURBS曲面API ============

@router.post("/surfaces/create")
async def create_surface(data: NURBSSurfaceCreate):
    sid = data.surface_id or f"surface_{len(_surfaces)}"
    cps = [[ControlPoint(cp['x'], cp['y'], cp['z'], cp.get('weight', 1.0))
            for cp in row] for row in data.control_points]
    surf = NURBSSurface(degree_u=data.degree_u, degree_v=data.degree_v, control_points=cps)
    _surfaces[sid] = surf
    return {"success": True, "surface_id": sid, "surface_data": surf.to_dict()}


@router.get("/surfaces/{surface_id}")
async def get_surface(surface_id: str):
    if surface_id not in _surfaces:
        raise HTTPException(status_code=404, detail="Surface not found")
    return {"surface_id": surface_id, "surface_data": _surfaces[surface_id].to_dict()}


@router.post("/surfaces/{surface_id}/modify")
async def modify_surface(surface_id: str, mod: SurfaceModification):
    surf = _surfaces.get(surface_id)
    if not surf:
        raise HTTPException(status_code=404, detail="Surface not found")
    try:
        p = mod.parameters
        if mod.operation_type == "translate":
            surf.translate(p.get("dx", 0), p.get("dy", 0), p.get("dz", 0))
        elif mod.operation_type == "scale":
            surf.scale(p.get("sx", 1), p.get("sy", 1), p.get("sz", 1))
        elif mod.operation_type == "rotate":
            surf.rotate(p.get("angle", 0), p.get("axis", "z"))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {mod.operation_type}")
        _history.append({"surface_id": surface_id, "operation": mod.operation_type, "parameters": p})
        return {"success": True, "surface_id": surface_id, "surface_data": surf.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/surfaces/{surface_id}/control-point")
async def update_control_point(surface_id: str, update: ControlPointUpdate):
    surf = _surfaces.get(surface_id)
    if not surf:
        raise HTTPException(status_code=404, detail="Surface not found")
    surf.modify_control_point(update.i, update.j, (update.x, update.y, update.z))
    if update.weight is not None:
        surf.modify_control_point_weight(update.i, update.j, update.weight)
    return {"success": True, "surface_id": surface_id,
            "control_point": {"i": update.i, "j": update.j,
                              "position": (update.x, update.y, update.z), "weight": update.weight}}


@router.get("/surfaces/{surface_id}/evaluate")
async def evaluate_surface(surface_id: str,
                           u: float = Query(0.5, ge=0, le=1), v: float = Query(0.5, ge=0, le=1)):
    surf = _surfaces.get(surface_id)
    if not surf:
        raise HTTPException(status_code=404, detail="Surface not found")
    return {"surface_id": surface_id, "u": u, "v": v,
            "point": surf.evaluate_point(u, v).tolist(),
            "normal": surf.evaluate_normal(u, v).tolist(),
            "curvature": surf.evaluate_curvature(u, v)}


@router.delete("/surfaces/{surface_id}")
async def delete_surface(surface_id: str):
    if surface_id in _surfaces:
        del _surfaces[surface_id]
        return {"success": True, "message": f"Surface {surface_id} deleted"}
    raise HTTPException(status_code=404, detail="Surface not found")


# ============ 参数API ============

def _upsert_parameter(db: Session, name: str, value: float) -> ParameterRecord:
    """按 name 唯一键 upsert 参数记录并提交"""
    record = (db.query(ParameterRecord)
              .filter(ParameterRecord.name == name).first())
    if record:
        record.value = value
    else:
        record = ParameterRecord(name=name, value=value)
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/parameters")
async def get_parameters(db: Session = Depends(get_db)):
    rows = db.query(ParameterRecord).all()
    return {"parameters": {
        r.name: {"name": r.name, "value": r.value} for r in rows
    }}


@router.post("/parameters/add")
async def add_parameter(data: ParameterUpdate, db: Session = Depends(get_db)):
    record = _upsert_parameter(db, data.name, data.value)
    _history.append({"operation": "add_parameter",
                     "name": data.name, "value": data.value})
    return {"success": True,
            "parameter": {"name": record.name, "value": record.value}}


@router.post("/parameters/update")
async def update_parameter(data: ParameterUpdate, db: Session = Depends(get_db)):
    record = _upsert_parameter(db, data.name, data.value)
    _history.append({"operation": "update_parameter",
                     "name": data.name, "value": data.value})
    return {"success": True,
            "parameter": {"name": record.name, "value": record.value}}


@router.get("/parameters/automotive")
async def get_automotive_parameters():
    from ..car_generator import NURBSCarBodyGenerator
    gen = NURBSCarBodyGenerator()
    return {"parameters": gen.params}


# ============ 测量API ============

@router.post("/measurements/distance")
async def measure_distance(data: DistanceMeasurement):
    import numpy as np
    p1 = np.array([data.point1['x'], data.point1['y'], data.point1['z']])
    p2 = np.array([data.point2['x'], data.point2['y'], data.point2['z']])
    dist = float(np.linalg.norm(p2 - p1))
    return {"measurement": {"type": "distance", "label": data.label,
                            "value": dist, "point1": data.point1, "point2": data.point2}}


@router.post("/measurements/angle")
async def measure_angle(data: AngleMeasurement):
    import numpy as np
    v = np.array([data.vertex['x'], data.vertex['y'], data.vertex['z']])
    p1 = np.array([data.point1['x'], data.point1['y'], data.point1['z']])
    p2 = np.array([data.point2['x'], data.point2['y'], data.point2['z']])
    a, b = p1 - v, p2 - v
    cos_ang = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)
    angle = float(np.degrees(np.arccos(np.clip(cos_ang, -1, 1))))
    return {"measurement": {"type": "angle", "label": data.label, "value": angle}}


@router.get("/measurements/summary")
async def get_measurement_summary():
    return {"total_measurements": 0, "types": ["distance", "angle", "curvature"]}


# ============ 历史记录API ============

@router.get("/history")
async def get_history():
    return {"history": _history}


@router.post("/history/undo")
async def undo_modification():
    if _history:
        _history.pop()
    return {"success": True, "message": "Modification undone"}
