#!/usr/bin/env python3
"""
EVOLUTION AI 汽车造型开发算法自测脚本

核心算法流程：
1. 硬点参数输入 → 2. 硬点坐标推导 → 3. 轮廓曲线生成 → 4. 截面扫掠 → 5. 车身网格生成

自测目标：确保3D模型参数与标杆车型真实数据一致
"""

import math

# 测试用模型参数（与前端一致）
TEST_MODELS = {
    'sedan_c': {
        'name': 'C级轿车', 'L': 5.10, 'W': 1.99, 'H': 1.51, 'WB': 3.06,
        'FO': 0.85, 'RO': 1.19, 'GC': 0.14, 'WR': 0.33, 'TW': 1.66,
        'AA': 26, 'CA': 40, 'WL': 0.82, 'WBulge': 0.03
    },
    'sedan_d': {
        'name': 'D级轿车', 'L': 5.29, 'W': 1.92, 'H': 1.50, 'WB': 3.22,
        'FO': 0.82, 'RO': 1.25, 'GC': 0.13, 'WR': 0.35, 'TW': 1.62,
        'AA': 26, 'CA': 38, 'WL': 0.77, 'WBulge': 0.02
    },
    'suv_full': {
        'name': '大型SUV', 'L': 5.06, 'W': 2.00, 'H': 1.78, 'WB': 3.11,
        'FO': 0.88, 'RO': 1.07, 'GC': 0.22, 'WR': 0.38, 'TW': 1.68,
        'AA': 28, 'CA': 46, 'WL': 0.85, 'WBulge': 0.02
    },
    'suv_mid': {
        'name': '中型SUV', 'L': 4.85, 'W': 1.99, 'H': 1.70, 'WB': 2.92,
        'FO': 0.81, 'RO': 1.12, 'GC': 0.20, 'WR': 0.36, 'TW': 1.64,
        'AA': 28, 'CA': 44, 'WL': 0.82, 'WBulge': 0.02
    },
    'coupe': {
        'name': '轿跑', 'L': 4.52, 'W': 1.85, 'H': 1.30, 'WB': 2.45,
        'FO': 0.93, 'RO': 1.14, 'GC': 0.12, 'WR': 0.34, 'TW': 1.54,
        'AA': 22, 'CA': 35, 'WL': 0.66, 'WBulge': 0.04
    },
    'sports': {
        'name': '超跑', 'L': 4.57, 'W': 1.96, 'H': 1.22, 'WB': 2.60,
        'FO': 0.88, 'RO': 1.09, 'GC': 0.10, 'WR': 0.35, 'TW': 1.68,
        'AA': 24, 'CA': 32, 'WL': 0.63, 'WBulge': 0.05
    },
}

# 标杆车型真实数据
BENCHMARKS = {
    'sedan_c': {'name': '蔚来ET7', 'L': 5.101, 'W': 1.987, 'H': 1.509, 'WB': 3.060, 'GC': 0.140},
    'sedan_d': {'name': '奔驰S级', 'L': 5.290, 'W': 1.921, 'H': 1.503, 'WB': 3.216, 'GC': 0.130},
    'suv_full': {'name': '宝马X5', 'L': 5.060, 'W': 2.004, 'H': 1.779, 'WB': 3.105, 'GC': 0.220},
    'suv_mid': {'name': '蔚来ES6', 'L': 4.854, 'W': 1.995, 'H': 1.703, 'WB': 2.915, 'GC': 0.200},
    'coupe': {'name': '保时捷911', 'L': 4.519, 'W': 1.852, 'H': 1.298, 'WB': 2.450, 'GC': 0.120},
    'sports': {'name': '法拉利296', 'L': 4.565, 'W': 1.958, 'H': 1.186, 'WB': 2.600, 'GC': 0.100},
}

def derive_hardpoints(params):
    """硬点坐标推导函数（与前端JavaScript一致）"""
    p = params
    fwx = p['FO']
    rwx = p['L'] - p['RO']
    wcy = p['GC'] + p['WR']
    fwz = p['TW'] / 2 + p['WR'] * 0.35
    noseTipY = p['GC'] + 0.43
    hoodY = p['GC'] + 0.66
    waistY = p['GC'] + p['WL']
    if hoodY >= waistY:
        hoodY = waistY - 0.05
    aBaseX = fwx + 0.10
    aTopY = p['H'] * 0.92
    aTopX = aBaseX + (aTopY - waistY) / math.tan(p['AA'] * math.pi / 180)
    roofY = p['H']
    cBaseX = rwx + 0.30
    cTopX = cBaseX - 0.50
    cTopY = aTopY - 0.03
    roofPeakX = (aTopX + cTopX) / 2
    cBaseY = waistY + 0.02
    trunkY = waistY - 0.05
    bumperRY = p['GC'] + 0.42
    frontFenderW = p['W'] / 2 * 0.95
    cabinW = p['W'] / 2 * 0.86
    rearFenderW = p['W'] / 2 * 0.95
    
    return {
        'fwx': fwx, 'rwx': rwx, 'wcy': wcy, 'fwz': fwz,
        'hoodY': hoodY, 'waistY': waistY,
        'aBaseX': aBaseX, 'aTopX': aTopX, 'aTopY': aTopY,
        'roofPeakX': roofPeakX, 'roofY': roofY,
        'cTopX': cTopX, 'cTopY': cTopY,
        'cBaseX': cBaseX, 'cBaseY': cBaseY,
        'trunkY': trunkY, 'noseTipY': noseTipY,
        'bumperRY': bumperRY,
        'frontFenderW': frontFenderW, 'cabinW': cabinW, 'rearFenderW': rearFenderW,
    }

