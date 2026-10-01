"""FastAPI应用入口：CORS配置、安全响应头、路由注册、启动初始化

关键修复（对应 /api/v1 响应头审计报告）：
  1. CORS allow_origins 由 "*" 改为显式白名单（settings.cors_allow_origins_list），
     配合 allow_credentials=True 不违反 W3C Fetch 规范；
     同时启用 CORSMiddleware 的 expose_headers=[Content-Disposition, ETag, X-Session-Id]
     让前端 JS fetch 能读到下载文件名等关键头。
  2. 新增「全局安全响应头中间件 SecurityHeadersMiddleware」：
     对 2xx/3xx/4xx/5xx/FileResponse 等所有响应统一注入 6 条安全头
     (X-Content-Type-Options / X-Frame-Options / CSP / Referrer-Policy /
      Permissions-Policy / Cache-Control)，并可选择去除 `server: uvicorn` 信息泄露。
  3. 注册 4 个 exception_handler（StarletteHTTPException / RequestValidationError /
     Exception / 405 MethodNotAllowed），保证即使路由抛出异常、
     或请求未进入 CORSMiddleware 分支时（如 404 路由不存在），CORS + 安全头仍会补齐。
  4. 所有跨域响应都会带上 Vary: Origin，避免 CDN / 反代把错误 Origin 的 ACAO 缓存下来。
"""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .config import settings
from .database import init_db
from .rate_limit import limiter
from .routes import (
    admin, ai, analytics, auth, bayes, build, car, export, import_export,
    llm_proxy, model, modify, project, quality, training, texture, variant,
    workflow,
)


# 后端错误日志：backend/logs/backend-error.log（与 routes/admin.py 读取路径一致）
_ERROR_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "backend-error.log"
_error_logging_ready = False


def _setup_error_logging() -> None:
    """挂载 ERROR 级滚动文件 handler（幂等，reload 多进程下也安全）。

    超级管理员可通过 /api/v1/admin/backend-errors 读取该文件排查 BUG。
    """
    global _error_logging_ready
    if _error_logging_ready:
        return
    _ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        _ERROR_LOG_PATH, maxBytes=5 * 1024 * 1024,
        backupCount=3, encoding="utf-8",
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    ))
    root = logging.getLogger()
    root.addHandler(handler)
    # 确保 ERROR 会被文件 handler 落盘（不抬高控制台输出级别）
    if root.level == logging.NOTSET or root.level > logging.ERROR:
        root.setLevel(logging.ERROR)
    _error_logging_ready = True


# =========================================================================
# 1) Starlette "纯 ASGI" 中间件：对 server 头做脱敏（必须在最外层，因为
#    ASGI 消息头 `server` 是 uvicorn 在最外层写入的；使用 BaseHTTPMiddleware
#    捕获不到，因为它是在响应对象里看的，而 server 头是 uvicorn 直接写 http11）
# =========================================================================
class StripServerHeaderMiddleware:
    """去除 `server: uvicorn` 信息泄露头（纯 ASGI wrapper，最外层）。"""

    __slots__ = ("app", "enable")

    def __init__(self, app: ASGIApp, enable: bool = True) -> None:
        self.app = app
        self.enable = enable

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enable or scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        async def _send_sans_server(message: Message) -> None:
            if message["type"] == "http.response.start":
                cleaned = []
                for name, value in message.get("headers", []):
                    if name.lower() == b"server":
                        continue
                    cleaned.append((name, value))
                message["headers"] = cleaned
            await send(message)

        await self.app(scope, receive, _send_sans_server)


