# Milestone 13F Integration Audit & Architectural Specification
## Coupled Mission Resource Ledger, Power Modeling & Multi-Objective Sensitivity Engine

**Project:** NASA Space Apps Challenge — MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Milestone:** 13F (Coupled Mission Resource Ledger)  
**Author:** Agent B (System Integration Specialist)  
**Target Module:** [`src/marswalk/core/mission_resource_model.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/mission_resource_model.py)  
**Audit Date:** 2026-10-31  
**Status:** **ARCHITECTURAL AUDIT COMPLETE — SPECIFICATION RATIFIED**  

---

## 1. Executive Summary

Milestone 13F establishes the **Coupled Mission Resource Ledger, Power Modeling & Multi-Objective Sensitivity Engine** for MarsWalk 2.0 / Project Atlas. 

While Milestone 13E delivered the joint kinematic and topological co-design engine ([`joint_mission_planner.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/joint_mission_planner.py)), it treated time and energy as decoupled proxies: duration was derived purely from terrain impedance cost, and energy was estimated as an uncoupled aggregate without dynamically accounting for:
1. **Dynamic Communications Power Draw:** Transceiver power varying dynamically based on line-of-sight state (Direct-to-Base high-gain X-band vs. low-power UHF Proximity Relay vs. low-power listening during geometric connectivity gaps).
2. **Topographic Locomotion Work:** Drive motor electrical energy (or crew EVA metabolic work) varying as a function of Horn 3x3 facet slope, directional ascent grade, and deceleration/descent efficiency.
3. **Scientific Payload Dwell & Environmental Thermal Loads:** Active instrument power during 15-minute contact observations coupled with ambient thermal maintenance power scaled by in-situ Martian atmospheric temperatures (NASA PDS Mars 2020 MEDA Sol 890 archive).
4. **Active Relay Station Battery Depletion:** Ensuring surface promontory relay nodes do not exhaust their energy reserves while forwarding telemetry for distant traverses.
5. **Multi-Parameter Sensitivity Sweeps:** Determining operational "cliff edges" where small variations in driving speed, battery initial state-of-charge (SoC), payload power, or dust opacity ($\tau$) precipitate mission-critical constraint violations.

