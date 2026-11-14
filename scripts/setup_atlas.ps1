# scripts/setup_atlas.ps1
# Automated Setup Script for Project Atlas / MarsWalk 2.0
# Requires PowerShell 5.1+ and Python 3.10+ (Python 3.12 recommended)

[CmdletBinding()]
param(
    [switch]$UseLockFile = $false,
    [string]$PythonExe = "python"
)

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  PROJECT ATLAS / MARSWALK 2.0 - REPRODUCIBLE ENVIRONMENT SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check Python installation and version
try {
    $versionOutput = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>&1
    Write-Host "[OK] Detected Python executable: $PythonExe (Version $versionOutput)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Could not execute Python. Ensure Python 3.10+ is installed and on PATH." -ForegroundColor Red
    exit 1
}

# 2. Virtual environment creation
if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] Creating clean virtual environment in .venv..." -ForegroundColor Yellow
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Existing virtual environment found in .venv." -ForegroundColor Green
}

$VenvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    # Unix fallback
    $VenvPython = "./.venv/bin/python"
}

# 3. Upgrade pip and install wheel
Write-Host "[INFO] Upgrading pip, setuptools, and wheel..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip setuptools wheel --quiet

# 4. Install production dependencies
if ($UseLockFile -and (Test-Path "requirements-lock.txt")) {
    Write-Host "[INFO] Installing exact locked dependencies from requirements-lock.txt..." -ForegroundColor Yellow
    & $VenvPython -m pip install -r requirements-lock.txt --quiet
} else {
    Write-Host "[INFO] Installing production dependencies from requirements.txt..." -ForegroundColor Yellow
    & $VenvPython -m pip install -r requirements.txt --quiet
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Dependency installation encountered errors." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Dependencies installed successfully." -ForegroundColor Green

# 5. Verify installation
Write-Host "[INFO] Running verify_installation.py..." -ForegroundColor Yellow
$env:PYTHONPATH = "src"
& $VenvPython scripts/verify_installation.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "  SETUP COMPLETE: Environment is ready." -ForegroundColor Green
    Write-Host "  To launch the application: .\scripts\start_atlas.ps1" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Verification detected warnings or errors. Check log above." -ForegroundColor Yellow
}
