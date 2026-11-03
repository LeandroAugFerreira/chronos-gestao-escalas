param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$runtimePath = [System.IO.Path]::GetFullPath($RuntimeDir)
if ($runtimePath.StartsWith($projectPath, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Escolha CHRONOS_RUNTIME_DIR fora da pasta do projeto/OneDrive para o ambiente e os caches.'
}
$venvPath = Join-Path $runtimePath 'venv'
$pythonPath = Join-Path $venvPath 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv --without-pip $venvPath
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente virtual.' }
}
python -m pip --python $pythonPath install --cache-dir (Join-Path $runtimePath 'pip-cache') -r (Join-Path $projectPath 'backend\requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências Python.' }
& $pythonPath (Join-Path $projectPath 'backend\scripts\generate_demo.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Fixture inválida; confira antes de regenerar.' }
& $pythonPath (Join-Path $projectPath 'backend\scripts\manage.py') init-local --runtime $runtimePath
if ($LASTEXITCODE -ne 0) { throw 'Falha na configuração local.' }
& $pythonPath (Join-Path $projectPath 'backend\scripts\manage.py') migrate
if ($LASTEXITCODE -ne 0) { throw 'Falha nas migrations.' }
& $pythonPath (Join-Path $projectPath 'backend\scripts\manage.py') seed-demo
if ($LASTEXITCODE -ne 0) { throw 'Falha na importação da demonstração.' }
Push-Location (Join-Path $projectPath 'frontend')
try {
    npm.cmd ci --cache (Join-Path $runtimePath 'npm-cache') --no-fund --no-audit
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências frontend.' }
} finally { Pop-Location }
Write-Host "Chronos 1.0 preparado. Runtime: $runtimePath"
Write-Host 'Execute start-backend.ps1 e start-frontend.ps1 em terminais separados.'
Write-Host 'Para criar seu acesso, execute scripts\create-admin.ps1 e escolha uma senha.'
