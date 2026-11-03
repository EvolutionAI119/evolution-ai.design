# 内饰四类核心零部件渲染适配落地方案

> 版本：v1.0 | 适用对象：EVOLUTION-AI.DESIGN Car3D 渲染管线 | 坐标系约定：X=车长（前+）、Y=车高、Z=车宽（左+）

---

## 0. 现状基线

| 维度 | 当前状态 | 约束/机会 |
|------|---------|----------|
| 几何真源 | `utils/carProfile.js`（轮廓/比例）+ `utils/carGlass.js`（座舱/DLO/洞口） | 内饰件必须挂同一坐标系，禁止重复推导 |
| UV 体系 | **无 UV**（`splitBodyAperturesInterior` 重排后删除） | 全靠参数化 PBR 材质 + 几何细节，无贴图依赖 |
| 材质体系 | 车漆（clearcoat）、玻璃（transparent）、内饰洞壁（0x1b1d22） | 新增材质复用 `MeshStandardMaterial`/`MeshPhysicalMaterial` 分组思路 |
| 渲染层级 | 车身外壳 → 内饰洞壁 → 玻璃（`depthWrite: false`） | 内饰件需插入正确 renderOrder，避免 z-fighting |
| 阴影/光照 | PCFSoftShadowMap + RoomEnvironment PMREM + ACESFilmic | 内饰件不投外观阴影（`castShadow: false`），接收环境光 |
| 动画耦合 | `doorHinges` 驱动门开合；`carGroup` 随 VTOL 升降/转向 | 门板必须挂 hinge 子节点，其余挂 carGroup 静态节点 |

---

## 1. IP（仪表台 / Instrument Panel）

### 1.1 模型集成路径

```
utils/carInterior.js → createInstrumentPanel(P, cabin)
```

| 输入 | 来源 | 用途 |
|------|------|------|
| `P.cowlPoint` | `carProfile.deriveCarProfile` | IP 前缘定位（风挡底边内缩 15mm） |
| `P.aPillarRoot` | 同上 | IP 侧向包络边界 |
| `cabin.dlo[0][1]` | `carGlass.buildDloFrame` | IP 上沿高度（贴合风挡底边） |
| `P.floorY` / `P.overall_width` | `carProfile` | 下沿落地、横向满铺至门板内缘 |

**几何策略**：双曲率参数化曲面（上下两片蒙皮 + 侧向围合），上表面细分 32×16 段，下表面简化。出风口/饰条槽用几何凹陷（非贴图），深度 8~12mm。

### 1.2 材质适配规则

| 区域 | 材质类型 | 参数 | 说明 |
|------|---------|------|------|
| 上表面（受光面） | `MeshStandardMaterial` | `roughness: 0.7, metalness: 0.05` | 软触肤质，低反射 |
| 下裙/骨架 | `MeshStandardMaterial` | `roughness: 0.4, metalness: 0.1` | 硬塑，结构感 |
| 出风口/饰条槽 | `MeshStandardMaterial` | `roughness: 0.2, metalness: 0.9` | 金属镀层质感 |
| 中控屏位（预留） | `MeshPhysicalMaterial` | `roughness: 0.08, clearcoat: 1.0` | 玻璃质感，可替换挂载 |

### 1.3 渲染层级

| 属性 | 值 | 说明 |
|------|-----|------|
| 父节点 | `carGroup`（静态） | 随整车 VTOL/转向，不随门开合 |
| `renderOrder` | 2 | 高于车身外壳（1）、低于玻璃（3） |
| `castShadow` | `false` | 舱内件不投外观阴影 |
| `receiveShadow` | `true` | 接收环境光遮蔽 |
| `side` | `THREE.DoubleSide` | 从车外透过风挡可见，法线兜底 |

### 1.4 交互逻辑预留

```javascript
mesh.userData = {
  part: 'ip',
  zone: 'cockpit-front',
  slots: ['infotainment', 'cluster', 'passenger-airbag'],
  materialVariant: 'soft-touch' // 供 CMF 切换
}
```

---

## 2. CONSOLE（中控总成 / Center Console）

