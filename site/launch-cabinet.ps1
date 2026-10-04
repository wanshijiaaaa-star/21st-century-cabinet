$ErrorActionPreference = 'Stop'

$url = 'http://127.0.0.1:4173/'
$statusUrl = "${url}api/status"
$serverScript = Join-Path $PSScriptRoot 'local_server.py'
$dataRoot = Join-Path $PSScriptRoot 'data'
$logRoot = Join-Path $dataRoot 'logs'
$venvPython = Join-Path $env:LOCALAPPDATA 'CenturyCabinet\we-rss-venv\Scripts\python.exe'

function Test-CabinetServer {
    try {
        Invoke-RestMethod -Uri $statusUrl -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Show-CabinetMessage([string]$message, [int]$icon = 48) {
    $shell = New-Object -ComObject WScript.Shell
    $shell.Popup($message, 0, '21世纪内阁', $icon) | Out-Null
}

if (Test-CabinetServer) {
    Start-Process $url
    exit 0
}

$pythonCandidates = @()
if (Test-Path -LiteralPath $venvPython) {
    $pythonCandidates += [pscustomobject]@{ File = $venvPython; Prefix = @() }
}
$pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if ($pyLauncher) {
    $pythonCandidates += [pscustomobject]@{ File = $pyLauncher.Source; Prefix = @('-3') }
}
$systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
if ($systemPython) {
    $pythonCandidates += [pscustomobject]@{ File = $systemPython.Source; Prefix = @() }
}

$python = $null
foreach ($candidate in $pythonCandidates) {
    try {
        & $candidate.File @($candidate.Prefix) -c 'import sys' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate
            break
        }
    } catch {
        continue
    }
}

if (-not $python) {
    Show-CabinetMessage '没有找到可用的 Python。请先运行项目根目录的“安装环境.cmd”。' 16
    exit 1
}

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$stdoutLog = Join-Path $logRoot 'cabinet-server.log'
$stderrLog = Join-Path $logRoot 'cabinet-server-error.log'
$arguments = @($python.Prefix) + @("`"$serverScript`"", '--no-browser')

try {
    $serverProcess = Start-Process -FilePath $python.File -ArgumentList $arguments `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
} catch {
    Show-CabinetMessage "无法启动本机服务：$($_.Exception.Message)" 16
    exit 1
}

for ($attempt = 0; $attempt -lt 40; $attempt++) {
    Start-Sleep -Milliseconds 500
    if (Test-CabinetServer) {
        Start-Process $url
        exit 0
    }
    if ($serverProcess.HasExited) {
        break
    }
}

Show-CabinetMessage "本机服务未能启动。请查看日志：`n$stderrLog" 16
exit 1
