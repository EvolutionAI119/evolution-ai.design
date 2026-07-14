"""pytest共享fixtures"""
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
