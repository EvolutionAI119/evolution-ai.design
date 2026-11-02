# EVOLUTION-AI.DESIGN 全量复盘与复现手册

| 项 | 内容 |
|---|---|
| 报告编号 | EVO-RETRO-2026-1102 |
| 复盘日期 | 2026-11-02（北京时间） |
| 证据时点 | `main` HEAD `0ad4ede2`（2026-10-28）；工作区含未提交内饰批次 |
| 复盘方式 | git 全量日志 + 目录索引 + 文档抽样 + 关键命令实跑（未通读 2.7GB 运行数据） |
| 性质 | 工程复盘 + 方法论提炼 + 复现手册；不改业务代码 |

> 阅读顺序建议：先读第 1 节结论 → 第 6 节复现手册（要动手的人）→ 第 2/3 节（要接手的人）→ 第 7 节（要排期的人）。

---

## 1. 结论与关键发现（结论先行）

### 1.1 当前阶段

**平台已进入「v1.2 功能完备 + v1.3 内饰布置闭环」的交付前夜，但主线停在提交边界之外。**

| 判定 | 证据 |
|---|---|
| 主线代码停在 2026-10-28 | `git log` HEAD = `0ad4ede2`；此后无新提交 |
| 工作区有 32 项未提交变更（9 改 + 23 新增） | `git status --porcelain`：9 `M` + 23 `??`；diffstat 7 文件 +1425/−180 行 |
| 内饰布置已形成完整闭环 | [2D_LAYOUT_VERIFICATION.md](../../2D_LAYOUT_VERIFICATION.md) v1.3（63 项检查全通过）；`CarSection2D.vue`、`carInteriorLayout.js`、`carInteriorKinematics.js` 均为未跟踪新文件 |
| 前端测试基线已从 416 涨到 **771** | 本次实跑 `npx vitest run`：19 文件 / 771 通过 |
| 后端与算法基线维持 | `pytest --collect-only`：后端 **411**、算法 **200**；本次未全量执行 |
| 结构事实（脚本实跑） | 19 路由模块 / **154** 端点（152+2）/ 17 ORM 表 / 12 前端路由 / 22 维 CarParams |
| 本地服务当前未运行 | 审计时 `netstat` 无 5173 / 8000 / 4040 监听 |
| 公网最近发布 | `gh-pages` HEAD `99c91c70`（2026-10-28，修复黑屏 404）；本次未重新核验公网 |

### 1.2 最大瓶颈（按影响排序）

1. **价值最高的改动停留在未提交工作区**：内饰/玻璃/2D 三视图批次共 1425 行新增，一旦误清理或并行会话冲突，损失不可逆。这是当前第一风险，优先级高于任何新功能。
2. **文档事实漂移已成系统性**：同一仓库内至少存在 5 套互相冲突的数字口径（详见 §2.4），接手者无法判断哪份可信。
3. **跨仓库单一真源未闭合**：`carProfile.js` 的轮拱包络、玻璃分缝已同步到 SISA 一部分，但 `car_body.build_closed_shell`、`feature_lines.build_wheel_arch`、`dimension_plan` 拱半径仍在待同步清单（见 [project_memory](../../../.trae/documents/轮拱挖通_车门动画_角度把手参数化_20261022.md) 同批记录与 `wheel-arch-envelope-sync` 技能）。跨仓库口径漂移会抵消单仓库的全部同源努力。
4. **几何质量仍依赖人工视觉判定**：3D 折痕/遮挡/浮出类问题必须多机位截图 + 生产构建复验，单次验证成本高；这类问题占近期提交的大头（10-21 至 10-25 共 10+ 修复提交）。
5. **运行数据与代码不同源**：`data/` 2.7GB、训练权重 2.0GB 全在 `.gitignore` 外，换机复现需要重新生成或另行拷贝。

### 1.3 复现最短路径（详见 §6）

```powershell
# 1) 前端（唯一必需，内置 mock fallback，后端可选）
cd D:\API\Evolution-Ai.Design
npm install
npm run dev            # http://localhost:5173/#/designer

# 2) 后端（需要真实生成/训练/导出时）
cd backend
pip install -r requirements.txt
python start.py        # http://localhost:8000/docs

# 3) 验证（三个硬门禁）
npx vitest run                    # 当前 771 / 19 文件
cd backend; python -m pytest tests -q      # 411 收集
cd ../algorithm_model; python -m pytest tests -q   # 200 收集
```

**最小环境变量**只有 4 个（其余可留空）：`ENVIRONMENT=development`、`DEBUG=true`、`DATABASE_URL=sqlite:///./evolution_ai.db`、`SECRET_KEY=<任意开发值>`。Redis / PostgreSQL / Docker / GPU / LLM Key **全部可跳过**，缺失时按设计降级或 503，不会伪装成功。

---

## 2. 开发过程复盘与关键节点时间线

### 2.1 节奏总览（git 实测）

| 月份 | 提交数 | 阶段特征 |
|---|---:|---|
| 2026-08 | 2 | 仅工程骨架与测试基准，之后 38 天空窗 |
| 2026-09 | 23 | 基座日（09-27 单日 10+ 提交）→ 权限/安全/部署 |
| 2026-10 | 91 | 造型单一真源长线 + 飞行 + 品牌 DNA + 文档体系 |
| 2026-11-01 → 11-02 | 0（提交） | 内饰批次仅存在于工作区 |

全仓 **116 提交**、4 个 tag（`v1.0.1` / `v1.01` / `v1.02-stable` / `v1.03-nurbs-step`）。提交密度呈「基座日—长尾修复」形态：09-27 一天完成认证、LLM、训练、部署、贝叶斯、文档六件套；10 月则被 2D/3D 几何修复主导。

```text
2026-08-18   ● 骨架
2026-09-27   ●●●●●●●●●●  基座日（10+）
2026-09-29   ●●●  安全/部署
2026-10-01   ●●●  证据型功能
2026-10-07   ●●●●●  NURBS 车身
2026-10-11   ●●●●  比例同源 / 账号封存 / SEO
2026-10-16   ●●●●  反重力飞行
2026-10-21   ●●●●●●  轮拱/轮腔/玻璃拓扑
2026-10-22   ●●●●●  车门联动 / 品牌 DNA / 技能
2026-10-23   ●●●  五图原则 / 真门洞
2026-10-24   ●●●●●●  bevel / 玻璃写实
2026-10-25   ●●  门缝条 / 车门贴合
2026-10-27   ●●●  方法论图书 / 论文基线
2026-10-28   ●●●  技能固化 / 发布修复
2026-10-29→11-02  ○○○  内饰布置（未提交）
```

### 2.2 分阶段节点表

> 「产出物」列给项目内相对路径；提交号为 git 一手证据。括号内为对应文档章节。

#### 阶段 0｜工程奠基（2026-08-18）

| 时间 | 做了什么 | 产出物 | 关键决策 / 坑 |
|---|---|---|---|
| 08-18 | 补全骨架、完善 `.gitignore`、提交 19 款品牌车图测试基准 `dd3e689a` | [.gitignore](../../../.gitignore)、[public/brands](../../../public/brands)、[tests](../../../tests) | 决策：先立法（忽略规则 + 基准图）再写功能，避免运行产物污染仓库 |
| 08-18 | E2E 回归封装为可复用 CLI `58ec8694` | [tests/api.test.js](../../../tests/api.test.js) | 决策：回归必须任何会话一键复跑——后续「单一真源 + 全量回归」的起点 |
| 08-19 → 09-26 | **记录缺口**：38 天无提交 | — | 项目动机、SISA 早期形态不可从本仓库重建 |

#### 阶段 1｜后端与算法基座（2026-09-27）

