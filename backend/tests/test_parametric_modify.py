"""
汽车参数化修改功能测试
"""

import sys
import os

# 直接添加模块路径
modules_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'modules')
sys.path.insert(0, modules_path)

from nurbs_engine import NURBSSurface, NURBSCurve, ControlPoint, KnotVector, SurfaceModifier
from sketch_editor import Sketch, SketchModifier, ConstraintType
from parametric_modifier import (
    ParametricModifier, 
    AutomotiveParameterLibrary,
    ModificationType,
    ModificationOperation,
    Parameter,
    ParameterType
)
from measurement_tool import (
    MeasurementTool,
    SurfaceMeasurement,
    AutomotiveMeasurement,
    MeasurementPoint
)
import numpy as np


def test_automotive_parameters():
    """测试汽车参数库"""
    print("=" * 60)
    print("测试1: 汽车参数库")
    print("=" * 60)
    
    lib = AutomotiveParameterLibrary()
    params = lib.get_automotive_parameters()
    
    print(f"\n共有 {len(params)} 个汽车标准参数:")
    print("-" * 40)
    
    for key, param in params.items():
        print(f"  [{param.category}] {param.name}")
        print(f"    当前值: {param.value} {param.unit}")
        print(f"    范围: {param.min_value} - {param.max_value}")
        if param.target_value:
            print(f"    目标值: {param.target_value}")
            print(f"    公差: +{param.tolerance_plus}/-{param.tolerance_minus}")
        print()
    
    return params


def test_nurbs_surface():
    """测试NURBS曲面创建和修改"""
    print("=" * 60)
    print("测试2: NURBS曲面创建与修改")
    print("=" * 60)
    
    # 创建汽车引擎盖曲面
    print("\n创建汽车引擎盖曲面...")
    
    degree_u, degree_v = 3, 3
    num_u, num_v = 8, 6
    
    # 控制点网格 - 模拟引擎盖形状
    control_points = []
    for i in range(num_u):
        row = []
        u_param = i / (num_u - 1)
        for j in range(num_v):
            v_param = j / (num_v - 1)
            
            # X: 沿车身方向 (0-1500mm)
            x = u_param * 1500
            
            # Y: 沿宽度方向 (-750 to 750mm)
            y = (v_param - 0.5) * 1500
            
            # Z: 高度变化，模拟引擎盖弧度
            z = 50 + 100 * np.sin(u_param * np.pi) * np.cos(v_param * np.pi * 0.5)
            
            # 边缘权重增加，使边缘更尖锐
            weight = 1.0
            if i == 0 or i == num_u - 1 or j == 0 or j == num_v - 1:
                weight = 1.5
            
            row.append(ControlPoint(x, y, z, weight))
        control_points.append(row)
    
    surface = NURBSSurface(
        degree_u=degree_u,
        degree_v=degree_v,
        control_points=control_points
    )
    
    print(f"  曲面创建成功!")
    print(f"  阶数: {surface.degree_u} x {surface.degree_v}")
    print(f"  控制点数: {len(control_points)} x {len(control_points[0])}")
    
    # 评估曲面上的点
    print("\n评估曲面上的点:")
    test_points = [(0.0, 0.5), (0.5, 0.5), (1.0, 0.5), (0.5, 0.0), (0.5, 1.0)]
    
    for u, v in test_points:
        point = surface.evaluate_point(u, v)
        normal = surface.evaluate_normal(u, v)
        curvature = surface.evaluate_curvature(u, v)
        
        print(f"\n  参数 (u={u}, v={v}):")
        print(f"    点坐标: ({point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f})")
        print(f"    法向量: ({normal[0]:.4f}, {normal[1]:.4f}, {normal[2]:.4f})")
        print(f"    高斯曲率: {curvature['gaussian_curvature']:.6f}")
        print(f"    平均曲率: {curvature['mean_curvature']:.6f}")
    
    return surface


