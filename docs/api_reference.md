# API 参考总览

> 版本：平台 v1.2（2026-09-27 基于源码生成）
> 共 **16 个路由模块、116 个 HTTP 端点**（113 个 `@router` 注册，另含 `api-keys` 3 个），统一前缀 `/api/v1`。
> 请求 / 响应均为 JSON（导出下载类端点除外）。
>
> 认证标记：
> - 🔐 必须认证：`Authorization: Bearer <JWT>`（Depends get_current_user）
> - 🔹 可选认证：携带 JWT 时关联用户（Depends get_optional_user）
> - 无标记：公开
>
> 交互式文档：后端运行时访问 `http://localhost:8000/docs`。

---

## 1. 项目管理 — project.py（5）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/projects/` | 创建项目 | |
| GET | `/projects/` | 项目列表（可按 status 过滤） | |
| GET | `/projects/{project_id}` | 项目详情 | |
| PUT | `/projects/{project_id}` | 更新项目 | |
| DELETE | `/projects/{project_id}` | 删除项目 | |

## 2. 模型文件 — model.py（4）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/models/upload/` | 上传模型文件（multipart，可带 project_id） | |
| GET | `/models/` | 模型列表（可按 project_id 过滤） | |
| GET | `/models/{model_id}` | 模型详情 | |
| DELETE | `/models/{model_id}` | 删除模型 | |

## 3. 模型构建 — build.py（6）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/build/` | 构建模型 | |
| POST | `/build/rebuild` | 重新构建 | |
| POST | `/build/batch` | 批量构建 | |
| GET | `/build/cache` | 构建缓存状态 | |
| DELETE | `/build/cache/{model_id}` | 清除指定模型缓存 | |
| GET | `/build/status/{model_id}` | 查询模型构建状态 | |

## 4. 车身生成 — car.py（6）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/car/generate` | 生成完整车身 | |
| POST | `/car/generate/component` | 生成单个车身部件 | |
| GET | `/car/components` | 可生成部件列表 | |
| GET | `/car/parameters` | 车身生成参数配置 | |
| POST | `/car/regenerate` | 重新生成车身 | |
| POST | `/car/export` | 导出生成的车身数据 | |

## 5. 模型修改 — modify.py（15）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/modify/surfaces/create` | 创建 NURBS 曲面 | |
| GET | `/modify/surfaces/{surface_id}` | 查询曲面 | |
| POST | `/modify/surfaces/{surface_id}/modify` | 修改曲面 | |
| POST | `/modify/surfaces/{surface_id}/control-point` | 更新控制点 | |
| GET | `/modify/surfaces/{surface_id}/evaluate` | 曲面点求值（u, v） | |
| DELETE | `/modify/surfaces/{surface_id}` | 删除曲面 | |
| GET | `/modify/parameters` | 参数列表 | |
| POST | `/modify/parameters/add` | 新增参数 | |
| POST | `/modify/parameters/update` | 更新参数 | |
| GET | `/modify/parameters/automotive` | 汽车工程参数 | |
| POST | `/modify/measurements/distance` | 距离测量 | |
| POST | `/modify/measurements/angle` | 角度测量 | |
| GET | `/modify/measurements/summary` | 测量汇总 | |
| GET | `/modify/history` | 修改历史 | |
| POST | `/modify/history/undo` | 撤销 | |

## 6. 模型导出 — export.py（4）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/export/` | 创建导出任务 | |
| GET | `/export/download/{model_id}/{format}` | 下载指定格式文件 | |
| GET | `/export/formats` | 支持的导出格式 | |
| GET | `/export/history/{model_id}` | 模型导出历史 | |

## 7. 模型变体 — variant.py（7）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/variants/` | 创建变体 | |
| GET | `/variants/{model_id}` | 模型变体列表 | |
| GET | `/variants/{model_id}/history` | 变体版本历史 | |
| GET | `/variants/{model_id}/{variant_id}` | 变体详情 | |
| DELETE | `/variants/{model_id}/{variant_id}` | 删除变体 | |
| POST | `/variants/compare` | 变体对比 | |
| POST | `/variants/{model_id}/{variant_id}/rollback` | 回滚到指定变体 | |

## 8. 工作流 — workflow.py（7）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/workflows/` | 创建工作流 | |
| GET | `/workflows/` | 工作流列表（project_id / status 过滤） | |
| GET | `/workflows/{workflow_id}` | 工作流详情 | |
| POST | `/workflows/{workflow_id}/execute` | 执行工作流 | |
| GET | `/workflows/{workflow_id}/steps` | 工作流步骤列表 | |
| PUT | `/workflows/{workflow_id}` | 更新工作流 | |
| DELETE | `/workflows/{workflow_id}` | 删除工作流 | |

## 9. 质量与拓扑 — quality.py（8）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/topology/optimize/` | 拓扑优化 | |
| POST | `/quality/check/` | 创建质量检查报告 | |
| GET | `/quality/reports/` | 质量报告列表（project_id / model_id 过滤） | |
| GET | `/quality/reports/{report_id}` | 质量报告详情 | |
| POST | `/data/handover/` | 数据交接准备 | |
| GET | `/parameters/` | 参数集列表 | |
| GET | `/reports/{report_path}` | 下载报告文件（path 型路径） | |
| GET | `/exports/{export_path}` | 下载导出文件（path 型路径） | |