class NormalizeCorsAcaoMiddleware:
    """最外层 ASGI 网关：确保「ACAO='*' 永远不会和 ACAC=true 同时出现」。

    W3C Fetch 规范（https://fetch.spec.whatwg.org/#cors-protocol-and-credentials）明确禁止
    Access-Control-Allow-Origin: *  与  Access-Control-Allow-Credentials: true  组合。
    但 Starlette/FastAPI 的 CORSMiddleware 在部分路径下（错误响应、简单请求回写）可能
    仍写出 "*" + "true" 组合；此处做「出厂前最终校正」：
      - 若请求含 Origin 头 → 把 * 改写为具体 Origin（回显），并补 Vary: Origin
      - 否则 → 去掉 ACAC=true 标记
    """

    __slots__ = ("app",)

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @staticmethod
    def _origin_from_scope(scope: Scope) -> Optional[str]:
        for name, value in scope.get("headers", []):
            if name.lower() == b"origin":
                try:
                    return value.decode("latin-1")
                except Exception:
                    return None
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        origin = self._origin_from_scope(scope)

        async def _fix_acao(message: Message) -> None:
            if message["type"] != "http.response.start":
                await send(message)
                return
            headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
            b_acao = b"access-control-allow-origin"
            b_acac = b"access-control-allow-credentials"
            b_vary = b"vary"
            has_acao_star = any(n.lower() == b_acao and v.strip() == b"*" for n, v in headers)
            has_acac_true = any(
                n.lower() == b_acac and v.strip().lower() == b"true" for n, v in headers
            )
            if has_acao_star and has_acac_true:
                rebuilt: list[tuple[bytes, bytes]] = []
                for n, v in headers:
                    nl = n.lower()
                    if nl == b_acao:
                        if origin:
                            rebuilt.append((b_acao, origin.encode("latin-1")))
                        else:
                            # 无 Origin → 说明非浏览器跨域；直接去掉 ACAC=true 即可
                            continue
                    elif nl == b_acac and not origin:
                        continue  # 没 Origin 就没必要声明 credentials=true
                    else:
                        rebuilt.append((n, v))
                # 追加/合并 Vary: Origin
                existing_v = ""
                for n, v in rebuilt:
                    if n.lower() == b_vary:
                        existing_v = v.decode("latin-1", errors="ignore")
                entries = [e.strip() for e in existing_v.split(",") if e.strip()]
                if "Origin" not in entries:
                    entries.append("Origin")
                    rebuilt = [(n, v) for n, v in rebuilt if n.lower() != b_vary]
                    rebuilt.append((b_vary, ", ".join(entries).encode("latin-1")))
                message["headers"] = rebuilt
            await send(message)

        await self.app(scope, receive, _fix_acao)


# =========================================================================
# 2) BaseHTTPMiddleware：统一注入 6 条安全响应头 + Vary: Origin
#    BaseHTTPMiddleware 能覆盖 StreamingResponse / FileResponse /
#    JSONResponse 以及所有 exception_handler 生成的响应。
# =========================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有响应（包括 4xx/5xx/FileResponse）注入 HTTP 安全响应头。"""

    def __init__(self, app: ASGIApp, s: "Settings") -> None:
        super().__init__(app)
        self.s = s

    @staticmethod
    def _ensure_header(headers: list[tuple[bytes, bytes]], name: str, value: str,
                       only_if_missing: bool = True) -> None:
        bn = name.lower().encode("latin-1")
        bv = value.encode("latin-1")
        if only_if_missing and any(h[0] == bn for h in headers):
            return
        headers.append((bn, bv))

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        headers: list[tuple[bytes, bytes]] = list(response.raw_headers)  # type: ignore[attr-defined]

        # -- 安全响应头：仅在缺失时写入，允许特定路由按需覆盖 --
        self._ensure_header(headers, "X-Content-Type-Options", self.s.SEC_HEADER_XCTO)
        self._ensure_header(headers, "X-Frame-Options",        self.s.SEC_HEADER_XFO)
        self._ensure_header(headers, "Content-Security-Policy", self.s.SEC_HEADER_CSP)
        self._ensure_header(headers, "Referrer-Policy",        self.s.SEC_HEADER_RP)
        self._ensure_header(headers, "Permissions-Policy",     self.s.SEC_HEADER_PERM)
        if self.s.SEC_HEADER_HSTS_MAX_AGE and request.url.scheme == "https":
            self._ensure_header(
                headers, "Strict-Transport-Security",
                f"max-age={self.s.SEC_HEADER_HSTS_MAX_AGE}; includeSubDomains",
            )
        # 动态 API 一律 no-store；若路由已显式写了 Cache-Control（如静态资源、下载）就不覆盖
        self._ensure_header(headers, "Cache-Control", self.s.SEC_HEADER_CC_API)

        # -- [CORS 兜底] 永不出现 ACAO='*' + ACAC=true 的违规组合（W3C Fetch 规范禁止） --
        b_acao = b"access-control-allow-origin"
        b_acac = b"access-control-allow-credentials"
        has_acao_star = any(
            n.lower() == b_acao and v.strip() == b"*" for n, v in headers
        )
        has_acac_true = any(
            n.lower() == b_acac and v.strip().lower() == b"true" for n, v in headers
        )
        if has_acao_star and has_acac_true:
            client_origin = request.headers.get("origin") or ""
            cleaned = []
            for n, v in headers:
                if n.lower() == b_acao:
                    if client_origin:
                        cleaned.append((b_acao, client_origin.encode("latin-1")))
                    else:
                        # 没 Origin 头 → 非跨域请求，直接去掉 ACAC=true 标记也可
                        cleaned.append((b_acao, b"null"))
                    # 同步添加/修正 Vary: Origin
                else:
                    cleaned.append((n, v))
            headers = cleaned
            # 确保 Vary: Origin（否则下一层 CDN 缓存会乱）
            existing_vary2 = ""
            for hn, hv in headers:
                if hn.lower() == b"vary":
                    existing_vary2 = hv.decode("latin-1", errors="ignore")
            entries2 = [e.strip() for e in existing_vary2.split(",") if e.strip()]
            if "Origin" not in entries2:
                entries2.append("Origin")
                headers = [(n, v) for n, v in headers if n.lower() != b"vary"]
                headers.append((b"vary", ", ".join(entries2).encode("latin-1")))

        # -- Vary: Origin（防止 CDN / 反代在跨域场景下缓存错 ACAO 值）--
        if self.s.CORS_VARY_ORIGIN:
            existing_vary = ""
            for hn, hv in headers:
                if hn.lower() == b"vary":
                    existing_vary = hv.decode("latin-1", errors="ignore")
            entries = [e.strip() for e in existing_vary.split(",") if e.strip()]
            if "Origin" not in entries:
                entries.append("Origin")
                # 先移除旧的 Vary，再追加合并后的值
                headers = [(n, v) for n, v in headers if n.lower() != b"vary"]
                headers.append((b"vary", ", ".join(entries).encode("latin-1")))

        # 写回 Response.headers（FastAPI/Starlette 会把两者对齐）
        response.raw_headers = headers  # type: ignore[attr-defined]
        # 同步更新 .headers 字典，便于下游读取
        for n, v in headers:
            response.headers[n.decode("latin-1")] = v.decode("latin-1")
        return response


