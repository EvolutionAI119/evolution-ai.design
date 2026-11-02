# 资产清单（ASSET MANIFEST）

| 项 | 内容 |
|---|---|
| 版本 | v1.0 · 2026-11-02 |
| 范围 | 本仓库内可复用的智能体、Skills、工作流、数据集 |
| 唯一事实源 | [VALIDATION_20261102.md](retrospective/2026-11-02/VALIDATION_20261102.md)；数字门禁 `scripts/pre_commit_check.py` |
| 可见性 | **默认仅内部可见**；数据集与训练产物**不可对外公开**，对外材料不得引用路径或样本 |

> 路径均为项目根相对路径。状态标注：`可用` / `雏形` / `缺失` / `仅参考`。

---

## 1. 智能体（Agents）

| ID | 名称 | 路径 | 角色 / Prompt 要点 | 编排关系 | 状态 |
|---|---|---|---|---|---|
| A-01 | `evolution-ai-design` | [.trae/agents/evolution-ai-design.md](../.trae/agents/evolution-ai-design.md) | 平台全栈专家：功能开发、修复、架构、联调、算法、迁移、安全、测试、部署、文档；中文沟通，关键决策先说明 | 由主会话按任务调用；按触发条件转向 S-01~S-07 | 可用（数字已校准） |
| A-02 | 评审/裁决角色 | — | 需要独立的“审核 B/C”角色定义与 checklist prompt | 应与人审 L5 配合 | 缺失 |
| A-03 | 编排器（dispatcher） | — | 需要按任务类型自动选择 skill/agent 的路由定义 | 当前靠人工选择 | 缺失 |

**编排事实**：仓库只有 1 个正式 agent 定义；不存在多智能体编排文件。任务→技能的映射靠 agent 正文与 skill frontmatter 的 `description` 触发，属于“隐式编排”。

---

## 2. Skills

| ID | 名称 | 路径 | 触发条件 | 用途 | 状态 |
|---|---|---|---|---|---|
| S-01 | `deploy-gh-pages` | [.trae/skills/deploy-gh-pages/SKILL.md](../.trae/skills/deploy-gh-pages/SKILL.md) | 需要发布公网、更新站点、修复公网黑屏/404 | dist 全量同步 gh-pages 并推送 | 可用（**本轮公网发布冻结**） |
| S-02 | `launch-services-detached` | [.trae/skills/launch-services-detached/SKILL.md](../.trae/skills/launch-services-detached/SKILL.md) | 启动/重启本地三服务、服务掉线、同步 cpolar 域名 | 以独立顶层进程拉起 cpolar/后端/前端 | 可用 |
| S-03 | `doc-code-audit` | [.trae/skills/doc-code-audit/SKILL.md](../.trae/skills/doc-code-audit/SKILL.md) | 核对文档、文档一致性、stale numbers、死链 | 文档与源码事实核对 | 可用；已被 `pre_commit_check.py` 部分自动化 |
| S-04 | `project-intro-deck` | [.trae/skills/project-intro-deck/SKILL.md](../.trae/skills/project-intro-deck/SKILL.md) | 生成中英文项目介绍 PPT | 可视化介绍材料 | 可用 |
| S-05 | `troubleshoot-i18n-deploy` | [.trae/skills/troubleshoot-i18n-deploy/SKILL.md](../.trae/skills/troubleshoot-i18n-deploy/SKILL.md) | 中文界面显示英文、文档数字过期、公网白屏/黑屏 | 两类故障的定位与修复 | 可用 |
| S-06 | `threejs-automotive-preview-debugging` | [.trae/skills/threejs-automotive-preview-debugging/SKILL.md](../.trae/skills/threejs-automotive-preview-debugging/SKILL.md) | 高光白带、反射异常、破面、零件不可见/比例失调 | Car3D 渲染根因与多视角截图 | 可用（2026-11-02 入库） |
| S-07 | `wheel-arch-envelope-sync` | [.trae/skills/wheel-arch-envelope-sync/SKILL.md](../.trae/skills/wheel-arch-envelope-sync/SKILL.md) | 轮拱造型异常、车轮穿壳、拱顶不足、EVO→SISA 同步 | 轮拱包络跨平台对齐 | 可用（2026-11-02 入库） |
| S-08 | 内饰布置校验 | — | 需要把 L1~L5 检查固化为可调用技能 | 当前只有 [2D_LAYOUT_VERIFICATION.md](2D_LAYOUT_VERIFICATION.md) 文档 | 雏形（建议 M3 技能化） |

