<#
.SYNOPSIS
    Evolution-AI.Design NURBS 专家模型 Ollama 部署脚本
.DESCRIPTION
    1. 检查/安装 Ollama
    2. 拉取 Qwen2.5-7B-Instruct 基础模型
    3. 创建 nurbs-expert 自定义模型
    4. 运行推理测试
.NOTES
    适用于 Windows PowerShell 5/7
    前置条件: 已安装 Ollama (https://ollama.com/download)
#>

param(
    [string]$ModelName = "nurbs-expert",
    [string]$BaseModel = "qwen2.5:7b-instruct",
    [switch]$UseFinetuned = $false
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NURBS Expert Model - Ollama Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: 检查 Ollama
Write-Host "[1/5] 检查 Ollama 安装..." -ForegroundColor Yellow
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaPath) {
    Write-Host "  Ollama 未安装！请先下载安装: https://ollama.com/download" -ForegroundColor Red
    Write-Host "  安装后重新运行此脚本。" -ForegroundColor Red
    exit 1
}
Write-Host "  Ollama 已安装: $($ollamaPath.Source)" -ForegroundColor Green

# 检查 Ollama 服务状态
Write-Host "  检查 Ollama 服务..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
    Write-Host "  Ollama 服务运行中 (已安装 $($health.models.Count) 个模型)" -ForegroundColor Green
} catch {
    Write-Host "  Ollama 服务未启动，正在启动..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "  Ollama 服务已启动" -ForegroundColor Green
}

# Step 2: 拉取基础模型
Write-Host ""
Write-Host "[2/5] 拉取基础模型: $BaseModel ..." -ForegroundColor Yellow
$existingModels = $health.models.name
if ($BaseModel -in $existingModels) {
    Write-Host "  $BaseModel 已存在，跳过拉取" -ForegroundColor Green
} else {
    Write-Host "  拉取中（约 4.7GB，请耐心等待）..." -ForegroundColor Yellow
    & ollama pull $BaseModel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  拉取失败！请检查网络连接。" -ForegroundColor Red
        exit 1
    }
    Write-Host "  $BaseModel 拉取成功" -ForegroundColor Green
}

# Step 3: 创建 NURBS 专家模型
Write-Host ""
Write-Host "[3/5] 创建 NURBS 专家模型: $ModelName ..." -ForegroundColor Yellow

$modelfilePath = Join-Path $ProjectRoot "scripts\Modelfile"
if (-not (Test-Path $modelfilePath)) {
    Write-Host "  Modelfile 不存在: $modelfilePath" -ForegroundColor Red
    exit 1
}

# 如果使用微调模型，修改 FROM 行
if ($UseFinetuned) {
    $ggufPath = Join-Path $ProjectRoot "data\training\merged\nurbs_expert.gguf"
    if (Test-Path $ggufPath) {
        $content = Get-Content $modelfilePath -Raw
        $content = $content -replace "FROM qwen2.5:7b-instruct", "FROM $ggufPath"
        $tempModelfile = Join-Path $env:TEMP "Modelfile_finetuned"
        Set-Content -Path $tempModelfile -Value $content -Encoding UTF8
        & ollama create "$ModelName-finetuned" -f $tempModelfile
        $ModelName = "$ModelName-finetuned"
    } else {
        Write-Host "  微调 GGUF 文件不存在: $ggufPath" -ForegroundColor Red
        Write-Host "  请先运行: python scripts\merge_lora.py" -ForegroundColor Yellow
        Write-Host "  回退到基础模型..." -ForegroundColor Yellow
        & ollama create $ModelName -f $modelfilePath
    }
} else {
    & ollama create $ModelName -f $modelfilePath
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "  模型创建失败！" -ForegroundColor Red
    exit 1
}
Write-Host "  模型 $ModelName 创建成功" -ForegroundColor Green

# Step 4: 推理测试
Write-Host ""
Write-Host "[4/5] 推理测试..." -ForegroundColor Yellow

$testQuestions = @(
    "什么是NURBS曲面的G1连续性？在汽车A级曲面中有什么要求？",
    "车身蒙皮(body_upper_skin)为什么需要30x20控制点？",
    "SOP检查项8的R角为什么在参数化NURBS车身中大量FAIL？"
)

foreach ($i in 0..($testQuestions.Count - 1)) {
    Write-Host ""
    Write-Host "  测试 $($i + 1)/$($testQuestions.Count):" -ForegroundColor Cyan
    Write-Host "  Q: $($testQuestions[$i])" -ForegroundColor White

    $body = @{
        model  = $ModelName
        prompt = $testQuestions[$i]
        stream = $false
    } | ConvertTo-Json -Depth 3

    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
        -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 60

    $answer = $response.response
    $preview = if ($answer.Length -gt 200) { $answer.Substring(0, 200) + "..." } else { $answer }
    Write-Host "  A: $preview" -ForegroundColor Gray
    Write-Host "  耗时: $([math]::Round($response.total_duration / 1e9, 2))s | Token数: $($response.eval_count)" -ForegroundColor DarkGray
}

# Step 5: 输出部署信息
Write-Host ""
Write-Host "[5/5] 部署完成！" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  部署信息摘要" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  模型名称:    $ModelName" -ForegroundColor White
Write-Host "  Ollama API:  http://localhost:11434" -ForegroundColor White
Write-Host "  交互命令:    ollama run $ModelName" -ForegroundColor White
Write-Host "  API 调用:    POST http://localhost:11434/api/generate" -ForegroundColor White
Write-Host ""
Write-Host "  后端集成:    POST http://localhost:8000/api/v1/ai/chat" -ForegroundColor White
Write-Host "  前端调用:    aiAPI.chatWithExpert(question)" -ForegroundColor White
Write-Host ""
Write-Host "  微调部署:    python scripts\merge_lora.py" -ForegroundColor Yellow
Write-Host "              .\scripts\setup_ollama.ps1 -UseFinetuned" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
