# Milestone 13Y: Planetary Communications & Delay-Tolerant Networking Research Foundation

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13Y — Atlas Planetary Network  
**Author:** Deep Space Communications & Autonomous Systems Division  
**Classification:** Research Simulation Specification & Theoretical Foundation

---

## 1. Executive Summary & Historical Context

Planetary exploration communications have historically relied on direct-to-Earth (DTE) links via the Deep Space Network (DSN) augmented by single-hop proximity relay orbiters (e.g., Mars Global Surveyor, 2001 Mars Odyssey, Mars Reconnaissance Orbiter, Trace Gas Orbiter, and MAVEN).

As robotic exploration scales to multi-rover fleets, high-cadence aerial reconnaissance, distributed ISRU outposts, and permanent crewed settlements, point-to-point DTE links encounter fundamental physical bottlenecks:
1. **Geometric Visibility:** Planetary rotation and orbital mechanics impose periodic occultations (Martian night and line-of-sight obstruction).
2. **Extreme Propagation Delays:** Earth–Mars one-way light time varies from $3.1\text{ minutes}$ (at conjunction opposition minimum $0.37\text{ AU}$) to $22.2\text{ minutes}$ (at superior conjunction maximum $2.68\text{ AU}$).
3. **Severe Solar Conjunction Blackouts:** Every $\sim 26\text{ months}$, Mars passes behind the Sun from Earth's perspective, inducing coronal scintillation, extreme noise, and complete telemetry blackouts for 10–14 days.
4. **Bandwidth Asymmetry:** Surface exploration units have constrained power ($\sim 5\text{ W}$ to $100\text{ W}$ RF) and compact antennas, while orbiters carry high-gain directional antennas and high-power transmitters.

Milestone 13Y establishes the computational architecture for an end-to-end **Martian Planetary Network**, combining orbital relay constellations, inter-settlement terrestrial networks, and Delay-Tolerant Networking (DTN).

---

## 2. Standards & Theoretical References

### 2.1 RFC 9171 — Bundle Protocol Version 7 (BPv7)
The Consultative Committee for Space Data Systems (CCSDS 734.2-B-1) and IETF RFC 9171 define the Bundle Protocol for environments characterized by high delay, intermittent connectivity, and high error rates.
Key principles utilized in Atlas 13Y:
- **Custody Transfer:** Intermediate nodes accept custody of bundles until confirmed delivered to the next custodial node.
- **Store-and-Forward Architecture:** Nodes store bundles persistently in non-volatile buffer queues when no active contact window is open.
- **Bundle Lifecycle State Machine:**
  $$\text{CREATED} \longrightarrow \text{QUEUED} \longrightarrow \text{TRANSMITTING} \longrightarrow \text{RECEIVED} \longrightarrow \text{STORED} \longrightarrow \text{FORWARDING} \longrightarrow \text{DELIVERED}$$
  Terminal/failure states: $\text{EXPIRED}$, $\text{CORRUPTED}$, $\text{DROPPED}$.
- **Bundle Priorities:** Strict priority queuing to ensure critical life-support, emergency, and command bundles pre-empt routine telemetry and bulk science imagery.

### 2.2 Contact Graph Routing (CGR) & LunaNet Interoperability
- **Predictable Topology Dynamics:** Unlike terrestrial mobile ad-hoc networks (MANETs), planetary orbital dynamics are deterministic. Planetary and orbital contact windows $[t_{\text{start}}, t_{\text{end}}]$ can be pre-calculated months in advance using celestial ephemerides.
- **Time-Dependent Contact Graphs:** Vertices represent planetary and orbital nodes; directed edges represent time-bounded contact opportunities with finite capacity (bytes) and latency ($t_{\text{prop}} + t_{\text{tx}}$).
- **LunaNet & Mars Relay Network Architecture:** Emulates NASA/ESA Mars Relay Operations Service (MaROS) scheduling patterns, providing multi-mission relay support for surface landers, rovers, and regional outposts.

---

## 3. Physical Principles & Formulation

