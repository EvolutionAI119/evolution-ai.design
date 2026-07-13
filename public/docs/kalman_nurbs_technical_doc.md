# 卡尔曼滤波 + NURBS 曲面优化技术文档

> 版本: v3.0 | 更新日期: 2026-06-23 | 模块: `kalman_nurbs.py`

---

## 1. 概述

本文档详细描述了 EVOLUTION AI 汽车造型系统中 **卡尔曼滤波参数平滑** 与 **NURBS 曲面重构** 的完整算法流程、关键实现细节及调优指南，供后续团队复用和迭代。

### 1.1 设计目标

| 目标 | 说明 |
|------|------|
| 轮廓真实性 | 基于 A2MAC1 风格真实车身断面数据库，生成接近真实汽车造型的曲面 |
| 参数平滑性 | 使用卡尔曼滤波消除硬点参数序列中的噪声和不连续跳变 |
| 曲面质量 | NURBS B样条曲面保证 C2 连续性，曲率分布均匀 |
| 工程可用性 | 支持 IGES / STEP / STL 多格式导出，对接主流 CAD 系统 |

### 1.2 系统架构

```
硬点参数 (18个主参数)
    │
    ├──▶ derive_hardpoints() ──▶ 16个二级硬点
    │
    ├──▶ side_upper_profile() ──▶ 侧视轮廓关键点
    ├──▶ top_width_profile()   ──▶ 顶视宽度关键点
    │
    ├──▶ KalmanFilter1D / MultiVarKalmanFilter ──▶ 参数平滑
    │
    ├──▶ build_car_nurbs_control_mesh() ──▶ 控制网格 (20×32)
    │       │
    │       ├── A2MAC1 断面插值
    │       ├── 三区权重混合 (引擎盖/乘员舱/行李箱)
    │       ├── Tumblehome 截面计算
    │       └── 轮拱权重增强
    │
    └──▶ NURBSSurface ──▶ evaluate_grid() ──▶ to_mesh()
            │
            ├── export_iges()  ──▶ IGES Type 128
            ├── export_step()  ──▶ STEP AP214
            └── export_stl()   ──▶ STL Binary
```

---

## 2. A2MAC1 风格车身断面数据库

### 2.1 数据结构

```python
@dataclass
class CarCrossSection:
    name: str                              # 车型名称
    stations: List[float]                  # 断面位置 (轴距百分比)
    profiles: List[List[Tuple[float, float]]]  # 各断面 (y, z) 坐标
```

### 2.2 BMW 3 Series F30 参考数据

| 断面编号 | 位置 (轴距比) | 区域 | 特征 |
|----------|--------------|------|------|
| 0 | -0.30 | 前保险杠 | 窄截面，快速收窄 |
| 1 | -0.15 | 大灯区 | 渐宽，特征线开始 |
| 2 | 0.00 | 前轴 | 轮拱最宽点 |
| 3 | 0.30 | A柱基 | 肩部展开 |
| 4 | 0.60 | 中舱 | 最大截面，车顶最高 |
| 5 | 0.90 | C柱基 | 开始收窄 |
| 6 | 1.20 | 后保险杠 | 窄截面收尾 |

### 2.3 断面插值算法

使用 **smoothstep** 函数实现相邻断面间的平滑过渡：

```python
def interpolate_cross_section(target_station, cs_db):
    # 二分查找目标位置所在区间
    for i in range(len(stations) - 1):
        if stations[i] <= target_station <= stations[i + 1]:
            t = (target_station - stations[i]) / (stations[i+1] - stations[i])
            t = t * t * (3 - 2 * t)  # smoothstep
            # 线性插值各 (y, z) 点
            for j in range(n_pts):
                y = p1[j][0] + (p2[j][0] - p1[j][0]) * t
                z = p1[j][1] + (p2[j][1] - p1[j][1]) * t
```

**smoothstep 公式**: `t' = 3t² - 2t³`，保证 C1 连续（一阶导数为0在端点处）。

---

## 3. 卡尔曼滤波器

### 3.1 一维卡尔曼滤波器 (KalmanFilter1D)

**状态向量**: `x = [位置, 速度]` (2×1)

**状态转移矩阵**:
```
F = [[1, dt],
     [0,  1]]
```

