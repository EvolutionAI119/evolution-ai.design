# 附录 C 本平台事实基线（可核对数字表）

> 作者：量子剑客

本表是全书所有实证数字的单一出处。所有条目均可在本仓库公开文档中复核；引用本表数字时必须同时引用出处文件。路径相对仓库根目录。

---

## C.1 后端路由模块（19 个，151 个路由端点）

| 模块文件 | 路径前缀 | 端点数 | 职责 | 出处 |
|---|---|---:|---|---|
| project.py | `/api/v1/projects` | 5 | 项目 CRUD | `docs/ARCHITECTURE_DESIGN.md` §3.1 |
| model.py | `/api/v1/models` | 4 | 模型文件上传/查询/删除 | 同上 |
| build.py | `/api/v1/build` | 6 | 模型构建/重建/批量/缓存 | 同上 |
| car.py | `/api/v1/car` | 6 | 车身与部件生成、参数、导出 | 同上 |
| modify.py | `/api/v1/modify` | 15 | NURBS 曲面、参数、测量、历史 | 同上 |
| export.py | `/api/v1/export` | 4 | 模型导出与下载 | 同上 |
| variant.py | `/api/v1/variants` | 7 | 变体/版本/对比/回滚 | 同上 |
| workflow.py | `/api/v1/workflows` | 9 | 工作流与步骤、执行、训练评审 | 同上 |
| quality.py | `/api/v1`（quality/topology/data 等） | 9 | 质量检查、G2 检查、拓扑优化、数据交接、文件下载 | 同上 |
| training.py | `/api/v1/ai` | 15 | PyTorch 训练任务、样本批次、已训练模型、分析端点 | 同上 |
| ai.py | `/api/v1/ai` | 3 | NURBS 专家对话、Ollama 模型/健康 | 同上 |
| bayes.py | `/api/v1/bayes` | 7 | 贝叶斯优化会话全生命周期 | 同上 |
| texture.py | `/api/v1/texture` | 3 | 参数化纹理分析与应用 | 同上 |
| import_export.py | `/api/v1/import-export` | 11 | 导入→改参→导出全链路会话 | 同上 |
| llm_proxy.py | `/api/v1/llm` | 4 | 多 LLM 提供商统一代理 | 同上 |
| design_intent.py | `/api/v1/design-intent` | 3 | 自然语言设计意图解析与变体 | 同上 |
| analytics.py | `/api/v1/analytics` | 21 | 埋点统计、社区留言/引用线索、通知中心、数据导出 | 同上 |
| admin.py | `/api/v1/admin` | 7 | 管理后台：用户/登录记录/审计/错误日志 | 同上 |
| auth.py | `/api/v1/auth`、`/api/v1/api-keys` | 12 | 注册/登录/微信授权（9）、API Key 管理（3） | 同上 |
| **合计** | — | **151** | — | — |

**端点计数校验**：5+4+6+6+15+4+7+9+9+15+3+7+3+11+4+3+21+7+12 = **151**。
另有 `main.py` 2 个系统端点，合计 **153 个 HTTP 端点**（口径：151 路由 + 2 系统）。
HTTP 方法分布：GET 75 / POST 63 / PUT 4 / DELETE 9，合计 151，与逐模块行合计互校一致。
出处：`docs/ARCHITECTURE_DESIGN.md` §3.1（含图 3-1 图注）。

## C.2 ORM 数据表（17 张）

| # | 表名 | 模型类 | 领域分组 | 出处 |
|---:|---|---|---|---|
| 1 | projects | Project | 项目/流程/模型 | `docs/ARCHITECTURE_DESIGN.md` §5；`backend/app/database.py` |
| 2 | model_files | ModelFile | 项目/流程/模型 | 同上 |
| 3 | workflows | Workflow | 项目/流程/模型 | 同上 |
| 4 | workflow_steps | WorkflowStep | 项目/流程/模型 | 同上 |
| 5 | quality_reports | QualityReport | 质量/参数/变体 | 同上 |
| 6 | parameter_sets | ParameterSet | 质量/参数/变体 | 同上 |
| 7 | model_variants | ModelVariant | 质量/参数/变体 | 同上 |
| 8 | parameter_records | ParameterRecord | 质量/参数/变体 | 同上 |
| 9 | users | User | 用户/审计/密钥 | 同上 |
| 10 | login_records | LoginRecord | 用户/审计/密钥 | 同上 |
| 11 | admin_audit_logs | AdminAuditLog | 用户/审计/密钥 | 同上 |
| 12 | api_keys | ApiKey | 用户/审计/密钥 | 同上 |
| 13 | training_tasks | TrainingTask | 训练任务 | 同上 |
| 14 | page_views | PageView | 社区/通知/埋点 | 同上 |
| 15 | messages | Message | 社区/通知/埋点 | 同上 |
| 16 | external_references | ExternalReference | 社区/通知/埋点 | 同上 |
| 17 | notifications | Notification | 社区/通知/埋点 | 同上 |

**计数校验**：4 + 4 + 4 + 1 + 4 = **17 张**。关系链：Project 1—N ModelFile / Workflow / QualityReport；Workflow 1—N WorkflowStep；ModelFile 1—N ModelVariant（自引用 parent）；User 1—N ApiKey / LoginRecord / Notification。

