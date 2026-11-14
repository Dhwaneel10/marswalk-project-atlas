# PROJECT ATLAS — MILESTONE 13P
# PLANETARY AERIAL OPERATIONS SCENARIO CATALOG
## 10 Reproducible Flight Scenarios and the 6-Stage Flagship Crater Reconnaissance Demonstration

**Milestone:** 13P — Atlas Aerial Corps: Multi-Rotorcraft Intelligence, Aerial Science, Flight Dynamics & Rover–Aircraft Cooperation  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Core Implementation:** `src/marswalk/core/mars_aerial_scenario_engine.py`

---

## 1. Overview of the 10 Aerial Exploration Scenarios

To thoroughly test, benchmark, and demonstrate planetary rotorcraft flight, aerodynamics, autonomous contingencies, and rover-aircraft cooperation, Milestone 13P establishes a standardized catalog of **10 Reproducible Planetary Aerial Scenarios**. Every scenario preserves its initial seeds, atmospheric conditions, event sequences, and verification criteria for deterministic replay.

---

## 2. Flagship Scenario 01: "The Crater Reveal" (6-Stage Walkthrough)

The signature demonstration of Project Atlas illustrates the complete lifecycle of cooperative ground-aerial planetary exploration across six chronological stages:

```
+--------------------------------------------------------------------------------------------------------+
|                              SCENARIO 01: 6-STAGE OPERATIONAL LIFECYCLE                                |
+--------------------------------------------------------------------------------------------------------+
|  [Stage 1]       [Stage 2]         [Stage 3]       [Stage 4]       [Stage 5]       [Stage 6]           |
|  Rover Impasse   Rotorcraft        Aerial Survey   Scout Safe      Cooperative     Rover Arrival &     |
|  at Crater Rim   Takeoff & Climb   14 Boulders     Touchdown on    Route Bypass    Synchronized        |
|  Slope > 18 deg  to 15m AGL        Discovered      3.2 deg Slope   Refinement      Telemetry Downlink  |
+--------------------------------------------------------------------------------------------------------+
```

### Stage 1: Rover Standstill at Crater Rim
- **Elapsed Time:** $t = 0.0\text{ s}$
- **Initial Setup:** Perseverance rover reaches coordinates $(0, 0)$, facing a steep $22.0^\circ$ escarpment rim leading down into Jezero Crater. Orbital CTX imagery is ambiguous; rover route planner evaluates a blind traverse uncertainty of $68.0\%$ and halts to avoid entrapment.
- **Decision:** Mission Control authorizes an immediate aerial reconnaissance sortie by the co-located Ingenuity-class Light Scout (`AERO-INGENUITY-01`).

### Stage 2: Autonomous Rotorcraft Deployment
- **Elapsed Time:** $t = 25.0\text{ s}$
- **Action:** Scout spins up its coaxial rotors to $2,537\text{ RPM}$ (advancing tip Mach $0.702$), validates thrust margin ($TM = 1.28 \ge 1.15$), and executes a vertical climb to $15.0\text{ m}$ AGL in $8.5\text{ seconds}$.
- **Telemetry:** Electrical power consumption stabilizes at $362.4\text{ W}$; battery State of Charge drops slightly to $96.8\%$.

### Stage 3: Escarpment Flyover & Boulder Hazard Discovery
- **Elapsed Time:** $t = 60.0\text{ s}$
- **Action:** Scout cruises forward along the planned corridor at $7.0\text{ m/s}$ ($V_{\text{be}}$), capturing visible optical imagery at $0.78\text{ cm/px}$ GSD.
- **Scientific Discovery:** The aerial camera maps an uncataloged rockfall slump at $(42.5, 58.0)$ containing $14$ large boulders ($r \ge 0.85\text{ m}$) directly across the baseline rover traverse path. The hazard is georeferenced and flagged as impassable for ground mobility.

