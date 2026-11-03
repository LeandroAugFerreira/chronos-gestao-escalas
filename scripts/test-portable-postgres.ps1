param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR, [string[]]$TestArgs = @('-q'))
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$binaryPath = Join-Path $RuntimeDir 'postgres\pgsql\bin\pg_ctl.exe'
$dataPath = Join-Path $RuntimeDir 'pg-test-data'
$credentialsPath = Join-Path $RuntimeDir 'pg-test.env'
if (-not (Test-Path -LiteralPath $binaryPath) -or -not (Test-Path -LiteralPath $credentialsPath)) {
    throw 'Runtime portátil não disponível. Use um PostgreSQL de teste e scripts\check-postgres.ps1.'
}
$entry = Get-Content -LiteralPath $credentialsPath | Where-Object { $_.StartsWith('CHRONOS_TEST_POSTGRES_URL=') } | Select-Object -First 1
if (-not $entry) { throw 'Configuração do PostgreSQL de teste ausente.' }
$previousTestUrl = $env:CHRONOS_TEST_POSTGRES_URL
$previousPgBin = $env:CHRONOS_PG_BIN
$env:CHRONOS_PG_BIN = Split-Path -Parent $binaryPath
$env:CHRONOS_TEST_POSTGRES_URL = $entry.Substring('CHRONOS_TEST_POSTGRES_URL='.Length)
$startedHere = $false
try {
    & $binaryPath -D $dataPath status *> $null
    if ($LASTEXITCODE -ne 0) {
        & $binaryPath -D $dataPath -l (Join-Path $RuntimeDir 'pg-test-server.log') -o '-h 127.0.0.1 -p 5547 -c shared_buffers=32MB -c max_connections=20' -w start
        if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar o PostgreSQL de teste.' }
        $startedHere = $true
    }
    $pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
    $projectPath = Split-Path -Parent $PSScriptRoot
    & $pythonPath (Join-Path $projectPath 'backend\scripts\run_tests.py') @TestArgs
    if ($LASTEXITCODE -ne 0) { throw 'Testes do perfil portátil falharam.' }
} finally {
    if ($startedHere) {
        & $binaryPath -D $dataPath -m fast -w stop
    }
    $env:CHRONOS_TEST_POSTGRES_URL = $previousTestUrl
    $env:CHRONOS_PG_BIN = $previousPgBin
}
