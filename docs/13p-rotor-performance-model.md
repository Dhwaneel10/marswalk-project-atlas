# PROJECT ATLAS — MILESTONE 13P
# ROTOR AERODYNAMIC PERFORMANCE MODEL: MOMENTUM THEORY, BEM, AND TRANSLATIONAL LIFT
## Thin-Atmosphere Hover Dynamics, Compressibility Corrections, Forward Flight Bucket Curves, and Power Budgets

**Milestone:** 13P — Atlas Aerial Corps: Multi-Rotorcraft Intelligence, Aerial Science, Flight Dynamics & Rover–Aircraft Cooperation  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Core Implementation:** `src/marswalk/core/mars_rotor_aerodynamics.py` & `src/marswalk/core/mars_aircraft_performance.py`

---

## 1. Classical Momentum Theory in Thin Planetary Atmospheres

To generate aerodynamic lift in an atmosphere with density $\rho \approx 0.015\text{ kg/m}^3$, a rotor must impart substantial downward momentum to a large mass flow of air.

### 1.1. Hover Thrust Equilibrium
In steady hover at altitude $z$, vertical thrust $T$ must exactly balance vehicle weight:

$$T = m \cdot g_{\text{Mars}} = m \cdot 3.721\text{ m/s}^2$$

For the $1.80\text{ kg}$ Light Scout (Ingenuity profile):
$$T_{\text{hover}} = 1.80\text{ kg} \times 3.721\text{ m/s}^2 = 6.6978\text{ N}$$

### 1.2. Rotor Disk Loading & Inflow Velocity
For a rotor radius $R = 0.605\text{ m}$, the swept disk area is:

$$A = \pi R^2 = \pi \times (0.605\text{ m})^2 = 1.1499\text{ m}^2$$

The disk loading ($DL$) is:
$$DL = \frac{T}{A} = \frac{6.6978\text{ N}}{1.1499\text{ m}^2} = 5.8247\text{ N/m}^2$$

By Rankine-Froude momentum theory, the ideal induced velocity through the rotor disk in hover is:

$$v_{i,\text{ideal}} = \sqrt{\frac{T}{2 \rho A}} = \sqrt{\frac{6.6978}{2 \times 0.015018 \times 1.1499}} = \sqrt{193.89} = 13.924\text{ m/s}$$

> [!NOTE]
> On Earth, an equivalent light UAV has an induced velocity of only $\sim 2 - 3\text{ m/s}$. On Mars, the low density forces the rotor to accelerate the air to nearly $14\text{ m/s}$ ($50\text{ km/h}$) downward just to hover!

### 1.3. Ideal and Actual Induced Power
The ideal induced power required to produce this downward momentum is:

$$P_{i,\text{ideal}} = T \cdot v_{i,\text{ideal}} = 6.6978\text{ N} \times 13.924\text{ m/s} = 93.26\text{ W}$$

Accounting for non-uniform inflow, tip losses, and coaxial counter-rotating wake interference via empirical factor $\kappa = 1.20$:

$$P_{\text{induced}} = \kappa \cdot T \cdot v_{i,\text{ideal}} = 1.20 \times 93.26\text{ W} = 111.91\text{ W}$$

---

## 2. Blade Element Profile Power & Compressibility Corrections

### 2.1. Base Hover Profile Power
Profile power accounts for blade surface skin friction and pressure drag as the blades rotate through the fluid:

$$P_{0,\text{hover}} = \frac{1}{8} \rho \sigma C_{d0} A V_{\text{tip}}^3$$

where:
- $\sigma = \frac{N_{\text{blades}} \cdot c_{\text{mean}}}{\pi R} = \frac{4 \times 0.080}{\pi \times 0.605} = 0.1683$ (Rotor solidity).
- $V_{\text{tip}} = \Omega R = \left(\frac{2,537 \times 2\pi}{60}\right) \times 0.605 = 265.67 \times 0.605 = 160.73\text{ m/s}$.
- At $V_{\text{tip}} = 160.73\text{ m/s}$ and $a = 228.92\text{ m/s}$, hover tip Mach is $M_{\text{tip}} = 0.702$.
- $C_{d0,\text{effective}} \approx 0.035$ (accounting for low Reynolds $Re \approx 14,000$).
- Evaluating:
  $$P_{0,\text{hover}} = \frac{1}{8} \times 0.015018 \times 0.1683 \times 0.035 \times 1.1499 \times (160.73)^3 \approx 61.6\text{ W}$$

