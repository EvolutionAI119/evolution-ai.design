"""Ollama 集成端点的健壮性测试：地址异常时 503 而非 500。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db
from app.routes import ai

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def test_models_bad_host_returns_503(monkeypatch):
    # 无协议头/不可解析地址：httpx UnsupportedProtocol → 统一 503
    monkeypatch.setattr(ai, "OLLAMA_HOST", "bad-host-without-proto")
    r = client.get("/api/v1/ai/models")
    assert r.status_code == 503


def test_chat_bad_host_returns_503(monkeypatch):
    monkeypatch.setattr(ai, "OLLAMA_HOST", "bad-host-without-proto")
    r = client.post("/api/v1/ai/chat", json={"question": "什么是 G2 连续性？"})
    assert r.status_code == 503


def test_health_bad_host_reports_offline(monkeypatch):
    # /ai/health 任何异常都应优雅报告 offline
    monkeypatch.setattr(ai, "OLLAMA_HOST", "bad-host-without-proto")
    r = client.get("/api/v1/ai/health")
    assert r.status_code == 200
    assert r.json()["status"] == "offline"
