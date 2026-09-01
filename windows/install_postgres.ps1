<#
.SYNOPSIS
    Install PostgreSQL 16 + TimescaleDB + PostGIS on Windows Server.
    Configures a 3512 GB data tablespace on a dedicated drive.

.NOTES
    Run as Administrator in PowerShell.
    Assumes: D:\ is the OS/system drive, E:\ is the 3512 GB data drive.
    Adjust $DataDrive and $WalDrive to your actual drive letters.
    Downloads: PostgreSQL 16 installer + TimescaleDB + PostGIS packages.

.USAGE
    .\install_postgres.ps1 -DbPassword "YourStrongPassword123!"
#>

param(
    [Parameter(Mandatory)]
    [string]$DbPassword,

    [string]$DataDrive   = "E",         # 3512 GB HDD/SSD for DB data
    [string]$WalDrive    = "E",         # ideally separate fast SSD; same if only one drive
    [string]$PgVersion   = "16",
    [string]$PgPort      = "5432",
    [string]$DbName      = "rainfall_runoff",
    [string]$AppUser     = "hms_app"
)

$ErrorActionPreference = "Stop"
$PgHome    = "C:\Program Files\PostgreSQL\$PgVersion"
$PgBin     = "$PgHome\bin"
$DataDir   = "${DataDrive}:\pgdata"
$WalDir    = "${WalDrive}:\pgwal"
$TableDir  = "${DataDrive}:\pgtablespace\hydrocast"
$LogDir    = "${DataDrive}:\pglogs"
$Installer = "$env:TEMP\postgresql-16-installer.exe"
$TsdbMsi   = "$env:TEMP\timescaledb.exe"

# ── 1. Download PostgreSQL 16 ────────────────────────────────────────────────
Write-Host "`n[1/8] Downloading PostgreSQL $PgVersion..." -ForegroundColor Cyan
$PgUrl = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1258893"   # PG16 Win x64
Invoke-WebRequest -Uri $PgUrl -OutFile $Installer -UseBasicParsing

# ── 2. Install PostgreSQL (silent) ────────────────────────────────────────────
Write-Host "[2/8] Installing PostgreSQL..." -ForegroundColor Cyan
Start-Process -FilePath $Installer -ArgumentList @(
    "--unattendedmodeui", "none",
    "--mode", "unattended",
    "--superpassword", $DbPassword,
    "--serverport", $PgPort,
    "--datadir", $DataDir,
    "--prefix", $PgHome,
    "--enable-components", "server,commandlinetools"
) -Wait -NoNewWindow

# Add pg binaries to system PATH
$Env:PATH += ";$PgBin"
[System.Environment]::SetEnvironmentVariable("PATH", $Env:PATH + ";$PgBin", "Machine")

Write-Host "PostgreSQL $PgVersion installed at $PgHome" -ForegroundColor Green

# ── 3. Download + Install TimescaleDB ────────────────────────────────────────
Write-Host "[3/8] Installing TimescaleDB..." -ForegroundColor Cyan
$TsdbUrl = "https://packagecloud.io/timescale/timescaledb/packages/el/8/timescaledb-2-postgresql-16-x86_64.rpm"
# For Windows: use the official TimescaleDB Windows installer
$TsdbWinUrl = "https://timescale-assets.s3.amazonaws.com/builds/timescaledb/2.15.3/timescaledb-2.15.3-pg16-windows-amd64.zip"
$TsdbZip = "$env:TEMP\timescaledb.zip"
Invoke-WebRequest -Uri $TsdbWinUrl -OutFile $TsdbZip -UseBasicParsing
Expand-Archive -Path $TsdbZip -DestinationPath "$env:TEMP\tsdb" -Force

# Copy .dll files to PostgreSQL lib directory
Copy-Item "$env:TEMP\tsdb\lib\*" "$PgHome\lib\" -Force
Copy-Item "$env:TEMP\tsdb\share\extension\*" "$PgHome\share\extension\" -Force
Write-Host "TimescaleDB installed" -ForegroundColor Green

# ── 4. Configure postgresql.conf ─────────────────────────────────────────────
Write-Host "[4/8] Configuring postgresql.conf..." -ForegroundColor Cyan

