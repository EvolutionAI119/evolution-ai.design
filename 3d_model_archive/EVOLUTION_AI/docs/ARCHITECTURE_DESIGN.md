# EVOLUTION AI 项目架构设计（重构版）

> **作者**：EVOLUTION AI Development Team
> **时间**：2026年7月
> **状态**：已批准，重构完成
> **版本基线**：8143827（release: V1.01）

---

## 0. 项目定位

**EVOLUTION AI** —— NURBS驱动的参数化汽车造型开发平台

**核心闭环**：
```
硬点参数输入 → NURBS曲面生成 → G2连续性验证 → AI自动优化 → 多格式导出
   (14参数)       (15+曲面)       (曲率检查)       (模拟退火)      (GLB/STEP)
```

**目标用户**：
- **主用户**：汽车系统开发从业者，技术决策 + 演示
- **下游用户**：造型设计师、评审委员会、对外销售演示

**差异化**：
- 不是 DEMO 玩具 —— 是可工程化部署的全栈产品
- NURBS曲面引擎可独立剥离（不依赖 Web）—— 算法模型包已就绪
- 完整数据闭环（方案库 + 评估历史 + 优化曲线）
- 支持STEP格式导出，可对接工业CAD软件

---

## 1. 全景架构图

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EVOLUTION AI 架构（重构版）                       │
│                                                                       │
│  ╔══════════════════════════════════════════════════════════════════╗  │
│  ║                    L1: 表现层 (Frontend)                        ║  │
│  ╠══════════════════════════════════════════════════════════════════╣  │
│  ║  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         ║  │
│  ║  │参数编辑器│  │3D 预览   │  │质量报告  │  │AI 优化   │         ║  │
│  ║  │(Vue 3)   │  │(Three.js)│  │(ECharts) │  │(实时进度)│         ║  │
│  ║  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         ║  │
│  ║       └─────────────┴──────┬───────┴──────────────┘               ║  │
│  ╚═════════════════════════════╪═════════════════════════════════════╝  │
│                                ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  L2: API 网关层 (FastAPI + Uvicorn + Nginx)                    │   │
│  │  ─ REST API: /api/v1/{car|quality|optimize|storyboard|export}  │   │
│  │  ─ WebSocket: /ws/optimize/{task_id}  (实时进度推送)           │   │
│  │  ─ 静态资源: /static/{glb|step|png|html}                       │   │
│  └─────────────────────────────┬─────────────────────────────────┘   │
│                                ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  L3: 业务服务层 (Service Layer)                                │   │
│  │  ─ 建模服务    (CarModelService → NURBSCarBodyGenerator)       │   │
│  │  ─ 评估服务    (QualityService → NURBS质量评估)                │   │
│  │  ─ 优化服务    (OptimizeService, 异步任务)                      │   │
│  │  ─ 脚本服务    (StoryboardService)                              │   │
│  │  ─ 导出服务    (ExportService: GLB/STL/OBJ/STEP/PNG)           │   │
│  │  ─ 方案服务    (ProjectService: 增删改查)                       │   │
│  └─────────────────────────────┬─────────────────────────────────┘   │
│                                ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  L4: NURBS引擎层 (NURBS Engine) ← 重构核心 ✅                   │   │
│  │  ─ nurbs_engine/          (ControlPoint/KnotVector/NURBSSurface)│   │
│  │  ─ car_body_generator/    (NURBSCarBodyGenerator, 34部件)      │   │
│  │  ─ surface_quality/       (G0/G1/G2 评估 + AI 优化)            │   │
│  │  ─ storyboard/            (3 套模板 + 自定义分镜)              │   │
│  │  ─ api.py                 (5 大统一门面 API)                   │   │
│  └─────────────────────────────┬─────────────────────────────────┘   │
│                                ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  L5: 基础设施层 (Infrastructure)                                 │   │
│  │  ─ 数据: SQLite (方案库) + JSON (评估历史)                       │   │
│  │  ─ 缓存: Redis (优化任务结果 / 会话)                             │   │
│  │  ─ 队列: Celery (异步 AI 优化任务)                               │   │
│  │  ─ 监控: Loguru + Prometheus  (后续 M4 引入)                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术选型

