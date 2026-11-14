# PROJECT ATLAS — MILESTONE 13Q
# SCIENTIFIC EVIDENCE GRAPH SPECIFICATION
## Directed Acyclic Lineage, Cryptographic Provenance & Evidential Authority Bounding

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_evidence_graph.py`  
**Status:** `QUALIFIED`

---

## 1. Overview

The **Scientific Evidence Graph** is an immutable Directed Acyclic Graph (DAG) that establishes an unbroken chain of custody from raw planetary sensor telemetry to high-level scientific discoveries:

$$\text{Observation} \longrightarrow \text{Measurement} \longrightarrow \text{Feature} \longrightarrow \text{Interpretation} \longrightarrow \text{Hypothesis}$$

Every node maintains its own cryptographic payload hash (SHA-256), sensor calibration status, measurement quality metrics, and spatial/temporal coordinates.

---

## 2. Evidence Taxonomy and Hierarchy

To prevent the common AI error of treating synthetic scenario defaults as real observational discoveries, Milestone 13Q establishes a strict taxonomy of evidence classifications:

| Classification | Authority Rank | Description |
|---|---|---|
| `DIRECT_OBSERVATION` | 7 (Highest) | Unprocessed raw in-situ or orbital sensor telemetry. |
| `CALIBRATED_OBSERVATION` | 6 | Radiometrically, geometrically, or spectrally calibrated telemetry. |
| `DERIVED_OBSERVATION` | 5 | Extracted quantitative physical metrics (e.g., band depth, slope). |
| `MODEL_OUTPUT` | 4 | Forward physical simulations (e.g., GCM temperature, MCD reanalysis). |
| `INFERRED_FEATURE` | 3 | Algorithmic or heuristic feature classification (e.g., boulder, slump). |
| `SCIENTIFIC_INTERPRETATION` | 2 | High-level geological interpretation (e.g., lacustrine deposit). |
| `SIMULATED_OBSERVATION` | 1 | Synthetically generated test inputs or mock telemetry. |
| `CONFIGURED_ASSUMPTION` | 0 (Lowest) | Operator-configured simulation boundary condition. |

---

## 3. The Evidential Authority Rule

> [!IMPORTANT]
> **EVIDENTIAL AUTHORITY BOUNDING INVARIANT:**
> An interpretation, derived feature, or scientific hypothesis can **NEVER inherit greater evidential authority than the weakest supporting measurement in its upstream ancestral lineage.**

For example:
- If a synthetic radar sounder (`SIMULATED_OBSERVATION`, rank 1) detects an apparent reflector, an upstream derived boundary (`DERIVED_OBSERVATION`, rank 5) and an interpretation claiming "Subsurface Ice Sheet" (`DIRECT_OBSERVATION`, rank 7) are evaluated by `get_maximum_inherited_authority()`.
- The engine traverses the complete ancestral DAG, identifies the weakest link (`SIMULATED_OBSERVATION`), and clamps the maximum empirical authority of the claim to `SIMULATED_OBSERVATION`.
- This mathematically prevents Project Atlas from ever claiming an in-situ Martian discovery based on synthetic simulation models.
