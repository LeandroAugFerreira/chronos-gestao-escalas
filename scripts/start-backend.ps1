param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Execute scripts\setup.ps1 primeiro.' }
Push-Location (Join-Path (Split-Path -Parent $PSScriptRoot) 'backend')
try {
    & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8017
    if ($LASTEXITCODE -ne 0) { throw 'O backend encerrou com erro.' }
} finally { Pop-Location }
