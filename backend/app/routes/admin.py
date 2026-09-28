"""分级权限 · 管理后台路由

角色边界：
- admin（管理员）：查看用户列表（仅安全字段）、查看全部登录记录，用于排查问题。
  不返回任何用户敏感数据（密码哈希 / API Key 一律不下发）。
- superadmin（超级管理员）：账户修复（启停 / 重置密码 / 调整角色）、
  查看后端错误日志与审计日志。所有写操作均落 AdminAuditLog，详细可追溯。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import (AdminAuditLog, LoginRecord, User, get_db)
from ..security import (ROLE_ADMIN, ROLE_SUPERADMIN, ROLE_USER,
                        hash_password, require_admin, require_superadmin,
                        user_is_admin)

router = APIRouter(prefix="/api/v1/admin", tags=["管理后台"])

# 后端错误日志文件（与 main.py 中 FileHandler 的输出路径保持一致）
ERROR_LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "backend-error.log"
ALLOWED_ROLES = (ROLE_USER, ROLE_ADMIN, ROLE_SUPERADMIN)


# ── 响应/请求模型 ─────────────────────────────

class AdminUserOut(BaseModel):
    """用户安全视图：绝不含密码哈希等敏感字段。"""
    id: int
    email: str
    username: str
    role: str
    is_admin: bool
    is_active: bool
    created_at: Optional[datetime] = None


class LoginRecordOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    email: str
    success: bool
    reason: Optional[str] = None
    method: str
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogOut(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: str
    target_id: Optional[int] = None
    detail_json: str
    ip: Optional[str] = None
    created_at: Optional[datetime] = None


class SetActiveRequest(BaseModel):
    is_active: bool


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class SetRoleRequest(BaseModel):
    role: str


class BackendErrorsOut(BaseModel):
    content: str
    file_path: str
    truncated: bool


# ── 工具函数 ─────────────────────────────────

def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "")[:64]


def _get_target_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _write_audit(db: Session, *, admin: User, action: str,
                 target_id: int, detail: dict, request: Request) -> None:
    """记录超级管理员敏感操作（不含明文密码等敏感数据）。"""
    db.add(AdminAuditLog(
        admin_id=admin.id,
        action=action,
        target_type="user",
        target_id=target_id,
        detail_json=json.dumps(detail, ensure_ascii=False)[:2000],
        ip=_client_ip(request),
    ))
    db.commit()


# ── 管理员（admin+）：排查问题 / 登录记录 ──────

@router.get("/users", response_model=List[AdminUserOut])
def list_users(current: User = Depends(require_admin),
               db: Session = Depends(get_db)):
    """全部用户列表（仅安全字段，不含密码/密钥等敏感数据）。"""
    return [
        AdminUserOut(
            id=u.id, email=u.email, username=u.username,
            role=getattr(u, "role", ROLE_USER) or ROLE_USER,
            is_admin=user_is_admin(u), is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in db.query(User).order_by(User.id.asc()).all()
    ]


@router.get("/login-records", response_model=List[LoginRecordOut])
def list_login_records(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    email: Optional[str] = Query(None, description="按邮箱模糊筛选"),
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """全部用户的登录记录（成功/失败），用于排查登录问题。"""
    q = db.query(LoginRecord)
    if email:
        q = q.filter(LoginRecord.email.like(f"%{email.strip().lower()}%"))
    rows = (q.order_by(LoginRecord.created_at.desc())
             .offset(offset).limit(limit).all())
    return [LoginRecordOut(
        id=r.id, user_id=r.user_id, email=r.email, success=r.success,
        reason=r.reason, method=r.method or "password", ip=r.ip,
        user_agent=r.user_agent, created_at=r.created_at,
    ) for r in rows]


# ── 超级管理员（superadmin）：账户修复 ─────────

@router.post("/users/{user_id}/active", response_model=AdminUserOut)
def set_user_active(user_id: int, req: SetActiveRequest,
                    request: Request,
                    current: User = Depends(require_superadmin),
                    db: Session = Depends(get_db)):
    """启用 / 停用账户（解决账户被误停用导致无法登录的问题）。"""
    target = _get_target_user(db, user_id)
    if target.id == current.id and not req.is_active:
        raise HTTPException(status_code=400, detail="不能停用当前登录的超级管理员账户")
    target.is_active = req.is_active
    db.commit()
    db.refresh(target)
    _write_audit(db, admin=current, action="set_active",
                 target_id=target.id,
                 detail={"is_active": req.is_active,
                         "email": target.email}, request=request)
    return AdminUserOut(
        id=target.id, email=target.email, username=target.username,
        role=target.role, is_admin=user_is_admin(target),
        is_active=target.is_active, created_at=target.created_at)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: int, req: ResetPasswordRequest,
                        request: Request,
                        current: User = Depends(require_superadmin),
                        db: Session = Depends(get_db)):
    """重置账户密码（解决忘记密码等登录问题）。新密码不回显。"""
    target = _get_target_user(db, user_id)
    target.password_hash = hash_password(req.new_password)
    db.commit()
    _write_audit(db, admin=current, action="reset_password",
                 target_id=target.id,
                 detail={"email": target.email,
                         "password_length": len(req.new_password)},
                 request=request)
    return {"ok": True}


@router.post("/users/{user_id}/role", response_model=AdminUserOut)
def set_user_role(user_id: int, req: SetRoleRequest,
                  request: Request,
                  current: User = Depends(require_superadmin),
                  db: Session = Depends(get_db)):
    """调整账户角色（user / admin / superadmin）。"""
    if req.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=422,
                            detail="非法角色，仅允许 user / admin / superadmin")
    target = _get_target_user(db, user_id)
    if target.id == current.id and req.role != ROLE_SUPERADMIN:
        raise HTTPException(status_code=400,
                            detail="不能降低当前登录超级管理员的角色")
    old_role = getattr(target, "role", ROLE_USER) or ROLE_USER
    target.role = req.role
    # 同步历史 is_admin 列，保持兼容
    target.is_admin = req.role in (ROLE_ADMIN, ROLE_SUPERADMIN)
    db.commit()
    db.refresh(target)
    _write_audit(db, admin=current, action="set_role",
                 target_id=target.id,
                 detail={"email": target.email,
                         "old_role": old_role, "new_role": req.role},
                 request=request)
    return AdminUserOut(
        id=target.id, email=target.email, username=target.username,
        role=target.role, is_admin=user_is_admin(target),
        is_active=target.is_active, created_at=target.created_at)


# ── 超级管理员（superadmin）：后端错误 / 审计 ──

@router.get("/audit-logs", response_model=List[AuditLogOut])
def list_audit_logs(limit: int = Query(100, ge=1, le=500),
                    current: User = Depends(require_superadmin),
                    db: Session = Depends(get_db)):
    """查看管理操作审计日志（详细、可追溯）。"""
    rows = (db.query(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(limit).all())
    return [AuditLogOut(
        id=r.id, admin_id=r.admin_id, action=r.action,
        target_type=r.target_type or "user", target_id=r.target_id,
        detail_json=r.detail_json or "{}", ip=r.ip,
        created_at=r.created_at,
    ) for r in rows]


@router.get("/backend-errors", response_model=BackendErrorsOut)
def read_backend_errors(lines: int = Query(200, ge=1, le=1000),
                        current: User = Depends(require_superadmin)):
    """读取后端错误日志尾部（ERROR 及以上），用于 BUG 调试。

    仅读取固定日志文件，不暴露任意文件/源码读写能力。
    """
    if not ERROR_LOG_PATH.exists():
        return BackendErrorsOut(content="", file_path=str(ERROR_LOG_PATH),
                                truncated=False)
    # 倒读尾部 N 行，避免大文件全量加载
    collected: List[str] = []
    truncated = False
    with ERROR_LOG_PATH.open("rb") as f:
        f.seek(0, 2)  # 文件末尾
        position = f.tell()
        while position > 0 and len(collected) <= lines:
            block_size = min(8192, position)
            position -= block_size
            f.seek(position)
            block = f.read(block_size)
            collected = block.splitlines() + collected
            truncated = position > 0 and len(collected) > lines
    tail = collected[-lines:]
    content = "\n".join(chunk.decode("utf-8", errors="replace")
                        for chunk in tail)
    return BackendErrorsOut(content=content,
                            file_path=str(ERROR_LOG_PATH),
                            truncated=truncated)
