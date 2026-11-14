"""Update web/index.html to include Mission Robustness Lab UI."""

import os

INDEX_PATH = "web/index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add Robustness tab button to inspectorTabs
tab_target = '<button class="inspector-tab active" data-tab="tabMissionControl" id="tabBtnMissionControl">&#128640; Cockpit</button>'
tab_replacement = tab_target + '\n        <button class="inspector-tab" data-tab="tabRobustnessLab" id="tabBtnRobustnessLab">&#128737; Robustness</button>'

if 'id="tabBtnRobustnessLab"' not in html:
    assert tab_target in html, "tab_target not found in index.html"
    html = html.replace(tab_target, tab_replacement, 1)

# 2. Add Robustness Lab button in Cockpit operational toolbar
btn_target = '<button id="btnMcExportDecisionPack"'
btn_replacement = '<button id="btnMcRobustnessLab" class="btn-secondary" style="flex:1; min-width:110px; font-size:8.5px; justify-content:center; border-color:rgba(239,68,68,0.5); color:#fca5a5;">&#128737; Robustness Lab</button>\n            <button id="btnMcExportDecisionPack"'

if 'id="btnMcRobustnessLab"' not in html:
    assert btn_target in html, "btn_target not found in index.html"
    html = html.replace(btn_target, btn_replacement, 1)

