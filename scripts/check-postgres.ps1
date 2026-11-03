param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
if (-not $env:CHRONOS_TEST_POSTGRES_URL) {
    throw 'Defina CHRONOS_TEST_POSTGRES_URL para um banco PostgreSQL exclusivo terminado em _test. Consulte docs\testing\phase2.md.'
}
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
$projectPath = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectPath 'backend')
try {
    & $pythonPath -m pytest -q tests/test_phase2.py
    if ($LASTEXITCODE -ne 0) { throw 'Validação PostgreSQL falhou.' }
} finally { Pop-Location }
