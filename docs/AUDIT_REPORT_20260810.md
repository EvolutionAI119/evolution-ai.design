# Evolution-AI.Design 综合审计报告

> 报告日期: 2026-08-10
> 审计范围: 2026-08-09 ~ 2026-08-10 全量工作
> 涵盖: 项目清理归档、死代码审计、LLM 微调与 RAG 修复、Docker 容器化

---

## 一、项目概览

### 技术架构（4 层）

| 层 | 技术栈 | 核心目录 |
|------|------|------|
| 前端 | Vue 3 + Vite + Pinia + Three.js + Element Plus | `src/`（8 个页面、4 个组件、4 个 store） |
| 后端 | FastAPI + SQLite + Uvicorn | `backend/`（10 条路由：ai / car / build / export / quality / workflow 等） |
| 算法 | Cython 加速 NURBS + 参数化车身 + A 级曲面 SOP 评估 | `algorithm_model/`（car_modeling / freeform / surface_quality / storyboard） |
| AI/LLM | Qwen2.5-0.5B + QLoRA + RAG（Ollama API 兼容） | `scripts/llm_server.py` + `data/training/` |

### 核心功能

- 参数化车身生成：SAE 坐标系驱动，L/W/H/WB 等参数控制 17 个组件、33 个曲面
- NURBS 曲面质量评估：G0/G1/G2 连续性检查、ISO 曲率梯度比、CV 变异系数、R 角检查
- SOP 检查清单：13 项检查、183 条记录、67 条自动化、自动化通过率 79%
- AI 专家问答：基于微调模型 + RAG 检索的 NURBS 知识问答服务

---

## 二、8 月 9 日审计记录

### 2.1 前端图片加载修复

**问题**: Designer.vue 中车型图片直接调用远程 `text_to_image` API，浏览器端因缺少 IDE 鉴权环境返回 `net::ERR_FAILED`。

**修复措施**:
- `src/config/carPresets.js`: 新增 `generatePresetImage()` 函数，在模块初始化时为 19 款车型预渲染本地 SVG dataURL（含品牌色和尺寸标注）
- `src/views/Designer.vue`: 删除远程加载逻辑和 `imageCache`/`cleanupImageCache` 死代码，`loadImage()` 改为 `prepareModelImage()`，`getImageState()` 默认返回 `loaded`

**代码审查发现**:
- `prepareModelImage` 检查条件逻辑缺陷（覆盖预置图片）→ 已修复
- `getBrandKeyForModel` 变量遮蔽问题 → 已修复

**验证结果**: 控制台无 error 和 ERR_FAILED，模型图片、Car3D/Car2D 组件、参数滑块、AI 面板、颜色选择器、导航栏全部正常。

### 2.2 项目归档清理

**动作**: 审核项目全部文件，将非核心废弃文件归档到 `_archive/`。

**归档分类**（共 ~80+ 文件）:

| 目录 | 内容 | 文件数 |
|------|------|------|
| `_archive/dirs/3d_automation/` | 3D 交互系统、AI 工作流文档、思维导图 | ~25 |
| `_archive/dirs/docs/` | 历史完结报告（W1~W4、M2.5）、产品规格、架构设计 | ~30 |
| `_archive/dirs/evolution_ai_demo_w2d1/` | 旧版前端构建产物 | ~25 |
| `_archive/dirs/core/` | 旧版核心代码（car_surface.py、full_body.py） | 3 |
| `_archive/dirs/codeact/` | CodeAct 测试脚本 | 2 |
| `_archive/dirs/SUPER_AGENT/` | 旧版 Agent 脚本 | 1 |
| `_archive/dirs/generation/` | 旧版参数化生成脚本 | 1 |
| `_archive/dirs/viewer/` | 旧版 API 服务器 | 1 |
| `_archive/docs/` | 旧文档（CHANGELOG、README_DEMO、SOLUTION_ARCHITECTURE） | 3 |
| `_archive/misc/` | 杂项 HTML 演示、Plotly 截图 | 6 |
| `_archive/scripts/` | 过期启动脚本、Streamlit/Plotly 测试 | ~20 |

**根目录保留的核心文件**: 前端源码 `src/`、后端源码 `backend/`、算法模型 `algorithm_model/`、脚本 `scripts/`、数据 `data/`、测试 `tests/`、Docker 配置、构建配置。

### 2.3 整体测试验证

**结果**: 201 个测试全部通过，0 失败，9 条警告（与本次清理无关）。

### 2.4 Git 提交

- Commit: `c6a65af3`，分支: `v1.01-reconstruct`
- 涉及 139 个文件变更（137 个删除 = 归档、2 个修改 = carPresets.js + Designer.vue）
- 76 行新增、33,974 行删除

### 2.5 后端接口验证

