"""认证路由：用户注册 / 登录(JWT) / 当前用户 / API Key 管理 / 微信扫码登录"""
from __future__ import annotations

import re
import secrets
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import ApiKey, User, get_db
from ..security import (create_access_token, decrypt_api_key, encrypt_api_key,
                        get_current_user, hash_password, verify_password)

router = APIRouter(prefix="/api/v1/auth", tags=["用户认证"])
keys_router = APIRouter(prefix="/api/v1/api-keys", tags=["API Key 管理"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SUPPORTED_PROVIDERS = ["ernie", "qwen", "hunyuan", "doubao", "deepseek", "kimi", "siliconflow"]


# ── 请求/响应模型 ──────────────────────────────

class RegisterRequest(BaseModel):
    email: str = Field(..., description="邮箱（登录账号）")
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    is_admin: bool
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class ApiKeyStatus(BaseModel):
    provider: str
    configured: bool
    masked: Optional[str] = None
    updated_at: Optional[datetime] = None


class ApiKeySetRequest(BaseModel):
    api_key: str = Field(..., min_length=4, description="提供商 API Key/Token")


def _mask(key: str) -> str:
    """脱敏显示：sk-****后4位"""
    tail = key[-4:] if len(key) >= 4 else key
    return f"****{tail}"


def _to_user_info(u: User) -> UserInfo:
    return UserInfo(id=u.id, email=u.email, username=u.username,
                    is_admin=u.is_admin, created_at=u.created_at)


# ── 注册 / 登录 / 当前用户 ─────────────────────

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    user = User(
        email=email,
        username=req.username.strip(),
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    from ..config import settings
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token,
                         expires_in=settings.JWT_EXPIRE_MINUTES * 60,
                         user=_to_user_info(user))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被停用")

    from ..config import settings
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token,
                         expires_in=settings.JWT_EXPIRE_MINUTES * 60,
                         user=_to_user_info(user))


@router.get("/me", response_model=UserInfo)
def me(current: User = Depends(get_current_user)):
    return _to_user_info(current)


# ── API Key 管理（需登录） ─────────────────────

@keys_router.get("", response_model=List[ApiKeyStatus])
def list_keys(current: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    result = []
    by_provider = {k.provider: k for k in current.api_keys}
    for p in SUPPORTED_PROVIDERS:
        rec = by_provider.get(p)
        if rec:
            plain = decrypt_api_key(rec.key_encrypted)
            result.append(ApiKeyStatus(provider=p, configured=True,
                                       masked=_mask(plain),
                                       updated_at=rec.updated_at))
        else:
            result.append(ApiKeyStatus(provider=p, configured=False))
    return result


@keys_router.put("/{provider}", response_model=ApiKeyStatus)
def set_key(provider: str, req: ApiKeySetRequest,
            current: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400,
                            detail=f"不支持的提供商: {provider}")
    encrypted = encrypt_api_key(req.api_key.strip())
    record = (db.query(ApiKey)
              .filter(ApiKey.user_id == current.id,
                      ApiKey.provider == provider).first())
    if record:
        record.key_encrypted = encrypted
    else:
        record = ApiKey(user_id=current.id, provider=provider,
                        key_encrypted=encrypted)
        db.add(record)
    db.commit()
    db.refresh(record)
    return ApiKeyStatus(provider=provider, configured=True,
                        masked=_mask(req.api_key.strip()),
                        updated_at=record.updated_at)


@keys_router.delete("/{provider}")
def delete_key(provider: str,
               current: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    record = (db.query(ApiKey)
              .filter(ApiKey.user_id == current.id,
                      ApiKey.provider == provider).first())
    if record is None:
        raise HTTPException(status_code=404, detail="未配置该提供商的 Key")
    db.delete(record)
    db.commit()
    return {"success": True, "provider": provider}


# ── 微信扫码登录（开放平台 OAuth2 授权码流程） ──────────

_WECHAT_AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
_WECHAT_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
_WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"
# state 防 CSRF：state -> 过期时间戳（10 分钟有效）
_wechat_states: dict[str, float] = {}


def _wechat_enabled() -> bool:
    return bool(settings.WECHAT_APPID and settings.WECHAT_SECRET)


def _wechat_redirect_uri() -> str:
    return (settings.WECHAT_REDIRECT_URI
            or "http://127.0.0.1:8000/api/v1/auth/wechat/callback")


def _cleanup_states() -> None:
    now = time.time()
    for k in [k for k, exp in _wechat_states.items() if exp < now]:
        _wechat_states.pop(k, None)


@router.get("/methods")
def auth_methods():
    """报告可用的登录方式，前端据此隐藏未配置的第三方登录入口。"""
    return {
        "password": True,
        "wechat_qr": _wechat_enabled(),
        "mp_oauth": _mp_enabled(),
    }


@router.get("/wechat/qr")
def wechat_qr():
    """返回微信扫码授权 URL；未配置 AppID/Secret 时 503（前端据此隐藏入口）。"""
    if not _wechat_enabled():
        raise HTTPException(status_code=503,
                            detail="微信登录未配置：请在 .env 中设置 "
                                   "WECHAT_APPID / WECHAT_SECRET")
    _cleanup_states()
    state = secrets.token_urlsafe(16)
    _wechat_states[state] = time.time() + 600
    url = (
        f"{_WECHAT_AUTHORIZE_URL}?appid={settings.WECHAT_APPID}"
        f"&redirect_uri={quote(_wechat_redirect_uri(), safe='')}"
        f"&response_type=code&scope=snsapi_login"
        f"&state={state}#wechat_redirect"
    )
    return {"auth_url": url, "state": state}


def _wechat_popup_html(title: str, message: str, payload_js: str) -> HTMLResponse:
    """回调后返回的极简页面：postMessage 通知登录窗口后自动关闭。

    postMessage 的 targetOrigin 指向前端地址（回调页在后端域，opener 是前端域）。
    """
    import json as _json
    target = _json.dumps(settings.FRONTEND_URL)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;text-align:center;padding-top:80px;color:#333}}</style>
</head><body>
<h3>{title}</h3><p>{message}</p>
<script>
(function() {{
  try {{
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage({payload_js}, {target});
    }}
  }} catch (e) {{}}
  setTimeout(function() {{ window.close(); }}, 1200);
}})();
</script>
</body></html>"""
    return HTMLResponse(
        content=html,
        headers={"Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'"},
    )


@router.get("/wechat/callback")
async def wechat_callback(code: str = "", state: str = "",
                          db: Session = Depends(get_db)):
    """微信回调：code 换 access_token → 拉取用户信息 → 绑定/创建用户 → 发 JWT。"""
    if not _wechat_enabled():
        raise HTTPException(status_code=503, detail="微信登录未配置")

    _cleanup_states()
    if not code:
        return _wechat_popup_html("微信登录失败", "缺少授权码 code", '{"type":"wechat_auth","ok":false,"error":"missing_code"}')
    if not state or _wechat_states.pop(state, None) is None:
        return _wechat_popup_html("微信登录失败", "state 无效或已过期", '{"type":"wechat_auth","ok":false,"error":"invalid_state"}')

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.get(_WECHAT_TOKEN_URL, params={
                "appid": settings.WECHAT_APPID,
                "secret": settings.WECHAT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            })
            data = token_resp.json()
    except httpx.HTTPError:
        return _wechat_popup_html("微信登录失败", "无法连接微信服务，请稍后重试", '{"type":"wechat_auth","ok":false,"error":"network"}')

    openid = data.get("openid")
    if not openid:
        return _wechat_popup_html(
            "微信登录失败",
            data.get("errmsg", "code 无效或已过期"),
            '{"type":"wechat_auth","ok":false,"error":"code_rejected"}')

    unionid = data.get("unionid") or ""
    nickname = ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            info_resp = await client.get(_WECHAT_USERINFO_URL, params={
                "access_token": data["access_token"],
                "openid": openid,
            })
            nickname = (info_resp.json() or {}).get("nickname") or ""
    except httpx.HTTPError:
        pass  # 昵称获取失败不阻断登录

    # 优先按 unionid / openid 查找已有用户；否则自动创建
    q = db.query(User)
    user = None
    if unionid:
        user = q.filter(User.wechat_unionid == unionid).first()
    if user is None:
        user = db.query(User).filter(User.wechat_openid == openid).first()
    if user is None:
        user = User(
            email=f"wx_{openid}@wechat.local",
            username=nickname or "微信用户",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            wechat_unionid=unionid or None,
            wechat_openid=openid,
        )
        db.add(user)
    else:
        if unionid and not user.wechat_unionid:
            user.wechat_unionid = unionid
        if not user.wechat_openid:
            user.wechat_openid = openid
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    import json
    payload = json.dumps({
        "type": "wechat_auth", "ok": True,
        "token": token, "user": _to_user_info(user).model_dump(mode="json"),
    })
    return _wechat_popup_html("微信登录成功", "正在返回平台……", payload)


# ── 微信公众号网页授权登录（snsapi_userinfo，测试号即可用） ──────────
# 授权页地址与开放平台扫码不同：connect/oauth2/authorize
_MP_AUTHORIZE_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
# code 换 token / 拉取用户信息的接口与开放平台相同（sns/oauth2/*）
_mp_states: dict[str, float] = {}
# 轮询结果存储：state -> {"result": dict, "expire": 时间戳}
# 回调完成后落地，供 PC 端 /mp/poll 一次性读走（PC 扫码 + 轮询登录流程）
_mp_results: dict[str, dict] = {}
# 前端登录会话票据：ticket -> {"state": str, "expire": 时间戳}
# 同一浏览器会话内多次点击/开关二维码均复用同一票据，
# 手机扫码结果按 state 落地后 PC 按 ticket 必能取到，杜绝会话错配
_mp_tickets: dict[str, dict] = {}


def _mp_enabled() -> bool:
    return bool(settings.MP_APPID and settings.MP_SECRET)


def _mp_redirect_uri() -> str:
    return (settings.MP_REDIRECT_URI
            or "http://127.0.0.1:8000/api/v1/auth/mp/callback")


def _cleanup_mp_states() -> None:
    now = time.time()
    for k in [k for k, exp in _mp_states.items() if exp < now]:
        _mp_states.pop(k, None)


@router.get("/mp/authorize")
def mp_authorize(ticket: str = ""):
    """返回公众号网页授权 URL；未配置 MP_APPID/MP_SECRET 时 503。

    ticket 为前端会话标识（sessionStorage）：会话内若已有待扫码的
    state 则直接复用，保证「多次点击 / 多个二维码」与 PC 轮询始终对应。
    """
    if not _mp_enabled():
        raise HTTPException(status_code=503,
                            detail="公众号登录未配置：请在 .env 中设置 "
                                   "MP_APPID / MP_SECRET（可用免费测试号）")
    now = time.time()
    _cleanup_mp_states()
    ticket_entry = _mp_tickets.get(ticket) if ticket else None
    # 复用条件：票据存在、未过期、其 state 仍在等待扫码
    if (ticket_entry and ticket_entry["expire"] > now
            and ticket_entry["state"] in _mp_states):
        state = ticket_entry["state"]
        _mp_states[state] = now + 600
        ticket_entry["expire"] = now + 600
    else:
        state = secrets.token_urlsafe(16)
        _mp_states[state] = now + 600
        ticket = ticket or secrets.token_urlsafe(16)
        _mp_tickets[ticket] = {"state": state, "expire": now + 600}
    url = (
        f"{_MP_AUTHORIZE_URL}?appid={settings.MP_APPID}"
        f"&redirect_uri={quote(_mp_redirect_uri(), safe='')}"
        f"&response_type=code&scope=snsapi_userinfo"
        f"&state={state}#wechat_redirect"
    )
    return {"auth_url": url, "state": state, "ticket": ticket}


def _mp_finish(state: str, result: dict) -> None:
    """回调完成后落地结果，供 PC 端轮询一次性读走（10 分钟有效）。"""
    if state:
        _mp_results[state] = {"result": result, "expire": time.time() + 600}


@router.get("/mp/poll")
def mp_poll_by_ticket(ticket: str = ""):
    """按前端会话票据轮询授权结果：pending / done / expired。"""
    if not ticket:
        raise HTTPException(status_code=400, detail="缺少 ticket 参数")
    now = time.time()
    for k in [k for k, v in _mp_results.items() if v["expire"] < now]:
        _mp_results.pop(k, None)
    entry = _mp_tickets.get(ticket)
    if not entry:
        return {"status": "expired"}
    state = entry["state"]
    # 已完成：结果一次性读走
    done = _mp_results.pop(state, None)
    if done:
        return {"status": "done", "result": done["result"]}
    # 等待扫码
    if entry["expire"] > now and _mp_states.get(state, 0) > now:
        return {"status": "pending"}
    _mp_tickets.pop(ticket, None)
    return {"status": "expired"}


@router.get("/mp/poll/{state}")
def mp_poll(state: str):
    """PC 端轮询公众号授权结果。

    pending：等待用户扫码确认；done：返回结果并一次性清除；
    expired：state 过期（10 分钟）或不存在。
    """
    now = time.time()
    for k in [k for k, v in _mp_results.items() if v["expire"] < now]:
        _mp_results.pop(k, None)
    entry = _mp_results.pop(state, None)
    if entry:
        return {"status": "done", "result": entry["result"]}
    expire = _mp_states.get(state)
    if expire is not None and expire > now:
        return {"status": "pending"}
    _mp_states.pop(state, None)
    return {"status": "expired"}


@router.get("/mp/callback")
async def mp_callback(request: Request, code: str = "", state: str = "",
                      db: Session = Depends(get_db)):
    """公众号网页授权回调：code 换 token → 拉取用户信息 → 绑定/创建用户 → 发 JWT。"""
    if not _mp_enabled():
        raise HTTPException(status_code=503, detail="公众号登录未配置")

    _cleanup_mp_states()
    if not code:
        _mp_finish(state, {"type": "mp_auth", "ok": False, "error": "missing_code"})
        return _wechat_popup_html("公众号登录失败", "缺少授权码 code",
                                  '{"type":"mp_auth","ok":false,"error":"missing_code"}')
    if not state or _mp_states.pop(state, None) is None:
        return _wechat_popup_html("公众号登录失败", "state 无效或已过期",
                                  '{"type":"mp_auth","ok":false,"error":"invalid_state"}')

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.get(_WECHAT_TOKEN_URL, params={
                "appid": settings.MP_APPID,
                "secret": settings.MP_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            })
            data = token_resp.json()
    except httpx.HTTPError:
        _mp_finish(state, {"type": "mp_auth", "ok": False, "error": "network"})
        return _wechat_popup_html("公众号登录失败", "无法连接微信服务，请稍后重试",
                                  '{"type":"mp_auth","ok":false,"error":"network"}')

    openid = data.get("openid")
    if not openid:
        _mp_finish(state, {"type": "mp_auth", "ok": False, "error": "code_rejected"})
        return _wechat_popup_html("公众号登录失败",
                                  data.get("errmsg", "code 无效或已过期"),
                                  '{"type":"mp_auth","ok":false,"error":"code_rejected"}')

    unionid = data.get("unionid") or ""
    nickname = ""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            info_resp = await client.get(_WECHAT_USERINFO_URL, params={
                "access_token": data["access_token"],
                "openid": openid,
            })
            nickname = (info_resp.json() or {}).get("nickname") or ""
    except httpx.HTTPError:
        pass  # 昵称获取失败不阻断登录

    # 优先按 unionid / openid 查找；否则自动创建（与开放平台扫码共用用户体系）
    user = None
    if unionid:
        user = db.query(User).filter(User.wechat_unionid == unionid).first()
    if user is None:
        user = db.query(User).filter(User.wechat_openid == openid).first()
    if user is None:
        user = User(
            email=f"mp_{openid}@wechat.local",
            username=nickname or "公众号用户",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            wechat_unionid=unionid or None,
            wechat_openid=openid,
        )
        db.add(user)
    else:
        if unionid and not user.wechat_unionid:
            user.wechat_unionid = unionid
        if not user.wechat_openid:
            user.wechat_openid = openid
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    import json
    result = {
        "type": "mp_auth", "ok": True,
        "token": token, "user": _to_user_info(user).model_dump(mode="json"),
    }
    # 落地结果供 PC 端轮询
    _mp_finish(state, result)
    # 手机微信扫码场景：不能重定向到 127.0.0.1（手机访问不到电脑），
    # 只显示成功提示页，PC 端轮询读到结果后自行登录
    if "MicroMessenger" in (request.headers.get("user-agent") or ""):
        return HTMLResponse(
            content="""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录成功</title>
<style>body{margin:0;font-family:-apple-system,sans-serif;background:#0b0b12;
color:#fff;display:flex;min-height:100vh;align-items:center;justify-content:center}
.box{text-align:center;padding:32px}
.ok{width:76px;height:76px;margin:0 auto 22px;border-radius:50%;
background:#4ade80;display:flex;align-items:center;justify-content:center}
.ok svg{width:40px;height:40px}
h2{margin:0 0 10px;font-size:20px}
p{margin:0;font-size:14px;line-height:1.7;color:rgba(255,255,255,.55)}</style>
</head><body><div class="box">
<div class="ok"><svg viewBox="0 0 24 24" fill="none" stroke="#06120a" stroke-width="3"
stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
<h2>登录成功</h2>
<p>已确认授权，请返回电脑端<br>EVOLUTION AI 将自动完成登录</p>
</div></body></html>""",
        )
    # PC 弹窗场景兜底：postMessage 通知后自动关闭
    payload = json.dumps(result)
    return _wechat_popup_html("公众号登录成功", "请返回电脑端查看，本页面可关闭", payload)
