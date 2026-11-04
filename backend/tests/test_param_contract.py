# -*- coding: utf-8 -*-
"""参数契约一致性测试

`/car/generate`（扁平 params_override）与 `/import-export/import`（分组 params）
必须共用同一套别名映射与区间校验：

  * 越界一律 422，且错误消息包含 字段名 / 实际值 / 允许区间；
  * 不自动夹紧、不静默通过；
  * 未知字段名沿用既有语义忽略（不是越界）；
  * 两端响应结构一致（422 + detail 字符串）。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db
from app import param_contract


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


@pytest.fixture(autouse=True)
def _isolate_generator():
    """隔离全局生成器：test_car 的 500 分支会把 Mock 留在 `_generator`，
    导致后续用例拿到一个必然抛错的实例（与本文件无关但会串扰）。"""
    from app.routes import car as car_routes
    car_routes._generator = None
    yield
    car_routes._generator = None


@pytest.fixture(autouse=True)
def _auth_header(demo_user):
    r = client.post("/api/v1/auth/login", json={
        "email": "demo@evolution-ai.design", "password": "demo123456"})
    assert r.status_code == 200, r.text
    client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    yield
    client.headers.pop("Authorization", None)


GROUPS = param_contract.load_parameter_groups()


# ---------------------------------------------------------------------------
# 1. 共享别名映射
# ---------------------------------------------------------------------------
def test_flat_alias_resolves_to_canonical_group():
    out = param_contract.resolve_flat_overrides({"roof_height": 850})
    assert out == {"车身部件": {"roof_length": 850}}

    out = param_contract.resolve_flat_overrides(
        {"wheel_base": 2890, "front_overhang": 950, "rear_overhang": 1110})
    flat = {k: v for items in out.values() for k, v in items.items()}
    assert flat == {"wheelbase": 2890, "overhang_front": 950, "overhang_rear": 1110}


def test_unknown_flat_keys_are_still_ignored():
    assert param_contract.resolve_flat_overrides({"not_a_real_param": 1}) == {}
    assert param_contract.validate_flat_overrides({"not_a_real_param": 1}) == []


# ---------------------------------------------------------------------------
# 2. 区间语义：越界报错 / 合法通过 / 不夹紧
# ---------------------------------------------------------------------------
def test_flat_out_of_range_carries_field_value_and_range():
    errors = param_contract.validate_flat_overrides({"wheel_diameter": 680})
    assert len(errors) == 1
    msg = errors[0]
    assert "wheel_diameter" in msg
    assert "Value 680" in msg
    assert "[350, 600]" in msg


def test_alias_out_of_range_reports_submitted_and_canonical_names():
    """前端 roof_height=550 映射到 roof_length 后越界，两个名字都要出现"""
    errors = param_contract.validate_flat_overrides({"roof_height": 550})
    assert len(errors) == 1
    msg = errors[0]
    assert "roof_height" in msg
    assert "body_components.roof_length" in msg
    assert "Value 550" in msg
    assert "[1200, 2000]" in msg


def test_flat_in_range_passes():
    assert param_contract.validate_flat_overrides({"overall_length": 5000}) == []
    assert param_contract.validate_flat_overrides(None) == []


def test_flat_validation_does_not_mutate_inputs():
    payload = {"wheel_diameter": 680}
    before = dict(payload)
    param_contract.validate_flat_overrides(payload)
    assert payload == before, "校验不应改写调用方载荷（不得夹紧）"


def test_grouped_and_flat_share_range_phrase():
    """同一后端参数，分组与扁平入口给出相同的值+区间描述"""
    flat_msg = param_contract.validate_flat_overrides({"roof_length": 550})[0]
    grouped_msg = param_contract.validate_group_value(
        GROUPS, "body_components", "roof_length", 550)
    for msg in (flat_msg, grouped_msg):
        assert "Value 550" in msg
        assert "[1200, 2000]" in msg
        assert "roof_length" in msg


def test_grouped_key_alias_only_when_name_absent():
    """显式分组内原名优先：车身部件.roof_height 是板厚语义，不做别名"""
    ref, err = param_contract.resolve_grouped_key(GROUPS, "车身部件", "roof_height")
    assert err is None and ref == ("车身部件", "roof_height")
    # 原名不存在时才走别名
    ref, err = param_contract.resolve_grouped_key(GROUPS, "整车尺寸", "wheel_base")
    assert err is None and ref == ("整车尺寸", "wheelbase")


# ---------------------------------------------------------------------------
# 3. /car/generate 端：越界 422，不夹紧
# ---------------------------------------------------------------------------
def test_generate_rejects_out_of_range():
    r = client.post("/api/v1/car/generate",
                    json={"params_override": {"wheel_diameter": 680}})
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert isinstance(detail, str)
    assert "wheel_diameter" in detail
    assert "680" in detail
    assert "[350, 600]" in detail


def test_generate_rejects_frontend_default_payload():
    """中试暴露的真实冲突：前端品牌参数中的越界键必须被明确拒绝

    注意 rear_slant_angle 在后端**存在同名参数**（造型角度，5~60），
    沿用既有解析规则「原名优先」，因此 18 合法、不会走 c_pillar_angle 别名。
    语义是否统一留给产品裁决，本测试只锁定当前契约的实际行为。
    """
    payload = {
        "overall_length": 4950, "overall_width": 1880, "overall_height": 1460,
        "wheel_base": 2890, "track_width": 1600, "ground_clearance": 140,
        "hood_length": 1050, "roof_height": 550, "wheel_diameter": 680,
        "windshield_angle": 35, "rear_window_angle": 28, "rear_slant_angle": 18,
        "front_overhang": 950, "rear_overhang": 1110,
    }
    r = client.post("/api/v1/car/generate", json={"params": payload})
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    for name in ("roof_height", "wheel_diameter", "windshield_angle"):
        assert name in detail, f"{name} 未出现在错误消息：{detail}"


def test_generate_accepts_in_range_and_does_not_clamp():
    r = client.post("/api/v1/car/generate",
                    json={"params_override": {"overall_length": 5000}})
    assert r.status_code == 200, r.text
    assert r.json()["total_surfaces"] > 0
    # 被拒绝的越界值不得留在生成器参数里（无夹紧痕迹）
    params = client.get("/api/v1/car/parameters").json()["parameters"]
    assert params["整车尺寸"]["overall_length"]["value"] == 4800


def test_regenerate_rejects_out_of_range():
    r = client.post("/api/v1/car/regenerate",
                    json={"params_override": {"roof_length": 900}})
    assert r.status_code == 422, r.text
    assert "[1200, 2000]" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 4. /import-export/import 端：同结构 422
# ---------------------------------------------------------------------------
BASE = "/api/v1/import-export"


def test_import_rejects_out_of_range_with_same_structure():
    r = client.post(f"{BASE}/import", json={
        "name": "range-check",
        "params": {"body_components": {"roof_length": 550}},
    })
    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert isinstance(detail, str)
    assert "body_components.roof_length" in detail
    assert "Value 550" in detail
    assert "[1200, 2000]" in detail


def test_import_accepts_in_range():
    r = client.post(f"{BASE}/import", json={
        "name": "range-ok",
        "params": {"body_components": {"roof_length": 1500}},
    })
    assert r.status_code == 200, r.text


def test_import_grouped_roof_height_keeps_thickness_semantics():
    """显式分组 roof_height = 板厚（30~100），不属于前端 roof_length"""
    r = client.post(f"{BASE}/import", json={
        "name": "thickness",
        "params": {"车身部件": {"roof_height": 50}},
    })
    assert r.status_code == 200, r.text

    r = client.post(f"{BASE}/import", json={
        "name": "thickness-bad",
        "params": {"车身部件": {"roof_height": 550}},
    })
    assert r.status_code == 422
    assert "[30, 100]" in r.json()["detail"]


def test_import_group_alias_maps_to_canonical_key():
    r = client.post(f"{BASE}/import", json={
        "name": "alias",
        "params": {"整车尺寸": {"wheel_base": 2890}},
    })
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]
    rows = {p["key"]: p for p in client.get(f"{BASE}/{sid}/params").json()}
    assert rows["wheelbase"]["value"] == 2890
    assert "wheel_base" not in rows
