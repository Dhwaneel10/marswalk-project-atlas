import os
import re
from build_joint_panel_html import get_tab_panel_html
from build_joint_styles_css import get_joint_css
from build_joint_app_js import get_joint_js

HTML_PATH = 'web/index.html'
CSS_PATH = 'web/styles.css'
JS_PATH = 'web/app.js'

def update_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add HUD button
    hud_btn = '''        <button id="btnToggleRelayNet" class="theater-action-btn theater-relaynet-btn active" title="Toggle Atlas Mars RelayNet Mesh & Connectivity Twin">
          <span class="btn-icon">&#128225;</span> RELAYNET
          <span id="theaterRelayStatusDot" class="relaynet-status-dot online"></span>
        </button>'''
    
    hud_btn_replacement = '''        <button id="btnToggleRelayNet" class="theater-action-btn theater-relaynet-btn active" title="Toggle Atlas Mars RelayNet Mesh & Connectivity Twin">
          <span class="btn-icon">&#128225;</span> RELAYNET
          <span id="theaterRelayStatusDot" class="relaynet-status-dot online"></span>
        </button>
        <button id="btnToggleJointStudio" class="theater-action-btn theater-jointstudio-btn active" title="Toggle Joint Mission Co-Design Studio Drawer">
          <span class="btn-icon">&#9881;</span> CO-DESIGN
          <span id="theaterJointStatusDot" class="relaynet-status-dot online"></span>
        </button>'''
    
    if 'id="btnToggleJointStudio"' not in content:
        if hud_btn in content:
            content = content.replace(hud_btn, hud_btn_replacement, 1)
            print("Added HUD button #btnToggleJointStudio")
        else:
            print("ERROR: hud_btn target not found!")
    else:
        print("#btnToggleJointStudio already present")

    # 2. Add Tab button
    tab_btn_target = '<button class="inspector-tab" data-tab="tabRehearsalDirector" id="tabBtnRehearsalDirector">&#127916; Rehearsal</button>'
    tab_btn_replacement = '''<button class="inspector-tab" data-tab="tabRehearsalDirector" id="tabBtnRehearsalDirector">&#127916; Rehearsal</button>
        <button class="inspector-tab" data-tab="tabJointMissionStudio" id="tabBtnJointMissionStudio" title="Joint Mission Co-Design: Traverse Planning &times; RelayNet">&#9881; Co-Design</button>'''
    
    if 'id="tabBtnJointMissionStudio"' not in content:
        if tab_btn_target in content:
            content = content.replace(tab_btn_target, tab_btn_replacement, 1)
            print("Added Tab button #tabBtnJointMissionStudio")
        else:
            print("ERROR: tab_btn_target not found!")
    else:
        print("#tabBtnJointMissionStudio already present")

    # 3. Add Theater Drawer #jointMissionStudioPanel
    drawer_target = '<!-- Milestone 13C: Interactive Raycast Spatial Inspector Card -->'
    drawer_snippet = '''  <!-- Milestone 13E: Joint Mission Co-Design In-Theater Control Drawer Panel -->
  <div id="jointMissionStudioPanel" class="jointstudio-control-panel">
    <div class="jointstudio-panel-header">
      <div class="jointstudio-panel-title">
        <span class="jointstudio-icon">&#9881;</span>
        <span>JOINT CO-DESIGN TWIN</span>
      </div>
      <div class="jointstudio-header-actions">
        <span id="jointMissionStatusBadge" class="jointstudio-badge-status pareto">PARETO RANK 1</span>
        <button id="btnCloseJointStudioPanel" class="jointstudio-btn-close">&times;</button>
      </div>
    </div>

    <div class="jointstudio-panel-body">
      <!-- Active Co-Design Candidate Telemetry -->
      <div class="jointstudio-telemetry-box">
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">ACTIVE CANDIDATE:</span>
          <span id="jointTheaterCandidateId" class="jointstudio-telemetry-val text-cyan">JMC-01 (Nominal Balanced)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">TRAVERSE DISTANCE:</span>
          <span id="jointTheaterDistance" class="jointstudio-telemetry-val">3,412 m (&plusmn;0 m)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">COMMS COVERAGE:</span>
          <span id="jointTheaterCoverage" class="jointstudio-telemetry-val text-emerald">100.0% (0s gap)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">RELAYS DEPLOYED:</span>
          <span id="jointTheaterRelays" class="jointstudio-telemetry-val">1 (MRN-01 Scarp Promontory)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">METABOLIC WORK:</span>
          <span id="jointTheaterEnergy" class="jointstudio-telemetry-val">1,240 kJ (Waligora Model)</span>
        </div>
      </div>

      <!-- Quick Candidate Selector -->
      <div class="jointstudio-candidate-picker">
        <div class="jointstudio-section-title">SELECT CO-DESIGN CANDIDATE</div>
        <select id="jointTheaterCandidateSelect" class="hud-select" style="width:100%; font-size:10px; font-weight:600; padding:4px 6px;">
          <option value="">Run Co-Design Optimization...</option>
        </select>
      </div>

      <!-- Trajectory Display Toggles -->
      <div class="jointstudio-toggles-section">
        <div class="jointstudio-section-title">TRAJECTORY &amp; GAP LAYERS</div>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowSelected" checked>
          <span class="jointstudio-legend-indicator" style="background: #00e5ff; box-shadow: 0 0 6px #00e5ff;"></span>
          <span>Selected Co-Design Ribbon</span>
        </label>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowParetoAlts" checked>
          <span class="jointstudio-legend-indicator" style="background: #a855f7;"></span>
          <span>Pareto Alternative Routes (Dashed)</span>
        </label>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowDominated" checked>
          <span class="jointstudio-legend-indicator" style="background: #64748b;"></span>
          <span>Dominated Routes (Muted Grey)</span>
        </label>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowGaps" checked>
          <span class="jointstudio-legend-indicator" style="background: #ef4444; box-shadow: 0 0 6px #ef4444;"></span>
          <span>Blackout Comms Gaps (Pulsating)</span>
        </label>
      </div>

      <!-- Quick Actions -->
      <div class="jointstudio-actions-section">
        <button id="btnTheaterRunJointOptimize" class="jointstudio-action-button primary">
          <span class="btn-icon">&#9889;</span> Optimize Co-Design Candidates
        </button>
        <button id="btnTheaterPromoteJoint" class="jointstudio-action-button secondary" style="margin-top:6px;">
          <span class="btn-icon">&#128640;</span> Promote to Active Mission Plan
        </button>
      </div>
    </div>
  </div>\n\n  '''

    if 'id="jointMissionStudioPanel"' not in content:
        if drawer_target in content:
            content = content.replace(drawer_target, drawer_snippet + drawer_target, 1)
            print("Added #jointMissionStudioPanel")
        else:
            print("ERROR: drawer_target not found!")
    else:
        print("#jointMissionStudioPanel already present")

    # 4. Add Tab panel #tabJointMissionStudio
    tab_panel_target = '<!-- TAB 1: PLAN (Surface Traverse Planning & Configuration) -->'
    panel_html = get_tab_panel_html()

    if 'id="tabJointMissionStudio"' not in content:
        if tab_panel_target in content:
            content = content.replace(tab_panel_target, panel_html + '\n      ' + tab_panel_target, 1)
            print("Added #tabJointMissionStudio panel")
        else:
            print("ERROR: tab_panel_target not found!")
    else:
        print("#tabJointMissionStudio already present")

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("HTML updated successfully.")

