# 发布前最终检查清单（2026-11-04 穿模修复批次）

> 用途：`gh-pages` 推送前的逐项核对表。**全部勾选后才允许推送公网**（既定流程：先本地验证，再发布）。
> 关联报告：[CLIP_FIX_REPORT_20261104.md](./CLIP_FIX_REPORT_20261104.md)

---

## 0. 前置条件（当前状态：未提交）

- [ ] 工作树改动已提交（本轮 12 改 5 新增，见 `git status`）
  - 已改：`src/utils/carProfile.js`、`carInteriorLayout.js`、`carInterior.js`、`src/three/materials.js`、`src/three/assembly/assembleCar.js`、`src/three/geometry/bodyShell.js`、`src/three/geometry/smoothing.js`、`vite.config.js`、4 个测试文件
  - 新增：`src/utils/carBodyEnvelope.js`、`src/tests/carBodyEnvelope.spec.js`、`src/tests/bodyShellAperture.spec.js`、`docs/CLIP_FIX_REPORT_20261104.md`
- [ ] 提交信息说明「为什么」：穿模四类根因 + 车漆黑楔形四层根因 + 生产分块 TDZ 修复，而非仅列文件
- [ ] `dist/` 为**本次修复后**的构建（当前 `dist/index.html` 时间戳晚于源码改动）
- [ ] 无临时脚本残留（`scripts/_tmp_*.mjs` 应为 0 个）

```powershell
git status --short
Get-ChildItem scripts -Filter "_tmp_*"
```

---

## 1. 代码与测试门禁

- [ ] 全量单测全绿：`861 / 861`，`26 / 26` 文件
- [ ] 穿模门禁 spec 在列（`src/tests/carBodyEnvelope.spec.js`），且含「轮廓采样点全部有限」断言
- [ ] 车漆黑楔形门禁 spec 在列（`src/tests/bodyShellAperture.spec.js`）：六车型内饰组 `sideFacing=0` / `upHorizontal=0`，`bodyMat` 为 `DoubleSide`
- [ ] 六车型零可见穿模断言在列（suv / mpv / pickup 为本次重点）
- [ ] 皮卡第二排「包络后缘 > cabRearX − 20mm」断言在列
- [ ] `python scripts/pre_commit_check.py` → `GATE PASS`（facts / docs / sisa 三项）

```powershell
npx vitest run --reporter=dot
python scripts/pre_commit_check.py
```

---

## 2. 构建与产物

- [ ] `npm run build` 成功，无 warning 级错误
- [ ] `dist/assets/` 中 `three` 分块**不再引用** `three-examples`（TDZ 回归点）
- [ ] `dist/assets/` 中 `three-examples` 分块存在且被页面正常加载
- [ ] `dist/index.html` 的 `assets` 引用全部存在（无 404）
- [ ] `docs/preview/ip-luggage-3d.js` 已决策：重建（含本次修复）或明确不发布该页
  - 现状：该包仍为旧构建，**不含**本轮衬板/顶棚/皮卡后排修复

```powershell
npm run build
$t = Get-Content dist/assets/three-*.js -Raw
"three 块引用 examples: " + ($t -match 'three-examples')
```

---

## 3. 视觉验收（本地双环境）

- [ ] dev（5173）+ `scripts/car3d-baseline/harness.html`：6 车型 × 正侧 / 车尾 / 俯视 / 45° × 开关门 = 48 张复核
- [ ] 生产（`dist` + 8177）DEMO → 「A 级曲面」演示：3D 正常挂载、无控制台报错
- [ ] 重点复查三个历史病灶：
  - [ ] SUV / MPV 尾部后侧围：无深色板穿出
  - [ ] 皮卡驾驶室后壁：无座椅/头枕露出，货箱前壁不越界
  - [ ] 六车型前后轮拱：无深色件露黑（MASK 以内不算穿模）
- [ ] 黑屏/白屏检查：首屏 3s 内出车，无 `ReferenceError`（尤其 `Cannot access ... before initialization`）
- [ ] 误报甄别：皮卡车尾正视的黑色楔形为**阴影**（隐藏货箱深色板后截图不变），不作为缺陷

---

## 4. 文档与口径

- [ ] `docs/CLIP_FIX_REPORT_20261104.md` 已入库，且「不适用项」（无物理引擎 / 无骨骼 / 无碰撞交互）写明
- [ ] 无 stale 数字（`pre_commit_check.py` 的 docs 项已覆盖）
- [ ] 若改动行李舱名义容积/舱宽 → 同步 `docs/*` 与帮助中心文案（本批次**未改**，应为 0 处）
- [ ] README / 文档导航无需新增条目（仅新增一份报告则不强制）

---

## 5. 部署执行（`gh-pages` 全量同步）

- [ ] 确认 `dist/` 与源码同步（构建后未再改源码）
- [ ] **全量**同步 `dist/` → `gh-pages` 工作树，含 `assets/`、`index.html`、`404.html`
  - 严禁只同步部分目录：漏 `assets/` 会直接黑屏
- [ ] 专利/发布守卫：仅在确认发布时设置 `EVOAI_ALLOW_PUSH=1`
- [ ] 提交并推送 `gh-pages`（非 `main`；不 force push）
- [ ] 记录发布版本：commit hash + 构建时间 + 本次修复要点

```powershell
$env:EVOAI_ALLOW_PUSH="1"
# 按 deploy-gh-pages 技能执行全量同步与推送（不可省略 assets/）
```

---

## 6. 发布后验证（公网）

- [ ] 打开 https://evolution-ai.design ，**强制刷新**（Ctrl+F5）避开旧缓存
- [ ] 首屏无黑屏/白屏；控制台 0 个 `pageerror`
- [ ] DEMO → 「A 级曲面」演示：3D 车辆正常渲染、可旋转
- [ ] 六车型逐一切换：外观无深色内饰件穿出（重点 SUV / MPV 尾部、pickup 后壁与轮拱）
- [ ] `assets/` 抽检：随机 3 个分块请求返回 200（非 404）
- [ ] 若公网仍见旧版本特征：CDN 缓存未失效 → 等待/刷新，必要时换 hash 文件名重新构建

---

## 7. 回滚预案

- [ ] 记录上一次稳定 `gh-pages` commit（用于回退）
- [ ] 回滚方式：`git revert` 该发布提交后重新全量同步推送（不做 `reset --hard` / force push）
- [ ] 回滚触发条件：公网黑屏、3D 不挂载、或出现新的外观穿模

---

## 8. 本批次已知遗留（不阻断发布，但需备案）

| 编号 | 遗留 | 影响 | 处置 |
|---|---|---|---|
| R-01 | `docs/preview/ip-luggage-3d.js` 为旧构建 | 该预览页不含本轮修复 | 发布前重建，或确认该页不在发布范围 |
| R-02 | 皮卡货箱深色板位于栏板上沿 +6mm | 后视有 1 条深色唇边（阴影下不明显） | 容差内合规；如需消除需产品确认后下调至 −30mm |
| R-03 | 门洞/机盖/扶手盖全程未纳入截图集 | 仅 0°/全开端点覆盖 | 刚体矩形端点合规即全程合规，可接受 |
