# 品牌 DNA 模块技术适配文档

> 版本：1.0 · 日期：2026-10-11
> 模块：`backend/app/brand_dna/`

---

## 1. 概述

本模块吸收 SISA 已完成的 **2D 形状识别与标注技术成果** 及 **品牌造型 DNA 语言**，在平台侧建立独立的品牌造型 DNA 定制化模块。

**核心设计原则**：通过 JSON 数据契约实现与 SISA 的隔离，不 import SISA 代码，不包含墨玉等机密品牌数据。

---

## 2. SISA 技术成果迁移清单

### 2.1 2D 形状标注规范迁移

| SISA 成果 | 平台适配模块 | 迁移方式 |
|-----------|-------------|---------|
| `sisa/features.py` 12 维无量纲特征 | `features_2d.py` | 方法论独立实现，输出格式兼容 |
| `sisa/car_form.py` 车体缝合逻辑 | 不迁移（属 SISA 核心算法层） | 仅保留特征提取接口 |
| `internal/topology/extract_topology.py` 拓扑提取 | 不迁移 | 提供数据契约，支持成果包导入 |

**12 维无量纲特征清单**（与 SISA 完全一致）：

| # | 特征名 | 含义 | 归一化方式 |
|---|--------|------|-----------|
| 1 | deg_u | u 方向次数 | 原值 |
| 2 | deg_v | v 方向次数 | 原值 |
| 3 | cp_ratio | 控制点网格长宽比 | n_u / n_v |
| 4 | cp_total | 控制点数 | log10 / 4 归一化到 [0,1] |
| 5 | span_ratio | 参数域跨度比 | span_u / span_v |
| 6 | extent_aspect | 包围盒长短轴比 | ext[1] / ext[0] |
| 7 | extent_mid | 包围盒中轴占比 | ext[2] / ext[0] |
| 8 | planarity | 平面度 | SVD 最小/最大奇异值 |
| 9 | cp_roughness | 控制点粗糙度 | 二阶差分范数 / 点数 |
| 10 | knot_uniformity_u | u 节点均匀度 | 1 / (1 + CV) |
| 11 | knot_uniformity_v | v 节点均匀度 | 1 / (1 + CV) |
| 12 | weight_dev | 权重偏离度 | mean(|w - 1|) |

### 2.2 品牌造型 DNA 语言迁移

| SISA 成果 | 平台适配模块 | 迁移方式 |
|-----------|-------------|---------|
| `internal/brand_dna/moyu_brand_dna.json` 结构 | `schema.py` | 抽象结构定义，不含墨玉数据 |
| `sisa/dna_derive.py` DNA→参数派生 | 不迁移 | 平台使用自有 `car_generator.py` 参数体系 |
| `sisa/on_brand.py` 合规判定 | `on_brand.py` | 方法论独立实现，判定分级一致 |

**DNA 数据结构顶层字段**：

```
_CONFIDENTIAL      密级声明
brand              品牌基本信息
philosophy         设计哲学框架
jade_traits        材质特质映射
forbidden/allowed  造型约束清单
on_brand_constraints  可量化合规约束
cmf                色彩材质工艺
models             车型参数矩阵
engine_spec        引擎运行时规格
```

### 2.3 预处理流程迁移

SISA 的特征提取预处理流程（控制点归一化、节点向量处理、包围盒计算）已在 `features_2d.py` 中完整复现：

1. **控制点校验**：shape 必须为 (n_u, n_v, 3)，n_u/n_v ≥ 2
2. **节点归一化**：线性映射到 [0,1]，计算跨度与均匀度
3. **包围盒计算**：min/max 排序得到三轴长度
4. **SVD 平面度**：中心化后奇异值分解
5. **粗糙度计算**：二阶差分范数归一化

---

## 3. 接口规范

### 3.1 特征提取接口

```python
from backend.app.brand_dna import extract_features, SurfaceFeatures

feat = extract_features(
    control_points,          # numpy (n_u, n_v, 3)
    degree_u=3, degree_v=3,
    knots_u=[...], knots_v=[...],
    weights=[...],           # 可选
    family="hood", source="import",
)
# feat.vec  → [12 维特征]
# feat.as_dict() → {"family", "source", "vec"}  （与 SISA 兼容）
```

### 3.2 品牌合规判定接口

```python
from backend.app.brand_dna import evaluate_on_brand

result = evaluate_on_brand(dna_dict, measured_dict)
# result.pass_count / fail_count / no_data_count / score
# result.clauses → List[Clause]  （每条约束的判定结果）
```

### 3.3 DNA 加载接口

```python
from backend.app.brand_dna import load_dna, import_dna_file, list_available_dnas

# 导入（机密数据仅内存，不持久化）
ok, msg, dna = import_dna_file("path/to/brand_dna.json", persist=True)

# 加载已存储的 DNA
dna = load_dna("brand_key")

# 列出可用 DNA
dnas = list_available_dnas()
```

---

## 4. 数据契约（SISA ↔ 平台）

### 4.1 成果包格式

SISA 输出的脱敏成果包为 JSON 文件，遵循 `schema.SCHEMA_VERSION = "1.0"`：

```json
{
  "schema_version": "1.0",
  "_CONFIDENTIAL": {
    "level": "public|internal|confidential",
    "policy": "...",
    "storage": "..."
  },
  "brand": { "key": "...", "name": "...", "zh_name": "..." },
  "on_brand_constraints": { ... },
  "models": [ ... ],
  "engine_spec": { "zero_rules": [], "range_rules": [], "series_spec": {} }
}
```

### 4.2 密级处理规则

| 密级 | 平台行为 |
|------|---------|
| public | 可持久化到 `brand_dna/dnas/` |
| internal | 可持久化，但不外发 |
| confidential | **仅内存使用，不持久化** |

---

## 5. 验证结果

| 验证项 | 结果 |
|--------|------|
| 隔离测试（不 import SISA） | ✅ 20/20 通过 |
| SISA 端无侵入 | ✅ SISA 隔离测试 6/6 通过 |
| 特征提取兼容性 | ✅ 输出格式与 SISA `SurfaceFeatures.as_dict()` 一致 |
| 合规判定分级 | ✅ PASS/FAIL/NO_DATA/N/A 四级正确 |
| 机密数据隔离 | ✅ confidential 级别不持久化 |
