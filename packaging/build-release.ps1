[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [string]$PythonHome,
    [string]$SitePackages
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$packagingRoot = $PSScriptRoot
$repositoryRoot = Split-Path -Parent $packagingRoot
$version = (Get-Content -LiteralPath (Join-Path $repositoryRoot 'VERSION') -Raw).Trim()
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repositoryRoot 'release'
}
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$buildRoot = [System.IO.Path]::GetFullPath((Join-Path $packagingRoot '.build'))
$stageRoot = Join-Path $buildRoot 'payload'
$appRoot = Join-Path $stageRoot 'App'
$runtimeRoot = Join-Path $stageRoot 'Runtime'
$payloadZip = Join-Path $buildRoot 'payload.zip'
$iconPath = Join-Path $repositoryRoot 'site\assets\cabinet-icon.ico'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'

function Assert-ChildPath([string]$Path, [string]$ExpectedRoot) {
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $fullRoot = [System.IO.Path]::GetFullPath($ExpectedRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    if (-not $fullPath.StartsWith($fullRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "拒绝操作预期目录之外的路径：$fullPath"
    }
}

function Clear-GeneratedDirectory([string]$Path, [string]$ExpectedRoot) {
    Assert-ChildPath -Path $Path -ExpectedRoot $ExpectedRoot
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Copy-Tree(
    [string]$Source,
    [string]$Destination,
    [string[]]$ExcludedDirectories = @(),
    [string[]]$ExcludedFiles = @()
) {
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "找不到待打包目录：$Source"
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $arguments = @(
        $Source,
        $Destination,
        '/E',
        '/COPY:DAT',
        '/DCOPY:DAT',
        '/R:2',
        '/W:1',
        '/NFL',
        '/NDL',
        '/NJH',
        '/NJS',
        '/NP'
    )
    if ($ExcludedDirectories.Count -gt 0) {
        $arguments += '/XD'
        $arguments += $ExcludedDirectories
    }
    if ($ExcludedFiles.Count -gt 0) {
        $arguments += '/XF'
        $arguments += $ExcludedFiles
    }
    & robocopy @arguments | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "复制失败（robocopy 退出代码 $LASTEXITCODE）：$Source"
    }
}

function Invoke-Compiler([string[]]$Arguments) {
    & $compiler @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "C# 编译失败，退出代码：$LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $compiler)) {
    throw "找不到 Windows .NET Framework C# 编译器：$compiler"
}
if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "找不到应用图标：$iconPath"
}

if (-not $PythonHome) {
    $PythonHome = (& py -3.13 -c 'import sys; print(sys.base_prefix)').Trim()
}
$PythonHome = [System.IO.Path]::GetFullPath($PythonHome)
if (-not (Test-Path -LiteralPath (Join-Path $PythonHome 'pythonw.exe'))) {
    throw "找不到 Python 3.13 运行时：$PythonHome"
}

if (-not $SitePackages) {
    $SitePackages = Join-Path $env:LOCALAPPDATA 'CenturyCabinet\we-rss-venv\Lib\site-packages'
}
$SitePackages = [System.IO.Path]::GetFullPath($SitePackages)
if (-not (Test-Path -LiteralPath (Join-Path $SitePackages 'fastapi'))) {
    throw "找不到已安装的采集器依赖：$SitePackages`n请先为打包机准备 Python 3.13 依赖，发行版用户无需执行此步骤。"
}

Write-Host "正在构建 21世纪内阁 V$version 独立发行版..."
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
Clear-GeneratedDirectory -Path $stageRoot -ExpectedRoot $buildRoot
Clear-GeneratedDirectory -Path $OutputDirectory -ExpectedRoot $repositoryRoot
New-Item -ItemType Directory -Path $appRoot, $runtimeRoot -Force | Out-Null

Write-Host '1/6 复制私有 Python 运行时（不会安装到用户系统）...'
Copy-Tree -Source $PythonHome -Destination $runtimeRoot `
    -ExcludedDirectories @((Join-Path $PythonHome 'Lib\site-packages'), '__pycache__') `
    -ExcludedFiles @('*.pyc', '*.pyo')
Copy-Tree -Source $SitePackages -Destination (Join-Path $runtimeRoot 'Lib\site-packages') `
    -ExcludedDirectories @('__pycache__') `
    -ExcludedFiles @('*.pyc', '*.pyo')

Write-Host '2/6 复制公开程序文件（排除个人数据和开发文件）...'
$siteStage = Join-Path $appRoot 'site'
New-Item -ItemType Directory -Path $siteStage -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $repositoryRoot 'site\local_server.py') -Destination $siteStage
Copy-Tree -Source (Join-Path $repositoryRoot 'site\dist') -Destination (Join-Path $siteStage 'dist')

