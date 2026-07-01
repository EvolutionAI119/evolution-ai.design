---
AIGC:
    Label: "1"
    ContentProducer: 001191110102MACQD9K64018705
    ProduceID: 7625792088554078499-data_volume/files/所有对话/主对话/MEMORY.md
    ReservedCode1: ""
    ContentPropagator: 001191110102MACQD9K64028705
    PropagateID: 4250075737373691#1781912857888
    ReservedCode2: ""
---
# MEMORY.md

> 规则、事实、当前状态。详细内容降级到 `recent_memory/`。

---

## 当前项目状态

### EVOLUTION AI（主项目）
- **算法核心 v1.0**：✅ 已交付。`EVOLUTION_AI_DEMO/algorithm_model/`（30 文件，5/5 自检 9.49s）
- **架构设计 v1.0**：✅ 已完成。落盘到 D:\API\AI_3D_Model_Build\EVOLUTION_AI\docs\ARCHITECTURE_DESIGN.md（云端副本 `EVOLUTION_AI_DEMO/docs/ARCHITECTURE_DESIGN.md`）
- **后端 MVP (M1)**：⏳ 待启动。FastAPI + 5 大 API + OpenAPI 文档（1 周）
- **前端 (M3)**：⏳ 待启动。Vue 3 + Three.js + WebSocket（2 周）
- **生产部署 (M4)**：⏳ 待启动。Docker + Nginx + 监控（1 周）

### ai-car-styling Skill
- 状态：已发布 v4，skill_id=7653081413079646242, deploy_id=7653079383841718272
- 算法模型已独立打包，可反向集成

### 历史视频项目
- surfaceId: 1c4914c5-b8a4-4c6c-8a28-9ac692565ed4（待主人确认启动）

---

## 关键路径速查

### 云端
- 算法模型：`/app/data/所有对话/主对话/EVOLUTION_AI_DEMO/algorithm_model/`
- 架构设计：`/app/data/所有对话/主对话/EVOLUTION_AI_DEMO/docs/ARCHITECTURE_DESIGN.md`
- 完整车身建模（历史）：`/app/data/所有对话/主对话/EVOLUTION_AI_DEMO/core/full_body.py`

### 桌面端（D:\API\AI_3D_Model_Build\EVOLUTION_AI\）
- 架构设计：`docs\ARCHITECTURE_DESIGN.md` ✅
- 根 README：❌ 未创建（桌面端 bash 超时 / 高危确认拦截）

---

## 重要约定

- **沟通风格**：先结论后依据；少解释过程；"药到病除"
- **格式**：Coze 用 Markdown；文件用 `computer://` 协议（绝对路径）
- **@ 用户**：`[主人](at://owner)` 协议
- **算法模型导入**：用包导入（`from algorithm_model.api import`），不写 try/except 兼容
- **MEMORY/USER/SOUL/TOOLS**：即时层只用 edit_file，严禁用 write_file 覆盖

---

## 风险与待办

- ⚠️ **MEMORY.md 重建**：2026-06-19 22:57 误用 write_file 覆盖原文件，原详细内容已丢失。已重建为简化版，详细历史需从对话上下文/云端文件恢复
- ⚠️ **桌面端 bash**：PowerShell 模式，read 操作触发高危确认，write_file 偶发超时
- 🔜 **待主人决策**：
  1. 架构设计是否过审？要不要改？
  2. 接着推 M1（FastAPI 后端骨架）？
  3. 视频项目是否启动？
  4. README.md 是否在桌面端补建？

---

## 重要联系人 / 资源

- **主人代号**：量子剑客 · 自称解药
- **Skill 商店**：https://www.coze.cn/store/skill/7653081413079646242
- **Skill 图标**：https://s.coze.cn/image/ump9VIsPgKs/
- **股票关注**：永鼎股份(600105)/光迅科技(002281)/中天科技(600522)/新易盛(300502)

---

> 本内容由 Coze AI 生成，请遵循相关法律法规及《人工智能生成合成内容标识办法》使用与传播。
