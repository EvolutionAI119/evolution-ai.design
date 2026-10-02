<#
.SYNOPSIS
  以独立顶层进程启动 EVOLUTION AI 三服务（cpolar 隧道 / FastAPI 后端 / Vite 前端）。
.DESCRIPTION
  幂等：已在监听的端口自动跳过。cpolar 免费版重启换域名时自动同步 backend\.env 的
  MP_REDIRECT_URI。-Restart 先停后端与前端（默认不动隧道，保持域名不变）。
#>
[CmdletBinding()]
param(
    [switch]$Restart,   # 先停止后端(8000)+前端(5173)再启动
    [switch]$NoTunnel   # 跳过 cpolar 隧道
)
$ErrorActionPreference = 'Stop'

# ── 路径：脚本位于 <root>\.trae\skills\launch-services-detached\scripts ──
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$backendDir  = Join-Path $projectRoot 'backend'
$envFile     = Join-Path $backendDir '.env'
$cpolarPkg   = 'https://www.cpolar.com/static/downloads/releases/3.3.12/cpolar-stable-windows-amd64-setup.zip'

# ── 端口工具 ──
function Get-PortPid {
    param([int]$Port)
    $line = netstat -ano | Select-String ":$Port .*LISTENING" | Select-Object -First 1
    if ($line) { return [int](($line.ToString().Trim() -split '\s+')[-1]) }
    return $null
}

function Wait-Port {
    param([int]$Port, [int]$TimeoutSec = 30, [switch]$Free)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $listening = $null -ne (Get-PortPid -Port $Port)
        if ($Free -and -not $listening) { return $true }
        if (-not $Free -and $listening) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# 命令行级进程探测：reload 父进程在重启 server 子进程的瞬间端口短暂空闲，
# 仅靠端口检查会重复启动（曾出现两个 start.py 并存、请求随机分流）。
function Find-ServiceProc {
    param([string]$Pattern)
    $items = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match $Pattern })
    return $items
}

# ── cpolar 可执行文件：查找 / 自动安装 ──
function Find-CpolarExe {
    $cmd = Get-Command cpolar.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'cpolar\cpolar.exe'),
        (Join-Path $env:TEMP 'cpolar_dl\extract\cpolar\cpolar.exe')
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return (Resolve-Path $p).Path }
    }
    return $null
}

function Install-CpolarExe {
    Write-Host '[cpolar] 未找到客户端，下载并安装 3.3.12 ...'
    $dstDir = Join-Path $env:LOCALAPPDATA 'cpolar'
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    $zip   = Join-Path $env:TEMP ("cpolar-{0}.zip" -f (Get-Random))
    $unzip = Join-Path $env:TEMP ("cpolar-u-{0}" -f (Get-Random))
    $stage = Join-Path $env:TEMP ("cpolar-s-{0}" -f (Get-Random))
    try {
        & curl.exe -sL -o $zip $cpolarPkg
        Expand-Archive -Path $zip -DestinationPath $unzip -Force
        $msi = Get-ChildItem $unzip -Recurse -Filter '*.msi' | Select-Object -First 1
        Start-Process -FilePath 'msiexec.exe' `
            -ArgumentList @('/a', $msi.FullName, '/qn', "TARGETDIR=$stage") `
            -Wait | Out-Null
        $exe = Get-ChildItem $stage -Recurse -Filter 'cpolar.exe' | Select-Object -First 1
        if (-not $exe) { throw 'cpolar.exe 提取失败' }
        Copy-Item $exe.FullName (Join-Path $dstDir 'cpolar.exe') -Force
    }
    finally {
        Remove-Item $zip, $unzip, $stage -Recurse -Force -ErrorAction SilentlyContinue
    }
    return (Join-Path $dstDir 'cpolar.exe')
}

# ── 域名提取 / .env 同步（无 BOM UTF-8） ──
# cpolar 免费域名：兼容各区域后缀（r31.cpolar.top / r7.cpolar.cn 等）
$DomainPattern = '[a-z0-9]+\.r\d+\.cpolar\.(?:top|cn|com)'

function Get-CpolarDomain {
    for ($i = 0; $i -lt 10; $i++) {
        $raw = & curl.exe -s --max-time 10 http://127.0.0.1:4040/http/in
        $m = [regex]::Match(($raw -join "`n"), "https://$DomainPattern")
        if ($m.Success) {
            return [regex]::Match($m.Value, "(?<=https://)$DomainPattern").Value
        }
        Start-Sleep -Seconds 1
    }
    return $null
}

