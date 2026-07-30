@echo off
chcp 65001 > nul
echo ========================================
echo   Configure Docker Mirror Accelerator
echo ========================================
echo.

set DOCKER_DAEMON=%USERPROFILE%\.docker\daemon.json

if exist "%DOCKER_DAEMON%" (
    echo [1/2] Backing up original config to daemon.json.bak
    copy "%DOCKER_DAEMON%" "%DOCKER_DAEMON%.bak" >nul
) else (
    echo [1/2] Creating new config file
    if not exist "%USERPROFILE%\.docker" mkdir "%USERPROFILE%\.docker"
)

echo [2/2] Writing mirror sources...
(
echo {
echo   "registry-mirrors": [
echo     "https://docker.mirrors.ustc.edu.cn",
echo     "https://hub-mirror.c.163.com",
echo     "https://mirror.baidubce.com"
echo   ]
echo }
) > "%DOCKER_DAEMON%"

echo.
echo ========================================
echo   Mirror accelerator configured
echo ========================================
echo.
echo   Mirrors:
echo     - USTC:  docker.mirrors.ustc.edu.cn
echo     - 163:   hub-mirror.c.163.com
echo     - Baidu: mirror.baidubce.com
echo.
echo   Restart Docker Desktop to take effect:
echo     Right-click tray icon - Quit Docker Desktop
echo     Then reopen Docker Desktop
echo.
echo   After restart, double-click start-docker.bat
echo ========================================
pause
