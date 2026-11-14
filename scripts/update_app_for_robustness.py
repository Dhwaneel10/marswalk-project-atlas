"""Update web/app.js to integrate Milestone 12E Mission Robustness Lab."""

with open("web/app.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update switchInspectorTab
target_switch = """  function switchInspectorTab(tabId) {
    if (inspectorTabs) {
      inspectorTabs.forEach(t => {
        if (t.dataset.tab === tabId) t.classList.add('active');
        else t.classList.remove('active');
      });
    }
    const panels = { tabMissionControl, tabPlan, tabResults, tabScenarios, tabWorkspaces };
    Object.keys(panels).forEach(k => {
      if (panels[k]) {
        if (k === tabId) panels[k].classList.remove('hidden');
        else panels[k].classList.add('hidden');
      }
    });
    if (inspectorPanel) {
      if (tabId === 'tabMissionControl') {
        inspectorPanel.classList.add('cockpit-mode');
      } else {
        inspectorPanel.classList.remove('cockpit-mode');
      }
    }
  }"""

replacement_switch = """  function switchInspectorTab(tabId) {
    if (inspectorTabs) {
      inspectorTabs.forEach(t => {
        if (t.dataset.tab === tabId) t.classList.add('active');
        else t.classList.remove('active');
      });
    }
    const panels = { tabMissionControl, tabRobustnessLab, tabPlan, tabResults, tabScenarios, tabWorkspaces };
    Object.keys(panels).forEach(k => {
      if (panels[k]) {
        if (k === tabId) panels[k].classList.remove('hidden');
        else panels[k].classList.add('hidden');
      }
    });
    if (inspectorPanel) {
      if (tabId === 'tabMissionControl' || tabId === 'tabRobustnessLab') {
        inspectorPanel.classList.add('cockpit-mode');
      } else {
        inspectorPanel.classList.remove('cockpit-mode');
      }
    }
  }"""

if "tabRobustnessLab," not in code:
    assert target_switch in code, "target_switch not found in app.js"
    code = code.replace(target_switch, replacement_switch, 1)

# 2. Add Robustness Lab Implementation before openOnboarding
target_onboarding = "  function openOnboarding(step = 1) {"

robustness_impl = """  // =========================================================================
  // MILESTONE 12E: ATLAS MISSION ROBUSTNESS LAB & SENSITIVITY ENGINE
  // =========================================================================
  let currentRobustnessReport = null;
  let selectedResilientStrategyId = "strat_baseline";

  // DOM Elements for Robustness Lab
  let tabRobustnessLab = null;
  let tabBtnRobustnessLab = null;
  let btnMcRobustnessLab = null;
  let robCampaignSelect = null;
  let robSuiteSelect = null;
  let btnRunRobustnessBattery = null;
  let robStatusTag = null;
  let robStatusBanner = null;
  let robFeasibilityBadge = null;
  let robEnvelopeRatioText = null;
  let robEnvelopeProgressBar = null;
  let robBottlenecksList = null;
  let robBreakpointsContainer = null;
  let robSensitivityList = null;
  let robVulnCountBadge = null;
  let robVulnerableTargetsContainer = null;
  let robAns1 = null;
  let robAns2 = null;
  let robAns3 = null;
  let robAns4 = null;
  let robAns5 = null;
  let robAns6 = null;
  let robAns7 = null;
  let robStrategiesContainer = null;
  let robRecommendationText = null;
  let btnPromoteResilientStrategy = null;

  function initRobustnessLabElements() {
    tabRobustnessLab = document.getElementById('tabRobustnessLab');
    tabBtnRobustnessLab = document.getElementById('tabBtnRobustnessLab');
    btnMcRobustnessLab = document.getElementById('btnMcRobustnessLab');
    robCampaignSelect = document.getElementById('robCampaignSelect');
    robSuiteSelect = document.getElementById('robSuiteSelect');
    btnRunRobustnessBattery = document.getElementById('btnRunRobustnessBattery');
    robStatusTag = document.getElementById('robStatusTag');
    robStatusBanner = document.getElementById('robStatusBanner');
    robFeasibilityBadge = document.getElementById('robFeasibilityBadge');
    robEnvelopeRatioText = document.getElementById('robEnvelopeRatioText');
    robEnvelopeProgressBar = document.getElementById('robEnvelopeProgressBar');
    robBottlenecksList = document.getElementById('robBottlenecksList');
    robBreakpointsContainer = document.getElementById('robBreakpointsContainer');
    robSensitivityList = document.getElementById('robSensitivityList');
    robVulnCountBadge = document.getElementById('robVulnCountBadge');
    robVulnerableTargetsContainer = document.getElementById('robVulnerableTargetsContainer');
    robAns1 = document.getElementById('robAns1');
    robAns2 = document.getElementById('robAns2');
    robAns3 = document.getElementById('robAns3');
    robAns4 = document.getElementById('robAns4');
    robAns5 = document.getElementById('robAns5');
    robAns6 = document.getElementById('robAns6');
    robAns7 = document.getElementById('robAns7');
    robStrategiesContainer = document.getElementById('robStrategiesContainer');
    robRecommendationText = document.getElementById('robRecommendationText');
    btnPromoteResilientStrategy = document.getElementById('btnPromoteResilientStrategy');
  }

  function initRobustnessLab() {
    initRobustnessLabElements();

    if (tabBtnRobustnessLab) {
      tabBtnRobustnessLab.addEventListener('click', () => {
        switchInspectorTab('tabRobustnessLab');
        syncRobustnessCampaigns();
      });
    }

    if (btnMcRobustnessLab) {
      btnMcRobustnessLab.addEventListener('click', () => {
        switchInspectorTab('tabRobustnessLab');
        syncRobustnessCampaigns();
      });
    }

    if (btnRunRobustnessBattery) {
      btnRunRobustnessBattery.addEventListener('click', () => {
        const suite = robSuiteSelect ? robSuiteSelect.value : 'full_battery';
        const cid = robCampaignSelect ? robCampaignSelect.value : (mcState.selectedCampaignId || null);
        runRobustnessLabEvaluation(suite, cid);
      });
    }

    if (btnPromoteResilientStrategy) {
      btnPromoteResilientStrategy.addEventListener('click', () => {
        promoteSelectedResilientStrategyAction();
      });
    }
  }

  function syncRobustnessCampaigns() {
    if (!robCampaignSelect) return;
    if (mcState.campaigns && mcState.campaigns.length > 0) {
      robCampaignSelect.innerHTML = '';
      mcState.campaigns.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.campaign_id;
        opt.textContent = `${c.name || c.campaign_id} (v${c.version || 1} • ${c.status || 'PLANNED'})`;
        if (c.campaign_id === mcState.selectedCampaignId) {
          opt.selected = true;
        }
        robCampaignSelect.appendChild(opt);
      });
    } else {
      loadMissionControlCampaigns(false).then(() => {
        syncRobustnessCampaigns();
      });
    }
  }

  async function runRobustnessLabEvaluation(suiteType = 'full_battery', targetCampaignId = null) {
    const cid = targetCampaignId || (robCampaignSelect ? robCampaignSelect.value : mcState.selectedCampaignId);

    showRobStatus(`Executing deterministic stress battery (${suiteType})... Grounding in USGS CTX 20m DTM...`, false);
    if (btnRunRobustnessBattery) btnRunRobustnessBattery.disabled = true;
    if (robStatusTag) {
      robStatusTag.textContent = 'EVALUATING';
      robStatusTag.style.background = 'rgba(234, 179, 8, 0.15)';
      robStatusTag.style.color = '#fde047';
      robStatusTag.style.borderColor = 'rgba(234, 179, 8, 0.3)';
    }

    try {
      const payload = {
        suite_type: suiteType,
        campaign_id: cid || undefined
      };
      const resp = await fetch('/api/robustness/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.message || `HTTP ${resp.status}`);
      }

      const report = await resp.json();
      currentRobustnessReport = report;
      selectedResilientStrategyId = report.recommended_strategy_id || 'strat_baseline';

      renderRobustnessReport(report);
      showRobStatus(`Stress Battery Evaluated: ${report.experiment_id} (${report.case_evaluations ? report.case_evaluations.length : 0} scenarios completed in ${report.execution_time_ms || 120}ms)`, true);

      if (robStatusTag) {
        robStatusTag.textContent = 'COMPLETED';
        robStatusTag.style.background = 'rgba(16, 185, 129, 0.15)';
        robStatusTag.style.color = 'var(--status-green)';
        robStatusTag.style.borderColor = 'rgba(16, 185, 129, 0.3)';
      }
    } catch (err) {
      console.error('[RobustnessLab] Evaluation error:', err);
      showRobStatus(`Stress evaluation failed: ${err.message}`, true, true);
      if (robStatusTag) {
        robStatusTag.textContent = 'FAILED';
        robStatusTag.style.background = 'rgba(239, 68, 68, 0.15)';
        robStatusTag.style.color = '#fca5a5';
      }
    } finally {
      if (btnRunRobustnessBattery) btnRunRobustnessBattery.disabled = false;
    }
  }

  function renderRobustnessReport(report) {
    if (!report) return;

    // 1. Feasibility Envelope
    const envelope = report.feasibility_envelope || {};
    const total = envelope.tested_cases_count || 0;
    const feasible = envelope.feasible_cases_count || 0;
    const ratioPct = envelope.tested_feasibility_pct || 0;

    if (robEnvelopeRatioText) {
      robEnvelopeRatioText.textContent = `${feasible} / ${total} cases (${ratioPct.toFixed(0)}%)`;
    }
    if (robEnvelopeProgressBar) {
      robEnvelopeProgressBar.style.width = `${Math.min(100, Math.max(0, ratioPct))}%`;
      if (ratioPct >= 80) {
        robEnvelopeProgressBar.style.background = 'var(--status-green)';
      } else if (ratioPct >= 50) {
        robEnvelopeProgressBar.style.background = 'var(--status-amber)';
      } else {
        robEnvelopeProgressBar.style.background = '#ef4444';
      }
    }
    if (robFeasibilityBadge) {
      if (ratioPct === 100) {
        robFeasibilityBadge.textContent = '100% FEASIBLE';
        robFeasibilityBadge.style.background = 'rgba(16, 185, 129, 0.15)';
        robFeasibilityBadge.style.color = 'var(--status-green)';
      } else if (ratioPct >= 70) {
        robFeasibilityBadge.textContent = `${ratioPct.toFixed(0)}% STABLE`;
        robFeasibilityBadge.style.background = 'rgba(234, 179, 8, 0.15)';
        robFeasibilityBadge.style.color = '#fde047';
      } else {
        robFeasibilityBadge.textContent = `${ratioPct.toFixed(0)}% FRAGILE`;
        robFeasibilityBadge.style.background = 'rgba(239, 68, 68, 0.15)';
        robFeasibilityBadge.style.color = '#fca5a5';
      }
    }

    // Bottlenecks
    if (robBottlenecksList) {
      robBottlenecksList.innerHTML = '';
      const bList = envelope.bottlenecks || [];
      if (bList.length === 0) {
        robBottlenecksList.innerHTML = '<li>No operational bottlenecks identified across tested parameters.</li>';
      } else {
        bList.forEach(b => {
          const li = document.createElement('li');
          li.textContent = b;
          robBottlenecksList.appendChild(li);
        });
      }
    }

    // Breakpoints
    if (robBreakpointsContainer) {
      const bps = envelope.critical_breakpoints || [];
      if (bps.length === 0) {
        robBreakpointsContainer.textContent = 'No failure breakpoints reached in tested envelope.';
      } else {
        robBreakpointsContainer.innerHTML = bps.map(bp =>
          `<div style="padding:2px 4px; background:rgba(239,68,68,0.1); border-left:2px solid #ef4444; margin-bottom:2px;">
            <strong>${bp.parameter_name}:</strong> ${bp.nominal_value} &rarr; ${bp.tested_value} (${bp.status}): ${bp.failure_reason}
          </div>`
        ).join('');
      }
    }

    // 2. Parameter Sensitivity Gradients
    if (robSensitivityList) {
      robSensitivityList.innerHTML = '';
      const sensitivities = report.parameter_sensitivities || [];
      if (sensitivities.length === 0) {
        robSensitivityList.innerHTML = '<div style="font-size:8px; color:var(--text-tertiary); font-style:italic;">No continuous parameters perturbed in this suite.</div>';
      } else {
        const maxElasticity = Math.max(...sensitivities.map(s => s.relative_elasticity || 0), 1.0);
        sensitivities.forEach(s => {
          const row = document.createElement('div');
          row.className = 'rob-sens-row';
          const fillWidth = Math.min(100, Math.max(5, (s.relative_elasticity / maxElasticity) * 100));
          row.innerHTML = `
            <div class="rob-sens-header">
              <span style="color:var(--text-primary); font-weight:700;">#${s.sensitivity_rank || 1} ${s.parameter_name}</span>
              <span style="color:#f87171;">&epsilon; = ${(s.relative_elasticity || 0).toFixed(2)} (${s.dimension || 'param'})</span>
            </div>
            <div class="rob-sens-bar-track">
              <div class="rob-sens-bar-fill" style="width:${fillWidth.toFixed(0)}%;"></div>
            </div>
            <div style="font-size:7.5px; color:var(--text-tertiary); display:flex; justify-content:space-between; margin-top:1px;">
              <span>Gradient: ${(s.sensitivity_duration_s_per_unit || 0) > 0 ? '+' : ''}${(s.sensitivity_duration_s_per_unit || 0).toFixed(1)} s / unit</span>
              <span>Tested: [${(s.tested_range || [0, 0]).join(' &rarr; ')}]</span>
            </div>
          `;
          robSensitivityList.appendChild(row);
        });
      }
    }

    // 3. Vulnerable Objectives & Units
    if (robVulnerableTargetsContainer) {
      robVulnerableTargetsContainer.innerHTML = '';
      const vulns = envelope.vulnerable_targets || [];
      if (robVulnCountBadge) robVulnCountBadge.textContent = `${vulns.length} Vulnerable`;

      if (vulns.length === 0) {
        robVulnerableTargetsContainer.innerHTML = '<div style="font-size:8px; color:var(--status-green); font-style:italic;">All candidate science targets successfully achieved across stress cases.</div>';
      } else {
        vulns.forEach(v => {
          const item = document.createElement('div');
          item.className = 'rob-target-item';
          const badgeColor = v.vulnerability_level === 'HIGH' ? '#ef4444' : (v.vulnerability_level === 'MEDIUM' ? 'var(--status-amber)' : 'var(--telemetry-cyan)');
          item.innerHTML = `
            <div>
              <strong style="color:var(--text-primary);">${v.name || v.target_id}</strong>
              <span style="color:var(--text-tertiary); margin-left:4px;">(${v.target_id})</span>
            </div>
            <div style="display:flex; align-items:center; gap:4px;">
              <span style="font-family:var(--font-mono); color:${badgeColor}; font-weight:700;">Dropped ${v.drop_count}x (${(v.drop_frequency_pct || 0).toFixed(0)}%)</span>
              <span class="wp-badge" style="font-size:7px; color:${badgeColor}; border-color:${badgeColor};">${v.vulnerability_level || 'MED'}</span>
            </div>
          `;
          robVulnerableTargetsContainer.appendChild(item);
        });
      }
    }

    // 4. Seven Core Answers
    const answers = report.answers_to_key_questions || {};
    if (robAns1) robAns1.textContent = answers.most_sensitive_assumptions || '—';
    if (robAns2) robAns2.textContent = answers.infeasibility_conditions || '—';
    if (robAns3) robAns3.textContent = answers.vulnerable_objectives_and_units || '—';
    if (robAns4) robAns4.textContent = answers.performance_spread || '—';
    if (robAns5) robAns5.textContent = answers.maximum_margin_plans || '—';
    if (robAns6) robAns6.textContent = answers.supporting_evidence || '—';
    if (robAns7) robAns7.textContent = answers.unestablished_limits || '—';

    // 5. Strategy Comparisons
    if (robStrategiesContainer) {
      robStrategiesContainer.innerHTML = '';
      const strats = report.strategy_comparisons || [];
      strats.forEach(st => {
        const isRec = st.strategy_id === (report.recommended_strategy_id || 'strat_baseline');
        const card = document.createElement('div');
        card.className = `rob-strat-card ${st.strategy_id === selectedResilientStrategyId ? 'selected' : ''}`;
        card.dataset.strategyId = st.strategy_id;

        const feasPct = ((st.stressed_feasibility_ratio || 0) * 100).toFixed(0);
        const nomSci = ((st.nominal_metrics && st.nominal_metrics.science_score) || 0).toFixed(1);
        const marginStr = formatDuration(st.stressed_min_margin_s || 0);

        card.innerHTML = `
          <div class="rob-strat-header">
            <div>
              <strong style="font-size:9px; color:var(--text-primary);">${st.name}</strong>
              ${isRec ? '<span class="wp-badge" style="background:rgba(16,185,129,0.2); color:var(--status-green); font-size:7px; margin-left:4px;">RECOMMENDED</span>' : ''}
              ${st.pareto_optimal ? '<span class="wp-badge" style="background:rgba(168,85,247,0.15); color:#c084fc; font-size:7px; margin-left:2px;">PARETO</span>' : ''}
            </div>
            <span style="font-family:var(--font-mono); font-size:8.5px; font-weight:700; color:var(--status-green);">${feasPct}% Feasible</span>
          </div>
          <div style="font-size:8px; color:var(--text-secondary); line-height:1.2;">${st.description}</div>
          <div style="display:flex; justify-content:space-between; font-size:7.5px; font-family:var(--font-mono); color:var(--text-tertiary); margin-top:2px;">
            <span>Nominal Sci: <strong style="color:var(--text-primary);">${nomSci} pts</strong></span>
            <span>Min Margin: <strong style="color:var(--telemetry-cyan);">${marginStr}</strong></span>
            <span>Retention: <strong style="color:var(--status-green);">${(st.stressed_science_retention_pct || 0).toFixed(0)}%</strong></span>
          </div>
          <div style="font-size:7.5px; color:var(--text-tertiary); font-style:italic; margin-top:2px; border-top:1px dashed var(--border-subtle); padding-top:2px;">
            ${st.tradeoff_rationale}
          </div>
        `;

        card.addEventListener('click', () => {
          selectedResilientStrategyId = st.strategy_id;
          document.querySelectorAll('.rob-strat-card').forEach(el => el.classList.remove('selected'));
          card.classList.add('selected');
        });

        robStrategiesContainer.appendChild(card);
      });
    }

    if (robRecommendationText) {
      robRecommendationText.textContent = report.recommendation_rationale || 'Recommendation standing by.';
    }
  }

  async function promoteSelectedResilientStrategyAction() {
    if (!currentRobustnessReport) {
      alert("No evaluated robustness experiment available to promote.");
      return;
    }
    const cid = currentRobustnessReport.target_id || (robCampaignSelect ? robCampaignSelect.value : mcState.selectedCampaignId);
    const stratId = selectedResilientStrategyId || currentRobustnessReport.recommended_strategy_id || 'strat_baseline';

    showRobStatus(`Promoting resilient strategy '${stratId}' to official campaign revision...`, false);
    if (btnPromoteResilientStrategy) btnPromoteResilientStrategy.disabled = true;

    try {
      const resp = await fetch('/api/robustness/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign_id: cid,
          candidate_strategy_id: stratId
        })
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.message || `HTTP ${resp.status}`);
      }

      const res = await resp.json();
      showRobStatus(`Strategy promoted successfully! New revision v${res.campaign ? res.campaign.version : 2} saved.`, true);

      await loadMissionControlCampaigns(true);
      if (res.campaign && res.campaign.campaign_id) {
        selectMissionControlCampaign(res.campaign.campaign_id);
      }
    } catch (err) {
      console.error('[RobustnessLab] Promote error:', err);
      showRobStatus(`Promotion failed: ${err.message}`, true, true);
    } finally {
      if (btnPromoteResilientStrategy) btnPromoteResilientStrategy.disabled = false;
    }
  }

  function showRobStatus(msg, autoHide = false, isError = false) {
    if (!robStatusBanner) return;
    robStatusBanner.textContent = msg;
    robStatusBanner.classList.remove('hidden');
    robStatusBanner.style.color = isError ? '#ff1744' : 'var(--telemetry-cyan)';
    robStatusBanner.style.borderColor = isError ? 'rgba(255,23,68,0.4)' : 'var(--border-medium)';

    if (autoHide) {
      setTimeout(() => {
        if (robStatusBanner) robStatusBanner.classList.add('hidden');
      }, 5000);
    }
  }

"""

if "initRobustnessLab()" not in code:
    assert target_onboarding in code, "target_onboarding not found in app.js"
    code = code.replace(target_onboarding, robustness_impl + "\n" + target_onboarding, 1)

# 3. Call initRobustnessLab() in init()
target_init = "    initMissionControl();"
replacement_init = "    initMissionControl();\n    initRobustnessLab();"

if "initRobustnessLab();" not in code:
    assert target_init in code, "target_init not found in app.js"
    code = code.replace(target_init, replacement_init, 1)

# 4. Expose in window.__atlas
target_atlas = "        // Milestone 12C: Route Decision Workbench API"
robustness_atlas = """        // Milestone 12E: Mission Robustness Lab API
        runRobustnessLab: (suite, cid) => runRobustnessLabEvaluation(suite, cid),
        getRobustnessReport: () => currentRobustnessReport,
        promoteResilientStrategy: (stratId) => promoteSelectedResilientStrategyAction(stratId),
        syncRobustnessCampaigns: () => syncRobustnessCampaigns(),
"""

if "runRobustnessLab:" not in code:
    assert target_atlas in code, "target_atlas not found in app.js"
    code = code.replace(target_atlas, robustness_atlas + target_atlas, 1)

with open("web/app.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated web/app.js successfully!")