**观测矩阵**: `H = [[1, 0]]`

**过程噪声矩阵**:
```
Q = [[Q·dt², Q·dt],
     [Q·dt,    Q ]]
```

**更新方程**:
```
预测:  x̂ₖ⁻ = F·x̂ₖ₋₁
      Pₖ⁻ = F·Pₖ₋₁·Fᵀ + Q

更新:  y = z - H·x̂ₖ⁻
      S = H·Pₖ⁻·Hᵀ + R
      K = Pₖ⁻·Hᵀ / S
      x̂ₖ = x̂ₖ⁻ + K·y
      Pₖ = (I - K·H)·Pₖ⁻
```

**调参指南**:

| 参数 | 默认值 | 作用 | 调优建议 |
|------|--------|------|----------|
| Q (过程噪声) | 0.001 | 信任模型预测程度 | Q↑ → 更跟随测量值，平滑减弱 |
| R (测量噪声) | 0.01 | 信任测量值程度 | R↑ → 更平滑，响应变慢 |
| dt | 1.0 | 采样间隔 | 与参数采样密度匹配 |

**典型应用场景**:
- 侧视轮廓 topY 序列平滑: `Q=0.0003, R=0.002`
- 硬点参数去噪: `Q=0.001, R=0.01`

### 3.2 多变量卡尔曼滤波器 (MultiVarKalmanFilter)

**状态向量**: `x = [p₁, v₁, p₂, v₂, ..., pₙ, vₙ]` (2n×1)

同时平滑多个相关参数（如 L, W, H, WB），保持参数间的一致性。

**关键特性**:
- 每个参数独立的位置-速度对
- Joseph 形式协方差更新: `P = (I-KH)·P·(I-KH)ᵀ + K·R·Kᵀ`，数值更稳定
- 批量处理: `filter_matrix(data, dt)` 输入 (n_steps, n_vars) 矩阵

### 3.3 便捷函数

```python
def kalman_smooth_profile(profile, Q=0.001, R=0.01):
    """对一维序列应用卡尔曼滤波平滑"""
    kf = KalmanFilter1D(Q=Q, R=R)
    smoothed = []
    for val in profile:
        kf.predict()
        kf.update(val)
        smoothed.append(kf.x[0])
    return smoothed
```

---

## 4. NURBS 曲面系统

### 4.1 B样条基函数 (de Boor 算法)

采用 Cox-de Boor 递推公式计算基函数值：

```python
def bspline_basis_deboor(u, p, knots, n_ctrl):
    # 1. 二分查找 knot span
    # 2. 初始化 N[span] = 1.0
    # 3. 逐阶递推 (degree 1 → p)
    #    left[d] = u - knots[span+1-d]
    #    right[d] = knots[span+d] - u
    #    temp = N[span-r] / (right[r+1] + left[d-r])
    #    N[span-r] = saved + right[r+1] * temp
    #    saved = left[d-r] * temp
```

**边界处理**:
- `u ≤ knots[0]`: `N[0] = 1.0`
- `u ≥ knots[-1]`: `N[-1] = 1.0`
- 分母接近零时 (`|denom| < 1e-15`): 置零避免数值溢出

### 4.2 节点向量生成

```python
def generate_knot_vector(n_control, p, method='average'):
    m = n_control + p + 1
    knots[0:p+1] = 0.0          # 起始 p+1 重节点
    knots[m-p-1:m] = 1.0       # 终止 p+1 重节点
    # 内部节点均匀分布
    for j in range(1, n_interior + 1):
        knots[p + j] = j / (n_interior + 1)
```

**特性**: Clamped 节点向量，保证曲面通过首末控制点行。

### 4.3 NURBS 曲面求值

**数学定义**:
```
S(u,v) = Σᵢ Σⱼ wᵢⱼ·Nᵢ(u)·Nⱼ(v)·Pᵢⱼ / Σᵢ Σⱼ wᵢⱼ·Nᵢ(u)·Nⱼ(v)
```

**优化实现** (`evaluate_grid`):
1. 预计算所有 u/v 采样点的基函数值矩阵 `N_u_all`, `N_v_all`
2. 三重循环求加权和，避免重复基函数计算
3. 权重归一化: `pt /= w_sum`

