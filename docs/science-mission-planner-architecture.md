# Atlas Science Mission Planner Architecture
## Multi-Instrument Observation Scheduling, Target Prioritization & Resource Integration

**System Component:** `src/marswalk/core/science_mission_planner.py`  
**Milestone:** 13G-R Release Qualification  
**Project:** MarsWalk 2.0 / Project Atlas  
**Architecture Classification:** Planetary In-Situ Science Observation & Traverse Co-Design  

---

## 1. Architectural Overview

The Science Mission Planner integrates surface science observations with traverse kinematics, energy budgeting, and onboard data accounting. It transforms a spatial rover route from a passive point-to-point traverse into an active scientific exploration mission.

```mermaid
flowchart TD
    A["Selected Science Targets & Objectives"] --> B["Authoritative Compatibility Validator"]
    B --> C["5-Phase Activity Scheduler"]
    C --> D["Terramechanical & Payload Energy Model (13F)"]
    C --> E["Mission Data Ledger (13G Byte Accounting)"]
    D --> F["Feasibility & Hard Constraints Engine"]
    E --> F
    F --> G["8D Multi-Objective Pareto Optimizer"]
    G --> H["Mission Theater Digital Twin Sync"]
```

---

## 2. Science Target Prioritization & Tri-State Provenance

Targets are modeled via `ScienceTargetConfig`:

### Priority Provenance Classification
To ensure scientific integrity and prevent operator preference from being misrepresented as empirical truth, every target priority carries an explicit provenance tag:
1. `USER_ASSIGNED_PRIORITY`: Priority explicitly input by an astronaut, science team lead, or human operator.
2. `SOURCE_DERIVED_PRIORITY`: Priority derived from peer-reviewed mission literature (e.g., Farley et al. 2020, Mangold et al. 2021).
3. `UNASSESSED_PRIORITY`: Default score when no specific evaluation exists; never treated as high-confidence discovery value.

### Multi-Objective Preference Utility
Mission science utility is calculated as a normalized linear preference utility:

\[
U_{\text{science}} = \sum_{k=1}^K w_{\text{target}, k} \cdot S(T_k) \cdot \mathbb{I}_{\text{completed}}(T_k)
\]

where $S(T_k) \in [0, 100]$ is the configured priority score, $w_{\text{target}, k}$ is the relative target weight, and $\mathbb{I}_{\text{completed}}(T_k) = 1$ only if all scheduled observation phases finish within mission time and energy limits.

---

## 3. Chronological 5-Phase Observation Scheduling

At every scheduled target stop, the planner decomposes scientific activities into 5 discrete phases to capture realistic mechanical and electrical overheads:

```mermaid
sequenceDiagram
    participant Rover as Rover Platform
    participant Arm as Robotic Arm Turret
    participant Inst as Science Instrument
    participant Ledger as Onboard Data Ledger

    Note over Rover,Ledger: Phase 1: Rover Arrival & Settle (300 s, 110 W base load)
    Rover->>Rover: Settle on Martian regolith, thermal stabilization

    Note over Rover,Ledger: Phase 2: Instrument Preparation & Warmup (180 s)
    Rover->>Arm: Unstow turret arm & orient sensors
    Rover->>Inst: Optics heater / sensor warmup (30 W)

    Note over Rover,Ledger: Phase 3: Observation Execution (Calibrated Duration)
    Inst->>Inst: Active data acquisition (Laser/XRF/Radar/Spectra)
    Inst->>Ledger: Transmit raw detector streams

    Note over Rover,Ledger: Phase 4: Post-Processing & Cache (120 s)
    Rover->>Ledger: Generate MissionDataProduct & SHA-256 Checksum
    Ledger->>Ledger: Allocate flash storage bytes & update backlog

    Note over Rover,Ledger: Phase 5: Instrument Stow & Secure (240 s)
    Arm->>Rover: Retract robotic arm to travel latches
```

### Cumulative Energy Cost for Target Stop
For target $T_k$ with instruments $M(T_k)$:

\[
E_{\text{target}}(T_k) = P_{\text{base}} \cdot \Delta t_{\text{settle}} + \sum_{m \in M(T_k)} \left[ (P_{\text{base}} + P_{\text{warmup}}) \cdot \Delta t_{\text{warmup}} + (P_{\text{base}} + P_m) \cdot \Delta t_m + (P_{\text{base}} + P_{\text{cache}}) \cdot \Delta t_{\text{cache}} \right] + P_{\text{base}} \cdot \Delta t_{\text{stow}}
\]

This energy is integrated into the battery state-of-charge (SOC) accounting from Milestone 13F. If battery SOC drops below the configured `reserve_margin_pct`, an `ENERGY_CONSTRAINT_VIOLATION` is flagged.