def update_css():
    with open(CSS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'Milestone 13E: Joint Mission Co-Design' not in content:
        joint_css = get_joint_css()
        content = content + '\n' + joint_css
        with open(CSS_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("CSS appended successfully.")
    else:
        print("Milestone 13E CSS already present.")

def update_js():
    with open(JS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update switchInspectorTab
    old_panels = 'const panels = { tabMissionControl, tabExperimentStudio, tabRobustnessLab, tabRehearsalDirector, tabPlan, tabResults, tabScenarios, tabWorkspaces };'
    new_panels = 'const panels = { tabMissionControl, tabExperimentStudio, tabRobustnessLab, tabRehearsalDirector, tabJointMissionStudio, tabPlan, tabResults, tabScenarios, tabWorkspaces };'
    if old_panels in content:
        content = content.replace(old_panels, new_panels, 1)
        print("Updated panels dictionary in switchInspectorTab")

    old_cockpit_check = "if (tabId === 'tabMissionControl' || tabId === 'tabExperimentStudio' || tabId === 'tabRobustnessLab' || tabId === 'tabRehearsalDirector') {"
    new_cockpit_check = "if (tabId === 'tabMissionControl' || tabId === 'tabExperimentStudio' || tabId === 'tabRobustnessLab' || tabId === 'tabRehearsalDirector' || tabId === 'tabJointMissionStudio') {"
    if old_cockpit_check in content:
        content = content.replace(old_cockpit_check, new_cockpit_check, 1)
        print("Updated cockpit-mode check in switchInspectorTab")

    # 2. Add raycaster check for jointMissionTraverseGroup
    old_raycast_target = 'if (!hitHandled) {\n        const intersects = raycaster.intersectObjects(waypointBeacons);'
    new_raycast_check = '''if (!hitHandled && jointMissionTraverseGroup && jointMissionTraverseGroup.visible) {
        const jmHits = raycaster.intersectObjects(jointMissionTraverseGroup.children, true);
        if (jmHits.length > 0) {
          let topObj = jmHits[0].object;
          while (topObj.parent && topObj.parent !== jointMissionTraverseGroup && topObj.parent !== jointCandidatesGroup && topObj.parent !== jointGapsGroup && topObj.parent !== jointSelectedRouteGroup) {
            topObj = topObj.parent;
          }
          if (topObj.userData && (topObj.userData.candidateData || topObj.userData.gapData)) {
            const hitType = topObj.userData.gapData ? 'joint_gap_segment' : 'joint_candidate_route';
            const hitData = topObj.userData.gapData || topObj.userData.candidateData;
            showTheaterSpatialInspector(hitType, hitData, jmHits[0].point);
            hitHandled = true;
          }
        }
      }
      if (!hitHandled) {
        const intersects = raycaster.intersectObjects(waypointBeacons);'''
    
    if 'jointMissionTraverseGroup' not in content:
        if old_raycast_target in content:
            content = content.replace(old_raycast_target, new_raycast_check, 1)
            print("Added raycasting hit test for jointMissionTraverseGroup")
        else:
            print("ERROR: old_raycast_target not found!")

    # 3. Add cases in showTheaterSpatialInspector
    old_inspector_case = "} else if (type === 'los_obstruction') {"
    new_inspector_cases = '''} else if (type === 'joint_candidate_route') {
      if (typeBadge) typeBadge.textContent = 'CO-DESIGN TRAVERSE';
      const c = data;
      const m = c.metrics || {};
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Candidate ID:</span><span class="theater-inspector-val text-cyan">${c.candidate_id} (${c.strategy_name || 'Candidate'})</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Pareto Status:</span><span class="theater-inspector-val" style="color:${c.is_pareto ? '#10b981' : '#94a3b8'};">${c.is_pareto ? 'NON-DOMINATED (RANK 1)' : 'DOMINATED'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Traverse Distance:</span><span class="theater-inspector-val">${Number(m.total_distance_m || 0).toFixed(0)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Comms Coverage:</span><span class="theater-inspector-val" style="color:#10b981;">${Number(m.comms_coverage_pct || 0).toFixed(1)}%</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Relays Deployed:</span><span class="theater-inspector-val">${m.relay_count || 0} towers</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Waligora Metabolic:</span><span class="theater-inspector-val">${Number((m.metabolic_energy_j || 0) / 1000).toFixed(0)} kJ</span></div>
      `;
      if (citation) citation.textContent = 'Atlas Joint Mission Co-Design Engine (USGS CTX 20m DTM)';
    } else if (type === 'joint_gap_segment') {
      if (typeBadge) typeBadge.textContent = 'COMMS BLACKOUT GAP';
      const g = data;
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Gap Identifier:</span><span class="theater-inspector-val text-crimson" style="color:#ef4444;">${g.gap_id || 'GAP-01'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Blackout Distance:</span><span class="theater-inspector-val">${Number(g.gap_distance_m || 0).toFixed(0)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Blackout Duration:</span><span class="theater-inspector-val">${Number(g.duration_s || 0).toFixed(0)} s (${(Number(g.duration_s || 0)/60).toFixed(1)} min)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Occluding Scarp:</span><span class="theater-inspector-val">Delta Front Topographic Ridge</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Mitigation Triage:</span><span class="theater-inspector-val" style="color:#f59e0b;">Deploy Promontory Tower or Detour</span></div>
      `;
      if (citation) citation.textContent = 'Geometric LOS Raycasting Engine (USGS CTX DTM)';
    } else if (type === 'los_obstruction') {'''

    if "'joint_candidate_route'" not in content:
        if old_inspector_case in content:
            content = content.replace(old_inspector_case, new_inspector_cases, 1)
            print("Added joint_candidate_route and joint_gap_segment to showTheaterSpatialInspector")
        else:
            print("ERROR: old_inspector_case not found!")

    # 4. Initialize in initRelayNetEngine / initMissionTheater
    init_hook_target = 'initRelayNetEngine();'
    init_hook_replacement = '''initRelayNetEngine();
      // Milestone 13E: Initialize Atlas Joint Mission Co-Design Studio
      initJointMissionStudio();
      if (params.get('jointstudio') === '1' || params.get('jointstudio') === 'true') {
        switchInspectorTab('tabJointMissionStudio');
      }'''

    if 'initJointMissionStudio();' not in content:
        if init_hook_target in content:
            content = content.replace(init_hook_target, init_hook_replacement, 1)
            print("Added initJointMissionStudio hook")
        else:
            print("ERROR: init_hook_target not found!")

    # 5. Expose on window.Atlas API
    api_target = 'autoPlanOptimalRelays: () => autoPlanOptimalRelays(),'
    api_replacement = '''autoPlanOptimalRelays: () => autoPlanOptimalRelays(),
        // Milestone 13E: Joint Mission Co-Design API
        initJointMissionStudio: () => initJointMissionStudio(),
        runJointMissionOptimization: () => runJointMissionOptimization(),
        selectJointConfiguration: (id) => selectJointConfiguration(id),
        promoteJointConfiguration: () => promoteJointConfiguration(),
        switchJointWizardStep: (step) => switchJointWizardStep(step),'''

    if 'runJointMissionOptimization' not in content:
        if api_target in content:
            content = content.replace(api_target, api_replacement, 1)
            print("Exposed Joint Mission API on window.Atlas")
        else:
            print("ERROR: api_target not found!")

    # 6. Append Joint JS module
    if 'Milestone 13E: Atlas Joint Mission Co-Design Studio' not in content:
        joint_js = get_joint_js()
        content = content + '\n' + joint_js
        print("Appended Milestone 13E JS module.")

    with open(JS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("JS updated successfully.")

if __name__ == '__main__':
    update_html()
    update_css()
    update_js()
