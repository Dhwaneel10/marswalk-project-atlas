"""
Updates web/index.html for Milestone 13F:
- 7-Step Stepper Navigation
- In-Theater Battery Gauge & Feasibility in #jointMissionStudioPanel
- Step 4: Energy & Resources Subsystems
- Steps 5 (Solve), 6 (Pareto Studio with Dimension Switcher & Scorecard Columns), 7 (Promote)
"""

with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update In-Theater Panel #jointMissionStudioPanel telemetry
old_theater_telemetry = """        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">METABOLIC WORK:</span>
          <span id="jointTheaterEnergy" class="jointstudio-telemetry-val">1,240 kJ (Waligora Model)</span>
        </div>
      </div>"""

new_theater_telemetry = """        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">ENERGY CONSUMED:</span>
          <span id="jointTheaterEnergy" class="jointstudio-telemetry-val text-purple">12.45 MJ (3,458 Wh)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">FEASIBILITY:</span>
          <span id="jointTheaterFeasibilityBadge" class="feasibility-badge feasible">FEASIBLE (OK)</span>
        </div>
      </div>

      <!-- Real-Time Battery SOC Gauge (Milestone 13F) -->
      <div style="margin-top:6px; padding:6px 8px; border-radius:4px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.06);">
        <div style="display:flex; justify-content:space-between; font-size:8px; margin-bottom:2px;">
          <span style="color:#94a3b8; font-weight:600;">BATTERY SOC (REAL-TIME):</span>
          <span id="jointTheaterBatterySocVal" class="font-mono text-cyan" style="font-weight:700;">100.0% (4,800 Wh)</span>
        </div>
        <div class="theater-battery-gauge-track" style="position:relative; width:100%; height:6px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
          <div id="jointTheaterBatteryBar" class="theater-battery-gauge-fill" style="width: 100%; height:100%; background: #10b981; transition:width 0.2s ease, background 0.3s ease;"></div>
          <div class="theater-battery-reserve-marker" style="position:absolute; top:0; bottom:0; left:20%; width:2px; background:#f59e0b;" title="20% Reserve Threshold"></div>
        </div>
      </div>"""

assert old_theater_telemetry in html, "Failed to find old_theater_telemetry"
html = html.replace(old_theater_telemetry, new_theater_telemetry, 1)

# 2. Update 6-step nav to 7-step nav
old_stepper_nav = """          <div class="joint-stepper-nav" id="jointWizardStepper">
            <button class="joint-step-btn active" data-step="1" title="Step 1: Define Mission Requirements &amp; Weights">
              <span class="step-num">1</span><span class="step-name">Mission</span>
            </button>
            <button class="joint-step-btn" data-step="2" title="Step 2: Configure Mobility &amp; Locomotion">
              <span class="step-num">2</span><span class="step-name">Mobility</span>
            </button>
            <button class="joint-step-btn" data-step="3" title="Step 3: Configure Mars RelayNet Comms">
              <span class="step-num">3</span><span class="step-name">Comms</span>
            </button>
            <button class="joint-step-btn" data-step="4" title="Step 4: Autonomous Co-Design Optimization">
              <span class="step-num">4</span><span class="step-name">Solve</span>
            </button>
            <button class="joint-step-btn" data-step="5" title="Step 5: Interactive Pareto Frontier Studio">
              <span class="step-num">5</span><span class="step-name">Pareto</span>
            </button>
            <button class="joint-step-btn" data-step="6" title="Step 6: Plan Selection &amp; Promotion">
              <span class="step-num">6</span><span class="step-name">Promote</span>
            </button>
          </div>"""

