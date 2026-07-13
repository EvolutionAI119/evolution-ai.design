"""模型变体API单元测试（全数据库持久化）"""
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import init_db, SessionLocal, ModelVariant

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def _create_project_and_model() -> int:
    """辅助：创建项目+模型，返回 model_id"""
    proj_resp = client.post("/api/v1/projects/", json={"name": "Variant Test Project"})
    project_id = proj_resp.json()["id"]
    build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
    return build_resp.json()["model_id"]


# ============ POST /api/v1/variants/ ============

class TestCreateVariant:
    def test_create_variant(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/", json={
            "model_id": model_id,
            "name": "运动版变体",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "运动版变体"
        assert data["model_id"] == model_id
        assert data["id"] > 0

    def test_create_variant_with_params(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/", json={
            "model_id": model_id,
            "name": "长轴距版",
            "params_override": {"overall_length": 5200, "wheelbase": 3100},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "长轴距版"
        assert data["params"] is not None

    def test_create_variant_with_description(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/", json={
            "model_id": model_id,
            "name": "测试变体",
            "description": "用于测试的变体",
        })
        assert resp.status_code == 200
        assert resp.json()["description"] == "用于测试的变体"

    def test_create_variant_model_not_found(self):
        resp = client.post("/api/v1/variants/", json={
            "model_id": 9999,
            "name": "无效变体",
        })
        assert resp.status_code == 404

    def test_create_multiple_variants(self):
        model_id = _create_project_and_model()
        r1 = client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "变体A",
        })
        r2 = client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "变体B",
        })
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["id"] != r2.json()["id"]

    def test_create_variant_persisted_to_db(self):
        """验证变体被持久化到数据库"""
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/", json={
            "model_id": model_id,
            "name": "持久化变体",
            "params_override": {"overall_length": 5000},
        })
        variant_id = resp.json()["id"]

        # 直接查数据库确认持久化
        db = SessionLocal()
        variant = db.query(ModelVariant).filter(ModelVariant.id == variant_id).first()
        db.close()
        assert variant is not None
        assert variant.name == "持久化变体"
        assert variant.params_json is not None
        assert variant.car_data_json is not None


# ============ GET /api/v1/variants/{model_id} ============

class TestListVariants:
    def test_list_empty(self):
        model_id = _create_project_and_model()
        resp = client.get(f"/api/v1/variants/{model_id}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_create(self):
        model_id = _create_project_and_model()
        client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "变体1",
        })
        client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "变体2",
        })
        resp = client.get(f"/api/v1/variants/{model_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [v["name"] for v in data]
        assert "变体1" in names
        assert "变体2" in names


# ============ GET /api/v1/variants/{model_id}/{variant_id} ============

class TestGetVariant:
    def test_get_variant_detail(self):
        model_id = _create_project_and_model()
        create_resp = client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "详细变体",
        })
        variant_id = create_resp.json()["id"]

        resp = client.get(f"/api/v1/variants/{model_id}/{variant_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "详细变体"
        assert "components_count" in data

    def test_get_variant_not_found(self):
        model_id = _create_project_and_model()
        resp = client.get(f"/api/v1/variants/{model_id}/9999")
        assert resp.status_code == 404


# ============ DELETE /api/v1/variants/{model_id}/{variant_id} ============

class TestDeleteVariant:
    def test_delete_variant(self):
        model_id = _create_project_and_model()
        create_resp = client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "待删除变体",
        })
        variant_id = create_resp.json()["id"]

        resp = client.delete(f"/api/v1/variants/{model_id}/{variant_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # 验证已删除
        list_resp = client.get(f"/api/v1/variants/{model_id}")
        assert len(list_resp.json()) == 0

    def test_delete_variant_not_found(self):
        model_id = _create_project_and_model()
        resp = client.delete(f"/api/v1/variants/{model_id}/9999")
        assert resp.status_code == 404

    def test_delete_variant_db_removed(self):
        """验证删除后数据库记录也被移除"""
        model_id = _create_project_and_model()
        create_resp = client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "待删除",
        })
        variant_id = create_resp.json()["id"]

        client.delete(f"/api/v1/variants/{model_id}/{variant_id}")

        db = SessionLocal()
        variant = db.query(ModelVariant).filter(ModelVariant.id == variant_id).first()
        db.close()
        assert variant is None


# ============ POST /api/v1/variants/compare ============

