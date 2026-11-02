# 内饰造型设计统一标准与一致性校验规范

> 版本：v1.0 | 适用：EVOLUTION-AI.DESIGN 平台 6 车型 19 品牌车系 | 坐标系：X=车长（前+）、Y=车高、Z=车宽（左+）

---

## 0. 基准数据源

| 层级 | 文件 | 职责 |
|------|------|------|
| 车型拓扑 | `src/config/carPresets.js` → `carTypes` / `carTypeParams` | 6 车型几何/性能基线 |
| 品牌车型库 | `src/config/carPresets.js` → `brandsRaw` | 19 款认证车型参数覆盖 |
| 几何推导 | `src/utils/carProfile.js` → `deriveCarProfile` | 轮廓/比例/轮拱/坡面统一推导 |
| 座舱/玻璃 | `src/utils/carGlass.js` → `deriveCabinGlass` / `buildDloFrame` | 座舱边界/DLO/洞口统一推导 |
| 内饰扩展 | `src/utils/carInterior.js`（新建） | IP/CONSOLE/DOOR PANELS/SEATS 参数化生成 |

**原则**：所有内饰件必须消费 `deriveCarProfile` + `deriveCabinGlass` 的输出，禁止独立推导坐标。

---

## 1. 六车型内饰拓扑统一标准

### 1.1 车型内饰定位矩阵

| 车型 | 座舱定位 | IP 特征 | CONSOLE 特征 | DOOR PANELS 特征 | SEATS 特征 |
|------|---------|--------|-------------|-----------------|-----------|
| sedan | 标准三厢，均衡 | 对称翼展式，横向满铺 | 贯通式，前后分段 | 四门独立，软包上沿 | 5 座（2+3），H 点标准 |
| suv | 高坐姿，大空间 | 高耸直立，强调纵向 | 高耸宽厚，储物强化 | 高门板，防刮耐磨 | 5/7 座可选，H 点 +60mm |
| coupe | 低趴运动，2+2 | 低矮环抱，驾驶者导向 | 短促紧凑，后段弱化 | 无框门适配，轻薄 | 4 座（2+2），H 点 -20mm |
| sport | 极致运动，赛道化 | 极简碳纤维，信息聚焦 | 赛道式短中控台 | 轻量化，拉手替代扶手 | 2 座，桶椅，H 点 -40mm |
| mpv | 厢式最大化，商务 | 分层悬浮，空间感优先 | 前后贯通走廊式 | 侧滑门适配，宽大扶手 | 6/7 座（2+2+2/3），H 点 +80mm |
| pickup | 乘用化货用， rugged | 直立粗壮，功能主义 | 宽大储物，耐用材质 | 高防水沿，工具挂钩 | 5 座（2+3），H 点 +50mm |

### 1.2 统一结构逻辑

```
所有车型共享以下拓扑骨架：

carGroup
├── IP (instrument-panel)
│   ├── ip-upper (soft-touch)
│   ├── ip-lower (hard-plastic)
│   └── ip-slots [infotainment, cluster, airbag]
├── CONSOLE (center-console)
│   ├── console-front (storage/cupholder)
│   ├── console-armrest (hinge: console-lid)
│   └── console-rear (vent/usb)
├── DOOR-PANELS ×4 (or ×2 for coupe/sport)
│   ├── door-panel-front-left (hingeKey: fl)
│   ├── door-panel-front-right (hingeKey: fr)
│   ├── door-panel-rear-left (hingeKey: rl, sedan/suv/mpv/pickup)
│   └── door-panel-rear-right (hingeKey: rr, sedan/suv/mpv/pickup)
└── SEATS
    ├── seat-row-1 [driver, passenger]
    ├── seat-row-2 [left, mid, right] (sedan/suv/mpv/pickup)
    └── seat-row-3 [left, right] (mpv 7-seat, optional)
```

### 1.3 统一坐标锚点

| 锚点 | 定义 | 来源 |
|------|------|------|
| `ipTopY` | IP 上沿高度 | `cabin.dlo[0][1] - 0.015`（风挡底边内缩） |
| `ipBottomY` | IP 下沿高度 | `P.floorY + 0.08`（地板参考面上抬） |
| `consoleWidth` | 中控宽度 | `P.overall_width - 2 × (doorInnerGap + seatWidth)` |
| `seatHPoint(row)` | 第 N 排 H 点 | `P.seat_h_point_front` / `P.seat_h_point_rear` |
| `doorPanelZ(side)` | 门板内表面 Z | `±(P.overall_width/2 - doorThickness - 0.008)` |

---

## 2. 19 品牌车型差异化适配规范

### 2.1 品牌造型语言映射

