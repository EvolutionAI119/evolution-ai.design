# -*- coding: utf-8 -*-
"""游客模式（账号体系封存期）专项测试

锁定两条关键行为：
  1. GUEST_MODE=true 时，受保护接口免登录，统一落到内置 guest 账户
     （幂等：多次调用返回同一账户，角色 superadmin 保证可测全部功能）
  2. 生产环境开启 GUEST_MODE 时配置校验拒绝启动（fail-fast）
"""
import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_guest_mode_grants_full_access_without_token(client, monkeypatch):
    """GUEST_MODE=true：无令牌访问受保护接口，返回内置 guest 账户"""
    monkeypatch.setattr(settings, "GUEST_MODE", True)
    r1 = client.get("/api/v1/auth/me")
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["email"] == "guest@evolution-ai.design"
    assert body["role"] == "superadmin"

    # 幂等：再次访问（以及超管接口）命中同一 guest 账户
    r2 = client.get("/api/v1/auth/me")
    assert r2.json()["id"] == body["id"]
    r3 = client.get("/api/v1/admin/users")
    assert r3.status_code == 200, r3.text


def test_guest_mode_forbidden_in_production():
    """生产环境 + GUEST_MODE=true 必须 fail-fast"""
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 48,
            DEBUG=False,
            GUEST_MODE=True,
        )
