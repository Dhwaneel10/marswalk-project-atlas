# Atlas Mars RelayNet: Mathematical Foundations & Algorithmic Methods

## 1. Geometric Line-of-Sight (LOS) Formulations

### 1.1 Parametric 3D Ray Definition
Given a transmission source $P_0 = (x_0, y_0, z_0)$ and a receiver target $P_1 = (x_1, y_1, z_1)$ in local Cartesian space, the geometric line-of-sight ray is parameterized by continuous variable $t \in [0, 1]$:

$$P(t) = P_0 + t (P_1 - P_0) = \begin{pmatrix} x_0 + t(x_1 - x_0) \\ y_0 + t(y_1 - y_0) \\ z_0 + t(z_1 - z_0) \end{pmatrix}$$

Where:
- $z_0 = z_{\text{DTM}}(x_0, y_0) + h_{\text{antenna}, 0}$ represents the effective elevation of the transmitter phase center.
- $z_1 = z_{\text{DTM}}(x_1, y_1) + h_{\text{antenna}, 1}$ represents the effective elevation of the receiver phase center.
- $h_{\text{LOS}}(t) = z_0 + t(z_1 - z_0)$ is the unoccluded line-of-sight elevation at normalized parameter $t$.

### 1.2 Mars Planetary Curvature Correction
On the spherical Martian datum with mean radius $R_{\text{Mars}} = 3,396,190\text{ m}$ (IAU 2000), surface curvature induces a vertical elevation drop over horizontal Euclidean distance $d(t) = t \cdot \|(x_1 - x_0, y_1 - y_0)\|_2$:

$$\Delta h_{\text{curv}}(t) = \frac{d(t)^2}{2 R_{\text{Mars}}}$$

For local surface traverses within Jezero Crater ($d \le 5000\text{ m}$):

$$\Delta h_{\text{curv}}(5000\text{ m}) = \frac{25 \times 10^6\text{ m}^2}{2 \times 3,396,190\text{ m}} \approx 3.68\text{ mm}$$

While negligible over 2-5 km tactical traverses relative to 20-meter DTM vertical accuracy ($\approx 1\text{ m}$), the term is explicitly incorporated to ensure rigorous planetary geodesy.

### 1.3 Continuous Bilinear DTM Surface Sampling
Let $(r, c)$ denote continuous float coordinates on the DTM raster grid. For integer grid indices $r_0 = \lfloor r \rfloor$, $c_0 = \lfloor c \rfloor$, $r_1 = r_0 + 1$, and $c_1 = c_0 + 1$, the normalized fractional offsets are:

$$\Delta r = r - r_0, \quad \Delta c = c - c_0$$

The continuous interpolated terrain elevation $z(r, c)$ is computed via bilinear filtering:

$$z(r, c) = (1 - \Delta r)(1 - \Delta c) Z_{r_0, c_0} + (1 - \Delta r)\Delta c Z_{r_0, c_1} + \Delta r (1 - \Delta c) Z_{r_1, c_0} + \Delta r \Delta c Z_{r_1, c_1}$$

**NoData Sentinel Guard:** If any of the four adjacent corner posts contains a NoData sentinel ($Z \le -9000.0\text{ m}$), bilinear evaluation aborts and returns status `UNKNOWN_TERRAIN`, preventing interpolation across missing data boundaries.

### 1.4 Nyquist Spatial Sampling Criterion
To prevent aliasing and missed narrow terrain ridges, the spatial step size $\Delta s$ along the ray must satisfy the spatial Nyquist theorem relative to grid resolution $(dx, dy)$:

$$\Delta s \le \frac{1}{2} \min(dx, dy)$$

For the authentic USGS CTX 20m Jezero DTM ($dx = 18.973\text{ m}$, $dy = 20.000\text{ m}$):

$$\Delta s \le \frac{18.973}{2} \approx 9.486\text{ m}$$

The number of discrete evaluation steps $N_{\text{steps}}$ along a baseline of distance $D = \|P_1 - P_0\|_2$ is:

$$N_{\text{steps}} = \max\left(4, \left\lceil \frac{D}{\Delta s} \right\rceil\right)$$

