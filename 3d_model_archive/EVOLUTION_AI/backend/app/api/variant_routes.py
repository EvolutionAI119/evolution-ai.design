"""
模型版本/变体API路由（全数据库持久化）
"""
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.models.database import SessionLocal, ModelFile, ModelVariant, ParameterSet
from app.modules.car_body_generator import NURBSCarBodyGenerator as CarBodyGenerator
from app.schemas.base import (
    ModelVariantCreateRequest,
    ModelVariantResponse,
    ModelCompareRequest,
)
from app.config.settings import settings
from app.utils.logger import logger


router = APIRouter(prefix="/api/v1/variants", tags=["模型变体"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=ModelVariantResponse)
async def create_variant(request: ModelVariantCreateRequest, db: Session = Depends(get_db)):
    """基于已有模型创建变体"""
    model = db.query(ModelFile).filter(ModelFile.id == request.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 生成变体模型
    generator = CarBodyGenerator()
    car = generator.generate_complete_car()

    # 收集参数
    params = request.params_override or {}
    if model.filepath and Path(model.filepath).exists():
        try:
            with open(model.filepath, "r", encoding="utf-8") as f:
                original = json.load(f)
                if "parameters" in original:
                    merged = original["parameters"]
                    merged.update(params)
                    params = merged
        except Exception:
            pass

    # 写入数据库
    variant = ModelVariant(
        model_id=request.model_id,
        name=request.name,
        parent_variant_id=None,
        params_json=json.dumps(params, ensure_ascii=False),
        description=request.description,
        car_data_json=json.dumps(car, ensure_ascii=False),
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)

    logger.info(f"Created variant '{request.name}' (id={variant.id}) for model {request.model_id}")

    return ModelVariantResponse(
        id=variant.id,
        name=variant.name,
        model_id=variant.model_id,
        parent_variant_id=variant.parent_variant_id,
        params=params,
        description=variant.description,
        created_at=variant.created_at,
    )


@router.get("/{model_id}", response_model=List[ModelVariantResponse])
async def list_variants(model_id: int, db: Session = Depends(get_db)):
    """列出模型的所有变体"""
    variants = db.query(ModelVariant).filter(ModelVariant.model_id == model_id).all()
    return [
        ModelVariantResponse(
            id=v.id,
            name=v.name,
            model_id=v.model_id,
            parent_variant_id=v.parent_variant_id,
            params=json.loads(v.params_json) if v.params_json else None,
            description=v.description,
            created_at=v.created_at,
        )
        for v in variants
    ]


@router.get("/{model_id}/history")
async def get_version_history(model_id: int, db: Session = Depends(get_db)):
    """获取模型的版本历史"""
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # 获取参数集历史
    param_sets = (
        db.query(ParameterSet)
        .filter(ParameterSet.project_id == model.project_id)
        .order_by(ParameterSet.created_at.desc())
        .all()
    )

    # 获取变体列表
    variants = db.query(ModelVariant).filter(ModelVariant.model_id == model_id).all()

    history = {
        "model_id": model_id,
        "current_status": model.status,
        "created_at": model.created_at.isoformat(),
        "parameter_versions": [
            {
                "id": ps.id,
                "name": ps.name,
                "created_at": ps.created_at.isoformat(),
            }
            for ps in param_sets
        ],
        "variants": [
            {
                "id": v.id,
                "name": v.name,
                "created_at": v.created_at.isoformat(),
            }
            for v in variants
        ],
    }

    return history


@router.get("/{model_id}/{variant_id}")
async def get_variant(model_id: int, variant_id: int, db: Session = Depends(get_db)):
    """获取变体详情（含完整模型数据）"""
    variant = db.query(ModelVariant).filter(
        ModelVariant.id == variant_id,
        ModelVariant.model_id == model_id,
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    car_data = {}
    if variant.car_data_json:
        try:
            car_data = json.loads(variant.car_data_json)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": variant.id,
        "name": variant.name,
        "model_id": variant.model_id,
        "params": json.loads(variant.params_json) if variant.params_json else None,
        "description": variant.description,
        "created_at": variant.created_at.isoformat(),
        "components_count": car_data.get("total_surfaces", 0),
    }


@router.delete("/{model_id}/{variant_id}")
async def delete_variant(model_id: int, variant_id: int, db: Session = Depends(get_db)):
    """删除变体"""
    variant = db.query(ModelVariant).filter(
        ModelVariant.id == variant_id,
        ModelVariant.model_id == model_id,
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    db.delete(variant)
    db.commit()
    return {"success": True, "message": f"Variant {variant_id} deleted"}


@router.post("/compare")
async def compare_models(request: ModelCompareRequest, db: Session = Depends(get_db)):
    """对比两个模型"""
    model_a = db.query(ModelFile).filter(ModelFile.id == request.model_id_a).first()
    model_b = db.query(ModelFile).filter(ModelFile.id == request.model_id_b).first()

    if not model_a:
        raise HTTPException(status_code=404, detail=f"Model {request.model_id_a} not found")
    if not model_b:
        raise HTTPException(status_code=404, detail=f"Model {request.model_id_b} not found")

    # 基础对比
    comparison = {
        "model_a": {
            "id": model_a.id,
            "filename": model_a.filename,
            "file_type": model_a.file_type,
            "file_size": model_a.file_size,
            "status": model_a.status,
        },
        "model_b": {
            "id": model_b.id,
            "filename": model_b.filename,
            "file_type": model_b.file_type,
            "file_size": model_b.file_size,
            "status": model_b.status,
        },
        "differences": {
            "file_size_diff": model_b.file_size - model_a.file_size if model_a.file_size and model_b.file_size else None,
            "type_match": model_a.file_type == model_b.file_type,
        },
    }

    # 参数对比（从数据库 params_json 读取）
    params_a = _get_model_params(model_a)
    params_b = _get_model_params(model_b)

    if params_a or params_b:
        all_keys = set(list(params_a.keys()) + list(params_b.keys()))
        param_diff = {}
        for key in all_keys:
            val_a = params_a.get(key)
            val_b = params_b.get(key)
            if val_a != val_b:
                param_diff[key] = {"value_a": val_a, "value_b": val_b}
                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    param_diff[key]["delta"] = val_b - val_a
        comparison["param_differences"] = param_diff

    return comparison


@router.post("/{model_id}/{variant_id}/rollback")
async def rollback_to_variant(model_id: int, variant_id: int, db: Session = Depends(get_db)):
    """回滚到指定变体版本"""
    model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    variant = db.query(ModelVariant).filter(
        ModelVariant.id == variant_id,
        ModelVariant.model_id == model_id,
    ).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # 用变体参数回滚模型
    variant_params = json.loads(variant.params_json) if variant.params_json else {}
    model.status = "rolled_back"
    model.params_json = variant.params_json
    if variant.car_data_json:
        model.car_data_json = variant.car_data_json
    db.commit()

    logger.info(f"Rolled back model {model_id} to variant {variant_id}")

    return {
        "success": True,
        "model_id": model_id,
        "rolled_back_to": variant_id,
        "variant_name": variant.name,
        "params": variant_params,
    }


def _get_model_params(model: ModelFile) -> Dict[str, Any]:
    """从模型记录读取构建参数（数据库 params_json）"""
    if model.params_json:
        try:
            return json.loads(model.params_json)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}
