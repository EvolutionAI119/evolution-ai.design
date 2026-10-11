# SISA 2D 渲染成果集成与 Cayenne 渲染修复说明

> 状态：已实施并验证 ｜ 影响面板：设计器「2D 渲染」卡片与「2D 视图」预览
> 数据来源：`shared_reference/SISA_REVERSE_REFERENCE_PACK.json`（SISA 点云逆向参考数据包）

---

## 1. 问题定位（修复前）

用户报告 Cayenne（SUV）在 2D RENDER 面板中渲染异常：画面只剩零散碎片
（悬浮小圆圈、一小段窗线、贴地小弧），车身主体不可见。

| # | 缺陷 | 根因 | 严重度 |
|---|---|---|---|
| 1 | **车顶/引擎盖/腰带线整段被裁切** | 缩放只按宽度计算（`(800-80)/L`），高度方向无约束。Cayenne H=1673mm 时 `roofTopY ≈ -72px`，translate 后仍在 viewBox 之外，整个上车身画到画布外 | 高（主异常） |
| 2 | **车轮几何错位** | 外胎弧端点取 `groundY - 离地间隙`（应取地面），且 sweep/大弧标志组合只画出下半弧；内圈圆心与外弧不同心 → 悬浮小圆 + 贴地小弧 | 高 |
| 3 | **轮廓不闭合** | 只有 hood/trunk/belt 三条独立线段，无前/后保险杠立面、无底边连接，形似漂浮碎片 | 中 |
| 4 | **SUV 比例失真** | hood/belt/trunk 高度比例按轿车硬编码（0.62/0.76/0.66），SUV 腰线明显更高 | 中 |
| 5 | **侧窗关键点无钳位** | SUV/MPV 后风挡角度小（22°/15°），`底点X = 顶点X + 垂高/tan` 无上界，可越出车尾 | 中 |
| 6 | 顶层 console.log ×3（SISA 反馈单问题 A） | `<script setup>` 顶层语句每次挂载执行，控制台噪声 | 低 |
| 7 | 参数缺省用 `\|\|` | 合法的 `0` 值（如 rear_slant_angle: 0）被吞成默认值 | 低 |

## 2. 渲染管线重构（`src/components/Car2D.vue`）

### 2.1 双向自适应缩放（修缺陷 1）

```js
scale = min( (svgWidth - 80) / L, (groundY - padTop) / (H + gc) )
```

- 画布改为 800×420，地面线 `groundY = 364`，顶部 `padTop = 30`（兼作 SISA 图例区），
  底部 56px 为 WB/L 标注区。
- 同时约束宽度（车长）与高度（离地间隙 + 车高）两个方向，任意参数组合下车顶不越界。
- 内容水平居中：`contentX = (svgWidth − L·scale) / 2`。

### 2.2 车轮触地 + 同心（修缺陷 2，落实 SISA ground_alignment）

- 轮胎最低点 = 地面：`wheelCY = groundY − r`（SISA 参考包改进点：z 原点 = 地面）。
- 轮胎（深色填充圆）/ 轮辋（0.58r）/ 轮毂（0.12r）三者同心。
- 车身底边 = 侧裙下缘 = `groundY − 离地间隙`，轮拱以轮心为圆心（r×1.16）
  在底边上开口，端点由弦长公式计算并钳位。

### 2.3 闭合车身轮廓（修缺陷 3）

单一 `<path>`：前保立面 → 圆角鼻 → 引擎盖 → A 柱 → 车顶 → C 柱 → 尾门圆角 →
后保立面 → 底边（双轮拱）→ 闭合。淡绿填充 + 描边；叠加地面阴影椭圆、
侧窗 DLO（含 B 柱分隔线）、腰带虚线。

### 2.4 分层比例按车型（修缺陷 4，参考 SISA 实测地标）

| 车型 | hood | belt | trunk |
|---|---|---|---|
| sedan | 0.60 | 0.74 | 0.66 |
| **suv** | **0.66** | **0.80** | **0.72** |
| coupe | 0.62 | 0.72 | 0.70 |
| sport | 0.66 | 0.72 | 0.72 |
| mpv | 0.52 | 0.76 | 0.74 |
| pickup | 0.60 | 0.78 | 0.80 |

SUV hood 取 0.66 逼近 SISA 实测 `hood_height_ratio ≈ 0.69`（参考车同为 SUV 形态）。

### 2.5 全链路钳位（修缺陷 5）

- `windshieldTopX ≤ rearX − tailReserve − 120mm`，且 ≥ hoodEnd + 120mm；
- `rearWindowBottomX ≤ rearX − tailReserve`；
- `roofLen` 保底 `max(400mm, maxRoof×0.25)` 且不超过可用顶长。

### 2.6 质量与性能

- 删除顶层 console.log（SISA 问题 A），并有测试守卫（见 §4）。
- 参数缺省一律 `??`（修缺陷 7）。
- 所有描边加 `vector-effect="non-scaling-stroke"`：线宽不随缩放变化，小尺寸面板仍清晰。
- 几何量全部 `computed` 缓存，仅依赖变化时重算，无逐帧开销。

