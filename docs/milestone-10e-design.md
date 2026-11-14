# MarsWalk 2.0 — Milestone 10E: Mission Science Report & Export Dashboard
## Technical Architecture & Engineering Design Specification

### 1. Overview & Objective
Milestone 10E delivers an authoritative, reproducible **Mission Science Report & Export Dashboard** for MarsWalk 2.0 / Project Atlas. It aggregates all analytical dimensions of an EVA traverse—including A* cost-optimized routing metrics, science sampling waypoint sequences and dwell allocations, sortie black-box event ledger entries, and source-attributed Martian environmental intelligence snapshots—into both an isolated, print-friendly, self-contained HTML publication document and a companion machine-readable JSON archive compliant with JSON Schema Draft 2020-12.

---

### 2. Core Architectural Pillars

```
+---------------------------------------------------------------------------------------------------+
|                                  MARSWALK 2.0 DATA REPOSITORY                                     |
|                                                                                                   |
|  [Saved Mission Plan]        [A* Routing Engine]      [Sortie Black Box]     [Weather Manager]   |
|  - Start / Goal / Stops      - Traversal Distance     - Mission Events       - In-Situ (MEDA)     |
|  - Vehicle Envelope          - Cost Function Score    - Contingencies        - In-Situ (REMS)     |
|  - Dwell Requirements        - Min/Max Elevation      - Detour Continuations - Climatology (MCD)  |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                        MISSION SCIENCE REPORT ASSEMBLER (mission_report.py)                       |
|                                                                                                   |
|  1. Stable Report ID Generation (rep_<slug>_<uid>)                                               |
|  2. Reproducibility Manifest (USGS CTX DTM 20m, SHA-256 hash, Model & Assumptions Versions)       |
|  3. Safe Handling of Missing Telemetry (Explicit Nulls, is_computed flags, No Zero-Filling)       |
|  4. Environmental Attribution (Strict Separation: In-Situ vs Modelled Climatology vs Archives)   |
|  5. Strict HTML Escaping (html.escape against XSS vectors)                                       |
|  6. Contract Validation against schemas/api/v1/mission-science-report.schema.json                 |
+---------------------------------------------------------------------------------------------------+
                                                  │
                        ┌─────────────────────────┴─────────────────────────┐
                        ▼                                                   ▼
+-----------------------------------------------+   +-----------------------------------------------+
|       SELF-CONTAINED HTML SCIENCE REPORT      |   |       MACHINE-READABLE JSON COMPANION         |
|  - Embedded Dark Theme (Atlas UI aesthetic)   |   |  - Full Draft 2020-12 Schema Compliance       |
|  - High-Contrast Clean Print Stylesheet       |   |  - Unaltered DTM Coordinates & Telemetry      |
|  - Complete Waypoint & Black-Box Event Tables |   |  - Reproducible Input Fingerprints            |
|  - USGS / PDS Source Provenance Links         |   |  - Ideal for Peer Review & Automated Audits   |
+-----------------------------------------------+   +-----------------------------------------------+
```

---

### 3. Data Contract Specification (`mission-science-report.schema.json`)

The report structure is strictly governed by `schemas/api/v1/mission-science-report.schema.json`:
- `report_id`: String pattern `^rep_[a-zA-Z0-9_-]{3,64}$`.
- `generated_at_utc`: RFC 3339 / ISO 8601 UTC timestamp.
- `mission_id` & `mission_name`: Mission identity tokens.
- `mission_status`: `"nominal"`, `"disrupted"`, `"continued"`, `"completed"`, `"incomplete"`, or `"infeasible"`.
- `reproducibility_manifest`:
  - `terrain_dataset_id`: `"USGS_CTX_DTM_JEZERO_20M"`
  - `terrain_sha256`: `"875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"`
  - `model_version`: `"2.0.0"`
  - `software_version`: `"2.0.0"`
- `plan_summary`: Coordinates, elevations, vehicle envelope, and stop count.
- `mobility_metrics`: Distance, cost, total and traversal duration, dwell, slopes, and elevation relief. Explicitly nullable with `is_computed: false` if trajectory calculation is pending.
- `stop_metrics`: Array of waypoints with target names, DTM cell coordinates, planned dwell times, and execution status (`"planned"`, `"reached"`, `"in_progress"`).
- `sortie_ledger_summary`: Black-box event count, contingency flags, continuation counts, and chronological event ledger entries.
- `environmental_context`: Provenance-labelled atmospheric pressure, air temperature, wind velocity, optical depth ($\tau$), Sol, and source institution.
- `provenance_audit`: Data sources, analytical verification notes, and NASA operational disclaimers.

---

### 4. Atlas Web UI Integration

The report dashboard is surfaced directly in Atlas:
1. **Header Entry Point (`#btnHeaderReport`)**: Direct access button styled with amber accent next to Environmental Intelligence.
2. **Dashboard Modal (`#missionReportModal`)**:
   - Mission Selector: Switch between the active traversal plan or any saved mission definition.
   - Atmospheric Site Selector: Select from Jezero Crater (Perseverance MEDA), Gale Crater (Curiosity REMS), Olympus Mons (MCD), or Elysium Planitia (InSight).
   - Metrics Ribbon: Real-time summaries of traversal distance, duration, dwell, weather site, and black-box event count.
   - High-Fidelity Sandboxed Preview: Renders the full report within an isolated `<iframe>` (`srcdoc`), preventing CSS leakage while delivering true WYSIWYG fidelity.
   - Instant Actions:
     - `⬇ HTML`: Exports standalone offline document (`marswalk_rep_*.html`).
     - `⬇ JSON`: Exports structured contract payload (`marswalk_rep_*.json`).
     - `🖨 PRINT`: Dispatches browser print dialog invoking high-contrast black-and-white `@media print` layout.

---

### 5. Scientific Integrity & Disclaimers

In accordance with NASA Space Apps challenge rules and scientific integrity requirements:
- **No Synthetic Observations**: In-situ telemetry is sourced solely from official NASA PDS archives (MEDA on Mars 2020 Perseverance, REMS on MSL Curiosity).
- **Model Disclosures**: Climatological models (Mars Climate Database v6.1) are explicitly demarcated as simulated baselines.
- **Astronaut Safety Warning**: Modeled traverse envelopes and cost surfaces are analytical tools and are prominently badged: *"NOT certified operationally safe for crewed surface exploration without real-time mission ops verification."*
