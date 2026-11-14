# Milestone 13F — Atlas Energy & Resource Intelligence: Architecture Audit
## Resource-Constrained Mars Traverse Planning, Power Budgeting & Mission Feasibility Digital Twin

**Milestone:** 13F — Architecture Audit  
**System:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Three.js r128, Atlas API on port 3000  
**Date:** 2026-10-31  

---

## 1. Executive Summary & Problem Formulation

MarsWalk 2.0 currently couples terrain mobility kinematics (Milestone 11/12), geometric line-of-sight visibility, relay network graph optimization, and dynamic timeline handovers (Milestone 13D/13E). However, mission operational viability on Mars is ultimately bounded by **finite onboard energy, electrical power margins, and mission time envelopes**.

A surface route may be physically traversable with low slope angles and fully covered by geometric line-of-sight relay links, yet **operationally infeasible** because:
1. The combined mechanical rolling work, gravitational lifting work, and avionics base load exceed the rover's usable battery capacity.
2. The mission duration required to traverse the route, conduct in-situ science observations, and deploy intermediate relay towers exceeds the allocated single-Sol exploration window or life-support consumables envelope.
3. The deployed relay network exhausts its field tower battery reserves during prolonged multi-hop transmission.

Milestone 13F introduces **Energy and Resource Intelligence** to transform Atlas into a true mission feasibility Digital Twin, evaluating terrain, communications, energy, and time constraints as a unified decision space.

```
+---------------------------------------------------------------------------------------------------+
|                                  MILESTONE 13F INTEGRATED PIPELINE                                |
+---------------------------------------------------------------------------------------------------+
|  1. Mission Definition (Origin, Goal, Science Waypoints, Sol Budget, Objective Weights)           |
|  2. Mobility Systems (Vehicle Platform, Mass, Speed Envelope, Slope Limits)                       |
|  3. Mars RelayNet Communications (Base Mast, Rover Mast, Relay Budget, Field Tower Heights)       |
|  4. Energy & Resource Configuration (Battery Capacity, Base Load, Instruments, Relays, Crr, Eta)  |
|  5. Autonomous Co-Design Optimization (Traverse Generator + LOS Raycasting + Submodular Sweep)    |
|  6. Energy Ledger & Resource Feasibility Engine (Mechanical Work, Electrical Loads, Schedule)     |
|  7. Resource-Aware Pareto Studio (Multi-Dimensional Scatter Plot, Comparative Scorecard)          |
|  8. 3D Mission Theater Digital Twin (Dynamic Battery Drain, Segment Energy Raycaster, Warnings)   |
|  9. Verifiable Decision Dossier Export (Draft 2020-12 JSON Schema & Markdown Decision Pack)       |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Review of Existing Reusable Subsystems & Metrics

To avoid duplication, the resource model interfaces directly with existing, verified MarsWalk modules:

| Subsystem | Existing Module | Reusable Metrics & Outputs | Integration Role in 13F |
| :--- | :--- | :--- | :--- |
| **Topographic DTM Engine** | `src/marswalk/core/terrain.py` | Bilinear elevation $z(r, c)$, Horn 3x3 slope $\theta(r, c)$, anisotropic spacing $dx=18.9729\text{ m}, dy=20.0\text{ m}$, step distance $d$. | Supplies segment distance and slope angles for rolling resistance $W_r$ and gravitational work $W_g$. |
| **Kinematic Route Planner** | `src/marswalk/core/planner.py` | Waypoint sequence, leg distances, traverse duration $t_{\text{trav}}$, nominal speeds for `crew_eva` and `robotic_rover`. | Supplies kinematic duration for electrical time-based power integration ($E = P \Delta t$). |
| **Geometric LOS Raycasting** | `src/marswalk/core/terrain_visibility.py` | 3D line-of-sight clearance, ray impact points, terrain occlusion coordinates. | Distinguishes direct vs relayed link states affecting comms equipment power draw. |
| **Relay Topology Graph** | `src/marswalk/core/relay_graph.py` | Deployed relay node positions, antenna heights, Tarjan cut vertices, articulation bridges. | Identifies active relay count and backhaul dependencies for network energy budgets. |
| **Submodular Relay Optimizer** | `src/marswalk/core/relay_planner.py` | Screened candidate promontory pool (12 sites), submodular greedy relay selection ($K_{\text{max}}$). | Deploys optimal relay masts whose operational energy must be modeled. |
| **Dynamic Timeline Twin** | `src/marswalk/core/mission_connectivity.py` | Time-indexed checkpoints $(t, r, c)$, comms state (`CONNECTED_DIRECT`, `CONNECTED_RELAYED`, `GAP`), gap intervals. | Drives time-varying comms duty cycles and synchronization with 3D Theater scrubber. |
| **Joint Co-Design Planner** | `src/marswalk/core/joint_mission_planner.py` | Multi-objective A* traverse candidates ($T_1 \dots T_k$), Jaccard deduplication ($< 85\%$), Pareto frontier extraction. | Host optimizer extended with resource metrics and hard feasibility constraints. |
| **Mission Control & Cockpit** | `web/app.js` & `web/index.html` | `#tabJointMissionStudio`, `#jointMissionStudioPanel`, `#paretoScatterCanvas`, `#theaterTimelineScrubber`. | User interface extended with resource configuration, energy ledger, and battery SOC gauges. |

