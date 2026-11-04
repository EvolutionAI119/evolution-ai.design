# 中试复跑手册（PILOT RUNBOOK）

目标：任何人按本文件即可复跑中试，不依赖口头经验。
覆盖两个脚本：

- [`scripts/pilot_api_run.mjs`](../scripts/pilot_api_run.mjs)：后端真实链路（生成 → 导入改参 → 预览 → 导出 → 下载 → 格式校验）
- [`scripts/pilot_ui_run.mjs`](../scripts/pilot_ui_run.mjs)：前端真实链路（Vite 5173 → 代理 → 后端 8000 → 3D/2D 产物）

> 相关口径：[`docs/GEOMETRY_ACCEPTANCE.md`](./GEOMETRY_ACCEPTANCE.md)（G2 未测量与验收标准）、
> [`docs/CAR3D_BASELINE.md`](./CAR3D_BASELINE.md)（3D 视觉基线）。

---

## 1. 前置条件

| 项 | 要求 | 检查方式 |
|---|---|---|
| 操作系统 | Windows（脚本用 PowerShell 采样进程树） | — |
| Node | 可运行 `.mjs`（仓库已装 `puppeteer-core`） | `node -v`；`node -e "import('puppeteer-core')"` |
| 浏览器 | Microsoft Edge（Chromium），路径 `C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe` 或 `C:/Program Files/Microsoft/Edge/Application/msedge.exe` | 脚本启动时自检，缺失退出码 2 |
| 后端 | `http://127.0.0.1:8000`，健康且 `/api/v1/car/generate` 可响应 | `curl http://127.0.0.1:8000/api/v1/car/components` |
| 前端（仅 UI 脚本） | Vite `5173`（或自定义 `VITE_PORT`），`/api/v1` 代理到 8000 | 浏览器打开 `http://127.0.0.1:5173/#/designer` |
| Python 环境 | 后端依赖已安装（`backend/` 下可 `python -c "import app.main"`） | — |

### 1.1 启动服务（两个终端）

```powershell
# 终端 A：后端（backend/ 目录）
python -u -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 终端 B：前端（仓库根目录）
npx vite --port 5173
```

说明：

- 后端冷启动导入需 25–35s，健康检查通过后再跑脚本；
- `/api/v1/car/generate` 需要登录态。`backend/.env` 当前为 `GUEST_MODE=true`，
  中试期间以匿名访客跑通；生产环境该值会被配置层拦截（见 `GEOMETRY_ACCEPTANCE.md` 第 4 节）；
- 若改 `GUEST_MODE=false`，UI 脚本需先登录，否则生成阶段失败。

---

## 2. 后端链路（pilot_api_run.mjs）

### 2.1 运行

```powershell
# 严格模式（默认）：如实记录前端原始参数的结果
node scripts/pilot_api_run.mjs

# 完整链路模式：生成阶段原值被拒（422）后，用夹紧到后端区间的参数重试
node scripts/pilot_api_run.mjs --clamp-generate

# 自定义次数/输出目录
node scripts/pilot_api_run.mjs --runs 10 --out pilot-artifacts/api --clamp-generate
```

参数说明：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--runs` | 10 | 运行次数；计划固定为 4×sedan、3×suv、3×pickup |
| `--out` | `pilot-artifacts/api` | 产物目录 |
| `--clamp-generate` | 关闭 | 生成阶段先发前端原值；若 422 再发按后端区间夹紧的值。**仅用于验证下游链路**，原值失败会记录在 `stages.generateExact` |

### 2.2 每轮做什么

1. `POST /api/v1/car/generate`（前端参数集，扁平 `params`）；
2. `POST /api/v1/import-export/import`（转成分组参数，先发原值、再夹紧重试）；
3. `GET /api/v1/import-export/{sid}/preview`（3D 点云）；
4. `POST /api/v1/import-export/{sid}/export` 依次导出 `step/glb/stl/obj/json`；
5. `GET /api/v1/import-export/{sid}/download/{filename}` 取回文件；
6. 独立校验：STEP 头尾、GLB/STL/OBJ 可被 trimesh 解析、文件非空；
7. 采样后端进程内存/句柄（每轮前后）。

### 2.3 产物结构

```
pilot-artifacts/api/
├── pilot-api-summary.json          # 汇总（见 2.4）
├── verify-products.json            # 产物独立校验结果（60/60 可打开）
└── runNN-<type>/
    ├── generate.response.json      # 生成响应（含 nurbs_quality）
    ├── preview.response.json       # 预览点云/包围盒
    ├── runNN-<type>.step/.glb/.stl/.obj/.json
    └── stats.json                  # 单轮阶段耗时/内存
