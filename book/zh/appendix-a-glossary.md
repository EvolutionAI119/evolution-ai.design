# 附录 A 术语表（中英对照）

> 作者：量子剑客

本表收录全书出现的核心术语，按三组排序：**方法论术语**、**几何与算法术语**、**工程术语**。每条给出中文定义、英文术语与主要出处章节号（章号指 `zh/` 与 `en/` 同名章节）。

---

## A.1 方法论术语

| # | 中文术语 | 英文术语 | 中文定义 | 出处章节 |
|---:|---|---|---|---|
| 1 | AI 原生 | AI-native | 把不确定性作为一等公民纳入架构，而非在传统系统上"加 AI 功能"的开发范式 | 第 1 章 |
| 2 | 开放的复杂巨系统 | Open Complex Giant System (OCGS) | 子系统数量巨大、层次复杂、与环境持续交换物质能量信息，且人参与其中的系统；不能用还原论瀑布法治理 | 第 2 章 |
| 3 | 综合集成方法 | Metasynthesis | 钱学森提出的从定性到定量的方法论：专家体系、机器体系、知识体系三角闭环 | 第 3 章 |
| 4 | 从定性到定量 | From qualitative to quantitative | 先把专家经验结构化，再用数据与模型定量收敛，反复迭代的方法路线 | 第 3 章 |
| 5 | 人机结合以人为主 | Human–machine combination with humans in the lead | 机器提供候选与证据，人保留判断与责任的组织原则 | 第 3、15 章 |
| 6 | 专家体系 | Expert system (of experts) | 综合集成中承担经验、直觉与价值判断的人的组织形态 | 第 3、15 章 |
| 7 | 机器体系 | Machine system | 综合集成中承担计算、检索与枚举的机器与模型集合 | 第 3、15 章 |
| 8 | 知识体系 | Knowledge system | 综合集成中沉淀文档、数据与可复用知识的载体 | 第 3、16 章 |
| 9 | 总体设计部 | General Design Department | 以总体方案统摄各子系统、对人机分工负总责的组织单元 | 第 15 章 |
| 10 | 研讨厅 | Hall for Workshop of Metasynthetic Engineering (HWMSE) | 人机共同研讨、证据上墙、结论留痕的工作场域 | 第 15 章 |
| 11 | 薄壳编排 | Thin-shell orchestration | Web/接口层只做参数校验、鉴权与流程编排，不包含领域逻辑的架构原则 | 第 4 章 |
| 12 | 五层架构 | Five-layer architecture | 前端层、接口层、服务层、算法层、数据层的分层结构，层间只经契约通信 | 第 4 章 |
| 13 | 契约优先 | Contract-first | 端点、数据表与状态机先于实现冻结，字段 100% 对齐是硬约束 | 第 6 章 |
| 14 | 一个向量四种表达 | One vector, four representations | 同一 CarParams 参数向量同时驱动网格、NURBS、质量评估与导出，消除二次拟合 | 第 5 章 |
| 15 | 二次拟合 | Secondary fitting | 从网格反向拟合 NURBS 引入的误差来源，本平台以单一向量根除 | 第 5 章 |
| 16 | 序参量 | Order parameter | 协同学中支配系统宏观秩序的慢变量；抓住序参量即可治理整体 | 第 18 章 |
| 17 | 快变量 | Fast variable | 系统中允许试错、被序参量支配并随环境快速涨落的变量 | 第 18 章 |
| 18 | 深度演化 | Deep evolution | 让系统在运行中通过闭环反馈自我改进结构，而非靠外部重构升级 | 第 18 章 |
| 19 | 闭环反馈 | Closed-loop feedback | 输出结果被采集、评估并回灌到决策环节的机制，经验由此沉淀为结构 | 第 12、18 章 |
| 20 | 可验证交付 | Verifiable delivery | 每个结论都能回溯到一次真实执行与一组可复核证据的交付标准 | 第 11、12 章 |
| 21 | 文档漂移 | Documentation drift | 文档与源码不同源核对导致的失真；本平台以一致性审计禁止 | 第 16 章 |
| 22 | 文档即产品 | Documentation as product | 文档与代码同为交付物，享有同等评审与门禁地位 | 第 16 章 |
| 23 | 信任地基 | Trust foundation | 分层测试为 AI 原生项目提供的可依赖基座，而非覆盖率装饰 | 第 11 章 |
| 24 | 诚实降级 | Honest degradation | 可选能力缺失时返回 503 或显式降级，绝不伪装成功 | 第 9 章 |
| 25 | 语义接口 | Semantic interface | 把审美与品牌判断转化为可解释、可回归数值的接口层 | 第 10 章 |
| 26 | 品牌 DNA | Brand DNA | 品牌设计语言的参数化与规则化表达，可用于 On-Brand 判定 | 第 10 章 |
| 27 | 证据上墙 | Evidence on the wall | 研讨厅中将候选方案与实测数据公开呈现、供集体判读的工作方式 | 第 15 章 |
| 28 | 验收线 | Acceptance line | 团队统一的、不可退让的交付通过标准 | 第 17 章 |
| 29 | 六类角色 | Six roles | AI 原生团队的角色分工谱系：哲学守门人、方法工程师、系统架构师、契约管理员、质量工程师、验证负责人，各守一类文档（哲学、方法、架构、API、质量、验证） | 第 17 章 |
| 30 | 三种节奏 | Three rhythms | 轮次级（秒到小时，机器自闭环）、迭代级（周到双周，团队评审）、演化级（月到季度，阈值与基线修订）的分层节律，禁止串频 | 第 17 章 |

