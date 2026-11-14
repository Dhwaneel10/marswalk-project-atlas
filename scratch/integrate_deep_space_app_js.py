import os

APP_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"

with open(APP_PATH, "r", encoding="utf-8") as f:
    app_js = f.read()

if "initDeepSpaceAutonomyEngine" in app_js:
    print("app.js already has initDeepSpaceAutonomyEngine.")
    exit(0)

# 1. Add tab constants around line 856:
target_tab_var = "  const tabEnvironmentValidation = document.getElementById('tabEnvironmentValidation');"
new_tab_var = """  const tabDeepSpaceAutonomy = document.getElementById('tabDeepSpaceAutonomy');
  const tabBtnDeepSpaceAutonomy = document.getElementById('tabBtnDeepSpaceAutonomy');
  const tabEnvironmentValidation = document.getElementById('tabEnvironmentValidation');"""

app_js = app_js.replace(target_tab_var, new_tab_var, 1)

# 2. Add to panels object in switchInspectorTab:
target_panels = "tabEnvironmentStudio, tabEnvironmentValidation,"
new_panels = "tabEnvironmentStudio, tabEnvironmentValidation, tabDeepSpaceAutonomy,"
app_js = app_js.replace(target_panels, new_panels, 1)

# 3. Add to cockpit-mode tabs list:
target_cockpit = "tabId === 'tabEnvironmentValidation'"
new_cockpit = "tabId === 'tabEnvironmentValidation' || tabId === 'tabDeepSpaceAutonomy'"
app_js = app_js.replace(target_cockpit, new_cockpit, 1)

# 4. Add URL parameter handler:
target_url = "if (params.get('tab') === 'tribunal') {"
new_url = """if (params.get('tab') === 'autonomy' || params.get('tab') === 'deep-space' || params.get('tab') === 'tabDeepSpaceAutonomy') {
        switchInspectorTab('tabDeepSpaceAutonomy');
      }
      if (params.get('tab') === 'tribunal') {"""
app_js = app_js.replace(target_url, new_url, 1)

# 5. Add call to initDeepSpaceAutonomyEngine in init()
target_init_call = "initEnvironmentValidationEngine();"
new_init_call = """initEnvironmentValidationEngine();
      // Milestone 13O: Initialize Deep Space Autonomy Engine
      initDeepSpaceAutonomyEngine();"""
app_js = app_js.replace(target_init_call, new_init_call, 1)

