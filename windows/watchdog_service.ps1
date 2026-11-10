<#
.SYNOPSIS
    HydroCast Autonomous Windows Watchdog & Self-Healing Service
    Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Continuously monitors all four critical HydroCast server ports:
      - 5432: PostgreSQL Database
      - 8000: FastAPI Operational Backend Hub
      - 3000: Next.js Public Flood Intelligence Portal
      - 3001: Next.js Operator Mission Control Console

    Every 30 seconds, the watchdog tests TCP connectivity to each port.
    If any service is unresponsive or crashed, it triggers an immediate
    self-healing restart and records an entry in the watchdog log.

.USAGE
    # Continuous background monitoring (default 30s interval):
    powershell -ExecutionPolicy Bypass -File .\windows\watchdog_service.ps1

    # Single-pass health check (for scheduled tasks or test runners):
    powershell -ExecutionPolicy Bypass -File .\windows\watchdog_service.ps1 -Once
#>

param(
    [int]$IntervalSeconds = 30,
    [switch]$Once,
    [string]$WorkingDir = (Resolve-Path (Join-Path $PSScriptRoot ".."))
)

$LogDir = Join-Path $WorkingDir "data\logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}
$LogFile = Join-Path $LogDir "watchdog_service.log"

function Write-WatchdogLog {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $LogLine = "[$Timestamp] [$Level] $Message"
    Write-Host $LogLine -ForegroundColor $(if ($Level -eq "ERROR") { "Red" } elseif ($Level -eq "WARN") { "Yellow" } elseif ($Level -eq "SUCCESS") { "Green" } else { "Cyan" })
    Add-Content -Path $LogFile -Value $LogLine -ErrorAction SilentlyContinue
}

function Test-TcpPort {
    param(
        [string]$ComputerName = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutMs = 1500
    )
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connect = $tcpClient.BeginConnect($ComputerName, $Port, $null, $null)
        $success = $connect.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
        if ($success -and $tcpClient.Connected) {
            $tcpClient.EndConnect($connect)
            $tcpClient.Close()
            return $true
        } else {
            $tcpClient.Close()
            return $false
        }
    } catch {
        return $false
    }
}

