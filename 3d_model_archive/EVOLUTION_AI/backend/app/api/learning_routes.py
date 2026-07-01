from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Optional, Dict, Any

from app.modules.learning_engine import LearningEngine
from app.schemas.base import (
    LearningParams,
    LearningRequest,
    ModelLearningRequest,
    AutoLearningRequest,
    EvaluationResponse,
    LearningResponse,
    ModelLearningResponse,
    AutoLearningStatus,
    ModelInfo,
)
from app.utils.logger import logger

router = APIRouter()

_engine = LearningEngine()


@router.post("/evaluate/", response_model=EvaluationResponse)
def evaluate_parameters(params: LearningParams):
    """评估参数组合的质量评分"""
    try:
        result = _engine.evaluate_params(params.dict())
        return result
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn/", response_model=LearningResponse)
def run_learning(request: LearningRequest):
    """运行单次学习会话"""
    try:
        seed_params = request.seed_params.dict() if request.seed_params else None

        if request.benchmark_key:
            _engine.init_engine(benchmark_key=request.benchmark_key)

        result = _engine.run_learning(
            seed_params=seed_params,
            generations=request.generations,
            population_size=request.population_size,
        )
        return result
    except Exception as e:
        logger.error(f"Learning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learn/model/", response_model=ModelLearningResponse)
def run_model_learning(request: ModelLearningRequest):
    """运行预定义车型的学习会话"""
    try:
        result = _engine.run_model_learning(
            model_key=request.model_key,
            generations=request.generations,
            population_size=request.population_size,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Model learning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto/start/")
def start_auto_learning(request: AutoLearningRequest):
    """启动全时自主学习"""
    try:
        seed_params = request.seed_params.dict() if request.seed_params else None
        _engine.start_auto_learning(
            seed_params=seed_params,
            interval=request.interval,
            generations=request.generations,
        )
        return {"message": "Auto learning started", "status": _engine.get_auto_status()}
    except Exception as e:
        logger.error(f"Failed to start auto learning: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto/stop/")
def stop_auto_learning():
    """停止全时自主学习"""
    try:
        _engine.stop_auto_learning()
        return {"message": "Auto learning stopped", "status": _engine.get_auto_status()}
    except Exception as e:
        logger.error(f"Failed to stop auto learning: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auto/status/", response_model=AutoLearningStatus)
def get_auto_learning_status():
    """获取全时自主学习状态"""
    return _engine.get_auto_status()


@router.get("/models/", response_model=List[ModelInfo])
def get_available_models():
    """获取可用车型列表"""
    return _engine.get_available_models()


@router.get("/params/ranges/")
def get_parameter_ranges():
    """获取参数范围约束"""
    return _engine.get_param_ranges()


@router.get("/params/weights/")
def get_weights():
    """获取各维度评估权重"""
    return _engine.get_weights()


@router.get("/params/default/")
def get_default_params():
    """获取默认参数"""
    return _engine.DEFAULT_PARAMS