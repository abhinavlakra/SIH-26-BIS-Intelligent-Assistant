# ManakMitra — full-stack development mode (Windows PowerShell)
#
# Starts the FastAPI backend on :8000 and the Vite dev server on :5173, both
# with hot reload. Open http://localhost:5173.
#
# For a demo, prefer .\scripts\run_demo.ps1 — one port, no second process.

$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot ".."
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $frontend
    try { npm install } finally { Pop-Location }
}

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Cyan
$api = Start-Process -PassThru -WorkingDirectory $backend `
    -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"

try {
    Write-Host "Starting frontend on http://localhost:5173 ...`n" -ForegroundColor Green
    Write-Host "  Open http://localhost:5173  (Ctrl+C to stop both)`n" -ForegroundColor Green
    Push-Location $frontend
    try { npm run dev } finally { Pop-Location }
} finally {
    if ($api -and -not $api.HasExited) {
        Write-Host "`nStopping backend..." -ForegroundColor Cyan
        Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue
    }
}
