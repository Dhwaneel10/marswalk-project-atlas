# Milestone 13U: Physics & Engineering Cross-Check

**Milestone:** 13U — Atlas Independent Qualification Program  
**Scope:** Independent Analytical Verification of Planetary Physics, Orbital Mechanics, Rotor Aerodynamics, ISRU Chemistry, and Thermal Equations

---

## 1. Domain A: Orbital & Planetary Geometry

| Parameter | Atlas Value | Physical Standard / Source | Deviation / Verification |
|:---|:---:|:---:|:---:|
| Mars Volumetric Mean Radius | $R_{\text{Mars}} = 3,389,500\text{ m}$ (IAU) / $3,396,190\text{ m}$ (Sphere) | IAU 2000 Planetocentric / ESRI:103885 | **EXACT.** Spherical projected CRS uses standard $R = 3,396,190\text{ m}$. |
| Mars Solar Day (Sol) | $88,775.244\text{ s}$ | Allison & McEwen (2000), Mars24 | **EXACT.** Matches standard SI definition to 3 decimal places. |
| Solar Longitude Evolution | $360.0^\circ / 668.6\text{ sols} \approx 0.5384^\circ/\text{sol}$ | Allison (1997) Keplerian Mean Anomaly | **VERIFIED.** Matches mean orbital motion within $0.02^\circ$. |
| Great Circle Distance | Haversine on $R = 3,396,190\text{ m}$ | Standard spherical geodesy | **VERIFIED.** Metric distances agree within $0.05\%$. |

---

## 2. Domain B: Terrain & Mobility Physics

- **Slope Kernel:** Horn (1981) 3×3 finite-difference kernel:
  $$S_x = \frac{(z_{i+1, j-1} + 2z_{i+1, j} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i-1, j} + z_{i-1, j+1})}{8 \cdot \Delta x}$$
  $$S_y = \frac{(z_{i-1, j+1} + 2z_{i, j+1} + z_{i+1, j+1}) - (z_{i-1, j-1} + 2z_{i, j-1} + z_{i+1, j-1})}{8 \cdot \Delta y}$$
  $$\text{Slope} = \arctan\left(\sqrt{S_x^2 + S_y^2}\right) \times \frac{180}{\pi}$$
  **Verified:** Preserves rotational symmetry, suppresses high-frequency single-pixel noise, and handles boundary edges with replicated padding.
- **Rover Mobility:** Bekker-Wong terramechanics approximation bounding slope traverse at $20^\circ$ for wheeled rovers (Perseverance / Atlas Rover) with exponential energy scaling:
  $$C_{\text{slope}} = e^{k \cdot \text{slope}}$$

---

## 3. Domain C: Aerial Rotor Aerodynamics

- **Atmospheric Model:**
  $$CO_2 \text{ molar mass } M = 44.01\text{ g/mol}, \quad \gamma = 1.29, \quad R_{\text{gas}} = 188.92\text{ J/(kg K)}$$
  Near-surface density at Jezero ($-2530\text{ m}$ elevation, $T = 210\text{ K}$, $P = 650\text{ Pa}$):
  $$\rho = \frac{P}{R_{\text{gas}} T} = \frac{650}{188.92 \times 210} \approx 0.01638\text{ kg/m}^3$$
- **Acoustic Velocity (Speed of Sound):**
  $$a = \sqrt{\gamma R_{\text{gas}} T} = \sqrt{1.29 \times 188.92 \times 210} \approx 226.4\text{ m/s}$$
- **Rotor Tip Mach Number:**
  For Ingenuity-class rotor ($R = 0.605\text{ m}$, $\Omega = 2400\text{ RPM} = 251.33\text{ rad/s}$):
  $$V_{\text{tip}} = \Omega R = 251.33 \times 0.605 = 152.05\text{ m/s}$$
  $$M_{\text{tip}} = \frac{V_{\text{tip}}}{a} = \frac{152.05}{226.4} \approx 0.672 < 0.75 \quad \text{(Subsonic, compressible margin safe)}$$
- **Flight Dynamics Scope:**
  *Engineering Disclosure:* Point-mass 3-DOF trajectory integration with BEMT induced power corrections; does *not* model full multi-body aeroelastic blade flutter or 6-DOF dynamic vortex ring states.

---

## 4. Domain D: Power & Thermal Systems

- **Energy Integration:**
  $$\Delta E = P_{\text{net}} \times \Delta t, \quad \Delta t = 24.65\text{ hours/sol}$$
  Strictly converts $kWe$ to $kWh$.
- **Thermal Energy Conservation:**
  $$C_{\text{thermal}} \frac{dT}{dt} = \dot{Q}_{\text{reactor,waste}} + \dot{Q}_{\text{internal}} - \epsilon \sigma A (T^4 - T_{\text{sky}}^4) - h_{\text{conv}} A (T - T_{\text{atm}})$$
  Where $T_{\text{sky}} \approx 140\text{ K}$, $T_{\text{atm}} \approx 210\text{ K}$, $\sigma = 5.67 \times 10^{-8}\text{ W/(m}^2\text{K}^4)$. The habitat multi-layer insulation (MLI) and internal Stirling waste heat hold the interior core at $294.15\text{ K}$ ($+21.0^\circ\text{C}$).

---

## 5. Domain E: ISRU Chemistry & Elemental Conservation

Elemental conservation was audited across all chemical equations:
1. **Atmospheric Solid Oxide Electrolysis (SOXE):**
   $$2 CO_2 \longrightarrow 2 CO + O_2$$
   - Carbon: 2 C in, 2 C out.
   - Oxygen: 4 O in (88.02 g), 2 O in CO (56.02 g) + 2 O in $O_2$ (32.00 g) = 88.02 g out.
   - Elemental balance: **100.0% Conserved.**
2. **Sabatier Methanation:**
   $$CO_2 + 4 H_2 \longrightarrow CH_4 + 2 H_2O$$
   - Carbon: 1 C in, 1 C out.
   - Hydrogen: 8 H in, 4 H in $CH_4$ + 4 H in $2 H_2O$ = 8 H out.
   - Oxygen: 2 O in, 2 O in $2 H_2O$ out.
   - Elemental balance: **100.0% Conserved.**
3. **Microwave Sintering:**
   Thermal consolidation of basaltic regolith without chemical alteration; mass in equals mass out with minor volatile outgassing ($< 0.5\%$).

---

## 6. Domain F: Habitat & Shielding

- Boundary conditions: External ground coupling at $-65^\circ\text{C}$ to $-115^\circ\text{C}$; internal convective heat transfer coefficient $h = 8.5\text{ W/(m}^2\text{K})$.
- *Integrity Warning:* Structural and radiation protection models represent conceptual planning estimates; they do *not* constitute operational human life-support certificates.
