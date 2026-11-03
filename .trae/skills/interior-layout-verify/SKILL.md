---
name: interior-layout-verify
description: 内饰布置 L1~L5 一键校验（2D 布置 / 横断面 / 门洞基准 / 人机工程 / 3D↔2D 对齐 / 运动件扫掠 / 座舱视觉）。当用户要求校验内饰、核对座椅与门洞/中控台间距、验证人机工程阈值、或改动 carInterior*/Car2D/Car3D 后需要回归时使用。不用于纯造型外观调整。
---

# 内饰布置校验（S-08）

把 [2D_LAYOUT_VERIFICATION.md](../../../docs/2D_LAYOUT_VERIFICATION.md) 的 L1~L5 检查固化为可重跑命令。任何阈值修改必须**同时**改文档与 `src/tests/carInteriorLayout.spec.js`，禁止只改测试放行。

## 1. 可重跑闸门（L1~L4 + 运动学）

在仓库根目录依次执行，任一失败即停止并按第 4 节归因：

```powershell
# L1~L4 + A~G 组：2D 合规、横断面、门洞基准、人机工程、3D↔2D 对齐
npx vitest run src/tests/carInteriorLayout.spec.js

# 运动件扫掠：滑轨全行程、调角器/遮阳板/扶手盖 75°
npx vitest run src/tests/carInteriorKinematics.spec.js

# 内饰网格与布局同源（座椅/中控/门板/方向盘三辐）
npx vitest run src/tests/carInterior.spec.js src/tests/carInteriorSteering.spec.js
```

判据：全部通过；测试输出里的车型覆盖必须是 6 车型（`sedan/suv/coupe/sport/mpv/pickup`），新增车型需同步阈值。

## 2. 全量回归与构建

```powershell
npx vitest run            # 全量前端
npx vite build            # 改动 Car2D / Car3D / CarSection2D 时必须
```

## 3. 座舱视觉（L5 的 3D 补充）

门板/内饰改动后，用固定 cockpit 机位复核门内板与 70° 开门遮挡：

```powershell
node scripts/car3d_baseline.mjs --out .tmp-car3d-check
node scripts/car3d_baseline_compare.mjs --cur .tmp-car3d-check
```

- 期望：非 cockpit 机位像素差 0.00%；`cockpit-door1` 能看到门内板深色饰面。
- 差异超限时保留 `*.diff.png` 作为证据，结论写「机位 / 像素差 / 归因」三要素。

## 4. 失败归因顺序

1. **布局数值断言失败**：先看是 `carInteriorLayout.js` 常量变更还是测试阈值过期——以 `docs/2D_LAYOUT_VERIFICATION.md` 的阈值表为准，不得反向迁就代码。
2. **3D 网格断言失败**：检查 `carInterior.js` 是否绕开 `deriveInteriorLayout` 自行推导坐标（禁止双份真源）。
3. **运动扫掠失败**：定位到具体车型 + 具体运动件 + 角度区间，按最小改动修，不改全局默认角。
4. **基线差异**：先按 `docs/CAR3D_BASELINE.md` 的归因流程处理，确认是预期几何变更后再整体重采集。

## 5. 汇报格式

用中文 Markdown：命令 → 真实通过数 → 失败项归因 → 残余风险；不写「目视差不多」。
