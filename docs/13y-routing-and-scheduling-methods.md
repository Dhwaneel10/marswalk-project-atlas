# Milestone 13Y: Routing & Scheduling Methods Specification

**Milestone:** 13Y — Atlas Planetary Network  
**Components:**
- `src/marswalk/core/atlas_planetary_routing.py`
- `src/marswalk/core/atlas_contact_scheduler.py`  
**Classification:** Algorithmic Specification & Space-Time Network Routing

---

## 1. Time-Dependent Contact Graph Routing (CGR)

Terrestrial routing protocols (e.g. OSPF, BGP) rely on persistent topological links. In deep-space planetary networks, links are episodic and intermittent.

Contact Graph Routing (CGR) models the communication topology as a directed graph where edges are discrete contact windows $W_k = (u, v, t_{start}, t_{end}, R_{data}, t_{prop})$.

### 1.1 Space-Time Dijkstra Algorithm
To find the earliest delivery path for payload of size $S$ bytes from origin $S_0$ to destination $D$:
1. State vector: $(u, t_{arr}, \text{hops})$.
2. Successor function: for an outgoing contact window $W = (u, v, t_s, t_e, R, \tau_{prop})$:
   $$t_{tx\_start} = \max(t_{arr}, t_s)$$
   $$\Delta t_{tx} = \frac{8 S}{R}$$
   If $t_{tx\_start} + \Delta t_{tx} \le t_e$, then the contact is feasible, and:
   $$t_{next\_arr} = t_{tx\_start} + \Delta t_{tx} + \tau_{prop}$$
3. Priority Queue: minimum arrival time $t_{arr}$ guarantees time-optimal delivery.

---

## 2. Competing Schedulers Taxonomy

| Scheduler ID | Designation | Priority Policy | Objective Function | Key Characteristics |
| :--- | :--- | :--- | :--- | :--- |
| **SCHED-01** | `GREEDY` | FIFO | $\min(t_{start})$ | Immediately dispatches across first available open window regardless of rate or destination proximity. |
| **SCHED-02** | `EARLIEST-DELIVERY` | CGR Dijkstra | $\min(t_{arrival})$ | Evaluates multi-hop space-time trajectories to minimize end-to-end delivery timestamp. |
| **SCHED-03** | `PRIORITY-FIRST` | Strict Class 1–6 | $\max(\text{PriorityWeight})$ | Strictly reserves high-rate passes for Class 1 (Emergency) and Class 2 (Command Uplink). |
| **SCHED-04** | `DEADLINE-AWARE` | EDF (TTL) | $\min(t_{expire} - t)$ | Prioritizes bundles closest to their Time-To-Live expiration to prevent data loss. |
| **SCHED-05** | `RESOURCE-AWARE` | Energy & Buffer Safe | $\min(\text{Energy}) \text{ s.t. } \text{Occ} \le 85\%$ | Avoids transmitting to saturated buffers; favors high elevation passes with high link margin. |
| **SCHED-06** | `ATLAS-ADAPTIVE` | Multi-Objective Pareto | $\max(U(\text{Urgency}, \text{Rate}, \text{Margin}, \text{Buffer}))$ | Dynamically optimizes throughput, emergency delivery, and buffer stability across changing Martian conditions. |

---

## 3. Disjoint Resilient Multi-Path Routing

For mission-critical command uplinks (Class 2) and life-support telemetry (Class 1), single-path routing exposes the mission to catastrophic single-point-of-failure (SPOF) risks if an orbiter experiences an anomaly.

The Atlas multi-path routing algorithm computes:
1. **Primary Route:** Time-optimal trajectory $P_1 = (N_0, N_1, \dots, N_k, D)$.
2. **Intermediate Node Set:** $\mathcal{I} = \{N_1, \dots, N_k\}$.
3. **Disjoint Secondary Route:** Space-time path $P_2$ constrained to the pruned contact graph:
   $$\mathcal{G}' = \mathcal{G} \setminus \mathcal{I}$$
If $P_2$ exists, critical bundles can be redundantly replicated across both disjoint routes to achieve near-unity delivery probability.
