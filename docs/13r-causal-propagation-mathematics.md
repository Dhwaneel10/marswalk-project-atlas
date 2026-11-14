# ATLAS 13R — CAUSAL PROPAGATION MATHEMATICS
## Directed Acyclic Graphs, Boolean Logic Gates, and Cascade Dynamics

**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Milestone:** 13R — Atlas Apocalypse Engine  
**Module:** `src/marswalk/core/mars_failure_propagation.py`  

---

### 1. Mathematical Formulation of Failure Propagation

In complex space systems, an individual component failure rarely remains isolated. Instead, electrical cross-strapping, shared thermal busses, software scheduling queues, and resource constraints cause failures to cascade across subsystems.

We model failure propagation as a time-parameterized Directed Acyclic Graph:
$$\mathcal{G} = (\mathcal{V}, \mathcal{E}, \mathcal{G}_{\text{logic}}, \mathcal{T}_{\text{delay}}, \mathcal{B}_{\text{contain}})$$

Where:
- $\mathcal{V} = \{v_1, v_2, \dots, v_n\}$ represents subsystem states or failure nodes.
- $\mathcal{E} \subseteq \mathcal{V} \times \mathcal{V}$ represents directed causal propagation pathways.
- $\mathcal{G}_{\text{logic}}: \mathcal{V} \to \{\text{OR}, \text{AND}, \text{THRESHOLD}\}$ represents the Boolean gate logic evaluating incoming causal edges.
- $\mathcal{T}_{\text{delay}}: \mathcal{E} \to \mathbb{R}^+$ represents physical propagation delay in seconds (e.g. thermal diffusion, buffer saturation time).
- $\mathcal{B}_{\text{contain}}: \mathcal{E} \to \Sigma_{\text{barriers}}$ specifies operational containment boundaries capable of severing causal edges.

---

### 2. Node Failure Activation Rules

A non-failed node $v \in \mathcal{V}$ transitions to failed at simulation time $t$ if and only if its input gate condition is satisfied:

#### A. Boolean OR Gate:
$$\text{Trigger}(v, t) = \exists e = (u, v) \in \text{Incoming}(v) \quad \text{s.t.} \quad u \text{ is failed} \;\land\; t \ge t_u + \tau_e \;\land\; \mathcal{B}(e) \notin \text{ActiveBarriers}$$

Any uncontained failed parent whose delay has elapsed activates the target.

#### B. Boolean AND Gate:
$$\text{Trigger}(v, t) = \forall e = (u, v) \in \text{UnblockedIncoming}(v), \quad u \text{ is failed} \;\land\; t \ge \max_{u}(t_u + \tau_e)$$

All non-quarantined upstream failure modes must co-occur to induce downstream system failure (e.g., loss of UHF Electra AND loss of DTE X-band is required to cause total communications silence).

---

### 3. Containment Boundary Mechanics

An edge $e = (u, v)$ with barrier assignment $b = \mathcal{B}(e)$ is severed whenever $b$ is activated by an autonomous recovery plan or operator override:
$$e \text{ is blocked} \iff b \in \text{ActiveBarriers}$$

For example:
- Edge: $\text{ROV\_MOTOR\_FR\_STALL} \xrightarrow{\tau=5\text{s}} \text{ROV\_POWER\_BUS\_SURGE}$
- Barrier: $\text{ISOLATE\_FL\_MOTOR}$
- When $\text{ISOLATE\_FL\_MOTOR}$ is energized, electrical bus overcurrent is prevented, containing the failure within the mechanical bogie boundary.

---

### 4. Causal Trace Synthesis

For any consequential failure $v_{\text{target}}$, the engine performs depth-first backward search to synthesize all minimal causal paths leading from root causes:
$$\text{Trace} = \left( v_{\text{root}} \to v_1 \to v_2 \to \dots \to v_{\text{target}}, \; \sum \tau_i, \; \{b_1, b_2, \dots\} \right)$$

This guarantees complete causal traceability for post-flight incident boards and mission assurance audits.
