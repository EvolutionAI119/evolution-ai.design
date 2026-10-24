# 附录 B 检查清单

> 作者：量子剑客

四类清单用于评审与交付前自检。每条格式：**检查项 —— 通过标准 —— 本仓库证据（文件/命令）**。所有证据路径相对仓库根目录。

---

## B.1 架构清单（Architecture Checklist）

- [ ] 五层分层无跨层调用 —— 前端只经 `/api/v1`，算法层不 import 路由 —— `docs/ARCHITECTURE_DESIGN.md` §2–§4；`backend/app/routes/*.py` 只编排不求值
- [ ] 薄壳编排成立 —— 路由函数只做校验、鉴权、编排，领域逻辑在 `backend/app/` 与 `algorithm_model/` —— `docs/ARCHITECTURE_DESIGN.md` §3.2
- [ ] 算法内核可独立安装与测试 —— `algorithm_model/` 不依赖 FastAPI，pytest 独立运行 —— `python -m pytest tests/ -q`（algorithm_model 目录下，205 例全过）
- [ ] 契约先于实现冻结 —— 端点、表结构、状态机三处有文档且与代码一致 —— `docs/api_reference.md`、`docs/ARCHITECTURE_DESIGN.md` §5
- [ ] 单一参数向量驱动四种表达 —— CarParams 22 维同时驱动网格/NURBS/质量/导出，无二次拟合 —— `algorithm_model/car_modeling/car_params.py`；`docs/PRODUCT_SPEC.md` §4.2
- [ ] 状态只有一个真相源 —— 前端用 Pinia（auth/designer/project/ui），页面不复述几何逻辑 —— `src/stores/`；`docs/ARCHITECTURE_DESIGN.md` §2
- [ ] 可选能力诚实降级 —— PyTorch/Ollama/Redis/CLIP 缺失时 503 或降级，不伪装成功 —— `docs/PRODUCT_SPEC.md` §6；`backend/app/clip_semantics.py`
- [ ] 17 张 ORM 表与文档一致 —— `database.py` 模型数与架构文档 §5 表格逐项对应 —— `backend/app/database.py`；`docs/ARCHITECTURE_DESIGN.md` §5
- [ ] 19 路由模块全部挂载 —— `main.py` include_router 覆盖全部模块 —— `backend/app/main.py`；`docs/ARCHITECTURE_DESIGN.md` §3.1
- [ ] LLM 统一代理与固定注册表 —— 提供商走 `llm_proxy.py`，不允许散点直连 —— `backend/app/routes/llm_proxy.py`；`docs/ARCHITECTURE_DESIGN.md` §3.1
- [ ] 配置集中管理 —— pydantic-settings 单一入口，生产 SECRET_KEY fail-fast —— `backend/app/config.py`

## B.2 交付清单（Delivery Checklist）

- [ ] 三层测试基线全绿 —— 算法 205 / 后端 388 / 前端 362，合计 955 例 —— `python -m pytest tests/ -q`；`python -m pytest -q`（backend）；`npx vitest run`
- [ ] 一站式自检通过 —— test_all.py 五模块全过（不计入 955 求和） —— `python test_all.py`（algorithm_model 目录下）
- [ ] 跳过与预期失败如实标注 —— 1 跳过（RUN_REAL_LLM）+ 2 xfail 单独列示 —— `docs/ARCHITECTURE_DESIGN.md` §9
- [ ] 前端构建产物可解释 —— `npm run build` 无告警，产物哈希命名 —— `package.json`；`backend/app/static/admin/assets/`
- [ ] 部署拓扑可复现 —— docker-compose 必填环境变量有校验 —— `deploy/docker-compose.yml`；`deploy/.env.example`
- [ ] 12 个前端页面路由可达 —— Hash 路由全表与文档一致 —— `docs/ARCHITECTURE_DESIGN.md` §2 路由表
- [ ] 19 模块 151 端点明细可逐条核对 —— api_reference 与 ARCHITECTURE_DESIGN §3.1 计数一致 —— `docs/api_reference.md`
- [ ] 导入→改参→导出全链路可走通 —— import_export 11 端点会话全流程冒烟通过 —— `docs/PRODUCT_SPEC.md` §4.7
- [ ] 贝叶斯会话全生命周期可用 —— create → suggest → observe → best/samples 闭环 —— `docs/bayes_optimization.md` §3；`backend/app/bayes_optimizer.py`
- [ ] 品牌知识库可查询 —— 5 品牌 19 车型元数据装载与语义检索可用 —— `backend/config/brand_design_knowledge.json`；`src/config/carPresets.js`
- [ ] 里程碑基线带日期与口径 —— 引用测试数字必须标注时点，不用旧快照替代当前基线 —— `docs/VALIDATION_REPORT_20260927.md`（历史 489 口径）；955 为 2026-10 后基线
- [ ] 发布说明与版本同步 —— README/CHANGELOG 与实际构建一致 —— 根 `README.md` 测试一节

