<#
.SYNOPSIS
    HydroCast PostgreSQL Database Initialization Script
    Configured for Shivaji University Kolhapur (SUK) Windows Server Standard.

.DESCRIPTION
    Creates the rainfall_runoff database, enables PostGIS extension, applies
    core schema, inserts official Panchganga subbasins/stations/rating curves,
    and sets up approved SUK administrator credentials.

.USAGE
    .\windows\init_database.ps1 -PgUser "postgres" -PgPassword "YourPassword"
#>

param(
    [string]$PgHost = "127.0.0.1",
    [string]$PgPort = "5432",
    [string]$PgUser = "postgres",
    [string]$PgPassword = $env:PGPASSWORD,
    [string]$DbName = "rainfall_runoff",
    [string]$AppUser = "hms_app",
    [string]$AppPassword = "hms_secret_2026"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " HYDROCAST WINDOWS SERVER — DATABASE INITIALIZATION" -ForegroundColor Cyan
Write-Host " Shivaji University Kolhapur (SUK) Production Environment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Locate psql executable
$PsqlCmd = Get-Command psql -ErrorAction SilentlyContinue
if (-not $PsqlCmd) {
    $CommonPaths = @(
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files\PostgreSQL\14\bin\psql.exe"
    )
    foreach ($p in $CommonPaths) {
        if (Test-Path $p) {
            $PsqlBin = $p
            break
        }
    }
} else {
    $PsqlBin = $PsqlCmd.Source
}

if (-not $PsqlBin) {
    Write-Host "[ERROR] PostgreSQL 'psql' client not found in PATH or standard Program Files locations." -ForegroundColor Red
    Write-Host "Please install PostgreSQL 16 or add the bin directory to system PATH." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/5] Using PostgreSQL client: $PsqlBin" -ForegroundColor Green

if ($PgPassword) {
    $env:PGPASSWORD = $PgPassword
}

# 1. Create Application User & Database if not exists
Write-Host "[2/5] Creating application role ($AppUser) and database ($DbName)..." -ForegroundColor Cyan
$InitSql = @"
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$AppUser') THEN
        CREATE ROLE $AppUser WITH LOGIN PASSWORD '$AppPassword' CREATEDB;
    END IF;
END
\$\$;
SELECT 'CREATE DATABASE $DbName OWNER $AppUser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DbName')\gexec
GRANT ALL PRIVILEGES ON DATABASE $DbName TO $AppUser;
"@

& $PsqlBin -h $PgHost -p $PgPort -U $PgUser -d postgres -c $InitSql
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] DB check finished with exit code $LASTEXITCODE" -ForegroundColor Yellow
}

# 2. Apply Core Schema (run from database dir so \ir paths resolve consistently)
$DbDir = Join-Path $PSScriptRoot "..\database"
Write-Host "[3/5] Applying core schema (database/schema.sql)..." -ForegroundColor Cyan
Push-Location $DbDir
try {
    & $PsqlBin -h $PgHost -p $PgPort -U $PgUser -d $DbName -f "schema.sql"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed applying schema.sql" -ForegroundColor Red
        exit 1
    }

    # 3. Apply Seeds
    Write-Host "[4/5] Applying catchment seeds (database/seeds.sql)..." -ForegroundColor Cyan
    & $PsqlBin -h $PgHost -p $PgPort -U $PgUser -d $DbName -f "seeds.sql"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed applying seeds.sql" -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

# 4. Apply Admin RBAC schema and upgrades
Write-Host "[5/6] Applying administrator auth schema (database/auth)..." -ForegroundColor Cyan
$AuthDir = Join-Path $PSScriptRoot "..\database\auth"
foreach ($file in @("01_admin_users.sql", "02_admin_users_upgrade.sql")) {
    $path = Join-Path $AuthDir $file
    if (Test-Path $path) {
        & $PsqlBin -h $PgHost -p $PgPort -U $PgUser -d $DbName -f $path
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed applying $file" -ForegroundColor Red
            exit 1
        }
    }
}

# 5. Optional bootstrap seed (template by default; contains no real credentials)
$BootstrapFile = Join-Path $AuthDir "03_seed_adm1_users.sql"
if (Test-Path $BootstrapFile) {
    Write-Host "[6/6] Applying bootstrap admin template (database/auth/03_seed_adm1_users.sql)..." -ForegroundColor Cyan
    & $PsqlBin -h $PgHost -p $PgPort -U $PgUser -d $DbName -f $BootstrapFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed applying 03_seed_adm1_users.sql" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[NEXT STEP] Create the first real administrator account (no credentials are committed to git):" -ForegroundColor Yellow
Write-Host "  python -m backend.scripts.manage_users add --username <admin> --password <password> --role admin --email <email> --name \"<Full Name>\"" -ForegroundColor Yellow

Write-Host "`n[SUCCESS] PostgreSQL Database initialized and ready for production." -ForegroundColor Green
Write-Host "App Connection URI: postgresql://${AppUser}:${AppPassword}@${PgHost}:${PgPort}/${DbName}" -ForegroundColor Green

