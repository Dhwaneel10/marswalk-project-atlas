# MarsWalk 2.0 — Milestone 9U Baseline Audit Report
## End-to-End Scenario Proof, Decision Pack Integrity & Live Competition Rehearsal

**Auditor:** Principal Software Engineer, Scientific Reproducibility Auditor & Space Apps Demo Lead  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 18, 2026  
**Milestone:** 9U  

---

## 1. Initial Repository State & Verification Ledger

Before any code modifications in Milestone 9U, the repository was independently verified against physical ground truth:

### 1.1 Command Outputs & Diagnostics
- **Git Status:** Uncommitted modifications preserved across `README.md`, `schemas/`, `scripts/`, `src/`, `tests/`, `web/`, and `docs/`. Zero accidental deletions or sibling project mutations.
- **Active Server:** `scripts/run_atlas.py` running in background on `http://127.0.0.1:3000` (PID active, 12 waypoints, Jezero 20m DTM loaded).
- **Pytest Suite:** **277 passed in 87.35 seconds** (100% green, 0 failures, 0 warnings).
- **Preflight Diagnostics:** **12 / 12 passed in 395.3 ms**.
  - All 12 checkpoints green: Server, Assets, Gazetteer (2,061 items), Imagery Registry (9 products), Viking Basemap, Jezero Optical CTX, Jezero 20m DTM, A* Planner, Gauntlet/Recovery Engine, Persistent Workspaces (7 missions, 11 experiments), Briefing Exporter, Tactical Streamlit App.

---

## 2. Code Inspection & Critical Findings

### 2.1 Critical Investigation: Interactive Contingency vs. Baseline Export Identity
**Investigation Question:** Does the actual interactive contingency workflow export its exact selected scenario or merely export a fresh baseline mission?

**Findings:**
1. **Server-Side API (`src/marswalk/api/service.py:1788-1836`):**
   - In `export_decision_pack_api`, if an API consumer provides `mission_input` and `custom_events` (or `events`), but does not precompute and attach `scenario_result` (or `contingency_result`), the endpoint does **not** automatically execute `contingency_simulate_api`.
   - Instead, `scen_res` evaluates to `None`, and `build_canonical_mission_run_bundle` is invoked with `scenario_result=None` and `contingency_input=None`.
   - **Impact:** An API consumer attempting to export a contingency Decision Pack by supplying `mission_input` + `custom_events` receives a **baseline-only** Decision Pack with zero contingency data!
   - **Required Fix:** If `payload` contains `custom_events` or `events` or `contingency`, but `scenario_result` is missing, `export_decision_pack_api` must automatically execute `contingency_simulate_api(payload, terrain, transform, waypoints)` to resolve the true scenario.

2. **Client-Side Export Flow (`web/app.js:3715-3760` & `web/index.html:860-865, 1060-1075`):**
   - Both the Workspace tab export button (`btnExportDecisionPack`) and the Contingency tab export button (`btnExportContingencyDecisionPack`) route to a single untyped function `exportDecisionPack()`.
   - `exportDecisionPack()` blindly falls back:
     ```javascript
     scenario_result: activeContingencyResult || lastGauntletResult || undefined
     ```
   - **Flaw A (Unintended Scenario in Baseline Export):** If a user previously simulated a contingency, switches to the Workspaces tab, and clicks "Export Decision Pack", the old contingency is silently attached to what the user intended to be a baseline mission briefing!
   - **Flaw B (Stale Contingency Export):** If the user changes mission parameters (e.g., changes vehicle mode or moves start point), `isContingencyStale` becomes `true`. Currently `exportDecisionPack` only logs a warning in status, but still packages the stale, mismatched scenario result!
   - **Flaw C (Missing Contingency in Contingency Tab):** If a user clicks `📦 Decision Pack (.zip)` on the Contingency card without having run a simulation, it silently exports a baseline mission without warning.
   - **Required Fix:** Split export into explicit contexts (`export_mode: "contingency"` vs `export_mode: "baseline"` vs `export_mode: "auto"`). Enforce freshness: block export or require recalculation if contingency is stale.

