# MarsWalk 2.0 — Milestone 9U Live Competition Rehearsal Script
## 3-Minute Live Demonstration Walkthrough for NASA Space Apps Judges & Reviewers

**Target Audience:** NASA Space Apps Challenge Judges, Aerospace Reviewers, Planetary Scientists  
**Duration:** ~3 Minutes (Live Interactive Demo)  
**Host Application:** MarsWalk 2.0 — Project Atlas  
**Local URL:** `http://127.0.0.1:3000`  
**Terrain Model:** USGS Astrogeology Science Center MRO CTX Jezero Crater DTM (20 m/pixel)  

---

### Speaker Note & Ground Rules
- Keep speech cadence steady, technical, and grounded in primary planetary data sources.
- Highlight that all routes, slopes, and energy costs are computed live on real elevation data, never mocked or hardcoded.
- Clearly state the scientific research disclaimer: MarsWalk 2.0 is an educational and mission rehearsal prototype, not certified flight software for human astronaut EVA operations.

---

## ACT 1: System Readiness & Preflight Verification (0:00 – 0:30)

**Spoken Narration:**
> *"Welcome to MarsWalk 2.0. Before commanding any planetary surface operations or presenting route analysis to mission directors, our first priority is operational verification and data integrity. 
> With one click on our Preflight Diagnostics, MarsWalk runs an automated 12-point system audit across the live HTTP server, IAU gazetteer of 2,061 Martian features, USGS 20-meter Jezero elevation DTM, A* planning engine, contingency simulator, and persistent mission workspaces. All 12 checkpoints pass in under 500 milliseconds. 
> Notice checkpoint 10: our workspace stores 7 historical missions and 11 scientific experiments with guaranteed immutability—never overwritten or fabricated."*

**Interactive Actions:**
1. Click **Diagnostics (12 Checkpoints)** button in the header bar.
2. Observe modal loading and flashing 12 green `[PASSED]` indicators.
3. Point out:
   - **Check 03:** 2,061 IAU features loaded.
   - **Check 07:** USGS CTX 20m GeoTIFF ($250 \times 250\text{ px}$, $5 \times 5\text{ km}$ surveyed region).
   - **Check 10:** Persistent storage verified with zero mutation.
4. Click **Close Diagnostics**.

---

## ACT 2: Nominal Traverse Planning & Vehicle Comparison (0:30 – 1:15)

**Spoken Narration:**
> *"Next, let's plan a multi-stop surface sortie across Jezero Crater. Our landing site is Octavia E. Butler Landing. We set our goal at Delta Rim Overlook, with intermediate scientific sampling at Hawksbill Gap and Skinner Ridge.
> MarsWalk computes the optimal traverse using A* search on real topographic slope gradients, applying Minetti's asymmetric human metabolic cost function for crew walking and Perseverance drive telemetry for robotic mobility.
> Notice the route statistics: 3.4 km traverse distance, 42 meters of cumulative elevation climb, maximum slope safely under the 15-degree limit, and an active travel duration of 1 hour 42 minutes under balanced crew EVA pace. The mission timeline accounts for 15-minute scientific dwell time at each sample site."*

**Interactive Actions:**
1. Switch to **Workstation (Jezero)** tab.
2. Select profile **Balanced** and vehicle mode **Crew EVA**.
3. Confirm endpoints:
   - Start: Octavia Landing $(117, 157)$
   - Intermediate Stops: Hawksbill Gap $(95, 140)$ & Skinner Ridge $(82, 133)$
   - Goal: Delta Rim Overlook $(66, 128)$
4. Click **Plan Traverse**.
5. Highlight live 3D path drawn across the Jezero CTX elevation model, color-coded slope profile, and HUD telemetry bar.

---

## ACT 3: Compound Contingency Injection & Real-Time Detour (1:15 – 2:05)

