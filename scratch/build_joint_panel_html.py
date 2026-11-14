# Build tabJointMissionStudio panel HTML

def get_tab_panel_html():
    return '''      <!-- TAB JOINT MISSION STUDIO (Milestone 13E: Joint Mission Co-Design) -->
      <div id="tabJointMissionStudio" class="inspector-tab-panel hidden">
        <!-- Header & Scientific Provenance Disclosure -->
        <div class="control-card" style="margin-bottom:8px; padding:8px 10px; border-left:3px solid var(--telemetry-cyan); background:linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.95) 100%);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="control-label" style="font-size:10px; font-weight:800; color:var(--telemetry-cyan); letter-spacing:0.8px;">&#9881; JOINT MISSION DESIGN STUDIO</span>
            <span class="wp-badge" style="background:rgba(0,229,255,0.15); color:var(--telemetry-cyan); border-color:rgba(0,229,255,0.3); font-size:8px;">CO-DESIGN v2</span>
          </div>
          <div style="font-size:8.5px; color:#94a3b8; line-height:1.35;">
            Coupled optimization of surface traverse kinematics and Mars RelayNet line-of-sight visibility across authentic USGS Jezero Crater topography.
          </div>
          <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:6px;">
            <span class="wp-badge" style="font-size:7.5px;">USGS CTX 20m DTM (DOI: 10.5066/P906QQT8)</span>
            <span class="wp-badge" style="font-size:7.5px;">IAU 2000 Mars Spheroid (R=3,396,190m)</span>
            <span class="wp-badge" style="font-size:7.5px; background:rgba(16,185,129,0.12); color:#10b981;">Submodular Greedy + Pareto</span>
          </div>
        </div>

        <!-- 6-Step Guided Wizard Stepper -->
        <div class="joint-stepper-container" style="margin-bottom:10px;">
          <div class="joint-stepper-nav" id="jointWizardStepper">
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
          </div>
        </div>

        <!-- STEP 1: Mission Requirements & Objective Weights -->
        <div id="jointStepPanel1" class="joint-step-content active">
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128506; STEP 1: MISSION ENDPOINTS &amp; SCIENCE TARGETS
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Origin / Base:</label>
                <input type="text" id="jointInputStart" class="hud-select" value="[117, 157] Octavia Butler Base" style="width:100%; font-size:9px;" readonly>
              </div>
              <div>
                <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Target Destination:</label>
                <select id="jointSelectGoal" class="hud-select" style="width:100%; font-size:9px;">
                  <option value="138,114" selected>Delta Remnant / Three Forks [138, 114]</option>
                  <option value="175,122">Kodiak Butte Promontory [175, 122]</option>
                  <option value="150,140">Séítah Carbonates Region [150, 140]</option>
                  <option value="95,185">Belva Crater Rim Lookout [95, 185]</option>
                </select>
              </div>
            </div>
            <div style="margin-bottom:6px;">
              <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Planning Horizon / Time Budget:</label>
              <select id="jointSelectBudget" class="hud-select" style="width:100%; font-size:9px;">
                <option value="88775" selected>1 Sol Exploration Window (24.6h / 88,775s)</option>
                <option value="14400">Sortie EVA Window (4.0 hours / 14,400s)</option>
                <option value="28800">Extended Sortie (8.0 hours / 28,800s)</option>
              </select>
            </div>
          </div>

          <!-- Multi-Objective Optimization Weights -->
          <div class="control-card" style="margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1;">&#9878; OBJECTIVE TRADE-OFF WEIGHTS</span>
              <button id="btnJointNormalizeWeights" class="btn-secondary" style="font-size:8px; padding:1px 5px;" title="Normalize weights to sum to 1.0">&Sigma; = 1.0</button>
            </div>

            <!-- Weight Presets -->
            <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
              <button class="joint-preset-pill active" data-preset="balanced">Balanced (0.3/0.35/0.2/0.15)</button>
              <button class="joint-preset-pill" data-preset="mobility_first">Mobility-First</button>
              <button class="joint-preset-pill" data-preset="connectivity_first">Comms-First</button>
              <button class="joint-preset-pill" data-preset="infrastructure_first">Min-Relays</button>
            </div>

            <!-- Weight Sliders -->
            <div style="display:flex; flex-direction:column; gap:6px;">
              <div>
                <div style="display:flex; justify-content:space-between; font-size:8.5px; margin-bottom:1px;">
                  <span style="color:#94a3b8;">Traverse Distance Weight (w_dist):</span>
                  <span id="jointWeightDistVal" class="text-cyan font-mono">0.30</span>
                </div>
                <input type="range" id="jointWeightDist" min="0" max="1" step="0.05" value="0.30" class="hud-slider" style="width:100%;">
              </div>
              <div>
                <div style="display:flex; justify-content:space-between; font-size:8.5px; margin-bottom:1px;">
                  <span style="color:#94a3b8;">Comms Gap Penalty Weight (w_gap):</span>
                  <span id="jointWeightGapVal" class="text-emerald font-mono">0.35</span>
                </div>
                <input type="range" id="jointWeightGap" min="0" max="1" step="0.05" value="0.35" class="hud-slider" style="width:100%;">
              </div>
              <div>
                <div style="display:flex; justify-content:space-between; font-size:8.5px; margin-bottom:1px;">
                  <span style="color:#94a3b8;">Relay Deploy Footprint Weight (w_relays):</span>
                  <span id="jointWeightRelaysVal" class="text-amber font-mono">0.20</span>
                </div>
                <input type="range" id="jointWeightRelays" min="0" max="1" step="0.05" value="0.20" class="hud-slider" style="width:100%;">
              </div>
              <div>
                <div style="display:flex; justify-content:space-between; font-size:8.5px; margin-bottom:1px;">
                  <span style="color:#94a3b8;">Apollo Waligora Energy Weight (w_energy):</span>
                  <span id="jointWeightEnergyVal" class="text-purple font-mono">0.15</span>
                </div>
                <input type="range" id="jointWeightEnergy" min="0" max="1" step="0.05" value="0.15" class="hud-slider" style="width:100%;">
              </div>
            </div>
          </div>
          <div style="display:flex; justify-content:flex-end;">
            <button class="btn-primary joint-next-step-btn" data-next="2" style="font-size:9.5px; padding:4px 10px;">Proceed to Mobility &rarr;</button>
          </div>
        </div>

        <!-- STEP 2: Mobility Configuration -->
        <div id="jointStepPanel2" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128663; STEP 2: MOBILITY &amp; LOCOMOTION PLATFORM
            </div>
            <div style="margin-bottom:6px;">
              <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Exploration Platform:</label>
              <select id="jointPlatformSelect" class="hud-select" style="width:100%; font-size:9px;">
                <option value="perseverance_rover" selected>Perseverance Rover Class (1025 kg, 0.55 m/s, Mechanical Drive)</option>
                <option value="crew_eva">Crew EVA Astronaut Suit (140 kg, 1.0 m/s, Apollo Waligora Metabolic Model)</option>
              </select>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Nominal Slope:</label>
                <input type="number" id="jointSlopeNominal" class="hud-select" value="15.0" step="1.0" min="5" max="20" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Caution Slope:</label>
                <input type="number" id="jointSlopeCaution" class="hud-select" value="20.0" step="1.0" min="10" max="24" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8px; color:#94a3b8; display:block;">Critical Limit:</label>
                <input type="number" id="jointSlopeCritical" class="hud-select" value="25.0" step="1.0" min="15" max="35" style="width:100%; font-size:9px;">
              </div>
            </div>
            <div style="padding:6px 8px; border-radius:4px; font-size:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.06); color:#94a3b8;">
              <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                <span>Apollo Waligora Metabolic Power Limit:</span>
                <span class="text-cyan font-mono">320.0 W</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span>Maximum Mission Energy Budget:</span>
                <span class="text-cyan font-mono">18.5 MJ (5,140 Wh)</span>
              </div>
            </div>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="1" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Mission</button>
            <button class="btn-primary joint-next-step-btn" data-next="3" style="font-size:9.5px; padding:4px 10px;">Proceed to Comms &rarr;</button>
          </div>
        </div>

        <!-- STEP 3: Mars RelayNet Configuration -->
        <div id="jointStepPanel3" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128225; STEP 3: MARS RELAYNET COMMUNICATIONS
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Base Mast Height:</label>
                <input type="number" id="jointBaseMast" class="hud-select" value="10.0" step="1.0" min="5" max="30" style="width:100%; font-size:9px;">
              </div>
              <div>
                <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Mobile Antenna Mast:</label>
                <input type="number" id="jointRoverMast" class="hud-select" value="2.5" step="0.5" min="1" max="5" style="width:100%; font-size:9px;">
              </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:6px;">
              <div>
                <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Relay Budget (K_max):</label>
                <select id="jointRelayBudget" class="hud-select" style="width:100%; font-size:9px;">
                  <option value="0">0 Relays (Direct Base Only)</option>
                  <option value="1">1 Deployable Relay Tower</option>
                  <option value="2" selected>2 Deployable Relay Towers</option>
                  <option value="3">3 Deployable Relay Towers</option>
                  <option value="4">4 Deployable Relay Towers</option>
                </select>
              </div>
              <div>
                <label style="font-size:8.5px; color:#94a3b8; display:block; margin-bottom:2px;">Field Tower Height:</label>
                <input type="number" id="jointFieldMast" class="hud-select" value="8.0" step="1.0" min="3" max="15" style="width:100%; font-size:9px;">
              </div>
            </div>
            <div style="padding:6px 8px; border-radius:4px; font-size:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.06); color:#94a3b8;">
              <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
                <span>Screened Candidate Promontories:</span>
                <span class="text-emerald font-mono">12 Sites (Jezero Crater Ridges)</span>
              </div>
              <div style="display:flex; justify-content:space-between;">
                <span>Maximum Blackout Tolerance:</span>
                <span class="text-cyan font-mono">&le; 400 m / &le; 900 s (15 min)</span>
              </div>
            </div>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="2" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Mobility</button>
            <button class="btn-primary joint-next-step-btn" data-next="4" style="font-size:9.5px; padding:4px 10px;">Proceed to Solve &rarr;</button>
          </div>
        </div>

        <!-- STEP 4: Solve & Autonomous Optimization -->
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
        </div>

        <!-- STEP 5: Interactive Pareto Frontier Studio -->
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
        </div>

        <!-- STEP 6: Promotion & Artifact Export -->
        <div id="jointStepPanel6" class="joint-step-content hidden">
          <div class="control-card" style="margin-bottom:8px; padding:10px;">
            <div class="control-label" style="font-size:9.5px; font-weight:700; color:#cbd5e1; margin-bottom:6px;">
              &#128640; STEP 6: PROMOTE CO-DESIGN TO ACTIVE MISSION PLAN
            </div>
            <div id="jointSelectedSummaryCard" style="padding:8px; border-radius:4px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.08); margin-bottom:10px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span id="jointSelectedName" style="font-weight:700; color:var(--telemetry-cyan); font-size:10px;">JMC-01: Scarp Crest Highway</span>
                <span id="jointSelectedRank" class="wp-badge" style="background:rgba(16,185,129,0.15); color:#10b981;">Pareto Rank 1</span>
              </div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:8.5px; color:#cbd5e1;">
                <div>Distance: <span id="jointSummaryDist" class="font-mono text-cyan">3,412 m</span></div>
                <div>Coverage: <span id="jointSummaryCoverage" class="font-mono text-emerald">100.0%</span></div>
                <div>Relays: <span id="jointSummaryRelays" class="font-mono text-amber">1 (MRN-01)</span></div>
                <div>Energy: <span id="jointSummaryEnergy" class="font-mono text-purple">1,240 kJ</span></div>
              </div>
            </div>
            <button id="btnPromoteJointPlan" class="joint-action-button primary" style="width:100%; padding:10px 14px; font-size:11px; margin-bottom:8px;">
              <span class="btn-icon">&#128640;</span> PROMOTE TO ACTIVE CAMPAIGN PLAN
            </button>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
              <button id="btnExportJointJson" class="btn-secondary" style="font-size:9px; padding:6px 8px;">
                &#128230; Export Plan (JSON)
              </button>
              <button id="btnExportJointMd" class="btn-secondary" style="font-size:9px; padding:6px 8px;">
                &#128196; Download Dossier (MD)
              </button>
            </div>
          </div>

          <!-- Scientific Disclosure -->
          <div style="padding:6px 8px; border-radius:4px; font-size:7.5px; line-height:1.3; background:rgba(0,229,255,0.06); border:1px solid rgba(0,229,255,0.2); color:#a5f3fc; margin-bottom:8px;">
            <strong>SCIENTIFIC DISCLOSURE:</strong> Modeled joint co-design produces deterministic engineering candidate trade-offs based on geometric line-of-sight and USGS CTX 20m Jezero topography. These are planning and decision support heuristics, NOT certified astronaut flight paths or RF-certified link propagation models.
          </div>

          <div style="display:flex; justify-content:flex-start;">
            <button class="btn-secondary joint-prev-step-btn" data-prev="5" style="font-size:9.5px; padding:4px 10px;">&larr; Back to Pareto Studio</button>
          </div>
        </div>
      </div>
'''

if __name__ == '__main__':
    html = get_tab_panel_html()
    print(f"Generated {len(html)} chars of HTML.")
