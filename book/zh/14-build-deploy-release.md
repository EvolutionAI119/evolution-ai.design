# 第 14 章 构建、部署与发布

> 作者：量子剑客
> 第四卷 · 工程：把不确定性收敛为交付

## 一、引言问题

一个 AI 原生平台的发布，远比"打包上传"复杂。算法层带着需要编译的 Cython 扩展，前端拖着 Three.js 这样的大体积 3D 库，后端启动前要过密钥校验，知识库文档还要随站发布。两个工程问题随之而来。第一，构建产物为什么长这样？当 `dist/` 里出现九个 chunk，每个 chunk 的存在都应有理由，而不是打包器的即兴发挥。第二，部署拓扑能否在一台新机器上复现？如果上线依赖某位工程师记忆里的七个手工步骤，那么每次发布都是一次不可审计的表演。

本章的命题是：**构建产物可解释，部署拓扑可复现**。可解释意味着产物结构与配置意图一一对应；可复现意味着拓扑全部写进声明式文件，一条命令拉起，健康检查守门，密钥只从环境注入。

## 二、原则

**其一，产物即文档。** 构建配置里的每一条规则都是一次决策记录：为什么这个大库整体缓存、为什么那个小库独立成块。读配置应能还原意图，读产物应能验证意图。

**其二，拓扑声明式，启动单命令。** 服务有几个、谁依赖谁、数据落在哪个卷，全部由 compose 文件声明；首次部署与第一百次部署执行同一条命令，得到同一个结果。

**其三，密钥与产物分离。** 镜像与静态产物从不携带密钥；密钥在运行期由环境注入，缺失即 fail-fast。可公开的东西彻底公开，需保密的东西绝不进构建。

**其四，发布面最小化。** 公开站点只承载公开功能；管理后台的代码不进公开产物，从路由、菜单到 chunk 全部移除，改由后端独立托管。

## 三、案例解剖

先看构建侧。`vite.config.js` 的 `manualChunks` 是一份带注释的决策清单：先判 `@element-plus/icons-vue` 再判 `element-plus`——因为后者的 id 同样包含前者字样，顺序错了图标库会被错误合并；Three.js 拆为 `three` 主包与 `three-examples` 附加件两块，分别缓存；`vue`、`markdown-it`、`axios` 各自独立。注释里写明了反向决策的理由："大库刻意整体缓存而非无限细拆，拆分过细会成倍增加请求数且破坏库级缓存收益"，因此 `chunkSizeWarningLimit` 放宽到 1000kB，消除无意义的体积告警。另有两个发布侧决定：`base: './'` 用相对路径保证产物可移植，`sourcemap: false` 控制公开产物的信息暴露；`docsPlugin` 在构建时把 `docs/` 下的 Markdown、PDF、HTML 与 SVG 复制进 `dist/docs/`，让知识库随站发布、与代码同版本——文档即产品的交付形态。

<figure class="doc-figure"><img src="../docs/images/october-deployment.svg" alt="生产部署拓扑：浏览器经 Nginx 同域反代，/ 走 dist 静态站，/api 与 /admin 走 FastAPI 后端，数据落 PostgreSQL 与 Redis，承载于内地合规云主机"><figcaption><strong>图 14-1 ｜ 生产部署拓扑：同域反代 + 内地合规</strong> 读图：浏览器只与一个 Nginx 入口对话——`/` 分发给 dist 静态站，`/api` 与 `/admin` 反代到 FastAPI 后端，数据落 PostgreSQL 与 Redis；左下 GitHub Pages 托管公开静态站（零 Admin 代码），右下注明承载约束：2C4G 云主机加 swap、Docker 四服务栈、域名转入境内与 ICP 备案、含微信扫码须内地服务器、数据不出境。拓扑的每一条线都能在 compose 与 nginx 配置里找到对应行。</figcaption></figure>

再看部署侧，仓库里并存两套互补拓扑。根目录 `Dockerfile` 是单体形态：多阶段构建先在 builder 阶段编译 NURBS 内核的 Cython 扩展，运行阶段以非 root 用户（uid 1000）运行，声明 `/app/data` 与 `/app/logs` 两个卷，健康检查打 `/health`；根 `docker-compose.yml` 把它编排为四服务栈——backend、PostgreSQL 16、Redis 7（强制 `requirepass`）、nginx，数据库默认不对外暴露 5432，启动顺序由 `depends_on: service_healthy` 收敛。`deploy/` 目录是拆分形态：`backend.Dockerfile`（python:3.11-slim，非 root 的 appuser，`start.py` 入口，健康检查打 `/api/v1/health`）与 `frontend.Dockerfile`（node:20-alpine 里 `npm ci` 后 `vite build`，产物交给 nginx:1.27-alpine）分别构建，`deploy/docker-compose.yml` 只把 80 端口暴露给外界，`SECRET_KEY` 用 `${SECRET_KEY:?...}` 声明为必填，Redis 作为可选服务默认注释。

