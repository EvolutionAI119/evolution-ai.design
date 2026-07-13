"""
车身生成API路由
"""
import time
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.modules.car_body_generator import NURBSCarBodyGenerator as CarBodyGenerator
from app.schemas.base import (
    CarGenerateRequest,
    CarComponentGenerateRequest,
    CarComponentResponse,
    CarCompleteResponse,
)
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/car", tags=["车身生成"])

# 全局生成器实例
_generator: CarBodyGenerator = None


def _get_generator() -> CarBodyGenerator:
    global _generator
    if _generator is None:
        _generator = CarBodyGenerator()
    return _generator


# 部件名 → 生成方法映射（无需 side/position 参数的方法）
_SIMPLE_COMPONENTS = {
    "hood": "generate_hood",
    "windshield": "generate_windshield",
    "roof": "generate_roof",
    "rear_window": "generate_rear_window",
    "trunk": "generate_trunk",
    "bumper_front": "generate_bumper_front",
    "bumper_rear": "generate_bumper_rear",
    "grille": "generate_grille",
    "door_seam": "generate_door_seam",
}

# 需要 side 参数的部件
_SIDE_COMPONENTS = {
    "door_front": "generate_door_front",
    "door_rear": "generate_door_rear",
    "headlight": "generate_headlight",
    "taillight": "generate_taillight",
    "mirror": "generate_mirror",
}

# 需要 position + side 参数的部件
_POSITION_SIDE_COMPONENTS = {
    "wheel": "generate_wheel",
    "fender": "generate_fender",
}

# 所有可用部件
ALL_COMPONENTS = list(_SIMPLE_COMPONENTS.keys()) + list(_SIDE_COMPONENTS.keys()) + list(_POSITION_SIDE_COMPONENTS.keys()) + ["pillar"]


@router.post("/generate", response_model=CarCompleteResponse)
async def generate_complete_car(request: CarGenerateRequest):
    """生成完整车身模型"""
    try:
        start = time.time()
        gen = _get_generator()
        car = gen.generate_complete_car()
        elapsed = (time.time() - start) * 1000

        logger.info(f"Generated complete car: {car['total_surfaces']} components in {elapsed:.1f}ms")

        return CarCompleteResponse(
            name=car["name"],
            components=car["components"],
            total_surfaces=car["total_surfaces"],
            parameters=car.get("parameters"),
        )
    except Exception as e:
        logger.error(f"Car generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/component", response_model=CarComponentResponse)
async def generate_component(request: CarComponentGenerateRequest):
    """生成单个车身部件"""
    try:
        gen = _get_generator()
        component = request.component

        if component in _SIMPLE_COMPONENTS:
            method = getattr(gen, _SIMPLE_COMPONENTS[component])
            result = method()

        elif component in _SIDE_COMPONENTS:
            method = getattr(gen, _SIDE_COMPONENTS[component])
            result = method(side=request.side or "left")

        elif component in _POSITION_SIDE_COMPONENTS:
            method = getattr(gen, _POSITION_SIDE_COMPONENTS[component])
            result = method(
                position=request.position or "front",
                side=request.side or "left",
            )

        elif component == "pillar":
            result = gen.generate_pillar(
                pillar_type=request.pillar_type or "A",
                side=request.side or "left",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown component: {component}. Available: {ALL_COMPONENTS}",
            )

        return CarComponentResponse(
            name=result["name"],
            type=result["type"],
            points=result.get("points"),
            color=result.get("color"),
            opacity=result.get("opacity"),
            position=result.get("position"),
            extra={
                k: v for k, v in result.items()
                if k not in ("name", "type", "points", "color", "opacity", "position")
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Component generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components")
async def list_components():
    """列出所有可用车身部件"""
    components_info = []

    for name in _SIMPLE_COMPONENTS:
        components_info.append({"component": name, "params": []})

    for name in _SIDE_COMPONENTS:
        components_info.append({"component": name, "params": ["side"]})

    for name in _POSITION_SIDE_COMPONENTS:
        components_info.append({"component": name, "params": ["side", "position"]})

    components_info.append({"component": "pillar", "params": ["side", "pillar_type"]})

    return {"components": components_info, "total": len(components_info)}


@router.get("/parameters")
async def get_car_parameters():
    """获取当前汽车参数配置"""
    gen = _get_generator()
    return {"parameters": gen.params}


@router.post("/regenerate")
async def regenerate_car(request: CarGenerateRequest):
    """用新参数重新生成车身"""
    try:
        global _generator
        _generator = CarBodyGenerator()
        car = _generator.generate_complete_car()

        logger.info(f"Regenerated car with {car['total_surfaces']} components")

        return CarCompleteResponse(
            name=car["name"],
            components=car["components"],
            total_surfaces=car["total_surfaces"],
            parameters=car.get("parameters"),
        )
    except Exception as e:
        logger.error(f"Car regeneration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_car_data(request: CarGenerateRequest):
    """导出完整车身数据为JSON"""
    try:
        gen = _get_generator()
        car = gen.export_car_data()

        return {
            "name": car["name"],
            "total_surfaces": car["total_surfaces"],
            "components_count": len(car["components"]),
            "exported": True,
        }
    except Exception as e:
        logger.error(f"Car export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
