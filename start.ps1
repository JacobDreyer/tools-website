# Field Kit — build the front end if needed, then serve everything on :8765.
#   .\start.ps1          normal run
#   .\start.ps1 -Dev     API on :8765 + Vite dev server on :5173 (hot reload)
param([switch]$Dev, [switch]$Rebuild)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root 'server\.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host '> creating venv' -ForegroundColor Cyan
    py -m venv (Join-Path $root 'server\.venv')
    & $python -m pip install -q -r (Join-Path $root 'server\requirements.txt')
}

if (-not (Test-Path (Join-Path $root 'frontend\node_modules'))) {
    Write-Host '> npm install' -ForegroundColor Cyan
    npm --prefix (Join-Path $root 'frontend') install
}

if ($Dev) {
    Write-Host '> api  http://127.0.0.1:8765' -ForegroundColor Cyan
    Write-Host '> ui   http://localhost:5173' -ForegroundColor Cyan
    Start-Process -FilePath $python -ArgumentList (Join-Path $root 'server\app.py'), '--reload'
    npm --prefix (Join-Path $root 'frontend') run dev
    return
}

if ($Rebuild -or -not (Test-Path (Join-Path $root 'frontend\dist\index.html'))) {
    Write-Host '> building front end' -ForegroundColor Cyan
    npm --prefix (Join-Path $root 'frontend') run build
}

& $python (Join-Path $root 'server\app.py')
