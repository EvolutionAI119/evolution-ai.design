# SISA → 平台：问题审核反馈单

> 生成：SISA（内部算法核）｜审核人：SISA 自动化审核流程
> 依据：《SISA 资产分类与保密声明》第三条（资产单向流动 平台 → SISA）
> 说明：本单为**逆向反馈的缺陷审核结论**，不含 SISA 算法实现、不含墨玉 DNA。
> 审核方法：**逐条对照上游仓库已提交 HEAD 实测**，不采信二手描述。

---

## 一、审核基线（可复现）

| 项 | 值 |
|---|---|
| 上游仓库 HEAD | `2a87fcd9`（分支 `feature/nurbs-*`，2026-10-11 11:15） |
| 相关文件工作区状态 | **未改动**（与 HEAD 一致）→ 结论对已提交代码有效 |
| 审核方式 | 源码定位 + 构建产物字节核对 + 依赖清单比对 |

---

## 二、审核结论总表

| # | 问题 | 结论 | 严重度 | 归属 |
|---|---|---|---|---|
| A | `Car2D.vue` 三处顶层 `console.log` | **成立** | 低 | 上游仓库 |
| B | `echarts` 全量引入 | **成立（程度需修正）** | 低-中 | 上游仓库 |
| C | `image_reconstruction.py` 的 `except cv2.error` 自毁降级 | **代码成立，归属非上游仓库** | 中 | 源压缩包变体 |
| D | `continuity_checker.py` 缺 `surface_curvature_fd` | **归因错误（我方失误）** | — | 撤回 |
| E | `CarViewer.vue` wireframe/toggleAuto 失效 | **不成立**（上游仓库无此文件） | — | 撤回 |
| F | `Designer.vue` `applyPreset` 不完整 | **不成立**（上游仓库无该实现） | — | 撤回 |
| G | echarts 使公开前台包体 +1 MB | **不成立**（公开 dist 不含 echarts） | — | 撤回 |

---

## 三、成立项（建议修复）

### A. `Car2D.vue` 顶层 console.log

**位置**：`src/components/Car2D.vue:91-93`（`<script setup>` 顶层，缩进 0）

```js
console.log(`[Car2D] ${props.carType.toUpperCase()} - H=${...}`)
console.log(`[Car2D] beltLineY=${beltLineY.value.toFixed(1)}, roofTopY=...`)
console.log(`[Car2D] hoodLineY=${...}, trunkLineY=${...}`)
```

**影响**：`<script setup>` 顶层语句在组件每次挂载时执行 → 控制台噪声。
该组件被 `Designer.vue` 使用且有单测（`tests/car2d.test.js`），故每次进入设计器都会打印。

**建议**：删除三行；如需保留调试信息，改为 `if (import.meta.env.DEV)` 包裹。

### B. echarts 全量引入

**位置**：`src/components/AdminEvidence.vue:153`

```js
import * as echarts from 'echarts'      // 全量，非按需
```

**事实核对（字节级）**：

| 产物 | 大小 | 含 echarts/zrender |
|---|---|---|
| `dist/assets/`（**公开前台**） | 5.91 MB（75 文件） | **不含** |
| `backend/app/static/admin/assets/echarts-*.js` | **1,032,446 B** | 含 |
| `backend/app/static/admin/assets/` 合计 | 2.18 MB | — |

**结论修正**：echarts 已被 `vite.config.js` 的 `manualChunks` 正确分包，
且**只存在于管理后台产物**（`/admin` 由后端独立托管）。
故"拖累公开前台"**不成立**；真实影响仅限 **/admin 首屏需加载 ~1.0 MB**。

**建议**（可选，低优先）：`AdminEvidence.vue` 改用按需引入
（`echarts/core` + 具体 chart/component），预计可把该 chunk 压到 ~300 KB。

---

## 四、撤回项（附撤回理由）

### D. `continuity_checker.py` —— **我方归因错误，特此撤回**

**我曾上报**："上游把该文件从 1050 行/28 函数退化为 537 行/18 函数"。

**实测复核**：

| 证据 | 结果 |
|---|---|
| 上游仓库该文件历史提交 | 仅 2 次（`f17070ec` / `dd3e689a`），**始终 537 行/18 函数** |
| 上游仓库该文件是否含 `surface_curvature_fd` | **否**（从未有过） |
| SISA `shared-assets/upstream/` 上游副本 | **537 行/18 函数**（与仓库一致） |

**真实经过**：SISA 的 harness 初始版本即为 537 行（与上游一致）；
是 SISA 自身在吸收源压缩包时引入了 1050 行变体（该变体**仅存在于压缩包**，
从未出现在上游仓库历史）。故"上游退化"**不成立**，责任在 SISA 侧的取材口径。

**已采取的措施（SISA 侧）**：保留更完整的变体作为整合层依赖，并加装"防退化守卫"。
**对平台的需求：无。** 此条不构成上游缺陷。

### E / F / G —— 撤回

| 项 | 撤回理由 |
|---|---|
| E `CarViewer.vue` | 全仓（排除 `node_modules`）**不存在该文件**；结论基于压缩包内旧快照 |
| F `Designer.vue` `applyPreset` | 上游 `Designer.vue` 实为 **2027 行**，使用 Pinia + `../config/carPresets`；**无** `applyPreset` / `PRESETS` / `params.js` / `componentParams` |
| G 前台 +1 MB | 公开 `dist/assets` 经字节扫描**不含** echarts |

**根因说明**：先前一轮审计所依据的是一份**工作区导出压缩包**
（`project_files_backup.zip`，含大量未提交内容），其中若干文件与上游仓库
**并不一致**。本次审核改为**逐条对照仓库 HEAD**，故修正上述结论。
SISA 侧已记录该口径教训：**引用外部代码结论前必须核对目标仓库版本**。

---

## 五、仍需平台确认的一条（C）

### C. `image_reconstruction.py` 的降级路径自毁

**代码事实**（源压缩包变体，**上游仓库无此文件**）：

```python
try:
    import cv2
except ...:
    cv2 = None                      # L28 置空

...
except cv2.error:                   # L75 —— cv2 为 None 时抛 AttributeError
```

无 opencv 的环境下，异常处理语句本身崩溃，
使"优雅降级"失效（实测 `AttributeError: 'NoneType' object has no attribute 'error'`）。

**归属说明**：该文件**不在上游仓库**中，而在工作区导出压缩包内。
故此项**不作为上游缺陷**，仅供平台判断该变体是否应回归仓库；
若回归，建议同步修掉此处。

---

## 六、交付与边界

- 本单放置于平台工作区 `shared_reference/`，作为参考数据（依声明第三条），
  **由声明人决定是否采用**。
- **未包含**：SISA 算法实现、墨玉造型 DNA、内部模型权重、任何凭据。
- 可复现：所有结论均给出文件路径与行号，或构建产物字节数。
