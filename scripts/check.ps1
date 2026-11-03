param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
& $pythonPath (Join-Path $projectPath 'backend\scripts\generate_demo.py') --check
if ($LASTEXITCODE -ne 0) { throw 'Fixture inválida.' }
& $pythonPath (Join-Path $PSScriptRoot 'validate_phase1.py')
if ($LASTEXITCODE -ne 0) { throw 'Documentação/metadados inválidos.' }
Push-Location (Join-Path $projectPath 'backend')
try {
    & $pythonPath (Join-Path $projectPath 'backend\scripts\run_tests.py') -q
    if ($LASTEXITCODE -ne 0) { throw 'Testes backend falharam.' }
} finally { Pop-Location }
Push-Location (Join-Path $projectPath 'frontend')
try {
    npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw 'Testes frontend falharam.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Compilação frontend falhou.' }
} finally { Pop-Location }
