$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktopPath = [Environment]::GetFolderPath('Desktop')
$pythonPath = "C:\Users\ponte\AppData\Local\Programs\Python\Python312\python.exe"
$shortcutPath = Join-Path $desktopPath "Painel DP.lnk"
$iconPath = Join-Path $scriptPath "painel.ico"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = "`"$scriptPath\painel.py`""
$shortcut.WorkingDirectory = $scriptPath
$shortcut.Description = "Painel de gestão de demandas DP"
$shortcut.WindowStyle = 0

if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
}

$shortcut.Save()

Write-Host "Atalho criado na area de trabalho!"
Write-Host "Arquivo: $shortcutPath"
