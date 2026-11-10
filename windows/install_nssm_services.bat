@echo off
REM ============================================================================
REM HydroCast Dual-Layer Windows Service Installer (NSSM + Watchdog)
REM Shivaji University Kolhapur (SUK) Production Windows Server Standard
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================
echo   HYDROCAST WINDOWS SERVICE INSTALLER
echo   Shivaji University Kolhapur (SUK)
echo ============================================================

REM 1. Administrator Privilege Check
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This installer requires Administrator privileges.
    echo Please right-click install_nssm_services.bat and select "Run as administrator".
    pause
    exit /b 1
)

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"
echo Working Directory: %CD%

REM 2. Invoke PowerShell Service Registrar
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%\windows\install_services.ps1"

REM 3. Verify NSSM binary availability
set "NSSM_BIN=nssm.exe"
where %NSSM_BIN% >nul 2>&1
if %errorLevel% neq 0 (
    if exist "%TEMP%\nssm.exe" (
        set "NSSM_BIN=%TEMP%\nssm.exe"
    ) else (
        echo [WARN] NSSM executable not found in PATH or TEMP.
    )
)

REM 4. Register Autonomous HydroCast Watchdog Service
if exist "%NSSM_BIN%" (
    echo Registering HydroCast-Watchdog Windows Service...
    "%NSSM_BIN%" stop HydroCast-Watchdog confirm >nul 2>&1
    "%NSSM_BIN%" remove HydroCast-Watchdog confirm >nul 2>&1
    "%NSSM_BIN%" install HydroCast-Watchdog powershell.exe "-ExecutionPolicy Bypass -File \"%PROJECT_ROOT%\windows\watchdog_service.ps1\""
    "%NSSM_BIN%" set HydroCast-Watchdog AppDirectory "%PROJECT_ROOT%"
    "%NSSM_BIN%" set HydroCast-Watchdog DisplayName "HydroCast Autonomous Watchdog Supervisor"
    "%NSSM_BIN%" set HydroCast-Watchdog Description "Continuously supervises ports 5432, 8000, 3000, and 3001 with 30s auto-healing."
    "%NSSM_BIN%" set HydroCast-Watchdog Start SERVICE_AUTO_START
    "%NSSM_BIN%" set HydroCast-Watchdog AppRestartDelay 5000
    "%NSSM_BIN%" start HydroCast-Watchdog >nul 2>&1
    echo [OK] HydroCast-Watchdog registered and started.
)

echo.
echo ============================================================
echo   HYDROCAST SERVICES INSTALLED SUCCESSFULLY
echo ============================================================
pause