| 时间 | 做了什么 | 产出物 | 决策 / 坑 |
|---|---|---|---|
| 09-27 | 认证 / 微信登录 / LLM 代理 / 训练后端 / 部署工程化 `43848a01` | [backend/app/routes/auth.py](../../../backend/app/routes/auth.py)、[backend/app/routes/llm_proxy.py](../../../backend/app/routes/llm_proxy.py)、[backend/app/routes/training.py](../../../backend/app/routes/training.py) | 一次性铺满 L3 骨架 |
| 09-27 | CAD 导入流程测试（STL/STEP/CATPart/Wire）`7a8a7c3a` `f3df5905` | [backend/app/cad_importer.py](../../../backend/app/cad_importer.py) | 坑：CATPart 兜底文案断言必须对齐实际输出（proprietary / not supported / Fallback） |
| 09-27 | 网页两处 500 + 生产 SECRET_KEY fail-fast `1b9f0310` | [backend/app/config.py](../../../backend/app/config.py) | 决策：生产环境用默认密钥直接拒绝启动 |
| 09-27 | 贝叶斯优化容器（GP + EI/UCB）`3196eabf` | [backend/app/bayes_optimizer.py](../../../backend/app/bayes_optimizer.py) | 坑：自检契约漂移、`run_full_pipeline` 从 box body 构造网格失败 |
| 09-27 | 全面复盘 + 架构/产品/API/论文 `ff351db3` `b24d4e46` | [docs/ARCHITECTURE_DESIGN.md](../../ARCHITECTURE_DESIGN.md)、[docs/PRODUCT_SPEC.md](../../PRODUCT_SPEC.md) | 决策：文档是产物，不是副产品 |
| 09-27 | 新增 `doc-code-audit` 技能 `1c2c1e8c` | [.trae/skills/doc-code-audit](../../../.trae/skills/doc-code-audit/SKILL.md) | 决策：「文档说错」按缺陷管理 |

#### 阶段 2｜权限、社区与「证据型」功能（2026-09-29 → 10-03）

| 时间 | 做了什么 | 产出物 | 决策 / 坑 |
|---|---|---|---|
| 09-29 | RBAC 四级权限 + 管理后台 + 登录审计 `ddc5043b` | [backend/app/routes/admin.py](../../../backend/app/routes/admin.py)、[backend/app/routes/auth.py](../../../backend/app/routes/auth.py) | 权限模型先于业务扩张 |
| 09-29 | AI 创意工具接真实端点 `94f13289` | [src/views/DeepLearning.vue](../../../src/views/DeepLearning.vue) | 占位端点必须替换为真实能力 |
| 10-01 | 可验证影响证据系统 `5106f049` | [docs/VALIDATION_REPORT_20261025.md](../../VALIDATION_REPORT_20261025.md) 的「证据」传统 | 决策：任何影响/性能声明必须可追溯 |
| 10-02 | AI 设计意图引擎 `fef68f19` | [backend/app/routes/design_intent.py](../../../backend/app/routes/design_intent.py)、[src/views/DesignCopilot.vue](../../../src/views/DesignCopilot.vue) | 一句话 → 整车方案 |
| 10-02 | 多工具协同协议 v1 `856c2651` | [COLLABORATION_PROTOCOL.md](../../../COLLABORATION_PROTOCOL.md) | 坑：两个 AI 工具按端口互杀 → 从此禁止按端口清理进程 |
| 10-02 | LLM 密钥隔离 + 密钥注册表 `72bcf6cc` | [backend/.env.example](../../../backend/.env.example)、`backend/.key-registry.json` | 每平台独立凭证，注册表不含明文 |

#### 阶段 3｜安全、部署与账号体系封存（2026-09-29 → 10-11）

| 时间 | 做了什么 | 产出物 | 决策 / 坑 |
|---|---|---|---|
| 09-29 | 限流 + DEBUG fail-fast + env 样板 `a35000de` | [backend/app/rate_limit.py](../../../backend/app/rate_limit.py) | 安全左移 |
| 09-29 | PostgreSQL + Alembic + Docker 非 root `0b0f971c` | [docker-compose.yml](../../../docker-compose.yml)、[deploy/docker-compose.yml](../../../deploy/docker-compose.yml) | 生产栈四服务：backend/postgres/redis/nginx |
| 10-01 | CNAME + `.nojekyll` 进 `public/` `274592ef` `d5ce5092` | [public](../../../public) | 坑：`_` 前缀目录会被 Jekyll 过滤 |
| 10-11 | Admin 移出公开前端 `c45d9ccc` | [vite.admin.config.js](../../../vite.admin.config.js) | 决策：管理代码不进公开产物 |
| 10-11 | 仅 `/admin` 放行 CSP `unsafe-eval` `864421d5` | [backend/app/main.py](../../../backend/app/main.py) | 坑：vue-i18n 编译被 CSP 拦截导致白屏 |
| 10-11 | **账号体系整体封存，全站游客** `6040bac4` | [src/router.js](../../../src/router.js) | 决策依据：cpolar 随机域名 → 微信 10003 无法自愈；合规成本 > 收益 |
| 10-11 | 京东云 2C4G 部署清单 + 2G swap `a40226e6` | [deploy/jdcloud_2c4g_checklist.md](../../../deploy/jdcloud_2c4g_checklist.md) | 坑：小内存 OOM |
| 10-15 | SEO + favicon `456427f5` `424936a0` | [public/robots.txt](../../../public/robots.txt)、[public/sitemap.xml](../../../public/sitemap.xml) | 公网可发现性补齐 |

#### 阶段 4｜知识库与双语文档体系（2026-09-27 → 10-28）

| 时间 | 做了什么 | 产出物 | 决策 / 坑 |
|---|---|---|---|
| 09-27 → 09-29 | 双语文档骨架 + 16 张专业 SVG + 图注双语 `90d9ae17` `a2cd4a2d` `779c9159` | [docs/images](../../images)（现 193 个 SVG） | 决策：图题 + 读图说明成对出现 |
| 09-29 | 全站中英混杂清理 `35ef47da` | [src/i18n.js](../../../src/i18n.js) | 规范：「同一内容块单一语言」，专名豁免 |
| 10-23 | 五图原则全量增强 `79ed3b66` | 16 中 + 15 英文档 | 坑：不得用占位示意值灌水 |
| 10-25 | 《AI 原生软件开发方法论》18 章 + 4 附录 `12af61bc` | [book/README.md](../../../book/README.md) | 中英逐章对应（1245 行中文正文） |
| 10-27 | 图书修订、论文基线同步 `e44e0c02` `ab70c2e9` `e04103bf` | [docs/EVOLUTION_AI_paper.md](../../EVOLUTION_AI_paper.md) | 统一取数口径 154 端点 / 1000+ 测试 |
| 10-28 | 双语错位与部署黑屏培训素材 `0ad4ede2` | [.trae/skills/troubleshoot-i18n-deploy](../../../.trae/skills/troubleshoot-i18n-deploy/SKILL.md) | 坑：症状相同但根因在三个不同事实源 |

#### 阶段 5｜2D/3D 造型单一真源重构（2026-10-07 → 10-25，最长战线）

| 子阶段 | 代表提交 | 产出物 | 关键决策 / 坑 |
|---|---|---|---|
| 5.1 NURBS 车身封闭化（10-07→10-10） | `ea41ce3b` `4ab70371` `7c128f4c` | [algorithm_model/car_modeling](../../../algorithm_model/car_modeling) | 7 类开口全封闭；坑：方盒子感、轮眉台阶 |
| 5.2 比例语义统一（10-11） | `1bfb91ef` `1e184b83` | [src/utils/carProfile.js](../../../src/utils/carProfile.js) | 「离地总高 = H」；旧口径腰线低 150–190mm |
| 5.3 座舱玻璃 + tumblehome（10-12→10-14） | `548b4e87` `c2b65d4e` `3a788352` `2e704a51` | [src/utils/carGlass.js](../../../src/utils/carGlass.js) | 几何抽纯函数 + 单测；六车型倾角 26/24/18/12/10/8° |
| 5.4 轮拱包络 / 轮腔（10-21） | `d26ab6d4` `f6bea5cc` `489d698d` `9869eea1` | `WHEEL_ENVELOPE` / `deriveWheelArch` / `archLinerProfile` | 坑：圆形筒套椭圆拱口 → 互穿 15/44mm；「零件缺失」先查埋没 |
| 5.5 车门/侧窗联动（10-22→10-23） | `0d4e2283` `c17db990` | [src/components/Car3D.vue](../../../src/components/Car3D.vue) | 决策：挖真门洞而非叠门板；玻璃挂车门铰链 |
| 5.6 玻璃写实 + G1（10-24） | `f0409161` `15ccf5b4` `d6636bc6` `98a4e59e` | 同上 | 坑：渐减 offset 致车顶沉入；改固定 `BODY_BEVEL_SIZE + GLASS_SURFACE_GAP` |
| 5.7 bevel 与门洞收尾（10-24→10-25） | `353e68ce` `b42e51e4` | 同上 | 坑：30mm bevel 造成 25mm 台阶、整车宽 60mm；缝条挂车身不随门退场 |

