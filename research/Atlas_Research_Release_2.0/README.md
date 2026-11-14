# Project Atlas Research Release 2.0
## Standalone Evaluation Package & Scientific Reproduction Baseline

**Package Designation:** `ATLAS-RESEARCH-RELEASE-2.0`  
**Milestone:** `13AG — THE EXTERNAL RESEARCH CHALLENGE`  
**Parent Milestone:** `13AF — Independent Benchmark & Research Freeze`  
**Release Date:** 2026-11-07  
**Status:** `READY_FOR_EXTERNAL_RESEARCH_REVIEW`  
**License:** Open Science / MIT Compatible  

---

## 1. Executive Summary

Project Atlas is an open-architecture planetary mission simulation and autonomous operations platform designed for Mars surface, aerial, and orbital operations.

**Research Release 2.0** provides external peer reviewers, aerospace communications engineers, planetary scientists, and software quality auditors with a completely frozen, self-contained baseline to independently reproduce, audit, and challenge the physical and computational models implemented in Project Atlas.

### What is Included in this Package:
1. **Frozen Source Code Snapshot (`src/marswalk/core/`):** Full, unedited implementations of Martian atmospheric radiative transfer, antenna radiation patterns, physical link budgets, orbital contact planning, and delay-tolerant routing.
2. **Zero-Dependency Benchmark Suite (`benchmarks/`):** Standalone reference implementations replicating optical dust extinction, RF dust-storm attenuation, receiver noise reference-plane invariance, antenna Airy patterns, and end-to-end link budget scenarios with zero third-party packages.
3. **Primary Parameter & Provenance Registry (`data/`):** Complete provenance metadata, primary literature citations, and 5-regime sensitivity matrices for all astrophysical parameters.
4. **Three Domain Review Dossiers (`REVIEW_TRACKS.md`):** Deep technical overviews for Review A (Atmosphere), Review B (RF Engineering), and Review C (Scientific Computing).
5. **36-Question Falsification Questionnaire (`EXTERNAL_CHALLENGE_QUESTIONS.md`):** Rigorous, probing inquiries inviting reviewers to test model limits, assumptions, and edge cases.
6. **Technical Academic Paper (`TECHNICAL_PAPER.md`):** Full academic manuscript detailing architecture, physical equations, validation evidence, and non-probabilistic truth disclosures.
7. **Evidence Reconciliation Dossier (`EVIDENCE_RECONCILIATION.md`):** Complete resolution of reporting discrepancies, including test collection taxonomy, execution runtimes, and the mass-normalization equivalence of Goldhirsh vs Ho & Golshan.
8. **Cryptographic Manifest (`SOURCE_MANIFEST.sha256`):** SHA-256 hashes for every file in the package.

---

## 2. Quick Navigation Index

| Document / Asset | Purpose & Contents | Primary Audience |
|:---|:---|:---|
| [`RELEASE_README.md`](RELEASE_README.md) | High-level package introduction and reviewer quick-start guide | All Reviewers |
| [`TECHNICAL_PAPER.md`](TECHNICAL_PAPER.md) | Full technical academic paper describing system and physics | Academic & Research Community |
| [`EVIDENCE_RECONCILIATION.md`](EVIDENCE_RECONCILIATION.md) | Detailed resolution of all internal reporting discrepancies | Systems & Verification Auditors |
| [`REVIEW_TRACKS.md`](REVIEW_TRACKS.md) | Specialized technical dossiers across Tracks A, B, and C | Domain Specialists |
| [`EXTERNAL_CHALLENGE_QUESTIONS.md`](EXTERNAL_CHALLENGE_QUESTIONS.md) | 36 structured challenge questions for scientific falsification | Peer Reviewers |
| [`EXTERNAL_REVIEW_TARGETS.md`](EXTERNAL_REVIEW_TARGETS.md) | Prioritized candidate research institutions and public groups | Planning & Outreach |
| [`REVIEW_RESPONSE_REGISTER.md`](REVIEW_RESPONSE_REGISTER.md) | Formal intake and status tracking register for review comments | Maintainers & Reviewers |
| [`SOURCE_MANIFEST.sha256`](SOURCE_MANIFEST.sha256) | Cryptographic verification manifest of all package files | Security & Integrity Auditors |
| [`BENCHMARK_MANIFEST.json`](BENCHMARK_MANIFEST.json) | Metadata, input parameters, and tolerances for all benchmarks | Computational Reviewers |
| [`ENVIRONMENT.json`](ENVIRONMENT.json) | Complete execution environment, Python interpreter, and versions | DevOps & Replication Specialists |
| [`TEST_EXECUTION_RECORD.json`](TEST_EXECUTION_RECORD.json) | Process-level metrics and stdout records for the 94-file test suite | Quality Assurance Engineers |

---

## 3. How to Run the Independent Benchmarks

### Requirements
- Standard Python 3.10 or higher.
- **Zero external libraries required** (`math`, `json`, `dataclasses`, and `hashlib` only).

### Execution Commands

```bash
# Navigate to the benchmarks directory
cd benchmarks

# 1. Run all 4 fundamental propagation benchmarks
python run_all_benchmarks.py

# 2. Run the 3 end-to-end communication scenarios
python benchmark_link_budget_scenarios.py

# 3. Run the clean-environment reproducibility verification
python test_clean_environment_reproducibility.py
```

All 3 scripts should output `PASS` with zero errors.

---

## 4. Key Scientific Disclosures

1. **Optical Extrapolation:** 1550 nm laser attenuation is an Ångström power-law extrapolation ($\alpha = -0.082$) from MER Pancam 440–880 nm observations. It is **not** a direct in-situ laser measurement.
2. **Dielectric Analogs:** RF dust storm permittivity $\epsilon_r = 2.80 - j 0.0420$ ($\tan\delta = 0.015$) is derived from terrestrial basalt and Apollo lunar regolith analogs at zero moisture.
3. **Rayleigh-Jeans Brightness Departure:** At 32 GHz, the equivalent Rayleigh-Jeans brightness temperature is $2.029\text{ K}$, departing by $-0.70\text{ K}$ ($-25.54\%$) from the thermodynamic $2.725\text{ K}$ CMB.
4. **No Flight Certification:** All simulation models and schedules are research tools and are **not** certified for crewed spaceflight without hardware-in-the-loop validation.

---

## 5. Reviewer Feedback Protocol

Please log critical reviews, corrections, or challenge answers using the template provided in [`REVIEW_RESPONSE_REGISTER.md`](REVIEW_RESPONSE_REGISTER.md).
