# PROJECT ATLAS — RESEARCH RELEASE 2.0
## Standalone Evaluation Package for External Scientific and Engineering Reviewers

**Release Designation:** `ATLAS-RESEARCH-RELEASE-2.0`  
**Parent Milestones:** `13AF` (Independent Benchmark) & `13AG` (The External Research Challenge)  
**Publication Reference:** MarsWalk 2.0 / Project Atlas Scientific Evaluation Package  
**Current Status:** `READY_FOR_EXTERNAL_RESEARCH_REVIEW`  
**Repository Working Tree:** `https://github.com/nasa-spaceapps/marswalk` (Project Atlas)  
**Date:** 2026-11-07  

---

## 1. What is Project Atlas Research Release 2.0?

Project Atlas is an open-architecture planetary mission simulation and autonomous operations platform developed for the NASA International Space Apps Challenge. 

**Research Release 2.0** is an independently frozen research package designed to enable external planetary scientists, telecommunications engineers, and scientific software auditors to:
1. **Inspect** the exact mathematical models, equations, boundary guards, and primary literature citations used across Martian atmospheric radiative transfer, RF microwave propagation, antenna beamforming, and receiver noise.
2. **Replicate** every benchmark calculation in a clean Python environment with **zero dependencies** on the Atlas backend server or proprietary harnesses.
3. **Falsify or Challenge** modeling assumptions using a structured, 30+ question review dossier across three independent evaluation tracks.
4. **Audit** the codebase against adversarial mutations and test coverage records.

> [!IMPORTANT]
> **External Review Status Disclosure:**  
> The designation `READY_FOR_EXTERNAL_RESEARCH_REVIEW` indicates that the internal development team has frozen the codebase, reconciled all reported evidence, and verified standalone reproducibility. It **does NOT mean** external review has been completed, nor does it imply endorsement by NASA, ESA, or any external institution. Genuine external review begins only when independent researchers evaluate this package and return findings.

---

## 2. Package Directory Layout

```text
research/Atlas_Research_Release_2.0/
├── RELEASE_README.md                    # This document
├── README.md                            # Comprehensive release guide & sitemap
├── EVIDENCE_RECONCILIATION.md           # Resolution of all internal reporting discrepancies
├── REVIEW_TRACKS.md                     # Specific dossiers for Tracks A, B, and C
├── EXTERNAL_CHALLENGE_QUESTIONS.md      # 30+ falsifiable questions for external evaluators
├── EXTERNAL_REVIEW_TARGETS.md           # Prioritized candidate institutions & literature targets
├── REVIEW_RESPONSE_REGISTER.md          # Formal intake & disposition tracker for reviewer feedback
├── TECHNICAL_PAPER.md                   # Full academic paper articulating system architecture & benchmarks
├── SOURCE_MANIFEST.sha256               # Cryptographic SHA-256 hashes of all frozen files
├── BENCHMARK_MANIFEST.json              # Benchmark definitions, inputs, and expected tolerances
├── ENVIRONMENT.json                     # Complete execution environment & dependency specifications
├── TEST_EXECUTION_RECORD.json           # Raw execution metrics for full repository test suite
├── benchmarks/                          # Standalone benchmark reproduction scripts (zero dependencies)
│   ├── benchmark_optical_dust.py        # Spherical airmass & Ångström spectral scaling
│   ├── benchmark_rf_dust.py             # Multiband RF dust loss & Rayleigh volume integration
│   ├── benchmark_receiver_noise.py      # Receiver noise decomposition & reference plane invariance
│   ├── benchmark_antenna_patterns.py    # Fraunhofer distances & Airy diffraction patterns
│   ├── run_all_benchmarks.py            # Flagship standalone test runner
│   └── benchmark_results_summary.json   # Output metrics from latest execution
├── data/                                # Literature-derived parameters and sensitivity tables
│   ├── parameter_provenance_registry.json # 12 core astrophysical and RF parameters with primary citations
│   ├── optical_angstrom_sensitivity_table.csv # 5-regime Ångström exponent sensitivity matrix
│   └── rf_dust_attenuation_table.csv    # Multiband RF dust loss vs elevation angle table
└── src/marswalk/core/                   # Frozen source code snapshots of production physics modules
    ├── atlas_mars_atmospheric_model.py  # Production Martian atmospheric engine
    ├── atlas_antenna_model.py           # Production antenna field-region & pattern engine
    ├── atlas_network_link_model.py      # Production physical link budget engine
    ├── atlas_orbital_contact_planner.py # Production orbital contact planning engine
    ├── atlas_dtn_engine.py              # Delay-tolerant bundle routing engine
    └── terrain_visibility.py            # Line-of-sight elevation & terrain masking engine
```

---

## 3. Quick Start: Reproducing the Benchmarks in 60 Seconds

You do **not** need to install Atlas or run its HTTP server. The benchmark scripts in `benchmarks/` have **zero third-party dependencies** and run on any machine with standard Python 3.10+:

```bash
# 1. Navigate to the benchmarks directory
cd research/Atlas_Research_Release_2.0/benchmarks

# 2. Run the flagship independent benchmark runner
python run_all_benchmarks.py
```

### Expected Clean Console Output:

```text
================================================================================
ATLAS MILESTONE 13AF: INDEPENDENT PROPAGATION BENCHMARK SUITE
================================================================================
Running: Benchmark 1 - Optical Dust Spectral Propagation...
  [PASS] Benchmark 1: Optical Dust Attenuation replicated within 0.01 dB tolerance.

Running: Benchmark 2 - RF Dust-Storm Microwave Attenuation...
  [PASS] Benchmark 2: RF Dust Attenuation replicated within 0.005 dB tolerance.

Running: Benchmark 3 - Receiver System Noise Temperature & Reference Plane...
  [PASS] Benchmark 3: Receiver Noise replicated within 1e-12 dB tolerance.

Running: Benchmark 4 - Antenna Radiation Patterns & Far-Field Limits...
  [PASS] Benchmark 4: Antenna Radiation Patterns replicated within 0.01 dB tolerance.

================================================================================
ALL 4 INDEPENDENT PROPAGATION BENCHMARKS PASSED SUCCESSFULLY.
Summary metrics saved to: benchmark_results_summary.json
================================================================================
```

---

## 4. Integrity & SHA-256 Hash Verification

To confirm that the files in your package have not been modified or corrupted, verify the cryptographic hashes:

```bash
# On Linux/macOS:
sha256sum -c SOURCE_MANIFEST.sha256

# On Windows (PowerShell):
Get-FileHash -Algorithm SHA256 (Get-ChildItem -Recurse -File src,benchmarks,data) | Format-Table
```

---

## 5. How to Submit Feedback

External researchers are invited to submit critical reviews, corrections, counter-evidence, or challenge responses using the structured framework in [`REVIEW_RESPONSE_REGISTER.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/research/Atlas_Research_Release_2.0/REVIEW_RESPONSE_REGISTER.md).

Every comment is logged under one of seven disposition statuses:  
`OPEN` $\rightarrow$ `UNDER_INVESTIGATION` $\rightarrow$ `ACCEPTED` / `PARTIALLY_ACCEPTED` / `DISAGREED_WITH_EVIDENCE` $\rightarrow$ `REMEDIATED` $\rightarrow$ `RETESTED`.
