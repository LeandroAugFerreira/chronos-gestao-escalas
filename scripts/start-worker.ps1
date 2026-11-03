param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR, [switch]$Once)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Execute scripts\setup.ps1 primeiro.' }
Push-Location (Join-Path (Split-Path -Parent $PSScriptRoot) 'backend')
try {
    $workerArgs = @('scripts/worker.py', '--runtime-dir', $RuntimeDir)
    if ($Once) { $workerArgs += '--once' }
    & $pythonPath @workerArgs
    if ($LASTEXITCODE -ne 0) { throw 'O worker encerrou com erro.' }
} finally { Pop-Location }
