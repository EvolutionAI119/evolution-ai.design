# -*- coding: utf-8 -*-
"""参数持久化正式测试：数据库表替代内存存储，add/update 同为 upsert 语义。

覆盖契约：
- GET /modify/parameters 返回数据库中的参数
- add 新参数立即可读；update 同名参数只更新值（不产生重复记录）
- add 同名参数同样为更新语义
"""
import uuid

import pytest

from app.database import ParameterRecord, SessionLocal

BASE = "/api/v1"


@pytest.fixture
def param_name():
    """生成唯一参数名并在用例结束后清理数据库行。"""
    name = f"_pytest_param_{uuid.uuid4().hex[:12]}"
    yield name
    db = SessionLocal()
    db.query(ParameterRecord).filter(ParameterRecord.name == name).delete()
    db.commit()
    db.close()


def test_parameter_persistence_lifecycle(client, param_name):
    # 初始不存在
    r = client.get(f"{BASE}/modify/parameters")
    assert r.status_code == 200, r.text
    assert param_name not in r.json()["parameters"]

    # add 新参数
    r = client.post(f"{BASE}/modify/parameters/add",
                    json={"name": param_name, "value": 1.5})
    assert r.status_code == 200, r.text
    assert r.json()["parameter"] == {"name": param_name, "value": 1.5}

    r = client.get(f"{BASE}/modify/parameters")
    params = r.json()["parameters"]
    assert params[param_name]["value"] == 1.5

    # update 同名参数：值更新且不重复
    r = client.post(f"{BASE}/modify/parameters/update",
                    json={"name": param_name, "value": 2.75})
    assert r.status_code == 200, r.text
    assert r.json()["parameter"]["value"] == 2.75

    r = client.get(f"{BASE}/modify/parameters")
    params = r.json()["parameters"]
    assert params[param_name]["value"] == 2.75
    assert list(params).count(param_name) == 1

    # add 同名参数同为 upsert
    r = client.post(f"{BASE}/modify/parameters/add",
                    json={"name": param_name, "value": 3.0})
    assert r.status_code == 200, r.text
    assert r.json()["parameter"]["value"] == 3.0