new_stepper_nav = """          <div class="joint-stepper-nav" id="jointWizardStepper">
            <button class="joint-step-btn active" data-step="1" title="Step 1: Define Mission Requirements &amp; Weights">
              <span class="step-num">1</span><span class="step-name">Mission</span>
            </button>
            <button class="joint-step-btn" data-step="2" title="Step 2: Configure Mobility Platforms">
              <span class="step-num">2</span><span class="step-name">Mobility</span>
            </button>
            <button class="joint-step-btn" data-step="3" title="Step 3: Mars RelayNet Communications">
              <span class="step-num">3</span><span class="step-name">Comms</span>
            </button>
            <button class="joint-step-btn" data-step="4" title="Step 4: Energy Budgets &amp; Subsystems">
              <span class="step-num">4</span><span class="step-name">Energy</span>
            </button>
            <button class="joint-step-btn" data-step="5" title="Step 5: Autonomous Co-Design Optimization">
              <span class="step-num">5</span><span class="step-name">Solve</span>
            </button>
            <button class="joint-step-btn" data-step="6" title="Step 6: Interactive Pareto Frontier Studio">
              <span class="step-num">6</span><span class="step-name">Pareto</span>
            </button>
            <button class="joint-step-btn" data-step="7" title="Step 7: Plan Selection &amp; Promotion">
              <span class="step-num">7</span><span class="step-name">Promote</span>
            </button>
          </div>"""

assert old_stepper_nav in html, "Failed to find old_stepper_nav"
html = html.replace(old_stepper_nav, new_stepper_nav, 1)

# 3. Update Step 3 button to go to Step 4 (Energy)
old_step3_btn = """            <button class="btn-primary joint-next-step-btn" data-next="4" style="font-size:9.5px; padding:4px 10px;">Proceed to Solve &rarr;</button>"""
new_step3_btn = """            <button class="btn-primary joint-next-step-btn" data-next="4" style="font-size:9.5px; padding:4px 10px;">Proceed to Energy &rarr;</button>"""
assert old_step3_btn in html, "Failed to find old_step3_btn"
html = html.replace(old_step3_btn, new_step3_btn, 1)