$collectorSource = Join-Path $repositoryRoot 'we-mp-rss'
$collectorStage = Join-Path $appRoot 'we-mp-rss'
Copy-Tree -Source $collectorSource -Destination $collectorStage `
    -ExcludedDirectories @(
        (Join-Path $collectorSource 'data'),
        (Join-Path $collectorSource 'web_ui'),
        (Join-Path $collectorSource 'compose'),
        (Join-Path $collectorSource 'docs'),
        (Join-Path $collectorSource 'tests'),
        (Join-Path $collectorSource '.git'),
        (Join-Path $collectorSource '.github'),
        '__pycache__',
        'node_modules'
    ) `
    -ExcludedFiles @(
        '.env',
        '.env.*',
        '*.db',
        '*.sqlite*',
        '*.log',
        '*.pyc',
        '*.pyo',
        '*.bak',
        '*.bat',
        '*.cmd',
        '*.ps1',
        '*.sh'
    )
Copy-Item -LiteralPath (Join-Path $packagingRoot 'runtime_bootstrap.py') -Destination $appRoot
Copy-Item -LiteralPath (Join-Path $repositoryRoot 'VERSION') -Destination $stageRoot
Copy-Item -LiteralPath (Join-Path $repositoryRoot 'LICENSE') -Destination $stageRoot
Copy-Item -LiteralPath (Join-Path $repositoryRoot 'THIRD_PARTY_NOTICES.md') -Destination $stageRoot
Copy-Item -LiteralPath $iconPath -Destination (Join-Path $stageRoot 'cabinet-icon.ico')

Write-Host '3/6 编译无终端图形启动器和卸载器...'
$launcherOutput = Join-Path $stageRoot '21世纪内阁.exe'
$uninstallerOutput = Join-Path $stageRoot '卸载21世纪内阁.exe'
Invoke-Compiler @(
    '/nologo',
    '/target:winexe',
    '/platform:x64',
    '/optimize+',
    "/win32icon:$iconPath",
    "/out:$launcherOutput",
    '/reference:System.dll',
    '/reference:System.Drawing.dll',
    '/reference:System.Windows.Forms.dll',
    (Join-Path $packagingRoot 'launcher\Program.cs')
)
Invoke-Compiler @(
    '/nologo',
    '/target:winexe',
    '/platform:x64',
    '/optimize+',
    "/win32icon:$iconPath",
    "/out:$uninstallerOutput",
    '/reference:System.dll',
    '/reference:System.Drawing.dll',
    '/reference:System.Windows.Forms.dll',
    (Join-Path $packagingRoot 'installer\Uninstaller.cs')
)

Write-Host '4/6 压缩离线应用负载...'
if (Test-Path -LiteralPath $payloadZip) {
    Remove-Item -LiteralPath $payloadZip -Force
}
Push-Location $stageRoot
try {
    & tar.exe -a -c -f $payloadZip *
    if ($LASTEXITCODE -ne 0) {
        throw "离线负载压缩失败，退出代码：$LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host '5/6 编译图形安装程序...'
$installerOutput = Join-Path $OutputDirectory "21世纪内阁-安装程序-$version.exe"
Invoke-Compiler @(
    '/nologo',
    '/target:winexe',
    '/platform:x64',
    '/optimize+',
    "/win32icon:$iconPath",
    "/out:$installerOutput",
    '/reference:System.dll',
    '/reference:System.Core.dll',
    '/reference:System.Drawing.dll',
    '/reference:System.Windows.Forms.dll',
    '/reference:System.IO.Compression.dll',
    '/reference:System.IO.Compression.FileSystem.dll',
    "/resource:$payloadZip,CenturyCabinet.Payload",
    (Join-Path $packagingRoot 'installer\Installer.cs'),
    (Join-Path $packagingRoot 'installer\ShellLink.cs')
)

Write-Host '6/6 生成独立卸载包、说明和校验值...'
$standaloneUninstaller = Join-Path $OutputDirectory '21世纪内阁-卸载程序.exe'
Copy-Item -LiteralPath $uninstallerOutput -Destination $standaloneUninstaller
Copy-Item -LiteralPath (Join-Path $packagingRoot '发行版说明.md') -Destination $OutputDirectory

$artifacts = @($installerOutput, $standaloneUninstaller)
$checksums = foreach ($artifact in $artifacts) {
    $hash = Get-FileHash -LiteralPath $artifact -Algorithm SHA256
    "$($hash.Hash.ToLowerInvariant())  $([System.IO.Path]::GetFileName($artifact))"
}
$checksums | Set-Content -LiteralPath (Join-Path $OutputDirectory 'SHA256SUMS.txt') -Encoding utf8

$archivePath = Join-Path $OutputDirectory "21世纪内阁-发行版-$version.zip"
Push-Location $OutputDirectory
try {
    & tar.exe -a -c -f $archivePath `
        ([System.IO.Path]::GetFileName($installerOutput)) `
        ([System.IO.Path]::GetFileName($standaloneUninstaller)) `
        '发行版说明.md' `
        'SHA256SUMS.txt'
    if ($LASTEXITCODE -ne 0) {
        throw "发行归档压缩失败，退出代码：$LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

Write-Host ''
Write-Host '发行版构建完成：' -ForegroundColor Green
Get-ChildItem -LiteralPath $OutputDirectory -File | Select-Object Name, Length | Format-Table -AutoSize
