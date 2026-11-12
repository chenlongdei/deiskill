# deiskill 一键安装（Windows PowerShell）：把仓库克隆或更新到 %USERPROFILE%\.deiskill\repo，再运行安装器。
#
#   irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
#
# 只装某几个 Skill，或指定装到哪个 Agent：先下载本脚本，再运行
#   powershell -ExecutionPolicy Bypass -File bootstrap.ps1 dei-capture --target "$HOME\.claude\skills"
$ErrorActionPreference = "Stop"
$RepoUrl = if ($env:DEISKILL_REPO) { $env:DEISKILL_REPO } else { "https://github.com/chenlongdei/deiskill.git" }
$Home_ = if ($env:DEISKILL_HOME) { $env:DEISKILL_HOME } else { Join-Path $HOME ".deiskill" }
$Dest = Join-Path $Home_ "repo"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "缺少 git。请先安装：winget install --id Git.Git -e   装好后重新打开 PowerShell 再运行。" -ForegroundColor Red; exit 1
}
# Windows 上 Python 的命令可能是 python、py 或 python3
$Py = $null
foreach ($c in @("python", "py", "python3")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike "*WindowsApps*") { $Py = $c; break }
}
if (-not $Py) {
    Write-Host "缺少 Python 3.9+。请先安装：winget install --id Python.Python.3.12 -e   装好后重新打开 PowerShell 再运行。" -ForegroundColor Red; exit 1
}

if (Test-Path (Join-Path $Dest ".git")) {
    Write-Host "更新 $Dest"; git -C $Dest pull --ff-only --quiet
} else {
    Write-Host "下载到 $Dest"; New-Item -ItemType Directory -Force -Path $Home_ | Out-Null
    git clone --depth 1 --quiet $RepoUrl $Dest
}
$env:PYTHONUTF8 = "1"
& $Py (Join-Path $Dest "scripts\install.py") @args
