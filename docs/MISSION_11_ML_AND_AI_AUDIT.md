# MISSION 11 — MACHINE LEARNING & ARTIFICIAL INTELLIGENCE ARCHITECTURAL AUDIT

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Standard:** NASA Autonomous Systems Taxonomy (NASA OCT TA-4), Software Assurance Standards (NASA-STD-8739.8B)  
**Investigation Scope:** Source code inspection across `src/`, model weight search, dependency analysis, and algorithmic classification.  
**Deliverable File Link:** [`MISSION_11_ML_OPPORTUNITY_ASSESSMENT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_ML_OPPORTUNITY_ASSESSMENT.md)

---

## 1. Executive Summary & Verification Findings

A comprehensive static analysis and dependency audit was conducted across the entire MarsWalk codebase to determine the presence, scope, and implementation details of Machine Learning (ML) and Artificial Intelligence (AI).

### Key Audit Findings:
1. **Pre-Trained Deep Learning Weights:** **ZERO (0).** No pre-trained neural network weights (`.pt`, `.pth`, `.onnx`, `.h5`, `.bin`, `.weights`, `.joblib`) exist anywhere in the repository.
2. **Deep Learning Framework Dependencies:** **ZERO (0).** Neither PyTorch, TensorFlow, Keras, JAX, Scikit-learn, XGBoost, nor LightGBM are listed in `pyproject.toml` or imported anywhere in `src/`.
3. **Statistical Machine Learning Implementation:** **YES (Active).** In [`preferences.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/preferences.py), MarsWalk implements a custom, self-contained **Bradley-Terry pairwise preference ranking model** ($L_2$-regularized logistic cross-entropy minimization solved via SciPy's L-BFGS-B convex optimizer).
4. **Primary AI Architecture:** The platform's intelligence is built on **classical deterministic AI**, heuristic graph search, multi-objective Pareto optimization, physics-based terramechanics, and deterministic discrete-event simulation (DES).

---

## 2. Subsystem Algorithmic Classification Matrix

To eliminate buzzword ambiguity, every intelligent subsystem within MarsWalk 2.0 is rigorously classified below according to its mathematical foundation:

| Subsystem Module | Primary Function | Algorithmic Classification | Mathematical / Computational Formulation |
| :--- | :--- | :--- | :--- |
| [`planner.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/planner.py) | Point-to-point and multi-stop traverse planning | **Classical AI / Heuristic Graph Search** | Directed 8-connected **A\* Search** with generalized Octile distance heuristic; Pairwise cache; Bounded **Beam Search** for TSP stops. |
| [`science_budget.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/science_budget.py) | Multi-criteria route trade-off analysis | **Multi-Objective Optimization** | **Pareto Frontier Identification**; Non-dominated sorting across 3 dimensions: Distance ($d$), Slope Risk ($\theta_{\max}$), Science Score ($S$). |
| [`terrain.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/terrain.py) | Traversability and energy expenditure modeling | **Physics-Based Empirical Modeling** | **Horn's 8-neighbor gradient filter** for topographic slope ($\nabla z$); Root-mean-square roughness; **Bekker-Wong terramechanics** soft regolith slip resistance. |
| [`campaign_simulator.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/campaign_simulator.py) | Mission execution and environment interaction | **Deterministic Discrete-Event Simulation (DES)** | **Bresenham 3D line-of-sight raycasting** over CTX raster; Modified **Beer-Lambert solar attenuation** ($I = I_0 e^{-\tau/\cos\theta}$); Merkle hash-chain logging. |
| [`autonomous_resilience.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/autonomous_resilience.py) | Dynamic contingency response & communications | **Automated FDIR & Networking Protocol** | **Finite-State Machine (FSM)** for Fault Detection, Isolation & Recovery; **RFC 5050 Delay-Tolerant Networking (DTN)** custody transfer queue. |
| [`preferences.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/preferences.py) | Commander AI Operator Preference Learning | **Statistical Machine Learning (Online Preference Learning)** | **Bradley-Terry pairwise logistic regression** with $L_2$ regularization; Convex loss optimization via **SciPy L-BFGS-B**. |
| [`route_explainer.py`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/src/marswalk/core/route_explainer.py) | Natural language route trade-off explanations | **Deterministic Template-Based NLG** | Multi-persona explainability templates (Professional, Concise, Field Geologist, Skeptical Flight Director). |

---

## 3. Deep Dive: The Statistical Machine Learning Implementation (`preferences.py`)

While MarsWalk does not employ deep neural networks, it does contain a mathematically rigorous, self-contained statistical learning engine:

### 3.1 Problem Formulation
When human mission planners select a preferred traverse over alternative candidate routes, the system observes a preference pair: $\mathbf{x}_{\text{sel}} \succ \mathbf{x}_{\text{rej}}$, where $\mathbf{x} \in \mathbb{R}^4$ is a normalized feature vector:
$$\mathbf{x} = \begin{bmatrix} \tilde{d}_{\text{norm}} & \tilde{\theta}_{\text{slope, norm}} & \tilde{r}_{\text{rough, norm}} & \tilde{S}_{\text{science, norm}} \end{bmatrix}^T$$

### 3.2 Bradley-Terry Pairwise Logistic Loss
Under the Bradley-Terry preference model, the probability that the operator prefers route $\mathbf{x}_i$ over $\mathbf{x}_j$ is modeled as:
$$P(\mathbf{x}_i \succ \mathbf{x}_j) = \sigma(\mathbf{w}^T (\mathbf{x}_i - \mathbf{x}_j)) = \frac{1}{1 + e^{-\mathbf{w}^T (\mathbf{x}_i - \mathbf{x}_j)}}$$

The objective function minimizes the $L_2$-regularized negative log-likelihood:
$$\mathcal{L}(\mathbf{w}) = \sum_{k=1}^K \ln\left(1 + e^{-\mathbf{w}^T \mathbf{z}_k}\right) + \frac{\lambda}{2} \|\mathbf{w}\|_2^2$$
where $\mathbf{z}_k = \mathbf{x}_{\text{sel}, k} - \mathbf{x}_{\text{rej}, k}$ and $\lambda = 0.5$ (regularization hyperparameter).

### 3.3 Optimization Engine
The gradient is computed analytically:
$$\nabla_{\mathbf{w}} \mathcal{L} = -\sum_{k=1}^K (1 - \sigma(\mathbf{w}^T \mathbf{z}_k)) \mathbf{z}_k + \lambda \mathbf{w}$$
MarsWalk passes $\mathcal{L}(\mathbf{w})$ and $\nabla_{\mathbf{w}} \mathcal{L}$ directly to `scipy.optimize.minimize` using the **L-BFGS-B quasi-Newton optimizer** (`options={"maxiter": 100, "ftol": 1e-7}`).

### 3.4 Verification of Architectural Independence
The preference learner is strictly decoupled from the core pathfinder:
- The A\* pathfinder generates all candidate routes deterministically.
- The preference learner only scores and ranks feasible candidates post-generation.
- Infeasible routes (violating slope, energy, or distance constraints) are **never** ranked or recommended, preserving hard safety constraints regardless of learned weights.

---

## 4. Why Classical AI Was Chosen Over Deep Learning

The deliberate choice of classical AI and convex optimization over deep neural networks reflects established NASA flight software engineering principles:

1. **Deterministic Reproducibility:** In space exploration operations, identical inputs must yield identical routes. Deep neural networks and stochastic policies can produce inconsistent outputs, introducing mission risk.
2. **Flight Computer Resource Footprint:** Mars flight computers (e.g., RAD750 at $133\,\text{MHz}$ with $512\,\text{MB}$ RAM, or High-Performance Spaceflight Computing RISC-V) cannot host multi-gigabyte PyTorch/CUDA environments. MarsWalk runs 100% locally with zero GPU requirements and minimal RAM footprint ($<200\,\text{MB}$).
3. **Certified Safety Bounds:** Classical A\* guarantees optimality and completeness on the discretized grid. It cannot hallucinate non-existent corridors or path through impassable cliffs.
4. **Auditability and Explainability:** Flight directors must understand *why* a route was chosen. MarsWalk's Horn slope costs and Pareto frontiers can be inspected and defended mathematically in mission reviews.