#### 阶段 6｜反重力飞行分支（2026-10-16）

| 时间 | 做了什么 | 产出物 | 决策 / 坑 |
|---|---|---|---|
| 10-16 | VTOL 全车型飞行 + 无眩晕悬浮 `2c87cb02` | [src/utils/flightPhysics.js](../../../src/utils/flightPhysics.js) | 全车型统一能力 |
| 10-16 | 飞控全栈（360° 转向 / HUD / 指标卡）`974bad89` | `src/views/Demo.vue` | 决策：对外声明为「受界工程估算模型」 |
| 10-16 | 飞行实测报告 + 理论推导专章 `9cc516c6` `ce97bd25` | [docs/flight_performance_report.md](../../flight_performance_report.md) | 坑：公式必须与源码逐项核实 |

#### 阶段 7｜品牌 DNA 与安全围栏（2026-10-22）

| 时间 | 做了什么 | 产出物 | 决策 / 坑 |
|---|---|---|---|
| 10-22 | 品牌 DNA 装载 / On-Brand / 2D 特征 `a38de31f` | [backend/app/brand_dna](../../../backend/app/brand_dna) | 决策：与 SISA 完全隔离，仅 stdlib + numpy；机密 DNA 只内存 |
| 10-22 | 游客全站放行 + Help 升级 `427f8a0b` | [src/views/Help.vue](../../../src/views/Help.vue) | 与账号封存配套 |
| 10-22 | 三服务启动技能 + cloudflared 备选 `fbf25f2a` | [.trae/skills/launch-services-detached](../../../.trae/skills/launch-services-detached/SKILL.md) | 坑：后台任务会连带杀死常驻服务 → 必须独立顶层进程 |

#### 阶段 8｜内饰布置与交付收口（2026-10-29 → 11-02，工作区）

| 时间 | 做了什么 | 产出物 | 状态 |
|---|---|---|---|
| 10-29 | 内饰布置 v1.0：H 点/座椅/IP/中控/地板 | `src/utils/carInteriorLayout.js`（866 行） | **未跟踪** |
| 10-31 | v1.3：滑轨有效行程限位 + 调角器/遮阳板/扶手盖运动学 | `src/utils/carInteriorKinematics.js`、`carSection2D.vue` | **未跟踪** |
| 11-01 | 内饰模型展示与 IP 行李舱设计 | [docs/IP_CONSOLE_LUGGAGE_DESIGN.html](../../IP_CONSOLE_LUGGAGE_DESIGN.html) | **未跟踪** |
| 11-02 | 2D 布置多级验证文档 v1.3 | [docs/2D_LAYOUT_VERIFICATION.md](../../2D_LAYOUT_VERIFICATION.md) | **未跟踪** |
| 11-02 | 前端全量 771 测试通过（本次实跑） | 19 文件 / 771 | 已验证 |

### 2.3 关键决策台账（补充本报告新增项）

| # | 决策 | 理由 | 影响 | 证据 |
|---|---|---|---|---|
| D1 | 几何一律抽零依赖纯函数 | 2D/3D/后端必须同源 | 单测锁契约，不靠肉眼 | `c2b65d4e` `2e704a51` |
| D2 | 比例语义「离地总高 = H」 | 旧口径腰线低 150–190mm | 六车型与真车对齐 | `1bfb91ef` |
| D3 | 玻璃偏移固定常量 | 渐减 offset 沉入车顶 | 无台阶折痕 | `d6636bc6` |
| D4 | bevel 30→12mm 且 `depth=W−2×bevel` | 车顶台阶 + 整车宽 60mm | 宽度严格 | `353e68ce` |
| D5 | 开门挖真洞 | 门板-侧壁几何重复 | 内壁需内饰材质 | `c17db990` |
| D6 | 布置基准用线不用体 | 实体唇板造成假最低点 | 接近/离去角构造线 | `489d698d` |
| D7 | 账号整体封存 | 微信域名漂移不可自愈 | 全站游客 | `6040bac4` |
| D8 | 发布 = 构建 + 公网 MD5 强校验 | CDN / ES module 缓存 | 「修完未验」流程上不可能 | `deploy-gh-pages` 技能 |
| D9 | 内饰坐标只由 `deriveInteriorLayout` 出 | 2D/3D 各自推导必漂移 | 2D 只做投影换算 | [2D_LAYOUT_VERIFICATION](../../2D_LAYOUT_VERIFICATION.md) §1 |
| D10 | 侧视不足以判横向干涉，必须加 A-A 横断面 | 侧视是 X-Y，Z 维盲区 | 新增 `CarSection2D` + D 组判据 | FIX-07/08 |

---

## 3. 当前进展

### 3.1 已具备能力（已验证事实）

| 能力域 | 现状 | 入口 / 证据 |
|---|---|---|
| 参数化整车 2D/3D | 六车型（sedan/suv/coupe/sport/mpv/pickup），2D 侧视 + A-A 横断面 + 3D 实时 | [Designer.vue](../../../src/views/Designer.vue)、[Car2D.vue](../../../src/components/Car2D.vue)、[Car3D.vue](../../../src/components/Car3D.vue)、[CarSection2D.vue](../../../src/components/CarSection2D.vue) |
| 内饰布置 | 座椅/IP/中控/门板/地毯/顶棚/安全带 + 运动件扫掠 | [carInteriorLayout.js](../../../src/utils/carInteriorLayout.js)、[carInteriorKinematics.js](../../../src/utils/carInteriorKinematics.js) |
| NURBS + STEP 工程输出 | 双管线（mesh / NURBS），8 类几何格式 | [algorithm_model/api.py](../../../algorithm_model/api.py)、[backend/app/routes/export.py](../../../backend/app/routes/export.py) |
| 曲面质量 | G0 0.1mm / G1 1.0°（视觉 5°）/ G2 判据 | [algorithm_model/surface_quality](../../../algorithm_model/surface_quality) |
| 贝叶斯优化 | RBF-GP + EI/UCB，15 维默认空间（脚本实测，文档仍写 14） | [backend/app/bayes_optimizer.py](../../../backend/app/bayes_optimizer.py) |
| 深度学习 / LLM | 训练任务后台化 + 7 提供商代理 + Ollama 本地专家 | [backend/app/routes/training.py](../../../backend/app/routes/training.py)、[backend/app/routes/llm_proxy.py](../../../backend/app/routes/llm_proxy.py) |
| 品牌 DNA | 5 品牌 19 车型知识库 + On-Brand 判定 | [backend/config/brand_design_knowledge.json](../../../backend/config/brand_design_knowledge.json)、[backend/app/brand_dna](../../../backend/app/brand_dna) |
| 反重力飞行 | VTOL + 飞控 + 性能报告（受界估算声明） | [src/utils/flightPhysics.js](../../../src/utils/flightPhysics.js) |
| 部署 | GitHub Pages 静态站 + Docker 四服务 + cpolar 隧道 | [deploy/](../../../deploy)、[.trae/skills/deploy-gh-pages](../../../.trae/skills/deploy-gh-pages/SKILL.md) |

### 3.2 可运行入口与验证方式

| 入口 | 命令 | 端口 | 验证 |
|---|---|---|---|
| 前端开发 | `npm run dev` | 5173 | 打开 `/#/designer`，切六车型，看 2D/3D |
| 前端生产预览 | `npm run build && npm run preview` | 4173（默认） | **几何复验一律用生产预览**，避开 HMR 缓存 |
| 后端 API | `cd backend && python start.py` | 8000 | `http://localhost:8000/docs` |
| 三服务常驻 | `.trae/skills/launch-services-detached/scripts/start_services.ps1` | 5173/8000/4040 | `.devservices/runtime.json` |
| 前端测试 | `npx vitest run` | — | 本次 19 文件 / 771 通过 |
| 后端测试 | `cd backend && python -m pytest tests -q` | — | 411 收集 |
| 算法测试 | `cd algorithm_model && python -m pytest tests -q` | — | 200 收集 |
| 结构事实 | `python scripts/verify_facts.py` | — | 154 端点 / 17 表 / 12 路由 |
| 公网 | `https://evolution-ai.design` | — | 最近发布 `99c91c70`（10-28），本次未复验 |

