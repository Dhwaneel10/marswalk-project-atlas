# Project MarsWalk — Comprehensive Technical Defect Register

**Document ID:** `MARSWALK-DEF-001`  
**Date:** 2026-11-14  
**Author:** Technical Auditor & Systems Engineer  
**Workspace:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Audit Scope:** Full Codebase Vulnerability, Defect & Fragility Register

---

## 1. Defect Severity Classification

- **CRITICAL (P0):** Directly prevents application launch, breaks core runtime execution, or causes unrecoverable crash on the primary demonstration path.
- **MAJOR (P1):** Breaks automated verification, prevents test suite execution, or hardcodes environment assumptions that fail on Linux.
- **MODERATE (P2):** Degrades maintainability, adds cognitive friction, causes unnecessary disk clutter, or creates fragile architectural couplings.
- **MINOR (P3):** Code hygiene issues, stray backup files, or non-blocking configuration warnings.

---

## 2. Defect Register & Root Cause Analysis

### DEF-001: Top-Level `rasterio` Import Prevents Server Boot
- **Severity:** **CRITICAL (P0)**
- **Affected File:** `scripts/run_atlas.py` (Line 16)
- **Reproduction:**
  ```bash
  python3 scripts/run_atlas.py --port 3000
  ```
- **Observed Error:**
  ```text
  Traceback (most recent call last):
    File "scripts/run_atlas.py", line 16, in <module>
      import rasterio
  ModuleNotFoundError: No module named 'rasterio'
  ```
- **Root Cause Analysis:** `scripts/run_atlas.py` eagerly imports `rasterio` at the module root before entering `main()` or parsing CLI arguments. When running in a clean Linux environment where `rasterio` is not installed globally in `/usr/bin/python3`, the server cannot even display `--help` or serve static web assets.
- **Hackathon Impact:** High. The web interface cannot be served on port 3000 without resolving this dependency.
- **Remediation:** Establish a dedicated local `.venv` containing `rasterio`, and encapsulate imports inside lazy loaders.

---

### DEF-002: Eager Import Cascade in `marswalk.api.__init__` Blocks Preflight CLI
- **Severity:** **CRITICAL (P0)**
- **Affected Files:** `src/marswalk/api/__init__.py` (Line 5), `src/marswalk/api/service.py` (Line 15), `scripts/preflight_check.py`
- **Reproduction:**
  ```bash
  python3 scripts/preflight_check.py
  ```
- **Observed Error:**
  ```text
  Traceback (most recent call last):
    File "scripts/preflight_check.py", line 28, in <module>
      from marswalk.api.preflight import run_preflight_diagnostics
    File "src/marswalk/api/__init__.py", line 5, in <module>
      from marswalk.api.service import plan_route_api, gauntlet_api, parse_endpoint_rc
    File "src/marswalk/api/service.py", line 15, in <module>
      import rasterio
  ModuleNotFoundError: No module named 'rasterio'
  ```
- **Root Cause Analysis:** `marswalk/api/__init__.py` unconditionally imports `service.py`. When another tool (like `preflight_check.py` or `campaign_analytics.py`) imports from `marswalk.api` solely to access lightweight contracts or diagnostic functions, it is forced to load `service.py` and its full transitive dependency graph (`rasterio`, `affine`, `jsonschema`).
- **Hackathon Impact:** High. Preflight readiness diagnostics cannot execute to verify system health before presentations.
- **Remediation:** Remove eager `service.py` exports from `__init__.py`. Keep package `__init__.py` files clean or use lazy module imports.

---

### DEF-003: Pytest 6.2.5 Ignores `pyproject.toml` Pythonpath Configuration
- **Severity:** **MAJOR (P1)**
- **Affected Files:** `pyproject.toml` (Lines 22–24), `tests/*.py`
- **Reproduction:**
  ```bash
  python3 -m pytest tests/test_milestone_13aa_end_to_end.py
  ```
- **Observed Error:**
  ```text
  ModuleNotFoundError: No module named 'marswalk'
  PytestConfigWarning: Unknown config option: pythonpath
  ```
- **Root Cause Analysis:** The project relies on `[tool.pytest.ini_options] pythonpath = ["src", "."]` to resolve package imports. Pytest on Ubuntu 22.04 LTS is version 6.2.5; `pythonpath` was only introduced in Pytest 7.0.0+.
- **Hackathon Impact:** High. Developers running standard `pytest` commands observe mass test collection crashes (88 test files failing collection).
- **Remediation:** Always invoke pytest with `PYTHONPATH=src python3 -m pytest` or upgrade pytest to `>= 8.0.0` in `.venv`.

---

### DEF-004: Hardcoded Windows Paths in Over 30 Browser Acceptance Scripts
- **Severity:** **MAJOR (P1)**
- **Affected Files:** Over 30 scripts in `scripts/` (e.g., `audit_milestone_13a_browser_acceptance.py`, `verify_apocalypse_browser.py`, `build_a0_poster.py`)
- **Reproduction:**
  ```bash
  python3 scripts/audit_milestone_13a_browser_acceptance.py
  ```
