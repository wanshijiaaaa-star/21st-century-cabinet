$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw '未找到 Git，无法执行发布隐私检查。'
}

$forbiddenTrackedPatterns = @(
    '(^|/)site/data/',
    '(^|/)we-mp-rss/data/',
    '(^|/)we-mp-rss/config\.yaml$',
    '(^|/)\.env$',
    '(^|/)\.env\.(?!example$)',
    '\.(db|sqlite|sqlite3|log|pem|key|lic)$',
    '接入清单.*\.csv$',
    '(^|/)site/\.openai/hosting\.json$',
    'site-deploy.*\.(zip|tar\.gz)$'
)

$safeRepository = $projectRoot.Replace('\', '/')
$trackedFiles = @(& git -c "safe.directory=$safeRepository" ls-files)
if ($LASTEXITCODE -ne 0) {
    throw 'Git could not list tracked files; the privacy check did not run.'
}
$violations = foreach ($path in $trackedFiles) {
    foreach ($pattern in $forbiddenTrackedPatterns) {
        if ($path -match $pattern) {
            $path
            break
        }
    }
}

if ($violations) {
    Write-Host '发现不应被 Git 跟踪的文件：' -ForegroundColor Red
    $violations | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
    exit 1
}

$textFiles = $trackedFiles | Where-Object {
    $_ -match '\.(cmd|ps1|py|js|ts|tsx|vue|html|css|json|md|txt|yaml|yml|toml|ini|csv)$'
}
$privateMarkers = 'C:\\Users\\Lenovo|appgprj_[A-Za-z0-9]+|git\.chatgpt-team\.site|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
$contentViolations = foreach ($path in $textFiles) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        if (Select-String -LiteralPath $path -Pattern $privateMarkers -Quiet) {
            $path
        }
    }
}

if ($contentViolations) {
    Write-Host '发现本机路径、内部项目标识或私钥标记：' -ForegroundColor Red
    $contentViolations | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host '隐私检查通过：未发现被跟踪的运行数据或已知私人标记。' -ForegroundColor Green
