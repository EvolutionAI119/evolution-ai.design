"""车身生成API单元测试"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


# ============ POST /api/v1/car/generate ============

class TestGenerateCompleteCar:
    def test_generate_success(self):
        resp = client.post("/api/v1/car/generate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "完整车身"
        assert "components" in data
        assert isinstance(data["components"], list)
        assert data["total_surfaces"] > 0

    def test_generate_with_project_id(self):
        resp = client.post("/api/v1/car/generate", json={"project_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_surfaces"] > 0

    def test_generate_with_params_override(self):
        resp = client.post("/api/v1/car/generate", json={
            "params_override": {"overall_length": 5000}
        })
        assert resp.status_code == 200
        assert resp.json()["total_surfaces"] > 0


# ============ POST /api/v1/car/generate/component ============

class TestGenerateComponent:
    def test_simple_component_hood(self):
        resp = client.post("/api/v1/car/generate/component", json={"component": "hood"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "hood"
        assert data["name"] == "发动机盖"

    def test_simple_component_roof(self):
        resp = client.post("/api/v1/car/generate/component", json={"component": "roof"})
        assert resp.status_code == 200
        assert resp.json()["type"] == "roof"

    def test_simple_component_grille(self):
        resp = client.post("/api/v1/car/generate/component", json={"component": "grille"})
        assert resp.status_code == 200
        assert resp.json()["type"] == "grille"

    def test_side_component_door_front_left(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "door_front", "side": "left"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "door"
        assert "left" in data["name"]

    def test_side_component_door_front_right(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "door_front", "side": "right"
        })
        assert resp.status_code == 200
        assert "right" in resp.json()["name"]

    def test_side_component_headlight(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "headlight", "side": "left"
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "headlight"

    def test_position_side_component_wheel(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "wheel", "side": "left", "position": "front"
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "wheel"

    def test_position_side_component_fender(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "fender", "side": "right", "position": "rear"
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "fender"

    def test_pillar_a(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "pillar", "side": "left", "pillar_type": "A"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "pillar"
        assert "A" in data["name"]

    def test_pillar_b(self):
        resp = client.post("/api/v1/car/generate/component", json={
            "component": "pillar", "pillar_type": "B"
        })
        assert resp.status_code == 200

    def test_unknown_component(self):
        resp = client.post("/api/v1/car/generate/component", json={"component": "invalid"})
        assert resp.status_code == 400
        assert "Unknown component" in resp.json()["detail"]

    def test_component_has_color(self):
        resp = client.post("/api/v1/car/generate/component", json={"component": "hood"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["color"] is not None

    def test_component_has_position(self):
        resp = client.post("/api/v1/car/generate/component", json={"component": "hood"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["position"] is not None

    def test_component_default_side(self):
        """不传 side 时默认 left"""
        resp = client.post("/api/v1/car/generate/component", json={"component": "headlight"})
        assert resp.status_code == 200
        assert "left" in resp.json()["name"]


# ============ GET /api/v1/car/components ============

class TestListComponents:
    def test_list_components(self):
        resp = client.get("/api/v1/car/components")
        assert resp.status_code == 200
        data = resp.json()
        assert "components" in data
        assert data["total"] > 0
        # 检查关键部件存在
        names = [c["component"] for c in data["components"]]
        assert "hood" in names
        assert "wheel" in names
        assert "pillar" in names
        assert "headlight" in names

    def test_wheel_has_position_param(self):
        resp = client.get("/api/v1/car/components")
        data = resp.json()
        wheel = next(c for c in data["components"] if c["component"] == "wheel")
        assert "position" in wheel["params"]
        assert "side" in wheel["params"]

    def test_pillar_has_pillar_type_param(self):
        resp = client.get("/api/v1/car/components")
        data = resp.json()
        pillar = next(c for c in data["components"] if c["component"] == "pillar")
        assert "pillar_type" in pillar["params"]


# ============ GET /api/v1/car/parameters ============

class TestGetCarParameters:
    def test_get_parameters(self):
        resp = client.get("/api/v1/car/parameters")
        assert resp.status_code == 200
        data = resp.json()
        assert "parameters" in data
        params = data["parameters"]
        assert isinstance(params, dict)


# ============ POST /api/v1/car/regenerate ============

class TestRegenerateCar:
    def test_regenerate(self):
        resp = client.post("/api/v1/car/regenerate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "完整车身"
        assert data["total_surfaces"] > 0

    def test_regenerate_with_params(self):
        resp = client.post("/api/v1/car/regenerate", json={
            "params_override": {"overall_length": 5200}
        })
        assert resp.status_code == 200


# ============ POST /api/v1/car/export ============

class TestExportCarData:
    def test_export(self):
        with patch("app.api.car_routes._generator", None), \
             patch("app.api.car_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.export_car_data.return_value = {
                "name": "完整车身",
                "components": [{"name": "hood"}],
                "total_surfaces": 1,
            }
            resp = client.post("/api/v1/car/export", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert data["exported"] is True
            assert data["total_surfaces"] > 0
            assert data["components_count"] > 0


# ============ 补充：异常 500 分支 ============

class TestCarExceptions:
    def test_generate_500(self):
        """generate_complete_car 抛异常 → 500"""
        with patch("app.api.car_routes._generator", None), \
             patch("app.api.car_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.side_effect = RuntimeError("crash")
            resp = client.post("/api/v1/car/generate", json={})
            assert resp.status_code == 500

    def test_generate_component_500(self):
        """组件生成方法抛异常 → 500"""
        with patch("app.api.car_routes._generator", None), \
             patch("app.api.car_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_hood.side_effect = RuntimeError("crash")
            resp = client.post("/api/v1/car/generate/component", json={"component": "hood"})
            assert resp.status_code == 500

    def test_regenerate_500(self):
        """regenerate 时生成器异常 → 500"""
        with patch("app.api.car_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.side_effect = RuntimeError("crash")
            resp = client.post("/api/v1/car/regenerate", json={})
            assert resp.status_code == 500

    def test_export_500(self):
        """export_car_data 抛异常 → 500"""
        with patch("app.api.car_routes._generator", None), \
             patch("app.api.car_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.export_car_data.side_effect = RuntimeError("crash")
            resp = client.post("/api/v1/car/export", json={})
            assert resp.status_code == 500