| 层级 | 选型 | 理由 | 状态 |
|------|------|------|------|
| **前端框架** | Vue 3 + Vite | 渐进式，TypeScript 友好，生态成熟 | ✅ 完成 |
| **3D 渲染** | Three.js | 业界标准，GLB/OBJ 格式原生支持 | ✅ 完成 |
| **3D 高保真** | (可选) Blender + Python API | 静态图 / 视频出图 | M3 引入 |
| **数据可视化** | ECharts | 国产开源，中文友好，曲线/雷达图强 | ✅ 完成 |
| **UI 组件** | Element Plus | Vue 3 官方推荐 | ✅ 完成 |
| **后端框架** | FastAPI | 异步原生，自动 OpenAPI 文档 | ✅ 完成 |
| **ASGI 服务器** | Uvicorn | 性能稳定，FastAPI 官方推荐 | ✅ 完成 |
| **数据校验** | Pydantic v2 | FastAPI 原生 | ✅ 完成 |
| **NURBS引擎** | 自研 nurbs_engine/ | 完整实现B样条基函数和曲面评估 | ✅ 完成 |
| **车身生成** | NURBSCarBodyGenerator | 集成NURBS引擎，G2连续 | ✅ 完成 |
| **数据库** | SQLite (开发) / PostgreSQL (生产) | 轻量起步，零配置 | ✅ 完成 |
| **缓存** | Redis (可选) | 优化任务结果缓存 | M3 引入 |
| **异步任务** | Celery + Redis broker | AI 优化耗时 5s+，需异步 | M2 引入 |
| **数据迁移** | Alembic | SQLAlchemy 官方 | M2 引入 |
| **日志** | Loguru | 比 logging 简单 10 倍 | ✅ 完成 |
| **测试** | pytest + httpx | FastAPI 官方推荐 | ✅ 完成 |
| **容器化** | Docker + docker-compose | 一键启动 | M4 引入 |
| **反向代理** | Nginx (生产) | 静态资源 + HTTPS | M4 引入 |

---

## 3. 目录结构