## A.2 几何与算法术语

| # | 中文术语 | 英文术语 | 中文定义 | 出处章节 |
|---:|---|---|---|---|
| 31 | NURBS | Non-Uniform Rational B-Splines | 非均匀有理 B 样条，汽车 A 级曲面的工业标准表达 | 第 5 章 |
| 32 | A 级曲面 | Class-A surface | 满足高光反射连续性要求的最高等级外观曲面 | 第 5 章 |
| 33 | G0 连续性 | G0 continuity | 位置连续：两曲面在边界处重合 | 第 5 章 |
| 34 | G1 连续性 | G1 continuity | 切向连续：边界处法线方向一致（公差 1.0°） | 第 5 章 |
| 35 | G2 连续性 | G2 continuity | 曲率连续：边界处曲率值一致（网格评估阈值 G2 < 2°；工程检查按 G0 0.1mm + G1 1.0° 逐缝判定，无独立 G2 公差） | 第 5 章 |
| 36 | 控制多边形 | Control polygon | 由控制顶点连成、牵引 NURBS 曲线形状的多边形 | 第 5 章 |
| 37 | 控制顶点 | Control point | 决定 B 样条/NURBS 形状的顶点，一般不落在曲面上 | 第 5 章 |
| 38 | 节点向量 | Knot vector | 定义 B 样条参数区间的非减序列，决定曲线分段 | 第 5 章 |
| 39 | 蒙皮 | Skinning / Lofting | 通过一族截面曲线放样生成曲面的方法 | 第 5 章 |
| 40 | 截面环 | Section ring | 车身横截面的闭合多边形环，是网格与 NURBS 的共同源头 | 第 5 章 |
| 41 | 曲率梳 | Curvature comb | 沿曲线按法向画出曲率比例线段的检测可视化 | 第 5 章 |
| 42 | 反射线 | Reflection line / Highlight line | 模拟条纹光源在曲面上的反射，用于肉眼判读曲面质量 | 第 5 章 |
| 43 | 斑马纹 | Zebra stripes | 反射线的条纹化实现，断口位置即连续性缺陷位置 | 第 5 章 |
| 44 | 扫掠 | Sweep | 截面沿导引线运动生成曲面的构造 | 第 5 章 |
| 45 | 圆角 | Fillet / Blend | 两曲面间的过渡曲面，本平台由 freeform 子包构造 | 第 5 章 |
| 46 | 光顺 | Fairing / Fairness optimization | 以降低曲率波动为目标迭代调整控制顶点的过程（本平台用模拟退火） | 第 5 章 |
| 47 | 模拟退火 | Simulated annealing | 以概率接受劣解跳出局部最优的随机优化算法 | 第 5 章 |
| 48 | 代理模型 | Surrogate model | 用廉价近似替代昂贵真值评估的模型，本平台用高斯过程 | 第 8 章 |
| 49 | 高斯过程 | Gaussian Process (GP) | 给出预测均值与方差的非参数贝叶斯回归，本平台取各向同性 RBF 核（ℓ=0.25） | 第 8 章 |
| 50 | RBF 核 | Radial Basis Function kernel（同义：平方指数核 squared-exponential, SE） | 平方指数核，样本间相似度随距离指数衰减；同名异称，读外部文献时勿当两种核 | 第 8 章 |
| 51 | 采集函数 | Acquisition function | 在代理模型上定义"下一个最值得评估的点"的标量函数 | 第 8 章 |
| 52 | 期望改进 | Expected Improvement (EI) | 采集函数之一：当前最优点上改进量的期望 | 第 8 章 |
| 53 | 置信上界 | Upper Confidence Bound (UCB) | 采集函数之一：均值与不确定性的加权和，平衡探索与利用 | 第 8 章 |
| 54 | 探索-利用平衡 | Exploration–exploitation trade-off | 在未知区域采样与在最优附近精修之间的取舍 | 第 8 章 |
| 55 | 贝叶斯优化 | Bayesian Optimization (BO) | 代理模型 + 采集函数的序列决策框架，用于昂贵黑箱优化 | 第 8 章 |
| 56 | 双判据收敛（规划） | Dual-criterion convergence (planned) | 规划中的收敛判据：当前优化循环以 EI 最小改进量 0.01（ei_xi）为停止参考，平台期由会话观察与人工裁决，自动双判据收敛为路线图项 | 第 8 章 |
| 57 | 热启动 | Warm start | 用既有观测初始化贝叶斯会话，避免从零探索 | 第 8 章 |
| 58 | 归一化造型向量 | Normalized styling vector | 映射到 [0,1] 区间的 14 维默认优化空间向量 | 第 8 章 |
| 59 | 语义评分 | Semantic score | CLIP/规则特征对审美维度的可解释打分，可回归可审计 | 第 10 章 |
| 60 | 多层感知机 | Multi-Layer Perceptron (MLP) | 本平台训练模块采用的紧凑全连接网络（隐藏层 48 单元） | 第 9 章 |
| 61 | 截面网格 | Section mesh | 由截面环阵列构成的车身网格（单侧 (49,25,3)） | 第 5 章 |
| 62 | 拓扑封闭 | Topology closure | 前脸/尾门封板、A/C 柱三角楔等七类开口的封闭关系约束 | 第 11 章 |

