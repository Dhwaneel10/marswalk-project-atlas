# DEMONSTRATION SCRIPT & EVALUATOR WALKTHROUGH
## Live Hands-On Tour of MarsWalk 2.0 / Project Atlas

**NASA International Space Apps Challenge 2026**  
**Role:** Evaluator / Mission Flight Controller Walkthrough  
**Expected Duration:** 5–7 Minutes  
**Target URL:** `http://127.0.0.1:3000/`  

---

### Step 1: Launch and Initialization
1. In your terminal, verify the system is running or start it via:
   ```bash
   ./scripts/start_atlas.sh --port 3000
   ```
2. Open your web browser and navigate to `http://127.0.0.1:3000/`.
3. **What to Observe:**
   - The application automatically launches into **Astronaut EVA Mode** as the primary human operational workflow.
   - At the top center of the cockpit, observe the cyan glowing badge: `[ASTRONAUT EVA ACTIVE]`.
   - In the footer and header banner, note the prominent scientific transparency disclosure:  
     `"RESEARCH DECISION-SUPPORT MODEL — NOT AN OPERATIONAL FLIGHT SAFETY CERTIFICATION"`.
   - In the 3D WebGL viewport, the 1-meter USGS HiRISE elevation mesh of Jezero Crater renders with realistic lighting, displaying the Western Fan Delta topography and the landing site.

---

### Step 2: Planning 3 Human EVA Route Options
1. On the left-hand Mission Control sidebar, locate the **Astronaut EVA Parameters** card:
   - Crew member mass: $80\text{ kg}$
   - Suit & Gear mass: $40\text{ kg}$
   - Walking Speed: $0.8\text{ m/s}$
   - Max Slope Cutoff: $20.0^\circ$
   - Target Objective: `Delta Scarp Sample Site`
2. Click the primary action button: **[Plan 3 EVA Routes]**.
3. **What to Observe:**
   - Within 1.5 seconds, the engine computes three distinct, Pareto-optimal traversal options and displays them in the **EVA Route Comparison** panel:
     - **Option 1: Conservative Route:** Strict $15^\circ$ slope limit, lowest cardiovascular exertion, maximum life-support safety margin ($>200\text{ L}$ O2 reserve).
     - **Option 2: Science-Priority Route:** Traverses near geological scarp exposures, visits high-value mineral outcrops, higher metabolic work, acceptable reserve.
     - **Option 3: Time-Efficient Route:** Direct line-of-sight path over moderate terrain, minimal duration, optimized for rapid return.
   - Select the **Science-Priority Route** card.

---

### Step 3: Dual-Track Outbound vs Return Visualization
1. Look at the 3D terrain canvas.
2. **What to Observe:**
   - Notice that the route is rendered as **two distinct, high-contrast tracks**:
     - **Amber / Gold Polyline (`#fbbf24`):** Outbound leg from Habitat Base to the Science Target, elevated at $+5.0\text{ m}$.
     - **Cyan Polyline (`#06b6d4`):** Return leg from the Science Target back to Base, elevated at $+7.5\text{ m}$.
   - The $+2.5\text{ m}$ elevation offset prevents z-fighting and allows you to clearly see that the return path takes an alternate, lower-gradient route around a steep scarp rather than forcing the astronaut to climb back up steep downhill segments.
   - In the route metrics panel, observe the disaggregated statistics:
     - Outbound Distance: $\approx 1,240\text{ m}$ | Outbound Time: $\approx 26\text{ min}$
     - Return Distance: $\approx 1,310\text{ m}$ | Return Time: $\approx 28\text{ min}$
     - Dwell Science Time: $30\text{ min}$

---

### Step 4: Astronaut Visor HUD Telemetry
1. Locate the translucent **Astronaut Visor HUD Overlay** in the upper-right corner of the viewport.
2. **What to Observe:**
   - **Oxygen Gauge:** Shows total oxygen consumed vs. capacity (e.g., `462.1 L / 600.0 L (77%)`).
   - **Metabolic Burn:** Shows total kilocalories burned (e.g., `882.2 kcal`).
   - **Reserve Margin:** Confirms remaining oxygen is safely above the mandatory $20\%$ ($120.0\text{ L}$) reserve threshold.
   - **Heart Rate / Effort Indicator:** Nominal green status indicator.

---

### Step 5: Autonomous Contingency & Dust Storm Resilience
1. In the left sidebar, scroll down to the **Human EVA Contingency Scenarios** panel.
2. Click the button: **[Simulate Dust Storm Encroachment]**.
3. **What to Observe:**
   - The system immediately injects real atmospheric telemetry from the Sol 89 Jezero dust storm event, where optical depth $\tau \ge 3.0$.
   - The contingency state machine transitions:  
     `NOMINAL` $\to$ `CAUTION` $\to$ `RETURN_TO_BASE`.
   - The Visor HUD badge flashes amber/red with advisory guidance:  
     `"CRITICAL ADVISORY: Atmospheric dust opacity exceeds safety limits (tau >= 3.0). Solar visibility deteriorating. Execute immediate Return-to-Base via Escape Corridor B."`
   - The 3D viewport instantly highlights the fastest emergency return route to the Habitat Airlock.

---

### Step 6: Seamless Mode Isolation (Robotic Rover Mode)
1. At the top of the interface, click the mode switch pill: **[Robotic Rover Mode]**.
2. **What to Observe:**
   - The UI cleanly transitions without reloading or clearing data.
   - The active mode badge switches to `[ROVER MISSION ACTIVE]`.
   - The controls switch to rover parameters: wheel slip threshold, mechanical rollover margin, and science instrument payloads (PIXL, SHERLOC, SuperCam).
   - The 3D viewport displays the official *Perseverance* ground-truth traverse track from Sol 0 to Sol 1000+, complete with rock abrasion and sample core locations.
3. Click **[Astronaut EVA Mode]** to switch back, observing that both workflows remain completely isolated, stable, and independent.