```
D:\API\EVOLUTION_AI\3d_model_archive\EVOLUTION_AI\
│
├── README.md                              # 项目总览
├── ARCHITECTURE_DESIGN.md                # 本文档（重构版）
├── docker-compose.yml                     # 一键启动编排（M4）
├── .env.example                           # 环境变量模板
├── pyproject.toml                         # 项目元数据 + 依赖
│
├── backend/                               # ★ 后端服务（FastAPI）
│   ├── main.py                            # FastAPI app 入口
│   ├── config.py                          # Pydantic Settings
│   ├── deps.py                            # 依赖注入
│   │
│   ├── app/
│   │   ├── modules/
│   │   │   ├── nurbs_engine.py            # ★ NURBS曲面引擎
│   │   │   └── car_body_generator.py      # ★ NURBS车身生成器
│   │   ├── api/                           # 路由层
│   │   │   ├── v1/
│   │   │   │   ├── car.py                 # /api/v1/car/* (建模)
│   │   │   │   ├── quality.py             # /api/v1/quality/* (评估)
│   │   │   │   ├── optimize.py            # /api/v1/optimize/* (优化)
│   │   │   │   ├── storyboard.py          # /api/v1/storyboard/* (脚本)
│   │   │   │   ├── project.py             # /api/v1/project/* (方案库)
│   │   │   │   └── export.py              # /api/v1/export/* (导出)
│   │   │   └── websocket/
│   │   │       └── optimize.py            # /ws/optimize/{task_id}
│   │   ├── services/                      # 业务服务层
│   │   │   ├── car_model_service.py       # 封装 NURBSCarBodyGenerator
│   │   │   ├── quality_service.py         # 封装 NURBS质量评估
│   │   │   ├── optimize_service.py        # 封装 optimize_surface
│   │   │   ├── storyboard_service.py      # 封装 make_storyboard
│   │   │   ├── export_service.py          # GLB/STL/OBJ/STEP 转换
│   │   │   └── project_service.py         # 方案库 CRUD
│   │   ├── models/                        # Pydantic 数据模型
│   │   ├── db/                            # 数据层
│   │   ├── tasks/                         # 异步任务 (Celery)
│   │   ├── utils/                         # 工具
│   │   └── tests/                         # 后端测试
│   │
│   └── config/
│       └── automotive_parameters.json     # 车辆参数配置
│
├── frontend/                              # ★ 前端（Vue3）
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   ├── stores/                        # Pinia 状态管理
│   │   ├── api/                           # axios 封装
│   │   ├── components/
│   │   │   ├── CarPreview/                # Three.js 3D 预览
│   │   │   ├── ParamEditor/               # 参数编辑器
│   │   │   ├── QualityReport/             # 评估报告
│   │   │   └── OptimizeProgress/          # 优化进度 (WebSocket)
│   │   ├── views/
│   │   │   ├── Designer.vue               # 设计师主界面
│   │   │   ├── Quality.vue
│   │   │   ├── Optimize.vue
│   │   │   └── Storyboard.vue
│   │   └── assets/
│   └── public/
│
├── algorithm_model/                       # ★ 独立算法包（30文件）
│   ├── api.py                             # 5 大统一对外 API
│   ├── main.py                            # CLI 入口（7 个子命令）
│   ├── test_all.py                        # 一站式自检（5/5全过）
│   ├── car_modeling/                      # 参数化车身建模（9文件）
│   ├── surface_quality/                   # G0/G1/G2 评估 + AI 优化
│   ├── storyboard/                        # 3 套模板 + 自定义分镜
│   └── storyboard_viewer/                 # MD + HTML 渲染
│
├── docs/                                  # ★ 核心文档
│   ├── ARCHITECTURE_DESIGN.md             # 本文档
│   ├── EVOLUTION_AI_Methodology_2.0.md    # 方法论（2.0-R）
│   ├── algorithm_summary.md               # 算法总结（V1.01-R）
│   ├── flowchart_five_phases.md           # 五阶段流程
│   └── 算法模型交付总结.md                 # 交付总结（重构版）
│
├── outputs/                               # 产物集中目录
│   ├── cars/                              # GLB 模型
│   ├── reports/                           # 评估报告
│   ├── storyboards/                       # 分镜 (md/html/json)
│   └── snapshots/                         # 静态图 (PNG)
│
└── scripts/                               # 运维脚本
    ├── start_dev.sh                       # 开发启动
    ├── start_prod.sh                      # 生产启动
    └── seed_data.py                       # 种子数据
```

---

## 4. 核心引擎架构

### 4.1 NURBS引擎层

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NURBS引擎层                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ControlPoint                                                      │
│  ├─ x, y, z: 坐标                                                  │
│  ├─ weight: 权重                                                   │
│  ├─ to_array(): 转换为numpy数组                                    │
│  └─ from_array(): 从numpy数组创建                                  │
├─────────────────────────────────────────────────────────────────────┤
│  KnotVector                                                        │
│  ├─ values: 节点值列表                                             │
│  ├─ normalize(): 归一化                                            │
│  ├─ to_json() / from_json(): JSON序列化                            │
│  └─ _create_uniform_knot_vector(): 创建均匀节点矢量                 │
├─────────────────────────────────────────────────────────────────────┤
│  NURBSCurve                                                        │
│  ├─ degree: 曲线阶次                                               │
│  ├─ control_points: 控制点列表                                     │
│  ├─ knot_vector: 节点矢量                                          │
│  ├─ evaluate_point(t): 计算曲线上的点                              │
│  ├─ _evaluate_basis_function(): B样条基函数计算                     │
│  └─ compute_length(): 计算曲线长度                                  │
├─────────────────────────────────────────────────────────────────────┤
│  NURBSSurface                                                      │
│  ├─ degree_u / degree_v: 曲面阶次                                  │
│  ├─ control_points: 控制点矩阵                                      │
│  ├─ knot_vector_u / knot_vector_v: 节点矢量                        │
│  ├─ evaluate_point(u, v): 计算曲面上的点                            │
│  ├─ evaluate_normal(u, v): 计算法向量                              │
│  ├─ evaluate_curvature(u, v): 计算曲率                            │
│  ├─ modify_control_point(): 修改控制点                              │
│  ├─ _evaluate_basis_function(): B样条基函数计算                     │
│  └─ _initialize_knot_vectors(): 初始化节点矢量                      │
├─────────────────────────────────────────────────────────────────────┤
│  SurfaceModifier                                                   │
│  ├─ translate(): 平移                                              │
│  ├─ scale(): 缩放                                                  │
│  ├─ rotate(): 旋转                                                 │
│  └─ offset(): 偏移                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 NURBS车身生成器

