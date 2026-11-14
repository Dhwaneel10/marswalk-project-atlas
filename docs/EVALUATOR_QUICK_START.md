# EVALUATOR QUICK START GUIDE
## Project MarsWalk 2.0 / Atlas — "WHEN MARS GOES DARK"
**Document ID:** `GUIDE-EVALUATOR-QUICKSTART-2026`  
**Target Platform:** Ubuntu 22.04 LTS (x86_64)  
**Demonstration Port:** `3000`  
**Workspace Root:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`

---

## 1. 60-SECOND EVALUATOR OVERVIEW

Project MarsWalk 2.0 (Project Atlas) demonstrates **autonomous planetary rover resilience** during catastrophic environmental disruption in Jezero Crater, Mars.

When a severe regional dust storm drops solar power by $55\%$ and the rover enters a topographic communications blackout behind the Hawksbill Gap crater shoulder, an impassable rockfall blocks the planned ascent channel:
- **Strategy A (Nominal Static Architecture):** Lacks local custody buffering, loses line-of-sight telemetry, pushes into the boulder barrier, experiences drive motor stall ($650\,\text{W}$), rapidly depletes battery reserves ($3{,}400\,\text{Wh}$), and fails with $60\%$ data loss ($2{,}944\,\text{KB}$ lost).
- **Strategy B (MarsWalk 2.0 Adaptive Architecture):** Intercepts data bundles into an RFC 9171 DTN flash buffer ($0\,\text{bytes}$ lost), detects excessive drive resistance, enters an autonomous safe hold ($0\,\text{W}$ drive load), computes a lateral detour ascending Ridge Terrace ($+42.6\,\text{m}$ elevation delta), clears the crater shoulder shadow, restores line-of-sight RF communications, and flushes all scientific discoveries in strict priority order with $100\%$ delivery and bit-exact cryptographic proof.

---

## 2. OPTION 1 — ONE-COMMAND AUTOMATED SHOWCASE

The fastest way to evaluate the entire pipeline from end to end is our unified showcase runner:

```bash
cd /home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission
./scripts/run_showcase.sh 3000
```

### What This Script Does:
1. Verifies the isolated virtual environment (`.venv`).
2. Checks daemon health on port 3000 (auto-starts the server if not already running).
3. Executes the full 7-stage simulation via `POST /api/flagship/when-mars-goes-dark/run`.
4. Queries and prints the side-by-side Strategy Comparison table.
5. Cryptographically verifies the Merkle hash chain (`0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`).
6. Saves timestamped JSON dossiers into `outputs/showcase/`.

---

## 3. OPTION 2 — INTERACTIVE BROWSER WORKSTATION

Open your browser to:
[http://127.0.0.1:3000/](http://127.0.0.1:3000/)

### Step-by-Step Interactive Evaluation:
1. **Navigate to Cockpit:** If not already focused, click **`1. Mission Control`** in the primary navigation header to reveal the Surface Traverse Planning interface.
2. **Execute Full Mission:** Click **`▶ RUN MISSION`** (`#btnFlagshipRunAll`).
   - Observe the 7-stage animated playback across Jezero Crater.
   - Notice the telemetry HUD updating real-time: Sol, elevation, comms status, solar flux, battery charge, optical depth, alarms, and DTN buffer utilization.
   - Watch the Three.js 3D viewport highlight the nominal route (cyan), the rockfall hazard (red sphere), and the lateral Ridge Terrace detour (amber/green).
3. **Inspect Disruption Event:** Click **`DISRUPTION`** (`#btnFlagshipDisruption`).
   - The scrubber jumps directly to Stage 3 (Sol 14.45).
   - Comms status shows `BLOCKED_TERRAIN_OCCLUSION` with red indicators and active RF carrier lost alarms.
4. **Inspect Adaptive Recovery & Custody Drain:** Click **`DETOUR & DTN`** (`#btnFlagshipAdaptive`).
   - The scrubber advances through Stage 6 (Lateral Detour) to Stage 7 (Ridge Relay Delivery).
   - Comms status switches to `RESTORED_128KBPS`.
   - The DTN buffer flushes from $3\,\text{bundles}$ ($2{,}944\,\text{KB}$) down to $0$, and delivered bundles reach $6/6$ ($100\%$).
5. **Inspect Strategy Comparison:** Click **`COMPARE`** (`#btnFlagshipCompare`).
   - Toggles open the side-by-side Strategy Comparison modal showing Strategy A (FAILED_TRAPPED, 40% data preservation) vs Strategy B (COMPLETED_SUCCESS, 100% data preservation, 7,850 Wh battery reserve).
6. **Verify Merkle Proof:** Click **`VERIFY PROOF`** (`#btnFlagshipReplay`).
   - The narrative box immediately confirms bit-exact reconciliation across all 7 stage hashes and displays the verified root hash: `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`.

---

## 4. OPTION 3 — TERMINAL API EVALUATION (`curl`)

Evaluators can directly inspect the backend REST endpoints:

### 1. Trigger Deterministic Simulation Run:
```bash
curl -s -X POST -H "Content-Type: application/json" -d '{}' http://127.0.0.1:3000/api/flagship/when-mars-goes-dark/run | jq '{status, mission_id, root_merkle_hash, snapshots_count}'
```
*Expected Output:*
```json
{
  "status": "QUALIFIED",
  "mission_id": "MISSION-MARS-DARK-001",
  "root_merkle_hash": "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8",
  "snapshots_count": 7
}
```

### 2. Fetch Side-by-Side Comparison:
```bash
curl -s http://127.0.0.1:3000/api/flagship/when-mars-goes-dark/comparison | jq .comparison_metrics
```

### 3. Verify Cryptographic Merkle Replay:
```bash
curl -s http://127.0.0.1:3000/api/flagship/when-mars-goes-dark/replay | jq '{is_valid, verification_message, root_merkle_hash}'
```
*Expected Output:*
```json
{
  "is_valid": true,
  "verification_message": "Merkle root hash matches bit-exact state chain.",
  "root_merkle_hash": "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8"
}
```

### 4. Test Defensive Input Validation (Adversarial):
```bash
curl -s -X POST -H "Content-Type: application/json" -d '{"tau": -2.5}' http://127.0.0.1:3000/api/flagship/when-mars-goes-dark/run | jq
```
*Expected Output: HTTP 400 Bad Request with `ERR_VALIDATION_FAILED`.*

---

## 5. OPTION 4 — AUTOMATED TEST SUITE EXECUTION

To run the automated integration tests:

```bash
cd /home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_when_mars_goes_dark_integration.py -v
```

*Expected Result: 9 passed in ~15 seconds.*

---

## 6. VERIFIED EVIDENCE & VIDEO RECORDING

All evidence generated during automated evaluation is persisted in the repository:
- **Browser Walkthrough Video:** [operator_interface_walkthrough.mp4](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/showcase/operator_interface_walkthrough.mp4) (3.4 MB live browser capture)
- **Flagship Execution JSON:** [flagship_mission_execution.json](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/showcase/flagship_mission_execution.json)
- **Strategy Comparison JSON:** [strategy_comparison.json](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/showcase/strategy_comparison.json)
- **Merkle Proof JSON:** [merkle_verification.json](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/showcase/merkle_verification.json)
