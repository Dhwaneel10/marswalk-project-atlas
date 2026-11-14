section_8 = '''

## 8. Atlas Joint Mission Co-Design (Traverse Planning \u00d7 Relay Network Optimization)

Introduced in Milestone 13E, the **Joint Mission Design Studio** unifies surface mobility planning and Mars RelayNet infrastructure planning into a coupled co-design system.

### Launching Joint Mission Co-Design
- **URL Parameter:** `http://127.0.0.1:3000/?mode=demo&jointstudio=1` or `http://127.0.0.1:3000/?jointstudio=1`
- **Cockpit Tab:** Click the **\u2699 Co-Design** tab in `#inspectorTabs`.
- **Theater HUD Control:** Click **\u2699 CO-DESIGN** in the top bar to toggle `#jointMissionStudioPanel`.

### Live Demonstration Workflow
1. **Define Mission & Objectives (Step 1):**
   - Origin: Octavia E. Butler Landing Base `[117, 157]`.
   - Destination: Delta Remnant / Three Forks `[138, 114]`.
   - Select weight preset: `Balanced (0.3/0.35/0.2/0.15)` or `Comms-First`.
2. **Configure Mobility & Comms Platforms (Steps 2 & 3):**
   - Confirm Perseverance platform, slope limits (15\u00b0 / 20\u00b0 / 25\u00b0), Base mast (10m), rover antenna (2.5m), and relay budget ($K_{\\text{max}} = 2$).
3. **Run Autonomous Co-Design Optimization (Step 4):**
   - Click `[\u26a1 EXECUTE JOINT CO-DESIGN OPTIMIZATION]`.
   - Observe solver generating candidate traverses, evaluating 3D geometric line-of-sight against USGS Jezero 20m DTM, and computing Pareto dominance in $< 850\\text{ ms}$.
4. **Explore Pareto Frontier Trade-Offs (Step 5):**
   - Inspect the interactive 2D scatter plot (Traverse Distance vs Blackout Gap Duration vs Relays).
   - Point out green non-dominated frontier candidates versus grey dominated alternatives.
   - Click candidate rows in the comparative scorecard table to switch active preview.
   - Read the dynamic trade-off explanation box with Marginal Rate of Substitution (MRS) and scarp occlusion attribution.
5. **Inspect 3D Mission Theater Multi-Traverse Hierarchy:**
   - Switch to Mission Theater.
   - Observe bold cyan selected candidate ribbon, dashed violet Pareto alternatives, faint grey dominated paths, and pulsating crimson blackout gaps.
   - Notice deployed emerald relay towers on promontories and dynamic carrier beam handovers.
6. **Promote Plan & Export Artifacts (Step 6):**
   - Click `[\U0001f680 PROMOTE CO-DESIGN TO ACTIVE MISSION PLAN]` to deploy candidate to active operations.
   - Click `Export Plan (JSON)` or `Download Dossier (MD)` to inspect Draft 2020-12 valid schema evidence.
'''

with open('docs/conference-demo-guide.md', 'r', encoding='utf-8') as f:
    guide = f.read()

if 'Milestone 13E' not in guide:
    with open('docs/conference-demo-guide.md', 'w', encoding='utf-8') as f:
        f.write(guide + '\n' + section_8)
    print("Updated docs/conference-demo-guide.md")
else:
    print("docs/conference-demo-guide.md already has Milestone 13E")
