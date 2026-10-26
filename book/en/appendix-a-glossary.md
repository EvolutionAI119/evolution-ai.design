# Appendix A · Glossary (English–Chinese)

> Author: Quantum Swordsman

This glossary collects the core terms used throughout the book, ordered in three groups: **Methodology**, **Geometry & Algorithms**, and **Engineering**. Each entry gives the English term, the Chinese equivalent, a definition, and the chapter where it primarily appears (chapter numbers refer to the identically named files under `zh/` and `en/`).

---

## A.1 Methodology Terms

| # | English term | 中文术语 | Definition | Chapter |
|---:|---|---|---|---|
| 1 | AI-native | AI 原生 | A development paradigm that treats uncertainty as a first-class architectural citizen, rather than bolting AI features onto a conventional system | Ch. 1 |
| 2 | Open Complex Giant System (OCGS) | 开放的复杂巨系统 | A system with a vast number of hierarchically organized subsystems, continuous exchange with its environment, and humans in the loop; not governable by reductionist waterfall methods | Ch. 2 |
| 3 | Metasynthesis | 综合集成方法 | Qian Xuesen's qualitative-to-quantitative methodology: a triangular loop of expert system, machine system, and knowledge system | Ch. 3 |
| 4 | From qualitative to quantitative | 从定性到定量 | First structure expert experience, then converge quantitatively with data and models, iterating between the two | Ch. 3 |
| 5 | Human–machine combination with humans in the lead | 人机结合以人为主 | Machines supply candidates and evidence; humans retain judgment and accountability | Ch. 3, 15 |
| 6 | Expert system (of experts) | 专家体系 | The organizational form that carries experience, intuition, and value judgment within metasynthesis | Ch. 3, 15 |
| 7 | Machine system | 机器体系 | The ensemble of machines and models that carries computation, retrieval, and enumeration within metasynthesis | Ch. 3, 15 |
| 8 | Knowledge system | 知识体系 | The carrier that accumulates documents, data, and reusable knowledge within metasynthesis | Ch. 3, 16 |
| 9 | General Design Department | 总体设计部 | The organizational unit that governs subsystems through an overall plan and takes ultimate responsibility for human–machine division of labor | Ch. 15 |
| 10 | Hall for Workshop of Metasynthetic Engineering (HWMSE) | 研讨厅 | The working arena where humans and machines deliberate together, evidence is put on the wall, and conclusions leave an audit trail | Ch. 15 |
| 11 | Thin-shell orchestration | 薄壳编排 | The architectural principle that the web/interface layer only validates, authenticates, and orchestrates — never holds domain logic | Ch. 4 |
| 12 | Five-layer architecture | 五层架构 | Frontend, interface, service, algorithm, and data layers communicating only through contracts | Ch. 4 |
| 13 | Contract-first | 契约优先 | Endpoints, tables, and state machines are frozen before implementation; 100% field alignment is a hard constraint | Ch. 6 |
| 14 | One vector, four representations | 一个向量四种表达 | A single CarParams vector drives mesh, NURBS, quality, and export simultaneously, eliminating secondary fitting | Ch. 5 |
| 15 | Secondary fitting | 二次拟合 | The error source of reverse-fitting NURBS from meshes; eradicated on this platform by the single-vector design | Ch. 5 |
| 16 | Order parameter | 序参量 | In synergetics, the slow variable that enslaves the system's macroscopic order; govern it and you govern the whole | Ch. 18 |
| 17 | Fast variable | 快变量 | A variable that may trial-and-error freely, is enslaved by order parameters, and fluctuates quickly with the environment | Ch. 18 |
| 18 | Deep evolution | 深度演化 | Letting the system improve its own structure at runtime through closed-loop feedback, rather than via external rewrites | Ch. 18 |
| 19 | Closed-loop feedback | 闭环反馈 | A mechanism in which outputs are collected, evaluated, and fed back into decisions, sedimenting experience into structure | Ch. 12, 18 |
| 20 | Verifiable delivery | 可验证交付 | The delivery standard under which every conclusion traces back to a real execution and a set of auditable evidence | Ch. 11, 12 |
| 21 | Documentation drift | 文档漂移 | The distortion caused when documents are not checked against source; forbidden on this platform by consistency audits | Ch. 16 |
| 22 | Documentation as product | 文档即产品 | Documents are deliverables equal to code, with the same review and gating status | Ch. 16 |
| 23 | Trust foundation | 信任地基 | The dependable base that layered testing provides for AI-native projects — not a coverage ornament | Ch. 11 |
| 24 | Honest degradation | 诚实降级 | When an optional capability is absent, return 503 or degrade explicitly — never fake success | Ch. 9 |
| 25 | Semantic interface | 语义接口 | The interface layer that turns aesthetic and brand judgment into interpretable, regressable numbers | Ch. 10 |
| 26 | Brand DNA | 品牌 DNA | The parameterized and rule-based expression of a brand's design language, usable for On-Brand judgment | Ch. 10 |
| 27 | Evidence on the wall | 证据上墙 | The deliberation practice of publicly presenting candidates with measured data for collective reading | Ch. 15 |
| 28 | Acceptance line | 验收线 | The team's unified, non-negotiable pass bar for delivery | Ch. 17 |
| 29 | Six roles | 六类角色 | The role spectrum of an AI-native team: philosophy keeper, method engineer, chief architect, contract steward, quality engineer, validation lead — each guarding one class of document (philosophy, method, architecture, API, quality, validation) | Ch. 17 |
| 30 | Three rhythms | 三种节奏 | Layered cadence, never cross-frequency: round-level (seconds to hours, machine self-loop), iteration (one to two weeks, team review), evolution (months to quarters, threshold and baseline revision) | Ch. 17 |