## A.3 工程术语

| # | 中文术语 | 英文术语 | 中文定义 | 出处章节 |
|---:|---|---|---|---|
| 63 | 服务端渲染 | Server-Side Rendering (SSR) | 在服务端生成首屏 HTML 的渲染方式（本平台为 SPA，未采用） | 第 7 章 |
| 64 | 单页应用 | Single-Page Application (SPA) | 前端路由接管页面切换的应用形态，本平台 12 页面即 SPA 路由 | 第 7 章 |
| 65 | 服务端请求伪造 | Server-Side Request Forgery (SSRF) | 诱导服务器访问内网地址的攻击；本平台以主机白名单与协议校验防护 | 第 9、13 章 |
| 66 | 内容安全策略 | Content Security Policy (CSP) | 限制脚本/样式来源的响应头，本平台由中间件统一注入 | 第 13 章 |
| 67 | 跨域资源共享 | Cross-Origin Resource Sharing (CORS) | 浏览器跨域访问机制；本平台生产环境显式白名单，禁止 `*`+credentials | 第 13 章 |
| 68 | JSON Web 令牌 | JSON Web Token (JWT) | 本平台登录态载体，由 `security.py` 签发与校验 | 第 13 章 |
| 69 | Fernet 对称加密 | Fernet symmetric encryption | 本平台用于 API Key 落库加密的对称加密方案 | 第 13 章 |
| 70 | 对象关系映射 | Object-Relational Mapping (ORM) | SQLAlchemy 模型类到数据表的映射，本平台共 17 张表 | 第 4、6 章 |
| 71 | 持续集成 | Continuous Integration (CI) | 每次变更自动运行测试与门禁的实践 | 第 14 章 |
| 72 | 持续交付/部署 | Continuous Delivery/Deployment (CD) | 构建产物可解释、部署拓扑可复现的发布实践 | 第 14 章 |
| 73 | 模块热替换 | Hot Module Replacement (HMR) | Vite 开发期的局部刷新能力，提升前端迭代速度 | 第 14 章 |
| 74 | 渐进式框架 | Progressive framework | Vue 3 的自我定位；本平台前端基于 Vue 3 + Vite | 第 7 章 |
| 75 | 状态管理 | State management (Pinia) | 前端唯一真相源；本平台用 Pinia 管理 auth/designer/project/ui | 第 7 章 |
| 76 | 依赖注入 | Dependency injection | FastAPI `Depends` 机制，`get_current_user` 等鉴权依赖由此注入 | 第 6、13 章 |
| 77 | 反向代理 | Reverse proxy | Nginx 将 `/api/v1` 转发至后端 8000 端口的部署结构 | 第 14 章 |
| 78 | HTTPS 隧道 | HTTPS tunnel | cpolar 为本地开发提供公网 HTTPS 域名的隧道服务 | 第 14 章 |
| 79 | 幂等 | Idempotence | 重复请求产生相同效果的性质；批量构建等端点按此设计 | 第 6 章 |
| 80 | 速率限制 | Rate limiting | 对 LLM 代理等昂贵端点的调用频控 | 第 13 章 |
| 81 | 审计日志 | Audit log | 管理操作与登录流水的留痕表（admin_audit_logs / login_records） | 第 12 章 |
| 82 | 埋点 | Tracking / Instrumentation | page_views 表承载的页面访问统计事件 | 第 12 章 |
| 83 | 降级兜底 | Graceful fallback | 后端不可用时前端 mock 兜底，PyTorch/Ollama 缺失时返回 503 | 第 9 章 |
| 84 | 失败快速 | Fail-fast | 生产环境 SECRET_KEY 未配置即启动失败的防护策略 | 第 13 章 |
| 85 | 游客模式 | Guest mode | 未登录请求以内置游客身份放行、管理端点仍需管理员的默认策略 | 第 13 章 |
| 86 | 端到端测试 | End-to-End test (E2E) | 验证完整用户路径的测试，本平台只保留少数主链 | 第 11 章 |
| 87 | 测试金字塔 | Test pyramid | 单元—集成—组件—E2E 的分层预算结构 | 第 11 章 |
| 88 | 预期失败 | Expected failure (xfail) | 已知失败原因、以 xfail 标注不计入通过的测试口径 | 第 11 章 |
| 89 | 一站式自检 | One-stop self-check (test_all.py) | 算法目录下验证装配后可运行性的五模块自检，不计入测试基线求和 | 第 11 章 |
| 90 | 知识图谱 | Knowledge graph | 帮助页以三维节点呈现 12 文档、4 层逻辑关系的可视化 | 第 16 章 |

---

**统计**：方法论 30 条 + 几何与算法 32 条 + 工程 28 条，合计 **90 条**。
