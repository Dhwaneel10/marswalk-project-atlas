# Milestone 13G — Optimization Architecture Audit (Agent C)
## Science Return & Data Logistics Co-Design System for MarsWalk 2.0 / Project Atlas

**Milestone:** 13G — Science Target Prioritization × Observation Scheduling × Onboard Data Management × Resource-Constrained Mission Optimization  
**Agent Role:** Agent C — Optimization Engine Architect  
**Target File:** `docs/milestone-13g-agent-c-optimization-audit.md`  
**System:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Three.js r128, Atlas API on port 3000  
**Date:** 2026-11-01  

---

## 1. Executive Summary & Problem Formulation

MarsWalk 2.0 currently integrates terrain mobility kinematics (Milestones 11–12), geometric line-of-sight raycasting, surface relay network topology optimization (Milestone 13D), coupled traverse-relay co-design (Milestone 13E), and deterministic rover/relay energy accounting (Milestone 13F).

However, current planning algorithms treat science waypoints as static geographic waypoints that merely impose travel distance and idle electrical dwell time. In real Mars exploration (e.g., NASA Mars 2020 *Perseverance*, Mars Science Laboratory *Curiosity*), planetary surface missions are fundamentally governed by a **tightly coupled co-design trade-off** between:
1. **Scientific Return:** Which targets are visited, which in-situ instruments are operated, and how much scientific knowledge is harvested under configured mission priorities.
2. **Mobility & Energy Budgets:** The mechanical rolling work, gravitational potential changes, and avionics base loads required to navigate across rugged topography.
3. **Onboard Storage & Buffer Dynamics:** Finite flash memory capacity, data product queuing, and storage fill pressure from high-data-rate instruments (multispectral imagers, deep UV Raman spectrometers, subsurface radar).
4. **Data Logistics & Communications Connectivity:** Intermittent line-of-sight visibility to base stations or orbiters, multi-hop relay throughput, protocol overhead, and transmission blackouts.

```
+---------------------------------------------------------------------------------------------------------+
|                         MILESTONE 13G UNIFIED CO-DESIGN OPTIMIZATION SPACE                             |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|       [ Candidate Traverses (T_k) ] <=========> [ Candidate Science Targets (S_i) ]                    |
|                      |                                       |                                          |
|                      v                                       v                                          |
|       [ Mechanical & Electrical Work ]           [ Instrument Observation Schedule ]                    |
|           W_m = W_r + max(0, W_g)                 (Warmup, Exposure, Active Power, Dwell)               |
|                      |                                       |                                          |
|                      +-------------------+-------------------+                                          |
|                                          |                                                              |
|                                          v                                                              |
|                     +-----------------------------------------+                                         |
|                     |     UNIFIED MISSION TIMELINE ENGINE     |                                         |
|                     +-----------------------------------------+                                         |
|                               /                     \                                                   |
|                              v                       v                                                  |
|         [ Dynamic Comm Visibility C(t) ]        [ Data Generation D_gen(t) ]                            |
|         - Direct Line-of-Sight to Base          - Synthetic Instrument Models                           |
|         - Multi-Hop Promontory Relays           - Onboard Storage Ledger S_used(t)                      |
|         - Geometric Terrain Blackouts           - Backlog Accounting D_backlog(t)                       |
|                              \                       /                                                  |
|                               v                     v                                                   |
|                        +-----------------------------------+                                            |
|                        |   SIMULATED DATA TRANSFER ENGINE  |                                            |
|                        |    D_transferred = R_eff * Delta_t|                                            |
|                        +-----------------------------------+                                            |
|                                          |                                                              |
|                                          v                                                              |
|                     +-----------------------------------------+                                         |
|                     |        HARD CONSTRAINT GATING           |                                         |
|                     | - Battery Energy Floor & Reserve Margin |                                         |
|                     | - Mission Sol Duration Ceiling          |                                         |
|                     | - Storage Capacity Overflow Ceiling     |                                         |
|                     | - Instrument Operational Envelope       |                                         |
|                     +-----------------------------------------+                                         |
|                                          |                                                              |
|                                          v                                                              |
|                     +-----------------------------------------+                                         |
|                     |   8-DIMENSIONAL PARETO OPTIMIZATION     |                                         |
|                     | - Science Utility (U_sci)               |                                         |
|                     | - Total Energy Consumed (E_tot)         |                                         |
|                     | - Mission Duration (T_mission)          |                                         |
|                     | - Relay Towers Deployed (K_relay)       |                                         |
|                     | - Connectivity Availability (A_comm)    |                                         |
|                     | - Data Volume Collected (D_coll)        |                                         |
|                     | - Simulated Data Transferred (D_trans)  |                                         |
|                     | - Peak Storage Occupancy (S_peak)       |                                         |
|                     +-----------------------------------------+                                         |
+---------------------------------------------------------------------------------------------------------+
```

This audit specifies the formal mathematical models, state representations, hard gating criteria, non-dominated sorting algorithms, and marginal trade-off formulations required to extend `src/marswalk/core/joint_mission_planner.py` into a complete **Science Return & Data Logistics Co-Design System**.

---

## 2. Unified Co-Design State Vector & Architectural Topology

### 2.1 The Co-Design Configuration Vector

A joint mission co-design candidate $\mathcal{C}$ is formalized as an 8-tuple evaluated over the continuous mission time horizon $t \in [0, T_{\text{mission}}]$:

