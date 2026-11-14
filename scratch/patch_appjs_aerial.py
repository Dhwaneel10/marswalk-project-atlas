import re

with open("web/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add initialization in DOMContentLoaded / startup
startup_target = "initDeepSpaceAutonomyEngine();\n"
aerial_startup = """initDeepSpaceAutonomyEngine();
      // Milestone 13P: Initialize Planetary Aerial Corps Engine
      initAerialCorpsEngine();
      if (params.get('tab') === 'aerial' || params.get('tab') === 'aerial-corps' || params.get('tab') === 'tabAerialCorps') {
        switchInspectorTab('tabAerialCorps');
      }
"""
if "initAerialCorpsEngine();" not in content:
    content = content.replace(startup_target, aerial_startup, 1)

# 2. Add implementation of initAerialCorpsEngine at the bottom of app.js
aerial_impl = """
  // =========================================================================
  // MILESTONE 13P: ATLAS AERIAL CORPS FLIGHT OPERATIONS ENGINE
  // =========================================================================
  function initAerialCorpsEngine() {
    const scenarioSelect = document.getElementById('acScenarioSelect');
    const btnRunScenario = document.getElementById('btnAcRunScenario');
    const btnEvalPerf = document.getElementById('btnAcEvalPerf');
    const btnJointPlan = document.getElementById('btnAcJointPlan');
    const btnReset = document.getElementById('btnAcReset');

    const elFleetCards = document.getElementById('acFleetCardsContainer');
    const elStagesContainer = document.getElementById('acScenarioStagesContainer');
    const elStageBadge = document.getElementById('acScenarioStageCountBadge');

    let currentFleet = [];
    let currentScenarios = [];

    // Load initial status
    async function loadStatus() {
      try {
        const resp = await fetch('/api/aerial/status');
        if (!resp.ok) return;
        const data = await resp.json();
        currentFleet = data.aircraft_fleet || [];
        renderFleetCards(currentFleet);
        renderAtmosphericLab(data.atmospheric_state || {});
      } catch (err) {
        console.warn('[AerialCorps] Failed to load status:', err);
      }
    }

    // Load scenarios list
    async function loadScenarios() {
      try {
        const resp = await fetch('/api/aerial/scenarios');
        if (!resp.ok) return;
        currentScenarios = await resp.json();
        if (scenarioSelect) {
          scenarioSelect.innerHTML = '';
          currentScenarios.forEach(sc => {
            const opt = document.createElement('option');
            opt.value = sc.id;
            opt.textContent = `${sc.id}: ${sc.name}`;
            if (sc.signature) opt.selected = true;
            scenarioSelect.appendChild(opt);
          });
        }
      } catch (err) {
        console.warn('[AerialCorps] Failed to load scenarios:', err);
      }
    }

    function renderFleetCards(fleet) {
      if (!elFleetCards) return;
      elFleetCards.innerHTML = '';
      fleet.forEach((ac, idx) => {
        const card = document.createElement('div');
        card.className = `aerial-corps-aircraft-card ${idx === 0 ? 'active-aircraft' : ''}`;
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <strong style="color:#38bdf8; font-size:10px;">${ac.name}</strong>
            <span class="wp-badge" style="background:rgba(56,189,248,0.2); color:#38bdf8; font-size:8px;">${ac.flight_mode}</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:4px; font-size:8.5px; color:#cbd5e1;">
            <div>Pos: [${ac.position_xyz_m[0]}, ${ac.position_xyz_m[1]}]</div>
            <div>Alt AGL: <strong style="color:#10b981;">${ac.altitude_agl_m}m</strong></div>
            <div>Battery: <strong style="color:${ac.battery_soc_pct < 25 ? '#f87171' : '#34d399'};">${ac.battery_soc_pct}%</strong></div>
            <div>Power: ${ac.power_draw_w}W</div>
          </div>
        `;
        elFleetCards.appendChild(card);
      });
    }

    function renderAtmosphericLab(atmos) {
      const elDensity = document.getElementById('acMetricDensity');
      const elSound = document.getElementById('acMetricSound');
      if (elDensity && atmos.density_kg_m3) elDensity.textContent = `${atmos.density_kg_m3.toFixed(4)} kg/m³`;
      if (elSound && atmos.speed_of_sound_m_s) elSound.textContent = `${atmos.speed_of_sound_m_s.toFixed(1)} m/s`;
    }

    async function runScenario(scenarioId) {
      const scId = scenarioId || (scenarioSelect ? scenarioSelect.value : 'SCENARIO_01');
      try {
        const resp = await fetch('/api/aerial/scenarios/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario_id: scId }),
        });
        if (!resp.ok) return;
        const res = await resp.json();
        renderScenarioStages(res);
      } catch (err) {
        console.error('[AerialCorps] Run scenario failed:', err);
      }
    }

    function renderScenarioStages(res) {
      if (!elStagesContainer) return;
      elStagesContainer.innerHTML = '';
      if (elStageBadge) elStageBadge.textContent = `STAGE ${res.stages.length} / ${res.total_stages}`;

      res.stages.forEach(st => {
        const div = document.createElement('div');
        div.className = 'aerial-corps-stage-item completed';
        div.innerHTML = `
          <div style="min-width:55px; font-weight:700; color:#38bdf8;">T+${st.elapsed_time_s.toFixed(0)}s</div>
          <div style="flex:1;">
            <div style="font-weight:700; color:#f1f5f9;">Stage ${st.stage_number}: ${st.stage_name}</div>
            <div style="color:#94a3b8; font-size:8.5px;">${st.description}</div>
            ${st.events.length > 0 ? `<div style="color:#34d399; font-size:8px; margin-top:2px;">&bull; ${st.events.join('<br>&bull; ')}</div>` : ''}
          </div>
        `;
        elStagesContainer.appendChild(div);
      });
    }

    async function evaluatePerformance() {
      try {
        const resp = await fetch('/api/aerial/performance/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: 'LIGHT_SCOUT' }),
        });
        if (!resp.ok) return;
        const env = await resp.json();
        const elTM = document.getElementById('acMetricThrustMargin');
        const elPwr = document.getElementById('acMetricHoverPower');
        const elEnd = document.getElementById('acMetricEndurance');
        if (elTM) elTM.textContent = `${env.hover_thrust_margin.toFixed(2)} ≥ 1.15`;
        if (elPwr) elPwr.textContent = `${env.hover_power_w.toFixed(1)} W`;
        if (elEnd) elEnd.textContent = `${env.estimated_hover_endurance_s.toFixed(1)} s`;
      } catch (err) {
        console.error('[AerialCorps] Evaluate performance failed:', err);
      }
    }

    async function planJointMission() {
      try {
        const resp = await fetch('/api/aerial/rover-cooperation/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rover_id: 'PERSEVERANCE_01',
            aircraft_id: 'AERO-INGENUITY-01',
            target_region_name: 'Jezero Delta Front',
            rover_current_xy_m: [0.0, 0.0],
            science_target_xy_m: [80.0, 95.0],
          }),
        });
        if (!resp.ok) return;
        const plan = await resp.json();
        const elSaved = document.getElementById('acMetricDistSaved');
        const elUncert = document.getElementById('acMetricUncertaintyDrop');
        const elEnergy = document.getElementById('acMetricNetEnergy');
        if (elSaved) elSaved.textContent = `${plan.net_rover_distance_delta_m.toFixed(1)} m`;
        if (elUncert) elUncert.textContent = `${plan.baseline_rover_uncertainty_pct.toFixed(0)}% → ${plan.refined_rover_uncertainty_pct.toFixed(1)}%`;
        if (elEnergy) elEnergy.textContent = `+${plan.net_mission_energy_delta_wh.toFixed(1)} Wh`;
      } catch (err) {
        console.error('[AerialCorps] Joint mission plan failed:', err);
      }
    }

    async function resetFleet() {
      try {
        await fetch('/api/aerial/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        loadStatus();
        if (elStagesContainer) elStagesContainer.innerHTML = '<div style="color:#94a3b8; font-size:9px; padding:4px;">Fleet reset to initial basecamp standby state.</div>';
      } catch (err) {
        console.error('[AerialCorps] Reset failed:', err);
      }
    }

    // Attach button listeners
    if (btnRunScenario) btnRunScenario.addEventListener('click', () => runScenario());
    if (btnEvalPerf) btnEvalPerf.addEventListener('click', evaluatePerformance);
    if (btnJointPlan) btnJointPlan.addEventListener('click', planJointMission);
    if (btnReset) btnReset.addEventListener('click', resetFleet);

    // Initial load
    loadStatus();
    loadScenarios();

    // Export API to window.Atlas
    window.Atlas = window.Atlas || {};
    window.Atlas.aerialCorps = {
      loadStatus,
      loadScenarios,
      runScenario,
      evaluatePerformance,
      planJointMission,
      resetFleet,
    };
  }
"""

if "function initAerialCorpsEngine()" not in content:
    content += "\n" + aerial_impl

with open("web/app.js", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated web/app.js with initAerialCorpsEngine!")