仓库外由 TRAE 提供的通用技能（`algorithm-debugging`、`TRAE-*` 等）不计入本清单。

---

## 3. 工作流

| ID | 名称 | 节点 | 依赖 | 调用方式 | 状态 |
|---|---|---|---|---|---|
| W-01 | 参数化整车生成 | carProfile 参数 → algorithm_model 网格/NURBS → GLB/STL/STEP 导出 → 2D/3D 预览 | `carProfile.js`、`car_generator.py` | Designer 页面 / 后端 car、build、export 路由 | 可用 |
| W-02 | 内饰布置闭环 | 参数 → `deriveInteriorLayout` → 2D 侧视 / A-A 剖面 / 3D 内饰 → L1~L5 校验 | `carInteriorLayout.js`、`carInteriorKinematics.js` | `npx vitest run` + Designer 目视 | 可用；L5 人工 |
| W-03 | 玻璃 DLO 分缝 | carGlass 分缝 → 3D 带玻璃/窗片 | `carGlass.js`、`Car3D.vue` | Designer 3D 预览 | 可用 |
| W-04 | EVO→SISA 轮拱同步 | 参数导出 → SISA 侧 `sync_open_source.ps1` → 包络核对 | `D:\API\SISA` | S-07；**单向，禁止回流** | 雏形（依赖 SISA 侧执行） |
| W-05 | 3D 预览调试 | 截图 → 根因分类 → 最小修复 → 多机位复验 | S-06 | skill 触发 + 浏览器实机 | 可用 |
| W-06 | 发布闭环 | vitest → build → dist 全量同步 → 公网 MD5 比对 | S-01 | 手动授权后执行 | 可用（**冻结中**） |
| W-07 | 训练评审 | 训练完成 → `POST /workflows/training-review` → 合规性审核 → 质量审核 | 后端 workflow 路由、登录 Token | API：9 个 `/workflows` 端点 | 可用 |
| W-08 | 贝叶斯优化 | 参数空间（14 维）→ RBF-GP → EI/UCB 建议 | `bayes_optimizer.py` | 后端 bayes 路由 | 可用；无自动双判据收敛（雏形） |

### 3.1 工作流节点契约（标准化封装）

新增工作流必须显式声明以下字段，禁止隐式约定：

| 字段 | 含义 | 约束 |
|---|---|---|
| `id` | 稳定工作流 ID | `W-xx`，不复用 |
| `nodes` | 有序节点 | 每节点含 `name` / `input` / `output` / `owner` |
| `depends_on` | 依赖的资产 ID | 只能引用本清单 A/S/W/D 编号 |
| `entrypoint` | 唯一调用入口 | 函数路径或 HTTP 端点，二者只选其一 |
| `evidence` | 验证证据 | 测试文件名或截图/报告路径 |
| `visibility` | 可见性 | `internal` / `public`，默认 `internal` |
| `status` | 状态 | `可用` / `雏形` / `缺失` |

### 3.2 新增工作流模板（4 步）

1. 在本文件新增一行 W-xx，填齐 3.1 字段；
2. 若为后端流程：在 `backend/app/routes/workflow.py` 增加端点，并复用 `Workflow` / `WorkflowStep` 表；
3. 若为前端/几何流程：入口函数放 `src/utils/`，纯函数优先，禁止在组件内另立坐标；
4. 补测试 + 在 `VALIDATION_20261102.md` 追加一行验证证据。

---

## 4. 数据集（摘要）

