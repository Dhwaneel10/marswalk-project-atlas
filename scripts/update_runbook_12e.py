"""Update docs/v2-demonstration-runbook.md with Milestone 12E walkthrough."""

with open("docs/v2-demonstration-runbook.md", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update flowchart
target_flow = """```mermaid
flowchart LR
    A["1. Planetary Baseline<br/>(Jezero 20m DTM)"] --> B["2. Environmental Audit<br/>(PDS4 MEDA / REMS)"]
    B --> C["3. Campaign Planning<br/>(Multi-Sol Targets)"]
    C --> D["4. Design Space Explorer<br/>(Pareto Optimization)"]
    D --> E["5. Candidate Promotion<br/>(Baseline Immutability)"]
    E --> F["6. Fleet Coordination<br/>(Robotic & Crew)"]
    F --> G["7. Digital Twin Sim<br/>(Temporal Execution)"]
    G --> H["8. Performance Analytics<br/>(Causal Attribution)"]
```"""

replacement_flow = """```mermaid
flowchart LR
    A["1. Planetary Baseline<br/>(Jezero 20m DTM)"] --> B["2. Environmental Audit<br/>(PDS4 MEDA / REMS)"]
    B --> C["3. Campaign Planning<br/>(Multi-Sol Targets)"]
    C --> D["4. Design Space Explorer<br/>(Pareto Optimization)"]
    D --> E["5. Mission Control Cockpit<br/>(Rehearsal & Profile)"]
    E --> F["6. Robustness Lab<br/>(Stress & Sensitivity)"]
    F --> G["7. Resilient Plan Adoption<br/>(Lineage & Proof)"]
```"""

if "6. Robustness Lab" not in text:
    if target_flow in text:
        text = text.replace(target_flow, replacement_flow, 1)

# 2. Add Step 11 before Truth Disclosures
target_truth = "## 🛡️ Scientific Integrity & Truth Disclosures"

step_11 = """### Step 11: Atlas Mission Robustness Lab — Deterministic Stress Testing, Sensitivity Analysis & Resilient Plan Adoption (Milestone 12E)

1. **Access the Mission Robustness Lab:**
   - In the HUD inspector tab bar, click **"🛡 Robustness"** (or click **"🛡 Robustness Lab"** from the Mission Control operational commands toolbar).
   - The panel opens in wide cockpit-mode view.
2. **Select Stress Suite:**
   - From the **"Stress Suite Type"** dropdown, select:
     - `★ Full Battery (10 Curated Stress Cases)` (recommended)
     - `Duration Contraction (-15%, -30%, -45%)`
     - `Mobility Derating (0.85x, 0.70x, Slope 12°)`
     - `Operational Holds (+15m, +30m, +60m)`
     - `Corridor Chokepoints (30m, 60m, 100m)`
     - `Compound Operational Gauntlet`
3. **Execute the Deterministic Stress Battery:**
   - Click **"▶ EXECUTE DETERMINISTIC STRESS BATTERY"**.
   - In ~150ms, MarsWalk evaluates all bounded scenarios against the baseline campaign without mutating the original plan.
4. **Inspect the Feasibility Envelope & Bottlenecks:**
   - The Feasibility Envelope Gauge indicates the tested feasibility ratio (e.g. `10 / 10 cases (100%)`).
   - The progress bar visualizes margin stability.
   - Identified physical bottlenecks pinpoint critical constraints (e.g. sortie duration ceilings, traction loss on steep crater walls).
5. **Inspect Parameter Sensitivity Gradients & Elasticities:**
   - The ranked sensitivity list reveals which operational assumptions exert the greatest influence on mission duration and science return.
   - For example, `#1 max_slope_deg` (elasticity $\\epsilon = 0.88$, gradient $-261.6\\text{ s/unit}$) followed by `#2 speed_factor` (elasticity $\\epsilon = 0.38$).
6. **Review Objective & Unit Vulnerabilities:**
   - The Vulnerability Matrix shows which candidate science targets drop first when margins contract (e.g., peripheral waypoints like Skinner Ridge or Enchanted Lake).
7. **Read the Grounded Answers to the 7 Core Engineering Questions:**
   - Read unambiguous, evidence-backed answers to:
     1. *Which assumptions most affect the plan?*
     2. *Under what conditions does it become infeasible?*
     3. *Which objectives and units are most vulnerable?*
     4. *How much does performance change across scenarios?*
     5. *Which plans retain maximum margin?*
     6. *What evidence supports conclusions?*
     7. *What cannot be established?* (Contains mandatory non-probabilistic truth disclosure).
8. **Compare Resilient Strategies & Adopt Selected Plan:**
   - The Strategy Comparison section contrasts:
     - `Baseline Plan (Nominal Profile)`: Maximum nominal science yield under standard conditions.
     - `Conservative High-Margin Strategy`: Builds in larger temporal buffers and slope safety margins; retains superior margin under traction derating.
     - `Agile High-Yield Strategy`: Fast profile maximizing throughput.
   - Click on any candidate strategy card to select it.
   - Click **"⬆ ADOPT RESILIENT STRATEGY"** to promote it into an official new campaign revision (v2), preserving parent lineage and revision metadata.

---

"""

if "Step 11: Atlas Mission Robustness Lab" not in text:
    assert target_truth in text, "target_truth not found"
    text = text.replace(target_truth, step_11 + target_truth, 1)

# 3. Add row to Truth Disclosures table
table_target = "| **Analytics** | Evidence-corroborated causal attribution | Certified fault tree diagnosis | Simulation Event Ledger & Delta Decomposition |"
table_row = "\n| **Robustness Lab & Sensitivity** | Deterministic stress testing, finite-difference gradients ($d\\text{Metric}/d\\text{Param}$), elasticity, tested-scenario ratio | Real-world Martian probability, likelihood of success, astronaut safety certification | USGS CTX Jezero DEM & Apollo Lunar EVA Empirical Models |"

if "Robustness Lab & Sensitivity" not in text:
    assert table_target in text, "table_target not found"
    text = text.replace(table_target, table_target + table_row, 1)

with open("docs/v2-demonstration-runbook.md", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated docs/v2-demonstration-runbook.md successfully!")
