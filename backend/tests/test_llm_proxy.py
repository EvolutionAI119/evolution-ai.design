# -*- coding: utf-8 -*-
"""LLM 代理正式测试：提供商注册表 / Key 鉴权 / 能力校验 / 上游真实透传。

覆盖契约：
- GET /llm/providers 返回 6 家及其能力
- 未配置 Key 调用 → 401（不静默降级）
- 未知提供商 → 400；提供商不具备的能力 → 501
- 配置假 Key 后请求真实发往上游（上游返回鉴权错误即证明链路真实、SSRF 端点固定）
"""
import uuid

import pytest

BASE = "/api/v1"
PROVIDER_IDS = {"ernie", "qwen", "hunyuan", "doubao", "deepseek", "kimi", "siliconflow"}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_providers_catalog(client):
    r = client.get(f"{BASE}/llm/providers")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 7
    assert {p["id"] for p in data["providers"]} == PROVIDER_IDS
    doubao = next(p for p in data["providers"] if p["id"] == "doubao")
    assert "images" in doubao["capabilities"]
    deepseek = next(p for p in data["providers"] if p["id"] == "deepseek")
    assert deepseek["capabilities"] == ["chat"]
    sf = next(p for p in data["providers"] if p["id"] == "siliconflow")
    assert set(sf["capabilities"]) == {"chat", "embeddings", "images"}


def test_chat_without_key_unauthorized(client):
    r = client.post(f"{BASE}/llm/deepseek/chat/completions",
                    json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 401, r.text
    assert "Key" in r.json()["detail"]


def test_unknown_provider_rejected(client):
    r = client.post(f"{BASE}/llm/openai/chat/completions",
                    json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400, r.text


def test_unsupported_capability_not_implemented(client):
    r = client.post(f"{BASE}/llm/deepseek/images/generations",
                    json={"prompt": "a car"})
    assert r.status_code == 501, r.text


def test_real_upstream_passthrough_with_fake_key(client):
    """配置假 Key → 真实请求 DeepSeek；上游应原样返回错误（含 error 字段）。"""
    email = f"llm_{uuid.uuid4().hex[:12]}@test.com"
    reg = client.post(f"{BASE}/auth/register", json={
        "email": email, "username": "LLM测试", "password": "pass123456",
    })
    assert reg.status_code == 200, reg.text
    headers = _auth(reg.json()["access_token"])
    try:
        r = client.put(f"{BASE}/api-keys/deepseek",
                       json={"api_key": "sk-thisisafakekey1234567890"},
                       headers=headers)
        assert r.status_code == 200, r.text

        r = client.post(f"{BASE}/llm/deepseek/chat/completions",
                        json={"messages": [{"role": "user", "content": "hi"}],
                              "max_tokens": 5},
                        headers=headers)
        # 真实上游对假 Key 的响应：鉴权/计费/限流类 4xx，且错误体来自上游
        assert r.status_code in (400, 401, 402, 403, 429), r.text[:300]
        assert "error" in r.text
    finally:
        client.delete(f"{BASE}/api-keys/deepseek", headers=headers)


def test_siliconflow_upstream_passthrough_with_fake_key(client):
    """配置假 Key → 真实请求 SiliconFlow；上游返回鉴权错误即证明端点接入正确。"""
    email = f"sf_{uuid.uuid4().hex[:12]}@test.com"
    reg = client.post(f"{BASE}/auth/register", json={
        "email": email, "username": "SF测试", "password": "pass123456",
    })
    assert reg.status_code == 200, reg.text
    headers = _auth(reg.json()["access_token"])
    try:
        r = client.put(f"{BASE}/api-keys/siliconflow",
                       json={"api_key": "sk-fake-siliconflow-1234567890"},
                       headers=headers)
        assert r.status_code == 200, r.text

        r = client.post(f"{BASE}/llm/siliconflow/chat/completions",
                        json={"messages": [{"role": "user", "content": "hi"}],
                              "max_tokens": 5},
                        headers=headers)
        # 真实上游对假 Key 的响应：鉴权类 4xx，且错误体来自上游而非本地
        assert r.status_code in (400, 401, 402, 403, 429), r.text[:300]
        assert "error" in r.text or "message" in r.text
    finally:
        client.delete(f"{BASE}/api-keys/siliconflow", headers=headers)