# 3. Add tabRobustnessLab panel before tabPlan
panel_target = '<!-- TAB 1: PLAN (Surface Traverse Planning & Configuration) -->'
robustness_panel = '''<!-- TAB ROBUSTNESS LAB (Milestone 12E: Atlas Mission Robustness Lab) -->
      <div id="tabRobustnessLab" class="inspector-tab-panel hidden">
        <!-- Robustness Lab Control & Execution Header -->
        <div class="control-card" style="margin-bottom:8px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="control-label" style="font-size:9px; font-weight:700; color:#f87171;">&#128737; MISSION ROBUSTNESS &amp; SENSITIVITY LAB</span>
            <span id="robStatusTag" class="wp-badge" style="font-size:8px; background:rgba(239,68,68,0.15); color:#fca5a5; border-color:rgba(239,68,68,0.3);">READY</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px; margin-top:4px;">
            <div>
              <label style="font-size:8.5px; color:var(--text-tertiary); display:block; margin-bottom:2px;">Target Plan:</label>
              <select id="robCampaignSelect" class="hud-select" style="width:100%; font-size:10px; padding:3px 5px;">
                <option value="">Loading campaigns...</option>
              </select>
            </div>
            <div>
              <label style="font-size:8.5px; color:var(--text-tertiary); display:block; margin-bottom:2px;">Stress Suite Type:</label>
              <select id="robSuiteSelect" class="hud-select" style="width:100%; font-size:10px; padding:3px 5px;">
                <option value="full_battery">&#9733; Full Battery (10 Curated Stress Cases)</option>
                <option value="duration_stress">Duration Contraction (-15%, -30%, -45%)</option>
                <option value="mobility_derating">Mobility Derating (0.85x, 0.70x, Slope 12&deg;)</option>
                <option value="operational_delays">Operational Holds (+15m, +30m, +60m)</option>
                <option value="corridor_closures">Corridor Chokepoints (30m, 60m, 100m)</option>
                <option value="compound_gauntlet">Compound Operational Gauntlet</option>
              </select>
            </div>
            <button id="btnRunRobustnessBattery" class="btn-primary" style="font-size:10px; font-weight:700; padding:6px 10px; margin-top:2px; background:linear-gradient(135deg, #ef4444 0%, #dc2626 100%); border-color:#f87171; justify-content:center;">
              &#9654; EXECUTE DETERMINISTIC STRESS BATTERY
            </button>
          </div>
          <div id="robStatusBanner" class="hidden" style="font-size:8.5px; font-family:var(--font-mono); padding:4px 8px; border-radius:3px; margin-top:6px; background:rgba(0,0,0,0.6); border:1px solid var(--border-medium); color:var(--telemetry-cyan);"></div>
        </div>

        <!-- Feasibility Envelope Card -->
        <div class="telemetry-card" style="margin-bottom:8px; padding:8px 10px;">
          <div class="telemetry-card-header" style="margin-bottom:6px; font-size:9px;">
            <span>&#9878; FEASIBILITY ENVELOPE &amp; BOUNDS</span>
            <span id="robFeasibilityBadge" class="wp-badge" style="font-size:8px; background:rgba(16,185,129,0.15); color:var(--status-green); border-color:rgba(16,185,129,0.3);">100% FEASIBLE</span>
          </div>
          <div style="margin-bottom:6px;">
            <div style="display:flex; justify-content:space-between; font-size:8.5px; margin-bottom:3px; font-family:var(--font-mono);">
              <span>Tested Feasibility Ratio:</span>
              <strong id="robEnvelopeRatioText">0 / 0 cases (0%)</strong>
            </div>
            <div style="width:100%; height:8px; background:rgba(255,255,255,0.08); border-radius:4px; overflow:hidden;">
              <div id="robEnvelopeProgressBar" style="width:0%; height:100%; background:var(--status-green); transition:width 0.3s ease;"></div>
            </div>
          </div>
          <div style="font-size:8.5px; color:var(--text-secondary); margin-top:4px;">
            <strong>Identified Bottlenecks:</strong>
            <ul id="robBottlenecksList" style="margin:4px 0 0 14px; padding:0; color:var(--text-secondary); font-size:8px; line-height:1.3;">
              <li>Run stress battery to evaluate bottlenecks.</li>
            </ul>
          </div>
          <div style="font-size:8.5px; color:var(--text-secondary); margin-top:6px;">
            <strong>Critical Breakpoints:</strong>
            <div id="robBreakpointsContainer" style="font-size:8px; font-family:var(--font-mono); color:var(--text-tertiary); margin-top:2px;">
              None recorded.
            </div>
          </div>
        </div>

        <!-- Parameter Sensitivity Ranking Card -->
        <div class="telemetry-card" style="margin-bottom:8px; padding:8px 10px;">
          <div class="telemetry-card-header" style="margin-bottom:6px; font-size:9px;">
            <span>&#128200; PARAMETER SENSITIVITY GRADIENTS</span>
            <span style="font-size:7.5px; color:var(--text-tertiary);">&part;Metric / &part;Param</span>
          </div>
          <div id="robSensitivityList" style="display:flex; flex-direction:column; gap:4px;">
            <div style="font-size:8px; color:var(--text-tertiary); font-style:italic;">Execute stress battery to compute finite-difference sensitivity gradients.</div>
          </div>
        </div>

        <!-- Objective & Unit Vulnerability Matrix Card -->
        <div class="telemetry-card" style="margin-bottom:8px; padding:8px 10px;">
          <div class="telemetry-card-header" style="margin-bottom:6px; font-size:9px;">
            <span>&#9888; VULNERABLE OBJECTIVES &amp; TARGETS</span>
            <span id="robVulnCountBadge" class="wp-badge" style="font-size:8px;">0 Vulnerable</span>
          </div>
          <div id="robVulnerableTargetsContainer" style="display:flex; flex-direction:column; gap:3px; max-height:110px; overflow-y:auto;">
            <div style="font-size:8px; color:var(--text-tertiary); font-style:italic;">No targets deferred under tested conditions.</div>
          </div>
        </div>

        <!-- 7 Core Engineering Questions Answers Card -->
        <div class="telemetry-card" style="margin-bottom:8px; padding:8px 10px;">
          <div class="telemetry-card-header" style="margin-bottom:6px; font-size:9px;">
            <span>&#128221; ENGINEERING SYNTHESIS &amp; SEVEN CORE ANSWERS</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:6px;">
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">1. Most Sensitive Assumptions:</span>
              <p id="robAns1" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">2. Infeasibility Conditions:</span>
              <p id="robAns2" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">3. Vulnerable Objectives &amp; Units:</span>
              <p id="robAns3" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">4. Performance Spread:</span>
              <p id="robAns4" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">5. Maximum Margin Plans:</span>
              <p id="robAns5" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">6. Supporting Evidence:</span>
              <p id="robAns6" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
            <div class="rob-q-box" style="padding:4px 6px; background:rgba(0,0,0,0.3); border:1px solid var(--border-subtle); border-radius:3px;">
              <span class="rob-q-title" style="font-size:8px; font-weight:700; color:var(--telemetry-cyan); display:block; margin-bottom:2px;">7. Unestablished Limits:</span>
              <p id="robAns7" class="rob-q-text" style="font-size:8px; color:var(--text-secondary); margin:0; line-height:1.3;">—</p>
            </div>
          </div>
        </div>

        <!-- Resilient Strategy Comparison & Candidate Promotion Card -->
        <div class="telemetry-card" style="margin-bottom:8px; padding:8px 10px;">
          <div class="telemetry-card-header" style="margin-bottom:6px; font-size:9px;">
            <span>&#9878; RESILIENT STRATEGY COMPARISON &amp; PROMOTION</span>
            <span class="wp-badge" style="background:rgba(168,85,247,0.15); color:#c084fc; font-size:8px;">PARETO TRADE-OFF</span>
          </div>
          <div id="robStrategiesContainer" style="display:flex; flex-direction:column; gap:5px; margin-bottom:8px;">
            <div style="font-size:8px; color:var(--text-tertiary); font-style:italic;">Execute stress battery to compare resilient strategy alternatives.</div>
          </div>
          <div id="robRecommendationText" style="font-size:8.5px; color:var(--telemetry-cyan); font-family:var(--font-mono); margin-bottom:6px; padding:4px 6px; background:rgba(0,229,255,0.06); border:1px solid rgba(0,229,255,0.2); border-radius:3px;">
            Standing by for stress battery execution.
          </div>
          <button id="btnPromoteResilientStrategy" class="btn-primary" style="width:100%; font-size:9px; font-weight:700; padding:5px; background:linear-gradient(135deg, #10b981 0%, #059669 100%); border-color:#34d399; justify-content:center;">
            &#11014; ADOPT RESILIENT STRATEGY
          </button>
        </div>

        <!-- Truth & Limitations Notice -->
        <div style="padding:6px 8px; border-radius:4px; font-size:7.5px; line-height:1.3; background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.2); color:#fca5a5; margin-bottom:8px;">
          <strong>CRITICAL SCIENTIFIC NOTICE:</strong> Tested scenario frequency (e.g. 70% feasible) measures deterministic performance across the finite evaluated stress suite ONLY. It MUST NOT be interpreted as a physical Martian probability, empirical success rate, or certified astronaut flight safety margin. All calculations derive from USGS CTX 20m Jezero topography and SI units.
        </div>
      </div>\n\n      '''

if 'id="tabRobustnessLab"' not in html:
    assert panel_target in html, "panel_target not found in index.html"
    html = html.replace(panel_target, robustness_panel + panel_target, 1)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("Updated web/index.html successfully!")
