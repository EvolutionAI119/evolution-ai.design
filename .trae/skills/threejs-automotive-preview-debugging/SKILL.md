---
name: threejs-automotive-preview-debugging
description: 系统化调试与修复本仓库 Three.js 3D 实车预览（Car3D.vue）的渲染和造型问题，包括高光白带、环境反射异常、几何破面、零件不可见/比例失调、多视角截图验证。当遇到 3D 预览高光异常、腰线白带、后视镜/车轮/大灯渲染错误、材质反射突兀时使用；不用于 2D SVG 侧视图的纯坐标调试（走 algorithm-debugging）。
---

# Three.js 3D 实车预览调试技能训练手册

适用文件：`src/components/Car3D.vue`。核心教训：**先定位根因再改代码，禁止盲目调材质亮度掩盖问题**。

---

## 模块一：问题场景与根因库

### 1.1 症状 → 根因对照表

| 症状 | 真实根因 | 根因类型 |
|---|---|---|
| 尾盖/腰线突兀白带 | `RoomEnvironment` 发光板强度 17~100（+y 达 100），近水平面掠射角 Fresnel 整片反白 | 环境反射 |
| 车轮呈纯黑洞 | 实心圆柱轮胎端盖遮住轮辋 + 辐条错误绕 X 轴旋转 | 几何遮挡 |
| 前大灯不可见 | 按固定 frontX 放置，真实前鼻轮廓与 bevel 更靠前，灯组埋入实体 | 装配定位 |
| 灯组在翼子板转角露白斑 | 灯组横向位置太靠外 | 装配定位 |
| 后视镜镜面不可见 | 镜面缩进镜壳约 30mm，被壳体遮挡 | 几何遮挡 |
| 后视镜比例失真 | 200mm 镜壳 + 75mm 支架 → 六车型总宽 2.43~2.53m（应约 W+0.37m） | 比例失调 |
| greenhouse 收窄处三角破面 | 挤出收窄后法线未重算 | 法线断裂 |
| 腰线两侧高光断裂 | 门板与车身用不同材质实例 | 材质不一致 |
| Vue 警告 isFullscreen 未定义 | 模板绑定存在但 script 未声明 ref | 响应式缺失 |

### 1.2 根因分类判断标准

- **渲染类**（白带/高光异常）：表面平滑、法线连续但出现亮带 → 优先怀疑环境反射，不是几何问题。
- **几何类**（破面/遮挡）：射线命中最外层对象不是预期零件 → 零件被遮住或缩进实体内部。
- **装配类**（零件不可见/位置错）：用固定常量定位而非从真实轮廓采样 → 参数化车型下必然漂移。
- **比例类**（零件过大/过小）：横向总宽 = W + 2×(支架 + 镜壳深/2)，超 W+0.4m 即失真。

---

## 模块二：排查步骤（标准诊断流程）

### 流程 A：高光/白带异常（严格按顺序，禁止跳步）

1. **射线检测**：用与异常视角一致的正交相机发射线，只接受 `h.object.visible && h.object.isMesh`（过滤 GridHelper 误命中）。确认命中的是车身曲面还是独立零件。
2. **法线连续性检查**：输出命中点的面法线 + 三顶点法线按重心坐标插值。注意 `h.face.normal` 是几何面法线，≠ 最终着色法线，两者都要看。
3. **光照分离对照实验**（关键判据）：
   - `scene.environment = null` 保留直接光，截图 `xxx_direct_only.png` → **白带消失 = 环境反射主因**。
   - 保留 environment、方向光强度设 0，截图 `xxx_environment_only.png` → **白带仍在 = 确认环境反射**。
4. **判定结论**：两步对照都指向环境反射 → 走解决方案 3.1；法线插值不连续 → 走解决方案 3.4。

### 流程 B：零件不可见

1. 从对应视角射线检测，确认最外层命中对象是什么。
2. 检查零件相对包围体的偏移量（如镜面缩进量、轮辋轴向位置、灯组与前鼻轮廓的差值）。
3. 检查旋转轴是否与零件主轴一致（车轮辐条必须绕轮轴 Z，不是 X）。

### 流程 C：比例失调

1. 写数值脚本，导入 `carTypeParams` + `deriveCarProfile` + `deriveCabinGlass` + `buildDloFrame` + `shellHalfZAt`。
2. 对六车型（sedan/suv/coupe/sport/mpv/pickup）分别计算安装点半宽、零件外缘、总宽 delta。
3. **注意**：`mountY = hoodLineY + 0.03` 在默认六车型中位于 DLO 底边以下，`mountZ` 等于车身最大半宽，不能假设"此处已收窄"。

---

## 模块三：解决方案库（已验证参数）

### 3.1 环境反射白带 —— 定点缩放发光板