$$\mathcal{C} = \Big\langle \mathcal{T}, \mathcal{S}, \Pi_{\text{obs}}, \mathcal{R}, \mathbf{E}(t), \mathbf{D}(t), \mathbf{S}(t), \mathbf{B}(t) \Big\rangle$$

Where:
1. **Traverse Geometry $\mathcal{T}$:** An ordered sequence of 8-connected grid coordinates $\mathbf{p} = \langle (r_0, c_0), (r_1, c_1), \dots, (r_N, c_N) \rangle$ defining the rover route across the calibrated USGS Jezero CTX 20m DTM.
2. **Selected Science Targets $\mathcal{S}$:** A discrete subset $\mathcal{S} \subseteq \mathcal{S}_{\text{candidate}}$ of candidate exploration waypoints visited along $\mathcal{T}$.
3. **Observation Schedule $\Pi_{\text{obs}}$:** Chronologically ordered sequence of scientific activities:
   $$\Pi_{\text{obs}} = \Big\{ \big(k, \tau_{\text{arr}, k}, \tau_{\text{prep}, k}, \tau_{\text{obs}, k}, \mathcal{I}_k, P_{\text{inst}, k}, \text{Vol}_k \big) \Big\}_{k=1}^{|\mathcal{S}|}$$
   detailing arrival time, instrument calibration/warmup duration, active exposure duration, instrument assignment $\mathcal{I}_k$, electrical operating power, and raw data volume produced.
4. **Relay Deployment Set $\mathcal{R}$:** A selected subset of surface relay masts $\mathcal{R} \subseteq \mathcal{P}_{\text{promontories}}$ deployed at promontory candidate positions, with antenna mast heights $h_{\text{relay}}$ and battery reserves $C_{\text{relay}}$.
5. **Dynamic Energy State $\mathbf{E}(t)$:** Continuous battery energy and state-of-charge trajectories for the exploration vehicle and all deployed relays:
   $$\mathbf{E}(t) = \Big\langle E_{\text{rover}}(t), \text{SOC}_{\text{rover}}(t), \big\{ E_{\text{relay}, j}(t), \text{SOC}_{\text{relay}, j}(t) \big\}_{j \in \mathcal{R}} \Big\rangle$$
6. **Data Volume Trajectory $\mathbf{D}(t)$:** Cumulative accounting of bits generated and simulated bits transferred:
   $$\mathbf{D}(t) = \Big\langle D_{\text{collection}}(t), D_{\text{sim\_transfer}}(t), D_{\text{released}}(t) \Big\rangle$$
7. **Onboard Storage State $\mathbf{S}(t)$:** Instantaneous occupied flash memory:
   $$S_{\text{used}}(t) \in [0, S_{\text{capacity}}]$$
8. **Remaining Backlog $\mathbf{B}(t)$:** Un-transferred collected data awaiting telemetry pass:
   $$D_{\text{backlog}}(t) = D_{\text{collection}}(t) - D_{\text{sim\_transfer}}(t) - D_{\text{released}}(t)$$

---

## 3. Science Utility Mathematical Formulation ($U_{\text{science}}$)

### 3.1 Linear Weighted Preference Model

Science return is modeled as a scalar utility function $U_{\text{science}}$ defined over the visited target set $\mathcal{S}$ and executed observations $\Pi_{\text{obs}}$:

$$U_{\text{science}}(\mathcal{S}, \Pi_{\text{obs}}) = \sum_{i \in \mathcal{S}} u_i(x_i)$$

Where $x_i$ represents the multi-attribute feature vector of target $i$, and $u_i(x_i)$ is evaluated as:

$$u_i(x_i) = \gamma_i \cdot \sum_{m \in \mathcal{M}} w_m \cdot s_{i, m} \cdot \prod_{c \in \Omega_i} \mathbb{I}(\text{constraint}_{i, c} \text{ satisfied})$$

### 3.2 Variable Definitions & Domains

| Parameter | Domain | Definition | Provenance & Handling |
| :--- | :--- | :--- | :--- |
| $\mathcal{M}$ | Discrete Set | Configured mission objective categories | Defined in mission planner config |
| $w_m$ | $[0.0, 1.0], \sum w_m = 1.0$ | Normalized objective weight profile | Configured by user/mission operator |
| $s_{i, m}$ | $[0.0, 100.0]$ | Inherent science rating of target $i$ under objective $m$ | Cataloged target database / Jezero registry |
| $\gamma_i$ | $[0.5, 1.5]$ | Target priority scaling multiplier | Based on priority classification |
| $\Omega_i$ | Discrete Set | Pre-observation prerequisites for target $i$ | Instrument dependencies & environmental gates |
| $\mathbb{I}(\cdot)$ | $\{0, 1\}$ | Boolean indicator function | Evaluates to 1 if prerequisite met, 0 otherwise |

### 3.3 Configurable Mission Objectives ($\mathcal{M}$)

Atlas supports 5 canonical mission objective categories:
1. **Geological Characterization ($m = \text{geo}$):** Stratigraphic outcrop layering, deltaic sedimentary facies, boulder morphology, impact breccia analysis.
2. **Mineralogical Investigation ($m = \text{min}$):** Carbonate, clay/phyllosilicate, and sulfate detection indicative of past aqueous habitability.
3. **Atmospheric & Environmental Observation ($m = \text{atm}$):** Diurnal temperature cycles, pressure oscillations, dust opacity, wind vectors (e.g., MEDA).
4. **Surface Morphology & Regolith Mechanics ($m = \text{morph}$):** Aeolian bedforms, dune ripple migration, soil bearing capacity, wheel slip hazard assessment.
5. **Astrobiological Potential ($m = \text{astro}$):** Organic carbon preservation potential, biosignature candidate screening, sample caching candidate triage.

