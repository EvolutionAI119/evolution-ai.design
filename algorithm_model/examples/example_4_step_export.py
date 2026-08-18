"""
Example 4 — NURBS 曲面 → STEP 闭环验证 (Phase 1b)

流程：
  1. SweptSurface 沿空间路径扫描圆形截面 → NURBS dict
  2. StepWriter 序列化为 STEP AP214 文件
  3. 结构化校验：ISO 头尾、实体引用完整性、关键实体类型齐全

运行：
  cd D:\\API\\Evolution-Ai.Design
  python algorithm_model\\examples\\example_4_step_export.py
"""

import os
import sys
import re

# 保证可从 examples/ 目录导入 algorithm_model 包
# _HERE = .../algorithm_model/examples ; 项目根 = 上两级
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from algorithm_model.freeform.swept_surface import SweptSurface
from algorithm_model.freeform.step_writer import StepWriter


def build_test_surface() -> dict:
    """构造一个 NURBS 扫掠曲面（模拟车身装饰条/特征线）。"""
    # 路径：沿 X 轴方向的微弯曲线（模拟车身腰线走向）
    path = np.array([
        [0.0, 0.0, 0.0],
        [0.5, 0.02, 0.0],
        [1.0, 0.03, 0.0],
        [1.5, 0.02, 0.0],
        [2.0, 0.0, 0.0],
    ])
    swept = SweptSurface(
        path_points=path,
        section_type='circle',
        section_params={'radius': 0.05, 'n_points': 8},
        path_samples=10,
        degree_u=3,
        degree_v=3,
    )
    surf = swept.build()
    return surf


def validate_step(filename: str) -> dict:
    """STEP 文件结构校验。"""
    with open(filename, 'r', encoding='ascii') as f:
        text = f.read()

    result = {
        'iso_header': text.startswith('ISO-10303-21;'),
        'iso_footer': text.rstrip().endswith('END-ISO-10303-21;'),
        'has_header_sec': 'HEADER;' in text,
        'has_data_sec': 'DATA;' in text,
        'has_endsec': 'ENDSEC;' in text,
    }

    # 提取 DATA 段
    data_match = re.search(r'DATA;\n(.*?)\nENDSEC;', text, re.DOTALL)
    if not data_match:
        result['error'] = 'DATA section not found'
        return result
    data_text = data_match.group(1)

    # 解析实体定义：#N = ...;（含括号构造实体如 #N = (LENGTH_UNIT()...)）
    defined = set()
    for m in re.finditer(r'#(\d+)\s*=', data_text):
        defined.add(int(m.group(1)))
    # 字母开头的具名实体类型统计（括号构造实体不在 required 列表内，跳过类型计数）
    entity_types = {}
    for m in re.finditer(r'#\d+\s*=\s*([A-Z_][A-Z0-9_]*)', data_text):
        etype = m.group(1)
        entity_types[etype] = entity_types.get(etype, 0) + 1
    result['entity_count'] = len(defined)
    result['entity_types'] = entity_types

    # 收集所有引用 #M（排除定义处的 #N=，排除 *）
    refs = set()
    # 仅在实体体中找引用：以 "#数字" 出现且不在 "= #" 定义位置
    for m in re.finditer(r'(?<!\d)#(\d+)', data_text):
        refs.add(int(m.group(1)))
    # 定义自身的 ID 也可能被 regex 捕获（#N = 中的 #N），排除
    unresolved = refs - defined
    # ORIENTED_EDGE 的 * 是合法的自引用占位，无需解析
    result['unresolved_refs'] = sorted(unresolved)
    result['all_refs_resolved'] = (len(unresolved) == 0)

    # 关键实体类型齐全性
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
    print('Phase 1b: NURBS → STEP 闭环验证')
    print('=' * 60)

    # 1. 构造 NURBS 曲面
    surf = build_test_surface()
    cps = surf['control_points']
    print(f'[1] NURBS 曲面构造完成')
    print(f'    控制点网格: {cps.shape} (n_u x n_v x 3)')
    print(f'    次数 (p,q): {surf["degree"]}')
    print(f'    knots_u 长度: {len(surf["knots_u"])}, knots_v 长度: {len(surf["knots_v"])}')
    rational = bool(np.any(np.abs(np.asarray(surf["weights"]) - 1.0) > 1e-9))
    print(f'    有理: {rational}')

    # 2. 写 STEP
    out_dir = os.path.join(_ROOT, 'data', 'step')
    os.makedirs(out_dir, exist_ok=True)
    filename = os.path.join(out_dir, 'muyu_test_surface.step')
    w = StepWriter()
    w.add_surface_as_product(surf, name='muyu_test_surface')
    n_ent = w.write_file(filename)
    size = os.path.getsize(filename)
    print(f'[2] STEP 文件已写入: {filename}')
    print(f'    实体数: {n_ent}, 文件大小: {size} bytes')

    # 3. 校验
    v = validate_step(filename)
    print(f'[3] 结构校验')
    print(f'    ISO 头/尾: {v["iso_header"]}/{v["iso_footer"]}')
    print(f'    HEADER/DATA/ENDSEC: {v["has_header_sec"]}/{v["has_data_sec"]}/{v["has_endsec"]}')
    print(f'    实体总数: {v.get("entity_count", 0)}')
    print(f'    引用完整性: {"OK" if v["all_refs_resolved"] else "FAIL " + str(v["unresolved_refs"])}')
    print(f'    关键实体齐全: {"OK" if v["required_ok"] else "MISSING " + str(v["missing_required"])}')
    print(f'    实体类型分布:')
    for t, c in sorted(v.get('entity_types', {}).items()):
        print(f'      {t:42s} {c}')

    ok = all([
        v['iso_header'], v['iso_footer'], v['has_data_sec'],
        v.get('all_refs_resolved', False), v.get('required_ok', False),
    ])
    print('=' * 60)
    print(f'结果: {"PASS ✅  STEP 闭环验证通过" if ok else "FAIL ❌  见上方细节"}')
    print('=' * 60)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
