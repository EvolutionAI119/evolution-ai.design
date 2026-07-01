import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    init_db()
    yield


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "EVOLUTION AI"}


def test_create_project():
    response = client.post("/api/v1/projects/", json={"name": "Test Project", "description": "Test Description"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "Test Description"
    assert "id" in data


def test_get_projects():
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_parameters():
    response = client.get("/api/v1/parameters/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "整车级" in data


def test_validate_parameters():
    response = client.post("/api/v1/parameters/validate/")
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert "issues" in data


def test_topology_optimization():
    response = client.post("/api/v1/topology/optimize/", json={"model_id": 999})
    assert response.status_code == 404


def test_quality_check():
    response = client.post("/api/v1/quality/check/", json={"model_id": 999})
    assert response.status_code == 404


def test_data_handover():
    response = client.post("/api/v1/data/handover/", json={"model_id": 999})
    assert response.status_code == 404