### 3.3 未完成项与已知问题

**已验证事实**

- 工作区 32 项未提交（内饰批次 + 玻璃/2D 修改），未进入任何分支。
- 文档数字冲突：见 §3.4。
- `backend/app/bayes_optimizer.py` 无 `converged` 字段、无自动收敛判定（`verify_facts.py` 复核为 `False`）。
- 本地服务审计时未运行。

**推断（未在本次复核）**

- 公网站点内容与 `gh-pages 99c91c70` 一致，但 CDN/缓存状态未重新验证。
- SISA 侧三项同口径同步是否完成，本仓库无法判定；仅能从 `project_memory` 的「遗留同步清单」推断仍未闭环。
- 玻璃分色 alphaMap + marching squares 方案是否已在代码落地，本次未逐行核验；文档称规范已确立。
- 内饰验收 HTML 的存在说明曾通过验收，但其中「710/710」已被当前 771 覆盖，属历史口径。

**待裁决 / 遗留**

| 编号 | 问题 | 影响 | 建议 |
|---|---|---|---|
| R1 | 开门后「仍有遮挡」未被用户确认关闭 | 体验 | 默认开门角 70°→82° / 门内板补面 / 最小座舱（三选一，需用户裁决） |
| R2 | 跨仓库 SISA 同口径同步 | 造型一致性 | 按 `wheel-arch-envelope-sync` 清单同批升级 |
| R3 | pre-push 专利守卫中文子串误报 | 提交流程 | 改写措辞；长期改词边界匹配 |
| R4 | 账号体系「封存」代码仍在 | 维护面 | 文档明确标注「已下线」，或另分支归档 |
| R5 | 一次性脚本与调试目录残留 | 仓库噪声 | 继续用 `.gitignore` 隔离，禁止入库 |
| R6 | 根目录 `evolution_ai.db` 1.07GB | 磁盘/误提交风险 | 确认忽略；迁移到 `backend/` 单一库 |

### 3.4 事实基线冲突表（本报告最重要的治理发现）

| 事实 | 本次实测 | 冲突来源 | 处置 |
|---|---|---|---|
| 前端测试 | **771 / 19 文件** | README 写 416；2D_LAYOUT 写 710/18；agent 写 123 | 以本次实跑为准，更新 README/验证报告 |
| 后端测试 | **411 收集**（408+1skip+2xfail 为上次执行口径） | agent 写 204；ARCHITECTURE 写 388 | 以 411 为准 |
| 算法测试 | **200 收集** | ARCHITECTURE 写 205；README 写 200 | 复跑后二选一 |
| HTTP 端点 | **154**（152+2） | ARCHITECTURE 写 153；agent 写 118 | 以 154 为准 |
| 路由模块 | **19** | agent 写 17；其余文档 19 | 以 19 为准 |
| ORM 表 | **17** | agent 写 13；ARCHITECTURE 写 17 | 以 17 为准 |
| 贝叶斯默认空间 | **15 维** | 文档写 14 | 二选一后同步 `bayes_optimization.md` |
| 导出格式 | 脚本口径 **20**；README 写 8 几何 + JSON | 口径差异（别名/组合） | 文档注明「8 类几何 + JSON」 |
| 前端路由 | **12** | README 写 10 个 views | 以 12 路由 / 15 视图文件为准 |

> 治理建议：把 `scripts/verify_facts.py` + 三层 pytest 输出作为唯一事实源，任何文档数字必须引用「命令 + 日期 + SHA」。

---

## 4. 顶层架构设计

### 4.1 分层结构（文本架构图）

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ L1 体验层（浏览器）                                                          │
│  12 路由页面（Dashboard / Designer / Copilot / Projects / DeepLearning /     │
│  Quality / Deliver / Demo / Help / Community / Contact / ProjectDetail）     │
│  渲染组件：Car2D（侧视）+ CarSection2D（A-A 断面）+ Car3D（Three.js）         │
│  单一真源工具层：carProfile / carGlass / carInteriorLayout /                 │
│                 carInteriorKinematics / car2dProjection / flightPhysics      │
│  状态：Pinia（auth/designer/project/ui）；i18n 中英双语；mock fallback        │
└───────────────────────────┬────────────────────────────────────────────────┘
                            │ HTTPS / JSON（Hash 路由）
┌───────────────────────────▼────────────────────────────────────────────────┐
│ L2 接入层                                                                    │
│  开发：Vite Proxy  /api/v1 → 127.0.0.1:8000；/api/ide → 外部 AI 网关          │
│  生产：Nginx（静态 dist + /api 反代）；cpolar HTTPS 隧道；GitHub Pages 静态   │
└───────────────────────────┬────────────────────────────────────────────────┘
                            │ REST
┌───────────────────────────▼────────────────────────────────────────────────┐
│ L3 编排层（FastAPI）                                                          │
│  19 路由模块 / 154 端点；薄壳编排，不重写算法                                  │
│  领域模块：bayes_optimizer / car_generator / cad_importer / nurbs /          │
│           brand_knowledge / brand_dna / fence / texture_analyzer /           │
│           clip_semantics / security / session_store                          │
│  横切：JWT、限流、CORS/CSP、Fernet 密钥、游客模式、审计日志                     │
└───────────────────────────┬────────────────────────────────────────────────┘
                            │ Python 函数调用 / dataclass 契约
┌───────────────────────────▼────────────────────────────────────────────────┐
│ L4 算法层（algorithm_model，可独立安装）                                       │
│  car_modeling（22 维 CarParams / body / body_nurbs / glass / wheels / ...）   │
│  freeform（NURBS 核心 / 扫掠 / 圆角 / STEP writer / Cython 加速）              │
│  surface_quality（G0/G1/G2 / 反射线 / 优化）                                   │
│  storyboard（分镜）                                                            │
│  统一入口 api.py：build_car / evaluate_surface / optimize_surface / ...       │
└───────────────────────────┬────────────────────────────────────────────────┘
                            │ ORM / 文件
┌───────────────────────────▼────────────────────────────────────────────────┐
│ L5 数据与基础设施                                                             │
│  SQLite（开发，17 表）/ PostgreSQL（生产）/ Redis（会话，可选）               │
│  文件：data/{models,exports,step,training,uploads}；public/brands；docs/images │
│  外部：LLM 提供商 ×7 / Ollama / SISA 独立仓库 / S3 无                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 核心模块职责与接口

| 模块 | 职责 | 对外接口 | 关键约束 |
|---|---|---|---|
| `src/utils/carProfile.js` | 六车型比例、轮拱包络、装配判据、接近/离去角 | `deriveCarProfile` / `WHEEL_ENVELOPE` / `deriveWheelFitment` | 唯一几何真源；2D/3D/后端同公式 |
| `src/utils/carGlass.js` | DLO 分缝、B 柱、G1 圆角、玻璃带 | `buildDloFrame` / `buildDloStrip` / `filletXAtY` | 零依赖纯函数 + 单测锁契约 |
| `src/utils/carInteriorLayout.js` | 内饰锚点、断面、附件、滑轨行程（米制） | `deriveInteriorLayout` / `deriveSectionLayout` / `deriveInteriorTrim` / `deriveSeatTrackTravel` | 2D/3D 不得各自推导坐标 |
| `src/utils/carInteriorKinematics.js` | 调角器/遮阳板/扶手盖扫掠 | `deriveKinematics` | 全行程无穿透 |
| `src/components/Car3D.vue` | Three.js 场景、材质、车门动画、内饰网格 | props: params / 状态 | 1875 行，**当前最大单体风险** |
| `backend/app/main.py` | 应用装配、中间件、异常、健康检查 | `create_app()` | 安全头/CORS 统一 |
| `backend/app/bayes_optimizer.py` | GP + EI/UCB | suggest / observe / export samples | 无自动收敛字段 |
| `algorithm_model/api.py` | 算法黑盒入口 | 7 大 API | 不依赖 FastAPI |
| `algorithm_model/freeform` | NURBS 数学 + STEP | 曲面求值 / writer | Cython 加速 ~70× |

