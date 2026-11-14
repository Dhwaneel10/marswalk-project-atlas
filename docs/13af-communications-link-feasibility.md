# PROJECT ATLAS — MILESTONE 13AF
# Martian Communications Link Feasibility & Survivability Audit

**Document Identifier:** `ATLAS-DOC-13AF-LINK-FEASIBILITY`  
**Milestone:** 13AF — Atlas Independent Benchmark & Research Freeze  
**Parent Milestone:** 13AE — Propagation Evidence Closure  
**Date:** 2026-11-07  
**Status:** QUALIFIED FEASIBILITY FRAMEWORK

---

## 1. Executive Summary & Epistemological Correction

In Milestone 13AE, the finding that UHF microwave propagation experiences $< 0.10\text{ dB}$ attenuation during Martian dust storms was characterized in several passages as "guaranteeing rover proximity survivability."

**Milestone 13AF formally repudiates and retracts that claim.**

A favorable propagation loss coefficient is a necessary condition for radio transmission, but it **never guarantees operational communications, link closure, hardware functionality, or mission survivability**. 

To establish true engineering defensibility, this document:
1. Rigorously demarcates six distinct operational concepts that must never be conflated.
2. Implements a full link-budget feasibility model encompassing RF electronics, geometry, antenna beam patterns, thermal noise, and modulation coding thresholds.
3. Formulates multiple explicit test scenarios, including a scenario where atmospheric dust loss is negligible ($< 0.02\text{ dB}$) yet the link **fails completely** due to geometric path loss, receiver sensitivity, and off-axis antenna nulls.

---

## 2. Six-Tier Conceptual Demarcation

In accordance with NASA and IEEE systems engineering standards, communications analysis in Project Atlas must distinguish the following six levels:

| Tier | Concept | Definition | Governing Factors |
|:---:|:---|:---|:---|
| **1** | **Dust Propagation Loss** | Specific electromagnetic attenuation caused by absorption/scattering within atmospheric mineral dust aerosols along the slant ray. | Mass loading $M$, complex permittivity $\epsilon_r$, carrier frequency $f$, Chapman airmass $X(\theta)$. |
| **2** | **Total Propagation Loss** | Net physical path attenuation between transmitter and receiver apertures in space. | Free-space path loss (FSPL), $CO_2$ gaseous continuum absorption, dust attenuation, multipath reflection, terrain diffraction. |
| **3** | **Link Margin** | Decibel difference between received signal-to-noise spectral density ($C/N_0$) and the minimum threshold $(C/N_0)_{\text{req}}$ required for a specified bit error rate (BER). | $P_{\text{tx}}$, $G_{\text{tx}}(\theta,\phi)$, $G_{\text{rx}}(\theta,\phi)$, total loss, $T_{\text{sys}}$, data rate $R_b$, required $E_b/N_0$, coding gain. |
| **4** | **Link Availability** | The fraction of mission time during which the link margin is non-negative and geometric line-of-sight is unobstructed. | Orbital ephemerides, local elevation mask, terrain shadowing, solar conjunctions, antenna tracking dynamics. |
| **5** | **Hardware Reliability** | Probability that the physical transmitter, receiver, diplexer, traveling-wave tube amplifier (TWTA), power supply, and antenna pointing mechanisms function without mechanical or electrical breakdown. | Mean Time Between Failures (MTBF), radiation dose, thermal cycling on Mars ($-120^\circ\text{C}$ to $+20^\circ\text{C}$), component wear. |
| **6** | **Operational Survivability** | The capacity of the planetary surface rover or mission node to maintain state of charge, thermal equilibrium, and vital telemetry execution under planetary hazards. | Solar array dust obscuration, battery health, thermal insulation, software fault recovery, mission operations. |

> [!CAUTION]
> **Defensive Rule:** Low dust loss ($\le 0.10\text{ dB}$) at Tier 1 does not guarantee Tier 2 path loss, Tier 3 link margin, Tier 4 availability, Tier 5 hardware reliability, or Tier 6 operational survivability.

---

## 3. Comprehensive Link Budget Feasibility Equations

The deterministic link budget is evaluated according to CCSDS 130.1-G-3 and NASA JPL Deep Space Communications standards:

### 3.1 Equivalent Isotropically Radiated Power (EIRP)
$$\text{EIRP}_{\text{dBW}} = P_{\text{tx, dBW}} - L_{\text{tx\_cable, dB}} + G_{\text{tx, dBi}} - L_{\text{tx\_point, dB}}$$

