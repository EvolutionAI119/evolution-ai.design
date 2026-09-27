# EVOLUTION AI

> 下一代 AI 汽车造型开发平台 — 从一句话到 3D 整车，全链路 AI 辅助设计

![Status](https://img.shields.io/badge/status-v1.02--stable-brightgreen) ![Version](https://img.shields.io/badge/version-1.2.0-blue) ![Frontend](https://img.shields.io/badge/frontend-Vue%203%20%2B%20Vite%20%2B%20Three.js-blue) ![Backend](https://img.shields.io/badge/backend-FastAPI-green)

---

## 🎯 项目愿景

让汽车造型设计进入「**说一句话，就出 3D 整车**」的时代。
从概念草图 → 参数化建模 → AI 优化 → 视频分镜 → 工程交付，一气呵成。

---

## 📦 当前状态 (v1.02-stable, 2026-08-02)

治乱后稳定基线，作为 NURBS+STEP 工程化管线开发起点。

| 模块 | 状态 | 技术栈 | 说明 |
|------|------|--------|------|
| **前端** | ✅ 可运行 | Vue 3 + Vite 5 + Three.js + Element Plus + Pinia | 8 个路由页面，3D 实时渲染，i18n 双语 |
| **后端** | ✅ 可运行 | FastAPI + SQLAlchemy 2.0 + Celery + Redis | 21 端点，4 张 ORM 表，异步任务队列 |
| **算法层** | ✅ 黑盒 | Python 3.11+ / NumPy / SciPy / Trimesh | 5 大 API / 7 CLI / 155 测试通过 |
| **Mock Fallback** | ✅ 已集成 | - | backend 不可用时显示 10 个 mock 项目 + SVG 预览 |
| **NURBS+STEP 管线** | ⏳ 规划中 | 纯 Python STEP writer | 按 [技术审计报告](docs/TECHNICAL_AUDIT_20260801.md) Phase 0→4 推进 |

---

## 🚀 快速开始

唯一活跃开发目录：`D:\API\Evolution-Ai.Design`

### 1. 启动前端 (Vite Dev Server, 端口 5173)

```powershell
cd D:\API\Evolution-Ai.Design
npm install      # 首次运行
npm run dev      # 启动开发服务器
# 访问 http://localhost:5173/
```

路由使用 Hash 模式（适配 GitHub Pages 静态部署）：
- 首页：`http://localhost:5173/#/`
- AI 设计器：`http://localhost:5173/#/designer`
- 项目列表：`http://localhost:5173/#/projects`
- 项目详情：`http://localhost:5173/#/projects/1`

### 2. 启动后端 (FastAPI, 端口 8000, 可选)

前端已内置 mock fallback，后端可选。如需完整功能：

```powershell
cd D:\API\Evolution-Ai.Design\backend
pip install -r requirements.txt

# 起 Redis (M2 必装)
redis-server --port 6379

# 起 Celery worker (M2 必起, 新终端)
.\start_celery_worker.bat

# 起 FastAPI
.\start_backend.bat
# API 文档：http://localhost:8000/docs
```

### 3. 构建生产版本

```powershell
npm run build     # 输出到 dist/
npm run preview   # 本地预览生产构建
```

### 4. 跑测试

```powershell
# 前端测试
npm test

# 后端测试
cd backend
pytest tests/ -v

# 算法层自检
cd algorithm_model
python test_all.py
```

---

## 🏗️ 架构设计

详见：[`docs/ARCHITECTURE_DESIGN.md`](docs/ARCHITECTURE_DESIGN.md)

**核心架构 5 层分层**：

```
L1 前端层    ─  Vue 3 + Three.js + Element Plus + Pinia
L2 API 网关  ─  Vite Dev Proxy (/api/v1 → 8000, /api/ide → trae-api-cn)
L3 后端服务  ─  FastAPI + 6 大薄壳服务 (编排不重写算法)
L4 算法层    ─  algorithm_model (5 大 API / 7 CLI, 黑盒使用)
L5 基础设施  ─  SQLite + Redis + Celery + 文件存储
```

**关键设计决策**：
1. ✅ 算法模型与 Web 完全解耦（可独立 pip install）
2. ✅ 后端只做编排，不重写算法
3. ✅ 异步优先（>1s 操作走 Celery，API 返回 `202 + task_id`）
4. ✅ 前端内置 mock fallback（backend 不可用时不黑屏）

---

## 📂 项目结构

```
Evolution-Ai.Design/
├── src/                            ← Vue 3 前端源码
│   ├── views/                      ← 8 个路由页面
│   │   ├── Dashboard.vue           ← 首页总览
│   │   ├── Designer.vue            ← AI 设计器 (参数+3D预览)
│   │   ├── Projects.vue            ← 项目列表 (含 mock fallback)
│   │   ├── ProjectDetail.vue       ← 项目详情
│   │   ├── DeepLearning.vue        ← 深度学习设计器
│   │   ├── Quality.vue             ← 质量检查
│   │   ├── Deliver.vue             ← 工程交付
│   │   └── Demo.vue                ← DEMO 演示
│   ├── components/                 ← 复用组件 (Car2D/Car3D/Markdown/TechMatrix)
│   ├── stores/                     ← Pinia 状态 (designer/project/ui)
│   ├── data/                       ← mock 数据 (mockProjects) + 配置
│   ├── utils/                      ← imageGenerator (SVG) + llm
│   ├── api.js                      ← axios 实例 + API 模块
│   ├── router.js                   ← vue-router (Hash 模式)
│   ├── i18n.js                     ← vue-i18n 双语
│   └── main.js                     ← 应用入口
├── backend/                        ← FastAPI 后端
│   ├── app/
│   │   ├── routes/                 ← 9 个路由模块 (build/car/export/...)
│   │   ├── car_generator.py        ← 车身生成器
│   │   ├── database.py             ← SQLAlchemy 2.0 ORM
│   │   └── main.py                 ← FastAPI 入口
│   ├── tests/                      ← pytest 测试
│   └── requirements.txt
├── algorithm_model/                ← 算法核心 (黑盒使用)
│   ├── car_modeling/               ← 整车建模 (body/assembler/wheels/...)
│   ├── surface_quality/            ← 曲面质量 (G0/G1/G2 + 反射线)
│   ├── freeform/                   ← NURBS 核心 + 扫掠 + 圆角
│   └── tests/                      ← 155 测试通过
├── docs/                           ← 文档
│   ├── TECHNICAL_AUDIT_20260801.md ← ⭐ NURBS+STEP 技术路线审计报告
│   ├── ARCHITECTURE_DESIGN.md      ← 架构设计 v1.0
│   ├── PRODUCT_SPEC.md             ← 产品功能定义
│   ├── DESIGN_TOKENS.md            ← 设计令牌
│   ├── W1~W4_*.md                  ← 周报与完结报告
│   └── 复盘总结_20260711.md        ← 历史复盘
├── tests/                          ← 前端 vitest 测试
├── vite.config.js                  ← Vite 配置 (端口 5173, 代理)
├── package.json                    ← npm 依赖
└── index.html                      ← HTML 入口
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| **前端** | Vue 3.4 / Vite 5.3 / Three.js 0.166 / Element Plus 2.7 / Pinia 2.1 / vue-router 4.4 / vue-i18n 9.13 / axios 1.7 |
| **后端** | FastAPI / Pydantic v2 / SQLAlchemy 2.0 / Celery 5 / Redis 6 / Uvicorn / Loguru |
| **算法层** | Python 3.11+ / NumPy / SciPy / Trimesh / Plotly / Cython (399x 加速) |
| **数据库** | SQLite (开发) → PostgreSQL (生产) |
| **部署** | Docker + Nginx (规划中) / GitHub Pages (静态) |

---

## 🎯 下一阶段路线图 (NURBS+STEP 工程化)

按 [技术审计报告](docs/TECHNICAL_AUDIT_20260801.md) 的"双轨并行"策略推进：

```
Phase 1a (1天)    Phase 1b (0.5天)   Phase 2 (2-3天)    Phase 3 (2-3天)
STEP writer    →  单曲面闭环      →  车身 NURBS化    →  全车 STEP 装配
~200行 Python     SweptSurface       body.py 改造       14 零件导出
                  验证 STEP 可打开   mesh→控制点        FreeCAD 验证
```

**核心策略**：
- mesh 管线（现有）→ 继续用于前端实时预览、GLB 导出
- NURBS 管线（新建）→ 用于 STEP/IGES 工程输出、A级曲面质量分析
- 纯 Python STEP writer（无需 OCCT/build123d 500MB 依赖）
- 参数直驱 NURBS（避免 mesh→NURBS 拟合误差）

---

## 📊 性能基线

| 场景 | 耗时 | 指标 |
|------|------|------|
| 整车构建 | ~200ms | 3475 顶点 / 6504 面 |
| 球面质量评估 | 50.8ms | grade=D / g2=0.199 |
| 后端测试 | 3.04s | 15/15 通过 |
| 端到端测试 | 7.85s | 19/19 通过 |
| 算法层自检 | 9.49s | 155/155 通过 (零回归) |
| Cython 加速 | 0.40ms/板 | 399x 加速 |

---

## 🎬 3 套预设方案

| 方案 | L (m) | W (m) | H (m) | 风格 |
|------|-------|-------|-------|------|
| **sport** | 4.50 | 1.85 | 1.30 | 跑车 |
| **luxury** | 5.20 | 1.95 | 1.50 | 豪华轿车 |
| **suv** | 4.80 | 1.95 | 1.72 | SUV |

---

## 📚 文档导航

- [⭐ NURBS+STEP 技术审计报告](docs/TECHNICAL_AUDIT_20260801.md) — 下一阶段路线图（必读）
- [贝叶斯优化模块使用文档](docs/bayes_optimization.md) — GP + EI/UCB 代理寻优容器，与训练模块联动
- [架构设计 v1.0](docs/ARCHITECTURE_DESIGN.md) — 5 层分层设计
- [产品功能定义](docs/PRODUCT_SPEC.md) — 需求与场景
- [设计令牌](docs/DESIGN_TOKENS.md) — UI 设计规范
- [算法模型文档](algorithm_model/README.md) — 5 大 API + 7 CLI 速查
- [复盘总结 20260711](docs/复盘总结_20260711.md) — 历史复盘
- [W1~W4 周报](docs/) — 开发周报与完结报告

---

## 📝 开发规范

- **算法层零修改**：`algorithm_model/` 是黑盒，service 层只调不写
- **后端服务薄壳**：每个 service 10-50 行，纯调度
- **字段 100% 对齐**：Pydantic model 与 algorithm_model 数据类签名必须严格一致
- **测试驱动**：新功能必须配测试用例
- **M2 异步约定**：>1s 操作走 Celery，API 返回 `202 + task_id`，客户端轮询 `GET /api/v1/task/{tid}`
- **Mock Fallback 优先**：前端关键页面必须有 mock 数据兜底，backend 不可用时不黑屏
- **Hash 路由**：使用 `createWebHashHistory` 适配 GitHub Pages 静态部署

---

## 🤝 协作约定

- **唯一活跃目录**：`D:\API\Evolution-Ai.Design` （`D:\API\EVOLUTION_AI` 已退役）
- **外部归档**：`D:\API\_archive\` （历史快照与 tar.gz）
- **沟通风格**：先结论后依据；少解释过程
- **文件引用**：用绝对路径
- **周复盘节奏**：每周一次复盘，沉淀到 `docs/weekly-reviews/`
- **版本发布**：成熟版本及时更新 GitHub 仓库，让网站早日恢复常态化运行

---

## 📜 License

Proprietary — 内部项目

---

<p align="center">
  <em>「说一句话，就出 3D 整车」— EVOLUTION AI</em>
</p>