## B.3 安全清单（Security Checklist）

- [ ] 生产 SECRET_KEY fail-fast —— 未配置即启动失败 —— `backend/app/config.py`
- [ ] 安全响应头统一注入 —— X-Content-Type-Options / X-Frame-Options / CSP / Referrer-Policy / Permissions-Policy / Cache-Control，去除 `server: uvicorn` —— `backend/app/main.py` 中间件；`docs/ARCHITECTURE_DESIGN.md` §7
- [ ] CORS 显式白名单 —— 生产禁止 ACAO `*` + credentials，含 ASGI 校正中间件 —— `backend/app/main.py`；`docs/ARCHITECTURE_DESIGN.md` §7
- [ ] SSRF 防护生效 —— LLM/纹理等出站请求主机白名单与协议校验 —— `backend/app/routes/llm_proxy.py`；第 9、13 章
- [ ] JWT 签发校验闭环 —— `get_current_user` / `get_optional_user` 依赖注入全覆盖受保护端点 —— `backend/app/security.py`
- [ ] API Key 加密落库 —— Fernet 加密，(user_id, provider) 唯一 —— `backend/app/database.py`（api_keys 表）；`docs/ARCHITECTURE_DESIGN.md` §5
- [ ] 游客模式默认拒绝敏感操作 —— 未登录放行只读，管理端点仍需管理员依赖 —— `docs/ARCHITECTURE_DESIGN.md` §2 访问控制
- [ ] 异常处理不泄露内部信息 —— StarletteHTTPException / RequestValidationError / 405 统一处理，错误响应补 CORS —— `backend/app/main.py`；`docs/ARCHITECTURE_DESIGN.md` §7
- [ ] 管理后台独立防护 —— `/admin/` 静态资产可访问、`unsafe-eval` 仅限后台文档 CSP —— 拓扑/后台 3 项测试（`docs/ARCHITECTURE_DESIGN.md` §9）
- [ ] 生产 GUEST_MODE 启动约束 —— 生产开启 GUEST_MODE 必须启动失败（有测试锁定） —— 游客模式 2 项测试（`docs/ARCHITECTURE_DESIGN.md` §9）
- [ ] 上传文件类型与尺寸校验 —— 模型上传走白名单与大小限制 —— `backend/app/routes/model.py`
- [ ] 密钥不入库明文、不入日志 —— 全库检索无明文 key、无日志泄露 —— `backend/app/security.py`；`backend/app/routes/auth.py`

## B.4 文档清单（Documentation Checklist）

- [ ] 关键数字全库一致 —— 19 模块 / 153 端点 / 17 表 / 12 页面 / 955 测试在 ARCHITECTURE_DESIGN、PRODUCT_SPEC、README 间一致 —— `docs/ARCHITECTURE_DESIGN.md` §3.1 §5 §9；`docs/PRODUCT_SPEC.md` §5
- [ ] 端点计数口径写明 —— 151 路由 + 2 系统 = 153，且 GET 75 / POST 63 / PUT 4 / DELETE 9 行列互校 —— `docs/ARCHITECTURE_DESIGN.md` §3.1
- [ ] 历史数字保留并标注 —— 2026-09-27 的 489 与历史 118 口径注明时点，不删改旧报告 —— `docs/VALIDATION_REPORT_20260927.md`
- [ ] 文档与源码同源核对 —— 无"文档漂移"：表格逐项可对应代码 —— `docs/ARCHITECTURE_DESIGN.md` §5 与 `backend/app/database.py`
- [ ] 图表有读图指引 —— 每图 caption 含"读图/读法结论" —— `docs/ARCHITECTURE_DESIGN.md` 各 `<figcaption>`
- [ ] 中英文档同名同序 —— `docs/` 与 `docs/en/` 章节一一对应，数字不删节 —— `docs/en/ARCHITECTURE_DESIGN.md`
- [ ] 帮助页知识图谱同步 —— 12 文档 4 层图谱与文档体系一致 —— `docs/PRODUCT_SPEC.md` §4.11；`src/views/Help.vue`
- [ ] 参考文献与延伸阅读可回溯 —— 外部文献入附录 D，仓库文档用相对路径 —— `book/zh/appendix-d-references.md`
- [ ] 术语统一 —— 首次出现中英对照，全文以附录 A 为准 —— `book/zh/appendix-a-glossary.md`
