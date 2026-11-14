# Project MarsWalk — Technical Scenario Specification: "WHEN MARS GOES DARK"
## Environmental Disruption, Delay-Tolerant Networking & Autonomous Recovery

**Scenario ID:** `SCEN_MARS_DARK_COMPOUND`  
**Document ID:** `MARSWALK-SCENARIO-002`  
**Execution Sequence:** 7 Verified Operational Stages  
**Target Environment:** Jezero Crater Western Delta Margin  
**Engine Implementation:** `src/marswalk/core/when_mars_goes_dark.py`  
**API Endpoints:** `GET/POST /api/flagship/when-mars-goes-dark/run`, `GET /api/flagship/when-mars-goes-dark/replay`

---

## 1. Observable Operational Sequence

The demonstrator executes a verified, non-probabilistic operational sequence across 7 distinct stages:

```
[STAGE 1: Nominal Sortie]
       │
       ▼ (Atmospheric Tau Spike from 0.82 to 3.25)
[STAGE 2: Environmental Disruption]
       │
       ▼ (Rover enters scarp depression; line-of-sight obstructed)
[STAGE 3: Topographic Comms Blackout]
       │
       ▼ (SHERLOC Raman discovery stored in local RFC 9171 flash buffer)
[STAGE 4: DTN Data Preservation]
       │
       ▼ (Scarp rockfall blocks primary ascent channel; motor alert triggers safe hold)
[STAGE 5: Corridor Fault & Safe Hold]
       │
       ▼ (Multi-objective A* replanner routes lateral detour around Ridge Terrace)
[STAGE 6: Adaptive Replanning & Causal Rationale]
       │
       ▼ (Rover crests Ridge Terrace at -2,492m; RF link restored; DTN priority flush)
[STAGE 7: Ridge Relay Delivery & Qualification]
```

---

## 2. Event-by-Event Engineering Breakdown

### Event A — Regional Dust Storm (Sol 14.35)
- **Atmospheric Tau ($\tau$):** Increases from $0.82$ (clear sky) to $3.25$ (dense regional storm).
- **Solar Irradiance:** Direct normal solar flux falls from $590.0\,\text{W/m}^2$ to $265.5\,\text{W/m}^2$ ($-55.0\%$).
- **Rover Autonomous Speed:** Reduced by $40\%$ ($0.60\times$ nominal, $0.021\,\text{m/s}$) to mitigate visual odometry feature tracking degradation and wheel slip across unsettled dust deposits.
- **Battery Impact:** Net vehicle energy draws directly from onboard $15\,\text{kWh}$ Li-ion reserve.
- **Telemetry Alarms:** `WARN_ATMOSPHERIC_TAU_HIGH`, `WARN_SOLAR_POWER_DERATED`.

### Event B — Communications Blackout & Topographic Shadow (Sol 14.45)
- **Physical Geometry:** As the rover advances toward Hawksbill Gap (`(136, 91)`), it descends into a local depression at elevation $-2,518\,\text{m}$.
- **Ray-Trace Ray Obstruction:** Bilinear Line-of-Sight analysis between rover antenna ($2.5\,\text{m}$ AGL) and Three Forks Base Station ($15.0\,\text{m}$ AGL) proves the ray vector penetrates the crater shoulder with negative clearance margin ($-4.8\,\text{m}$).
- **Orbital Window:** Mars Reconnaissance Orbiter (MRO) Electra UHF relay pass has completed its 12-minute transit window; next orbiter pass (TGO) is scheduled in $2.8$ hours.
- **Direct Carrier:** Drops to $0\,\text{kbps}$.
- **Telemetry Alarms:** `ALERT_RF_CARRIER_LOST`, `ALERT_LINE_OF_SIGHT_OCCLUDED`.

### Event C — RFC 9171 DTN Data Preservation (Sol 14.55)
- **Data Generation:** During the communications blackout, the rover conducts active science at a fresh rock abrasion outcrop, capturing:
  1. `BUNDLE-SCI-RAMAN-002`: Deep-UV Raman spectroscopy confirming aromatic organic signatures ($768\,\text{KB}$, Class 3 High-Priority Science).
  2. `BUNDLE-ENG-HOUSEKEEP-003`: Battery cell thermal and voltage profiles ($128\,\text{KB}$, Class 4 Routine Engineering).
  3. `BUNDLE-SCI-MASTCAM-004`: $360^{\circ}$ multispectral panorama ($2,048\,\text{KB}$, Class 5 Bulk Science).
- **Custody Asserted:** Standard internet/streaming protocols (TCP/UDP) discard packets when carrier drops. The rover's Delay-Tolerant Networking engine asserts local custody into non-volatile storage.
- **Queue State:** 3 bundles totaling $2,944\,\text{KB}$ stored in priority order. Peak buffer utilization reaches $8.98\%$ of allocated 32 MB flash.
- **Packet Loss:** Exactly **0 bytes lost**.

