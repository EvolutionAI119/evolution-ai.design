"""模型构建/重建API路由（全数据库持久化）"""
import time
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, ModelFile, Project, ParameterSet
from ..car_generator import NURBSCarBodyGenerator as CarBodyGenerator
from ..schemas import ModelBuildRequest, ModelRebuildRequest, ModelBuildResponse
from ..config import settings

router = APIRouter(prefix="/api/v1/build", tags=["模型构建"])


@router.post("/", response_model=ModelBuildResponse)
async def build_model(request: ModelBuildRequest, db: Session = Depends(get_db)):
    """从参数构建新模型"""
    try:
        start = time.time()
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        generator = CarBodyGenerator()
        car = generator.generate_complete_car()
        params_data = request.params or {}
        # 保存参数集
        db.add(ParameterSet(
            project_id=request.project_id,
            name=f"build_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            params=json.dumps(params_data)))
        # 创建模型文件记录（持久化 car_data 与 params）
        ts = int(time.time())
        model = ModelFile(
            project_id=request.project_id,
            filename=f"car_model_{ts}.json",
            filepath=str(settings.models_path / f"car_model_{ts}.json"),
            file_type="JSON", file_size=len(json.dumps(car)), status="built",
            params_json=json.dumps(params_data, ensure_ascii=False),
            car_data_json=json.dumps(car, ensure_ascii=False))
        db.add(model)
        db.commit()
        db.refresh(model)
        elapsed = (time.time() - start) * 1000
        return ModelBuildResponse(
            model_id=model.id, status="built", components_count=car["total_surfaces"],
            build_time_ms=round(elapsed, 2), parameters_used=params_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild", response_model=ModelBuildResponse)
async def rebuild_model(request: ModelRebuildRequest, db: Session = Depends(get_db)):
    """重建已有模型（支持参数覆盖和部分重建）"""
    try:
        start = time.time()
        model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        generator = CarBodyGenerator()
        if request.rebuild_components:
            # 部分重建：从数据库读取现有 car_data
            car_data = {}
            if model.car_data_json:
                try:
                    car_data = json.loads(model.car_data_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            if not car_data:
                car_data = generator.generate_complete_car()
            method_map = {
                "hood": generator.generate_hood, "windshield": generator.generate_windshield,
                "roof": generator.generate_roof, "bumper": generator.generate_bumper_front}
            components = []
            for comp in car_data.get("components", []):
                if comp.get("type") in request.rebuild_components:
                    method = method_map.get(comp["type"])
                    components.append(method() if method else comp)
                else:
                    components.append(comp)
            car = {"name": car_data.get("name", "重建车身"),
                   "components": components, "total_surfaces": len(components)}
        else:
            car = generator.generate_complete_car()
        rebuild_params = request.params_override or {}
        model.status = "rebuilt"
        model.params_json = json.dumps(rebuild_params, ensure_ascii=False)
        model.car_data_json = json.dumps(car, ensure_ascii=False)
        db.commit()
        elapsed = (time.time() - start) * 1000
        return ModelBuildResponse(
            model_id=request.model_id, status="rebuilt",
            components_count=car["total_surfaces"], build_time_ms=round(elapsed, 2),
            parameters_used=rebuild_params)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_build(project_ids: List[int], db: Session = Depends(get_db)):
    """批量构建模型"""
    results = []
    for project_id in project_ids:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            results.append({"project_id": project_id, "status": "error", "detail": "Project not found"})
            continue
        try:
            start = time.time()
            car = CarBodyGenerator().generate_complete_car()
            ts = int(time.time())
            model = ModelFile(
                project_id=project_id, filename=f"car_model_{ts}.json",
                filepath=str(settings.models_path / f"car_model_{ts}.json"),
                file_type="JSON", file_size=len(json.dumps(car)), status="built",
                params_json=json.dumps({}, ensure_ascii=False),
                car_data_json=json.dumps(car, ensure_ascii=False))
            db.add(model)
            db.commit()
            db.refresh(model)
            elapsed = (time.time() - start) * 1000
            results.append({"project_id": project_id, "model_id": model.id, "status": "built",
                            "components_count": car["total_surfaces"], "build_time_ms": round(elapsed, 2)})
        except Exception as e:
            results.append({"project_id": project_id, "status": "error", "detail": str(e)})
    return {"results": results}


@router.get("/cache")
async def get_build_cache(db: Session = Depends(get_db)):
    """获取构建缓存状态"""
    models = db.query(ModelFile).filter(ModelFile.car_data_json.isnot(None)).all()
    return {"cached_models": len(models), "model_ids": [m.id for m in models]}


@router.delete("/cache/{model_id}")
async def clear_build_cache(model_id: int, db: Session = Depends(get_db)):
    """清除指定模型的构建缓存"""
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if not model.car_data_json:
        raise HTTPException(status_code=404, detail="Model not found in cache")
    model.car_data_json = None
    db.commit()
    return {"success": True, "message": f"Cache for model {model_id} cleared"}


@router.get("/status/{model_id}")
async def get_build_status(model_id: int, db: Session = Depends(get_db)):
    """获取模型构建状态"""
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"model_id": model_id, "status": model.status,
            "cached": model.car_data_json is not None,
            "filename": model.filename, "file_type": model.file_type,
            "created_at": model.created_at.isoformat()}
