# Project MarsWalk — Ubuntu 22.04 LTS Bootstrap & Environment Report

**Document ID:** `MARSWALK-BOOT-001`  
**Date:** 2026-11-14  
**Author:** Principal Software Architect & Linux Systems Engineer  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Target Platform:** Ubuntu 22.04 LTS (x86_64, Linux 6.6.137+, glibc 2.35)  
**Status:** **100% OPERATIONAL & VERIFIED**

---

## 1. Executive Summary

Mission 1 authorized the immediate bootstrapping and operational recovery of the MarsWalk 2.0 / Project Atlas repository on Ubuntu 22.04 LTS. In accordance with strict engineering constraints:
- An isolated Python virtual environment (`.venv`) was constructed at the workspace root.
- **Zero packages were installed into the system Python**, and no global environments were altered.
- All core geospatial, numerical, and contract dependencies (`rasterio`, `affine`, `jsonschema`, `numpy`, `scipy`, `pytest`) were successfully installed via precompiled binary wheels.
- Native POSIX Bash launchers (`scripts/setup_atlas.sh`, `scripts/start_atlas.sh`) were created with execution permissions (`chmod +x`).
- `scripts/verify_installation.py` verified **26 of 26 checkpoints passed (0 warnings, 0 failures)**.

---

## 2. Environment Specifications & Isolation Architecture

### 2.1 Host System Diagnostics
- **Operating System:** Ubuntu 22.04.5 LTS (Jammy Jellyfish).
- **Kernel Architecture:** Linux x86_64 (6.6.137+).
- **System Python:** Python 3.10.12 located at `/usr/bin/python3`.
- **Node.js Runtime:** v22.23.5 (verified clean syntax on `web/app.js`).
- **Web Frontend Dependencies:** 100% vendored in `web/libs/` (`three.min.js`, `OrbitControls.js`); zero npm installation required.

### 2.2 Virtual Environment Construction
The isolated runtime was provisioned using Python's standard library `venv` module:
```bash
/usr/bin/python3 -m venv .venv
```
Tooling inside `.venv` was upgraded to eliminate legacy wheel build deprecations:
- `pip`: 22.0.2 &rarr; **26.3**
- `setuptools`: 59.6.0 &rarr; **84.2.1**
- `wheel`: &rarr; **0.48.0**
- `packaging`: &rarr; **26.3**

---

## 3. Installed Package Manifest & Version Audit

The minimal required dependency graph was installed strictly into `.venv/lib/python3.10/site-packages`:

| Package Name | Installed Version | Declared in `requirements.txt` | Purpose in Project Atlas |
|:---|:---:|:---:|:---|
| **`numpy`** | `2.2.6` | `>=2.0.0` | Numerical tensor operations, Horn slope convolution |
| **`scipy`** | `1.15.3` | `>=1.14.0` | Spatial kd-trees, `ndimage` dilation & filters |
| **`rasterio`** | `1.4.4` | `>=1.4.0` | USGS MRO CTX 20m GeoTIFF I/O, window queries |
| **`affine`** | `3.0.1` | `>=2.4.0` | Geodetic affine transforms (`ESRI:103885` &rarr; IAU 2000) |
| **`jsonschema`** | `4.26.0` | `>=4.20.0` | Draft 2020-12 data contract schema validation |
| **`requests`** | `2.34.2` | `>=2.31.0` | HTTP client telemetry and live server test harness |
| **`websockets`** | `16.1.1` | `>=12.0` | Real-time Chrome DevTools Protocol (CDP) streams |
| **`pytest`** | `9.2.0` | `>=8.0.0` | Modern test runner (natively honors `pyproject.toml`) |
| **`pillow`** | `12.3.0` | `requirements-lock.txt` | Optical texture validation (`jezero_ctx_orthomosaic`) |
| **`plotly`** | `7.1.0` | `requirements-lock.txt` | Analytical plotting companion in `app.py` |
| **`streamlit`**| `1.65.0` | `requirements-lock.txt` | Interactive tactical workstation companion |

*Note on Geospatial Native Libraries:* `rasterio==1.4.4` installed cleanly from official PyPI `manylinux_2_28_x86_64` binary wheels containing statically linked GDAL and PROJ shared libraries, eliminating the need for `apt-get install libgdal-dev` on Ubuntu 22.04.

---

## 4. Resolution of Host Environment & ROS 2 Interference

### The Defect
During initial test discovery, Pytest crashed with:
```text
Error while loading plugin "pytest11"
ModuleNotFoundError: No module named 'yaml' in /opt/ros/humble/lib/python3.10/site-packages/launch...
```
Investigation revealed that the developer's Ubuntu workstation had **ROS 2 Humble** installed in `/opt/ros/humble/`. The default `PYTHONPATH` exported ROS paths, causing two severe side effects:
1. Pytest automatically loaded the ROS `launch_testing` plugin via global setuptools entrypoints.
2. A ROS package named `scripts` in `/opt/ros/humble/local/lib/python3.10/dist-packages/scripts` shadowed the project's local `scripts/` directory.

