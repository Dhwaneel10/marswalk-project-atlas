# PROJECT ATLAS — MILESTONE 13Q
# TEN REPRODUCIBLE DISCOVERY SCENARIOS CATALOG
## Deterministic Scenarios, Ground Truth Generating Parameters & Stage Breakdowns

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_discovery_scenario_engine.py`  
**Status:** `QUALIFIED`

---

## 1. Catalog Overview

| Scenario ID | Name | Primary Target | Key Capability Demonstrated |
|---|---|---|---|
| **SCENARIO_01** | **The Question That Changes Mars** | Jezero Western Delta Scarp | Flagship 6-stage active discovery, competing hypotheses, PIXL confirmation. |
| **SCENARIO_02** | **The False Discovery** | Neretva Vallis Channel | Adversarial tester discovers detector thermal drift; rejects own initial guess. |
| **SCENARIO_03** | **The Two Mineral Problem** | Kodiak Butte Outcrop | Smectite vs Carbonate ambiguity resolved via PIXL XRF elemental stoichiometry. |
| **SCENARIO_04** | **The Blind Spot** | Northern Delta Terrace | Evaluates exploration value of unobserved high-uncertainty terrain. |
| **SCENARIO_05** | **Rover vs Aircraft** | Jezero Crater Floor | Quantitative trade-off: Ground-only vs Aerial recon + targeted rover verification. |
| **SCENARIO_06** | **The Vanishing Science Instrument** | Séítah Geologic Unit | Mid-campaign instrument dropout and autonomous replacement replanning. |
| **SCENARIO_07** | **The Communication Blackout** | Belva Crater Ejecta | Local active science autonomy during two-week superior solar conjunction. |
| **SCENARIO_08** | **The Competing Geology** | Delta Front Layered Beds | Sedimentary delta vs pyroclastic ash fall evaluated via radar and texture. |
| **SCENARIO_09** | **The Resource Crisis** | Centinela Butte Scarp | Severe battery reserve (40 Wh) forces cost-aware single-action prioritization. |
| **SCENARIO_10** | **The Autonomous Planetary Scientist** | Full Jezero Corridor | End-to-end multi-sol campaign synthesizing climate, flight, and discovery dossier. |

---

## 2. Flagship Scenario 01: Six Stage Progression

1. **Stage 1 (Aerial Anomaly Detection):** `AERO-INGENUITY-01` acquires preliminary reconnaissance spectrum showing apparent band depth $0.142$ at $2.3\ \mu\text{m}$.
2. **Stage 2 (Instrument Capability Audit):** Adversarial auditor evaluates `AERO_NIR_SPECTROMETER` specifications, flags physical range $[700, 1050]\text{ nm}$, and prevents premature celebration.
3. **Stage 3 (Competing Hypotheses Formulation):** System registers three mutually competing hypotheses: `HYP-01-SMECTITE` ($P=0.45$), `HYP-02-CARBONATE` ($P=0.35$), `HYP-03-ARTIFACT` ($P=0.20$); Shannon entropy $H = 1.518\text{ bits}$.
4. **Stage 4 (Active Experiment Selection):** Value engine calculates $EIG = 1.25\text{ bits}$ for Rover PIXL in-situ mapping, rejecting uninformative broad optical imaging.
5. **Stage 5 (In-Situ Lithochemistry Execution):** Perseverance arrives at outcrop, deploys PIXL arm, maps elemental abundances ($\text{Si}=22.4\%, \text{Al}=2.8\%, \text{Ca}=1.5\%$), confirming authentic phyllosilicate smectite stoichiometry and ruling out carbonate.
6. **Stage 6 (Hypothesis Resolution):** Atlas transitions `HYP-01-SMECTITE` to `SUPPORTED_BY_EVIDENCE` ($P=0.94$), formally rejects `HYP-02` and `HYP-03`, slashes entropy to $0.354\text{ bits}$, and updates cryptographic evidence DAG.
