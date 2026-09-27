"""质量报告列表/详情回归测试。

重点覆盖：历史行 report_data 以字符串（Python repr / JSON / 无法解析文本）
存储时，接口仍返回 200 且 report_data 规整为 dict，不再 500。
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import (QualityReport, SessionLocal, init_db)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def _project_model():
    """创建项目并构建出一个模型记录，返回 (project_id, model_id)。"""
    pid = client.post("/api/v1/projects/", json={"name": "QR Test"}).json()["id"]
    r = client.post("/api/v1/build/", json={"project_id": pid})
    assert r.status_code == 200
    return pid, r.json()["model_id"]


def _add_report(pid, mid, data):
    db = SessionLocal()
    try:
        db.add(QualityReport(
            project_id=pid, model_id=mid,
            overall_score=90.0, passed=True, report_data=data))
        db.commit()
    finally:
        db.close()


def test_legacy_repr_report_returns_dict():
    # 历史行：str(dict) 的 Python repr
    pid, mid = _project_model()
    legacy = str({"score": 92.5, "passed": True, "checks": {"g0": True}})
    _add_report(pid, mid, legacy)

    r = client.get("/api/v1/quality/reports/", params={"model_id": mid})
    assert r.status_code == 200
    item = r.json()[0]
    assert isinstance(item["report_data"], dict)
    assert item["report_data"]["score"] == 92.5
    assert item["report_data"]["checks"]["g0"] is True


def test_json_report_returns_dict():
    # 新行：json.dumps 存储
    pid, mid = _project_model()
    _add_report(pid, mid, json.dumps({"score": 88.0, "checks": {"g1": False}}))

    r = client.get("/api/v1/quality/reports/", params={"model_id": mid})
    assert r.status_code == 200
    data = r.json()[0]["report_data"]
    assert isinstance(data, dict)
    assert data["score"] == 88.0


def test_check_then_get_report_roundtrip():
    # /quality/check 产出的新报告可被详情接口正常读取
    pid, mid = _project_model()
    r = client.post("/api/v1/quality/check/", json={"model_id": mid})
    assert r.status_code == 200
    report_id = r.json()["report_id"]

    r2 = client.get(f"/api/v1/quality/reports/{report_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert isinstance(body["report_data"], dict)
    assert body["report_data"]["score"] == 92.5


def test_unparseable_string_does_not_500():
    # 无法解析的文本也不能让接口崩溃
    pid, mid = _project_model()
    _add_report(pid, mid, "===corrupted report===")

    r = client.get("/api/v1/quality/reports/", params={"model_id": mid})
    assert r.status_code == 200
    data = r.json()[0]["report_data"]
    assert data == {"raw_text": "===corrupted report==="}


def test_filter_by_project_and_model():
    pid, mid = _project_model()
    _add_report(pid, mid, json.dumps({"score": 70.0}))

    assert client.get("/api/v1/quality/reports/",
                      params={"project_id": pid}).json()[0]["report_data"]["score"] == 70.0
    assert client.get("/api/v1/quality/reports/",
                      params={"model_id": mid}).json()[0]["report_data"]["score"] == 70.0
    # 不存在的过滤条件 → 空列表而非报错
    assert client.get("/api/v1/quality/reports/",
                      params={"project_id": 999999}).json() == []
