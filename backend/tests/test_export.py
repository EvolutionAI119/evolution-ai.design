"""模型导出与下载API单元测试"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def _create_project_and_model() -> int:
    """辅助：创建项目+模型，返回 model_id"""
    proj_resp = client.post("/api/v1/projects/", json={"name": "Export Test Project"})
    project_id = proj_resp.json()["id"]
    build_resp = client.post("/api/v1/build/", json={"project_id": project_id})
    return build_resp.json()["model_id"]


# ============ GET /api/v1/export/formats ============

class TestListExportFormats:
    def test_list_formats(self):
        resp = client.get("/api/v1/export/formats")
        assert resp.status_code == 200
        data = resp.json()
        assert "formats" in data
        assert len(data["formats"]) > 0

    def test_format_keys(self):
        resp = client.get("/api/v1/export/formats")
        keys = [f["key"] for f in resp.json()["formats"]]
        assert "glb" in keys
        assert "stl" in keys
        assert "json" in keys
        assert "step" in keys
        assert "iges" in keys

    def test_format_has_mime_type(self):
        resp = client.get("/api/v1/export/formats")
        for f in resp.json()["formats"]:
            assert "mime_type" in f
            assert "extension" in f
            assert "description" in f


# ============ POST /api/v1/export/ ============

class TestExportModel:
    def test_export_json(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == model_id
        assert len(data["files"]) == 1
        assert data["files"][0]["format"] == "json"
        assert data["export_time_ms"] >= 0

    def test_export_multiple_formats(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json", "stl"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["files"]) == 2
        fmt_list = [f["format"] for f in data["files"]]
        assert "json" in fmt_list
        assert "stl" in fmt_list

    def test_export_with_precision(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json"],
            "precision": 0.001,
        })
        assert resp.status_code == 200

    def test_export_without_metadata(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json"],
            "include_metadata": False,
        })
        assert resp.status_code == 200

    def test_export_model_not_found(self):
        resp = client.post("/api/v1/export/", json={
            "model_id": 9999,
            "formats": ["json"],
        })
        assert resp.status_code == 404

    def test_export_unsupported_format(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["unsupported_fmt"],
        })
        assert resp.status_code == 400

    def test_export_glb_format(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["glb"],
        })
        assert resp.status_code == 200

    def test_export_step_format(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["step"],
        })
        assert resp.status_code == 200

    def test_export_obj_format(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["obj"],
        })
        assert resp.status_code == 200

    def test_export_file_has_size(self):
        model_id = _create_project_and_model()
        resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json"],
        })
        data = resp.json()
        for f in data["files"]:
            assert "size" in f
            assert f["size"] >= 0


# ============ GET /api/v1/export/download/{model_id}/{format} ============

class TestDownloadExport:
    def test_download_before_export(self):
        """未导出时下载应返回 404"""
        model_id = _create_project_and_model()
        resp = client.get(f"/api/v1/export/download/{model_id}/json")
        assert resp.status_code == 404

    def test_download_after_export(self):
        model_id = _create_project_and_model()
        export_resp = client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json"],
        })
        assert export_resp.status_code == 200
        resp = client.get(f"/api/v1/export/download/{model_id}/json")
        assert resp.status_code == 200

    def test_download_unsupported_format(self):
        model_id = _create_project_and_model()
        resp = client.get(f"/api/v1/export/download/{model_id}/xyz")
        assert resp.status_code == 400

    def test_download_model_not_found(self):
        resp = client.get("/api/v1/export/download/9999/json")
        assert resp.status_code == 404


# ============ GET /api/v1/export/history/{model_id} ============

class TestExportHistory:
    def test_history_no_exports(self):
        model_id = _create_project_and_model()
        resp = client.get(f"/api/v1/export/history/{model_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == model_id
        assert isinstance(data["exports"], list)

    def test_history_after_export(self):
        model_id = _create_project_and_model()
        client.post("/api/v1/export/", json={
            "model_id": model_id,
            "formats": ["json"],
        })
        resp = client.get(f"/api/v1/export/history/{model_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["exports"]) >= 1


# ============ 异常 500 分支 ============

class TestExportExceptions:
    def test_export_500_on_error(self):
        """导出过程抛异常 → 500"""
        model_id = _create_project_and_model()
        with patch("app.routes.export.CarBodyGenerator") as MockGen:
            MockGen.return_value.generate_complete_car.side_effect = RuntimeError("export crash")
            resp = client.post("/api/v1/export/", json={
                "model_id": model_id,
                "formats": ["json"],
            })
            assert resp.status_code == 500
