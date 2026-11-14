# ATLAS 13AE: BASELINE & EVIDENCE RECONCILIATION

**Document Identifier:** `ATLAS-DOC-13AE-STAGE-00`  
**Milestone:** 13AE — Propagation Evidence Closure  
**Parent Milestone:** 13AD — Mars Physics Reference Validation  
**Date:** November 2026  
**Status:** Baseline Established & Reconciled  

---

## 1. Baseline Preservation & Environment Record

### 1.1 Host Environment & Dependencies
- **Operating System:** Windows 11 Home Single Language (Build 10.0.26300, 64-bit AMD64)
- **Python Runtime:** Python 3.12.4 (`.venv\Scripts\python.exe`, MSVC v.1940 64-bit)
- **Key Scientific Libraries:**
  - `scipy`: 1.18.1
  - `numpy`: 2.5.4
  - `pytest`: 9.1.1
  - `anyio`: 4.15.1
- **Atlas HTTP Daemon:** Running in background on `http://127.0.0.1:3000` (`task-31274`).
- **Repository Location:** `E:\Python\NASA-Spaceapps\Marswalk`
- **Git State:** Clean working tree with untracked historical milestones and outputs preserved intact.

---

## 2. Reproduction of Historical 13AD Test Evidence

### 2.1 Direct Milestone Test Reproduction
The core physical validation and boundary suites from Milestones 13AD, 13AC, 13AB, and 13Y were re-executed:

```powershell
.\.venv\Scripts\pytest.exe tests/test_milestone_13ad_mars_physics_validation.py `
                          tests/test_milestone_13ac_physics_boundaries.py `
                          tests/test_milestone_13ab_numerical_and_defect_closure.py `
                          tests/test_milestone_13y_planetary_network.py
```

**Execution Result:**
- **Collected:** 61 test items across 4 test suites.
- **Passed:** 61 passed.
- **Failed:** 0 failed.
- **Execution Time:** 1.12 seconds.
- **Exit Code:** `0` (Success).

### 2.2 Preflight Readiness Check
Execution of `scripts/preflight_check.py`:
- **Command:** `.\.venv\Scripts\python.exe scripts/preflight_check.py`
- **Result:** 12/12 checkpoints passed in 505.7 ms.
- **Exit Code:** `0` (Success).

---

## 3. Full-Repository Pytest Audit & Reconciliation

In Milestone 13AD's execution summary, the complete repository pytest run was launched as a background task (`task-31745`).

### 3.1 Root Cause of Missing Full Summary
Inspection of the execution log revealed that `task-31745` stalled at `[ 23%]` progress. Detailed forensic analysis identified the root cause:
- Test `tests/test_milestone_10d_weather_intelligence.py::TestMilestone10dEnvironmentalIntelligence::test_15_api_post_weather_refresh_success` calls `refresh_weather_api({"site_id": "jezero_crater"})` without an active HTTP mock.
- In offline/sandboxed development environments, the underlying `urllib` request attempts to reach the external NASA Planetary Data System (PDS) URL, hanging for the full 15-second OS socket connect timeout before falling back to cached historical data.
- While the test ultimately passes (`20 passed in 17.33s`), running 1,235 tests sequentially causes cumulative socket timeout delays exceeding 2 to 3 minutes, leading to task cancellation before the final report summary was recorded.

### 3.2 Reconciliation Mandate for 13AE
Milestone 13AE will ensure that:
1. Every regression run executes to completion with raw logs preserved.
2. The final test summary (collected, passed, failed, duration, exit code) is captured from a complete, uninterrupted test execution.
3. No aggregate totals are reported from overlapping or partial runs.

---

## 4. Scope of 13AE Scientific & Engineering Remediation

13AE addresses seven specific scientific discrepancies identified in 13AD:
1. **Ångström Exponent Direction:** Auditing the positive exponent $+0.35$ against Lemmon et al. (2014, 2019), Wolff et al. (2009), and modern Mars laser comms literature (arXiv:2504.16955 / Fernández-Rodríguez et al. 2024), where $\alpha \approx -0.082$ or near zero.
2. **RF Dust-Storm Attenuation:** Reconciling the sub-0.5 dB Ka-band claim with NASA/JPL's *Radio Wave Propagation Handbook for Communication on and around Mars* (1.0 to 1.3 dB typical, $\ge 3\text{ dB}$ in severe storms).
3. **Opportunity Scale Height:** Re-interpreting the $19.2\text{ km}$ fit as an observationally informed local non-exponential profile rather than a universal Martian scale height.
4. **Receiver System Noise:** Clarifying antenna-plane vs receiver-plane reference conventions for $T_{\text{sys}} = T_{\text{ant}} + (L-1)T_L + L T_{\text{rx}}$, and treating the 2.7 K CMB as an external sky brightness floor rather than a universal system-temperature minimum.
5. **Antenna Far-Field Standard:** Demarcating the $\max(2D^2/\lambda, 5D, 2\lambda)$ formula as a conservative screening rule rather than a universally mandated IEEE normative law.
6. **Airy Pattern Applicability:** Restricting the $J_1(u)/u$ formulation to its true physical domain (ideal uniformly illuminated circular aperture) with explicit disclosures for real horn/dish blockage and edge tapers.
7. **Complete Empirical Validation:** Executing an uncompromised full-repository test and targeted mutation campaign.