```js
const studio = new RoomEnvironment()
studio.traverse((object) => {
  if (object.isMesh && object.material?.isMeshBasicMaterial) {
    object.material.color.multiplyScalar(0.04)  // 只降发光板，保留室内漫反射
  }
})
```

验证效果：尾盖高光像素均值从 [222,240,226] 降至 [148,206,162]，由纯白转为车身色高光。**不要用** `scene.environmentIntensity` 全局降环境——整车会变暗。

### 3.2 后视镜造型 —— 圆角 + 渐缩 + 分层镜面

```js
// 支架：微锥形，长 25mm
new THREE.CylinderGeometry(0.017, 0.012, 0.025, 20)
// 镜壳：120×105×160mm，大圆角压平顶
const housingGeom = new RoundedBoxGeometry(0.12, 0.105, 0.16, 8, 0.032)
// 沿横向渐缩高度 ky = 1 - 0.12t²，法线按逆缩放归一化（不平面重算）
// 镜面与密封圈放镜壳后侧 -housingLength/2 - 0.0012，不缩进实体
// 安装半宽：shellHalfZAt(hoodLineY + 0.03, dloFrame, bodyExtentZ)
```

六车型验收：总宽 delta ≈ 0.37m，ratio ≈ 1.20。

### 3.3 车漆材质 —— 车身门板同一实例

```js
new THREE.MeshPhysicalMaterial({
  color: bodyColor, metalness: 0.42, roughness: 0.34,
  clearcoat: 0.35, clearcoatRoughness: 0.24, envMapIntensity: 0.85
})
// const doorMat = bodyMat  —— 消除腰线两侧高光断裂
```

### 3.4 收窄破面 —— 保硬边平滑法线

挤出后按 `taperK(y) = shellHalfZAt(y, dloFrame, bodyExtentZ) / bodyExtentZ` 收窄，再 `smoothNormalsKeepHardEdges(geom, 1e-4, 32)`（按位置焊顶点，仅平均夹角 <32° 的相邻面）。

### 3.5 车轮/大灯修复要点

- 车轮：轮辋盘、轮唇、中心盖、五辐条放朝外胎侧；辐条绕轮轴 Z 旋转；深枪灰轮辋 + 亮银辐条分层。
- 大灯：`noseXAt(y, halfRange)` 从真实前脸轮廓采样灯高处前缘，灯罩外露约 6mm；`hlZ = fit.wall - 0.27` 内移避免翼子板转角露白。

---

## 模块四：验证方法（每轮必做）

### 4.1 数值验证

六车型脚本输出 W、mountZ、outerZ、totalW、delta、ratio；判定标准：delta ∈ [0.35, 0.40]m 且左右对称、所有值有限。

### 4.2 视觉验证（CDP 截图标准流程）

1. headless Edge + `--enable-unsafe-swiftshader`，**每轮换新 `--user-data-dir` 后缀**（ES module 强缓存，旧 profile 会看到旧代码）。
2. 导航后若 `.car-3d-container` 数量为 0（路由懒加载），先点击菜单「AI 设计器」挂载组件，等待至数量为 2。
3. 操作对象始终是**第二个**容器（`window.__CAR3D_SCENES__[1]`）。
4. 截 rear/front/left/right/isometric/perspective 六视角 + 局部放大。
5. 局部放大用 PIL：截图为 2x deviceScaleFactor（3200×2200），crop 后 LANCZOS 放大。

### 4.3 验收清单

- [ ] 镜壳圆角连续，无整片平顶高光
- [ ] 镜面与密封圈可见、无穿插、无 z-fighting
- [ ] 镜座-支架-镜壳接触连续，无悬空
- [ ] 腰线垂直像素采样 RGB 无 >200 的突兀亮带
- [ ] 尾盖高光呈车身色而非纯白
- [ ] 六车型总宽 delta ∈ [0.35, 0.40]m
- [ ] `npm test`（vitest run）全绿

---

## 注意事项（红线与陷阱）

1. **不篡改法线掩盖高光**；不用 `environmentIntensity` 全局降环境。
2. `RoundedBoxGeometry` 继承 `BoxGeometry`，`geometry.type` 统计为 0 属正常，不代表未创建。
3. PowerShell 中 `npm run dev > log 2>&1` 重定向不可靠；判断服务状态直接轮询 `http://127.0.0.1:5173/`。
4. Vite 服务用 `Start-Process cmd '/c npm run dev'` 独立启动，验证完 `Stop-Process` 清理，避免僵尸进程占端口。
5. 材质/几何改动后，此前"全绿"的测试结果不代表当前状态——必须重跑 `npm test`。
6. 截图像素采样时先确认图片实际分辨率（2x DPR），避免按显示尺寸裁错区域。