完整卡片（来源、规模、格式、用途、公开边界）见 [data_card.md](data_card.md)。

| ID | 名称 | 路径 | 规模 | 用途 | 可见性 |
|---|---|---|---|---|---|
| D-01 | 合并模型权重 | `data/training/merged/merged_model/` | 1884.6 MB（`.safetensors`） | 推理/继续训练 | 内部 |
| D-02 | NURBS QLoRA 适配器 | `data/training/nurbs-qwen-lora/` | 33.6 MB（adapter）+ tokenizer | 曲面语义微调 | 内部 |
| D-03 | 曲面质量样本 | `data/training/a_surface_quality_dataset.jsonl` | 23 行 | 质量评分示例 | 内部 |
| D-04 | NURBS 曲面样本 | `data/training/nurbs_surface_dataset.jsonl` | 29 行 | 曲面生成示例 | 内部 |
| D-05 | QLoRA 增强样本 | `data/training/qlora_enhanced_dataset.jsonl` | 63 行 | 指令微调 | 内部 |
| D-06 | 车型 MLP 权重 | `data/training/cartype_mlp_task*.pt` | 171 个 / ≈205 MB | 车型分类实验 | 内部 |
| D-07 | 导出产物 | `data/exports/` | 725 文件 / 527.4 MB | 历史导出与回归样本 | 内部 |
| D-08 | 用户上传 CAD | `data/uploads/` | 120 文件 / 138.8 MB | STEP/STP/IGS/STL/CATPart 导入 | 内部（含用户数据） |
| D-09 | STEP 产物 | `data/step/` | 43 文件 / 8.3 MB | STEP 导出样本 | 内部 |
| D-10 | 训练用 IGES | `data/models/Training_Model.igs` | 6.1 MB | 建模参考 | 内部 |
| D-11 | SISA 参考包 | `shared_reference/` | 4 文件 | 只读参考 | 仅参考 |

`data/` 整体约 **2.7 GB**，已被 `.gitignore` 排除，不进版本库、不进公网构建。

---

## 5. 新增资产模板

### 5.1 新增 Agent

```markdown
---
name: <agent-name>
description: <一句话职责 + 何时调用 + 何时不调用>
tools: read, edit, terminal, websearch, preview
---

# <角色名>
1. 职责边界：...
2. 可调用的 Skill：S-xx ...
3. 必跑验证：`npx vitest run` / `pytest` / `scripts/pre_commit_check.py`
4. 禁止：跨仓库引用 SISA 模块、提交未跟踪半成品
```

### 5.2 新增 Skill

```markdown
---
name: <skill-name>
description: <触发词：中文/English；明确“不用于……”>
---
## 触发后的执行步骤
1. 复现/取证命令
2. 最小修复
3. 验证命令与预期输出
```

落点 `.trae/skills/<name>/SKILL.md`，同目录放脚本与示例；完成后在本清单 §2 登记。

### 5.3 新增数据集

1. 原始文件放 `data/<类别>/`（已被 gitignore，禁止入库）；
2. 在本清单 §4 与 [data_card.md](data_card.md) 登记来源、规模、格式、用途、可见性；
3. 默认 `internal`；对外发布需书面授权，且不得包含用户上传 CAD 或品牌机密数据；
4. 大文件禁止进入 `dist/` 或公网构建。

---

## 6. 缺口与下一步

| 缺口 | 影响 | 建议 |
|---|---|---|
| 无编排器/评审 agent | 任务路由靠人工与描述匹配 | M3 增加 A-02/A-03 |
| 内饰校验未技能化（S-08 雏形） | L1~L5 每次靠人记文档 | M3 封装为 skill + 脚本 |
| W-04 依赖 SISA 侧手工执行 | 同步不可自动验证 | 增加只读核对脚本（不回流） |
| W-08 无自动收敛 | 需人工判停 | 保持现状，文档标注“停止参考” |
| 数据集无版本/许可字段 | 无法追溯来源 | 在 data_card 增加 `version` / `license` 列 |
