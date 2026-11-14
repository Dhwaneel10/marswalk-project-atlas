# PROJECT ATLAS — MILESTONE 13AF
# Receiver System Noise Temperature, Antenna Beam Integration & CMB Reference Benchmark

**Document Identifier:** `ATLAS-DOC-13AF-RECEIVER-NOISE-BENCHMARK`  
**Milestone:** 13AF — Atlas Independent Benchmark & Research Freeze  
**Parent Milestone:** 13AE — Propagation Evidence Closure  
**Date:** 2026-11-07  
**Status:** QUALIFIED THERMODYNAMIC BENCHMARK

---

## 1. Executive Summary & Epistemological Disclosures

Milestone 13AD/13AE introduced a defensive lower-bound check of $2.725\text{ K}$ (Cosmic Microwave Background) on antenna input temperature.

Milestone 13AF audits this boundary from electromagnetic and thermodynamic fundamentals:
1. **Antenna Temperature is a Beam Integral, Not a Local Thermodynamic Property:**
   An antenna does not possess an inherent "temperature" in the thermodynamic sense; rather, the antenna noise temperature $T_A$ is the normalized pattern integral of the external angular brightness temperature distribution $T_b(\theta, \phi)$:
   $$T_A = \frac{\int_{4\pi} P_n(\theta, \phi) T_b(\theta, \phi) d\Omega}{\int_{4\pi} P_n(\theta, \phi) d\Omega}$$
   The CMB floor of $2.725\text{ K}$ is an asymptotic lower bound valid only when an antenna points into deep space with zero planetary disk interception and zero ground spillover.
2. **Planck vs Rayleigh–Jeans Brightness Temperature Departure:**
   The thermodynamic CMB temperature is $T_{\text{CMB}} = 2.725\text{ K}$. However, in radio engineering, noise power is conventionally expressed via Nyquist's theorem ($P = k B T_{\text{RJ}}$) using the Rayleigh–Jeans equivalent brightness temperature $T_{\text{RJ}}$. At microwave frequencies, $h \nu \approx k T$, causing the equivalent Rayleigh–Jeans brightness temperature of deep space to depart substantially from $2.725\text{ K}$—dropping to **$2.029\text{ K}$ at 32 GHz** (a $25.5\%$ difference).
3. **Reference Plane Invariance:**
   We independently re-verify the input-referred versus output-referred noise formulations across Antenna Terminals (Plane A) and LNA Input (Plane B), proving zero double-counting of feed line losses.

---

## 2. Antenna Temperature Beam Integration Mechanics

The total brightness temperature field $T_b(\theta, \phi)$ impinging on an antenna on or orbiting Mars is decomposed into four physical components:

$$T_b(\theta, \phi) = T_{\text{CMB}}(\theta, \phi) + T_{\text{Mars}}(\theta, \phi) + T_{\text{atm}}(\theta, \phi) + T_{\text{ground}}(\theta, \phi)$$

### 2.1 Pattern Discretization & Solid Angle Integration
For an antenna with normalized power pattern $P_n(\theta, \phi)$ and beam efficiency $\eta_M = \frac{\Omega_M}{\Omega_A}$:

$$T_A = \eta_M T_{b, \text{main}} + (1 - \eta_M) T_{\text{spillover}}$$

We evaluate five operational antenna geometries in the Martian theater:

| Case ID | Geometry / Orientation | Main Beam Interception | Spillover / Sidelobe Interception | Calculated Antenna Temperature ($T_A$) |
|:---|:---|:---|:---|:---:|
| **GEO-01** | Deep Space High-Gain Dish ($\theta_{\text{elev}} = 60^\circ$, Earth tracking) | Unobstructed deep space ($T_b \approx T_{\text{CMB}} + T_{\text{atm}}$) | $5\%$ ground spillover from Martian surface ($T_{\text{ground}} \approx 210\text{ K}$) | **$15.2\text{ K}$** |
| **GEO-02** | Orbiter Nadir-Pointing Earth Station Relay ($\theta = -90^\circ$) | Full Martian disk ($T_{\text{Mars}} \approx 210\text{ K}$) | $3\%$ deep space cold sky ($2.7\text{ K}$) | **$203.8\text{ K}$** |
| **GEO-03** | Rover Surface Monopole ($\theta = 15^\circ$, broad omni beam) | $50\%$ upper sky hemisphere ($T_{\text{sky}} \approx 10\text{ K}$) | $50\%$ lower ground hemisphere ($T_{\text{ground}} \approx 210\text{ K}$) | **$110.0\text{ K}$** |
| **GEO-04** | Ground Station Horizon Grazing ($\theta = 2^\circ$) | $40\%$ sky, $20\%$ atmospheric emission ($T_m \approx 180\text{ K}$) | $40\%$ warm Martian surface regolith ($210\text{ K}$) | **$135.4\text{ K}$** |
| **GEO-05** | Theoretical Ideal Space Probe (Zero sidelobes, pointed away from Mars/Sun) | $100\%$ unobstructed CMB | $0\%$ spillover | **$2.725\text{ K}$ (Theoretical Minimum)** |

**Engineering Finding:** In practical Mars surface and orbital operations, antenna noise temperature is almost always between **$15\text{ K}$ and $210\text{ K}$** due to the warm Martian planetary disk ($210\text{ K}$) and ground emission. The $2.725\text{ K}$ threshold represents the absolute physical asymptote for an ideal lossless antenna pointed into cold space.

---

## 3. Planck vs Rayleigh–Jeans Brightness Temperature Departure

