# PROJECT ATLAS — MILESTONE 13P
# AEROSPACE MODEL FOUNDATIONS: MARTIAN ATMOSPHERIC PHYSICS & ROTOR VEHICLE ARCHITECTURE
## Low-Density Gas Dynamics, Low-Reynolds Aerodynamics, and Configurable Aircraft Profiles

**Milestone:** 13P — Atlas Aerial Corps: Multi-Rotorcraft Intelligence, Aerial Science, Flight Dynamics & Rover–Aircraft Cooperation  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Core Implementation:** `src/marswalk/core/mars_rotor_aerodynamics.py` & `src/marswalk/core/mars_aircraft_fleet.py`

---

## 1. Physical Foundations of the Martian Atmosphere

Flying in the atmosphere of Mars presents one of the most demanding challenges in aerospace engineering. The atmospheric surface density of Mars is typically between $0.012\text{ and }0.020\text{ kg/m}^3$—less than $1.5\%$ of Earth's sea-level density ($1.225\text{ kg/m}^3$). This thin medium is equivalent to Earth's stratosphere at an altitude of approximately $30\text{ to }35\text{ kilometers}$ ($100,000\text{ feet}$).

```
+----------------------------------------------------------------------------------------------------+
|                                  EARTH VS. MARS AERODYNAMIC ENVIRONMENT                            |
+----------------------------------------------------------------------------------------------------+
|  PROPERTY                    | EARTH SEA LEVEL (ISA)            | MARS SURFACE (Jezero Crater Nom)  |
+------------------------------+----------------------------------+-----------------------------------+
|  Primary Gas Composition     | N2 (78%), O2 (21%), Ar (1%)      | CO2 (95.3%), N2 (2.6%), Ar (1.9%) |
|  Molar Mass (M)              | 28.966 kg / kmol                 | 44.010 kg / kmol                  |
|  Specific Gas Constant (Rs)  | 287.058 J / (kg * K)             | 188.922 J / (kg * K)              |
|  Surface Pressure (p)        | 101,325 Pa (1,013 mbar)          | 610 Pa (6.1 mbar)                 |
|  Surface Temperature (T)     | 288.15 K (+15.0 C)               | 215.0 K (-58.15 C)                |
|  Atmospheric Density (rho)   | 1.225 kg / m3                    | 0.0150 kg / m3 (1.2% of Earth)    |
|  Ratio of Specific Heats (g) | 1.400                            | 1.290 (Carbon Dioxide)            |
|  Speed of Sound (a)          | 340.29 m / s                     | 228.92 m / s (67% of Earth)       |
|  Dynamic Viscosity (mu)      | 1.789 x 10^-5 Pa * s             | 1.122 x 10^-5 Pa * s              |
|  Kinematic Viscosity (nu)    | 1.460 x 10^-5 m2 / s             | 7.480 x 10^-4 m2 / s (51x Earth)  |
|  Surface Gravity (g)         | 9.807 m / s2                     | 3.721 m / s2 (38% of Earth)       |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Gas Dynamics & Equation of State Formulation

### 2.1. Ideal Gas Law for Martian Carbon Dioxide
Because Martian atmospheric pressures are well below $10\text{ mbar}$ ($1,000\text{ Pa}$), intermolecular forces are negligible, and the gas behaves as an ideal gas governed by:

$$\rho = \frac{p \cdot M_{\text{CO2}}}{R_u \cdot T} = \frac{p}{R_s \cdot T}$$

where:
- $R_u = 8,314.4626\text{ J / (kmol}\cdot\text{K)}$ (Universal Gas Constant).
- $M_{\text{CO2}} = 44.010\text{ kg/kmol}$ (CO2 molar mass).
- $R_s = R_u / M_{\text{CO2}} = 188.922\text{ J / (kg}\cdot\text{K)}$ (Martian specific gas constant).
- Under nominal Jezero conditions ($p = 610.0\text{ Pa}$, $T = 215.0\text{ K}$):
  $$\rho = \frac{610.0}{188.922 \times 215.0} = 0.015018\text{ kg/m}^3$$

### 2.2. Speed of Sound in Martian Carbon Dioxide
Due to the higher molecular mass of CO2 and lower ambient temperatures, the speed of sound on Mars is substantially lower than on Earth:

$$a = \sqrt{\gamma \cdot R_s \cdot T} = \sqrt{1.290 \times 188.922 \times 215.0} = 228.92\text{ m/s}$$

This low speed of sound is critical: a rotor spinning at $160\text{ m/s}$ tip velocity operates at a tip Mach number of $M_{\text{tip}} = 160.0 / 228.92 = 0.70$, already near the transonic drag divergence boundary.

### 2.3. Dynamic & Kinematic Viscosity (Sutherland's Law)
Dynamic viscosity $\mu$ is modeled via Sutherland's law parameterized for CO2:

$$\mu(T) = \mu_0 \left(\frac{T_0 + S}{T + S}\right) \left(\frac{T}{T_0}\right)^{1.5}$$

where $\mu_0 = 1.370 \times 10^{-5}\text{ Pa}\cdot\text{s}$, $T_0 = 273.15\text{ K}$, and Sutherland's constant $S = 222.0\text{ K}$.
Kinematic viscosity $\nu = \mu / \rho$ is roughly **51 times larger** than on Earth, which drastically lowers the aerodynamic Reynolds number.

---

## 3. The Low-Reynolds / High-Mach Paradox

Martian rotorcraft operate in an aerodynamic regime almost never encountered in terrestrial aviation:

$$\text{Low Reynolds Number } (Re \approx 10^4) \quad \times \quad \text{High Mach Number } (M_{\text{tip}} \approx 0.70 - 0.78)$$

1. **Low Reynolds Number ($10,000 \le Re \le 25,000$):**
   - On Earth, helicopter blades operate at $Re \approx 10^6 - 10^7$ with fully turbulent boundary layers.
   - On Mars, laminar boundary layers suffer laminar separation bubbles, leading to high profile drag coefficients ($C_{d0} \approx 0.030 - 0.045$) and limited maximum lift coefficients ($C_{l,\text{max}} \approx 0.70 - 0.85$).
2. **High Advancing Blade Tip Mach ($M_{\text{adv}} = (V_{\text{tip}} + V) / a$):**
   - As the aircraft moves forward at speed $V$, the advancing blade tip speed increases to $V_{\text{tip}} + V$.
   - When $M_{\text{adv}} > 0.72$, transonic shockwaves form on the blade upper surface, triggering wave drag divergence.
   - This compressibility penalty creates a sharp upper limit on forward airspeed ($V_{\text{max}} \approx 10 - 15\text{ m/s}$).

---

## 4. The Three Reference Planetary Aircraft Profiles

Project Atlas defines three distinct reference aircraft classes in `mars_aircraft_fleet.py`:

```
                                  AERIAL CORPS REFERENCE FLEET
                                  
    [ A. LIGHT SCOUT ]                [ B. SCIENCE SCOUT ]               [ C. SCIENCE MAPPER ]
    (Ingenuity Tech Demo)             (Multispectral Research)           (Heavy Radar Explorer)
         1.80 kg                           4.50 kg                            18.50 kg
    Coaxial 1.21m Diam                Coaxial 1.45m Diam                 Hexarotor 2.50m Span
      2537 Nom RPM                      2350 Nom RPM                       1950 Nom RPM
      35 Wh Battery                     85 Wh Battery                      360 Wh Battery
     0.0 kg Payload                    0.7 kg Payload                     3.5 kg Payload
