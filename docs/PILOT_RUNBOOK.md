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

### 1.1 参数唯一真源与映射（复跑前必读）

- 后端 [`backend/config/automotive_parameters.json`](../backend/config/automotive_parameters.json) 是参数区间的唯一真源；
- 前端扁平参数（`src/config/carPresets.js`）提交前必须经共享映射表 [`src/config/paramMapping.js`](../src/config/paramMapping.js)
  转成后端语义，禁止在后端猜别名：

| 前端键 | 后端键 | 说明 |
|---|---|---|
| `wheel_base` | `wheelbase` | 轴距 |
| `front_overhang` | `overhang_front` | 前悬 |
| `rear_overhang` | `overhang_rear` | 后悬 |
| `roof_height` | `roof_length` | **车顶跨度 1200–2000mm**，与板厚 `roof_height`（30–100mm）是完全不同的两个字段 |
| `rear_slant_angle` | `rear_slant_angle` | 独立合法参数，不再映射到 `c_pillar_angle` |

- 只读区间端点（游客可访问，前端选车型时拉取用于约束滑杆）：
  `GET /api/v1/car/parameters/schema`，返回 `groups` / `flat`（含 `min`/`max`/`group`）/ `aliases` / `semantics`。

### 1.2 启动服务（两个终端）

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
# 默认（严格）：前端设计值经映射表转后端语义后原值直通，不得夹紧
node scripts/pilot_api_run.mjs --runs 10 --out pilot-artifacts/api

# 诊断模式（仅排查越界用）：原值被拒后按区间夹紧重试；结果不能作为验收证据
node scripts/pilot_api_run.mjs --runs 10 --out pilot-artifacts/api-diagnostic --clamp-generate
```

参数说明：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--runs` | 10 | 运行次数；计划固定为 4×sedan、3×suv、3×pickup |
| `--out` | `pilot-artifacts/api` | 产物目录 |
| `--clamp-generate` | 关闭 | 诊断专用：原值 422 后按区间夹紧重试。**验收要求 0 次 422，启用本开关的结果不得作为通过证据**；原值结果记录在 `stages.generateExact` |

### 2.2 每轮做什么

1. `POST /api/v1/car/generate`（前端参数集，扁平 `params`）；
2. `POST /api/v1/import-export/import`（经共享映射表转成后端英文分组键，默认发原值、不做夹紧重试）；
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
| `successRate` | 成功轮次占比 | 100（本轮 100） |
| `p95GenerateMs` | 生成 P95 | ≤ 1000ms（本轮 386；上轮 343） |
| `p95ExportMs` | 单格式导出 P95 | ≤ 3000ms（本轮 1388；上轮 1209） |
| `p95TotalMs` | 端到端 P95（含 `generateExact` 与 `validate` 下载校验） | ≤ 5000ms（本轮 2355） |
| `productOpenRate` | 产物可打开率 | 100（本轮 100） |
| `paramFidelity` | 尺寸保真（长/宽/高误差 %） | 长 ≤0.1、宽 ≤0.5、高 ≤5（本轮 L 0、W 0.07–0.54、H 2.35–3.10） |
| `exactImportRejected` | 原始设计值被区间校验拒绝次数 | **0**（非 0 说明映射表或默认载荷仍越界） |
| `memStart`/`memEnd` | 后端 WS 内存与句柄 | 无持续增长（本轮 494.6→486.1MB，845→847） |

中试基线（2026-11-05，严格直通、无夹紧，10 轮）：`successRate 100`、`p95GenerateMs 386`、
`p95ExportMs 1388`、`p95TotalMs 2355`、`productOpenRate 100`、`exactImportRejected 0/10`、
STEP 822 实体、GLB 26,820 顶点 / 49,892 面。

> **P95 统计口径（必须按此解释，避免下次再漂移）**
> - `p95XxxMs` 的实现是升序后取 `ceil(n*0.95)-1` 索引；`n=10` 时索引为 9，即 **P95 = 单轮最大值**，
>   判据实质是「最差一轮」，对单次抖动极敏感。需要稳定 P95 时用 `--runs 20` 以上，并同时看中位数。
> - `p95TotalMs = Σ(全部 stage.ms)`。2026-11-05 起 stage 里新增 `generateExact`（同一生成请求的重复
>   计时）与 `validate`（下载 + 格式校验），因此本轮 2355ms 与 2026-11-04 的 1723ms **不可直接比较**。
>   跨轮只比 `p95GenerateMs` 与 `p95ExportMs`。

> **P95 复测记录（2026-11-05，均不加 `--clamp-generate`）**

| 轮次 | 环境 | `p95GenerateMs` | `p95ExportMs` | `p95TotalMs` |
|---|---|---|---|---|
| 上轮基线 11-04 | 未记录负载 | 343 | 1209 | 1723（旧口径） |
| A（契约重启后首跑） | 冷启动 | 423 | 1447 | 2676 |
| B（隔离空闲窗口） | 关闭 Vite/浏览器 | 386 | 1388 | 2355 |
| C（隔离窗口 1） | load 平均 28.5%、峰值 46% | 429 | 1507 | 2495 |
| D（隔离窗口 2） | load 平均 30.9%、峰值 46% | 432 | 1462 | 2513 |

