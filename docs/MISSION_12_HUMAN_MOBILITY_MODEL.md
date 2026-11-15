# MISSION 12 — HUMAN MOBILITY & BIOMECHANICAL COST MODEL
## Mathematical Formulation, Biomechanics & Terrain Impedance

**Document Version:** 1.0.0  
**Module:** [`src/marswalk/core/astronaut_eva.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/astronaut_eva.py)  
**Classification:** Scientific Modeling Specification  

---

### 1. Fundamental Distinction: Human Biomechanics vs. Rover Terramechanics

Robotic rovers navigate planetary surfaces governed by **Bekker-Wong terramechanics**: wheel sinkage in compressible Martian regolith, grouser thrust shear, slip ratios, motor torque ceilings, and rigid chassis tip-over thresholds.

Suited astronauts on foot navigate according to **human biomechanics and metabolic expenditure**:
1. Active locomotion effort is driven by leg work against gravity, balance stabilization across uneven ground, and mechanical resistance of pressurized space suits.
2. Incline difficulty does not manifest as wheel slip, but as an exponential surge in cardiopulmonary metabolic rate ($\dot{V}_{O_2}$ and $\text{kcal/h}$).
3. Downhill locomotion provides only modest energy recovery, as eccentric muscle braking and descent slip hazards require active stabilization.
4. Carried mass (tools, core drill, rock sample tubes) directly scales the metabolic cost of every step.

---

### 2. Mathematical Formulation of the Human Step Cost

The directed traversal effort $C_{\text{human}}(u \to v)$ between adjacent grid cells $u = (r_1, c_1)$ and $v = (r_2, c_2)$ on an 8-connected digital elevation model is formulated as:

$$C_{\text{human}}(u \to v) = d(u, v) \cdot \left[ 1.0 + P_{\text{slope}}(\theta_{uv}) + P_{\text{roughness}}(\sigma_v) + P_{\text{uphill}}(\Delta z) \right] \cdot M_{\text{payload}}$$

#### 2.1 Variables & Definitions
- $d(u, v)$: Euclidean ground metric distance in meters:
  $$d(u, v) = \sqrt{(\Delta c \cdot \Delta x_{\text{ground}})^2 + (\Delta r \cdot \Delta y_{\text{ground}})^2}$$
- $\Delta z = z(v) - z(u)$: Elevation differential in meters.
- $\theta_{\text{step}} = \arctan\left(\frac{|\Delta z|}{d(u, v)}\right) \cdot \frac{180^\circ}{\pi}$: Direct directional incline along the transition edge.
- $\theta_v = \text{slope\_deg}[v]$: Horn gradient slope at destination cell.
- $\theta_{uv} = \max(\theta_v, \theta_{\text{step}})$: Effective step slope.

#### 2.2 Impassable Suited Barrier (Configurable Cutoff)
If $\theta_{uv} \ge \theta_{\text{max\_walk}}$ (configurable default $20.0^\circ$, illustrative conservative range $15.0^\circ - 20.0^\circ$):
$$C_{\text{human}}(u \to v) = \infty$$

> [!WARNING]
> **Scientific Integrity Disclosure:**
> The $20.0^\circ$ cutoff is an illustrative planning threshold derived from Apollo Lunar Surface EVA operational guidelines (NASA SP-287). It is **NOT** a certified NASA operational limit or flight spacesuit design threshold for Mars.

#### 2.3 Non-Linear Slope Penalty $P_{\text{slope}}$
Adapted from the empirical energy expenditure curves of Minetti et al. (2002) for gradient walking:
$$P_{\text{slope}}(\theta_{uv}) = w_s \cdot \left(\frac{\theta_{uv}}{\theta_{\text{crit}}}\right)^2$$
Where:
- $\theta_{\text{crit}} = 12.0^\circ$ is the critical incline where suited walking effort accelerates.
- $w_s = 2.5$ is the dimensionless slope penalty weighting factor.

#### 2.4 Surface Roughness Penalty $P_{\text{roughness}}$
Accounts for stabilization effort, ankle rollover hazard, and micro-relief in rocky or loose regolith fields:
$$P_{\text{roughness}}(\sigma_v) = w_r \cdot \left(\frac{\sigma_v}{0.5\,\text{m}}\right)$$
Where $\sigma_v$ is the detrended standard deviation of surface elevation (roughness) at cell $v$, and $w_r = 1.8$.

#### 2.5 Asymmetric Uphill Penalty $P_{\text{uphill}}$
Represents gravitational work performed lifting the total suited system mass against Martian gravity ($g_{\text{Mars}} = 3.721\,\text{m/s}^2$):
$$P_{\text{uphill}}(\Delta z) = w_{\text{up}} \cdot \max\left(0.0, \frac{\Delta z}{d(u, v)}\right)$$
Where $w_{\text{up}} = 3.0$.

#### 2.6 Carried Payload Mass Multiplier $M_{\text{payload}}$
$$M_{\text{payload}} = \frac{M_{\text{body}} + M_{\text{suit}} + M_{\text{gear}}}{M_{\text{body}} + M_{\text{suit}}}$$
For baseline parameters:
- $M_{\text{body}} = 80.0\,\text{kg}$
- $M_{\text{suit}} = 60.0\,\text{kg}$
- $M_{\text{gear}} = 25.0\,\text{kg}$ (science tools, sample collection bags, sample tubes)
- $M_{\text{payload}} = \frac{165.0}{140.0} \approx 1.179$ ($+17.9\%$ additional physical effort).

---

### 3. Walking Velocity & Fatigue Derating Model

#### 3.1 Effective Walking Speed $v_{\text{effective}}$
The suited astronaut does not move at constant speed. As terrain impedance increases, pace decelerates:

$$v_{\text{effective}} = \max\left(v_{\text{min}}, \frac{v_0}{\text{Impedance}} \cdot \eta_{\text{cadence}}\right)$$

Where:
- $v_0 = 2.0\,\text{km/h}$ ($0.556\,\text{m/s}$) nominal flat terrain pace.
- $v_{\text{min}} = 1.0\,\text{km/h}$ ($0.278\,\text{m/s}$) lower pace bound.
- $\text{Impedance} = \max\left(1.0, \frac{C_{\text{human}}}{d(u, v)}\right)$.
- $\eta_{\text{cadence}} = 0.85$ (duty cycle: 51 minutes walking, 9 minutes brief operational pause/rest per hour).

#### 3.2 Fatigue Accumulation
For long sorties ($>4.0\text{ hours}$), active walk velocity derates linearly by $3\%$ per elapsed hour of continuous locomotion:
$$v_{\text{fatigued}}(t) = v_{\text{effective}} \cdot \max(0.75, 1.0 - 0.03 \cdot t_{\text{elapsed\_hrs}})$$

---

### 4. Non-Probabilistic Truth Disclosures

In accordance with rule `AGENTS.md` and project scientific integrity standards:
1. **Measured Terrain:** Raw CTX $20\,\text{m}$ digital elevation values extracted directly from USGS PDS archives (DOI: 10.5066/P906QQT8).
2. **Derived Slope:** First-order Horn central differences calculated on 8-neighbor cells.
3. **Modeled Mobility Cost:** Purely deterministic mathematical formulation representing physical effort in *equivalent flat-terrain meters*.
4. **Unverified Traversability:** Sub-pixel hazards ($<20\,\text{m}$ boulders, cracks, crevices, soil bearing capacity) are explicitly designated as *unresolved by CTX imagery* and require on-site astronaut visual confirmation.
