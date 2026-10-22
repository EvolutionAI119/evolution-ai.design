"""安全围栏 · 技术监测层：结构化安全审计事件流

以 JSONL（每行一个 JSON 对象）落盘 backend/logs/security-audit.jsonl，
经 RotatingFileHandler 滚动（FENCE_AUDIT_MAX_BYTES / FENCE_AUDIT_BACKUP_COUNT）。

事件命名约定（<域>.<对象>.<结果>）：
  auth.login.failure      登录失败（爆破预警信号）
  auth.register           新账户注册
  authz.denied            401/403 越权访问尝试
  ratelimit.hit           限流触发（滥用预警信号）
  llm.request             LLM 代理调用（不含提示词内容，仅元数据）
  llm.guard.body_limit    LLM 请求体超限（防滥用）
  llm.guard.messages      LLM 消息条数超限
  llm.guard.chars         LLM 总字符超限
  llm.guard.injection     命中提示注入特征（风险预警）
  upload.rejected         上传文件超限被拒（防失控/资源滥用）
  fence.maintenance       维护模式拦截
  fence.body_limit        全局请求体超限

隐私边界：仅记录安全事件元数据（IP/路径/计数/特征名），
不记录提示词正文、响应内容或用户敏感数据。
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextvars import ContextVar
from typing import Any, Optional

#: 请求追踪上下文（由 middleware.RequestContextMiddleware 填充）
request_id_var: ContextVar[str] = ContextVar("fence_request_id", default="")

_audit_logger: Optional[logging.Logger] = None
_audit_lock = threading.Lock()


def _default_audit_path() -> Path:
    """审计文件默认位置：backend/logs/security-audit.jsonl（logs/ 已 gitignore）"""
    return Path(__file__).resolve().parents[2] / "logs" / "security-audit.jsonl"


def configure_audit(path: Optional[Path] = None) -> Optional[logging.Logger]:
    """初始化（幂等）审计专用 logger；显式传 path 可重定向（测试隔离用）。

    返回底层 logger；FENCE_AUDIT_ENABLED=false 时返回 None（emit 静默跳过）。
    测试重复调用 configure_audit 会重建 handler——由 _audit_lock 串行化。
    """
    global _audit_logger
    from ..config import settings

    if not settings.FENCE_AUDIT_ENABLED:
        return None
    with _audit_lock:
        target = Path(path) if path else _default_audit_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("evolution.fence.audit")
        # 幂等：已配置且同路径则直接复用
        for h in logger.handlers:
            if isinstance(h, RotatingFileHandler) and Path(h.baseFilename) == target:
                _audit_logger = logger
                return logger
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            target, maxBytes=settings.FENCE_AUDIT_MAX_BYTES,
            backupCount=settings.FENCE_AUDIT_BACKUP_COUNT, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        _audit_logger = logger
        return logger


def _safe_str(value: Any, cap: int = 256) -> str:
    return str(value)[:cap]


def emit(event: str, *, level: str = "info", ip: Optional[str] = None,
         path: Optional[str] = None, method: Optional[str] = None,
         user_id: Optional[int] = None, **detail: Any) -> None:
    """写入一条安全审计事件（永不抛出——审计失败不阻断业务主流程）。

    每行 JSON 字段：ts / event / level / request_id / ip / path / method /
    user_id / detail。detail 仅接受标量或短列表（长度截断到 256 字符/项）。
    """
    logger = _audit_logger
    if logger is None:
        try:
            logger = configure_audit()
        except Exception:
            return
        if logger is None:
            return  # FENCE_AUDIT_ENABLED=false：显式关闭审计流
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
        "level": level,
        "request_id": request_id_var.get() or None,
        "ip": _safe_str(ip) if ip else None,
        "path": _safe_str(path) if path else None,
        "method": method,
        "user_id": user_id,
    }
    if detail:
        record["detail"] = {
            k: (_safe_str(v) if isinstance(v, (str, bytes)) else v)
            for k, v in detail.items() if v is not None
        }
    try:
        logger.log(
            logging.WARNING if level == "warning" else logging.INFO,
            json.dumps(record, ensure_ascii=False))
    except Exception:
        logging.getLogger("evolution").warning(
            "安全审计事件写入失败: %s", event, exc_info=True)


def read_tail(path: Optional[Path] = None, lines: int = 200) -> tuple[list[str], bool]:
    """倒读审计文件尾部 N 行（供 /admin/security-events 观测接口）。

    返回 (行列表, 是否被截断)。文件不存在时返回 ([], False)。
    """
    target = Path(path) if path else _default_audit_path()
    if not target.exists():
        return [], False
    collected: list[bytes] = []
    truncated = False
    with target.open("rb") as f:
        f.seek(0, 2)
        position = f.tell()
        while position > 0 and len(collected) <= lines:
            block_size = min(8192, position)
            position -= block_size
            f.seek(position)
            block = f.read(block_size)
            collected = block.splitlines() + collected
            truncated = position > 0 and len(collected) > lines
    tail = collected[-lines:]
    decoded = [chunk.decode("utf-8", errors="replace") for chunk in tail]
    return decoded, truncated
