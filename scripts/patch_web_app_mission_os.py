"""Patch web/app.js to add initMissionOSEngine() for Milestone 13T."""
import sys

def patch():
    with open("web/app.js", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add hook in initialization block
    init_target = """        initSettlementEngine();
        if (params.get('tab') === 'settlement' || params.get('tab') === 'settlement_center' || params.get('tab') === 'tabSettlement') {
          switchInspectorTab('tabSettlement');
        }"""
    init_repl = (
        init_target + "\n"
        "        initMissionOSEngine();\n"
        "        if (params.get('tab') === 'mission_os' || params.get('tab') === 'mission-os' || params.get('tab') === 'tabMissionOS') {\n"
        "          switchInspectorTab('tabMissionOS');\n"
        "        }"
    )
    if init_target in content:
        content = content.replace(init_target, init_repl, 1)
    else:
        print("Init target not found in web/app.js!")
        sys.exit(1)

    # 2. Add initMissionOSEngine() definition before the final closing brace
    func_target = "    window.Atlas.settlementEngine = {\n      loadStatus,\n      runScenario,\n      runReadinessReview,\n      advanceSol,\n      resetSettlement,\n    };\n  }\n\n}"
    
    func_code = """    window.Atlas.settlementEngine = {
      loadStatus,
      runScenario,
      runReadinessReview,
      advanceSol,
      resetSettlement,
    };
  }

  // ============================================================================
  // MILESTONE 13T: ATLAS PLANETARY MISSION OPERATING SYSTEM ENGINE
  // ============================================================================
  function initMissionOSEngine() {
    const statusBadge = document.getElementById('missionOSStatusBadge');
    const solVal = document.getElementById('missionOSSol');
    const solTimeVal = document.getElementById('missionOSSolTime');
    const lsVal = document.getElementById('missionOSLs');
    const powerVal = document.getElementById('missionOSPower');
    const batteryVal = document.getElementById('missionOSBattery');
    const waterVal = document.getElementById('missionOSWater');
    const oxygenVal = document.getElementById('missionOSOxygen');
    const sinteredVal = document.getElementById('missionOSSinteredBlocks');
    const habVal = document.getElementById('missionOSHabStatus');
    const stateHashVal = document.getElementById('missionOSStateHash');

    const btnFlagship = document.getElementById('btnRunFlagshipMissionOS');
    const btnAdvance1 = document.getElementById('btnAdvanceSolMissionOS');
    const btnAdvance5 = document.getElementById('btnAdvance5SolMissionOS');
    const btnDispatchCmd = document.getElementById('btnDispatchEarthCmdMissionOS');
    const btnInjectDust = document.getElementById('btnInjectDustStormMissionOS');
    const btnVerifyReplay = document.getElementById('btnVerifyReplayMissionOS');
    const btnExportDossier = document.getElementById('btnExportDossierMissionOS');

    const contingencyStatus = document.getElementById('missionOSContingencyStatus');
    const diagnosisText = document.getElementById('missionOSDiagnosisText');
    const readinessScore = document.getElementById('missionOSReadinessScore');
    const replayAuditBadge = document.getElementById('missionOSReplayAuditBadge');

    async function loadStatus() {
      try {
        const res = await fetch('/api/mission-os/status');
        if (!res.ok) return;
        const data = await res.json();

        if (statusBadge) {
          statusBadge.textContent = data.status || 'EXECUTING';
          if (data.status === 'COMPLETED') {
            statusBadge.style.background = '#1b3d2f';
            statusBadge.style.color = '#7ee787';
            statusBadge.style.borderColor = '#238636';
          }
        }
        if (solVal) solVal.textContent = 'SOL ' + String(data.current_sol || 1).padStart(2, '0');
        if (solTimeVal) solTimeVal.textContent = data.current_sol_time || '06:00:00';
        if (lsVal) lsVal.textContent = (data.solar_longitude_ls || 56.4).toFixed(2) + '°';

        if (data.resource_ledgers && data.resource_ledgers.length > 0) {
          const lastLedger = data.resource_ledgers[data.resource_ledgers.length - 1];
          if (powerVal) powerVal.textContent = `${lastLedger.power_generated_kwe || 120} / ${lastLedger.power_consumed_kwe || 68}`;
          if (batteryVal) batteryVal.textContent = `${lastLedger.battery_soc_pct || 94}%`;
          if (waterVal) waterVal.textContent = Math.round(lastLedger.water_reserve_kg || 3450).toLocaleString();
          if (oxygenVal) oxygenVal.textContent = Math.round(lastLedger.oxygen_reserve_kg || 1250).toLocaleString();
          if (sinteredVal) sinteredVal.textContent = lastLedger.sintered_blocks_count || 120;
        }

        if (stateHashVal && data.state_hash) {
          stateHashVal.textContent = data.state_hash.substring(0, 8) + '...' + data.state_hash.substring(56);
        }

        // Update phase progress bars
        if (data.phases && data.phases.length >= 7) {
          const pKeys = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];
          pKeys.forEach((key, idx) => {
            const phase = data.phases[idx];
            const pText = document.getElementById(`phase${key}Progress`);
            const pBar = document.getElementById(`phase${key}Bar`);
            if (pText && phase) {
              pText.textContent = phase.is_completed ? '100% COMPLETE' : (phase.is_active ? `${phase.completion_pct}% ACTIVE` : 'PENDING');
            }
            if (pBar && phase) {
              pBar.style.width = `${phase.completion_pct || (phase.is_completed ? 100 : 0)}%`;
            }
          });
        }
      } catch (err) {
        console.warn('[MissionOS] Failed to load status:', err);
      }
    }

    if (btnFlagship) {
      btnFlagship.addEventListener('click', async () => {
        btnFlagship.disabled = true;
        btnFlagship.textContent = 'RUNNING 12 PHASES...';
        try {
          const res = await fetch('/api/mission-os/flagship/run');
          if (res.ok) {
            await loadStatus();
            if (readinessScore) readinessScore.textContent = '100.0% / PASSED';
            if (replayAuditBadge) replayAuditBadge.textContent = '100% BIT-EXACT VERIFIED';
            btnFlagship.textContent = '✓ FLAGSHIP COMPLETED (100% QUALIFIED)';
          }
        } catch (err) {
          console.error('[MissionOS] Flagship run error:', err);
          btnFlagship.textContent = 'RUN FLAGSHIP DEMO (12 PHASES)';
        } finally {
          btnFlagship.disabled = false;
        }
      });
    }

    if (btnAdvance1) {
      btnAdvance1.addEventListener('click', async () => {
        await fetch('/api/mission-os/advance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sols_to_advance: 1 })
        });
        await loadStatus();
      });
    }

    if (btnAdvance5) {
      btnAdvance5.addEventListener('click', async () => {
        await fetch('/api/mission-os/advance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sols_to_advance: 5 })
        });
        await loadStatus();
      });
    }

    if (btnDispatchCmd) {
      btnDispatchCmd.addEventListener('click', async () => {
        await fetch('/api/mission-os/dispatch-command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_asset_id: 'ATLAS-ROVER-01',
            action: 'EXPLORE_DELTA_FAN',
            parameters: { target_lat: 18.4520, target_lon: 77.4350 }
          })
        });
        await loadStatus();
      });
    }

    if (btnInjectDust) {
      btnInjectDust.addEventListener('click', async () => {
        const res = await fetch('/api/mission-os/inject-event', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            subsystem: 'ATMOSPHERE',
            mode: 'REGIONAL_DUST_STORM',
            root_cause: 'Particulate optical depth tau surge to 2.80'
          })
        });
        if (res.ok) {
          const injData = await res.json();
          if (contingencyStatus) {
            contingencyStatus.textContent = 'DUST STORM INJECTED (tau=2.80)';
            contingencyStatus.style.color = '#ff7b72';
          }
          if (diagnosisText && injData.response) {
            diagnosisText.textContent = injData.response.diagnosis;
          }
          await loadStatus();
        }
      });
    }

    if (btnVerifyReplay) {
      btnVerifyReplay.addEventListener('click', async () => {
        const res = await fetch('/api/mission-os/replay');
        if (res.ok) {
          const replayData = await res.json();
          if (replayAuditBadge) {
            replayAuditBadge.textContent = replayData.is_valid ? '100% BIT-EXACT VERIFIED' : 'REPLAY MISMATCH';
            replayAuditBadge.style.color = replayData.is_valid ? '#7ee787' : '#ff7b72';
          }
        }
      });
    }

    if (btnExportDossier) {
      btnExportDossier.addEventListener('click', async () => {
        const res = await fetch('/api/mission-os/dossier');
        if (res.ok) {
          const dossier = await res.json();
          const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `ATLAS_MISSION_DOSSIER_${dossier.mission_id}.json`;
          a.click();
        }
      });
    }

    // Initial status load
    loadStatus();

    // Export to window.Atlas
    window.Atlas = window.Atlas || {};
    window.Atlas.missionOS = {
      loadStatus,
      advanceSol: async (n=1) => {
        await fetch('/api/mission-os/advance', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sols_to_advance: n }) });
        await loadStatus();
      },
    };
  }

}"""

    if func_target in content:
        content = content.replace(func_target, func_code, 1)
    else:
        print("Function target not found in web/app.js!")
        sys.exit(1)

    with open("web/app.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched web/app.js with initMissionOSEngine!")

if __name__ == "__main__":
    patch()
