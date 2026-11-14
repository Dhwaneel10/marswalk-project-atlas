# Atlas Mission Energy: Mathematical Formulations & Derivation Proofs

## 1. Physical Constants & Planetary Datum

All calculations in the Atlas Resource Intelligence Subsystem operate strictly under the standard International System of Units (SI) with explicit Martian datum parameters:

| Parameter | Symbol | Nominal Value | Units | Provenance / Standard |
|---|---|---|---|---|
| Martian Surface Gravity | $g_{\text{Mars}}$ | $3.71$ | $\text{m/s}^2$ | NASA Planetary Fact Sheet (Engineering Nominal) |
| IAU Mars Spheroid Radius | $R_{\text{Mars}}$ | $3,396,190.0$ | $\text{m}$ | IAU / IAG Working Group 2000 |
| Jezero Grid West-East Resolution | $dx$ | $18.972887$ | $\text{m}$ | USGS CTX DTM at $18.442^\circ\text{ N}$ Latitude |
| Jezero Grid North-South Resolution | $dy$ | $20.0$ | $\text{m}$ | USGS CTX DTM Meridian Pitch |
| Energy Conversion Factor | — | $3600.0$ | $\text{J/Wh}$ | Exact SI Identity ($1\text{ Wh} = 3600\text{ J}$) |

---

## 2. Geospatial Anisotropic Distance Formulation

Because the Jezero Crater USGS CTX DTM grid is sampled in equirectangular coordinates (Plate Carrée projection) centered near latitude $\phi \approx 18.442^\circ\text{ N}$, grid steps exhibit longitudinal convergence.

Given a coordinate displacement $\Delta \text{row} = r_2 - r_1$ and $\Delta \text{col} = c_2 - c_1$:

$$\Delta x = \Delta \text{col} \cdot dx = \Delta \text{col} \cdot 18.972887\text{ m}$$
$$\Delta y = \Delta \text{row} \cdot dy = \Delta \text{row} \cdot 20.0\text{ m}$$
$$d_{\text{horiz}} = \sqrt{(\Delta x)^2 + (\Delta y)^2}$$

The 3D surface arc length traversed across elevation change $\Delta z = z_2 - z_1$ is:

$$d_{\text{3D}} = \sqrt{d_{\text{horiz}}^2 + (\Delta z)^2}$$

The local traverse slope angle $\theta$ is:

$$\theta = \arctan\left(\frac{|\Delta z|}{d_{\text{horiz}}}\right) \quad (\text{radians})$$

---

## 3. Terramechanical Mobility Work Derivations

### 3.1. Rolling Resistance on Regolith
Martian regolith behaves as a compressible granular medium. Rolling resistance arises from sinkage, soil compaction, and wheel tread deformation. The normal contact force on a slope of inclination $\theta$ is:

$$F_N = m \cdot g_{\text{Mars}} \cdot \cos(\theta)$$

The resistive rolling friction force is:

$$F_r = C_{rr} \cdot F_N = C_{rr} \cdot m \cdot g_{\text{Mars}} \cdot \cos(\theta)$$

Where $C_{rr}$ is the dimensionless rolling resistance coefficient ($0.08$ nominal for wheeled rovers on cohesive Jezero sandy regolith). The mechanical work required to overcome rolling resistance across 3D distance $d$ is:

$$W_r = F_r \cdot d = C_{rr} \cdot m \cdot g_{\text{Mars}} \cdot \cos(\theta) \cdot d \quad [\text{Joules}]$$

### 3.2. Gravitational Potential Work
When ascending or descending a slope, gravitational force acts parallel to the incline:

$$F_g = m \cdot g_{\text{Mars}} \cdot \sin(\theta)$$

The gravitational work done along the incline is:

$$W_g = F_g \cdot d = m \cdot g_{\text{Mars}} \cdot \sin(\theta) \cdot d$$

Substituting $\sin(\theta) = \frac{\Delta z}{d}$, this reduces identically to the potential energy difference:

$$W_g = m \cdot g_{\text{Mars}} \cdot \Delta z \quad [\text{Joules}]$$

Where:
- $\Delta z > 0$ represents an ascent (climbing uphill against gravity).
- $\Delta z < 0$ represents a descent (moving downhill with gravity).

### 3.3. Descent Energy Formulation (Conservative Modeling Assumption)
On terrestrial electric passenger vehicles, descents frequently utilize regenerative braking to recharge traction storage ($W_g < 0 \implies \Delta E < 0$).

For planetary exploration traverses, MarsWalk adopts a **conservative configurable modeling assumption** by setting `allow_regenerative_braking: False` by default. This ensures that traverse planning algorithms do not rely on speculative or unverified energy recapture during slope descent to maintain safety margins. Unless rover-specific technical documentation and certified flight telecommand protocols validate in-situ regenerative charging into cold-regime flight batteries through high gear-ratio planetary actuators, gravitational descent work ($W_g < 0$) is modeled as dissipated torque/heat rather than battery recharge.

Therefore, under the conservative baseline assumption, downhill gravitational work does **not** offset rolling compaction resistance:

$$W_{\text{mech}} = W_r + \max(0, W_g) = m \cdot g_{\text{Mars}} \left( C_{rr} \cdot \cos(\theta) \cdot d + \max(0, \Delta z) \right)$$

When optional regenerative braking is explicitly enabled by the operator for experimental studies, recovery efficiency $\eta_{\text{regen}} = 0.35$ applies to descents:

$$W_{\text{mech, regen}} = W_r + \begin{cases} W_g & \text{if } W_g \ge 0 \\ \eta_{\text{regen}} \cdot W_g & \text{if } W_g < 0 \end{cases}$$