### 2.1 模型集成路径

```
utils/carInterior.js → createCenterConsole(P)
```

| 分段 | 范围 | 特征 |
|------|------|------|
| 前段 | IP 下沿 → 前排座椅前缘 | 杯架 + 储物格（几何开槽） |
| 中段 | 前排座椅之间 | 扶手箱（可开盖） |
| 后段 | 后排地板通道 | 后排出风口 + USB 面板 |

**宽度计算**：`P.overall_width - 2 × (doorPanelInnerGap + seatWidth)`，由座椅内缘间距反推。

### 2.2 材质适配规则

| 区域 | 材质 | 参数 |
|------|------|------|
| 主体硬塑 | `MeshStandardMaterial` | `roughness: 0.45, metalness: 0.08` |
| 扶手软包 | `MeshStandardMaterial` | `roughness: 0.75, metalness: 0.02` |
| 饰板（钢琴黑/木纹/金属） | `MeshStandardMaterial` | 三预设，`carPresets.js` 风格对象参数切换 |
| 杯架/充电板槽 | `MeshStandardMaterial` | `roughness: 0.3, metalness: 0.3` |

### 2.3 渲染层级

| 属性 | 值 |
|------|-----|
| 父节点 | `carGroup`（静态） |
| `renderOrder` | 2（与 IP 同层） |
| 与座椅间隙 | Z 向 ≥ 20mm，避免 z-fighting |

### 2.4 交互逻辑预留

```javascript
mesh.userData = {
  part: 'console',
  zones: ['front-storage', 'armrest', 'rear-vent'],
  hinge: 'console-lid',           // 扶手箱盖开合，复用 doorProgress 缓动模式
  slots: ['cupholder', 'wireless-charge', 'usb-panel'],
  materialVariant: 'piano-black'
}
```

---

## 3. DOOR PANELS（门板内饰）

### 3.1 模型集成路径

```
utils/carInterior.js → createDoorPanel(P, dl, side, hingeKey)
```

| 输入 | 来源 | 用途 |
|------|------|------|
| `dl.doorInnerBoundary` | `carGlass.deriveDoorLayout` | 门洞轮廓 |
| `hingeKey` | 同上 | 绑定铰链，随门开合 |
| `side` | 调用方 | 左/右镜像 |

**关键约束**：内饰板是**门片内侧的独立网格**，Z 向偏移门片厚度 + 8mm，**必须作为 `doorHinges[hingeKey]` 的子节点**，才能随开门动画外摆。

### 3.2 材质适配规则

| 区域 | 材质 | 参数 |
|------|------|------|
| 上沿软包（肘托） | `MeshStandardMaterial` | `roughness: 0.8, metalness: 0.0` |
| 中部本体 | `MeshStandardMaterial` | `roughness: 0.5, metalness: 0.05` |
| 下部防踢区 | `MeshStandardMaterial` | `roughness: 0.85, metalness: 0.0` |
| 内开手柄/按键区 | `MeshStandardMaterial` | `roughness: 0.25, metalness: 0.85` |
| 氛围灯槽 | `MeshBasicMaterial`（自发光） | `color: 0x00ff88, transparent: true, opacity: 0.6` |

### 3.3 渲染层级

| 属性 | 值 |
|------|-----|
| 父节点 | `doorHinges[hingeKey]`（动态） |
| `renderOrder` | 2 |
| 与门片关系 | 同层，Z 向偏移避免共面闪烁 |

### 3.4 交互逻辑预留

```javascript
mesh.userData = {
  part: 'door-panel',
  side: 'left' | 'right',
  hingeKey: dl.hingeKey,
  slots: ['window-switch', 'door-handle', 'ambient-light'],
  adjustable: false  // 门板本身不动，玻璃升降另算
}
```

---

## 4. SEATS（座椅组）

### 4.1 模型集成路径

```
utils/carInterior.js → createSeatRow(P, rowIndex)
```

| 排数 | 条件 | 配置 |
|------|------|------|
| 一排 | 恒有 | 2 座（驾驶位 + 副驾） |
| 二排 | `P.seat_rows >= 2` | 整体长椅或 4/6 分割 |
| 三排 | `P.seat_rows >= 3` | 2 座或整体（按车型） |

