"""API 限流：slowapi Limiter 单例 + 签名修复装饰器（按客户端 IP 限流）

适用端点：
  - auth.py    /login /register          → 防口令爆破与批量注册（RATE_LIMIT_AUTH）
  - llm_proxy.py 三个 POST 转发端点       → 防 LLM 滥用刷量（RATE_LIMIT_AI）

RATE_LIMIT_ENABLED=false 时整体禁用（pytest 在 conftest.py 导入 app 前设置）。

兼容性说明（__signature__ 修复的原因）：
  路由模块使用 `from __future__ import annotations`（PEP 563，注解为字符串）。
  slowapi 的 @limiter.limit 经 functools.wraps 包装后，FastAPI 解析路由签名时
  使用 wrapper.__globals__（= slowapi 模块命名空间）求值字符串注解，
  LoginRequest 等模型在该命名空间不可见 → Pydantic 请求体被误判为
  query 参数（表现为 422 {"loc":["query","req"]}）。
  本模块 limit() 在包装后回填「已解析为真实类型对象」的 __signature__，
  FastAPI 对非字符串注解不再做全局求值，从而绕开该问题。
"""
import inspect
import typing

from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings

limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)


def limit(limit_value: str):
    """带 FastAPI 签名修复的 slowapi 限流装饰器（用法同 limiter.limit）。

    被装饰端点必须包含 ``request: Request`` 形参（slowapi 要求）。
    """
    def decorator(func):
        wrapped = limiter.limit(limit_value)(func)
        try:
            hints = typing.get_type_hints(func)
            sig = inspect.signature(func)
            params = []
            for p in sig.parameters.values():
                if p.annotation is not inspect.Parameter.empty:
                    p = p.replace(annotation=hints.get(p.name,
                                                       inspect.Parameter.empty))
                params.append(p)
            wrapped.__signature__ = sig.replace(
                parameters=params,
                return_annotation=hints.get("return", inspect.Signature.empty),
            )
        except Exception:
            # 签名解析失败时保留 slowapi 原始包装（不影响启动，仅可能回到上述兼容性问题）
            pass
        return wrapped
    return decorator
