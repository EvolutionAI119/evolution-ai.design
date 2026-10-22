"""
2D/3D 曲面形状无量纲特征提取
=============================

吸收 SISA ``features.py`` 的方法论，独立实现 12 维无量纲特征提取。

设计原则
--------
1. **无量纲化**：所有特征归一化到 [0,1] 或比值，确保跨车型/跨部位可比
2. **失败即返回 None**：任何一步失败返回 None，不静默产出假特征
3. **独立依赖**：仅依赖 numpy，不 import SISA 任何模块
4. **数据契约兼容**：输出格式与 SISA ``SurfaceFeatures.as_dict()`` 一致，
   支持双方成果互通

特征清单（12 维）
-----------------
 1  deg_u              u 方向次数（拓扑复杂度）
 2  deg_v              v 方向次数
 3  cp_ratio           控制点网格长宽比
 4  cp_total           控制点数（规模，对数归一化）
 5  span_ratio         参数域跨度比
 6  extent_aspect      包围盒长短轴比
 7  extent_mid         包围盒中轴占比
 8  planarity          平面度（最小奇异值 / 最大奇异值）
 9  cp_roughness       控制点邻域差分粗糙度（归一化）
10  knot_uniformity_u  u 节点均匀度
11  knot_uniformity_v  v 节点均匀度
12  weight_dev         权重偏离 1 的程度（有理曲面特征）
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

#: 特征维度
FEATURE_DIM = 12

#: 特征名称（顺序固定，与 SISA 兼容）
FEATURE_NAMES = (
    "deg_u", "deg_v", "cp_ratio", "cp_total",
    "span_ratio", "extent_aspect", "extent_mid", "planarity",
    "cp_roughness", "knot_uniformity_u", "knot_uniformity_v", "weight_dev",
)


@dataclass
class SurfaceFeatures:
    """一张曲面的无量纲特征

    与 SISA ``SurfaceFeatures`` 数据契约兼容，可双向交换。
    """
    family: str = "other"
    source: str = ""
    vec: List[float] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "source": self.source,
            "vec": [round(v, 6) for v in self.vec],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SurfaceFeatures":
        return cls(
            family=d.get("family", "other"),
            source=d.get("source", ""),
            vec=list(d.get("vec", [])),
        )


def _normalize_knots(vals: Sequence[float]) -> Tuple[float, float]:
    """归一化节点向量到 [0,1]，返回 (span, 均匀度)

    均匀度 = 1 / (1 + CV)，CV 为相邻差分的变异系数。
    完全均匀 → 1.0，极度不均匀 → 趋近 0。
    """
    a = np.asarray(vals, dtype=float)
    if a.size < 2:
        return 0.0, 0.0
    span = float(a[-1] - a[0])
    if span <= 1e-12:
        return 0.0, 0.0
    u = (a - a[0]) / span
    d = np.diff(u)
    if d.size == 0 or d.mean() <= 1e-12:
        return float(span), 0.0
    cv = float(d.std() / d.mean())
    return float(span), float(1.0 / (1.0 + cv))


def extract_features(
    control_points: Any,
    *,
    degree_u: int = 0,
    degree_v: int = 0,
    knots_u: Optional[Sequence[float]] = None,
    knots_v: Optional[Sequence[float]] = None,
    weights: Optional[Sequence[float]] = None,
    family: str = "other",
    source: str = "",
) -> Optional[SurfaceFeatures]:
    """由控制点矩阵提取 12 维无量纲特征

    参数
    ----
    control_points: numpy 数组或可转为数组的对象，shape (n_u, n_v, 3)
    degree_u / degree_v: 曲面次数
    knots_u / knots_v: 节点向量（可选）
    weights: 权重数组（可选，有理曲面用）
    family / source: 分类标签

    返回
    ----
    SurfaceFeatures 或 None（任何一步失败）
    """
    try:
        cp = np.asarray(control_points, dtype=float)
        if cp.ndim != 3 or cp.shape[2] != 3:
            return None
        n_u, n_v = cp.shape[0], cp.shape[1]
        if n_u < 2 or n_v < 2:
            return None

        # 1-2: 次数
        deg_u = float(degree_u)
        deg_v = float(degree_v)

        # 3: 控制点网格长宽比
        cp_ratio = float(n_u / n_v) if n_v else 0.0

        # 4: 控制点数（对数归一化到 [0,1]，1→0, 10000→1）
        cp_total_raw = float(n_u * n_v)
        cp_total = math.log10(max(cp_total_raw, 1.0)) / 4.0
        cp_total = max(0.0, min(1.0, cp_total))

        # 5: 参数域跨度比
        span_u, uni_u = _normalize_knots(knots_u or [])
        span_v, uni_v = _normalize_knots(knots_v or [])
        span_ratio = float(span_u / span_v) if span_v > 1e-12 else 0.0

        # 6-7: 包围盒（相对量）
        flat = cp.reshape(-1, 3)
        lo, hi = flat.min(axis=0), flat.max(axis=0)
        ext = np.sort(hi - lo)[::-1]
        mx = float(ext[0]) if ext[0] > 1e-12 else 1.0
        extent_aspect = float(ext[1] / mx) if mx > 0 else 0.0
        extent_mid = float(ext[2] / mx) if mx > 0 else 0.0

        # 8: 平面度（SVD 最小奇异值 / 最大奇异值）
        centered = flat - flat.mean(axis=0)
        try:
            s = np.linalg.svd(centered, compute_uv=False)
            planarity = float(s[-1] / s[0]) if s[0] > 1e-12 else 0.0
        except np.linalg.LinAlgError:
            planarity = 0.0

        # 9: 控制点邻域差分粗糙度（u 方向二阶差分归一化）
        try:
            d2 = np.diff(cp, n=2, axis=0)
            rough = float(np.linalg.norm(d2) / max(cp_total_raw, 1.0))
            cp_roughness = min(1.0, rough)
        except Exception:
            cp_roughness = 0.0

        # 10-11: 节点均匀度
        knot_uni_u = uni_u
        knot_uni_v = uni_v

        # 12: 权重偏离 1 的程度
        if weights is not None:
            w = np.asarray(weights, dtype=float)
            if w.size > 0:
                weight_dev = float(np.mean(np.abs(w - 1.0)))
                weight_dev = min(1.0, weight_dev)
            else:
                weight_dev = 0.0
        else:
            weight_dev = 0.0

        vec = [
            deg_u, deg_v, cp_ratio, cp_total,
            span_ratio, extent_aspect, extent_mid, planarity,
            cp_roughness, knot_uni_u, knot_uni_v, weight_dev,
        ]

        return SurfaceFeatures(family=family, source=source, vec=vec)

    except Exception:
        return None


def feature_vector_to_dict(vec: Sequence[float]) -> Dict[str, float]:
    """将特征向量转为 {name: value} 字典"""
    if len(vec) != FEATURE_DIM:
        raise ValueError(f"特征向量长度必须为 {FEATURE_DIM}, 实际 {len(vec)}")
    return {name: float(val) for name, val in zip(FEATURE_NAMES, vec)}


__all__ = [
    "SurfaceFeatures",
    "extract_features",
    "feature_vector_to_dict",
    "FEATURE_DIM",
    "FEATURE_NAMES",
]
