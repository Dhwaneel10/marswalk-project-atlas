# Project Atlas — Installation Quickstart Guide

Release Identifier: Atlas Research Preview 1.0 (Build 13V-RC1)
Classification: Academic Research Simulation Software (Non-Flight-Certified)

## System Requirements
- Supported OS: Windows 10/11 (64-bit), Linux (Ubuntu 22.04+), macOS (13.0+)
- Python Runtime: Python 3.10+ (Python 3.12 recommended)
- Disk Storage: ~2.5 GB (including USGS CTX DTM raster)
- GPU: Not required (pure CPU numerical modeling & point-mass physics)

## Installation (Windows PowerShell)
```powershell
# 1. Automated environment setup
.\scripts\setup_atlas.ps1

# 2. Verify environment, imports, and DTM dataset hash
python scripts/verify_installation.py
```

## Installation (Linux / macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python scripts/verify_installation.py
```

## Verification
Executing `scripts/verify_installation.py` checks 26 system health parameters.
All checks must report [PASSED].
