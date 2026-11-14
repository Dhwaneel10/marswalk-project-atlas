"""
Update web/app.js to integrate Milestone 12F Autonomous Mission Rehearsal Director.
"""

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

replacement_switch = """  function switchInspectorTab(tabId) {
    if (inspectorTabs) {
      inspectorTabs.forEach(t => {
        if (t.dataset.tab === tabId) t.classList.add('active');
        else t.classList.remove('active');
      });
    }
    const panels = { tabMissionControl, tabRobustnessLab, tabRehearsalDirector, tabPlan, tabResults, tabScenarios, tabWorkspaces };
    Object.keys(panels).forEach(k => {
      if (panels[k]) {
        if (k === tabId) panels[k].classList.remove('hidden');
        else panels[k].classList.add('hidden');
      }
    });
    if (inspectorPanel) {
      if (tabId === 'tabMissionControl' || tabId === 'tabRobustnessLab' || tabId === 'tabRehearsalDirector') {
        inspectorPanel.classList.add('cockpit-mode');
      } else {
        inspectorPanel.classList.remove('cockpit-mode');
      }
    }
  }"""

if "tabRehearsalDirector," not in code:
    assert target_switch in code, "target_switch not found in app.js"
    code = code.replace(target_switch, replacement_switch, 1)

# 2. Add Rehearsal Director implementation before openOnboarding
target_onboarding = "  function openOnboarding(step = 1) {"