**新增参数需求**（`carProfile` schema 扩展）：

```javascript
seat_rows: 1 | 2 | 3           // 默认 1，SUV/MPV 可选 2/3
seat_h_point_front: 0.32       // H 点高度（m），驾驶位基准
seat_h_point_rear: 0.30        // 后排 H 点
seat_track_length: 0.25        // 滑轨行程（m）
```

**单座几何**：坐垫 + 靠背 + 头枕三件参数化组合，锚点由 `overall_length`、`h_point`、`ground_clearance` 反推。

### 4.2 材质适配规则

| 材质预设 | 参数 | 适用 |
|---------|------|------|
| 织物 | `roughness: 0.9, metalness: 0` | 基础车型 |
| 真皮 | `roughness: 0.5, metalness: 0.05, clearcoat: 0.3` | 豪华车型 |
| Alcantara | `roughness: 0.95, metalness: 0` | 运动车型 |

缝线细节：几何凹槽（深度 1mm，宽度 3mm），非贴图。

### 4.3 渲染层级

| 属性 | 值 |
|------|-----|
| 父节点 | `carGroup`（静态） |
| `renderOrder` | 2 |
| 驾驶位标记 | `userData.zone = 'driver'`，供车内视角预设定位 |

### 4.4 交互逻辑预留

```javascript
mesh.userData = {
  part: 'seat',
  row: 1 | 2 | 3,
  position: 'left' | 'right' | 'mid',
  adjustable: true,
  adjustments: ['slide', 'recline', 'height'],
  materialVariant: 'fabric' | 'leather' | 'alcantara'
}
```

---

## 5. 通用约束与验证清单

### 5.1 零改动保证

| 项目 | 状态 |
|------|------|
| 坐标系原点/轴向 | 不变（X=车长，Y=高，Z=宽） |
| 渲染分辨率/抗锯齿 | 不变（`renderer.setPixelRatio(Math.min(devicePixelRatio, 2))`） |
| 光照类型/位置/强度 | 不变（Ambient + Main + Fill + Rim） |
| 阴影设置 | 不变（PCFSoftShadowMap，内饰件 `castShadow: false`） |
| 相机参数 | 不变（PerspectiveCamera 45°，正交备用） |

### 5.2 性能预算

| 指标 | 预算 | 说明 |
|------|------|------|
| 新增面数 | ≤ 整车外壳 30% | 四组件合计 |
| Draw call 增量 | ≤ 8 个 | 按材质分组合批 |
| 内存增量 | ≤ 15MB | 几何 + 材质 |

### 5.3 落地顺序

```
SEATS（一排两座）→ IP → DOOR PANELS → CONSOLE
     ↑ 锚点最明确      ↑ 与风挡强绑定      ↑ 依赖车门 hinge      ↑ 填补空隙
```

### 5.4 潜在风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 无 UV 体系，复杂曲面精致度上限低 | IP 双曲率造型可能显生硬 | 增加几何细分（32×16 → 64×32），用几何凹陷替代贴图 |
| 门板挂错层级 | 内饰板不随门开合 | 强制 `userData.hingeKey` 校验，挂载时断言父节点为 hinge |
| `seat_rows` 参数未定义 | 三排座椅无法渲染 | 先在 `carProfile.js` 补 schema + 默认值，再实现几何 |
| 玻璃 `depthWrite: false` 导致内饰透显异常 | 从车外看内饰浮空 | 内饰件 `renderOrder: 2`，玻璃 `renderOrder: 3`，确保深度排序正确 |

---

## 6. 验收标准

- [ ] 四组件在 Designer 页双实例（线框/实时预览）中均正确渲染
- [ ] 开门动画中门板内饰随门片同步外摆，无滞后/错位
- [ ] 从车外透过风挡可见 IP 上表面，无深度穿插
- [ ] 435 项测试通过，无新增渲染错误
- [ ] 场景对象扫描：无孤立顶点、无未使用材质、无隐藏冗余节点