## C.3 前端页面（12 个，Hash 路由）

| # | 路由 | 页面 | 核心职责 | 出处 |
|---:|---|---|---|---|
| 1 | `/` | Dashboard | 平台总览与功能入口 | `docs/ARCHITECTURE_DESIGN.md` §2 |
| 2 | `/designer` | Designer | AI 参数化设计器：参数面板 + 3D 实时渲染 | 同上 |
| 3 | `/copilot` | DesignCopilot | 设计副驾：意图解析 + 参数变体 | 同上 |
| 4 | `/projects` | Projects | 项目列表 | 同上 |
| 5 | `/projects/:id` | ProjectDetail | 项目详情与模型管理 | 同上 |
| 6 | `/deep-learning` | DeepLearning | 深度学习设计器：训练批次、风格/生成式设计 | 同上 |
| 7 | `/quality` | Quality | 质量检查与报告列表 | 同上 |
| 8 | `/deliver` | Deliver | 工程交付与数据交接 | 同上 |
| 9 | `/demo` | Demo | 功能演示（含 VTOL 飞行物理） | 同上 |
| 10 | `/help` | Help | 帮助中心：3D 知识图谱、模块手册、文档体系 | 同上 |
| 11 | `/community` | Community | 社区互动（留言、引用线索） | 同上 |
| 12 | `/contact` | Contact | 联系与反馈 | 同上 |

注：登录/账户页源码封存于 `src/views/Login.vue`、`src/views/Account.vue`（游客免登录，不计入 12 路由页）。

## C.4 自动化测试（955 例基线）

| 测试套件 | 用例数 | 结果 | 出处 |
|---|---:|---|---|
| algorithm_model pytest（tests/） | 205 | 全过 | `docs/ARCHITECTURE_DESIGN.md` §9 |
| backend pytest（tests/） | 388（1 跳过、2 xfailed） | 全过 | 同上 |
| frontend vitest | 362 | 全过 | 同上 |
| **合计** | **955+** | **全绿** | 同上 |

**计数校验**：205 + 388 + 362 = **955**。后端 1 跳过（需 `RUN_REAL_LLM=1`）与 2 预期失败（曲率管线已迁至 SISA，xfail 标注）单独列示，不混入"通过"。另有 `test_all.py` 一站式五模块自检，验证装配后可运行性，**不计入 955 求和**。分层占比：算法 21.5% / 后端 40.6% / 前端 37.9%；后端与前端合计 750 例（78.5%）。
历史口径（仅供回溯，不用于当前基线）：2026-09-27 快照为 489 例（算法 200 / 后端 178 / 前端 111，另有一站式自检 5 模块），出处 `docs/VALIDATION_REPORT_20260927.md` §1–§2。

## C.5 核心算法规格

| 指标 | 数值 | 出处 |
|---|---|---|
| CarParams 参数向量维度 | 22 维 | `docs/evolution_systems_thinking.md`（"22 维造型参数 × 176 顶点 × 33 曲面"）；`docs/PRODUCT_SPEC.md` §4.2 |
| 车身网格顶点数 | 176 顶点 | `docs/evolution_systems_thinking.md`（巨量性行） |
| NURBS 曲面片数 | 33 曲面 | 同上；`docs/AUDIT_REPORT_20260810.md`（"17 个组件、33 个曲面"） |
| 连续性等级 | G0 / G1 / G2（公差 0.1 mm / 1.0°） | `docs/ARCHITECTURE_DESIGN.md` §7 图例；`algorithm_model/surface_quality/` |
| 贝叶斯默认优化空间 | 14 维（归一化 [0,1]） | `docs/bayes_optimization.md` §3；`docs/EVOLUTION_AI_paper.md`（"14 维默认空间、GP、EI/UCB、会话"） |
| 高斯过程核 | 各向同性 RBF（ℓ=0.25） | `backend/app/bayes_optimizer.py`；第 8 章 |
| 采集函数 | EI / UCB | `docs/bayes_optimization.md` |
| 收敛阈值 | 0.01（双判据） | 第 8 章；`docs/bayes_optimization.md` |
| 训练网络 | 紧凑 MLP（隐藏层 48 单元） | `docs/EVOLUTION_AI_paper.md` |

## C.6 品牌知识库

| 指标 | 数值 | 出处 |
|---|---|---|
| 品牌数 | 5 品牌 | `backend/config/brand_design_knowledge.json`；`docs/ARCHITECTURE_DESIGN.md` §3.3；`docs/PRODUCT_SPEC.md` §5 |
| 车型数 | 19 车型 | 同上；`src/config/carPresets.js` |

知识库承载品牌/车型参数与设计语言元数据，支持语义查询与相似检索（`backend/app/brand_knowledge.py`）。

---

**总校验**：151（路由端点）+ 2（系统端点）= **153**；17 张表；12 个页面；955 例测试（205+388+362）。以上数字与 `docs/ARCHITECTURE_DESIGN.md`、`docs/api_reference.md`、`docs/PRODUCT_SPEC.md`、`docs/VALIDATION_REPORT_20260927.md`（历史口径）一致。
