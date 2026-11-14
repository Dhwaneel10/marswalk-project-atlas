@echo off
setlocal enabledelayedexpansion

title MarsWalk 2.0 — Project Atlas Launcher

echo ============================================================================
echo   MARSWALK 2.0 -- PROJECT ATLAS COMPETITION LAUNCHER
echo ============================================================================

cd /d "%~dp0\.."

set PORT=3000
set HOST=127.0.0.1

:: 1. Verify virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found at .venv\Scripts\python.exe.
    echo Please setup the environment from repository root:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip.exe install -e .
    echo.
    pause
    exit /b 1
)

:: 2. Check if port is already occupied
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [NOTICE] Port %PORT% is already occupied by an active process.
    echo Probing existing MarsWalk Atlas server health...
    powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://127.0.0.1:%PORT%/api/health' -TimeoutSec 2; Write-Host '  >> Existing Atlas server is ONLINE:' $r.target } catch { Write-Host '  >> Port is in use by another non-MarsWalk process.' }"
    echo.
    echo Opening browser to http://%HOST%:%PORT%...
    start http://%HOST%:%PORT%
    echo.
    echo If you need to restart the server, identify its PID and terminate it:
    echo   netstat -ano ^| findstr ":%PORT% "
    echo   taskkill /PID ^<PID^> /F
    echo ============================================================================
    pause
    exit /b 0
)

echo [OK] Virtual environment found (.venv\Scripts\python.exe).
echo [OK] Port %PORT% is free.
echo.
echo Launching MarsWalk Project Atlas daemon...
echo Application URL: http://%HOST%:%PORT%
echo Press Ctrl+C to stop the server.
echo ============================================================================
echo.

.\.venv\Scripts\python.exe scripts\run_atlas.py --port %PORT%

pause
