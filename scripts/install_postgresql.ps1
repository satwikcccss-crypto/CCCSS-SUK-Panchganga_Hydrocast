# =============================================================================
# HydroCast Panchganga - PostgreSQL 16 Installation & Setup Script
# Target: Windows Server Standard @ SUK
# Run this script in an ELEVATED PowerShell (Run as Administrator)
# =============================================================================

# ── 1. Download PostgreSQL 16 installer (if not already downloaded) ──────────
$installerPath = "E:\postgresql-16.15-5-windows-x64.exe"
$installerUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.15-5-windows-x64.exe"

if (-not (Test-Path $installerPath)) {
    Write-Host "Downloading PostgreSQL 16 installer..."
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
}

# ── 2. Install PostgreSQL 16 (silent, unattended) ────────────────────────────
Write-Host "Installing PostgreSQL 16..."
& $installerPath `
    --mode unattended `
    --prefix "C:\Program Files\PostgreSQL\16" `
    --serverport 5432 `
    --superpassword postgres `
    --servicename postgresql-16 `
    --lang en

# ── 3. Verify installation ───────────────────────────────────────────────────
$pgBin = "C:\Program Files\PostgreSQL\16\bin"
if (-not (Test-Path "$pgBin\pg_ctl.exe")) {
    Write-Error "PostgreSQL installation failed - pg_ctl.exe not found at $pgBin"
    exit 1
}
Write-Host "PostgreSQL 16 installed successfully."

# ── 4. Add PostgreSQL bin to PATH (current session) ──────────────────────────
$env:PATH = "$pgBin;$env:PATH"

# ── 5. Verify service is running ─────────────────────────────────────────────
Start-Sleep -Seconds 5
$service = Get-Service -Name "postgresql-16" -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "Service status: $($service.Status)"
    if ($service.Status -ne 'Running') {
        Start-Service -Name "postgresql-16"
    }
}

# ── 6. Create database and user ──────────────────────────────────────────────
Write-Host "Creating database and user..."
& "$pgBin\psql.exe" -U postgres -c "CREATE USER hms_app WITH PASSWORD 'hms_secret_2026';" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "User hms_app may already exist (continuing...)" }

& "$pgBin\psql.exe" -U postgres -c "CREATE DATABASE rainfall_runoff OWNER hms_app;" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Database rainfall_runoff may already exist (continuing...)" }

# ── 7. Create tablespace directory on E:\ drive ──────────────────────────────
$tablespaceDir = "E:\pg_tablespace\hydrocast_ts"
if (-not (Test-Path $tablespaceDir)) {
    New-Item -ItemType Directory -Path $tablespaceDir -Force | Out-Null
    Write-Host "Created tablespace directory: $tablespaceDir"
}

# ── 8. Load schema and seeds ─────────────────────────────────────────────────
Write-Host "Loading schema and seed data..."
$projectRoot = "E:\Hydrocast Windows Server"
$setupSql = "$projectRoot\database\setup_postgresql.sql"

& "$pgBin\psql.exe" -U hms_app -d rainfall_runoff -h 127.0.0.1 -p 5432 -f "$setupSql"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== PostgreSQL setup complete! ==="  -ForegroundColor Green
    Write-Host "Database: rainfall_runoff"
    Write-Host "User: hms_app"
    Write-Host "Host: 127.0.0.1:5432"
    Write-Host ""
    Write-Host "Next: Update .env DATABASE_URL and restart the backend:"
    Write-Host "  DATABASE_URL=postgresql://hms_app:hms_secret_2026@127.0.0.1:5432/rainfall_runoff"
} else {
    Write-Error "Schema loading failed. Check errors above."
}

# =============================================================================
# END OF SCRIPT
# =============================================================================