| 品牌 | 造型语言 | 内饰材质倾向 | 特征元素 |
|------|---------|-------------|---------|
| Rolls-Royce | 极致奢华，手工定制 | 真皮 + 实木 + 金属镀铬 | 对开马车门、星光顶、钟表 |
| Bentley | 运动奢华，英伦 GT | 真皮 + 碳纤维 + 菱形缝线 | 旋转屏、牛眼出风口 |
| Bugatti | 超跑性能，技术裸露 | 碳纤维 + Alcantara + 钛合金 | 马蹄形中控、极简仪表 |
| Porsche | 功能主义，驾驶者导向 | 真皮 + 铝合金 + 织物 | 五连表、左侧点火 |
| Ferrari | 赛道激情，意大利美学 | 真皮 + 碳纤维 + 红色缝线 | 方向盘集成控制、跃马标志 |

### 2.2 车型参数覆盖规则

```javascript
// carPresets.js brandsRaw 中每款车型的 params 覆盖结构
{
  key: 'phantom',
  car_type: 'sedan',
  params: {
    // 几何覆盖（可选）
    overall_length: 5990,
    // 内饰材质覆盖（新增）
    interior: {
      material_preset: 'rolls-royce-luxury',
      ip_veneer: 'walnut',
      seat_stitch: 'contrast-piping'
    },
    // 特征元素开关
    features: {
      coach_doors: true,
      starlight_headliner: true
    }
  }
}
```

### 2.3 材质预设体系

| 预设 ID | 基础材质 | 适用品牌 | 参数包 |
|---------|---------|---------|--------|
| `standard` | 织物 + 硬塑 | 通用 | roughness 0.7/0.4 |
| `luxury` | 真皮 + 实木 | Rolls-Royce / Bentley | roughness 0.5, clearcoat 0.3 |
| `sport` | Alcantara + 碳纤维 | Bugatti / Porsche / Ferrari | roughness 0.9, metalness 0.1 |
| `executive` | Nappa 真皮 + 铝合金 | Bentley / 高配 sedan | roughness 0.55, metalness 0.3 |

---

## 3. 模型切换操作指引

### 3.1 车型切换流程（用户侧）

```
用户操作                    系统响应                              校验点
─────────────────────────────────────────────────────────────────────────
点击品牌车型卡片      →   selectModel(brandKey, modelKey)      →   品牌图片加载
                      →   setCarType(model.car_type)           →   车型宫格高亮
                      →   applyModelParams(model.params)       →   参数滑块同步
                      →   updateCar()                          →   Car3D 重建
                      →   updateInterior() (新增)              →   内饰件重建
```

### 3.2 车型切换流程（开发侧）

```javascript
// Designer.vue 或调用方
const switchModel = (brandKey, modelKey) => {
  const model = findModel(brandKey, modelKey)
  if (!model) return console.warn('Model not found')

  // 1. 车型拓扑切换（6 车型骨架）
  carType.value = model.car_type

  // 2. 参数应用（19 车型差异化）
  Object.assign(carParams.value, model.params)

  // 3. 内饰材质预设
  interiorPreset.value = model.params?.interior?.material_preset || 'standard'

  // 4. 特征元素开关
  featureFlags.value = model.params?.features || {}

  // 5. 触发重建（Car3D watch 自动响应）
  // updateCar() 由 watch(props.carParams) 驱动
}
```

### 3.3 6 车型切换对照表

| 从 ↓ 到 → | sedan | suv | coupe | sport | mpv | pickup |
|-----------|-------|-----|-------|-------|-----|--------|
| **sedan** | — | H 点 +60mm | H 点 -20mm | H 点 -40mm | 骨架重构 | 骨架重构 |
| **suv** | H 点 -60mm | — | 不兼容 | 不兼容 | 骨架重构 | 骨架重构 |
| **coupe** | H 点 +20mm | 不兼容 | — | 座椅减少 | 不兼容 | 不兼容 |
| **sport** | H 点 +40mm | 不兼容 | 座椅增加 | — | 不兼容 | 不兼容 |
| **mpv** | 骨架重构 | 骨架重构 | 不兼容 | 不兼容 | — | 骨架重构 |
| **pickup** | 骨架重构 | 骨架重构 | 不兼容 | 不兼容 | 骨架重构 | — |

> 「骨架重构」= 需重新执行 `deriveCarProfile` + `deriveCabinGlass` 全量推导；「H 点 ±Nmm」= 座椅局部调整；「不兼容」= 造型语言冲突，禁止直接切换。

---

## 4. 一致性校验清单

### 4.1 几何一致性

