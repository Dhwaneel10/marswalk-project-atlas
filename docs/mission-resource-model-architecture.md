# Atlas Mission Resource Intelligence Subsystem: Architecture & Engineering Design

## 1. Executive Summary

The **Atlas Mission Resource Intelligence Subsystem** elevates MarsWalk 2.0 / Project Atlas from geometric route and communications co-design into a resource-constrained, multi-subsystem mission feasibility Digital Twin. 

Traverse planning in extraterrestrial exploration environments cannot treat paths as simple geometric curves across elevation fields. A rover traverse may be topographically feasible and maintain direct line-of-sight visibility with high-gain relay towers, yet remain operationally unviable if cumulative mobility work, instrument thermal pre-heating, and radio-frequency transmission deplete the onboard energy storage below safety thresholds.

The Resource Intelligence Subsystem models the coupled interplay of terramechanical rolling resistance, Martian gravitational potential work, subsystem electrical avionics loads, high-power science dwell phases, and telecommunication link transmission costs along authentic USGS Jezero Crater Digital Terrain Models (DTM).

---

## 2. Architectural Decomposition

```
+----------------------------------------------------------------------------------------------------+
|                                    PROJECT ATLAS DIGITAL TWIN                                      |
|                                                                                                    |
|  +---------------------------+     +-------------------------------+     +----------------------+  |
|  |   USGS CTX 20m Jezero     |     |   Line-of-Sight Geometric     |     |  Science Objectives  |  |
|  |   Bilinear Terrain DTM    |     |   Raycaster & Relay Graph     |     |  & Waypoints Model   |  |
|  +-------------+-------------+     +---------------+---------------+     +----------+-----------+  |
|                |                                   |                                |              |
|                +-----------------+                 |                 +--------------+              |
|                                  |                 |                 |                             |
|                                  v                 v                 v                             |
|                    +---------------------------------------------------------------+               |
|                    |             Coupled Joint Co-Design Optimization             |               |
|                    |     (Distance × Blackout Duration × Relay Cost × Energy)      |               |
|                    +-------------------------------+-------------------------------+               |
+----------------------------------------------------|-----------------------------------------------+
                                                     |
                                                     v
+----------------------------------------------------------------------------------------------------+
|                         ATLAS MISSION RESOURCE INTELLIGENCE ENGINE                                 |
|                                                                                                    |
|  +----------------------------------+             +---------------------------------------------+  |
|  |     Terramechanical Mobility     |             |       Subsystem Electrical Budgeting        |  |
|  |  W_m = W_r + max(0, W_g)         |             |  P_total = P_base + P_inst + P_tx + P_rx    |  |
|  |  Descent Non-Regen Physics       |             |  Science Dwell & Mast Deployment Timings    |  |
|  +-----------------+----------------+             +----------------------+----------------------+  |
|                    |                                                     |                         |
|                    +----------------------+------------------------------+                         |
|                                           |                                                        |
|                                           v                                                        |
|                    +-----------------------------------------------+                               |
|                    |           Mission Resource Ledger             |                               |
|                    |  - Chronological Timeline Event Stream        |                               |
|                    |  - Cumulative Joules & Watt-Hours Tracking    |                               |
|                    |  - Battery SOC & Usable Reserve Margins       |                               |
|                    |  - Energy Conservation Audit (Tolerance 1e-4) |                               |
|                    +----------------------+------------------------+                               |
|                                           |                                                        |
|                    +----------------------+------------------------+                               |
|                    |                                               |                               |
|                    v                                               v                               |
|  +------------------------------------+  +------------------------------------------------------+  |
|  |  7-State Feasibility Classifier   |  |        Deterministic Sensitivity Sweeper             |  |
|  |  - FEASIBLE_WITHIN_CONFIGURED      |  |  - Mass, Crr, Speed, Efficiency, Base Load, Battery  |  |
|  |  - FEASIBLE_WITH_LOW_RESERVE       |  |  - Dimensionless Elasticity Rankings                 |  |
|  |  - CRITICAL_ENERGY_VIOLATION       |  |  - Scientific Non-Probabilistic Notice               |  |
|  +------------------------------------+  +------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Subsystem Components & Responsibilities

### 3.1. Terramechanical Mobility Engine (`src/marswalk/core/mission_resource_model.py`)
Computes mechanical work for each discrete step along the Jezero 20m grid.
- **Rolling Resistance Work ($W_r$):** Models compaction and hysteresis losses on Martian regolith:
  $$W_r = m \cdot g_{\text{Mars}} \cdot C_{rr} \cdot \cos(\theta) \cdot d$$
- **Gravitational Work ($W_g$):** Models potential energy change:
  $$W_g = m \cdot g_{\text{Mars}} \cdot \sin(\theta) \cdot d = m \cdot g_{\text{Mars}} \cdot \Delta z$$
- **Descent Non-Regenerative Physics (Conservative Modeling Assumption):** MarsWalk models descent without energy recapture as a conservative configurable modeling assumption (`allow_regenerative_braking: False` by default). Unless verified by rover-specific technical documentation and certified flight telecommand protocols, gravitational descent work ($W_g < 0$) is treated as dissipated torque/heat and does **not** subtract from rolling resistance:
  $$W_{\text{mech}} = W_r + \max(0, W_g)$$
- **Electrical Motor Conversion:**
  $$E_{\text{mobility}} = \frac{W_{\text{mech}}}{\eta_{\text{drivetrain}}}$$

### 3.2. Subsystem Electrical Budgeting
Tracks auxiliary power draws across operational mission modes:
- **Baseline Avionics Load ($P_{\text{base}}$):** Continuous flight computer, thermal heaters, IMU, and survival bus ($110\text{ W}$ nominal).
- **Communication RF Load ($P_{\text{tx}}, P_{\text{rx}}$):** Uplink transmission to relay nodes or direct-to-base ($45\text{ W}$ transmit, $15\text{ W}$ receive).
- **Science Instrument Payload ($P_{\text{inst}}$):** Remote sensing spectrometers, contact abrasion drills, and sample collection mechanisms ($120\text{ W}$ nominal).
- **Relay Ground Stations:** Base station and deployable promontory relays are evaluated under separate solar/battery budgets with standby ($8\text{ W}$) and active multi-hop routing ($35\text{ W}$) loads.

### 3.3. Mission Resource Ledger (`MissionResourceLedger`)
Maintains a sequential, chronological timeline of mission events ($t_0 \to t_{\text{end}}$):
- Segment traverse driving phases
- Science target dwell phases (e.g. 15-minute Raman spectroscopy dwell)
- Relay deployment operations (e.g. 20-minute mast erection and RF alignment)
- Verification of First-Law Energy Conservation:
  $$\Delta E_{\text{battery}} = \sum E_{\text{activities}}$$
  $$\text{Tolerance: } |\Delta E_{\text{battery}} - E_{\text{total}}| \le 10^{-4}\text{ J}$$

### 3.4. 7-State Feasibility State Machine
Every mission candidate is classified into one of seven deterministic operational states:
1. `FEASIBLE_WITHIN_CONFIGURED_BUDGET`: Final battery SOC exceeds configured reserve threshold ($\Delta \text{SOC} \ge \text{Reserve}_{\text{pct}}$) and all activities complete before deadline.
2. `FEASIBLE_WITH_LOW_RESERVE`: Energy remains positive throughout traverse, but final SOC drops into safety reserve margin ($0 < \Delta \text{SOC} < \text{Reserve}_{\text{pct}}$).
3. `CRITICAL_ENERGY_VIOLATION`: Cumulative energy demand strictly exceeds usable battery storage before all activities conclude.
4. `SCHEDULE_TIME_EXHAUSTION`: Traverse and activities exceed allowable operational window despite sufficient energy.
5. `MULTI_CONSTRAINT_VIOLATION`: Both energy capacity and operational time limits are breached.
6. `RELAY_POWER_DEPLETED`: Rover maintains energy, but an essential network relay node exhausts its battery reserve during routing.
7. `INSUFFICIENT_DATA`: Missing terrain or platform parameters prevent deterministic evaluation.

---

## 4. Software Contracts & Data Schemas

### 4.1. Draft 2020-12 Validation Schemas
Two JSON schemas govern API exchanges:
- `schemas/api/v1/joint-mission-resource-evaluation.schema.json`
- `schemas/api/v1/joint-mission-resource-sensitivity.schema.json`

### 4.2. API Endpoints
- `POST /api/joint-mission/resource-evaluate` (aliases: `/api/resource/evaluate`)
- `POST /api/joint-mission/resource-sensitivity` (aliases: `/api/resource/sensitivity`)
- `POST /api/joint-mission/optimize` (extended with coupled resource metrics and Pareto trade-off vectors)

---

## 5. Provenance & Scientific Constraints
- **Terrain Dataset:** USGS CTX 20m DTM (DOI `10.5066/P906QQT8`, SHA-256 `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`).
- **Planetary Coordinate Datum:** IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$, $g_{\text{Mars}} = 3.71\text{ m/s}^2$).
- **Non-Probabilistic Truth Disclosure:** All sensitivity sweeps represent deterministic variation across engineering assumptions and do not constitute empirical failure probabilities.
- **Safety Boundary Notice:** Modeled routes and resource margins are mission simulation tools and are **not certified flight trajectories for human astronauts**.
