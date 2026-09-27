"""SECRET_KEY 生产 fail-fast 校验测试。"""
import pytest
from pydantic import ValidationError

from app.config import _DEFAULT_SECRET_KEY, Settings


def test_production_rejects_default_key():
    # 生产环境使用内置开发默认密钥：必须拒绝启动
    with pytest.raises(ValidationError) as exc:
        Settings(ENVIRONMENT="production", SECRET_KEY=_DEFAULT_SECRET_KEY)
    assert "SECRET_KEY" in str(exc.value)


def test_production_rejects_short_key():
    # 生产环境密钥过短（<32 位）：必须拒绝启动
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", SECRET_KEY="too-short-secret")


def test_production_accepts_strong_key():
    # 生产环境合规密钥：正常加载
    strong = "x" * 40
    s = Settings(ENVIRONMENT="production", SECRET_KEY=strong)
    assert s.SECRET_KEY == strong


def test_development_allows_default_key():
    # 开发环境允许使用内置默认值，保证本地即开即用
    s = Settings(ENVIRONMENT="development", SECRET_KEY=_DEFAULT_SECRET_KEY)
    assert s.SECRET_KEY == _DEFAULT_SECRET_KEY


def test_non_production_env_names_skip_check():
    # 环境名大小写/空格不影响判断；非 production 一律放行默认值
    s = Settings(ENVIRONMENT="  Development ", SECRET_KEY=_DEFAULT_SECRET_KEY)
    assert s.SECRET_KEY == _DEFAULT_SECRET_KEY
