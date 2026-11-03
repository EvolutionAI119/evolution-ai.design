# Car3D.vue 拆分设计与实施进度

| 项 | 内容 |
|---|---|
| 版本 | v1.1 · 2026-11-03（补实施进度） |
| 对象 | [src/components/Car3D.vue](../src/components/Car3D.vue)（1518 行 / 65 KB） |
| 目标 | 行数降 40% 以上；渲染结果零差异；纯函数可单测 |
| 约束 | 每批只搬一个模块、行为不变；拆分前先补渲染基线；每步独立提交、全绿 |
| 关联 | [ASSET_MANIFEST.md](ASSET_MANIFEST.md)、[2D_LAYOUT_VERIFICATION.md](2D_LAYOUT_VERIFICATION.md) |

---

## 1. 现状与根因

Car3D 单体同时承担：NURBS 网格构建、车身开洞、玻璃分缝、车轮/轮拱、灯/保险杠/后视镜、车门与铰链、内饰座椅、场景/相机/交互、VTOL/反重力动画、UI 状态与样式。任何局部改动都要在 1875 行里定位，且 3D 问题只能靠截图复验，回归成本高。

**拆分原则**：
1. 组件只保留模板、props 与 UI 状态，几何/场景逻辑全部外移；
2. 每个模块只依赖 `carProfile` / `carGlass` / `carInteriorLayout` 三个真源，不新增坐标推导；
3. 共享 `THREE` 与材质缓存，避免重复创建与显存泄漏；
4. 先抽纯函数，再抽有状态模块，最后抽动画/交互。

---

## 2. 目标模块与职责

| 模块 | 从 Car3D 迁出的内容（当前行段） | 职责 | 依赖 |
|---|---|---|---|
| `src/three/materials.js` | `paintColor`、玻璃/橡胶/镀铬材质 | 统一材质与复用缓存 | 无 |
| `src/three/geometry/smoothing.js` | `smoothNormalsKeepHardEdges`（392–474） | 法线平滑纯函数 | 无 |
| `src/three/geometry/bodyShell.js` | `splitBodyAperturesInterior`（475–554）、`alignNurbsToProfile`（555–601）、`applyGreenhouseTaper`（830–888）、侧围轮廓（722–829） | 车身壳、开洞、锥化 | smoothing、profile |
| `src/three/parts/glass.js` | `addBandGlass`（915–958）、`addDloPane`（959–991） | DLO 分缝与窗片 | carGlass、materials |
| `src/three/parts/wheels.js` | `createNurbsWheel`（346–391）、`createWheel`（1013–1068）、`addArchLiner`（1069–1096）、升力装置（992–1012） | 车轮、轮腔衬、升力件 | profile、materials |
| `src/three/parts/lightsBumpers.js` | 保险杠（1100–1114）、前大灯（1110–1141）、尾灯（1142–1157） | 灯与保险杠贴合外表面 | profile、materials |
| `src/three/parts/doors.js` | 分缝线/门板/把手（1158–1212）、`attachDoorTrimToHinges`（585–601） | 车门几何与铰链挂载 | profile、materials |
| `src/three/parts/mirrors.js` | 镜壳/凸面镜片（1213–1379） | 后视镜 | profile、materials |
| `src/three/interior/seats.js` | `addInteriorSeats`（602–615）、座椅段（1380–1387） | 座椅网格编排 | carInterior |
| `src/three/scene/createScene.js` | `initScene`（1388–1499） | 渲染器、相机、灯光、环境 | materials |
| `src/three/scene/interactions.js` | 鼠标/滚轮/尺寸（1500–1552） | 交互事件与清理 | createScene |
| `src/three/scene/flightFx.js` | VTOL 风扇/能量场（1553–1599） | 飞行特效 | materials |
| `src/three/scene/animate.js` | 动画循环（1600–1691）、视图/重置（1692–1740） | 门、VTOL、转向、视角 | createScene、doors |
| `src/three/dispose.js` | `disposeMaterial` / `disposeObject`（1751–1779） | 统一释放 | 无 |
| `src/composables/useCarScene.js` | `createCar`（616–721）、`updateCar`（1780–1961）、生命周期 | 编排与响应式更新 | 上述全部 |
| `Car3D.vue` | 模板 + UI 状态 + 按钮 | 仅视图层 | useCarScene |

预期：Car3D.vue 从 1875 行降到约 350–450 行；其余模块每个 60–250 行。

---

## 3. 依赖图

```text
carProfile.js ─┬─> geometry/bodyShell.js ─┐
carGlass.js ───┼─> parts/glass.js ────────┤
carInteriorLayout.js ─> interior/seats.js ─┤
                                           ├─> composables/useCarScene.js ─> Car3D.vue
materials.js ──> parts/{wheels,lightsBumpers,doors,mirrors}.js ─┘
               └─> scene/{createScene,flightFx}.js
scene/createScene.js ─> scene/{interactions,animate}.js ─> useCarScene.js
```

单向依赖：`Car3D.vue → useCarScene → parts/scene → 真源`；禁止反向 import，禁止 parts 之间横向调用。

---

## 4. 分步迁移（每步可独立回滚）

