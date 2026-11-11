# Cria o atalho "Painel DP" na área de trabalho (e, com -Inicializacao, também na inicialização do Windows)
param([switch]$Inicializacao)

$pasta = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = (Get-Command pythonw -ErrorAction Stop).Source }
$icone = Join-Path $pasta 'painel.ico'
$shell = New-Object -ComObject WScript.Shell

function Novo-Atalho($destino, $argumentos) {
    $a = $shell.CreateShortcut($destino)
    $a.TargetPath = $pythonw
    $a.Arguments = $argumentos
    $a.WorkingDirectory = $pasta
    $a.IconLocation = "$icone,0"
    $a.Description = 'Painel de Demandas do Departamento Pessoal'
    $a.Save()
    Write-Output "Atalho criado: $destino"
}

$desktop = [Environment]::GetFolderPath('Desktop')
Novo-Atalho (Join-Path $desktop 'Painel DP.lnk') "`"$pasta\painel.py`""

if ($Inicializacao) {
    $startup = [Environment]::GetFolderPath('Startup')
    Novo-Atalho (Join-Path $startup 'Painel DP (segundo plano).lnk') "`"$pasta\painel.py`" --sem-navegador"
}
