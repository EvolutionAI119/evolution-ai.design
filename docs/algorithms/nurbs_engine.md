# NURBS曲面引擎算法文档

## 1. 概述

EVOLUTION AI NURBS曲面引擎是一个自研的B样条曲线/曲面计算引擎，实现了完整的De Boor-Cox递推算法，支持汽车A级曲面的精确生成和质量评估。

## 2. 核心数据结构

### 2.1 ControlPoint（控制点）

三维坐标点，包含齐次坐标权重：

| 属性 | 类型 | 说明 |
|------|------|------|
| x | float | X坐标 |
| y | float | Y坐标 |
| z | float | Z坐标 |
| weight | float | 齐次坐标权重（默认1.0） |

### 2.2 KnotVector（节点矢量）

B样条曲线/曲面的节点序列：

- **均匀节点矢量**：内部节点均匀分布
- **非均匀节点矢量**：可自定义节点位置
- **重复节点**：用于控制曲线端点行为

## 3. B样条基函数算法

### 3.1 De Boor-Cox递推公式

```
N_{i,0}(u) = 1,  if knots[i] ≤ u < knots[i+1]
             0,  otherwise

N_{i,k}(u) = (u - knots[i]) / (knots[i+k] - knots[i]) * N_{i,k-1}(u)
           + (knots[i+k+1] - u) / (knots[i+k+1] - knots[i+1]) * N_{i+1,k-1}(u)
```

### 3.2 算法实现

```python
def _basis_function(i: int, k: int, u: float, knots: List[float]) -> float:
    if i + k + 1 >= len(knots):
        return 0.0
    if k == 0:
        if knots[i] <= u < knots[i + 1] or (u >= 1.0 and i == len(knots) - 2):
            return 1.0
        return 0.0
    result = 0.0
    denom1 = knots[i + k] - knots[i]
    if denom1 > 1e-10:
        result += (u - knots[i]) / denom1 * _basis_function(i, k - 1, u, knots)
    denom2 = knots[i + k + 1] - knots[i + 1]
    if denom2 > 1e-10:
        result += (knots[i + k + 1] - u) / denom2 * _basis_function(i + 1, k - 1, u, knots)
    return result
```

### 3.3 算法复杂度

| 操作 | 时间复杂度 | 空间复杂度 |
|------|-----------|-----------|
| 基函数求值 | O(k^2) | O(k) |
| 曲线点求值 | O(n*k^2) | O(n) |
| 曲面点求值 | O(n*m*k^2*l^2) | O(n*m) |

其中n、m为控制点数量，k、l为U/V方向阶数。

## 4. NURBS曲线

### 4.1 曲线方程

```
C(u) = Σ_{i=0}^{n} N_{i,p}(u) * w_i * P_i / Σ_{i=0}^{n} N_{i,p}(u) * w_i
```

其中：
- N_{i,p}(u)：p阶B样条基函数
- w_i：控制点权重
- P_i：控制点坐标

### 4.2 关键方法

| 方法 | 功能 | 参数 |
|------|------|------|
| evaluate_point(t) | 计算曲线点 | t: 参数值(0-1) |
| compute_length() | 近似曲线长度 | num_samples: 采样数 |

## 5. NURBS曲面

### 5.1 曲面方程

```
S(u, v) = Σ_{i=0}^{n} Σ_{j=0}^{m} N_{i,p}(u) * N_{j,q}(v) * w_{ij} * P_{ij}
          / Σ_{i=0}^{n} Σ_{j=0}^{m} N_{i,p}(u) * N_{j,q}(v) * w_{ij}
```

### 5.2 法向量计算

采用中心差分法：

```python
def evaluate_normal(self, u: float, v: float) -> np.ndarray:
    eps = 0.001
    du = self.evaluate_point(u + eps, v) - self.evaluate_point(u - eps, v)
    dv = self.evaluate_point(u, v + eps) - self.evaluate_point(u, v - eps)
    normal = np.cross(du, dv)
    norm = np.linalg.norm(normal)
    if norm > 1e-10:
        normal /= norm
    return normal
```

### 5.3 曲率计算

```python
def evaluate_curvature(self, u: float, v: float) -> Dict[str, float]:
    eps = 0.001
    p = self.evaluate_point(u, v)
    puu = (self.evaluate_point(u + eps, v) - 2 * p + self.evaluate_point(u - eps, v)) / (eps ** 2)
    pvv = (self.evaluate_point(u, v + eps) - 2 * p + self.evaluate_point(u, v - eps)) / (eps ** 2)
    normal = self.evaluate_normal(u, v)
    k1 = float(np.dot(puu, normal))
    k2 = float(np.dot(pvv, normal))
    return {
        'gaussian_curvature': k1 * k2,
        'mean_curvature': (k1 + k2) / 2,
        'principal_curvature_1': k1,
        'principal_curvature_2': k2
    }
```

### 5.4 曲面变换

支持平移、缩放、旋转变换：

| 方法 | 功能 |
|------|------|
| translate(dx, dy, dz) | 平移变换 |
| scale(sx, sy, sz, center) | 缩放变换 |
| rotate(angle, axis, center) | 旋转变换 |

## 6. 精度控制

| 参数 | 值 | 说明 |
|------|-----|------|
| 分母阈值 | 1e-10 | 防止除零错误 |
| 法向量归一化 | 1e-10 | 防止零向量 |
| 采样密度 | 可配置 | 影响计算精度和性能 |

## 7. 数据序列化

支持JSON格式的曲面数据序列化：

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        'degree_u': self.degree_u,
        'degree_v': self.degree_v,
        'control_points': [[{'x': cp.x, 'y': cp.y, 'z': cp.z, 'weight': cp.weight}
                            for cp in row] for row in self.control_points],
        'knot_vector_u': self.knot_vector_u.values,
        'knot_vector_v': self.knot_vector_v.values
    }
```

## 8. 技术特点

1. **纯Python实现**：无外部依赖，易于集成和部署
2. **精确算法**：标准De Boor-Cox递推，保证计算精度
3. **高效计算**：递归实现，支持任意阶数的B样条
4. **完整功能**：曲线、曲面、变换、曲率评估
5. **数据持久化**：支持JSON序列化和反序列化