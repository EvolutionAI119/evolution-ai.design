"""W-08 双判据自动收敛参考的回归测试。

判据：①最近窗口内最优值相对提升停滞；②同窗口观测离散度低。
两条同时满足才 `converged=True`，且只作为「可停止」参考，不自动终止会话。
"""
from app.bayes_optimizer import BayesSession, ParameterSpace


def _session(goal="maximize"):
    return BayesSession(space=ParameterSpace([{"name": "x", "min": 0.0, "max": 1.0}]),
                        goal=goal, seed=7)


def _feed(session, scores):
    for i, s in enumerate(scores):
        session.observe({"x": i / max(len(scores) - 1, 1)}, s)


def test_not_ready_before_min_observations():
    s = _session()
    _feed(s, [0.1, 0.2, 0.3])
    c = s.convergence()
    assert c["ready"] is False
    assert c["converged"] is False
    assert c["n_observations"] == 3


def test_plateau_is_converged():
    s = _session()
    _feed(s, [0.80, 0.801, 0.799, 0.800, 0.802, 0.798, 0.801, 0.799])
    c = s.convergence(window=5, improvement_eps=0.05, score_std_eps=0.05)
    assert c["ready"] is True
    assert c["converged"] is True
    assert c["criteria"]["stop_by_improvement"] is True
    assert c["criteria"]["stop_by_std"] is True
    assert c["best_score"] == 0.802


def test_still_improving_is_not_converged():
    s = _session()
    _feed(s, [0.10, 0.30, 0.50, 0.70, 0.90, 0.95, 0.98, 1.00])
    c = s.convergence(window=5)
    assert c["converged"] is False
    assert c["criteria"]["stop_by_improvement"] is False
    assert "目标仍在提升" in c["reason"]


def test_minimize_direction_uses_internal_scores():
    # minimize 目标下分数恒定 → 内部取负后同样判为收敛
    s = _session(goal="minimize")
    _feed(s, [0.50] * 8)
    c = s.convergence(window=5)
    assert c["converged"] is True
    assert c["best_score"] == 0.50


def test_summary_exposes_convergence():
    s = _session()
    _feed(s, [0.5] * 8)
    summary = s.summary()
    assert "convergence" in summary
    assert summary["convergence"]["converged"] is True
