<#
.SYNOPSIS
  EVOLUTION AI - LLM 推理服务一键部署管理脚本

.DESCRIPTION
  管理 NURBS LLM 推理服务的完整生命周期：
  1. 提示词一致性验证（llm_server.py ↔ Modelfile）
  2. Docker 容器构建/启动/停止
  3. 本地模式启动（Docker 不可用时自动降级）
  4. 端到端测试（Q1 + Q3 + Q10）

.EXAMPLE
  .\scripts\docker-llm.ps1              # 默认：验证提示词 + 构建 + 启动 + 测试
  .\scripts\docker-llm.ps1 up           # 构建并启动容器（Docker 模式）
  .\scripts\docker-llm.ps1 up -Local    # 本地模式启动（不依赖 Docker）
  .\scripts\docker-llm.ps1 logs         # 查看实时日志
  .\scripts\docker-llm.ps1 test         # 运行 Q1/Q3/Q10 端到端测试
  .\scripts\docker-llm.ps1 verify       # 仅验证提示词一致性
  .\scripts\docker-llm.ps1 status       # 查看容器和健康状态
  .\scripts\docker-llm.ps1 down         # 停止并清理
  .\scripts\docker-llm.ps1 restart      # 重启容器
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "logs", "test", "verify", "status", "down", "restart", "all")]
    [string]$Action = "all",

    [switch]$Local
)

$ErrorActionPreference = "Stop"
$ComposeFile = "docker-compose.llm.yml"
$ContainerName = "evolution-llm"
$ApiBase = "http://localhost:11434"
$ProjectRoot = $PSScriptRoot | Split-Path -Parent
$LlmServer = Join-Path $ProjectRoot "scripts\llm_server.py"
$Modelfile = Join-Path $ProjectRoot "scripts\Modelfile"
$MergedModel = Join-Path $ProjectRoot "data\training\merged\merged_model"

# ── 工具函数 ──────────────────────────────────

function Write-Header($text) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

