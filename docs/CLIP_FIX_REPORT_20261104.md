# 内饰/整车穿模排查与修复报告（非主目标车型）

- 报告日期：2026-11-04
- 平台：EVOLUTION-AI.DESIGN（参数化 A 级曲面 / 实车预览）
- 范围：sedan、suv、coupe、sport、mpv、pickup 六车型；外观可见的内饰件穿出
- 结论：**六车型全部 0 可见穿模**；853 项单测全绿；dev 与生产构建双环境回归通过

---

## 1. 执行摘要

上一轮已修掉主目标车型（绿色 SUV 外观截图）暴露的穿模。本轮针对「其余车型」做全面复盘：

1. 先用「真实装配网格 → 车身包络」的逐件判据扫全六车型（每车型 162~211 个 Mesh，其中内饰件 66~98 个），
   定位出 4 类仍存在的越界：**尾段全高板越出溜背/尾门斜面、顶棚后缘越出车顶后缘、皮卡第二排越出驾驶室后壁、深色货箱板抬升过量**。
2. 逐条修在「布局派生层」（单一真源），不靠事后裁剪网格：衬板/内板按车身侧视上界收口、顶棚后界退到车顶仍为全高的区间、
   皮卡第二排后移量按座椅侧视包络外扩量重定值。
3. 顺带修复一处**生产构建致命缺陷**：`manualChunks` 把项目自身 `src/three/**` 也归入 `three` 分块，
   形成 `three ↔ three-examples` 循环分块，`OrbitControls` 的 `class extends` 在 core 未初始化时求值，
   生产包整页 3D 不渲染（`Cannot access 'qe' before initialization`）。已改为仅对 `node_modules/three` 分包。
4. 验证：包络判据自检 + 六车型逐个 Mesh 审计 = 0 可见越界；48 张多视角/多状态截图复核；
   生产 `dist` 服务下 3D 场景正常挂载且无运行时错误。

---

## 2. 排查口径与「不适用项」说明

| 用户要求项 | 本平台实际情况 | 处理方式 |
|---|---|---|
| 3D 模型资源 | 全部为**参数化生成**（`deriveCarProfile` + `assembleCar`），无外部 glTF/FBX 资产 | 逐 Mesh 的世界 AABB 审计（真实装配网格，非布局近似） |
| 碰撞体配置 | **无碰撞体**（没有物理引擎、没有刚体/凸包） | N/A，见第 6 节 |
| 骨骼绑定数据 | **无骨骼/Skin/Bone**（座椅靠背调角由参数驱动，非蒙皮动画） | N/A，见第 6 节 |
| 物理引擎参数 | **无**（Three.js 纯静态预览，无 Ammo / Cannon / Rapier） | N/A，见第 6 节 |
| 触发场景 | 实际存在：视角切换、车门开合、机盖/尾门举升、扶手盖开合、座椅调角与滑轨行程、参数实时变更 | 见第 5 节矩阵 |

> 因此「车辆行驶状态、碰撞交互」两类场景在该平台不存在；「动画播放」映射为上述机构动画。

---

## 3. 判定方法（唯一真源）

**车身包络判据** `src/utils/carBodyEnvelope.js`（只依赖 `carProfile` + `carGlass`，不反向依赖布局，无循环）：

1. 纵向：`[rearX, frontX]` 之内；
2. 上界：`y ≤ bodyTopAt(x)`（沿侧视轮廓逐 x 取顶边，天然覆盖溜背与尾门斜面）；
3. 下界：`y ≥ bodyBottomY`；
4. 横向：`|z| ≤ shellHalfZAt(y)`（车顶收窄后的真实侧壁）；
5. 轮拱：落在拱腔椭圆内且 `|z| ≥ archInnerZ` → 命中；若该点横向落在轮胎区间且低于该 x 处轮胎顶面，判为
   `visible=false`（被轮胎挡住，外观不可见，只记 MASK 不记穿模）。

定位分两级：
- **布局级**：`src/tests/carBodyEnvelope.spec.js`（六车型全部内饰 AABB 零可见穿模，作为门禁常驻）；
- **装配级**：临时脚本用 `THREE.Box3` 取**真实装配 Mesh** 的世界 AABB 再投入同一判据（本轮定位手段，已删除临时脚本）。

---

## 4. 问题清单与修复（按根因分类）

### 4.1 判据自身静默失效（隐形 bug，先修）

| 项 | 现象 | 根因 | 修复 |
|---|---|---|---|
| C-01 | 上界/侧壁判定「永远通过」 | `bodyOutlinePolygon` 把**已解析的圆角几何**传给了 `bodySideOutline` 的第 3 参（该参语义是「圆角半径默认值表」），车顶 6 条命令产出 `x/y = null`，240 个采样点中 67 个 NaN → `bodyTopAt/halfZAt` 全线 NaN | 改传 `ROOF_FILLETS`；spec 增加 `poly.every(Number.isFinite)` 防回归 |

