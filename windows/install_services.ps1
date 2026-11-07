<#
.SYNOPSIS
    HydroCast Windows Server Service Installer (NSSM)
    Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Installs and configures HydroCast services as native Windows Services:
      1. HydroCast-Backend (FastAPI Uvicorn on :8000)
      2. HydroCast-Scheduler (Autonomous 24/7 Hydrological Scheduler)
      3. HydroCast-Watchdog (Supervisory Process Watchdog)
      4. HydroCast-PublicWeb (Next.js Public Portal on :3000)
      5. HydroCast-OperatorConsole (Next.js Operator Mission Control on :3001)

.USAGE
    Run as Administrator in PowerShell:
    .\windows\install_services.ps1
#>

param(
    [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [string]$NssmBin = "nssm.exe"
)

# Require Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

$ErrorActionPreference = "Stop"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " HYDROCAST WINDOWS SERVER -- SERVICE INSTALLATION (NSSM)" -ForegroundColor Cyan
Write-Host " Shivaji University Kolhapur (SUK) Production Environment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Locate or download NSSM if missing
$NssmCmd = Get-Command $NssmBin -ErrorAction SilentlyContinue
if (-not $NssmCmd) {
    $TempNssm = Join-Path $env:TEMP "nssm.exe"
    if (-not (Test-Path $TempNssm)) {
        Write-Host "Downloading NSSM service manager..." -ForegroundColor Cyan
        $ZipUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $ZipFile = Join-Path $env:TEMP "nssm.zip"
        Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile -UseBasicParsing
        Expand-Archive -Path $ZipFile -DestinationPath "$env:TEMP\nssm_unzipped" -Force
        Copy-Item "$env:TEMP\nssm_unzipped\nssm-2.24\win64\nssm.exe" $TempNssm -Force
    }
    $NssmPath = $TempNssm
} else {
    $NssmPath = $NssmCmd.Source
}

$PythonExe = (Get-Command python).Source
$NodeExe   = (Get-Command node -ErrorAction SilentlyContinue)
if ($NodeExe) { $NodeExe = $NodeExe.Source }

Write-Host "Using NSSM:   $NssmPath" -ForegroundColor Green
Write-Host "Using Python: $PythonExe" -ForegroundColor Green
Write-Host "Using Node:   $NodeExe" -ForegroundColor Green
Write-Host "Working Dir:  $WorkingDir" -ForegroundColor Green

function Register-NssmService {
    param(
        [string]$ServiceName,
        [string]$AppPath,
        [string]$AppArgs,
        [string]$DisplayName,
        [string]$Description
    )
    Write-Host "`nConfiguring Windows Service: $ServiceName..." -ForegroundColor Cyan
    
    # Stop and remove existing if present
    & $NssmPath stop $ServiceName 2>$null | Out-Null
    & $NssmPath remove $ServiceName confirm 2>$null | Out-Null

    # Install service
    & $NssmPath install $ServiceName $AppPath $AppArgs
    & $NssmPath set $ServiceName AppDirectory $WorkingDir
    & $NssmPath set $ServiceName DisplayName $DisplayName
    & $NssmPath set $ServiceName Description $Description
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START

    # Recovery actions: Restart service automatically on failure
    & $NssmPath set $ServiceName AppRestartDelay 5000
    & $NssmPath set $ServiceName AppThrottle 1500
    & $NssmPath set $ServiceName AppStdout (Join-Path $WorkingDir "data\logs\service_${ServiceName}.log")
    & $NssmPath set $ServiceName AppStderr (Join-Path $WorkingDir "data\logs\service_${ServiceName}_err.log")

    Write-Host "Service $ServiceName registered with Auto-Restart." -ForegroundColor Green
}

# 1. HydroCast Backend API
Register-NssmService `
    -ServiceName "HydroCast-Backend" `
    -AppPath $PythonExe `
    -AppArgs "-m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000" `
    -DisplayName "HydroCast Backend Operational API" `
    -Description "FastAPI REST and WebSocket hub for HydroCast Panchganga on SUK Server."

# 2. HydroCast 24/7 Scheduler
Register-NssmService `
    -ServiceName "HydroCast-Scheduler" `
    -AppPath $PythonExe `
    -AppArgs "-m backend.service.scheduler_daemon" `
    -DisplayName "HydroCast Hydrological Cycle Scheduler" `
    -Description "Autonomous 4x daily forecast cycles and hourly telemetry verification."

# 3. HydroCast Supervisory Watchdog
Register-NssmService `
    -ServiceName "HydroCast-Watchdog" `
    -AppPath $PythonExe `
    -AppArgs "-m backend.service.watchdog" `
    -DisplayName "HydroCast System Watchdog & Supervisor" `
    -Description "Process watchdog and hardware telemetry monitor for HydroCast."

# 4. Next.js Public Portal (:3000)
if ($NodeExe) {
    Register-NssmService `
        -ServiceName "HydroCast-PublicWeb" `
        -AppPath $NodeExe `
        -AppArgs "frontend-public/node_modules/next/dist/bin/next start frontend-public -p 3000" `
        -DisplayName "HydroCast Public Visitor Portal" `
        -Description "Lightweight public disaster intelligence portal (Dashboard, Rain, Runoff)."
}

# 5. Next.js Operator Console (:3001)
if ($NodeExe) {
    Register-NssmService `
        -ServiceName "HydroCast-OperatorConsole" `
        -AppPath $NodeExe `
        -AppArgs "frontend-admin/node_modules/next/dist/bin/next start frontend-admin -p 3001" `
        -DisplayName "HydroCast Operator Mission Control" `
        -Description "Dedicated administrative control room with direct, passwordless access for Shivaji University operators."
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " ALL HYDROCAST SERVICES REGISTERED SUCCESSFULLY" -ForegroundColor Green
Write-Host " Use '.\windows\service_control.ps1 -Action start' to launch." -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan

