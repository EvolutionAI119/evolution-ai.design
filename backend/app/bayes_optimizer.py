"""贝叶斯优化引擎（纯 numpy 实现，无新增重依赖）

用途：作为机器学习后台训练的「贝叶斯容器」——
  以高斯过程（GP, RBF 核）为代理模型，EI / UCB 为采集函数，
  在造型参数空间（车长/车宽/轴距等 14 参数，边界可自定义）中迭代寻优；
  观测样本可导出为与 /ai/train 数据集兼容的训练格式。

内部约定：无论用户目标为 maximize / minimize，内部一律转为最大化处理
（minimize 时对 score 取负），采集函数与 best 逻辑因此保持单一实现。
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
from scipy.special import ndtr  # 标准正态 CDF（requirements 已含 scipy）

# 与 routes/training.py 的 PARAM_ORDER 对齐的默认造型参数空间
# （边界取各车型质心分布的外包络并留 10~20% 余量，单位 mm / 度）
DEFAULT_SPACE: List[Dict[str, float]] = [
    {"name": "overall_length",     "min": 4000.0, "max": 6200.0},
    {"name": "overall_width",      "min": 1750.0, "max": 2150.0},
    {"name": "overall_height",     "min": 1100.0, "max": 2050.0},
    {"name": "wheel_base",         "min": 2400.0, "max": 3700.0},
    {"name": "track_width",        "min": 1450.0, "max": 1900.0},
    {"name": "ground_clearance",   "min": 80.0,   "max": 280.0},
    {"name": "hood_length",        "min": 700.0,  "max": 1700.0},
    {"name": "roof_height",        "min": 300.0,  "max": 1050.0},
    {"name": "wheel_diameter",     "min": 600.0,  "max": 850.0},
    {"name": "windshield_angle",   "min": 18.0,   "max": 50.0},
    {"name": "rear_window_angle",  "min": 10.0,   "max": 50.0},
    {"name": "rear_slant_angle",   "min": 5.0,    "max": 55.0},
    {"name": "front_overhang",     "min": 750.0,  "max": 1150.0},
    {"name": "rear_overhang",      "min": 850.0,  "max": 1350.0},
]

# GP 观测数少于此值时使用随机空间填充采样（代理模型尚未稳定）
_N_INIT = 2
# 采集函数优化的候选池大小（归一化空间内随机采样）
_POOL_SIZE = 4096


class ParameterSpace:
    """连续参数空间：名称 + 上下界，负责归一化/反归一化与参数校验。"""

    def __init__(self, spec: List[Dict[str, Any]]):
        if not spec:
            raise ValueError("参数空间不能为空")
        self.names: List[str] = [str(p["name"]) for p in spec]
        if len(set(self.names)) != len(self.names):
            raise ValueError("参数空间存在重复参数名")
        self.low = np.array([float(p["min"]) for p in spec], dtype=float)
        self.high = np.array([float(p["max"]) for p in spec], dtype=float)
        if np.any(self.high <= self.low):
            raise ValueError("参数边界非法：存在 max <= min")

    @property
    def dim(self) -> int:
        return len(self.names)

    def normalize(self, x: np.ndarray) -> np.ndarray:
        return (x - self.low) / (self.high - self.low)

    def denormalize(self, u: np.ndarray) -> np.ndarray:
        return self.low + u * (self.high - self.low)

    def params_to_vector(self, params: Dict[str, float]) -> np.ndarray:
        """参数 dict → 按空间顺序的向量；未知/缺失参数、越界值一律报错。"""
        unknown = set(params) - set(self.names)
        if unknown:
            raise KeyError(f"未知参数: {sorted(unknown)}")
        missing = [n for n in self.names if n not in params]
        if missing:
            raise KeyError(f"缺失参数: {missing}")
        vec = np.array([float(params[n]) for n in self.names], dtype=float)
        if np.any(vec < self.low) or np.any(vec > self.high):
            raise ValueError("参数值超出边界")
        return vec

    def vector_to_params(self, vec: np.ndarray) -> Dict[str, float]:
        return {n: float(v) for n, v in zip(self.names, vec)}

    def to_spec(self) -> List[Dict[str, Any]]:
        return [
            {"name": n, "min": float(lo), "max": float(hi)}
            for n, lo, hi in zip(self.names, self.low, self.high)
        ]


class GaussianProcessSurrogate:
    """RBF 核高斯过程回归（各向同性长度尺度，Cholesky 求解）。"""

    def __init__(self, length_scale: float = 0.25, noise: float = 1e-6):
        self.length_scale = float(length_scale)
        self.noise = float(noise)
        self._X: Optional[np.ndarray] = None
        self._L: Optional[np.ndarray] = None
        self._alpha: Optional[np.ndarray] = None

    def _kernel(self, A: np.ndarray, B: np.ndarray) -> np.ndarray:
        a2 = np.sum(A * A, axis=1, keepdims=True)
        b2 = np.sum(B * B, axis=1, keepdims=True)
        d2 = np.maximum(a2 + b2.T - 2.0 * (A @ B.T), 0.0)
        return np.exp(-d2 / (2.0 * self.length_scale ** 2))

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """X: (n, d) 归一化输入；y: (n,) 标准化输出。"""
        K = self._kernel(X, X) + self.noise * np.eye(len(X))
        self._L = np.linalg.cholesky(K)
        self._alpha = np.linalg.solve(self._L.T, np.linalg.solve(self._L, y))
        self._X = X

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """返回 (均值, 标准差)，均为标准化空间。"""
        assert self._X is not None and self._L is not None and self._alpha is not None
        Ks = self._kernel(X, self._X)
        mean = Ks @ self._alpha
        v = np.linalg.solve(self._L, Ks.T)
        var = np.maximum(1.0 - np.sum(v * v, axis=0), 1e-12)  # k(x,x)=1
        return mean, np.sqrt(var)


def _normal_pdf(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z * z) / np.sqrt(2.0 * np.pi)


def _normal_cdf(z: np.ndarray) -> np.ndarray:
    return ndtr(z)


@dataclass
class BayesSession:
    """一次贝叶斯寻优会话：参数空间 + 目标方向 + 采集函数 + 观测序列。"""

    space: ParameterSpace
    goal: str = "maximize"           # maximize | minimize
    acquisition: str = "ei"          # ei | ucb
    seed: Optional[int] = None
    name: str = ""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    ucb_kappa: float = 2.0           # UCB 探索权重
    ei_xi: float = 0.01              # EI 最小改进量
    observations: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)
        self._gp = GaussianProcessSurrogate()

    # -- 内部方向归一：minimize → 取负，统一为最大化 --
    def _internal_scores(self) -> np.ndarray:
        s = np.array([o["score"] for o in self.observations], dtype=float)
        return s if self.goal == "maximize" else -s

    def _random_points(self, n: int) -> np.ndarray:
        return self._rng.random((n, self.space.dim))

    def suggest(self, n: int = 1) -> List[Dict[str, float]]:
        """建议下一组采样参数（原始量纲）。

        观测不足 _N_INIT 时随机空间填充；否则拟合 GP 并在候选池上
        最大化采集函数（EI / UCB）。多点建议按采集值排序取前 n。
        """
        n = max(1, int(n))
        if len(self.observations) < _N_INIT:
            pts = self._random_points(n)
        else:
            X = self.space.normalize(
                np.array([o["vector"] for o in self.observations], dtype=float))
            y = self._internal_scores()
            y_std = (y - y.mean()) / (y.std() + 1e-12)
            self._gp.fit(X, y_std)
            pool = self._random_points(_POOL_SIZE)
            mu, sigma = self._gp.predict(pool)
            if self.acquisition == "ucb":
                acq = mu + self.ucb_kappa * sigma
            else:  # ei
                best = float(y_std.max())
                imp = mu - best - self.ei_xi
                z = imp / sigma
                acq = imp * _normal_cdf(z) + sigma * _normal_pdf(z)
            idx = np.argsort(acq)[::-1][:n]
            pts = pool[idx]
        return [self.space.vector_to_params(self.space.denormalize(u)) for u in pts]

    def observe(self, params: Dict[str, float], score: float) -> Dict[str, Any]:
        """记录一次观测（参数 → 质量分）。"""
        vec = self.space.params_to_vector(params)  # KeyError/ValueError 由路由层转 400
        entry = {
            "index": len(self.observations),
            "parameters": self.space.vector_to_params(vec),
            "score": float(score),
            "vector": vec,
        }
        self.observations.append(entry)
        return {"index": entry["index"], "n_observations": len(self.observations)}

    def best(self) -> Optional[Dict[str, Any]]:
        """当前最优观测（按目标方向）。"""
        if not self.observations:
            return None
        y = self._internal_scores()
        i = int(np.argmax(y))
        o = self.observations[i]
        return {"index": o["index"], "parameters": o["parameters"], "score": o["score"]}

    def samples(self) -> Dict[str, Any]:
        """导出训练样本（features 字段名与训练管线 PARAM_ORDER 兼容）。"""
        return {
            "feature_order": list(self.space.names),
            "goal": self.goal,
            "samples": [
                {"features": o["parameters"], "score": o["score"]}
                for o in self.observations
            ],
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "goal": self.goal,
            "acquisition": self.acquisition,
            "n_observations": len(self.observations),
            "space": self.space.to_spec(),
            "best": self.best(),
        }


class BayesSessionStore:
    """进程内会话存储（线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, BayesSession] = {}

    def create(self, session: BayesSession) -> BayesSession:
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[BayesSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


# 全局存储（与 training 任务管理一致的进程内模式）
SESSION_STORE = BayesSessionStore()
