# Atlas Fleet Operations User Guide & Operator Runbook
## Step-by-Step Walkthrough of the Atlas Fleet Control Center

**Interface Tab:** `🚀 FLEET CONTROL` (`#tabFleetControl`)  
**URL Parameter:** `http://127.0.0.1:3000/?tab=fleet`  
**Target Viewports:** $1920 \times 1080$ (Desktop) and $1366 \times 768$ (Tactical Laptop)

---

## 1. Accessing the Fleet Control Center

1. Launch MarsWalk 2.0 / Project Atlas in your modern web browser:
   ```
   http://127.0.0.1:3000/?tab=fleet
   ```
2. Or click the **🚀 FLEET CONTROL** tab button on the main inspector tab bar.
3. The interface immediately switches into wide analytical **cockpit mode**, revealing:
   - Global Fleet Header Deck
   - Five-Card Fleet Overview HUD
   - Action Control Bar
   - Five Interconnected Operational Workbenches (Areas 1–5)

---

## 2. Global Fleet Header & 5-Card HUD

- **Active Fleet Dropdown:** Selects the active exploration fleet (default: `Jezero Western Delta Fleet (4 Rovers)`).
- **Master Status Pill:** Displays real-time operational status (`FLEET NOMINAL` in green or `RECOVERY ACTIVE` in amber).
- **5-Card Telemetry Deck:**
  1. **Active Rovers:** Shows count of operational vehicles (`4 / 4 Units`).
  2. **Fleet Traverse:** Total deconflicted driving distance across all rovers (`18.4 km`).
  3. **Min Battery Margin:** Worst-case battery SOC across the fleet (`36.8% - Rover Alpha`).
  4. **RelayNet Connectivity:** Aggregate communication reachability to the base station (`100.0%`).
  5. **Fleet Science Yield:** Cumulative scientific utility achieved (`2,840 pts`).

---

## 3. Operational Action Bar

- **⚡ Allocate Science:** Triggers distributed task allocation across the 12 Jezero targets using authoritative instrument compatibility.
- **🗺️ Coordinate Routes:** Executes multi-agent terrain-aware A* routing, generates 4D spatiotemporal reservations, and resolves proximity bottlenecks.
- **📅 Synchronize Schedule:** Compiles the parallel multi-sol Gantt schedule across Sols 1–5.
- **🎯 6D Pareto Optimize:** Computes the non-dominated Pareto frontier and displays the 5 configuration champions.
- **🚨 Inject Disturbance (F1–F7):** Jumps to the Counterfactual Disturbance Lab to simulate planetary anomalies.
- **✅ Promote Fleet Plan:** Formally promotes the validated recovery plan to operational status.

---

## 4. Workbench Walkthrough

### Area 1: Four Rover Status Cards Grid
Displays dedicated telemetry cards for:
- **Rover Alpha (Cyan `#38bdf8`):** Contact petrology lead carrying PIXL and SHERLOC.
- **Rover Beta (Emerald `#10b981`):** Subsurface radar surveyor carrying RIMFAX.
- **Rover Gamma (Purple `#a855f7`):** Astrobiology coring specialist carrying SHERLOC and CORING_TOOL.
- **Rover Delta (Amber `#f59e0b`):** Mobile relay and environmental sentinel with a 3.5m mast antenna.

Each card features an active battery gauge, storage utilization bar, assigned targets, and live RelayNet link status.

### Area 2: Distributed Science Task Assignment Board
A table detailing all 12 Jezero targets with assigned rovers, instruments used, dwell times, and status. Clicking **"View Compatibility Rationale"** displays why each rover was assigned or marked ineligible.

### Area 3: Multi-Lane Synchronized Fleet Timeline
Click between **Sol 1** through **Sol 5** tabs to scrub through parallel rover activity lanes:
- Blue blocks: Traverse legs
- Green blocks: Science observations
- Purple blocks: Downlink windows
- Amber blocks: Spatial holds / chokepoint yielding
- Slate blocks: Diurnal recharge and sleep

### Area 4: 6D Pareto Optimization Champions Matrix
Compares the 5 champion profiles across all 6 objective dimensions. Click **"Select"** on any champion to apply that configuration immediately to the active fleet.

### Area 5: Counterfactual Disturbance & Recovery Lab
1. Select a disturbance scenario (e.g. **F1: Rover Inoperability** or **F2: Relay Outage**).
2. Choose the affected rover and onset sol.
3. Click **"Synthesize Fleet Recovery"**.
4. Inspect the **3-Way Comparative Scorecard** comparing Baseline Nominal vs Disturbed Unmitigated vs Autonomous Recovery.
5. In the **Promotion Sign-Off Drawer**, enter an approver callsign and rationale, then click **"Authorize Promotion"** to record the cryptographic SHA-256 fingerprint.

---

## 5. 3D Mission Theater Integration

Switching to the 3D viewport displays:
- Four simultaneous color-coded trajectory ribbons matching rover accents.
- 3D rover location spheres with vertical laser indicator beacons.
- Green/cyan pulsing microwave line-of-sight Fresnel links representing the RelayNet communication mesh.