### 3.4 Target Priority Classifications ($\gamma_i$)

To maintain strict scientific integrity, all targets must declare their priority derivation:
- `USER_ASSIGNED_PRIORITY` ($\gamma_i = 1.0 \times \text{user\_factor}$): Manually prioritized by user in Mission Studio.
- `SOURCE_DERIVED_PRIORITY` ($\gamma_i = 1.0$): Extracted directly from primary mission science documentation (e.g. NASA Mars 2020 Jezero landing site science team priority maps).
- `UNASSESSED_PRIORITY` ($\gamma_i = 0.5$): Uncharacterized opportunistic terrain waypoint.

### 3.5 Epistemic Truth Disclosure (Mandatory Scientific Disclosure)

> [!IMPORTANT]
> **Operational Science Preference vs. Objective Truth**  
> Calculated utility scores $U_{\text{science}}$ represent **user-configured mission preferences and tactical scheduling weights**, NOT an objective measurement of absolute scientific discovery or physical reality on Mars. No simulation can determine the true groundbreaking nature of an in-situ Martian sample before physical measurement and terrestrial laboratory analysis.

---

## 4. Hard Resource Constraints vs. Soft Multi-Objective Trade-offs

A central flaw in naive multi-objective optimization is allowing high science utility scores to compensate for physical mission failure (e.g., a route that collects 10,000 science points but exhausts its battery or exceeds Sol duration is presented as a "Pareto alternative").

Atlas Milestone 13G enforces a strict **two-stage architecture**:
1. **Stage 1: Hard Feasibility Gating ($\Phi(\mathcal{C}) \in \{0, 1\}$):** Any candidate configuration that violates any hard physical constraint is immediately classified as `INFEASIBLE`, assigned infinite loss, and excluded from the Pareto frontier.
2. **Stage 2: Non-Dominated Sorting on Feasible Subspace ($\mathcal{F} = \{\mathcal{C} \mid \Phi(\mathcal{C}) = 1\}$):** Multi-objective trade-offs are evaluated strictly among viable missions.

```
+---------------------------------------------------------------------------------------------------------+
|                               STAGE 1: HARD CONSTRAINT GATING PIPELINE                                  |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  Candidate Mission Configuration C = < T, S, Pi_obs, R, E(t), D(t), S(t), B(t) >                        |
|                                         |                                                               |
|  [Gate 1] Min Battery Energy Floor:    min_t E_rover(t) > 0 ?              NO ----+                     |
|  [Gate 2] Min Reserve Margin:          min_t SOC_rover(t) >= beta_res ?    NO ----+                     |
|  [Gate 3] Sol Duration Ceiling:        T_mission <= T_max_duration ?       NO ----+                     |
|  [Gate 4] Storage Capacity Ceiling:    max_t S_used(t) <= S_capacity ?     NO ----+                     |
|  [Gate 5] Relay Network Survival:      forall j, min_t E_relay,j(t) > 0 ?  NO ----+                     |
|  [Gate 6] Instrument Availability:     Thermal, power & duty cycle OK?     NO ----+                     |
|  [Gate 7] Prerequisite Dependencies:   Context imaging before Raman?       NO ----+                     |
|  [Gate 8] Traverse Slope Hazard:       max_step theta <= theta_max ?       NO ----+                     |
|  [Gate 9] Regolith NoData Mask:        forall (r, c), invalid_mask == 0 ?  NO ----+                     |
|                                         |                                         |                     |
|                                        YES                                        |                     |
|                                         v                                         v                     |
|                          +-----------------------------+           +-----------------------------+      |
|                          |    CLASSIFIED: FEASIBLE     |           |   CLASSIFIED: INFEASIBLE    |      |
|                          | Proceed to 8D Pareto Studio |           | Segregated to Audit Dossier |      |
|                          +-----------------------------+           +-----------------------------+      |
+---------------------------------------------------------------------------------------------------------+
```

### 4.1 Specification of Hard Gates

#### Gate 1: Zero-Battery Floor (Rover Locomotion & Life Support)
$$\min_{t \in [0, T_{\text{mission}}]} E_{\text{rover}}(t) > 0\text{ J}$$
Rover battery energy must never reach complete depletion ($0\text{ Wh}$).

#### Gate 2: Usable Battery Reserve Margin ($\beta_{\text{reserve}}$)
$$\min_{t \in [0, T_{\text{mission}}]} E_{\text{rover}}(t) \ge E_{\text{reserve}} = \beta_{\text{reserve}} \cdot C_{\text{battery}}$$
Where $\beta_{\text{reserve}} \in [0.10, 0.30]$ (nominal 20% reserve threshold). If energy drops into the reserve band, the mission is classified as `FEASIBLE_WITH_LOW_RESERVE` (advisory warning) or `ENERGY_CONSTRAINT_VIOLATION` if configured as a hard cutoff.

#### Gate 3: Maximum Mission Duration Envelope ($T_{\text{max\_duration}}$)
$$T_{\text{mission}} = t_{\text{traverse}} + \sum_{k \in \Pi_{\text{obs}}} t_{\text{obs}, k} + \sum_{j \in \mathcal{R}} t_{\text{deploy}, j} + t_{\text{delay}} \le T_{\text{max\_duration}}$$
Where $T_{\text{max\_duration}} = 88,775.2\text{ s}$ (1 Martian Sol) for robotic operations or $28,800\text{ s}$ (8-hour Sortie) for crewed EVA scenarios.