- **Observed Error:**
  ```text
  FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  ```
- **Root Cause Analysis:** Scripts contain hardcoded Windows executable paths:
  `CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"`
  `ARTIFACT_DIR = r"C:\Users\dhwan\.gemini\antigravity\brain\..."`
  No fallback logic or dynamic binary discovery (`shutil.which`) is implemented.
- **Hackathon Impact:** Medium. Automated browser screenshot evidence capture and headless CDP verification cannot run on Linux.
- **Remediation:** Parameterize browser discovery using `shutil.which("google-chrome")` or environment variables `CHROME_BIN`.

---

### DEF-005: Total Absence of Native Linux Shell Launchers
- **Severity:** **MAJOR (P1)**
- **Affected Files:** Entire `scripts/` directory
- **Reproduction:** Inspection of `find scripts/ -name "*.sh"` returns zero results.
- **Root Cause Analysis:** The application was developed exclusively with Windows PowerShell (`.ps1`) and batch scripts (`.bat`).
- **Hackathon Impact:** Medium. Linux operators have no one-click launcher to initialize `.venv`, install packages, or start the server.
- **Remediation:** Create standard POSIX executable bash scripts (`scripts/setup_atlas.sh`, `scripts/start_atlas.sh`).

---

### DEF-006: Monolithic Overloaded Frontend Architecture (24 Tabs)
- **Severity:** **MODERATE (P2)**
- **Affected Files:** `web/index.html` (652 KB), `web/app.js` (1.2 MB)
- **Root Cause Analysis:** Incremental development across Milestones 8 through 13 resulted in 24 tab interfaces appended into single monolithic files without component modularization. Subsystems like *Planetary Foundry*, *Aerial Corps*, and *Settlement Consumables* compete for screen real estate and memory.
- **Hackathon Impact:** High risk of cognitive overload and presentation disorientation. Judges will be confused by 24 tabs during a 5-minute pitch.
- **Remediation:** Default the UI to a streamlined "Flagship Competition Cockpit" view highlighting the 5 Core Capabilities, hiding speculative tabs from the primary navigation bar.

---

### DEF-007: Test Artifact Workspace Pollution in Repository
- **Severity:** **MODERATE (P2)**
- **Affected Files:** `data/workspaces/events/` (over 4,000 JSONs), `data/workspaces/recommendations/` (over 1,000 JSONs)
- **Root Cause Analysis:** Integration tests from Milestone 11 wrote transient test fixtures directly into persistent repository directories without cleanup or gitignoring.
- **Hackathon Impact:** Low runtime impact, but increases git clone size and clutters directory navigation.
- **Remediation:** Protected under Mission 0 data safety rules. Future tests must use isolated `/tmp` fixtures or mock IDs prefixed with `test_`.

---

### DEF-008: Stray Historical Backup File in Web Root
- **Severity:** **MINOR (P3)**
- **Affected File:** `web/app.js.bak13d_orig` (841 KB)
- **Root Cause Analysis:** Leftover manual backup from Milestone 13D development.
- **Hackathon Impact:** Negligible. Does not impact runtime unless inadvertently referenced.
- **Remediation:** Retain untouched per Mission 0 rules; exclude from deployment bundles.

---

### DEF-009: Missing Default `.env` Configuration File
- **Severity:** **MINOR (P3)**
- **Affected File:** Workspace root (`.env.example` exists, `.env` absent)
- **Root Cause Analysis:** `.env` was gitignored, but no automatic copy step exists for new clones.
- **Hackathon Impact:** Low. Server falls back to internal defaults (`127.0.0.1:3000`).
- **Remediation:** Provide automatic `.env` creation in `setup_atlas.sh`.

---

## 3. Defect Summary & Resolution Matrix

| Defect ID | Severity | Description | Milestone Scheduled for Fix |
|:---:|:---:|:---|:---:|
| **DEF-001** | CRITICAL | Top-level `rasterio` import crashes `run_atlas.py` | Milestone 1 |
| **DEF-002** | CRITICAL | Eager import cascade in `marswalk.api.__init__` | Milestone 2 |
| **DEF-003** | MAJOR | Pytest 6.2.5 pythonpath configuration defect | Milestone 1 |
| **DEF-004** | MAJOR | Hardcoded Windows paths in browser audit scripts | Milestone 4 |
| **DEF-005** | MAJOR | Total absence of native Linux `.sh` launchers | Milestone 1 |
| **DEF-006** | MODERATE | Monolithic 24-tab UI causing presentation clutter | Milestone 3 |
| **DEF-007** | MODERATE | Workspace test artifact pollution (5,000+ files) | Post-Competition |
| **DEF-008** | MINOR | Stray backup file `web/app.js.bak13d_orig` | Post-Competition |
| **DEF-009** | MINOR | Missing `.env` default configuration file | Milestone 1 |