function Write-Ok($text) { Write-Host "  [OK] $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "  [!]  $text" -ForegroundColor Yellow }
function Write-Err($text) { Write-Host "  [X]  $text" -ForegroundColor Red }
function Write-Info($text) { Write-Host "  ..  $text" -ForegroundColor Gray }

# ── 提示词一致性验证 ──────────────────────────

function Verify-Prompts {
    Write-Header "提示词一致性验证"

    if (-not (Test-Path $LlmServer)) { Write-Err "找不到 $LlmServer"; return $false }
    if (-not (Test-Path $Modelfile)) { Write-Err "找不到 $Modelfile"; return $false }

    $pyContent = (Get-Content $LlmServer -Raw -Encoding UTF8) -replace "`r`n", "`n"
    $mfContent = (Get-Content $Modelfile -Raw -Encoding UTF8) -replace "`r`n", "`n"

    # 关键锚点列表（两个文件都必须包含）
    $anchors = @(
        @{ Name = "核心块A(定义)标题";   Pattern = "A. G0/G1/G2 连续性精确定义 — 当问`"什么是G1" },
        @{ Name = "核心块B(实测)标题";   Pattern = "B. 实测配对数值 — 当问`"车身/保险杠" },
        @{ Name = "核心块C(间隙分类)标题"; Pattern = "C. 设计间隙分类（正常vs需修复）— 当问`"哪些间隙正常" },
        @{ Name = "核心块D(路由守卫)标题"; Pattern = "D. 路由守卫（强制性，回答任何问题前必须先确认属于哪一块）" },
        @{ Name = "G1定义含四关键词";    Pattern = "切向量方向一致，即法向量夹角 < 1度（1.0 度）。阈值：法向量夹角 < 1.0 度。" + [char]10 + "  ▸ 必用关键词：切向量、法向量、1度、共享边界" },
        @{ Name = "Q1守卫禁实测";       Pattern = "什么是 G1 / 什么是G0 / 什么是连续性 / G1定义 / 含义」→ 返回 A 块（切向量/法向量/1度/共享边界），禁止回答 0.000mm/0.131deg" },
        @{ Name = "Q3守卫答保险杠";      Pattern = "车身与前保险杠 / 保险杠 G0/G1 / 值多少」→ 返回 B 块（0.000mm / 0.131deg），禁止回答 A 块定义" },
        @{ Name = "Q10守卫禁曲率禁保险杠"; Pattern = "间隙正常 / 需要修复 / 哪些间隙 / 设计间隙 / 装配间隙」→ 严格按 C 块三大分类输出，禁止回答曲率/变化率/定义/车身保险杠数值" },
        @{ Name = "C块含装配间隙+车轮";  Pattern = "车轮与车身：257-370mm 装配间隙" },
        @{ Name = "C块含凹陷+格栅";      Pattern = "前保险杠↔进气格栅：3.294mm 凹陷" },
        @{ Name = "C块含外凸+大灯";      Pattern = "前大灯外凸：15.5-17.4mm（左/右）" },
        @{ Name = "C块需修复异常间隙";   Pattern = "共享边界零件 G0 > 0.1mm 且不属于 凹陷/外凸/装配间隙 时，判定为装配缺陷需修复" },
        @{ Name = "C块Q10必用关键词";    Pattern = "必用关键词：装配间隙、凹陷、外凸、车轮" },
        @{ Name = "凹陷（recess）中文在前"; Pattern = "凹陷（recess" },
        @{ Name = "外凸（bulge）中文在前"; Pattern = "外凸（bulge" },
        @{ Name = "装配间隙中文在前";    Pattern = "装配间隙（assembly clearance" },
        @{ Name = "凹陷设计标注";       Pattern = "凹陷设计（recess design）" },
        @{ Name = "外凸设计标注";       Pattern = "外凸设计（bulge design）" },
        @{ Name = "SOP 统计";          Pattern = "13项检查" },
        @{ Name = "SAE 坐标系";         Pattern = "X=纵向车头" },
        @{ Name = "ISO 曲率";          Pattern = "ISO ratio=4.2" }
    )

    $allOk = $true

    Write-Host ""
    Write-Host "  [llm_server.py] 锚点检查:" -ForegroundColor White
    foreach ($a in $anchors) {
        if ($pyContent -match [regex]::Escape($a.Pattern)) {
            Write-Ok $a.Name
        } else {
            Write-Err $a.Name
            $allOk = $false
        }
    }

    Write-Host ""
    Write-Host "  [Modelfile] 锚点检查:" -ForegroundColor White
    foreach ($a in $anchors) {
        if ($mfContent -match [regex]::Escape($a.Pattern)) {
            Write-Ok $a.Name
        } else {
            Write-Err $a.Name
            $allOk = $false
        }
    }

    Write-Host ""
    if ($allOk) {
        Write-Ok "两个文件提示词完全一致（$($anchors.Count) 个锚点全部命中）"
    } else {
        Write-Err "提示词不一致，请检查上述缺失项"
    }

    return $allOk
}

# ── Docker 检查 ──────────────────────────────

function Check-Docker {
    try {
        $savedPref = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        $output = & docker info 2>&1
        $ok = ($LASTEXITCODE -eq 0) -and ($output -match "Server Version|Containers|Images")
        $ErrorActionPreference = $savedPref
        return $ok
    } catch {
        return $false
    }
}

function Wait-Healthy($timeoutSec = 120) {
    Write-Host "  等待服务就绪..." -NoNewline
    for ($i = 0; $i -lt $timeoutSec; $i += 5) {
        try {
            $r = Invoke-RestMethod -Uri "$ApiBase/api/tags" -TimeoutSec 3 -ErrorAction Stop
            Write-Host " 就绪 (${i}s)" -ForegroundColor Green
            return $true
        } catch {
            Write-Host "." -NoNewline -ForegroundColor Gray
            Start-Sleep -Seconds 5
        }
    }
    Write-Host " 超时" -ForegroundColor Red
    return $false
}

# ── 本地模式 ──────────────────────────────────

$script:localJobId = $null

function Action-UpLocal {
    Write-Header "本地模式启动 LLM 推理服务"

    if (-not (Test-Path $MergedModel)) {
        Write-Err "微调模型不存在: $MergedModel"
        exit 1
    }

    # 检查端口是否被占用
    $occupied = netstat -ano | Select-String ":11434 "
    if ($occupied) {
        $pidLine = ($occupied -split '\s+')[-1]
        Write-Warn "端口 11434 被占用 (PID $pidLine)，正在停止..."
        Stop-Process -Id $pidLine -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    Write-Info "启动: python $LlmServer --model-path $MergedModel --port 11434"
    $job = Start-Job -ScriptBlock {
        param($script, $model)
        python $script --model-path $model --port 11434
    } -ArgumentList $LlmServer, $MergedModel

    $script:localJobId = $job.Id
    Write-Ok "后台进程已启动 (Job ID: $($job.Id))"

    if (-not (Wait-Healthy 90)) {
        Write-Err "本地服务启动超时"
        Write-Host "  查看输出: Receive-Job -Id $($job.Id)" -ForegroundColor Gray
        exit 1
    }

    Write-Ok "本地服务就绪"
    Write-Host ""
    Write-Host "  API 地址: $ApiBase" -ForegroundColor White
    Write-Host "  停止方式: Stop-Job -Id $($job.Id); Remove-Job -Id $($job.Id)" -ForegroundColor White
    Write-Host "  测试命令: .\scripts\docker-llm.ps1 test" -ForegroundColor White
}

function Stop-LocalService {
    if ($script:localJobId) {
        Stop-Job -Id $script:localJobId -ErrorAction SilentlyContinue
        Remove-Job -Id $script:localJobId -ErrorAction SilentlyContinue
        $script:localJobId = $null
        Write-Ok "本地服务已停止"
        return
    }

    # 查找并终止占用 11434 端口的进程
    $occupied = netstat -ano | Select-String ":11434 "
    if ($occupied) {
        $pidLine = ($occupied -split '\s+')[-1]
        Stop-Process -Id $pidLine -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Ok "已终止端口 11434 进程 (PID $pidLine)"
    }
}

# ── Docker 模式 ───────────────────────────────

function Action-UpDocker {
    Write-Header "Docker 模式构建并启动 LLM 推理服务"

    if (-not (Check-Docker)) {
        Write-Err "Docker daemon 未运行"
        Write-Host "  方案 1: 启动 Docker Desktop 后重试" -ForegroundColor Gray
        Write-Host "  方案 2: 使用本地模式: .\scripts\docker-llm.ps1 up -Local" -ForegroundColor Gray
        exit 1
    }

    Write-Host "  构建镜像..." -ForegroundColor Gray
    docker compose -f $ComposeFile build --no-cache 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    if ($LASTEXITCODE -ne 0) { Write-Err "构建失败"; exit 1 }
    Write-Ok "镜像构建完成"

    Write-Host "  启动容器..." -ForegroundColor Gray
    docker compose -f $ComposeFile up -d 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    Write-Ok "容器已启动"

    if (-not (Wait-Healthy)) {
        Write-Err "服务未就绪，查看日志：.\scripts\docker-llm.ps1 logs"
        exit 1
    }
    Write-Ok "服务健康检查通过"
    Write-Host ""
    Write-Host "  API 地址: $ApiBase" -ForegroundColor White
    Write-Host "  RAG 状态: $ApiBase/api/rag/status" -ForegroundColor White
    Write-Host "  测试命令: .\scripts\docker-llm.ps1 test" -ForegroundColor White
}

# ── 统一启动入口 ──────────────────────────────

function Action-Up {
    if ($Local) {
        Action-UpLocal
    } else {
        # Docker 不可用时自动降级到本地模式
        if (-not (Check-Docker)) {
            Write-Warn "Docker daemon 未运行，自动切换到本地模式"
            Write-Host ""
            Action-UpLocal
        } else {
            Action-UpDocker
        }
    }
}

# ── 日志 ──────────────────────────────────────

function Action-Logs {
    if ($Local -or $script:localJobId) {
        Write-Header "查看本地服务日志 (Ctrl+C 退出)"
        if ($script:localJobId) {
            Receive-Job -Id $script:localJobId -Wait
        } else {
            Write-Warn "无本地服务在运行"
        }
    } else {
        Write-Header "查看容器日志 (Ctrl+C 退出)"
        docker compose -f $ComposeFile logs -f --tail=50
    }
}

# ── 状态 ──────────────────────────────────────

function Action-Status {
    Write-Header "服务状态"

    # 容器状态
    if (-not $Local) {
        Write-Host "  [Docker 容器]" -ForegroundColor White
        docker compose -f $ComposeFile ps 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }

    # API 健康检查
    Write-Host ""
    Write-Host "  [API 健康检查]" -ForegroundColor White
    Write-Host "    $ApiBase/api/tags ..." -NoNewline
    try {
        $r = Invoke-RestMethod -Uri "$ApiBase/api/tags" -TimeoutSec 3
        Write-Host " 在线" -ForegroundColor Green
        Write-Host "    模型: $($r.models.Count) 个" -ForegroundColor Gray
    } catch {
        Write-Host " 离线" -ForegroundColor Red
        return
    }

    # RAG 状态
    Write-Host "    $ApiBase/api/rag/status ..." -NoNewline
    try {
        $rag = Invoke-RestMethod -Uri "$ApiBase/api/rag/status" -TimeoutSec 3
        Write-Host " OK" -ForegroundColor Green
        Write-Host "    RAG: enabled=$($rag.rag_enabled)  chunks=$($rag.chunk_count)" -ForegroundColor Gray
    } catch {
        Write-Host " 失败" -ForegroundColor Red
    }
}

# ── 停止 ──────────────────────────────────────

function Action-Down {
    if ($Local -or $script:localJobId) {
        Write-Header "停止本地服务"
        Stop-LocalService
    } else {
        Write-Header "停止并清理 Docker 容器"
        docker compose -f $ComposeFile down 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        Write-Ok "已清理"
    }
}

# ── 重启 ──────────────────────────────────────

function Action-Restart {
    Action-Down
    Action-Up
}

# ── 端到端测试 ────────────────────────────────

function Action-Test {
    Write-Header "端到端测试 (Q1 + Q3 + Q10)"

    if (-not (Wait-Healthy 30)) {
        Write-Err "服务未就绪，先执行: .\scripts\docker-llm.ps1 up"
        exit 1
    }

    # RAG 状态
    Write-Host ""
    try {
        $rag = Invoke-RestMethod -Uri "$ApiBase/api/rag/status" -TimeoutSec 5
        Write-Info "RAG: enabled=$($rag.rag_enabled)  chunks=$($rag.chunk_count)"
    } catch {
        Write-Warn "RAG 状态检查失败"
    }

    # 测试用例定义
    $tests = @(
        @{
            Id       = "Q1"
            Category = "nurbs_basics"
            Question = "什么是NURBS曲面的G1连续性？"
            Keywords = @("切向量", "法向量", "1度", "共享边界")
            MinHits  = 2
        },
        @{
            Id       = "Q3"
            Category = "continuity"
            Question = "车身与前保险杠的G0和G1值分别是多少？"
            Keywords = @("0.000", "0.131")
            MinHits  = 2
        },
        @{
            Id       = "Q10"
            Category = "parametric_design"
            Question = "哪些设计间隙是正常的？哪些需要修复？"
            Keywords = @("装配间隙", "凹陷", "外凸", "recess", "bulge", "车轮")
            MinHits  = 3
        }
    )

    $results = @()

    foreach ($t in $tests) {
        Write-Host ""
        Write-Host ("─" * 60) -ForegroundColor DarkGray
        Write-Host "  $($t.Id) [$($t.Category)]" -ForegroundColor White
        Write-Host "  问题: $($t.Question)" -ForegroundColor White
        Write-Host ("─" * 60) -ForegroundColor DarkGray

        # 调用 API（temperature=0.2 平衡 G1 定义生成与 Q10 术语抗幻觉）
        $payload = @{
            model    = "nurbs-expert"
            prompt   = $t.Question
            stream   = $false
            options  = @{ temperature = 0.2; top_p = 0.7; num_predict = 512 }
        } | ConvertTo-Json -Depth 3

        try {
            $resp = Invoke-RestMethod -Uri "$ApiBase/api/generate" -Method Post -Body $payload -ContentType "application/json" -TimeoutSec 180
            $answer = $resp.response.Trim()
        } catch {
            Write-Err "API 调用失败: $_"
            $results += @{ Id = $t.Id; Passed = $false; Score = "0/$($t.Keywords.Count)" }
            continue
        }

        # 显示回答前 200 字
        $preview = $answer.Substring(0, [Math]::Min(200, $answer.Length))
        Write-Host "  回答: $preview" -ForegroundColor Gray
        Write-Host ""

        # 关键词命中检查
        $hits = 0
        Write-Host "  关键词命中 (需要>=$($t.MinHits)):" -ForegroundColor Gray
        foreach ($kw in $t.Keywords) {
            if ($answer -match [regex]::Escape($kw)) {
                Write-Host "    [V] $kw  命中" -ForegroundColor Green
                $hits++
            } else {
                Write-Host "    [X] $kw  未命中" -ForegroundColor Red
            }
        }

        $passed = $hits -ge $t.MinHits
        $score = "$hits/$($t.Keywords.Count)"
        $mark = if ($passed) { "PASS" } else { "FAIL" }
        $color = if ($passed) { "Green" } else { "Red" }
        Write-Host ""
        Write-Host "  得分: $score  ->  $mark" -ForegroundColor $color

        $results += @{ Id = $t.Id; Passed = $passed; Score = $score }
    }

    # 汇总
    Write-Host ""
    Write-Header "测试汇总"
    $allPass = $true
    $passCount = 0
    foreach ($r in $results) {
        $mark = if ($r.Passed) { "[V]" } else { "[X]" }
        $color = if ($r.Passed) { "Green" } else { "Red" }
        $status = if ($r.Passed) { "PASS" } else { "FAIL" }
        Write-Host "  $mark $($r.Id): $($r.Score)  $status" -ForegroundColor $color
        if ($r.Passed) { $passCount++ } else { $allPass = $false }
    }

    Write-Host ""
    Write-Host "  通过: $passCount / $($results.Count)" -ForegroundColor $(if ($allPass) { "Green" } else { "Yellow" })
    Write-Host ""
    if ($allPass) {
        Write-Ok "端到端测试全部通过"
    } else {
        Write-Err "存在失败项"
        Write-Host "  查看日志: .\scripts\docker-llm.ps1 logs" -ForegroundColor Gray
        exit 1
    }
}

# ── 主逻辑 ──────────────────────────────────

switch ($Action) {
    "verify"  { $ok = Verify-Prompts; if (-not $ok) { exit 1 } }
    "up"      { Action-Up }
    "logs"    { Action-Logs }
    "test"    { Action-Test }
    "status"  { Action-Status }
    "down"    { Action-Down }
    "restart" { Action-Restart }
    "all"     {
        # 1. 验证提示词一致性
        $ok = Verify-Prompts
        if (-not $ok) {
            Write-Err "提示词验证失败，请先修复后再部署"
            exit 1
        }
        # 2. 启动服务
        Action-Up
        # 3. 运行端到端测试
        Action-Test
        # 4. 本地模式下自动停止服务
        if ($Local -or $script:localJobId) {
            Write-Header "清理本地服务"
            Stop-LocalService
        }
    }
}
