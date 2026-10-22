"""安全围栏 · 边界守卫中间件（纯 ASGI，流式安全）

三个独立中间件（注册顺序见 main.py，自外向内）：
  RequestContextMiddleware  为每个请求分配 X-Request-Id 并写入审计上下文；
  BodySizeLimitMiddleware   Content-Length 超过 FENCE_MAX_BODY_BYTES → 413；
  MaintenanceModeMiddleware FENCE_MAINTENANCE_MODE=true 时 API 一律 503
                            （仅保留 /api/v1/health 探针，供恢复后探测）。

响应头说明：三者注册在 SecurityHeadersMiddleware / CORSMiddleware 内层，
因此短路响应（413/503）同样携带安全响应头与 CORS 头，行为与常规错误一致。
"""
from __future__ import annotations

import json
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ..config import settings
from .audit import emit, request_id_var

_HEALTH_PATH = "/api/v1/health"


def _client_ip(scope: Scope) -> str:
    client = scope.get("client")
    return (client[0] if client else "") or ""


class RequestContextMiddleware:
    """为每个 HTTP 请求分配 16 位十六进制 request_id。

    - 写入 scope["state"]（路由层可读 request.state.request_id）
    - 写入 audit.request_id_var（安全审计事件自动携带）
    - 响应头回写 X-Request-Id（排障串联前后端日志）
    """

    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        rid = uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        state = scope.setdefault("state", {})
        state["fence_request_id"] = rid

        async def _send_with_rid(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", rid.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, _send_with_rid)
        finally:
            request_id_var.reset(token)


async def _short_circuit(send: Send, status: int, detail: str,
                         extra_headers: list[tuple[str, str]] | None = None) -> None:
    """在进入路由前直接返回 JSON 错误（413 / 503）。"""
    body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
    headers = [(b"content-type", b"application/json; charset=utf-8"),
               (b"content-length", str(len(body)).encode("ascii"))]
    for name, value in (extra_headers or []):
        headers.append((name.lower().encode("ascii"), value.encode("latin-1")))
    await send({"type": "http.response.start", "status": status,
                "headers": headers})
    await send({"type": "http.response.body", "body": body})


class BodySizeLimitMiddleware:
    """全局请求体体积守卫（防滥用/资源耗尽的第一道门）。

    依据 Content-Length 头判断（httpx/axios/fetch 均会携带）；
    分块上传（无 Content-Length）由路由层 read_upload_limited 分块限读兜底。
    """

    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.FENCE_ENABLED:
            return await self.app(scope, receive, send)
        limit = settings.FENCE_MAX_BODY_BYTES
        content_length: str | None = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                content_length = value.decode("latin-1", errors="ignore")
                break
        if content_length and content_length.strip().isdigit() \
                and int(content_length) > limit:
            emit("fence.body_limit", level="warning",
                 path=scope.get("path", ""), method=scope.get("method", ""),
                 ip=_client_ip(scope),
                 content_length=int(content_length), limit=limit)
            await _short_circuit(
                send, 413,
                f"请求体过大（上限 {limit // 1024 // 1024}MB），已被安全围栏拦截")
            return
        await self.app(scope, receive, send)


class MaintenanceModeMiddleware:
    """应急响应 · 维护模式：一键停摆全部 API（保留健康探针）。

    触发条件：FENCE_ENABLED=true 且 FENCE_MAINTENANCE_MODE=true。
    响应携带 Retry-After: 300，供前端/网关友好退避。
    """

    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not settings.FENCE_ENABLED \
                or not settings.FENCE_MAINTENANCE_MODE:
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        if not path.startswith("/api/") or path == _HEALTH_PATH:
            return await self.app(scope, receive, send)
        emit("fence.maintenance", level="warning", path=path,
             method=scope.get("method", ""), ip=_client_ip(scope))
        await _short_circuit(
            send, 503, "平台维护中，请稍后重试（维护模式由管理员开启）",
            extra_headers=[("Retry-After", "300")])
