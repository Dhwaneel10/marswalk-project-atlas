# Project MarsWalk 2.0 / Atlas — Evaluator Demonstration Script
**Document ID:** `DOC-MW-M7-DEMO-SCRIPT`  
**Target Audiences:** 3-Minute Competition Pitch | 5-Minute Technical Review Walkthrough  
**URL:** [http://127.0.0.1:3000/](http://127.0.0.1:3000/)  
**Platform:** Ubuntu 22.04 LTS | Python 3.10  

---

## Part 1: The 3-Minute Lightning Competition Pitch

*Target Timing: Exactly 180 seconds. Focus on the core mission problem, authentic NASA data, science trade-offs, and autonomous resilience.*

### [00:00 – 00:30] The Hook & The Problem
- **Presenter Action:** Open [http://127.0.0.1:3000/](http://127.0.0.1:3000/). The landing page appears.
- **Presenter Script:**
  > *"Welcome to MarsWalk 2.0, Project Atlas. Navigating a robotic rover on Mars is not like driving on Earth. Commands take up to 22 minutes to travel across interplanetary space. Meanwhile, rovers face steep crater walls, seasonal dust storms that starve solar panels, and sudden communications blackouts. If a rover bypasses a critical astrobiology site, we waste priceless mission opportunities; if it blindly drives into steep terrain, the vehicle tips over and the mission is lost."*

### [00:30 – 01:15] The Solution & Real Planetary Data
- **Presenter Action:** Point to the epistemological truth badges on the hero stage, then click **`★ EVALUATOR TOUR →`**. The 3D Jezero Crater surface loads, and the Golden Path HUD expands.
- **Presenter Script:**
  > *"MarsWalk solves this by putting real NASA and USGS planetary science directly into the routing loop. We don't use procedural or synthetic terrain. We load USGS 20-meter CTX topography and 1-meter HiRISE micro-hazard digital elevation models of Jezero Crater, alongside 33.2 kilometers of real Perseverance rover locations from the NASA Planetary Data System."*

### [01:15 – 02:00] The Core Science Trade-Off (Step 5)
- **Presenter Action:** In the Golden Path HUD, click Step **`5. SCIENCE`**, then click **`▶ EXECUTE STEP ACTION`**. The side-by-side trade table renders.
- **Presenter Script:**
  > *"Here is the core of our routing engine. We command a traverse from the Three Forks sample depot to the Delta Scarp Rim. Route A takes the direct path: 2.3 kilometers, but it bypasses our science targets and scores zero points. Route B intelligently detours to Wildcat Ridge—where Perseverance discovered organic molecules—and Kodiak Butte. It adds 3.1 kilometers and 907 watt-hours of energy, but delivers 160 points of verified astrobiological yield. MarsWalk gives mission planners mathematically defensible trade-offs."*

### [02:00 – 02:45] Autonomous Resilience & DTN Custody (Step 6 & 7)
- **Presenter Action:** Click Step **`6. DETOUR`**, then click **`▶ EXECUTE STEP ACTION`**. The "When Mars Goes Dark" scenario replay launches. Click Step **`7. MERKLE`** and execute.
- **Presenter Script:**
  > *"When disaster strikes—like a regional dust storm cutting solar output by 71% and a rockfall blocking the primary corridor during a 4-hour blackout—MarsWalk doesn't panic. The rover enters an autonomous safe hold, plans a lateral ridge detour, and climbs out of radio shadow to restore its orbiter link. Under RFC 9171 Delay-Tolerant Networking, not a single byte of telemetry is lost, and the entire mission state is cryptographically proven by a bit-exact SHA-256 Merkle root."*

### [02:45 – 03:00] The Conclusion
- **Presenter Script:**
  > *"MarsWalk 2.0 proves that authentic planetary data, multi-objective optimization, and autonomous resilience can protect our explorers and maximize discovery on Mars. Thank you."*

---

## Part 2: The 5-Minute Technical Review Walkthrough

*Target Timing: 300 seconds. A step-by-step technical walkthrough for judges conducting an in-depth rubric assessment.*

### Step 1: Open the Interactive Evaluator Tour [00:00 – 00:45]
1. Load [http://127.0.0.1:3000/](http://127.0.0.1:3000/).
2. Click the yellow **`★ EVALUATOR TOUR`** button in the header of the Five-Pillar Operations Deck.
3. Observe Step 1: **Authentic Mars Data Provenance & Geodesy**.
4. Click `[▶ EXECUTE STEP ACTION]`.
5. **Expected Output:**
   - CTX 20m DEM: `USGS_CTX_DEM_PROCESSED_20M` (250×250 px, SHA-256 verified).
   - HiRISE 1m DTM: `USGS_TRN_HIRISE_1M` (600×600 px Hawksbill Gap window).
   - Provenance status: `8/8 INTEGRITY VERIFIED`.

### Step 2: Multi-Resolution Slope Inspection [00:45 – 01:30]
1. Click Step **`2. TERRAIN`** in the stepper ribbon.
2. Click `[▶ EXECUTE STEP ACTION]`.
3. **Expected Output:**
   - 3D camera moves to Hawksbill Gap (`row: 136, col: 91`).
   - Comparison table renders:
     - Hawksbill Gap: 1.0 m HiRISE resolution, elevation $-2,554.7\,\text{m}$, Horn slope $9.4^\circ$ (`CAUTION (ASCENT)`).
     - Crater Floor: 20.0 m CTX resolution, elevation $-2,480.5\,\text{m}$, Horn slope $3.0^\circ$ (`NOMINAL FLAT`).

### Step 3: Ground Truth Rover History [01:30 – 02:15]
1. Click Step **`3. ROVER`** in the stepper ribbon.
2. Click `[▶ EXECUTE STEP ACTION]`.
3. **Expected Output:**
   - 3D camera focuses on Three Forks Depot cache (`row: 146, col: 77`).
   - Summary: 33.2 km archived traverse across 1,896 sols.
   - Inventory table displays the 10 sealed titanium tubes (including Malay #241 and Bearwallow #239).

### Step 4: Authentic Atmospheric Physics [02:15 – 03:00]
1. Click Step **`4. MEDA`** in the stepper ribbon.
2. Click `[▶ EXECUTE STEP ACTION]`.
3. **Expected Output:**
   - Injected atmospheric parameters: $\tau = 2.45$, $T_{\text{air}} = -35.0^\circ\text{C}$, $P = 725.0\,\text{Pa}$, Wind $18.4\,\text{m/s}$.
   - Subsystem impact: Solar output drops to $50.4\,\text{W}$ ($-94.4\%$ loss for severe storm), battery heater load is $27.0\,\text{W}$.
   - Operational assessment: `DEGRADED_OPERATIONS_DUST_STORM`.

### Step 5: Multi-Objective A* Trade Study [03:00 – 03:45]
1. Click Step **`5. SCIENCE`** in the stepper ribbon.
2. Click `[▶ EXECUTE STEP ACTION]`.
3. **Expected Output:**
   - Route A (Direct): $2,309.7\,\text{m}$, $659.9\,\text{Wh}$, $1.28\,\text{h}$, **$0\,\text{pts}$ yield** (bypasses targets $>30\,\text{m}$).
   - Route B (Science-Priority): $5,406.2\,\text{m}$, $1,567.1\,\text{Wh}$, $3.00\,\text{h}$, **$+160\,\text{pts}$ yield** (Wildcat Ridge + Kodiak Butte).
   - Delta: $+3,096.5\,\text{m}$ ($+134.1\%$), $+907.2\,\text{Wh}$ ($+137.5\%$), **$+160\,\text{pts}$ gain**.

### Step 6 & 7: Autonomous Resilience & Merkle Proof [03:45 – 05:00]
1. Click Step **`6. DETOUR`**, click `[▶ EXECUTE STEP ACTION]`.
   - Replay executes: Safe hold commanded at $T+01:45$, lateral ridge detour bypasses blockage, MRO orbiter link restored.
2. Click Step **`7. MERKLE`**, click `[▶ EXECUTE STEP ACTION]`.
   - Merkle root hash: `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`.
   - DTN yield: 100% (6/6 bundles delivered, 0 bytes lost).
   - Qualification badge: `✔ EVALUATOR GOLDEN PATH FULLY VERIFIED`.

---

## Part 3: Fallback & Recovery Procedures

- **If port 3000 is occupied:** Run `./scripts/start_atlas.sh --port 3001` and navigate to `http://127.0.0.1:3001`.
- **If the 3D surface fails to load:** Refresh the page or click `Explore Workstation` on the landing page.
- **If browser is headless:** Execute `.venv/bin/python scripts/audit_golden_path_browser.py` to run the identical sequence over Chrome DevTools Protocol.
