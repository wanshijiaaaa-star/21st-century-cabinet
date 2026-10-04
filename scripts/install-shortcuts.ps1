$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $projectRoot 'site\launch-cabinet.ps1'
$icon = Join-Path $projectRoot 'site\assets\cabinet-icon.ico'
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "找不到启动器：$launcher"
}
if (-not (Test-Path -LiteralPath $icon)) {
    throw "找不到快捷方式图标：$icon"
}

$desktop = [Environment]::GetFolderPath('Desktop')
$startMenu = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'
$shortcutPaths = @(
    (Join-Path $desktop '21世纪内阁.lnk'),
    (Join-Path $startMenu '21世纪内阁.lnk')
)

$shell = New-Object -ComObject WScript.Shell
foreach ($path in $shortcutPaths) {
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $powershell
    $shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`""
    $shortcut.WorkingDirectory = Join-Path $projectRoot 'site'
    $shortcut.IconLocation = "$icon,0"
    $shortcut.Description = '启动21世纪内阁本机服务并打开网页'
    $shortcut.Save()
}

Write-Host '已创建快捷方式：' -ForegroundColor Green
$shortcutPaths | ForEach-Object { Write-Host "  $_" }
Write-Host '可以在开始菜单中搜索“21世纪内阁”，右键后选择固定到开始屏幕或任务栏。'
