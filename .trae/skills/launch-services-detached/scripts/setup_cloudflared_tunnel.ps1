<#
.SYNOPSIS
  一次性初始化 cloudflared 命名隧道（固定域名，永久解决微信扫码 10003 域名漂移）。
.DESCRIPTION
  前置（用户手动，一次性）：
    1. Cloudflare 控制台添加站点 evolution-ai.design（Free 计划）
    2. 到域名注册商把 NS 改为 Cloudflare 分配的两个 nameserver
    3. 本目录同级先执行：cloudflared tunnel login（浏览器授权，选 evolution-ai.design）
  本脚本完成：创建隧道 evoai-api -> 写 config.yml -> 绑定 api.evolution-ai.design DNS。
  之后 start_services.ps1 检测到 config.yml 会自动改用 cloudflared，cpolar 退为备用。
  GitHub Pages 不受影响：在 Cloudflare DNS 保留 @ / www 的 CNAME 指向 GitHub 即可。
.PARAMETER Hostname
  固定回调域名，默认 api.evolution-ai.design
#>
[CmdletBinding()]
param(
    [string]$Hostname = 'api.evolution-ai.design',
    [string]$TunnelName = 'evoai-api'
)
$ErrorActionPreference = 'Stop'

$cfExe = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
if ($cfExe) { $cf = $cfExe.Source }
else {
    $cf = Join-Path $env:LOCALAPPDATA 'cloudflared\cloudflared.exe'
    if (-not (Test-Path $cf)) { throw '未找到 cloudflared.exe' }
}

$cfDir = Join-Path $env:USERPROFILE '.cloudflared'
$cert = Join-Path $cfDir 'cert.pem'
if (-not (Test-Path $cert)) {
    throw "缺少 $cert。请先执行：& '$cf' tunnel login（浏览器完成授权后重跑本脚本）"
}

# 1. 创建隧道（已存在则复用）
$list = & $cf tunnel list --output json 2>$null | ConvertFrom-Json
$existing = @($list | Where-Object { $_.name -eq $TunnelName })
if ($existing.Count -gt 0) {
    $tunnelId = $existing[0].id
    Write-Host "[tunnel] 复用已存在隧道 $TunnelName ($tunnelId)"
}
else {
    Write-Host "[tunnel] 创建隧道 $TunnelName ..."
    & $cf tunnel create $TunnelName
    $list = & $cf tunnel list --output json | ConvertFrom-Json
    $tunnelId = @($list | Where-Object { $_.name -eq $TunnelName })[0].id
    if (-not $tunnelId) { throw '隧道创建失败' }
    Write-Host "[tunnel] 已创建 $tunnelId"
}

$credFile = Join-Path $cfDir "$tunnelId.json"
if (-not (Test-Path $credFile)) { throw "缺少凭证文件 $credFile" }

# 2. 写 config.yml（无 BOM UTF-8）
$config = @"
tunnel: $tunnelId
credentials-file: $credFile

ingress:
  - hostname: $Hostname
    service: http://localhost:8000
  - service: http_status:404
"@
[System.IO.File]::WriteAllText((Join-Path $cfDir 'config.yml'), $config,
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host "[config] 已写入 $cfDir\config.yml（$Hostname -> http://localhost:8000）"

# 3. 绑定 DNS（幂等）
Write-Host "[dns] 绑定 $Hostname ..."
& $cf tunnel route dns $TunnelName $Hostname

Write-Host ''
Write-Host "完成。后续每次启动由 start_services.ps1 自动拉起隧道。"
Write-Host "最后一步（手动，一次性）：微信测试号后台「网页授权域名」填：$Hostname"