# 4. Insert Step 4: Energy Budgets & Power Subsystems and rename Step 4->5, Step 5->6, Step 6->7
step4_html = """
        <!-- STEP 4: Energy Budgets & Power Subsystems (Milestone 13F) -->
        <div id="jointStepPanel4" class="joint-step-content hidden">
          <!-- Preset Selection Card -->
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#9889; STEP 4: ENERGY &amp; RESOURCE CONFIGURATION
            </div>
            <div style="font-size:8px; color:#94a3b8; margin-bottom:8px;">
              Select an operational platform preset or fine-tune battery, terramechanical, and electrical subsystem parameters.
            </div>
            <div class="resource-presets-container" style="display:grid; grid-template-columns:1fr 1fr; gap:4px; margin-bottom:8px;">
              <button class="joint-resource-preset-btn active" data-preset="perseverance_nominal">
                <span class="preset-name">&#128663; Perseverance Nominal</span>
                <span class="preset-spec">4.8 kWh &bull; Crr 0.08 &bull; 110W Base</span>
              </button>
              <button class="joint-resource-preset-btn" data-preset="high_power_drill">
                <span class="preset-name">&#128296; High-Power Drill</span>
                <span class="preset-spec">6.0 kWh &bull; 240W Drill &bull; 30m Dwell</span>
              </button>
              <button class="joint-resource-preset-btn" data-preset="ultralight_scout">
                <span class="preset-name">&#128640; Ultralight Scout</span>
                <span class="preset-spec">1.6 kWh &bull; 200kg &bull; 0.65 m/s</span>
              </button>
              <button class="joint-resource-preset-btn" data-preset="crew_eva_sortie">
                <span class="preset-name">&#129497; Crew EVA Sortie</span>
                <span class="preset-spec">2.5 kWh &bull; Waligora &bull; 1.0 m/s</span>
              </button>
            </div>
          </div>

          <!-- Battery & Margin Configuration Card -->
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9px; font-weight:700; color:var(--telemetry-cyan); margin-bottom:6px;">
              &#128267; BATTERY STORAGE &amp; OPERATIONAL MARGINS
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <div style="display:flex; justify-content:space-between; font-size:8px; margin-bottom:2px;">
                  <span style="color:#94a3b8;">Usable Battery Capacity:</span>
                  <span id="jointBatteryCapVal" class="font-mono text-cyan">4,800 Wh</span>
                </div>
                <input type="range" id="jointBatteryCapacity" min="1000" max="10000" step="200" value="4800" class="hud-slider" style="width:100%;">
              </div>
              <div>
                <div style="display:flex; justify-content:space-between; font-size:8px; margin-bottom:2px;">
                  <span style="color:#94a3b8;">Reserve Margin Threshold:</span>
                  <span id="jointReserveMarginVal" class="font-mono text-amber">20.0%</span>
                </div>
                <input type="range" id="jointReserveMargin" min="5" max="40" step="1" value="20" class="hud-slider" style="width:100%;">
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:6px; margin-top:4px;">
              <input type="checkbox" id="jointAllowRegenBraking">
              <label for="jointAllowRegenBraking" style="font-size:8px; color:#cbd5e1; cursor:pointer;">
                Allow Regenerative Braking on Descents (Disabled by default: strictly conserves descent work)
              </label>
            </div>
          </div>

          <!-- Terramechanics & Locomotion Efficiency Card -->
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9px; font-weight:700; color:var(--telemetry-cyan); margin-bottom:6px;">
              &#9881; TERRAMECHANICS &amp; LOCOMOTION EFFICIENCY
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Rolling Res. (C_rr):</label>
                <input type="number" id="jointRollingCrr" class="hud-select" value="0.08" step="0.01" min="0.03" max="0.20" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Drivetrain Eff. (&eta;):</label>
                <input type="number" id="jointDrivetrainEff" class="hud-select" value="0.72" step="0.02" min="0.50" max="0.90" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Drive Speed (m/s):</label>
                <input type="number" id="jointDriveSpeed" class="hud-select" value="0.38" step="0.02" min="0.10" max="1.50" style="width:100%; font-size:9px;">
              </div>
            </div>
          </div>

          <!-- Electrical Subsystem Loads & Dwell Scheduling Card -->
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9px; font-weight:700; color:var(--telemetry-cyan); margin-bottom:6px;">
              &#9889; ELECTRICAL LOADS &amp; MISSION TIMETABLE
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Avionics Base Load (W):</label>
                <input type="number" id="jointBaseLoadW" class="hud-select" value="110.0" step="5" min="40" max="300" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Instrument Active Load (W):</label>
                <input type="number" id="jointInstActiveW" class="hud-select" value="120.0" step="10" min="20" max="400" style="width:100%; font-size:9px;">
              </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Science Dwell per WP (s):</label>
                <input type="number" id="jointScienceDwellS" class="hud-select" value="900" step="60" min="120" max="3600" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Relay Deploy Time (s):</label>
                <input type="number" id="jointRelayDeployS" class="hud-select" value="1200" step="60" min="300" max="3600" style="width:100%; font-size:9px;">
              </div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="3" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Comms</button>
            <button class="btn-primary joint-next-step-btn" data-next="5" style="font-size:9.5px; padding:4px 10px;">Proceed to Solve &rarr;</button>
          </div>
        </div>
"""