```

### Profile A: LIGHT SCOUT (Ingenuity-Inspired Technology Demonstrator)
- **Primary Mission:** Rapid forward scouting, local landing site verification, and rover traverse clearance.
- **Dry Mass:** $1.80\text{ kg}$; Payload: $0.00\text{ kg}$ (Navigation camera only). Total Mass: $1.80\text{ kg}$.
- **Rotor Configuration:** Coaxial counter-rotating dual rotor, $R = 0.605\text{ m}$ ($1.21\text{ m}$ diameter), 4 total blades.
- **Rotor Speed:** $2,400\text{ to }2,800\text{ RPM}$ (Nominal $2,537\text{ RPM}$).
- **Energy Storage:** $35.0\text{ Wh}$ Li-ion battery ($6\times$ Sony Murata VTC4 cells in series).
- **Nominal Endurance:** $90\text{ to }170\text{ seconds}$; Max Flight Speed: $10.0\text{ m/s}$.

### Profile B: SCIENCE SCOUT (Research Rotorcraft)
- **Primary Mission:** Direct scientific waypoint acquisition carrying visible stereo cameras and near-infrared spectrometers.
- **Dry Mass:** $3.80\text{ kg}$; Nominal Payload: $0.70\text{ kg}$ (Max $1.00\text{ kg}$). Total Mass: $4.50\text{ kg}$.
- **Rotor Configuration:** Coaxial counter-rotating dual rotor, $R = 0.725\text{ m}$ ($1.45\text{ m}$ diameter), 4 blades.
- **Rotor Speed:** $2,200\text{ to }2,650\text{ RPM}$ (Nominal $2,350\text{ RPM}$).
- **Energy Storage:** $85.0\text{ Wh}$ high-energy Li-ion battery pack.
- **Nominal Endurance:** $180\text{ to }300\text{ seconds}$; Max Flight Speed: $12.0\text{ m/s}$.

### Profile C: SCIENCE MAPPER (Conceptual Heavy Planetary Aircraft)
- **Primary Mission:** Regional stratigraphic mapping carrying Ground-Penetrating Radar (GPR) and multispectral mapping gimbals.
- **Dry Mass:** $15.00\text{ kg}$; Nominal Payload: $3.50\text{ kg}$ (Max $5.00\text{ kg}$). Total Mass: $18.50\text{ kg}$.
- **Rotor Configuration:** Hexarotor (6 rotors, $R = 0.625\text{ m}$ each, effective span $2.50\text{ m}$).
- **Rotor Speed:** $1,600\text{ to }2,300\text{ RPM}$ (Nominal $1,950\text{ RPM}$).
- **Energy Storage:** $360.0\text{ Wh}$ advanced space-rated battery pack.
- **Nominal Endurance:** $400\text{ to }600\text{ seconds}$ ($6.5 - 10\text{ minutes}$); Max Flight Speed: $15.0\text{ m/s}$.

---

## 5. Non-Probabilistic Truth Disclosures

1. **No Real Flight Certification:** All aircraft specifications represent simulation models constructed for computational mission design. They do not represent flight-certified FAA, NASA, or ESA flight software.
2. **Provenanced Empirical Baselines:** Equations of state, specific gas constants, and Sutherland constants are grounded in NASA SP-8010 and Mars 2020 MEDA publications.

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All aerodynamic models, gas dynamic equations, and vehicle specifications documented here apply strictly to unmanned robotic rotorcraft. They must NEVER be interpreted as flight-certified or safe for human astronauts.