### Event D — Scarp Rockfall & Safe Hold (Sol 14.65)
- **Disruption Nature:** A simulated localized regolith collapse in Hawksbill Gap deposits a $55\,\text{m}$ boulder field across cells `(134..138, 89..93)`.
- **Detection Mechanism:** Forward Navcam stereo vision identifies impassable terrain roughness and slope gradients exceeding $28.5^{\circ}$ ($>15.0^{\circ}$ safety limit).
- **Traction Motor Feedback:** Motor current spikes upon initial regolith contact, triggering flight rule safety threshold.
- **Autonomous Response:** Rover halts immediately in **Autonomous Safe Hold**. Original mission plan remains immutable in history.
- **Telemetry Alarms:** `FAULT_CORRIDOR_OCCLUSION`, `WARN_TRACTION_MOTOR_OVERTEMP`, `ALERT_SAFE_HOLD_ACTIVE`.

### Event E — Adaptive Replanning & Causal Explanation (Sol 14.75)
- **Replanning Invocation:** Autonomous replanning engine (`replan_adaptive_mission`) is triggered with the rockfall zone marked as impassable (`inf` cost).
- **Alternative Itinerary Evaluation:**
  - Evaluates bypassing Hawksbill Gap and redirecting to Ridge Terrace `(102, 110)` before proceeding to terminal Delta Scarp Overlook `(66, 128)`.
  - Traverse distance: $+214.2\,\text{m}$ lateral detour ($1,518.8\,\text{m}$ vs $1,415.5\,\text{m}$ nominal).
  - Maximum slope along detour: $14.2^{\circ}$ (strictly within $15.0^{\circ}$ flight rule envelope).
- **Forensic Causal Explanation:**
  > *"Route avoids impassable Hawksbill scarp collapse corridor. Navigates low-gradient terrace to Ridge Terrace promontory (elevation $-2,492.0\,\text{m}$, gain $+42.6\,\text{m}$). Detour clears crater terrain shoulder, re-establishing geometric line-of-sight to Three Forks Base Station and enabling high-priority DTN custody drain."*

### Event F — Ridge Relay Clearance & Priority Custody Drain (Sol 14.95)
- **Elevation Gain:** Rover ascends to Ridge Terrace at elevation $-2,492.0\,\text{m}$.
- **Line-of-Sight Restoration:** Ray tracing confirms Line-of-Sight clearance margin of $+18.4\,\text{m}$ over the crater floor. RF carrier re-establishes at $128\,\text{kbps}$.
- **DTN Prioritized Custody Drain:**
  1. `BUNDLE-RECOVERY-CONFIRM-005` (Class 2 Urgent Command Uplink, $96\,\text{KB}$) &rarr; **DELIVERED** (Sol 14.92)
  2. `BUNDLE-SCI-RAMAN-002` (Class 3 High-Priority Science, $768\,\text{KB}$) &rarr; **DELIVERED** (Sol 14.93, SHA-256 match)
  3. `BUNDLE-ENG-HOUSEKEEP-003` (Class 4 Routine Engineering, $128\,\text{KB}$) &rarr; **DELIVERED** (Sol 14.94)
  4. `BUNDLE-SCI-MASTCAM-004` (Class 5 Bulk Science, $2,048\,\text{KB}$) &rarr; **DELIVERED** (Sol 14.95)
- **Final Metrics:** 6 of 6 bundles delivered ($100.0\%$). Zero bundles dropped. Buffer utilization returns to $0.0\%$. Rover reaches terminal goal with $7,850\,\text{Wh}$ battery reserve remaining.

---

## 3. Cryptographic State Chain Audit

Every stage produces a deterministic SHA-256 state snapshot:

| Stage | Title | Sol | Elevation | DTN Delivered | State Hash |
|:---:|:---|:---:|:---:|:---:|:---:|
| 1 | Nominal Traverse | 14.00 | $-2,534.6\,\text{m}$ | 2 | `2dc3fa0842211ea1eb09ad695e1eec5b40cf5081fdb702005a76980ec252f8d3` |
| 2 | Dust Storm Onset | 14.35 | $-2,531.0\,\text{m}$ | 2 | `a9062ee46cba3b2a8f8d9fa89e3ec8b4e7fe34382c448bb9910d652758155bb3` |
| 3 | Comms Blackout | 14.45 | $-2,519.8\,\text{m}$ | 2 | `4e6503c5aeeb2ecb1e2c94382fa3be79b764a7c06eb69d2f2d95b5ca4908ae55` |
| 4 | DTN Custody | 14.55 | $-2,519.8\,\text{m}$ | 2 | `f7b8243be125f69c530e15967ba9e3e7a3eb0f93798cf02bb8efba202cf71cb1` |
| 5 | Corridor Fault & Safe Hold | 14.65 | $-2,519.8\,\text{m}$ | 2 | `3659cf719ca7091217088d8bcfce312b989931b790d79796ffaaee9893d18386` |
| 6 | Adaptive Replanning | 14.75 | $-2,519.8\,\text{m}$ | 2 | `16bc7eb366d2f34ec8df20b0c609ecf385c491295fc8fa573d8a43657b9854ad` |
| 7 | Ridge Relay Delivery | 14.95 | $-2,481.5\,\text{m}$ | 6 | `0fa0a37e193910c0bf1ca5603ca964b4c7490fe4ff917e7fc04c0556e87f6922` |

**Root Merkle Hash:** `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8` (100% Bit-Exact Deterministic Match across executions).