#### Gate 4: Maximum Onboard Storage Capacity ($S_{\text{capacity}}$)
$$\max_{t \in [0, T_{\text{mission}}]} S_{\text{used}}(t) \le S_{\text{capacity}}$$
Where $S_{\text{capacity}} = 512\text{ GB}$ ($4,096\text{ Gb}$). If an observation generates data that exceeds available free storage ($S_{\text{capacity}} - S_{\text{used}}(t)$), the observation cannot be executed unless an explicit overwrite policy is active.

#### Gate 5: Surface Relay Battery Envelope
$$\forall j \in \mathcal{R}: \min_{t \in [0, T_{\text{mission}}]} E_{\text{relay}, j}(t) \ge E_{\text{relay\_reserve}, j}$$
Surface relays deployed on promontories must maintain battery reserves throughout the active mission window.

#### Gate 6: Instrument Operational & Thermal Envelopes
$$\forall k \in \Pi_{\text{obs}}: P_{\text{inst}, k} \le P_{\text{inst\_peak\_limit}} \quad \text{and} \quad \delta_{\text{inst}, k} \le \delta_{\text{max\_duty\_cycle}}$$
Sensors must respect operational limits (e.g. SuperCam laser burst limits, PIXL high-voltage tube duty cycle).

#### Gate 7: Prerequisite Dependencies & Staging Locks
If observation $B$ requires prior context from observation $A$ (e.g., Mastcam-Z stereo context imaging $\to$ PIXL arm placement), $A$ must precede $B$ in time, and the rover must not deviate from the target waypoint before both are complete.

#### Gate 8: Geotechnical Critical Slope Cutoff
$$\max_{(r, c) \in \mathbf{p}} \theta(r, c) \le \theta_{\text{max\_slope}} = 25.0^\circ$$
No candidate traverse may plan a step across terrain exceeding the mechanical rollover threshold.

#### Gate 9: NoData & Obstacle Mask Conservation
$$\forall (r, c) \in \mathbf{p}: \text{invalid\_mask}[r, c] == 0$$
Strict preservation of USGS DTM NoData sentinels (`-9999.0` or invalid masks).

---

## 5. Exact Data Return, Simulated Transfer & Storage Backlog Accounting

### 5.1 Synthetic Data Product Profiles

To provide realistic data volume dynamics while maintaining scientific traceability, Milestone 13G defines 6 canonical synthetic instrument profiles modeled after NASA Mars 2020 payloads:

| Instrument Profile | Real-World Analog | Observation Mode | Nominal Duration ($t_{\text{obs}}$) | Active Power ($P_{\text{inst}}$) | Synthetic Data Size | Data Category |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ENV_SENSOR_PACK` | MEDA | Continuous background monitoring | $60\text{ s / checkpoint}$ | $15\text{ W}$ | $0.5\text{ MB / hr}$ | `TELEMETRY` |
| `STEREO_CONTEXT_CAM` | Mastcam-Z | Multispectral terrain panorama | $300\text{ s}$ | $35\text{ W}$ | $120\text{ MB}$ | `IMAGING` |
| `REMOTE_MICRO_IMAGER`| SuperCam | Laser LIBS + Micro-imaging burst | $600\text{ s}$ | $85\text{ W}$ | $45\text{ MB}$ | `SPECTRAL` |
| `ELEMENTAL_XRF_MAP` | PIXL | Contact arm X-ray fluorescence | $1800\text{ s}$ | $110\text{ W}$ | $250\text{ MB}$ | `CONTACT_SCIENCE` |
| `RAMAN_LUMINESCENCE` | SHERLOC | Deep UV Raman & luminescence scan | $2400\text{ s}$ | $140\text{ W}$ | $380\text{ MB}$ | `CONTACT_SCIENCE` |
| `SUBSURFACE_RADAR` | RIMFAX | Continuous sounding during traverse | Active while driving | $25\text{ W}$ | $15\text{ MB / 100m}$ | `RADAR_SOUNDING` |

*(Note: All data sizes and transfer rates represent synthetic planning models and are explicitly cataloged as such).*

### 5.2 Step-by-Step Onboard Storage Integration

Onboard storage occupancy $S_{\text{used}}(t)$ is updated via exact byte conservation at every discrete mission timeline step $t_k \to t_{k+1}$:

$$S_{\text{used}}(t_{k+1}) = S_{\text{used}}(t_k) + \Delta D_{\text{gen}}(t_k) - \Delta D_{\text{released}}(t_k)$$

Where:
- $\Delta D_{\text{gen}}(t_k)$: Data generated during time step $\Delta t_k = t_{k+1} - t_k$.
- $\Delta D_{\text{released}}(t_k)$: Storage explicitly freed by policy following successful simulated transfer.

```
+---------------------------------------------------------------------------------------------------------+
|                                 ONBOARD STORAGE STATE MACHINE                                           |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   [ Free Storage: S_avail ]                                                                             |
|              |                                                                                          |
|              v (Instrument Observation Produces Data)                                                   |
|   [ Buffer Write: S_used += D_gen ]                                                                     |
|              |                                                                                          |
|              +---> S_used / S_capacity < 0.60  =======> State: STORAGE_AVAILABLE                        |
|              +---> 0.60 <= S_used / S_cap < 0.85 =====> State: STORAGE_PRESSURE                         |
|              +---> 0.85 <= S_used / S_cap < 0.98 =====> State: STORAGE_NEAR_CAPACITY                    |
|              +---> S_used / S_cap >= 0.98  ===========> State: STORAGE_CAPACITY_REACHED                 |
|              |                                                                                          |
|              v (Transfer Window Available: C(t) != GAP)                                                 |
|   [ Transmit Buffer: D_sim_transfer += R_eff * Delta_t ]                                                |
|              |                                                                                          |
|              v (Base Station Verification ACK Received)                                                 |
|   [ Release Storage: S_used -= D_released ]                                                             |
|              |                                                                                          |
|              v (Data Integrity Conservation Check)                                                      |
|   D_backlog = D_collection - D_sim_transfer - D_released                                                |
+---------------------------------------------------------------------------------------------------------+
```

### 5.3 Simulated Communications-Aware Data Transfer Engine

Data transfer is evaluated dynamically across the mission timeline synchronized with the RelayNet line-of-sight communications state $C(t)$:

$$\Delta D_{\text{sim\_transfer}}(t) = R_{\text{effective}}(t) \cdot \Delta t \cdot \eta_{\text{protocol}}$$

Where:
- $\eta_{\text{protocol}} = 0.88$ (12% CCSDS / CFDP framing, FEC, and retransmission overhead).
- $R_{\text{effective}}(t)$ is determined by the active link graph path:
  $$R_{\text{effective}}(t) = \begin{cases} 
  R_{\text{direct}} = 2.0\text{ Mbps} & \text{if } C(t) = \text{CONNECTED\_DIRECT} \\
  R_{\text{relay}} \cdot \left(\frac{1}{H(t)}\right)^{0.6} & \text{if } C(t) = \text{CONNECTED\_RELAYED} \text{ with } H(t) \text{ hops} \\
  0.0\text{ Mbps} & \text{if } C(t) = \text{GAP (Blackout / Occluded)}
  \end{cases}$$
  where nominal $R_{\text{relay}} = 1.0\text{ Mbps}$.

### 5.4 Mandatory Strict Data Conservation Identity

At every instant $t$ and at final mission termination $T_{\text{mission}}$, the following conservation law must hold identically to within floating-point epsilon ($10^{-9}$):

$$D_{\text{backlog}}(t) \equiv D_{\text{collection}}(t) - D_{\text{sim\_transfer}}(t) - D_{\text{released}}(t)$$

Storage is **never released** until a transfer has been simulated, verified, and acknowledged. Un-transferred data remains in $D_{\text{backlog}}$ and occupies $S_{\text{used}}$.

---

## 6. Multi-Dimensional Pareto Frontier Extension (8 Dimensions)

### 6.1 The 8 Optimization Criteria

Milestone 13E established Pareto analysis across 7 mobility and communications dimensions. Milestone 13G extends the objective space to **8 distinct mission performance dimensions**, unifying science return, energy, duration, infrastructure, communications, data throughput, and onboard storage:

| Dimension | Metric | Symbol | Goal | Raw Units | Physical Bounds ($[L_d, U_d]$) | Canonical Loss Function ($f_d \in [0, 1]$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dim 1** | **Science Utility** | $U_{\text{sci}}$ | **MAXIMIZE** | Points $[0, 500]$ | $[0.0, U_{\text{max\_possible}}]$ | $f_1 = 1.0 - \min\left(1.0, \frac{U_{\text{sci}}}{U_{\text{max\_possible}}}\right)$ |
| **Dim 2** | **Total Energy Consumed** | $E_{\text{tot}}$ | **MINIMIZE** | Watt-hours ($\text{Wh}$) | $[E_{\text{baseline\_direct}}, C_{\text{battery}}]$ | $f_2 = \min\left(1.0, \max\left(0.0, \frac{E_{\text{tot}} - E_{\text{baseline}}}{C_{\text{battery}} - E_{\text{baseline}}}\right)\right)$ |
| **Dim 3** | **Total Mission Duration** | $T_{\text{mission}}$ | **MINIMIZE** | Seconds ($\text{s}$) | $[T_{\text{direct\_traverse}}, T_{\text{max\_duration}}]$ | $f_3 = \min\left(1.0, \max\left(0.0, \frac{T_{\text{mission}} - T_{\text{direct}}}{T_{\text{max\_duration}} - T_{\text{direct}}}\right)\right)$ |
| **Dim 4** | **Surface Relay Masts** | $K_{\text{relay}}$ | **MINIMIZE** | Count $[0, 3]$ | $[0, K_{\text{max\_budget}}]$ | $f_4 = \frac{K_{\text{relay}}}{K_{\text{max\_budget}}}$ |
| **Dim 5** | **Communications Blackout** | $A_{\text{comm}}$ | **MINIMIZE LOSS** | Percentage $[0, 100\%]$ | $[0.0, 100.0\%]$ | $f_5 = 1.0 - \left(\frac{\text{Availability}_{\text{pct}}}{100.0}\right)$ |
| **Dim 6** | **Data Volume Collected** | $D_{\text{coll}}$ | **MAXIMIZE** | Megabytes ($\text{MB}$) | $[0.0, D_{\text{max\_sample}}]$ | $f_6 = 1.0 - \min\left(1.0, \frac{D_{\text{coll}}}{D_{\text{max\_sample}}}\right)$ |
| **Dim 7** | **Data Return Throughput** | $D_{\text{trans}}$ | **MAXIMIZE** | Megabytes ($\text{MB}$) | $[0.0, D_{\text{coll}}]$ | $f_7 = 1.0 - \left(\frac{D_{\text{trans}}}{\max(D_{\text{coll}}, 1.0)}\right)$ |
| **Dim 8** | **Peak Storage Fill Ratio** | $S_{\text{peak}}$ | **MINIMIZE** | Percentage $[0, 100\%]$ | $[0.0, S_{\text{capacity}}]$ | $f_8 = \frac{S_{\text{peak}}}{S_{\text{capacity}}}$ |

*(Note: All loss functions $f_d \in [0.0, 1.0]$ are strictly framed such that $f_d = 0.0$ represents optimal performance and $f_d = 1.0$ represents worst-case boundary performance, establishing true dimensional homogeneity).*

### 6.2 Non-Dominated Sorting Algorithm Across 8D

Let $\mathcal{F}$ be the set of all hard-constraint-feasible candidate co-design configurations.

A configuration $\mathcal{C}_A \in \mathcal{F}$ **Pareto-dominates** configuration $\mathcal{C}_B \in \mathcal{F}$ (denoted $\mathcal{C}_A \prec \mathcal{C}_B$) if and only if:

$$\forall d \in \{1, \dots, 8\}: f_d(\mathcal{C}_A) \le f_d(\mathcal{C}_B) + \epsilon_{\text{tol}}$$
$$\text{AND}$$
$$\exists d \in \{1, \dots, 8\}: f_d(\mathcal{C}_A) < f_d(\mathcal{C}_B) - \epsilon_{\text{tol}}$$

Where $\epsilon_{\text{tol}} = 10^{-6}$ protects against floating-point imprecision.

The **Non-Dominated Pareto Set** $\mathcal{P}^*$ is the maximal subset of $\mathcal{F}$ containing all configurations not dominated by any other feasible configuration:

$$\mathcal{P}^* = \Big\{ \mathcal{C}_A \in \mathcal{F} \;\Big|\; \nexists \mathcal{C}_B \in \mathcal{F} \text{ such that } \mathcal{C}_B \prec \mathcal{C}_A \Big\}$$

---

## 7. Normalization, Scalar Scoring & Marginal Rates of Substitution (MRS)

### 7.1 Scalarized Composite Objective Loss ($J_w$)

To support decision selection under configured operator priorities, Atlas evaluates a scalarized weighted loss $J_w(\mathcal{C})$:

$$J_w(\mathcal{C}) = \sum_{d=1}^8 \bar{w}_d \cdot f_d(\mathcal{C}), \quad \bar{w}_d = \frac{w_d}{\sum_{k=1}^8 w_k}$$

Atlas defines 5 canonical operational weight profiles:

| Profile | $w_{\text{sci}}$ | $w_{\text{energy}}$ | $w_{\text{time}}$ | $w_{\text{relays}}$ | $w_{\text{blackout}}$ | $w_{\text{coll}}$ | $w_{\text{trans}}$ | $w_{\text{storage}}$ | Operational Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Balanced (Nominal)** | $0.20$ | $0.15$ | $0.10$ | $0.10$ | $0.10$ | $0.15$ | $0.15$ | $0.05$ | Multi-domain balanced compromise |
| **Science-First** | $0.40$ | $0.05$ | $0.05$ | $0.05$ | $0.05$ | $0.25$ | $0.10$ | $0.05$ | Maximizes targets & instruments visited |
| **Data Logistics-First**| $0.10$ | $0.10$ | $0.05$ | $0.15$ | $0.20$ | $0.10$ | $0.25$ | $0.05$ | Prioritizes line-of-sight & buffer evacuation |
| **Resource-Conservative**|$0.10$ | $0.35$ | $0.25$ | $0.05$ | $0.05$ | $0.05$ | $0.05$ | $0.10$ | Minimizes battery draw & Sol duration |
| **Infrastructure-Min** | $0.15$ | $0.15$ | $0.15$ | $0.35$ | $0.05$ | $0.05$ | $0.05$ | $0.05$ | Solves mission with minimal/zero relay towers |

### 7.2 Marginal Rates of Substitution (MRS) Formulations

To provide transparent, explainable decision rationales for why one Pareto candidate is chosen over another, Atlas calculates pairwise Marginal Rates of Substitution:

#### 1. Science Return vs. Energy Expenditure
$$\text{MRS}_{U, E} = \frac{\Delta E_{\text{consumed}}}{\Delta U_{\text{science}}} = \frac{E_{\text{tot}}(\mathcal{C}_A) - E_{\text{tot}}(\mathcal{C}_B)}{U_{\text{sci}}(\mathcal{C}_A) - U_{\text{sci}}(\mathcal{C}_B)} \quad \left[\frac{\text{Wh}}{\text{Science Point}}\right]$$
*Physical interpretation:* Quantifies the additional battery energy required to harvest one additional unit of scientific utility.

#### 2. Science Return vs. Data Logistics Return
$$\text{MRS}_{U, D} = \frac{\Delta D_{\text{sim\_transfer}}}{\Delta U_{\text{science}}} = \frac{D_{\text{trans}}(\mathcal{C}_A) - D_{\text{trans}}(\mathcal{C}_B)}{U_{\text{sci}}(\mathcal{C}_A) - U_{\text{sci}}(\mathcal{C}_B)} \quad \left[\frac{\text{MB}}{\text{Science Point}}\right]$$
*Physical interpretation:* Measures data volume returned per science point, identifying data-heavy vs data-efficient observations.

#### 3. Data Return Throughput vs. Energy Expenditure
$$\text{MRS}_{D, E} = \frac{\Delta E_{\text{consumed}}}{\Delta D_{\text{sim\_transfer}}} = \frac{E_{\text{tot}}(\mathcal{C}_A) - E_{\text{tot}}(\mathcal{C}_B)}{D_{\text{trans}}(\mathcal{C}_A) - D_{\text{trans}}(\mathcal{C}_B)} \quad \left[\frac{\text{Wh}}{\text{MB Transferred}}\right]$$
*Physical interpretation:* Measures the energetic efficiency of returning telemetry over the deployed communications topology.

#### 4. Storage Fill Reduction vs. Infrastructure Cost
$$\text{MRS}_{S, K} = \frac{\Delta S_{\text{peak}}}{\Delta K_{\text{relay}}} = \frac{S_{\text{peak}}(\mathcal{C}_B) - S_{\text{peak}}(\mathcal{C}_A)}{K_{\text{relay}}(\mathcal{C}_A) - K_{\text{relay}}(\mathcal{C}_B)} \quad \left[\frac{\text{MB Buffer Relieved}}{\text{Relay Tower}}\right]$$
*Physical interpretation:* Quantifies how much onboard flash memory pressure is relieved per additional relay tower deployed.

---

## 8. Algorithmic Workflow & Integration with JointMissionPlanner

### 8.1 Step-by-Step Co-Design Pipeline

The extended `optimize_science_mission_codesign()` orchestrator operates via the following deterministic execution sequence:

```
+---------------------------------------------------------------------------------------------------------+
|                    CO-DESIGN EXECUTION SEQUENCE IN JOINT MISSION PLANNER                                |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  1. INPUT VALIDATION: Validate start, goal, waypoints, terrain bounds, instruments, and budgets.        |
|                                                                                                         |
|  2. SUBSET ENUMERATION: Generate candidate science target subsets S_k (power set up to |S| <= 6).       |
|                                                                                                         |
|  3. TRAVERSE SYNTHESIS: For each target subset, compute minimum-effort TSP traverse using pairwise      |
|     leg cache (leveraging Waligora metabolic cost + Min-Distance heuristics).                           |
|                                                                                                         |
|  4. RELAY POOL SCREENING: Screen promontory candidate nodes on Jezero DTM (max 12 promontories).        |
|                                                                                                         |
|  5. SUBMODULAR RELAY PLACEMENT: For each traverse and relay budget k in [0..K_max], select relays      |
|     maximizing geometric line-of-sight coverage over traverse and science targets.                     |
|                                                                                                         |
|  6. INTEGRATED DYNAMIC SIMULATION: For each coupled candidate <Traverse, Relays, Targets>:             |
|     a. Integrate mechanical rolling work W_r and gravitational work W_g along all terrain cells.       |
|     b. Evaluate LOS raycasting and dynamic comms state C(t) from rover to Base/Relays.                 |
|     c. Execute observation schedule at each target: warmup, active power, dwell time.                  |
|     d. Generate synthetic data products and update onboard storage ledger S_used(t).                   |
|     e. Evaluate simulated transfer rate R_eff(t) and transfer data during connected windows.            |
|     f. Verify exact data conservation: D_backlog = D_collection - D_transferred - D_released.          |
|                                                                                                         |
|  7. HARD CONSTRAINT GATING: Filter candidates through 9 hard gates (battery, reserve, duration,         |
|     storage, relays, instruments, slope, NoData). Flag and segregate infeasible plans.                 |
|                                                                                                         |
|  8. 8-DIMENSIONAL PARETO EXTRACTION: Perform non-dominated sorting on feasible subspace F.             |
|                                                                                                         |
|  9. DECISION EXPLANATION & DOSSIER GENERATION: Select optimal candidate under active profile,          |
|     compute pairwise Marginal Rates of Substitution (MRS), format decision dossier and JSON schema.    |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### 8.2 Computational Complexity Analysis

