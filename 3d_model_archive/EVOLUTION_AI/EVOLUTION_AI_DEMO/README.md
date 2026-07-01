# EVOLUTION AI

> 参数化 + AI 驱动的汽车造型开发平台

---

## 项目状态

| 阶段 | 状态 | 关键产物 |
|------|------|---------|
| 算法核心 | ✅ 已交付 | `algorithm_model/` v1.0.0 (5/5 自检通过) |
| 架构设计 | ✅ 已完成 | `docs/ARCHITECTURE_DESIGN.md` |
| 后端 MVP (M1) | ⏳ 待启动 | `backend/` (FastAPI) |
| 前端 (M3) | ⏳ 待启动 | `frontend/` (Vue 3 + Three.js) |
| 生产部署 (M4) | ⏳ 待启动 | Docker + Nginx |

---

## 快速开始

### 1. 算法模型（已就绪）

```bash
cd algorithm_model
pip install -r requirements.txt
python test_all.py        # 自检（应输出 5/5 通过）
python main.py --help     # CLI 7 个子命令
```

### 2. 文档导航

- 📐 **架构设计**：[`docs/ARCHITECTURE_DESIGN.md`](docs/ARCHITECTURE_DESIGN.md) —— 必读
- 📋 **产品功能**：[`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md)
- 📦 **算法模型交付总结**：[`docs/算法模型交付总结.md`](docs/算法模型交付总结.md)
- 🎬 **视频脚本展示整合**：[`docs/视频脚本展示功能整合总结.md`](docs/视频脚本展示功能整合总结.md)

---

## 核心能力

- ✅ **参数化车身建模**：22 维 CarParams 控制 8 大部件（车壳+玻璃+4轮+灯+格栅+镜+门缝）
- ✅ **曲面质量评估**：G0/G1/G2 连续性 + 反射线评分 → A/B/C/D 等级
- ✅ **AI 自动优化**：模拟退火算法，Metropolis 准则
- ✅ **视频脚本生成**：3 套内置模板（宣传/技术/极简），支持自定义分镜
- ✅ **多格式渲染**：Markdown + HTML + JSON

---

## 迭代路线

| 里程碑 | 目标 | 工时 |
|--------|------|------|
| **M1: MVP** | FastAPI 后端 + 5 大 API + OpenAPI 文档 | 1 周 |
| **M2: 数据 + 异步** | SQLite/PG + Celery + 方案库 CRUD | 1 周 |
| **M3: 前端** | Vue 3 + Three.js + WebSocket | 2 周 |
| **M4: 部署** | Docker + Nginx + 监控 | 1 周 |

详见 [架构设计文档 § 11](docs/ARCHITECTURE_DESIGN.md#11-迭代路线4-个里程碑)。

---

## 技术栈

**后端**：Python 3.10+ · FastAPI · Pydantic v2 · SQLAlchemy · Celery
**前端**：Vue 3 · Vite · TypeScript · Three.js · ECharts · Element Plus
**算法**：NumPy · Trimesh · SciPy · Matplotlib
**数据**：SQLite (dev) / PostgreSQL (prod) · Redis
**部署**：Docker · docker-compose · Nginx

---

## 目录

```
EVOLUTION_AI/
├── algorithm_model/        # ★ L4 算法核心（已交付）
├── backend/                # ⏳ L2-L3 FastAPI 后端（待建）
├── frontend/               # ⏳ L1 Vue 3 前端（待建）
├── outputs/                # 产物输出
├── docs/                   # 文档
└── scripts/                # 运维脚本
```

---

**作者**：灵感解药 · 2026-06-19