**NURBSCarBodyGenerator** 类结构：

```python
class NURBSCarBodyGenerator:
    # 初始化
    __init__(config_path)           # 加载配置，初始化坐标系
    
    # 坐标系初始化
    _initialize_coordinate_system() # 设置L/W/H/WB/TW/GC/FO/RO
    
    # NURBS工具方法
    _create_nurbs_surface_from_points()  # 从3D点创建NURBS曲面
    _evaluate_nurbs_surface()            # 采样NURBS曲面
    
    # 车身部件生成（NURBS曲面）
    generate_hood()              # 发动机盖
    generate_windshield()        # 前风挡玻璃
    generate_roof()              # 车顶
    generate_rear_window()       # 后风挡玻璃
    generate_trunk()             # 行李箱盖
    generate_door_front()        # 前门
    generate_door_rear()         # 后门
    generate_bumper_front()      # 前保险杠
    generate_bumper_rear()       # 后保险杠
    generate_fender()            # 翼子板
    
    # 车身部件生成（基础几何）
    generate_headlight()         # 前大灯
    generate_taillight()         # 后尾灯
    generate_grille()            # 进气格栅
    generate_wheel()             # 车轮
    generate_mirror()            # 后视镜
    generate_pillar()            # 立柱
    generate_door_seam()         # 车门分缝
    
    # 整车组装与导出
    generate_complete_car()      # 生成完整汽车模型
    export_car_data()            # 导出JSON数据
    export_glb()                 # 导出GLB格式
    export_stl()                 # 导出STL格式
    export_obj()                 # 导出OBJ格式
    export_step()                # 导出STEP格式（AP214）
```

---

## 5. 数据流

### 5.1 主流程：参数 → NURBS曲面 → 3D模型

```
用户 (Vue3)
   │ 1. 调整 14 维硬点参数
   ▼
前端 ParamEditor
   │ 2. POST /api/v1/car/build  {params}
   ▼
FastAPI 路由
   │ 3. 调用 CarModelService
   ▼
NURBSCarBodyGenerator.generate_complete_car()
   │ 4. 硬点推导 → NURBS控制点布局 → 曲面生成 → 质量评估
   │ 5. 返回 34 部件数据（含NURBS曲面信息）
   ▼
ExportService.to_glb(parts)
   │ 6. NURBS曲面采样 → 三角面构建 → GLB编码
   ▼
Response { glb_url, stats, nurbs_quality }
   │
   ▼
前端 CarPreview
   │ 7. GLTFLoader 加载 /static/cars/{hash}.glb
   ▼
Three.js 渲染
```

### 5.2 NURBS曲面生成流程

```
硬点参数输入
   │
   ▼
坐标系初始化 (L, W, H, WB, TW, GC, FO, RO)
   │
   ▼
轮心坐标计算 (fwx, rwx, wcy, fwz)
   │
   ▼
A/C柱位置推导 (aBaseX, aTopY, cBaseX, cTopY)
   │
   ▼
按部件生成NURBS曲面：
   ├─ 发动机盖 (degree_u=5, degree_v=3, num_u=12, num_v=8)
   ├─ 前风挡 (degree_u=3, degree_v=3, num_u=8, num_v=6)
   ├─ 车顶 (degree_u=5, degree_v=3, num_u=10, num_v=8)
   ├─ 后风挡 (degree_u=3, degree_v=3, num_u=8, num_v=6)
   ├─ 行李箱盖 (degree_u=3, degree_v=3, num_u=8, num_v=6)
   ├─ 翼子板 (degree_u=3, degree_v=3, num_u=6, num_v=6)
   ├─ 车门 (degree_u=3, degree_v=3, num_u=8, num_v=8)
   └─ 保险杠 (degree_u=3, degree_v=3, num_u=6, num_v=8)
   │
   ▼
曲面质量评估（法向量、曲率、G2连续性）
   │
   ▼
车身网格生成（NURBS采样 + 三角面构建）
   │
   ▼
导出（GLB/STL/OBJ/STEP）
```

