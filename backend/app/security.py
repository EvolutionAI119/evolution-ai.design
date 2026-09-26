"""安全模块：密码哈希(PBKDF2)、JWT 签发与校验、API Key 加解密、当前用户依赖

设计原则：
  - 密码哈希使用标准库 hashlib.pbkdf2_hmac（无需额外原生依赖，跨平台稳定）
  - JWT 使用 PyJWT（HS256）
  - API Key 静态加密使用 cryptography.Fernet，密钥由 settings.SECRET_KEY 派生
"""
from __future__ import annotations

import base64
import hashlib
import hmac as hmac_mod
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .database import User, get_db

# =========================================================================
# 密码哈希（PBKDF2-HMAC-SHA256，标准库实现）
# =========================================================================
_PBKDF2_ITERATIONS = 240_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """生成 pbkdf2 密码哈希串：pbkdf2_sha256$迭代次数$salt$hash"""
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码与存储哈希是否匹配（恒定时间比较）"""
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt_hex), int(iterations))
        return hmac_mod.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


# =========================================================================
# JWT 签发与校验
# =========================================================================
def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """签发 JWT；data 建议含 sub(用户id)、email"""
    minutes = expires_minutes or settings.JWT_EXPIRE_MINUTES
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["exp"] = now + timedelta(minutes=minutes)
    payload["iat"] = now
    return jwt.encode(payload, settings.SECRET_KEY,
                      algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解码并校验 JWT，失败抛出对应 HTTP 异常"""
    try:
        return jwt.decode(token, settings.SECRET_KEY,
                          algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的访问令牌")


# =========================================================================
# API Key 加解密（Fernet，密钥由 SECRET_KEY 经 SHA256 派生）
# =========================================================================
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        # Fernet 要求 32 字节 base64 编码密钥
        derived = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        _fernet = Fernet(base64.urlsafe_b64encode(derived))
    return _fernet


def encrypt_api_key(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


# =========================================================================
# FastAPI 依赖：当前登录用户
# =========================================================================
def _extract_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证信息，请先登录")
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    # 也允许直接传裸 token
    if len(parts) == 1:
        return parts[0]
    raise HTTPException(status_code=401, detail="认证头格式错误")


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 解析当前用户"""
    token = _extract_token(authorization)
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="令牌内容无效")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被停用")
    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选认证：无 token 时返回 None（兼容既有匿名接口）"""
    if not authorization:
        return None
    token = _extract_token(authorization)
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()


def get_user_api_key(db: Session, user: Optional[User], provider: str) -> Optional[str]:
    """获取用户某提供商的 API Key（解密）；用户未登录/未配置返回 None。

    环境变量兜底：EVOAI_{PROVIDER}_KEY（服务级统一密钥）
    """
    env_key = os.getenv(f"EVOAI_{provider.upper()}_KEY", "").strip()
    if env_key:
        return env_key
    if user is None:
        return None
    record = next((k for k in user.api_keys if k.provider == provider), None)
    if record is None:
        return None
    return decrypt_api_key(record.key_encrypted)