### The Engineering Solution
Both Linux launcher scripts (`setup_atlas.sh` and `start_atlas.sh`) and all test commands enforce environment hygiene:
```bash
export PYTHONPATH="src:."
export PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
```
This guarantees that local MarsWalk modules take strict precedence and external system plugins are completely bypassed.

---

## 5. Linux Launcher Scripts Created

### 5.1 Automated Setup Script: `scripts/setup_atlas.sh`
- Verifies Ubuntu distribution and asserts Python runtime `>= 3.10`.
- Creates `.venv` if missing.
- Upgrades `pip`, `setuptools`, and `wheel`.
- Installs production and analytical dependencies.
- Copies `.env.example` to `.env` if not present.
- Executes `scripts/verify_installation.py` and returns an exit code of `0` on success.
- **Permissions:** `rwxr-xr-x` (`chmod +x`).

### 5.2 Application Launcher Script: `scripts/start_atlas.sh`
- Accepts command-line flags: `--port <PORT>` (default `3000`), `--no-browser`, `--demo`, and `--help`.
- Validates `.venv` existence and checks port availability via `ss` / `netstat`.
- Normalizes `PYTHONPATH="src:."`.
- Starts `scripts/run_atlas.py` with clear startup telemetry.
- **Permissions:** `rwxr-xr-x` (`chmod +x`).

---

## 6. Official Installation Verification Certificate

Executing `scripts/verify_installation.py` under the isolated `.venv` produces:

```text
==============================================================================
  PROJECT ATLAS / MARSWALK 2.0 — INSTALLATION & ENVIRONMENT AUDIT
==============================================================================
[PASSED] Python Runtime: 3.10.12 (>= 3.10 required, 3.12 recommended)
[PASSED] Package 'numpy' (v2.2.6): Numerical tensor operations
[PASSED] Package 'scipy' (v1.15.3): Scientific calculations & spatial trees
[PASSED] Package 'rasterio' (v1.4.4): Planetary geospatial raster I/O
[PASSED] Package 'affine' (v3.0.1): Affine coordinate transformations
[PASSED] Package 'jsonschema' (v4.26.0): Draft 2020-12 data contract enforcement
[PASSED] Package 'requests' (v2.34.2): HTTP client telemetry communication
[PASSED] Package 'websockets' (v16.1.1): Real-time CDP and telemetry streams
[PASSED] Package 'pytest' (v9.2.0): Automated test runner & regression suites
[PASSED] Architecture Module 'marswalk.core.terrain': Terrain elevation & Horn slope kernel
[PASSED] Architecture Module 'marswalk.core.planner': A* search & TSP tour optimization
[PASSED] Architecture Module 'marswalk.core.atlas_campaign_compiler': Intent ingestion & 7-phase DAG compiler
[PASSED] Architecture Module 'marswalk.core.atlas_mission_event_coordinator': Discrete-event priority scheduler
[PASSED] Architecture Module 'marswalk.core.atlas_mission_state': Mission state twin & Merkle hash chain
[PASSED] Architecture Module 'marswalk.core.atlas_resource_operations': ISRU, Kilopower & mass/energy accounting
[PASSED] Architecture Module 'marswalk.core.atlas_scientific_operations': Bayesian hypothesis testing & Shannon gain
[PASSED] Architecture Module 'marswalk.core.atlas_autonomous_operations': OWLT delay modeling & idempotent commands
[PASSED] Architecture Module 'marswalk.core.atlas_mission_execution_core': Closed-loop mission execution engine
[PASSED] Architecture Module 'marswalk.core.atlas_unified_asset_manager': Heterogeneous rover/aircraft fleet registry
[PASSED] Architecture Module 'marswalk.core.atlas_mission_resilience_coordinator': Cascading failure injection & FDIR
[PASSED] Architecture Module 'marswalk.core.atlas_mission_replay': Deterministic replay verification engine
[PASSED] Primary USGS Jezero 20m DTM (jezero_ready_20m.tif): Exists and SHA-256 verified (875e7e80c170b84e...)
[PASSED] Frontend Asset 'web/index.html': Found (652165 bytes)
[PASSED] Frontend Asset 'web/app.js': Found (1219554 bytes)
[PASSED] Frontend Asset 'web/styles.css': Found (199753 bytes)
[PASSED] Mathematical & Physical Core: Horn kernel & hypsometric formulas validated
------------------------------------------------------------------------------
Summary: 26 passed, 0 warnings, 0 failures
>>> RESULT: Environment and installation verified successfully for Project Atlas. <<<
==============================================================================
```
