# MarsWalk 2.0 / Project Atlas — Milestone 13L: Mars Solar Ephemeris & Surface Geometry

## 1. Overview
The Solar Geometry Engine (`src/marswalk/core/mars_solar_environment.py`) implements deterministic planetary ephemeris equations for the IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$). It computes celestial solar positioning, top-of-atmosphere flux, surface incidence angles across sloped terrain, and direct-beam atmospheric transmission.

## 2. Mathematical Formulations

### 2.1 Solar Longitude ($L_s$) and Seasonal Cycle
Mars orbital motion is parameterized by $L_s$ (degrees $[0^\circ, 360^\circ)$):
- $L_s = 0^\circ$: Northern Vernal Equinox
- $L_s = 90^\circ$: Northern Summer Solstice (Aphelion vicinity)
- $L_s = 180^\circ$: Northern Autumnal Equinox
- $L_s = 270^\circ$: Northern Winter Solstice (Perihelion vicinity, global dust season)

For mission sol $S$ with initial seasonal offset $L_{s0}$:
$$L_s = \left( L_{s0} + (S - 1) \cdot \frac{360.0}{668.6} \right) \pmod{360^\circ}$$
where $668.6$ is the number of Martian Sols per Martian Year.

### 2.2 Solar Declination ($\delta_{\odot}$)
Given Mars obliquity $\epsilon \approx 25.19^\circ$:
$$\sin \delta_{\odot} = \sin \epsilon \cdot \sin(L_s \cdot \frac{\pi}{180})$$
$$\delta_{\odot} = \arcsin(\sin \delta_{\odot}) \cdot \frac{180}{\pi}$$

### 2.3 Local True Solar Time (LTST) & Hour Angle ($h_{\odot}$)
Local Solar Time is expressed in decimal hours $[0.0, 24.0)$ where $12.0$ corresponds to local solar noon:
$$h_{\odot} = (LTST - 12.0) \cdot 15.0^\circ$$

### 2.4 Solar Elevation Angle ($\alpha_{\odot}$) & Zenith Angle ($\theta_z$)
For reference latitude $\phi$ (Jezero Crater $\phi = 18.442^\circ\text{ N}$):
$$\sin \alpha_{\odot} = \sin \phi \sin \delta_{\odot} + \cos \phi \cos \delta_{\odot} \cos h_{\odot}$$
$$\alpha_{\odot} = \arcsin(\sin \alpha_{\odot}) \cdot \frac{180}{\pi}, \quad \theta_z = 90.0^\circ - \alpha_{\odot}$$
If $\alpha_{\odot} \le 0.0^\circ$, the Sun is below the horizon (nighttime).

### 2.5 Solar Azimuth Angle ($\phi_{\odot}$)
Computed using horizontal projection components clockwise from North ($0^\circ=\text{North}, 90^\circ=\text{East}, 180^\circ=\text{South}, 270^\circ=\text{West}$):
$$x_{\odot} = -\cos \delta_{\odot} \sin h_{\odot}$$
$$y_{\odot} = \cos \phi \sin \delta_{\odot} - \sin \phi \cos \delta_{\odot} \cos h_{\odot}$$
$$\phi_{\odot} = \left( \operatorname{atan2}(x_{\odot}, y_{\odot}) \cdot \frac{180}{\pi} \right) \pmod{360^\circ}$$

### 2.6 Mars-Sun Distance & Top of Atmosphere (TOA) Irradiance
Accounting for Martian orbital eccentricity $e = 0.0934$ and semi-major axis $a = 1.52368\text{ AU}$ with perihelion near $L_s \approx 251^\circ$:
$$r_{\text{orbit}} = \frac{a (1 - e^2)}{1 + e \cos((L_s - 251.0^\circ) \cdot \frac{\pi}{180})}$$
$$S_{\text{TOA}} = \frac{S_{1\text{AU}}}{r_{\text{orbit}}^2} = \frac{1361.0\text{ W/m}^2}{r_{\text{orbit}}^2}$$

### 2.7 Surface Incidence Angle ($\theta_i$) on Sloped Terrain
For a local surface with slope $\theta_s$ and aspect azimuth $\psi$ (derived from Horn 3x3 finite differences):
$$\cos \theta_i = \cos \theta_s \cos \theta_z + \sin \theta_s \sin \theta_z \cos(\phi_{\odot} - \psi)$$
- If $\cos \theta_i \le 0$, the surface normal faces away from the Sun (self-shadowed).
- Incidence angle: $\theta_i = \arccos(\max(0, \cos \theta_i)) \cdot \frac{180}{\pi}$.

### 2.8 Direct-Beam Atmospheric Attenuation
Direct solar flux reaching the surface accounting for optical depth $\tau$:
$$\text{Airmass } m = \frac{1.0}{\max(0.05, \sin \alpha_{\odot})}$$
$$I_{\text{direct}} = S_{\text{TOA}} \cdot e^{-\tau \cdot m} \cdot \cos \theta_i$$