- **Target Subset Evaluation:** For $K \le 6$ science targets, $2^K = 64$ subsets.
- **Pairwise Leg Caching:** With $|\mathcal{S}| + 2 \le 8$ nodes, pairwise legs count is $\binom{8}{2} = 28$ directional A* searches, computed once and reused across all subsets in $< 150\text{ ms}$.
- **Promontory Screening:** Topographic curvature screening across Jezero 20m DTM executed in $< 35\text{ ms}$.
- **Dynamic Timeline Integration:** $O(N_{\text{steps}})$ with $N_{\text{steps}} \le 500$ cells per route, executing in $< 3\text{ ms}$ per candidate.
- **Total End-to-End Search Runtime:** Evaluating 64 target subsets $\times$ 3 relay budgets ($= 192$ configurations) executes in **$< 850\text{ ms}$**, well within the Atlas API timeout budget ($< 5000\text{ ms}$).

---

## 9. Scientific Integrity, Epistemic Disclosures & Verification Quality Gates

### 9.1 Planetary Science Rigor Rules

1. **Topographic Source Provenance:** All terrain operations strictly reference the calibrated USGS HiRISE/CTX DTM for Jezero Crater (DOI: `10.5066/P906QQT8`), referenced to the IAU 2000 Mars Spheroid ($R_{\text{Mars}} = 3,396,190.0\text{ m}$).
2. **Gravitational Model:** Surface gravity acceleration is strictly modeled as $g_{\text{Mars}} = 3.71\text{ m/s}^2$.
3. **Descent Work Physics Disclosure (Required 13F Correction):**
   > [!NOTE]
   > MarsWalk models descent work as non-regenerative ($W_{m} = W_r + \max(0, W_g)$) as a **conservative, safety-oriented engineering modeling choice** to prevent overestimating battery life. This is **not an asserted flight fact** of Mars 2020 actuators.
