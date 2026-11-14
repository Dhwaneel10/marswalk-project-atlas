# Counterfactual Scenario Modeling & Disturbance Methods

## 1. The 12 Standardized Planetary Disturbance Models

The **Counterfactual Scenario Engine** (`CampaignCounterfactualEngine`) equips Atlas with 12 standardized disturbance models reflecting authentic Martian surface operational hazards across communications, energy, science, data, mobility, and flight operations.

| ID | Disturbance Name | Subsystem | Typical Trigger & Physical Mechanism | Primary Impact |
|:---|:---|:---|:---|:---|
| **R1** | `R1_RELAY_LOSS` | Communications | Orbiter safe-mode or geometric occultation behind crater rim crest | Complete RF blackout along traverse segments; loss of real-time telemetry |
| **R2** | `R2_COMMS_DEGRADATION` | Communications | Elevated atmospheric dust tau / multi-path scattering | 40% reduction in downlink throughput rate; transmission latency spikes |
| **R3 / E1** | `E1_BATTERY_DEGRADATION` | Power & Energy | Lithium-ion cell string open circuit / thermal degradation | 25% reduction in total battery capacity; night heater reserve violation |
| **E2** | `E2_DUST_STORM_SOLAR_LOSS` | Power & Energy | Regional Martian dust storm obscuring solar irradiance | 50% cut in daily array generation; energy deficit under nominal drive |
| **S1** | `S1_HIGH_UTILITY_DISCOVERY` | Science & Payload | Serendipitous detection of hydrated minerals / bio-signatures | Opportunity for +150 utility; demands +60 min contact science dwell |
| **S2** | `S2_SCIENCE_TIME_OVERRUN` | Science & Payload | Drill bit binding / sample tube sealing resistance | 90-minute operational delay; encroaches on drive daylight and battery |
| **D1** | `D1_FLASH_STORAGE_FAULT` | Storage & Memory | Cosmic ray single-event upset locking flash memory sectors | 30% reduction in usable storage buffer; high risk of buffer overflow |
| **D2** | `D2_DOWNLINK_BOTTLENECK` | Storage & Memory | DSN ground station contention truncating orbital pass | 50% cut in pass duration; accumulated backlog remaining onboard |
| **M1** | `M1_WHEEL_DRIVE_ANOMALY` | Mobility | Actuator motor brush wear / gearbox thermal resistance | 40% reduction in maximum drive velocity; rover cannot reach Sol terminus |
| **M2** | `M2_OBSTACLE_SLIP_HAZARD` | Mobility | Loose aeolian bedforms (megaripples) exceeding slip limits | Forced 1.8 km flanking detour around high-slip dune fields |
| **O1** | `O1_SOL_EARLY_TERMINATION` | Operations | Precautionary flight software safe-mode abort on IMU anomaly | Immediate halt to all sol activities; early transition to safe bivouac |
| **O2** | `O2_INSTRUMENT_CALIBRATION_FAULT` | Operations | Thermal drift in spectrometer reference calibration target | Observation data flagged dubious; demands mid-sol recalibration |

---

## 2. Mathematical Disturbance Injection

Disturbances are parameterized and mathematically injected into a child branch via `run_counterfactual_scenario(scenario_type, target_sol, severity, parameters)`.

### Example: E1 Battery Capacity Degradation
$$\tilde{C}_{\text{batt}} = C_{\text{batt}} \cdot (1.0 - \delta_{\text{loss}})$$
$$\text{Consumed Energy Fraction} = \frac{E_{\text{consumed}}}{\tilde{C}_{\text{batt}}}$$
$$\text{Reserve Margin} = 1.0 - \text{Consumed Energy Fraction} - SOC_{\text{min\_reserve}}$$

If Reserve Margin $< 0$, invariant `ENG-001` fails.

### Example: R1 Line-of-Sight Relay Blackout
For all waypoints $w_i$ in sol schedule $s_{\text{target}}$:
$$\text{LOS}(w_i, \text{Relay}_{\text{active}}) \leftarrow 0.0$$
$$\text{Coverage}_{\text{sol}} = \frac{1}{N} \sum_{i=1}^N \text{LOS}(w_i, \text{Relay}_{\text{active}})$$

If $\text{Coverage}_{\text{sol}} < 0.85$, invariant `COMM-001` fails.

---

## 3. Automated Recovery Synthesis

For each disturbance, the engine generates an optimal counterfactual recovery branch:
1. **Rerouting**: Alters path waypoints to exploit terrain high points with continuous LOS or avoid high-slope sand ripples.
2. **Activity Pruning & Rescheduling**: Defers lower-tier science targets to subsequent sols while preserving primary objectives.
3. **Data Compression**: Switches payload output formats from uncompressed TIFF to compressed JPEG2000 to mitigate flash storage pressure.
4. **Speed Throttling**: Lowers mobility actuator current draw to balance battery survival budgets.
