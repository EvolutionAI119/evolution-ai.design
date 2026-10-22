# 品牌 DNA 模块隔离边界说明

> 版本：1.0 · 日期：2026-10-11

---

## 1. 隔离目标

确保品牌造型 DNA 模块与 SISA 核心算法层**完全解耦**，支持独立维护、迭代，且不影响 SISA 原有技术链路的正常运行。

---

## 2. 物理隔离边界

### 2.1 代码边界

| 维度 | 平台 `brand_dna` 模块 | SISA |
|------|----------------------|------|
| 代码位置 | `backend/app/brand_dna/` | `D:\API\SISA\` |
| import 依赖 | 标准库 + numpy | SISA 内部模块 + 平台快照 |
| 反向依赖 | 平台其他模块可 import brand_dna | SISA 不 import 平台 brand_dna |
| 数据流向 | 平台 ← JSON 成果包 ← SISA | SISA → JSON 成果包 → 平台 |

### 2.2 强制约束

1. **`brand_dna/` 内任何文件不得出现 `import sisa` 或 `from sisa`**
2. **`brand_dna/` 内任何文件不得引用 `SISA/internal/` 路径**
3. **机密品牌 DNA 数据（如墨玉）不得写入 `brand_dna/dnas/` 目录**
4. **SISA 端不修改任何平台文件**（除 `shared-assets/upstream/` 快照）

---

## 3. 数据隔离边界

### 3.1 密级分级与处理

```
┌─────────────────────────────────────────────────┐
│              数据密级处理矩阵                      │
├──────────────┬──────────────┬───────────────────┤
│ 密级          │ 平台持久化    │ 内存使用           │
├──────────────┼──────────────┼───────────────────┤
│ public       │ ✅ 允许       │ ✅ 允许            │
│ internal     │ ✅ 允许       │ ✅ 允许            │
│ confidential │ ❌ 禁止       │ ✅ 允许（运行时）   │
└──────────────┴──────────────┴───────────────────┘
```

### 3.2 数据交换通道

**唯一通道**：JSON 文件契约

```
SISA 成果输出 → 脱敏 JSON 文件 → 平台 import_dna_file() → 内存/持久化
```

- SISA 侧负责输出符合 `schema_version=1.0` 的 JSON
- 平台侧负责校验结构与密级，决定是否持久化
- 不允许直接读取 SISA 目录文件

---

## 4. 功能隔离边界

### 4.1 模块职责划分

| 功能 | 平台 `brand_dna` | SISA |
|------|-----------------|------|
| DNA 结构定义 | ✅ `schema.py` | — |
| 2D 特征提取 | ✅ `features_2d.py`（方法论复用） | ✅ `features.py`（原始实现） |
| 合规判定引擎 | ✅ `on_brand.py`（方法论复用） | ✅ `on_brand.py`（原始实现） |
| DNA 派生（几何推导） | ❌ 不实现 | ✅ `dna_derive.py` |
| 车体缝合/轮系生成 | ❌ 不实现 | ✅ `car_form.py` |
| 拓扑提取 | ❌ 不实现 | ✅ `extract_topology.py` |
| 墨玉机密 DNA | ❌ 不存储 | ✅ `internal/brand_dna/` |

### 4.2 接口稳定性保证

- 平台 `SurfaceFeatures.as_dict()` 输出格式与 SISA **完全一致**
- 平台 `Clause.as_dict()` 输出格式与 SISA **完全一致**
- 特征维度 `FEATURE_DIM=12` 与 SISA **固定对齐**
- 特征名称顺序 `FEATURE_NAMES` 与 SISA **固定对齐**

---

## 5. 隔离验证机制

### 5.1 自动化测试

`backend/tests/test_brand_dna.py` 包含：

- `TestIsolationBoundary`：扫描 import 语句，禁止 sisa/internal 依赖
- `TestLoader`：验证 confidential 数据不持久化
- `TestEndToEndCompatibility`：验证数据契约兼容性

### 5.2 运行时防护

```python
# loader.py 中的密级检查
level, can_persist = _check_confidentiality(dna)
if level == "confidential":
    persist = False  # 强制不持久化
```

---

## 6. 变更影响评估

| 变更类型 | 影响范围 | 回滚方式 |
|---------|---------|---------|
| 修改 brand_dna 内部实现 | 仅影响品牌 DNA 功能 | git revert |
| 修改 schema 版本 | 需同步更新 SISA 成果包格式 | 版本协商 |
| SISA 修改 DNA 结构 | 平台需同步 schema（向后兼容） | 版本降级 |
| 平台新增品牌 DNA | 不影响 SISA | 删除文件 |

**结论**：brand_dna 模块的变更不会影响 SISA 核心算法链路；SISA 的变更仅在数据契约层需要对齐。
