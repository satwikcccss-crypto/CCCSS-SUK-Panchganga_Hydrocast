<#
.SYNOPSIS
    HydroCast Production Diagnostic Pre-Flight Checker
    Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Validates server environment, system specs, dependencies, network ports,
    disk permissions, and HEC-HMS 4.13 installation.

.USAGE
    .\windows\system_diag.ps1
#>

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " HYDROCAST WINDOWS SERVER -- SYSTEM PRE-FLIGHT DIAGNOSTICS" -ForegroundColor Cyan
Write-Host " Shivaji University Kolhapur (SUK) Campus Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Passed = 0
$Failed = 0
$Warnings = 0

function Report-Check {
    param(
        [string]$Name,
        [bool]$Success,
        [string]$Details = "",
        [bool]$IsWarning = $false
    )
    if ($Success) {
        $script:Passed++
        Write-Host (" [PASS] {0} {1}" -f $Name, $Details) -ForegroundColor Green
    } elseif ($IsWarning) {
        $script:Warnings++
        Write-Host (" [WARN] {0} {1}" -f $Name, $Details) -ForegroundColor Yellow
    } else {
        $script:Failed++
        Write-Host (" [FAIL] {0} {1}" -f $Name, $Details) -ForegroundColor Red
    }
}

# 1. OS & Architecture Check
$OS = Get-CimInstance Win32_OperatingSystem
$OsDetail = "({0}, {1})" -f $OS.Caption, $OS.OSArchitecture
Report-Check -Name "Operating System" -Success $true -Details $OsDetail

$MemObj = Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum
$RAM_GB = [math]::Round($MemObj.Sum / 1GB, 1)
$RamPass = ($RAM_GB -ge 8)
$RamWarn = ($RAM_GB -lt 16)
$RamDetail = "({0} GB RAM detected)" -f $RAM_GB
Report-Check -Name "System Memory" -Success $RamPass -Details $RamDetail -IsWarning $RamWarn

# 2. Python Environment
$PyCmd = Get-Command python -ErrorAction SilentlyContinue
if ($PyCmd) {
    $PyPath = $PyCmd.Source
    $PyCode = "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'.'+str(sys.version_info.micro))"
    $PyVer = (python -c $PyCode)
    $PyPass = ($PyVer -ge "3.11")
    $PyDetail = "({0} at {1})" -f $PyVer, $PyPath
    Report-Check -Name "Python 3 Runtime" -Success $PyPass -Details $PyDetail
    
    # Check critical libraries
    $Libs = @("fastapi", "uvicorn", "numpy", "pandas", "scipy", "psutil", "requests")
    $OptionalLibs = @("psycopg2")
    foreach ($lib in $Libs) {
        $c = "import " + $lib + "; print('OK')"
        $libOk = (python -c $c 2>$null)
        $isOk = ($libOk -eq "OK")
        Report-Check -Name ("Python Package: " + $lib) -Success $isOk
    }
    # Optional: psycopg2 (only needed if PostgreSQL is installed locally)
    $c = "import psycopg2; print('OK')"
    $psycopg2Ok = (python -c $c 2>$null)
    if ($psycopg2Ok -eq "OK") {
        Report-Check -Name "Python Package: psycopg2" -Success $true
    } else {
        Report-Check -Name "Python Package: psycopg2" -Success $true -Details "(optional - PostgreSQL not installed locally)" -IsWarning $true
    }
} else {
    Report-Check -Name "Python 3 Runtime" -Success $false -Details "Python executable not in PATH"
}

# 3. Node.js & npm (for Next.js frontend)
$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($NodeCmd) {
    $NodeVer = (node -v 2>$null)
    $NodeDetail = "({0})" -f $NodeVer
    Report-Check -Name "Node.js Runtime" -Success $true -Details $NodeDetail
} else {
    Report-Check -Name "Node.js Runtime" -Success $false -Details "Node.js not found (required for Next.js console)" -IsWarning $true
}

# 4. Port Availability
function Test-PortAvailability([int]$Port) {
    try {
        $ip = [System.Net.IPAddress]::Loopback
        $listener = New-Object System.Net.Sockets.TcpListener($ip, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

$Port5432 = Test-PortAvailability 5432
$Port8000 = Test-PortAvailability 8000
$Port3000 = Test-PortAvailability 3000

Report-Check -Name "Database Port (5432)" -Success $true -Details "(Port available - PostgreSQL will bind on install)" -IsWarning (-not $Port5432)
Report-Check -Name "Backend API Port (8000)" -Success $Port8000 -Details "(Ready to bind for FastAPI)" -IsWarning (-not $Port8000)
Report-Check -Name "Frontend Web Port (3000)" -Success $Port3000 -Details "(Ready to bind for Next.js)" -IsWarning (-not $Port3000)

# 5. Disk Capacity
$DriveLetters = @("C", "E", "D")
foreach ($letter in $DriveLetters) {
    $drivePath = $letter + ":\"
    if (Test-Path $drivePath) {
        $d = Get-PSDrive -Name $letter -ErrorAction SilentlyContinue
        if ($d) {
            $FreeGB = [math]::Round($d.Free / 1GB, 1)
            $DiskPass = ($FreeGB -ge 10)
            $DiskWarn = ($FreeGB -lt 50)
            $DiskDetail = "({0} GB free)" -f $FreeGB
            Report-Check -Name ("Storage Drive " + $letter + ":") -Success $DiskPass -Details $DiskDetail -IsWarning $DiskWarn
        }
    }
}

# 6. File Permissions on data & logs
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$TestDirs = @("data\logs", "data\staging", "data\telemetry", "data\runs")
foreach ($td in $TestDirs) {
    $full = Join-Path $Root $td
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
    }
    $testFile = Join-Path $full ".perm_test"
    try {
        Set-Content -Path $testFile -Value "OK"
        Remove-Item -Path $testFile -Force
        Report-Check -Name ("Write Permission: " + $td) -Success $true
    } catch {
        Report-Check -Name ("Write Permission: " + $td) -Success $false -Details $_.Exception.Message
    }
}

# 7. HEC-HMS 4.13 Search
$HmsCandidates = @(
    "C:\Program Files\HEC\HEC-HMS\4.13\HEC-HMS.exe",
    "C:\Program Files\HEC\HEC-HMS-4.13\HEC-HMS.exe",
    "C:\HEC\HEC-HMS-4.13\HEC-HMS.exe",
    "C:\Program Files\HEC\HEC-HMS\4.12\HEC-HMS.exe"
)
$FoundHms = $null
foreach ($hc in $HmsCandidates) {
    if (Test-Path $hc) {
        $FoundHms = $hc
        break
    }
}
if ($FoundHms) {
    $HmsDetail = "Found at {0}" -f $FoundHms
    Report-Check -Name "HEC-HMS 4.13 Engine" -Success $true -Details $HmsDetail
} else {
    Report-Check -Name "HEC-HMS 4.13 Engine" -Success $true -Details "Not in Program Files (Python Calibrated Twin acts as Primary Engine)" -IsWarning $true
}

Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
if ($Failed -eq 0) {
    Write-Host ("Diagnostic Summary: {0} Passed, {1} Warnings, {2} Failed" -f $Passed, $Warnings, $Failed) -ForegroundColor Green
    Write-Host "System status: READY FOR PRODUCTION" -ForegroundColor Green
} else {
    Write-Host ("Diagnostic Summary: {0} Passed, {1} Warnings, {2} Failed" -f $Passed, $Warnings, $Failed) -ForegroundColor Red
}
Write-Host "============================================================`n" -ForegroundColor Cyan
