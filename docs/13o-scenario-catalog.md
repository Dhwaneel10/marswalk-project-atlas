# PROJECT ATLAS — MILESTONE 13O
# DEEP SPACE AUTONOMY SCENARIO CATALOG
## 10 Reproducible Interplanetary Operational Scenarios and the 8-Stage Flagship Demonstration

**Milestone:** 13O — Atlas Deep Space Autonomy Lab  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Core Implementation:** `src/marswalk/core/deep_space_scenario_engine.py`

---

## 1. Overview of Scenario Suite

To rigorously test, benchmark, and demonstrate deep space operations under delayed, intermittent, and disrupted communications, Milestone 13O introduces a standardized catalog of **10 Reproducible Interplanetary Scenarios**. Each scenario specifies initial conditions, environmental events, communication link profiles, telecommand sequences, and formal acceptance criteria.

---

## 2. Flagship Scenario 01: "The Rover That Lost Earth"

The signature demonstration of Project Atlas illustrates the complete end-to-end lifecycle of deep space robotic agency across 8 discrete chronological stages:

```
+--------------------------------------------------------------------------------------------------------+
|                              SCENARIO 01: 8-STAGE OPERATIONAL LIFECYCLE                                |
+--------------------------------------------------------------------------------------------------------+
|  [Stage 1]       [Stage 2]         [Stage 3]       [Stage 4]       [Stage 5]     [Stage 6]   [Stage 7] |
|  Departure       Obstacle Formed   RF Outage       Stale Command   Autonomous    Earth Holds Downlink  |
|  Earth Plan ->   Rockfall at       Relay Lost ->   Rejected Onboard->Detour ->   Waiting ->  Received  |
|  Transmitted     (35.0, 50.0)      No Contact      State Mismatch  Executed      No Signal   on Earth  |
|                                                                                                  |     |
|                                                                                 [Stage 8] <------+     |
|                                                                                 Mission Cont.          |
+--------------------------------------------------------------------------------------------------------+
```

### Stage 1: The Departure (Earth Dispatches Plan)
- **Time:** $t = 0.0\text{ min}$
- **Action:** Earth Mission Control plans a $100\text{ m}$ science traverse in Jezero Crater towards an ancient delta outcrop. The command (`CMD-2026-11-04-001`) is validated against expected state version `v1`, signed with Tier 2 tactical approval, packetized with a SHA-256 digest, and enqueued into the Goldstone DSN uplink buffer.
- **Channel:** Enters the deep space channel with an orbital one-way light time (OWLT) of $14.2\text{ minutes}$.

### Stage 2: Unexpected Terrain (The Physical Reality on Mars)
- **Time:** $t = 4.5\text{ min}$ (Telecommand is still traveling in interplanetary vacuum)
- **Physical Event:** A minor seismic tremor or thermal slope failure causes a steep rockfall slump across the Jezero delta traverse corridor at coordinates $(x = 35.0, y = 50.0)$.
- **Rover Detection:** Rover Hazcams and navigation cameras detect the boulder field ($r = 8.5\text{ m}$). Local hazard map is updated. Rover increments its local state version from `v1` to `v2`.
- **Epistemic Reality:** Earth is completely unaware of this event; on Earth screens, the path appears clear.

### Stage 3: Communication Disruption (Loss of Line-of-Sight)
- **Time:** $t = 8.0\text{ min}$
- **Channel Event:** The local UHF orbiter relay (Mars Reconnaissance Orbiter analog) sets behind the western rim of Jezero Crater. Direct-to-Earth carrier drops below the horizon mask. Mars enters a complete communications occultation lasting $45\text{ minutes}$.

### Stage 4: The Stale Command (Onboard Interception & Rejection)
- **Time:** $t = 14.2\text{ min}$
- **Arrival:** Telecommand `CMD-2026-11-04-001` reaches the rover.
- **Onboard Invariant Verification:**
  - `Expected State Version == 1`, but `Current State Version == 2`. $\implies$ **MISMATCH**.
  - Traverse corridor intersects active rockfall slump at $(35.0, 50.0)$. $\implies$ **COLLISION HAZARD**.