# Detect RAM
$RAM_GB = [math]::Round((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB)
$SharedBuffers      = [math]::Round($RAM_GB * 0.25)
$EffectiveCache     = [math]::Round($RAM_GB * 0.75)
$WorkMem            = [math]::Max(64, [math]::Round($RAM_GB * 1024 / 200))  # MB, rough estimate
$MaintenanceWorkMem = [math]::Min(4096, [math]::Round($RAM_GB * 0.05 * 1024))

$PgConf = "$DataDir\postgresql.conf"
$Config = @"

# ── HydroCast Tuning (auto-generated) ─────────────────────────────────────
# Server has ${RAM_GB}GB RAM

# Memory
shared_buffers          = ${SharedBuffers}GB
effective_cache_size    = ${EffectiveCache}GB
work_mem                = ${WorkMem}MB
maintenance_work_mem    = ${MaintenanceWorkMem}MB
wal_buffers             = 64MB

# WAL
wal_level               = replica
max_wal_size            = 8GB
min_wal_size            = 2GB
checkpoint_completion_target = 0.9
wal_compression         = on

# Query planner
random_page_cost        = 1.1     # SSD; use 4.0 for HDD
effective_io_concurrency = 200    # SSD; use 2 for HDD
default_statistics_target = 200

# Connections
max_connections         = 100
superuser_reserved_connections = 5

# WAL location (separate drive if possible)
# Uncomment and set after initdb:
# data_directory          = '$DataDir'

# Logging
logging_collector       = on
log_directory           = '$LogDir'
log_filename            = 'postgresql-%Y%m%d_%H%M%S.log'
log_rotation_size       = 100MB
log_min_duration_statement = 1000   # log queries > 1s
log_line_prefix         = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# TimescaleDB
shared_preload_libraries = 'timescaledb'
timescaledb.max_background_workers = 8
timescaledb.telemetry_level = off

# Parallel
max_worker_processes    = 8
max_parallel_workers_per_gather = 4
max_parallel_workers    = 8

# Autovacuum (tune for time-series inserts)
autovacuum_vacuum_scale_factor  = 0.01
autovacuum_analyze_scale_factor = 0.005
autovacuum_max_workers          = 4
"@

Add-Content -Path $PgConf -Value $Config
Write-Host "postgresql.conf updated (RAM: ${RAM_GB}GB)" -ForegroundColor Green

# ── 5. Create directories ─────────────────────────────────────────────────────
Write-Host "[5/8] Creating directories..." -ForegroundColor Cyan
foreach ($dir in @($WalDir, $TableDir, $LogDir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
# Grant PostgreSQL service account permissions
$PgService = "NT AUTHORITY\NetworkService"   # default Windows service account
foreach ($dir in @($DataDir, $WalDir, $TableDir, $LogDir)) {
    $acl = Get-Acl $dir
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $PgService, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
    $acl.SetAccessRule($rule)
    Set-Acl $dir $acl
}
Write-Host "Directories created" -ForegroundColor Green

# ── 6. Restart PostgreSQL service ────────────────────────────────────────────
Write-Host "[6/8] Restarting PostgreSQL service..." -ForegroundColor Cyan
Restart-Service -Name "postgresql-x64-$PgVersion" -Force
Start-Sleep -Seconds 5
Write-Host "PostgreSQL service running" -ForegroundColor Green

# ── 7. Initialize database ────────────────────────────────────────────────────
Write-Host "[7/8] Creating database and extensions..." -ForegroundColor Cyan

$PsqlCmd = { param($sql) & "$PgBin\psql.exe" -U postgres -c $sql }
$env:PGPASSWORD = $DbPassword

# Create database
& "$PgBin\psql.exe" -U postgres -c "CREATE DATABASE $DbName;" 2>$null

# Create tablespace on 3512 GB drive
& "$PgBin\psql.exe" -U postgres -d $DbName -c @"
CREATE TABLESPACE hydrocast_data LOCATION '$($TableDir -replace '\\','/')';
COMMENT ON TABLESPACE hydrocast_data IS '3512GB dedicated tablespace — E:\';
"@

# Install extensions
& "$PgBin\psql.exe" -U postgres -d $DbName -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
& "$PgBin\psql.exe" -U postgres -d $DbName -c "CREATE EXTENSION IF NOT EXISTS postgis;"
& "$PgBin\psql.exe" -U postgres -d $DbName -c "CREATE EXTENSION IF NOT EXISTS pg_cron;"
& "$PgBin\psql.exe" -U postgres -d $DbName -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"

# Create application user
& "$PgBin\psql.exe" -U postgres -d $DbName -c "CREATE USER $AppUser WITH PASSWORD '$DbPassword';"
& "$PgBin\psql.exe" -U postgres -d $DbName -c "GRANT ALL ON DATABASE $DbName TO $AppUser;"

Write-Host "Database $DbName created with TimescaleDB + PostGIS" -ForegroundColor Green

# ── 8. Apply schema ────────────────────────────────────────────────────────────
Write-Host "[8/8] Applying schema..." -ForegroundColor Cyan
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SchemaFile = Join-Path $ScriptDir "..\database\schema_v3.sql"
if (Test-Path $SchemaFile) {
    & "$PgBin\psql.exe" -U postgres -d $DbName -f $SchemaFile
    Write-Host "Schema applied" -ForegroundColor Green
} else {
    Write-Host "Schema file not found at $SchemaFile — apply manually" -ForegroundColor Yellow
}

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "Connection string: postgresql://${AppUser}:PASSWORD@localhost:${PgPort}/${DbName}"
Write-Host "Tablespace: $TableDir  (~3512 GB available on ${DataDrive}:\"
Write-Host "`nNext steps:"
Write-Host "  1. Apply schema: psql -U postgres -d $DbName -f database\schema_v3.sql"
Write-Host "  2. Set DATABASE_URL in .env"
Write-Host "  3. Run: python -m src.orchestrator"