rehearsal_impl = """  // =========================================================================
  // MILESTONE 12F: AUTONOMOUS MISSION REHEARSAL DIRECTOR
  // =========================================================================
  let currentRehearsalRecord = null;

  // DOM Elements for Rehearsal Director
  let tabRehearsalDirector = null;
  let tabBtnRehearsalDirector = null;
  let btnHeaderRehearsalDirector = null;
  let btnMcRehearsalDirector = null;
  let rehCampaignSelect = null;
  let rehPolicySelect = null;
  let rehMarginThreshold = null;
  let rehDisturbanceType = null;
  let rehTriggerTimeInput = null;
  let rehDisturbanceParamDesc = null;
  let btnExecuteRehearsal = null;
  let btnResetRehearsal = null;
  let rehStatusTag = null;
  let rehStatusBanner = null;

  // Comparison HUD elements
  let rehComparisonCard = null;
  let rehOutcomeBadge = null;
  let rehExecutiveAssessmentText = null;
  let rehSciencePreservedVal = null;
  let rehNetScienceDeltaVal = null;
  let rehRecoveredMarginVal = null;
  let rehDelayIncurredVal = null;
  let rehTargetsRetainedVal = null;
  let rehRecoveryEfficiencyVal = null;

  // Track summaries and progress bars
  let rehTrackBaselineSummary = null;
  let rehTrackDisturbedSummary = null;
  let rehTrackRecoveredSummary = null;
  let rehBarBaseline = null;
  let rehBarDisturbed = null;
  let rehBarRecovered = null;

  let rehCandidatesContainer = null;
  let rehCausalLedgerContainer = null;
  let btnExportRehearsalPack = null;
  let btnReplayRehearsal = null;

  function initRehearsalDirector() {
    tabRehearsalDirector = document.getElementById('tabRehearsalDirector');
    tabBtnRehearsalDirector = document.getElementById('tabBtnRehearsalDirector');
    btnHeaderRehearsalDirector = document.getElementById('btnHeaderRehearsalDirector');
    btnMcRehearsalDirector = document.getElementById('btnMcRehearsalDirector');
    rehCampaignSelect = document.getElementById('rehCampaignSelect');
    rehPolicySelect = document.getElementById('rehPolicySelect');
    rehMarginThreshold = document.getElementById('rehMarginThreshold');
    rehDisturbanceType = document.getElementById('rehDisturbanceType');
    rehTriggerTimeInput = document.getElementById('rehTriggerTimeInput');
    rehDisturbanceParamDesc = document.getElementById('rehDisturbanceParamDesc');
    btnExecuteRehearsal = document.getElementById('btnExecuteRehearsal');
    btnResetRehearsal = document.getElementById('btnResetRehearsal');
    rehStatusTag = document.getElementById('rehStatusTag');
    rehStatusBanner = document.getElementById('rehStatusBanner');

    rehComparisonCard = document.getElementById('rehComparisonCard');
    rehOutcomeBadge = document.getElementById('rehOutcomeBadge');
    rehExecutiveAssessmentText = document.getElementById('rehExecutiveAssessmentText');
    rehSciencePreservedVal = document.getElementById('rehSciencePreservedVal');
    rehNetScienceDeltaVal = document.getElementById('rehNetScienceDeltaVal');
    rehRecoveredMarginVal = document.getElementById('rehRecoveredMarginVal');
    rehDelayIncurredVal = document.getElementById('rehDelayIncurredVal');
    rehTargetsRetainedVal = document.getElementById('rehTargetsRetainedVal');
    rehRecoveryEfficiencyVal = document.getElementById('rehRecoveryEfficiencyVal');

    rehTrackBaselineSummary = document.getElementById('rehTrackBaselineSummary');
    rehTrackDisturbedSummary = document.getElementById('rehTrackDisturbedSummary');
    rehTrackRecoveredSummary = document.getElementById('rehTrackRecoveredSummary');
    rehBarBaseline = document.getElementById('rehBarBaseline');
    rehBarDisturbed = document.getElementById('rehBarDisturbed');
    rehBarRecovered = document.getElementById('rehBarRecovered');

    rehCandidatesContainer = document.getElementById('rehCandidatesContainer');
    rehCausalLedgerContainer = document.getElementById('rehCausalLedgerContainer');
    btnExportRehearsalPack = document.getElementById('btnExportRehearsalPack');
    btnReplayRehearsal = document.getElementById('btnReplayRehearsal');

    // Tab buttons
    if (tabBtnRehearsalDirector) {
      tabBtnRehearsalDirector.addEventListener('click', () => {
        switchInspectorTab('tabRehearsalDirector');
        syncRehearsalCampaigns();
      });
    }

    if (btnHeaderRehearsalDirector) {
      btnHeaderRehearsalDirector.addEventListener('click', () => {
        enterWorkstation();
        switchInspectorTab('tabRehearsalDirector');
        syncRehearsalCampaigns();
      });
    }

    if (btnMcRehearsalDirector) {
      btnMcRehearsalDirector.addEventListener('click', () => {
        switchInspectorTab('tabRehearsalDirector');
        syncRehearsalCampaigns();
      });
    }

    if (rehDisturbanceType) {
      rehDisturbanceType.addEventListener('change', updateRehearsalDisturbanceDesc);
    }

    if (btnExecuteRehearsal) {
      btnExecuteRehearsal.addEventListener('click', () => executeRehearsalAction());
    }

    if (btnResetRehearsal) {
      btnResetRehearsal.addEventListener('click', resetRehearsalControls);
    }

    if (btnExportRehearsalPack) {
      btnExportRehearsalPack.addEventListener('click', exportRehearsalPack);
    }

    if (btnReplayRehearsal) {
      btnReplayRehearsal.addEventListener('click', replayRehearsalSequence);
    }

    updateRehearsalDisturbanceDesc();
  }

  function updateRehearsalDisturbanceDesc() {
    if (!rehDisturbanceType || !rehDisturbanceParamDesc) return;
    const dtype = rehDisturbanceType.value;
    const trig = rehTriggerTimeInput ? rehTriggerTimeInput.value : '3600';

    if (dtype === 'operational_delay') {
      rehDisturbanceParamDesc.textContent = `Injects +1800s sampling hold or comms blackout at T+${trig}s. Reduces available EVA return margin.`;
    } else if (dtype === 'corridor_closure') {
      rehDisturbanceParamDesc.textContent = `Blocks a 50m radius corridor around traverse route at T+${trig}s. Forces detour or shedding.`;
    } else if (dtype === 'mobility_derating') {
      rehDisturbanceParamDesc.textContent = `Derates mobility to 0.70x speed (drift sand / traction slip) at T+${trig}s. Transit durations increase by ~43%.`;
    } else if (dtype === 'target_unavailability') {
      rehDisturbanceParamDesc.textContent = `Invalidates active scientific waypoint at T+${trig}s due to discovered hazard or unsuitability.`;
    } else if (dtype === 'unit_dropout') {
      rehDisturbanceParamDesc.textContent = `Exploration unit suffers disabling fault at T+${trig}s. Triggers autonomous multi-unit cross-asset handoff.`;
    }
  }

  async function syncRehearsalCampaigns() {
    if (!rehCampaignSelect) return;
    try {
      const resp = await fetch('/api/campaigns');
      if (!resp.ok) return;
      const data = await resp.json();
      const camps = data.campaigns || [];
      if (!camps.length) return;

      const currentVal = rehCampaignSelect.value;
      rehCampaignSelect.innerHTML = '';
      camps.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.campaign_id;
        opt.textContent = `${c.name || c.campaign_id} (${c.sorties ? c.sorties.length : 1} sols, v${c.version || 1})`;
        rehCampaignSelect.appendChild(opt);
      });

      if (currentVal && Array.from(rehCampaignSelect.options).some(o => o.value === currentVal)) {
        rehCampaignSelect.value = currentVal;
      } else if (mcState && mcState.selectedCampaignId) {
        rehCampaignSelect.value = mcState.selectedCampaignId;
      }
    } catch (err) {
      console.warn('[RehearsalDirector] Failed to sync campaigns:', err);
    }
  }

  function resetRehearsalControls() {
    if (rehPolicySelect) rehPolicySelect.value = 'balanced';
    if (rehMarginThreshold) rehMarginThreshold.value = '1800';
    if (rehDisturbanceType) rehDisturbanceType.value = 'operational_delay';
    if (rehTriggerTimeInput) rehTriggerTimeInput.value = '3600';
    updateRehearsalDisturbanceDesc();
    if (rehComparisonCard) rehComparisonCard.style.display = 'none';
    if (rehStatusTag) {
      rehStatusTag.textContent = 'READY';
      rehStatusTag.style.background = 'rgba(124,58,237,0.15)';
      rehStatusTag.style.color = '#c4b5fd';
    }
  }

  async function executeRehearsalAction(overridePayload = null) {
    const cid = (overridePayload && overridePayload.campaign_id) || (rehCampaignSelect ? rehCampaignSelect.value : (mcState ? mcState.selectedCampaignId : null));
    if (!cid) {
      alert("Please select a baseline exploration campaign first.");
      return;
    }

    const dtype = (overridePayload && overridePayload.disturbance_type) || (rehDisturbanceType ? rehDisturbanceType.value : 'operational_delay');
    const triggerTime = overridePayload ? (overridePayload.trigger_time_s || 3600.0) : parseFloat((rehTriggerTimeInput && rehTriggerTimeInput.value) || '3600');
    const policy = (overridePayload && overridePayload.policy_type) || (rehPolicySelect ? rehPolicySelect.value : 'balanced');
    const minMargin = overridePayload ? (overridePayload.min_margin_threshold_s || 1800.0) : parseFloat((rehMarginThreshold && rehMarginThreshold.value) || '1800');

    let distParams = {};
    if (dtype === 'operational_delay') {
      distParams = { delay_s: 1800.0 };
    } else if (dtype === 'corridor_closure') {
      distParams = { center_rc: [115, 155], radius_m: 50.0 };
    } else if (dtype === 'mobility_derating') {
      distParams = { speed_factor: 0.7 };
    } else if (dtype === 'target_unavailability') {
      distParams = { target_id: 'tgt_001', reason: 'Hazardous boulder field identified' };
    } else if (dtype === 'unit_dropout') {
      distParams = { affected_unit_id: 'unit_scout_1', reason: 'Power subsystem brownout' };
    }

    if (overridePayload && overridePayload.disturbances) {
      // allow full array of disturbances
    }

    const payload = overridePayload || {
      campaign_id: cid,
      title: `Rehearsal: ${dtype.replace('_', ' ').toUpperCase()}`,
      disturbances: [
        {
          disturbance_id: `dst_${Date.now().toString(36)}`,
          disturbance_type: dtype,
          trigger_time_s: triggerTime,
          parameters: distParams,
          description: `Scheduled operational ${dtype.replace('_', ' ')}`
        }
      ],
      recovery_policy: {
        policy_type: policy,
        min_margin_threshold_s: minMargin
      }
    };

    showRehStatus(`Executing closed-loop rehearsal simulation for campaign '${cid}'...`, false);
    if (btnExecuteRehearsal) btnExecuteRehearsal.disabled = true;

    try {
      const resp = await fetch('/api/rehearsal/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.message || `HTTP ${resp.status}`);
      }

      const res = await resp.json();
      currentRehearsalRecord = res.rehearsal;
      renderRehearsalComparison(currentRehearsalRecord);
      showRehStatus(`Rehearsal completed successfully (${currentRehearsalRecord.outcome_status}) in ${currentRehearsalRecord.execution_duration_ms}ms.`, true);

      return currentRehearsalRecord;
    } catch (err) {
      console.error('[RehearsalDirector] Execution error:', err);
      showRehStatus(`Rehearsal failed: ${err.message}`, true, true);
    } finally {
      if (btnExecuteRehearsal) btnExecuteRehearsal.disabled = false;
    }
  }

  function renderRehearsalComparison(record) {
    if (!record || !rehComparisonCard) return;

    rehComparisonCard.style.display = 'block';

    // Outcome Badge
    if (rehOutcomeBadge) {
      rehOutcomeBadge.textContent = record.outcome_status;
      if (record.outcome_status === 'RECOVERED') {
        rehOutcomeBadge.style.background = 'rgba(16,185,129,0.15)';
        rehOutcomeBadge.style.color = 'var(--status-green)';
        rehOutcomeBadge.style.borderColor = 'rgba(16,185,129,0.3)';
      } else if (record.outcome_status === 'RECOVERED_WITH_DEGRADATION') {
        rehOutcomeBadge.style.background = 'rgba(245,158,11,0.15)';
        rehOutcomeBadge.style.color = '#fbbf24';
        rehOutcomeBadge.style.borderColor = 'rgba(245,158,11,0.3)';
      } else {
        rehOutcomeBadge.style.background = 'rgba(239,68,68,0.15)';
        rehOutcomeBadge.style.color = '#f87171';
        rehOutcomeBadge.style.borderColor = 'rgba(239,68,68,0.3)';
      }
    }

    if (rehStatusTag) {
      rehStatusTag.textContent = record.outcome_status;
      rehStatusTag.style.color = rehOutcomeBadge.style.color;
      rehStatusTag.style.background = rehOutcomeBadge.style.background;
    }

    const comp = record.comparison || {};
    const baseM = record.baseline_metrics || {};
    const distM = record.disturbed_metrics || {};
    const recM = record.recovered_metrics || {};

    if (rehExecutiveAssessmentText) {
      rehExecutiveAssessmentText.textContent = comp.executive_assessment || 'Assessment completed.';
    }

    if (rehSciencePreservedVal) {
      rehSciencePreservedVal.textContent = `${comp.science_preservation_pct || 0}%`;
    }
    if (rehNetScienceDeltaVal) {
      const net = comp.net_science_delta || 0;
      rehNetScienceDeltaVal.textContent = `${net >= 0 ? '+' : ''}${net.toFixed(1)} pts`;
      rehNetScienceDeltaVal.style.color = net < 0 ? '#fbbf24' : 'var(--text-primary)';
    }
    if (rehRecoveredMarginVal) {
      rehRecoveredMarginVal.textContent = formatDuration(recM.min_margin_s || 0);
    }
    if (rehDelayIncurredVal) {
      const dly = comp.delay_incurred_s || 0;
      rehDelayIncurredVal.textContent = `${dly >= 0 ? '+' : ''}${formatDuration(Math.abs(dly))}`;
    }
    if (rehTargetsRetainedVal) {
      rehTargetsRetainedVal.textContent = `${recM.targets_completed || 0} / ${baseM.targets_attempted || 0}`;
    }
    if (rehRecoveryEfficiencyVal) {
      rehRecoveryEfficiencyVal.textContent = `${comp.recovery_efficiency_pct || 100}%`;
    }

    // Trajectory summaries & progress bars
    if (rehTrackBaselineSummary) {
      rehTrackBaselineSummary.textContent = `${baseM.science_score || 0} pts • Margin: ${formatDuration(baseM.min_margin_s || 0)}`;
    }
    if (rehTrackDisturbedSummary) {
      rehTrackDisturbedSummary.textContent = `${distM.science_score || 0} pts • ${distM.violations && distM.violations.length ? distM.violations.length + ' Violations' : 'Depleted'}`;
    }
    if (rehTrackRecoveredSummary) {
      rehTrackRecoveredSummary.textContent = `${recM.science_score || 0} pts • Margin: ${formatDuration(recM.min_margin_s || 0)}`;
    }

    if (rehBarBaseline) rehBarBaseline.style.width = '100%';
    if (rehBarDisturbed) {
      const distPct = Math.max(10, Math.min(100, ((distM.science_score || 0) / Math.max(1, baseM.science_score || 1)) * 100));
      rehBarDisturbed.style.width = `${distPct}%`;
    }
    if (rehBarRecovered) {
      const recPct = Math.max(10, Math.min(100, comp.science_preservation_pct || 0));
      rehBarRecovered.style.width = `${recPct}%`;
    }

    // Render candidate options
    if (rehCandidatesContainer) {
      rehCandidatesContainer.innerHTML = '';
      const cands = record.recovery_candidates || [];
      cands.forEach(c => {
        const card = document.createElement('div');
        const isSel = c.selection_status === 'SELECTED';
        const isInf = !c.is_feasible;
        card.style.padding = '5px 8px';
        card.style.borderRadius = '4px';
        card.style.fontSize = '8px';
        card.style.lineHeight = '1.25';
        card.style.border = `1px solid ${isSel ? 'rgba(168,85,247,0.4)' : (isInf ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.08)')}`;
        card.style.background = isSel ? 'rgba(168,85,247,0.1)' : 'rgba(0,0,0,0.2)';
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
            <strong style="color:${isSel ? '#c084fc' : (isInf ? '#fca5a5' : 'var(--text-primary)')}; font-size:8.5px;">${c.title}</strong>
            <span class="wp-badge" style="font-size:7px; background:${isSel ? 'rgba(168,85,247,0.2)' : 'rgba(255,255,255,0.06)'}; color:${isSel ? '#c084fc' : 'var(--text-tertiary)'};">${c.selection_status}</span>
          </div>
          <div style="display:flex; gap:10px; font-family:var(--font-mono); color:var(--text-secondary); margin-bottom:2px;">
            <span>Sci: <strong>${c.projected_science_score} pts</strong></span>
            <span>Margin: <strong>${formatDuration(c.projected_margin_s)}</strong></span>
            <span>Targets: <strong>${c.projected_targets_completed}</strong></span>
          </div>
          <div style="color:var(--text-tertiary); font-style:italic;">${c.decision_rationale}</div>
        `;
        rehCandidatesContainer.appendChild(card);
      });
    }

    // Render Causal Ledger
    if (rehCausalLedgerContainer) {
      rehCausalLedgerContainer.innerHTML = '';
      const steps = record.causal_ledger || [];
      steps.forEach(s => {
        const item = document.createElement('div');
        item.style.padding = '4px 6px';
        item.style.borderRadius = '3px';
        item.style.fontSize = '8px';
        item.style.background = 'rgba(255,255,255,0.02)';
        item.style.borderLeft = `2px solid ${s.step_type === 'SELECTION_DECISION' ? '#a855f7' : (s.step_type === 'DISTURBANCE_TRIGGER' ? '#ef4444' : 'var(--telemetry-cyan)')}`;
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; margin-bottom:1px;">
            <strong style="color:var(--text-primary); font-size:8.5px;">Step ${s.step_index}: ${s.title}</strong>
            <span style="font-family:var(--font-mono); color:var(--text-tertiary); font-size:7.5px;">T+${s.simulated_time_s}s</span>
          </div>
          <div style="color:var(--text-secondary); line-height:1.2;">${s.description}</div>
        `;
        rehCausalLedgerContainer.appendChild(item);
      });
    }
  }

  function exportRehearsalPack() {
    if (!currentRehearsalRecord) {
      alert("No completed rehearsal record available to export.");
      return;
    }
    const jsonStr = JSON.stringify(currentRehearsalRecord, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentRehearsalRecord.rehearsal_id}_decision_pack.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function replayRehearsalSequence() {
    if (!currentRehearsalRecord || !rehCausalLedgerContainer) return;
    const items = rehCausalLedgerContainer.children;
    if (!items.length) return;

    let idx = 0;
    const interval = setInterval(() => {
      Array.from(items).forEach((el, i) => {
        if (i === idx) {
          el.style.background = 'rgba(168,85,247,0.2)';
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
          el.style.background = 'rgba(255,255,255,0.02)';
        }
      });
      idx++;
      if (idx >= items.length) {
        clearInterval(interval);
      }
    }, 600);
  }

  function showRehStatus(msg, autoHide = false, isError = false) {
    if (!rehStatusBanner) return;
    rehStatusBanner.textContent = msg;
    rehStatusBanner.classList.remove('hidden');
    rehStatusBanner.style.color = isError ? '#ff1744' : '#c4b5fd';
    rehStatusBanner.style.borderColor = isError ? 'rgba(255,23,68,0.4)' : 'rgba(124,58,237,0.3)';

    if (autoHide) {
      setTimeout(() => {
        if (rehStatusBanner) rehStatusBanner.classList.add('hidden');
      }, 5000);
    }
  }

"""