> C、D 两轮连续复测均未达到 `gen ≤343ms / export ≤1209ms`，故 **P95 未关闭**。机器另有外部服务
> `D:\API\StarMission\command-center`（node `server\index.js`，端口 8799，见第 5 节）常态占用约 0.4 核，
> 16 逻辑核上整机 load 在 25%–31% 波动，属**环境干扰未消除**，不据此声称零退化。

> **参数单真源后的预期**：默认路径应 **0 次 422**。若出现 422，必须按「哪个键 / 哪个入口 /
> 哪个默认载荷」逐条定位修复，**不得用 `--clamp-generate` 掩盖后当作通过**。

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
| `successRate` | 成功轮次占比 | 100（本轮 100） |
| `p95UiElapsedMs` | 单轮全流程 P95 | ≤ 20000ms（本轮 5731；上轮 10801） |
| `p95GenerateRequestMs` | 生成请求 P95 | ≤ 3000ms（本轮 953；上轮 1728） |
| `svgOpenRate` | 2D 图纸可打开率 | 100（本轮 100） |
| `sceneRegistryStable` | 场景注册稳定（NURBS 存在、mesh>20） | `true`（本轮 true） |
| `meshSeries`/`triSeries` | 每轮 mesh/三角面 | 同车型内稳定（本轮 sedan 145/75,398；suv 147/75,684；pickup 141/78,006；与基线脚本统计口径不同，各自门限为准） |
| `heapStartMB`→`heapEndMB` | JS 堆 | 无持续增长（本轮 61.9→59.9） |
| `pageErrors`/`consoleErrors`/`failedRequests` | 运行期错误 | 全部为 0（本轮 0/0/0） |

> **必须用硬件 GL**（`PILOT_GL=hw`）。SwiftShader 下 pickup 单轮实测可达 120s（2026-11-05
> 校验中复现 120,407ms），P95 判据完全失真，不能作为验收数据。

> **参数单真源后的预期**：Designer 切换车型后滑杆已按 `/car/parameters/schema` 的区间约束，
> 点击生成应 0 次 422；出现 422 即说明某个默认载荷未落在区间内，按 3.4 的「键/入口/载荷」定位。

---

## 4. 3D 视觉基线（辅助判据）

中试之外，Car3D 改动仍需过基线：

```powershell
node scripts/car3d_baseline.mjs --out docs/preview/car3d-baseline/_current
node scripts/car3d_baseline_compare.mjs --cur docs/preview/car3d-baseline/_current
```

判据（[`docs/CAR3D_BASELINE.md`](./CAR3D_BASELINE.md)）：像素差 ≤1%、三角面 ±0.5%、
bbox ±5%、网格数 ±0.5%；退出码 0 通过。中试当次实测：10/10 分镜、像素差 0.00%、
201 mesh / 43,246 tris、hinge 1.222。

---

## 5. 已知故障与处置

| 现象 | 根因 | 处置 |
|---|---|---|
| 脚本卡住/每轮数百秒，run05 超时 | `PILOT_GL` 未设 → SwiftShader；外部孤儿 `server/index.js` 占 CPU | 设 `PILOT_GL=hw`；结束无关 node 进程 |
| `ReferenceError: disposeObject is not defined`，3D 仅 1 mesh | `useCarScene.js` 漏 import（已修复，提交 e7042516） | 确认修复在 HEAD；重跑 |
| 后端 8000 无响应 / 进程消失 | 后台子进程被宿主清理；冷启动未完成 | 用独立 top-level 进程启动；等 25–35s 健康检查 |
| 生成 422 | 前端默认载荷或映射仍越界（契约已单真源，正常应为 0） | 按「键 / 入口 / 默认载荷」逐条定位，改设计值或映射表；**不要夹紧掩盖** |
| 生成**不**返回 422、越界值被接受 | 8000 端口是契约提交之前的旧进程 | 重启后端后再跑；旧进程持有 `/api/v1/car/generate` 则新契约不生效 |
| 基线 0/10 | 工作区存在未提交几何改动，或参数设计值改动后未重采 | 用 HEAD worktree 复核；有意变更需整体重采并提交基线 |
| API `p95ExportMs` 上浮（1209→1447/1388/1507/1462ms，门限 3000 内） | 外部**其他项目**服务 `D:\API\StarMission\command-center`：node `server\index.js`，PID 13572，监听 8799、连 8765，启动 2026-11-02 19:09:57，父进程已退出；常态占用约 0.4 核 | **不要结束**（非本项目）。在低负载窗口复测并同期采样整机 load；报告须写「环境干扰未消除」 |
| UI P95 数百秒、单轮 120s | `PILOT_GL` 未设 → SwiftShader 软渲染（pickup 78k tris 最明显） | 必须设 `PILOT_GL=hw`；该数据不得用于验收 |

