"""车身生成API路由"""
import time
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ..car_generator import NURBSCarBodyGenerator as CarBodyGenerator
from ..schemas import (CarGenerateRequest, CarComponentGenerateRequest,
                       CarComponentResponse, CarCompleteResponse)

router = APIRouter(prefix="/api/v1/car", tags=["车身生成"])

# 全局生成器实例（懒加载）
_generator: CarBodyGenerator = None


def _get_generator() -> CarBodyGenerator:
    global _generator
    if _generator is None:
        _generator = CarBodyGenerator()
    return _generator


# 无需 side/position 参数的部件
_SIMPLE_COMPONENTS = {
    "hood": "generate_hood", "windshield": "generate_windshield",
    "roof": "generate_roof", "rear_window": "generate_rear_window",
    "trunk": "generate_trunk", "bumper_front": "generate_bumper_front",
    "bumper_rear": "generate_bumper_rear", "grille": "generate_grille",
    "door_seam": "generate_door_seam",
}
# 需要 side 参数的部件
_SIDE_COMPONENTS = {
    "door_front": "generate_door_front", "door_rear": "generate_door_rear",
    "headlight": "generate_headlight", "taillight": "generate_taillight",
    "mirror": "generate_mirror",
}
# 需要 position + side 参数的部件
_POSITION_SIDE_COMPONENTS = {"wheel": "generate_wheel", "fender": "generate_fender"}

ALL_COMPONENTS = (list(_SIMPLE_COMPONENTS) + list(_SIDE_COMPONENTS)
                  + list(_POSITION_SIDE_COMPONENTS) + ["pillar"])


@router.post("/generate", response_model=CarCompleteResponse)
async def generate_complete_car(request: CarGenerateRequest):
    """生成完整车身模型"""
    try:
        start = time.time()
        car = _get_generator().generate_complete_car()
        elapsed = (time.time() - start) * 1000
        return CarCompleteResponse(
            name=car["name"], components=car["components"],
            total_surfaces=car["total_surfaces"], parameters=car.get("parameters"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/component", response_model=CarComponentResponse)
async def generate_component(request: CarComponentGenerateRequest):
    """生成单个车身部件"""
    try:
        gen = _get_generator()
        comp = request.component
        if comp in _SIMPLE_COMPONENTS:
            result = getattr(gen, _SIMPLE_COMPONENTS[comp])()
        elif comp in _SIDE_COMPONENTS:
            result = getattr(gen, _SIDE_COMPONENTS[comp])(side=request.side or "left")
        elif comp in _POSITION_SIDE_COMPONENTS:
            result = getattr(gen, _POSITION_SIDE_COMPONENTS[comp])(
                position=request.position or "front", side=request.side or "left")
        elif comp == "pillar":
            result = gen.generate_pillar(pillar_type=request.pillar_type or "A",
                                         side=request.side or "left")
        else:
            raise HTTPException(status_code=400,
                                detail=f"Unknown component: {comp}. Available: {ALL_COMPONENTS}")
        return CarComponentResponse(
            name=result["name"], type=result["type"], points=result.get("points"),
            color=result.get("color"), opacity=result.get("opacity"),
            position=result.get("position"),
            extra={k: v for k, v in result.items()
                   if k not in ("name", "type", "points", "color", "opacity", "position")})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components")
async def list_components():
    """列出所有可用车身部件"""
    info = ([{"component": n, "params": []} for n in _SIMPLE_COMPONENTS]
            + [{"component": n, "params": ["side"]} for n in _SIDE_COMPONENTS]
            + [{"component": n, "params": ["side", "position"]} for n in _POSITION_SIDE_COMPONENTS])
    info.append({"component": "pillar", "params": ["side", "pillar_type"]})
    return {"components": info, "total": len(info)}


@router.get("/parameters")
async def get_car_parameters():
    """获取当前汽车参数配置"""
    return {"parameters": _get_generator().params}


@router.post("/regenerate", response_model=CarCompleteResponse)
async def regenerate_car(request: CarGenerateRequest):
    """用新参数重新生成车身"""
    try:
        global _generator
        _generator = CarBodyGenerator()
        car = _generator.generate_complete_car()
        return CarCompleteResponse(
            name=car["name"], components=car["components"],
            total_surfaces=car["total_surfaces"], parameters=car.get("parameters"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_car_data(request: CarGenerateRequest):
    """导出完整车身数据为JSON"""
    try:
        car = _get_generator().export_car_data()
        return {"name": car["name"], "total_surfaces": car["total_surfaces"],
                "components_count": len(car["components"]), "exported": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