```

### 2.4 汇总字段与判据

| 字段 | 含义 | 通过判据 |
|---|---|---|
| `successRate` | 成功轮次占比 | 100 |
| `p95GenerateMs` | 生成 P95 | ≤ 1000ms（中试实测 343） |
| `p95ExportMs` | 单格式导出 P95 | ≤ 3000ms（实测 1209） |
| `p95TotalMs` | 端到端 P95 | ≤ 5000ms（实测 1723） |
| `productOpenRate` | 产物可打开率 | 100（实测 100） |
| `paramFidelity` | 尺寸保真（长/宽/高误差 %） | 长 ≤0.1、宽 ≤0.5、高 ≤5 |
| `exactImportRejected` | 原始前端参数被区间校验拒绝的次数 | 严格模式下应 >0（证明校验生效） |
| `memStart`/`memEnd` | 后端 WS 内存与句柄 | 无持续增长（实测 472.5→493.9MB，841→844） |

中试基线（2026-11-04，10 轮）：`successRate 100`、`p95GenerateMs 343`、`p95ExportMs 1209`、
`p95TotalMs 1723`、`productOpenRate 100`、STEP 822 实体、GLB 26,820 顶点 / 49,892 面。

> **当前预期（参数严格校验后）**：前端原始参数中 `roof_height`、`wheel_diameter`、
> `windshield_angle`（导入侧还有 `c_pillar_angle`）超出后端区间，默认运行会在生成阶段如实记录
> 422；这是第 1 项参数契约的验收证据，不是脚本故障。要跑完整下游链路请加 `--clamp-generate`，
> 或等待"参数以哪端为准"的裁决。

---

## 3. 前端链路（pilot_ui_run.mjs）

### 3.1 运行

```powershell
# 必须用硬件 GL：SwiftShader 软渲染在 2 视口 × 77k 三角面下会退化到数百秒/轮
$env:PILOT_GL='hw'
node scripts/pilot_ui_run.mjs

# 自定义次数/端口/输出目录
$env:VITE_PORT='5173'
node scripts/pilot_ui_run.mjs --runs 10 --out pilot-artifacts/ui

# 结束后清理环境变量
Remove-Item Env:PILOT_GL, Env:VITE_PORT
```

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `PILOT_GL` | 未设置 | `hw` = ANGLE D3D11 硬件渲染；不设置 = SwiftShader 软渲染（慢，仅作对照） |
| `VITE_PORT` | 5173 | 前端端口；脚本访问 `http://127.0.0.1:{PORT}/#/designer` |

### 3.2 每轮做什么

1. **每轮启动全新浏览器与页面**（避免同页面累积渲染导致退化）；
2. 在 Designer 页切换车型卡片（`.car-type-card`），点击生成（`.generate-btn`）；
3. 监听 `POST /api/v1/car/generate` 的状态/耗时/部件数；
4. 读取 `window.__CAR3D_SCENES__`：mesh 数、三角面数、NURBS/线框标记；
5. 读取 `svg.car-2d-svg`，落成独立可打开的 HTML；
6. 截图 `designer.png`；
7. 采样 JS 堆内存、浏览器进程树 WorkingSet/句柄；
8. 记录 page error / console error / 失败请求。

### 3.3 产物结构

```
pilot-artifacts/ui/
├── pilot-ui-summary.json
└── runNN-<type>/
    ├── metrics.json          # 本轮状态、耗时、mesh/tris、内存
    ├── designer.png          # Designer 截图（目视复核用）
    └── 2d-drawing.html       # 独立 2D 图纸（可直接浏览器打开）
```

