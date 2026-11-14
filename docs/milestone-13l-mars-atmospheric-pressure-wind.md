# MarsWalk 2.0 / Project Atlas — Milestone 13L: Atmospheric Pressure & Wind Model

## 1. Overview
The Atmospheric Pressure & Surface Wind Engine (`src/marswalk/core/mars_atmospheric_environment.py`) models elevation-dependent hydrostatic air pressure, gas density, and diurnal surface wind speed vectors over Jezero Crater, calibrated to Mars 2020 Perseverance MEDA pressure sensor (PS) and wind sensor (WS) datasets.

## 2. Hydrostatic Barometric Pressure
Martian atmospheric pressure scales exponentially with elevation above the datum:
$$P(z) = P_0 \cdot \exp\left(-\frac{z}{H_p}\right)$$
where:
- $P_0 = 610.0\text{ Pa}$: Reference atmospheric pressure at datum ($z = 0\text{ m}$).
- $H_p = 11,100.0\text{ m}$: Atmospheric scale height for Mars $\text{CO}_2$ atmosphere.
- At Jezero Crater floor ($z \approx -2500\text{ m}$), nominal hydrostatic pressure is:
  $$P(-2500) = 610 \cdot \exp\left(\frac{2500}{11100}\right) \approx 763.8\text{ Pa}$$

## 3. Atmospheric Gas Density
Density $\rho$ is computed using the ideal gas law:
$$\rho = \frac{P}{R_{\text{spec}} \cdot T_K}$$
where $R_{\text{spec}} \approx 188.92\text{ J/(kg}\cdot\text{K)}$ for pure carbon dioxide. At $760\text{ Pa}$ and $-40^\circ\text{C}$ ($233.15\text{ K}$), $\rho \approx 0.01726\text{ kg/m}^3$ (approx. 1.4% of Earth sea-level air density).

## 4. Diurnal Wind Speed & Gust Dynamics
Perseverance MEDA wind records show strong diurnal periodicity driven by daytime convective boundary layer turbulence and thermal slope winds along the western delta scarp:
- **Calm Mornings (06:00–10:00 LTST):** Mean speeds $2.0–4.0\text{ m/s}$, gusts $< 6.0\text{ m/s}$. Ideal for robotic arm deployment and microscopic contact science.
- **Convective Afternoons (13:00–16:00 LTST):** Peak mean speeds $8.0–14.0\text{ m/s}$, convective gusts up to $22.0–25.0\text{ m/s}$.
- **Operational Wind Hazard Limit:** $22.0\text{ m/s}$ peak gust threshold. Exceeding this limit triggers the `HIGH_WIND_GUST` operational hazard warning, advising arm stowing and antenna stabilization.
