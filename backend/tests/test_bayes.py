"""贝叶斯优化容器回归测试。

覆盖：会话生命周期（创建/查询/删除）、采样建议在边界内、观测上报校验、
GP 代理模型随观测更新并使 best 向最优收敛、训练样本导出格式、404/400。
"""
import pytest
from fastapi.testclient import TestClient

from app.bayes_optimizer import DEFAULT_SPACE
from app.main import app

client = TestClient(app)


def _create(**overrides):
    body = {"seed": 42}
    body.update(overrides)
    r = client.post("/api/v1/bayes/sessions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _suggest(sid, n=1):
    r = client.get(f"/api/v1/bayes/sessions/{sid}/suggest", params={"n": n})
    assert r.status_code == 200, r.text
    return r.json()["suggestions"]


def _observe(sid, params, score):
    r = client.post(f"/api/v1/bayes/sessions/{sid}/observe",
                    json={"parameters": params, "score": score})
    assert r.status_code == 200, r.text
    return r.json()


# ── 会话生命周期 ──────────────────────────────────────────────

def test_create_default_space_has_14_params():
    s = _create()
    assert s["goal"] == "maximize"
    assert s["acquisition"] == "ei"
    assert s["n_observations"] == 0
    assert s["best"] is None
    names = [p["name"] for p in s["space"]]
    assert names == [p["name"] for p in DEFAULT_SPACE]
    assert len(names) == 14


def test_create_custom_space_and_get_summary():
    s = _create(name="t", goal="minimize", acquisition="ucb",
                space=[{"name": "x", "min": 0, "max": 1}])
    assert s["goal"] == "minimize"
    r = client.get(f"/api/v1/bayes/sessions/{s['session_id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "t"


def test_create_invalid_space_400():
    r = client.post("/api/v1/bayes/sessions", json={
        "space": [{"name": "x", "min": 2.0, "max": 1.0}]})
    assert r.status_code == 400


def test_unknown_session_404():
    assert client.get("/api/v1/bayes/sessions/nope").status_code == 404
    assert client.get("/api/v1/bayes/sessions/nope/suggest").status_code == 404
    assert client.post("/api/v1/bayes/sessions/nope/observe",
                       json={"parameters": {}, "score": 1.0}).status_code == 404
    assert client.get("/api/v1/bayes/sessions/nope/best").status_code == 404
    assert client.delete("/api/v1/bayes/sessions/nope").status_code == 404


def test_delete_session():
    s = _create()
    assert client.delete(f"/api/v1/bayes/sessions/{s['session_id']}").status_code == 200
    assert client.get(f"/api/v1/bayes/sessions/{s['session_id']}").status_code == 404


# ── 采样建议与观测 ────────────────────────────────────────────

def test_suggest_within_bounds_before_observations():
    s = _create()
    for sug in _suggest(s["session_id"], n=5):
        for p in s["space"]:
            v = sug[p["name"]]
            assert p["min"] <= v <= p["max"]


def test_observe_validation():
    s = _create(space=[{"name": "x", "min": 0, "max": 1}])
    sid = s["session_id"]
    # 未知参数 → 400
    assert client.post(f"/api/v1/bayes/sessions/{sid}/observe",
                       json={"parameters": {"x": 0.5, "y": 1}, "score": 1}).status_code == 400
    # 越界 → 400
    assert client.post(f"/api/v1/bayes/sessions/{sid}/observe",
                       json={"parameters": {"x": 2.0}, "score": 1}).status_code == 400
    # 正常上报
    r = _observe(sid, {"x": 0.5}, 10.0)
    assert r["n_observations"] == 1
    assert r["best"]["score"] == 10.0


def test_best_409_without_observations():
    s = _create()
    assert client.get(f"/api/v1/bayes/sessions/{s['session_id']}/best").status_code == 409


def test_best_respects_minimize_goal():
    s = _create(goal="minimize", space=[{"name": "x", "min": 0, "max": 1}])
    sid = s["session_id"]
    _observe(sid, {"x": 0.1}, 5.0)
    _observe(sid, {"x": 0.9}, -3.0)
    # minimize → score 最小的为最优
    r = client.get(f"/api/v1/bayes/sessions/{sid}/best")
    assert r.json()["score"] == -3.0


# ── 收敛方向（GP + EI 代理寻优）────────────────────────────────

@pytest.mark.parametrize("acq", ["ei", "ucb"])
def test_converges_toward_1d_optimum(acq):
    """目标 f(x)=-(x-0.7)^2（maximize，最优 0）。15 轮闭环后 best 应逼近 0。"""
    s = _create(acquisition=acq, seed=7,
                space=[{"name": "x", "min": 0, "max": 1}])
    sid = s["session_id"]
    for _ in range(15):
        x = _suggest(sid)[0]["x"]
        _observe(sid, {"x": x}, -(x - 0.7) ** 2)
    best = client.get(f"/api/v1/bayes/sessions/{sid}/best").json()
    assert best["score"] > -0.01  # |x-0.7| < 0.1


# ── 训练样本导出 ──────────────────────────────────────────────

def test_samples_export_training_format():
    s = _create(space=[{"name": "a", "min": 0, "max": 10},
                       {"name": "b", "min": -1, "max": 1}])
    sid = s["session_id"]
    _observe(sid, {"a": 5.0, "b": 0.0}, 88.0)
    _observe(sid, {"a": 6.0, "b": 0.5}, 91.0)

    r = client.get(f"/api/v1/bayes/sessions/{sid}/samples")
    assert r.status_code == 200
    body = r.json()
    assert body["feature_order"] == ["a", "b"]
    assert body["goal"] == "maximize"
    assert len(body["samples"]) == 2
    assert body["samples"][0] == {"features": {"a": 5.0, "b": 0.0}, "score": 88.0}
