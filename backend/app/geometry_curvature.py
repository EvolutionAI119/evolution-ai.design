"""真实曲率与 G2 连续性 —— 补齐 D:\\API 生态的缺口

为什么需要本模块
----------------
侦察发现全库**缺少正确的曲率实现**：

1. `EvolutionAI/.../surface_quality/continuity.py`
   把「G2」实现为**更严的法向夹角阈值**（g2_threshold=2.0），
   完全没有计算曲率；且 g1/g2 计数存在重复计数（每条内部边被数两次）。

2. `EvolutionAI/.../surface_quality/curvature.py`
   只有 `estimate_normals` 与 `angle_between`，**无任何曲率函数**。

3. `3d_model_archive/.../nurbs_engine.py: evaluate_curvature()`
   仅取 `puu·n` 与 `pvv·n`，这是**u/v 方向的法曲率**，不是主曲率；
   且忽略了混合二阶导 `puv`，未解形状算子。

4. `3d_model_archive/.../quality_checker.py: curvature_comb_check()`
   **是伪造的**——直接向结果塞入一条硬编码 issue（"B柱上端曲率突变"），未分析几何。

行业标准要求
------------
`SOP-A SURF-001 §5.2` 对 G2 的定义是**曲率比 0.8 ~ 1.2**（附录 A: κ_a = κ_b），
即必须比较两侧的**曲率值**，而非法向夹角。

本模块提供参考实现，并用已知曲面做数值验证。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

# SOP-A SURF-001 §5.2 / 附录 A
G2_CURVATURE_RATIO_RANGE: Tuple[float, float] = (0.8, 1.2)


def _nurbs_root() -> Path:
    """定位含 algorithm_model 的工程根"""
    here = Path(__file__).resolve()
    # backend/app/geometry_curvature.py → 工程根
    return here.parents[2]


def _ensure_path() -> None:
    root = _nurbs_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


# ---------------------------------------------------------------------------
# 形状算子与主曲率
# ---------------------------------------------------------------------------
def fundamental_forms(
    surface_fn,
    u: float,
    v: float,
    h: float = 1e-4,
) -> Dict[str, Any]:
    """计算第一、第二基本形式与单位法向

    Args:
        surface_fn: 可调用 (u, v) -> np.ndarray(3,)
        u, v: 参数值
        h: 有限差分步长

    Returns:
        dict: pu, pv, puu, puv, pvv, n, E, F, G, L, M, N
    """
    p = surface_fn(u, v)

    pu = (surface_fn(u + h, v) - surface_fn(u - h, v)) / (2 * h)
    pv = (surface_fn(u, v + h) - surface_fn(u, v - h)) / (2 * h)

    puu = (surface_fn(u + h, v) - 2 * p + surface_fn(u - h, v)) / (h * h)
    pvv = (surface_fn(u, v + h) - 2 * p + surface_fn(u, v - h)) / (h * h)
    puv = (surface_fn(u + h, v + h) - surface_fn(u + h, v - h)
           - surface_fn(u - h, v + h) + surface_fn(u - h, v - h)) / (4 * h * h)

    n_raw = np.cross(pu, pv)
    n_norm = float(np.linalg.norm(n_raw))
    if n_norm < 1e-14:
        raise ValueError(f"曲面在 (u={u}, v={v}) 处退化：法向为零")
    n = n_raw / n_norm

    # 第一基本形式（度量张量）
    E = float(np.dot(pu, pu))
    F = float(np.dot(pu, pv))
    G = float(np.dot(pv, pv))
    # 第二基本形式（曲率张量）
    L = float(np.dot(puu, n))
    M = float(np.dot(puv, n))
    N = float(np.dot(pvv, n))

    return {"pu": pu, "pv": pv, "puu": puu, "puv": puv, "pvv": pvv,
            "n": n, "E": E, "F": F, "G": G, "L": L, "M": M, "N": N}


def principal_curvatures(
    surface_fn,
    u: float,
    v: float,
    h: float = 1e-4,
) -> Dict[str, float]:
    """真实主曲率 κ1/κ2 —— 解形状算子 S = I⁻¹·II 的特征值

    形状算子（Weingarten）：
        S = (1/(EG-F²)) · [[L·G - M·F,  M·E - L·F],
                           [M·G - N·F,  N·E - M·F]]
    其特征值即主曲率 κ1, κ2（实对称，故为实数）。

    与旧实现的关键差别：旧实现只取 puu·n / pvv·n，忽略了 M(puv) 与
    度量张量的耦合，在扭曲曲面上会给出错误结果。
    """
    ff = fundamental_forms(surface_fn, u, v, h=h)
    E, F, G, L, M, N = ff["E"], ff["F"], ff["G"], ff["L"], ff["M"], ff["N"]

    denom = E * G - F * F
    if abs(denom) < 1e-18:
        raise ValueError(f"曲面在 (u={u}, v={v}) 处度量张量奇异")

    S = np.array([
        [L * G - M * F, M * E - L * F],
        [M * G - N * F, N * E - M * F],
    ], dtype=float) / denom

    # 特征值（主曲率）；对称化以消除有限差分噪声
    S_sym = (S + S.T) / 2.0
    k1, k2 = np.linalg.eigvalsh(S_sym)

    K = k1 * k2                      # 高斯曲率
    H = (k1 + k2) / 2.0              # 平均曲率

    return {
        "k1": float(k1), "k2": float(k2),
        "gaussian_curvature": float(K),
        "mean_curvature": float(H),
        "abs_max": float(max(abs(k1), abs(k2))),
        "normal": ff["n"].tolist(),
    }


@dataclass
class G2Result:
    """两点之间的 G2（曲率连续）判定结果"""
    curvature_ratio: Optional[float]
    passed: bool
    k_a: float
    k_b: float
    detail: str
    threshold: Tuple[float, float] = G2_CURVATURE_RATIO_RANGE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "curvature_ratio": self.curvature_ratio,
            "passed": self.passed,
            "k_a": self.k_a, "k_b": self.k_b,
            "threshold": list(self.threshold),
            "detail": self.detail,
        }


# 绝对曲率容差（1/长度）。低于此值视为"实际平整"。
# 依据：实测中格栅边缘曲率约 1e-6（受数值噪声支配），
# 而车身边缘约 0.1~0.6；用 1e-9 会把噪声当作有效曲率，
# 产生 4e8 这类无意义的比值。
CURVATURE_EPS = 1e-7


def _safe_ratio(k_big: float, k_small: float) -> Optional[float]:
    """曲率比 = 大/小（同号时）。异号表示曲率方向翻转，无法比较。"""
    if abs(k_small) < CURVATURE_EPS:
        return None
    if k_big * k_small <= 0:
        return None                     # 异号：曲率方向相反
    return abs(k_big / k_small)


def check_g2_curvature(
    k_a: float,
    k_b: float,
    ratio_range: Tuple[float, float] = G2_CURVATURE_RATIO_RANGE,
) -> G2Result:
    """按 SOP 的「曲率比 0.8~1.2」判定 G2

    注意：这是**真正的曲率比较**，不是法向夹角阈值。

    三种边界情况：
      1. 两侧都实际平整 → 视为曲率连续（PASS）
      2. 一侧平整、另一侧有曲率 → 曲率变化无限大，不连续（FAIL）
      3. 两侧有曲率但异号 → 曲率方向翻转，不连续（FAIL）
    """
    lo, hi = ratio_range
    a_flat = abs(k_a) < CURVATURE_EPS
    b_flat = abs(k_b) < CURVATURE_EPS

    if a_flat and b_flat:
        return G2Result(1.0, True, k_a, k_b, "两侧均实际平整，视为曲率连续")

    if a_flat or b_flat:
        curved = k_b if a_flat else k_a
        return G2Result(
            None, False, k_a, k_b,
            f"一侧实际平整、另一侧曲率 {curved:.4g}（1/m）：曲率变化无限大，不满足 G2",
        )

    big, small = (k_a, k_b) if abs(k_a) >= abs(k_b) else (k_b, k_a)
    ratio = _safe_ratio(big, small)
    if ratio is None:
        return G2Result(None, False, k_a, k_b,
                        "两侧曲率异号：曲率方向翻转，不满足 G2")

    # 边界容差：SOP 的 0.8/1.2 是闭区间，但浮点表示会使 ratio 恰好等于
    # 边界时（如 1.2000000000000002）被误判为超差。取相对容差吸收该误差。
    eps = 1e-9
    ok = (lo - eps) <= ratio <= (hi + eps)
    return G2Result(
        round(ratio, 4), ok, k_a, k_b,
        f"曲率比 {ratio:.4f} {'在' if ok else '不在'} [{lo},{hi}] 内",
    )


def check_g2_across_seam(
    surface_a_fn,
    surface_b_fn,
    param_a: Tuple[float, float],
    param_b: Tuple[float, float],
    *,
    direction_a: str = "v",
    direction_b: str = "v",
    ratio_range: Tuple[float, float] = G2_CURVATURE_RATIO_RANGE,
) -> G2Result:
    """跨接缝的 G2 判定：取两侧**垂直于接缝方向**的法曲率做比较

    对 A 级曲面接缝而言，沿接缝方向的曲率应连续（即"曲率梳"在接缝处对齐）。
    """
    ka = normal_curvature(surface_a_fn, *param_a, direction=direction_a)
    kb = normal_curvature(surface_b_fn, *param_b, direction=direction_b)
    return check_g2_curvature(ka, kb, ratio_range=ratio_range)


def normal_curvature(
    surface_fn,
    u: float,
    v: float,
    *,
    direction: str = "v",
    h: float = 1e-4,
    normalize_param: bool = True,
) -> float:
    """沿指定参数方向的法曲率 κ_n = II(d,d)/I(d,d)

    这正是「曲率梳」所呈现的量。
    """
    ff = fundamental_forms(surface_fn, u, v, h=h)
    if direction == "v":
        du, dv = ff["pu"], ff["pv"]
        L, M, N = ff["L"], ff["M"], ff["N"]
        E, F, G = ff["E"], ff["F"], ff["G"]
        # 沿 v 方向：二阶量取 N，一阶量取 G
        num, den = N, G
    elif direction == "u":
        num, den = ff["L"], ff["E"]
    else:
        raise ValueError("direction 只能是 'u' 或 'v'")
    if abs(den) < 1e-18:
        return 0.0
    return float(num / den)


# ---------------------------------------------------------------------------
# 自检：用已知解析曲面验证数值正确性
# ---------------------------------------------------------------------------
def _self_test() -> Dict[str, Any]:
    """用球面 / 平面 / 圆柱面验证曲率计算

    球面半径 R 的解析解：κ1 = κ2 = 1/R，K = 1/R²，H = 1/R
    平面：κ1 = κ2 = 0
    圆柱半径 R：κ1 = 1/R, κ2 = 0
    """
    out: Dict[str, Any] = {}

    # --- 球面 R=2 ---
    # 注意：主曲率的**符号**取决于法向取向（此处 pu×pv 指向球心内侧，故为负），
    # 大小才是几何不变量。故按量值比较，同时保留符号供参考。
    R = 2.0

    def sphere(u, v):
        return np.array([R * np.cos(v) * np.cos(u),
                         R * np.cos(v) * np.sin(u),
                         R * np.sin(v)])

    kk = principal_curvatures(sphere, 0.7, 0.4)
    out["sphere"] = {
        "k1": round(kk["k1"], 6), "k2": round(kk["k2"], 6),
        "expected_magnitude": 1.0 / R,
        "err_k1": round(abs(abs(kk["k1"]) - 1.0 / R), 10),
        "err_k2": round(abs(abs(kk["k2"]) - 1.0 / R), 10),
        "gauss": round(kk["gaussian_curvature"], 6),
        "mean": round(kk["mean_curvature"], 6),
        "note": "符号为负表示法向朝向球心侧",
    }

    # --- 平面 ---
    def plane(u, v):
        return np.array([u, v, 0.0])

    kp = principal_curvatures(plane, 0.3, 0.6)
    out["plane"] = {"k1": round(abs(kp["k1"]), 10), "k2": round(abs(kp["k2"]), 10),
                    "expected_magnitude": 0.0}

    # --- 圆柱 R=1.5（沿 u 展开，v 为轴向）---
    Rc = 1.5

    def cyl(u, v):
        return np.array([Rc * np.cos(u), Rc * np.sin(u), v])

    kc = principal_curvatures(cyl, 0.5, 0.3)
    principal = sorted([abs(kc["k1"]), abs(kc["k2"])], reverse=True)
    out["cylinder"] = {
        "k_max": round(principal[0], 6), "k_min": round(principal[1], 10),
        "expected_k_max": 1.0 / Rc,
        "err": round(abs(principal[0] - 1.0 / Rc), 10),
    }
    return out


# ---------------------------------------------------------------------------
# 跨接缝曲率采样（供集成层对 NURBS 曲面 dict 使用）
# ---------------------------------------------------------------------------
def _surface_fn_from_dict(surf: Dict[str, Any]):
    """把 NURBS 曲面 dict 包装为 (u,v) -> np.ndarray(3,) 可调用对象"""
    _ensure_path()
    from algorithm_model.freeform.nurbs_core import evaluate_surface

    def fn(u: float, v: float) -> np.ndarray:
        return np.asarray(evaluate_surface(surf, float(u), float(v)), dtype=float)

    return fn


def sample_edge_curvature(
    surf: Dict[str, Any],
    edge: str,
    *,
    n_samples: int = 9,
    h: float = 1e-4,
    inside: float = 0.02,
    direction: str = "auto",
) -> Optional[np.ndarray]:
    """沿曲面某条边界**内侧**采样法曲率，返回 (n,) 数组

    取内侧而非边界处，是因为边界上的单侧差分不可靠。
    direction='auto' 时选垂直于该边的参数方向（即曲率梳方向）。
    """
    if edge not in ("u0", "u1", "v0", "v1"):
        return None
    fn = _surface_fn_from_dict(surf)
    if direction == "auto":
        direction = "u" if edge in ("u0", "u1") else "v"

    ts = np.linspace(0.0, 1.0, n_samples)
    out: List[float] = []
    for t in ts:
        try:
            if edge == "u0":
                u, v = inside, t
            elif edge == "u1":
                u, v = 1.0 - inside, t
            elif edge == "v0":
                u, v = t, inside
            else:
                u, v = t, 1.0 - inside
            u = min(max(u, h * 2), 1.0 - h * 2)
            v = min(max(v, h * 2), 1.0 - h * 2)
            out.append(normal_curvature(fn, u, v, direction=direction, h=h))
        except Exception:
            continue
    return np.asarray(out, dtype=float) if out else None


def g2_between_surfaces(
    surf_a: Dict[str, Any],
    surf_b: Dict[str, Any],
    *,
    edge_a: Optional[str] = None,
    edge_b: Optional[str] = None,
    n_samples: int = 9,
    ratio_range: Tuple[float, float] = G2_CURVATURE_RATIO_RANGE,
) -> Dict[str, Any]:
    """两个 NURBS 曲面之间的 G2（曲率连续）评估

    分别沿两条边采样法曲率，对齐后逐点比较曲率比。
    未指定边时自动挑选**通过率最高、曲率比最接近 1** 的一对边。
    """
    best: Optional[Dict[str, Any]] = None
    edges_a = [edge_a] if edge_a else ["u0", "u1", "v0", "v1"]
    edges_b = [edge_b] if edge_b else ["u0", "u1", "v0", "v1"]

    for ea in edges_a:
        ca = sample_edge_curvature(surf_a, ea, n_samples=n_samples)
        if ca is None or ca.size == 0:
            continue
        for eb in edges_b:
            cb = sample_edge_curvature(surf_b, eb, n_samples=n_samples)
            if cb is None or cb.size == 0:
                continue
            n = min(ca.size, cb.size)
            ratios: List[float] = []
            n_pass = 0
            for x, y in zip(ca[:n], cb[:n]):
                r = check_g2_curvature(float(x), float(y), ratio_range=ratio_range)
                if r.curvature_ratio is not None:
                    ratios.append(r.curvature_ratio)
                if r.passed:
                    n_pass += 1
            if not ratios:
                continue
            mean_ratio = float(np.mean(ratios))
            cand = {
                "edge_a": ea, "edge_b": eb,
                "pass_rate": round(n_pass / n, 4),
                "mean_curvature_ratio": round(mean_ratio, 4),
                "max_curvature_ratio": round(max(ratios), 4),
                "n_samples": n,
                "g2_pass": bool(n_pass / n >= 0.9),
                "curvature_ratio": round(mean_ratio, 4),
                "threshold": list(ratio_range),
            }
            key = (cand["pass_rate"], -abs(mean_ratio - 1.0))
            if best is None or key > (best["pass_rate"],
                                      -abs(best["mean_curvature_ratio"] - 1.0)):
                best = cand

    if best is None:
        return {"g2_pass": False, "curvature_ratio": None,
                "detail": "无法完成曲率采样（曲面退化或求值失败）",
                "threshold": list(ratio_range)}
    return best


def _demo_g2() -> None:
    """G2 判定的正反例"""
    print("\n=== G2 判定（SOP 曲率比 0.8~1.2）===")
    for name, a, b in [
        ("两侧曲率一致", 0.25, 0.26),
        ("曲率比 1.5（超标）", 0.25, 0.375),
        ("曲率异号（方向翻转）", 0.25, -0.25),
        ("两侧近零（平面）", 1e-12, -1e-12),
    ]:
        r = check_g2_curvature(a, b)
        print("  %-22s → %-6s ratio=%-8s %s" % (
            name, "PASS" if r.passed else "FAIL",
            r.curvature_ratio, r.detail))


if __name__ == "__main__":
    print("=== 曲率数值自检（对比解析解）===")
    res = _self_test()
    for k, v in res.items():
        print(f"  {k:10s} {v}")
    _demo_g2()