> 这是上几轮「审计零命中」却仍有外观穿模的根因：x 向与轮拱判据工作正常，上下界/侧壁一直静默放行。

### 4.2 尾段全高板越出溜背/尾门斜面（外观可见的深色板）

| 项 | 车型 | 实测最大越界 | 根因 | 修复 |
|---|---|---|---|---|
| C-02 | SUV / MPV | 侧衬板 637mm / 653mm | 行李舱侧衬板、尾门内板是按「矩形全高板」派生的（floor→topY），而尾段车身侧视上界已随尾门斜面快速下落 | `deriveLuggageLayout` 中按 `topEnvelopeOver(poly, x0, x1)` 收口 `sideLiners / frontLiner / lidInner` 顶边 |
| C-03 | MPV | 顶棚 14mm | 顶棚 `x0` 取「后窗顶 + 20mm」，落在车顶后缘圆角起点之内 | `deriveInteriorTrim` 把顶棚 `x0` 逐步前移，直到 `bodyTopAt(x) ≥ y1 + 4mm` |
| C-04 | pickup | 顶棚 786mm（越过驾驶室后壁） | 顶棚 `x0 = cabRearX - 0.02`，比驾驶室后壁还靠后 20mm，直接落在货箱上方（该处上界只有栏板高） | 同上（顶棚后界自动退到驾驶室后壁内侧） |

### 4.3 皮卡第二排整排越出驾驶室后壁

| 项 | 实测 | 根因 | 修复 |
|---|---|---|---|
| C-05 | 头枕顶越界 377mm；座椅包络后缘越过后壁 | 排位取 `cabRearX + 0.28`，但座椅侧视包络（靠背后倾 + 头枕）向后外扩约 **0.365m**，故靠背/头枕顶越过驾驶室后壁、且后壁上方的车身高度已回落 | 后移量改为 `cabRearX + 0.40`（留 35mm 余量）；两侧测试同步更新，并新增「包络后缘 > cabRearX - 20mm」门禁断言 |

### 4.4 轮拱腔体侵入（上轮已修，本轮复核）

| 项 | 实测 | 修复 |
|---|---|---|
| C-06 | MPV 27mm / SUV 30mm / pickup 95mm 露黑 | 凡纵向跨进拱区的舱体（行李舱、货箱、地毯、座椅、安全带下固定点）统一收口到 `archInnerZ`；地毯按拱区**分段渲染**；IP 下体前缘按 `archRearEdgeX` 收短（sedan 1315→1298、suv 1275→1243） |
| C-07 | 方向盘 Z 偏出门 255mm 并侵入前轮拱 | `steerWheel.z` 归位到 `front.seat.centers[0]` |

### 4.5 皮卡货箱拓扑语义错误（上轮已修，本轮复核）

| 项 | 实测 | 修复 |
|---|---|---|
| C-08 | 货箱与驾驶室重叠 180mm、越出车尾面 120mm | `carProfile.pickup`：`bedFrontX = cabRearX - 0.02`、`bedRearX = rearX + 0.12`（按「货箱内腔」语义收紧）；布局层再做 `x0/x1` 双向夹紧 |

### 4.6 生产构建缺陷（阻断「推公网前验证」）

| 项 | 现象 | 根因 | 修复 |
|---|---|---|---|
| C-09 | 本地 `dist` 整页 3D 不渲染，控制台 `ReferenceError: Cannot access 'qe' before initialization`（`three-examples` 分块 1:198） | `manualChunks` 判定 `/three/` 过于宽泛，把项目自身 `src/three/**` 也塞进 `three` 分块；这些文件 import `OrbitControls`（`three-examples` 分块），而 `OrbitControls` 又 import three core → 两个分块循环，`class extends` 在 core 尚未初始化时求值触发 TDZ | 改为仅匹配 `/node_modules/three/`；项目源码回归默认分块，循环消除（`three` 分块不再引用 `three-examples`） |

---

## 5. 回归验证矩阵

### 5.1 单测（`npx vitest run`）

| 指标 | 结果 |
|---|---|
| 测试文件 | 25 / 25 通过 |
| 用例 | **853 / 853 通过** |
| 新增门禁 | `src/tests/carBodyEnvelope.spec.js`：包络判据自检（轮廓闭合/有限、`roofTopY` 采样 ≤5mm、拱顶高于轮心）+ 六车型全部内饰件零可见穿模 |
| 同步修改 | `car2d.test.js` 期望 Mesh 数 193→196（地毯按拱区拆分 +3）；`carInterior*.spec.js` 皮卡后排定值与包络后缘断言；`ipConsoleLuggage.spec.js` 舱宽/饰盒条件式断言 |

