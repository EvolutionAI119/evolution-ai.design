"""安全围栏 · 应急响应层：能力级应急开关（killswitch）

「确保人工智能始终处于人类控制之下」的工具化落地：每个高风险能力
（LLM 代理 / 文件导入等）绑定一个配置开关，管理员在发现恶用/滥用/失控
迹象时，修改 .env（FENCE_DISABLE_* = true）并重启即可立即停摆该能力，
无需改代码、无需部署。

用法（路由端点）：
    @router.post("/...", dependencies=[Depends(killswitch_dependency(
        "LLM 代理", "FENCE_DISABLE_LLM_PROXY"))])

测试用法：monkeypatch settings 对应属性后直接调用端点。
"""
from __future__ import annotations

from fastapi import HTTPException

from ..config import settings


def killswitch_dependency(capability: str, setting_name: str):
    """生成能力级应急开关 FastAPI 依赖。

    开关为 true 时端点返回 503（附开关名，便于运维定位），
    同时不抛出审计事件——开关状态是管理员主动行为，不是攻击信号。
    """
    def _check() -> None:
        if settings.FENCE_ENABLED and getattr(settings, setting_name, False):
            raise HTTPException(
                status_code=503,
                detail=f"「{capability}」已被管理员临时停用"
                       f"（应急开关 {setting_name}）")
    return _check