### 4.4 曲面到网格转换

```python
def to_mesh(n_u_samples, n_v_samples):
    # 1. evaluate_grid() 生成 X, Y, Z 矩阵
    # 2. ravel() 展平为顶点数组
    # 3. 四边形 → 2个三角形
    #    a---b
    #    | / |
    #    c---d
    #    triangles: [a,c,b] + [b,c,d]
```

---

## 5. 车身 NURBS 控制网格构建

### 5.1 硬点参数体系

**18个主参数** → **16个二级硬点** → 控制网格

| 主参数 | 符号 | 典型值(m) | 说明 |
|--------|------|-----------|------|
| 车长 | L | 4.84 | FO+WB+RO |
| 车宽 | W | 1.83 | 含后视镜 |
| 车高 | H | 1.45 | 含车顶天线 |
| 轴距 | WB | 2.96 | 前后轴距离 |
| 前悬 | FO | 0.96 | 前轴到车头 |
| 后悬 | RO | 0.92 | 后轴到车尾 |
| 离地间隙 | GC | 0.14 | 最小离地 |
| 轮径 | WR | 0.33 | 含轮胎 |
| 轮距 | TW | 1.56 | 左右轮中心距 |
| A柱角 | AA | 28° | 前风挡倾角 |
| Raked角 | RA | 55° | 车顶后掠角 |
| C柱角 | CA | 50° | 后风挡倾角 |
| 腰线高 | WL | 0.78 | 腰线离地高度 |
| 肩宽比 | shoulderW | 0.90 | 肩部/车宽比 |
| 轮拱隆起 | archBulge | 0.03 | 轮拱外凸量 |

### 5.2 二级硬点推导 (比例计算)

**核心原则**: 所有二级参数从主参数按比例推导，**不使用硬编码绝对偏移量**。

```python
def derive_hardpoints(p):
    h.noseTipY  = p.GC + p.H * 0.25     # 车头高度
    h.hoodY     = p.GC + p.H * 0.42     # 引擎盖高度
    h.baseWindY = p.GC + p.H * 0.55     # 风挡基点
    h.topWindY  = p.GC + p.H * 0.82     # 风挡顶点
    h.roofY     = p.GC + p.H * 0.97     # 车顶最高点
    h.rearWinY  = p.GC + p.H * 0.78     # 后风挡起点
    h.deckY     = p.GC + p.H * 0.58     # 行李箱高度
    h.tailY     = p.GC + p.H * 0.35     # 车尾高度
    h.waistY    = p.GC + p.H * 0.60     # 腰线高度
    h.fwx       = p.FO                   # 前轮X坐标
    h.rwx       = p.FO + p.WB           # 后轮X坐标
```

### 5.3 三区权重系统

车身沿X轴分为三个区域，各区域截面特征不同：

```
引擎盖区 (Hood)     乘员舱区 (Cabin)     行李箱区 (Trunk)
|←── ho ──→|←──────── co ────────→|←── to ──→|
```

**权重计算**:
```python
def compute_zone_weights(x, h, WB):
    hood_end = h.fwx + WB * 0.08
    cabin_start = h.fwx + WB * 0.08
    cabin_end = h.rwx - WB * 0.15
    trunk_start = h.rwx - WB * 0.15
    
    # smoothstep 过渡，过渡宽度与轴距成比例
    trans = WB * 0.05
    ho = smoothstep((hood_end + trans - x) / (2 * trans))
    to = smoothstep((x - trunk_start + trans) / (2 * trans))
    co = 1.0 - ho - to
```

### 5.4 Tumblehome 截面计算

Tumblehome 指车身从肩部到车顶的内收效应：

```python
def compute_cross_section_params(hw, shoulderW, tumble_rad, ho, co, to):
    # 肩部半宽: shoulderW 比例控制
    shldHW_h = hw * 0.78 * ho + hw * 0.97 * co + hw * 0.85 * to
    shldHW_c = hw * shoulderW
    shldHW = shldHW_h * ho + shldHW_c * co + shldHW_h * to
    
    # 车顶半宽: tumblehome 角度控制
    roofHW_h = hw * 0.55 * ho + hw * 0.80 * co + hw * 0.60 * to
    roofHW_c = shldHW_c - (shldHW_c - roofHW_c) * sin(tumble_rad)
    roofHW = roofHW_h * ho + roofHW_c * co + roofHW_h * to
```

