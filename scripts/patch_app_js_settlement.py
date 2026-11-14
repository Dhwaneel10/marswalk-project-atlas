# Patch web/app.js to add initSettlementEngine and wire up Settlement Center

with open('web/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add init call and URL query check around line 19335
call_target = """        initMissionResilienceEngine();
        if (params.get('tab') === 'resilience' || params.get('tab') === 'apocalypse' || params.get('tab') === 'tabResilience') {
          switchInspectorTab('tabResilience');
        }"""

call_replacement = """        initMissionResilienceEngine();
        if (params.get('tab') === 'resilience' || params.get('tab') === 'apocalypse' || params.get('tab') === 'tabResilience') {
          switchInspectorTab('tabResilience');
        }
        initSettlementEngine();
        if (params.get('tab') === 'settlement' || params.get('tab') === 'settlement_center' || params.get('tab') === 'tabSettlement') {
          switchInspectorTab('tabSettlement');
        }"""

assert call_target in content, "call_target not found in web/app.js"
content = content.replace(call_target, call_replacement, 1)

# 2. Add initSettlementEngine implementation before the final closing brace
engine_code = """
  // ==========================================================================
  // MILESTONE 13S: ATLAS PLANETARY SETTLEMENT OPERATIONS CENTER CONTROLLER
  // ==========================================================================
  function initSettlementEngine() {
    const tabBtnSettlement = document.getElementById('tabBtnSettlement');

    const btnReset = document.getElementById('btnSettlementReset');
    const btnAdvance = document.getElementById('btnSettlementAdvanceSol');
    const lifecycleBadge = document.getElementById('settlementLifecycleBadge');
    const solVal = document.getElementById('settlementSolVal');
    const siteSelect = document.getElementById('settlementSiteSelect');
    const archSelect = document.getElementById('settlementArchSelect');

    const powerBadge = document.getElementById('settlementPowerSourceBadge');
    const grossGenVal = document.getElementById('settlementGrossGenVal');
    const demandVal = document.getElementById('settlementDemandVal');
    const deliveredVal = document.getElementById('settlementDeliveredVal');
    const batterySocVal = document.getElementById('settlementBatterySocVal');
    const shedLoadsContainer = document.getElementById('settlementShedLoadsContainer');

    const waterStockVal = document.getElementById('settlementWaterStockVal');
    const o2StockVal = document.getElementById('settlementO2StockVal');
    const ch4StockVal = document.getElementById('settlementCh4StockVal');
    const sinteredBlocksVal = document.getElementById('settlementSinteredBlocksVal');

    const habitatList = document.getElementById('settlementHabitatList');
    const constructionList = document.getElementById('settlementConstructionOperationsList');
    const constructionBadge = document.getElementById('settlementConstructionStatusBadge');
    const btnStepConstruction = document.getElementById('btnStepConstructionStage');

    const btnFission = document.getElementById('btnSimulatePowerFission');
    const btnSolarStorm = document.getElementById('btnSimulatePowerSolarStorm');
    const btnWater = document.getElementById('btnRunIsruWaterBatch');
    const btnO2 = document.getElementById('btnRunIsruOxygenBatch');
    const btnSinter = document.getElementById('btnRunIsruSinterBatch');

    const scoreBadge = document.getElementById('settlementReadinessScoreBadge');
    const scorePct = document.getElementById('settlementReadinessScorePct');
    const progressBar = document.getElementById('settlementReadinessProgressBar');
    const verifiedList = document.getElementById('settlementVerifiedCheckpointsList');
    const unmetList = document.getElementById('settlementUnmetGapsList');
    const btnReadiness = document.getElementById('btnExecuteReadinessReview');

    const scenarioSelect = document.getElementById('settlementScenarioSelect');
    const btnRunScenario = document.getElementById('btnRunSettlementScenario');
    const scenarioConsole = document.getElementById('settlementScenarioConsole');
    const stateHashVal = document.getElementById('settlementStateHashVal');

    // Tab button listener
    if (tabBtnSettlement) {
      tabBtnSettlement.addEventListener('click', () => {
        if (typeof switchInspectorTab === 'function') {
          switchInspectorTab('tabSettlement');
        }
        loadStatus();
      });
    }

    async function loadStatus() {
      try {
        const resp = await fetch('/api/settlement/status');
        if (!resp.ok) return;
        const data = await resp.json();

        if (lifecycleBadge) {
          lifecycleBadge.textContent = data.lifecycle_state || 'NOMINAL';
          lifecycleBadge.className = `settlement-badge ${data.status === 'DEGRADED' || data.status === 'RECOVERY' ? 'badge-critical' : 'badge-nominal'}`;
        }
        if (solVal) solVal.textContent = `Sol ${data.current_sol || 1}`;
        if (siteSelect && data.site_id) siteSelect.value = data.site_id;
        if (archSelect && data.archetype) archSelect.value = data.archetype;

        if (data.power) {
          if (grossGenVal) grossGenVal.textContent = `${(data.power.generation_gross_kw || 0).toFixed(1)} kW`;
          if (demandVal) demandVal.textContent = `${(data.power.total_demand_kw || 0).toFixed(1)} kW`;
          if (deliveredVal) deliveredVal.textContent = `${(data.power.total_delivered_kw || 0).toFixed(1)} kW`;
          if (batterySocVal) batterySocVal.textContent = `${(data.power.battery_soc_pct || 0).toFixed(1)}%`;

          if (shedLoadsContainer) {
            const sheds = data.power.active_shed_loads || [];
            if (sheds.length === 0) {
              shedLoadsContainer.innerHTML = '<span style="color:#4ade80; font-size:9.5px;">&check; Zero loads shed &bull; All 7 priority tiers fully energized</span>';
            } else {
              shedLoadsContainer.innerHTML = sheds.map(s => `<span class="settlement-badge badge-warning" style="margin-right:4px; margin-bottom:4px;">${s}</span>`).join('');
            }
          }
        }

        if (data.consumables && data.consumables.water) {
          if (waterStockVal) waterStockVal.textContent = `${Math.round(data.consumables.water.final_inventory || 0).toLocaleString()} kg`;
        }
        if (data.consumables && data.consumables.oxygen) {
          if (o2StockVal) o2StockVal.textContent = `${Math.round(data.consumables.oxygen.final_inventory || 0).toLocaleString()} kg`;
        }
        if (data.isru_inventories) {
          if (ch4StockVal) ch4StockVal.textContent = `${Math.round(data.isru_inventories.liquid_methane_ch4_kg || 0).toLocaleString()} kg`;
          if (sinteredBlocksVal) sinteredBlocksVal.textContent = `${Math.round(data.isru_inventories.sintered_regolith_blocks || 0).toLocaleString()} blocks`;
        }

        if (data.construction_summary && constructionBadge) {
          constructionBadge.textContent = `${data.construction_summary.completed_count} / ${data.construction_summary.total_operations} STAGES COMPLETE`;
        }

        await loadHabitats();
        await loadConstructionSchedule();
        await loadReplayHash();
      } catch (err) {
        console.error('Failed to load settlement status:', err);
      }
    }

    async function loadHabitats() {
      try {
        const resp = await fetch('/api/settlement/habitat/thermal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ambient_temp_c: -65.0, solar_flux_wm2: 450.0, dt_s: 3600.0 })
        });
        if (!resp.ok) return;
        const data = await resp.json();
        if (habitatList && data.modules) {
          habitatList.innerHTML = data.modules.map(m => `
            <div class="settlement-op-item">
              <div>
                <strong>${m.module_id}</strong> &bull; Temp: <span style="color:#38bdf8;">${m.internal_temp_c.toFixed(1)}&deg;C</span>
              </div>
              <div>
                Heating: <span style="color:#facc15;">${m.q_active_heating_required_kw.toFixed(1)} kW</span>
              </div>
            </div>
          `).join('');
        }
      } catch (err) {
        console.error('Failed to load habitats:', err);
      }
    }

    async function loadConstructionSchedule() {
      try {
        const resp = await fetch('/api/settlement/construction/schedule');
        if (!resp.ok) return;
        const data = await resp.json();
        if (constructionList && data.operations) {
          constructionList.innerHTML = data.operations.map(op => `
            <div class="settlement-op-item">
              <div>
                <span style="font-family:monospace; font-weight:700;">${op.op_id}</span>: ${op.name}
              </div>
              <div>
                <span class="settlement-badge ${op.status === 'COMPLETED' ? 'badge-nominal' : op.status === 'PRECONDITIONS_MET' ? 'badge-info' : 'badge-warning'}">${op.status}</span>
              </div>
            </div>
          `).join('');
        }
      } catch (err) {
        console.error('Failed to load construction schedule:', err);
      }
    }

    async function loadReplayHash() {
      try {
        const resp = await fetch('/api/settlement/replay');
        if (!resp.ok) return;
        const data = await resp.json();
        if (stateHashVal && data.final_state_hash) {
          stateHashVal.textContent = data.final_state_hash;
        }
      } catch (err) {
        console.error('Failed to load replay hash:', err);
      }
    }

    async function runReadinessReview() {
      try {
        if (btnReadiness) {
          btnReadiness.disabled = true;
          btnReadiness.textContent = 'AUDITING GATES...';
        }
        const resp = await fetch('/api/settlement/readiness-review');
        if (!resp.ok) return;
        const data = await resp.json();

        if (scorePct) scorePct.textContent = `${data.readiness_score_pct.toFixed(1)}%`;
        if (progressBar) progressBar.style.width = `${Math.min(100, data.readiness_score_pct)}%`;
        if (scoreBadge) {
          scoreBadge.textContent = data.is_ready_for_simulation_arrival ? 'SIMULATION READY' : 'UNMET GAPS DETECTED';
          scoreBadge.className = `settlement-badge ${data.is_ready_for_simulation_arrival ? 'badge-nominal' : 'badge-warning'}`;
        }

        if (verifiedList && data.verified_checkpoints) {
          verifiedList.innerHTML = data.verified_checkpoints.map(c => `<li style="color:#4ade80;">&check; ${c}</li>`).join('');
        }
        if (unmetList && data.unmet_gaps) {
          if (data.unmet_gaps.length === 0) {
            unmetList.innerHTML = '<li style="color:#4ade80;">&check; Zero unmet gaps. All Phase F requirements verified!</li>';
          } else {
            unmetList.innerHTML = data.unmet_gaps.map(g => `<li style="color:#f87171;">&#9888; ${g}</li>`).join('');
          }
        }
      } catch (err) {
        console.error('Failed to execute readiness review:', err);
      } finally {
        if (btnReadiness) {
          btnReadiness.disabled = false;
          btnReadiness.textContent = 'RUN READINESS REVIEW';
        }
      }
    }

    async function runScenario() {
      try {
        const scenId = scenarioSelect ? scenarioSelect.value : 'SCENARIO-10-MARS-BASE-ALPHA';
        if (btnRunScenario) {
          btnRunScenario.disabled = true;
          btnRunScenario.textContent = 'EXECUTING...';
        }
        if (scenarioConsole) scenarioConsole.textContent = `[EXEC] Running ${scenId}...\n`;

        const resp = await fetch('/api/settlement/scenarios/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario_id: scenId })
        });
        if (!resp.ok) return;
        const res = await resp.json();

        let output = `=================================================================\\n`;
        output += `SCENARIO: ${res.scenario_title} (${res.scenario_id})\\n`;
        output += `STATUS: ${res.success ? 'SUCCESS (PASS)' : 'DEGRADED / COMPROMISED'}\\n`;
        output += `SUMMARY: ${res.summary}\\n`;
        output += `-----------------------------------------------------------------\\n`;
        output += `KEY METRICS:\\n`;
        for (const [k, v] of Object.entries(res.key_metrics || {})) {
          output += `  &bull; ${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}\\n`;
        }
        output += `-----------------------------------------------------------------\\n`;
        output += `TIMELINE EVENTS:\\n`;
        (res.timeline_events || []).forEach(ev => {
          output += `  &bull; ${JSON.stringify(ev)}\\n`;
        });
        output += `=================================================================\\n`;

        if (scenarioConsole) scenarioConsole.innerHTML = output.replace(/\\n/g, '<br>');
        await loadStatus();
      } catch (err) {
        console.error('Failed to run settlement scenario:', err);
      } finally {
        if (btnRunScenario) {
          btnRunScenario.disabled = false;
          btnRunScenario.textContent = 'RUN SCENARIO';
        }
      }
    }

    async function advanceSol() {
      try {
        await fetch('/api/settlement/advance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sols_to_advance: 1 })
        });
        await loadStatus();
      } catch (err) {
        console.error('Failed to advance sol:', err);
      }
    }

    async function resetSettlement() {
      try {
        await fetch('/api/settlement/reset', { method: 'POST' });
        await loadStatus();
      } catch (err) {
        console.error('Failed to reset settlement:', err);
      }
    }

    // Attach button listeners
    if (btnAdvance) btnAdvance.addEventListener('click', advanceSol);
    if (btnReset) btnReset.addEventListener('click', resetSettlement);
    if (btnReadiness) btnReadiness.addEventListener('click', runReadinessReview);
    if (btnRunScenario) btnRunScenario.addEventListener('click', runScenario);

    if (btnFission) {
      btnFission.addEventListener('click', async () => {
        await fetch('/api/settlement/power/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ power_source: 'NUCLEAR_FISSION', atmospheric_tau: 0.45 })
        });
        await loadStatus();
      });
    }

    if (btnSolarStorm) {
      btnSolarStorm.addEventListener('click', async () => {
        await fetch('/api/settlement/power/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ power_source: 'SOLAR_PV', atmospheric_tau: 2.85 })
        });
        await loadStatus();
      });
    }

    if (btnWater) {
      btnWater.addEventListener('click', async () => {
        await fetch('/api/settlement/isru/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ process: 'WATER_EXTRACTION', feedstock_kg: 500.0, water_wt_pct: 7.5 })
        });
        await loadStatus();
      });
    }

    if (btnO2) {
      btnO2.addEventListener('click', async () => {
        await fetch('/api/settlement/isru/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ process: 'ATMOSPHERIC_OXYGEN', co2_intake_kg: 250.0 })
        });
        await loadStatus();
      });
    }

    if (btnSinter) {
      btnSinter.addEventListener('click', async () => {
        await fetch('/api/settlement/isru/evaluate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ process: 'REGOLITH_SINTERING', regolith_mass_kg: 1200.0 })
        });
        await loadStatus();
      });
    }

    if (btnStepConstruction) {
      btnStepConstruction.addEventListener('click', async () => {
        await fetch('/api/settlement/construction/step', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ op_id: 'OP-02-PAD-GRADING', execution_timestamp_s: 1000.0, command_dispatch_timestamp_s: 800.0 })
        });
        await loadStatus();
      });
    }

    // Initial load
    loadStatus();

    // Export to window.Atlas
    window.Atlas = window.Atlas || {};
    window.Atlas.settlementEngine = {
      loadStatus,
      runScenario,
      runReadinessReview,
      advanceSol,
      resetSettlement,
    };
  }
"""

# Insert before the last closing brace of app.js
last_brace = content.rfind('}')
assert last_brace != -1, "last brace not found in web/app.js"
content = content[:last_brace] + engine_code + "\n}\n"

with open('web/app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("web/app.js patched with initSettlementEngine successfully!")