### 3.2 Total Path Loss
$$L_{\text{path, dB}} = \text{FSPL}_{\text{dB}} + A_{\text{gas, dB}} + A_{\text{dust, dB}}$$
$$\text{FSPL}_{\text{dB}} = 20 \log_{10}\left(\frac{4 \pi R}{\lambda}\right)$$

### 3.3 Received Signal Power at Antenna Terminals ($P_{\text{ant}}$)
$$P_{\text{ant, dBW}} = \text{EIRP}_{\text{dBW}} - L_{\text{path, dB}} + G_{\text{rx, dBi}} - L_{\text{rx\_point, dB}}$$

### 3.4 Receiver System Noise Spectral Density ($N_0$)
Evaluated at Antenna Terminals (Plane A):
$$T_{\text{sys}} = T_{\text{ant}} + (L_{\text{rx\_feed}} - 1) T_L + L_{\text{rx\_feed}} T_{\text{rx}}$$
$$N_{0, \text{dBW/Hz}} = 10 \log_{10}\left(k_B \cdot T_{\text{sys}}\right), \quad k_B = 1.380649 \times 10^{-23}\text{ J/K}$$

### 3.5 Carrier-to-Noise Spectral Density ($C/N_0$) and Link Margin
$$(C/N_0)_{\text{dB-Hz}} = P_{\text{ant, dBW}} - N_{0, \text{dBW/Hz}}$$
$$(C/N_0)_{\text{req, dB-Hz}} = \left(\frac{E_b}{N_0}\right)_{\text{req, dB}} + 10 \log_{10}(R_{b, \text{bps}})$$
$$\text{Margin}_{\text{dB}} = (C/N_0)_{\text{dB-Hz}} - (C/N_0)_{\text{req, dB-Hz}}$$

---

## 4. Multi-Scenario Feasibility Analysis

We analyze three operational proximity links between a surface rover (nominal 5 W transmitter, UHF 401.5 MHz) and an orbiter relay at $400\text{ km}$ periapsis:

### Scenario 1: Nominal Overhead Relay Pass (Link Closed)
- **Geometry:** Overhead zenith pass ($\theta = 85^\circ$, $R = 401.6\text{ km}$).
- **Dust Loading:** Moderate dust storm ($\tau_{880} = 1.5$, mass loading $M = 0.30\text{ mg/m}^3$).
- **Transmitter:** $P_{\text{tx}} = 5.0\text{ W}$ ($+6.99\text{ dBW}$), $L_{\text{cable}} = 0.8\text{ dB}$, Monopole $G_{\text{tx}} = +2.15\text{ dBi}$, Pointing loss $= 0.2\text{ dB}$.
  $\text{EIRP} = 6.99 - 0.80 + 2.15 - 0.20 = +8.14\text{ dBW}$.
- **Propagation:**
  $\text{FSPL} = 20 \log_{10}\left(\frac{4 \pi \times 401.6 \times 10^3}{0.7467}\right) = 136.60\text{ dB}$.
  $A_{\text{gas}} = 0.005\text{ dB}$, $A_{\text{dust}} = 0.032\text{ dB}$. Total $L_{\text{path}} = 136.64\text{ dB}$.
- **Receiver:** Orbiter patch array $G_{\text{rx}} = +6.0\text{ dBi}$, $L_{\text{point}} = 0.5\text{ dB}$.
  $P_{\text{ant}} = 8.14 - 136.64 + 6.0 - 0.5 = -123.00\text{ dBW}$.
- **Noise:** $T_{\text{ant}} = 210.0\text{ K}$, $L_{\text{feed}} = 1.0\text{ dB}$ ($L = 1.259$), $T_L = 250\text{ K}$, $NF = 2.0\text{ dB}$ ($T_{\text{rx}} = 169.6\text{ K}$).
  $T_{\text{sys}} = 210.0 + (0.259 \times 250) + (1.259 \times 169.6) = 210.0 + 64.75 + 213.53 = 488.28\text{ K}$.
  $N_0 = 10 \log_{10}(1.380649 \times 10^{-23} \times 488.28) = -200.28\text{ dBW/Hz}$.
- **Performance:**
  $C/N_0 = -123.00 - (-200.28) = +77.28\text{ dB-Hz}$.
  Required $(E_b/N_0)$ for uncoded BPSK ($\text{BER} \le 10^{-5}$) $= 9.6\text{ dB}$. Rate $R_b = 32\text{ kbps}$ ($45.05\text{ dB-Hz}$).
  $(C/N_0)_{\text{req}} = 9.6 + 45.05 = 54.65\text{ dB-Hz}$.
- **Link Margin:** $\text{Margin} = 77.28 - 54.65 = \mathbf{+22.63\text{ dB}}$ (**Link Closed & Operational**).

---

