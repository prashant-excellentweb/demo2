<#
.SYNOPSIS
    Starts the FastAPI backend and the Vite dev server together.

.DESCRIPTION
    Vite serves the UI on :5173 and proxies /api to FastAPI on :8000, so both
    sides hot-reload. Ctrl+C stops both.

.EXAMPLE
    .\scripts\dev.ps1
    .\scripts\dev.ps1 -ApiPort 8001
#>
param(
    [int]$ApiPort = 8000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# This project has been developed with both ".venv" and "venv" in place, so
# accept either rather than failing on the one that happens to be missing.
$python = @(".venv", "venv") |
    ForEach-Object { Join-Path $root "$_\Scripts\python.exe" } |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $python) {
    Write-Error "No virtualenv found. Run: python -m venv .venv; .venv\Scripts\python -m pip install -r requirements-dev.txt"
}

$pypdf = & $python -c "import importlib.util; print(importlib.util.find_spec('pypdf') is not None)"
if ($pypdf.Trim() -ne "True") {
    Write-Warning "$python is missing dependencies (pypdf). Run: $python -m pip install -r requirements-dev.txt"
}
if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Warning "No .env found. Copy .env.example to .env and set SECRET_KEY plus a provider key."
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Error "Frontend dependencies missing. Run: cd frontend; npm install"
}

$api = Start-Process -PassThru -NoNewWindow -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", $ApiPort

Write-Host ""
Write-Host "  API  -> http://127.0.0.1:$ApiPort (docs at /docs)" -ForegroundColor Cyan
Write-Host "  UI   -> http://localhost:5173" -ForegroundColor Cyan
Write-Host ""

try {
    # Vite runs in the foreground so its output stays attached to this terminal.
    Set-Location (Join-Path $root "frontend")
    npm run dev
}
finally {
    if ($api -and -not $api.HasExited) {
        Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Backend stopped." -ForegroundColor DarkGray
    }
}