This document provides the exhaustive architectural audit across existing system modules, formulates the exact mathematical specifications and Python data structures for [`src/marswalk/core/mission_resource_model.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/mission_resource_model.py), defines API service routing and Draft 2020-12 JSON schemas, and specifies zero-data-loss persistence conventions.

---

## 2. Exhaustive Audit of Existing Touchpoints

```
+---------------------------------------------------------------------------------------------------+
|                                 MARSWALK 2.0 ARCHITECTURAL TOUCHPOINTS                             |
+---------------------------------------------------------------------------------------------------+
|  [terrain.py]              [planner.py]               [mission_connectivity.py]   [relay_graph.py]|
|   Horn Slopes, Elev,       Traverse Path, Dwells,      Checkpoints, Line-of-Sight,  Relay Nodes,  |
|   Step Distances, Costs    Leg Times, Vehicle Modes    Gap Intervals, Handovers     Topology Graph|
|         \                       |                               |                        /        |
|          +----------------------+-------------------------------+-----------------------+         |
|                                 |                                                                 |
|                                 v                                                                 |
|           [src/marswalk/core/joint_mission_planner.py] (Milestone 13E)                            |
|             • JointMissionInput                                                                   |
|             • CandidateTraverse                                                                   |
|             • RelayDeploymentConfig                                                               |
|             • JointMissionMetrics                                                                 |
|             • JointMissionOptimizationResult                                                      |
|                                 |                                                                 |
|                                 v                                                                 |
|           [src/marswalk/core/mission_resource_model.py] (Milestone 13F)                           |
|             • RoverResourceConfig & RelayResourceConfig                                           |
|             • SegmentResourceRecord & MissionActivityEvent                                        |
|             • MissionResourceLedger                                                               |
|             • ResourceSensitivityResult                                                           |
|             • ResourceFeasibilityClassification (7-State Enum)                                    |
|                                 |                                                                 |
|         +-----------------------+-----------------------+                                         |
|         v                                               v                                         |
|  [api/service.py & scripts/run_atlas.py]       [schemas/api/v1/*.json] & [data/workspaces/]       |
|   /api/joint-mission/resource-evaluate          joint-mission-resource-evaluation.schema.json     |
|   /api/joint-mission/resource-sensitivity       joint-mission-resource-sensitivity.schema.json    |
|   Atomic Workspace Persistence                  Zero-data-loss tmp + os.replace()                 |
+---------------------------------------------------------------------------------------------------+
```

### 2.1 Touchpoint 1: `src/marswalk/core/joint_mission_planner.py`
In Milestone 13E, [`joint_mission_planner.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/joint_mission_planner.py) coordinates traverse generation with relay site placement.

#### Backward-Compatible Class Extensions:
1. **`JointMissionInput`**:
   Extend with optional resource configuration dictionaries and flags without altering the existing positional or keyword arguments:
   ```python
   @dataclass
   class JointMissionInput:
       start_rc: Tuple[int, int]
       goal_rc: Tuple[int, int]
       base_station: Dict[str, Any]
       waypoints: List[ScienceWaypoint] = field(default_factory=list)
       mobility_config: Dict[str, Any] = field(default_factory=dict)
       terrain_preference: str = "balanced"
       relay_budget: int = 2
       max_direct_range_m: float = 2500.0
       max_relay_range_m: float = 5000.0
       rover_antenna_h: float = 2.5
       base_antenna_h: float = 10.0
       relay_antenna_h: float = 10.0
       permitted_gap_distance_m: float = 0.0
       permitted_gap_duration_s: float = 0.0
       objective_profile: str = "balanced"
       custom_weights: Optional[Dict[str, float]] = None
       max_route_candidates: int = 5
       # Milestone 13F Non-Breaking Additions:
       rover_resource_config: Optional[Dict[str, Any]] = None
       relay_resource_config: Optional[Dict[str, Any]] = None
       evaluate_resources: bool = True
   ```
2. **`CandidateTraverse`**:
   Preserve all existing attributes (`traverse_id`, `label`, `strategy_description`, `path_rc`, `distance_m`, `elevation_gain_m`, `elevation_loss_m`, `mean_slope_deg`, `max_slope_deg`, `terrain_effort_m`, `estimated_duration_s`, `planner_profile`, `is_valid`).
   Add:
   ```python
   resource_summary: Optional[Dict[str, Any]] = None
   ```
   In `CandidateTraverse.to_dict()`, emit `"resource_summary"` if present, ensuring legacy test assertions comparing standard dictionary keys remain unaffected.
3. **`JointMissionMetrics`**:
   Add energy totals and feasibility fields to the dataclass with safe defaults:
   ```python
   energy_total_wh: float = 0.0
   energy_drive_wh: float = 0.0
   energy_idle_wh: float = 0.0
   energy_comms_wh: float = 0.0
   energy_science_wh: float = 0.0
   final_soc_pct: float = 100.0
   min_soc_pct: float = 100.0
   resource_feasibility: str = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"
   ```
   In `JointMissionMetrics.to_dict()`, store these in a dedicated `"resource_metrics"` dictionary or inline within `"physical_metrics"`. Placing them in a dedicated block keeps physical spatial metrics distinct from electrical/chemical energy metrics.
4. **`JointMissionOptimizationResult`**:
   Add optional sensitivity analysis payload:
   ```python
   resource_sensitivity: Optional[Dict[str, Any]] = None
   ```
   In `to_dict()`, serialize when present.

### 2.2 Touchpoint 2: `src/marswalk/core/terrain.py` & `src/marswalk/core/planner.py`
The kinematic and physical inputs necessary for the resource ledger originate in [`terrain.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/terrain.py) and [`planner.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/planner.py):
1. **Grid Metrics & Directional Step Geodesy:**
   Between adjacent cells $u=(r_1, c_1)$ and $v=(r_2, c_2)$:
   $$\Delta x = (c_2 - c_1) \cdot dx\_ground\_m, \quad \Delta y = (r_2 - r_1) \cdot dy\_ground\_m$$
   $$d(u, v) = \sqrt{\Delta x^2 + \Delta y^2}$$
2. **Topographic Elevation Differentials:**
   $$\Delta z = z(v) - z(u) = \text{elevation}[r_2, c_2] - \text{elevation}[r_1, c_1]$$
   $$\theta_{step} = \arctan\left(\frac{|\Delta z|}{d(u, v)}\right) \cdot \frac{180^\circ}{\pi}$$
3. **Horn 3x3 Gradient Slope:**
   $$\theta_{dest} = \text{slope\_deg}[r_2, c_2], \quad \theta_{eff} = \max(\theta_{dest}, \theta_{step})$$
4. **Waligora Equivalent Flat-Terrain Cost:**
   $$C(u \to v) = d(u, v) \cdot \left[1.0 + \alpha_s \left(\frac{\theta_{eff}}{\theta_{crit}}\right)^2 + \alpha_r \left(\frac{\sigma}{\sigma_0}\right) + \alpha_{up} \max\left(0, \frac{\Delta z}{d(u, v)}\right)\right]$$
   $C(u \to v)$ has physical units of **meters of equivalent flat-terrain effort**.
5. **Leg Durations & Intermediate Science Dwells:**
   Nominal traverse speed converts effort into segment duration:
   $$\Delta t_{traverse} = \frac{C(u \to v)}{v_{nom}}$$
   Intermediate science waypoints ([`ScienceWaypoint`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/planner.py#L27-L40)) introduce discrete dwell intervals ($\Delta t_{dwell} = 900\text{ s}$ nominal) where locomotion power ceases and scientific instruments engage.

### 2.3 Touchpoint 3: `src/marswalk/core/relay_planner.py`, `src/marswalk/core/relay_graph.py` & `src/marswalk/core/mission_connectivity.py`
The dynamic communications environment is supplied by [`mission_connectivity.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/mission_connectivity.py):
1. **Discrete Timeline Checkpoints:**
   Each checkpoint provides:
   - `time_s`: Timestamp relative to mission departure ($t=0$).
   - `rc`: Interpolated rover location $(r, c)$.
   - `communication_state`: One of `CONNECTED_DIRECT`, `CONNECTED_RELAYED`, or `SIMULATED_GEOMETRIC_CONNECTIVITY_GAP`.
   - `active_path`: Ordered list of nodes routing the telemetry (e.g. `["ROVER", "BASE"]`, `["ROVER", "RELAY_02", "BASE"]`, or `[]`).
   - `hop_count`: Number of network hops ($1, 2, \dots$).
   - `primary_link_distance_m`: Slant range from rover to its first direct contact node.
2. **Comms Activity States:**
   - **Direct-to-Base ($1\text{ hop}$):** High transmitter power ($P_{comms\_direct} \approx 35\text{ W}$) to close link budget over $2.5\text{ km}$ distance.
   - **Relayed ($2+\text{ hops}$):** Low-power proximity link ($P_{comms\_relay} \approx 15\text{ W}$) to nearest surface relay station.
   - **Connectivity Gap ($0\text{ hops}$):** Transmitter in standby/search listening mode ($P_{comms\_gap} \approx 5\text{ W}$); science data buffered in onboard solid-state mass memory (SSMM).
3. **Relay Node Activity States:**
   For each surface relay node $r_k$:
   - If $r_k \in \text{active\_path}$, relay $r_k$ draws active retransmission power ($P_{relay\_active} \approx 22\text{ W}$).
   - If $r_k \notin \text{active\_path}$, relay $r_k$ draws quiescent listening power ($P_{relay\_idle} \approx 4\text{ W}$).
4. **Handovers:**
   State transitions between Direct, Relayed, and Gap create discrete `COMMS_HANDOVER` activity events in the mission event stream.

### 2.4 Touchpoint 4: `src/marswalk/api/service.py` & `scripts/run_atlas.py`
1. **API Endpoints:**
   In [`src/marswalk/api/service.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/api/service.py):
   - `joint_mission_resource_evaluate_api(payload, terrain, transform)`: Evaluates a candidate configuration against specified battery and power parameters.
   - `joint_mission_resource_sensitivity_api(payload, terrain, transform)`: Executes 5-parameter sensitivity sweeps.
2. **Server Routing:**
   In [`scripts/run_atlas.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/scripts/run_atlas.py):
   - Add routes under `do_POST`:
     ```python
     elif clean_path == "/api/joint-mission/resource-evaluate":
         result = joint_mission_resource_evaluate_api(payload, self.terrain, self.transform)
     elif clean_path == "/api/joint-mission/resource-sensitivity":
         result = joint_mission_resource_sensitivity_api(payload, self.terrain, self.transform)
     ```
   - Standardize error formatting with `APIError(status_code, message)` ensuring HTTP 400 for malformed parameters and HTTP 500 for calculation exceptions.

### 2.5 Touchpoint 5: Draft 2020-12 Schemas in `schemas/api/v1/`
1. New schema: `schemas/api/v1/joint-mission-resource-evaluation.schema.json`
2. New schema: `schemas/api/v1/joint-mission-resource-sensitivity.schema.json`
3. Backwards-compatible updates to `joint-mission-evaluation.schema.json` and `joint-mission-optimization.schema.json` to accept optional `resource_metrics`, `resource_ledger`, and `resource_sensitivity` objects.

### 2.6 Touchpoint 6: Persistence Conventions in `data/workspaces/`
1. **Directory Structure:**
   Store promoted resource ledgers in `data/workspaces/joint_missions/` or dedicated sub-workspace `data/workspaces/joint_mission_resources/`.
2. **Atomic Write Invariant:**
   Never write directly to destination JSON files. Use temporary files with atomic renaming:
   ```python
   tmp_path = f"{record_path}.tmp"
   with open(tmp_path, "w", encoding="utf-8") as f:
       json.dump(payload, f, indent=2)
   os.replace(tmp_path, record_path)
   ```
3. **Cryptographic Fingerprinting:**
   SHA-256 digest computed from canonical JSON (`sort_keys=True`) of input parameters to guarantee end-to-end data provenance.

---

## 3. Mathematical Foundations of the Coupled Resource Model

### 3.1 Vehicle Locomotion & Drive Power Formulation
For a robotic exploration platform (e.g., Mars 2020 Perseverance analogue, mass $m \approx 1025\text{ kg}$) or suited crew EVA ($m \approx 140\text{ kg}$):

```
                       +-----------------------------------+
                       | Total Segment Power P_total(t)    |
                       +-----------------------------------+
                                         |
     +-----------------+-----------------+-----------------+-----------------+
     |                 |                 |                 |                 |
     v                 v                 v                 v                 v
[P_drive(t)]     [P_idle(t)]       [P_comms(t)]      [P_science(t)]    [P_thermal(t)]
 Mobility &       Avionics &        RF Transmit       Scientific        Heating against
 Horn Slopes      Housekeeping      Link State        Payload Dwells    Martian Cold
```

#### 1. Mechanical Rolling Resistance & Slope Work:
$$\theta = \theta_{eff} \quad (\text{degrees}), \quad \alpha = \theta \cdot \frac{\pi}{180^\circ} \quad (\text{radians})$$
$$F_{roll} = C_{rr} \cdot m \cdot g_{mars} \cdot \cos(\alpha)$$
$$F_{grade} = m \cdot g_{mars} \cdot \sin(\alpha) \quad (\text{for uphill } \Delta z > 0)$$
where:
- $g_{mars} = 3.72076\text{ m/s}^2$ (IAU 2000 Mars surface gravity).
- $C_{rr} \approx 0.08$ (calibrated rolling resistance for loose Martian regolith / sandy terrain).

#### 2. Electrical Drive Motor Power:
For traversal at forward velocity $v$ (m/s):
$$P_{mech} = (F_{roll} + \max(0, F_{grade})) \cdot v$$
$$P_{drive} = P_{drive\_base} + \frac{P_{mech}}{\eta_{mech}} \cdot \left[1.0 + k_{slope} \left(\frac{\theta}{\theta_{crit}}\right)^2\right]$$
where:
- $P_{drive\_base} \approx 120\text{ W}$ (drive actuator quiescent/gearhead excitation power).
- $\eta_{mech} \approx 0.70$ (electromechanical powertrain efficiency).
- $k_{slope} \approx 1.5$ (motor slip and wheel sinkage impedance on slopes).
- On downhill segments ($\Delta z < 0$), gravitational assist reduces drive load, down to a minimum dynamic braking floor:
$$P_{drive\_downhill} = \max(60.0\text{ W}, P_{drive\_base} - 0.5 \cdot |F_{grade}| \cdot v \cdot \eta_{mech})$$

#### 3. Apollo Waligora Metabolic Model (Crew EVA Mode):
When `vehicle_mode == "crew_eva"`, locomotion energy represents suited astronaut metabolic work:
$$P_{metabolic} = P_{base\_metabolic} + C_{waligora} \cdot v \cdot \left[1.0 + 2.0 \left(\frac{\theta}{\theta_{crit}}\right)^2 + 1.5 \max\left(0, \frac{\Delta z}{d}\right)\right]$$
where:
- $P_{base\_metabolic} \approx 184.2\text{ W}$ ($158.4\text{ kcal/h}$) baseline standing/suit movement.
- Specific energy expenditure: $92.0\text{ Wh/km}$ ($331.2\text{ J/m}$) based on Apollo lunar surface traverses (Waligora et al. 1975).
- Alongside human metabolic work, the Portable Life Support System (PLSS) battery draws electrical power for ventilation, water sublimation pumps, bio-telemetry, and helmet lighting ($P_{PLSS\_elec} \approx 85\text{ W}$).

### 3.2 Dynamic Communications Subsystem Power
Communications power $P_{comms}(t)$ switches dynamically according to the active link state identified by RelayNet:
$$P_{comms}(t) = \begin{cases} 
P_{comms\_direct} & \text{if } \text{state} = \text{CONNECTED\_DIRECT} \\ 
P_{comms\_relay} & \text{if } \text{state} = \text{CONNECTED\_RELAYED} \\ 
P_{comms\_gap} & \text{if } \text{state} = \text{SIMULATED\_GEOMETRIC\_CONNECTIVITY\_GAP} 
\end{cases}$$
Default calibrated parameters:
- $P_{comms\_direct} = 35.0\text{ W}$ (X-band TWTA/SSPA Direct-to-Base link).
- $P_{comms\_relay} = 15.0\text{ W}$ (UHF proximity link to promontory relay station).
- $P_{comms\_gap} = 5.0\text{ W}$ (Beacon scan / receiver listening mode).

### 3.3 Environmental Thermal Loads & Solar Generation
1. **Atmospheric Temperature Scaling:**
   From NASA PDS Mars 2020 MEDA archive (Sol 890 tranche):
   Nominal diurnal ambient temperature $T_{amb} \approx -61.7^\circ\text{C}$ ($211.45\text{ K}$).
   Survival setpoint for internal avionics / battery enclosure $T_{target} \approx -20.0^\circ\text{C}$ ($253.15\text{ K}$).
   Thermal heater maintenance power:
   $$P_{thermal} = \max\left(0.0, k_{thermal} \cdot (T_{target} - T_{amb})\right)$$
   With default insulation conductance $k_{thermal} \approx 0.60\text{ W/}^\circ\text{C}$, nominal daytime thermal power is $P_{thermal} \approx 25.0\text{ W}$.
2. **Solar Recharge (if equipped):**
   $$P_{solar} = P_{solar\_nominal} \cdot \cos(\theta_{zenith}) \cdot e^{-\tau / \cos(\theta_{zenith})}$$
   where $\tau = 0.42$ is the authentic MEDA Sol 890 optical depth.

### 3.4 Net Power & Numerical State-of-Charge (SoC) Integration
Across any segment $i$ of duration $\Delta t_i = t_{i} - t_{i-1}$:
$$P_{total, i} = P_{drive, i} + P_{idle, i} + P_{comms, i} + P_{science, i} + P_{thermal, i}$$
$$P_{net, i} = P_{total, i} - P_{solar, i}$$
$$E_{segment, i} = P_{net, i} \cdot \frac{\Delta t_i}{3600.0} \quad (\text{Watt-hours})$$
Battery State-of-Charge updates discretely:
$$\text{SoC}_i = \text{SoC}_{i-1} - \frac{E_{segment, i}}{E_{battery\_capacity}} \times 100\%$$
$$\text{SoC}_{min} = \min_{i} \text{SoC}_i$$

---

## 4. Architectural Specification of `mission_resource_model.py`

### 4.1 Seven-State Feasibility Classification Enum
```python
class ResourceFeasibilityClassification(str, Enum):
    """
    Exhaustive deterministic resource feasibility classification.
    """
    FEASIBLE_WITHIN_CONFIGURED_BUDGET = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"
    FEASIBLE_WITH_LOW_RESERVE = "FEASIBLE_WITH_LOW_RESERVE"
    ENERGY_CONSTRAINT_VIOLATION = "ENERGY_CONSTRAINT_VIOLATION"
    TIME_CONSTRAINT_VIOLATION = "TIME_CONSTRAINT_VIOLATION"
    MULTIPLE_CONSTRAINT_VIOLATIONS = "MULTIPLE_CONSTRAINT_VIOLATIONS"
    UNKNOWN_RESOURCE_FEASIBILITY = "UNKNOWN_RESOURCE_FEASIBILITY"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
```

#### Deterministic Classification Logic:
```
                                 [Validate Inputs]
                                         |
                       +-----------------+-----------------+
                       | Valid                             | Invalid
                       v                                   v
             [Evaluate Simulation]               INVALID_CONFIGURATION
                       |
         +-------------+-------------+
         | Incomplete / Unreachable  | Complete Simulation
         v                           v
UNKNOWN_RESOURCE_FEASIBILITY   [Check Constraints]
                                     |
              +----------------------+----------------------+
              | Both Violated                               | One or None Violated
              v                                             v
MULTIPLE_CONSTRAINT_VIOLATIONS          +-------------------+-------------------+
                                        | Time Exceeded Only| Energy Violated Only
                                        v                   v
                             TIME_CONSTRAINT_VIOLATION  ENERGY_CONSTRAINT_VIOLATION
                                        |
                                        +-------------------+
                                        | Both Satisfied    |
                                        v                   v
                             [Check Min Reserve]            |
                                        |                   |
                     +------------------+------------------+|
                     | SoC_min >= min_reserve              || SoC_min < min_reserve
                     v                                     v
       FEASIBLE_WITHIN_CONFIGURED_BUDGET       FEASIBLE_WITH_LOW_RESERVE
```

1. If $E_{capacity} \le 0$, $v_{nom} \le 0$, or coordinates invalid $\to$ `INVALID_CONFIGURATION`.
2. If route unreachable or no checkpoints $\to$ `UNKNOWN_RESOURCE_FEASIBILITY`.
3. Let $T_{viol} = (t_{total} > t_{limit})$ and $E_{viol} = (\text{SoC}_{min} < \text{SoC}_{critical} \text{ or } \text{final\_energy} > E_{capacity})$.
4. If $T_{viol} \land E_{viol} \to$ `MULTIPLE_CONSTRAINT_VIOLATIONS`.
5. If $E_{viol} \land \neg T_{viol} \to$ `ENERGY_CONSTRAINT_VIOLATION`.
6. If $T_{viol} \land \neg E_{viol} \to$ `TIME_CONSTRAINT_VIOLATION`.
7. If $\neg T_{viol} \land \neg E_{viol}$:
   - If $\text{SoC}_{min} \ge \text{SoC}_{min\_reserve} \to$ `FEASIBLE_WITHIN_CONFIGURED_BUDGET`.
   - Else ($\text{SoC}_{critical} \le \text{SoC}_{min} < \text{SoC}_{min\_reserve}$) $\to$ `FEASIBLE_WITH_LOW_RESERVE`.

### 4.2 Core Data Structures

```python
@dataclass
class RoverResourceConfig:
    """
    Configuration parameters for exploration platform energy and power modeling.
    """
    vehicle_mode: str = "robotic_rover"           # "robotic_rover" or "crew_eva"
    battery_capacity_wh: float = 1200.0           # Nominal battery capacity in Wh
    initial_soc_pct: float = 100.0                # Initial State-of-Charge percentage (0-100)
    min_reserve_pct: float = 20.0                 # Nominal safety reserve buffer
    critical_reserve_pct: float = 10.0            # Emergency cutoff limit
    power_base_idle_w: float = 80.0               # Quiescent avionics/housekeeping power
    power_drive_nominal_w: float = 120.0          # Base motor excitation power on flat terrain
    power_comms_direct_w: float = 35.0            # High-gain Direct-to-Base RF transmitter
    power_comms_relay_w: float = 15.0             # Proximity UHF Relay RF transceiver
    power_comms_idle_w: float = 5.0               # Comms listening/beacon standby power
    power_science_dwell_w: float = 65.0           # Scientific instruments during science dwells
    speed_nominal_mps: float = 0.035              # Base velocity (0.035 m/s for rover; 0.556 m/s for EVA)
    vehicle_mass_kg: float = 1025.0               # Vehicle mass (Perseverance 1025kg; Suited Crew 140kg)
    mechanical_drive_efficiency: float = 0.70     # Electromechanical powertrain efficiency
    slope_penalty_factor: float = 1.5             # Slope impedance coefficient
    operational_time_limit_s: float = 14400.0     # Sol drive limit (14400s rover; 28800s crew EVA)
    solar_generation_nominal_w: float = 0.0       # Solar array peak capacity (0 for RTG/Battery only)
    dust_opacity_tau: float = 0.42                # PDS MEDA Sol 890 optical depth
    ambient_temp_c: float = -61.7                 # PDS MEDA Sol 890 atmospheric temperature
    thermal_heater_power_w: float = 25.0          # Internal electronics heating power

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vehicle_mode": self.vehicle_mode,
            "battery_capacity_wh": round(self.battery_capacity_wh, 1),
            "initial_soc_pct": round(self.initial_soc_pct, 1),
            "min_reserve_pct": round(self.min_reserve_pct, 1),
            "critical_reserve_pct": round(self.critical_reserve_pct, 1),
            "power_base_idle_w": round(self.power_base_idle_w, 1),
            "power_drive_nominal_w": round(self.power_drive_nominal_w, 1),
            "power_comms_direct_w": round(self.power_comms_direct_w, 1),
            "power_comms_relay_w": round(self.power_comms_relay_w, 1),
            "power_comms_idle_w": round(self.power_comms_idle_w, 1),
            "power_science_dwell_w": round(self.power_science_dwell_w, 1),
            "speed_nominal_mps": round(self.speed_nominal_mps, 4),
            "vehicle_mass_kg": round(self.vehicle_mass_kg, 1),
            "mechanical_drive_efficiency": round(self.mechanical_drive_efficiency, 2),
            "operational_time_limit_s": round(self.operational_time_limit_s, 1),
            "solar_generation_nominal_w": round(self.solar_generation_nominal_w, 1),
            "dust_opacity_tau": round(self.dust_opacity_tau, 2),
            "ambient_temp_c": round(self.ambient_temp_c, 1),
            "thermal_heater_power_w": round(self.thermal_heater_power_w, 1),
        }
```

```python
@dataclass
class RelayResourceConfig:
    """
    Configuration parameters for deployed surface relay station energy budget.
    """
    battery_capacity_wh: float = 500.0            # Relay battery capacity in Wh
    initial_soc_pct: float = 100.0                # Initial battery State-of-Charge
    min_reserve_pct: float = 20.0                 # Relay safety reserve buffer
    power_idle_w: float = 4.0                     # Quiescent receiver standby power
    power_tx_forwarding_w: float = 22.0           # Active RF retransmission power
    solar_generation_w: float = 12.0              # Fixed daylight solar recharging capacity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "battery_capacity_wh": round(self.battery_capacity_wh, 1),
            "initial_soc_pct": round(self.initial_soc_pct, 1),
            "min_reserve_pct": round(self.min_reserve_pct, 1),
            "power_idle_w": round(self.power_idle_w, 1),
            "power_tx_forwarding_w": round(self.power_tx_forwarding_w, 1),
            "solar_generation_w": round(self.solar_generation_w, 1),
        }
```

```python
@dataclass
class SegmentResourceRecord:
    """
    Energy expenditure and power telemetry across a single traverse segment.
    """
    segment_index: int
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    start_time_s: float
    end_time_s: float
    duration_s: float
    distance_m: float
    elevation_start_m: float
    elevation_end_m: float
    slope_deg: float
    traversal_effort_m: float
    comm_state: str                               # CONNECTED_DIRECT, CONNECTED_RELAYED, or GAP
    active_path: List[str]
    # Power Breakdown (W)
    p_drive_w: float
    p_idle_w: float
    p_comms_w: float
    p_science_w: float
    p_thermal_w: float
    p_total_w: float
    p_solar_w: float
    p_net_w: float
    # Energy Breakdown (Wh)
    e_drive_wh: float
    e_idle_wh: float
    e_comms_wh: float
    e_science_wh: float
    e_thermal_wh: float
    e_total_wh: float
    e_solar_wh: float
    e_net_wh: float
    # State of Charge (%)
    soc_start_pct: float
    soc_end_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_index": self.segment_index,
            "start_rc": [self.start_rc[0], self.start_rc[1]],
            "end_rc": [self.end_rc[0], self.end_rc[1]],
            "start_time_s": round(self.start_time_s, 1),
            "end_time_s": round(self.end_time_s, 1),
            "duration_s": round(self.duration_s, 1),
            "distance_m": round(self.distance_m, 2),
            "elevation_start_m": round(self.elevation_start_m, 2),
            "elevation_end_m": round(self.elevation_end_m, 2),
            "slope_deg": round(self.slope_deg, 2),
            "traversal_effort_m": round(self.traversal_effort_m, 2),
            "comm_state": self.comm_state,
            "active_path": self.active_path,
            "power_breakdown_w": {
                "drive": round(self.p_drive_w, 1),
                "idle": round(self.p_idle_w, 1),
                "comms": round(self.p_comms_w, 1),
                "science": round(self.p_science_w, 1),
                "thermal": round(self.p_thermal_w, 1),
                "total": round(self.p_total_w, 1),
                "solar": round(self.p_solar_w, 1),
                "net": round(self.p_net_w, 1),
            },
            "energy_breakdown_wh": {
                "drive": round(self.e_drive_wh, 2),
                "idle": round(self.e_idle_wh, 2),
                "comms": round(self.e_comms_wh, 2),
                "science": round(self.e_science_wh, 2),
                "thermal": round(self.e_thermal_wh, 2),
                "total": round(self.e_total_wh, 2),
                "solar": round(self.e_solar_wh, 2),
                "net": round(self.e_net_wh, 2),
            },
            "soc_start_pct": round(self.soc_start_pct, 2),
            "soc_end_pct": round(self.soc_end_pct, 2),
        }
```

```python
@dataclass
class MissionActivityEvent:
    """
    Discrete operational event in the mission energy and resource ledger.
    """
    event_id: str
    timestamp_s: float
    duration_s: float
    event_type: str                               # TRAVERSE_STEP, SCIENCE_DWELL, COMMS_HANDOVER, DEPARTURE, ARRIVAL
    location_rc: Tuple[float, float]
    activity_description: str
    rover_power_w: float
    energy_consumed_wh: float
    rover_soc_pct: float
    active_relay_id: Optional[str] = None
    relay_power_w: Optional[float] = None
    relay_soc_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp_s": round(self.timestamp_s, 1),
            "duration_s": round(self.duration_s, 1),
            "event_type": self.event_type,
            "location_rc": [round(self.location_rc[0], 2), round(self.location_rc[1], 2)],
            "activity_description": self.activity_description,
            "rover_power_w": round(self.rover_power_w, 1),
            "energy_consumed_wh": round(self.energy_consumed_wh, 2),
            "rover_soc_pct": round(self.rover_soc_pct, 2),
            "active_relay_id": self.active_relay_id,
            "relay_power_w": round(self.relay_power_w, 1) if self.relay_power_w is not None else None,
            "relay_soc_pct": round(self.relay_soc_pct, 2) if self.relay_soc_pct is not None else None,
        }
```

```python
@dataclass
class MissionResourceLedger:
    """
    Comprehensive mission resource and power consumption ledger.
    """
    ledger_id: str
    created_at_utc: str
    sha256_fingerprint: str
    vehicle_mode: str
    feasibility_status: str                       # ResourceFeasibilityClassification value
    # Cumulative Energy Totals (Wh)
    total_energy_wh: float
    drive_energy_wh: float
    idle_energy_wh: float
    comms_energy_wh: float
    science_energy_wh: float
    thermal_energy_wh: float
    solar_energy_wh: float
    net_energy_wh: float
    # State-of-Charge Metrics (%)
    initial_soc_pct: float
    final_soc_pct: float
    min_soc_pct: float
    min_soc_timestamp_s: float
    min_soc_location_rc: Tuple[float, float]
    margin_to_critical_pct: float
    # Temporal Metrics (s)
    total_mission_time_s: float
    operational_time_limit_s: float
    remaining_time_margin_s: float
    # Relay Infrastructure State
    relay_resource_summaries: Dict[str, Dict[str, Any]]
    # Chronological Series
    segments: List[SegmentResourceRecord]
    activity_events: List[MissionActivityEvent]
    # Invariants, Warnings & Provenance
    constraint_violations: List[str]
    warnings: List[str]
    model_disclosures: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "created_at_utc": self.created_at_utc,
            "sha256_fingerprint": self.sha256_fingerprint,
            "vehicle_mode": self.vehicle_mode,
            "feasibility_status": self.feasibility_status,
            "energy_summary_wh": {
                "total_energy_wh": round(self.total_energy_wh, 2),
                "drive_energy_wh": round(self.drive_energy_wh, 2),
                "idle_energy_wh": round(self.idle_energy_wh, 2),
                "comms_energy_wh": round(self.comms_energy_wh, 2),
                "science_energy_wh": round(self.science_energy_wh, 2),
                "thermal_energy_wh": round(self.thermal_energy_wh, 2),
                "solar_energy_wh": round(self.solar_energy_wh, 2),
                "net_energy_wh": round(self.net_energy_wh, 2),
            },
            "soc_summary": {
                "initial_soc_pct": round(self.initial_soc_pct, 2),
                "final_soc_pct": round(self.final_soc_pct, 2),
                "min_soc_pct": round(self.min_soc_pct, 2),
                "min_soc_timestamp_s": round(self.min_soc_timestamp_s, 1),
                "min_soc_location_rc": [round(self.min_soc_location_rc[0], 2), round(self.min_soc_location_rc[1], 2)],
                "margin_to_critical_pct": round(self.margin_to_critical_pct, 2),
            },
            "time_summary": {
                "total_mission_time_s": round(self.total_mission_time_s, 1),
                "operational_time_limit_s": round(self.operational_time_limit_s, 1),
                "remaining_time_margin_s": round(self.remaining_time_margin_s, 1),
            },
            "relay_resource_summaries": self.relay_resource_summaries,
            "segments": [s.to_dict() for s in self.segments],
            "activity_events": [e.to_dict() for e in self.activity_events],
            "constraint_violations": self.constraint_violations,
            "warnings": self.warnings,
            "model_disclosures": self.model_disclosures,
        }
```

```python
@dataclass
class ResourceSensitivityResult:
    """
    Multi-dimensional parametric sensitivity analysis result.
    """
    analysis_id: str
    baseline_feasibility: str
    baseline_final_soc_pct: float
    baseline_total_energy_wh: float
    baseline_total_time_s: float
    speed_variations: List[Dict[str, Any]]         # 0.75x, 1.0x, 1.25x, 1.5x nominal velocity
    temperature_sweeps: List[Dict[str, Any]]       # -80C (night), -61.7C (MEDA), -40C (afternoon), -20C (peak noon)
    payload_power_sweeps: List[Dict[str, Any]]     # 0.5x, 1.0x, 1.25x, 1.5x science dwell instrument draw
    initial_soc_sweeps: List[Dict[str, Any]]       # 100%, 90%, 80%, 70%, 60% departure battery level
    solar_tau_sweeps: List[Dict[str, Any]]         # tau = 0.2 (clear), 0.42 (MEDA Sol 890), 0.8 (dust veil), 1.5 (storm)
    critical_cliff_points: Dict[str, Any]          # Exact threshold values precipitating constraint violations
    operational_recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "baseline": {
                "feasibility": self.baseline_feasibility,
                "final_soc_pct": round(self.baseline_final_soc_pct, 2),
                "total_energy_wh": round(self.baseline_total_energy_wh, 2),
                "total_time_s": round(self.baseline_total_time_s, 1),
            },
            "speed_variations": self.speed_variations,
            "temperature_sweeps": self.temperature_sweeps,
            "payload_power_sweeps": self.payload_power_sweeps,
            "initial_soc_sweeps": self.initial_soc_sweeps,
            "solar_tau_sweeps": self.solar_tau_sweeps,
            "critical_cliff_points": self.critical_cliff_points,
            "operational_recommendations": self.operational_recommendations,
        }
```

---

## 5. API Routing, Schema Design & Persistence Specification

### 5.1 API Service Signatures
In [`src/marswalk/api/service.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/api/service.py):

```python
def joint_mission_resource_evaluate_api(
    payload: Dict[str, Any],
    terrain: TerrainGrid,
    transform: Any,
) -> Dict[str, Any]:
    """
    Evaluates detailed electrical, communications, and locomotion energy consumption
    for a specified traverse path and relay deployment configuration.
    """
    ...

def joint_mission_resource_sensitivity_api(
    payload: Dict[str, Any],
    terrain: TerrainGrid,
    transform: Any,
) -> Dict[str, Any]:
    """
    Executes multi-parameter sensitivity sweeps across speed, temperature,
    payload power, departure battery state-of-charge, and atmospheric dust tau.
    """
    ...
```

### 5.2 Server Dispatch (`scripts/run_atlas.py`)
Add routes in `do_POST`:
```python
elif clean_path == "/api/joint-mission/resource-evaluate":
    result = joint_mission_resource_evaluate_api(payload, self.terrain, self.transform)
elif clean_path == "/api/joint-mission/resource-sensitivity":
    result = joint_mission_resource_sensitivity_api(payload, self.terrain, self.transform)
```

### 5.3 Draft 2020-12 JSON Schema Specification

#### Schema 1: `schemas/api/v1/joint-mission-resource-evaluation.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MarsWalk Joint Mission Resource Evaluation Schema",
  "description": "JSON Schema for MarsWalk 2.0 / Project Atlas Milestone 13F Coupled Mission Resource Ledger Evaluation",
  "type": "object",
  "required": [
    "schema_version",
    "ledger_id",
    "sha256_fingerprint",
    "vehicle_mode",
    "feasibility_status",
    "energy_summary_wh",
    "soc_summary",
    "time_summary",
    "segments",
    "activity_events",
    "provenance"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0.0" },
    "ledger_id": { "type": "string" },
    "sha256_fingerprint": { "type": "string" },
    "vehicle_mode": { "type": "string", "enum": ["robotic_rover", "crew_eva"] },
    "feasibility_status": {
      "type": "string",
      "enum": [
        "FEASIBLE_WITHIN_CONFIGURED_BUDGET",
        "FEASIBLE_WITH_LOW_RESERVE",
        "ENERGY_CONSTRAINT_VIOLATION",
        "TIME_CONSTRAINT_VIOLATION",
        "MULTIPLE_CONSTRAINT_VIOLATIONS",
        "UNKNOWN_RESOURCE_FEASIBILITY",
        "INVALID_CONFIGURATION"
      ]
    },
    "energy_summary_wh": {
      "type": "object",
      "required": ["total_energy_wh", "drive_energy_wh", "idle_energy_wh", "comms_energy_wh", "science_energy_wh", "net_energy_wh"],
      "properties": {
        "total_energy_wh": { "type": "number" },
        "drive_energy_wh": { "type": "number" },
        "idle_energy_wh": { "type": "number" },
        "comms_energy_wh": { "type": "number" },
        "science_energy_wh": { "type": "number" },
        "thermal_energy_wh": { "type": "number" },
        "solar_energy_wh": { "type": "number" },
        "net_energy_wh": { "type": "number" }
      }
    },
    "soc_summary": {
      "type": "object",
      "required": ["initial_soc_pct", "final_soc_pct", "min_soc_pct", "margin_to_critical_pct"],
      "properties": {
        "initial_soc_pct": { "type": "number", "minimum": 0, "maximum": 100 },
        "final_soc_pct": { "type": "number" },
        "min_soc_pct": { "type": "number" },
        "min_soc_timestamp_s": { "type": "number" },
        "min_soc_location_rc": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
        "margin_to_critical_pct": { "type": "number" }
      }
    },
    "time_summary": {
      "type": "object",
      "required": ["total_mission_time_s", "operational_time_limit_s", "remaining_time_margin_s"],
      "properties": {
        "total_mission_time_s": { "type": "number" },
        "operational_time_limit_s": { "type": "number" },
        "remaining_time_margin_s": { "type": "number" }
      }
    },
    "relay_resource_summaries": { "type": "object" },
    "segments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["segment_index", "distance_m", "duration_s", "comm_state", "power_breakdown_w", "energy_breakdown_wh", "soc_start_pct", "soc_end_pct"]
      }
    },
    "activity_events": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["event_id", "timestamp_s", "duration_s", "event_type", "rover_power_w", "rover_soc_pct"]
      }
    },
    "constraint_violations": { "type": "array", "items": { "type": "string" } },
    "warnings": { "type": "array", "items": { "type": "string" } },
    "provenance": { "type": "object" }
  }
}
```

#### Schema 2: `schemas/api/v1/joint-mission-resource-sensitivity.schema.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MarsWalk Joint Mission Resource Sensitivity Schema",
  "description": "JSON Schema for MarsWalk 2.0 / Project Atlas Milestone 13F Multi-Parameter Resource Sensitivity Analysis",
  "type": "object",
  "required": [
    "schema_version",
    "analysis_id",
    "baseline",
    "speed_variations",
    "temperature_sweeps",
    "payload_power_sweeps",
    "initial_soc_sweeps",
    "solar_tau_sweeps",
    "critical_cliff_points",
    "operational_recommendations",
    "provenance"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0.0" },
    "analysis_id": { "type": "string" },
    "baseline": {
      "type": "object",
      "required": ["feasibility", "final_soc_pct", "total_energy_wh", "total_time_s"]
    },
    "speed_variations": { "type": "array", "items": { "type": "object" } },
    "temperature_sweeps": { "type": "array", "items": { "type": "object" } },
    "payload_power_sweeps": { "type": "array", "items": { "type": "object" } },
    "initial_soc_sweeps": { "type": "array", "items": { "type": "object" } },
    "solar_tau_sweeps": { "type": "array", "items": { "type": "object" } },
    "critical_cliff_points": { "type": "object" },
    "operational_recommendations": { "type": "array", "items": { "type": "string" } },
    "provenance": { "type": "object" }
  }
}
```

### 5.4 Zero-Data-Loss Workspace Persistence Specification
When a resource ledger is saved or promoted:
1. Target Directory: `data/workspaces/joint_missions/resources/` (created automatically via `os.makedirs(..., exist_ok=True)`).
2. Filename: `resource_ledger_{configuration_id}_{sha256[:12]}.json`.
3. Atomic Renaming Guarantee:
   ```python
   tmp_file = f"{target_path}.tmp"
   with open(tmp_file, "w", encoding="utf-8") as f:
       json.dump(record, f, indent=2)
   os.replace(tmp_file, target_path)
   ```
4. Immutability & Provenance:
   Each persisted file incorporates complete metadata:
   - USGS CTX 20m Jezero DEM DOI: `10.5066/P906QQT8`
   - NASA PDS Mars 2020 MEDA Sol 890 citation
   - Apollo Lunar EVA Waligora metabolic cost model citation (Waligora et al. 1975 / NASA SP-287)
   - Mandatory non-certification disclosure:
     `"Simulated engineering estimates only; NOT certified for flight operations or astronaut life safety."`

---

## 6. Implementation Checklist & Verification Gates for Milestone 13F

| Gate ID | Target Component | Acceptance Criteria |
| :--- | :--- | :--- |
| **G1** | `mission_resource_model.py` | Implementation of `RoverResourceConfig`, `RelayResourceConfig`, `SegmentResourceRecord`, `MissionActivityEvent`, `MissionResourceLedger`, `ResourceSensitivityResult`. |
| **G2** | 7-State Classification Enum | Complete deterministic logic coverage for `FEASIBLE_WITHIN_CONFIGURED_BUDGET`, `FEASIBLE_WITH_LOW_RESERVE`, `ENERGY_CONSTRAINT_VIOLATION`, `TIME_CONSTRAINT_VIOLATION`, `MULTIPLE_CONSTRAINT_VIOLATIONS`, `UNKNOWN_RESOURCE_FEASIBILITY`, `INVALID_CONFIGURATION`. |
| **G3** | Backward Compatibility | `joint_mission_planner.py` compiles cleanly, runs all existing 690 pytest cases with zero regressions, and accepts optional resource configs. |
| **G4** | Dynamic Comms Integration | Comms power draw transitions correctly across Direct (35W), Relayed (15W), and Gap (5W) checkpoints. |
| **G5** | Slope & Waligora Work | Mechanical rolling + grade power accurately reflects Horn 3x3 slopes; Crew EVA mode accurately calculates Apollo Waligora metabolic kilocalories. |
| **G6** | Sensitivity Sweeps | 5-parameter sweeps evaluate speed ($\pm 25\%, \pm 50\%$), temperature (-80°C to -20°C), payload power, departure SoC, and tau. |
| **G7** | Schemas & Validation | Draft 2020-12 validation succeeds for evaluation and sensitivity JSON payloads. |
| **G8** | Persistence Integrity | Atomic `.tmp` write and `os.replace` verified with zero data corruption. |
| **G9** | Non-Certification Disclosures | Disclosures present on all API payloads, documentation, and ledger exports. |

---

## 7. Mandatory Scientific Invariants & Disclosures

1. **Topographic Data Provenance:**
   DTM elevations and slopes derive exclusively from USGS CTX Jezero Crater DTM (`jezero_ready_20m.tif`), DOI `10.5066/P906QQT8`.
2. **Coordinate Reference System:**
   Planar distances and geometries use IAU 2000 Mars Planetocentric Sphere ($R=3,396,190\text{ m}$) with local Equirectangular projection ($\Delta x = \Delta c \cdot 18.973\text{ m}$, $\Delta y = \Delta r \cdot 20.0\text{ m}$).
3. **Atmospheric Environment:**
   Atmospheric temperatures and optical depth $\tau$ derive from NASA PDS Mars 2020 MEDA Sol 890 archival logs; they are distinguished from uncalibrated real-time Martian weather.
4. **Energy Model Limitations:**
   Locomotion and metabolic models are planning and rehearsal heuristics based on terrestrial/lunar analogues (Apollo Waligora 1975) and Mars 2020 surface telemetry.
5. **Non-Certification Disclaimers:**
   No modeled traverse, power ledger, or communications timeline is certified as operationally safe for astronauts or flight execution.
