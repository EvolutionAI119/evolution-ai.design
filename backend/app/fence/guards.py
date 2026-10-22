"""安全围栏 · 防恶用/滥用层：输入侧守卫

三类守卫：
  guard_llm_payload   LLM 代理 payload 守卫——请求体字节 / messages 条数 /
                      总字符三重上限 + 提示注入特征扫描（默认仅记录预警，
                      FENCE_BLOCK_INJECTION=true 时升级为阻断，循序渐进）
  scan_injection      提示注入特征检测（中英双语模式库）
  read_upload_limited 上传文件分块限读（不信任 file.size，按实际字节拦截）

注入检测采用「记录优先、阻断可选」策略：设计/工程语义下正常讨论
（如「如何防提示注入」）不应被误伤；高频命中属风险预警信号，
由审计事件流供管理员研判后再决定是否开阻断。
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import HTTPException, UploadFile

from ..config import settings
from . import audit


def _fence_413(detail: str, event: str, **detail_fields) -> HTTPException:
    audit.emit(event, level="warning", **detail_fields)
    return HTTPException(status_code=413, detail=detail)


# ── 提示注入特征库（中英双语，大小写不敏感） ─────────────
_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("en.ignore_instructions", r"ignore\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts|rules|directions)"),
        ("en.disregard_system", r"disregard\s+(?:all\s+)?(?:previous|prior|your)\s+(?:instructions|guidelines|system\s+prompt)"),
        ("en.reveal_system_prompt", r"(?:reveal|show|print|repeat|output|leak)\s+(?:me\s+)?(?:your\s+)?(?:full\s+|initial\s+|original\s+|hidden\s+)?system\s+prompt"),
        ("en.dan_jailbreak", r"\b(?:do\s+anything\s+now|dan\s+mode|developer\s+mode\s+enabled|jailbreak)\b"),
        ("en.roleplay_unrestricted", r"you\s+(?:are|will\s+(?:be|act\s+as))\s+(?:now\s+)?(?:an?\s+)?(?:unrestricted|uncensored|unfiltered)"),
        ("zh.override_instructions", r"(?:忽略|无视)(?:之前|以上|上面|先前|所有)?的?(?:指令|提示词?|设定|规则)"),
        ("zh.reveal_system_prompt", r"(?:输出|泄露|打印|告诉我|展示)(?:你的)?(?:完整|初始|原始|隐藏)?的?系统提示词?"),
        ("zh.unrestricted_role", r"(?:你现在|从现在开始你)(?:是|扮演|进入).{0,6}(?:无限制|无道德|不受约束|越狱|开发者模式)"),
        ("zh.jailbreak_keyword", r"越狱模式|破解限制|解除限制"),
    )
)


def scan_injection(text: str) -> Optional[str]:
    """扫描单段文本是否命中注入特征；命中返回特征名，未命中返回 None。"""
    if not text:
        return None
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return name
    return None


def _llm_texts(payload: dict) -> list[str]:
    """从 payload 中提取供扫描的文本（chat messages / embeddings input / images prompt）。"""
    texts: list[str] = []
    messages = payload.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):  # 多模态 content parts
                    for part in content:
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            texts.append(part["text"])
    inp = payload.get("input")
    if isinstance(inp, str):
        texts.append(inp)
    elif isinstance(inp, list):
        texts.extend(t for t in inp if isinstance(t, str))
    if isinstance(payload.get("prompt"), str):
        texts.append(payload["prompt"])
    return texts


def guard_llm_payload(payload: dict, *, provider: str, capability: str,
                      ip: Optional[str] = None, path: Optional[str] = None) -> None:
    """LLM 代理 payload 守卫（在透传上游前调用）。

    超限 → 413 + 审计事件；命中注入特征 → 默认仅记录 WARN 预警，
    FENCE_BLOCK_INJECTION=true 时 400 阻断。
    """
    if not settings.FENCE_ENABLED:
        return

    body_bytes = len(str(payload).encode("utf-8"))
    if body_bytes > settings.FENCE_LLM_MAX_BODY_BYTES:
        raise _fence_413(
            f"请求体超过上限（{settings.FENCE_LLM_MAX_BODY_BYTES // 1024}KB）",
            "llm.guard.body_limit", provider=provider, capability=capability,
            ip=ip, path=path, body_bytes=body_bytes)

    messages = payload.get("messages")
    if isinstance(messages, list) and len(messages) > settings.FENCE_LLM_MAX_MESSAGES:
        raise _fence_413(
            f"messages 条数超过上限（{settings.FENCE_LLM_MAX_MESSAGES}）",
            "llm.guard.messages", provider=provider, capability=capability,
            ip=ip, path=path, count=len(messages))

    total_chars = sum(len(t) for t in _llm_texts(payload))
    if total_chars > settings.FENCE_LLM_MAX_TOTAL_CHARS:
        raise _fence_413(
            f"输入总字符超过上限（{settings.FENCE_LLM_MAX_TOTAL_CHARS}）",
            "llm.guard.chars", provider=provider, capability=capability,
            ip=ip, path=path, total_chars=total_chars)

    if settings.FENCE_INJECTION_SCAN_ENABLED:
        for text in _llm_texts(payload):
            hit = scan_injection(text)
            if hit:
                audit.emit("llm.guard.injection", level="warning",
                           ip=ip, path=path, provider=provider,
                           capability=capability, pattern=hit,
                           blocked=settings.FENCE_BLOCK_INJECTION)
                if settings.FENCE_BLOCK_INJECTION:
                    raise HTTPException(
                        status_code=400,
                        detail="请求包含被安全围栏识别为提示注入的内容，已拦截")
                break  # 记录模式下每请求至多一条预警，避免刷屏


async def read_upload_limited(file: UploadFile, max_bytes: Optional[int] = None) -> bytes:
    """分块限读上传文件：按实际字节拦截，防内存耗尽（防失控）。

    超限 → 413 + upload.rejected 审计事件。文件名与大小元数据入审计，
    不落文件内容。
    """
    limit = max_bytes if max_bytes is not None else settings.FENCE_UPLOAD_MAX_BYTES
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            audit.emit("upload.rejected", level="warning",
                       path=f"upload:{file.filename or 'unnamed'}",
                       size_bytes=total, limit=limit)
            raise HTTPException(
                status_code=413,
                detail=f"上传文件过大（上限 {limit // 1024 // 1024}MB），已被安全围栏拦截")
        chunks.append(chunk)
    return b"".join(chunks)
