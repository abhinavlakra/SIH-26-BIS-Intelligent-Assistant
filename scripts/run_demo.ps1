# ManakMitra — demo mode (Windows PowerShell)
#
# Builds the frontend and serves the whole app from ONE process on ONE port.
# This is what you should run during judging: nothing to coordinate, no
# "did you start the other server?" failure mode.
#
#     .\scripts\run_demo.ps1     ->  http://localhost:8000

$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot ".."
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "[1/3] Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $frontend
    try { npm install } finally { Pop-Location }
} else {
    Write-Host "[1/3] Frontend dependencies present." -ForegroundColor Cyan
}

Write-Host "[2/3] Building the frontend..." -ForegroundColor Cyan
Push-Location $frontend
try { npm run build } finally { Pop-Location }

Write-Host "`n[3/3] Serving app + API on http://localhost:8000" -ForegroundColor Green
Write-Host "      UI:      http://localhost:8000" -ForegroundColor Green
Write-Host "      Swagger: http://localhost:8000/docs`n" -ForegroundColor Green

Push-Location $backend
try {
    python -m uvicorn app.main:app --port 8000
} finally {
    Pop-Location
}
