# scripts/start_atlas.ps1
# Launcher for Project Atlas / MarsWalk 2.0 HTTP API & Interactive Workstation

[CmdletBinding()]
param(
    [int]$Port = 3000,
    [string]$HostAddress = "127.0.0.1",
    [switch]$NoBrowser = $false
)

$VenvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

$env:PYTHONPATH = "src"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  LAUNCHING PROJECT ATLAS / MARSWALK 2.0" -ForegroundColor Cyan
Write-Host "  URL: http://$HostAddress`:$Port" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$argsList = @("scripts/run_atlas.py", "--port", "$Port", "--host", "$HostAddress")
if ($NoBrowser) {
    $argsList += "--no-browser"
}

& $VenvPython @argsList
