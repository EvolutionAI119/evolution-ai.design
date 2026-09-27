"""贝叶斯优化路由：机器学习后台训练的代理寻优容器

端点（前缀 /api/v1/bayes）：
  POST   /sessions                创建寻优会话（参数空间/目标方向/采集函数）
  GET    /sessions/{sid}          会话摘要（含当前最优）
  DELETE /sessions/{sid}          删除会话
  GET    /sessions/{sid}/suggest  建议下一组采样参数（GP + EI/UCB）
  POST   /sessions/{sid}/observe  上报一次观测（参数 → 质量分）
  GET    /sessions/{sid}/best     当前最优观测
  GET    /sessions/{sid}/samples  导出训练样本（与 /ai/train 数据集格式兼容）

使用闭环：suggest → 用建议参数评估造型质量（如 /ai/evaluate-quality 或人工评分）
→ observe 回填 → 再 suggest，迭代收敛后由 /samples 导出为训练数据。
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..bayes_optimizer import (
    DEFAULT_SPACE, BayesSession, ParameterSpace, SESSION_STORE,
)

router = APIRouter(prefix="/api/v1/bayes", tags=["贝叶斯优化"])


class ParamSpec(BaseModel):
    name: str = Field(..., min_length=1)
    min: float
    max: float


class CreateSessionRequest(BaseModel):
    name: Optional[str] = None
    # 缺省使用 14 个造型规范参数空间（与训练管线 PARAM_ORDER 对齐）
    space: Optional[List[ParamSpec]] = None
    goal: Literal["maximize", "minimize"] = "maximize"
    acquisition: Literal["ei", "ucb"] = "ei"
    seed: Optional[int] = Field(None, description="随机种子（复现实验用）")


class ObserveRequest(BaseModel):
    parameters: Dict[str, float]
    score: float = Field(..., description="该组参数的质量评分（目标函数值）")


def _get_session_or_404(session_id: str) -> BayesSession:
    s = SESSION_STORE.get(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="寻优会话不存在")
    return s


@router.post("/sessions", status_code=201)
def create_session(req: CreateSessionRequest):
    spec = ([p.model_dump() for p in req.space] if req.space else DEFAULT_SPACE)
    try:
        space = ParameterSpace(spec)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    session = BayesSession(
        space=space,
        goal=req.goal,
        acquisition=req.acquisition,
        seed=req.seed,
        name=req.name or "",
    )
    SESSION_STORE.create(session)
    return session.summary()


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    return _get_session_or_404(session_id).summary()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if not SESSION_STORE.delete(session_id):
        raise HTTPException(status_code=404, detail="寻优会话不存在")
    return {"deleted": session_id}


@router.get("/sessions/{session_id}/suggest")
def suggest(session_id: str, n: int = Query(1, ge=1, le=32)):
    session = _get_session_or_404(session_id)
    return {
        "session_id": session_id,
        "acquisition": session.acquisition,
        "suggestions": session.suggest(n),
    }


@router.post("/sessions/{session_id}/observe")
def observe(session_id: str, req: ObserveRequest):
    session = _get_session_or_404(session_id)
    try:
        result = session.observe(req.parameters, req.score)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"session_id": session_id, **result, "best": session.best()}


@router.get("/sessions/{session_id}/best")
def best(session_id: str):
    session = _get_session_or_404(session_id)
    b = session.best()
    if b is None:
        raise HTTPException(status_code=409, detail="会话尚无观测数据")
    return {"session_id": session_id, **b}


@router.get("/sessions/{session_id}/samples")
def samples(session_id: str):
    session = _get_session_or_404(session_id)
    return {"session_id": session_id, **session.samples()}