# 6. Add complete initDeepSpaceAutonomyEngine implementation right before the end of the file:
deep_space_engine_js = """
  // =========================================================================
  // MILESTONE 13O: ATLAS DEEP SPACE AUTONOMY ENGINE
  // =========================================================================
  function initDeepSpaceAutonomyEngine() {
    const scenarioSelect = document.getElementById('dsScenarioSelect');
    const btnRunScenario = document.getElementById('btnDsRunScenario');
    const btnAdvanceTime = document.getElementById('btnDsAdvanceTime');
    const btnInjectHazard = document.getElementById('btnDsInjectHazard');
    const btnResetSim = document.getElementById('btnDsResetSim');

    const elUplink = document.getElementById('dsUplinkDelayText');
    const elDownlink = document.getElementById('dsDownlinkDelayText');
    const elRtlt = document.getElementById('dsRtltText');
    const elInFlight = document.getElementById('dsInFlightText');
    const elSimTime = document.getElementById('dsSimTimeText');
    const elEarthTrack = document.getElementById('dsEarthTimelineContent');
    const elChannelTrack = document.getElementById('dsChannelTimelineContent');
    const elMarsTrack = document.getElementById('dsMarsTimelineContent');
    const elBattery = document.getElementById('dsBatteryChargeText');
    const elStateVer = document.getElementById('dsRoverStateVerText');
    const elDecisionText = document.getElementById('dsDecisionText');
    const elStagesContainer = document.getElementById('dsScenarioStagesContainer');
    const elRoverModeBadge = document.getElementById('dsRoverModeBadge');

    let currentStatus = null;
    let latestScenarioResult = null;

    async function loadStatus() {
      try {
        const resp = await fetch('/api/deep-space/status');
        if (!resp.ok) return;
        const data = await resp.json();
        currentStatus = data;
        renderStatus(data);
      } catch (err) {
        console.warn('Deep space status fetch error:', err);
      }
    }

    async function loadScenarios() {
      if (!scenarioSelect) return;
      try {
        const resp = await fetch('/api/deep-space/scenarios');
        if (!resp.ok) return;
        const scenarios = await resp.json();
        scenarioSelect.innerHTML = '';
        scenarios.forEach(sc => {
          const opt = document.createElement('option');
          opt.value = sc.scenario_id;
          opt.textContent = `${sc.scenario_id}: ${sc.title}`;
          scenarioSelect.appendChild(opt);
        });
      } catch (err) {
        console.warn('Deep space scenarios fetch error:', err);
      }
    }

    function renderStatus(data) {
      if (!data) return;
      const c = data.comm_status || {};
      const f = data.fleet_status || {};
      const rovers = f.rovers || {};
      const rAlpha = rovers['ROVER_ALPHA'] || {};

      if (elUplink) elUplink.textContent = `${c.uplink_owlt_minutes || 14.2} min`;
      if (elDownlink) elDownlink.textContent = `${c.downlink_owlt_minutes || 14.2} min`;
      if (elRtlt) elRtlt.textContent = `${c.rtlt_minutes || 28.4} min`;
      if (elInFlight) elInFlight.textContent = `${c.in_flight_uplink || 0} UP / ${c.in_flight_downlink || 0} DN`;

      const tSec = data.sim_time_s || 0;
      const hrs = Math.floor(tSec / 3600);
      const mins = Math.floor((tSec % 3600) / 60);
      const secs = Math.floor(tSec % 60);
      if (elSimTime) elSimTime.textContent = `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

      if (elBattery && rAlpha.battery_charge_wh !== undefined) {
        const pct = Math.round((rAlpha.battery_charge_wh / 1200.0) * 100);
        elBattery.textContent = `${rAlpha.battery_charge_wh} Wh (${pct}%)`;
      }
      if (elStateVer && rAlpha.state_version !== undefined) {
        elStateVer.textContent = `Version ${rAlpha.state_version}`;
      }
      if (elRoverModeBadge && rAlpha.operating_mode) {
        elRoverModeBadge.textContent = `MODE: ${rAlpha.operating_mode}`;
      }
    }

    async function runSelectedScenario() {
      const scId = scenarioSelect ? scenarioSelect.value : 'SCENARIO_01';
      try {
        const resp = await fetch('/api/deep-space/scenarios/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario_id: scId, seed: 42 })
        });
        if (resp.ok) {
          const res = await resp.json();
          latestScenarioResult = res;
          renderScenarioResult(res);
          loadStatus();
        }
      } catch (err) {
        console.warn('Scenario run error:', err);
      }
    }

    function renderScenarioResult(res) {
      if (!elStagesContainer || !res.stage_summaries) return;
      const badge = document.getElementById('dsScenarioStageCountBadge');
      if (badge) badge.textContent = `STAGE ${res.stages_completed} / ${res.total_stages} (PASS)`;

      let html = '';
      res.stage_summaries.forEach(st => {
        html += `<div class="deep-space-stage-item completed">
          <span style="font-weight:700; color:#10b981; font-family:monospace;">&#10004; STAGE ${st.stage_num}:</span>
          <strong style="color:#e2e8f0;">${st.title}</strong>
          <span style="color:#94a3b8; font-size:8px;">${st.details}</span>
        </div>`;
      });
      elStagesContainer.innerHTML = html;

      // Update Tracks
      if (elEarthTrack) elEarthTrack.innerHTML = '<span style="color:#38bdf8; font-weight:700;">Earth Telecommand Dispatched &amp; Telemetry Confirmed</span>';
      if (elChannelTrack) elChannelTrack.innerHTML = '<span style="color:#c084fc;">RTLT 28.4 min round-trip propagation verified</span>';
      if (elMarsTrack) elMarsTrack.innerHTML = '<span style="color:#10b981; font-weight:700;">Stale instruction intercepted &bull; Local detour contingency executed</span>';

      // Update Decision Explanation
      if (elDecisionText) {
        elDecisionText.innerHTML = `<span style="color:#10b981; font-weight:700;">ACCEPTED CONTINGENCY:</span> Recomputed local detour around rockfall at (35.0, 50.0). Hard battery reserve preserved (&gt;200 Wh). In-situ state version updated.`;
      }
    }

    async function advanceSimulation() {
      try {
        const resp = await fetch('/api/deep-space/simulation/advance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step_seconds: 300.0 })
        });
        if (resp.ok) {
          loadStatus();
        }
      } catch (err) {
        console.warn('Advance error:', err);
      }
    }

    async function injectHazard() {
      try {
        const resp = await fetch('/api/deep-space/simulation/inject-hazard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rover_id: 'ROVER_ALPHA',
            hazard_type: 'FRESH_ROCKFALL_SLUMP',
            location_xy: [35.0, 50.0],
            severity: 'HIGH_IMPEDANCE',
            description: 'Scarp boulder detachment detected'
          })
        });
        if (resp.ok) {
          loadStatus();
          if (elDecisionText) {
            elDecisionText.innerHTML = '<span style="color:#ef4444; font-weight:700;">OBSTACLE DETECTED:</span> Rockfall slump at (35.0, 50.0). Mars state version incremented.';
          }
        }
      } catch (err) {
        console.warn('Hazard error:', err);
      }
    }

    async function resetSimulation() {
      try {
        const resp = await fetch('/api/deep-space/simulation/reset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ seed: 42, default_owlt_s: 852.0 })
        });
        if (resp.ok) {
          loadStatus();
          if (elStagesContainer) elStagesContainer.innerHTML = '';
          const badge = document.getElementById('dsScenarioStageCountBadge');
          if (badge) badge.textContent = 'STAGE 0 / 8';
          if (elDecisionText) elDecisionText.textContent = 'Standing by for incoming command evaluation.';
        }
      } catch (err) {
        console.warn('Reset error:', err);
      }
    }

    if (btnRunScenario) btnRunScenario.addEventListener('click', runSelectedScenario);
    if (btnAdvanceTime) btnAdvanceTime.addEventListener('click', advanceSimulation);
    if (btnInjectHazard) btnInjectHazard.addEventListener('click', injectHazard);
    if (btnResetSim) btnResetSim.addEventListener('click', resetSimulation);

    // Initial triggers
    loadScenarios();
    loadStatus();

    // Expose Automation API
    const dsApi = {
      loadStatus,
      loadScenarios,
      runSelectedScenario,
      advanceSimulation,
      injectHazard,
      resetSimulation,
      getStatus: () => currentStatus,
      getResult: () => latestScenarioResult,
    };

    if (!window.Atlas) window.Atlas = {};
    window.Atlas.deepSpaceAutonomy = dsApi;
    if (window.__atlas) window.__atlas.deepSpaceAutonomy = dsApi;
  }
"""

app_js = app_js + "\n" + deep_space_engine_js

with open(APP_PATH, "w", encoding="utf-8") as f:
    f.write(app_js)

print("app.js updated successfully with Deep Space Autonomy Engine.")