- **Decision:** Rover Autonomy Engine **REJECTS** the command. It logs an explainable decision record citing rule `INV-HAZARD-INTERSECTION-01` and `INV-STATE-VERSION-01`. Wheels remain locked.

### Stage 5: Autonomous Response (Bounded Local Detour Execution)
- **Time:** $t = 15.0\text{ min}$
- **Contingency Evaluation:** Operating in `BOUNDED_AUTONOMY` mode, the rover evaluates whether a northern detour around the rockfall satisfies its certified envelope ($d_{\text{detour}} = 18.4\text{ m} \le 50\text{ m}$, projected $\text{SoC} = 68.4\% \ge 30\%$).
- **Execution:** Rover computes tangent avoidance waypoints, engages drive motors, safely circumnavigates the boulders, re-converges on the target science outcrop, and engages survival heaters.

### Stage 6: Earth Cannot Respond (The Silence of Interplanetary Latency)
- **Time:** $t = 20.0\text{ min}$
- **Earth Reality:** On Earth, telemetry monitors still show the rover in its initial position at $t=0$, because downlink propagation takes another $14.2\text{ minutes}$ plus relay windowing. Flight controllers observe radio silence and must trust the vehicle's onboard autonomy policy.

### Stage 7: Contact Restored (Telemetry Downlink Arrival)
- **Time:** $t = 28.4\text{ min}$ (Full Round-Trip Light Time)
- **Downlink Ingestion:** Goldstone DSN locks carrier with the rising Mars relay orbiter. The downlink packet arrives on Earth.
- **Telemetry Parsing:** Earth Mission Control discovers that:
  1. The original command was intercepted and rejected.
  2. An unexpected rockfall was mapped.
  3. The rover autonomously executed an $18.4\text{ m}$ detour and is currently safe at the target waypoint with $68.4\%$ battery reserve.

### Stage 8: Mission Continuation (Synchronized Cooperative Planning)
- **Time:** $t = 30.0\text{ min}$
- **Cooperative Replanning:** Flight controllers ingest the rover-mapped rockfall into Earth's global terrain model, increment Earth's state model to `v2`, and author the next sol's drill sampling plan with updated situational truth.

---

## 3. Catalog of Additional Operational Scenarios (02 to 10)

### SCENARIO_02: Solar Conjunction Blackout
- **Objective:** Validates operational survival during a 14-sol superior solar conjunction when the Sun-Earth-Mars angle $< 2.0^\circ$.
- **Behavior:** Uplink commands are barred by automated flight rules. Rover enters conservative `BOUNDED_AUTONOMY` mode, logging environmental readings into high-capacity flash storage. Once the conjunction passes, buffered data is downlinked in bulk without data loss.

### SCENARIO_03: The Delayed Acknowledgement & Duplicate Prevention
- **Objective:** Verifies that delayed telemetry acknowledgements do not cause double execution of hazardous commands.
- **Behavior:** Earth commands a $50\text{ m}$ drive. Downlink ACK is delayed due to ground station antenna re-pointing. Earth retransmits the command. Rover's idempotency engine recognizes the duplicate SHA-256 payload and sequence ID, suppresses physical actuation, and re-downlinks the original completion token.

### SCENARIO_04: The Outdated Instruction (State Version Mismatch)
- **Objective:** Demonstrates automatic rejection of commands authored against an obsolete rover configuration.
- **Behavior:** Earth transmits an instrument mast deployment predicated on state `v2`. Prior to arrival, an unexpected thermal event forced the mast into protective stowage, incrementing rover state to `v4`. Onboard validator rejects the telecommand to prevent mechanical collision.

### SCENARIO_05: Orbiter Relay Gap & Contact Windowing
- **Objective:** Simulates intermittent store-and-forward communication through non-geostationary Mars orbiters (MRO / Mars Odyssey).
- **Behavior:** Telemetry packets generated while the rover is in deep canyon valleys are queued locally. When the orbiter crosses the local zenith ($12\text{ min}$ pass window), the high-speed UHF proximity transceiver drains the queue.

