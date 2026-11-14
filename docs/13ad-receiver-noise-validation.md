# ATLAS 13AD: RECEIVER NOISE TEMPERATURE VALIDATION & THERMODYNAMIC BOUNDARIES

**Document Identifier:** `ATLAS-DOC-13AD-STAGE-06`  
**Milestone:** 13AD — Mars Physics Reference Validation  
**Parent:** `ATLAS-13AC-PHYSICS-BOUNDARY`  
**Status:** Approved & Enforced  
**Date:** November 2026  

---

## 1. Executive Summary

Milestone 13AD audits and validates the receiver noise temperature model utilized throughout Project Atlas communications. In telecommunications engineering, the noise spectral density $N_0$ establishes the fundamental floor against which signal energy $E_b$ is measured.

This report establishes:
1. The formal mathematical decomposition of total system noise temperature $T_{\text{sys}}$ into antenna, feed cable, and low-noise amplifier (LNA) receiver stages.
2. Thermodynamic validity boundaries, specifically the absolute lower bound imposed by the Cosmic Microwave Background ($T_{\text{CMB}} \approx 2.725\text{ K}$) and the positivity requirement of the Johnson-Nyquist thermal model ($T_{\text{sys}} > 0\text{ K}$).
3. Operating domain distinctions across surface rovers, orbital relay platforms, and deep-space ground stations on Earth.

---

## 2. Mathematical System Noise Decomposition

Total equivalent system noise temperature referred to the antenna reference plane is expressed as:

$$T_{\text{sys}} = T_{\text{ant}} + T_{\text{feed}} + T_{\text{rx}} \cdot L_{\text{feed}}$$

where:
- $T_{\text{ant}}$: Antenna brightness temperature (Kelvin), integrating all radiation captured by the main beam and sidelobes from the surrounding environment.
- $L_{\text{feed}}$: Linear insertion loss of the feed line, wave-guide, or coaxial cable:
  $$L_{\text{feed}} = 10^{\frac{L_{\text{cable, dB}}}{10}} \ge 1.0$$
- $T_{\text{feed}}$: Thermal noise contribution of the lossy passive feed line at ambient physical temperature $T_{\text{phys}}$:
  $$T_{\text{feed}} = (L_{\text{feed}} - 1) \cdot T_{\text{phys}}$$
- $T_{\text{rx}}$: Receiver / Low-Noise Amplifier (LNA) equivalent input noise temperature derived from the receiver Noise Figure ($\text{NF}_{\text{dB}}$):
  $$T_{\text{rx}} = (10^{\frac{\text{NF}}{10}} - 1) \cdot T_0, \quad \text{where } T_0 = 290.0\text{ K}$$

### 2.1 Thermal Noise Spectral Density ($N_0$)
According to the Johnson-Nyquist theorem, available thermal noise power per unit bandwidth is:

$$N_0 = k_B \cdot T_{\text{sys}} \quad (\text{W/Hz})$$
$$N_{0,\text{dBW/Hz}} = 10 \log_{10}(k_B \cdot T_{\text{sys}}) = -228.60 + 10 \log_{10}(T_{\text{sys}})$$

where $k_B = 1.380649 \times 10^{-23}\text{ J/K}$ is the exact Boltzmann constant (SI 2019 redefinition).

---

## 3. Thermodynamic Validity Boundaries

### 3.1 The 2.7 K Cosmic Microwave Background Floor
In free space or any unobstructed viewing geometry, an antenna cannot capture a brightness temperature below the Cosmic Microwave Background ($2.725\text{ K}$). Any assumption of $T_{\text{ant}} < 2.7\text{ K}$ is physically impossible.

In `ReceiverSpec.calculate_system_noise_temp`:
```python
if t_antenna_k < 2.7:
    raise ValueError(f"Antenna brightness temperature cannot be below CMB (2.7 K), got {t_antenna_k} K")
```

### 3.2 Operating-Domain Requirement vs Mathematical Clamp
Rather than silently clamping unphysical negative or zero temperatures to arbitrary constants, Atlas treats $T_{\text{sys}} > 0\text{ K}$ as an operating domain requirement of the Johnson-Nyquist thermal model. An unpowered receiver or absolute-zero system is outside the domain of classical thermal communications and is rejected with explicit diagnostic error feedback.

---

## 4. Operational Regimes & Antenna Brightness Temperatures

Antenna brightness temperature $T_{\text{ant}}$ depends on the spatial environment viewed by the antenna pattern:

| Operational Asset | Viewing Direction | Governing Brightness Temperature | Typical $T_{\text{sys}}$ (X/Ka-Band) |
| :--- | :--- | :--- | :--- |
| **Surface Rover / Habitat** | Skyward ($> 20^\circ$ elevation) | Cold sky + atmospheric emission: $T_{\text{ant}} \approx 15 - 30\text{ K}$ | $150 - 220\text{ K}$ |
| **Surface Rover / Habitat** | Horizon grazing ($< 5^\circ$) | Warm Martian regolith ground spillover ($T_{\text{ground}} \approx 210 - 240\text{ K}$) | $280 - 380\text{ K}$ |
| **Orbital Spacecraft (Nadir)** | Mars planetary disc | Mars thermal emission ($\epsilon \approx 0.95, T_{\text{mars}} \approx 215\text{ K}$) | $250 - 320\text{ K}$ |
| **Orbital Spacecraft (Crosslink)** | Deep space / cold sky | Cosmic background + galactic background: $T_{\text{ant}} \approx 3 - 6\text{ K}$ | $90 - 140\text{ K}$ (cryo/HEMT LNA) |
| **Solar Conjunction Alignment** | Sun within sidelobes | Solar radio burst brightness: $T_{\text{ant}} > 10,000\text{ K}$ | Extreme thermal degradation ($> 15\text{ dB}$ margin loss) |

---

## 5. Verification Test Suite Alignment

The analytical decomposition implemented in `ReceiverSpec.calculate_system_noise_temp` will be independently validated in Stage 7 (`tests/test_milestone_13ad_mars_physics_validation.py`):
1. Nominal surface receiver ($T_{\text{ant}} = 210\text{ K}, \text{NF} = 2.0\text{ dB}, L_{\text{cable}} = 1.0\text{ dB}, T_{\text{phys}} = 250\text{ K}$):
   - $L_{\text{feed}} = 10^{0.1} = 1.2589$
   - $T_{\text{feed}} = (1.2589 - 1) \times 250 = 64.73\text{ K}$
   - $T_{\text{rx}} = (10^{0.2} - 1) \times 290 = 0.5849 \times 290 = 169.62\text{ K}$
   - $T_{\text{sys}} = 210 + 64.73 + (169.62 \times 1.2589) = 210 + 64.73 + 213.53 = 488.26\text{ K}$
2. Deep space cold-sky receiver ($T_{\text{ant}} = 5\text{ K}, \text{NF} = 1.2\text{ dB}, L_{\text{cable}} = 0.2\text{ dB}$):
   - Resolves to $T_{\text{sys}} \approx 135\text{ K}$.
3. Sub-CMB input rejection ($T_{\text{ant}} = 1.0\text{ K} < 2.7\text{ K}$):
   - Must strictly raise `ValueError`.
