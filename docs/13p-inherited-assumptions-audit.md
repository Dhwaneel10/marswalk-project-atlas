# PROJECT ATLAS — MILESTONE 13P
# INHERITED ASSUMPTIONS AUDIT: 13O PARAMETERS & AERIAL ADAPTATION
## Parameter Classification, Provenance Traceability, and Rover vs. Aircraft Operating Domain Discrepancies

**Milestone:** 13P — Atlas Aerial Corps  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Purpose:** Formal audit of all configuration assumptions and parameters inherited from Milestone 13O (Deep Space Autonomy Lab) prior to integration with planetary aerial flight systems.

---

## 1. Classification Methodology

In accordance with MarsWalk project scientific rules, every inherited parameter is categorized into one of four formal tiers:
1. **Published Physical Value:** Empirically verified universal or astronomical constant derived from standard physical and planetary observations (e.g., speed of light in vacuum, Mars orbital distance range, CO2 molar mass).
2. **Source-Backed Engineering Parameter:** Parameter derived directly from documented spacecraft engineering specifications, NASA/JPL/ESA mission design publications, or telecommunications protocols (e.g., DSN antenna diameters, X-band/UHF frequencies, solar conjunction elongation cutoffs).
3. **Configured Simulation Assumption:** Heuristic or operational threshold chosen for tractable simulation modeling within Project Atlas (e.g., rover detour distance cap, tactical heading deflection limit, battery reserve floor).
4. **Unverified Value:** Numerical assumption without documented primary source or empirical justification.

---

## 2. Comprehensive Inherited Parameter Matrix

| Parameter Name | Inherited 13O Value | Classification | Primary Source / Provenance | Rover Applicability | Aerial Rotorcraft Applicability | Action for Milestone 13P |
|---|---|---|---|---|---|---|
| **Speed of Light ($c$)** | $299,792,458\text{ m/s}$ | **Published Physical Value** | BIPM (1983 definition) | Exact | Exact | **Retain as universal physical constant** |
| **Mars-Earth Distance ($d$)** | $0.372\text{ to }2.683\text{ AU}$ | **Published Physical Value** | NASA JPL Horizons Ephemeris DE440 | Exact | Exact | **Retain for deep space delay calculations** |
| **One-Way Light Time (OWLT)** | $3.1\text{ to }22.3\text{ min}$ (Nominal $14.2\text{ min}$) | **Published Physical Value** | Derived from $d / c$ | Exact | Exact | **Retain for Earth-aircraft flight plan uplink** |
| **Round-Trip Light Time (RTLT)** | $6.2\text{ to }44.6\text{ min}$ (Nominal $28.4\text{ min}$) | **Published Physical Value** | Derived from $2 \times d / c$ | Exact | Exact | **Retain for Earth-aircraft telemetry loop** |
| **Solar Conjunction Cutoff** | Sun-Earth-Probe angle $< 2.0^\circ$ | **Source-Backed Engineering** | NASA DSN Service Catalog / JPL Mars Ops | Exact | Exact | **Retain; no flight plans uplinked during conjunction** |
| **Solar Conjunction Duration** | $14\text{ to }16\text{ sols}$ | **Source-Backed Engineering** | Historical Mars missions (MRO, MSL, M2020) | Exact | Exact | **Retain; aircraft grounded or dormant** |
| **UHF Proximity Frequency** | $401.5\text{ MHz}$ (Ch 1), $435\text{ MHz}$ (Ch 2) | **Source-Backed Engineering** | CCSDS 211.0-B-5, Electra Transceiver Specs | Rover-Orbiter / Rover-Rover | Aircraft-Rover / Aircraft-Orbiter | **Retain for aircraft-to-rover Proximity-1 links** |
| **DSN Ground Stations** | Goldstone ($70\text{m}$), Madrid ($70\text{m}$), Canberra ($70\text{m}$) | **Source-Backed Engineering** | NASA Deep Space Network 810-005 Handbook | Direct-to-Earth uplink | Not applicable directly (via Relay) | **Retain; aircraft communicates via rover/relay** |
| **Relay Overpass Windows** | $8\text{ to }15\text{ min}$ per pass | **Source-Backed Engineering** | MRO, Mars Odyssey, TGO sun-synchronous orbits | Exact | Exact | **Retain for aerial data downlink** |
| **Rover Detour Limit** | $50.0\text{ meters}$ | **Configured Simulation Assumption** | Atlas 13H/13I/13O tactical detour envelope | Valid for rovers | **FATALLY INVALID FOR AIRCRAFT** | **REPLACE with 3D flight corridor ($150-500\text{ m}$)** |
| **Heading Deflection Limit** | $45.0^\circ$ | **Configured Simulation Assumption** | Atlas 13O rover steering curvature limit | Valid for rovers | **INVALID FOR AIRCRAFT** | **REPLACE with full $360^\circ$ yaw agility** |
| **Battery Reserve Floor** | $30.0\%$ | **Configured Simulation Assumption** | Atlas 13F/13O rover survival heater reserve | Valid for rovers | **DANGEROUSLY AMBIGUOUS FOR FLIGHT** | **REPLACE with Landing Reserve + Abort Floor** |