### 2.2. Compressibility Drag Rise on Advancing Blade
In forward flight at horizontal speed $V$, the advancing blade tip speed reaches:

$$V_{\text{adv}} = V_{\text{tip}} + V, \quad M_{\text{adv}} = \frac{V_{\text{tip}} + V}{a}$$

When $M_{\text{adv}} > 0.72$, transonic wave drag creates a steep power penalty:

$$C_{d0,\text{effective}} = C_{d0,\text{base}} + 0.50 \cdot (M_{\text{adv}} - 0.72) + 5.0 \cdot (M_{\text{adv}} - 0.72)^2$$

This causes profile drag to rise rapidly once forward flight exceeds $8\text{ to }10\text{ m/s}$.

---

## 3. Forward Flight Translational Lift & The Power Bucket Curve

In forward flight, the rotor sweeps through a fresh stream of undisturbed air, increasing effective mass flow and reducing required induced velocity according to Glauert's momentum relation:

$$v_i(V) = \frac{v_{i,\text{hover}}^2}{\sqrt{V^2 + v_i(V)^2}}$$

As forward speed $V$ increases from $0$ to $6\text{ m/s}$, induced velocity drops from $13.9\text{ m/s}$ to $\sim 10.2\text{ m/s}$, saving over $25\text{ W}$ of induced power.

However, profile power and parasite drag increase with forward velocity:
$$P_0(\mu) = P_{0,\text{hover}} \left(1 + 4.65 \mu^2\right), \quad \text{where } \mu = \frac{V}{V_{\text{tip}}}$$
$$P_{\text{parasite}} = \frac{1}{2} \rho V^3 f_{\text{eq, total}}$$

```
Power (Watts)
  300 |                                                 .-' (Compressibility & Parasite Rise)
      | \                                            .-'
  250 |  \                                        .-'
      |   \                                    .-'
  200 |    \..                              .-'
      |       ''--..                  ..--''
  150 |             ''--..........--''
      |                       |
  100 +-----------------------+---------------------------------
      0                       V_be (~5-7 m/s)                 20  Forward Speed (m/s)
```

The superposition of decreasing induced power and increasing profile/parasite power creates the classic **Helicopter Power Bucket Curve**:
- **Pure Hover ($V = 0$):** Electrical Power $\approx 226.4\text{ W}$ (Aerodynamic: $173.5\text{ W}$).
- **Best Endurance Speed ($V_{\text{be}} \approx 5.5 - 7.0\text{ m/s}$):** Electrical Power $\approx 208.5\text{ W}$ (Translational lift saves $\sim 18\text{ W}$).
- **High Speed ($V > 12\text{ m/s}$):** Advancing blade Mach $> 0.75$; power rises above $260\text{ W}$.

---

## 4. Electrical Power & Energy Budget Formulation

Total electrical power demanded from the battery pack is:

$$P_{\text{electrical}} = \frac{P_{\text{induced}} + P_{\text{profile}} + P_{\text{parasite}} + P_{\text{climb}}}{\eta_{\text{motor}}} + P_{\text{avionics}}$$

where $\eta_{\text{motor}} \approx 0.82$ (motor and electronic speed controller efficiency) and $P_{\text{avionics}} \approx 15.0\text{ W}$.

Battery State of Charge (SoC) integration:

$$\text{SoC}(t) = \text{SoC}_0 - \frac{1}{E_{\text{batt}}} \int_0^t P_{\text{electrical}}(\tau) \, d\tau$$

Flight endurance is governed by the $20\%$ mandatory touchdown reserve floor:

$$t_{\text{endurance}} = \frac{0.80 \times E_{\text{batt}} \times 3,600\text{ s}}{P_{\text{electrical}}}$$

For the Light Scout ($35\text{ Wh}$ battery):
$$t_{\text{endurance}} = \frac{0.80 \times 35.0 \times 3,600}{226.4} = \frac{100,800}{226.4} \approx 445\text{ seconds theoretical, or } \sim 150-180\text{ s with climb/gust margins.}$$

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All aerodynamic equations, power budgets, and endurance figures documented here apply exclusively to unmanned robotic vehicles. They must never be considered safe or certified for crewed flight or human astronaut transport.