流量入口的最后一公里由 nginx 配置钉死。`deploy/nginx.conf` 关掉 `server_tokens`，`client_max_body_size 64m` 与后端 50MB 上传上限对齐，gzip 覆盖 JSON 与静态资源；`default.conf.template` 把路由写成五段：`/api/v1`、`/docs`、`/openapi.json` 反代后端并透传 `X-Request-ID` 与真实 IP（与第 12 章的审计链呼应），`/admin` 单独反代到后端托管的管理后台，带 hash 的 `/assets/` 与图片长缓存一年，未知路径回退 `index.html` 支撑 SPA，点文件（`.env`、`.git`）一律拒绝。发布面最小化则体现在分工上：gh-pages 公开静态站不含任何 Admin 代码，管理后台由后端 StaticFiles 在 `/admin/` 独立托管，登录门语义由后端把关。

首次部署的命令链因此很短：`npm run build` 产出 `dist/`，`docker compose up -d --build` 拉起全栈，全新数据库执行一次 `alembic upgrade head`，SQLite 老数据如需迁移由 `backend/scripts/migrate_sqlite_to_pg.py` 一次性完成。本地开发则是另一条已声明的拓扑：Vite 5173、FastAPI 8000、cpolar 4040 隧道；LLM 推理服务独立编排于 `docker-compose.llm.yml`，与主栈互不绑架。

**跨域映射。**

- 在本平台 = 前端产物、后端镜像与算法包版本一同锁定，回滚以整体为单位；在 LLM 应用 = 模型版本、提示词版本与评测基线必须随发布一同锁定，否则回滚无法复现当时的输出。
- 在本平台 = 构建分块与部署拓扑解耦，开发态与生产态只差一层接入；在 Agent 平台 = 能力清单随版本发布并对外可查，避免"文档说有、线上没有"。

【能力状态】构建分块、镜像与部署拓扑为【已实现·测试锁定】；灰度发布与自动回滚为路线图项【部分实现】。

## 四、反模式与代价

**无限细拆 chunk。** 迷信"越小越好"，把每个依赖拆成独立文件。请求数成倍增长，库级缓存被破坏，首屏反而更慢；体积告警驱动的拆分是虚荣工程。

**密钥烧进镜像。** 把 SECRET_KEY 写进 Dockerfile 或静态配置。镜像一旦推送即泄露，且无法在不大改产物的情况下轮换；密钥属于运行期，不属于构建期。

**数据库对公网开洞。** 为了"调试方便"把 5432 映射到宿主所有网卡。compose 里被注释掉的端口映射是一种设计：需要时临时放开、用完收回，而不是默认敞开。

**公开站携带管理代码。** 管理后台路由、菜单与 chunk 随公开静态站一起分发。攻击者不必猜到后台地址，直接下载源码慢慢研究；发布面每多一分，防线就薄一分。

**编排没有健康检查。** 依赖容器"启动了"就当"就绪了"，流量打到尚未完成初始化的进程。`depends_on` 配 `service_healthy` 不是仪式，是启动期错误的唯一防线。

**文档与产物漂移。** 站点上线后知识库停留在旧版本。文档必须随构建进入 `dist/`，与代码同批发布、同批回滚。

## 五、操作清单

1. 构建产物走 `npm run build`；改动 `manualChunks` 时同步更新注释中的决策理由。
2. 审查 `dist/` 的 chunk 清单：每个大文件能说出归属与存在理由，说不出即合并或删除。
3. 首次部署：`docker compose up -d --build`，随后 `docker compose exec backend bash -c "cd /app/backend && alembic upgrade head"`。
4. 生成密钥用 `python -c "import secrets; print(secrets.token_urlsafe(48))"`，只写 `.env`，不进任何 Dockerfile 与命令载荷。
5. 启动后核对健康检查：后端 `/api/v1/health` 与 nginx 探活全部通过再对外放流量。
6. nginx 只暴露 80/443；数据库与 Redis 端口默认不映射，临时调试限定 `127.0.0.1`。
7. 上传上限两端对齐：`client_max_body_size` 与后端 `MAX_FILE_SIZE` 保持一致口径。
8. 公开产物发布前检查零 Admin 代码：无 `/admin` 路由、无管理 chunk、无后台入口。
9. 数据卷（`pg-data`、`evoai-data`）纳入备份计划；容器可丢，卷不可丢。
10. 回滚预案与发布同练：静态站回滚镜像 tag，数据库变更坚持可逆迁移。

## 六、本章自检

1. 打开你的构建产物，每个 chunk 的存在理由能否在配置注释里找到？找不到的那些是意图还是意外？
2. 给你一台全新机器、一份仓库与一份 `.env`，一条命令能否复现整个拓扑？还差哪几步手工操作没被声明？
3. 你的公开产物里有没有不该出现的代码与秘密？你用什么检查证明"没有"，而不是相信"没有"？