### Stage 4: Scout Safe Touchdown
- **Elapsed Time:** $t = 95.0\text{ s}$
- **Action:** Scout arrives at Airfield Bravo $(80.0, 95.0)$. Onboard laser altimeter evaluates landing suitability: ground slope is $3.2^\circ \le 8^\circ$, surface roughness is $0.04\text{ m}$, and boulder clearance is $> 12\text{ m}$ (Composite Score: $0.84$).
- **Touchdown:** Scout executes vertical descent at $-1.2\text{ m/s}$ and shuts down rotors. Final battery SoC is $78.2\%$ (well above the $20\%$ mandatory touchdown reserve).

### Stage 5: Cooperative Route Optimization
- **Elapsed Time:** $t = 110.0\text{ s}$
- **Data Transfer:** Scout downlinks the $42.5\text{ MB}$ aerial orthomosaic to Perseverance over the $401.5\text{ MHz}$ Proximity-1 UHF link.
- **Route Refinement:** Perseverance ingests the boulder coordinates into its costmap and synthesizes a smooth northern detour around the hazard. Traverse distance drops from $208.5\text{ m}$ (with blind backtrack) to $146.1\text{ m}$ (saving $62.4\text{ m}$), and route uncertainty collapses from $68.0\%$ to $8.5\%$.

### Stage 6: Rover Arrival & Synchronized Telemetry
- **Elapsed Time:** $t = 180.0\text{ s}$
- **Execution:** Perseverance traverses along the aerial-cleared corridor without a single obstacle strike, reaching Airfield Bravo alongside the scout.
- **Synergy:** Net mission energy saved is $+82.4\text{ Wh}$. A consolidated ground-aerial science return package is enqueued for deep space Earth downlink.

---

## 3. Catalog of Scenarios 02 Through 10

### SCENARIO_02: The Lost Aircraft
- **Core Challenge:** In-flight communication carrier loss caused by terrain diffraction behind a crater rim.
- **Autonomy Behavior:** Heartbeat timer ($5.0\text{ s}$) expires; aircraft switches to `BOUNDED_AERIAL_AUTONOMY`, evaluates battery margin ($85.0\%$), and executes an autonomous contingency vertical descent to a pre-certified alternate landing site.

### SCENARIO_03: The Thin-Air Challenge
- **Core Challenge:** Extreme thin-atmosphere conditions ($p = 520\text{ Pa}$, $T = 245\text{ K}$, $\rho = 0.0112\text{ kg/m}^3$).
- **Autonomy Behavior:** Aerodynamic engine evaluates full $1.0\text{ kg}$ payload, determines thrust margin drops to $1.06 < 1.15$, and automatically rejects flight plan until payload is de-rated to $0.45\text{ kg}$ to restore $TM \ge 1.15$.

### SCENARIO_04: The Dust Wall
- **Core Challenge:** Sudden convective dust event inducing $14.2\text{ m/s}$ horizontal crosswind gust.
- **Autonomy Behavior:** 6-DOF attitude controller tilts rotor disk $16.5^\circ$ into the wind to arrest drift, detects approaching advancing blade transonic stall, aborts cruise, and drops altitude to $8\text{ m}$ within the surface boundary layer.

### SCENARIO_05: Two Aircraft, One Target
- **Core Challenge:** Science Scout and Science Mapper both request flight corridors toward the same Delta Scarp target at overlapping times.
- **Autonomy Behavior:** Fleet intelligence detects 4D spatial-temporal cylinder intersection, reserves corridor for Scout 2, and automatically deconflicts Mapper 3 to altitude $30.0\text{ m}$ with $15\text{ s}$ temporal separation.

### SCENARIO_06: The Dangerous Landing
- **Core Challenge:** Laser altimeter detects designated touchdown zone has $14.5^\circ$ slope and $0.18\text{ m}$ roughness.
- **Autonomy Behavior:** Site is formally rejected (`GROUND_SLOPE_TOO_STEEP_14.5deg`); aircraft diverts $18.7\text{ m}$ to verified flat terrace ($2.8^\circ$ slope) and touches down safely.

