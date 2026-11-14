# Project Atlas — Milestone 13AB: State Preservation & Baseline Snapshot
## Pre-Remediation Environment, Git Status, Process Inventory & Evidence Integrity

**Document Version:** 1.0.0  
**Classification:** Baseline State Preservation Record  
**Milestone:** 13AB — Assurance Closure Program  
**Parent Milestone:** 13AA — Atlas Assurance Grand Prix  
**Date:** 2026-11-07  
**Working Directory:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

### 1. Repository & Git Status Inspection

The working tree was inspected using standard Git commands. The repository has been initialized with Git (`.git` directory present on branch `main`), but **no initial commit has been made yet**. Therefore, `git rev-parse HEAD` and `git log` return exit code 1 because `HEAD` is not yet associated with an object hash. All workspace files remain untracked in the working tree, and no user files or modifications were reset, overwritten, cleaned, or discarded.

#### Command 1: `git status`
- **Exact Command:** `git status`
- **Working Directory:** `E:\Python\NASA-Spaceapps\Marswalk`
- **Exit Code:** `0`
- **Output:**
  ```text
  On branch main

  No commits yet

  Untracked files:
    (use "git add <file>..." to include in what will be committed)
          .agents/
          .env.example
          .gitignore
          AGENTS.md
          DATA_PROVENANCE_AND_LICENSES.md
          README.md
          THIRD_PARTY_NOTICES.md
          data/
          docs/
          outputs/
          publication/
          pyproject.toml
          requirements-lock.txt
          requirements.txt
          schemas/
          scratch/
          scripts/
          src/
          tests/
          web/

  nothing added to commit but untracked files present (use "git add" to track)
  ```

#### Command 2: `git rev-parse HEAD`
- **Exact Command:** `git rev-parse HEAD`
- **Working Directory:** `E:\Python\NASA-Spaceapps\Marswalk`
- **Exit Code:** `1`
- **Output:**
  ```text
  fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree.
  Use '--' to separate paths from revisions, like this:
  'git <command> [<revision>...] -- [<file>...]'
  HEAD
  ```
- **Finding:** Explains historical exit code 1 during initial Git inspection in Milestone 13AA. In a freshly initialized Git repository before `git commit`, `HEAD` is an unborn branch reference. No commit hash was manufactured.

---

### 2. Python Environment & Dependency Snapshot

- **Operating System:** Windows 11 Home Single Language (Build 10.0.26300, 64-bit)
- **Python Executable:** `E:\Python\NASA-Spaceapps\Marswalk\.venv\Scripts\python.exe`
- **Python Version:** `3.12.4`
- **Package Manager:** `pip 24.0`
- **Test Runner:** `pytest 9.1.1` (plugins: `anyio-4.15.1`)
- **Key Scientific & Geospatial Dependencies:**
  - `numpy 2.5.4`
  - `scipy 1.18.1`
  - `pandas 3.0.6`
  - `rasterio 1.5.2`
  - `affine 3.0.1`
  - `jsonschema 4.26.0` (Draft 2020-12)
  - `streamlit 1.66.0`

---

### 3. Application Process Inventory

At baseline inspection time, the following application processes were active:
- **Atlas HTTP API Server (Daemon):**
  - **PID:** 58720
  - **Command:** `$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe scripts/run_atlas.py --port 3000 --no-browser`
  - **Task ID:** `0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144/task-30874`
  - **Port:** `3000` (`http://127.0.0.1:3000`)
  - **Health Endpoint:** `/api/health` returning HTTP 200 (`online`).

---

### 4. Preservation of 13AA Evidence & SHA-256 Hashes

All Milestone 13AA assurance documents and machine-readable manifests have been preserved. A dedicated immutable backup snapshot was created in `outputs/13aa_baseline_snapshot/`.