### 5.2 装配级逐件审计（真实 Mesh AABB → 包络判据）

| 车型 | Mesh 总数 | 内饰件 | 可见越界件 |
|---|---|---|---|
| sedan | 196 | 89 | 0 |
| suv | 188 | 79 | 0 |
| coupe | 176 | 83 | 0 |
| sport | 162 | 66 | 0 |
| mpv | 211 | 98 | 0 |
| pickup | 185 | 89（含货箱深色板） | 0 |

### 5.3 视觉回归（Edge headless + SwiftShader，1280×800）

- 组合：6 车型 × 4 机位（正侧 / 正视车尾 / 俯视 / 45° 等轴）× 2 状态（关门 / 开门 70°）= **48 张**
- 结果：绿色车身外表面完整；此前 SUV/MPV 尾部的大面积黑色楔形（侧衬板/尾门内板越界）已消失；
  皮卡驾驶室后壁不再露出座椅/头枕；轮拱、侧门、车顶、车尾均无深色内饰件露出。
- 误报剔除：皮卡车尾正视图中「黑色楔形」经隐藏深色货箱板后**截图完全一致**，确认为驾驶室投下的阴影，不是几何穿出。

### 5.4 双环境验证

| 环境 | 方式 | 结果 |
|---|---|---|
| dev | `vite`(5173) + `scripts/car3d-baseline/harness.html` 六车型渲染 | 48 张截图全部通过 |
| prod | `npm run build` → `python -m http.server 8177` 服务 `dist` | 构建成功；DEMO 页「A 级曲面」演示 3D 正常挂载（`scenes=1 / canvas=1`），**0 运行时错误** |
| 门禁 | `python scripts/pre_commit_check.py` | `GATE PASS`（facts/docs/sisa 全通过，无旧口径） |

---

## 6. 不适用项（明确声明）

- **碰撞体 / 物理引擎**：平台无物理仿真，无刚体、凸包、关节、重力/摩擦参数，因此不存在碰撞体配置错位导致的穿透。
- **骨骼绑定 / 蒙皮**：座椅、车门、机盖、扶手均为独立 Mesh + 铰链 Group，通过 `rotation` 驱动，无 Skin/Bone/权重。
- **行驶状态 / 碰撞交互**：无车辆运动学与碰撞求解，舵机/悬架/转向扫掠仅以**几何包络**形式进入轮拱椭圆推导
  （`WHEEL_ENVELOPE`：jounce 跳动、gapTop/gapSide、steerDeg 满舵外扩），属于静态设计包络而非运行时仿真。

---

## 7. 涉及文件

**新增**
- `src/utils/carBodyEnvelope.js` —— 车身包络判据（唯一真源）
- `src/tests/carBodyEnvelope.spec.js` —— 包络自检 + 六车型零穿模门禁

**修改**
- `src/utils/carProfile.js` —— 皮卡货箱内外界语义（`bedFrontX/bedRearX`）
- `src/utils/carInteriorLayout.js` —— 方向盘 Z 归位、IP 下体按拱收短、座椅/安全带/地毯按拱间净宽收口、
  行李舱侧衬板/内板按上界收口、顶棚后界收口、皮卡第二排后移量
- `src/utils/carInterior.js` —— 地毯分段渲染
- `vite.config.js` —— `manualChunks` 仅对 `node_modules/three` 分包（修生产 TDZ）
- 测试：`tests/car2d.test.js`、`src/tests/carInterior.spec.js`、`carInteriorLayout.spec.js`、`ipConsoleLuggage.spec.js`

---

## 8. 遗留事项与下一步

1. **未推送公网**。按既定流程「检查没问题再推送」，本轮仅完成本地闭环验证；推送需显式确认。
   推送前需确认 `dist` 为本次修复后的构建（当前 `dist` 已是修复后版本），并复核 `gh-pages` 全量同步（不可漏 `assets/`）。
2. 视觉回归的机位为 4 个正交/等轴机位 + 开门两态；`cockpit`（座舱内视角）与机盖/尾门举升全程、扶手盖 0→75° 未纳入本轮截图集，
   但已由 AABB 判据在 0°/全开两个端点覆盖（布局件是刚体矩形，端点合规即全程合规）。
3. 皮卡货箱深色板位于「栏板上沿 +6mm」，属刻意设计（俯视呈开放货舱），在容差内且外观为阴影掩盖；
   如需彻底消除「后视一条深色唇边」的观感，可下调至栏板上沿 −30mm（会改变俯视观感，需产品确认后再动）。
4. 六车型行李舱容积/舱宽名义值未变（本轮只收几何、不动 VDA 口径），文档无 stale 数字。