### 4.3 关键数据流

```text
① 设计闭环
Designer(params) → carAPI.generate → car_generator（mesh + 数据）
  → ModelFile 持久化（params_json / car_data_json）→ Car3D 实时渲染
  → variantAPI 保存/对比/回滚

② 导入→改参→导出
upload → cad_importer（失败降级点云）→ import_export 会话
  → GET/PUT params → preview → export（8 类几何 + JSON）→ download

③ 优化→训练
POST /bayes/sessions → suggest（GP+EI/UCB）→ 评分 → observe 迭代
  → /samples 导出 → /ai/train 后台任务 → /ai/tasks 轮询

④ 2D/3D 同源
carProfile/carInteriorLayout（米） → Car2D 投影（像素） / CarSection2D 投影
                                   → Car3D 直接建网格 → 零容差断言

⑤ 发布
vitest → build → dist 全量 → gh-pages worktree → push → 公网 MD5 比对
```

### 4.4 技术选型理由

| 选型 | 理由 | 代价 |
|---|---|---|
| Vue 3 + Vite | 组件化 + 秒级 HMR；Hash 路由适配 Pages | 无 SSR/SEO 天然弱，需静态 meta 补齐 |
| Three.js | 浏览器实时 3D，无插件 | 大 chunk；材质/几何细节需手工调 |
| FastAPI + Pydantic v2 | 契约优先、自动文档、类型校验 | 薄壳层易膨胀（154 端点） |
| 自研 NURBS / STEP writer | 参数直驱，避免 mesh→NURBS 拟合误差 | 数学与性能门槛高，需 Cython |
| SQLite → PostgreSQL | 开发零依赖，生产可迁移 | 双口径需 Alembic 纪律 |
| GitHub Pages + Docker | 零成本公网演示 + 可控生产 | 两套发布路径，易漏 assets |
| 纯函数 + Vitest | 几何契约可断言 | 测试文件体量大（5187 行） |

### 4.5 扩展点

| 扩展点 | 做法 | 边界 |
|---|---|---|
| 新车型 | `carProfile` 加档位 + `carTypeParams` 预设 + 玻璃/内饰表 | 不得新增第二套比例 |
| 新几何特征 | 纯函数 → 单测 → 2D/3D 双消费 → SISA 同步 | 不得在组件内硬编码 |
| 新端点 | `backend/app/routes/<domain>.py` + schema + 测试 | 不改算法层 |
| 新 LLM 提供商 | `llm_proxy` 注册表 + 环境变量槽位 | 密钥不落库明文 |
| 新技能 | `.trae/skills/<name>/SKILL.md` | 触发条件必须可判别 |

### 4.6 架构主要风险

| 风险 | 等级 | 证据 | 缓解 |
|---|---|---|---|
| 未提交真源批次丢失 | 高 | 32 项变更 / 1425 行 | 立即开分支提交，禁止 reset |
| `Car3D.vue` 单体过大 | 高 | 1875 行 / 82KB | 拆 `useCar3DScene` + 零件工厂，先补测试再拆 |
| 跨仓库口径漂移 | 高 | SISA 遗留清单 | 同批升级 + 跨仓库交叉测试 |
| 文档多口径 | 中高 | §3.4 九项冲突 | verify_facts 单一事实源 + 文档门禁 |
| 运行数据不可重建 | 中 | data 2.7GB 全忽略 | 数据卡（来源/生成脚本/哈希） |
| 单机 2C4G 生产 | 中 | 部署清单 | swap + 同域反代 + 限流 |
| 视觉验证成本 | 中 | 多机位 + 生产预览 | 固化截图脚本与标准机位 |

---

## 5. 方法论

### 5.1 实际在用的工程方法（不是口号，是可核对机制）

| 原则 | 落地机制 | 证据 |
|---|---|---|
| **世界模型** | 把「车」建成可计算的参数世界：22 维 CarParams + 六车型比例表 + 轮拱包络 + 内饰锚点；所有视图都是同一模型的投影 | `carProfile` / `carInteriorLayout` 单一真源；2D 只做投影换算 |
| **预测—验证—修正** | 先写纯函数与断言（预测），再跑测试/多机位（观测），偏差回写记忆（修正） | 771 前端断言；FIX-01~FIX-12 记录 |
| **自迭代** | 每次踩坑沉淀为 `project_memory` 硬约束/教训；事故升级为 skill | 206 行项目记忆；7 个仓库技能 |
| **持续优化** | 性能（Cython 70×/34×）、体积（chunk 拆分）、载荷（200KB JSON 守卫）、启动（fail-fast） | 记忆条目 + 架构文档 |
| **证据型交付** | 任何数字必须有命令、日期、SHA；发布必须公网 MD5 比对 | `VALIDATION_REPORT_20261025`；D8 |
| **契约优先** | Pydantic/TS 字段 100% 对齐；端点与表先定 | 架构文档 §3/§5 |
| **人机分工** | 机器给候选与证据，人保留裁决（开门角、审美、专利） | R1 待裁决项 |
| **单一运行时** | 全机一组服务，禁止按端口杀进程 | `COLLABORATION_PROTOCOL.md` |

### 5.2 新任务接入流程（可复用，8 步）

```text
① 读上下文（3 分钟）
   读 project_memory 相关条目 + COLLABORATION_PROTOCOL + 最近 git log
② 确认运行时（30 秒）
   netstat 查 5173/8000/4040；已运行则只编辑，不重启
③ 确认基线（1 分钟）
   git status --porcelain；npx vitest run（或相关子集）
④ 定位单一真源（关键）
   问：这个量现在由谁算？carProfile / carGlass / carInteriorLayout / 后端?
   找不到唯一入口 → 先建入口，不写第二套
⑤ 拆任务（TodoWrite）
   每步可验证；跨层改动列清 前端↔后端↔schema
⑥ 实现（最小改动）
   纯函数优先；不顺手重构；不引入新依赖
⑦ 验证（硬门禁，不可跳）
   L1 单测 → L2 构建 → L3 生产预览实机 → L4 公网 MD5（仅发布时）
⑧ 沉淀
   踩坑写记忆；可复用流程升 skill；数字更新验证报告；再提交
```

### 5.3 应保留 / 应淘汰

**保留**

- 单一真源 + 零依赖纯函数 + 单测锁契约。
- 生产构建预览复验（绕开 HMR/ES module 缓存）。
- 发布全量同步 + 公网 MD5 强校验。
- 记忆 → 约束 → 技能的三级沉淀。
- 协同协议（单一运行时、不按端口杀进程）。
- 「零件缺失先查埋没」「表达基准用线不用体」这类根因优先的判据。

**淘汰 / 收敛**

- 一次性下载/诊断脚本进仓库（现用 `_` 前缀 + `.gitignore` 隔离，但仍应定期清理）。
- 「凭截图猜根因」与无限重试浏览器（改为 A/B 隔离、射线、MD5 闭合）。
- 文档手写数字（改为一律引用 verify_facts 输出）。
- 渐减偏移、旧比例口径、面片二值玻璃分色等已被判决的旧方案。
- 单体组件继续膨胀（`Car3D.vue` 需拆分）。
- 多套事实口径并存（本报告 §3.4 即为代价）。

---

## 6. 资产全量梳理

### 6.1 智能体（Agents）

| 资产 | 路径 | 用途 | 状态 |
|---|---|---|---|
| 平台全栈专家 agent | [.trae/agents/evolution-ai-design.md](../../../.trae/agents/evolution-ai-design.md) | 本仓库开发/修复/架构/部署的专属角色定义（9243 字节） | 已有；**内容部分过期**：写 118 端点 / 17 路由 / 13 表 / 前端基线 123，与现行 154 / 19 / 17 / 771 冲突 |
| 宿主内置 Explore / general-purpose / Plan / browser_use 等 | 由运行环境提供，不在仓库 | 探索、通用执行、规划、浏览器验证 | 可用，无需仓库文件 |
| 子代理编排关系 | 无仓库内编排文件 | 目前是「单 agent + 宿主子代理」扁平结构 | 雏形；无多 agent 协作协议 |

> 结论：智能体资产只有 1 个正式定义，且数字已漂移。**优先级：中**（不影响运行，影响接手者判断）。

