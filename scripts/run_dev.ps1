# ManakMitra — start the development API (Windows PowerShell)
# Usage:  .\scripts\run_dev.ps1

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend"

Push-Location $backend
try {
    Write-Host "API docs will be at http://localhost:8000/docs`n" -ForegroundColor Green
    python -m uvicorn app.main:app --reload --port 8000
} finally {
    Pop-Location
}
