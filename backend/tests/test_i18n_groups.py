"""i18n / 中英文分组兼容 smoke test。

重点验证：
1. 英文稳定键 overall_dimensions 分组在 Import 和 PUT 修改中可以正常工作。
2. 中文分组 "整车尺寸" 仍然兼容（向后兼容 automotive_parameters.json）。
3. GET /params 返回的每一行都附带 group_key，便于前端 i18n。
4. Import CAD 风格的 warnings 应为英文（不出现中文字符串）。
"""
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db


@pytest.fixture(autouse=True)
def setup_db_fx():
    init_db()
    yield


@pytest.fixture
def client():
    return TestClient(app)


BASE = "/api/v1/import-export"


def _import(client, body):
    r = client.post(f"{BASE}/import", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_group_key_present_on_params(client):
    data = _import(client, {
        "name": "gk-check",
        "params": {"overall_dimensions": {"overall_length": 5000}},
    })
    sid = data["session_id"]
    r = client.get(f"{BASE}/{sid}/params")
    assert r.status_code == 200
    params = r.json()
    assert len(params) >= 10, "至少返回默认参数集合"
    for p in params:
        assert "group_key" in p, f"缺少 group_key：{p!r}"
        # group_key 必须是英文稳定键或原样回退值（不含 /），但不允许纯中文
        assert not any("\u4e00" <= ch <= "\u9fff" for ch in p["group_key"]), (
            f"group_key 出现中文：{p['group_key']}"
        )


def test_english_group_key_import_and_modify(client):
    """Deliver.vue 现在 PUT 提交英文 overall_dimensions / styling_angles"""
    data = _import(client, {
        "name": "en-group",
        "params": {
            "overall_dimensions": {"overall_length": 4900},
            "styling_angles": {"windshield_angle": 62},
        },
    })
    sid = data["session_id"]
    # 验证导入后覆盖生效
    r = client.get(f"{BASE}/{sid}/params")
    params = {p["key"]: p for p in r.json()}
    assert params["overall_length"]["value"] == 4900
    assert params["windshield_angle"]["value"] == 62
    assert params["overall_length"]["group_key"] == "overall_dimensions"
    assert params["windshield_angle"]["group_key"] == "styling_angles"

    # 英文分组 PUT 修改
    r2 = client.put(f"{BASE}/{sid}/params", json={"overrides": [
        {"group": "overall_dimensions", "key": "overall_length", "value": 5200},
        {"group": "styling_angles", "key": "windshield_angle", "value": 55},
    ]})
    assert r2.status_code == 200, r2.text
    modified = {p["key"]: p for p in r2.json()}
    assert modified["overall_length"]["value"] == 5200
    assert modified["windshield_angle"]["value"] == 55


def test_chinese_group_still_works_backwards_compat(client):
    """老版本 / 其他渠道传中文分组依然应该成功"""
    data = _import(client, {
        "name": "zh-group",
        "params": {"整车尺寸": {"overall_width": 1888}},
    })
    sid = data["session_id"]
    r = client.put(f"{BASE}/{sid}/params", json={"overrides": [
        {"group": "整车尺寸", "key": "overall_width", "value": 1899},
    ]})
    assert r.status_code == 200, r.text
    modified = {p["key"]: p for p in r.json()}
    assert modified["overall_width"]["value"] == 1899


def test_cad_import_warnings_are_english(client):
    """传一个假的 .stp 文件，验证响应中的 warnings 不含中文。"""
    fake = tempfile.NamedTemporaryFile(suffix=".stp", delete=False)
    try:
        fake.write(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
        fake.close()
        with open(fake.name, "rb") as fh:
            r = client.post(
                f"{BASE}/import/file",
                files={"file": ("trivial.stp", fh, "application/step")},
            )
        assert r.status_code == 200, r.text
        j = r.json()
        # warnings 中任何一项都不应包含中文字符
        for w in j.get("warnings") or []:
            assert not any("\u4e00" <= ch <= "\u9fff" for ch in w), (
                f"warnings 出现中文：{w}"
            )
    finally:
        Path(fake.name).unlink(missing_ok=True)


def test_validation_error_messages_stay_english(client):
    """分组不存在的错误，detail 应为英文。"""
    data = _import(client, {"name": "validate"})
    sid = data["session_id"]
    r = client.put(f"{BASE}/{sid}/params", json={"overrides": [
        {"group": "不存在的分组", "key": "x", "value": 1},
    ]})
    assert r.status_code == 422
    detail = r.json().get("detail", "")
    # 错误消息应包含输入字符串，但不应该夹杂中文 UI 文案（后端归一化英文输出）
    assert "does not exist" in detail
