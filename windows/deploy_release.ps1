<#
.SYNOPSIS
    One-command production deployment for HydroCast on Windows Server.

.DESCRIPTION
    Deploys the commit that is checked out in this directory, then rebuilds every
    artefact **on the server**. Nothing is copied from a developer machine:
    Python packages, Next.js bundles and the virtualenv are all produced here.

    Steps
      1. Pre-flight: Python/Node/npm versions, .env sanity, git state
      2. .venv creation + pip install -r requirements.lock
      3. Backend import smoke test
      4. npm ci + npm run build for frontend-public and frontend-admin
      5. Optional Alembic migration (-Migrate)
      6. NSSM service re-registration and restart
      7. Health checks on :8000, :3000, :3001

.PARAMETER Ref
    Git tag/branch/commit to check out before deploying. Omit to deploy the
    current checkout.

.PARAMETER Migrate
    Run `alembic upgrade head` against DATABASE_URL before restarting services.

.PARAMETER SkipFrontend
    Skip the two Next.js builds (backend-only change).

.PARAMETER SkipServices
    Rebuild only; do not touch Windows services.

.PARAMETER SkipHealthCheck
    Do not poll the health endpoints at the end.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\windows\deploy_release.ps1 -Ref windows-v1.4.2

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\windows\deploy_release.ps1 -SkipFrontend -Migrate
#>

param(
    [string]$Ref = "",
    [switch]$Migrate,
    [switch]$SkipFrontend,
    [switch]$SkipServices,
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$script:Failures = 0

function Write-Step([string]$Text) {
    Write-Host "`n==> $Text" -ForegroundColor Cyan
}

function Write-Ok([string]$Text) {
    Write-Host "    [OK] $Text" -ForegroundColor Green
}

function Write-Warn([string]$Text) {
    Write-Host "    [WARN] $Text" -ForegroundColor Yellow
}

function Fail([string]$Text) {
    Write-Host "    [FAIL] $Text" -ForegroundColor Red
    throw $Text
}

function Assert-Command([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "'$Name' is not on PATH. $Hint"
    }
}

function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        Fail "$Exe $($Arguments -join ' ') exited with code $LASTEXITCODE"
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " HYDROCAST PRODUCTION DEPLOYMENT" -ForegroundColor Cyan
Write-Host " Root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# ─────────────────────────────────────────────────────────────────────────────
# 1. Pre-flight
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "1/7  Pre-flight checks"

# A folder-copy deployment has no .git directory. That is supported; we simply
# skip revision tracking and the source-tree cleanliness gate.
$hasGit = Test-Path (Join-Path $ProjectRoot ".git")
if ($hasGit) {
    Assert-Command "git"  "Install Git for Windows."
}
Assert-Command "python" "Install Python 3.12 x64 and add it to PATH."

$pyVersion = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($pyVersion -notmatch '^(3\.1[2-9])$') {
    Fail "Python $pyVersion detected; HydroCast requires 3.12 or newer."
}
Write-Ok "Python $pyVersion"

if ($SkipFrontend) {
    Write-Ok "Node/npm checks skipped (-SkipFrontend)"
} else {
    Assert-Command "node" "Install Node.js 20 LTS (includes npm)."
    Assert-Command "npm"  "Install Node.js 20 LTS (includes npm)."

    $nodeVersion = (& node -v).TrimStart('v')
    $nodeMajor = [int]($nodeVersion.Split('.')[0])
    if ($nodeMajor -lt 20) {
        Fail "Node $nodeVersion detected; Next.js 14 requires Node 20 or newer."
    }
    if ($nodeMajor -gt 24) {
        Write-Warn "Node $nodeVersion is newer than the validated 20.x LTS line."
    } else {
        Write-Ok "Node $nodeVersion"
    }

    $npmVersion = (& npm -v).Trim()
    Write-Ok "npm $npmVersion"
}

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Fail ".env is missing. Copy .env.example to .env and fill in the production secrets."
}