### 1.5 Terrain Clearance & Occlusion Detection
At each sample point $k \in \{0, 1, \dots, N_{\text{steps}}\}$ with parameter $t_k = \frac{k}{N_{\text{steps}}}$, the terrain clearance $c(t_k)$ is:

$$c(t_k) = h_{\text{LOS}}(t_k) - z(P(t_k))$$

The global geometric visibility condition is:

$$\text{Visibility}(P_0, P_1) = \begin{cases} \text{BLOCKED}, & \text{if } \exists k \text{ such that } c(t_k) \le 0 \\ \text{VISIBLE}, & \text{if } \forall k, c(t_k) > 0 \end{cases}$$

When obstructed, the primary collision point is identified by the minimum clearance value:

$$k^* = \arg\min_k c(t_k), \quad c_{\min} = c(t_{k^*}) \le 0$$

---

## 2. Network Graph Algorithms

Let $G = (V, E)$ represent the communications network, where:
- $V = V_{\text{base}} \cup V_{\text{relays}} \cup V_{\text{units}}$ is the set of transceivers.
- $E = \{(u, v) \in V \times V \mid \text{Visibility}(u, v) = \text{VISIBLE} \land \text{dist}(u, v) \le R_{\max}\}$ is the set of viable line-of-sight edges.

### 2.1 Breadth-First Shortest Hop Routing
Starting from root node $s \in V_{\text{base}}$, BFS traversal determines:
1. Reachability indicator: $R(u) \in \{0, 1\}$ for each exploration unit $u \in V_{\text{units}}$.
2. Minimum hop count: $h(u) = \text{dist}_G(s, u)$.
3. Shortest path predecessor tree: $\pi(u)$.

### 2.2 Tarjan Single-Point-of-Failure Bridge Detection
To identify critical relay nodes whose failure would partition the communications network and disconnect surface assets, RelayNet implements Tarjan's bridge and articulation point algorithm in $O(|V| + |E|)$ time:

1. Perform Depth-First Search (DFS) starting from root $s$, maintaining discovery time $d[u]$ and low-link value $\text{low}[u]$:
   $$\text{low}[u] = \min \begin{cases} d[u] \\ d[v], & \forall (u, v) \in E_{\text{back}} \\ \text{low}[w], & \forall (u, w) \in E_{\text{tree}} \end{cases}$$
2. An edge $(u, v) \in E_{\text{tree}}$ is a **Bridge** if and only if:
   $$\text{low}[v] > d[u]$$
3. A non-root node $u$ is a **Cut-Vertex** (articulation point) if and only if there exists a tree child $v$ such that:
   $$\text{low}[v] \ge d[u]$$

### 2.3 Algebraic Connectivity (Fiedler Eigenvalue)
The unweighted graph Laplacian matrix $L \in \mathbb{R}^{|V| \times |V|}$ is defined as:

$$L = D - A$$

Where $D$ is the diagonal degree matrix ($D_{ii} = \deg(v_i)$) and $A$ is the symmetric adjacency matrix. Let the eigenvalues of $L$ be ordered:

$$0 = \lambda_1 \le \lambda_2 \le \lambda_3 \le \dots \le \lambda_{|V|}$$

The second smallest eigenvalue $\lambda_2(L)$ is the **algebraic connectivity** (Fiedler value):
- $\lambda_2(L) = 0 \iff$ The network graph is disconnected.
- $\lambda_2(L) > 0 \iff$ The network graph is connected.
- A larger $\lambda_2(L)$ indicates greater synchronization robustness and structural path redundancy.

---

## 3. Promontory Screening & Submodular Greedy Optimization

### 3.1 Candidate Promontory Extraction
Candidate relay sites $C \subset \text{DTM}$ are extracted by screening topographical features across Jezero Crater:
1. **Slope Feasibility:** Horn's $3 \times 3$ finite-difference slope must satisfy $\theta \le 12^\circ$ (safe for robotic lander/rover deployment).
2. **Elevation Constraint:** Mean elevation $Z > -2500\text{ m}$ (above deep crater floor depressions).
3. **Topographic Prominence:**
   $$\text{Prominence}(r, c) = Z(r, c) - \frac{1}{W^2} \sum_{i=-k}^k \sum_{j=-k}^k Z(r+i, c+j) > 25\text{ m}$$
   (where window size $W = 2k + 1 = 15$ cells $\approx 300\text{ m}$).
