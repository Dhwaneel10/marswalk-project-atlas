"""
Update web/index.html to include Milestone 12F Autonomous Mission Rehearsal Director UI.
"""

import os

INDEX_PATH = "web/index.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Add Rehearsal Director button in header
header_btn_target = '<button id="btnHeaderMissionControl" class="btn-primary btn-header-cockpit"'
header_btn_addition = '''<button id="btnHeaderRehearsalDirector" class="btn-primary btn-header-cockpit" style="font-size: 10px; padding: 4px 10px; background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); border-color: #a78bfa;" title="Autonomous Mission Rehearsal Director">
        &#127916; REHEARSAL DIRECTOR
      </button>

      '''

if 'id="btnHeaderRehearsalDirector"' not in html:
    assert header_btn_target in html, "btnHeaderMissionControl not found in index.html"
    html = html.replace(header_btn_target, header_btn_addition + header_btn_target, 1)

# 2. Add Rehearsal Director tab button in inspectorTabs
tab_btn_target = '<button class="inspector-tab" data-tab="tabRobustnessLab" id="tabBtnRobustnessLab">&#128737; Robustness</button>'
tab_btn_addition = tab_btn_target + '\n        <button class="inspector-tab" data-tab="tabRehearsalDirector" id="tabBtnRehearsalDirector">&#127916; Rehearsal</button>'

if 'id="tabBtnRehearsalDirector"' not in html:
    assert tab_btn_target in html, "tabBtnRobustnessLab not found in index.html"
    html = html.replace(tab_btn_target, tab_btn_addition, 1)

# 3. Add Rehearsal Director button in Cockpit operational toolbar
cockpit_btn_target = '<button id="btnMcRobustnessLab"'
cockpit_btn_addition = '''<button id="btnMcRehearsalDirector" class="btn-secondary" style="flex:1; min-width:115px; font-size:8.5px; justify-content:center; border-color:rgba(124,58,237,0.5); color:#c4b5fd;">&#127916; Rehearsal Director</button>\n            '''

if 'id="btnMcRehearsalDirector"' not in html:
    assert cockpit_btn_target in html, "btnMcRobustnessLab not found in index.html"
    html = html.replace(cockpit_btn_target, cockpit_btn_addition + cockpit_btn_target, 1)