def check_geometry_consistency(params):
    """检查几何一致性"""
    h = derive_hardpoints(params)
    errors = []
    
    actual_wb = h['rwx'] - h['fwx']
    expected_wb = params['WB']
    wb_error = abs(actual_wb - expected_wb)
    if wb_error > 0.01:
        errors.append(f"轴距偏差: 计算={actual_wb:.3f}m, 期望={expected_wb:.3f}m, 误差={wb_error*1000:.1f}mm")
    else:
        print(f"✓ 轴距正确: {actual_wb:.3f}m")
    
    if h['wcy'] <= params['GC']:
        errors.append(f"轮心高度错误: wcy={h['wcy']:.3f}m <= GC={params['GC']:.3f}m")
    else:
        print(f"✓ 轮心高度正确: {h['wcy']:.3f}m")
    
    if h['waistY'] >= h['roofY']:
        errors.append(f"腰线高于车顶: waistY={h['waistY']:.3f}m > roofY={h['roofY']:.3f}m")
    else:
        print(f"✓ 腰线高度合理: {h['waistY']:.3f}m")
    
    if h['aTopX'] >= h['roofPeakX']:
        errors.append(f"A柱顶超过车顶峰值: aTopX={h['aTopX']:.3f}m > roofPeakX={h['roofPeakX']:.3f}m")
    else:
        print(f"✓ A柱顶位置合理: {h['aTopX']:.3f}m")
    
    if h['cTopX'] <= h['aTopX']:
        errors.append(f"C柱顶在A柱顶前方: cTopX={h['cTopX']:.3f}m < aTopX={h['aTopX']:.3f}m")
    else:
        print(f"✓ C柱顶位置合理: {h['cTopX']:.3f}m")
    
    if h['cabinW'] >= h['frontFenderW']:
        errors.append(f"乘员舱宽度大于翼子板: cabinW={h['cabinW']:.3f}m >= frontFenderW={h['frontFenderW']:.3f}m")
    else:
        print(f"✓ 宽度比例合理: cabinW={h['cabinW']:.3f}m < frontFenderW={h['frontFenderW']:.3f}m")
    
    if h['hoodY'] >= h['waistY']:
        errors.append(f"发动机盖高于腰线: hoodY={h['hoodY']:.3f}m > waistY={h['waistY']:.3f}m")
    else:
        print(f"✓ 发动机盖高度合理: {h['hoodY']:.3f}m")
    
    return errors

def analyze_proportions(params):
    """分析车身比例"""
    h = derive_hardpoints(params)
    print("\n=== 比例分析 ===")
    
    wb_ratio = params['WB'] / params['L']
    print(f"轴距/车长比: {wb_ratio:.3f} (理想范围: 0.55-0.62)")
    
    fo_ratio = params['FO'] / params['L']
    print(f"前悬/车长比: {fo_ratio:.3f} (理想范围: 0.15-0.20)")
    
    hw_ratio = params['H'] / params['W']
    print(f"高宽比: {hw_ratio:.3f} (轿车: 0.70-0.78, SUV: 0.85-0.92)")
    
    tw_ratio = params['TW'] / params['W']
    print(f"轮距/车宽比: {tw_ratio:.3f} (理想范围: 0.80-0.88)")
    
    waist_ratio = h['waistY'] / params['H']
    print(f"腰线高度/车高比: {waist_ratio:.3f} (理想范围: 0.55-0.65)")
    
    gc_ratio = params['GC'] / params['H']
    print(f"离地间隙/车高比: {gc_ratio:.3f} (理想范围: 0.08-0.15)")

def verify_against_benchmark(model_name, params, benchmark_data):
    """验证模型参数与标杆数据一致性"""
    print(f"\n=== {model_name} 标杆验证 ===")
    errors = []
    
    for key, expected in benchmark_data.items():
        if key == 'name':
            continue
        if key in params:
            actual = params[key]
            if isinstance(actual, str) or isinstance(expected, str):
                continue
            error = abs(actual - expected)
            if error > 0.05:
                errors.append(f"{key}: 模型={actual:.3f}, 标杆={expected:.3f}, 偏差={error*1000:.1f}mm")
            else:
                print(f"✓ {key}: {actual:.3f}m (标杆: {expected:.3f}m, 偏差: {error*1000:.1f}mm)")
    
    return errors

def main():
    print("=" * 70)
    print("EVOLUTION AI 汽车造型开发算法自测")
    print("=" * 70)
    
    all_errors = []
    
    for model_key, model_data in TEST_MODELS.items():
        print(f"\n{'='*50}")
        print(f"测试车型: {model_data['name']} ({model_key})")
        if model_key in BENCHMARKS:
            print(f"标杆车型: {BENCHMARKS[model_key]['name']}")
        print(f"{'='*50}")
        
        errors = check_geometry_consistency(model_data)
        all_errors.extend([f"{model_key}: {e}" for e in errors])
        
        analyze_proportions(model_data)
        
        if model_key in BENCHMARKS:
            bm_errors = verify_against_benchmark(model_data['name'], model_data, BENCHMARKS[model_key])
            all_errors.extend([f"{model_key}: {e}" for e in bm_errors])
    
    print(f"\n{'='*70}")
    print("自测结果汇总")
    print(f"{'='*70}")
    
    if all_errors:
        print(f"\n❌ 发现 {len(all_errors)} 个问题:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        return 1
    else:
        print("\n✅ 所有检查通过！")
        return 0

if __name__ == '__main__':
    exit(main())