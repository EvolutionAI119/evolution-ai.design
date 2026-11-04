# Car3D 视觉基线（P0）

| 项 | 内容 |
|---|---|
| 版本 | P0-2026-11-03 |
| 用途 | Car3D 拆分（P1~P4）与开门/内饰改动的回归判据 |
| 产物 | [car3d-baseline/](preview/car3d-baseline/)：10 张 PNG + `manifest.json`（合计约 990 KB） |
| 采集脚本 | [car3d_baseline.mjs](../scripts/car3d_baseline.mjs)（puppeteer-core + 本机 Edge） |
| 比对脚本 | [car3d_baseline_compare.mjs](../scripts/car3d_baseline_compare.mjs)（pixelmatch + 指标容差） |

## 1. 固定条件

| 项 | 固定值 |
|---|---|
| 视口 / 设备像素比 | 1280×800 / 1 |
| 车型 / 车色 | `sedan` / `#4ade80` |
| 渲染 | Edge headless + SwiftShader ANGLE（无 GPU 依赖，跨机器可复现） |
| 自动旋转 | 关闭（否则 perspective 分镜角度随帧漂移） |
| 门开度 | 70°（`carParams.door_open_angle` 默认值），由调试钩子瞬时摆位，不依赖动画计时 |

| 分镜 | 机位 | 说明 |
|---|---|---|
| `front-door0/1` | 正交 `front`，dist=5 | 正对车头 |
| `left-door0/1` | 正交 `left`，dist=5 | 驾驶员侧纯侧视 |
| `iso45-door0/1` | 透视 `isometric`，rotation=(π/4, π/4)，dist=10 | 45° 等轴 |
| `interior-door0/1` | 透视 `perspective`，默认 rotation=(0.4, 0.8)，dist=8 | 内饰观察位（开门）；Car3D 无独立内饰机位，用该固定机位代理 |
| `cockpit-door0/1` | 座舱内，rotation=(0.02, π)，dist=1.0，pan=(0,0) | 车内看向右前门；D-1 门内板验收机位（非预设机位，经 `setCameraPose` 瞬时落位） |

## 2. 生成与比对

```powershell
# 生成（自动拉起 Vite dev server；结束自动关闭）
node scripts/car3d_baseline.mjs

# 增量重采集到临时目录后比对（不覆盖基线）
node scripts/car3d_baseline.mjs --out docs/preview/car3d-baseline/_current
node scripts/car3d_baseline_compare.mjs --cur docs/preview/car3d-baseline/_current
```

判定阈值（比对脚本默认值）：

| 指标 | 阈值 | 含义 |
|---|---|---|
| 像素差 | ≤ 1% | 1280×800 内差异像素占比，超限输出 `*.diff.png` |
| 三角面数 | ±0.5% | 拆分迁移不应改变几何总量 |
| bbox | ±5% | 车身包围盒不得漂移 |
| 网格数 | ±0.5% | 零件数量守恒 |

退出码 `0` 全通过、`1` 有差异、`2` 缺文件。差异图（`*.diff.png`）与 `_current/` 为临时产物，**不提交**。

可重复性：相机与门位姿均通过 `scene.userData.__car3d__` 的 `setViewInstant` / `setCameraPose` / `setDoor` 瞬时定位，不依赖帧率与缓动；连续两次采集比对 **10/10 通过、像素差 0.00%**（2026-11-03）。

## 3. 基线数值（sedan）

- 网格数 201，三角面 43268（10 个分镜一致；开门只旋转铰链，不改变拓扑）。
- 铰链峰值角：`door0 = 0`，`door1 = 1.222 rad`（70°）。
- 包围盒（以 `front-door0` 为例）：`min [-2.585, 0, -1.108]`，`max [2.464, 1.472, ...]`；开门分镜的 z 向包围盒会随门板外摆增大，属预期。

## 4. 体积控制

- 只保留 5 机位 × 2 门态共 10 张 1280×800 PNG，合计约 990 KB；`manifest.json` < 6 KB。
- 不提交 `_current/`、`*.diff.png`、浏览器临时 profile；比对产物随用随删（`.tmp-car3d-*/` 已加入 `.gitignore`）。
- 视觉有意变更（例如门内板补面）后，先复核差异归因，再整体重采集覆盖基线并同步更新本文件的数值。

## 5. 已知观察（基线已固定，勿在拆分中无意改变）

- 开门状态下，45° 机位可见门片玻璃「高于车顶轮廓」的细长片。**归因结论（2026-11-03，逐顶点投影 + 射线拾取）**：
  - 几何排除：门片玻璃世界 Y 恒为 `[1.001, 1.425] m`，开门/关门完全一致（铰链只绕竖直轴 `rotation.y`），车顶最高 `1.472 m`，玻璃顶边始终低于车顶 47 mm；
  - 45° 机位：同一屏幕列上，左后门片最高顶点投影比车身最高不透明顶点高 168.3 px（右后门片则低 134.8 px）→「高出车顶」是俯视透视下的视差，不是几何越顶；
  - cockpit 机位：`eye = (0, 1.02, -1.00)`，`near = 0.1`；画面中央大灰色块与右侧竖条经射线拾取为 `seatbelt-upper-r1-left`（距相机 0.18 m 的内饰件），非门片玻璃；近侧（左侧）门片确有 7~8 个顶点落在 0.075~0.080 m 的近裁剪面内，但位于相机背后、不出现在该帧画面；
  - 材质只放大观感：`glassMat` 为 `opacity 0.25 / depthWrite=false / DoubleSide`，无厚度薄片在掠射角读成硬边浅灰，但不构成根因。
  - 处置：保持 70° 开门角不动；若要消除 cockpit 里的「薄片」，属相机（机位/近裁面）问题，须单独裁决。
- 门内板补面仅在座舱侧可见：`cockpit-door1` 相对「隐藏门内板」状态像素贡献约 0.8%，其余 4 机位 0.00%（外表面仍为车漆，门内板被门板本体遮挡）。

## 6. 依赖

采集新增 devDependencies：`puppeteer-core`（驱动本机 Edge，不下载浏览器）、`pngjs` 与 `pixelmatch`（像素比对）。若本机无 Edge，脚本会提示改用人工采集；CI 环境需预装 Chromium 并改写 `executablePath`。