4. **Simulated Data Transfer Disclosure:**
   > [!IMPORTANT]
   > Telemetry transmission is explicitly labeled `SIMULATED_DATA_TRANSFER`. MarsWalk models geometric line-of-sight and configured channel capacities; it does **not** execute actual radio-frequency radiation or communicate with NASA Deep Space Network (DSN) assets.
5. **No Operational Flight Safety Claims:** Modeled trajectories and resource ledgers are tactical mission planning heuristics and are **never certified as operational astronaut safety envelopes**.

---

## 10. Implementation Blueprint & Recommended Data Classes

The following Python dataclasses are recommended for implementation in `src/marswalk/core/science_mission_planner.py` and integration into `src/marswalk/core/joint_mission_planner.py`:

```python
"""
Data Architecture for Milestone 13G Science Mission & Data Logistics Co-Design.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

class ScienceTargetPriorityType(str, Enum):
    USER_ASSIGNED_PRIORITY = "USER_ASSIGNED_PRIORITY"
    SOURCE_DERIVED_PRIORITY = "SOURCE_DERIVED_PRIORITY"
    UNASSESSED_PRIORITY = "UNASSESSED_PRIORITY"

class StorageStateClassification(str, Enum):
    STORAGE_AVAILABLE = "STORAGE_AVAILABLE"
    STORAGE_PRESSURE = "STORAGE_PRESSURE"
    STORAGE_NEAR_CAPACITY = "STORAGE_NEAR_CAPACITY"
    STORAGE_CAPACITY_REACHED = "STORAGE_CAPACITY_REACHED"
    STORAGE_OVERFLOW_REJECTED = "STORAGE_OVERFLOW_REJECTED"

class SimulatedTransferStatus(str, Enum):
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    TRANSFER_IN_PROGRESS = "TRANSFER_IN_PROGRESS"
    TRANSFER_DEFERRED_GAP = "TRANSFER_DEFERRED_GAP"
    TRANSFER_QUEUE_BACKLOG = "TRANSFER_QUEUE_BACKLOG"

@dataclass
class InstrumentProfile:
    """Engineering profile for a scientific observation instrument."""
    instrument_id: str
    name: str
    active_power_w: float
    standby_power_w: float
    nominal_duration_s: float
    synthetic_data_rate_kbps: float
    nominal_data_volume_mb: float
    compatible_objective_types: List[str]
    warmup_duration_s: float = 60.0
    is_contact_instrument: bool = False

@dataclass
class ScienceObservationEvent:
    """Chronological record of a completed or scheduled scientific observation."""
    event_id: str
    target_id: str
    instrument_id: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    energy_consumed_j: float
    energy_consumed_wh: float
    data_generated_mb: float
    utility_score_awarded: float
    status: str = "SCHEDULED"

@dataclass
class OnboardDataProductRecord:
    """Individual data product record stored in onboard flash memory."""
    product_id: str
    observation_id: str
    target_id: str
    instrument_id: str
    data_category: str
    size_bytes: int
    size_mb: float
    creation_time_s: float
    sha256_checksum: str
    is_transferred: bool = False
    is_released_from_storage: bool = False

@dataclass
class ScienceCoDesignMetrics:
    """Unified 8-dimensional performance metrics for a co-design configuration."""
    # Dim 1: Science Utility
    science_utility_score: float
    targets_visited_count: int
    # Dim 2: Energy
    total_energy_wh: float
    mobility_energy_wh: float
    electrical_energy_wh: float
    final_battery_soc_pct: float
    min_battery_soc_pct: float
    # Dim 3: Duration
    total_duration_s: float
    traverse_duration_s: float
    science_dwell_duration_s: float
    # Dim 4: Infrastructure
    relay_count: int
    # Dim 5: Communications
    availability_pct: float
    gap_duration_s: float
    # Dim 6: Data Collected
    data_collected_mb: float
    # Dim 7: Data Transferred
    data_transferred_mb: float
    remaining_backlog_mb: float
    # Dim 8: Storage
    peak_storage_mb: float
    peak_storage_pct: float
    # Normalization & Feasibility
    normalized_8d_vector: Dict[str, float] = field(default_factory=dict)
    scalar_composite_loss: float = 0.0
    is_hard_gate_feasible: bool = True
    hard_gate_violations: List[str] = field(default_factory=list)
```

---

## 11. Conclusion & Recommendations for Implementation

1. **Strict Separation of Feasibility and Optimality:** Ensure `compute_pareto_frontier()` evaluates dominance **strictly on the subset of candidates that pass all 9 hard gates**. Infeasible candidates should be retained in the audit dossier with clear failure tags, but never awarded Pareto status.
2. **Deterministic Reproducibility:** Ensure all subset permutations, floating-point comparisons, and Jaccard deduplication rules use deterministic sorting keys and tie-breakers.
3. **Transparent Decision Dossier:** Ensure the decision explanation engine generates explicit, readable comparisons against competing Pareto alternatives, citing exact Marginal Rates of Substitution (Wh per science point, MB transferred per science point).
4. **Seamless Integration:** By building on the validated Milestone 13E `JointMissionPlanner` and 13F `MissionResourceLedger`, Milestone 13G achieves a complete **Science Return & Data Logistics Co-Design System** without breaking existing API data contracts or regression baselines.