class TestCompareModels:
    def test_compare_different_models(self):
        proj1 = client.post("/api/v1/projects/", json={"name": "Compare A"}).json()["id"]
        proj2 = client.post("/api/v1/projects/", json={"name": "Compare B"}).json()["id"]
        model_a = client.post("/api/v1/build/", json={"project_id": proj1}).json()["model_id"]
        model_b = client.post("/api/v1/build/", json={"project_id": proj2}).json()["model_id"]

        resp = client.post("/api/v1/variants/compare", json={
            "model_id_a": model_a,
            "model_id_b": model_b,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "model_a" in data
        assert "model_b" in data
        assert "differences" in data

    def test_compare_same_model(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/compare", json={
            "model_id_a": model_id,
            "model_id_b": model_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["differences"]["file_size_diff"] == 0
        assert data["differences"]["type_match"] is True

    def test_compare_model_not_found(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/compare", json={
            "model_id_a": model_id,
            "model_id_b": 9999,
        })
        assert resp.status_code == 404

    def test_compare_model_a_not_found(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/variants/compare", json={
            "model_id_a": 9999,
            "model_id_b": model_id,
        })
        assert resp.status_code == 404

    def test_compare_with_param_differences(self):
        """构建时传入不同参数，compare 直接从 DB params_json 读取差异"""
        proj1 = client.post("/api/v1/projects/", json={"name": "Param A"}).json()["id"]
        proj2 = client.post("/api/v1/projects/", json={"name": "Param B"}).json()["id"]
        model_a = client.post("/api/v1/build/", json={
            "project_id": proj1,
            "params": {"overall_length": 4800, "overall_width": 1800},
        }).json()["model_id"]
        model_b = client.post("/api/v1/build/", json={
            "project_id": proj2,
            "params": {"overall_length": 5200, "overall_width": 1900},
        }).json()["model_id"]

        resp = client.post("/api/v1/variants/compare", json={
            "model_id_a": model_a,
            "model_id_b": model_b,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "param_differences" in data
        param_diff = data["param_differences"]
        assert "overall_length" in param_diff
        assert param_diff["overall_length"]["delta"] == 5200 - 4800
        assert "overall_width" in param_diff
        assert param_diff["overall_width"]["delta"] == 1900 - 1800

    def test_compare_identical_param_variants(self):
        """两个模型参数相同时，param_differences 不含差值"""
        proj1 = client.post("/api/v1/projects/", json={"name": "Same A"}).json()["id"]
        proj2 = client.post("/api/v1/projects/", json={"name": "Same B"}).json()["id"]
        model_a = client.post("/api/v1/build/", json={
            "project_id": proj1,
            "params": {"overall_length": 5000},
        }).json()["model_id"]
        model_b = client.post("/api/v1/build/", json={
            "project_id": proj2,
            "params": {"overall_length": 5000},
        }).json()["model_id"]

        resp = client.post("/api/v1/variants/compare", json={
            "model_id_a": model_a,
            "model_id_b": model_b,
        })
        assert resp.status_code == 200
        data = resp.json()
        if "param_differences" in data:
            assert "overall_length" not in data["param_differences"]


# ============ GET /api/v1/variants/{model_id}/history ============

class TestVersionHistory:
    def test_history_no_variants(self):
        model_id = _create_project_and_model()
        resp = client.get(f"/api/v1/variants/{model_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == model_id
        assert "current_status" in data
        assert "variants" in data

    def test_history_with_variants(self):
        model_id = _create_project_and_model()
        client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "V1",
        })
        client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "V2",
        })
        resp = client.get(f"/api/v1/variants/{model_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["variants"]) == 2

    def test_history_model_not_found(self):
        resp = client.get("/api/v1/variants/9999/history")
        assert resp.status_code == 404


# ============ POST /api/v1/variants/{model_id}/{variant_id}/rollback ============

class TestRollbackVariant:
    def test_rollback(self):
        model_id = _create_project_and_model()
        create_resp = client.post("/api/v1/variants/", json={
            "model_id": model_id, "name": "回滚目标",
        })
        variant_id = create_resp.json()["id"]

        resp = client.post(f"/api/v1/variants/{model_id}/{variant_id}/rollback")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rolled_back_to"] == variant_id
        assert data["variant_name"] == "回滚目标"

    def test_rollback_variant_not_found(self):
        model_id = _create_project_and_model()
        resp = client.post(f"/api/v1/variants/{model_id}/9999/rollback")
        assert resp.status_code == 404

    def test_rollback_model_not_found(self):
        resp = client.post("/api/v1/variants/9999/1/rollback")
        assert resp.status_code == 404

    def test_rollback_updates_model_params(self):
        """回滚后模型 params_json 被更新为变体参数"""
        model_id = _create_project_and_model()
        create_resp = client.post("/api/v1/variants/", json={
            "model_id": model_id,
            "name": "回滚目标",
            "params_override": {"overall_length": 6000},
        })
        variant_id = create_resp.json()["id"]

        client.post(f"/api/v1/variants/{model_id}/{variant_id}/rollback")

        # 查数据库确认模型状态和参数已回滚
        db = SessionLocal()
        from app.models.database import ModelFile
        model = db.query(ModelFile).filter(ModelFile.id == model_id).first()
        db.close()
        assert model.status == "rolled_back"
        params = json.loads(model.params_json)
        assert params.get("overall_length") == 6000


# ============ filepath 存在时读取并合并参数 ============

class TestCreateVariantWithFile:
    def test_create_variant_filepath_exists_reads_params(self):
        """模型源文件存在时，从文件读取参数并合并"""
        model_id = _create_project_and_model()

        fake_data = json.dumps({"parameters": {"overall_length": 5000, "roof_height": 1400}})

        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=fake_data)), \
             patch("app.api.variant_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.return_value = {
                "name": "完整车身", "components": [], "total_surfaces": 0,
                "parameters": {},
            }
            resp = client.post("/api/v1/variants/", json={
                "model_id": model_id,
                "name": "文件参数变体",
                "params_override": {"overall_length": 5200},
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["params"] is not None

    def test_create_variant_filepath_exists_read_fails(self):
        """模型源文件存在但读取失败时，静默跳过"""
        model_id = _create_project_and_model()

        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", mock_open(read_data="")), \
             patch("app.api.variant_routes.json.load", side_effect=Exception("read error")), \
             patch("app.api.variant_routes.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.return_value = {
                "name": "完整车身", "components": [], "total_surfaces": 0,
                "parameters": {},
            }
            resp = client.post("/api/v1/variants/", json={
                "model_id": model_id,
                "name": "损坏文件变体",
            })
            assert resp.status_code == 200
            assert resp.json()["name"] == "损坏文件变体"
