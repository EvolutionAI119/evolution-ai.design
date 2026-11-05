# 几何验收口径与生产配置预检（2026-11-04）

本文件收口中试遗留的两类"口径"问题：

1. **G2 / A 级曲面证据**：明确平台侧测什么、不测什么，验收标准如何落地；
2. **生产配置预检**：用临时环境变量演练 fail-fast，确认配置层能拦住不安全配置。

> 适用范围：`EVOLUTION-AI.DESIGN` 平台仓库（不含 SISA 内核仓库）。
> 关联约束：70° 开门角不动、82° 待裁决、公网冻结、不做结构性重构。

---

## 1. 平台侧 G2 口径：**未测量**

曲率连续性管线（`iges_nurbs` / `nurbs_curvature`）已迁至 **SISA**，平台端
`NURBSCarBodyGenerator._measure_nurbs_quality()` 保留字段契约，但如实报告
"不可测"，不再伪造 `True`。

中试实测返回值（10/10 一致）：

```json
{
  "g2_continuous": false,
  "surface_count": 44,
  "control_points_total": 2123,
  "measured": false,
  "n_flat_surfaces": 0,
  "n_unmeasurable": 0,
  "curvature": {},
  "measure_error": "曲率管线已迁至 SISA，平台端不提供测量"
}
```

**口径定义**：

- `g2_continuous: false` 的语义是"**未测量 / 无法给出结论**"，**不是**"几何不满足 G2"；
  任何验收、看板、报告都不得把该值当作不合格判据。
- `curvature` 为空、`measured: false` 时，平台侧不提供任何逐曲面曲率证据。
- G2 的正式测量责任在 SISA；平台侧结果只可作为"移交前的占位字段"。

---

## 2. 验收标准（平台侧当前版本）

G2 不可测后，平台侧验收改为以下三项，全部可复跑：

### A. STEP 产物完整性与包围盒

| 检查项 | 方法 | 通过判据 | 中试实测 |
|---|---|---|---|
| STEP 文件结构 | 检查 `ISO-10303-21` 头 + `END-ISO-10303-21` 尾 | 头尾闭合、无截断 | 822 实体，头尾闭合 |
| 包围盒（长×宽×高） | 同源 GLB/STL 网格实测包围盒（mm） | 与请求尺寸偏差 ≤ 5% | 4950.0×1878.7×1425.7，长度 0.00%、宽度 0.03–0.37%、高度 2.35–3.05% |
| 多格式一致性 | 同一会话导出 GLB/STL/OBJ/JSON 并可解析 | 4 格式全部可打开 | 60/60 产物可打开 |

> **证据缺口**：平台侧没有 STEP 实体内核，无法直接对 STEP 做实体级包围盒复算，
> 上述包围盒来自同一参数源生成的 GLB/STL 网格。该缺口在第 4 节统一登记。

### B. C0 连续（共享边）

以"共享硬点/共享边"测试为证据，而不是曲率管线：

- `test_upper_body_chain_shares_edges`：上轮廓链相邻钣件共享边；
- `test_transverse_chain_edges_coincide`：横向链共享边重合；
- `test_pillar_wedges_share_glass_and_window_edges`：A/C 柱楔与玻璃/侧窗共享边；
- `test_shared_edges_stay_coplanar_under_override`：参数覆盖后共享边仍共面。

判据：上述用例全部通过（中试全量后端测试 429 passed / 1 skipped / 2 xfailed）。

### C. 目视复核

对 3 车型各至少 1 张 Designer 截图（`pilot-artifacts/ui/runNN-<type>/designer.png`）人工复核：

- 车身无破面、无穿模、无异常高光白带；
- 2D 图纸与 3D 预览轮廓一致；
- SUV 前脸灰斑、体量感列为 P2 观察项（不阻塞）。

---

## 3. A 级曲面证据缺口（明确登记）

| 缺口 | 现状 | 影响 | 处理 |
|---|---|---|---|
| G2 曲率连续 | 平台侧 `measured: false`，管线在 SISA | 无法用平台产物证明 A 级曲面 | 验收移交 SISA 后补测；平台侧只做 A/B/C 三项 |
| STEP 实体级包围盒 | 无 CAD 内核，只能用同源网格 | STEP 数值非实体复算 | 记录为证据缺口，不声称"STEP 实测 bbox" |
| 曲面阶次/控制点合理性 | `control_points_total=2123` 仅计数，无逐面质量评估 | 无法证明曲面光顺 | 由 SISA 曲率管线补 |
| 平面曲面占比 | `n_flat_surfaces=0` 但在 `measured:false` 下不具判定意义 | 不能据此判断"无平面" | 同样移交 SISA |

**结论**：当前平台侧几何验收是"**结构完整 + 尺寸可信 + C0 共享边 + 目视**"，
**不能作为 A 级曲面（G2）合格证据**。任何对外表述必须带此限定。

---

## 4. 生产配置预检（fail-fast 演练）

### 背景

`backend/app/config.py` 的 `Settings` 在 `model_validator(mode="after")` 中做生产环境
强校验；本次演练只使用**临时进程环境变量**，**未修改 `backend/.env` 默认值**。

### 演练命令（在 `backend/` 下执行）

```powershell
# 公共：所有演练都用独立 PowerShell 进程，结束后环境变量自动丢弃
$env:ENVIRONMENT='production'
$env:GUEST_MODE='false'
# 其余按用例设置
python -c "from app.config import settings; print('OK', settings.ENVIRONMENT, settings.DEBUG, settings.GUEST_MODE, len(settings.SECRET_KEY))"
```

### 结果

| 用例 | 临时环境变量 | 期望 | 实测 |
|---|---|---|---|
| A：默认 SECRET_KEY | `ENVIRONMENT=production`、`GUEST_MODE=false`，不覆盖 `SECRET_KEY`（沿用 `.env` 内置开发默认值） | 启动即失败 | 退出码 1，`pydantic_core.ValidationError`：**生产环境必须通过环境变量或 .env 覆盖 SECRET_KEY，不能使用内置开发默认值** |
| B：开放访客 | `ENVIRONMENT=production`、`DEBUG=false`、`GUEST_MODE=true`、48 位随机 `SECRET_KEY` | 启动即失败 | 退出码 1，`pydantic_core.ValidationError`：**生产环境禁止开启 GUEST_MODE=true：该模式将包含超级管理员接口在内的全部受保护接口对匿名访客开放** |
| C：合规配置 | `ENVIRONMENT=production`、`DEBUG=false`、`GUEST_MODE=false`、48 位随机 `SECRET_KEY` | 正常加载 | 退出码 0，输出 `OK ENV=production DEBUG=False GUEST=False SECRET_LEN=48` |

结论：配置层能拦住"默认密钥"与"生产开放访客"两类高危配置；合规配置可正常启动。

### 未改动项与遗留风险

- `backend/.env` **未改动**，其中仍为 `GUEST_MODE=true`（本地开发默认）。
- 该默认值在 `ENVIRONMENT=production` 下会被直接拦截（用例 B），因此**生产部署必须显式覆盖**，
  不能依赖仓库内 `.env`。
- 生产部署清单需补充：`ENVIRONMENT=production`、`DEBUG=false`、`GUEST_MODE=false`、
  `SECRET_KEY` ≥ 32 位（演练用 48 位）。

---

## 5. 复跑入口

- 中试脚本用法、产物结构、判据阈值见 [`docs/PILOT_RUNBOOK.md`](./PILOT_RUNBOOK.md)。
- 几何结构完整性与包围盒数据来自 `pilot-artifacts/api/`，前端截图来自 `pilot-artifacts/ui/`。