$envLines = @{}
Get-Content (Join-Path $ProjectRoot ".env") | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
        $envLines[$matches[1]] = $matches[2].Trim()
    }
}

$required = @("DATABASE_URL", "API_KEY", "JWT_SECRET", "ADMIN_PASSWORD", "INTERNAL_KEY")
foreach ($key in $required) {
    if (-not $envLines.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($envLines[$key])) {
        Fail ".env is missing a value for $key."
    }
    if ($envLines[$key] -match 'REPLACE_ME|change-this|CHANGE_ME') {
        Fail ".env still contains a placeholder for $key."
    }
}
Write-Ok ".env required keys present"

if ($envLines["JWT_SECRET"].Length -lt 32) {
    Write-Warn "JWT_SECRET is shorter than 32 characters; regenerate it with 48+ random bytes."
}
if ($envLines.ContainsKey("CORS_ORIGINS") -and $envLines["CORS_ORIGINS"] -match '\*') {
    Fail "CORS_ORIGINS contains '*'. The API refuses to start with a wildcard origin."
}
if ($envLines.ContainsKey("CORS_ORIGINS") -and $envLines["CORS_ORIGINS"] -match 'http://(?!localhost|127\.0\.0\.1)') {
    Write-Warn "CORS_ORIGINS contains a non-local http:// origin; production browsers send https://."
}

# Only source/config paths must be clean. Runtime state under data/ is expected
# to change while the scheduler is running.
if ($hasGit) {
    $dirty = & git status --porcelain -- backend frontend-public frontend-admin scripts windows alembic requirements.txt requirements.lock
    if ($dirty) {
        Write-Host $dirty
        Fail "Uncommitted changes in source paths. Commit them (or deploy a tag) before running this script."
    }
    Write-Ok "working tree clean for deployable paths"
} else {
    Write-Warn "No .git directory found - deploying the folder as-is (no revision checks)."
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Select revision
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "2/7  Selecting revision"

if ($Ref) {
    if (-not $hasGit) {
        Fail "-Ref requires a Git checkout; use a folder copy without -Ref."
    }
    Invoke-Native "git" @("fetch", "--tags", "--prune", "origin")
    Invoke-Native "git" @("checkout", $Ref)
}

if ($hasGit) {
    $commit = (& git rev-parse --short HEAD).Trim()
    $subject = (& git log -1 --pretty=%s).Trim()
} else {
    $commit = "folder-copy"
    $subject = "manual migration"
}
Write-Ok "Deploying $commit - $subject"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Python environment
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "3/7  Python environment"

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "    Creating .venv ..." -ForegroundColor Gray
    Invoke-Native "python" @("-m", "venv", ".venv")
}
Write-Ok "virtualenv present"

Invoke-Native $venvPython @("-m", "pip", "install", "--upgrade", "pip", "--quiet")
$lockFile = Join-Path $ProjectRoot "requirements.lock"
if (-not (Test-Path $lockFile)) {
    Fail "requirements.lock is missing; run scripts/gen_requirements_lock.py and commit it."
}
Invoke-Native $venvPython @("-m", "pip", "install", "-r", "requirements.lock", "--quiet")
Write-Ok "requirements.lock installed"

