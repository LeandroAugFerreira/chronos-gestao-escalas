param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR, [switch]$Once, [switch]$Scheduler)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Execute scripts\setup.ps1 primeiro.' }
Push-Location (Join-Path (Split-Path -Parent $PSScriptRoot) 'backend')
try {
    $workerArgs = @('scripts/automation_worker.py')
    if ($Once) { $workerArgs += '--once' }
    if ($Scheduler) { $workerArgs += '--scheduler' }
    & $pythonPath @workerArgs
    if ($LASTEXITCODE -ne 0) { throw 'Consumidor de automações encerrou com erro.' }
} finally { Pop-Location }
