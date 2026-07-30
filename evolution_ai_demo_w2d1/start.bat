@echo off
setlocal
chcp 65001 >nul

set PORT=8080
set DIR=%~dp0

echo ============================================================
echo   EVOLUTION AI DEMO - Local Server
echo ============================================================
echo.
echo Working directory: %DIR%
echo Port: %PORT%
echo.

echo [1/4] Checking port %PORT%...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    echo    Killing process %%P...
    taskkill /F /PID %%P >nul 2>&1
)
echo    Done.

echo.
echo [2/4] Starting HTTP server...
cd /d "%DIR%"
start "EVOLUTION-AI-Server" /min cmd /c "python -m http.server %PORT%"
timeout /t 2 /nobreak >nul
echo    Server started.

echo.
echo [3/4] Opening browser...
start "" "http://localhost:%PORT%/"
echo    Browser opened.

echo.
echo [4/4] Ready.
echo.
echo   URL:        http://localhost:%PORT%/
echo   Pages:      Home, Projects, Quality, Storyboard, Designer
echo   Note:       3D Designer needs backend on port 8000 (start_backend.bat)
echo.
echo Press any key to stop the server...
pause >nul

echo.
echo Stopping server...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%P >nul 2>&1
)
taskkill /F /FI "WINDOWTITLE eq EVOLUTION-AI-Server*" >nul 2>&1
echo Done.
endlocal