### 3.4. Drivetrain Losses & Motor Electrical Energy
With electromechanical drivetrain efficiency $\eta_{\text{drive}} \in (0, 1]$ ($0.72$ nominal):

$$E_{\text{mobility}} = \frac{W_{\text{mech}}}{\eta_{\text{drive}}} \quad [\text{Joules}]$$

Converted to Watt-hours:

$$E_{\text{mobility, Wh}} = \frac{E_{\text{mobility}}}{3600.0}$$

---

## 4. Subsystem Electrical Energy Budgeting

### 4.1. Traverse Drive Time
Given nominal drive velocity $v_{\text{drive}}$ ($0.38\text{ m/s}$ nominal), segment travel duration is:

$$t_{\text{drive}} = \frac{d}{v_{\text{drive}}} \quad [\text{seconds}]$$

### 4.2. Baseline & Auxiliary Power Loads
During the drive phase, the rover consumes auxiliary electrical power:
- Baseline Avionics: $P_{\text{base}}$ ($110\text{ W}$)
- Radio Receive / Telemetry: $P_{\text{rx}}$ ($15\text{ W}$)
- Transmit (when actively linked to relay/base): $P_{\text{tx}}$ ($45\text{ W}$)

$$E_{\text{aux, segment}} = (P_{\text{base}} + P_{\text{rx}} + \delta_{\text{tx}} P_{\text{tx}}) \cdot t_{\text{drive}} \quad [\text{Joules}]$$

### 4.3. Mission Dwell & Scientific Activities
When the rover stops at a waypoint for sample acquisition, contact drilling, or Mastcam-Z imaging:

$$E_{\text{science}} = (P_{\text{base}} + P_{\text{inst}} + P_{\text{tx}}) \cdot t_{\text{dwell}} \quad [\text{Joules}]$$

Where $P_{\text{inst}} = 120\text{ W}$ and $t_{\text{dwell}} = 900\text{ s}$ ($15\text{ minutes}$ nominal).

When deploying a promontory relay tower:

$$E_{\text{deploy}} = (P_{\text{base}} + P_{\text{mast\_motor}}) \cdot t_{\text{deploy}} \quad [\text{Joules}]$$

Where $P_{\text{mast\_motor}} = 65\text{ W}$ and $t_{\text{deploy}} = 1200\text{ s}$ ($20\text{ minutes}$ nominal).

---

## 5. Battery State of Charge & Reserve Margins

### 5.1. Energy Conservation Invariant
For an initial battery capacity $E_{\text{usable}}$:

$$E_{\text{rem}}(t) = E_{\text{usable}} - \sum_{i=1}^{k} E_i$$

At all times, the system enforces First-Law Energy Conservation:

$$|E_{\text{usable}} - (E_{\text{rem}}(t) + E_{\text{consumed}}(t))| \le 10^{-4}\text{ J}$$

### 5.2. State of Charge (SOC) Percentage
$$\text{SOC}(t) = \left( \frac{E_{\text{rem}}(t)}{E_{\text{usable}}} \right) \cdot 100\%$$

### 5.3. Usable Reserve Margin
Given configured reserve percentage $\text{Reserve}_{\text{pct}}$ ($20\%$ nominal):

$$E_{\text{reserve\_floor}} = E_{\text{usable}} \cdot \left(\frac{\text{Reserve}_{\text{pct}}}{100}\right)$$
$$E_{\text{margin}} = E_{\text{rem}}(t_{\text{end}}) - E_{\text{reserve\_floor}}$$
$$\text{Margin}_{\text{pct}} = \text{SOC}(t_{\text{end}}) - \text{Reserve}_{\text{pct}}$$

- If $\text{Margin}_{\text{pct}} \ge 0$: Traverse is fully feasible with reserve intact.
- If $-\text{Reserve}_{\text{pct}} < \text{Margin}_{\text{pct}} < 0$: Low reserve warning.
- If $\text{Margin}_{\text{pct}} \le -\text{Reserve}_{\text{pct}}$: Critical energy exhaustion violation ($E_{\text{rem}} \le 0$).

---

## 6. Deterministic Sensitivity & Elasticity Formulations

To quantify how sensitive the total energy consumption $E_{\text{total}}$ is to variations in engineering assumptions, the system computes the dimensionless elasticity $S_p$ for each parameter $p$:

$$S_p = \frac{\partial E / E}{\partial p / p} = \frac{\Delta E / E_{\text{baseline}}}{\Delta p / p_{\text{baseline}}}$$

For discrete parameter sweeps with $\pm 20\%$ perturbation:

$$S_p \approx \frac{E(1.20 \cdot p) - E(0.80 \cdot p)}{0.40 \cdot E_{\text{baseline}}}$$

### 6.1. Analytical Baseline Elasticities (Perseverance Nominal Traverse)
Empirical evaluations across the Jezero Octavia Butler to Delta Rim traverse yield:
1. **Drivetrain Efficiency ($\eta$):** $S_{\eta} \approx -0.814$ (Highest elasticity; reducing efficiency drastically increases energy).
2. **Vehicle Mass ($m$):** $S_m \approx +0.659$ (Linear impact on rolling resistance and climbing work).
3. **Driving Speed ($v$):** $S_v \approx -0.385$ (Slower speeds prolong traverse duration, increasing cumulative baseline avionics draw).
4. **Rolling Resistance ($C_{rr}$):** $S_{C_{rr}} \approx +0.356$ (Direct multiplier on rolling compaction work).
5. **Base Avionics Load ($P_{\text{base}}$):** $S_{P_{\text{base}}} \approx +0.341$ (Continuous electrical drain).
6. **Battery Capacity ($E_{\text{usable}}$):** $S_{E_{\text{usable}}} = 0.000$ (Battery size changes remaining margin, but does not alter the energy demanded by the mission).
