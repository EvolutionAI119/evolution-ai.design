# -*- coding: utf-8 -*-
"""微信扫码登录测试（mock 微信上游接口）"""
import json
import re

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.routes import auth as auth_module

BASE = "/api/v1/auth"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def wechat_on(monkeypatch):
    """临时开启微信配置"""
    monkeypatch.setattr(settings, "WECHAT_APPID", "wx_test_appid_123")
    monkeypatch.setattr(settings, "WECHAT_SECRET", "wx_test_secret_456")
    monkeypatch.setattr(settings, "WECHAT_REDIRECT_URI", "")
    yield


class _FakeResp:
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


class _FakeWechatClient:
    """替换 httpx.AsyncClient，模拟微信 token/userinfo 接口"""
    openid = "oWECHAT_TEST_OPENID"
    unionid = "uWECHAT_TEST_UNIONID"
    nickname = "微信测试员"

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        if "access_token" in url:
            return _FakeResp({
                "access_token": "WECHAT_AT",
                "openid": self.openid,
                "unionid": self.unionid,
            })
        return _FakeResp({"nickname": self.nickname})


def test_qr_503_when_not_configured(client):
    r = client.get(f"{BASE}/wechat/qr")
    assert r.status_code == 503
    assert "WECHAT_APPID" in r.json()["detail"]


def test_qr_returns_authorize_url(client, wechat_on):
    r = client.get(f"{BASE}/wechat/qr")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"]
    url = data["auth_url"]
    assert url.startswith("https://open.weixin.qq.com/connect/qrconnect?")
    assert "appid=wx_test_appid_123" in url
    assert "scope=snsapi_login" in url
    assert "response_type=code" in url
    # redirect_uri 已 URL 编码
    assert "redirect_uri=http" in url and "%2F" in url


def test_callback_missing_code(client, wechat_on):
    r = client.get(f"{BASE}/wechat/callback")
    assert r.status_code == 200
    assert "missing_code" in r.text


def test_callback_invalid_state(client, wechat_on):
    r = client.get(f"{BASE}/wechat/callback", params={"code": "abc", "state": "bad"})
    assert r.status_code == 200
    assert "invalid_state" in r.text


def test_callback_full_flow_creates_user(client, wechat_on, monkeypatch):
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _FakeWechatClient)

    # 1. 先取 state
    state = client.get(f"{BASE}/wechat/qr").json()["state"]

    # 2. 微信回调
    r = client.get(f"{BASE}/wechat/callback",
                   params={"code": "wx_code_001", "state": state})
    assert r.status_code == 200, r.text
    assert "wechat_auth" in r.text
    assert '"ok": true' in r.text

    # 3. 从 HTML 中解析 postMessage 载荷
    m = re.search(r"postMessage\((\{.*?\}), ", r.text, re.S)
    assert m, r.text
    payload = json.loads(m.group(1))
    assert payload["ok"] is True
    assert payload["user"]["username"] == "微信测试员"
    assert payload["user"]["email"].endswith("@wechat.local")

    # 4. token 可用于 /auth/me
    r = client.get(f"{BASE}/me",
                   headers={"Authorization": f"Bearer {payload['token']}"})
    assert r.status_code == 200
    assert r.json()["username"] == "微信测试员"

    # 5. 再次扫码登录应复用同一用户（不会重复注册）
    state2 = client.get(f"{BASE}/wechat/qr").json()["state"]
    r2 = client.get(f"{BASE}/wechat/callback",
                    params={"code": "wx_code_002", "state": state2})
    payload2 = json.loads(re.search(r"postMessage\((\{.*?\}), ", r2.text, re.S).group(1))
    assert payload2["user"]["id"] == payload["user"]["id"]


def test_callback_rejects_bad_wechat_code(client, wechat_on, monkeypatch):
    class _BadCodeClient(_FakeWechatClient):
        async def get(self, url, params=None):
            return _FakeResp({"errcode": 40029, "errmsg": "invalid code"})

    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _BadCodeClient)
    state = client.get(f"{BASE}/wechat/qr").json()["state"]
    r = client.get(f"{BASE}/wechat/callback",
                   params={"code": "bad_code", "state": state})
    assert r.status_code == 200
    assert "code_rejected" in r.text
    assert "invalid code" in r.text


def test_state_single_use(client, wechat_on, monkeypatch):
    """state 一次性：重放应被拒绝"""
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _FakeWechatClient)
    state = client.get(f"{BASE}/wechat/qr").json()["state"]
    client.get(f"{BASE}/wechat/callback", params={"code": "c1", "state": state})
    r = client.get(f"{BASE}/wechat/callback", params={"code": "c1", "state": state})
    assert "invalid_state" in r.text