#### Evidence Manifest & Log Hashes (SHA-256)
| File | Path | SHA-256 Hash |
| :--- | :--- | :--- |
| **13AA Assurance Manifest** | `outputs/13aa_assurance_manifest.json` | `2E08F2CC0F64BC8D54BBD5C2B70A5E8A92D42F4E954D346B3BFB495C18CB050E` |
| **13AA Baseline Manifest** | `outputs/13aa_baseline_manifest.json` | `8E406A8776C834C962FF59F6C3C1BC61CD5478AAD3FAA47936730E1CFA5EA122` |
| **13AA Preflight Log** | `outputs/13aa_baseline_preflight.log` | `5A01CE15A50B01CD10D29A02D954DF14BB0D248512637421FA92456EB741A910` |
| **13AA Pytest Baseline Log**| `outputs/13aa_baseline_pytest.log` | `C344F084646535186695E868B817C8A56485D1AC270F4C38FB5F2875BED217D5` |

#### Documentation Suite Hashes (SHA-256)
| Document Name | File Path | SHA-256 Hash |
| :--- | :--- | :--- |
| Adversarial Test Catalogue | `docs/13aa-adversarial-test-catalogue.md` | `6BB2982EA2314BA2A218CCA7AF8EE99F7FBD56A18DEB2D5D440815B3DEBC177D` |
| Baseline & Configuration | `docs/13aa-baseline-and-configuration.md` | `EF9A570A7523D8485E858A2974EC4961F13DCBCDA069279D25EE359877F179ED` |
| Master Claim Ledger | `docs/13aa-claim-ledger.md` | `944F378AE92FDF8F58C4D79C9E8A7E476BBEF66FDCC104523FE4033C945C9EC9` |
| End-to-End Mission Validation | `docs/13aa-end-to-end-validation.md` | `306E895EE64B324E33F585F76266D55E5C9A436D2C8727A6849884BD23D0D394` |
| Final Assurance Report | `docs/13aa-final-assurance-report.md` | `DDF42708B2338DB23638A6ACE586C32420808B68CEBE8D540A3479A098E64A57` |
| Limitations & Evidence Boundaries | `docs/13aa-limitations-and-evidence-boundaries.md` | `EA469ECC6592DA2F19F7ABAE2CA0879A5E85B5F31317DB07877F92FEBC376FEA` |
| Performance & Reproducibility | `docs/13aa-performance-and-reproducibility.md` | `94791412D4EC10AE146B7B8FB432BEE25B124B5CBE67B0EE5B3F40EBF784B4EB` |
| Physics & Numerical Audit | `docs/13aa-physics-and-numerical-audit.md` | `A6841CCB26A483EC4FEF7013AFA1DC97A13C07AE492801F52902DFCCBE020948` |
| Red Team Defect Findings | `docs/13aa-red-team-findings.md` | `6AB1DBEF1BDDFD6775420E6F4D55AA8EF54DC0C61CF015E77D344BBA3DC45155` |
| Scientific & Statistical Audit | `docs/13aa-scientific-and-statistical-audit.md` | `5CBDCAB679F9209F11EDECF09C3663A7E20E32454645229C29F5C5B173663484` |
| Security & Operational Review | `docs/13aa-security-and-operational-review.md` | `9089EE69D9F6C4C7769AEF93452CD5172C9E4582C9810A14DEEE328AFCF57095` |
| System Architecture Audit | `docs/13aa-system-architecture-audit.md` | `28E4E9DFBF12365BB3021F44F71B77104EEBC365021F1AC6A18C3BFA13EDBE8B` |
| Test Quality & Mutation Report | `docs/13aa-test-quality-and-mutation-report.md` | `F25ED0442649C2D76F11DD9F998D726B386470F1B94BC07360064293BA8D9E83` |

---

### 5. Preservation Guarantee

No historical artifacts from Milestones 13A through 13AA were overwritten, deleted, or degraded. All remediation work in Milestone 13AB proceeds non-destructively with strict additive and corrective controls.