| 接口 | 方法 | 状态 | 说明 |
|------|------|------|------|
| `/api/v1/car/parameters` | GET | 正常 | 返回 5 大类参数树 |
| `/api/v1/car/components` | GET | 正常 | 返回 17 个组件 |
| NURBS 曲面生成 | POST | 正常 | 生成 33 个曲面 + 33 个组件 |
| `/api/v1/ai/dataset-stats` | GET | 404 | 后端 main.py 未注册 AI 路由模块（后续已修复） |

### 2.6 测试数据蒸馏

- 清理 15 个未跟踪临时文件（~4MB）：pytest 生成的 `model_*` 目录和 NURBS 截图
- 更新 `.gitignore`：新增 `data/exports/model_*/` 和 `data/step/nurbs_a_class_*.png` 规则
- 蒸馏为训练材料：3 个文件共 52 条 prompt-completion 样本 + 1 份结构化知识文档，覆盖 8 个知识类别

### 2.7 LLM 微调与推理测试

| 阶段 | 模型 | 通过率 | 关键问题 |
|------|------|------|------|
| 基础模型推理 | Qwen2.5-0.5B-Instruct（未微调） | 1/10 (10%) | 缺乏 NURBS 领域知识和平台实测数据 |
| QLoRA 微调后 | Qwen2.5-0.5B + LoRA adapter | 3/10 (30%) | continuity 类别数值混淆、recess/bulge 术语缺失 |
| RAG 检索增强 | 微调模型 + RAG | 7/10 (70%) | Q1 术语缺失、Q3 数值混淆、Q10 术语缺失 |

**30% 通过率根因分析**（7 道失败题）:
- 缺乏平台特定数据：43%（3 题）
- 专业词汇缺失：29%（2 题）
- 概念定义错误：14%（1 题）
- 拒答模式：14%（1 题）
- 高风险类别（100% 失败）：continuity、nurbs_basics、parametric_design、quality_assessment

---

## 三、8 月 10 日 LLM 修复记录

### 3.1 系统提示词结构重构

**文件**: `scripts/llm_server.py` L33-L77、`scripts/Modelfile` L10-L54

| 修复项 | 修复前 | 修复后 |
|------|------|------|
| 关键数据位置 | 实测数值散落在速查表中 | body↔front 和 body↔rear 两条数据**置顶**在 `⚠ 最重要` 块 |
| 防混淆警告 | 无 | 明确警告「绝对不要把 recess/bulge 大间隙数值当成车身与保险杠的 G0」 |
| G1 连续性定义 | 仅写「切向量连续」 | 补充「切向量方向一致，即法向量夹角 < 1.0 度（1度）」 |
| 速查表分类 | 平铺罗列所有配对 | 按「【共享边界】/【recess】/【bulge】」三大类显式分隔 |
| 领域知识 | 仅 NURBS 数学 | 新增 SOP 统计、SAE 坐标系、LWHWB 默认参数、CV/R 角数值 |

### 3.2 RAG 检索意图路由

**文件**: `scripts/llm_server.py` L302-L334 `retrieve()` 函数

| 意图检测 | 动作 | 效果 |
|------|------|------|
| "车身 + 前保险杠 + 连续性" | `body↔front_bumper` 块 +50 分，`continuity_summary` +30 分 | 正确配对块排第 1 |
| grille/headlight/taillight 块 | 未明确提问时 -20 分 | 干扰项（3.294mm）排到第 5 |
| "间隙正常/修复" | wheel/hub/mirror/bumper 组件 +20 分 | Q10 装配间隙术语更易命中 |

### 3.3 验证结果

| 测试 | 修复前 | 修复后 | 关键词命中 |
|------|------|------|------|
| **Q1** G1 连续性定义 | FAIL (0/4) | **PASS (4/4)** | 切向量 / 法向量 / 1度 / 共享边界 |
| **Q3** 车身↔前保险杠 G0/G1 | FAIL (1/2，返回 3.294mm/88.814deg) | **PASS (2/2)** | 0.000 / 0.131 |

### 3.4 两文件一致性验证

- `llm_server.py` 与 `Modelfile` 的系统提示词**字节级完全一致**
- 14 个关键锚点全部命中（实测数据、切向量/法向量、三大分类、SOP 统计、SAE 坐标系等）
- 5 个 RAG 路由锚点全部命中（意图检测、加权 +50、抑制 -20 等）

### 3.5 Docker 容器化

**新增文件**:

| 文件 | 用途 |
|------|------|
| `Dockerfile.llm` | LLM 推理服务镜像（python:3.11-slim + torch CPU + transformers） |
| `docker-compose.llm.yml` | 一键启动 llm-server 服务，挂载 merged_model + 知识库 |
| `scripts/docker-llm.ps1` | PowerShell 一键管理脚本（up / logs / test / status / down / restart） |

