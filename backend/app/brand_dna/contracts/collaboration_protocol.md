# 成果共享协作规范

> 版本：1.0 · 日期：2026-10-11
> 适用：平台 ↔ SISA 算法成果双向共享

---

## 1. 协作目标

建立平台与 SISA 之间**定期的算法成果同步机制**，双方共享最新的模型优化、精度提升、性能调优成果，同时遵守隔离边界。

---

## 2. 同步方向与内容

### 2.1 平台 → SISA（开源资产同步）

**已有机制**：`D:\API\SISA\tools\sync_open_source.ps1`

| 内容 | 频率 | 方式 |
|------|------|------|
| 平台开源代码快照 | 按需 | `git archive HEAD` → SISA `shared-assets/upstream/` |
| 平台测试结果 | 按需 | 文档同步 |
| 平台 DNA schema 变更 | 按需 | 版本号通知 |

### 2.2 SISA → 平台（算法成果共享）

**新增机制**：脱敏成果包导出

| 内容 | 频率 | 方式 | 密级 |
|------|------|------|------|
| 2D 形状标注规范 | 版本更新时 | JSON Schema | public |
| 特征提取方法论 | 版本更新时 | 文档 + 接口规范 | public |
| 品牌 DNA 数据结构 | 版本更新时 | JSON Schema | public |
| 非机密品牌 DNA 数据 | 按需 | JSON 成果包 | public/internal |
| 模型精度提升报告 | 定期 | 文档 | internal |
| 机密品牌 DNA（墨玉） | 不共享 | 留在 SISA | confidential |

---

## 3. 成果包交换协议

### 3.1 成果包结构

```
sisa_deliverable_<date>.json
├── schema_version: "1.0"
├── _CONFIDENTIAL: { level, policy, storage }
├── deliverable_type: "features_spec" | "dna_schema" | "brand_dna" | "perf_report"
├── version: "x.y.z"
├── generated_at: "ISO-8601"
├── source: "SISA"
├── payload: { ... }
└── checksum: "sha256:..."
```

### 3.2 成果类型定义

| 类型 | payload 内容 | 平台处理 |
|------|-------------|---------|
| `features_spec` | 特征维度、名称、归一化方法 | 比对 `FEATURE_NAMES`，不一致时告警 |
| `dna_schema` | DNA 结构字段定义 | 比对 `BrandDNASchema`，必要时升级 |
| `brand_dna` | 完整品牌 DNA 数据 | `import_dna_file()` 导入 |
| `perf_report` | 精度/性能指标 | 文档存档，不入库 |

---

## 4. 同步流程

### 4.1 SISA → 平台 成果输出流程

```
1. SISA 侧生成成果（特征优化 / DNA 更新 / 精度报告）
2. SISA 侧执行脱敏：
   - 移除墨玉等机密品牌的具体参数
   - 仅保留结构定义与方法论
   - 设置 _CONFIDENTIAL.level
3. SISA 侧导出 JSON 成果包到交换目录
4. 平台侧 import_dna_file() 导入
5. 平台侧运行 test_brand_dna.py 验证兼容性
6. 记录同步日志
```

### 4.2 平台 → SISA 反馈流程

```
1. 平台侧发现特征提取或合规判定的优化点
2. 平台侧输出优化方案（不包含 SISA 机密数据）
3. 提交到 SISA 团队评审
4. SISA 侧评估是否采纳
5. 采纳后更新 SISA 实现，并在下一轮成果包中同步
```

---

## 5. 版本管理

### 5.1 Schema 版本号规则

```
主版本.次版本.修订号
│      │      └─ 向后兼容的字段补充
│      └──────── 新增必填字段或结构调整
└─────────────── 不兼容的结构变更
```

### 5.2 兼容性矩阵

| 平台 schema 版本 | SISA 成果包版本 | 兼容性 |
|-----------------|----------------|--------|
| 1.0.x | 1.0.x | ✅ 完全兼容 |
| 1.0.x | 1.1.x | ⚠️ 需升级平台 |
| 1.0.x | 2.x.x | ❌ 不兼容 |

---

## 6. 冲突处理

| 冲突场景 | 处理方式 |
|---------|---------|
| 特征维度不一致 | 以 SISA 为准，平台升级 `FEATURE_NAMES` |
| DNA 结构不兼容 | 以 schema_version 高的为准，低版本需升级 |
| 同名约束规则不同 | 保留双方规则，判定时取交集（更严格） |
| 密级认定分歧 | 按高密级处理（confidential > internal > public） |

---

## 7. 同步日志

每次同步记录以下信息：

```json
{
  "sync_id": "uuid",
  "timestamp": "ISO-8601",
  "direction": "sisa_to_platform | platform_to_sisa",
  "deliverable_type": "brand_dna",
  "version": "1.0.0",
  "status": "success | failed",
  "note": "..."
}
```

---

## 8. 例外管理

任何对本规范的偏离（如需要共享机密数据）须经资产所有人书面确认，并记录在案。
