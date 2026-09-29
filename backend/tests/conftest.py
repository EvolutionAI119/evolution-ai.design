"""pytest共享fixtures"""
import os

# 限流按客户端 IP 累计计数，TestClient 固定同一 IP 会互相干扰触发 429；
# 必须在导入 app.main 之前禁用（环境变量优先级高于 .env）
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前初始化数据库"""
    init_db()
    yield


@pytest.fixture
def client():
    """FastAPI测试客户端"""
    return TestClient(app)
