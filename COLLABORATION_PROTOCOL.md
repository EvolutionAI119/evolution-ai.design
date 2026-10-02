# 多工具协同开发协议（Collaboration Protocol）

> 适用对象：在本仓库工作的所有 AI 编码工具（TRAE、DeepSeek Harness 及未来新增）与人工开发者。
> 目标：**安全可控、方向正向、低耗、高效**。任何工具开始工作前先读本文件。
>
> 2026-10-02 起因：两个 AI 工具同时自行启动后端并按端口强杀对方进程，导致
> 后端反复重启、实例并存、请求随机分流。为彻底消除“端口战争”制定本协议。

## 一、第一原则：单一运行时（Single Runtime）

1. 本项目**全机只允许一组开发服务**，由 TRAE 的独立启动器（`launch-services-detached`）作为规范所有者（canonical owner）拉起：

   | 服务 | 端口 | 进程特征 |
   |---|---|---|
   | cpolar 公网隧道 | 4040（本地检查页） | `cpolar.exe http 8000` |
   | FastAPI 后端 | 8000 | `python start.py`（含 uvicorn reload 父子进程） |
   | Vite 前端 | 5173 | `node ... vite`（经 `cmd /c npm run dev`） |

2. **其他任何工具不得再启动 `uvicorn` / `npm run dev` / `cpolar`**，也不得自行重启它们。
3. 服务以独立顶层进程常驻，编辑代码**自动生效，不需要重启**：
   - 后端：uvicorn 以 `reload=True` 运行，保存 `.py` 即热重载（看终端/日志确认重载，而非重启进程）；
   - 前端：Vite HMR，保存即更新；
   - 验证手段：`curl.exe http://127.0.0.1:8000/api/v1/auth/methods` 与浏览器实际操作。

## 二、行为红线（所有工具必须遵守）

- **禁止**用 `Get-NetTCPConnection ... | Stop-Process -Force`、`netstat + Stop-Process`、`taskkill /F /IM` 等方式按端口/进程名批量清理服务；
- **禁止**抢占已在监听的 5173 / 8000 / 4040；
- **禁止** kill cpolar（免费隧道域名与重启绑定，重启会换域名并破坏微信网页授权配置）；
- 认为服务异常时，**先诊断、不擅杀**：健康检查 → 查看 `.devservices/runtime.json` 与进程命令行 → 在对话中向用户报告，由用户决定是否用规范脚本重启：
  `powershell -ExecutionPolicy Bypass -File .trae\skills\launch-services-detached\scripts\stop_services.ps1`

## 三、分支与提交协同

1. `main` 为受保护集成分支：只接收已通过测试的完整批次，**禁止 force-push**；
2. 各工具在独立特性分支工作：`feat/<工具名>-<主题>`（如 `feat/harness-iges-reader`），完成并自测后合并/PR；
3. 同文件并行编辑前先沟通；提交信息注明工具来源与测试证据，不提交未跟踪的半成品、假数据与调试产物（见 `.gitignore`）；
4. 不代替用户执行提交/推送以外的破坏性 Git 操作。

## 四、共享数据库与测试协同

1. 本地开发与测试共用同一 SQLite（`backend/evolution_ai.db`）：
   - 只允许使用幂等的 `init_db()` 迁移，**禁止**删库/清表等破坏性操作；
   - 测试夹具必须自具备前置条件并清理自有数据（参考 `tests/conftest.py` 的 `demo_user` fixture）；
2. 同一时刻只允许一个长批次测试/训练任务；开始前先检查是否有 `pytest` / 训练进程在运行；
3. 种子/演示数据须明确标注且经用户同意，禁止伪造“未来时间”的统计数据。

## 五、交接与冲突恢复

1. 运行时元数据由启动脚本写入 `.devservices/runtime.json`（gitignored）：owner、启动时间、域名；
2. 工作交接：在对话中说明“改动了什么、在哪个分支、测试结果、待决事项”，不留无归属的未跟踪文件；
3. 发现非本工具拉起的服务实例时：记录其 PID/命令行/父进程链 → 报告用户 → 按本协议由用户统一处置；
4. cpolar 域名变化时，规范脚本会自动同步 `backend/.env` 的 `MP_REDIRECT_URI`；
   若域名改变，需提醒用户到微信测试号后台更新「网页授权域名」。

## 六、检查清单（每个工具开工前 30 秒自检）

- [ ] 服务已在运行（5173/8000/4040 LISTENING）→ 我只编辑文件，不启动、不重启、不杀进程
- [ ] 我的改动在当前分支，且不与他人编辑同一文件
- [ ] 需要验证时用 curl / 浏览器，而非重启服务
- [ ] 测试前后清理自有数据；不运行与他人冲突的长任务

---

*协议版本 v1（2026-10-02）。如需调整规则，由用户确认后升版。*