### 6.2 Skills（7 个仓库技能）

| 技能 | 触发条件（来自 frontmatter） | 用途 | 路径 | 状态 |
|---|---|---|---|---|
| `deploy-gh-pages` | 发布公网、更新站点、公网黑屏/404 | dist 全量同步 gh-pages + 校验 | [SKILL.md](../../../.trae/skills/deploy-gh-pages/SKILL.md) | 成熟（六步流程） |
| `launch-services-detached` | 启动/重启三服务、服务掉线、cpolar 换域名 | 独立顶层进程拉起 5173/8000/4040 | [SKILL.md](../../../.trae/skills/launch-services-detached/SKILL.md) + 3 脚本 | 成熟 |
| `doc-code-audit` | 核对文档、一致性、stale 数字、死链 | 文档↔源码一键核对 | [SKILL.md](../../../.trae/skills/doc-code-audit/SKILL.md) + `check_consistency.py` | 成熟，但本次未运行 |
| `project-intro-deck` | 生成/更新项目介绍 PPT | 中英双版 12 页，碰撞检测 | [SKILL.md](../../../.trae/skills/project-intro-deck/SKILL.md) | 成熟 |
| `threejs-automotive-preview-debugging` | 3D 高光/反射/破面/零件不可见/比例失调 | Car3D 渲染根因库 | [SKILL.md](../../../.trae/skills/threejs-automotive-preview-debugging/SKILL.md) | 新增（未跟踪） |
| `wheel-arch-envelope-sync` | 拱轮错位/车轮穿壳/拱顶不足/EVO→SISA | 跨平台轮拱包络同步 | [SKILL.md](../../../.trae/skills/wheel-arch-envelope-sync/SKILL.md) | 新增（未跟踪） |
| `troubleshoot-i18n-deploy` | 中文界面英文内容、文档数字过期、公网白屏 | 三层事实源分层定位 | [SKILL.md](../../../.trae/skills/troubleshoot-i18n-deploy/SKILL.md) | 新增（已提交 `0ad4ede2`） |

另有宿主级技能（`TRAE-browseruse`、`TRAE-debugger`、`algorithm-debugging`、`skill-creator` 等）由运行环境提供，不在仓库内。

### 6.3 数据集 / 训练集

| 资产 | 路径 | 规模 | 格式 | 用途 | 状态 |
|---|---|---|---|---|---|
| A 级曲面 QA 集 | [data/training/a_surface_quality_dataset.jsonl](../../../data/training/a_surface_quality_dataset.jsonl) | 23 行 / 22.4KB | JSONL `{prompt, completion}` | 曲面 SOP/公差问答微调 | 已有；gitignored |
| NURBS 曲面知识集 | [data/training/nurbs_surface_dataset.jsonl](../../../data/training/nurbs_surface_dataset.jsonl) | 29 行 / 26.9KB | 同上 | NURBS/G1 概念与实现问答 | 已有；gitignored |
| 增强 QLoRA 集 | [data/training/qlora_enhanced_dataset.jsonl](../../../data/training/qlora_enhanced_dataset.jsonl) | 63 行 / 48.1KB | 同上 | QLoRA 微调主数据 | 已有；gitignored |
| LoRA 适配器 | [data/training/nurbs-qwen-lora](../../../data/training/nurbs-qwen-lora) | 12 文件 | safetensors 等 | 已训练权重 | 已有；gitignored |
| 合并模型 | `data/training/merged` | 5 个 safetensors ≈ 2.0GB | safetensors | 合并后权重 | 已有；gitignored |
| 训练任务产物 | `data/training/cartype_mlp_task*.pt` | 175 个 `.pt` / 205MB | PyTorch | 车型分类实验 | 已有；gitignored |
| 品牌车型知识库 | [backend/config/brand_design_knowledge.json](../../../backend/config/brand_design_knowledge.json) | 5 品牌 19 车型 × 14 参数 + 8 指标 | JSON | 设计约束/On-Brand | 已有，随仓库 |
| 品牌车型图 | [public/brands](../../../public/brands) | 5 品牌 / 38 文件 | JPG/PNG | 19 车型正侧视基准 | 已有，随仓库 |
| 品牌 DNA 机密 | `backend/app/brand_dna/dnas/` | 不在 git（仅 demo_public） | JSON | On-Brand 判定 | 已有；机密仅内存 |
| 模型/导出运行数据 | `data/{models,exports,step,uploads}` | 714+119+43+1 文件 ≈ 654MB | GLB/STL/STEP/IGES 等 | 生成与导出产物 | 运行产物，不入库 |
| 文档图库 | [docs/images](../../images) | 193 SVG | SVG | 文档五图原则 | 已有 |
| SISA 参考包 | [shared_reference](../../../shared_reference) | 4 文件 | JSON/MD | 跨仓库尺寸闭合参考 | 已有 |

> **数据可复现缺口**：`data/training` 2.3GB 全被 `.gitignore`，换机需要 `scripts/train_qlora.py` 重新生成或手工拷贝；缺少 `dataset card`（来源、生成命令、SHA256）。建议补一份 `data/README.md`（不入库大文件）。

### 6.4 工作流（Workflow）

| 工作流 | 节点 / 端点 | 依赖 | 调用方式 | 状态 |
|---|---|---|---|---|
| 后端工作流 CRUD + 执行 | create / list / get / update / delete / execute / steps / review / training-review（9 端点） | ORM `workflows` + `workflow_steps` | `POST /api/v1/workflows` → `POST /{id}/execute` | 已有（[workflow.py](../../../backend/app/routes/workflow.py)） |
| 设计意图工作流 | 解析 → 参数变体 → 项目 | design_intent 3 端点 | `POST /api/v1/design-intent/*` | 已有 |
| 导入→改参→导出 | upload → parse → params → preview → export → download（11 端点） | cad_importer + export | `POST /api/v1/import-export/*` | 已有 |
| 贝叶斯→训练 | session → suggest → observe → samples → train → poll | bayes + training | 前端 `bayesAPI` + 轮询 | 已有；无自动收敛 |
| 质量→交付 | 质量检查 → 报告 → 交付页 | quality 9 端点 + QualityReport | `/quality` → `/deliver` | 已有 |
| 算法一站式管线 | build_car → evaluate → optimize → storyboard | algorithm_model 7 API | `run_full_pipeline` | 已有 |
| 发布工作流 | vitest → build → dist 同步 → push → 公网 MD5 | gh-pages 技能 | 技能脚本 | 成熟 |
| 内饰多级验证工作流 | L1 契约 → L2 布置 → L2b 断面 → L2c 纵向 → L2d 附件 → L2e 运动 → L3 人机 → L4 对齐 → L5 目视 | vitest 3 个 spec | `npx vitest run src/tests/carInterior*` | 已有（工作区） |

---

## 7. 复现手册（最省时省消耗）

### 7.1 从零到跑起来（最小路径）

**前置**：Windows + Node 18+ + Python 3.11+（可选 Git）。

| 步骤 | 命令 | 说明 | 可否跳过 |
|---|---|---|---|
| 1 | `cd D:\API\Evolution-Ai.Design && npm install` | 前端依赖（约 1–3 分钟） | 不可 |
| 2 | `npm run dev` | 5173；**后端不启动也能浏览**（mock fallback） | 不可 |
| 3 | 打开 `http://localhost:5173/#/designer` | 六车型切换、2D/3D、参数面板 | 不可 |
| 4 | `cd backend && pip install -r requirements.txt` | 后端依赖 | 只看前端可跳过 |
| 5 | 复制 `backend/.env.example` → `backend/.env` | 只需 4 个变量（见 §7.2） | 不可（后端） |
| 6 | `python start.py` | 8000；`/docs` 可交互 | 只看前端可跳过 |
| 7 | `cd algorithm_model && python -m pytest tests -q` | 200 用例，约数秒 | 不碰算法可跳过 |
| 8 | `npx vitest run` | 771 用例，约 6 秒 | 不可（改前端必跑） |

**推荐常驻方式**（避免命令宿主连带杀死服务）：

```powershell
powershell -ExecutionPolicy Bypass -File .trae\skills\launch-services-detached\scripts\start_services.ps1
# 停止：stop_services.ps1
```

