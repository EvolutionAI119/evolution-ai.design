"""LLM 统一代理路由：把前端请求透传给六大模型提供商（OpenAI 兼容协议）

支持提供商：
  - ernie    百度文心（千帆 v2）
  - qwen     阿里通义千问（DashScope 兼容模式）
  - hunyuan  腾讯混元（TokenHub，2026 新端点）
  - doubao   字节豆包（火山方舟 Ark v3）
  - deepseek 深度求索
  - kimi     Moonshot Kimi
  - siliconflow 硅基流动（SiliconFlow 聚合平台）

设计原则：
  1. 提供商与端点固定写死在注册表中 → 杜绝 SSRF
  2. 鉴权 Key 解析顺序：环境变量 EVOAI_{PROVIDER}_KEY → 用户库中加密存储的 Key
  3. 无 Key 时返回明确 4xx，绝不静默降级到假实现
  4. 请求/响应体原样透传；上游错误码与错误体原样返回，便于前端排障
  5. 各提供商能力（chat/embeddings/images）如实声明，不支持的能力返回 501
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..rate_limit import limit
from ..security import get_optional_user, get_user_api_key

router = APIRouter(prefix="/api/v1/llm", tags=["LLM 模型代理"])


# ── 提供商注册表（2026 年核实的官方端点） ─────────────
class ProviderSpec:
    __slots__ = ("id", "name", "base_url", "default_model",
                 "capabilities", "docs_url")

    def __init__(self, id: str, name: str, base_url: str,
                 default_model: str, capabilities: List[str], docs_url: str):
        self.id = id
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.capabilities = capabilities
        self.docs_url = docs_url


PROVIDERS: Dict[str, ProviderSpec] = {
    "ernie": ProviderSpec(
        id="ernie", name="百度文心一言",
        base_url="https://qianfan.baidubce.com/v2",
        default_model="ernie-4.0",
        capabilities=["chat", "embeddings"],
        docs_url="https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html",
    ),
    "qwen": ProviderSpec(
        id="qwen", name="阿里通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-2.5-7b-instruct",
        capabilities=["chat", "embeddings"],
        docs_url="https://help.aliyun.com/zh/model-studio/developer-reference/compatibility-of-openai-with-dashscope",
    ),
    "hunyuan": ProviderSpec(
        id="hunyuan", name="腾讯混元",
        # TokenHub 新端点（旧 api.hunyuan.cloud.tencent.com 于 2026-09-30 停服）
        base_url="https://tokenhub.tencentmaas.com/v1",
        default_model="hunyuan-pro",
        capabilities=["chat"],
        docs_url="https://cloud.tencent.com/document/product/1729",
    ),
    "doubao": ProviderSpec(
        id="doubao", name="字节豆包",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        default_model="doubao-pro",
        capabilities=["chat", "embeddings", "images"],
        docs_url="https://www.volcengine.com/docs/82379",
    ),
    "deepseek": ProviderSpec(
        id="deepseek", name="DeepSeek 深度求索",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        capabilities=["chat"],
        docs_url="https://api-docs.deepseek.com/zh-cn/",
    ),
    "kimi": ProviderSpec(
        id="kimi", name="Moonshot Kimi",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        capabilities=["chat", "embeddings"],
        docs_url="https://platform.moonshot.cn/docs",
    ),
    "siliconflow": ProviderSpec(
        id="siliconflow", name="硅基流动 SiliconFlow",
        base_url="https://api.siliconflow.cn/v1",
        default_model="Qwen/Qwen2.5-7B-Instruct",
        capabilities=["chat", "embeddings", "images"],
        docs_url="https://docs.siliconflow.cn/",
    ),
}

# 各能力的上游路径与超时（秒）
_CAPABILITY_PATHS = {
    "chat": ("/chat/completions", 120.0),
    "embeddings": ("/embeddings", 60.0),
    "images": ("/images/generations", 180.0),
}


def _get_provider(provider: str) -> ProviderSpec:
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的提供商: {provider}，"
                   f"当前支持：{', '.join(PROVIDERS.keys())}",
        )
    return spec


async def _read_json_body(request: Request) -> Dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体必须是合法的 JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    return body


async def _proxy_upstream(
    provider: str, capability: str, request: Request, db: Session, user
) -> Response:
    """核心透传逻辑：取 Key → 补默认模型 → 转发 → 原样返回上游响应"""
    spec = _get_provider(provider)

    if capability not in spec.capabilities:
        raise HTTPException(
            status_code=501,
            detail=f"{spec.name} 暂不支持 {capability} 能力"
                   f"（支持：{', '.join(spec.capabilities)}）",
        )

    api_key = get_user_api_key(db, user, provider)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail=f"未配置 {spec.name} 的 API Key/Token，"
                   f"请先登录并在「账户设置 → API Key 管理」中填写",
        )

    payload = await _read_json_body(request)
    # 未显式指定 model 时注入该提供商的默认模型
    if not payload.get("model"):
        payload["model"] = spec.default_model

    sub_path, timeout = _CAPABILITY_PATHS[capability]
    url = f"{spec.base_url}{sub_path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upstream = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"请求 {spec.name} 超时（{timeout:.0f}s），请稍后重试",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 {spec.name} 服务，请检查网络后重试",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"调用 {spec.name} 失败：{type(exc).__name__}",
        )

    # 上游响应（含错误码与错误体）原样透传；content-type 以兼容 JSON / SSE
    media_type = upstream.headers.get("content-type", "application/json")
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=media_type.split(";")[0].strip() or "application/json",
    )


# ── 提供商列表 ────────────────────────────────────────

@router.get("/providers")
def list_providers(
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    """返回全部提供商元信息；configured 表示当前调用方是否已配置可用 Key"""
    result: List[Dict[str, Any]] = []
    for spec in PROVIDERS.values():
        key = get_user_api_key(db, user, spec.id)
        result.append({
            "id": spec.id,
            "name": spec.name,
            "default_model": spec.default_model,
            "capabilities": spec.capabilities,
            "docs_url": spec.docs_url,
            "configured": bool(key),
        })
    return {"providers": result, "count": len(result)}


# ── 对话补全 ──────────────────────────────────────────

@router.post("/{provider}/chat/completions")
@limit(settings.RATE_LIMIT_AI)
async def chat_completions(
    provider: str, request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    return await _proxy_upstream(provider, "chat", request, db, user)


# ── 向量嵌入 ──────────────────────────────────────────

@router.post("/{provider}/embeddings")
@limit(settings.RATE_LIMIT_AI)
async def embeddings(
    provider: str, request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    return await _proxy_upstream(provider, "embeddings", request, db, user)


# ── 文生图 ────────────────────────────────────────────

@router.post("/{provider}/images/generations")
@limit(settings.RATE_LIMIT_AI)
async def images_generations(
    provider: str, request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    return await _proxy_upstream(provider, "images", request, db, user)
