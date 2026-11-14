# MarsWalk 2.0 — Milestone 11C Design Specification
## Observation-Driven Campaign Intelligence & Adaptive Science Prioritization

**Milestone:** 11C (MarsWalk 2.0 V2)  
**Status:** IMPLEMENTATION DESIGN SPECIFICATION  
**Author:** MarsWalk Core Architecture Team  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater)  

---

### 1. Motivation & Context

Milestones 11A and 11B established the **Mission Campaign Orchestrator** and **Science Observation Registry**:
- 11A partitioned multi-sol sorties across authentic USGS CTX 20m topography respecting prerequisite DAGs.
- 11B provided closed-loop execution tracking, target/sortie lifecycle transitions, and immutable observation persistence.

However, planetary exploration is not a passive checklist: **what a rover or astronaut discovers on Sol 1 must dynamically inform what they do on Sol 2 and Sol 3**.
- If a rock coring sample at *Enchanted Lake* reveals high phyllosilicate clay content (`SUPPORTS_OBJECTIVE`), downstream exploration of the delta front deposit (*Hawksbill Gap*) gains higher priority.
- If an assay shows the target vein was barren basalt (`DOES_NOT_SUPPORT_OBJECTIVE`), the campaign planner should deprioritize downstream targets on that dead-end branch and pivot resources to alternative high-yield candidate sites.
- If an observation is `INCONCLUSIVE` or anomalous, a scientist may request an explicit follow-up inspection (`repeat_observation_requested=true`).

Milestone 11C implements **Observation-Driven Campaign Intelligence** to adapt future sortie schedules based on user-defined science objectives, objective weights, and authentic observational evidence without modifying historical execution or manufacturing synthetic conclusions.

---

### 2. Explicit Objective & Evidence Data Model

#### 2.1 Objective Classifications
```python
class ObjectiveClassification(str, Enum):
    SUPPORTS_OBJECTIVE = "SUPPORTS_OBJECTIVE"
    DOES_NOT_SUPPORT_OBJECTIVE = "DOES_NOT_SUPPORT_OBJECTIVE"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_ASSESSED = "NOT_ASSESSED"
```

#### 2.2 Provenance & Anti-Fabrication Principles
1. **No Inferred Success**: A target being visited or having an observation attached does **NOT** automatically imply scientific success. The outcome must be explicitly assessed or remain `NOT_ASSESSED`.
2. **Provenance Preservation**:
   - `SIMULATED`: Atlas simulation runs.
   - `IMPORTED_PDS_MEDA` / `IMPORTED_PDS_REMS`: Authentic NASA archival data.
   - `MEASURED_IN_SITU`: Measured field instruments.
   - Provenance is **never** altered when used in reprioritization.
3. **No Fabricated Confidence**: Confidence metrics are preserved as recorded; unmeasured metrics remain `null`.

#### 2.3 Extended Target Attributes
```json
{
  "id": "hawksbill_gap",
  "name": "Hawksbill Gap",
  "priority_score": 70.0,
  "science_objective": "delta_clay_mineralogy",
  "objective_classification": "SUPPORTS_OBJECTIVE",
  "linked_observation_ids": ["obs_spec_001"],
  "repeat_observation_requested": false
}
```

---

### 3. Campaign Reprioritization Engine Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  Campaign Intelligence Reprioritizer                       │
│              (src/marswalk/core/campaign_intelligence.py)                  │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐             ┌───────────────┐             ┌───────────────┐
│ Active State  │             │ Evidence &    │             │ User Weights  │
│ - Frozen Sols │             │ Assessments   │             │ & Repeat Req  │
│ - Completed   │             │ - Observations│             │ - Objectives  │
│ - Blocked     │             │ - Outcomes    │             │ - Profile     │
└───────┬───────┘             └───────┬───────┘             └───────┬───────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
             ┌────────────────────────────────────────────────┐
             │       Priority Adjustment & Candidate Filter    │
             │ - Non-Rescheduling Invariant: completed omitted│
             │ - Boost candidates with supportive prereqs     │
             │ - Deprioritize branches with refuted prereqs   │
             │ - Inject repeat target if requested            │
             └────────────────────────┬───────────────────────┘
                                      ▼
             ┌────────────────────────────────────────────────┐
             │         Sub-Plan Planner Execution             │
             │ - plan_mission_campaign(remaining_candidates)  │
             │ - Frozen sorties preserved                     │
             │ - Shifted sol indices                          │
             └────────────────────────┬───────────────────────┘
                                      ▼
             ┌────────────────────────────────────────────────┐
             │         Explainability & Comparison            │
             │ - TargetMovementRationales per target          │
             │ - StrategyComparison: Baseline vs Proposed     │
             │ - Model limitations & missing data notes       │
             └────────────────────────────────────────────────┘
```

---

### 4. Strategy Comparison Model

Comparisons evaluate genuine metric differences across:
1. **Baseline Plan**: Current unadapted plan.
2. **Adaptive Intelligence Plan**: Observation-driven proposal.
3. **Alternative Profiles**: `science_priority`, `time_constrained`, `conservative`.

Metrics evaluated:
- **Scheduled vs Deferred Targets**
- **Priority-Weighted Science Yield**
- **Total Traverse Distance ($m$)**
- **Total Duration ($s$)**
- **Total Sols & Sorties**
- **Feasibility & Dependency Adherence**

---

### 5. API Routes

- `POST /api/campaign/reprioritize`: Accepts campaign ID or payload with objective assessments, weights, and repeat requests. Generates explainable recommendation and revised campaign plan.
- `GET /api/campaign/recommendations?campaign_id=<id>`: Retrieves past reprioritization recommendation records for a campaign.