### 5.5 控制网格截面生成

沿 v 方向（截面方向）使用 **分段 smoothstep 插值**：

```
v ∈ [0, 0.20):  底部 → 门槛     (5个关键高度级别)
v ∈ [0.20, 0.45): 门槛 → 腰线
v ∈ [0.45, 0.75): 腰线 → 肩部
v ∈ [0.75, 1.00]: 肩部 → 车顶中心
```

每个区间内使用 smoothstep 插值 Y 坐标和半宽：

```python
if t_v < 0.20:
    tt = t_v / 0.20
    y = y_levels[0] + (y_levels[1] - y_levels[0]) * smoothstep(tt)
    hw_interp = hw_levels[0] + (hw_levels[1] - hw_levels[0]) * smoothstep(tt)
```

**右半截面 → 镜像左半截面**:
```python
# 镜像: Z 坐标取反
control_points[i, dst] = control_points[i, src].copy()
control_points[i, dst, 2] = -control_points[i, src, 2]
```

### 5.6 轮拱权重增强

在轮拱区域增大 NURBS 权重，使曲面更贴合轮拱形状：

```python
for wx in [h.fwx, h.rwx]:
    dist = abs(x - wx)
    if dist < p.WR * 2:
        arch_factor = 1.0 + 0.5 * (1 - dist / (p.WR * 2))
        # 仅影响侧面控制点
        if abs(control_points[i, j, 2]) > p.TW / 2 - p.WR * 0.3:
            weights[i, j] = arch_factor
```

---

## 6. 曲面质量分析

### 6.1 曲率计算方法

使用有限差分法计算 NURBS 曲面的第一、第二基本形式：

**第一基本形式**:
```
E = du·du,  F = du·dv,  G = dv·dv
```

**第二基本形式**:
```
L = duu·n,  M = duv·n,  N = dvv·n
```

**主曲率**:
```
k₁ = (L·G - M·F) / (E·G - F²)
k₂ = (N·E - M·F) / (E·G - F²)
```

**平均曲率**: `H = (k₁ + k₂) / 2`
**高斯曲率**: `K = k₁ · k₂`

### 6.2 质量指标

```python
def analyze_nurbs_quality(surface, n_samples=15):
    return {
        'curvature_min': float(np.min(curvatures)),
        'curvature_max': float(np.max(curvatures)),
        'curvature_mean': float(np.mean(curvatures)),
        'curvature_std': float(np.std(curvatures))
    }
```

**参考基准** (BMW 3系级别):
- 平均曲率: 0.01 ~ 0.05 (1/m)
- 曲率标准差: < 0.03 (1/m)
- 最大曲率: < 0.5 (1/m)（轮拱等特征区域除外）

---

## 7. 文件导出

### 7.1 IGES (Type 128 - Rational B-Spline Surface)

```
全局段 (G): 文件元信息
目录段 (D): Type 128 实体定义
参数段 (P): K1, K2, M1, M2 + 节点向量 + 权重 + 控制点 + UV范围
终止段 (T): 行计数
```

### 7.2 STEP (AP214 Automotive Design)

```
HEADER: FILE_DESCRIPTION, FILE_NAME, FILE_SCHEMA
DATA:
  - 长度单位定义 (SI_UNIT, MILLI, METRE)
  - 坐标系定义 (CARTESIAN_POINT, DIRECTION, AXIS2_PLACEMENT_3D)
  - 控制点 (CARTESIAN_POINT)
  - B_SPLINE_SURFACE_WITH_KNOTS (度数, 控制点引用, 节点重数, 节点值)
ENDSEC
END-ISO-10303-21
```

### 7.3 STL (Binary)

通过 `export_stl_binary()` 函数导出，用于3D打印验证。

---

## 8. 验证流程

### 8.1 运行验证脚本

```bash
cd docs
python verify_kalman_nurbs.py
```

### 8.2 验证输出

