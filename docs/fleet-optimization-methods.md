# 6D Pareto Fleet Optimization Methods
## Multi-Objective Optimization Across Science, Mobility, Energy, Communications & Storage

**Component:** `src/marswalk/core/fleet_optimization_engine.py`  
**JSON Contract:** `schemas/api/v1/fleet-optimization.schema.json`  
**Tradeoff Dimensionality:** 6 Independent Objective Dimensions

---

## 1. The 6-Dimensional Optimization Tradeoff Space

A multi-rover planetary mission cannot be evaluated on a single scalar metric. Maximizing science return demands long, hazardous traverses; conserving battery power limits mobility; maintaining high-speed communications restricts rovers to high ridges rather than deep canyons.

Project Atlas formalizes a **6D Pareto Optimization Space** $\mathcal{F} \subset \mathbb{R}^6$:

$$\vec{f}(C) = \begin{pmatrix}
f_1(C) = \mathcal{U}_{\text{science}}(C) & (\text{Maximize, points}) \\
f_2(C) = -D_{\text{traverse}}(C) & (\text{Minimize, km}) \\
f_3(C) = \min_i SOC_i(C) & (\text{Maximize, \%}) \\
f_4(C) = \overline{\text{Reachability}}_{\text{comms}}(C) & (\text{Maximize, \%}) \\
f_5(C) = -B_{\text{storage}}(C) & (\text{Minimize, MB}) \\
f_6(C) = -T_{\text{duration}}(C) & (\text{Minimize, hours})
\end{pmatrix}$$

### Pareto Dominance Criterion:
A configuration candidate $A$ dominates candidate $B$ ($A \succ B$) if and only if:
$$\forall k \in \{1, \dots, 6\}, \quad f_k(A) \ge f_k(B) \quad \land \quad \exists k \in \{1, \dots, 6\} \quad \text{s.t.} \quad f_k(A) > f_k(B)$$

The set of all non-dominated candidates forms the **Pareto Frontier** $\mathcal{P}^*$.

---

## 2. Five Specialized Fleet Configuration Champions

From the computed Pareto frontier, Atlas extracts five specialized configuration champions tailored for distinct operational preferences:

| Profile Key | Champion Name | Optimization Objective Focus | Key Characteristics |
| :--- | :--- | :--- | :--- |
| `BALANCED_CHAMPION` | **Balanced Champion** | Equal-weight normalized composite score | Science: $2,840\text{ pts}$, Distance: $18.4\text{ km}$, Min SOC: $36.8\%$, Comms: $100.0\%$, Duration: $120.0\text{ h}$. |
| `SCIENCE_MAXIMIZING` | **Science Maximizing** | $w_{\text{sci}} = 0.60, w_{\text{prio}} = 0.40$ | Pushes rovers to all 12 targets ($3,420\text{ pts}$), accepts lower battery margins ($24.5\%$) and longer traverses ($22.8\text{ km}$). |
| `ENERGY_EFFICIENT` | **Energy Efficient** | $w_{\text{soc}} = 0.50, w_{\text{dist}} = 0.30$ | Restricts vehicle slopes to $<12^\circ$; maintains $>52.4\%$ battery margin across all rovers ($13.2\text{ km}$). |
| `COMMUNICATIONS_FOCUSED`| **Comms Focused** | $w_{\text{comms}} = 0.60, w_{\text{backlog}} = 0.25$ | Dedicated Rover Delta mobile relay positioning; zero data backlog ($0.0\text{ MB}$); $100\%$ continuous link to Base Station. |
| `MINIMUM_DURATION` | **Minimum Duration** | $w_{\text{dur}} = 0.50, w_{\text{parallel}} = 0.30$ | Aggressive parallelization across Sols 1–4 ($86.5\text{ h}$ total duration); completes objectives before nightfall. |

---

## 3. Interactive Selection & Tactical Promotion

Within the **ATLAS FLEET CONTROL CENTER**, an operator can view the 6D Pareto comparison matrix, inspect trade-offs, and promote any champion to the active baseline plan with a single click.