## 3. SISA 共享成果对接（`src/config/sisaReference.js`）

### 3.1 数据流

```
shared_reference/SISA_REVERSE_REFERENCE_PACK.json   （SISA 交付，85KB）
        └─ python 提取曲线/地标/元数据
           └─ src/config/sisaReference.js            （平台消费层，内嵌数组）
                ├─ SISA_X_NORM / SISA_Z_TOP_NORM / SISA_Y_HALF_NORM（200 点）
                ├─ SISA_LANDMARKS（15 项地标）
                ├─ SISA_META（坐标系/来源/质量）
                └─ toPlatformX() / sampleTopNorm() / evalTopRMSE() / referenceTopOverlay()
```

> 边界：依《SISA 资产分类与保密声明》第三条，集成的是**逆向测量的客观几何结果**
> （曲线、地标、质量指标），不含 SISA 算法实现。`shared_reference/` 目录本身保持
> 工作区参考件，不入库；平台侧以内嵌生成文件为准（文件头注明生成来源与时间）。

### 3.2 坐标映射（README §2 约定）

| 参考包 | 平台 |
|---|---|
| X：车长，车头 = 0 | x ∈ [−L/2, +L/2]，`toPlatformX(xNorm, L) = xNorm·L − L/2` |
| Z：车高，**地面 = 0** | 渲染地面线即 z=0（本次重构落实） |
| 归一化 x ∈ [0,1] | 拉伸到任意车长做跨尺寸比较（README §3） |

### 3.3 渲染侧能力

1. **SISA 真车参考线叠加**：2D 渲染卡片标题右侧「SISA 参考」按钮开关。
   开启后绘制参考车顶廓线（黄色虚线，参考车拉伸到当前车长、同一比例尺），
   直观暴露车高比例与顶线形状差距。
2. **像真度 RMSE 量化**：按 README §4 方法，把当前车的顶廓线按 100 点采样、
   归一化为 z/H，`evalTopRMSE()` 对真车 `z_top_norm` 求均方根误差，
   显示于图例（如 Cayenne ≈ 0.217——两台不同车的客观形状差距）。
3. **ground_alignment / height_ratio 落地**：车轮触地、车底 = 离地间隙（§2.2）；
   SUV 分层比例校正（§2.4）。
4. **后续扩展预留**：`sections[]`（24 截面 × 80 点）已随包留存，
   供 3D 断面校验/封闭化约束使用（本次未动 3D 管线，避免超范围改动）。

## 4. 验证记录

| 验证项 | 结果 |
|---|---|
| vitest 全量回归 | ✅ 150/150（car2d.test.js 从 8 组扩到 10 组 16 例） |
| 新增测试覆盖 | 车顶不越界（6 车型）· 轮胎触地 · 侧窗钳位 · Cayenne 实参回归 · SISA RMSE/映射 · console.log 守卫 |
| i18n 键对齐 | ✅ zh/en 各 1554 键，0 缺失（`node scripts/check_i18n.mjs`） |
| vite build | ✅ 通过 |
| 浏览器实测（Cayenne） | ✅ 闭合轮廓 + 触地车轮 + 完整车顶；SISA 开关出现黄色虚线与 RMSE 0.217；无 JS 报错；无横向溢出 |

## 5. 维护指南

- **调整 2D 渲染几何**：改 `Car2D.vue` 后必须同步 `tests/car2d.test.js` 中的
  `computeCar2D` 镜像函数（两处公式一一对应，测试内含注释提示）。
- **更新 SISA 参考包**：SISA 交付新 JSON 后，用提取脚本重新生成
  `src/config/sisaReference.js`（或手工替换三个曲线数组与 META），跑
  `npx vitest run tests/car2d.test.js` 确认 §9 组仍通过。
- **i18n**：本功能新增 4 键（`designer.sisaRef / toggleSisaRef / sisaLegend / sisaRmse`），
  新增键务必 zh/en 成对，可用 `node scripts/check_i18n.mjs` 校验。
- **像真度基线**：后续如接 NURBS 生成顶廓线，可直接调 `evalTopRMSE(myTopNorm)`
  把「像不像真车」纳入自动回归阈值（建议先记录当前车型的基线值）。

## 6. 变更文件清单

| 文件 | 变更 |
|---|---|
| `src/components/Car2D.vue` | 渲染管线重构（§2 全部）+ SISA 叠加 |
| `src/config/sisaReference.js` | 新增：SISA 参考包平台消费层 |
| `src/views/Designer.vue` | 「SISA 参考」开关 + 样式，两个 Car2D 实例透传 |
| `src/i18n.js` | 新增 4 键（zh/en） |
| `tests/car2d.test.js` | 适配新管线 + 新增 2 组测试 |
| `scripts/check_i18n.mjs` | 新增：i18n 键对齐校验工具 |
| `docs/SISA_2D_RENDER_INTEGRATION.md` | 本文档 |
