$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$collectorRoot = Join-Path $projectRoot 'we-mp-rss'
$collectorData = Join-Path $collectorRoot 'data'
$configPath = Join-Path $collectorData 'config.yaml'
$configExample = Join-Path $collectorRoot 'config.example.yaml'
$venvRoot = Join-Path $env:LOCALAPPDATA 'CenturyCabinet\we-rss-venv'
$venvPython = Join-Path $venvRoot 'Scripts\python.exe'

Write-Host '正在准备 21世纪内阁 V1.0 本机环境...'

New-Item -ItemType Directory -Path $collectorData -Force | Out-Null
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath $configExample -Destination $configPath
    Write-Host '已创建本机私有配置：we-mp-rss/data/config.yaml'
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3.13 -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw '无法创建 Python 3.13 虚拟环境。请先安装 Python 3.13。'
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip 升级失败。' }

& $venvPython -m pip install -r (Join-Path $collectorRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '采集器依赖安装失败。' }

Write-Host "虚拟环境：$venvRoot"
Write-Host '本机数据目录不会被 Git 上传。'
