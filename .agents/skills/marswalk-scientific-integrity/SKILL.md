---
name: marswalk-scientific-integrity
description: >-
  Audits and enforces rigorous planetary science standards, data provenance, coordinate systems,
  SI units, and non-probabilistic truth disclosures across MarsWalk 2.0 / Project Atlas.
  Distinguishes real measurements from simulation heuristics and prevents misleading astronaut safety claims.
---

# MarsWalk Scientific Integrity Skill

## Purpose
Ensure all calculations, API contracts, user interface labels, and exported evidence packages adhere to strict planetary science standards, authentic remote sensing provenance, and NASA Space Apps scientific credibility guidelines.

## Mandatory Scientific Guardrails
1. **Never Invent Data:** Never synthesize artificial sensor telemetry and present it as authentic Martian measurements. All spatial calculations must originate from authentic USGS CTX 20m Jezero Crater Digital Terrain Models.
2. **Deterministic Modeling vs Empirical Probabilities:**
   - Evaluated scenario counts (e.g., $7/10$ cases or $70\%$) represent performance *strictly across the explicitly tested deterministic cases*.
   - **PROHIBITED:** Never label scenario frequencies as "physical probability of mission success," "empirical failure likelihood," or "certified reliability rates."
3. **Astronaut Safety Certification Prohibition:**
   - All traverses, speeds, and metabolic costs represent planning-simulation heuristics derived from remote sensing.
   - **PROHIBITED:** Never characterize a modeled route as "operationally safe for astronauts" or "flight-certified."
4. **Coordinate Systems & Units:**
   - Mars Projected CRS: `ESRI:103885` (Equirectangular Mars Sphere, $R=3,396,190\text{ m}$).
   - Mars Geographic CRS: Planetocentric IAU 2000 Sphere (East-positive longitude $[0^\circ, 360^\circ]$, Latitude $[-90^\circ, +90^\circ]$).
   - Distance: meters ($\text{m}$) or kilometers ($\text{km}$).
   - Time: seconds ($\text{s}$), hours ($\text{h}$), or Martian Sols ($88,775.244\text{ s/sol}$).
   - Slope: degrees ($^\circ$) derived via Horn 3x3 finite-difference kernel.
5. **Data Provenance Attributes:**
   - Terrain Dataset: `USGS_CTX_DTM_JEZERO_20M`
   - Terrain SHA-256: `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`
   - Atmosphere: NASA PDS4 archived MEDA (Perseverance) & REMS (Curiosity) measurements.
6. **Mathematical Zero-Baseline Safety:**
   - Percentage deltas must use `calculate_safe_pct_delta(candidate, baseline)`: if baseline is zero, percentage change is undefined; report absolute difference or $0.0\%$, never `inf` or `NaN`.

## Audit Checklist
- [ ] Dataset provenance and SHA-256 hashes are attached to export records.
- [ ] Model outputs are labeled as "Simulated Planning Estimates," not real telemetry.
- [ ] No physical Mars probability claims are made from finite stress cases.
- [ ] No modeled path is called certified safe for human crew.
- [ ] Zero-baseline divisions are safely guarded.
- [ ] Causal claims are supported by explicit event ledger records.