### 3.1 Planetary Orbital Mechanics & Occultation
Mars physical constants:
- Mean radius: $R_M = 3,396.19\text{ km} = 3,396,190\text{ m}$
- Standard gravitational parameter: $\mu_M = G M_M = 4.282837 \times 10^{13}\text{ m}^3/\text{s}^2$
- Mars rotation period (1 sol): $88,775.244\text{ s}$ ($24\text{ h } 39\text{ m } 35.244\text{ s}$)
- Second zonal harmonic: $J_2 = 1.96045 \times 10^{-3}$

The two-body equation of motion with $J_2$ secular secular node regression and argument of periapsis drift:
$$\dot{\Omega} = -\frac{3}{2} J_2 \left(\frac{R_M}{p}\right)^2 n \cos(i)$$
$$\dot{\omega} = \frac{3}{4} J_2 \left(\frac{R_M}{p}\right)^2 n (5 \cos^2(i) - 1)$$
where $a$ is semi-major axis, $e$ is eccentricity, $p = a(1 - e^2)$ is semi-latus rectum, $i$ is inclination, and $n = \sqrt{\mu / a^3}$ is mean motion.

**Line-of-Sight Occultation:**
For two points $\vec{r}_1$ and $\vec{r}_2$ in Mars-centered coordinates, the ray vector is $\vec{d} = \vec{r}_2 - \vec{r}_1$.
The closest distance of the ray path to the center of Mars ($R_{\text{min}}$) is:
$$t^* = -\frac{\vec{r}_1 \cdot \vec{d}}{|\vec{d}|^2}$$
If $0 < t^* < 1$, then $\vec{r}^* = \vec{r}_1 + t^* \vec{d}$, and:
$$R_{\text{min}} = |\vec{r}^*|$$
Occultation occurs if $R_{\text{min}} \le R_M + h_{\text{atm\_mask}}$ (where $h_{\text{atm\_mask}} \approx 20\text{ km}$ accounts for atmospheric refraction/extinction).

For a surface ground station $\vec{r}_{\text{surf}}$, the orbiter must also satisfy an elevation mask angle $\theta_{\text{elev}} \ge \theta_{\text{min}}$ (typically $10^\circ$ above local horizontal):
$$\sin(\theta_{\text{elev}}) = \frac{(\vec{r}_{\text{orb}} - \vec{r}_{\text{surf}}) \cdot \hat{n}_{\text{up}}}{|\vec{r}_{\text{orb}} - \vec{r}_{\text{surf}}|}$$

### 3.2 RF Link Budget & Achievable Capacity
For carrier frequency $f$, wavelength $\lambda = c / f$, and slant range distance $R = |\vec{r}_2 - \vec{r}_1|$:
1. **Free-Space Path Loss ($FSPL$):**
   $$FSPL\text{ (dB)} = 20 \log_{10}\left(\frac{4 \pi R}{\lambda}\right) = 20 \log_{10}(R) + 20 \log_{10}(f) - 147.55$$
2. **Equivalent Isotropically Radiated Power ($EIRP$):**
   $$EIRP\text{ (dBW)} = P_{tx}\text{ (dBW)} + G_{tx}\text{ (dBi)} - L_{tx}\text{ (dB)}$$
3. **Carrier-to-Noise Spectral Density ($C/N_0$):**
   $$P_{rx}\text{ (dBW)} = EIRP - FSPL + G_{rx}\text{ (dBi)} - L_{pointing} - L_{atm}$$
   $$N_0\text{ (dBW/Hz)} = 10 \log_{10}(k_B) + 10 \log_{10}(T_{sys})$$
   where $k_B = 1.380649 \times 10^{-23}\text{ J/K}$ (Boltzmann constant) and $T_{sys}$ is receiver system noise temperature (K).
   $$C/N_0\text{ (dB-Hz)} = P_{rx} - N_0$$
4. **Energy per Bit to Noise Ratio ($E_b/N_0$) & Data Rate:**
   $$\frac{E_b}{N_0}\text{ (dB)} = C/N_0 - 10 \log_{10}(R_{\text{data}})$$
   Given target required $(E_b/N_0)_{\text{req}}$ (e.g. $2.5\text{ dB}$ for rate $1/2$ LDPC code) with link margin $M \ge 3.0\text{ dB}$:
   $$R_{\text{data, max}} = 10^{(C/N_0 - (E_b/N_0)_{\text{req}} - M) / 10}\text{ bits/second}$$

