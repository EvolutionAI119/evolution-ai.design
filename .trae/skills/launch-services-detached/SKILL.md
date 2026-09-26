---
name: launch-services-detached
description: 以独立顶层进程启动 EVOLUTION AI 三服务（cpolar 隧道、FastAPI 后端、Vite 前端），服务不被命令宿主连带清理。当需要启动或重启本地三服务、服务意外掉线、或需同步 cpolar 新域名时使用。
---

# 独立进程启动服务

## 核心原则：为什么不用后台任务

- `run_in_background` 的后台任务与 Shell 命令宿主共享进程作业；在同一作业链中执行 pytest 等命令会触发连带清理，把长期运行的 cpolar / 后端 / 前端一起带停（本项目已多次发生）。
- 长期服务**必须**用 `Start-Process` 启动独立顶层进程（`-WindowStyle Hidden`），与命令通道的生命周期解耦。
- 不要用 `Start-Job`（作业受 PowerShell 会话管理，会话结束即消失），也不要在前台阻塞启动。

## 日常用法

```powershell
# 一键启动（幂等：已在监听的端口自动跳过；隧道在线则复用，域名变了自动同步 .env）
powershell -ExecutionPolicy Bypass -File .\.trae\skills\launch-services-detached\scripts\start_services.ps1

# 改完后端代码后最常用：重启后端+前端，保持 cpolar 隧道与域名不变
powershell -ExecutionPolicy Bypass -File .\.trae\skills\launch-services-detached\scripts\start_services.ps1 -Restart

# 停止后端+前端（不动隧道）
powershell -ExecutionPolicy Bypass -File .\.trae\skills\launch-services-detached\scripts\stop_services.ps1

# 连隧道一起停 / 启动时完全不启隧道
stop_services.ps1 -Tunnel
start_services.ps1 -NoTunnel
```

## 启动顺序与域名处理（脚本已内置；手动操作时必须遵循）

1. **先 cpolar**：`Start-Process <cpolar.exe> -ArgumentList 'http','8000'`；4040 已监听则复用，不重启。
2. 用 `curl.exe -s http://127.0.0.1:4040/http/in` 配合正则 `https://[a-z0-9]+\.r31\.cpolar\.top` 提取公网域名。**必须用 curl.exe**——Invoke-WebRequest 拿到的正文为空。
3. 域名与 `.env` 的 `MP_REDIRECT_URI` 不一致时（cpolar 免费版每次重启必换），**先更新 .env 再启动后端**；顺序反了授权链接会带旧域名。
4. **后端**：`Start-Process python -ArgumentList 'start.py' -WorkingDirectory <项目>\backend`（工作目录必须是 backend，端口 8000）。
5. **前端**：`Start-Process cmd -ArgumentList '/c','npm run dev' -WorkingDirectory <项目根>`（端口 5173）。
6. cpolar.exe 不在 PATH 也不在常规位置时，脚本自动下载 3.3.12（zip → `msiexec /a` 管理安装提取 exe）到 `%LOCALAPPDATA%\cpolar`。

## 红线与约束

- **任何命令载荷中不得出现明文凭证**（cpolar authtoken、API Key、appsecret）。密钥只进 `.env`；cpolar authtoken 由用户自行在终端执行 `cpolar authtoken <token>` 保存。
- PowerShell 5.1：顺序连接命令用 `;`，不用 `&&`；curl 一律写 `curl.exe`（PS 的 `curl` 是 Invoke-WebRequest 别名）。
- **先查端口再启动**：`netstat -ano | Select-String ':8000 .*LISTENING'`。僵尸进程会与新进程同时抢占端口、请求被随机分流（本项目实际发生过），必须杀掉所有监听 PID 后再启动。
- `.env` 写回必须是**无 BOM UTF-8**：`[System.IO.File]::WriteAllText(path, text, (New-Object System.Text.UTF8Encoding($false)))`。PS5 的 `Set-Content` 默认编码会破坏文件。
- 脚本须兼容 PowerShell 5.1：不用 `??`、`?.`、三元运算符。

## 验收标准

- 5173 / 8000 / 4040 三个端口均 LISTENING，且每个端口只有预期实例。
- `curl.exe http://127.0.0.1:8000/api/v1/auth/methods` 返回 JSON。
- `curl.exe https://<域名>/api/v1/auth/methods` 公网返回 HTTP 200。
- 域名发生变化时，必须提醒用户去微信测试号后台更新「网页授权获取用户基本信息」的域名。

## 故障速查

- 端口被占但服务异常：先跑 `stop_services.ps1`（多轮清理，覆盖后端 StatReload 父子进程），再启动。
- **停止后端口几秒内又被占用**：检查是否有用户自己的终端或 IDE 运行配置也在跑 `python start.py` / `npm run dev`——会与脚本实例并存（本项目实际出现过两个 reloader 父进程抢占 8000）。脚本只管理自己拉起的实例；并存实例需在对应终端中关闭，必要时用 CIM 核对命令行：`Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select ProcessId, CommandLine`。
- 4040 在监听但取不到域名：隧道尚未就绪，等待 1–2 秒后重试（脚本内已重试 10 次）。
- 后端启动失败：确认工作目录为 backend、`.env` 未被改坏（编码/语法）。
- 手机扫码显示成功但 PC 不跳转：确认前端为含 ticket 逻辑的版本（见 backend `auth.py` 的 `/mp/authorize`、`/mp/poll` 与前端 `Login.vue`），PC 按会话票据轮询。
