# Project Atlas: Research Preview 1.0 Release Notes

**Release Identifier:** `Atlas Research Preview 1.0`  
**Internal Build:** `13V-RC1`  
**Classification:** Research Simulation Software Preview (Local Evaluation Candidate)  
**Publication Status:** **UNPUBLISHED (Local Release Candidate Only)**  
**Date:** 2026-11-06  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)

---

## 1. Release Overview

`Atlas Research Preview 1.0` represents the culmination of Milestones 13A through 13V of Project Atlas / MarsWalk 2.0. It packages the unified planetary mission simulation architecture for independent review by university laboratories, planetary scientists, and aerospace systems engineers.

> [!IMPORTANT]
> **Notice to Reviewers:**  
> This software is an independent academic research tool for mission design and simulation. It has not been published or deployed to external package registries. It is not operational flight software and does not certify astronaut life-support safety.

---

## 2. Changelog & Cumulative Capabilities

### Core Capabilities Unified in this Release
- **Remote-Sensing Core:** Direct ingestion of USGS 20 m/pixel Jezero Crater CTX elevation models (`data/processed/jezero_ready_20m.tif`, SHA-256: `875e7e...`) and MOLA global basemaps.
- **Surface & Aerial Routing:** Terrain-constrained $A^*$ search and multi-stop TSP pathfinding coupled with 3-DOF rotorcraft momentum theory in thin Martian $CO_2$ ($M_{\text{tip}} < 0.75$).
- **Active Bayesian Science:** Active learning hypothesis testing evaluating mineralogical and lacustrine targets with Shannon entropy reduction tracking.
- **Deep Space Communication Latency:** Realistic $OWLT$ light-time delay simulation ($3\text{ to }22\text{ minutes}$) with cryptographic state-hash verification for stale command rejection.
- **Nuclear & Solar Infrastructure:** NASA Kilopower-class $40\text{ kWe}$ fission baseline, secondary solar grids, Solid Oxide Electrolysis (MOXIE analogue) $O_2$ production, Sabatier methanation, and microwave regolith block sintering.
- **Autonomous Resilience Engine:** Closed-loop Fault Detection, Isolation, and Recovery (FDIR) executing automated load-shedding during convective dust storms ($\tau = 2.80$) while preserving base life support thermal baselines ($294.15\text{ K}$).
- **Reproducible Flagship Campaign:** One-command reproduction of `ATLAS-MARS-BASE-ALPHA-001` with bit-exact SHA-256 Merkle root hashing (`f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`).

---

## 3. Quick-Start Reproduction Guide

```bash
# 1. Clone repository and navigate to root
cd E:\Python\NASA-Spaceapps\Marswalk

# 2. Automated environment setup (PowerShell)
.\scripts\setup_atlas.ps1

# 3. Verify environment and dataset integrity
python scripts/verify_installation.py

# 4. Execute the flagship 60-Sol mission reproduction
python scripts/run_flagship_mission.py

# 5. Launch interactive web cockpit (Localhost port 3000)
.\scripts\start_atlas.ps1 -Port 3000
```

---

## 4. Test Evidence & Verification Status

```
========================================================================================
RELEASE CANDIDATE VERIFICATION SUMMARY: ATLAS RESEARCH PREVIEW 1.0
========================================================================================
Verification Gate                    Result             Details
----------------------------------------------------------------------------------------
Full Automated Unit & Integration    1,116 / 1,116 PASS Zero failures; 2 warnings (227.2s)
Dedicated Adversarial Gauntlet       20 / 20 PASS       All 12 failure challenges verified
Preflight System Health Audit        12 / 12 PASS       Verified in 428.4 ms on port 3000
Clean Environment Installation       VERIFIED           Tested on pristine virtualenv
Deterministic Flagship Replay        BIT-EXACT MATCH    Root Hash: f9d124...bd14
Closed Mass Balance Check            CONSERVED          Net Discrepancy: 0.000000 kg
========================================================================================
```

---

## 5. Documentation Index

- **Research Architecture Package:** [`docs/research/architecture-overview.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/architecture-overview.md)
- **Subsystem Ownership Manifesto:** [`docs/research/module-ownership.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/module-ownership.md)
- **Data Flow & Telemetry Pipelines:** [`docs/research/data-flow.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/data-flow.md)
- **Discrete Event Model:** [`docs/research/event-model.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/event-model.md)
- **Multi-Tier Mission State Model:** [`docs/research/mission-state-model.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/mission-state-model.md)
- **HTTP REST API Reference:** [`docs/research/api-reference.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/api-reference.md)
- **Scientific Evidence Model:** [`docs/research/scientific-evidence-model.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/scientific-evidence-model.md)
- **Resource Accounting Ledgers:** [`docs/research/resource-accounting.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/resource-accounting.md)
- **Known Limitations & Disclosures:** [`docs/research/known-limitations.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/known-limitations.md)
- **Technical Research Paper Draft:** [`docs/publication/project-atlas-research-paper.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/publication/project-atlas-research-paper.md)
- **External Reviewer Guide & Challenge Kit:** [`docs/13v-external-reviewer-guide.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/13v-external-reviewer-guide.md)
- **Data Provenance & Licenses:** [`DATA_PROVENANCE_AND_LICENSES.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/DATA_PROVENANCE_AND_LICENSES.md)
- **Third-Party Notices:** [`THIRD_PARTY_NOTICES.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/THIRD_PARTY_NOTICES.md)