# =========================================================================
# 3) 异常处理器：确保 4xx / 5xx 也带 CORS 响应头
#    (CORSMiddleware 只在请求能匹配到路由时生效；404 / 405 / RequestValidationError
#     有时路由层先抛出异常，CORS 头会缺失；这里兜底补齐)
# =========================================================================
def _cors_headers_for(origin: Optional[str]) -> dict[str, str]:
    """给错误响应追加 CORS 头（必须与上层 CORSMiddleware 规则完全一致）。

    规则：
      - settings.DEBUG=True  → 允许任意 Origin（与 CORSMiddleware 的 allow_origins=["*"] 等效）
      - 否则严格走 settings.cors_allow_origins_list 白名单
    注意：因为我们 allow_credentials=True，所以 ACAO 永远是具体 Origin，不能是 "*"。
    """
    h: dict[str, str] = {}
    if not origin:
        return h
    allowed = settings.cors_allow_origins_list
    if settings.DEBUG or "*" in allowed or origin in allowed:
        h["Access-Control-Allow-Origin"] = origin
        h["Access-Control-Allow-Credentials"] = "true"
        h["Vary"] = "Origin"
    return h


def _apply_cors_on_error_response(request: Request, response: Response) -> Response:
    """给错误响应追加 CORS + Expose-Headers（仅在没写过时）。"""
    origin = request.headers.get("origin")
    for k, v in _cors_headers_for(origin).items():
        if k not in response.headers:
            response.headers[k] = v
    # 让前端 fetch 能读到 Content-Disposition / ETag（导出下载、前端缓存时常用）
    expose = "Content-Disposition, ETag, X-Session-Id, X-Request-Id"
    if "Access-Control-Expose-Headers" not in response.headers and origin:
        response.headers["Access-Control-Expose-Headers"] = expose
    return response