## A.2 Geometry & Algorithm Terms

| # | English term | 中文术语 | Definition | Chapter |
|---:|---|---|---|---|
| 31 | NURBS (Non-Uniform Rational B-Splines) | 非均匀有理 B 样条 | The industrial standard representation for automotive Class-A surfaces | Ch. 5 |
| 32 | Class-A surface | A 级曲面 | The highest grade of visible surface, satisfying highlight reflection continuity requirements | Ch. 5 |
| 33 | G0 continuity | G0 连续性 | Positional continuity: two surfaces coincide at the boundary | Ch. 5 |
| 34 | G1 continuity | G1 连续性 | Tangent continuity: aligned normals at the boundary (tolerance 1.0°) | Ch. 5 |
| 35 | G2 continuity | G2 连续性 | Curvature continuity: equal curvature values at the boundary (mesh-evaluation threshold G2 < 2°; engineering checks judge seam by seam at G0 0.1 mm + G1 1.0°, with no separate G2 tolerance) | Ch. 5 |
| 36 | Control polygon | 控制多边形 | The polygon of control points that steers a NURBS curve's shape | Ch. 5 |
| 37 | Control point | 控制顶点 | A vertex that determines B-spline/NURBS shape and generally does not lie on the surface | Ch. 5 |
| 38 | Knot vector | 节点向量 | The non-decreasing parameter sequence defining a B-spline's segmentation | Ch. 5 |
| 39 | Skinning / Lofting | 蒙皮 | Generating a surface through a family of section curves | Ch. 5 |
| 40 | Section ring | 截面环 | The closed polygonal ring of a body cross-section — the common source of mesh and NURBS | Ch. 5 |
| 41 | Curvature comb | 曲率梳 | An inspection visualization that draws curvature-proportional segments along the normal | Ch. 5 |
| 42 | Reflection line / Highlight line | 反射线 | Simulated striped-light reflections on a surface for visual quality judgment | Ch. 5 |
| 43 | Zebra stripes | 斑马纹 | A striped implementation of reflection lines; breaks mark continuity defects | Ch. 5 |
| 44 | Sweep | 扫掠 | A construction in which a section moves along a guide curve to generate a surface | Ch. 5 |
| 45 | Fillet / Blend | 圆角 | A transition surface between two surfaces; built by the platform's freeform subpackage | Ch. 5 |
| 46 | Fairing / Fairness optimization | 光顺 | Iteratively adjusting control points to reduce curvature fluctuation (simulated annealing on this platform) | Ch. 5 |
| 47 | Simulated annealing | 模拟退火 | A stochastic optimizer that accepts worsening moves probabilistically to escape local optima | Ch. 5 |
| 48 | Surrogate model | 代理模型 | A cheap approximation standing in for expensive ground-truth evaluation; Gaussian Process on this platform | Ch. 8 |
| 49 | Gaussian Process (GP) | 高斯过程 | Non-parametric Bayesian regression yielding predictive mean and variance; isotropic RBF kernel (ℓ=0.25) here | Ch. 8 |
| 50 | RBF kernel | RBF 核（同义：平方指数核） | The squared-exponential (SE) kernel; similarity decays exponentially with distance. Same kernel, two names—do not mistake the aliases for two different kernels | Ch. 8 |
| 51 | Acquisition function | 采集函数 | A scalar function over the surrogate that scores "the next point most worth evaluating" | Ch. 8 |
| 52 | Expected Improvement (EI) | 期望改进 | An acquisition function: the expected improvement over the current best | Ch. 8 |
| 53 | Upper Confidence Bound (UCB) | 置信上界 | An acquisition function: a weighted sum of mean and uncertainty, balancing exploration and exploitation | Ch. 8 |
| 54 | Exploration–exploitation trade-off | 探索-利用平衡 | The trade-off between sampling unknown regions and refining near the incumbent best | Ch. 8 |
| 55 | Bayesian Optimization (BO) | 贝叶斯优化 | The surrogate-plus-acquisition sequential decision framework for expensive black-box optimization | Ch. 8 |
| 56 | Dual-criterion convergence (planned) | 双判据收敛（规划） | Planned criterion: score plateau cross-confirmed with the EI minimum improvement 0.01 (`ei_xi`); the current code has no `converged` field—the loop stops on the EI reference plus session observation and human judgment | Ch. 8 |
| 57 | Warm start | 热启动 | Initializing a Bayesian session with existing observations instead of exploring from scratch | Ch. 8 |
| 58 | Normalized styling vector | 归一化造型向量 | A vector mapped into [0,1] spanning the 14-dimensional default optimization space | Ch. 8 |
| 59 | Semantic score | 语义评分 | Interpretable, regressable, auditable scoring of aesthetic dimensions from CLIP/rule features | Ch. 10 |
| 60 | Multi-Layer Perceptron (MLP) | 多层感知机 | The compact fully connected network used by the training module (48 hidden units) | Ch. 9 |
| 61 | Section mesh | 截面网格 | The body mesh assembled from an array of section rings (single side (49,25,3)) | Ch. 5 |
| 62 | Topology closure | 拓扑封闭 | Closure constraints over seven opening classes: front/tailgate panels, A/C-pillar wedges, etc. | Ch. 11 |