## 10. AI 训练 — training.py（14）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/ai/train` | 创建后台 PyTorch 训练任务 | 🔐 |
| GET | `/ai/tasks` | 训练任务列表（本人；管理员全部） | 🔐 |
| GET | `/ai/tasks/{task_id}` | 任务详情 | 🔐 |
| POST | `/ai/tasks/{task_id}/cancel` | 取消任务 | 🔐 |
| GET | `/ai/training/capabilities` | 训练能力与并发情况 | |
| POST | `/ai/train/batch` | 同步生成合成样本批次 | 🔹 |
| GET | `/ai/dataset-stats` | 数据集统计 | |
| GET | `/ai/car-types` | 车型元信息 | |
| GET | `/ai/styles` | 风格元信息 | |
| GET | `/ai/brands` | 品牌元信息 | |
| GET | `/ai/model-weights` | 已产出模型检查点 | |
| POST | `/ai/evaluate-quality` | 造型参数质量评估 | |
| POST | `/ai/generate-design` | 生成式设计 | |
| POST | `/ai/optimize` | 参数优化 | |

## 11. AI 助手 — ai.py（3）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/ai/chat` | NURBS 专家对话（Ollama） | |
| GET | `/ai/models` | 列出 Ollama 可用模型 | |
| GET | `/ai/health` | Ollama / NURBS 服务健康状态 | |

## 12. 贝叶斯优化 — bayes.py（7）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/bayes/sessions` | 创建优化会话（空间 / goal / acquisition / seed） | |
| GET | `/bayes/sessions/{session_id}` | 会话摘要 | |
| DELETE | `/bayes/sessions/{session_id}` | 删除会话 | |
| GET | `/bayes/sessions/{session_id}/suggest` | 建议采样参数（n，1–32） | |
| POST | `/bayes/sessions/{session_id}/observe` | 上报观测（parameters + score） | |
| GET | `/bayes/sessions/{session_id}/best` | 当前最优观测 | |
| GET | `/bayes/sessions/{session_id}/samples` | 导出训练样本 | |

详见 [bayes_optimization.md](bayes_optimization.md)。

## 13. 参数化纹理 — texture.py（3）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| GET | `/texture/regions` | 可应用纹理的目标部位列表 | |
| POST | `/texture/analyze` | 纹样 / 纹理分析 | |
| POST | `/texture/apply/{session_id}` | 将纹理应用到指定会话 | |

## 14. 导入改参导出 — import_export.py（11）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/import-export/import` | 按参数创建导入会话 | |
| POST | `/import-export/import/file` | 上传文件创建会话（multipart） | |
| GET | `/import-export/{session_id}/params` | 参数列表 | |
| GET | `/import-export/{session_id}/params/groups` | 参数分组 | |
| PUT | `/import-export/{session_id}/params` | 修改参数（overrides） | |
| GET | `/import-export/{session_id}/preview` | 3D 预览 | |
| POST | `/import-export/{session_id}/export` | 多格式导出 | |
| GET | `/import-export/{session_id}/download/{filename}` | 下载导出文件 | |
| GET | `/import-export/{session_id}/snapshot` | 参数快照 | |
| GET | `/import-export/sessions` | 会话列表 | |
| DELETE | `/import-export/{session_id}` | 删除会话 | |

## 15. LLM 统一代理 — llm_proxy.py（4）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| GET | `/llm/providers` | 已配置提供商列表 | 🔹 |
| POST | `/llm/{provider}/chat/completions` | 对话补全 | 🔹 |
| POST | `/llm/{provider}/embeddings` | 向量嵌入 | 🔹 |
| POST | `/llm/{provider}/images/generations` | 文生图 | 🔹 |

## 16. 认证与 API Key — auth.py（9）

| 方法 | 路径 | 功能 | 认证 |
|---|---|---|---|
| POST | `/auth/register` | 注册并返回 JWT | |
| POST | `/auth/login` | 密码登录并返回 JWT | |
| GET | `/auth/me` | 当前用户信息 | 🔐 |
| GET | `/auth/methods` | 已启用登录方式探测 | |
| GET | `/auth/wechat/qr` | 微信开放平台扫码二维码 | |
| GET | `/auth/wechat/callback` | 微信开放平台回调 | |
| GET | `/auth/mp/authorize` | 公众号网页授权入口 | |
| GET | `/auth/mp/poll` | 按票据轮询授权结果 | |
| GET | `/auth/mp/callback` | 公众号授权回调 | |
| GET | `/api-keys` | 当前用户 API Key 列表 | 🔐 |
| PUT | `/api-keys/{provider}` | 设置 API Key（后端加密） | 🔐 |
| DELETE | `/api-keys/{provider}` | 删除 API Key | 🔐 |

> 注：auth.py 包含 `auth` 与 `keys_router` 两个路由，共 12 个端点；
> 模块端点数统计（9）仅计入 `auth` 路由，3 个 api-keys 端点在此处一并列出。

---

## 17. 系统端点（main.py 直接定义）

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/i18n/config` | 国际化配置（默认语言 / 支持语言） |

---

## 18. 标准错误响应

| 状态码 | 含义 |
|---|---|
| 400 | 业务校验失败（如参数越界、非法空间定义） |
| 401 | JWT 缺失 / 失效 |
| 404 | 资源或会话不存在 |
| 405 | 方法不允许（含 Allow 头） |
| 409 | 状态冲突（如无观测查询 best） |
| 422 | 请求体 schema 校验失败（含字段错误明细） |
| 503 | 可选能力未就绪（PyTorch / Ollama / 微信配置缺失等） |
