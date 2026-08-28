# ManakMitra — one-time setup (Windows PowerShell)
# Usage:  .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$backend = Join-Path $PSScriptRoot "..\backend"

Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Cyan
python -m pip install -r (Join-Path $backend "requirements.txt")

$envFile = Join-Path $backend ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "`n[2/3] Creating backend\.env from .env.example..." -ForegroundColor Cyan
    Copy-Item (Join-Path $backend ".env.example") $envFile
    Write-Host "      Add your ANTHROPIC_API_KEY to backend\.env for LLM answers." -ForegroundColor Yellow
    Write-Host "      (The API also runs fine without one, in extractive mode.)" -ForegroundColor Yellow
} else {
    Write-Host "`n[2/3] backend\.env already exists — leaving it alone." -ForegroundColor Cyan
}

Write-Host "`n[3/3] Building the vector index..." -ForegroundColor Cyan
Push-Location $backend
try {
    python -m app.ingestion.build_index --rebuild
} finally {
    Pop-Location
}

Write-Host "`nSetup complete. Start the API with: .\scripts\run_dev.ps1" -ForegroundColor Green
