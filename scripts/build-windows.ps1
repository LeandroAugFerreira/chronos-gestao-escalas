param(
    [Parameter(Mandatory=$true)][string]$RuntimeDir,
    [string]$OutputDir
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $RuntimeDir 'venv\Scripts\python.exe'
$toolPath = Join-Path $RuntimeDir 'build-tools'
if (-not $OutputDir) { $OutputDir = Join-Path $projectRoot 'releases\windows' }
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Ambiente Python de compilação não encontrado.' }
if (-not (Test-Path -LiteralPath (Join-Path $toolPath 'PyInstaller'))) { throw 'PyInstaller deve estar instalado no diretório build-tools do runtime de compilação.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) { throw 'Execute o build do frontend primeiro.' }
$previousPythonPath = $env:PYTHONPATH
$previousTclPath = $env:TCL_LIBRARY
$previousTkPath = $env:TK_LIBRARY
try {
    $env:PYTHONPATH = $toolPath
    $basePython = (& $pythonPath -c 'import sys; print(sys.base_prefix)').Trim()
    $env:TCL_LIBRARY = Join-Path $basePython 'tcl\tcl8.6'
    $env:TK_LIBRARY = Join-Path $basePython 'tcl\tk8.6'
    Push-Location $projectRoot
    & $pythonPath -m PyInstaller --noconfirm --distpath $OutputDir --workpath (Join-Path $RuntimeDir 'pyinstaller-chronos-1.0') 'desktop\Chronos.spec'
    if ($LASTEXITCODE -ne 0) { throw 'Falha na compilação do executável.' }
} finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
    $env:TCL_LIBRARY = $previousTclPath
    $env:TK_LIBRARY = $previousTkPath
}
