"""
Example 5 — 车身截面 NURBS 化 → STEP 闭环验证 (Phase 2)

流程：
  1. CarParams 默认参数（22 维）
  2. build_body_nurbs(params) 生成车身 NURBS 曲面（上半蒙皮）
     - 沿车长 30 站位 × 周向 20 控制点
     - 每站位用 generate_cross_section 取 31 点半截面，构造开放全周 profile
     - 控制点网格 → nurbs_surface_from_grid(degree=3)
  3. validate_body_nurbs 校验包围盒/角点插值/偏差
  4. StepWriter 序列化为 body_phase2.step (STEP AP214)
  5. STEP 结构校验（ISO 头尾 / 引用完整性 / 关键实体齐全）

运行：
  cd D:\\API\\Evolution-Ai.Design
  python algorithm_model\\examples\\example_5_body_nurbs_step.py
"""

import os
import sys
import re

# 保证可从 examples/ 目录导入 algorithm_model 包
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from algorithm_model.car_modeling import CarParams
from algorithm_model.car_modeling.body_nurbs import (
    build_body_nurbs,
    validate_body_nurbs,
)
from algorithm_model.freeform.step_writer import StepWriter


def validate_step(filename: str) -> dict:
    """STEP 文件结构校验（与 example_4 同口径）。"""
    with open(filename, 'r', encoding='ascii') as f:
        text = f.read()

    result = {
        'iso_header': text.startswith('ISO-10303-21;'),
        'iso_footer': text.rstrip().endswith('END-ISO-10303-21;'),
        'has_header_sec': 'HEADER;' in text,
        'has_data_sec': 'DATA;' in text,
        'has_endsec': 'ENDSEC;' in text,
    }

    data_match = re.search(r'DATA;\n(.*?)\nENDSEC;', text, re.DOTALL)
    if not data_match:
        result['error'] = 'DATA section not found'
        return result
    data_text = data_match.group(1)

    defined = set()
    for m in re.finditer(r'#(\d+)\s*=', data_text):
        defined.add(int(m.group(1)))
    entity_types = {}
    for m in re.finditer(r'#\d+\s*=\s*([A-Z_][A-Z0-9_]*)', data_text):
        etype = m.group(1)
        entity_types[etype] = entity_types.get(etype, 0) + 1
    result['entity_count'] = len(defined)
    result['entity_types'] = entity_types

    refs = set()
    for m in re.finditer(r'(?<!\d)#(\d+)', data_text):
        refs.add(int(m.group(1)))
    unresolved = refs - defined
    result['unresolved_refs'] = sorted(unresolved)
    result['all_refs_resolved'] = (len(unresolved) == 0)

    required = [
        'CARTESIAN_POINT', 'DIRECTION', 'AXIS2_PLACEMENT_3D',
        'B_SPLINE_SURFACE_WITH_KNOTS', 'B_SPLINE_CURVE_WITH_KNOTS',
        'VERTEX_POINT', 'EDGE_CURVE', 'ORIENTED_EDGE', 'EDGE_LOOP',
        'FACE_OUTER_BOUND', 'ADVANCED_FACE', 'OPEN_SHELL',
        'SHELL_BASED_SURFACE_MODEL', 'MANIFOLD_SURFACE_SHAPE_REPRESENTATION',
        'PRODUCT', 'PRODUCT_DEFINITION', 'PRODUCT_DEFINITION_SHAPE',
        'SHAPE_DEFINITION_REPRESENTATION',
    ]
    missing = [t for t in required if t not in entity_types]
    result['missing_required'] = missing
    result['required_ok'] = (len(missing) == 0)
    return result


def main():
    print('=' * 60)
    print('Phase 2: 车身截面 NURBS 化 → STEP 闭环验证')
    print('=' * 60)

    # 1. CarParams
    params = CarParams()
    errors = params.validate()
    if errors:
        print('参数错误:')
        for e in errors:
            print(f'  - {e}')
        return 1
    print(f'[1] CarParams 默认参数')
    print(f'    L={params.L}m  W={params.W}m  H={params.H}m  wheelbase={params.wheelbase}m')
    print(f'    hood={params.hood_length}  cabin={params.cabin_length}  trunk={params.trunk_length}')

    # 2. 构建车身 NURBS 曲面
    surf = build_body_nurbs(
        params,
        n_stations=30,
        n_profile=20,
        use_blending=True,
    )
    cps = np.asarray(surf['control_points'])
    print(f'[2] 车身 NURBS 曲面构造完成')
    print(f'    控制点网格: {cps.shape} (n_stations x n_profile x 3)')
    print(f'    次数 (p,q): {surf["degree"]}')
    print(f'    knots_u 长度: {len(surf["knots_u"])}, knots_v 长度: {len(surf["knots_v"])}')
    rational = bool(np.any(np.abs(np.asarray(surf["weights"]) - 1.0) > 1e-9))
    print(f'    有理: {rational}')

    # 3. 曲面校验
    v = validate_body_nurbs(surf, params)
    print(f'[3] 曲面校验')
    print(f'    CP 网格: {v["cp_grid_shape"]}  共 {v["cp_count"]} 控制点')
    print(f'    包围盒 min: {v["bbox_min"]}')
    print(f'    包围盒 max: {v["bbox_max"]}')
    print(f'    包围盒 size: {v["bbox_size"]}')
    print(f'    期望 LWH:   {v["expected_LWH"]}')
    corner_err = [f'{e:.2e}' for e in v['corner_interpolation_err']]
    print(f'    角点插值误差: {corner_err}')
    print(f'    最大曲面-CP偏差: {v["max_surface_to_cp_dev"]:.4f}m')

    # 4. 写 STEP
    out_dir = os.path.join(_ROOT, 'data', 'step')
    os.makedirs(out_dir, exist_ok=True)
    filename = os.path.join(out_dir, 'body_phase2.step')
    w = StepWriter()
    w.add_surface_as_product(surf, name='body_upper_skin')
    n_ent = w.write_file(filename)
    size = os.path.getsize(filename)
    print(f'[4] STEP 文件已写入: {filename}')
    print(f'    实体数: {n_ent}, 文件大小: {size:,} bytes')

    # 5. STEP 结构校验
    sv = validate_step(filename)
    print(f'[5] STEP 结构校验')
    print(f'    ISO 头/尾: {sv["iso_header"]}/{sv["iso_footer"]}')
    print(f'    HEADER/DATA/ENDSEC: {sv["has_header_sec"]}/{sv["has_data_sec"]}/{sv["has_endsec"]}')
    print(f'    实体总数: {sv.get("entity_count", 0)}')
    print(f'    引用完整性: {"OK" if sv["all_refs_resolved"] else "FAIL " + str(sv["unresolved_refs"])}')
    print(f'    关键实体齐全: {"OK" if sv["required_ok"] else "MISSING " + str(sv["missing_required"])}')
    print(f'    实体类型分布 (Top 10):')
    for t, c in sorted(sv.get('entity_types', {}).items(), key=lambda x: -x[1])[:10]:
        print(f'      {t:42s} {c}')

    ok = all([
        sv['iso_header'], sv['iso_footer'], sv['has_data_sec'],
        sv.get('all_refs_resolved', False), sv.get('required_ok', False),
    ])
    print('=' * 60)
    print(f'结果: {"PASS ✅  Phase 2 车身 NURBS → STEP 闭环验证通过" if ok else "FAIL ❌  见上方细节"}')
    print('=' * 60)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
