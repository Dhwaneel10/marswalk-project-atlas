# Project Atlas — Milestone 13AA: Red Team Findings & Defect Register
## Centralized Vulnerability, Scientific Claim Corrections & Remediation Audit

**Document Version:** 1.0.0  
**Classification:** Scientific Red Team Findings Register  
**Milestone:** 13AA — Atlas Assurance Grand Prix  
**Date:** 2026-11-07  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

### 1. Severity Classification Framework

- **`BLOCKER`**: Invalidates a major scientific conclusion or renders the platform unsafe for its intended research purpose.
- **`CRITICAL`**: Severe correctness, mathematical instability, or reliability failure requiring code remediation before release.
- **`MAJOR`**: Significant defect, interface inconsistency, or unsupported claim requiring correction or explicit scope restriction.
- **`MINOR`**: Localized defect, warning, or non-critical formatting improvement.

---

### 2. Centralized Findings Register

| Finding ID | Severity | Affected Module | Root Cause | Engineering / Scientific Impact | Remediation Status | Regression Test |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| **`FND-13AA-01`** | **CRITICAL** | `atlas_network_link_model.py` | `calculate_free_space_path_loss` lacked explicit `math.isnan()` guard; in Python 3.12 `math.log10(nan)` returns `nan` without raising. | Silent propagation of `nan` into downstream RF link budget and data rate calculations. | **REPAIRED** (Added explicit `math.isnan()` guard raising `ValueError`). | `test_adversarial_numerical_nan_and_infinity_in_path_loss` |
| **`FND-13AA-02`** | **MAJOR** | `scripts/run_atlas.py` | Network router lacked `/api/planetary-network/overview` endpoint (only `/topology` was registered). | HTTP 404 error when clients queried network overview using consistent REST naming pattern. | **REPAIRED** (Registered `/api/planetary-network/overview` as route alias). | `test_mission_b_communications_under_degradation` & API curl |
| **`FND-13AA-03`** | **MAJOR** | `docs/13m-milestone-report.md` | Single-sol diurnal temperature fit ($52.1\%$ RMSE gain on Sol 10) presented without emphasizing global archive gain ($4.22\%$). | Risk of misleading users into believing global Martian climate prediction improved by $52.1\%$. | **DISCLOSED & RESTRICTED** (Scoped to single-sol diurnal cycle in Claim Ledger). | `CLM-13M-01` in Claim Ledger |
| **`FND-13AA-04`** | **MAJOR** | `atlas_dtn_engine.py` | DTN engine described as "RFC 9171 BPv7 implementation" without full CBOR wire format support. | Unwarranted claim of formal telecommunications standard compliance. | **DISCLOSED & RESTRICTED** (Re-labeled as "BPv7-inspired DTN proxy"). | `CLM-13Y-01` in Claim Ledger |
| **`FND-13AA-05`** | **MINOR** | `atlas_foundry_inspection.py` | Simulated compressive strength metrics could be misconstrued as laboratory geotechnical measurements. | Epistemic confusion between simulation heuristics and physical measurements. | **DISCLOSED & LABELED** (Explicitly labeled as synthetic quality proxies). | `CLM-13Z-02` in Claim Ledger |

---

### 3. Detailed Remediation Evidence

#### Remediation of FND-13AA-01 (Path Loss NaN Guard)
```python
# Before (src/marswalk/core/atlas_network_link_model.py):
if range_m <= 0 or freq_hz <= 0:
    return 0.0
# When range_m is float('nan'), (nan <= 0) evaluates False, math.log10(nan) -> returns nan silently.

# After (Remediated):
if math.isnan(range_m) or math.isnan(freq_hz):
    raise ValueError(f"Range ({range_m}) and frequency ({freq_hz}) cannot be NaN")
if range_m <= 0 or freq_hz <= 0:
    return 0.0
```
Verified via [`tests/test_milestone_13aa_adversarial.py`](file:///E:/Python/NASA-Spaceapps\Marswalk\tests\test_milestone_13aa_adversarial.py).
All 20 tests in [`tests/test_milestone_13y_planetary_network.py`](file:///E:/Python/NASA-Spaceapps\Marswalk\tests\test_milestone_13y_planetary_network.py) re-tested and passed.
