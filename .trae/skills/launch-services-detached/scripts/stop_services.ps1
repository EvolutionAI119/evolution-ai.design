<#
.SYNOPSIS
  停止 EVOLUTION AI 后端(8000)与前端(5173)。
.DESCRIPTION
  默认保留 cpolar 隧道以维持公网域名不变；多轮清理以覆盖后端 StatReload
  父子双进程及端口释放延迟。-Tunnel 时连同 cpolar(4040) 一起停止，
  注意免费版隧道重启后公网域名会变化。
#>
[CmdletBinding()]
param(
    [switch]$Tunnel,
    [int]$TimeoutSec = 30
)
$ports = @(8000, 5173)
if ($Tunnel) { $ports += 4040 }

# 递归收集子孙进程 PID：后端 StatReload/uvicorn 为父子多进程结构，
# 只杀监听端口的父进程会留下持有套接字的孤儿 worker（实际踩过）
function Get-DescendantPids {
    param([int]$ParentPid)
    $result = @()
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentPid" `
        -ErrorAction SilentlyContinue)
    foreach ($child in $children) {
        $childPid = [int]$child.ProcessId
        $result += $childPid
        $result += Get-DescendantPids -ParentPid $childPid
    }
    return $result
}

# 多轮清理：杀掉每个端口监听 PID 及其整个进程树
for ($round = 1; $round -le 3; $round++) {
    $killedAny = $false
    foreach ($port in $ports) {
        $procIds = @()
        foreach ($line in (netstat -ano | Select-String ":$port .*LISTENING")) {
            $procIds += [int](($line.ToString().Trim() -split '\s+')[-1])
        }
        # 监听 PID + 其所有子孙，去重后一并终止
        $targets = @()
        foreach ($procId in ($procIds | Sort-Object -Unique)) {
            $targets += $procId
            $targets += Get-DescendantPids -ParentPid $procId
        }
        foreach ($targetPid in ($targets | Sort-Object -Unique)) {
            try {
                Stop-Process -Id $targetPid -Force -ErrorAction Stop
                Write-Host "port ${port}: killed PID $targetPid"
                $killedAny = $true
            }
            catch {}
        }
    }
    if (-not $killedAny) { break }
    Start-Sleep -Seconds 1
}

# 等待端口全部释放
$deadline = (Get-Date).AddSeconds($TimeoutSec)
$remaining = $true
while ((Get-Date) -lt $deadline -and $remaining) {
    $remaining = $false
    foreach ($port in $ports) {
        if (netstat -ano | Select-String ":$port .*LISTENING" -Quiet) {
            $remaining = $true
        }
    }
    if ($remaining) { Start-Sleep -Milliseconds 500 }
}

if ($remaining) {
    Write-Warning '部分端口仍被占用：'
    foreach ($port in $ports) {
        if (netstat -ano | Select-String ":$port .*LISTENING" -Quiet) {
            Write-Warning "  $port"
        }
    }
}
else {
    $suffix = if ($Tunnel) { '（含隧道）' } else { '（隧道保留）' }
    Write-Host "全部已停止$suffix"
}

# 清理运行时标记（防止其他工具读到过期的 owner 信息）
$runtimeMarker = Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path '.devservices\runtime.json'
if (Test-Path $runtimeMarker) { Remove-Item $runtimeMarker -Force }
