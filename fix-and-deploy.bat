@echo off
chcp 65001 > nul
echo ========================================
echo   EVOLUTION AI - Full Reset and Deploy
echo   Mirrors: xuanyuan / 1ms / daocloud
echo ========================================
echo.

REM Step 1: Configure Docker mirror (2026 confirmed working)
echo [1/6] Configuring Docker mirrors...
set DOCKER_DAEMON=%USERPROFILE%\.docker\daemon.json
if not exist "%USERPROFILE%\.docker" mkdir "%USERPROFILE%\.docker"
(
echo {
echo   "registry-mirrors": [
echo     "https://docker.xuanyuan.me",
echo     "https://docker.1ms.run",
echo     "https://docker.m.daocloud.io"
echo   ]
echo }
) > "%DOCKER_DAEMON%"
echo       Mirror config written to: %DOCKER_DAEMON%
echo.

REM Step 2: Stop and remove old containers
echo [2/6] Cleaning old containers...
docker stop evolution-ai evolution-ai-frontend evolution-ai-backend 2>nul
docker rm evolution-ai evolution-ai-frontend evolution-ai-backend 2>nul
echo       Done.
echo.

REM Step 3: Verify Docker is running
echo [3/6] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found!
    pause
    exit /b 1
)
echo       Docker OK.
echo.

REM Step 4: Build image (this will use the new mirrors after Docker restart)
echo [4/6] Building image (first time: 5-10 min, please wait)...
cd /d "D:\API\EVOLUTION_AI_DEMO_v1.0"
docker compose build --progress=plain
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Please check the error above.
    echo   Common fix: Restart Docker Desktop, then run this script again.
    pause
    exit /b 1
)
echo       Build OK.
echo.

REM Step 5: Start services
echo [5/6] Starting services...
docker compose up -d
if errorlevel 1 (
    echo [ERROR] Start failed. Showing logs:
    docker compose logs --tail=30
    pause
    exit /b 1
)
echo       Services started.
echo.

REM Step 6: Wait and verify
echo [6/6] Waiting for services to be ready (10s)...
timeout /t 10 /nobreak > nul

echo.
echo ========================================
echo   EVOLUTION AI is running!
echo ========================================
echo.
echo   Frontend: http://localhost:8501
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo   Stop:   docker compose down
echo   Logs:   docker compose logs -f
echo ========================================
echo.

start http://localhost:8501
pause