### 5.3 AI 优化（异步 + WebSocket）

```
用户点击"开始优化"
   │ 1. POST /api/v1/optimize/start  {surface_id, max_iter}
   ▼
FastAPI 路由
   │ 2. 生成 task_id，推入 Celery
   │ 3. 立即返回 { task_id, ws_url }
   ▼
前端建立 WebSocket
   │ 4. WS /ws/optimize/{task_id}
   ▼
Celery Worker 执行 optimize_surface
   │ 5. 每 10 步 publish {progress, best_score, g2_ratio}
   ▼
WebSocket 推送到前端
   │ 6. OptimizeProgress 组件实时更新
   ▼
完成后推送 {done: true, result_url}
   │
   ▼
前端 QualityReport 渲染最终报告
```

---

## 6. API 设计

### 6.1 REST API

| 方法 | 路径 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET | `/api/v1/car/params/default` | 默认参数 | - | CarParams |
| POST | `/api/v1/car/build` | 构建 NURBS 车身 | CarParams | {glb_url, stats, nurbs_quality} |
| POST | `/api/v1/car/validate` | 参数越界校验 | CarParams | {valid, errors} |
| POST | `/api/v1/quality/assess` | 评估曲面质量 | {points, panel_name} | QualityReport |
| POST | `/api/v1/optimize/start` | 启动优化 | {points, panel_name, max_iter} | {task_id, ws_url} |
| GET | `/api/v1/optimize/{task_id}` | 查询优化结果 | - | OptimizationResult |
| POST | `/api/v1/storyboard/generate` | 生成分镜 | {product_name, style, ...} | {md, html, json} |
| GET | `/api/v1/storyboard/templates` | 列出模板 | - | [template_name, ...] |
| GET | `/api/v1/project/list` | 方案列表 | ?skip&limit | [Project, ...] |
| POST | `/api/v1/project/save` | 保存方案 | {name, params, ...} | {project_id} |
| GET | `/api/v1/export/{format}/{id}` | 导出 | ?format=glb/stl/obj/step | file |

### 6.2 WebSocket

| 路径 | 功能 | 消息格式 |
|------|------|---------|
| `/ws/optimize/{task_id}` | 优化进度 | `{progress: 0~100, best_score, g2_ratio, current_iter, done}` |

### 6.3 OpenAPI 文档

FastAPI 自动生成 `/docs`（Swagger UI）和 `/redoc`，无需额外配置。

---

## 7. 关键子系统设计

### 7.1 CarModelService（建模服务）

**职责**：参数校验 → 调用 NURBSCarBodyGenerator → 导出 GLB/STEP → 缓存

```python
class CarModelService:
    def build(self, params: CarParams) -> BuildResult:
        # 1. Pydantic 校验
        # 2. 调用 NURBSCarBodyGenerator
        generator = NURBSCarBodyGenerator()
        car = generator.generate_complete_car()
        # 3. 导出 GLB
        glb_bytes = generator.export_glb(temp_path)
        # 4. 导出 STEP（可选）
        step_bytes = generator.export_step(temp_path)
        # 5. 存文件 + 算 hash
        glb_hash = sha256(glb_bytes).hexdigest()[:16]
        # 6. 返回 URL 和质量信息
        return BuildResult(
            glb_url=f"/static/cars/{glb_hash}.glb",
            stats=...,
            nurbs_quality=car['nurbs_quality']
        )
```

**缓存策略**：相同 params hash 命中缓存（Redis，M3 引入）

### 7.2 NURBS质量评估

**职责**：验证曲面连续性，输出质量报告

```python
class NURBSQualityService:
    def assess_surface(self, surface: NURBSSurface) -> QualityReport:
        # 1. 边界点检查（G0连续）
        # 2. 法向量检查（G1连续）
        # 3. 曲率检查（G2连续）
        # 4. 斑马纹评分
        # 5. 高光轨迹评分
        return QualityReport(
            grade=grade,
            g2_ratio=g2_ratio,
            reflection_score=reflection_score,
            curvature_stats=curvature_stats
        )
```