### 3.4 汇总字段与判据

| 字段 | 含义 | 通过判据 |
|---|---|---|
| `successRate` | 成功轮次占比 | 100（实测 100） |
| `p95UiElapsedMs` | 单轮全流程 P95 | ≤ 20000ms（实测 10801） |
| `p95GenerateRequestMs` | 生成请求 P95 | ≤ 3000ms（实测 1728） |
| `svgOpenRate` | 2D 图纸可打开率 | 100（实测 100） |
| `sceneRegistryStable` | 场景注册稳定（NURBS 存在、mesh>20） | `true` |
| `meshSeries`/`triSeries` | 每轮 mesh/三角面 | 同车型内稳定（中试：sedan 147 mesh/77,006 tris；suv 138/77,348；pickup 143/79,638；与基线脚本的统计口径不同，各自门限为准） |
| `heapStartMB`→`heapEndMB` | JS 堆 | 无持续增长（实测 59.7→60.8） |
| `pageErrors`/`consoleErrors`/`failedRequests` | 运行期错误 | 全部为 0 |

> **当前预期（参数严格校验后）**：Designer 默认品牌参数同样含越界值，点击生成会收到 422，
> UI 中试会在生成阶段失败。这是**参数源未裁决**导致的已知影响，不是渲染回归；
> 待裁决后重跑。若只需验证渲染链路，可在页面手动把滑杆调到后端区间内再生成。

---

## 4. 3D 视觉基线（辅助判据）

中试之外，Car3D 改动仍需过基线：

```powershell
node scripts/car3d_baseline.mjs --out docs/preview/car3d-baseline/_current
node scripts/car3d_baseline_compare.mjs --cur docs/preview/car3d-baseline/_current
```

判据（[`docs/CAR3D_BASELINE.md`](./CAR3D_BASELINE.md)）：像素差 ≤1%、三角面 ±0.5%、
bbox ±5%、网格数 ±0.5%；退出码 0 通过。中试当次实测：10/10 分镜、像素差 0.00–0.01%、
201 mesh / 43,268 tris、hinge 1.222。

---

## 5. 已知故障与处置

| 现象 | 根因 | 处置 |
|---|---|---|
| 脚本卡住/每轮数百秒，run05 超时 | `PILOT_GL` 未设 → SwiftShader；外部孤儿 `server/index.js` 占 CPU | 设 `PILOT_GL=hw`；结束无关 node 进程 |
| `ReferenceError: disposeObject is not defined`，3D 仅 1 mesh | `useCarScene.js` 漏 import（已修复，提交 e7042516） | 确认修复在 HEAD；重跑 |
| 后端 8000 无响应 / 进程消失 | 后台子进程被宿主清理；冷启动未完成 | 用独立 top-level 进程启动；等 25–35s 健康检查 |
| 生成 422 | 参数越界（严格校验生效） | 见 2.4/3.4 的"当前预期"，不要夹紧后当作通过 |
| 生成仍**不**返回 422、越界值被接受 | 8000 端口是契约提交之前的旧进程 | 重启后端后再跑；`/api/v1/car/generate` 由旧代码持有则新契约不生效 |
| 基线 0/10 | 工作区未提交几何改动改变 mesh/tris | 用 HEAD worktree 复核；几何改动去留待裁决 |

---

## 6. 一键复跑清单

```powershell
# 0) 服务已起：8000 后端、5173 前端
# 1) 前端全量测试
npx vitest run

# 2) 后端全量测试
cd backend; python -m pytest tests -q; cd ..

# 3) 后端中试（严格记录 422；完整链路加 --clamp-generate）
node scripts/pilot_api_run.mjs

# 4) 前端中试（务必硬件 GL）
$env:PILOT_GL='hw'; node scripts/pilot_ui_run.mjs; Remove-Item Env:PILOT_GL

# 5) 3D 基线
node scripts/car3d_baseline.mjs --out docs/preview/car3d-baseline/_current
node scripts/car3d_baseline_compare.mjs --cur docs/preview/car3d-baseline/_current
```

产物目录 `pilot-artifacts/` 与 `_current/` 为临时产物，默认不提交。
