<#
.SYNOPSIS
    HydroCast Manual Pipeline Execution CLI
    Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Launches a standalone 12-step hydrological forecast cycle on the server
    with real-time colored progress logging.

.USAGE
    .\windows\run_pipeline_manual.ps1
    .\windows\run_pipeline_manual.ps1 -Date "20260929" -Hour 6
    .\windows\run_pipeline_manual.ps1 -SingleStep 7  # Retry step 7 only
#>

param(
    [string]$Date = "",
    [int]$Hour = -1,
    [string]$CycleId = "",
    [int]$SingleStep = 0
)

$ErrorActionPreference = "Stop"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " HYDROCAST PANCHGANGA -- MANUAL FORECAST CYCLE RUNNER" -ForegroundColor Cyan
Write-Host " Shivaji University Kolhapur (SUK) Windows Server Standard" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$PyCmd = "from backend.service.pipeline_worker import execute_cycle; "
if ($SingleStep -gt 0) {
    Write-Host "Mode: SINGLE STEP RETRY (Step $SingleStep)" -ForegroundColor Yellow
    $PyCmd += "res = execute_cycle(single_step=$SingleStep); print(res)"
} else {
    Write-Host "Mode: FULL 12-STEP FORECAST CYCLE" -ForegroundColor Green
    $PyCmd += "res = execute_cycle(); print(res)"
}

python -c $PyCmd

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Forecast cycle completed." -ForegroundColor Green
} else {
    Write-Host "`n[FAILED] Forecast cycle terminated with error." -ForegroundColor Red
}