### Scenario 2: Severe Dust Storm Slant Pass (Link Closed with Degraded Margin)
- **Geometry:** Low elevation pass ($\theta = 12^\circ$, slant range $R = 1,150\text{ km}$).
- **Dust Loading:** Severe global dust event ($\tau_{880} = 5.0$, $M = 1.00\text{ mg/m}^3$).
- **Propagation:**
  $\text{FSPL} = 145.75\text{ dB}$. $A_{\text{gas}} = 0.024\text{ dB}$, $A_{\text{dust}} = 0.457\text{ dB}$. Total $L_{\text{path}} = 146.23\text{ dB}$.
- **Received Power:** $P_{\text{ant}} = 8.14 - 146.23 + 6.0 - 1.2 = -133.29\text{ dBW}$.
- **Performance:**
  $C/N_0 = -133.29 - (-200.28) = +66.99\text{ dB-Hz}$.
  At $R_b = 32\text{ kbps}$, $\text{Margin} = 66.99 - 54.65 = \mathbf{+12.34\text{ dB}}$ (**Link Closed**).
  Even though dust loss increased by $14\times$ ($0.457\text{ dB}$ vs $0.032\text{ dB}$), the link closes because free-space path loss and RF margins dominate.

---

### Scenario 3: Negligible Dust Loss But Complete Link Failure (The Demonstration)
- **Context:** Clear Martian sky ($\tau_{880} = 0.20$, dust optical loss negligible).
- **Dust Loss:** $A_{\text{dust}} = \mathbf{0.009\text{ dB}}$ (virtually zero; total path atmospheric loss $< 0.12\text{ dB}$).
- **Physical Failure Mechanism:**
  1. **Extreme Low Elevation & Range:** Rover attempts communication at $\theta = 2.5^\circ$, where slant range $R = 2,280\text{ km}$ ($\text{FSPL} = 151.68\text{ dB}$).
  2. **Antenna Pattern Roll-Off / Chassis Null:** At $\theta = 2.5^\circ$, the rover monopole pattern drops by $-6.0\text{ dBi}$ into local chassis ground plane null ($G_{\text{tx}} = -3.85\text{ dBi}$).
  3. **Low-Power Survival Mode:** Rover transmits at emergency power $P_{\text{tx}} = 0.5\text{ W}$ ($-3.01\text{ dBW}$).
- **Quantitative Evaluation:**
  $\text{EIRP} = -3.01 - 0.80 - 3.85 - 0.10 = -7.76\text{ dBW}$.
  $L_{\text{path}} = 151.68 + 0.11 = 151.79\text{ dB}$.
  $P_{\text{ant}} = -7.76 - 151.79 + 6.0 = -153.55\text{ dBW}$.
  $C/N_0 = -153.55 - (-201.71) = +48.16\text{ dB-Hz}$.
  Required $(E_b/N_0)_{\text{req}} = 9.6\text{ dB}$, minimum margin $= 3.0\text{ dB}$.
  Net Budget for data rate: $\text{Net Budget} = 48.16 - 9.6 - 3.0 = 35.56\text{ dB-Hz}$.
  Maximum achievable bit rate: $R_{\text{max}} = 10^{3.556} \approx 3,597\text{ bps}$ ($3.6\text{ kbps}$).
  Because standard operational radio modes require at least $8\text{ kbps}$, **no eligible transmission mode exists**.
- **Link Status:**
  $$\text{Operational Rate} = 0\text{ bps}, \quad \text{Status} = \textbf{LINK FAILED (ACHIEVABLE RATE BELOW 8 KBPS)}$$

> [!IMPORTANT]
> **Defensive Proof:** In Scenario 3, dust attenuation is only **$0.009\text{ dB}$**, yet the communication link fails by more than **$10\text{ dB}$**. This definitively proves that low dust attenuation cannot guarantee link closure, communications reliability, or rover survivability.

---

## 5. Software Defensive Guardrails in Atlas

In `src/marswalk/core/atlas_network_link_model.py`:
1. `is_link_closed` strictly requires:
   $$\text{Margin}_{\text{dB}} \ge 0.0\text{ dB} \quad \text{AND} \quad R_{\text{slant}} \ge R_{\text{Fraunhofer}} \quad \text{AND} \quad \theta_{\text{elev}} > 0.0^\circ$$
2. A link is flagged as `LINK_FAILED_INSUFFICIENT_MARGIN` whenever $\text{Margin} < 0\text{ dB}$, regardless of whether atmospheric dust loss is low.
3. Telemetry outputs separate `atmospheric_loss_db`, `link_margin_db`, and `is_link_closed`, preventing any operational engine from assuming a small atmospheric loss equates to a successful contact.