---

## 6. 一键复跑清单

```powershell
# 0) 服务已起：8000 后端、5173 前端
# 1) 前端全量测试
npx vitest run

# 2) 后端全量测试
cd backend; python -m pytest tests -q; cd ..

# 3) 后端中试（严格直通，要求 0 次 422）
node scripts/pilot_api_run.mjs --runs 10 --out pilot-artifacts/api

# 4) 前端中试（务必硬件 GL）
$env:PILOT_GL='hw'; node scripts/pilot_ui_run.mjs --runs 10 --out pilot-artifacts/ui; Remove-Item Env:PILOT_GL

# 5) 3D 基线
node scripts/car3d_baseline.mjs --out docs/preview/car3d-baseline/_current
node scripts/car3d_baseline_compare.mjs --cur docs/preview/car3d-baseline/_current
```

产物目录 `pilot-artifacts/` 与 `_current/` 为临时产物，默认不提交。

---

## 7. 中试最终结论（2026-11-05）

**状态：有条件通过（维持）。** 已达标：成功率 20/20、0 次 422、产物可打开 60/60、3D 基线 10/10、
错误日志 0。未达标：P95 相对上轮不退化（导出 1209→1462~1507ms，生成 343→429~432ms，
均在绝对门限内但未回到上轮水平）。**该上浮已归因为环境负载与判据敏感度，不是新增功能成本**（见第 8 节
控制变量实测：HEAD 的导出分段与 HTTP 耗时均不慢于新契约前，整链中位数反而低 5%）。

清零条件（满足任一条即可升级为「通过」）：

1. 在无外部负载的同规格机器上复测 10 轮（`--runs 10`，不加 `--clamp-generate`），
   `p95GenerateMs ≤343` 且 `p95ExportMs ≤1209`；或
2. 由用户裁决更换判据口径（例如 `--runs 20` 取真 P95、或改用中位数 + 明确容差），
   并据此重新定义门限，避免「n=10 的 P95 = 最大值」把单次抖动判成回归。

---

## 8. 导出耗时分段与版本对比（2026-11-05）

**结论：导出变慢不是新增功能带来的，是测量窗口/机器负载差异；控制变量后 HEAD 不慢于新契约前。**

同一批设计值（sedan，`pilot-artifacts/sedan-groups.json`）、同机顺序执行、同进程分段计时
（10 轮中位数，单位 ms）：

| 段 | HEAD | 新契约前 `8855238b` | Δ |
|---|---|---|---|
| 几何生成（单次 `generate_complete_car`） | 82.25 | 78.75 | +3.5% |
| trimesh 场景构建（`_build_trimesh_scene` 减生成） | 95.61 | 99.82 | −4.2% |
| STEP 转换 + 写盘 | 4.92 | 5.61 | −12% |
| GLB 转换 + 写盘 | 10.02 | 9.29 | +7.9% |
| STL 转换 + 写盘 | 7.33 | ≈0（±7ms 噪声） | — |
| OBJ 转换 + 写盘 | 52.43 | 50.04 | +4.8% |
| JSON `dumps` + 写盘 | 23.91 | 27.34 | −12.5% |
| **五格式合计（模拟 route 顺序）** | **786.35** | **790.83** | **−0.6%** |

同窗口 HTTP 直连（同一脚本、同一入参，各 10 轮，服务端 `export_time_ms`）：

| 场景 | HEAD 中位 | 新契约前 中位 | Δ |
|---|---|---|---|
| export（会话复用） | 1024 | 1061 | −3.5% |
| export（每次先 preview，贴近中试序列） | 962 | 986 | −2.4% |
| 中试脚本整链（导出客户端耗时中位 / 最大） | 1080 / 1391 | 1139.5 / 1651 | −5.2% |

分段归因：导出耗时 ≈ **5 次完整几何生成**（step/glb/stl/obj/json 每个格式内部各调用一次
`generate_complete_car`）+ **3 次 trimesh 场景重建**（glb/stl/obj 各自 `_build_trimesh_scene`）。
按上表，`5×生成 + 3×场景` 约占 786ms 中的 700ms（89%）；格式转换+写盘只占约 99ms。
参数契约校验只在 import 入口（每会话一次）执行，不在导出循环内；schema 端点与前端映射表也不产生
导出侧重复请求；tris 43,268→43,246 的变化对导出无额外合并/校验步骤。

**优化空间（可消除的浪费，需授权后实施）**：导出循环里重复生成 5 次、重建场景 3 次。
若改为「一次生成 + 一次场景 + 逐格式转换写盘」，按分段实测预估 in-process 约 276ms、HTTP 约
400–520ms（相对当前 1024ms 下降 **50%–60%**）。方案很小、不动几何：`_build_trimesh_scene(car=None)`、
`export_*(path, car=None, scene=None)` 增加可选入参，`export_model` 只算一次；验收用导出文件字节哈希
与改前逐一对齐。是否实施由用户裁决；在裁决前按现状接受当前导出基线。
