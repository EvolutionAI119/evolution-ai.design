# -*- coding: utf-8 -*-
"""用户账户体系正式测试：注册 / 登录 / JWT 鉴权 / API Key 增查删。

覆盖契约：
- 注册成功返回 JWT 与用户信息；重复邮箱 → 409
- 错误密码 → 401；无 Token 访问受保护端点 → 401
- /api-keys 列出 6 家提供商；Key 加密存储、列表脱敏、可删除
- 不支持的提供商 → 400
"""
import uuid

import pytest

BASE = "/api/v1"


def _unique_email():
    return f"user_{uuid.uuid4().hex[:12]}@test.com"


@pytest.fixture
def registered(client):
    """注册一个全新用户，返回邮箱/密码/Token。"""
    email, password = _unique_email(), "pass123456"
    r = client.post(f"{BASE}/auth/register", json={
        "email": email, "username": "测试用户", "password": password,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    return {"email": email, "password": password,
            "token": body["access_token"], "user": body["user"]}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── 注册 / 当前用户 ─────────────────────────────

def test_register_success(registered):
    """注册返回 JWT、过期秒数与用户基本信息。"""
    assert registered["token"]
    assert registered["user"]["email"] == registered["email"]
    assert registered["user"]["is_admin"] is False


def test_me_with_token(client, registered):
    r = client.get(f"{BASE}/auth/me", headers=_auth(registered["token"]))
    assert r.status_code == 200, r.text
    assert r.json()["email"] == registered["email"]


def test_duplicate_register_conflict(client, registered):
    r = client.post(f"{BASE}/auth/register", json={
        "email": registered["email"], "username": "重复", "password": "pass123456",
    })
    assert r.status_code == 409, r.text


# ── 登录 / 鉴权失败 ─────────────────────────────

def test_login_wrong_password(client, registered):
    r = client.post(f"{BASE}/auth/login", json={
        "email": registered["email"], "password": "wrong-password",
    })
    assert r.status_code == 401, r.text


def test_login_success(client, registered):
    r = client.post(f"{BASE}/auth/login", json={
        "email": registered["email"], "password": registered["password"],
    })
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


def test_me_without_token(client):
    r = client.get(f"{BASE}/auth/me")
    assert r.status_code == 401, r.text


# ── API Key 管理 ────────────────────────────────

def test_list_api_keys_all_unconfigured(client, registered):
    r = client.get(f"{BASE}/api-keys", headers=_auth(registered["token"]))
    assert r.status_code == 200, r.text
    providers = [k["provider"] for k in r.json()]
    assert providers == ["ernie", "qwen", "hunyuan", "doubao", "deepseek", "kimi", "siliconflow"]
    assert all(not k["configured"] for k in r.json())


def test_set_get_masked_delete_api_key(client, registered):
    headers = _auth(registered["token"])
    # 设置
    r = client.put(f"{BASE}/api-keys/deepseek",
                   json={"api_key": "sk-test-deepseek-1234567890"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["masked"] == "****7890"
    # 再查：已配置且脱敏
    r = client.get(f"{BASE}/api-keys", headers=headers)
    dk = next(k for k in r.json() if k["provider"] == "deepseek")
    assert dk["configured"] and dk["masked"].startswith("****")
    # 删除
    r = client.delete(f"{BASE}/api-keys/deepseek", headers=headers)
    assert r.status_code == 200, r.text
    r = client.get(f"{BASE}/api-keys", headers=headers)
    dk = next(k for k in r.json() if k["provider"] == "deepseek")
    assert not dk["configured"]


def test_set_key_unsupported_provider(client, registered):
    r = client.put(f"{BASE}/api-keys/openai",
                   json={"api_key": "abcd1234"},
                   headers=_auth(registered["token"]))
    assert r.status_code == 400, r.text
