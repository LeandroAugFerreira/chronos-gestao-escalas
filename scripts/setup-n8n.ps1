param([string]$RuntimeDir = $env:CHRONOS_RUNTIME_DIR)
$ErrorActionPreference = 'Stop'
if (-not $RuntimeDir) { $RuntimeDir = Join-Path $env:LOCALAPPDATA 'Chronos\1.0' }
$runtimePath = [IO.Path]::GetFullPath($RuntimeDir)
$projectPath = Split-Path -Parent $PSScriptRoot
$securityStatus = Get-Content -LiteralPath (Join-Path $projectPath 'automation\n8n\security-status.json') -Raw | ConvertFrom-Json
if ($securityStatus.execution_allowed -ne $true) { throw 'Chronos 1.0: instalação n8n bloqueada pela auditoria da Fase 9. O runtime existente foi preservado; consulte docs/security/phase9-findings.md.' }
if ($runtimePath -match '(?i)onedrive' -or $runtimePath.StartsWith($projectPath + '\', [StringComparison]::OrdinalIgnoreCase) -or $runtimePath -eq $projectPath) { throw 'Use runtime fora do projeto e OneDrive.' }
$sourcePath = Join-Path $projectPath 'automation\n8n'
$manifest = Get-Content -LiteralPath (Join-Path $sourcePath 'runtime.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
$archiveName = 'node-' + $manifest.node_version + '-win-x64.zip'
$archivePath = Join-Path $runtimePath $archiveName
$nodePath = Join-Path $runtimePath ('node-' + $manifest.node_version + '-win-x64')
if (-not (Test-Path -LiteralPath $archivePath)) { Invoke-WebRequest -Uri ('https://nodejs.org/dist/' + $manifest.node_version + '/' + $archiveName) -OutFile $archivePath }
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.node_zip_sha256) { throw 'Hash do Node divergente; instalação interrompida.' }
if (-not (Test-Path -LiteralPath (Join-Path $nodePath 'node.exe'))) { Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimePath }
$n8nPath = Join-Path $runtimePath 'n8n'
$installedPath = Join-Path $n8nPath 'node_modules\n8n\package.json'
if (Test-Path -LiteralPath $installedPath) {
    $installed = Get-Content -LiteralPath $installedPath -Raw | ConvertFrom-Json
    if ($installed.version -eq $manifest.n8n_version) { Write-Output 'Chronos 1.0: runtime n8n fixado já disponível; instalação preservada.'; return }
    throw 'Há outra versão neste runtime. Preserve-a e escolha um diretório novo para a versão fixada.'
}
New-Item -ItemType Directory -Path $n8nPath -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $sourcePath 'package.json') -Destination (Join-Path $n8nPath 'package.json')
Copy-Item -LiteralPath (Join-Path $sourcePath 'package-lock.json') -Destination (Join-Path $n8nPath 'package-lock.json')
$previousPath = $env:PATH; $previousOptions = $env:NODE_OPTIONS
$previousPlaywright = $env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD; $previousPuppeteer = $env:PUPPETEER_SKIP_DOWNLOAD
try {
    $env:PATH = $nodePath + ';' + $env:PATH; $env:NODE_OPTIONS = '--max-old-space-size=768'
    $env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'; $env:PUPPETEER_SKIP_DOWNLOAD = 'true'
    & (Join-Path $nodePath 'node.exe') (Join-Path $nodePath 'node_modules\npm\bin\npm-cli.js') ci --prefix $n8nPath --cache (Join-Path $runtimePath 'npm-cache') --no-audit --no-fund --registry=https://registry.npmjs.org
    if ($LASTEXITCODE -ne 0) { throw 'Instalação n8n isolada não concluída.' }
} finally {
    $env:PATH = $previousPath; $env:NODE_OPTIONS = $previousOptions
    $env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = $previousPlaywright; $env:PUPPETEER_SKIP_DOWNLOAD = $previousPuppeteer
}
Write-Output 'Chronos 1.0: n8n preparado somente no runtime local; nenhum workflow ativado.'
