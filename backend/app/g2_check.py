"""G2 曲率连续性检测 —— 接入质量检查

把 car_generator 生成的车身曲面与 geometry_curvature 的真实曲率管线对接，
对相邻面板对执行 G2（曲率比 0.8~1.2，SOP-A SURF-001 §5.2）判定。

数据流：
  ModelFile.car_data_json → 提取带 surface 的组件
    → 格式转换（car_generator dict → nurbs_core dict）
    → g2_between_surfaces 逐对评估
    → 汇总报告
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .geometry_curvature import g2_between_surfaces, G2_CURVATURE_RATIO_RANGE

logger = logging.getLogger("evolution.g2_check")

# 相邻面板对：在真实车身中共享接缝、需要做 G2 判定的组合
# 每项 = (组件名A, 组件名B, 接缝说明)
ADJACENT_PAIRS: List[Tuple[str, str, str]] = [
    ("发动机盖", "前风挡玻璃", "机盖-风挡接缝"),
    ("前风挡玻璃", "车顶", "风挡-车顶接缝"),
    ("车顶", "后风挡玻璃", "车顶-后风挡接缝"),
    ("后风挡玻璃", "行李箱盖", "后风挡-行李箱接缝"),
    ("发动机盖", "前保险杠", "机盖-前保接缝"),
    ("行李箱盖", "后保险杠", "行李箱-后保接缝"),
    ("left前门", "left前翼子板", "左前门-左翼子板接缝"),
    ("left前门", "left后门", "左前门-左后门接缝"),
    ("left后门", "left后翼子板", "左后门-左翼子板接缝"),
    ("right前门", "right前翼子板", "右前门-右翼子板接缝"),
    ("right前门", "right后门", "右前门-右后门接缝"),
    ("right后门", "right后翼子板", "右后门-右翼子板接缝"),
]


def _car_surface_to_nurbs_dict(surf: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """把 car_generator 的 NURBSSurface.to_dict() 转为 nurbs_core 格式

    car_generator 格式:
      degree_u, degree_v, control_points (list[list[{x,y,z,weight}]]),
      knot_vector_u, knot_vector_v

    nurbs_core 格式:
      control_points (ndarray n_u×n_v×3), weights (ndarray n_u×n_v),
      degree (p,q), knots_u, knots_v, n (n_u,n_v)
    """
    try:
        cp_rows = surf["control_points"]
        cps = np.array(
            [[[p["x"], p["y"], p["z"]] for p in row] for row in cp_rows],
            dtype=float,
        )
        wts = np.array(
            [[p.get("weight", 1.0) for p in row] for row in cp_rows],
            dtype=float,
        )
        n_u, n_v = cps.shape[:2]
        deg_u = int(surf.get("degree_u", 3))
        deg_v = int(surf.get("degree_v", 3))
        ku = np.asarray(surf.get("knot_vector_u", []), dtype=float)
        kv = np.asarray(surf.get("knot_vector_v", []), dtype=float)

        # 补齐默认节点矢量（均匀）
        if ku.size == 0:
            ku = _default_knots(n_u, deg_u)
        if kv.size == 0:
            kv = _default_knots(n_v, deg_v)

        return {
            "control_points": cps,
            "weights": wts,
            "degree": (deg_u, deg_v),
            "knots_u": ku,
            "knots_v": kv,
            "n": (n_u, n_v),
        }
    except Exception as exc:
        logger.warning("曲面格式转换失败: %s", exc)
        return None


def _default_knots(n: int, p: int) -> np.ndarray:
    """生成均匀 clamped 节点矢量"""
    inner = n - p - 1
    if inner <= 0:
        return np.concatenate([np.zeros(p + 1), np.ones(p + 1)])
    interior = np.linspace(0, 1, inner + 2)[1:-1]
    return np.concatenate([np.zeros(p + 1), interior, np.ones(p + 1)])


def _extract_named_surfaces(
    car_data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """从 car_data_json 提取所有带 NURBS surface 的组件，按名称索引"""
    out: Dict[str, Dict[str, Any]] = {}
    for comp in car_data.get("components", []):
        s = comp.get("surface")
        if not s or "control_points" not in s:
            continue
        name = comp.get("name") or comp.get("type") or "?"
        converted = _car_surface_to_nurbs_dict(s)
        if converted is not None:
            out[name] = converted
    return out


def run_g2_check(car_data: Dict[str, Any]) -> Dict[str, Any]:
    """对整车执行 G2 曲率连续性检测

    Args:
        car_data: generate_complete_car() 返回的完整车身数据

    Returns:
        {
          "overall_g2_pass": bool,
          "n_pairs": int,
          "n_pass": int,
          "n_fail": int,
          "n_no_data": int,
          "pass_rate": float (0-100),
          "pairs": [ { pair, seam, g2_pass, curvature_ratio, ... } ],
          "threshold": [0.8, 1.2],
        }
    """
    surfaces = _extract_named_surfaces(car_data)
    pairs_result: List[Dict[str, Any]] = []
    n_pass = n_fail = n_no_data = 0

    for name_a, name_b, seam_label in ADJACENT_PAIRS:
        surf_a = surfaces.get(name_a)
        surf_b = surfaces.get(name_b)

        if surf_a is None or surf_b is None:
            missing = []
            if surf_a is None:
                missing.append(name_a)
            if surf_b is None:
                missing.append(name_b)
            pairs_result.append({
                "pair": f"{name_a} ↔ {name_b}",
                "seam": seam_label,
                "g2_pass": None,
                "curvature_ratio": None,
                "detail": f"缺数据：{', '.join(missing)} 无 NURBS 曲面",
                "status": "no_data",
            })
            n_no_data += 1
            continue

        try:
            r = g2_between_surfaces(
                surf_a, surf_b,
                n_samples=7,
                ratio_range=G2_CURVATURE_RATIO_RANGE,
            )
            passed = r.get("g2_pass", False)
            ratio = r.get("curvature_ratio")
            detail = r.get("detail", "")

            if not detail and ratio is not None:
                detail = (
                    f"曲率比 {ratio:.4f} "
                    f"{'在' if passed else '不在'} "
                    f"[{G2_CURVATURE_RATIO_RANGE[0]},{G2_CURVATURE_RATIO_RANGE[1]}] 内"
                )

            pairs_result.append({
                "pair": f"{name_a} ↔ {name_b}",
                "seam": seam_label,
                "g2_pass": passed,
                "curvature_ratio": ratio,
                "pass_rate": r.get("pass_rate"),
                "edge_a": r.get("edge_a"),
                "edge_b": r.get("edge_b"),
                "detail": detail,
                "status": "pass" if passed else "fail",
            })
            if passed:
                n_pass += 1
            else:
                n_fail += 1
        except Exception as exc:
            pairs_result.append({
                "pair": f"{name_a} ↔ {name_b}",
                "seam": seam_label,
                "g2_pass": None,
                "curvature_ratio": None,
                "detail": f"评估异常：{type(exc).__name__}: {exc}",
                "status": "error",
            })
            n_no_data += 1

    n_pairs = len(ADJACENT_PAIRS)
    n_evaluated = n_pass + n_fail
    overall = n_fail == 0 and n_evaluated > 0
    pass_rate = round(n_pass / n_evaluated * 100, 1) if n_evaluated > 0 else 0.0

    return {
        "overall_g2_pass": overall,
        "n_pairs": n_pairs,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_no_data": n_no_data,
        "pass_rate": pass_rate,
        "pairs": pairs_result,
        "threshold": list(G2_CURVATURE_RATIO_RANGE),
        "standard": "SOP-A SURF-001 §5.2（曲率比 0.8~1.2）",
    }


def run_g2_check_from_model(model_car_data_json: Optional[str]) -> Dict[str, Any]:
    """从 ModelFile.car_data_json 字符串执行 G2 检测

    供路由层调用。如果 car_data_json 为空则返回错误。
    """
    if not model_car_data_json:
        return {
            "overall_g2_pass": None,
            "n_pairs": len(ADJACENT_PAIRS),
            "n_pass": 0, "n_fail": 0, "n_no_data": len(ADJACENT_PAIRS),
            "pass_rate": 0.0,
            "pairs": [],
            "threshold": list(G2_CURVATURE_RATIO_RANGE),
            "standard": "SOP-A SURF-001 §5.2",
            "error": "该模型无车身数据（car_data_json 为空），请先执行生成",
        }

    car_data = json.loads(model_car_data_json)
    return run_g2_check(car_data)
