# EVOLUTION AI V2.1 整车造型算法热更新
# 一条命令完成：下载新代码 → 注入容器 → 重启服务

$ErrorActionPreference = "Stop"
$projectDir = "D:\API\EVOLUTION_AI_DEMO_v1.0"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  EVOLUTION AI V2.1 热更新" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 确保项目目录存在
if (-not (Test-Path $projectDir)) {
    New-Item -ItemType Directory -Path $projectDir -Force | Out-Null
    Write-Host "[OK] 创建目录: $projectDir"
}

# Step 1: 下载新代码
Write-Host "[1/5] 下载 car_body_builder.py (V2.1核心算法, 34KB)..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri "https://www.coze.cn/s/KbIP4cIJ3nk/" -OutFile "$projectDir\car_body_builder.py" -UseBasicParsing -TimeoutSec 30
    $size = (Get-Item "$projectDir\car_body_builder.py").Length
    Write-Host "  OK ($size bytes)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
    exit 1
}

Write-Host "[2/5] 下载 app.py (集成V2.1+6车型+I18N, 94KB)..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri "https://www.coze.cn/s/KcAI0ieSKh4/" -OutFile "$projectDir\app.py" -UseBasicParsing -TimeoutSec 30
    $size = (Get-Item "$projectDir\app.py").Length
    Write-Host "  OK ($size bytes)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Docker cp 注入容器
Write-Host "[3/5] 注入 Docker 容器 (evolution-ai)..." -ForegroundColor Yellow
docker cp "$projectDir\car_body_builder.py" evolution-ai:/app/car_body_builder.py
if ($LASTEXITCODE -ne 0) { Write-Host "  docker cp car_body_builder.py FAILED" -ForegroundColor Red; exit 1 }
Write-Host "  car_body_builder.py -> /app/" -ForegroundColor Green

docker cp "$projectDir\app.py" evolution-ai:/app/app.py
if ($LASTEXITCODE -ne 0) { Write-Host "  docker cp app.py FAILED" -ForegroundColor Red; exit 1 }
Write-Host "  app.py -> /app/" -ForegroundColor Green

# Step 3: 重启 Streamlit
Write-Host "[4/5] 重启 Streamlit..." -ForegroundColor Yellow
docker exec evolution-ai pkill -f streamlit 2>$null
Start-Sleep -Seconds 3
docker exec -d evolution-ai bash -c "cd /app && streamlit run app.py --server.port 8501 --server.headless true &"
if ($LASTEXITCODE -ne 0) { Write-Host "  restart FAILED" -ForegroundColor Red; exit 1 }
Write-Host "  OK - Streamlit restarted" -ForegroundColor Green

# Step 4: 验证
Start-Sleep -Seconds 5
Write-Host "[5/5] 验证服务状态..." -ForegroundColor Yellow
$health = docker exec evolution-ai curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>$null
if ($health -eq "200") {
    Write-Host "  Backend: healthy (HTTP 200)" -ForegroundColor Green
} else {
    Write-Host "  Backend: HTTP $health (may need a moment to start)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  V2.1 热更新完成!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "刷新浏览器查看新整车造型:" -ForegroundColor White
Write-Host "  http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "6种车型可选: sedan / SUV / coupe / MPV / sport / pickup" -ForegroundColor Gray
Write-Host ""