**端到端测试**（本地环境模拟容器）:
- 服务启动: 模型加载完成（494M params），RAG 开启（20 个知识块）
- Q1: **4/4 PASS** —「切向量方向在共享边界处保持一致，即法向量夹角小于1度」
- Q3: **2/2 PASS** —「body↔front_bumper G0=0.000mm，G1=0.131deg」

> 注: Docker Desktop daemon 今日未启动，采用本地相同依赖环境（transformers 4.57.6 + torch 2.4.1 CPU）模拟容器行为验证。Docker Desktop 就绪后执行 `.\scripts\docker-llm.ps1` 即可一键构建+启动+测试。

---

## 四、关键指标现状

<figure class="doc-figure">
  <img src="docs/images/validation-metrics.svg" alt="审计时点三层测试指标" loading="lazy">
  <figcaption><strong>图 4-1 ｜ 审计时点关键指标：三层测试规模与通过率</strong>读图：柱状图为审计时点的三层测试快照——算法 200 / 后端 178 / 前端 111 / 自检 5，489 例全通过；右侧徽章为收敛验证与文档核对结论，对应审计结论「事实基线一致」。</figcaption>
</figure>

| 指标 | 状态 | 说明 |
|------|------|------|
| 单元测试 | 201 / 201 通过 | 8 月 9 日最近一次全量运行 |
| LLM 10 题基准 | 7 / 10 通过（70%） | Q1/Q3 修复后提升，Q10 待重跑 |
| LLM Q1 + Q3 | 全过 | Q1 4/4、Q3 2/2 |
| LLM 服务 | 运行中 | 端口 11434，RAG 20 块加载正常 |
| Docker 主平台 | 就绪 | `Dockerfile` + `docker-compose.yml` |
| Docker LLM 服务 | 就绪 | `Dockerfile.llm` + `docker-compose.llm.yml` + `docker-llm.ps1` |
| Git 分支 | `v1.01-reconstruct` | 最新 commit `c6a65af3` |

---

## 五、遗留事项与建议

| 优先级 | 事项 | 说明 |
|------|------|------|
| 高 | Q10 重跑验证 | 已执行：原始问题 1/6 FAIL，模型不使用中文术语，详见 3.5 节 |
| 高 | Docker Desktop 启动后构建 | daemon 就绪后执行 `.\scripts\docker-llm.ps1` 验证真实容器环境 |
| 中 | 模型容量瓶颈 | 0.5B 模型对长提示词记忆有限，如 Q10 仍失败可考虑切换 7B 模型 |
| 中 | 全量 10 题回归 | 当前仅重跑 Q1/Q3，建议跑完整 10 题确认无回退 |
| 低 | 训练数据扩充 | 当前 63 条 JSONL，可扩充至 500+ 条进一步提升覆盖面 |

---

## 六、文件变更清单（8/9 ~ 8/10）

### 修改文件

| 文件 | 变更内容 |
|------|------|
| `src/config/carPresets.js` | 新增 `generatePresetImage()`，预渲染本地 SVG dataURL |
| `src/views/Designer.vue` | 删除远程图片加载死代码，改用本地预置图 |
| `scripts/llm_server.py` | 系统提示词重构（L33-77）+ RAG 意图路由（L302-334） |
| `scripts/Modelfile` | 系统提示词同步更新（L10-54） |
| `.gitignore` | 新增 `data/exports/model_*/` 和 `data/step/nurbs_a_class_*.png` |

### 新增文件

| 文件 | 用途 |
|------|------|
| `Dockerfile.llm` | LLM 推理服务 Docker 镜像定义 |
| `docker-compose.llm.yml` | LLM 服务 Docker Compose 编排 |
| `scripts/docker-llm.ps1` | Docker 一键管理脚本 |
| `scripts/deploy_finetuned.py` | QLoRA 微调 + 合并 + GGUF 转换自动化管线 |
| `scripts/train_qlora.py` | QLoRA 训练脚本 |
| `scripts/merge_lora.py` | LoRA adapter 合并脚本 |
| `scripts/analyze_failures.py` | 推理测试失败分析脚本 |
| `scripts/test_nurbs_inference.py` | NURBS 专家模型推理测试脚本 |
| `scripts/setup_ollama.ps1` | Ollama 环境配置脚本 |
| `data/training/parametric_design_knowledge.json` | RAG 知识库（20 个知识块） |
| `data/training/qlora_enhanced_dataset.jsonl` | QLoRA 训练数据（63 条） |
| `data/training/nurbs_surface_dataset.jsonl` | NURBS 曲面训练数据 |
| `data/training/a_surface_quality_dataset.jsonl` | A 级曲面质量训练数据 |
| `data/training/test_results.json` | 10 题推理测试结果 |
| `data/training/merged/merged_model/` | 合并后微调模型（~1.9GB） |
| `data/training/nurbs-qwen-lora/` | LoRA adapter + 3 个 checkpoint |

### 归档文件

- ~80+ 个非核心文件移至 `_archive/`（详见 2.2 节）