| 阶段 | 内容 | 验收 | 预估 |
|---|---|---|---|
| P0 基线 | 6 车型 × 6 机位截图；记录 mesh 数 / 三角面数 / bbox / draw calls | 基线文件入库 `docs/preview/car3d-baseline/` | 0.5 天 |
| P1 纯函数 | 抽 `smoothing` / `bodyShell` / 材质 | 783 测试全绿；截图零差异 | 1 天 |
| P2 零件 | 抽 `wheels` / `glass` / `doors` / `lightsBumpers` / `mirrors` / `seats` | 逐件截图对比；门开合角度不变 | 2 天 |
| P3 场景 | 抽 `createScene` / `interactions` / `flightFx` / `animate` / `dispose` | 交互、VTOL、反重力转向全通过 | 2 天 |
| P4 收口 | `useCarScene` 接管 updateCar；组件只剩 UI | 行数 ≤ 450；无未使用变量 | 1 天 |

每阶段提交前必跑：`npx vitest run`、`npm run build`、`python scripts/pre_commit_check.py`。

---

## 5. 回归方案

| 层 | 方法 | 判据 |
|---|---|---|
| 单元 | 纯函数（smoothing、bodyShell、dispose）新增 spec | 输入/输出数值断言 |
| 组件 | `window.__CAR3D_SCENES__` 已有注册表 | mesh 数、三角面数、bbox 与 P0 基线一致 |
| 视觉 | 6 车型 × 6 机位截图（side/cockpit/driver/rear34/cargo/frunk） | 像素差 < 1%；无高光白带/破面/穿壳 |
| 交互 | 门开合 0→70°、VTOL、原地转向 | 无抖动、无穿透、帧率不降 |
| 构建 | `npm run build` + 公网构建同源 | 无新增 warning；包体不增 5% 以上 |

---

## 6. 风险与应对

| 风险 | 应对 |
|---|---|
| 闭包状态散落，抽取后 props 不同步 | 先抽纯函数；有状态模块统一由 `useCarScene` 持有 |
| 材质/几何重复创建导致显存上涨 | `materials.js` 缓存 + `dispose.js` 统一释放 |
| 车门动画依赖局部变量 | 门模块导出 `createDoorRig()`，角度由 `carParams.door_open_angle` 驱动 |
| 视觉回归无自动化 | P0 先建截图基线；后续接像素对比脚本 |
| 一次改太多无法定位 | 严格按 P1→P4，每步单独提交 |

---

## 7. 实施进度（2026-11-03）

| 阶段 | 已完成 | 验证 |
|---|---|---|
| P0 | 5 机位 × 2 门态 = 10 分镜基线 + `manifest.json`，采集/比对脚本可重复 | 连续两轮 10/10、像素 0.00% |
| P1 | `geometry/smoothing.js`、`three/dispose.js` 抽出 | 全量 829 测试 + 基线 10/10 |
| P2 | `parts/doors.js`：`createDoorRig`（门缝/门板/把手/门内板 + 门片玻璃挂载） | 全量 829 测试；基线 10/10、像素 0.00%；门开合 1.222 rad（70°）不变 |
| P2 | `parts/glass.js`：`addBandGlass` / `addDloPane`（入参全显式，`doorGlass` 收集仍由 createCar 完成） | 全量 829 测试；基线 10/10、像素 0.00%；网格 201 / 三角面 43268 不变 |
| P2 | `interior/seats.js`：`addInteriorSeats` / `attachDoorTrimToHinges`（注入 doorHinges、preset 由调用方传入） | 全量 829 测试；基线 10/10、像素 0.00%；cockpit 门态分镜 0.00% |
| P2 | `parts/lightsBumpers.js`：保险杠 / 前大灯 / 尾灯（坐标常量逐字保留，尾灯复用头灯 `hlZ`） | 全量 829 测试；基线 10/10、像素 0.00%；front / left / bbox 均 0.00% |
| P2 | `parts/mirrors.js`：镜壳 / 连接颈 / 密封圈 / 凸面镜片（`zSide` 显式贯穿、贴花纹理左右共用） | 全量 829 测试；基线 10/10、像素 0.00%；left / iso45 / bbox 均 0.00% |
| P2 | `parts/wheels.js`：四轮 / 轮腔衬 / 升力风道盘唇（材质注入，`flightRings` 仍由组件驱动） | 全量 829 测试 + flightPhysics 35 用例；基线 10/10、像素 0.00%；left / iso45 / bbox 均 0.00% |

P2 剩余：`materials.js` 收口（统一材质与构建内复用缓存）。

## 8. 本轮结论

P0 基线与 P1/P2（`smoothing` / `dispose` / `doors` / `glass` / `seats` / `lightsBumpers` / `mirrors` / `wheels`）已落地，Car3D.vue 1875 → 1518 行；剩余 `materials.js` 收口与 P3 场景层（`createScene` / `interactions` / `flightFx` / `animate`）。每批以 `npx vitest run` + `node scripts/car3d_baseline.mjs --out .tmp-car3d-current` + `node scripts/car3d_baseline_compare.mjs --cur .tmp-car3d-current` 为闸门，任何分镜像素差超 1% 先归因再决定修复或回滚。
