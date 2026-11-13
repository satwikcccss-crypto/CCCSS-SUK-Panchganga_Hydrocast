<#
.SYNOPSIS
    HydroCast Automated PostgreSQL Backup Script
    Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Creates a compressed custom-format pg_dump of the rainfall_runoff database,
    calculates SHA-256 checksum, and rotates backups older than the retention period.

.USAGE
    .\windows\backup_database.ps1 -BackupDrive "E" -RetentionDays 30
#>

param(
    [string]$BackupDrive = "E",
    [int]$RetentionDays = 30,
    [string]$DbName = "rainfall_runoff",
    [string]$PgUser = "postgres",
    [string]$PgHost = "127.0.0.1",
    [string]$PgPort = "5432"
)

$ErrorActionPreference = "Stop"

$DateStr = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "${BackupDrive}:\pgbackups\hydrocast"
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$DumpFile = Join-Path $BackupDir "hydrocast_${DbName}_${DateStr}.dump"
$LogFile  = Join-Path $BackupDir "backup_audit.log"

Write-Host "[BACKUP] Starting backup for $DbName to $DumpFile..." -ForegroundColor Cyan

# Locate pg_dump
$PgDumpCmd = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $PgDumpCmd) {
    $CommonPaths = @(
        "E:\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        "C:\Program Files\PostgreSQL\14\bin\pg_dump.exe"
    )
    foreach ($p in $CommonPaths) {
        if (Test-Path $p) {
            $PgDumpBin = $p
            break
        }
    }
} else {
    $PgDumpBin = $PgDumpCmd.Source
}

if (-not $PgDumpBin) {
    Write-Host "[ERROR] pg_dump utility not found." -ForegroundColor Red
    exit 1
}

# Use PGPASSWORD from environment for non-interactive scheduled backups when provided.
# Prefer .pgpass/managed service credentials in production where possible.
if (-not $env:PGPASSWORD -and $env:POSTGRES_PASSWORD) {
    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
}

$t0 = Get-Date
& $PgDumpBin -h $PgHost -p $PgPort -U $PgUser -F c -b -v -f $DumpFile $DbName
$elapsed = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)

# Best-effort: keep process env clean if we populated it from POSTGRES_PASSWORD.
if ($env:POSTGRES_PASSWORD -and $env:PGPASSWORD -eq $env:POSTGRES_PASSWORD) {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

if ($LASTEXITCODE -eq 0 -and (Test-Path $DumpFile)) {
    $SizeMB = [math]::Round((Get-Item $DumpFile).Length / 1MB, 2)
    $Hash = (Get-FileHash -Path $DumpFile -Algorithm SHA256).Hash
    
    $AuditMsg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')] OK: Created $DumpFile (${SizeMB}MB in ${elapsed}s) SHA256: $Hash"
    Add-Content -Path $LogFile -Value $AuditMsg
    Write-Host "[SUCCESS] $AuditMsg" -ForegroundColor Green
    Write-Host "[DRILL] Verify restore on a staging/test database periodically: pg_restore --list `"$DumpFile`"" -ForegroundColor DarkCyan
} else {
    $AuditMsg = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC')] FAILED: Backup failed with exit code $LASTEXITCODE"
    Add-Content -Path $LogFile -Value $AuditMsg
    Write-Host "[ERROR] $AuditMsg" -ForegroundColor Red
    exit 1
}

# Retention cleanup
Write-Host "[RETENTION] Purging backups older than $RetentionDays days..." -ForegroundColor Cyan
$Cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "hydrocast_*.dump" | Where-Object { $_.LastWriteTime -lt $Cutoff } | ForEach-Object {
    Write-Host "Removing expired backup: $($_.Name)" -ForegroundColor Yellow
    Remove-Item $_.FullName -Force
}