def test_surface_modification():
    """测试曲面修改操作"""
    print("=" * 60)
    print("测试3: 曲面修改操作")
    print("=" * 60)
    
    modifier = ParametricModifier()
    
    # 创建测试曲面
    control_points = [
        [ControlPoint(0, 0, 0, 1), ControlPoint(0, 100, 0, 1), ControlPoint(0, 200, 0, 1)],
        [ControlPoint(100, 0, 50, 1), ControlPoint(100, 100, 60, 1), ControlPoint(100, 200, 50, 1)],
        [ControlPoint(200, 0, 100, 1), ControlPoint(200, 100, 110, 1), ControlPoint(200, 200, 100, 1)],
        [ControlPoint(300, 0, 50, 1), ControlPoint(300, 100, 60, 1), ControlPoint(300, 200, 50, 1)],
    ]
    
    surface = NURBSSurface(degree_u=3, degree_v=2, control_points=control_points)
    modifier.add_surface("test_surface", surface)
    
    print("\n初始曲面信息:")
    p = surface.evaluate_point(0.5, 0.5)
    print(f"  中心点: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
    
    # 测试平移
    print("\n执行平移操作 (dx=50, dy=0, dz=20):")
    op = ModificationOperation(
        operation_type=ModificationType.TRANSLATE,
        parameters={'dx': 50, 'dy': 0, 'dz': 20}
    )
    modifier.modify_surface("test_surface", op)
    p = surface.evaluate_point(0.5, 0.5)
    print(f"  平移后中心点: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
    
    # 测试缩放
    print("\n执行缩放操作 (sx=1.5, sy=1.0, sz=1.0):")
    op = ModificationOperation(
        operation_type=ModificationType.SCALE,
        parameters={'sx': 1.5, 'sy': 1.0, 'sz': 1.0}
    )
    modifier.modify_surface("test_surface", op)
    p = surface.evaluate_point(0.5, 0.5)
    print(f"  缩放后中心点: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
    
    # 测试旋转
    print("\n执行旋转操作 (angle=30, axis='z'):")
    op = ModificationOperation(
        operation_type=ModificationType.ROTATE,
        parameters={'angle': 30, 'axis': 'z'}
    )
    modifier.modify_surface("test_surface", op)
    p = surface.evaluate_point(0.5, 0.5)
    print(f"  旋转后中心点: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
    
    print(f"\n修改历史记录数: {len(modifier.history)}")
    
    return modifier


def test_sketch_editor():
    """测试草图编辑器"""
    print("=" * 60)
    print("测试4: 草图编辑器")
    print("=" * 60)
    
    sketch = Sketch("汽车侧视图轮廓")
    
    # 创建车身轮廓
    print("\n创建车身轮廓草图:")
    
    # 底盘线
    sketch.add_line((0, 0), (4800, 0))
    print("  添加底盘线: (0,0) -> (4800,0)")
    
    # 前保险杠
    sketch.add_line((0, 0), (0, 300))
    print("  添加前保险杠: (0,0) -> (0,300)")
    
    # 发动机盖
    sketch.add_line((0, 300), (1200, 350))
    print("  添加发动机盖: (0,300) -> (1200,350)")
    
    # A柱
    sketch.add_line((1200, 350), (1500, 1200))
    print("  添加A柱: (1200,350) -> (1500,1200)")
    
    # 车顶
    sketch.add_line((1500, 1200), (3000, 1250))
    print("  添加车顶: (1500,1200) -> (3000,1250)")
    
    # C柱
    sketch.add_line((3000, 1250), (3500, 600))
    print("  添加C柱: (3000,1250) -> (3500,600)")
    
    # 后风挡
    sketch.add_line((3500, 600), (4000, 400))
    print("  添加后风挡: (3500,600) -> (4000,400)")
    
    # 后备箱
    sketch.add_line((4000, 400), (4500, 350))
    print("  添加后备箱: (4000,400) -> (4500,350)")
    
    # 后保险杠
    sketch.add_line((4500, 350), (4800, 300))
    sketch.add_line((4800, 300), (4800, 0))
    print("  添加后保险杠")
    
    # 添加轮拱
    sketch.add_circle((800, 0), 350)   # 前轮
    sketch.add_circle((3500, 0), 350)  # 后轮
    print("  添加前后轮拱 (半径350mm)")
    
    # 添加约束
    sketch.add_constraint(ConstraintType.HORIZONTAL, [1])  # 底盘线水平
    sketch.add_constraint(ConstraintType.EQUAL_RADIUS, [10, 11])  # 两轮等半径
    print("  添加约束: 底盘水平, 两轮等半径")
    
    print(f"\n草图统计:")
    print(f"  实体数: {len(sketch.entities)}")
    print(f"  约束数: {len(sketch.constraints)}")
    
    # 测试草图修改
    print("\n测试草图缩放 (factor=0.5):")
    modifier = SketchModifier(sketch)
    modifier.scale(0.5)
    
    line_entity = sketch.entities[0]
    if hasattr(line_entity.data, 'end'):
        print(f"  底盘线长度: {line_entity.data.end.x}")
    
    return sketch


def test_measurement():
    """测试测量工具"""
    print("=" * 60)
    print("测试5: 测量工具")
    print("=" * 60)
    
    tool = MeasurementTool()
    
    # 测试距离测量
    print("\n距离测量测试:")
    p1 = MeasurementPoint(0, 0, 0)
    p2 = MeasurementPoint(4800, 0, 0)
    m1 = tool.measure_distance(p1, p2, "整车长度")
    print(f"  整车长度: {m1.value:.2f} {m1.unit}")
    
    p3 = MeasurementPoint(0, 0, 0)
    p4 = MeasurementPoint(0, 1850, 0)
    m2 = tool.measure_distance(p3, p4, "整车宽度")
    print(f"  整车宽度: {m2.value:.2f} {m2.unit}")
    
    p5 = MeasurementPoint(0, 0, 0)
    p6 = MeasurementPoint(0, 0, 1450)
    m3 = tool.measure_distance(p5, p6, "整车高度")
    print(f"  整车高度: {m3.value:.2f} {m3.unit}")
    
    # 测试角度测量
    print("\n角度测量测试:")
    vertex = MeasurementPoint(1200, 350, 0)
    point1 = MeasurementPoint(0, 300, 0)
    point2 = MeasurementPoint(1500, 1200, 0)
    m4 = tool.measure_angle(vertex, point1, point2, "A柱角度")
    print(f"  A柱角度: {m4.value:.2f} {m4.unit}")
    
    # 测试半径测量
    print("\n半径测量测试:")
    center = MeasurementPoint(800, 0, 0)
    point = MeasurementPoint(800, 350, 0)
    m5 = tool.measure_radius(center, point, "前轮半径")
    print(f"  前轮半径: {m5.value:.2f} {m5.unit}")
    
    # 测量摘要
    summary = tool.get_summary()
    print(f"\n测量摘要:")
    print(f"  总测量数: {summary['total']}")
    for type_name, stats in summary.get('by_type', {}).items():
        print(f"  {type_name}: 平均={stats['avg']:.2f}, 最小={stats['min']:.2f}, 最大={stats['max']:.2f}")
    
    return tool


def test_parametric_drive():
    """测试参数驱动"""
    print("=" * 60)
    print("测试6: 参数驱动修改")
    print("=" * 60)
    
    modifier = ParametricModifier()
    
    # 添加汽车参数
    lib = AutomotiveParameterLibrary()
    params = lib.get_automotive_parameters()
    
    for key, param in params.items():
        modifier.add_parameter(param)
    
    print(f"\n已加载 {len(modifier.parameters)} 个参数")
    
    # 创建测试曲面
    control_points = [
        [ControlPoint(0, -925, 0, 1), ControlPoint(0, 0, 50, 1), ControlPoint(0, 925, 0, 1)],
        [ControlPoint(2400, -925, 100, 1), ControlPoint(2400, 0, 150, 1), ControlPoint(2400, 925, 100, 1)],
        [ControlPoint(4800, -925, 0, 1), ControlPoint(4800, 0, 50, 1), ControlPoint(4800, 925, 0, 1)],
    ]
    
    surface = NURBSSurface(degree_u=2, degree_v=2, control_points=control_points)
    modifier.add_surface("body_surface", surface)
    
    print("\n初始曲面:")
    p = surface.evaluate_point(0.5, 0.5)
    print(f"  中心点: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
    
    # 修改整车长度参数
    print("\n修改整车长度参数: 4800 -> 5000")
    modifier.set_parameter("overall_length", 5000)
    
    # 修改整车宽度参数
    print("\n修改整车宽度参数: 1850 -> 2000")
    modifier.set_parameter("overall_width", 2000)
    
    # 修改整车高度参数
    print("\n修改整车高度参数: 1450 -> 1500")
    modifier.set_parameter("overall_height", 1500)
    
    # 应用参数驱动
    modifier.apply_parameter_drive("overall_length", "body_surface", {'scale_factor': 5000/4800})
    
    print("\n参数驱动后曲面:")
    p = surface.evaluate_point(0.5, 0.5)
    print(f"  中心点: ({p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f})")
    
    # 导出参数状态
    print("\n导出参数状态:")
    state = modifier.export_parameters()
    print(f"  参数数: {len(state['parameters'])}")
    print(f"  历史数: {len(state['history'])}")
    
    return modifier


def test_surface_quality():
    """测试曲面质量分析"""
    print("=" * 60)
    print("测试7: 曲面质量分析")
    print("=" * 60)
    
    # 创建A级曲面测试
    print("\n创建A级曲面测试模型:")
    
    degree_u, degree_v = 5, 5  # 高阶曲面
    num_u, num_v = 10, 8
    
    control_points = []
    for i in range(num_u):
        row = []
        for j in range(num_v):
            x = i * 100
            y = (j - 3.5) * 100
            # 平滑曲面
            z = 20 * np.sin(i * 0.3) * np.cos(j * 0.3)
            weight = 1.0
            row.append(ControlPoint(x, y, z, weight))
        control_points.append(row)
    
    surface = NURBSSurface(
        degree_u=degree_u,
        degree_v=degree_v,
        control_points=control_points
    )
    
    sm = SurfaceMeasurement()
    
    print("\n曲率分布分析:")
    curvature_map = sm.measure_surface_curvature_map(surface, num_samples=5)
    
    gaussian_curvatures = [c['gaussian_curvature'] for c in curvature_map]
    mean_curvatures = [c['mean_curvature'] for c in curvature_map]
    
    print(f"  高斯曲率范围: {min(gaussian_curvatures):.6f} ~ {max(gaussian_curvatures):.6f}")
    print(f"  平均曲率范围: {min(mean_curvatures):.6f} ~ {max(mean_curvatures):.6f}")
    
    # 检查连续性
    print("\n曲面连续性评估:")
    # 创建两个相邻曲面测试连续性
    control_points2 = []
    for i in range(num_u):
        row = []
        for j in range(num_v):
            x = i * 100 + 1000
            y = (j - 3.5) * 100
            z = 20 * np.sin((i + 10) * 0.3) * np.cos(j * 0.3)
            row.append(ControlPoint(x, y, z, 1.0))
        control_points2.append(row)
    
    surface2 = NURBSSurface(
        degree_u=degree_u,
        degree_v=degree_v,
        control_points=control_points2
    )
    
    continuity = sm.measure_continuity(surface, surface2)
    print(f"  G0距离平均: {continuity['G0_distance_avg']:.4f}")
    print(f"  G1角度平均: {continuity['G1_angle_avg']:.2f}°")
    print(f"  连续性等级: {continuity['continuity_level']}")
    
    return surface


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("*" * 60)
    print("*  EVOLUTION AI - 汽车参数化修改功能测试")
    print("*" * 60)
    print("\n")
    
    try:
        # 测试1: 汽车参数库
        params = test_automotive_parameters()
        
        # 测试2: NURBS曲面
        surface = test_nurbs_surface()
        
        # 测试3: 曲面修改
        modifier = test_surface_modification()
        
        # 测试4: 草图编辑
        sketch = test_sketch_editor()
        
        # 测试5: 测量工具
        tool = test_measurement()
        
        # 测试6: 参数驱动
        param_modifier = test_parametric_drive()
        
        # 测试7: 曲面质量
        quality_surface = test_surface_quality()
        
        print("\n")
        print("=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        print("\n测试结果汇总:")
        print("  ✓ 汽车参数库加载成功")
        print("  ✓ NURBS曲面创建和评估成功")
        print("  ✓ 曲面修改操作成功")
        print("  ✓ 草图编辑器功能正常")
        print("  ✓ 测量工具功能正常")
        print("  ✓ 参数驱动修改成功")
        print("  ✓ 曲面质量分析成功")
        print("\n")
        
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)