### 7.3 ExportService（导出服务）

支持格式：
- **GLB**（主用，Three.js / Web 原生）
- **STL**（3D 打印）
- **OBJ**（Blender / Maya 通用）
- **STEP**（AP214，工程CAD对接）
- **PNG**（matplotlib 静态图）

---

## 8. 前端架构

### 8.1 路由结构

```
/                       # 首页 (项目概览)
/designer               # 设计师主界面 (参数 + 预览)
  ├─ /designer/params   # 参数编辑
  ├─ /designer/preview  # 3D 预览
  └─ /designer/export   # 导出
/quality                # 质量评估
/optimize               # AI 优化 (WebSocket)
/storyboard             # 视频脚本
/projects               # 方案库
  └─ /projects/:id      # 方案详情
```

### 8.2 状态管理（Pinia）

```typescript
// stores/car.ts
export const useCarStore = defineStore('car', {
  state: () => ({
    params: defaultCarParams,
    glbUrl: null,
    stats: null,
    nurbsQuality: null,
    loading: false,
  }),
  actions: {
    async build() { /* POST /api/v1/car/build */ },
    async validate() { /* POST /api/v1/car/validate */ },
  },
})

// stores/optimize.ts
export const useOptimizeStore = defineStore('optimize', {
  state: () => ({
    taskId: null,
    ws: null,
    progress: 0,
    bestScore: null,
    g2Ratio: null,
    done: false,
  }),
  actions: {
    start() { /* POST /api/v1/optimize/start + WS */ },
  },
})
```

### 8.3 Three.js 集成

- **GLTFLoader** 加载 GLB
- **OrbitControls** 旋转缩放
- **网格化 + 材质**：
  - 车壳：金属漆材质（MeshStandardMaterial，metalness=0.7）
  - 玻璃：透明 + 反射（MeshPhysicalMaterial，transmission=0.9）
  - 轮毂：金属 + 辐条
  - 灯：自发光（emissive）

---

## 9. 性能基线

| 操作 | 耗时 | 数据量 | 备注 |
|------|------|--------|------|
| NURBS车身生成（34部件） | ~250ms | 776+控制点 | G2连续 |
| NURBS曲面评估（单部件） | ~10ms | 20×16采样点 | |
| GLB导出 | < 0.1s | ~130KB | |
| STEP导出 | < 0.5s | B样条曲面 | AP214 |
| 默认参数整车建模 | < 0.5s | 3475 顶点 / 6504 面 | |
| 车身曲面质量评估 | < 0.3s | QualityReport | |
| AI优化（80步） | ~1-5s | OptimizationResult | |
| 7镜视频脚本生成 | < 0.05s | Storyboard | |
| **一站式自检** | **9.5s** | **5模块全过** | |

**优化策略**：
- 同 params 缓存 GLB（hash 命中省 250ms）
- AI 优化必须异步（5s+ 必阻塞）
- 评估结果用 Redis 缓存（key=points_hash）
- 静态资源走 CDN（Nginx，M4）

---

## 10. 安全设计

| 维度 | 措施 |
|------|------|
| **API 鉴权** | JWT Token (M3 引入，M1-M2 先开放) |
| **参数越界** | Pydantic + CarParams.validate() 双重校验 |
| **文件上传** | 限制类型（仅 .glb/.stl/.obj/.step）+ 大小（<50MB） |
| **CORS** | 限定 origin（生产环境） |
| **限流** | slowapi（IP 维度 100 req/min） |
| **SQL 注入** | SQLAlchemy ORM（无裸 SQL） |
| **XSS** | Vue 3 自动转义 + CSP 头 |
| **路径遍历** | 文件名 hash 化，不接受用户路径 |

---

## 11. 重构核心变化

### 11.1 架构变化

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| 曲面生成 | 简单参数函数 (sin/cos/exp) | NURBS曲面引擎 |
| 连续性 | 手动拼接，无保证 | G2曲率连续 |
| 控制点 | 无 | 完整NURBS控制点布局 |
| 曲面质量 | 无法量化 | 可计算曲率、法向量 |
| 可扩展性 | 差 | 支持任意degree和控制点 |
| STEP导出 | 不支持 | AP214格式B样条曲面 |

