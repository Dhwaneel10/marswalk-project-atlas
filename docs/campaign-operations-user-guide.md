# Atlas Mission Operations Control Center (MOCC): User & Operator Guide
**MarsWalk 2.0 / Project Atlas • Milestone 13H**

---

## 1. Launching & Accessing the MOCC

1. Open your web browser to `http://127.0.0.1:3000`.
2. Access the MOCC via one of three entry points:
   - Click the top navigation button **"&#128506; MOCC OPS"** in the main application header.
   - Click the **"&#128506; MOCC Ops"** tab on the right inspector panel (`#tabBtnCampaignOperations`).
   - Navigate directly using URL query parameter: `http://127.0.0.1:3000/?tab=mocc`.

---

## 2. Navigating the Multi-Sol Cockpit

### 2.1 Campaign Overview KPIs
Located at the top of the MOCC panel, this 6-card deck provides instantaneous situational awareness:
- **Total Distance:** Cumulative geodesy surface distance across all planned sorties.
- **Campaign Time:** Total mission time including traverse locomotion, instrument dwells, and relay installations.
- **Science Yield:** Total scientific return evaluated across target priorities.
- **Min Battery SOC:** Minimum predicted battery State of Charge throughout the entire campaign.
- **LOS Comms Coverage:** Line-of-sight visibility percentage back to Octavia E. Butler Base.
- **Decision Gate:** Real-time invariant pass/fail status (`FEASIBLE` or `REQUIRES_REPLANNING`).

### 2.2 Multi-Sol Timeline & Interactive Sol Cards
Each Martian sol is presented as a distinct operational block:
- **Status Tag:** Indicates `NOMINAL`, `APPROVED`, or `EXECUTED`.
- **Activity Bar:** Visually decomposes daily schedule into **Drive** (Cyan), **Science** (Amber), **Relay Deployment** (Emerald), and **Bivouac Rest** (Purple).
- **Selecting a Sol:** Click any Sol card to focus camera and isolate that sol's trajectory in the 3D Mission Theater.

### 2.3 Live Simulated State HUD
Synchronized in real-time with the mission simulation clock:
- **Kinematics:** Displays instantaneous heading ($\theta$), local terrain slope, and ground speed.
- **Battery SOC Gauge:** Dynamic gradient bar indicating real-time cell capacity and reserve threshold ($20\%$).
- **Science Buffer Gauge:** Solid-state storage fill percentage and active downlink transfer rate.
- **RF Comms Link:** Active relay path (Direct or multi-hop via deployed masts) and terrain clearance margin.

---

## 3. Contingency Handling & Adaptive Replanning

When an unforeseen operational disruption occurs (e.g. boulder rockfall or sudden dust storm):
1. Click **"&#9889; Contingency Replan"** or trigger an event via the API.
2. The **Campaign Contingency Replanning & Delta Review** drawer will open.
3. Review the **Disruption Narrative** and examine the **Side-by-Side Delta Comparison Table**:
   - Compare Traverse Distance, Duration, Science Yield, Battery SOC, and Relay counts between Baseline (v1) and Contingency (v2).
4. Click **"&#128640; Approve & Promote Plan"** to commit the alternative into the active flight plan, or **"Revert to Baseline"** to cancel.
5. Export a complete forensic Markdown dossier by clicking **"Export Decision Dossier"**.