| 步骤 | 内容 | 指标 |
|------|------|------|
| 1 | 卡尔曼滤波平滑 | MSE 降低百分比 |
| 2 | 模型生成 | 顶点数/三角面数/耗时 |
| 3 | 包围盒对比 | X/Y/Z 范围 |
| 4 | 曲面质量 | 曲率均值/标准差/最大值 |
| 5 | 文件导出 | STL/IGES/STEP 文件大小 |
| 6 | 可视化 | 对比验证图 PNG |

### 8.3 典型验证结果

```
Original: 5265 vertices, 10240 triangles (22.8ms)
NURBS:    5120 vertices, 9954 triangles (4119.2ms)

Original curvature: mean=0.0176, std=0.0185, max=0.1812
NURBS curvature:    mean=0.1560, std=0.1213, max=0.6432

Exports:
  car_body_nurbs.stl: 486.1 KB
  car_body_nurbs.igs: 51.3 KB
  car_body_nurbs.stp: 43.3 KB
```

---

## 9. 调优指南

### 9.1 轮廓杂乱排查

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 侧视轮廓锯齿 | 截面插值区间划分粗糙 | 增加 v 方向分段数或控制点数 |
| 车顶过低 | shoulderY→topY 过渡计算错误 | 检查 `shoulderY_c` 权重比例 |
| 车尾过度收缩 | tailTaper 与 noseTaper 耦合 | 分离前后锥度独立计算 |
| 轮拱处凹陷 | 权重增强不足 | 增大 `arch_factor` 系数 |

### 9.2 参数敏感性

| 参数 | 敏感度 | 影响范围 |
|------|--------|----------|
| shoulderW | 高 | 全车肩部宽度、车顶宽度 |
| CA (C柱角) | 高 | 后风挡斜度、行李箱高度 |
| archBulge | 中 | 轮拱区域外凸量 |
| RA (Raked角) | 中 | 车顶后掠程度 |
| Q/R (卡尔曼) | 低 | 参数平滑程度 |

### 9.3 性能优化

- `evaluate_grid()` 是性能瓶颈，考虑向量化 N_u_all · N_v_all 外积
- 控制点数 20×32 为推荐值，增大到 30×48 可提升细节但耗时 3~5 倍
- 曲面求值采样 80×64 为推荐值，3D打印可降至 40×32

---

## 10. 扩展参考

### 10.1 CAD 平台开源资源

| 平台 | 开源项目 | 用途 |
|------|----------|------|
| DASSAULT | Open CASCADE (OCCT) | B-Rep 建模、IGES/STEP 读写 |
| AUTODESK | FBX SDK / ADSK Forge | 网格处理、格式转换 |
| Rhinoceros | openNURBS | NURBS 几何定义、3DM 格式 |
| Open CASCADE | OCCT | NURBS 求值、布尔运算 |

### 10.2 关键算法参考

- de Boor, C. (1972). *On calculating with B-splines*. J. Approx. Theory
- Piegl, L. & Tiller, W. (1997). *The NURBS Book*. Springer
- Kalman, R.E. (1960). *A New Approach to Linear Filtering and Prediction Problems*

---

## 附录 A: 接口速查

```python
# 卡尔曼滤波
from kalman_nurbs import KalmanFilter1D, MultiVarKalmanFilter, kalman_smooth_profile

kf = KalmanFilter1D(Q=0.001, R=0.01)
smoothed = kf.filter_sequence(measurements)

smoothed = kalman_smooth_profile(profile, Q=0.0003, R=0.002)

mvkf = MultiVarKalmanFilter(n_vars=4, Q_scale=0.001, R_scale=0.01)
result = mvkf.filter_matrix(data_matrix)

# NURBS 曲面
from kalman_nurbs import NURBSSurface, NURBSCurve, bspline_basis_deboor

surface = NURBSSurface(control_points, degree_u=3, degree_v=3, weights=weights)
pt = surface.evaluate(0.5, 0.5)
vertices, indices = surface.to_mesh(80, 64)

surface.export_iges("output.igs")
surface.export_step("output.stp")

# 车身生成
from kalman_nurbs import generate_nurbs_car_body, analyze_nurbs_quality

verts, idx, surface = generate_nurbs_car_body(p, h)
quality = analyze_nurbs_quality(surface, n_samples=15)
```
