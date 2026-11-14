# Milestone 13T: Shared State & Causal Discrete-Event Model

**Milestone:** 13T — Atlas Planetary Mission OS  
**System Module:** `atlas_mission_state.py` & `atlas_mission_event_coordinator.py`

---

## 1. Multi-Tiered Mission State Container

To model realistic deep-space operations where Earth Mission Control never has zero-latency visibility into Mars surface conditions, Mission OS maintains a 4-tier state container:

```
+-------------------------------------------------------------------------------------------------+
| 1. PHYSICAL SIMULATION STATE (Ground Truth on Mars)                                             |
|    - True spatial positions (lat, lon, elevation_m), odometry (m)                               |
|    - Life support reserves: H2O (kg), O2 (kg), N2 (kg), CH4 (kg)                                |
|    - Surface power: Kilopower reactor gross kWe, direct solar flux (W/m2), battery SoC (%)      |
|    - Structural status: Habitat pressure (101.3 kPa), internal temperature (294.15 K)          |
|    - Atmosphere: Dust optical depth (tau), ambient temperature (K)                             |
+-------------------------------------------------------------------------------------------------+
                                      |
                            OWLT Delay (852.3 s)
                            Packet Buffers & Loss
                                      v
+-------------------------------------------------------------------------------------------------+
| 2. EARTH-REPORTED STATE (Telemetry at Mission Control Center)                                    |
|    - Lagged by 14.2 min One-Way Light Time (OWLT)                                               |
|    - Known asset coordinates, reported consumables, acknowledged commands                      |
|    - Telemetry drift vector: Delta(P_true, P_reported)                                          |
+-------------------------------------------------------------------------------------------------+
                                      |
                                      +-------------------------------+
                                      v                               v
+-----------------------------------------------+ +-----------------------------------------------+
| 3. PREDICTED STATE (Lookahead Forecast)       | | 4. PLANNED STATE (Nominal Schedule)           |
|    - 10-Sol forecast horizon                  | |    - Active Campaign Phase (A through G)      |
|    - Consumables depletion projections        | |    - Active Task IDs & assigned assets        |
|    - Projected Shannon information entropy    | |    - Schedule variance & milestone status     |
+-----------------------------------------------+ +-----------------------------------------------+
```

---

## 2. Temporal Mechanics & Solar Clock

Mars temporal evolution is governed by authentic planetary mechanics:
- **Mars Sol Duration:** $88,775.244\text{ SI seconds}$ ($24\text{h }39\text{m }35.244\text{s}$).
- **Martian Second Conversion:**
  $$\text{Ratio} = \frac{88,775.244}{86,400.0} \approx 1.02749125\text{ SI seconds / Martian second}$$
- **Solar Longitude ($L_s$):**
  $$L_s(t) = \left( L_{s,0} + \Delta\text{sol} \times \frac{360^\circ}{668.6} \right) \pmod{360^\circ}$$
  where $668.6\text{ sols}$ is the Martian orbital period (1 Martian Year).
- **Mission Elapsed Time (MET):**
  $$\text{MET} = (\text{sol} - 1) \times 88,775.244 + \text{sol\_seconds}$$

---

## 3. Priority Event Queue & Causal Lineage

Events are ordered deterministically via priority tuple:
$$\text{SortKey} = (\text{sol}, \text{sol\_seconds}, \text{priority}, \text{event\_id})$$
where $\text{priority} \in [1, 10]$ ($1 = \text{Highest Contingency}, 10 = \text{Routine Telemetry}$).

Every dispatched event records `parent_event_id`, forming a Directed Acyclic Graph (DAG) that enables complete causal replay during incident investigations.
