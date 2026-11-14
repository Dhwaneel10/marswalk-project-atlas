<#
.SYNOPSIS
    MarsWalk 2.0 (Project Atlas) — Conference Demonstration Edition Launcher
.DESCRIPTION
    Production PowerShell launcher designed for evaluators, judges, and live conference demonstrations.
    - Resolves repository root reliably regardless of working directory or execution context.
    - Verifies the local Python virtual environment (.venv\Scripts\python.exe).
    - Checks port 3000 occupancy and validates existing Atlas server health via /api/health.
    - Prevents spawning duplicate daemons when an active server is already healthy.
    - Refuses to kill foreign/unknown processes occupying the port without user direction.
    - Launches default web browser directly to http://127.0.0.1:3000/?mode=demo.
.PARAMETER Port
    HTTP listen port (default: 3000).
.PARAMETER NoBrowser
    Do not automatically launch the web browser.
.PARAMETER Background
    Launch the Atlas server in a background window if starting fresh.
.PARAMETER AllowSystemPython
    Allow fallback to system Python if .venv is absent (not recommended).
.EXAMPLE
    .\scripts\start_marswalk_demo.ps1
.EXAMPLE
    .\scripts\start_marswalk_demo.ps1 -Port 3000 -NoBrowser
#>
[CmdletBinding()]
param(
    [int]$Port = 3000,
    [switch]$NoBrowser,
    [switch]$Background,
    [switch]$AllowSystemPython
)

$ErrorActionPreference = "Stop"

# 1. Reliable Project Root Resolution
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path
Set-Location $ProjectRoot

# Set PYTHONPATH to src for clean module import
$env:PYTHONPATH = "src"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  MARSWALK 2.0 -- PROJECT ATLAS: CONFERENCE DEMONSTRATION LAUNCHER" -ForegroundColor Cyan
Write-Host "  Target: Mars (IAU 2000 Sphere / USGS CTX Jezero Crater 20m DTM)" -ForegroundColor DarkCyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Repository Root: $ProjectRoot"

# 2. Virtual Environment Verification
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    if ($AllowSystemPython) {
        $PythonExe = "python"
        Write-Host "[WARNING] Local .venv not found. Falling back to system python: $PythonExe" -ForegroundColor Yellow
    } else {
        Write-Host "`n[ERROR] Python virtual environment (.venv) was not found at:" -ForegroundColor Red
        Write-Host "  $PythonExe`n" -ForegroundColor Yellow
        Write-Host "To initialize the required Windows environment, run:" -ForegroundColor White
        Write-Host "  python -m venv .venv" -ForegroundColor Green
        Write-Host "  .\.venv\Scripts\pip.exe install -r requirements.txt" -ForegroundColor Green
        Write-Host "`nOr pass -AllowSystemPython to attempt execution with system Python." -ForegroundColor Gray
        exit 1
    }
} else {
    Write-Host "[OK] Verified virtual environment: $PythonExe" -ForegroundColor Green
}

# 3. Port Occupancy & Server Health Detection
$TargetUrl = "http://127.0.0.1:$Port/?mode=demo"
$HealthUrl = "http://127.0.0.1:$Port/api/health"

$TcpConnection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if ($TcpConnection) {
    $OwningPid = $TcpConnection.OwningProcess
    Write-Host "[NOTICE] Port $Port is currently occupied by active process (PID $OwningPid)." -ForegroundColor Yellow
    Write-Host "Probing Atlas server health at $HealthUrl ..." -ForegroundColor Cyan
    try {
        $Health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3 -ErrorAction Stop
        if ($Health.status -eq "online") {
            Write-Host "[OK] Existing MarsWalk Project Atlas server is ONLINE and HEALTHY." -ForegroundColor Green
            Write-Host "  Engine:  $($Health.engine)" -ForegroundColor Gray
            Write-Host "  Target:  $($Health.target)" -ForegroundColor Gray
            Write-Host "  Terrain: $($Health.terrain_loaded) ($($Health.waypoints_count) waypoints)" -ForegroundColor Gray
            Write-Host "[INFO] Reusing existing daemon (PID $OwningPid) - duplicate process prevented." -ForegroundColor Green
            
            if (-not $NoBrowser) {
                Write-Host "Opening default browser to Conference Demonstration mode: $TargetUrl ..." -ForegroundColor Cyan
                Start-Process $TargetUrl
            }
            Write-Host "`n============================================================================" -ForegroundColor Cyan
            Write-Host "  DEMO READY: MarsWalk 2.0 is actively serving at $TargetUrl" -ForegroundColor Green
            Write-Host "============================================================================" -ForegroundColor Cyan
            exit 0
        } else {
            Write-Host "[ERROR] Port $Port responded, but reported unexpected status: $($Health.status)" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "[ERROR] Port $Port is occupied by an unrecognized non-MarsWalk process (PID $OwningPid)." -ForegroundColor Red
        Write-Host "  Refusing to terminate external process without administrator direction." -ForegroundColor Yellow
        Write-Host "  Please terminate PID $OwningPid or specify a custom port: .\scripts\start_marswalk_demo.ps1 -Port 3001" -ForegroundColor Yellow
        exit 1
    }
}

# 4. Port is Available - Launch Server
Write-Host "[OK] Port $Port is available for MarsWalk Atlas daemon." -ForegroundColor Green

if ($Background) {
    Write-Host "Launching MarsWalk Atlas daemon in background window..." -ForegroundColor Cyan
    $ProcArgs = @("scripts/run_atlas.py", "--port", "$Port", "--no-browser")
    $ServerProcess = Start-Process -FilePath $PythonExe -ArgumentList $ProcArgs -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Minimized
    
    # Wait for server to become healthy
    Write-Host "Waiting for server initialization on port $Port..." -NoNewline
    $MaxWaitSec = 15
    $Elapsed = 0
    $IsHealthy = $false
    while ($Elapsed -lt $MaxWaitSec) {
        Start-Sleep -Seconds 1
        $Elapsed++
        Write-Host "." -NoNewline
        try {
            $Check = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($Check.status -eq "online") {
                $IsHealthy = $true
                break
            }
        } catch {}
    }
    Write-Host ""
    
    if ($IsHealthy) {
        Write-Host "[OK] Server daemon initialized successfully (PID $($ServerProcess.Id))." -ForegroundColor Green
        if (-not $NoBrowser) {
            Write-Host "Opening browser: $TargetUrl" -ForegroundColor Cyan
            Start-Process $TargetUrl
        }
        Write-Host "`n============================================================================" -ForegroundColor Cyan
        Write-Host "  DEMO READY: MarsWalk 2.0 is running at $TargetUrl" -ForegroundColor Green
        Write-Host "============================================================================" -ForegroundColor Cyan
        exit 0
    } else {
        Write-Host "[ERROR] Server failed to start within $MaxWaitSec seconds." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Starting MarsWalk Atlas daemon in interactive foreground console..." -ForegroundColor Cyan
    Write-Host "Application URL: $TargetUrl"
    Write-Host "Press Ctrl+C to stop the server.`n"
    
    $ArgsList = @("scripts/run_atlas.py", "--port", "$Port", "--demo")
    if ($NoBrowser) {
        $ArgsList += "--no-browser"
    }
    
    & $PythonExe @ArgsList
}
