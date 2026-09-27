---
name: doc-code-audit
description: One-click documentation-vs-source consistency audit for this repo. Use for 核对文档, 一键核对, 文档一致性, stale numbers, dead links, or README navigation updates. Do not use for writing new features.
---

# 文档-源码一致性一键核对

把 EVOLUTION AI 知识体系文档（README、docs/、algorithm_model/README.md）与源码事实对齐。

## 触发后的执行步骤

1. **运行确定性核对脚本**（标准库实现，无需安装依赖）：

   ```powershell
   python .\.trae\skills\doc-code-audit\scripts\check_consistency.py
   ```

2. **读取脚本输出的事实基线**，逐项核对文档中的规模性陈述：
   - HTTP 端点总数（路由模块各 APIRouter 变量 + main.py 系统端点）；
   - ORM 表数（`backend/app/database.py` 的 `__tablename__`）；
   - 前端页面数（`src/router.js` 路由记录）；
   - CarParams 字段数（`algorithm_model/car_modeling/car_params.py`）；
   - 贝叶斯默认空间维数（`backend/app/bayes_optimizer.py` DEFAULT_SPACE）。

3. **发现不一致时以源码为准修正文档**，常见落点：
   - README.md：当前状态表、目录树、文档导航；
   - docs/ARCHITECTURE_DESIGN.md、docs/api_reference.md：端点口径与模块表；
   - docs/EVOLUTION_AI_paper.md、docs/whitepaper.md、docs/VALIDATION_REPORT_*.md：事实数字；
   - algorithm_model/README.md：API 数、模块树、性能数据。

4. **链接与导航问题**按脚本输出处理：
   - 死链：修正目标路径，禁止猜测路径，先用 Glob/Read 确认；
   - `file:///` 本机链接：改为仓库相对路径（如 `../scripts/x.py#L10-L20`）；
   - README 导航缺漏：docs 下每个 .md 都应在导航中有入口；删除文档后同步移除导航。

5. **重跑脚本直到零问题**（死链必须为 0）。

6. 若当次还涉及代码改动或用户要求验证，再运行三层测试（algorithm_model pytest、backend pytest、frontend vitest），并以真实输出为证据；测试命令见 docs/VALIDATION_REPORT_20260927.md 附录。

## 纪律

- 所有事实必须锚定源码或真实命令输出，禁止凭印象填写数字；
- 脚本只提取事实与机械校验，"文档该如何表述"由你判断；
- 不主动创建文档；历史报告的正文事实（测试日期、历史数据）不回改，只修链接与现行文档；
- 完成后向用户汇报：事实基线、修复清单、验证证据；提交/推送需用户明确同意。