old_step4_solve = """        <!-- STEP 4: Solve & Autonomous Optimization -->
        <div id="jointStepPanel4" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px; text-align:center; padding:12px 10px;">
            <div class="control-label" style="font-size:10px; font-weight:800; color:var(--telemetry-cyan); margin-bottom:6px;">
              &#9889; STEP 4: AUTONOMOUS CO-DESIGN OPTIMIZATION
            </div>
            <div style="font-size:8.5px; color:#94a3b8; line-height:1.4; margin-bottom:12px;">
              Executes multi-objective traverse search, evaluates geometric LOS against USGS CTX 20m DTM, runs submodular greedy relay selection, and computes Pareto non-dominated frontiers.
            </div>
            <button id="btnRunJointOptimization" class="joint-action-button primary" style="width:100%; padding:10px 14px; font-size:11px; margin-bottom:10px;">
              <span class="btn-icon">&#9889;</span> EXECUTE JOINT CO-DESIGN OPTIMIZATION
            </button>
            <div id="jointSolverStatusBox" class="joint-status-box hidden">
              <span id="jointSolverSpinner" class="joint-spinner">&#8635;</span>
              <span id="jointSolverStatusText">Initializing co-design solver...</span>
            </div>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="3" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Comms</button>
            <button class="btn-primary joint-next-step-btn" id="btnGoToPareto" data-next="5" style="font-size:9.5px; padding:4px 10px;">Inspect Pareto Frontier &rarr;</button>
          </div>
        </div>"""

new_step5_solve = step4_html + """
        <!-- STEP 5: Solve & Autonomous Optimization -->
        <div id="jointStepPanel5" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px; text-align:center; padding:12px 10px;">
            <div class="control-label" style="font-size:10px; font-weight:800; color:var(--telemetry-cyan); margin-bottom:6px;">
              &#9889; STEP 5: AUTONOMOUS CO-DESIGN OPTIMIZATION
            </div>
            <div style="font-size:8.5px; color:#94a3b8; line-height:1.4; margin-bottom:12px;">
              Executes multi-objective traverse search, evaluates geometric LOS against USGS CTX 20m DTM, calculates terramechanical work, models relay infrastructure, and computes resource-constrained Pareto frontiers.
            </div>
            <button id="btnRunJointOptimization" class="joint-action-button primary" style="width:100%; padding:10px 14px; font-size:11px; margin-bottom:10px;">
              <span class="btn-icon">&#9889;</span> EXECUTE JOINT CO-DESIGN OPTIMIZATION
            </button>
            <div id="jointSolverStatusBox" class="joint-status-box hidden">
              <span id="jointSolverSpinner" class="joint-spinner">&#8635;</span>
              <span id="jointSolverStatusText">Initializing co-design solver...</span>
            </div>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="4" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Energy</button>
            <button class="btn-primary joint-next-step-btn" id="btnGoToPareto" data-next="6" style="font-size:9.5px; padding:4px 10px;">Inspect Pareto Frontier &rarr;</button>
          </div>
        </div>"""

assert old_step4_solve in html, "Failed to find old_step4_solve"
html = html.replace(old_step4_solve, new_step5_solve, 1)

