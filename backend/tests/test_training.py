# -*- coding: utf-8 -*-
"""AI 训练后端正式测试：真实 PyTorch 训练 + 任务管理 + 分析端点契约。

覆盖契约：
- 能力端点公开；未登录创建训练 → 401
- 创建后台任务后状态流转 pending→running→completed，进度与逐轮指标真实写入，
  loss 实际下降、验证准确率合理、检查点落盘
- 任务列表/详情权限隔离（他人任务 → 403）；取消任务协作式生效
- 同步批次、数据统计、质量评估、设计生成、梯度优化端点结构正确
"""
import time
import uuid

import pytest

from app.config import settings

BASE = "/api/v1"

SEDAN_SURFACE = {
    "overall_length": 4950, "overall_width": 1880, "overall_height": 1460,
    "wheel_base": 2890, "track_width": 1600, "ground_clearance": 140,
    "hood_length": 1050, "roof_height": 550, "wheel_diameter": 680,
    "windshield_angle": 35, "rear_window_angle": 28, "rear_slant_angle": 18,
    "front_overhang": 950, "rear_overhang": 1110,
}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def login(client):
    """注册并登录一个全新用户，返回 (headers, email, password)。"""
    email = f"train_{uuid.uuid4().hex[:12]}@test.com"
    password = "pass123456"
    r = client.post(f"{BASE}/auth/register", json={
        "email": email, "username": "训练测试", "password": password,
    })
    assert r.status_code == 200, r.text
    return _auth(r.json()["access_token"]), email, password


def _poll_until_terminal(client, task_id, headers, timeout=90):
    """轮询任务直到进入终态。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get(f"{BASE}/ai/tasks/{task_id}", headers=headers)
        assert r.status_code == 200, r.text
        last = r.json()
        if last["status"] in ("completed", "failed", "cancelled"):
            return last
        time.sleep(0.5)
    pytest.fail(f"任务 {task_id} 在 {timeout}s 内未结束，最后状态：{last and last['status']}")


# ── 能力与鉴权 ─────────────────────────────────

def test_capabilities(client):
    r = client.get(f"{BASE}/ai/training/capabilities")
    assert r.status_code == 200, r.text
    cap = r.json()
    assert cap["backend"] == "pytorch"
    assert cap["torch_available"] is True
    assert cap["num_classes"] == 6 and cap["feature_count"] == 14


def test_train_requires_login(client):
    r = client.post(f"{BASE}/ai/train", json={"epochs": 3, "samples": 100})
    assert r.status_code == 401, r.text


# ── 真实 PyTorch 训练 ──────────────────────────

def test_real_training_full_flow(client, login):
    headers, _, _ = login
    r = client.post(f"{BASE}/ai/train", json={
        "name": "正式套件真实训练", "epochs": 6, "samples": 200,
        "batch_size": 32, "learning_rate": 0.01, "seed": 7,
    }, headers=headers)
    assert r.status_code == 200, r.text
    task = r.json()
    tid = task["id"]
    assert task["status"] == "pending"

    final = _poll_until_terminal(client, tid, headers)
    assert final["status"] == "completed", final.get("error_message")
    assert final["progress"] == 100.0

    metrics = final["metrics"]
    assert len(metrics) == 6
    loss_first, loss_last = metrics[0]["loss"], metrics[-1]["loss"]
    assert loss_last < loss_first  # loss 真实下降
    assert loss_last < 1.0
    assert max(m["val_acc"] for m in metrics) >= 0.7
    assert "Epoch" in (final.get("logs") or "")
    # 检查点确实落盘
    assert (settings.training_checkpoint_path / f"cartype_mlp_task{tid}.pt").exists()


def test_task_list_and_ownership(client, login):
    headers, _, _ = login
    # 建一个快速任务并等其完成
    r = client.post(f"{BASE}/ai/train",
                    json={"epochs": 3, "samples": 120}, headers=headers)
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    _poll_until_terminal(client, tid, headers)

    # 列表含本人任务
    r = client.get(f"{BASE}/ai/tasks", headers=headers)
    assert r.status_code == 200, r.text
    assert any(t["id"] == tid for t in r.json()["tasks"])

    # 他人不可见
    other_email = f"other_{uuid.uuid4().hex[:12]}@test.com"
    reg = client.post(f"{BASE}/auth/register", json={
        "email": other_email, "username": "他人", "password": "pass123456",
    })
    other_headers = _auth(reg.json()["access_token"])
    r = client.get(f"{BASE}/ai/tasks/{tid}", headers=other_headers)
    assert r.status_code == 403, r.text


def test_cancel_task(client, login):
    headers, _, _ = login
    r = client.post(f"{BASE}/ai/train", json={
        "name": "待取消任务", "epochs": 80, "samples": 2000, "batch_size": 64,
    }, headers=headers)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    time.sleep(1)
    r = client.post(f"{BASE}/ai/tasks/{cid}/cancel", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


# ── 同步批次与分析端点 ─────────────────────────

def test_sync_batch(client):
    r = client.post(f"{BASE}/ai/train/batch", json={"batch_size": 100})
    assert r.status_code == 200, r.text
    bd = r.json()
    assert bd["batch_size"] == 100 and bd["total_generated"] == 100
    assert isinstance(bd["compute_time_ms"], (int, float))
    assert len(bd["sample"]) == 14


def test_dataset_stats(client):
    r = client.get(f"{BASE}/ai/dataset-stats")
    assert r.status_code == 200, r.text
    assert r.json()["num_classes"] == 6
    assert r.json()["feature_count"] == 14


def test_evaluate_quality(client):
    r = client.post(f"{BASE}/ai/evaluate-quality",
                    json={"surface_data": SEDAN_SURFACE, "style": "modern"})
    assert r.status_code == 200, r.text
    qd = r.json()
    assert "quality_metrics" in qd and "overall_pass" in qd
    assert "recommendation" in qd
    # 标准三厢轿车参数应获得较高评分
    assert qd["quality_metrics"]["overall_score"] >= 80


def test_generate_design(client):
    r = client.post(f"{BASE}/ai/generate-design", json={
        "car_type": "sport", "style": "sporty", "brand": "ferrari",
    })
    assert r.status_code == 200, r.text
    dd = r.json()
    assert dd["design_id"].startswith("DSN-")
    assert dd["car_type"] == "sport"
    assert "creativity_score" in dd and dd["brand_dna_match"] is not None


def test_gradient_optimize(client):
    r = client.post(f"{BASE}/ai/optimize", json={
        "parameters": SEDAN_SURFACE,
        "objectives": ["aerodynamics", "quality", "manufacturability", "aesthetics"],
        "steps": 40,
    })
    assert r.status_code == 200, r.text
    od = r.json()
    assert all(k in od for k in ("pareto_score", "is_pareto_optimal",
                                 "optimization_iterations", "convergence",
                                 "objectives", "loss_history"))
    assert od["optimization_iterations"] == 40
    assert len(od["loss_history"]) == 40
    assert od["convergence"] > 0  # loss 实际下降
    assert set(od["objectives"]) == {
        "aerodynamics", "quality", "manufacturability", "aesthetics"}