### 3.3 Speed-of-Light & Serialization Latency
Total transmission duration for payload of $S$ bytes ($8S$ bits):
$$t_{\text{tx}} = \frac{8 S}{R_{\text{data}}}$$
Total one-way propagation latency:
$$t_{\text{prop}} = \frac{R}{c}$$
Earliest arrival timestamp at receiver:
$$t_{\text{arrival}} = t_{\text{tx\_start}} + t_{\text{tx}} + t_{\text{prop}}$$
This enforces the fundamental relativistic causality invariant: **no packet or bundle can ever be delivered before $t_{\text{create}} + t_{\text{tx}} + t_{\text{prop}}$**.

---

## 4. Operational Nodes & Topology

```
+-----------------------------------------------------------------------------------+
|                            EARTH GROUND SEGMENT                                   |
|                Deep Space Network (DSN: Goldstone, Madrid, Canberra)               |
+-----------------------------------------------------------------------------------+
                                         ^
                                         | X-band / Ka-band (8.4 GHz / 32 GHz)
                                         | Range: 0.37 AU - 2.68 AU
                                         v
+-----------------------------------------------------------------------------------+
|                        ORBITAL RELAY CONSTELLATION                                |
|  - ATLAS-ORB-01 (Ares-SunSync, Circular 400 km polar, MRO/TGO proxy)              |
|  - ATLAS-ORB-02 (Hellas-Polar, 400x1200 km elliptical, science/relay proxy)       |
|  - ATLAS-ORB-03 (Areostationary High-Altitude Relay, 17,032 km equatorial)        |
|  - ATLAS-ORB-04 (Odyssey-UHF, Circular 390 km polar, dedicated proximity relay)   |
+-----------------------------------------------------------------------------------+
                                   |         |
      UHF (401.5 MHz) / X-band    |         | UHF / Optical
      Range: 390 km - 2,500 km    v         v
+---------------------------------------+ +---------------------------------------+
|        MARS BASE ALPHA (Jezero)       | |      SCIENCE OUTPOST BETA (Nili)      |
| - High-Gain Mast Antenna (Class 1)    | | - Medium-Gain Directional Dish        |
| - 100 GB Primary DTN Storage Buffer   | | - 25 GB Science DTN Storage Buffer    |
| - Habitat Life-Support Telemetry      | | - Active Geochemical Analysis Stream  |
+---------------------------------------+ +---------------------------------------+
            ^                                         ^
            | Terrestrial Line-of-Sight Mesh         | Direct Point-to-Point
            | Surface Relay Towers / UHF              | Microwave / Optical
            v                                         v
+---------------------------------------+ +---------------------------------------+
|       RESOURCE OUTPOST GAMMA (Syrtis) | |      MOBILE ASSETS & ROVERS           |
| - Subsurface Ice Mining Telemetry     | | - ROVER-ALPHA-01, SCOUT-BETA-02       |
| - Automated Sintering Plant Status    | | - HEXACOPTER-AERO-01                  |
| - 50 GB Industrial Buffer             | | - 500 MB Constrained Buffers          |
+---------------------------------------+ +---------------------------------------+
```

---

## 5. Non-Probabilistic Scientific Disclosures & Limitations

1. **Keplerian & Perturbative Modeling:** Atlas uses an analytical two-body Keplerian propagator with $J_2$ secular node drift and harmonic perturbation. While highly accurate for multi-sol operational scheduling, it does not incorporate full 50x50 spherical harmonic gravity fields (e.g. MRO110C) or third-body solar/phobos perturbations.
2. **Atmospheric Attenuation:** Mars atmospheric attenuation is minimal compared to Earth due to low surface pressure ($\sim 600\text{ Pa}$), but dust storm opacity ($\tau \ge 2.5$) can degrade optical/laser communications. Radio links (UHF and X-band) are largely immune to dust attenuation.
3. **DTN Protocol Compliance:** The bundle engine implements the core architecture, state transitions, custody transfer, and priority scheduling inspired by RFC 9171 (BPv7). It is a research simulation engine and does not claim official NASA/CCSDS flight qualification or full cryptographic bundle security protocol (BPSec) implementation.
4. **Model Boundaries:** Model results reflect theoretical and simulated performance and must not be interpreted as operational NASA mission plans or human-rated life-support communications guarantees.
