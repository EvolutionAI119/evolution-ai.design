"""
车身 NURBS 化（Phase 2）— 双轨并行：mesh 管线(body.py) + NURBS 管线(本模块)

将车身从"参数化截面 → 三角网格"改为"参数化截面 → NURBS 控制点网格 → nurbs_surface_from_grid"。
输出 surf dict 可直接喂给 step_writer 生成 body.step。

设计（参数直驱，非 mesh→NURBS 拟合）：
  1. 沿车长取 n_stations 个站位 x_norm ∈ [-1, 1]
  2. 每站位用 generate_cross_section 取 31 点半截面 (y≥0, z 0→1)
  3. 构造开放全周 profile：左下(y>0,z=0) → 车顶(y>0,z=1) → 右下(y<0,z=0)
  4. profile 点直接作为 NURBS 控制点（clamped open-uniform 节点 → 边界角点插值、内部平滑逼近）
  5. 控制点网格 (n_stations, n_profile, 3) → nurbs_surface_from_grid(degree=3)

曲面参数：u=车长方向(开放)，v=周向(开放，左下→顶→右下)。代表车身上半蒙皮（侧围+车顶）。
"""

from typing import Dict
import numpy as np

from .body import get_hardpoints, _section_height
from .parametrize import generate_cross_section, ZONE_PARAMS_TABLE


def _body_skin_profile(
    x: float,
    hardpoints: Dict[str, float],
    zone_params=ZONE_PARAMS_TABLE,
    n_profile: int = 20,
) -> np.ndarray:
    """构造单站位的开放全周截面 profile (n_profile, 2) of (y, z)。

    左下(y>0,z=0) → 车顶(y>0,z=1) → 右下(y<0,z=0)，开放曲线。
    用 generate_cross_section 的 31 点半截面（y≥0, z 0→1 升再 1→0 闭），
    取升段 0..24 作为左半，镜像翻转作为右半。
    """
    cs = generate_cross_section(x, zone_params, hardpoints)
    pts = cs.points  # (31, 2), y≥0

    # 左半：升段 points[0..24] (z: 0→1)
    left = pts[0:25].copy()  # (25, 2)
    # 右半：left 翻转去首（去掉车顶重复点），y 取负
    right = left[-2::-1].copy()  # (24, 2), z: 1→0
    right[:, 0] = -right[:, 0]

    full = np.vstack([left, right])  # (49, 2)

    # 均匀子采样到 n_profile（保留首末角点）
    if n_profile < len(full):
        idx = np.linspace(0, len(full) - 1, n_profile).astype(int)
        full = full[idx]
    return full  # (n_profile, 2)


def build_body_nurbs(
    params,
    n_stations: int = 30,
    n_profile: int = 20,
    use_blending: bool = True,
    x_margin: float = 1.0,
) -> dict:
    """构建车身 NURBS 曲面（上半蒙皮），尺寸对齐真车 L×W×H。

    三项关键修正（让模型与真车一致）：
      1. 车宽：以中部最大半宽归一化到 W/2，消除 y_scales+shape_factors 衰减
      2. 车高：z 归一化到 [0,1] 后映射到 [ground_clearance, section_height]
      3. 侧面轮廓：每站位用 _section_height(xn, params) 作为车顶高度
         （引擎盖低→挡风斜上→车顶高→后挡风斜下→行李箱低）

    Args:
        params: CarParams
        n_stations: 车长方向控制点数（站位）
        n_profile: 周向控制点数
        use_blending: 启用三区段 blending
        x_margin: x_norm 范围 [-x_margin, x_margin]，1.0 = 完整车长

    Returns:
        nurbs_surface_from_grid dict: control_points (n_stations, n_profile, 3) + ...
    """
    from ..freeform.nurbs_core import nurbs_surface_from_grid

    hardpoints = get_hardpoints(params)
    zone_params = ZONE_PARAMS_TABLE if use_blending else None

    # 采样中部站位最大半宽，计算 y 缩放系数（让中部半宽 = W/2）
    mid_prof = _body_skin_profile(0.0, hardpoints, zone_params, n_profile)
    mid_max_y = max(mid_prof[:, 0].max(), 1e-6)
    y_scale = (params.W / 2) / mid_max_y

    x_norms = np.linspace(-x_margin, x_margin, n_stations)
    cp_grid = np.zeros((n_stations, n_profile, 3))

    for i, xn in enumerate(x_norms):
        x = xn * params.L / 2
        prof = _body_skin_profile(x, hardpoints, zone_params, n_profile)

        # y 缩放到 W/2 基准（保留截面形状比例，中部半宽 = W/2）
        y_actual = prof[:, 0] * y_scale

        # z 归一化到 [0, 1] 再映射到 [ground_clearance, section_height]
        section_h = _section_height(xn, params)
        z_min = prof[:, 1].min()
        z_max = prof[:, 1].max()
        z_norm = (prof[:, 1] - z_min) / max(z_max - z_min, 1e-6)
        z_actual = params.ground_clearance + z_norm * (section_h - params.ground_clearance)

        cp_grid[i, :, 0] = x
        cp_grid[i, :, 1] = y_actual
        cp_grid[i, :, 2] = z_actual

    # 次数受控制点数限制
    deg_u = min(3, n_stations - 1)
    deg_v = min(3, n_profile - 1)
    return nurbs_surface_from_grid(cp_grid, degree_u=deg_u, degree_v=deg_v)


def validate_body_nurbs(surf: dict, params) -> dict:
    """校验车身 NURBS 曲面：包围盒、CP 数、边界退化、采样偏差。"""
    from ..freeform.nurbs_core import evaluate_surface

    cps = np.asarray(surf['control_points'])
    n_u, n_v = cps.shape[0], cps.shape[1]

    # 包围盒（车身应近似 L × 2W × H）
    bbox_min = cps.min(axis=(0, 1))
    bbox_max = cps.max(axis=(0, 1))
    size = bbox_max - bbox_min

    # 边界角点插值检查：曲面在 (0,0)/(0,1)/(1,0)/(1,1) 应过对应 CP
    corners_param = [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0), (1.0, 1.0)]
    corner_err = []
    for (u, v) in corners_param:
        pt = evaluate_surface(surf, u, v)
        i = 0 if u < 0.5 else n_u - 1
        j = 0 if v < 0.5 else n_v - 1
        corner_err.append(float(np.linalg.norm(pt - cps[i, j])))

    # 采样偏差：内部参数点处曲面与最近 CP 的偏差量级
    max_dev = 0.0
    for u in np.linspace(0, 1, 7):
        for v in np.linspace(0, 1, 7):
            pt = evaluate_surface(surf, u, v)
            # 找最近 CP 距离
            d = np.linalg.norm(cps.reshape(-1, 3) - pt, axis=1).min()
            max_dev = max(max_dev, float(d))

    return {
        'cp_grid_shape': (n_u, n_v),
        'cp_count': n_u * n_v,
        'bbox_min': bbox_min.tolist(),
        'bbox_max': bbox_max.tolist(),
        'bbox_size': size.tolist(),
        'expected_LWH': [params.L, params.W, params.H],
        'corner_interpolation_err': corner_err,
        'max_surface_to_cp_dev': max_dev,
        'degree': list(surf['degree']),
    }