---

## 3. Deep Dive: Why Rover Limits Cannot Be Inherited by Rotorcraft

A fundamental failure mode in multi-agent robotics is treating aerial platforms as "fast rovers with an altitude coordinate." Rotorcraft and ground rovers inhabit completely divergent physics and operational domains:

```
+----------------------------------------------------------------------------------------------------+
|                                    DOMAIN DISCREPANCY COMPARISON                                   |
+----------------------------------------------------------------------------------------------------+
|  CHARACTERISTIC              | GROUND ROVER (Perseverance Class) | MARTIAN ROTORCRAFT (Ingenuity Class)     |
+------------------------------+-----------------------------------+------------------------------------------+
|  Nominal Speed               | 0.04 to 0.12 m/s (2.4 - 7.2 m/min)| 3.0 to 12.0 m/s (180 - 720 m/min)        |
|  Traverse / Flight Medium    | Rigid rock, sand, bedrock         | Low-density CO2 gas (~0.015 - 0.020 kg/m3)|
|  Total System Mass           | ~1,025 kg                         | 1.8 to 4.5 kg (Scout) / 15-20 kg (Mapper)|
|  Energy Storage (Battery)    | 1,500 to 2,500 Wh (RTG/Li-ion)    | 35 to 100 Wh (Sony/Murata VTC4 Li-ion)   |
|  Operational Power Draw      | 60 to 150 W (Drive: ~80-120 W)    | 350 to 550 W (Hover/Climb power)         |
|  Endurance per Charge        | 4.0 to 8.0 hours driving          | 90 to 180 seconds powered flight         |
|  Failure Mode on Power Loss  | Wheels stop; vehicle rests safely | Aerodynamic stall; catastrophic crash    |
+----------------------------------------------------------------------------------------------------+
```

### 3.1. Detour Distance Discrepancy
- For a rover moving at $0.08\text{ m/s}$, a $50\text{ m}$ detour represents $10.4\text{ minutes}$ of sustained locomotion over terrain.
- For an aircraft flying at $8.0\text{ m/s}$, $50\text{ m}$ is traversed in just **$6.25\text{ seconds}$**. An aerial scout typically operates over a mission radius of $200\text{ to }1,000\text{ meters}$. Constraining an aerial detour to $50\text{ m}$ would paralyze flight reconnaissance.
- **Milestone 13P Policy:** Aerial detour envelope is redefined based on remaining flight time and battery margin:
  $$d_{\text{detour, max}} = V_{\text{cruise}} \cdot \left( t_{\text{flight, max}} - t_{\text{elapsed}} - t_{\text{descent\_reserve}} \right)$$

### 3.2. Heading Deflection Discrepancy
- Rovers have mechanical steering angle limits ($< 45^\circ$ instantaneous curvature) to avoid high-centering or wheel scrub damage on sharp rock edges.
- Coaxial and multi-rotor aircraft possess omnidirectional yaw agility ($\dot{\psi} \approx 60-90^\circ/\text{s}$) and can pirouette in hover to any heading prior to initiating translational flight.
- **Milestone 13P Policy:** Heading deflection is governed by rotor torque margins, not rover steering constraints.

### 3.3. Battery Reserve Floor Discrepancy (Safety-Critical)
- If a rover reaches its $30\%$ battery reserve, it safely engages its electro-mechanical brakes and enters dormant trickle-charging.
- If a rotorcraft exhausts its battery while airborne, gravity ($g_{\text{Mars}} = 3.721\text{ m/s}^2$) pulls it into an uncontrolled descent resulting in complete hull destruction.
- **Milestone 13P Policy:** Aircraft enforce a two-tier energy floor:
  1. **Minimum Touchdown Reserve:** At least $20\%$ of battery capacity must remain upon landing gear contact.
  2. **Emergency Landing Trigger:** If current State of Charge drops below the energy required to execute a vertical descent plus reserve ($E_{\text{remain}} \le P_{\text{descent}} \cdot \Delta t_{\text{desc}} + E_{\text{reserve}}$), the aircraft aborts forward flight immediately and initiates `EMERGENCY_LANDING`.

---

## 4. Summary of Adaptations for Milestone 13P

1. **Retain Deep Space Physics:** Speed of light, orbital ephemeris, light-time delays, DSN tracking, and solar conjunction moratoriums are retained without modification.
2. **Decouple Mobility Physics:** Rover ground kinetics and costmaps are isolated from 3D flight dynamics.
3. **Establish Aerodynamic Foundations:** Introduce true thin-atmosphere rotor physics (blade element momentum theory, tip Mach, low-Reynolds drag).
4. **Define Dedicated Aerial Autonomy Modes:** Replace rover stop-and-hold with airborne hover, divert, and emergency landing policies.

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All parameters, vehicle specifications, and operational limits audited in this document are strictly designed for unmanned robotic exploration. None of these parameters or procedures are certified or safe for human astronauts.
