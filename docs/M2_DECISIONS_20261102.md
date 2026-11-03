# M2 裁决记录（2026-11-02）

| 项 | 内容 |
|---|---|
| 版本 | v1.0 · 2026-11-02 |
| 范围 | M2 期间需拍板的体验/几何/可见性事项 |
| 关联 | [ASSET_MANIFEST.md](ASSET_MANIFEST.md)、[data_card.md](data_card.md)、[CAR3D_SPLIT_DESIGN.md](CAR3D_SPLIT_DESIGN.md) |
| 约束 | 本轮不改业务代码；公网发布冻结 |

---

## D-1 开门遮挡（R1）裁决

**结论：采用「门内板补面」，保持默认开门角 70°，不改铰链运动学。**

### 现状证据

| 位置 | 事实 |
|---|---|
| [Car3D.vue](../src/components/Car3D.vue#L1185-L1210) `mkDoor` | 门板是 `BoxGeometry(w, doorH, 0.012)` 的**单层薄板**，与车身共用车漆材质 `bodyMat`；门玻璃按铰链轴平移后挂入 `hinge` |
| [Car3D.vue](../src/components/Car3D.vue#L1663-L1665) 动画 | `openRad = door_open_angle ?? 70`，`hinge.rotation.y = sign * quintic(doorProgress) * openRad` |
| [Car3D.vue](../src/components/Car3D.vue#L585-L599) `attachDoorTrimToHinges` | 仅把 `door-trim-*` / `door-armrest-*` 重挂到铰链；门板内侧本身没有内饰面 |
| [Car3D.vue](../src/components/Car3D.vue#L1172-L1179) 分缝线 | 开门时 `doorProgress >= 0.02` 即隐藏，故剩余遮挡源不是缝条 |

即：开门后外摆的是一个**单层车身色薄板 + 门玻璃**，内侧无门内板、无内饰暗腔过渡；从 3/4 机位看，薄板正面与背面同色、同反照，读感上仍是「一块挡住座舱的板」。

### 三方案对比

| 方案 | 做法 | 收益 | 风险 / 代价 | 裁决 |
|---|---|---|---|---|
| A 默认角 70°→82° | 只改 `door_open_angle` 默认值 | 外摆更彻底，正视机位投影面积下降 | 改动全局默认参数；需重验门缝、把手、玻璃、内饰挂载与后视镜/翼子板间距；不同车型角部余量未验证 | 否决（暂不采用） |
| **B 门内板补面** | 门板内侧增加内饰面（深色内饰材质 + 门槛/扶手过渡），几何仍在 `hinge` 下 | 不动机运动学；把「薄板」读感变为「真实车门内侧」，同时遮住门洞暗腔；只增几何 | 增加约 2 个薄面/门；需控制显存与 draw call；需确认内侧不与座椅/扶手扫掠干涉 | **采用** |
| C 最小座舱 | 门洞内侧补一圈简化座舱内壁 | 视觉封闭感最强 | 几何量最大、性能与维护成本最高；与后续 Car3D 拆分冲突 | 否决（作为兜底备选） |

### 实施方案（排在 Car3D 拆分 P2 之后）

1. 在 `src/three/parts/doors.js`（拆分后）为每个门板增加：
   - 内侧饰板：与门板同尺寸、向内偏移 6mm、深色内饰材质（复用 `createInteriorTrim` 的材质档）；
   - 门槛/门洞边缘过渡条：沿门板下沿与门洞内缘，避免直视穿透；
   - 全部挂在既有 `hinge` 下，不新增坐标推导，复用 `doorH`、`doorBottom`、`doorTop`。
2. 不改 `door_open_angle` 默认值，不改 `attachDoorTrimToHinges` 的配对规则。

### 验收标准

| 项 | 判据 |
|---|---|
| 视觉 | 固定 3 机位（外 3/4、正侧、cockpit）开门截图：门洞内不再出现「单色薄板正对镜头」；暗腔被内饰面遮住 |
| 几何 | 内侧饰板与座椅、扶手、门玻璃在 0°→70° 全程无穿插（复用运动件扫掠检查） |
| 回归 | `npx vitest run` 全绿；mesh/三角面数增量 ≤ 8%；draw call 增量 ≤ 4/车 |
| 回退 | 单文件回滚 `doors.js` 即恢复现状 |

> 若 B 落地后仍被判定「有遮挡」，再评审 A（82°）；在此之前不改默认角。

---

## D-2 方向盘三辐改造复核结论（未提交，已恢复）

**结论：改动几何错误，按方案 A 失败分支处理——不提交，文件恢复到 HEAD，问题登记待修。**

### 待提交改动

```js
// src/utils/carInterior.js createSteeringWheel()
for (const a of [0, Math.PI * 2 / 3, -Math.PI * 2 / 3]) {
  const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.008, sw.r, 0.008), mat)
  spoke.rotation.z = a
  spoke.position.set(Math.sin(a) * sw.r / 2, Math.cos(a) * sw.r / 2, 0)   // 符号错误
  plane.add(spoke)
}
```

### 数学复核

`rotation.z = a` 把局部 `+Y` 映射为世界 `(-sin a, cos a)`。半长 `r/2` 的辐条要从轮毂 `(0,0)` 指向轮圈，中心必须放在该方向的 `r/2` 处，即 `(-sin a * r/2, cos a * r/2)`；现实现用了 `+sin a`，水平方向镜像：

| 辐条角 a | 期望端点（轮圈上） | 实际端点 |
|---|---|---|
| 0° | `(0, r)` | `(0, r)` ✓ |
| ±120° | `(∓0.866r, -0.5r)` | 两根都终止于 `(0, -0.5r)`，另一端在 `(±0.866r, 0)` |

后果：下侧两根辐条互相重叠、既不经过轮毂也不贴轮圈，三辐形态不成立。既有 `BoxGeometry(0.008, r*1.8, 0.008)` 的三根整条横杆（0/±60°）虽对称，但视觉上读作六辐，也不是目标形态。

**处置**：`git restore --source=HEAD -- src/utils/carInterior.js`；当前无该文件改动。现有单测只覆盖 `deriveInteriorLayout` 的 `steerWheel` 数值（[carInteriorLayout.spec.js](../src/tests/carInteriorLayout.spec.js#L136-L154)），不覆盖网格几何，故不存在被破坏的既有断言，但也没有防护。

### 后续修复（M3，与门板补面同批）

1. 公式改为 `spoke.position.set(-Math.sin(a) * sw.r / 2, Math.cos(a) * sw.r / 2, 0)`，辐条长 `sw.r`，角度 `[0, ±2π/3]`。
2. 抽出纯函数 `steeringSpokeTransforms(r, angles)` 返回 `{position, rotationZ, length}`，供渲染与测试共用。
3. 新增 `src/tests/carInteriorSteering.spec.js`，至少三条断言：
   - 每根辐条一端在轮毂半径 `≤ 0.02` 内；
   - 另一端到中心距离 `≈ r`（±0.01）；
   - 三根辐条角度互差 120°，且不出现两根端点重合。
4. 修复后重新生成 `docs/preview/ip-luggage-3d.js` 打包产物（当前 HEAD 内已含同一符号错误的嵌入副本，见下）。

> 说明：`docs/preview/ip-luggage-3d.js` 是打包产物，HEAD 版本内嵌了同样的 `+sin` 三辐代码（源出早前一次生成）。本轮对外观无其他新增验收，暂不单独改打包产物，待源码修复后统一重新生成。

---

## D-3 数据资产可见性

**结论：全部数据集默认 `internal`，不可对外公开。**

- 落点：[data_card.md](data_card.md)、[ASSET_MANIFEST.md](ASSET_MANIFEST.md) §4；说明文档不放 `data/`（该目录被 `.gitignore` 排除）。
- 禁止外发：D-01/02/06 训练权重，D-07/08/09 含用户上传 CAD 与历史导出。
- 对外材料（报告、截图、演示）不得出现样本行、绝对路径、用户文件名；确需外发走 [COLLABORATION_PROTOCOL.md](../COLLABORATION_PROTOCOL.md) 审查。

---

## D-4 公网复验/发布

**结论：M1-3 冻结。** 本轮不部署、不推送站点、不对外发链接；`deploy-gh-pages`（S-01）与发布闭环（W-06）保持「可用但冻结」，待用户明确授权后执行。

---

## 本轮新增验证

| 项 | 命令 | 结果 |
|---|---|---|
| 后端全量（对齐 `car_generator.py` 清理后基线） | `python -m pytest -q`（`backend/`） | 408 passed, 1 skipped, 2 xfailed（收集 411），81.87s |
| 提交门禁 | `python scripts/pre_commit_check.py` | GATE PASS（见提交前输出） |
| 两处非批次改动 | `git restore --source=HEAD` | `src/utils/carInterior.js` 已恢复；预览产物若被外部生成器改写，保持不提交 |
