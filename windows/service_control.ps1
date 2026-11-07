<#
.SYNOPSIS
    HydroCast Windows Service Management Controller
    Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Provides unified start, stop, restart, and status monitoring
    for all HydroCast Windows services.

.USAGE
    .\windows\service_control.ps1 -Action status
    .\windows\service_control.ps1 -Action start
    .\windows\service_control.ps1 -Action stop
    .\windows\service_control.ps1 -Action restart
#>

param(
    [ValidateSet("status", "start", "stop", "restart")]
    [string]$Action = "status"
)

$Services = @(
    "HydroCast-Backend",
    "HydroCast-Scheduler",
    "HydroCast-Watchdog",
    "HydroCast-PublicWeb",
    "HydroCast-OperatorConsole"
)

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " HYDROCAST WINDOWS SERVICE CONTROLLER -- $Action.ToUpper()" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

foreach ($svcName in $Services) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host " [NOT INSTALLED] $svcName" -ForegroundColor DarkGray
        continue
    }

    switch ($Action) {
        "start" {
            if ($svc.Status -ne "Running") {
                Write-Host " Starting $svcName..." -ForegroundColor Cyan
                Start-Service -Name $svcName -ErrorAction Continue
                $svc.Refresh()
            }
            Write-Host " [RUNNING] $svcName" -ForegroundColor Green
        }
        "stop" {
            if ($svc.Status -eq "Running") {
                Write-Host " Stopping $svcName..." -ForegroundColor Yellow
                Stop-Service -Name $svcName -Force -ErrorAction Continue
                $svc.Refresh()
            }
            Write-Host " [STOPPED] $svcName" -ForegroundColor DarkGray
        }
        "restart" {
            Write-Host " Restarting $svcName..." -ForegroundColor Cyan
            Restart-Service -Name $svcName -Force -ErrorAction Continue
            $svc.Refresh()
            Write-Host " [RUNNING] $svcName" -ForegroundColor Green
        }
        "status" {
            if ($svc.Status -eq "Running") {
                Write-Host " [RUNNING] $svcName ($($svc.DisplayName))" -ForegroundColor Green
            } else {
                Write-Host " [STOPPED] $svcName ($($svc.DisplayName))" -ForegroundColor Red
            }
        }
    }
}

Write-Host "============================================================`n" -ForegroundColor Cyan