# 5. Update Step 5 (now Step 6: Pareto Frontier Studio)
old_step5_pareto = """        <!-- STEP 5: Interactive Pareto Frontier Studio -->
        <div id="jointStepPanel5" class="joint-step-content hidden">
          <!-- Pareto Frontier 2D Scatter Canvas -->
          <div class="control-card" style="margin-bottom:8px; padding:8px 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span class="control-label" style="font-size:9.5px; font-weight:700; color:var(--telemetry-cyan);">&#128200; PARETO TRADEOFF FRONTIER</span>
              <div style="display:flex; gap:6px; font-size:8px;">
                <span style="color:#10b981;">&#9679; Non-Dominated (Rank 1)</span>
                <span style="color:#64748b;">&#9679; Dominated</span>
                <span style="color:#00e5ff;">&#9678; Selected</span>
              </div>
            </div>
            <div class="pareto-canvas-container" style="position:relative; width:100%; height:200px; background:rgba(0,0,0,0.5); border-radius:4px; border:1px solid rgba(255,255,255,0.08); overflow:hidden;">
              <canvas id="paretoScatterCanvas" width="560" height="200" style="display:block; width:100%; height:100%; cursor:crosshair;"></canvas>
              <div id="paretoCanvasTooltip" class="pareto-canvas-tooltip hidden"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:8px; color:#64748b; margin-top:4px;">
              <span>&larr; X-Axis: Traverse Distance (m) [Shorter is Better]</span>
              <span>Y-Axis: Comms Gap Duration (s) [Zero is Better] &rarr;</span>
            </div>
          </div>

          <!-- Comparative Scorecard Table -->
          <div class="control-card" style="margin-bottom:8px; padding:8px 10px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128203; CO-DESIGN CANDIDATE COMPARATIVE SCORECARD
            </div>
            <div style="overflow-x:auto;">
              <table class="pareto-scorecard-table" id="paretoScorecardTable">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Strategy</th>
                    <th>Pareto Rank</th>
                    <th>Distance</th>
                    <th>Coverage</th>
                    <th>Relays</th>
                    <th>Gap Time</th>
                    <th>Energy</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="paretoScorecardBody">
                  <tr>
                    <td colspan="9" style="text-align:center; color:#64748b; padding:12px;">Run optimization to populate candidates...</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Dynamic Trade-off Explanation Card -->
          <div id="jointDecisionExplanationCard" class="control-card" style="margin-bottom:8px; padding:8px 10px; background:rgba(15,23,42,0.7); border:1px solid rgba(0,229,255,0.2);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span class="control-label" style="font-size:9px; font-weight:700; color:var(--telemetry-cyan);">&#129504; DECISION RATIONALE &amp; MARGINAL RATE OF SUBSTITUTION</span>
              <span id="jointExplanationBadge" class="wp-badge" style="font-size:7.5px;">RECOMMENDED</span>
            </div>
            <div id="jointExplanationNarrative" style="font-size:8.5px; color:#cbd5e1; line-height:1.4;">
              Select a candidate from the table or Pareto plot to view physical trade-off attribution, marginal rate of substitution (MRS), and terrain occlusion factors.
            </div>
          </div>

          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="4" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Solve</button>
            <button class="btn-primary joint-next-step-btn" data-next="6" style="font-size:9.5px; padding:4px 10px;">Proceed to Promote &rarr;</button>
          </div>
        </div>"""