The spectral radiance of a blackbody at physical temperature $T$ is given by Planck's law:

$$B_\nu(T) = \frac{2 h \nu^3}{c^2} \frac{1}{\exp\left(\frac{h \nu}{k_B T}\right) - 1}$$

The Rayleigh–Jeans approximation equates $B_\nu(T) \approx \frac{2 k_B T_{\text{RJ}} \nu^2}{c^2}$, defining the Rayleigh–Jeans equivalent brightness temperature:

$$T_{\text{RJ}}(\nu, T) = \frac{h \nu / k_B}{\exp\left(\frac{h \nu}{k_B T}\right) - 1}$$

Expanding the exponential for small $h \nu / k_B T$:

$$T_{\text{RJ}} \approx T - \frac{h \nu}{2 k_B}$$

Using the physical constants:
- $h = 6.62607015 \times 10^{-34}\text{ J}\cdot\text{s}$
- $k_B = 1.380649 \times 10^{-23}\text{ J/K}$
- Constant ratio: $\frac{h}{k_B} = 4.79924 \times 10^{-11}\text{ K/Hz} = 0.0479924\text{ K/GHz}$

### Departure from Thermodynamic CMB ($T = 2.725\text{ K}$) Across Atlas Frequency Bands

| Band | Carrier Frequency ($\nu$) | Characteristic Ratio $\frac{h \nu}{k_B}$ | Dimensionless Parameter $\frac{h \nu}{k_B T}$ | Exact Rayleigh–Jeans Brightness $T_{\text{RJ}}$ | Departure from 2.725 K ($\Delta T$) | Relative Error |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **UHF (Proximity)** | 401.5 MHz | 0.01927 K | 0.00707 | **2.715 K** | $-0.010\text{ K}$ | $-0.36\%$ |
| **S-Band (Telemetry)** | 2.20 GHz | 0.10558 K | 0.03875 | **2.672 K** | $-0.053\text{ K}$ | $-1.94\%$ |
| **X-Band (Deep Space)** | 8.40 GHz | 0.40314 K | 0.14794 | **2.528 K** | $-0.197\text{ K}$ | $-7.23\%$ |
| **Ka-Band (Deep Space)** | 32.0 GHz | 1.53576 K | 0.56358 | **2.029 K** | **$-0.696\text{ K}$** | **$-25.54\%$** |
| **Optical Laser (DSOC)** | 193.4 THz (1550 nm) | 9,282 K | 3,406 | **$0.000\text{ K}$** | $-2.725\text{ K}$ | $-100.0\%$ |

### Crucial Engineering Insight
At Ka-band ($32\text{ GHz}$), the quantum parameter $\frac{h \nu}{k_B T} = 0.564$ is not small. Applying the Rayleigh–Jeans equivalent temperature yields $T_{\text{RJ}} = 2.029\text{ K}$. Enforcing a strict $2.725\text{ K}$ floor in a Rayleigh–Jeans formula over-estimates the cold-sky noise contribution by **$0.70\text{ K}$**. While $0.70\text{ K}$ is negligible compared to a typical receiver noise temperature ($T_{\text{sys}} \sim 250 - 500\text{ K}$, causing $< 0.01\text{ dB}$ difference in link margin), **Atlas documentation must explicitly disclose that Rayleigh–Jeans conventions are retained as an engineering approximation**.

---

## 4. Feed Loss Reference Plane Invariance & Zero Double-Counting

We re-verify the input-referred relation for a receiver with passive feed loss $L \ge 1$ (where $L = 10^{\frac{L_{\text{cable, dB}}}{10}}$) at physical temperature $T_L$ and receiver equivalent noise temperature $T_{\text{rx}} = (10^{\frac{\text{NF}}{10}} - 1) \cdot 290\text{ K}$:

### 4.1 Plane A: Antenna Output Terminals (Input-Referred)
- Available Signal Power: $P_A = P_{\text{ant}}$
- System Noise Temperature:
  $$T_{\text{sys,A}} = T_{\text{ant}} + T_{\text{feed}} + L \cdot T_{\text{rx}} = T_{\text{ant}} + (L - 1) T_L + L T_{\text{rx}}$$
- Carrier-to-Noise Spectral Density:
  $$\left(\frac{C}{N_0}\right)_A = \frac{P_{\text{ant}}}{k_B T_{\text{sys,A}}}$$

### 4.2 Plane B: LNA Input Terminals (Output-Referred)
- Available Signal Power: $P_B = \frac{P_{\text{ant}}}{L}$
- System Noise Temperature:
  $$T_{\text{sys,B}} = \frac{T_{\text{ant}}}{L} + \left(1 - \frac{1}{L}\right) T_L + T_{\text{rx}} = \frac{T_{\text{sys,A}}}{L}$$
- Carrier-to-Noise Spectral Density:
  $$\left(\frac{C}{N_0}\right)_B = \frac{P_B}{k_B T_{\text{sys,B}}} = \frac{P_{\text{ant}} / L}{k_B (T_{\text{sys,A}} / L)} = \frac{P_{\text{ant}}}{k_B T_{\text{sys,A}}} = \left(\frac{C}{N_0}\right)_A$$

**Verification Result:** The two conventions yield identical $(C/N_0)$ and link margins to within infinite numerical precision ($< 10^{-14}\text{ dB}$). In Project Atlas, Plane A is standard throughout all modules, ensuring that cable loss $L$ is accounted for in $T_{\text{sys,A}}$ while $P_{\text{rx}}$ represents raw antenna power, completely precluding double-counting.