function Restart-PostgresService {
    Write-WatchdogLog "Initiating self-healing for PostgreSQL on Port 5432..." "WARN"
    $pgSvc = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pgSvc) {
        try {
            Restart-Service -Name $pgSvc.Name -Force -ErrorAction Stop
            Write-WatchdogLog "Restarted Windows service '$($pgSvc.Name)'." "SUCCESS"
            return
        } catch {
            Write-WatchdogLog "Failed to restart Windows service '$($pgSvc.Name)': $_" "ERROR"
        }
    }
    
    # Fallback to pg_ctl if installed in standard location
    $pgCtl = "E:\PostgreSQL\16\bin\pg_ctl.exe"
    $pgData = "E:\PostgreSQL\16\data"
    if (Test-Path $pgCtl) {
        Write-WatchdogLog "Invoking pg_ctl directly: $pgCtl" "INFO"
        Start-Process -FilePath $pgCtl -ArgumentList "restart -D `"$pgData`" -w" -NoNewWindow
    }
}

function Restart-BackendService {
    Write-WatchdogLog "Initiating self-healing for FastAPI Backend on Port 8000..." "WARN"
    $svc = Get-Service -Name "HydroCast-Backend" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        Restart-Service -Name "HydroCast-Backend" -Force -ErrorAction SilentlyContinue
        Write-WatchdogLog "Restarted HydroCast-Backend service." "SUCCESS"
        return
    } elseif ($svc) {
        Start-Service -Name "HydroCast-Backend" -ErrorAction SilentlyContinue
        Write-WatchdogLog "Started HydroCast-Backend service." "SUCCESS"
        return
    }

    # Fallback: start via Python directly
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { $py = "python" }
    Write-WatchdogLog "Launching Python Uvicorn backend process directly..." "INFO"
    Start-Process -FilePath $py -ArgumentList "-m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $WorkingDir -WindowStyle Hidden
}

function Restart-PublicWebService {
    Write-WatchdogLog "Initiating self-healing for Public Web Portal on Port 3000..." "WARN"
    $svc = Get-Service -Name "HydroCast-PublicWeb" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        Restart-Service -Name "HydroCast-PublicWeb" -Force -ErrorAction SilentlyContinue
        Write-WatchdogLog "Restarted HydroCast-PublicWeb service." "SUCCESS"
        return
    } elseif ($svc) {
        Start-Service -Name "HydroCast-PublicWeb" -ErrorAction SilentlyContinue
        Write-WatchdogLog "Started HydroCast-PublicWeb service." "SUCCESS"
        return
    }

    # Fallback: launch npm/node directly
    $pubDir = Join-Path $WorkingDir "frontend-public"
    Write-WatchdogLog "Launching frontend-public Next.js server on Port 3000..." "INFO"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run start -- -p 3000" -WorkingDirectory $pubDir -WindowStyle Hidden
}

function Restart-AdminWebService {
    Write-WatchdogLog "Initiating self-healing for Admin Mission Control on Port 3001..." "WARN"
    $svc = Get-Service -Name "HydroCast-OperatorConsole" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") {
        Restart-Service -Name "HydroCast-OperatorConsole" -Force -ErrorAction SilentlyContinue
        Write-WatchdogLog "Restarted HydroCast-OperatorConsole service." "SUCCESS"
        return
    } elseif ($svc) {
        Start-Service -Name "HydroCast-OperatorConsole" -ErrorAction SilentlyContinue
        Write-WatchdogLog "Started HydroCast-OperatorConsole service." "SUCCESS"
        return
    }

    # Fallback: launch npm/node directly
    $admDir = Join-Path $WorkingDir "frontend-admin"
    Write-WatchdogLog "Launching frontend-admin Next.js server on Port 3001..." "INFO"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run start -- -p 3001" -WorkingDirectory $admDir -WindowStyle Hidden
}

function Invoke-HealthCheck {
    $AllHealthy = $true

    # 1. Port 5432 (PostgreSQL)
    if (Test-TcpPort -Port 5432) {
        Write-WatchdogLog "Port 5432 (PostgreSQL): ONLINE" "INFO"
    } else {
        Write-WatchdogLog "Port 5432 (PostgreSQL): UNREACHABLE!" "ERROR"
        Restart-PostgresService
        $AllHealthy = $false
    }

    # 2. Port 8000 (FastAPI Backend)
    if (Test-TcpPort -Port 8000) {
        Write-WatchdogLog "Port 8000 (FastAPI Hub): ONLINE" "INFO"
    } else {
        Write-WatchdogLog "Port 8000 (FastAPI Hub): UNREACHABLE!" "ERROR"
        Restart-BackendService
        $AllHealthy = $false
    }

    # 3. Port 3000 (Public Portal)
    if (Test-TcpPort -Port 3000) {
        Write-WatchdogLog "Port 3000 (Public Portal): ONLINE" "INFO"
    } else {
        Write-WatchdogLog "Port 3000 (Public Portal): UNREACHABLE!" "ERROR"
        Restart-PublicWebService
        $AllHealthy = $false
    }

    # 4. Port 3001 (Admin Console)
    if (Test-TcpPort -Port 3001) {
        Write-WatchdogLog "Port 3001 (Admin Console): ONLINE" "INFO"
    } else {
        Write-WatchdogLog "Port 3001 (Admin Console): UNREACHABLE!" "ERROR"
        Restart-AdminWebService
        $AllHealthy = $false
    }

    return $AllHealthy
}

Write-WatchdogLog "Starting HydroCast Autonomous Watchdog Service [Interval: ${IntervalSeconds}s, Once: $Once]..." "INFO"

if ($Once) {
    $res = Invoke-HealthCheck
    Write-WatchdogLog "Single-pass health check finished. All healthy: $res" $(if ($res) { "SUCCESS" } else { "WARN" })
    exit $(if ($res) { 0 } else { 1 })
}

# Continuous 30s Loop
try {
    while ($true) {
        Invoke-HealthCheck | Out-Null
        Start-Sleep -Seconds $IntervalSeconds
    }
} catch {
    Write-WatchdogLog "Watchdog encountered an unhandled exception: $_" "ERROR"
    exit 1
}