new_step6_pareto = """        <!-- STEP 6: Interactive Pareto Frontier Studio -->
        <div id="jointStepPanel6" class="joint-step-content hidden">
          <!-- Pareto Frontier 2D Scatter Canvas & Trade-off Selector -->
          <div class="control-card" style="margin-bottom:8px; padding:8px 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span class="control-label" style="font-size:9.5px; font-weight:700; color:var(--telemetry-cyan);">&#128200; PARETO TRADEOFF FRONTIER</span>
              <div style="display:flex; gap:6px; font-size:8px;">
                <span style="color:#10b981;">&#9679; Non-Dominated (Rank 1)</span>
                <span style="color:#64748b;">&#9679; Dominated</span>
                <span style="color:#00e5ff;">&#9678; Selected</span>
              </div>
            </div>

            <!-- Metric Dimension Switcher (Milestone 13F) -->
            <div class="pareto-mode-selector" style="display:flex; gap:4px; margin-bottom:6px;">
              <button class="joint-pareto-mode-btn active" data-mode="energy_vs_distance">&#9889; Energy vs Distance</button>
              <button class="joint-pareto-mode-btn" data-mode="energy_vs_gap">&#128225; Energy vs Comms Gap</button>
              <button class="joint-pareto-mode-btn" data-mode="distance_vs_gap">&#128506; Distance vs Comms Gap</button>
            </div>

            <div class="pareto-canvas-container" style="position:relative; width:100%; height:200px; background:rgba(0,0,0,0.5); border-radius:4px; border:1px solid rgba(255,255,255,0.08); overflow:hidden;">
              <canvas id="paretoScatterCanvas" width="560" height="200" style="display:block; width:100%; height:100%; cursor:crosshair;"></canvas>
              <div id="paretoCanvasTooltip" class="pareto-canvas-tooltip hidden"></div>
            </div>
            <div id="paretoAxisLabels" style="display:flex; justify-content:space-between; font-size:8px; color:#64748b; margin-top:4px;">
              <span id="paretoXAxisLabel">&larr; X-Axis: Traverse Distance (m) [Shorter is Better]</span>
              <span id="paretoYAxisLabel">Y-Axis: Total Energy Consumed (Wh) [Lower is Better] &rarr;</span>
            </div>
          </div>

          <!-- Comparative Scorecard Table with Resource Feasibility -->
          <div class="control-card" style="margin-bottom:8px; padding:8px 10px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128203; CO-DESIGN CANDIDATE COMPARATIVE SCORECARD &amp; RESOURCE FEASIBILITY
            </div>
            <div style="overflow-x:auto;">
              <table class="pareto-scorecard-table" id="paretoScorecardTable">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Strategy</th>
                    <th>Pareto Rank</th>
                    <th>Distance</th>
                    <th>Duration</th>
                    <th>Coverage</th>
                    <th>Relays</th>
                    <th>Energy Consumed</th>
                    <th>Energy Remaining</th>
                    <th>Reserve</th>
                    <th>Feasibility</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="paretoScorecardBody">
                  <tr>
                    <td colspan="12" style="text-align:center; color:#64748b; padding:12px;">Run optimization to populate candidates...</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Dynamic Trade-off Explanation Card -->
          <div id="jointDecisionExplanationCard" class="control-card" style="margin-bottom:8px; padding:8px 10px; background:rgba(15,23,42,0.7); border:1px solid rgba(0,229,255,0.2);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span class="control-label" style="font-size:9px; font-weight:700; color:var(--telemetry-cyan);">&#129504; DECISION RATIONALE &amp; RESOURCE INTELLIGENCE</span>
              <span id="jointExplanationBadge" class="wp-badge" style="font-size:7.5px;">RECOMMENDED</span>
            </div>
            <div id="jointExplanationNarrative" style="font-size:8.5px; color:#cbd5e1; line-height:1.4;">
              Select a candidate from the table or Pareto plot to view physical trade-off attribution, marginal rate of substitution (MRS), and battery feasibility.
            </div>
          </div>

          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="5" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Solve</button>
            <button class="btn-primary joint-next-step-btn" data-next="7" style="font-size:9.5px; padding:4px 10px;">Proceed to Promote &rarr;</button>
          </div>
        </div>"""

assert old_step5_pareto in html, "Failed to find old_step5_pareto"
html = html.replace(old_step5_pareto, new_step6_pareto, 1)

# 6. Update Step 6 (now Step 7: Promotion)
old_step6_promote = """        <!-- STEP 6: Promotion & Artifact Export -->
        <div id="jointStepPanel6" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px; padding:10px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128640; STEP 6: PROMOTE CO-DESIGN TO ACTIVE MISSION PLAN
            </div>"""

new_step7_promote = """        <!-- STEP 7: Promotion & Artifact Export -->
        <div id="jointStepPanel7" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px; padding:10px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128640; STEP 7: PROMOTE CO-DESIGN TO ACTIVE MISSION PLAN
            </div>"""

assert old_step6_promote in html, "Failed to find old_step6_promote"
html = html.replace(old_step6_promote, new_step7_promote, 1)

old_step6_prev_btn = """            <button class="btn-secondary joint-prev-step-btn" data-prev="5" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Pareto Studio</button>"""
new_step7_prev_btn = """            <button class="btn-secondary joint-prev-step-btn" data-prev="6" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Pareto Studio</button>"""
assert old_step6_prev_btn in html, "Failed to find old_step6_prev_btn"
html = html.replace(old_step6_prev_btn, new_step7_prev_btn, 1)

with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("web/index.html updated successfully.")