4. **Non-Maximum Suppression (NMS):** Candidates are sorted by prominence. A candidate site $p$ is accepted if and only if its Euclidean distance to all previously accepted sites satisfies:
   $$\|p - q\|_2 \ge d_{\text{sep}} = 450\text{ m}$$

### 3.2 Submodular Greedy Relay Selection
Let $U = \{u_1, u_2, \dots, u_m\}$ be the set of exploration units requiring communications coverage to base station $s$. The objective function $f(S)$ evaluates the number of units with a valid multi-hop path to $s$ when relay set $S \subseteq C$ is deployed:

$$f(S) = \sum_{u \in U} \mathbf{1}\left(u \text{ is reachable from } s \text{ in } G(V \cup S, E)\right)$$

**Theorem (Nemhauser, Wolsey, Fisher 1978):**
The set function $f(S)$ is monotone and submodular:
1. Monotonicity: $S \subseteq T \implies f(S) \le f(T)$.
2. Submodularity: For all $S \subseteq T$ and $x \notin T$:
   $$f(S \cup \{x\}) - f(S) \ge f(T \cup \{x\}) - f(T)$$

Given a relay placement budget $k$, the greedy algorithm constructs solution $S_k$ iteratively:

$$s_{i}^* = \arg\max_{c \in C \setminus S_{i-1}} \Delta f(c \mid S_{i-1}) = \arg\max_{c \in C \setminus S_{i-1}} [f(S_{i-1} \cup \{c\}) - f(S_{i-1})]$$

The greedy algorithm guarantees a constant-factor approximation ratio:

$$f(S_k) \ge \left(1 - \frac{1}{e}\right) f(S^*) \approx 0.632 \cdot f(S^*)$$

Where $S^*$ is the optimal NP-hard placement.

### 3.3 Four-Tier Deterministic Tie-Breaking
When multiple candidate sites yield identical marginal coverage gains $\Delta f(c)$, ties are broken deterministically:
1. **Tier 1 (Marginal Coverage):** Maximize additional reachable units $\Delta f(c)$.
2. **Tier 2 (Average Clearance):** Maximize mean LOS clearance $\bar{c}$ across all incident edges.
3. **Tier 3 (Topographic Prominence):** Maximize local elevation prominence above crater floor.
4. **Tier 4 (Lexicographical ID):** String sorting on candidate identifier (e.g., `MRN_CAND_03` < `MRN_CAND_07`).

---

## 4. Dynamic Timeline Kinematics & Blackout Coalescing

### 4.1 Kinematic State Interpolation
Along any planned traverse polyline $W = (w_0, w_1, \dots, w_n)$, mission time $t$ corresponds to cumulative traversed distance $d(t) = v \cdot t$ (accounting for stationary dwells and delays). Kinematic position $P(t) = (r(t), c(t), z(t))$ is sampled at uniform temporal intervals $\Delta t = 10\text{ seconds}$.

### 4.2 State Classification
At each discrete checkpoint $k$:
- If $\text{Visibility}(P(t_k), \text{Base}) = \text{VISIBLE} \land \text{dist}(P(t_k), \text{Base}) \le R_{\text{direct}}$:
  $$\text{State}(t_k) = \text{CONNECTED\_DIRECT}$$
- Else if $\exists \text{ path } P(t_k) \rightsquigarrow \text{Base}$ via deployed relay mesh:
  $$\text{State}(t_k) = \text{CONNECTED\_RELAYED}$$
- Else:
  $$\text{State}(t_k) = \text{SIMULATED\_GEOMETRIC\_CONNECTIVITY\_GAP}$$

### 4.3 Blackout Gap Coalescing Algorithm
Contiguous sequences of gap checkpoints are coalesced into formal mission blackout intervals:

$$I_j = [t_{\text{start}}, t_{\text{end}}], \quad \Delta t_{\text{gap}} = t_{\text{end}} - t_{\text{start}}, \quad \Delta d_{\text{gap}} = d(t_{\text{end}}) - d(t_{\text{start}})$$

Each interval records the maximum collision ridge coordinates $(r^*, c^*)$, occluding elevation $Z^*$, and minimum clearance $c_{\min} \le 0$, providing direct causal explanations for mission replay and debriefing.
