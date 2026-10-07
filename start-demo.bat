@echo off
chcp 65001 > nul
setlocal

REM ============================================================
REM  EVOLUTION AI - 本地一键演示启动器
REM  启动后端(8000) + 前端(5173)，让平台真正可用
REM  生成日期：2026-10-01
REM ============================================================

set ROOT=%~dp0
set PY311=C:\Users\icemt.AI吃豆包的龙虾.000\AppData\Local\Programs\Python\Python311\python.exe

echo ============================================================
echo   EVOLUTION AI - 本地演示环境
echo ============================================================
echo.

REM ---------- 前置检查 ----------
if not exist "%PY311%" (
  echo [错误] 未找到 Python 3.11:
  echo        %PY311%
  echo        请修改本脚本中的 PY311 变量。
  pause & exit /b 1
)
where node >nul 2>&1 || (echo [错误] 未找到 node & pause & exit /b 1)

REM ---------- 后端 ----------
netstat -ano | findstr ":8000 " | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
  echo [提示] 8000 端口已被占用，跳过启动后端。
) else (
  echo [1/2] 启动后端 API ^(127.0.0.1:8000^)...
  REM 注意：不使用 start.py，因为它会带上 --reload。
  REM backend\scripts 等目录有文件变动时 --reload 会不断重启，
  REM 且 Windows 上旧进程可能留下继承的监听套接字
  REM（表现为端口占用但进程已不存在）。演示请用稳定模式：
  start "EVOAI-Backend" cmd /k "cd /d "%ROOT%backend" && "%PY311%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
  timeout /t 14 /nobreak >nul
)

REM ---------- 前端 ----------
netstat -ano | findstr ":5173 " | findstr LISTENING >nul 2>&1
if %errorlevel%==0 (
  echo [提示] 5173 端口已被占用，跳过启动前端。
) else (
  echo [2/2] 启动前端 ^(127.0.0.1:5173^)...
  start "EVOAI-Frontend" cmd /k "cd /d "%ROOT%" && npm run dev"
  timeout /t 10 /nobreak >nul
)

echo.
echo ============================================================
echo   已启动。请在浏览器打开：
echo.
echo     平台入口   http://127.0.0.1:5173/
echo     API 文档   http://127.0.0.1:8000/docs
echo     健康检查   http://127.0.0.1:8000/api/v1/health
echo ============================================================
echo.
echo   关闭演示：直接关掉两个黑色命令行窗口即可。
echo.
start "" http://127.0.0.1:5173/
pause