### 7.2 环境变量（最小集）

```ini
ENVIRONMENT=development          # 生产改 production（会强制 SECRET_KEY 校验）
DEBUG=true                       # 生产必须 false
DATABASE_URL=sqlite:///./evolution_ai.db
SECRET_KEY=evolution-ai-dev-secret-change-me-in-production-2026
# 以下全部可选：
# GUEST_MODE=true                # 受保护接口统一落到 guest；生产禁止
# SESSION_USE_REDIS=false        # 无 Redis 自动内存兜底
# EVOAI_<PROVIDER>_KEY=...       # 无 Key 时 LLM 端点 503，不影响几何
```

**可跳过**：PostgreSQL、Redis、Docker、GPU/PyTorch、Ollama、CLIP、微信/公众号、cpolar、LLM Key。

### 7.3 验证步骤（按成本递增）

| 级别 | 命令 | 通过判据 | 成本 |
|---|---|---|---|
| L1 结构 | `python scripts/verify_facts.py` | 19 / 154 / 17 / 12 | <1s |
| L2 单测 | `npx vitest run` | 19 文件 / 771 通过 | ~6s |
| L2 后端 | `cd backend && python -m pytest tests -q` | 411 收集，全过（约 100s） | ~2min |
| L2 算法 | `cd algorithm_model && python -m pytest tests -q` | 200 通过（约 5s） | ~5s |
| L3 构建 | `npm run build` | dist 生成、无致命错误 | ~30s |
| L3 实机 | `npm run preview` + 浏览器六车型 | 2D/3D 无越界/穿模/折痕 | 人工 |
| L4 发布 | `deploy-gh-pages` 技能 | 公网 MD5 与本地一致 | 人工+网络 |

### 7.4 常见故障与快速排查表

| 症状 | 最可能根因 | 一步排查 | 处置 |
|---|---|---|---|
| 前端起不来 / 端口占用 | 已有实例 | `netstat -ano \| Select-String ":5173"` | 用 `stop_services.ps1`，**不要按端口杀进程** |
| 页面 API 全部 404 | 后端未起 / 代理断开 | 打开 `:8000/docs` | 起后端或忽略（mock fallback） |
| 公网白屏/黑屏 | dist 漏 `assets/` | 公网 chunk 请求是否 404 | 按 `deploy-gh-pages` 全量同步 |
| 中文界面显示英文 | 三层事实源错位（i18n / docs zh-en / locale） | 先确认是 UI 文案还是文档正文 | 按 `troubleshoot-i18n-deploy` 分层定位 |
| 车型图变纯色 SVG | L1 本地图瞬时失败被永久降级 | Network 看 L1 图请求 | 修复降级链（仅瞬时重试，不永久降级） |
| 3D 车门/轮毂浮出 12mm | 装配基准仍用 `W/2 + bevel` | 查 `deriveWheelFitment` 入参 | 传真实半宽 `bodyExtentZ` |
| 车顶白带/折痕 | bevel 台阶或玻璃渐减 offset | 查 `BODY_BEVEL_SIZE` 与玻璃 gap | 固定常量 + 12mm bevel |
| 轮拱穿模/黑洞 | 圆筒内衬套椭圆拱口 | 查 `archLinerProfile` | 与拱口同形内嵌椭圆壳 |
| 座椅与中控重叠 | 只用侧视验证（Z 盲区） | 看 A-A 断面 | 按 D 组判据修正 `rowSeatLayout` |
| 改 `param_schema.py` 不生效 | 旧后端进程 | 看进程启动时间 | 重启 7801/8000 后端 |
| 测试数字与文档不符 | 并行会话/基线漂移 | `git status` + `git diff` | 以实跑为准，更新验证报告 |
| pre-push 被阻断 | 专利守卫中文子串误报 | 看钩子命中词 | 改写措辞，**不用 `EVOAI_ALLOW_PUSH` 绕过** |
| 浏览器复验仍是旧代码 | dev HMR / ES module 缓存 | 换生产 preview 新端口 | 一律生产构建复验 |
| SQLite locked | 长测试与开发共用库 | 是否有 pytest/训练在跑 | 同一时刻只跑一个长批次 |
| 训练集缺失 | `data/training` 被忽略 | 目录是否存在 | 跑 `scripts/train_qlora.py` 或另行拷贝 |

### 7.5 常用任务模板（少步骤）

#### T1 新增 Skill（3 步）

```powershell
# 1) 建目录 + SKILL.md（frontmatter 必须含 name/description，description 写清触发语）
New-Item -ItemType Directory .trae\skills\<name>
# 2) 写流程（可附 scripts/），确保命令可复制执行
# 3) 用一句真实触发语自测：能否只读 SKILL.md 完成操作
```

可跳过：README 导航、PDF/预览图（除非用户要展示）。验收：触发语命中 + 按步骤一次跑通。

#### T2 新增 Agent（2 步）

```text
1) .trae/agents/<name>.md：frontmatter(name/description/tools) + 角色/边界/流程/硬约束
2) 用 3 个典型任务试跑，确认不会越界改无关模块
```

可跳过：`tools` 精细化（先给最小集）。验收：能独立定位文件并给出可执行计划。

#### T3 接入新数据集（4 步）

```text
1) JSONL 放 data/training/（gitignored）；字段统一 {prompt, completion}
2) 在 scripts/train_qlora.py 的 DATASETS 列表登记文件名
3) 小样本 dry-run：python scripts/train_qlora.py --data <file> --epochs 1
4) 记录 dataset card（来源/行数/生成命令/SHA256）到 data/README.md
```

可跳过：全量训练（GPU 昂贵）；先用 1 epoch 验证格式。验收：加载无报错、样本可解析。

#### T4 调整工作流（4 步）

```text
1) 后端：backend/app/routes/workflow.py 加/改端点 + schemas.py 字段
2) 数据：database.py 若加表 → Alembic 增量迁移（不得只 create_all）
3) 测试：backend/tests/ 加用例；前端 api.js 同步方法
4) 验证：pytest 子集 → 全量 411 → 前端调用实测
```

可跳过：Docker 重建（本地 SQLite 足够）。验收：端点 200 + 步骤状态可轮询。

#### T5 新增几何特征（本项目最高频，5 步）

```text
1) 在 carProfile/carGlass/carInteriorLayout 中加纯函数（零依赖）
2) 先写失败测试锁定契约，再实现
3) 2D（Car2D / CarSection2D）只做投影；3D（Car3D）直接用米值
4) 六车型矩阵断言 + 生产 preview 多机位目视
5) 若影响轮拱/玻璃分缝 → 在 wheel-arch-envelope-sync 清单登记 SISA 同步
```

可跳过：后端 NURBS 联动（仅当参数需进后端时）。验收：新旧测试全绿 + 六车型无穿模。

#### T6 发布公网（4 步）

```text
1) npx vitest run（771 全绿）
2) npm run build
3) 按 deploy-gh-pages 技能：dist 全量 → gh-pages worktree → push
4) 公网 MD5 与本地逐字节比对；重试到 index.html 引用的 chunk 全可取
```

可跳过：无（发布是刚性闭环）。

---

## 8. 下一阶段工作任务规划

> 估算单位：人日（1 人）；优先级 P0 > P1 > P2。依赖用任务号表示。

### 8.1 2026-11（里程碑 M1：交付边界收口）

| # | 任务 | 优先级 | 依赖 | 工作量 | 验收标准 | 风险与应对 |
|---|---|---|---|---|---|---|
| M1-1 | 内饰/玻璃/2D 批次开分支提交 + 补 CHANGELOG | P0 | — | 1 | 32 项变更入库；771 全绿；diff 可追溯 | 误提交调试文件 → 按 `.gitignore` 白名单逐文件 add |
| M1-2 | 统一事实基线（README/ARCHITECTURE/agent/验证报告） | P0 | M1-1 | 1.5 | §3.4 九项冲突全部消除；数字均带命令+日期+SHA | 文档改动面大 → 以 verify_facts 输出为唯一来源批量替换 |
| M1-3 | 公网复验 + 发布（若 M1-1 影响前端） | P0 | M1-1 | 0.5 | MD5 一致；六车型实机 PASS | CDN 缓存 → 重试 + cache-busting |
| M1-4 | 开门遮挡 R1 裁决与实现 | P1 | — | 1–3 | 用户确认关闭；门洞/门板/内饰三选一落地 | 方案分歧 → 先出 3 个对比截图让用户裁决 |
| M1-5 | `Car3D.vue` 拆分设计（不实施） | P1 | M1-1 | 1 | 拆分清单 + 依赖图 + 回归方案 | 拆坏几何 → 先补渲染快照测试再动 |
| M1-6 | dataset card（数据来源/生成/SHA） | P2 | — | 0.5 | `data/README.md` 可指导换机复现 | 大文件不入库 → 只写元数据 |

