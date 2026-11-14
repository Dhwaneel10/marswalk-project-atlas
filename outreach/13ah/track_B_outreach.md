# PROJECT ATLAS — RESEARCH RELEASE 2.0
# TECHNICAL REVIEW PACKAGE & OUTREACH DRAFT: TRACK B
## RF Microwave Propagation, Rayleigh Dust Loss, Antenna Beamforming & Space Link Feasibility

**Document Designation:** `ATLAS-13AH-OUTREACH-TRACK-B`  
**Review Track:** Track B (RF & Space Communications Engineering)  
**Target Group:** Space Telecommunications Engineers, RF Propagation Specialists, Deep Space Network Architects  
**Date:** 2026-11-07  
**Status:** `DRAFT_PENDING_USER_AUTHORIZATION`  

> [!CAUTION]
> **STRICT COMPLIANCE NOTICE:**  
> This outreach draft is for internal preparation only. **Do NOT send this email, transmit files, or contact any individual without explicit, affirmative authorization from the user.**

---

## 1. Review Package Overview for Track B Evaluators

### 1.1 Technical Scope
This evaluation package invites scrutiny of the RF microwave link budgets, Rayleigh dielectric absorption, antenna field-region boundaries, cascaded receiver noise temperature decomposition, and link feasibility models implemented in **Project Atlas Research Release 2.0**.

### 1.2 Core Physical Equations Under Review
1. **Rayleigh Specific Microwave Attenuation (401.5 MHz–32.0 GHz):**
   $$\alpha_{\text{RF}} = 4.3429 \times 10^3 \cdot \frac{6 \pi}{\lambda \rho_{\text{grain}}} \text{Im}(-K) M \quad [\text{dB/km}]$$
   where $x = 2 \pi r / \lambda \le 0.0134 \ll 1$ at 32 GHz for $r \le 20\,\mu\text{m}$, and $\text{Im}(-K) = 0.00546833$.
2. **Antenna Fraunhofer Distance & Field-Region Boundaries:**
   $$R_{\text{ff}} = \frac{2 D^2}{\lambda}$$
   *(Links inside $R_{\text{ff}}$ are strictly flagged as `NEAR_FIELD_OUT_OF_DOMAIN`).*
3. **Airy Diffraction Pattern for Circular Apertures:**
   $$G(\theta) = G_{\text{max}} \left[\frac{2 J_1(u)}{u}\right]^2, \quad u = \pi \frac{D}{\lambda} \sin\theta$$
   *(Yields $-17.57\text{ dB}$ first sidelobe peak, bounded by a $-30\text{ dB}$ floor and $0.1\text{ dB}$ broadbeam guard).*
4. **Cascaded System Noise Reference Plane Invariance:**
   $$\left(\frac{C}{N_0}\right)_A \equiv \left(\frac{C}{N_0}\right)_B \quad (\Delta < 10^{-12}\text{ dB})$$
   *(Proves carrier-to-noise spectral density is invariant between Antenna Terminals and LNA Input).*

### 1.3 Key Primary Citations & Data Provenance
- **Goldhirsh (2000):** Parameterized microwave dust attenuation models on Mars (IEEE TAP).
- **Ho & Golshan (2000):** Mars communications beam attenuation and noise (NASA JPL DESCANSO Series).
- **Fixsen (2009):** Cosmic Microwave Background thermodynamic temperature ($2.725\text{ K}$).
- **ITU-R S.580 / NASA DSN Handbooks:** Earth station and deep-space antenna radiation standards.

### 1.4 Known Limitations Disclosed Upfront
- The dielectric constant $\epsilon_r = 2.80 - j 0.0420$ is derived from dry terrestrial basalt / Apollo lunar regolith analogs, not in-situ measured Martian dust.
- At 32 GHz, equivalent Rayleigh-Jeans brightness is $2.029\text{ K}$ ($-25.54\%$ departure from $2.725\text{ K}$ thermodynamic CMB). Enforcing a $2.7\text{ K}$ floor is an intentional conservative engineering upper bound.
- Real antenna strut blockage and spillover are approximated via bounded Airy profiles rather than full physical optics (PO) numerical integration.
- Operational link closure is strictly decoupled from atmospheric dust loss: low dust attenuation ($\le 0.01\text{ dB}$) does not prevent link failure due to geometric path loss or antenna nulls.

---

## 2. Specific Technical Inquiries for Track B Reviewers