# 4. Add tabRehearsalDirector panel before tabPlan
panel_target = '<!-- TAB 1: PLAN (Surface Traverse Planning & Configuration) -->'
rehearsal_panel = '''<!-- TAB REHEARSAL DIRECTOR (Milestone 12F: Autonomous Mission Rehearsal Director) -->
      <div id="tabRehearsalDirector" class="inspector-tab-panel hidden">
        <!-- Rehearsal Setup Card -->
        <div class="control-card" style="margin-bottom:8px; padding:8px 10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="control-label" style="font-size:9px; font-weight:700; color:#a78bfa;">&#127916; MISSION REHEARSAL DIRECTOR</span>
            <span id="rehStatusTag" class="wp-badge" style="font-size:8px; background:rgba(124,58,237,0.15); color:#c4b5fd; border-color:rgba(124,58,237,0.3);">READY</span>
          </div>

          <div style="display:flex; flex-direction:column; gap:6px; margin-top:4px;">
            <div>
              <label style="font-size:8.5px; color:var(--text-tertiary); display:block; margin-bottom:2px;">Baseline Exploration Campaign:</label>
              <select id="rehCampaignSelect" class="hud-select" style="width:100%; font-size:10px; padding:3px 5px;">
                <option value="">Loading campaigns...</option>
              </select>
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px;">
              <div>
                <label style="font-size:8.5px; color:var(--text-tertiary); display:block; margin-bottom:2px;">Recovery Policy:</label>
                <select id="rehPolicySelect" class="hud-select" style="width:100%; font-size:9.5px; padding:3px 4px;">
                  <option value="balanced" selected>Balanced (Detour &gt; Shed)</option>
                  <option value="safety_first">Safety First (Min 3600s)</option>
                  <option value="max_science">Max Science (Keep Targets)</option>
                </select>
              </div>
              <div>
                <label style="font-size:8.5px; color:var(--text-tertiary); display:block; margin-bottom:2px;">Min Margin Threshold:</label>
                <input type="number" id="rehMarginThreshold" class="hud-input" value="1800" min="0" max="7200" step="300" style="width:100%; font-size:9.5px; padding:3px 4px;" title="Minimum safe return margin in seconds">
              </div>
            </div>

            <!-- Disturbance Injection Sub-Panel -->
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:4px; padding:6px 8px; margin-top:2px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-size:8.5px; font-weight:700; color:#cbd5e1;">&#9888; SCHEDULED DISTURBANCE</span>
                <span id="rehDisturbanceCountTag" style="font-size:8px; color:var(--text-tertiary);">1 Configured</span>
              </div>
              <div style="display:grid; grid-template-columns: 1.2fr 0.8fr; gap:6px; margin-bottom:4px;">
                <div>
                  <label style="font-size:8px; color:var(--text-tertiary); display:block;">Disturbance Type:</label>
                  <select id="rehDisturbanceType" class="hud-select" style="width:100%; font-size:9px; padding:2px 4px;">
                    <option value="operational_delay">Operational Delay (+1800s)</option>
                    <option value="corridor_closure">Corridor Closure (50m)</option>
                    <option value="mobility_derating">Mobility Derating (0.7x)</option>
                    <option value="target_unavailability">Target Invalidation</option>
                    <option value="unit_dropout">Asset / Unit Dropout</option>
                  </select>
                </div>
                <div>
                  <label style="font-size:8px; color:var(--text-tertiary); display:block;">Trigger Time (s):</label>
                  <input type="number" id="rehTriggerTimeInput" class="hud-input" value="3600" min="0" step="600" style="width:100%; font-size:9px; padding:2px 4px;">
                </div>
              </div>
              <div id="rehDisturbanceParamDesc" style="font-size:8px; color:var(--text-secondary); line-height:1.2;">
                Simulates unexpected 30m sampling delay or comms blackout at T+3600s.
              </div>
            </div>

            <!-- Action Buttons -->
            <div style="display:flex; gap:6px; margin-top:4px;">
              <button id="btnExecuteRehearsal" class="btn-primary" style="flex:2; font-size:9.5px; padding:5px 8px; background:linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); border-color:#a78bfa; font-weight:700;">
                &#9654; EXECUTE REHEARSAL
              </button>
              <button id="btnResetRehearsal" class="btn-secondary" style="flex:1; font-size:9px; padding:5px 6px;">
                RESET
              </button>
            </div>
          </div>
          <div id="rehStatusBanner" class="hidden" style="font-size:8.5px; font-family:var(--font-mono); padding:4px 8px; border-radius:3px; margin-top:6px; background:rgba(0,0,0,0.6); border:1px solid var(--border-medium); color:var(--telemetry-cyan);"></div>
        </div>

        <!-- Rehearsal Comparison HUD (Tri-Track: Baseline vs Disturbed vs Recovered) -->
        <div id="rehComparisonCard" class="telemetry-card" style="margin-bottom:8px; padding:8px 10px; display:none;">
          <div class="telemetry-card-header" style="margin-bottom:6px; font-size:9px;">
            <span>&#9878; CLOSED-LOOP REHEARSAL OUTCOME</span>
            <span id="rehOutcomeBadge" class="wp-badge" style="background:rgba(16,185,129,0.15); color:var(--status-green); border-color:rgba(16,185,129,0.3);">RECOVERED</span>
          </div>

          <!-- Executive Assessment Box -->
          <div id="rehExecutiveAssessmentText" style="padding:6px 8px; border-radius:4px; font-size:8.5px; line-height:1.35; background:rgba(124,58,237,0.08); border:1px solid rgba(124,58,237,0.25); color:#ddd6fe; margin-bottom:8px;">
            Awaiting rehearsal run...
          </div>

          <!-- Delta Metrics Grid -->
          <div class="mc-metric-grid" style="margin-bottom:8px;">
            <div class="mc-metric-box">
              <span class="mc-metric-label">Science Preserved</span>
              <strong id="rehSciencePreservedVal" class="mc-metric-val" style="color:var(--status-green);">100%</strong>
            </div>
            <div class="mc-metric-box">
              <span class="mc-metric-label">Net Science Delta</span>
              <strong id="rehNetScienceDeltaVal" class="mc-metric-val">0.0 pts</strong>
            </div>
            <div class="mc-metric-box">
              <span class="mc-metric-label">Recovered Margin</span>
              <strong id="rehRecoveredMarginVal" class="mc-metric-val" style="color:var(--telemetry-cyan);">0 s</strong>
            </div>
            <div class="mc-metric-box">
              <span class="mc-metric-label">Delay Incurred</span>
              <strong id="rehDelayIncurredVal" class="mc-metric-val">+0 s</strong>
            </div>
            <div class="mc-metric-box">
              <span class="mc-metric-label">Targets Retained</span>
              <strong id="rehTargetsRetainedVal" class="mc-metric-val">0 / 0</strong>
            </div>
            <div class="mc-metric-box">
              <span class="mc-metric-label">Recovery Efficacy</span>
              <strong id="rehRecoveryEfficiencyVal" class="mc-metric-val" style="color:#c084fc;">100%</strong>
            </div>
          </div>

          <!-- Tri-Track Visual Comparison Bars -->
          <div style="background:rgba(0,0,0,0.25); border-radius:4px; padding:6px 8px; margin-bottom:8px; border:1px solid rgba(255,255,255,0.06);">
            <div style="font-size:8px; font-weight:700; color:var(--text-tertiary); margin-bottom:4px;">EXECUTION TRAJECTORY COMPARISON</div>
            
            <!-- Track 1: Baseline -->
            <div style="margin-bottom:5px;">
              <div style="display:flex; justify-content:space-between; font-size:7.5px; color:var(--text-secondary); margin-bottom:1px;">
                <span>NOMINAL BASELINE</span>
                <span id="rehTrackBaselineSummary">295.0 pts &bull; Margin: 12392s</span>
              </div>
              <div style="height:5px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                <div id="rehBarBaseline" style="width:100%; height:100%; background:var(--telemetry-cyan); border-radius:3px;"></div>
              </div>
            </div>

            <!-- Track 2: Disturbed Unmitigated -->
            <div style="margin-bottom:5px;">
              <div style="display:flex; justify-content:space-between; font-size:7.5px; color:#fca5a5; margin-bottom:1px;">
                <span>DISTURBED (UNMITIGATED)</span>
                <span id="rehTrackDisturbedSummary">Violations &bull; Depleted Margin</span>
              </div>
              <div style="height:5px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                <div id="rehBarDisturbed" style="width:65%; height:100%; background:#ef4444; border-radius:3px;"></div>
              </div>
            </div>

            <!-- Track 3: Closed-Loop Recovered -->
            <div>
              <div style="display:flex; justify-content:space-between; font-size:7.5px; color:#c4b5fd; margin-bottom:1px;">
                <span>AUTONOMOUS RECOVERED</span>
                <span id="rehTrackRecoveredSummary">Preserved &bull; Safe Margin</span>
              </div>
              <div style="height:5px; background:rgba(255,255,255,0.1); border-radius:3px; overflow:hidden;">
                <div id="rehBarRecovered" style="width:100%; height:100%; background:#8b5cf6; border-radius:3px;"></div>
              </div>
            </div>
          </div>

          <!-- Evaluated Recovery Candidates List -->
          <div style="margin-bottom:8px;">
            <div style="font-size:8px; font-weight:700; color:var(--text-tertiary); margin-bottom:4px;">RECOVERY CANDIDATE OPTIONS EVALUATED</div>
            <div id="rehCandidatesContainer" style="display:flex; flex-direction:column; gap:4px;">
              <!-- Dynamic candidate cards -->
            </div>
          </div>

          <!-- Causal Decision Ledger -->
          <div style="margin-bottom:8px;">
            <div style="font-size:8px; font-weight:700; color:var(--text-tertiary); margin-bottom:4px;">CAUSAL DECISION LEDGER</div>
            <div id="rehCausalLedgerContainer" style="display:flex; flex-direction:column; gap:3px; max-height:180px; overflow-y:auto; padding-right:2px;">
              <!-- Dynamic step items -->
            </div>
          </div>

          <!-- Rehearsal History & Export Controls -->
          <div style="display:flex; gap:6px; margin-top:6px;">
            <button id="btnExportRehearsalPack" class="btn-secondary" style="flex:1; font-size:8.5px; padding:4px 6px;">
              &#128190; EXPORT DECISION PACK
            </button>
            <button id="btnReplayRehearsal" class="btn-secondary" style="flex:1; font-size:8.5px; padding:4px 6px; border-color:rgba(124,58,237,0.4); color:#c4b5fd;">
              &#9658; REPLAY SEQUENCE
            </button>
          </div>
        </div>

        <!-- Scientific Disclosure Banner -->
        <div style="padding:6px 8px; border-radius:4px; font-size:7.5px; line-height:1.3; background:rgba(124,58,237,0.06); border:1px solid rgba(124,58,237,0.2); color:#c4b5fd; margin-bottom:8px;">
          <strong>REHEARSAL DISCLOSURE:</strong> Modeled closed-loop responses evaluate deterministic heuristic candidates based on USGS CTX 20m Jezero topography. Rehearsal outcomes measure robustness across explicitly injected disturbances only and are NOT certified astronaut flight paths.
        </div>
      </div>\n\n      '''

if 'id="tabRehearsalDirector"' not in html:
    assert panel_target in html, "tabPlan target not found in index.html"
    html = html.replace(panel_target, rehearsal_panel + panel_target, 1)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("Successfully updated web/index.html for Milestone 12F Mission Rehearsal Director.")