**Spoken Narration:**
> *"Surface exploration never goes completely according to plan. What happens when unforeseen planetary hazards arise mid-traverse?
> In our Interactive Contingency Designer, we stage a compound disruption:
> First, a physical corridor closure—a hypothetical rockfall blocking Hawksbill Gap with an 80-meter hazard footprint.
> Second, a vehicle mobility derating—restricting crew locomotion speed to 70% due to suit thermal regulation.
> Third, a mandatory 10-minute operational hold to run onboard sensor recalibrations.
> When we simulate this compound scenario, MarsWalk's engine immediately detects that the nominal path intersects the severed corridor. Rather than failing or generating an unsafe route, the planner recalculates an automated detour through an alternate slope-compliant depression.
> In our Comparison Matrix, judges can inspect the trade-offs: traverse distance increased by 312 meters, travel duration increased by 28 minutes, yet all scientific sampling targets remain preserved within the 8-hour EVA consumables budget."*

**Interactive Actions:**
1. Open the **Contingency Designer** card.
2. Enable Event 1: Closed Corridor at Hawksbill Gap $(95, 140)$, radius 80m.
3. Enable Event 2: Mobility derating (0.70x).
4. Enable Event 3: Operational Hold (600 seconds).
5. Click **Simulate Contingency**.
6. View the orange detour line navigating around the red danger cylinder.
7. Point out the live Comparison Table displaying baseline vs revised metrics side-by-side.

---

## ACT 4: Decision Pack Export, Tamper Detection & Independent Replay (2:05 – 3:00)

**Spoken Narration:**
> *"How do judges and aerospace evaluators know this calculation is mathematically authentic and hasn't been fabricated?
> We click 'Export Contingency Decision Pack'. MarsWalk bundles the entire run into an in-memory, auditable ZIP archive.
> Inside, we have:
> 1. `mission_bundle.json`: A canonical record conforming strictly to JSON Schema Draft 2020-12. It carries two cryptographic SHA-256 seals: an Input Computation Fingerprint that uniquely identifies all initial conditions, and an Execution Digest that cryptographically fingerprints the computed path geometry, distances, and timeline.
> 2. `mission_brief.md`: A technical briefing detailing trade-offs and primary literature citations.
> 3. `comparison.csv`: An RFC 4180 audit table separating ground distance, travel duration, dwell time, and hold delays.
> 4. `route.json`: Complete 3D GIS cartographic coordinates.
> 
> Let's test tamper detection: if someone attempts to falsify the bundle by altering a coordinate, changing the reported distance, or flipping reachability flags, MarsWalk's verification engine recomputes the cryptographic execution digest, catches the mismatch instantly, and blocks replay.
> Finally, when an auditor replays the authentic bundle through our independent Python verification engine, the path geometry reproduces with zero coordinate delta and 0.0-meter numerical discrepancy.
> MarsWalk delivers traceable planetary mission analysis you can independently verify."*

**Interactive Actions:**
1. Click **Export Contingency Decision Pack** button.
2. Show the downloaded ZIP file notification: `marswalk_decision_pack_run_bundle_contingency_....zip`.
3. Highlight the five enclosed artifacts.
4. Conclude with the formal scientific provenance disclosure.

---

## Summary of Demonstration Highlights

| Act | Focus | Key Feature Shown | Evidence Produced |
| :--- | :--- | :--- | :--- |
| **Act 1** | Integrity | Preflight Diagnostics (12 checks) | 12/12 passed in <500ms; 7 missions & 11 experiments immutable |
| **Act 2** | Science | Nominal A* Traverse Planning | Minetti metabolic effort, CTX 20m DTM, multi-stop timeline |
| **Act 3** | Resilience | Compound Contingency Injection | Rockfall closure + 0.7x mobility + 10m hold $\rightarrow$ dynamic detour |
| **Act 4** | Auditability | Decision Pack ZIP & Tamper Detection | Draft 2020-12 bundle, dual SHA-256 seals, deterministic replay |