---

### 2.2 Tamper Detection Gap: Input Hash vs. Result Integrity
**Investigation Question:** What does `computation_fingerprint` actually guarantee?

**Findings:**
- `computation_fingerprint` in `src/marswalk/api/contracts.py` computes:
  $$\text{SHA-256}\Big(\text{JSON}\big(\text{terrain\_id}, \text{terrain\_sha}, \text{start}, \text{goal}, \text{stops}, \text{profile}, \text{mode}, \text{constraints}, \text{events}\big)\Big)$$
- **The Guarantee:** `computation_fingerprint` cryptographically guarantees that the **inputs** (terrain raster + mission specifications + disruption definitions) are authentic and unaltered.
- **The Gap:** A malicious actor or corrupted storage could modify `bundle["baseline_route"]["distance_m"]`, tamper with `bundle["baseline_route"]["path_rc"]`, alter `bundle["reachability_and_feasibility"]["is_scenario_reachable"] = true`, or inject fabricated metrics into `comparison_metrics`.
- Because `verify_bundle_integrity` only recomputed the input fingerprint from `mission_input`, it would report:
  `fingerprint_matches: True, is_integrity_valid: True` even if the route coordinates or comparison metrics were completely falsified!
- **Required Fix:**
  - Implement a canonical **Result Digest** (`result_digest` or `execution_digest`) covering the computed outputs (`baseline_route.distance_m`, `baseline_route.path_rc`, `scenario_result.distance_m`, `scenario_result.path_rc`, `is_scenario_reachable`, `delta_distance_m`).
  - Anchor both the `input_fingerprint` AND the `result_digest` inside the canonical bundle so any tampering with either inputs OR computed route results is instantly flagged as `is_integrity_valid: False`.

---

### 2.3 Scenario Replay Fidelity
- In `replay_decision_pack_bundle`, when `bundle` has `contingency_input` with `events`:
  `contingency_simulate_api` is called with `scen_payload["custom_events"] = raw_events`.
- We must verify that `new_scen` reproduces not just the baseline route, but:
  - Exact scenario route coordinates (`rec_scen_path == new_scen_path`).
  - Exact retained and dropped science targets.
  - Feasibility, delta distance ($\le 0.1\text{ m}$), and travel time ($\le 0.1\text{ s}$).
  - When persisting, saves with `lifecycle_state: "reproducible"` under a distinct run ID, leaving all 7 historical missions and 11 historical experiments strictly immutable.

---

## 3. Plan of Execution for Milestone 9U

1. **Phase 2 (Contingency-to-Export Integration):**
   - Update `export_decision_pack_api` to automatically execute `contingency_simulate_api` if `custom_events` are supplied without `scenario_result`.
   - Update `web/app.js` to handle explicit export modes (`contingency` vs `baseline`) and enforce staleness guards.
2. **Phase 3 (Integrity, Replay & Tamper Detection):**
   - Add `compute_bundle_result_digest` in `src/marswalk/api/contracts.py` and register it in `mission-run-bundle.schema.json`.
   - Update `verify_bundle_integrity` in `src/marswalk/api/decision_pack.py` to audit both input fingerprint AND result digest.
   - Verify replay fidelity on compound contingencies (Closed Corridor + Reduced Mobility + Operational Delay).
3. **Phase 4 (Frontend & HTTP Integration Tests):**
   - Write comprehensive integration test suite `tests/test_milestone_9u_integration.py`.
4. **Phase 5 & 6 (Demo Rehearsal & Final Verification):**
   - Author `docs/milestone-9u-demo-script.md`.
   - Author `docs/milestone-9u-report.md`.
   - Re-run full test suite, preflight diagnostics, and verify 100% green.
