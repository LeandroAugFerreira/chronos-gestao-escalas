param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$runtimePath = [IO.Path]::GetFullPath($RuntimeDir)
$projectPath = Split-Path -Parent $PSScriptRoot
$securityStatus = Get-Content -LiteralPath (Join-Path $projectPath 'automation\n8n\security-status.json') -Raw | ConvertFrom-Json
if ($securityStatus.execution_allowed -ne $true) { throw 'Chronos 1.0: partida n8n bloqueada pela auditoria da Fase 9. Consulte docs/security/phase9-findings.md; o consumidor local continua disponível.' }
if ($runtimePath -match '(?i)onedrive' -or $runtimePath.StartsWith($projectPath + '\', [StringComparison]::OrdinalIgnoreCase) -or $runtimePath -eq $projectPath) { throw 'Use runtime fora do projeto e OneDrive.' }
$manifest = Get-Content -LiteralPath (Join-Path $projectPath 'automation\n8n\runtime.json') -Raw | ConvertFrom-Json
$nodePath = Join-Path $runtimePath ('node-' + $manifest.node_version + '-win-x64')
$n8nBin = Join-Path $runtimePath 'n8n\node_modules\n8n\bin\n8n'
if (-not (Test-Path -LiteralPath $n8nBin) -or -not (Test-Path -LiteralPath (Join-Path $nodePath 'node.exe'))) { throw 'Execute scripts\setup-n8n.ps1 primeiro.' }
$values = @{
    PATH = $nodePath + ';' + $env:PATH; NODE_OPTIONS = '--max-old-space-size=768'; N8N_USER_FOLDER = (Join-Path $runtimePath 'n8n-user')
    N8N_LISTEN_ADDRESS = '127.0.0.1'; N8N_HOST = '127.0.0.1'; N8N_PORT = '5687'; N8N_PROTOCOL = 'http'; N8N_SECURE_COOKIE = 'false'
    N8N_DIAGNOSTICS_ENABLED = 'false'; N8N_PERSONALIZATION_ENABLED = 'false'; N8N_VERSION_NOTIFICATIONS_ENABLED = 'false'; N8N_TEMPLATES_ENABLED = 'false'
    N8N_LICENSE_AUTO_RENEW_ENABLED = 'false'; N8N_COMMUNITY_PACKAGES_ENABLED = 'false'; N8N_SENTRY_DSN = ''; N8N_FRONTEND_SENTRY_DSN = ''
    N8N_RUNNERS_ENABLED = 'false'; N8N_PYTHON_ENABLED = 'false'; N8N_BLOCK_ENV_ACCESS_IN_NODE = 'true'; N8N_PAYLOAD_SIZE_MAX = '1'
    NODES_INCLUDE = '["n8n-nodes-base.webhook","n8n-nodes-base.httpRequest"]'
}
$previous = @{}
try {
    foreach ($key in $values.Keys) { $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process'); [Environment]::SetEnvironmentVariable($key, $values[$key], 'Process') }
    & (Join-Path $nodePath 'node.exe') $n8nBin start
    if ($LASTEXITCODE -ne 0) { throw 'n8n local encerrou com erro.' }
} finally {
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
}
