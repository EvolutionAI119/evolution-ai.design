# 验证记录 · 2026-11-02（M1 收敛后）

| 项 | 内容 |
|---|---|
| 记录编号 | EVO-VAL-2026-1102 |
| 起始 HEAD | `0ad4ede2`（2026-10-28） |
| 安全兜底 | tag `backup-pre-m1-20261102`；工作区快照 `refs/backups/pre-m1-worktree` = `744e45fc` |
| 执行环境 | Windows / PowerShell 5；Node `v24.15.0`；npm `11.12.1`；Python `3.11.9`；Vite `5.4.21` |
| 约束 | 未使用 `reset --hard`、`clean -f`、force push；未改动业务逻辑 |

> 本记录是当前唯一事实源。任何文档引用测试/结构数字时必须同时给出「命令 + 日期 + 本文件」。
> 本轮实测前端为 **783 / 19 文件**，替代复盘时点的 771；差异来自内饰三视图测试随批次入库。

---

## 1. 提交批次（main，按依赖顺序）

| # | 提交 | 范围 | 一句话原因 |
|---|---|---|---|
| 1 | `49b665c4` | carGlass / carProfile / carInteriorLayout / carInteriorKinematics + 4 个 spec + 参数快照 | 先入库几何数据真源，组件层才有唯一取数口 |
| 2 | `0f5e1feb` | carInterior.js / car2dProjection.js / carInterior.spec.js | 补齐批次 1 测试依赖，保证干净检出可跑 |
| 3 | `ce663cd9` | Car2D.vue / CarSection2D.vue / Designer.vue | 侧视与 A-A 横断面同源接入，不另立坐标 |
| 4 | `4930e389` | Car3D.vue | 3D 内饰网格与玻璃 DLO 分缝收口 |
| 5 | `71988471` | 2D_LAYOUT_VERIFICATION + INTERIOR_* 规范/验收 HTML | 验收链与规范可追溯 |
| 6 | `e3f19b21` | IP/行李舱设计 HTML、xlsx、3D 预览、67 项同源断言 | 设计交付件与代码锁死 |
| 7 | `5074259a` | 2 个 skill + 预览脚本 + 技能预览页 | 高频返工点固化为可复用技能 |
| 8 | `c2f80a75` | 复盘 Markdown + 自包含 HTML | 结论先行的评审与复现入口 |
| 9 | 本记录提交 | README / ARCHITECTURE / book / agent / 验证记录 / verify_facts 修正 | 九项事实冲突收敛为单一基线 |

回滚方式：按 #9 → #1 逆序 `git revert <hash>`；每批文件边界独立，无跨批混杂。

---

## 2. 从零到跑起来（最短命令与实测结果）

```bash
# 1) 安装（本项目根目录；ESM，Node 18+）
npm install

# 2) 启动前端（mock fallback，可脱离后端）
npm run dev
#   实测：VITE v5.4.21 ready in 668 ms → http://127.0.0.1:5173/
#   冒烟：GET / → HTTP 200，响应体 1605 字节

# 3) 前端测试（唯一前端基线）
npx vitest run
#   实测：19 files passed / 783 tests passed，约 4.0 s

# 4) 构建校验
npm run build
#   实测：✓ built in 8.92 s
```

后端与算法（按需，不影响前端独立运行）：

```bash
cd backend && python -m pytest tests -q
#   实测：408 passed, 1 skipped, 2 xfailed in 104.96 s（收集 411）

cd algorithm_model && python -m pytest tests -q
#   实测：200 passed in 4.32 s
```

结构事实（单一来源）：

```bash
python scripts/verify_facts.py
#   实测：routes total=152 + main.py direct=2 → 154；tables=17；formats=20；
#         router paths=12；CarParams fields=22；DEFAULT_SPACE=14
```

**可跳过**：Redis、PostgreSQL、Docker、GPU、LLM Key、`data/`（≈2.7 GB 训练/导出资产）。前端在无后端时走 mock fallback，页面不黑屏。

---

## 3. 结果判定

| 层级 | 命令 | 结果 | 判定 |
|---|---|---|---|
| 安装 | `npm install` | `removed 2 packages in 536 ms`（依赖树已满足） | 通过 |
| 启动 | `npm run dev` + `GET /` | 668 ms ready；HTTP 200 / 1605 B | 通过 |
| 前端单测 | `npx vitest run` | 19 文件 / 783 通过 | 通过 |
| 构建 | `npm run build` | 8.92 s | 通过 |
| 后端 | `pytest tests -q` | 408 passed / 1 skipped / 2 xfailed（411 收集） | 通过 |
| 算法 | `pytest tests -q` | 200 passed | 通过 |
| 结构 | `verify_facts.py` | 19 / 154（152+2）/ 17 / 12 / 22 / 14 | 通过 |

已知非失败项：
- 后端 1 skipped：`test_design_intent.py` 需真实 SiliconFlow（`RUN_REAL_LLM=1` 才启用）。
- 后端 2 xfailed：Harness 曲率管线已迁 SISA，平台端不再适用。
- 算法 6 warnings：第三方库弃用提示，不影响断言。

---

## 4. 本轮事实冲突处置

| 冲突 | 处置 |
|---|---|
| 前端 416 / 710 / 123 vs 实测 | 统一为 **783 / 19 文件**；更新 README、2D_LAYOUT、agent、ARCHITECTURE、book |
| 后端 204 / 388 vs 411 | 统一为 **411 收集（408+1skip+2xfail）** |
| 算法 205 vs 200 | 统一为 **200** |
| 端点 153 / 118 vs 154 | 统一为 **154（152+2）**；ARCHITECTURE 模块表补 admin 8 |
| 路由模块 17 vs 19 | 统一为 **19** |
| ORM 表 13 vs 17 | 统一为 **17**；agent 补齐 4 张新表 |
| 贝叶斯空间 15 vs 14 | 代码复核为 **14**；修正 `verify_facts.py` 的字符串计数误判 |
| 导出格式 20 vs 8+JSON | 保留两种口径：**20 个格式标识 = 8 类几何 + JSON（含别名/组合）** |
| 前端路由 10 vs 12 | 统一为 **12 路由 / 15 视图文件** |

历史报告 `docs/VALIDATION_REPORT_20261025.md` 正文不回改，仅在顶部标注「已被本记录取代」。

---

## 5. 快速排查（本轮实际遇到/可复现）

| 症状 | 先查 | 处置 |
|---|---|---|
| `vitest` 找不到新测试 | `vitest.config.js` include 是否覆盖路径 | 本项目含 `tests/**` 与 `src/**`，新文件放 `src/tests/` |
| 测试文件互相依赖未入库 | 干净检出后跑该 spec | 本记录中批次 1→2 即为此类；提交时按依赖顺序 |
| PowerShell 输出乱码/空列 | 使用 `-f` 格式化或 `Select-Object -Last` | 避免直接打印大对象 |
| 后端收集数与执行数不一致 | 区分 collected / passed / skipped / xfailed | 以「收集数」写基线，以「passed+skipped+xfailed」核账 |
| 端口已有服务 | 先健康检查，不按端口杀进程 | 遵守 `COLLABORATION_PROTOCOL.md` 单一运行时 |