| # | 校验项 | 工具/方法 | 通过标准 |
|---|--------|----------|---------|
| G1 | IP 上沿与风挡底边间隙 | 场景查询 `ipTopY - (cabin.dlo[0][1] - 0.015)` | ≤ 1mm |
| G2 | 门板内表面与门洞间隙 | 场景查询 `doorPanelZ - doorInnerZ` | 8mm ± 0.5mm |
| G3 | 座椅 H 点与 `seat_h_point` 参数 | 场景查询 `seat.position.y` | ≤ 5mm |
| G4 | 中控宽度与座椅内缘间隙 | 场景查询 `consoleWidth vs seatInnerGap` | ≥ 20mm |
| G5 | 六车型拓扑骨架完整性 | 遍历 `carGroup.children` | 4 大类节点齐全 |

### 4.2 材质一致性

| # | 校验项 | 工具/方法 | 通过标准 |
|---|--------|----------|---------|
| M1 | 材质预设与品牌匹配 | 查询 `userData.materialVariant` | 与品牌映射表一致 |
| M2 | 软包/硬塑分区正确 | 查询 `mesh.material.roughness` | 软包 ≥ 0.7，硬塑 ≤ 0.5 |
| M3 | 金属饰条 metalness | 查询 `mesh.material.metalness` | ≥ 0.8 |
| M4 | 无 UV 依赖 | 查询 `geometry.attributes.uv` | 不存在或为空 |

### 4.3 渲染一致性

| # | 校验项 | 工具/方法 | 通过标准 |
|---|--------|----------|---------|
| R1 | renderOrder 层级 | 查询 `mesh.renderOrder` | IP/CONSOLE/DOOR/SEAT = 2，玻璃 = 3 |
| R2 | 阴影设置 | 查询 `castShadow` / `receiveShadow` | 内饰件 `castShadow: false` |
| R3 | 透明玻璃后内饰可见 | 截图验证 | 风挡后 IP 上表面可见 |
| R4 | 双实例（线框/预览）同步 | 场景查询 `__CAR3D_SCENES__` | 两实例内饰件数量一致 |

### 4.4 交互一致性

| # | 校验项 | 工具/方法 | 通过标准 |
|---|--------|----------|---------|
| I1 | 门板随门开合 | 触发 `toggleDoor()` | 门板与门片同步外摆 |
| I2 | 扶手箱盖开合 | 触发 `console-lid` 动画 | 缓动曲线与车门一致 |
| I3 | 座椅调节预留 | 查询 `userData.adjustable` | 存在且为 `true` |
| I4 | 车型切换后内饰重建 | 切换车型后遍历场景 | 内饰件数量/类型与车型匹配 |

### 4.5 六车型覆盖验证矩阵

| 校验项 | sedan | suv | coupe | sport | mpv | pickup |
|--------|-------|-----|-------|-------|-----|--------|
| G1-G5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| M1-M4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| R1-R4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| I1-I4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 品牌差异化（19 车型） | 抽样 3 款 | 抽样 3 款 | 抽样 3 款 | 抽样 3 款 | 抽样 3 款 | 抽样 3 款 |

---

## 5. 新增依赖与扩展点

### 5.1 必须新增的文件

| 文件 | 职责 |
|------|------|
| `src/utils/carInterior.js` | IP/CONSOLE/DOOR PANELS/SEATS 参数化生成 |
| `src/config/interiorPresets.js` | 材质预设 + 品牌映射表 |

### 5.2 必须修改的文件

| 文件 | 修改内容 |
|------|---------|
| `src/utils/carProfile.js` | 新增 `seat_rows` / `seat_h_point_*` / `interior` 参数 schema |
| `src/config/carPresets.js` | 19 车型 `params.interior` + `params.features` 扩展 |
| `src/components/Car3D.vue` | `createCar()` 中调用 `carInterior.js` 生成内饰件 |

### 5.3 校验自动化建议

```javascript
// tests/interiorConsistency.spec.js（新建）
describe('内饰一致性校验', () => {
  it('IP 上沿与风挡底边间隙 ≤ 1mm', () => { /* G1 */ })
  it('门板随门开合同步', () => { /* I1 */ })
  it('六车型拓扑骨架完整', () => { /* G5 */ })
  it('品牌材质预设正确映射', () => { /* M1 */ })
})
```

---

## 6. 实施路线图

| 阶段 | 内容 | 产出 |
|------|------|------|
| P0 | `carInterior.js` 骨架 + SEATS 一排两座 | 可渲染基础座椅 |
| P1 | IP 参数化生成 + 材质预设体系 | 完整 IP |
| P2 | DOOR PANELS + 车门铰链耦合 | 四门内饰板 |
| P3 | CONSOLE + 扶手箱动画 | 中控总成 |
| P4 | 19 车型品牌参数全覆盖 + 校验清单自动化 | 全系列一致性 |

---

*本标准与 `INTERIOR_PARTS_RENDERING_PLAN.md` 配套使用，前者定「做什么」，本规范定「怎么统一」。*
