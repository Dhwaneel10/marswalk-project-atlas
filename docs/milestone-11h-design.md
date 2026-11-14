# MarsWalk 2.0 — Milestone 11H Design Document
## Campaign Design Space Explorer & Pareto Optimization

**Milestone:** 11H (MarsWalk 2.0 V2)  
**Status:** DESIGN & IMPLEMENTATION  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater Topography)  

---

## 1. Objective & Scope

The **Campaign Design Space Explorer** enables deterministic multi-objective evaluation across a bounded set of plausible campaign configurations. It evaluates alternative planner options, identifies Pareto-efficient candidate configurations, and provides grounded trade-off explanations to guide mission planning decisions without relying on arbitrary composite scores or unvalidated probabilistic models.

### Operational Boundaries & Scientific Disclaimers
1. **Deterministic Bounded Search**: The engine evaluates a finite, user-bounded collection of configurations. It is **NOT** an unbounded global optimizer, genetic algorithm, or probabilistic Monte Carlo simulator.
2. **No Fabricated Data**: Metrics are strictly computed from authentic USGS CTX 20m topography and existing kinematic models. No telemetry, sensor noise, or unmodeled consumables are invented.
3. **No Magic Composite Scores**: Objectives are retained as a documented multi-dimensional vector:
   $$\mathbf{J}(c) = \big( -\text{ScienceCoverage}(c),\, \text{Duration}(c),\, \text{Distance}(c),\, \text{UnallocatedPriority}(c),\, \text{Conflicts}(c) \big)$$
4. **Feasibility Gate**: Infeasible candidates (violating duration budgets, slope limits, or prerequisites) are partitioned and cannot dominate feasible candidates.
5. **Campaign Immutability**: Evaluating design spaces or promoting candidates never mutates historical baseline campaign versions; promotion generates a distinct new version ($v_{n+1}$).

---

## 2. Mathematical Formalism: Pareto Dominance

Let $\mathcal{C}$ be the set of evaluated campaign configurations. Each candidate $c \in \mathcal{C}$ yields an objective vector:
$$\mathbf{z}(c) = \big( z_1(c), z_2(c), z_3(c), z_4(c), z_5(c) \big)$$
where:
- $z_1(c) = \text{ScienceCoveragePct}(c) \in [0, 100]$ (to **maximize**)
- $z_2(c) = \text{TotalDurationSeconds}(c) \ge 0$ (to **minimize**)
- $z_3(c) = \text{TotalDistanceMeters}(c) \ge 0$ (to **minimize**)
- $z_4(c) = \text{UnallocatedPriority}(c) \ge 0$ (to **minimize**)
- $z_5(c) = \text{TemporalConflictsCount}(c) \ge 0$ (to **minimize**)

### Dominance Relation ($\succ$)
Let $A, B \in \mathcal{C}$ both be **feasible** candidates:
$$A \succ B \iff \begin{cases}
z_1(A) \ge z_1(B) \land z_2(A) \le z_2(B) \land z_3(A) \le z_3(B) \land z_4(A) \le z_4(B) \land z_5(A) \le z_5(B) \\
\mathbf{AND} \\
\big( z_1(A) > z_1(B) \lor z_2(A) < z_2(B) \lor z_3(A) < z_3(B) \lor z_4(A) < z_4(B) \lor z_5(A) < z_5(B) \big)
\end{cases}$$

### Candidate Partitions
1. **Pareto Frontier ($\mathcal{P}$)**: Feasible candidates not dominated by any other feasible candidate:
   $$\mathcal{P} = \{ c \in \mathcal{C}_{\text{feasible}} \mid \nexists c' \in \mathcal{C}_{\text{feasible}} \text{ s.t. } c' \succ c \}$$
2. **Dominated ($\mathcal{D}$)**: Feasible candidates dominated by at least one $c' \in \mathcal{P}$:
   $$\mathcal{D} = \{ c \in \mathcal{C}_{\text{feasible}} \mid \exists c' \in \mathcal{C}_{\text{feasible}} \text{ s.t. } c' \succ c \}$$
3. **Infeasible ($\mathcal{I}$)**: Candidates that violate kinematic limits, route feasibility, or sol time envelopes.
4. **Incomparable ($\mathcal{U}$)**: Candidates with missing, undefined, or incompatible metrics.

---

## 3. Search Dimensions & Bounds

### Supported Planning Dimensions
- **Planning Profiles**: `science_priority`, `time_constrained`, `conservative`.
- **Per-Sortie Duration Limits**: $21,600\text{ s}$ (6h), $28,800\text{ s}$ (8h), $32,400\text{ s}$ (9h), $36,000\text{ s}$ (10h).
- **Campaign Max Sols**: 2, 3, 4, 5 Sols.
- **Coordination Strategies**: `priority_first`, `balanced_workload`, `capability_matched`, `proximity_clustered`.
- **Target Subsets**: Mandatory core targets vs optional secondary targets.

### Search Bounds Controls
- `max_candidates`: Hard upper bound on generated candidates (default 10, max 25).
- `max_planner_calls`: Hard limit on heavy A* route planning executions.
- `input_deduplication`: SHA256 input fingerprinting prevents evaluating redundant configurations.
- `search_completeness`: If budget limits stop search before covering all dimension combinations, the engine explicitly reports `is_exhaustive: false`, `limit_reached: true`, and notes unexplored scopes.

---

## 4. API Endpoints & Contract Schema

### JSON Schema Contract
- Path: `schemas/api/v1/campaign-design-space.schema.json`
- Dialect: Draft 2020-12
- Enforces strict typing for design space runs, candidate metrics, dominance classifications, search bounds, and provenance.

### REST Endpoints
- `POST /api/campaign/design-space/evaluate`: Launches exploration and returns evaluated candidates.
- `GET /api/campaign/design-spaces`: Lists saved design space explorations.
- `GET /api/campaign/design-space/<id>`: Retrieves a specific design space run.
- `POST /api/campaign/design-space/promote`: Promotes a chosen candidate to a new campaign version ($v_{n+1}$).

---

## 5. Atlas UI Integration (Tab 8: `#campaignDesignSpaceView`)

- **Search Controls**: Interactive sliders and checkboxes for dimensions, bounds, and profile options.
- **Summary Metrics**: Considered, Deduplicated, Evaluated, Infeasible, Pareto Count, and Completeness status.
- **2D Trade-Off Scatter Plot**: Duration ($X$-axis) vs Science Coverage ($Y$-axis) visualizing the Pareto frontier line.
- **Candidate Comparison Table**: Sortable table with Pareto badges, delta metrics, and selection triggers.
- **Candidate Inspector & Promotion**: Inspects trade-off rationale, exact configuration differences, and promotes candidate to a new campaign version.
- **JSON Briefing Export**: Exports full reproducible design space record.