if "initRehearsalDirector()" not in code:
    assert target_onboarding in code, "target_onboarding not found in app.js"
    code = code.replace(target_onboarding, rehearsal_impl + "\n" + target_onboarding, 1)

# 3. Call initRehearsalDirector() in init()
target_init = "    initRobustnessLab();"
replacement_init = "    initRobustnessLab();\n    initRehearsalDirector();"

if "initRehearsalDirector();" not in code:
    assert target_init in code, "target_init not found in app.js"
    code = code.replace(target_init, replacement_init, 1)

# 4. Expose in window.__atlas and window.MarsWalk
target_atlas = "        // Milestone 12E: Mission Robustness Lab API"
rehearsal_atlas = """        // Milestone 12F: Mission Rehearsal Director API
        executeRehearsal: (payload) => executeRehearsalAction(payload),
        getRehearsal: () => currentRehearsalRecord,
        listRehearsals: (cid) => fetch('/api/rehearsal/list' + (cid ? '?campaign_id=' + cid : '')).then(r => r.json()),
        getRehearsalDisturbances: () => fetch('/api/rehearsal/disturbances').then(r => r.json()),
        syncRehearsalCampaigns: () => syncRehearsalCampaigns(),
"""

if "executeRehearsal:" not in code:
    assert target_atlas in code, "target_atlas not found in app.js"
    code = code.replace(target_atlas, rehearsal_atlas + target_atlas, 1)

with open("web/app.js", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated web/app.js successfully for Milestone 12F!")