function Get-EnvDomain {
    $text = [System.IO.File]::ReadAllText($envFile)
    $m = [regex]::Match($text, "(?m)^MP_REDIRECT_URI=https://($DomainPattern)")
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

function Set-EnvDomain {
    param([string]$Domain)
    $newLine = "MP_REDIRECT_URI=https://$Domain/api/v1/auth/mp/callback"
    $text = [System.IO.File]::ReadAllText($envFile)
    if ($text -match '(?m)^MP_REDIRECT_URI=') {
        $text = [regex]::Replace($text, '(?m)^MP_REDIRECT_URI=.*$', $newLine)
    }
    else {
        $text = $text.TrimEnd("`r", "`n") + "`r`n$newLine`r`n"
    }
    [System.IO.File]::WriteAllText($envFile, $text, (New-Object System.Text.UTF8Encoding($false)))
}

# ── 1. 可选：先停后端+前端（保持隧道） ──
if ($Restart) {
    & (Join-Path $PSScriptRoot 'stop_services.ps1')
}

# ── 2. cpolar 隧道（4040 已在监听则复用） ──
$domain = $null
if (-not $NoTunnel) {
    if (-not (Get-PortPid -Port 4040)) {
        $cpolarExe = Find-CpolarExe
        if (-not $cpolarExe) { $cpolarExe = Install-CpolarExe }
        Write-Host '[cpolar] 启动隧道 http 8000 ...'
        Start-Process -FilePath $cpolarExe -ArgumentList 'http', '8000' -WindowStyle Hidden
        if (-not (Wait-Port -Port 4040 -TimeoutSec 40)) {
            throw 'cpolar 启动超时（4040 未监听）'
        }
    }
    else {
        Write-Host '[cpolar] 隧道已在运行，复用'
    }
    $domain = Get-CpolarDomain
    if (-not $domain) { throw '无法从 4040 页面提取公网域名' }
    if ((Get-EnvDomain) -ne $domain) {
        Write-Host "[cpolar] 域名变化，已同步 .env -> $domain"
        Set-EnvDomain -Domain $domain
    }
    else {
        Write-Host "[cpolar] 域名未变：$domain"
    }
}

# ── 3. 后端（工作目录必须是 backend） ──
$backendProcs = Find-ServiceProc -Pattern 'python.*start\.py'
if (Get-PortPid -Port 8000) {
    Write-Host '[backend] 8000 已在监听，跳过'
}
elseif ($backendProcs.Count -gt 0) {
    Write-Host '[backend] start.py 已在运行（reload 重启窗口），等待现有实例 ...'
}
else {
    Write-Host '[backend] 启动 python start.py ...'
    Start-Process -FilePath 'python' -ArgumentList 'start.py' `
        -WorkingDirectory $backendDir -WindowStyle Hidden
}
if (-not (Wait-Port -Port 8000 -TimeoutSec 30)) {
    throw '后端启动超时（8000 未监听）'
}
$backendParents = @(Find-ServiceProc -Pattern 'python.*start\.py')
if ($backendParents.Count -ne 1) {
    throw "检测到 $($backendParents.Count) 个 start.py 实例，请先运行 stop_services.ps1 清理"
}

# ── 4. 前端 ──
$frontendProcs = Find-ServiceProc -Pattern 'vite[/\\]bin[/\\]vite'
if (Get-PortPid -Port 5173) {
    Write-Host '[frontend] 5173 已在监听，跳过'
}
elseif ($frontendProcs.Count -gt 0) {
    Write-Host '[frontend] vite 已在运行（启动窗口），等待现有实例 ...'
}
else {
    Write-Host '[frontend] 启动 npm run dev ...'
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev' `
        -WorkingDirectory $projectRoot -WindowStyle Hidden
}
if (-not (Wait-Port -Port 5173 -TimeoutSec 30)) {
    throw '前端启动超时（5173 未监听）'
}

# ── 4.5 运行时标记：供其他工具识别所有者，避免重复启动/抢占（见 COLLABORATION_PROTOCOL.md） ──
$runtimeDir = Join-Path $projectRoot '.devservices'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$tunnelUrl = $null
if ($domain) { $tunnelUrl = "https://$domain" }
$runtime = [ordered]@{
    owner    = 'launch-services-detached'
    started_at = (Get-Date).ToString('s')
    backend  = 'http://127.0.0.1:8000/'
    frontend = 'http://127.0.0.1:5173/'
    tunnel   = $tunnelUrl
}
[System.IO.File]::WriteAllText((Join-Path $runtimeDir 'runtime.json'),
    ($runtime | ConvertTo-Json),
    (New-Object System.Text.UTF8Encoding($false)))

# ── 5. 验收 ──
Write-Host ''
Write-Host '=== 服务状态 ==='
$methods = & curl.exe -s --max-time 10 http://127.0.0.1:8000/api/v1/auth/methods
Write-Host "methods : $methods"
if ($domain) {
    $pubCode = & curl.exe -s -o NUL -w '%{http_code}' --max-time 15 `
        "https://$domain/api/v1/auth/methods"
    Write-Host "public  : HTTP $pubCode (https://$domain)"
    if ($pubCode -ne '200') {
        Write-Warning '公网链路异常，请检查 cpolar 隧道'
    }
}
Write-Host ''
Write-Host '完成：前端 http://127.0.0.1:5173/  后端 http://127.0.0.1:8000/'
