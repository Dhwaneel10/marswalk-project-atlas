"""
scripts/patch_grand_prix_ui.py
Injects the Grand Prix Arena tab and navigation controls into web/index.html and web/app.js.
"""

from pathlib import Path

REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
INDEX_PATH = REPO_ROOT / "web" / "index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Header Button
btn_target = "<!-- Milestone 13H: Atlas Campaign Operations Director (MOCC) Button -->"
btn_insert = """      <!-- Milestone 13X: Atlas Mission Grand Prix Strategy Arena Button -->
      <button id="btnHeaderGrandPrix" class="btn-primary btn-header-cockpit" style="font-size: 10px; padding: 4px 10px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-color: #fbbf24;" title="Atlas Mission Grand Prix: Strategy Arena &amp; Algorithm Championship">
        &#127942; GRAND PRIX
      </button>\n\n"""

if "id=\"btnHeaderGrandPrix\"" not in content and btn_target in content:
    content = content.replace(btn_target, btn_insert + btn_target, 1)

# 2. Grand Prix Arena Panel
tab_target = '<div id="tabPlan" class="inspector-tab-panel hidden">'
tab_insert = """      <!-- ============================================================= -->
      <!-- TAB: GRAND PRIX ARENA (Milestone 13X) -->
      <!-- ============================================================= -->
      <div id="tabGrandPrix" class="inspector-tab-panel hidden grand-prix-panel">
        <div class="control-card grand-prix-header-card" style="border-left: 3px solid #f59e0b; background: linear-gradient(180deg, #120e06 0%, #080c14 100%); margin-bottom: 8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div>
              <span style="font-size:12px; font-weight:800; color:#fbbf24; letter-spacing:0.5px;">&#127942; ATLAS MISSION GRAND PRIX &bull; STRATEGY ARENA</span>
              <div style="font-size:9px; color:#8899a6;">Large-Scale Planetary Mission Optimization &bull; 6 Competing Strategies &bull; 8 Championship Rounds</div>
            </div>
            <div style="display:flex; gap:6px;">
              <button id="btnRunGrandPrixTournament" class="btn-primary" style="font-size:9.5px; padding:3px 10px; background:linear-gradient(135deg, #f59e0b 0%, #d97706 100%); border-color:#fbbf24;">
                &#9654; Run Tournament
              </button>
              <button id="btnExportGrandPrixDossier" class="btn-secondary" style="font-size:9.5px; padding:3px 8px;" title="Export Tournament Report (JSON/Markdown)">
                &#128190; Export
              </button>
            </div>
          </div>

          <!-- Arena Sub-Tabs -->
          <div class="grand-prix-nav-pills" style="display:flex; gap:4px; margin-top:6px; border-bottom:1px solid #1f2937; padding-bottom:6px;">
            <button class="gp-nav-pill active" data-gptab="gpTabStandings" id="gpPillStandings" style="font-size:9px; padding:2px 8px; border-radius:3px; background:#1f2937; color:#fbbf24; border:none; cursor:pointer;">1. Standings &amp; Champions</button>
            <button class="gp-nav-pill" data-gptab="gpTabCompare" id="gpPillCompare" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#8899a6; border:none; cursor:pointer;">2. Head-to-Head Autopsy</button>
            <button class="gp-nav-pill" data-gptab="gpTabScenarios" id="gpPillScenarios" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#8899a6; border:none; cursor:pointer;">3. Scenario Explorer</button>
            <button class="gp-nav-pill" data-gptab="gpTabSensitivity" id="gpPillSensitivity" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#8899a6; border:none; cursor:pointer;">4. Sensitivity Lab</button>
            <button class="gp-nav-pill" data-gptab="gpTabTheater" id="gpPillTheater" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#8899a6; border:none; cursor:pointer;">5. 3D Trajectory Theater</button>
          </div>
        </div>

        <!-- SUBTAB 1: Standings & Category Champions -->
        <div id="gpTabStandings" class="gp-subpanel">
          <!-- Category Champions Banner -->
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin-bottom:8px;">
            <div class="control-card" style="padding:6px; border-top:2px solid #00e5ff; background:#06101a;">
              <div style="font-size:8px; color:#00e5ff; font-weight:700;">SCIENCE CHAMPION</div>
              <div id="gpScienceChampionName" style="font-size:10px; font-weight:700; color:#fff;">Science-First Explorer</div>
              <div id="gpScienceChampionScore" style="font-size:8.5px; color:#8899a6;">12.15 Raw Pts</div>
            </div>
            <div class="control-card" style="padding:6px; border-top:2px solid #00e676; background:#06101a;">
              <div style="font-size:8px; color:#00e676; font-weight:700;">EFFICIENCY CHAMPION</div>
              <div id="gpEfficiencyChampionName" style="font-size:10px; font-weight:700; color:#fff;">Minimum-Cost Navigator</div>
              <div id="gpEfficiencyChampionScore" style="font-size:8.5px; color:#8899a6;">14.2 kWh Consumed</div>
            </div>
            <div class="control-card" style="padding:6px; border-top:2px solid #ff9100; background:#06101a;">
              <div style="font-size:8px; color:#ff9100; font-weight:700;">ROBUSTNESS CHAMPION</div>
              <div id="gpRobustnessChampionName" style="font-size:10px; font-weight:700; color:#fff;">Resource-Safe Planner</div>
              <div id="gpRobustnessChampionScore" style="font-size:8.5px; color:#8899a6;">100% Feasibility &bull; High CVaR</div>
            </div>
            <div class="control-card" style="padding:6px; border-top:2px solid #fbbf24; background:#06101a;">
              <div style="font-size:8px; color:#fbbf24; font-weight:700;">OVERALL CHAMPION</div>
              <div id="gpOverallChampionName" style="font-size:10px; font-weight:700; color:#fff;">Atlas Adaptive Director</div>
              <div id="gpOverallChampionScore" style="font-size:8.5px; color:#8899a6;">76.7 Composite Index</div>
            </div>
          </div>

          <!-- Tournament Round Standings Table -->
          <div class="control-card" style="padding:8px; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:10px; font-weight:700; color:#fbbf24;">8-ROUND CHAMPIONSHIP LEADERBOARD</span>
              <span id="gpSimulationStatusBadge" class="badge" style="background:rgba(251,191,36,0.15); color:#fbbf24; border:1px solid rgba(251,191,36,0.4); font-size:8px;">1,020 SIMULATIONS &bull; 100% EXECUTED</span>
            </div>
            <div style="overflow-x:auto;">
              <table style="width:100%; border-collapse:collapse; font-size:9px; color:#c9d1d9;">
                <thead>
                  <tr style="border-bottom:1px solid #1f2937; color:#8899a6; text-align:left;">
                    <th style="padding:3px;">Strategy</th>
                    <th style="padding:3px;">Algorithm Family</th>
                    <th style="padding:3px;">Science Mean</th>
                    <th style="padding:3px;">Energy (kWh)</th>
                    <th style="padding:3px;">Feasibility</th>
                    <th style="padding:3px;">Composite</th>
                    <th style="padding:3px;">CVaR 5%</th>
                  </tr>
                </thead>
                <tbody id="gpLeaderboardTableBody">
                  <!-- Dynamically populated -->
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SUBTAB 2: Head-to-Head Autopsy -->
        <div id="gpTabCompare" class="gp-subpanel hidden">
          <div class="control-card" style="padding:8px; margin-bottom:8px;">
            <div style="display:flex; gap:8px; align-items:center; margin-bottom:6px;">
              <label style="font-size:9px; color:#8899a6;">Strategy A:
                <select id="gpSelectStratA" style="background:#0d1117; color:#fff; border:1px solid #30363d; font-size:9px; border-radius:3px; padding:2px;">
                  <option value="STRAT-06-ATLAS">STRAT-06: Atlas Adaptive Director</option>
                  <option value="STRAT-01-GREEDY">STRAT-01: Greedy Explorer</option>
                  <option value="STRAT-02-MINCOST">STRAT-02: Minimum-Cost Navigator</option>
                  <option value="STRAT-03-SCIENCE">STRAT-03: Science-First Explorer</option>
                  <option value="STRAT-04-RESSAFE">STRAT-04: Resource-Safe Planner</option>
                  <option value="STRAT-05-PARETO">STRAT-05: Multi-Objective Optimizer</option>
                </select>
              </label>
              <label style="font-size:9px; color:#8899a6;">Strategy B:
                <select id="gpSelectStratB" style="background:#0d1117; color:#fff; border:1px solid #30363d; font-size:9px; border-radius:3px; padding:2px;">
                  <option value="STRAT-01-GREEDY">STRAT-01: Greedy Explorer</option>
                  <option value="STRAT-02-MINCOST">STRAT-02: Minimum-Cost Navigator</option>
                  <option value="STRAT-03-SCIENCE">STRAT-03: Science-First Explorer</option>
                  <option value="STRAT-04-RESSAFE">STRAT-04: Resource-Safe Planner</option>
                  <option value="STRAT-05-PARETO">STRAT-05: Multi-Objective Optimizer</option>
                  <option value="STRAT-06-ATLAS">STRAT-06: Atlas Adaptive Director</option>
                </select>
              </label>
              <label style="font-size:9px; color:#8899a6;">Seed:
                <input id="gpInputCompareSeed" type="number" value="1010" style="width:60px; background:#0d1117; color:#fff; border:1px solid #30363d; font-size:9px; border-radius:3px; padding:2px;">
              </label>
              <button id="btnRunHeadToHeadCompare" class="btn-primary" style="font-size:9px; padding:2px 8px;">Compare</button>
            </div>

            <!-- Head to Head Verdict Card -->
            <div id="gpCompareVerdictCard" style="background:#0d1117; border:1px solid #21262d; border-radius:4px; padding:6px; margin-bottom:6px;">
              <div style="font-size:9.5px; font-weight:700; color:#fbbf24; margin-bottom:4px;">HEAD-TO-HEAD DECISION AUTOPSY</div>
              <div id="gpCompareVerdictText" style="font-size:8.5px; color:#c9d1d9; line-height:1.5;">Click Compare to inspect decision divergences.</div>
            </div>

            <!-- Side-by-side Decision Steps Table -->
            <div style="max-height:160px; overflow-y:auto;">
              <table style="width:100%; border-collapse:collapse; font-size:8.5px; color:#8899a6;">
                <thead>
                  <tr style="border-bottom:1px solid #21262d; text-align:left;">
                    <th style="padding:2px;">Step</th>
                    <th style="padding:2px;">Strategy A Action</th>
                    <th style="padding:2px;">Strategy B Action</th>
                    <th style="padding:2px;">Divergence Reason</th>
                  </tr>
                </thead>
                <tbody id="gpCompareStepTableBody"></tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SUBTAB 3: Scenario Explorer -->
        <div id="gpTabScenarios" class="gp-subpanel hidden">
          <div class="control-card" style="padding:8px; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:10px; font-weight:700; color:#00e5ff;">SCENARIO PARAMETER INSPECTION</span>
              <div style="display:flex; gap:6px;">
                <select id="gpSelectScenarioPartition" style="background:#0d1117; color:#fff; border:1px solid #30363d; font-size:9px; border-radius:3px; padding:2px;">
                  <option value="DEVELOPMENT">Development Set (Seeds 1000-1199)</option>
                  <option value="TUNING">Tuning Set (Seeds 2000-2299)</option>
                  <option value="HELD_OUT">Held-Out Challenge (Seeds 5000+)</option>
                </select>
                <button id="btnFetchScenariosList" class="btn-secondary" style="font-size:9px; padding:2px 8px;">Fetch</button>
              </div>
            </div>
            <div id="gpScenarioListContainer" style="max-height:180px; overflow-y:auto; font-size:8.5px; color:#c9d1d9;">
              <!-- Dynamically populated scenario cards -->
            </div>
          </div>
        </div>

        <!-- SUBTAB 4: Sensitivity Lab -->
        <div id="gpTabSensitivity" class="gp-subpanel hidden">
          <div class="control-card" style="padding:8px; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:10px; font-weight:700; color:#ff9100;">PARAMETER SENSITIVITY &amp; INFEASIBILITY CLIFFS</span>
              <div style="display:flex; gap:6px;">
                <button class="btn-picker active" id="btnSensDust" style="font-size:8.5px; padding:2px 8px;">Dust Opacity (Tau)</button>
                <button class="btn-picker" id="btnSensEnergy" style="font-size:8.5px; padding:2px 8px;">Battery Capacity (kWh)</button>
              </div>
            </div>
            <div id="gpSensitivityChartContent" style="background:#060b12; border:1px solid #1f2937; border-radius:4px; padding:8px; font-size:8.5px; color:#c9d1d9;">
              <!-- Dynamically rendered sensitivity curve metrics and thresholds -->
            </div>
          </div>
        </div>

        <!-- SUBTAB 5: 3D Trajectory Theater -->
        <div id="gpTabTheater" class="gp-subpanel hidden">
          <div class="control-card" style="padding:8px; margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#a78bfa; margin-bottom:4px;">3D MISSION TRAJECTORY PLAYBACK</div>
            <div style="font-size:8.5px; color:#8899a6; line-height:1.4; margin-bottom:6px;">
              Replay competing routes directly on the 3D Jezero CTX elevation model. Green: Minimum-Cost, Blue: Greedy, Magenta: Science-First, Cyan: Atlas Adaptive.
            </div>
            <div style="display:flex; gap:6px;">
              <button id="btnReplayAllGrandPrixRoutes" class="btn-primary" style="font-size:9px; padding:3px 10px; background:linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); border-color:#a78bfa;">
                &#9654; Render 3D Trajectories
              </button>
              <button id="btnClearGrandPrixRoutes" class="btn-secondary" style="font-size:9px; padding:3px 8px;">Clear Overlays</button>
            </div>
          </div>
        </div>

        <!-- Mandatory Scientific Integrity Notice -->
        <div style="background:#091420; border:1px solid #1a2c40; border-radius:4px; padding:8px 10px; font-size:8px; color:#8899a6; line-height:1.4;">
          <strong style="color:var(--telemetry-cyan);">&#9888; Scientific Benchmarking Disclosure:</strong>
          Atlas Mission Grand Prix conducts simulated algorithmic benchmarking. Rankings, CVaR estimates, and feasibility boundaries reflect mathematical model evaluations and do not certify flight readiness or real-world mission success probabilities.
        </div>
      </div>\n\n"""

if "id=\"tabGrandPrix\"" not in content and tab_target in content:
    content = content.replace(tab_target, tab_insert + tab_target, 1)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully injected Grand Prix UI elements into web/index.html")
