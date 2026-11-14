<#
.SYNOPSIS
    MarsWalk 2.0 (Project Atlas) — PowerShell Application Launcher
.DESCRIPTION
    Launches the Atlas HTTP server on port 3000, checks port availability,
    verifies environment prerequisites, and opens the interactive 3D workstation in default browser.
.PARAMETER Port
    HTTP listen port (default: 3000).
.PARAMETER NoBrowser
    Do not automatically launch the web browser.
#>
[CmdletBinding()]
param(
    [int]$Port = 3000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectRoot

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  MARSWALK 2.0 -- PROJECT ATLAS COMPETITION LAUNCHER (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Repository: $ProjectRoot"

# 1. Resolve Python executable
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
    Write-Host "[WARNING] Local .venv not found. Falling back to system python: $PythonExe" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Using virtual environment: $PythonExe" -ForegroundColor Green
}

# 2. Check port availability
$TcpConnection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($TcpConnection) {
    Write-Host "[NOTICE] Port $Port is currently occupied by PID $($TcpConnection.OwningProcess)." -ForegroundColor Yellow
    Write-Host "Probing existing MarsWalk Atlas server health at http://127.0.0.1:$Port/api/health..."
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
        Write-Host "  >> Existing Atlas server is ONLINE: $($Health.target)" -ForegroundColor Green
        if (-not $NoBrowser) {
            Start-Process "http://127.0.0.1:$Port"
        }
        exit 0
    } catch {
        Write-Host "  >> Port $Port is occupied by a non-MarsWalk process. Please free the port and retry." -ForegroundColor Red
        exit 1
    }
}

# 3. Start Atlas server
Write-Host "[OK] Port $Port is available." -ForegroundColor Green
Write-Host "Starting MarsWalk Atlas server daemon on http://127.0.0.1:$Port ..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate the server.`n"

$env:PYTHONPATH = "src"
$ArgsList = @("scripts/run_atlas.py", "--port", "$Port")
if ($NoBrowser) {
    $ArgsList += "--no-browser"
}

& $PythonExe @ArgsList
