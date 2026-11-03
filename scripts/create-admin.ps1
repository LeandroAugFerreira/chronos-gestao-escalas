param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
$managePath = Join-Path (Split-Path -Parent $PSScriptRoot) 'backend\scripts\manage.py'
& $pythonPath $managePath create-admin
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível criar o administrador.' }