### SCENARIO_06: Multi-Rover Fleet Coordination & Peer Hazards
- **Objective:** Validates peer-to-peer UHF mesh hazard sharing between co-located surface rovers (Perseverance and Curiosity analogs).
- **Behavior:** Rover 1 encounters an unmapped dune slip corridor, broadcasts a `P2P_HAZARD_ALERT`. Rover 2, approaching the same region from $800\text{ m}$ away, ingests the alert and replans its path around the slip zone without Earth intervention.

### SCENARIO_07: The Energy Crisis (Thermal & Battery Depletion)
- **Objective:** Tests autonomous load shedding and survival preservation under sudden power loss.
- **Behavior:** Dust accumulation reduces solar panel output by $40\%$. The rover intercepts a commanded high-power rock abrasion activity, rejects the tool actuation, and enters `SAFE_HOLD` with survival heaters prioritized.

### SCENARIO_08: Epistemic Divergence & Reconnection
- **Objective:** Models belief divergence when Earth and Mars states drift apart during extended blackouts, followed by automated truth reconciliation.
- **Behavior:** During a 3-sol link loss, the rover detours $120\text{ m}$. Earth believes the rover is still at Waypoint Alpha. Upon link re-establishment, vector reconciliation updates Earth's digital twin to match Martian reality.

### SCENARIO_09: Deep Space Network Handover Contention
- **Objective:** Validates packet loss recovery during ground station tracking handovers from Goldstone to Canberra.
- **Behavior:** Carrier loss mid-transmission triggers automatic sequence number tracking and re-request protocols.

### SCENARIO_10: Non-Deterministic Wheel Slip & Inertial Realignment
- **Objective:** Tests onboard IMU visual odometry slip compensation during traverse over loose Martian regolith.
- **Behavior:** Wheel tachometers indicate $30\text{ m}$ traveled, but visual odometry reveals a $35\%$ slip deficit ($19.5\text{ m}$ actual ground progress). Rover autonomously recalibrates its dead-reckoning trajectory.

---

## 4. Scenario Execution Summary Table

| Scenario ID | Name | Primary Challenge | Autonomy Response | Verification Criterion |
|---|---|---|---|---|
| `SCENARIO_01` | The Rover That Lost Earth | In-transit rockfall + link outage | Intercepts stale plan, executes $18.4\text{ m}$ detour | Zero collision, goal reached, state reconciled |
| `SCENARIO_02` | Solar Conjunction Blackout | 14-sol plasma communication silence | Uplink moratorium, buffers $100\%$ telemetry | Zero corrupted packets, bulk downlink complete |
| `SCENARIO_03` | Delayed Acknowledgement | Retransmitted duplicate telecommand | Idempotency engine rejects double actuation | Exactly 1 physical movement, duplicate ACKed |
| `SCENARIO_04` | Outdated Instruction | Obsolete state version reference | Invariant validator rejects execution | State version check fails, safe hold maintained |
| `SCENARIO_05` | Orbiter Relay Gap | Intermittent $12\text{ min}$ overpass windows | Store-and-forward queue management | Buffer preserves all high-priority packets |
| `SCENARIO_06` | Multi-Rover Coordination | Shared regional hazard across fleet | P2P UHF mesh hazard broadcasting | Fleet rovers replan before entering hazard |
| `SCENARIO_07` | The Energy Crisis | Severe battery and thermal deficit | Rejects science loads, powers survival heaters | Battery never drops below hard $30\%$ reserve |
| `SCENARIO_08` | Epistemic Divergence | Earth belief drifts from Mars reality | Version vector reconciliation on contact | Ground twin accurately synchronizes to Mars |
| `SCENARIO_09` | DSN Handover Contention | Carrier drop during station slew | Selective packet retransmission | Zero lost bytes across station transition |
| `SCENARIO_10` | Non-Deterministic Slip | $35\%$ regolith wheel slip error | Visual odometry closed-loop correction | Arrives within $0.5\text{ m}$ of target waypoint |

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All scenarios, obstacle parameters, and autonomous contingency procedures cataloged here represent robotic research simulations. They must never be considered certified or safe for manned missions or human astronauts.