---

## 3. Required Resource & Energy Model Specifications

### 3.1 Rover Mobility Energy Model
For each traverse step $i \to i+1$ across cell distance $d$ and elevation difference $\Delta h = z_{i+1} - z_i$:
1. **Rolling Resistance Work:**
   $$W_{r, i} = C_{rr} \cdot m_{\text{total}} \cdot g_{\text{Mars}} \cdot \cos(\theta_i) \cdot d_i$$
   where $g_{\text{Mars}} = 3.71\text{ m/s}^2$, $m_{\text{total}} = m_{\text{rover}} + m_{\text{payload}}$, and $C_{rr} \in [0.03, 0.20]$ (nominal 0.08 for Martian regolith).
2. **Gravitational Work:**
   $$W_{g, i} = m_{\text{total}} \cdot g_{\text{Mars}} \cdot \Delta h_i$$
3. **Mechanical Work Accounting (No Unmodeled Regeneration):**
   $$W_{m, i} = W_{r, i} + \max(0, W_{g, i})$$
   *Physics Rule:* On descents ($\Delta h < 0$), gravitational potential energy does not reduce mechanical rolling resistance unless an explicit regenerative braking system is modeled. Without regenerative braking, descent requires zero uphill work, but mechanical rolling resistance remains positive ($W_{m, i} = W_{r, i}$).
4. **Electrical Mobility Energy:**
   $$E_{m, i} = \frac{W_{m, i}}{\eta_{\text{drive}}}$$
   where $\eta_{\text{drive}} \in [0.50, 0.90]$ (nominal 0.70 drivetrain efficiency).

### 3.2 Electrical Operating Loads
Total mission time is composed of traverse movement and dwell/activity periods:
1. **Avionics & Base Load:** $P_{\text{base}} \approx 80 - 150\text{ W}$ continuous.
2. **Scientific Instrument Loads:**
   - Standby during traverse: $P_{\text{inst, standby}} \approx 10 - 25\text{ W}$.
   - Active contact science / drilling during dwell: $P_{\text{inst, active}} \approx 90 - 250\text{ W}$ with configurable duty cycle $\delta_{\text{inst}}$.
3. **Communications Power Draw:**
   - Standby / beacon listening: $P_{\text{comm, standby}} \approx 15 - 30\text{ W}$.
   - Active high-gain transmission / relay uplink: $P_{\text{comm, active}} \approx 45 - 120\text{ W}$.

### 3.3 Communications Infrastructure Energy (Mars RelayNet)
Each deployed surface relay mast consumes:
$$E_{\text{relay}, j} = P_{\text{relay, standby}} \cdot t_{\text{standby}} + P_{\text{relay, active}} \cdot t_{\text{active}}$$
where $P_{\text{relay, standby}} \approx 5 - 10\text{ W}$, $P_{\text{relay, active}} \approx 25 - 45\text{ W}$, and each mast possesses a dedicated battery capacity $C_{\text{relay}} \approx 200 - 500\text{ Wh}$ ($0.72 - 1.80\text{ MJ}$).

### 3.4 Unified Energy Ledger & Step-by-Step Conservation
For every segment $i \in \{1 \dots N\}$:
$$E_{\text{remaining}, i} = E_{\text{remaining}, i-1} - \Delta E_{\text{consumed}, i} + \Delta E_{\text{recharged}, i}$$
where:
$$\Delta E_{\text{consumed}, i} = E_{m, i} + (P_{\text{base}} + P_{\text{inst}, i} + P_{\text{comm}, i}) \cdot \Delta t_i$$
Energy remaining must never drop below the configured reserve threshold $E_{\text{reserve}} = \beta_{\text{reserve}} \cdot C_{\text{battery}}$ (e.g. 20% reserve).

### 3.5 Mission Time & Activity Scheduling
Total mission duration:
$$T_{\text{mission}} = \sum_{i=1}^N \frac{d_i}{v_{\text{traverse}}} + \sum_{k=1}^K t_{\text{science}, k} + \sum_{m=1}^M t_{\text{relay\_deploy}, m} + t_{\text{delay}}$$
All duration and energy metrics must be bounded by configurable operational constraints:
- Maximum mission duration: $T_{\text{mission}} \le T_{\text{budget}}$ (e.g., 1 Sol / 88,775s or Sortie EVA / 28,800s).
- Battery reserve margin: $E_{\text{min\_remaining}} \ge E_{\text{reserve}}$.

