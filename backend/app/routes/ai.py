"""AI 路由：Ollama 集成，提供 NURBS 专家问答和模型管理"""
import os
import json
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..config import settings

router = APIRouter(prefix="/api/v1", tags=["AI 助手"])

# Ollama 默认地址
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "").strip() or "http://localhost:11434"
DEFAULT_MODEL = os.getenv("NURBS_MODEL", "").strip() or "nurbs-expert"


# ── 请求/响应模型 ──────────────────────────────

class ChatRequest(BaseModel):
    """NURBS 专家问答请求"""
    question: str = Field(..., description="用户问题")
    model: Optional[str] = Field(None, description="模型名（默认 nurbs-expert）")
    stream: bool = Field(False, description="是否流式输出")
    context: Optional[str] = Field(None, description="附加上下文（如当前车型/参数）")


class ChatResponse(BaseModel):
    """NURBS 专家问答响应"""
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="使用的模型")
    eval_count: int = Field(0, description="生成 token 数")
    duration_sec: float = Field(0.0, description="推理耗时（秒）")


class ModelInfo(BaseModel):
    """Ollama 模型信息"""
    name: str
    size: Optional[str] = None
    modified: Optional[str] = None


# ── API 端点 ────────────────────────────────────

@router.post("/ai/chat", response_model=ChatResponse, tags=["AI 助手"])
async def chat_with_nurbs_expert(req: ChatRequest):
    """
    与 NURBS 专家模型对话

    - 基于微调后的 Qwen2.5-7B + NURBS 知识数据集
    - 支持 A 级曲面、连续性、SOP 检查等领域问题
    """
    model_name = req.model or DEFAULT_MODEL

    # 构建提示词
    prompt = req.question
    if req.context:
        prompt = f"[上下文] {req.context}\n\n[问题] {req.question}"

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.85,
            "num_ctx": 4096,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama 服务未启动，请运行: ollama serve (地址: {OLLAMA_HOST})",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ollama 返回错误: {e.response.text}",
        )

    return ChatResponse(
        answer=data.get("response", ""),
        model=model_name,
        eval_count=data.get("eval_count", 0),
        duration_sec=round(data.get("total_duration", 0) / 1e9, 2),
    )


@router.get("/ai/models", response_model=list[ModelInfo], tags=["AI 助手"])
async def list_ollama_models():
    """列出 Ollama 中已安装的模型"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama 服务未启动 (地址: {OLLAMA_HOST})",
        )

    models = []
    for m in data.get("models", []):
        models.append(ModelInfo(
            name=m.get("name", ""),
            size=f"{round(m.get('size', 0) / 1e9, 1)}GB" if m.get("size") else None,
            modified=m.get("modified_at", ""),
        ))
    return models


@router.get("/ai/health", tags=["AI 助手"])
async def ai_health_check():
    """检查 Ollama 服务和 NURBS 专家模型可用性"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except (httpx.ConnectError, httpx.UnsupportedProtocol, Exception):
        return {
            "status": "offline",
            "ollama": "unreachable",
            "ollama_host": OLLAMA_HOST,
            "message": "Ollama 服务未启动，请运行: ollama serve",
            "model_ready": False,
        }

    model_names = [m["name"] for m in data.get("models", [])]
    expert_ready = any(DEFAULT_MODEL in name for name in model_names)

    return {
        "status": "online" if expert_ready else "partial",
        "ollama": "running",
        "ollama_host": OLLAMA_HOST,
        "models_installed": len(model_names),
        "model_names": model_names,
        "expert_model": DEFAULT_MODEL,
        "model_ready": expert_ready,
        "message": f"{DEFAULT_MODEL} 已就绪" if expert_ready else f"请运行: .\\scripts\\setup_ollama.ps1",
    }
