# -*- coding: utf-8 -*-
"""微信公众号网页授权测试（mock 微信上游接口）"""
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
def mp_on(monkeypatch):
    monkeypatch.setattr(settings, "MP_APPID", "mp_test_appid_123")
    monkeypatch.setattr(settings, "MP_SECRET", "mp_test_secret_456")
    monkeypatch.setattr(settings, "MP_REDIRECT_URI", "")
    yield


class _FakeResp:
    def __init__(self, data):
        self._d = data
    def json(self):
        return self._d


class _FakeMpClient:
    """替换 httpx.AsyncClient，模拟公众号 token/userinfo 接口"""
    openid = "oMP_TEST_OPENID"
    unionid = "uMP_TEST_UNIONID"
    nickname = "公众号测试员"

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        if "access_token" in url:
            return _FakeResp({
                "access_token": "MP_AT",
                "openid": self.openid,
                "unionid": self.unionid,
            })
        return _FakeResp({"nickname": self.nickname})


def test_authorize_503_when_not_configured(client, monkeypatch):
    # .env 可能已配置真实密钥：显式清空以保证 503 分支可测
    monkeypatch.setattr(settings, "MP_APPID", "")
    monkeypatch.setattr(settings, "MP_SECRET", "")
    r = client.get(f"{BASE}/mp/authorize")
    assert r.status_code == 503
    assert "MP_APPID" in r.json()["detail"]


def test_authorize_returns_url(client, mp_on):
    r = client.get(f"{BASE}/mp/authorize")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["state"]
    url = data["auth_url"]
    assert url.startswith("https://open.weixin.qq.com/connect/oauth2/authorize?")
    assert "appid=mp_test_appid_123" in url
    assert "scope=snsapi_userinfo" in url
    assert "response_type=code" in url
    assert "#wechat_redirect" in url


def test_callback_missing_code(client, mp_on):
    r = client.get(f"{BASE}/mp/callback")
    assert r.status_code == 200
    assert "missing_code" in r.text
    assert "mp_auth" in r.text


def test_callback_invalid_state(client, mp_on):
    r = client.get(f"{BASE}/mp/callback", params={"code": "abc", "state": "bad"})
    assert r.status_code == 200
    assert "invalid_state" in r.text


def test_callback_full_flow_creates_user(client, mp_on, monkeypatch):
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _FakeMpClient)

    state = client.get(f"{BASE}/mp/authorize").json()["state"]
    r = client.get(f"{BASE}/mp/callback",
                   params={"code": "mp_code_001", "state": state})
    assert r.status_code == 200, r.text
    assert "mp_auth" in r.text
    assert '"ok": true' in r.text

    m = re.search(r"postMessage\((\{.*?\}), ", r.text, re.S)
    assert m
    payload = json.loads(m.group(1))
    assert payload["ok"] is True
    assert payload["user"]["username"] == "公众号测试员"
    assert payload["user"]["email"].endswith("@wechat.local")

    r = client.get(f"{BASE}/me",
                   headers={"Authorization": f"Bearer {payload['token']}"})
    assert r.status_code == 200
    assert r.json()["username"] == "公众号测试员"

    # 二次扫码复用同一用户
    state2 = client.get(f"{BASE}/mp/authorize").json()["state"]
    r2 = client.get(f"{BASE}/mp/callback",
                    params={"code": "mp_code_002", "state": state2})
    payload2 = json.loads(re.search(r"postMessage\((\{.*?\}), ", r2.text, re.S).group(1))
    assert payload2["user"]["id"] == payload["user"]["id"]


def test_callback_rejects_bad_code(client, mp_on, monkeypatch):
    class _BadClient(_FakeMpClient):
        async def get(self, url, params=None):
            return _FakeResp({"errcode": 40029, "errmsg": "invalid code"})

    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _BadClient)
    state = client.get(f"{BASE}/mp/authorize").json()["state"]
    r = client.get(f"{BASE}/mp/callback",
                   params={"code": "bad", "state": state})
    assert r.status_code == 200
    assert "code_rejected" in r.text


def test_ticket_reuses_pending_state(client, mp_on):
    # 同一会话票据、state 尚未消费时，多次 authorize 复用同一 state
    r1 = client.get(f"{BASE}/mp/authorize", params={"ticket": "tk_reuse"})
    r2 = client.get(f"{BASE}/mp/authorize", params={"ticket": "tk_reuse"})
    assert r1.json()["state"] == r2.json()["state"]


def test_ticket_poll_full_flow(client, mp_on, monkeypatch):
    """会话票据全链路：pending → 手机回调成功 → done → 一次性消费。"""
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _FakeMpClient)

    # 1. authorize 带固定票据
    data = client.get(f"{BASE}/mp/authorize",
                      params={"ticket": "tk_flow_1"}).json()
    assert data["ticket"] == "tk_flow_1"
    state = data["state"]

    # 2. 扫码前按票据轮询为 pending
    r = client.get(f"{BASE}/mp/poll", params={"ticket": "tk_flow_1"})
    assert r.json()["status"] == "pending"

    # 3. 手机扫码回调成功（TestClient UA 非 MicroMessenger，走 popup）
    r = client.get(f"{BASE}/mp/callback",
                   params={"code": "c1", "state": state})
    assert '"ok": true' in r.text

    # 4. PC 按票据轮询拿到 done 与 token
    body = client.get(f"{BASE}/mp/poll",
                      params={"ticket": "tk_flow_1"}).json()
    assert body["status"] == "done"
    assert body["result"]["ok"] is True
    assert body["result"]["token"]

    # 5. 结果一次性：再次轮询为 expired
    r = client.get(f"{BASE}/mp/poll", params={"ticket": "tk_flow_1"})
    assert r.json()["status"] == "expired"