---

## 4. Proposed Data Structures (`src/marswalk/core/mission_resource_model.py`)

```python
class ResourceFeasibilityClassification(str, Enum):
    FEASIBLE_WITHIN_CONFIGURED_BUDGET = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"
    FEASIBLE_WITH_LOW_RESERVE = "FEASIBLE_WITH_LOW_RESERVE"
    ENERGY_CONSTRAINT_VIOLATION = "ENERGY_CONSTRAINT_VIOLATION"
    TIME_CONSTRAINT_VIOLATION = "TIME_CONSTRAINT_VIOLATION"
    MULTIPLE_CONSTRAINT_VIOLATIONS = "MULTIPLE_CONSTRAINT_VIOLATIONS"
    UNKNOWN_RESOURCE_FEASIBILITY = "UNKNOWN_RESOURCE_FEASIBILITY"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"

@dataclass
class RoverResourceConfig:
    rover_mass_kg: float = 1025.0
    payload_mass_kg: float = 50.0
    usable_battery_capacity_wh: float = 4800.0   # ~17.28 MJ
    reserve_margin_pct: float = 20.0             # 20% reserve threshold
    rolling_resistance_crr: float = 0.08
    drivetrain_efficiency: float = 0.72
    nominal_drive_speed_mps: float = 0.38
    base_electrical_load_w: float = 110.0
    instrument_standby_w: float = 15.0
    instrument_active_w: float = 120.0
    instrument_duty_cycle: float = 0.25
    comm_standby_w: float = 20.0
    comm_active_w: float = 85.0
    science_dwell_s: float = 900.0
    relay_deployment_s: float = 1200.0
    allow_regenerative_braking: bool = False

@dataclass
class RelayResourceConfig:
    usable_battery_capacity_wh: float = 400.0     # ~1.44 MJ
    reserve_margin_pct: float = 15.0
    standby_power_w: float = 8.0
    active_tx_power_w: float = 35.0

@dataclass
class SegmentResourceRecord:
    step_idx: int
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    distance_m: float
    elevation_change_m: float
    slope_deg: float
    duration_s: float
    mechanical_work_j: float
    mobility_energy_j: float
    electrical_load_energy_j: float
    total_energy_consumed_j: float
    energy_remaining_j: float
    battery_soc_pct: float
    is_reserve_violated: bool

@dataclass
class MissionResourceLedger:
    total_distance_m: float
    total_duration_s: float
    total_mobility_energy_j: float
    total_electrical_energy_j: float
    total_mission_energy_j: float
    total_relay_energy_j: float
    peak_instantaneous_power_w: float
    energy_per_km_wh: float
    final_energy_remaining_j: float
    min_energy_remaining_j: float
    final_battery_soc_pct: float
    min_battery_soc_pct: float
    reserve_margin_wh: float
    is_reserve_violated: bool
    is_time_violated: bool
    feasibility_classification: ResourceFeasibilityClassification
    constraint_violations: List[str]
    segment_records: List[SegmentResourceRecord]
    timeline_events: List[Dict[str, Any]]
```

---

## 5. Model Assumptions, Uncertainties & Scientific Disclosures

1. **First-Order Engineering Model:** The mobility equations represent classical mechanical work on rigid/partially yielding terrain. They are not high-fidelity terramechanics simulations (e.g. Bekker-Wong soil plasticity, sinkage slip, wheel lug interaction).
2. **Deterministic Sensitivity vs Probabilistic Truth:** Bounded parameter sweeps evaluate sensitivity to explicit engineering assumptions. They **must never be presented as empirical Martian failure probabilities**.
3. **No Unmodeled Free Energy:** Energy conservation holds strictly. Recharging is only included if a dedicated solar/RTG recharge model is explicitly enabled.
4. **Astronaut Safety Prohibition:** Modeled energy ledgers and travel times are mission-planning decision aids and are **NOT flight-certified life-support envelopes**.

---

## 6. Performance, Scalability & Regression Risks

1. **Computational Complexity:** Segment resource accounting is $O(N)$ with $N \le 500$ cells per candidate traverse, executing in $< 2\text{ ms}$ per route.
2. **Sensitivity Sweeps:** A sensitivity matrix of 5 parameters across 3 perturbation steps ($3^5 = 243$ combinations or One-At-A-Time 15 steps) must execute within $< 80\text{ ms}$.
3. **Zero Data Loss Guarantee:** All co-design records and resource ledgers will be stored under `data/workspaces/joint_missions/` or `data/workspaces/resources/` with non-destructive writes.
4. **Backwards Compatibility:** Existing `JointMissionMetrics` and API endpoints will retain their established fields while adding resource metadata. All existing 805 tests will continue to pass.