### 11.2 功能变化

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| 车身部件数 | 8个 | 34个 |
| NURBS曲面数 | 0 | 15+ |
| 控制点总数 | 0 | 776+ |
| 导出格式 | GLB/STL/OBJ | GLB/STL/OBJ/STEP |
| 质量评估 | 三角网格级别 | NURBS曲面级别 |

---

## 12. 迭代路线（4 个里程碑）

### M1: MVP —— 后端 + CLI（已完成）
- ✅ FastAPI 项目骨架
- ✅ 5 大 API 路由
- ✅ NURBS曲面引擎集成
- ✅ 静态资源服务
- ✅ 后端单元测试

### M2: 数据库 + 异步任务（进行中）
- [ ] SQLAlchemy + Alembic 初始化
- [ ] Project 模型 + CRUD API
- [ ] Celery + Redis 接入
- [ ] 优化任务改异步

### M3: 前端 + WebSocket（进行中）
- ✅ Vue 3 + Vite 项目骨架
- ✅ Three.js 3D 预览组件
- ✅ 14 维参数编辑器
- [ ] WebSocket 实时优化进度
- [ ] 方案库管理

### M4: 部署 + 监控（规划中）
- [ ] Dockerfile + docker-compose.yml
- [ ] Nginx 配置（HTTPS + 反代）
- [ ] Loguru 日志结构化
- [ ] Prometheus 指标
- [ ] CI/CD（GitHub Actions）

---

## 13. 与现有产物映射

| 现有产物 | 在新架构中的位置 | 备注 |
|---------|----------------|------|
| `nurbs_engine.py` | L4 NURBS引擎层 | **核心重构**，新增 |
| `car_body_generator.py` | L4 NURBS车身生成器 | **核心重构**，NURBSCarBodyGenerator |
| `algorithm_model/api.py` | L4 算法层 | 保留，作为后端服务依赖 |
| `algorithm_model/main.py` | CLI 入口 | 保留，运维/调试用 |
| `algorithm_model/test_all.py` | 测试基线 | **不动**，每次发布前跑 |
| `frontend/src/views/Designer.vue` | L1 表现层 | ✅ 已完成 |
| `frontend/src/components/Car3D.vue` | L1 表现层 | ✅ 已完成 |

---

## 14. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| NURBS曲面计算耗时 | 响应延迟 | 缓存策略 + 异步计算 |
| 复杂参数导致模型过大 | 加载慢 | 简化策略（LOD）+ 压缩（draco）|
| Three.js 学习曲线 | 前端延期 | M3 单独排期 + 用现成示例 |
| SQLite 并发写入 | 方案丢失 | M2 升级 PostgreSQL |
| Celery 部署复杂 | M2 延期 | M1 先用 FastAPI BackgroundTasks |
| 三方库升级破坏 API | 重构 | requirements 锁版本 + 测试覆盖 |

---

## 15. 总结

**核心思路**：
1. **NURBS引擎先行** ✅（已完成，15+曲面，G2连续）
2. **后端承上启下**（M1-M2）：把NURBS引擎包成 RESTful + WebSocket
3. **前端发力**（M3）：把后端装进 Three.js + Vue 3
4. **工程化收尾**（M4）：Docker + Nginx + 监控

**关键决策**：
- **NURBS引擎与Web完全解耦**：引擎可独立运行、可独立测试、可被其他项目直接引用
- **后端只做编排，不重写算法**：服务层是薄壳，调 NURBSCarBodyGenerator 即可
- **异步优先**：所有 > 1s 的操作（AI 优化 / 视频生成）默认异步 + 任务队列
- **数据结构稳定**：5 大 API 数据类签名冻结，前端按字段渲染

**预期产出**：
- 完整 Web 平台（参数编辑 → NURBS曲面生成 → 质量评估 → AI 优化 → 视频脚本 → 方案管理）
- 一键 Docker 启动
- OpenAPI 自动文档
- STEP格式导出，可对接工业CAD软件
- 主对话演示流程跑通

---

**基线版本：8143827**

*EVOLUTION AI Development Team*
*2026年7月*