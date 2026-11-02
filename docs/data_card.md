# 数据集卡片（DATA CARD）

| 项 | 内容 |
|---|---|
| 版本 | v1.0 · 2026-11-02 |
| 归属 | EVOLUTION-AI.DESIGN 平台内部资产 |
| 默认可见性 | **仅内部可见 / 不可对外公开** |
| 入库策略 | `data/` 全部被 `.gitignore` 排除；不进版本库、不进 `dist/`、不进公网构建 |
| 事实源 | [VALIDATION_20261102.md](retrospective/2026-11-02/VALIDATION_20261102.md) |

> 警告：D-01/02/06 为训练权重，D-07/08/09 含历史导出与**用户上传 CAD**。对外演示、截图、报告均不得暴露文件内容、路径或样本行；确需外发须书面授权并脱敏。

---

## D-01 合并模型权重（Qwen2.5-0.5B）

| 字段 | 值 |
|---|---|
| 路径 | `data/training/merged/merged_model/` |
| 主文件 | `model.safetensors` 1884.6 MB；同目录含 tokenizer/config |
| 架构 | `Qwen2ForCausalLM`，hidden 896，float32 |
| 来源 | 平台历史训练产物合并权重；基座为 Qwen2.5-0.5B-Instruct（见 D-02 adapter 配置） |
| 格式 | HuggingFace safetensors + tokenizer |
| 用途 | 本地推理、继续训练、LoRA 合并验证 |
| 规模 | 1 个模型目录（≈1.90 GB） |
| 可见性 | internal |
| 状态 | 可用；**缺少训练数据清单与许可字段**（待补） |

## D-02 NURBS QLoRA 适配器

| 字段 | 值 |
|---|---|
| 路径 | `data/training/nurbs-qwen-lora/` |
| 主文件 | `adapter_model.safetensors` 33.6 MB；tokenizer 约 15 MB |
| 基座 | `Qwen2.5-0.5B-Instruct`（`adapter_config.json` 记录原路径） |
| 训练参数 | PEFT LoRA，r=16，alpha=32，dropout=0.05；`training_samples=103` |
| 格式 | PEFT LoRA adapter + tokenizer |
| 用途 | NURBS/曲面语义问答微调 |
| 可见性 | internal |
| 状态 | 可用；`training_meta.json` 的 `base_model` 字段误写为自身路径，需修正 |

## D-03 ~ D-05 指令/样本数据集（JSONL）

| ID | 路径 | 行数 | 格式 | 用途 | 来源 | 状态 |
|---|---|---|---|---|---|---|
| D-03 | `data/training/a_surface_quality_dataset.jsonl` | 23 | JSONL | A 级曲面质量评分示例 | 平台历史样本 | 雏形（样本量小，无版本） |
| D-04 | `data/training/nurbs_surface_dataset.jsonl` | 29 | JSONL | NURBS 曲面生成/参数示例 | 平台历史样本 | 雏形 |
| D-05 | `data/training/qlora_enhanced_dataset.jsonl` | 63 | JSONL | QLoRA 指令微调增强集 | 平台历史样本 | 雏形 |

三份合计 115 行，**不足以独立训练**；D-02 的实际训练样本 103 条，与 JSONL 不完全对应，来源链需补齐。

## D-06 车型分类 MLP 权重

| 字段 | 值 |
|---|---|
| 路径 | `data/training/cartype_mlp_task*.pt` |
| 规模 | 171 个文件 / ≈205 MB |
| 格式 | PyTorch `.pt` |
| 用途 | 车型分类实验（任务编号即训练任务） |
| 可见性 | internal |
| 状态 | 可用；无统一 manifest，无法判断哪些是最佳 checkpoint |

## D-07 导出产物

| 字段 | 值 |
|---|---|
| 路径 | `data/exports/` |
| 规模 | 725 文件 / 527.4 MB |
| 格式 | 以 GLB/STL/STEP/JSON 为主 |
| 用途 | 历史导出留档、回归对比样本 |
| 可见性 | internal（可能含用户项目数据） |
| 状态 | 可用；**无清理策略**，按日期子目录堆积 |

## D-08 用户上传 CAD

| 字段 | 值 |
|---|---|
| 路径 | `data/uploads/` |
| 规模 | 120 文件 / 138.8 MB |
| 格式 | `.stp` 67、`.step` 27、`.igs` 12、`.catpart` 8、`.stl` 3、`.wire` 2、`.iges` 1 |
| 来源 | 用户上传（含第三方数据） |
| 用途 | CAD 导入解析、真实数据验证 |
| 可见性 | **internal，禁止外发**（含用户/第三方 CAD） |
| 状态 | 可用；无授权/保留期字段 |

## D-09 STEP 产物

| 字段 | 值 |
|---|---|
| 路径 | `data/step/` |
| 规模 | 43 文件 / 8.3 MB |
| 格式 | STEP |
| 用途 | 导出链路样本 |
| 可见性 | internal |
| 状态 | 可用 |

## D-10 训练用 IGES

| 字段 | 值 |
|---|---|
| 路径 | `data/models/Training_Model.igs` |
| 规模 | 6.1 MB |
| 格式 | IGES |
| 用途 | 建模/读取参考 |
| 可见性 | internal |
| 状态 | 可用 |

## D-11 SISA 参考包

| 字段 | 值 |
|---|---|
| 路径 | `shared_reference/` |
| 规模 | 4 文件 |
| 用途 | 只读参考；**单向同步，禁止回流** |
| 可见性 | 仅参考 |
| 状态 | 可用 |

---

## 汇总与复现

```powershell
# 目录规模（只读，不改数据）
Get-ChildItem data -Directory | ForEach-Object {
  $s=(Get-ChildItem $_.FullName -Recurse -File | Measure-Object Length -Sum).Sum
  $c=(Get-ChildItem $_.FullName -Recurse -File | Measure-Object).Count
  "{0}`t{1} files`t{2} MB" -f $_.Name,$c,[math]::Round($s/1MB,1)
}
```

实测（2026-11-02）：`exports` 725 / 527.4 MB，`training` 243 / 2299.9 MB，`uploads` 120 / 138.8 MB，`step` 43 / 8.3 MB，`models` 1 / 6.1 MB，合计约 **2.7 GB**。

## 缺口

| 缺口 | 影响 | 建议 |
|---|---|---|
| 无 `version` / `license` / `owner` 字段 | 无法追溯与合规审计 | M3 在每张卡增加三字段 |
| D-01/02 基座与训练数据链不完整 | 无法复现训练 | 补 base model、数据集、超参、训练命令 |
| D-06 无 checkpoint manifest | 选型靠猜 | 生成 `cartype_mlp_manifest.csv` |
| D-07/08 无保留期 | 磁盘与合规风险 | 按 90/180 天清理，保留样本单独归档 |
| 无脱敏规则 | 对外材料易泄露用户 CAD | 外发前走 [COLLABORATION_PROTOCOL.md](../COLLABORATION_PROTOCOL.md) 审查 |
