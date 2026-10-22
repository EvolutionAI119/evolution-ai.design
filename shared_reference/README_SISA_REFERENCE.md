# SISA 点云逆向参考数据包 · 对接说明

> 本文件由 SISA 生成，**仅供平台作为参考数据消费**。
> 依据《SISA 资产分类与保密声明》第三条，SISA 资产单向流动（平台 → SISA）；
> 此处交付的是**逆向测量的客观几何结果**，不是 SISA 的算法实现，
> 由声明人决定是否采用。

## 1. 来源
- 真实整车三维扫描：`Refine.stl`（2575029 点）
- 生成时间：2026-10-10T21:59:38+0800

## 2. 坐标系（务必先对齐）
| 轴 | 含义 | 原点 |
|---|---|---|
| X | 车长 | 车头端 = 0 |
| Y | 车宽 | 车身中线 = 0 |
| Z | 车高 | **地面 = 0** |

- 单位：mm
- 尺寸：L 4678.6 × W 1905.0 × H 1626.5 mm
- 与平台换算：`x_platform = x_reference - L/2`（平台在 x ∈ [-L/2, +L/2] 居中）

## 3. 关键地标（归一化 x，0=车头 1=车尾）
| 地标 | 值 |
|---|---|
| x_norm_front | 0.0 |
| x_norm_hood_end | 0.2714 |
| x_norm_windshield_peak_slope | 0.3266 |
| x_norm_roof_start | 0.3869 |
| x_norm_roof_end | 0.5025 |
| x_norm_rear_window_peak_slope | 0.6834 |
| x_norm_trunk_end | 0.7085 |
| x_norm_rear | 1.0 |
| hood_height_ratio | 0.6898 |
| roof_height_ratio | 1.0 |
| trunk_height_ratio | 0.9706 |
| max_upward_slope | 4.366 |
| max_downward_slope | -1.188 |
| flat_threshold | 0.92 |
| method | slope-threshold on the 88th-percentile top profile |

## 4. 提供的曲线
- `reference_curves.z_top_mm` —— 真实车**车顶线**（引擎盖 → 前风挡 → 车顶 → 后风挡 → 尾箱）
- `reference_curves.y_half_mm` —— 真实车**半宽廓线**
- `reference_curves.*_norm` —— 各自归一化版本，便于跨尺寸比较

**用法（把「像不像真车」变成可量化）**：
```python
import json, numpy as np
pk = json.load(open('SISA_REVERSE_REFERENCE_PACK.json', encoding='utf-8'))
x  = np.array(pk['reference_curves']['x_norm'])
zt = np.array(pk['reference_curves']['z_top_norm'])   # 目标车顶线
# 用你自己的生成器算出车顶线 z_mine(x)（同样归一化到 [0,1]）
# err = np.sqrt(np.mean((z_mine - zt)**2))    ← 对真车误差
```

## 5. 截面族
- `sections[]` 共 24 个截面，每截面 80 点 `[y, z]`（mm）
- 来自**外表面包络**（已剔除内饰点与底盘裁切平面）

## 6. 可用的改进点（附实测依据）
### ground_alignment
- **发现**：平台生成器最小 z ≈ 90mm（悬空），而真实车以地面为 0；本包 z 已归零到真地面。
- **建议**：车的 z 原点应为**地面**而非车身最低控制点；否则渲染与装配基准会整体抬高。
- **依据**：实测：平台 z 跨度 1330（90~1420）；真实车 1645（0~1645）

### height_ratio
- **发现**：真实车高/长 = 0.348；平台当前 = 0.277
- **建议**：车高比例可参考真实车基准，避免过扁或过高
- **依据**：本包 length/height 均来自真实扫描实测

### silhouette_target
- **发现**：本包提供 z_top(x) 与 y_half(x) 两条真实设计曲线，可直接做平台生成的**对真车误差**评估
- **建议**：用 reference_curves 做目标，计算 RMSE(= 平台的 z_top 与本包 z_top 之差的均方根)，把'像不像真车'从主观变成可量化
- **依据**：SISA 用同一曲线把逼近精度做到留出 CV 0.9956

### section_family
- **发现**：本包给出 24 个真实截面（每截面 80 点）
- **建议**：平台可用它校验自身断面形状；若要做封闭化，断面族可作为外蒙皮的约束
- **依据**：来自外表面包络，已剔除内饰与底盘裁切平面

## 7. 质量与边界（诚实标注）
- 拟合 RMSE 中位：10.235 mm
- 光滑度 p95（原始 → 平滑）：331.977669468749 → 167.05596849688138 mm
- 粗糙度 p95 残余主要来自真实几何（后视镜凸起 / 端部台阶），不是拟合噪声
- **未提供**：SISA 的算法实现、墨玉造型 DNA、任何内部模型权重。