### 8.2 2026-12（里程碑 M2：跨仓库一致性与可维护性）

| # | 任务 | 优先级 | 依赖 | 工作量 | 验收标准 | 风险与应对 |
|---|---|---|---|---|---|---|
| M2-1 | SISA 同口径同步三项（closed_shell / wheel_arch / dimension_plan） | P0 | M1-1 | 3–5 | 跨仓库交叉测试一致；拱心/拱半径零漂移 | 几何基线冲突 → 同批更新 + 交叉脚本 |
| M2-2 | 文档门禁脚本接入（verify_facts + doc-code-audit） | P1 | M1-2 | 2 | 文档数字不一致时 CI/本地失败 | 误报 → 建立白名单 |
| M2-3 | `Car3D.vue` 拆分实施（场景/零件/动画三层） | P1 | M1-5 | 4–6 | 行数降 40%；渲染快照零差异 | 回归面大 → 分步提交，每步全绿 |
| M2-4 | 玻璃 alphaMap 方案核验与落地（若未落地） | P2 | — | 2–4 | 边界无固定锯齿；截图对比 | 方案替换风险 → A/B 构建对比 |
| M2-5 | 内饰 AABB → 曲面化（R-05 执行层） | P2 | M2-3 | 3–5 | 观感提升且尺寸仍同源 | 造型与布置冲突 → 冻结包络不变 |

### 8.3 2027-01（里程碑 M3：工程化与复现效率）

| # | 任务 | 优先级 | 依赖 | 工作量 | 验收标准 | 风险与应对 |
|---|---|---|---|---|---|---|
| M3-1 | 一键复现脚本（doctor：环境/端口/依赖/测试） | P1 | M1-2 | 2 | 新机 10 分钟内跑起来 | 平台差异 → PowerShell 单栈，先 Windows |
| M3-2 | 测试分层提速（前端按域并行 / 后端标记慢例） | P2 | M2-3 | 2 | 前端 <3s，后端快例 <30s | 并行污染 → 隔离夹具 |
| M3-3 | 生产可观测性（结构化日志 + 关键链路 trace） | P2 | — | 3 | 任一失败可回溯请求/步骤 | 隐私 → 脱敏 |
| M3-4 | 账号体系归档决策（删除 / 独立分支 / 文档标注） | P2 | — | 1 | 代码与文档一致 | 误删 → 先打 tag |
| M3-5 | 专利守卫词边界匹配改造 | P2 | — | 1 | 不再误报普通几何注释 | 漏检 → 双跑对照 |

### 8.4 里程碑甘特（文本）

```text
2026-11   M1  ██████████  提交边界 / 事实基线 / 开门裁决
2026-12   M2        ██████████  SISA 同步 / 文档门禁 / Car3D 拆分
2027-01   M3              ██████████  一键复现 / 测试提速 / 可观测
```

### 8.5 依赖关系图

```text
M1-1 ──┬── M1-2 ──┬── M2-2 ── M3-1
       ├── M1-3   └── M3-3
       ├── M1-5 ── M2-3 ──┬── M2-5
       └── M2-1           └── M3-2
M1-4（独立，需用户裁决）
M1-6 / M2-4 / M3-4 / M3-5（独立）
```

---

## 9. 复盘方法与证据边界

### 9.1 本次实际执行的核查

| 核查 | 命令/方式 | 结果 |
|---|---|---|
| 提交史 | `git log --date=short --pretty=...` | 116 提交；HEAD/gh-pages 已记录 |
| 工作区 | `git status --porcelain` | 32 项（9 M / 23 ??） |
| 结构事实 | `python scripts/verify_facts.py` | 19 / 152+2 / 17 / 12 / 22 / 15 |
| 前端测试 | `npx vitest run --reporter=dot` | 19 文件 / 771 通过 |
| 后端/算法用例 | `pytest --collect-only -q` | 411 / 200 |
| 数据规模 | 目录递归统计 | `data/` ≈ 2.7GB；training 2.3GB |
| 服务状态 | `netstat` 过滤 5173/8000/4040 | 无监听 |
| 技能/智能体 | 目录 + frontmatter 抽样 | 7 技能 / 1 agent |
| 文档 | README、ARCHITECTURE、VALIDATION、DEVELOPMENT_HISTORY、2D_LAYOUT、book README 精读 | 见引用 |

### 9.2 未覆盖与不可判定

- `data/` 内 714 个导出文件、175 个 `.pt` 未逐文件检查内容，仅统计规模。
- `backend/tests` 411 例本次只收集未执行（上次执行口径见验证报告）。
- 公网内容未在本次重新抓取比对。
- SISA 仓库、Harness 保密项目不在本仓库范围，未探查。
- `docs/en` 与 `book/en` 未逐篇比对，只抽查结构与数字口径。

### 9.3 复现本报告的脚本

报告本身不需要新脚本；核查命令均为仓库既有：

```powershell
git log --date=short --pretty=format:"%h|%ad|%s" -30
git status --porcelain
python scripts/verify_facts.py
npx vitest run --reporter=dot
cd backend; python -m pytest tests --collect-only -q
cd ../algorithm_model; python -m pytest tests --collect-only -q
```

---

## 10. 相关文档索引（项目内相对路径）

| 文档 | 用途 |
|---|---|
| [README.md](../../../README.md) | 项目总览与快速开始（部分数字待按 §3.4 更新） |
| [docs/DEVELOPMENT_HISTORY.md](../../DEVELOPMENT_HISTORY.md) | 2026-08-18 → 10-25 工程史志（本报告时间线的底稿） |
| [docs/ARCHITECTURE_DESIGN.md](../../ARCHITECTURE_DESIGN.md) | 五层架构、路由清单、ORM、数据流 |
| [docs/VALIDATION_REPORT_20261025.md](../../VALIDATION_REPORT_20261025.md) | 10-25 事实基线（历史口径） |
| [docs/2D_LAYOUT_VERIFICATION.md](../../2D_LAYOUT_VERIFICATION.md) | 内饰布置 v1.3 多级验证（63 项） |
| [docs/MODULE_INTEGRATION_FLOW.md](../../MODULE_INTEGRATION_FLOW.md) | 模块集成数据流 |
| [docs/methodology.md](../../methodology.md) | 造型开发五维方法论 |
| [book/README.md](../../../book/README.md) | 《AI 原生软件开发方法论》18 章 |
| [COLLABORATION_PROTOCOL.md](../../../COLLABORATION_PROTOCOL.md) | 多工具单一运行时协议 |
| [.trae/agents/evolution-ai-design.md](../../../.trae/agents/evolution-ai-design.md) | 平台全栈 agent 角色定义 |
| [.trae/skills](../../../.trae/skills) | 7 个仓库技能 |
| [scripts/verify_facts.py](../../../scripts/verify_facts.py) | 结构事实唯一事实源 |

---

## 11. 一页纸行动清单

1. **今天**：把 32 项工作区变更提交到 `feat/interior-packaging`，跑 771 全绿；避免丢失。
2. **本周**：用 `verify_facts.py` 输出统一 README / ARCHITECTURE / agent / 验证报告五处数字。
3. **本周**：公网复验 `gh-pages 99c91c70`，确认内饰批次发布前后一致性。
4. **本月**：用户裁决开门遮挡方案；登记 SISA 三项同步工单。
5. **下月**：文档门禁脚本 + `Car3D.vue` 拆分第一步。
6. **长期**：任何新任务按 §5.2 八步接入；任何踩坑当轮写入记忆或升技能。

---

*报告结束。本文件与配套 HTML 仅新增于 `docs/retrospective/2026-11-02/`，未改动任何业务代码。*
