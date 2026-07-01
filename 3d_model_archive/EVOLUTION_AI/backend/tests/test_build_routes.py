"""模型构建/重建API单元测试（全数据库持久化）"""
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import init_db, SessionLocal, Project, ModelFile

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def _create_project() -> int:
    """辅助：创建项目并返回 ID"""
    resp = client.post("/api/v1/projects/", json={"name": "Build Test Project"})
    assert resp.status_code == 201
    return resp.json()["id"]


# ============ POST /api/v1/build/ ============

class TestBuildModel:
    def test_build_success(self):
        project_id = _create_project()
        resp = client.post("/api/v1/build/", json={"project_id": project_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "built"
        assert data["model_id"] > 0
        assert data["components_count"] > 0
        assert data["build_time_ms"] >= 0

    def test_build_with_params(self):
        project_id = _create_project()
        resp = client.post("/api/v1/build/", json={
            "project_id": project_id,
            "params": {"overall_length": 5000, "overall_width": 1900},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "built"
        assert "overall_length" in data["parameters_used"]

    def test_build_with_build_options(self):
        project_id = _create_project()
        resp = client.post("/api/v1/build/", json={
            "project_id": project_id,
            "build_options": {"detail_level": "high"},
        })
        assert resp.status_code == 200

    def test_build_project_not_found(self):
        resp = client.post("/api/v1/build/", json={"project_id": 9999})
        assert resp.status_code == 404

    def test_build_creates_model_record(self):
        project_id = _create_project()
        resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = resp.json()["model_id"]
        # 验证模型记录存在
        get_resp = client.get(f"/api/v1/models/{model_id}")
        assert get_resp.status_code == 200

    def test_build_persists_car_data_to_db(self):
        """验证构建后 car_data_json 被持久化到数据库"""
        project_id = _create_project()
        resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = resp.json()["model_id"]

        db = SessionLocal()
        model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
        db.close()
        assert model is not None
        assert model.car_data_json is not None
        car_data = json.loads(model.car_data_json)
        assert "total_surfaces" in car_data

    def test_build_persists_params_to_db(self):
        """验证构建后 params_json 被持久化到数据库"""
        project_id = _create_project()
        resp = client.post("/api/v1/build/", json={
            "project_id": project_id,
            "params": {"overall_length": 5200},
        })
        model_id = resp.json()["model_id"]

        db = SessionLocal()
        model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
        db.close()
        assert model.params_json is not None
        params = json.loads(model.params_json)
        assert params.get("overall_length") == 5200


# ============ POST /api/v1/build/rebuild ============

class TestRebuildModel:
    def test_rebuild_full(self):
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.post("/api/v1/build/rebuild", json={"model_id": model_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rebuilt"
        assert data["model_id"] == model_id
        assert data["components_count"] > 0

    def test_rebuild_with_params_override(self):
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.post("/api/v1/build/rebuild", json={
            "model_id": model_id,
            "params_override": {"overall_length": 5200},
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rebuilt"

    def test_rebuild_partial_components(self):
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.post("/api/v1/build/rebuild", json={
            "model_id": model_id,
            "rebuild_components": ["hood"],
        })
        assert resp.status_code == 200

    def test_rebuild_model_not_found(self):
        resp = client.post("/api/v1/build/rebuild", json={"model_id": 9999})
        assert resp.status_code == 404

    def test_rebuild_updates_car_data_in_db(self):
        """验证重建后 car_data_json 在数据库中被更新"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        client.post("/api/v1/build/rebuild", json={"model_id": model_id})

        db = SessionLocal()
        model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
        db.close()
        assert model.car_data_json is not None
        assert model.status == "rebuilt"


# ============ POST /api/v1/build/batch ============

class TestBatchBuild:
    def test_batch_build_single(self):
        project_id = _create_project()
        resp = client.post("/api/v1/build/batch", json=[project_id])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "built"

    def test_batch_build_multiple(self):
        p1 = _create_project()
        p2 = _create_project()
        resp = client.post("/api/v1/build/batch", json=[p1, p2])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2

    def test_batch_build_with_invalid_project(self):
        p1 = _create_project()
        resp = client.post("/api/v1/build/batch", json=[p1, 9999])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "built"
        assert data["results"][1]["status"] == "error"

    def test_batch_build_empty_list(self):
        resp = client.post("/api/v1/build/batch", json=[])
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_batch_build_persists_data(self):
        """验证批量构建也持久化 params_json 和 car_data_json"""
        project_id = _create_project()
        resp = client.post("/api/v1/build/batch", json=[project_id])
        model_id = resp.json()["results"][0]["model_id"]

        db = SessionLocal()
        model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
        db.close()
        assert model.params_json is not None
        assert model.car_data_json is not None


# ============ GET /api/v1/build/cache ============

class TestBuildCache:
    def test_cache_empty(self):
        resp = client.get("/api/v1/build/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert "cached_models" in data
        assert "model_ids" in data

    def test_cache_after_build(self):
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.get("/api/v1/build/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cached_models"] >= 1
        assert model_id in data["model_ids"]


# ============ DELETE /api/v1/build/cache/{model_id} ============

class TestClearBuildCache:
    def test_clear_cache(self):
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.delete(f"/api/v1/build/cache/{model_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_clear_cache_not_found(self):
        resp = client.delete("/api/v1/build/cache/9999")
        assert resp.status_code == 404

    def test_clear_cache_already_cleared(self):
        """模型 car_data_json 已为空时清除缓存返回 404"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        # 第一次清除
        client.delete(f"/api/v1/build/cache/{model_id}")
        # 第二次清除
        resp = client.delete(f"/api/v1/build/cache/{model_id}")
        assert resp.status_code == 404

    def test_clear_cache_sets_car_data_null(self):
        """清除缓存后数据库 car_data_json 为 NULL"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        client.delete(f"/api/v1/build/cache/{model_id}")

        db = SessionLocal()
        model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
        db.close()
        assert model.car_data_json is None


# ============ GET /api/v1/build/status/{model_id} ============

class TestBuildStatus:
    def test_status_after_build(self):
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.get(f"/api/v1/build/status/{model_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == model_id
        assert data["status"] == "built"
        assert data["cached"] is True

    def test_status_model_not_found(self):
        resp = client.get("/api/v1/build/status/9999")
        assert resp.status_code == 404

    def test_status_after_cache_cleared(self):
        """清除缓存后 cached 状态为 False"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        client.delete(f"/api/v1/build/cache/{model_id}")
        resp = client.get(f"/api/v1/build/status/{model_id}")
        assert resp.status_code == 200
        assert resp.json()["cached"] is False


# ============ 补充：缓存未命中部分重建 ============

class TestRebuildCacheMiss:
    def test_rebuild_partial_cache_miss(self):
        """清除缓存后部分重建，走 car_data_json 未命中分支"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        # 清除缓存（car_data_json 置 NULL）
        client.delete(f"/api/v1/build/cache/{model_id}")

        # 部分重建（car_data_json 为 NULL → 重新 generate_complete_car）
        resp = client.post("/api/v1/build/rebuild", json={
            "model_id": model_id,
            "rebuild_components": ["hood"],
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rebuilt"

    def test_rebuild_non_method_map_component(self):
        """rebuild_components 含非 method_map 部件（如 trunk），应保留原数据"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        resp = client.post("/api/v1/build/rebuild", json={
            "model_id": model_id,
            "rebuild_components": ["trunk", "bumper"],
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "rebuilt"


# ============ 补充：异常 500 分支 ============

class TestBuildExceptions:
    def test_build_500_on_generator_error(self):
        """构建过程中 CarBodyGenerator 抛异常 → 500"""
        project_id = _create_project()
        with patch("app.api.build_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.side_effect = RuntimeError("generator crash")
            resp = client.post("/api/v1/build/", json={"project_id": project_id})
            assert resp.status_code == 500

    def test_rebuild_500_on_generator_error(self):
        """重建过程中 CarBodyGenerator 抛异常 → 500"""
        project_id = _create_project()
        build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
        model_id = build_resp.json()["model_id"]

        with patch("app.api.build_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.side_effect = RuntimeError("rebuild crash")
            resp = client.post("/api/v1/build/rebuild", json={"model_id": model_id})
            assert resp.status_code == 500

    def test_batch_build_single_item_error(self):
        """批量构建中单个项目构建异常 → error 条目"""
        with patch("app.api.build_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.side_effect = RuntimeError("batch crash")
            project_id = _create_project()
            resp = client.post("/api/v1/build/batch", json=[project_id])
            assert resp.status_code == 200
            assert resp.json()["results"][0]["status"] == "error"
