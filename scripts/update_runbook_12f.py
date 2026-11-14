"""Patch docs/v2-demonstration-runbook.md with Step 12."""

RUNBOOK_PATH = "docs/v2-demonstration-runbook.md"

with open(RUNBOOK_PATH, "r", encoding="utf-8") as f:
    text = f.read()

target = "## 🛡️ Scientific Integrity & Truth Disclosures"

step_12 = """### Step 12: Autonomous Mission Rehearsal Director (Closed-Loop Simulation, Disruption Response & Replay)

1. **Open the Rehearsal Director:**
   - In the HUD inspector tab bar, click **"🎬 Rehearsal"** (or click **"🎬 REHEARSAL DIRECTOR"** in the top header or Cockpit toolbar).
   - The wide cockpit-mode Rehearsal Director panel opens.
2. **Configure Baseline Campaign & Recovery Policy:**
   - Select an exploration campaign from the **"Baseline Exploration Campaign"** dropdown.
   - Choose an adaptive recovery policy:
     - `Balanced (Detour > Shed)`: Prefers conservative detour; sheds only if necessary to preserve margin.
     - `Safety First (Min 3600s)`: Enforces high safety buffers; sheds peripheral targets aggressively.
     - `Max Science (Keep Targets)`: Prioritizes science yield as long as return margin is non-negative.
   - Set the **Min Margin Threshold** (default: 1800s / 30 min).
3. **Configure Supported Disturbances:**
   - Choose a disturbance type:
     - `Operational Delay (+1800s)`: Models sampling holds, comms dropouts, instrument timeouts.
     - `Corridor Closure (50m)`: Models rockfalls or slope failures blocking planned traverse paths.
     - `Mobility Derating (0.7x)`: Models wheel slippage, loose drift sand, or drive throttling.
     - `Target Invalidation`: Models scientific waypoints becoming unviable or hazardous.
     - `Asset / Unit Dropout`: Models equipment faults with multi-unit cross-asset handoff.
   - Set the simulated trigger time (e.g. `T+3600s`).
4. **Execute Closed-Loop Rehearsal:**
   - Click **"▶ EXECUTE REHEARSAL"**.
   - The Director evaluates the paired tri-track simulation:
     - **Track 1 (Baseline):** Nominal uninterrupted trajectory.
     - **Track 2 (Disturbed Unmitigated):** Consequence if no recovery is attempted (margin depletion, obstacle blocks, aborted sorties).
     - **Track 3 (Recovered Closed-Loop):** Autonomous evaluation of 3 competing recovery candidates and execution of the optimal plan.
5. **Inspect the Tri-Track Trajectory Comparison:**
   - Review the **Outcome Status Badge** (`RECOVERED`, `RECOVERED_WITH_DEGRADATION`, or `NO_FEASIBLE_RECOVERY`).
   - Compare quantitative delta metrics: **Science Preserved %**, **Net Science Delta**, **Recovered Margin**, **Delay Incurred**, and **Recovery Efficacy**.
   - Review comparative trajectory progress bars.
6. **Review Evaluated Recovery Candidates:**
   - Inspect the three competing recovery plans:
     - `Conservative Detour`: Reroutes around obstacle / absorbs delay to keep 100% of feasible science.
     - `Target Shedding`: Drops lowest-priority targets to safeguard return margin.
     - `Priority Rebalance / Cross-Asset Reallocation`: Transfers tasks to surviving units or reorders visits.
   - Check selection badges (`SELECTED`, `REJECTED`, `INFEASIBLE`) and review decision rationales.
7. **Trace the Causal Decision Ledger:**
   - Step through the auditable 7-step causal chain:
     `Initial State -> Disturbance Trigger -> Impact Assessment -> Option Space Evaluation -> Selection Decision -> Revised Execution -> Final Outcome`.
8. **Replay & Export Decision Pack:**
   - Click **"► REPLAY SEQUENCE"** to step through events visually on the timeline.
   - Click **"💾 EXPORT DECISION PACK"** to download the RFC 8259 / Draft 2020-12 validated rehearsal record.

---

"""

if "Step 12: Autonomous Mission Rehearsal Director" not in text:
    assert target in text, "Target not found in runbook"
    text = text.replace(target, step_12 + target, 1)

# Update table
old_table_end = "| **Robustness Lab & Sensitivity** | Deterministic stress testing, finite-difference gradients ($d\\text{Metric}/d\\text{Param}$), elasticity, tested-scenario ratio | Real-world Martian probability, likelihood of success, astronaut safety certification | USGS CTX Jezero DEM & Apollo Lunar EVA Empirical Models |"
new_table_row = "\n| **Mission Rehearsal Director** | Paired deterministic tri-track simulation, 3-way candidate recovery evaluation, auditable causal decision chains | Certified real-world rover autonomous navigation or crew flight envelope | USGS CTX Jezero DTM, Contingency Kinematics & Decision Ledgers |"

if "Mission Rehearsal Director" not in text:
    assert old_table_end in text, "Table end not found in runbook"
    text = text.replace(old_table_end, old_table_end + new_table_row, 1)

with open(RUNBOOK_PATH, "w", encoding="utf-8") as f:
    f.write(text)

print("Runbook updated successfully with Step 12!")
