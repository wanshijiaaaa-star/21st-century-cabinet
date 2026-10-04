$ErrorActionPreference = 'Stop'

$siteRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $siteRoot
$collectorRoot = Join-Path $projectRoot 'we-mp-rss'
$collectorData = Join-Path $collectorRoot 'data'
$configPath = Join-Path $collectorData 'config.yaml'
$databasePath = Join-Path $collectorData 'db.db'
$venvPython = Join-Path $env:LOCALAPPDATA 'CenturyCabinet\we-rss-venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw '尚未安装本机环境。请先双击项目根目录的“安装环境.cmd”。'
}

New-Item -ItemType Directory -Path $collectorData -Force | Out-Null
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath (Join-Path $collectorRoot 'config.example.yaml') -Destination $configPath
}

$env:WERSS_ADMIN_USER = 'admin'
$plainPassword = $null
$passwordPointer = [IntPtr]::Zero

try {
    if (-not (Test-Path -LiteralPath $databasePath)) {
        $securePassword = Read-Host '首次启动，请设置本机管理员密码' -AsSecureString
        $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
        if ([string]::IsNullOrWhiteSpace($plainPassword)) {
            throw '管理员密码不能为空。'
        }
        $env:WERSS_ADMIN_PASSWORD = $plainPassword
    }

    Push-Location $collectorRoot
    try {
        & $venvPython main.py -config 'data/config.yaml' -job True -init True
        if ($LASTEXITCODE -ne 0) {
            throw "公众号采集器退出，代码：$LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item Env:WERSS_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:WERSS_ADMIN_USER -ErrorAction SilentlyContinue
    $plainPassword = $null
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
}
