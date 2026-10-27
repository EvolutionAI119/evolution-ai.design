# 平台验证报告 · 2026-10-25

> 统计日期：2026-10-25（北京时间）
> Commit SHA：`b42e51e4`（main 分支）
> 性质：当前事实基线的唯一事实源。今后正文、README、宣传材料的数字一律引用本报告。
> 历史快照（201 / 489 / 483 / 955）保留在各历史报告中标注时点，不回改。

---

## 一、三层测试基线（固定命令实跑）

| 层 | 命令 | 结果 |
|---|---|---|
| 算法 | `cd algorithm_model && python -m pytest tests/ -q` | **200 passed**（4.84s） |
| 后端 | `cd backend && python -m pytest tests/ -q` | **411 收集 = 408 passed + 1 skipped + 2 xfailed**（98.28s） |
| 前端 | `npx vitest run --reporter=dot` | **416 passed**（4.40s） |

合计约 **1027**（统计口径：200 + 411 + 416）。

**skip/xfail 口径（禁止静默跳过，逐条列示）**：
- `1 skipped`：需真实 LLM 环境的用例（`RUN_REAL_LLM=1` 时执行）。
- `2 xfailed`：`tests/test_car_generator_fixes.py::test_quality_is_measured_not_hardcoded` 与 `::test_g2_claim_logic_is_consistent`——Harness 曲率管线（iges_nurbs/nurbs_curvature）已迁移至 SISA，平台端无法 import，测试不再适用（预期失败，非回归）。

## 二、结构数（`scripts/verify_facts.py` 一次扫描）

| 事实 | 实测值 | 出处 |
|---|---|---|
| 路由模块 | **19** | `backend/app/routes/`（20 文件含 `__init__.py`） |
| HTTP 端点 | **152 路由 + 2 系统 = 154** | routes/*.py 装饰器计数；`main.py` `@app.get/@app.post` ×2（health、i18n/config） |
| 路由模块端点分布 | project 5 / model 4 / build 6 / car 6 / modify 15 / export 4 / variant 7 / workflow 9 / quality 9 / training 15 / ai 3 / bayes 7 / texture 3 / import_export 11 / llm_proxy 4 / design_intent 3 / analytics 21 / **admin 8** / auth 12 | 加总 152 ✓ |
| ORM 表 | **17** | `backend/app/database.py` `__tablename__` ×17 |
| 前端页面 | **12 条 Hash 路由** | `src/router.js`（`src/views/` 15 个 .vue；Login/Account/Admin 不计入） |
| 导出格式 | **8 种几何格式**（glb/gltf/stl/obj/iges/step/igs/stp）+ JSON | `routes/export.py` `SUPPORTED_FORMATS`；主推 mesh→STL/GLB、NURBS→STEP/IGES |
| 参数维度 | **22 维 CarParams** | `algorithm_model/car_modeling/car_params.py` dataclass 字段 |
| 贝叶斯默认空间 | **14 维**（22 维中 8 维冻结硬点） | `backend/app/bayes_optimizer.py` `DEFAULT_SPACE` L23–37 |
| 质检阈值（网格评估） | **G1 < 5°、G2 < 2°** | `surface_quality/continuity.py`、`grader.py` |
| 质检阈值（工程检查） | **G0 0.1 mm、G1 1.0°（G1 视觉 5.0°）**；G2 无独立公差 | `car_modeling/continuity_checker.py` L39–41 |
| 贝叶斯引擎 | RBF-GP ℓ=0.25、noise=1e-6；EI ξ=0.01、UCB κ=2.0；_N_INIT=2、_POOL_SIZE=4096 | `bayes_optimizer.py` |
| 收敛实现 | **无 `converged` 字段、无自动收敛判定**；0.01 仅为 EI 最小改进量（ei_xi） | `bayes_optimizer.py` / `routes/bayes.py` grep 复核 |
| 整车网格 | 176 顶点 / 316 面（文档口径） | 待 `examples/example_1_full_car.py` 复核后上宣传片 |
| NURBS 曲面 | 33 片（审计报告口径，代码无计数常量） | `docs/AUDIT_REPORT_20260810.md` |

## 三、复核命令

```bash
python scripts/verify_facts.py                      # 结构数一次输出
cd algorithm_model && python -m pytest tests/ -q    # 200 passed
cd backend && python -m pytest tests/ -q            # 408 passed, 1 skipped, 2 xfailed
npx vitest run --reporter=dot                       # 416 passed
```

**使用纪律**：任何材料引用本报告数字时标注「取自 VALIDATION_REPORT_20261025（SHA b42e51e4）」；新数字上线先更新本报告。