### SCENARIO_07: The Hidden Ice Mapping Expedition
- **Core Challenge:** Airborne Ground-Penetrating Radar subsurface sounding.
- **Autonomy Behavior:** Science Mapper sounder maps synthetic cross-bedded dielectric interface at $3.8\text{ m}$ depth; system enforces mandatory truth disclosure that synthetic reflections do not represent confirmed water ice.

### SCENARIO_08: The Rover Needs Help
- **Core Challenge:** Ground rover encounters $32\%$ wheel slip in fine Séítah dune sand ripple troughs.
- **Autonomy Behavior:** Aerial scout flies $40\text{ m}$ ahead, maps boundary of loose ripple crests, and identifies a firm lithified bedrock pavement corridor, reducing rover slip to $4.5\%$.

### SCENARIO_09: The Aerial Swarm
- **Core Challenge:** 5-agent heterogeneous fleet (3 aircraft + 2 rovers) partitioned by high crater rim.
- **Autonomy Behavior:** Northern and southern squads continue local bounded autonomous operations without split-brain conflicts; upon link restoration, causal version vectors unify 8 distributed science observations.

### SCENARIO_10: The Perfect Martian Exploration Day
- **Core Challenge:** Full integrated multi-agent exploration sol.
- **Autonomy Behavior:** Combines MEDA climate data ingestion, multi-rotorcraft flight planning, rover advance, in-situ astrobiology target sampling, and 28.4-minute round-trip deep space telemetry downlink.

---

## 4. Master Scenario Verification Matrix

| ID | Title | Key Phenomenon Tested | Autonomy Engine Behavior | Verification Criterion |
|---|---|---|---|---|
| `SCENARIO_01` | The Crater Reveal | Escarpment impasse + rockfall | Surveys rim, discovers 14 boulders, refines route | $62.4\text{ m}$ saved, $59.5\%$ uncertainty drop |
| `SCENARIO_02` | The Lost Aircraft | Mid-flight UHF link loss | Transitions to autonomous contingency landing | Safe touchdown, $74.5\%$ battery preserved |
| `SCENARIO_03` | Thin-Air Challenge | $\rho = 0.0112\text{ kg/m}^3$ thin air | Evaluates $TM < 1.15$, de-rates payload to $0.45\text{ kg}$ | Physical feasibility enforced |
| `SCENARIO_04` | The Dust Wall | $14.2\text{ m/s}$ crosswind gust | Tilts $16.5^\circ$ into wind, drops altitude to $8\text{ m}$ | 6-DOF stability maintained |
| `SCENARIO_05` | Two Aircraft, One Target | Overlapping 4D flight corridors | 4D spatial-temporal cylinder deconfliction | Zero collision, separate corridors reserved |
| `SCENARIO_06` | Dangerous Landing | Primary site slope $14.5^\circ$ | Rejects site, diverts $18.7\text{ m}$ to $2.8^\circ$ terrace | Zero rollover, safe touchdown |
| `SCENARIO_07` | Hidden Ice Mapping | Airborne GPR radar sounding | Maps synthetic dielectric boundary at $3.8\text{ m}$ | Non-probabilistic truth disclosure logged |
| `SCENARIO_08` | Rover Needs Help | Rover wheel slip $32\%$ in dunes | Scout maps firm bedrock egress corridor | Rover wheel slip reduced to $4.5\%$ |
| `SCENARIO_09` | The Aerial Swarm | 5-agent communication partition | Causal vector merge across UHF proximity mesh | Zero split-brain, 8 observations unified |
| `SCENARIO_10` | Perfect Exploration Day | Full end-to-end multi-agent sol | Climate, scouting, rover drive, sampling, DSN | Complete multi-agent sol qualified |

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All scenarios, obstacle profiles, and autonomous contingency procedures cataloged here represent robotic research simulations. They must never be considered certified or safe for human astronauts or manned surface operations.