def create_app() -> FastAPI:
    _setup_error_logging()
    app = FastAPI(
        title="EVOLUTION AI - 汽车A级曲面开发平台",
        description="基于NURBS引擎的汽车A级曲面开发全流程解决方案",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -- API 限流（slowapi）：登录/注册防爆破、LLM 代理防刷量（按客户端 IP） --
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # -- 安全响应头中间件（先注册 = 放在 ASGI 栈更里层；Starlette middleware 是倒序包裹） --
    app.add_middleware(SecurityHeadersMiddleware, s=settings)

    # -- CORS（显式白名单 + 暴露前端需要的头） --
    # 注意：CORSMiddleware 放在外层，保证预检请求 / 普通跨域请求都能在安全头中间件之前拿到 ACAO。
    # FastAPI 的 CORSMiddleware 在 allow_credentials=True 时会**自动**把 allow_origins=["*"]
    # 按 "回显 Origin" 方式处理（即 ACAO 永远是具体 Origin，不返回 *），因此不违反 Fetch 规范。
    # 这里我们在 DEBUG 下允许任意 Origin（便于本地调试 app.example.com 等自定义 host）；
    # 生产模式严格走 settings.cors_allow_origins_list 白名单。
    _cors_origins = (
        ["*"] if settings.DEBUG else settings.cors_allow_origins_list
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "ETag", "X-Session-Id", "X-Request-Id"],
        max_age=600,
    )

    # 注册路由
    app.include_router(project.router, prefix="/api/v1", tags=["项目管理"])
    app.include_router(model.router, prefix="/api/v1", tags=["模型管理"])
    app.include_router(workflow.router, prefix="/api/v1", tags=["工作流"])
    app.include_router(quality.router, prefix="/api/v1", tags=["质量检查"])
    app.include_router(car.router, tags=["车身生成"])
    app.include_router(build.router, tags=["模型构建"])
    app.include_router(export.router, tags=["模型导出"])
    app.include_router(variant.router, tags=["模型变体"])
    app.include_router(modify.router, tags=["模型修改"])
    app.include_router(ai.router, tags=["AI 助手"])
    app.include_router(auth.router)
    app.include_router(auth.keys_router)
    app.include_router(llm_proxy.router, tags=["LLM 模型代理"])
    app.include_router(training.router)
    app.include_router(bayes.router, tags=["贝叶斯优化"])
    app.include_router(import_export.router, tags=["导入改参导出"])
    app.include_router(texture.router, tags=["参数化纹理设计"])
    app.include_router(analytics.router)
    app.include_router(admin.router)

    # =====================================================================
    # 异常处理器：兜底补上 CORS 头（CORSMiddleware 对 404/405/校验失败可能没生效）
    # =====================================================================
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
        # 500（含路由内部 except 后手动转换的 500）统一落错误日志，
        # 保证超级管理员能在「后端错误」中看到全部服务端错误
        if exc.status_code == 500:
            logging.getLogger("evolution").error(
                "HTTP 500 on %s %s: %s", request.method,
                request.url.path, exc.detail)
        body = {"detail": exc.detail}
        hdrs = dict(exc.headers or {})
        # 405 规范要求携带 Allow 头
        if exc.status_code == 405 and "allow" not in {k.lower(): v for k, v in hdrs.items()}:
            hdrs["Allow"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
        resp = JSONResponse(status_code=exc.status_code, content=body, headers=hdrs)
        return _apply_cors_on_error_response(request, resp)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Response:
        # 默认行为就是 422 + errors；仅在外面包一层 CORS
        resp = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )
        return _apply_cors_on_error_response(request, resp)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
        # 完整堆栈写入错误日志文件，供超级管理员排查 BUG
        logging.getLogger("evolution").exception(
            "Unhandled error on %s %s", request.method,
            request.url.path, exc_info=exc)
        # 500 绝对不能暴露堆栈；生产只给一条通用 detail
        detail = "Internal Server Error"
        if settings.DEBUG:
            detail = f"{type(exc).__name__}: {exc}"
        resp = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail},
        )
        return _apply_cors_on_error_response(request, resp)

    @app.on_event("startup")
    def startup():
        init_db()
        settings.models_path.mkdir(parents=True, exist_ok=True)
        settings.reports_path.mkdir(parents=True, exist_ok=True)
        settings.exports_path.mkdir(parents=True, exist_ok=True)

    @app.get("/api/v1/health")
    def health_check():
        return {"status": "healthy", "service": "EVOLUTION AI"}

    @app.get("/api/v1/i18n/config")
    def get_i18n_config():
        return {
            "default_language": settings.DEFAULT_LANGUAGE,
            "supported_languages": settings.supported_languages_list,
            "current_language": settings.DEFAULT_LANGUAGE,
        }

    return app


# -- ASGI 包装栈（uvicorn 调用入口）：最外层 → 最内层（FastAPI app） --
#   顺序（请求自上而下，响应自下而上）：
#     1. StripServerHeaderMiddleware        → 去除 server: uvicorn 信息泄露
#     2. NormalizeCorsAcaoMiddleware         → 拦截 ACAO='*' + ACAC=true 违规组合
#     3. FastAPI(create_app())
#        → CORSMiddleware (外层)
#        → SecurityHeadersMiddleware (内层)
#        → 路由/业务/异常处理器
_fastapi_app = create_app()
# 先在 FastAPI 外面包 ACAO 校正器
_app_with_acao_norm: ASGIApp = NormalizeCorsAcaoMiddleware(_fastapi_app)
# 再在最外面包 server 头脱敏（因为 uvicorn 在 server 层写完 server 头后先进入最外层）
if settings.HIDE_SERVER_HEADER:
    app: ASGIApp = StripServerHeaderMiddleware(_app_with_acao_norm, enable=True)
else:
    app = _app_with_acao_norm
