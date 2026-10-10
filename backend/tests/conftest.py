"""pytest共享fixtures"""
import os
import sys
from pathlib import Path

# 确保跨工程导入可用：
# `app.graded_surface` 依赖 `algorithm_model`（位于工程根 Evolution-Ai.Design/），
# 而测试从 backend/ 运行。必须在导入 app.* 之前把工程根加入 sys.path。
_BACKEND = Path(__file__).resolve().parents[1]
_ROOT = _BACKEND.parent
for _p in (_BACKEND, _ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# 限流按客户端 IP 累计计数，TestClient 固定同一 IP 会互相干扰触发 429；
# 必须在导入 app.main 之前禁用（环境变量优先级高于 .env）
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# 本地 .env 已开 GUEST_MODE（账号封存期）；测试必须强制走真实鉴权路径，
# 否则依赖 401/403 语义的用例会被游客旁路击穿（环境变量优先级高于 .env）
os.environ["GUEST_MODE"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

DEMO_EMAIL = "demo@evolution-ai.design"
DEMO_PASSWORD = "demo123456"


@pytest.fixture
def demo_user():
    """确保演示账户存在（幂等）。

    test_build / test_car / test_export / test_quality_reports / test_variant
    依赖该账户登录，但 init_db() 只建表不播种用户；在干净的 DB 上运行会全量
    401。这里直接建档（role=user），使测试自具备前置条件。
    """
    from app.database import SessionLocal, User
    from app.security import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == DEMO_EMAIL).first():
            db.add(User(
                email=DEMO_EMAIL, username="demo",
                password_hash=hash_password(DEMO_PASSWORD),
                role="user", is_admin=False, is_active=True))
            db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前初始化数据库"""
    init_db()
    yield


@pytest.fixture
def client():
    """FastAPI测试客户端"""
    return TestClient(app)