We request feedback on five targeted questions from our 36-question challenge dossier:
1. **Q-RF-01 (Basalt Dielectric Analogs):** Could iron oxides (hematite, magnetite) or minor magnetic permeability ($\mu_r \ne 1.0$) in Martian dust significantly increase microwave absorption beyond our dry basalt dielectric model?
2. **Q-RF-02 (Rayleigh Scattering Limits):** During intense saltation events where coarse grains ($50 - 100\,\mu\text{m}$) are momentarily suspended, at what threshold does Rayleigh absorption break down and require full Mie scattering corrections?
3. **Q-RF-04 (Fraunhofer Distance Enforcement):** For a 5-meter Ka-band ground reflector, $R_{\text{ff}} = 5.3\text{ km}$. Does Atlas's out-of-domain flag inside $R_{\text{ff}}$ create realistic or overly restrictive constraints on rover/drone communications near settlements?
4. **Q-RF-05 (Antenna Sidelobe Envelopes):** Is using a bounded Bessel $J_1(u)/u$ Airy disc pattern too optimistic regarding null depth compared to empirical ITU-R S.580 or NASA DSN sidelobe envelopes?
5. **Q-RF-06 (CMB Equivalent Brightness):** In cold-sky deep-space link budgets, should we replace the conservative $2.7\text{ K}$ floor with the exact frequency-dependent Planck equivalent ($2.029\text{ K}$ at 32 GHz)?

---

## 3. Formal Outreach Invitation Draft

```text
Subject: Technical Peer Review Request: Martian Space Communications & RF Propagation Models in Project Atlas (Research Baseline 2.0)

Dear Dr. [Last Name],

I hope this email finds you well.

I am contacting you on behalf of the Project Atlas engineering team, an open-science student and aerospace researcher initiative developed for the NASA International Space Apps Challenge. We have developed an integrated planetary mission simulation platform that couples orbital ephemerides, Martian atmospheric and dust propagation, antenna radiation patterns, and digital communication link budgets.

We are reaching out to you because of your recognized expertise and authoritative publications in [insert specific domain, e.g., deep space telecommunications systems engineering / planetary radio wave propagation / space network architecture]. Your technical publications have served as key references for our physical implementations.

We have frozen our research baseline (Research Release 2.0) and are preparing for external peer evaluation. Our objective is not to request an endorsement, but to invite rigorous technical critique, equation-level inspection, and methodological challenge of our space telecommunications models.

Specific areas where your technical criticism would be exceptionally valuable include:
1. Our mathematical reconciliation of the Goldhirsh (2000) and Ho & Golshan (2000) Ka-band dust attenuation models as mass-normalized Rayleigh absorption variants (see EVIDENCE_RECONCILIATION.md, Section 4).
2. The validity and limitations of using terrestrial basalt and Apollo lunar regolith dielectric constants (eps_r = 2.80 - j 0.042) as analogs for suspended Martian dust storms.
3. Our formulation of cascaded receiver noise temperature and proof of carrier-to-noise spectral density (C/N0) invariance between reference planes.
4. Our demarcation of operational link feasibility from atmospheric dust loss (demonstrating link failure under 0.009 dB dust loss in Scenario 3).

We have packaged a standalone, lightweight research archive (~128 KB) containing our technical manuscript draft, exact mathematical derivations, and zero-dependency Python benchmarks:
- Technical Manuscript Draft: TECHNICAL_PAPER.md
- Challenge Questionnaire: EXTERNAL_CHALLENGE_QUESTIONS.md (Questions 13–24)
- Standalone Benchmark Suite: benchmarks/benchmark_rf_dust.py & benchmark_link_budget_scenarios.py (runs in < 5 seconds on standard Python 3.10+)

The complete release package, benchmark source code, and cryptographic manifests can be inspected on GitHub at:
https://github.com/nasa-spaceapps/marswalk/tree/main/research/Atlas_Research_Release_2.0

We recognize your time is extremely valuable. A targeted review of the link-budget equations and assumptions in Section 3 of the technical paper would require approximately 30–45 minutes and would provide essential guidance to our team.

If you are willing to evaluate these models, your feedback can be provided directly by reply or via our structured review response template. All technical observations and criticisms will be logged verbatim, formally addressed in our remediation register, and acknowledged.

Thank you very much for your time, consideration, and leadership in deep space telecommunications engineering.

Sincerely,

[Your Name / Title]
Project Atlas Verification Team
NASA International Space Apps Challenge Initiative
Repository: https://github.com/nasa-spaceapps/marswalk
```
