<#
.DESCRIPTION
Starts the Celery worker for local development on native Windows.

The default prefork pool is not supported on native Windows, so this
script pins --pool=solo. On Linux/WSL/production use run_worker.sh
(defaults to the prefork pool).

Prereqs: Redis running on localhost:6379 (see README "Running the async
worker").

Usage:
    .\scripts\run_worker.ps1
    .\scripts\run_worker.ps1 --loglevel=debug
#>
[CmdletBinding()]
param(
    [string]$Loglevel = "info"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"

$CandidatePythons = @(
    (Join-Path $Backend "venv\Scripts\python.exe"),  # backend/venv
    (Join-Path $Root   ".venv\Scripts\python.exe"),  # .venv (repo root)
    "python"
)
$Python = $CandidatePythons | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Python) {
    Write-Error "No Python interpreter found. Installed backend/venv, .venv, or set PATH."
    exit 1
}

Push-Location $Backend
try {
    Write-Host "Starting Celery worker (pool=solo) ... press Ctrl+C to stop."
    & $Python -m celery -A core.celery worker --pool=solo -l $Loglevel
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}