"""
scripts/patch_grand_prix_appjs.py
Appends the Grand Prix Strategy Arena client-side engine to web/app.js.
"""

from pathlib import Path

REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
APP_JS_PATH = REPO_ROOT / "web" / "app.js"

with open(APP_JS_PATH, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Startup hook in URL param checking
param_target = "if (params.get('tab') === 'mission_os' || params.get('tab') === 'mission-os' || params.get('tab') === 'tabMissionOS') {"
param_insert = """      if (params.get('tab') === 'grand_prix' || params.get('tab') === 'grand-prix' || params.get('tab') === 'arena' || params.get('tab') === 'tabGrandPrix') {
        switchInspectorTab('tabGrandPrix');
      }\n"""

if "params.get('tab') === 'grand_prix'" not in code and param_target in code:
    code = code.replace(param_target, param_insert + "      " + param_target, 1)

# 2. Add init call in initialization sequence
init_target = "initMissionOSEngine();"
init_insert = """initMissionOSEngine();
        initGrandPrixEngine();"""

if "initGrandPrixEngine();" not in code and init_target in code:
    code = code.replace(init_target, init_insert, 1)

# 3. Append Grand Prix Arena Engine implementation
engine_code = """

  // ===========================================================================
  // MILESTONE 13X: ATLAS MISSION GRAND PRIX & STRATEGY ARENA ENGINE
  // ===========================================================================
  function initGrandPrixEngine() {
    console.log('[GrandPrix] Initializing Grand Prix Strategy Arena Engine...');

    // Header Quick-Launch Button
    const btnHeaderGP = document.getElementById('btnHeaderGrandPrix');
    if (btnHeaderGP) {
      btnHeaderGP.addEventListener('click', () => {
        switchInspectorTab('tabGrandPrix');
      });
    }

    // Sub-tab Navigation
    const navPills = document.querySelectorAll('.gp-nav-pill');
    navPills.forEach(pill => {
      pill.addEventListener('click', () => {
        navPills.forEach(p => {
          p.classList.remove('active');
          p.style.background = 'transparent';
          p.style.color = '#8899a6';
        });
        pill.classList.add('active');
        pill.style.background = '#1f2937';
        pill.style.color = '#fbbf24';

        const targetTabId = pill.getAttribute('data-gptab');
        document.querySelectorAll('.gp-subpanel').forEach(panel => {
          panel.classList.add('hidden');
        });
        const targetPanel = document.getElementById(targetTabId);
        if (targetPanel) {
          targetPanel.classList.remove('hidden');
        }
      });
    });

    // Subtab 1: Standings & Tournament Runner
    const btnRunTournament = document.getElementById('btnRunGrandPrixTournament');
    if (btnRunTournament) {
      btnRunTournament.addEventListener('click', async () => {
        btnRunTournament.disabled = true;
        btnRunTournament.textContent = 'Simulating...';
        await loadTournamentStandings(true);
        btnRunTournament.disabled = false;
        btnRunTournament.textContent = '\u25B6 Run Tournament';
      });
    }

    async function loadTournamentStandings(forceRun = false) {
      try {
        const url = forceRun ? '/api/grand-prix/tournament/run' : '/api/grand-prix/tournament/summary';
        const res = await fetch(url);
        if (!res.ok) return;
        const payload = await res.json();
        const dossier = payload.dossier;
        if (!dossier) return;

        // Update Champions Banner
        const champs = dossier.champions || {};
        if (champs.science_champion) {
          const el = document.getElementById('gpScienceChampionName');
          if (el) el.textContent = champs.science_champion.strategy_id;
          const sc = document.getElementById('gpScienceChampionScore');
          if (sc) sc.textContent = `${champs.science_champion.score.toFixed(2)} Raw Science Pts`;
        }
        if (champs.efficiency_champion) {
          const el = document.getElementById('gpEfficiencyChampionName');
          if (el) el.textContent = champs.efficiency_champion.strategy_id;
          const sc = document.getElementById('gpEfficiencyChampionScore');
          if (sc) sc.textContent = `${champs.efficiency_champion.score_kwh.toFixed(1)} kWh Consumed`;
        }
        if (champs.robustness_champion) {
          const el = document.getElementById('gpRobustnessChampionName');
          if (el) el.textContent = champs.robustness_champion.strategy_id;
          const sc = document.getElementById('gpRobustnessChampionScore');
          if (sc) sc.textContent = `${champs.robustness_champion.feasibility_pct}% Feas \u2022 CVaR ${champs.robustness_champion.cvar05.toFixed(1)}`;
        }
        if (champs.overall_grand_prix_champion) {
          const el = document.getElementById('gpOverallChampionName');
          if (el) el.textContent = champs.overall_grand_prix_champion.strategy_id;
          const sc = document.getElementById('gpOverallChampionScore');
          if (sc) sc.textContent = `${champs.overall_grand_prix_champion.composite_mean.toFixed(1)} Composite Index`;
        }

        // Leaderboard Table
        const tbody = document.getElementById('gpLeaderboardTableBody');
        if (tbody && dossier.overall_strategy_standings) {
          tbody.innerHTML = '';
          const standings = dossier.overall_strategy_standings;
          for (const [stratId, stat] of Object.entries(standings)) {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid #161b22';
            tr.innerHTML = `
              <td style="padding:4px 3px;"><strong style="color:#fff;">${stratId}</strong></td>
              <td style="padding:4px 3px; color:#8899a6;">${stratId.includes('ATLAS') ? 'INTEGRATED' : (stratId.includes('SCIENCE') ? 'BAYESIAN' : (stratId.includes('PARETO') ? 'NSGA-II' : 'HEURISTIC'))}</td>
              <td style="padding:4px 3px; color:#00e5ff;">${stat.science ? stat.science.mean.toFixed(2) : '-'}</td>
              <td style="padding:4px 3px; color:#00e676;">${stat.energy_kwh ? stat.energy_kwh.mean.toFixed(1) : '-'}</td>
              <td style="padding:4px 3px; color:${stat.feasibility_rate_pct >= 90 ? '#7ee787' : '#ff7b72'};">${stat.feasibility_rate_pct}%</td>
              <td style="padding:4px 3px; font-weight:700; color:#fbbf24;">${stat.composite_score ? stat.composite_score.mean.toFixed(1) : '-'}</td>
              <td style="padding:4px 3px; color:#8899a6;">${stat.composite_score ? stat.composite_score.cvar_05.toFixed(1) : '-'}</td>
            `;
            tbody.appendChild(tr);
          }
        }
      } catch (err) {
        console.error('[GrandPrix] Failed to load tournament standings:', err);
      }
    }

    // Subtab 2: Head-to-Head Compare
    const btnCompare = document.getElementById('btnRunHeadToHeadCompare');
    if (btnCompare) {
      btnCompare.addEventListener('click', async () => {
        const stratA = document.getElementById('gpSelectStratA').value;
        const stratB = document.getElementById('gpSelectStratB').value;
        const seed = document.getElementById('gpInputCompareSeed').value || '1010';

        try {
          const res = await fetch(`/api/grand-prix/compare?strat_a=${stratA}&strat_b=${stratB}&seed=${seed}`);
          if (!res.ok) return;
          const data = await res.json();
          const comp = data.comparison;
          if (!comp) return;

          const vText = document.getElementById('gpCompareVerdictText');
          if (vText && comp.verdict) {
            vText.innerHTML = `
              <div>Scenario: <strong>${comp.scenario_id}</strong> (Seed ${comp.seed})</div>
              <div>Science Winner: <strong style="color:#00e5ff;">${comp.verdict.science_winner}</strong> (${comp.strategy_a.evaluation.science.science_score} vs ${comp.strategy_b.evaluation.science.science_score})</div>
              <div>Efficiency Winner: <strong style="color:#00e676;">${comp.verdict.efficiency_winner}</strong> (${comp.strategy_a.evaluation.resources.energy_consumed_kwh} kWh vs ${comp.strategy_b.evaluation.resources.energy_consumed_kwh} kWh)</div>
              <div>Overall Composite Winner: <strong style="color:#fbbf24;">${comp.verdict.composite_winner}</strong></div>
            `;
          }

          const tbody = document.getElementById('gpCompareStepTableBody');
          if (tbody && comp.step_comparisons) {
            tbody.innerHTML = '';
            comp.step_comparisons.forEach(step => {
              const tr = document.createElement('tr');
              tr.style.borderBottom = '1px solid #161b22';
              tr.innerHTML = `
                <td style="padding:2px 3px; color:#fff;">${step.step}</td>
                <td style="padding:2px 3px; color:#c9d1d9;">${step.strategy_a_task}</td>
                <td style="padding:2px 3px; color:#c9d1d9;">${step.strategy_b_task}</td>
                <td style="padding:2px 3px; color:#8899a6;">${step.divergence}</td>
              `;
              tbody.appendChild(tr);
            });
          }
        } catch (err) {
          console.error('[GrandPrix] Compare failed:', err);
        }
      });
    }

    // Subtab 3: Scenario Explorer
    const btnFetchScenarios = document.getElementById('btnFetchScenariosList');
    if (btnFetchScenarios) {
      btnFetchScenarios.addEventListener('click', async () => {
        const part = document.getElementById('gpSelectScenarioPartition').value;
        try {
          const res = await fetch(`/api/grand-prix/scenarios?partition=${part}&count=4`);
          if (!res.ok) return;
          const data = await res.json();
          const cont = document.getElementById('gpScenarioListContainer');
          if (cont && data.scenarios) {
            cont.innerHTML = data.scenarios.map(sc => `
              <div style="background:#09101a; border:1px solid #1e293b; border-radius:3px; padding:6px; margin-bottom:4px;">
                <div style="display:flex; justify-content:space-between;">
                  <strong style="color:#00e5ff;">${sc.scenario_id} (Seed ${sc.seed})</strong>
                  <span style="color:#8899a6;">Dur: ${sc.duration_sols} Sols &bull; ${sc.is_synthetic_terrain ? 'Synthetic Scarp' : 'USGS 20m CTX'}</span>
                </div>
                <div style="color:#8899a6; font-size:8px; margin-top:2px;">
                  Temp: ${sc.environmental_params.temp_min_k}K - ${sc.environmental_params.temp_max_k}K &bull; Dust Tau: ${sc.environmental_params.dust_optical_depth_tau} &bull; OWLT: ${sc.comms_params.owlt_minutes}m &bull; Targets: ${sc.science_targets_count} &bull; Faults: ${sc.injected_faults_count}
                </div>
              </div>
            `).join('');
          }
        } catch (err) {
          console.error('[GrandPrix] Failed to fetch scenarios:', err);
        }
      });
    }

    // Subtab 4: Sensitivity Lab
    const btnSensDust = document.getElementById('btnSensDust');
    const btnSensEnergy = document.getElementById('btnSensEnergy');

    async function loadSensitivityParam(paramName) {
      try {
        const res = await fetch(`/api/grand-prix/sensitivity?param=${paramName}&seed=1050`);
        if (!res.ok) return;
        const data = await res.json();
        const rep = data.report;
        const cont = document.getElementById('gpSensitivityChartContent');
        if (cont && rep) {
          let rowsHtml = '';
          for (const [stratId, curve] of Object.entries(rep.strategy_curves || {})) {
            const cliff = rep.infeasibility_thresholds[stratId];
            const cliffText = cliff !== null ? `<span style="color:#ff7b72;">Cliff at ${cliff} ${rep.unit}</span>` : `<span style="color:#7ee787;">Always Feasible</span>`;
            const pts = curve.map(pt => `${pt.tau !== undefined ? pt.tau : pt.battery_capacity_kwh}: score ${pt.composite_score}`).join(' | ');
            rowsHtml += `
              <div style="margin-bottom:4px; border-bottom:1px solid #161b22; padding-bottom:3px;">
                <div style="display:flex; justify-content:space-between;">
                  <strong style="color:#fff;">${stratId}</strong>
                  ${cliffText}
                </div>
                <div style="color:#8899a6; font-size:7.5px;">${pts}</div>
              </div>
            `;
          }
          cont.innerHTML = `
            <div style="font-weight:700; color:#fbbf24; margin-bottom:4px;">${rep.parameter_name} Sweep [${rep.parameter_range.join(', ')}] ${rep.unit}</div>
            <div>${rowsHtml}</div>
          `;
        }
      } catch (err) {
        console.error('[GrandPrix] Sensitivity load failed:', err);
      }
    }

    if (btnSensDust && btnSensEnergy) {
      btnSensDust.addEventListener('click', () => {
        btnSensDust.classList.add('active');
        btnSensEnergy.classList.remove('active');
        loadSensitivityParam('dust');
      });
      btnSensEnergy.addEventListener('click', () => {
        btnSensEnergy.classList.add('active');
        btnSensDust.classList.remove('active');
        loadSensitivityParam('energy');
      });
    }

    // Export Dossier Button
    const btnExport = document.getElementById('btnExportGrandPrixDossier');
    if (btnExport) {
      btnExport.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/grand-prix/tournament/summary');
          if (res.ok) {
            const data = await res.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `atlas_grand_prix_championship_dossier.json`;
            a.click();
            URL.revokeObjectURL(url);
          }
        } catch (err) {
          console.error('[GrandPrix] Export failed:', err);
        }
      });
    }

    // Initial load
    loadTournamentStandings(false);
  }
"""

code = code.rstrip()
if "initGrandPrixEngine" not in code:
    if code.endswith("}"):
        # Insert before final closing brace of enclosing block
        idx = code.rfind("}")
        code = code[:idx] + engine_code + "\n}\n"
    else:
        code = code + engine_code

with open(APP_JS_PATH, "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully injected Grand Prix client-side logic into web/app.js")
