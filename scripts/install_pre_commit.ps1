# 安装仓库级 pre-commit 门禁（复制到 .git/hooks，不修改全局 git config）
$root = Split-Path -Parent $PSScriptRoot
$hookDir = Join-Path $root ".git\hooks"
$target = Join-Path $hookDir "pre-commit"
New-Item -ItemType Directory -Force -Path $hookDir | Out-Null
if (Test-Path $target) {
  $backup = "$target.bak-$(Get-Date -Format yyyyMMddHHmmss)"
  Copy-Item $target $backup
  Write-Host "已备份原钩子到 $backup"
}
Copy-Item (Join-Path $root ".githooks\pre-commit") $target -Force
Write-Host "已安装 $target"
Write-Host "验证：python scripts/pre_commit_check.py"