## A.3 Engineering Terms

| # | English term | 中文术语 | Definition | Chapter |
|---:|---|---|---|---|
| 63 | Server-Side Rendering (SSR) | 服务端渲染 | Rendering the first HTML payload on the server (not used here — the platform is an SPA) | Ch. 7 |
| 64 | Single-Page Application (SPA) | 单页应用 | An application where frontend routing owns page transitions; the platform's 12 pages are SPA routes | Ch. 7 |
| 65 | Server-Side Request Forgery (SSRF) | 服务端请求伪造 | An attack that coerces the server into reaching internal addresses; mitigated by host whitelists and scheme checks | Ch. 9, 13 |
| 66 | Content Security Policy (CSP) | 内容安全策略 | A response header constraining script/style origins; injected uniformly by middleware | Ch. 13 |
| 67 | Cross-Origin Resource Sharing (CORS) | 跨域资源共享 | The browser cross-origin mechanism; production uses explicit whitelists, never `*` + credentials | Ch. 13 |
| 68 | JSON Web Token (JWT) | JSON Web 令牌 | The login-state carrier, issued and verified by `security.py` | Ch. 13 |
| 69 | Fernet symmetric encryption | Fernet 对称加密 | The symmetric scheme used to encrypt API keys at rest | Ch. 13 |
| 70 | Object-Relational Mapping (ORM) | 对象关系映射 | SQLAlchemy model classes mapped to tables — 17 tables on this platform | Ch. 4, 6 |
| 71 | Continuous Integration (CI) | 持续集成 | The practice of running tests and gates automatically on every change | Ch. 14 |
| 72 | Continuous Delivery/Deployment (CD) | 持续交付/部署 | Release practice with interpretable build artifacts and reproducible deployment topology | Ch. 14 |
| 73 | Hot Module Replacement (HMR) | 模块热替换 | Vite's dev-time partial reload, accelerating frontend iteration | Ch. 14 |
| 74 | Progressive framework | 渐进式框架 | Vue 3's self-description; the platform frontend is Vue 3 + Vite | Ch. 7 |
| 75 | State management (Pinia) | 状态管理 | The single source of truth on the frontend; stores: auth / designer / project / ui | Ch. 7 |
| 76 | Dependency injection | 依赖注入 | FastAPI's `Depends` mechanism, injecting auth dependencies such as `get_current_user` | Ch. 6, 13 |
| 77 | Reverse proxy | 反向代理 | The deployment structure in which Nginx forwards `/api/v1` to backend port 8000 | Ch. 14 |
| 78 | HTTPS tunnel | HTTPS 隧道 | The cpolar service giving local development a public HTTPS domain | Ch. 14 |
| 79 | Idempotence | 幂等 | The property that repeated requests have the same effect; batch build endpoints are designed this way | Ch. 6 |
| 80 | Rate limiting | 速率限制 | Call-frequency control on expensive endpoints such as the LLM proxy | Ch. 13 |
| 81 | Audit log | 审计日志 | The trail tables for admin operations and logins (admin_audit_logs / login_records) | Ch. 12 |
| 82 | Tracking / Instrumentation | 埋点 | Page-visit events carried by the page_views table | Ch. 12 |
| 83 | Graceful fallback | 降级兜底 | Frontend mock when the backend is down; 503 when PyTorch/Ollama is missing | Ch. 9 |
| 84 | Fail-fast | 失败快速 | The guard that refuses startup in production when SECRET_KEY is unset | Ch. 13 |
| 85 | Guest mode | 游客模式 | The default policy: unauthenticated requests pass as a built-in guest; admin endpoints still require admin | Ch. 13 |
| 86 | End-to-End test (E2E) | 端到端测试 | Tests over complete user paths; the platform keeps only a few mainline chains | Ch. 11 |
| 87 | Test pyramid | 测试金字塔 | The layered budget structure: unit — integration — component — E2E | Ch. 11 |
| 88 | Expected failure (xfail) | 预期失败 | A test with a known cause, marked xfail and excluded from the pass count | Ch. 11 |
| 89 | One-stop self-check (test_all.py) | 一站式自检 | The five-module assembly-runnability check under the algorithm directory; not counted in the test-baseline sum | Ch. 11 |
| 90 | Knowledge graph | 知识图谱 | The help page's 3D node visualization of 12 documents across 4 logical layers | Ch. 16 |

---

**Totals**: Methodology 30 + Geometry & Algorithms 32 + Engineering 28 = **90 entries**.
