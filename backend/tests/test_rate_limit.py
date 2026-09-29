"""API 限流（slowapi）测试 —— Phase 5a 安全加固。

覆盖：
  1. pytest 进程内 RATE_LIMIT_ENABLED=false 生效：生产 app 连续登录不触发 429
  2. 限流启用时超过阈值触发 429，且 429 响应仍带安全响应头
     （SecurityHeadersMiddleware 对所有响应注入）
  3. limiter 已注册到 app.state，RateLimitExceeded 异常处理器已挂载
  4. /login /register 与 LLM 三个转发端点均已挂限流装饰器
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.main import SecurityHeadersMiddleware, _fastapi_app
from app.rate_limit import limiter


# ── 1) 测试进程内限流已禁用 ──────────────────────────────────────────

def test_limiter_disabled_in_pytest_process():
    assert settings.RATE_LIMIT_ENABLED is False
    assert limiter.enabled is False


def test_login_not_rate_limited_when_disabled(client):
    # 连续 12 次失败登录（> 10/minute 阈值）：禁用状态下不应出现 429
    for _ in range(12):
        resp = client.post("/api/v1/auth/login",
                           json={"email": "nobody@example.com", "password": "wrong"})
        assert resp.status_code == 401


# ── 2) 限流启用时的 429 行为（独立 mini app，避免污染全局 limiter） ──

def _mini_app() -> FastAPI:
    app = FastAPI()
    mini_limiter = Limiter(key_func=get_remote_address, enabled=True)
    app.state.limiter = mini_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SecurityHeadersMiddleware, s=settings)

    @app.get("/ping")
    @mini_limiter.limit("2/minute")
    def ping(request: Request):
        return {"ok": True}

    return app


def test_rate_limit_triggers_429_with_security_headers():
    c = TestClient(_mini_app())
    assert c.get("/ping").status_code == 200
    assert c.get("/ping").status_code == 200
    resp = c.get("/ping")
    assert resp.status_code == 429
    # 429 也必须带安全响应头（SecurityHeadersMiddleware 全响应覆盖）
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in {k.lower() for k in resp.headers.keys()}
    # 限流提示体
    assert "rate limit" in resp.text.lower()


# ── 3) limiter 注册与异常处理器 ──────────────────────────────────────

def test_limiter_registered_on_app_state():
    assert _fastapi_app.state.limiter is limiter
    assert RateLimitExceeded in _fastapi_app.exception_handlers


# ── 4) 关键端点均已挂限流装饰器 ──────────────────────────────────────

def test_auth_and_llm_endpoints_are_wrapped_by_limiter():
    target_names = {"login", "register",
                    "chat_completions", "embeddings", "images_generations"}
    found = {}
    for route in _fastapi_app.routes:
        fn = getattr(route, "endpoint", None)
        name = getattr(fn, "__name__", None)
        if name in target_names:
            # slowapi 的 @limiter.limit 经 functools.wraps 包装，保留 __wrapped__
            found[name] = hasattr(fn, "__wrapped__")
    assert found == {name: True for name in target_names}