Invoke-Native $venvPython @("-c", "import backend.api.main; print('backend import ok')")
Write-Ok "backend import smoke test"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Frontends
# ─────────────────────────────────────────────────────────────────────────────
if ($SkipFrontend) {
    Write-Step "4/7  Frontends (skipped)"
} else {
    Write-Step "4/7  Frontend builds"

    foreach ($app in @("frontend-public", "frontend-admin")) {
        $appPath = Join-Path $ProjectRoot $app
        if (-not (Test-Path (Join-Path $appPath "package-lock.json"))) {
            Fail "$app/package-lock.json is missing; npm ci cannot run reproducibly."
        }

        $envLocal = Join-Path $appPath ".env.local"
        $envTemplate = Join-Path $appPath ".env.local.example"
        if (-not (Test-Path $envLocal)) {
            if (Test-Path $envTemplate) {
                Copy-Item $envTemplate $envLocal
                Write-Warn "$app/.env.local was created from the example - review the URLs, then rebuild."
            } else {
                Fail "$app/.env.local is missing and no example file exists."
            }
        }

        Push-Location $appPath
        try {
            Write-Host "    $app : npm ci" -ForegroundColor Gray
            Invoke-Native "npm" @("ci", "--no-audit", "--no-fund")
            Write-Host "    $app : npm run build" -ForegroundColor Gray
            Invoke-Native "npm" @("run", "build")
        } finally {
            Pop-Location
        }
        Write-Ok "$app built"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. Database migration (opt-in)
# ─────────────────────────────────────────────────────────────────────────────
if ($Migrate) {
    Write-Step "5/7  Database migration"
    Invoke-Native $venvPython @("-m", "alembic", "upgrade", "head")
    Write-Ok "alembic upgrade head"
} else {
    Write-Step "5/7  Database migration (skipped; pass -Migrate to run)"
}

# ─────────────────────────────────────────────────────────────────────────────
# 6. Services
# ─────────────────────────────────────────────────────────────────────────────
if ($SkipServices) {
    Write-Step "6/7  Windows services (skipped)"
} else {
    Write-Step "6/7  Windows services"
    Invoke-Native "powershell" @("-ExecutionPolicy", "Bypass", "-File", ".\windows\install_services.ps1")
    Invoke-Native "powershell" @("-ExecutionPolicy", "Bypass", "-File", ".\windows\service_control.ps1", "-Action", "restart")
    Write-Ok "services re-registered and restarted"
}

# ─────────────────────────────────────────────────────────────────────────────
# 7. Health checks
# ─────────────────────────────────────────────────────────────────────────────
if ($SkipHealthCheck) {
    Write-Step "7/7  Health checks (skipped)"
} else {
    Write-Step "7/7  Health checks"

    $endpoints = @(
        @{ Name = "backend ready"; Url = "http://127.0.0.1:8000/healthz/ready"; Timeout = 90 },
        @{ Name = "public portal"; Url = "http://127.0.0.1:3000/";            Timeout = 45 },
        @{ Name = "admin console"; Url = "http://127.0.0.1:3001/";            Timeout = 45 }
    )

    foreach ($ep in $endpoints) {
        $deadline = (Get-Date).AddSeconds($ep.Timeout)
        $healthy = $false
        while ((Get-Date) -lt $deadline) {
            try {
                $resp = Invoke-WebRequest -Uri $ep.Url -UseBasicParsing -TimeoutSec 5
                if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
                    $healthy = $true
                    break
                }
            } catch {
                Start-Sleep -Seconds 3
            }
        }
        if ($healthy) {
            Write-Ok "$($ep.Name) responded at $($ep.Url)"
        } else {
            $script:Failures++
            Write-Host "    [FAIL] $($ep.Name) did not respond at $($ep.Url)" -ForegroundColor Red
            Write-Host "           Check data\logs\ and Get-Service HydroCast-*" -ForegroundColor DarkGray
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
$deployedFile = Join-Path $ProjectRoot "data\deployed_revision.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $deployedFile) | Out-Null
"$commit  $(Get-Date -Format o)  $subject" | Set-Content $deployedFile -Encoding UTF8

Write-Host "`n============================================================" -ForegroundColor Cyan
if ($script:Failures -eq 0) {
    Write-Host " DEPLOYMENT COMPLETE - $commit" -ForegroundColor Green
} else {
    Write-Host " DEPLOYMENT FINISHED WITH $($script:Failures) HEALTH FAILURE(S)" -ForegroundColor Red
}
Write-Host " Revision recorded in data\deployed_revision.txt" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

if ($script:Failures -gt 0) { exit 1 }
