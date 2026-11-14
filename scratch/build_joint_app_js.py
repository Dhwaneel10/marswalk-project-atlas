# Build Milestone 13E JavaScript code to integrate into web/app.js

def get_joint_js():
    return '''
// ==============================================================================
// Milestone 13E: Atlas Joint Mission Co-Design Studio & 3D Theater Integration
// ==============================================================================

let jointMissionTraverseGroup = null;
let jointCandidatesGroup = null;
let jointSelectedRouteGroup = null;
let jointGapsGroup = null;
let jointMissionOptimizationResult = null;
let jointSelectedCandidateId = null;
let currentJointWizardStep = 1;
let jointMissionDrawerVisible = true;

// DOM Element Handles
let tabBtnJointMissionStudio = null;
let tabJointMissionStudio = null;
let btnToggleJointStudio = null;
let jointMissionStudioPanel = null;
let btnCloseJointStudioPanel = null;
let paretoScatterCanvas = null;
let paretoCanvasTooltip = null;
let paretoScorecardTable = null;
let paretoScorecardBody = null;
let btnRunJointOptimization = null;
let btnTheaterRunJointOptimize = null;
let btnPromoteJointPlan = null;
let btnTheaterPromoteJoint = null;
let btnExportJointJson = null;
let btnExportJointMd = null;
let jointTheaterCandidateSelect = null;

function initJointMissionStudio() {
  initJointMissionTheaterGroup();
  bindJointStudioElements();
  setupJointStudioListeners();
  console.log('[JointMissionStudio] Initialized Joint Mission Co-Design Studio.');
}

function initJointMissionTheaterGroup() {
  if (!jezeroSurfaceGroup) return;
  if (!jointMissionTraverseGroup) {
    jointMissionTraverseGroup = new THREE.Group();
    jointMissionTraverseGroup.name = 'jointMissionTraverseGroup';

    jointCandidatesGroup = new THREE.Group();
    jointCandidatesGroup.name = 'jointCandidatesGroup';

    jointSelectedRouteGroup = new THREE.Group();
    jointSelectedRouteGroup.name = 'jointSelectedRouteGroup';

    jointGapsGroup = new THREE.Group();
    jointGapsGroup.name = 'jointGapsGroup';

    jointMissionTraverseGroup.add(jointCandidatesGroup);
    jointMissionTraverseGroup.add(jointSelectedRouteGroup);
    jointMissionTraverseGroup.add(jointGapsGroup);

    jezeroSurfaceGroup.add(jointMissionTraverseGroup);
  }
}

function bindJointStudioElements() {
  tabBtnJointMissionStudio = document.getElementById('tabBtnJointMissionStudio');
  tabJointMissionStudio = document.getElementById('tabJointMissionStudio');
  btnToggleJointStudio = document.getElementById('btnToggleJointStudio');
  jointMissionStudioPanel = document.getElementById('jointMissionStudioPanel');
  btnCloseJointStudioPanel = document.getElementById('btnCloseJointStudioPanel');
  paretoScatterCanvas = document.getElementById('paretoScatterCanvas');
  paretoCanvasTooltip = document.getElementById('paretoCanvasTooltip');
  paretoScorecardTable = document.getElementById('paretoScorecardTable');
  paretoScorecardBody = document.getElementById('paretoScorecardBody');
  btnRunJointOptimization = document.getElementById('btnRunJointOptimization');
  btnTheaterRunJointOptimize = document.getElementById('btnTheaterRunJointOptimize');
  btnPromoteJointPlan = document.getElementById('btnPromoteJointPlan');
  btnTheaterPromoteJoint = document.getElementById('btnTheaterPromoteJoint');
  btnExportJointJson = document.getElementById('btnExportJointJson');
  btnExportJointMd = document.getElementById('btnExportJointMd');
  jointTheaterCandidateSelect = document.getElementById('jointTheaterCandidateSelect');
}

function setupJointStudioListeners() {
  // Tab Button
  if (tabBtnJointMissionStudio) {
    tabBtnJointMissionStudio.addEventListener('click', () => {
      switchInspectorTab('tabJointMissionStudio');
    });
  }

  // In-Theater Drawer Toggle Button
  if (btnToggleJointStudio && jointMissionStudioPanel) {
    btnToggleJointStudio.addEventListener('click', () => {
      jointMissionDrawerVisible = !jointMissionDrawerVisible;
      jointMissionStudioPanel.classList.toggle('hidden', !jointMissionDrawerVisible);
      btnToggleJointStudio.classList.toggle('active', jointMissionDrawerVisible);
    });
  }
  if (btnCloseJointStudioPanel && jointMissionStudioPanel) {
    btnCloseJointStudioPanel.addEventListener('click', () => {
      jointMissionDrawerVisible = false;
      jointMissionStudioPanel.classList.add('hidden');
      if (btnToggleJointStudio) btnToggleJointStudio.classList.remove('active');
    });
  }

  // Stepper Navigation
  const stepBtns = document.querySelectorAll('.joint-step-btn');
  stepBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const step = parseInt(btn.dataset.step, 10);
      switchJointWizardStep(step);
    });
  });

  const nextBtns = document.querySelectorAll('.joint-next-step-btn');
  nextBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const next = parseInt(btn.dataset.next, 10);
      switchJointWizardStep(next);
    });
  });

  const prevBtns = document.querySelectorAll('.joint-prev-step-btn');
  prevBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const prev = parseInt(btn.dataset.prev, 10);
      switchJointWizardStep(prev);
    });
  });

  // Weight Presets
  const presetPills = document.querySelectorAll('.joint-preset-pill');
  presetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      presetPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      applyJointWeightPreset(pill.dataset.preset);
    });
  });

  // Weight Sliders Sync
  ['Dist', 'Gap', 'Relays', 'Energy'].forEach(metric => {
    const slider = document.getElementById(`jointWeight${metric}`);
    const valSpan = document.getElementById(`jointWeight${metric}Val`);
    if (slider && valSpan) {
      slider.addEventListener('input', () => {
        valSpan.textContent = parseFloat(slider.value).toFixed(2);
      });
    }
  });

  // Auto-Normalize Weights Button
  const btnNorm = document.getElementById('btnJointNormalizeWeights');
  if (btnNorm) {
    btnNorm.addEventListener('click', () => {
      normalizeJointWeights();
    });
  }

  // Run Optimization Buttons
  if (btnRunJointOptimization) {
    btnRunJointOptimization.addEventListener('click', () => {
      runJointMissionOptimization();
    });
  }
  if (btnTheaterRunJointOptimize) {
    btnTheaterRunJointOptimize.addEventListener('click', () => {
      runJointMissionOptimization();
    });
  }

  // Promote Buttons
  if (btnPromoteJointPlan) {
    btnPromoteJointPlan.addEventListener('click', () => {
      promoteJointConfiguration();
    });
  }
  if (btnTheaterPromoteJoint) {
    btnTheaterPromoteJoint.addEventListener('click', () => {
      promoteJointConfiguration();
    });
  }

  // Export Buttons
  if (btnExportJointJson) {
    btnExportJointJson.addEventListener('click', () => {
      exportJointMissionJson();
    });
  }
  if (btnExportJointMd) {
    btnExportJointMd.addEventListener('click', () => {
      exportJointMissionMd();
    });
  }

  // Candidate Selectors in Theater Drawer
  if (jointTheaterCandidateSelect) {
    jointTheaterCandidateSelect.addEventListener('change', (e) => {
      if (e.target.value) {
        selectJointConfiguration(e.target.value);
      }
    });
  }

  // Trajectory Layer Toggles
  const chkSelected = document.getElementById('chkJointShowSelected');
  const chkPareto = document.getElementById('chkJointShowParetoAlts');
  const chkDominated = document.getElementById('chkJointShowDominated');
  const chkGaps = document.getElementById('chkJointShowGaps');

  if (chkSelected && jointSelectedRouteGroup) {
    chkSelected.addEventListener('change', () => {
      jointSelectedRouteGroup.visible = chkSelected.checked;
    });
  }
  if (chkPareto && jointCandidatesGroup) {
    chkPareto.addEventListener('change', () => {
      jointCandidatesGroup.children.forEach(mesh => {
        if (mesh.userData && mesh.userData.is_pareto && !mesh.userData.is_selected) {
          mesh.visible = chkPareto.checked;
        }
      });
    });
  }
  if (chkDominated && jointCandidatesGroup) {
    chkDominated.addEventListener('change', () => {
      jointCandidatesGroup.children.forEach(mesh => {
        if (mesh.userData && !mesh.userData.is_pareto) {
          mesh.visible = chkDominated.checked;
        }
      });
    });
  }
  if (chkGaps && jointGapsGroup) {
    chkGaps.addEventListener('change', () => {
      jointGapsGroup.visible = chkGaps.checked;
    });
  }

  // Pareto Canvas Mouse Interaction (Hover tooltip & Click selection)
  setupParetoCanvasEvents();
}

function switchJointWizardStep(stepNum) {
  currentJointWizardStep = stepNum;
  const stepBtns = document.querySelectorAll('.joint-step-btn');
  stepBtns.forEach(btn => {
    const s = parseInt(btn.dataset.step, 10);
    btn.classList.toggle('active', s === stepNum);
    if (s < stepNum) btn.classList.add('completed');
  });

  for (let i = 1; i <= 6; i++) {
    const panel = document.getElementById(`jointStepPanel${i}`);
    if (panel) {
      panel.classList.toggle('hidden', i !== stepNum);
      panel.classList.toggle('active', i === stepNum);
    }
  }

  if (stepNum === 5 && jointMissionOptimizationResult) {
    setTimeout(() => {
      renderParetoFrontier(jointMissionOptimizationResult);
    }, 50);
  }
}

function applyJointWeightPreset(preset) {
  const wDist = document.getElementById('jointWeightDist');
  const wGap = document.getElementById('jointWeightGap');
  const wRelays = document.getElementById('jointWeightRelays');
  const wEnergy = document.getElementById('jointWeightEnergy');

  const vDist = document.getElementById('jointWeightDistVal');
  const vGap = document.getElementById('jointWeightGapVal');
  const vRelays = document.getElementById('jointWeightRelaysVal');
  const vEnergy = document.getElementById('jointWeightEnergyVal');

  let weights = { dist: 0.30, gap: 0.35, relays: 0.20, energy: 0.15 };
  if (preset === 'mobility_first') {
    weights = { dist: 0.50, gap: 0.15, relays: 0.10, energy: 0.25 };
  } else if (preset === 'connectivity_first') {
    weights = { dist: 0.15, gap: 0.55, relays: 0.20, energy: 0.10 };
  } else if (preset === 'infrastructure_first') {
    weights = { dist: 0.25, gap: 0.20, relays: 0.45, energy: 0.10 };
  }

  if (wDist && vDist) { wDist.value = weights.dist; vDist.textContent = weights.dist.toFixed(2); }
  if (wGap && vGap) { wGap.value = weights.gap; vGap.textContent = weights.gap.toFixed(2); }
  if (wRelays && vRelays) { wRelays.value = weights.relays; vRelays.textContent = weights.relays.toFixed(2); }
  if (wEnergy && vEnergy) { wEnergy.value = weights.energy; vEnergy.textContent = weights.energy.toFixed(2); }
}

function normalizeJointWeights() {
  const wDist = document.getElementById('jointWeightDist');
  const wGap = document.getElementById('jointWeightGap');
  const wRelays = document.getElementById('jointWeightRelays');
  const wEnergy = document.getElementById('jointWeightEnergy');

  let d = parseFloat(wDist.value) || 0;
  let g = parseFloat(wGap.value) || 0;
  let r = parseFloat(wRelays.value) || 0;
  let e = parseFloat(wEnergy.value) || 0;
  const sum = d + g + r + e;
  if (sum > 0) {
    d = d / sum; g = g / sum; r = r / sum; e = e / sum;
    wDist.value = d.toFixed(2); document.getElementById('jointWeightDistVal').textContent = d.toFixed(2);
    wGap.value = g.toFixed(2); document.getElementById('jointWeightGapVal').textContent = g.toFixed(2);
    wRelays.value = r.toFixed(2); document.getElementById('jointWeightRelaysVal').textContent = r.toFixed(2);
    wEnergy.value = e.toFixed(2); document.getElementById('jointWeightEnergyVal').textContent = e.toFixed(2);
  }
}

async function runJointMissionOptimization() {
  const statusBox = document.getElementById('jointSolverStatusBox');
  const statusText = document.getElementById('jointSolverStatusText');
  if (statusBox) statusBox.classList.remove('hidden');
  if (statusText) statusText.textContent = 'Generating candidate traverses & evaluating line-of-sight...';

  // Read input fields
  const goalVal = document.getElementById('jointSelectGoal') ? document.getElementById('jointSelectGoal').value : '138,114';
  const goalParts = goalVal.split(',').map(v => parseInt(v.trim(), 10));
  const goalRc = [goalParts[0] || 138, goalParts[1] || 114];
  const relayBudget = parseInt(document.getElementById('jointRelayBudget') ? document.getElementById('jointRelayBudget').value : '2', 10);
  const platform = document.getElementById('jointPlatformSelect') ? document.getElementById('jointPlatformSelect').value : 'perseverance_rover';
  const baseMast = parseFloat(document.getElementById('jointBaseMast') ? document.getElementById('jointBaseMast').value : '10.0');
  const roverMast = parseFloat(document.getElementById('jointRoverMast') ? document.getElementById('jointRoverMast').value : '2.5');
  const fieldMast = parseFloat(document.getElementById('jointFieldMast') ? document.getElementById('jointFieldMast').value : '8.0');

  const wDist = parseFloat(document.getElementById('jointWeightDist') ? document.getElementById('jointWeightDist').value : '0.30');
  const wGap = parseFloat(document.getElementById('jointWeightGap') ? document.getElementById('jointWeightGap').value : '0.35');
  const wRelays = parseFloat(document.getElementById('jointWeightRelays') ? document.getElementById('jointWeightRelays').value : '0.20');
  const wEnergy = parseFloat(document.getElementById('jointWeightEnergy') ? document.getElementById('jointWeightEnergy').value : '0.15');

  const payload = {
    start_rc: [117, 157],
    goal_rc: goalRc,
    intermediate_waypoints: [
      { id: 'WP-SEITAH', name: 'Séítah Carbonates', rc: [150, 140], priority_score: 85.0 },
      { id: 'WP-KODIAK', name: 'Kodiak Butte', rc: [175, 122], priority_score: 92.0 }
    ],
    max_relays_budget: relayBudget,
    weights: {
      distance: wDist,
      gap_duration: wGap,
      relay_cost: wRelays,
      metabolic_energy: wEnergy
    },
    antenna_mast_rover_m: roverMast,
    antenna_mast_base_m: baseMast,
    antenna_mast_relay_m: fieldMast,
    max_gap_duration_s: 900.0,
    vehicle_platform: platform
  };

  try {
    const res = await fetch('/api/joint-mission/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    jointMissionOptimizationResult = data;
    console.log('[JointMissionStudio] Optimization succeeded:', data);

    if (statusText) statusText.textContent = `Completed: ${data.all_candidates ? data.all_candidates.length : 0} candidates (${data.pareto_candidates ? data.pareto_candidates.length : 0} Pareto non-dominated).`;

    // Populate candidates into UI
    const defaultSelected = data.recommended_candidate || (data.pareto_candidates && data.pareto_candidates[0]) || (data.all_candidates && data.all_candidates[0]);
    if (defaultSelected) {
      jointSelectedCandidateId = defaultSelected.candidate_id;
    }

    renderParetoScorecard(data.all_candidates || [], jointSelectedCandidateId);
    updateJointTheaterCandidateDropdown(data.all_candidates || [], jointSelectedCandidateId);
    renderJointTraversesIn3D(data, jointSelectedCandidateId);
    updateJointSelectedSummary(defaultSelected);

    // Switch to step 5 (Pareto Studio)
    setTimeout(() => {
      switchJointWizardStep(5);
    }, 400);

  } catch (err) {
    console.error('[JointMissionStudio] Optimization failed:', err);
    if (statusText) statusText.textContent = `Error: ${err.message}`;
  }
}

function updateJointTheaterCandidateDropdown(candidates, selectedId) {
  if (!jointTheaterCandidateSelect) return;
  jointTheaterCandidateSelect.innerHTML = '';
  candidates.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.candidate_id;
    const rankStr = c.is_pareto ? '★ Rank 1' : 'Dominated';
    const distM = c.metrics ? Math.round(c.metrics.total_distance_m) : 0;
    const covPct = c.metrics ? c.metrics.comms_coverage_pct.toFixed(0) : 0;
    opt.textContent = `${c.candidate_id}: ${c.strategy_name || 'Route'} [${distM}m, ${covPct}% cov] (${rankStr})`;
    if (c.candidate_id === selectedId) opt.selected = true;
    jointTheaterCandidateSelect.appendChild(opt);
  });
}

function renderParetoScorecard(candidates, selectedId) {
  if (!paretoScorecardBody) return;
  paretoScorecardBody.innerHTML = '';

  candidates.forEach(c => {
    const m = c.metrics || {};
    const tr = document.createElement('tr');
    if (c.candidate_id === selectedId) tr.classList.add('pareto-row-selected');
    tr.dataset.candidateId = c.candidate_id;

    const rankBadge = c.is_pareto
      ? `<span class="pareto-rank-badge rank1">Rank 1 (Pareto)</span>`
      : `<span class="pareto-rank-badge dominated">Dominated</span>`;

    const distM = Math.round(m.total_distance_m || 0);
    const covPct = (m.comms_coverage_pct || 0).toFixed(1);
    const relays = m.relay_count !== undefined ? m.relay_count : (c.relays_deployed ? c.relays_deployed.length : 0);
    const gapSec = Math.round(m.max_blackout_duration_s || 0);
    const energyKj = Math.round((m.metabolic_energy_j || 0) / 1000);

    tr.innerHTML = `
      <td style="font-weight:700; color:var(--telemetry-cyan); font-family:monospace;">${c.candidate_id}</td>
      <td style="font-weight:600;">${c.strategy_name || 'Candidate'}</td>
      <td>${rankBadge}</td>
      <td class="font-mono">${distM} m</td>
      <td class="font-mono" style="color:${parseFloat(covPct) >= 95 ? '#10b981' : (parseFloat(covPct) >= 75 ? '#f59e0b' : '#ef4444')};">${covPct}%</td>
      <td class="font-mono text-center">${relays}</td>
      <td class="font-mono">${gapSec} s</td>
      <td class="font-mono">${energyKj} kJ</td>
      <td>
        <button class="pareto-btn-action btn-select-candidate" data-id="${c.candidate_id}" title="Select this Co-Design">Select</button>
      </td>
    `;

    tr.addEventListener('click', (e) => {
      selectJointConfiguration(c.candidate_id);
    });

    paretoScorecardBody.appendChild(tr);
  });

  const selectBtns = paretoScorecardBody.querySelectorAll('.btn-select-candidate');
  selectBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      selectJointConfiguration(btn.dataset.id);
    });
  });
}

function selectJointConfiguration(candidateId) {
  jointSelectedCandidateId = candidateId;

  // Update table selection
  if (paretoScorecardBody) {
    const rows = paretoScorecardBody.querySelectorAll('tr');
    rows.forEach(r => {
      r.classList.toggle('pareto-row-selected', r.dataset.candidateId === candidateId);
    });
  }

  // Update theater dropdown
  if (jointTheaterCandidateSelect) {
    jointTheaterCandidateSelect.value = candidateId;
  }

  if (!jointMissionOptimizationResult || !jointMissionOptimizationResult.all_candidates) return;
  const candidate = jointMissionOptimizationResult.all_candidates.find(c => c.candidate_id === candidateId);
  if (!candidate) return;

  // Update summary & telemetry boxes
  updateJointSelectedSummary(candidate);
  updateJointDecisionExplanation(candidate);

  // Redraw 3D routes with new selection
  renderJointTraversesIn3D(jointMissionOptimizationResult, candidateId);

  // Redraw Pareto scatter
  renderParetoFrontier(jointMissionOptimizationResult);
}

function updateJointSelectedSummary(candidate) {
  if (!candidate) return;
  const m = candidate.metrics || {};
  const distM = Math.round(m.total_distance_m || 0);
  const covPct = (m.comms_coverage_pct || 0).toFixed(1);
  const relays = m.relay_count !== undefined ? m.relay_count : (candidate.relays_deployed ? candidate.relays_deployed.length : 0);
  const energyKj = Math.round((m.metabolic_energy_j || 0) / 1000);

  // Tab summary card
  const nameEl = document.getElementById('jointSelectedName');
  const rankEl = document.getElementById('jointSelectedRank');
  const distEl = document.getElementById('jointSummaryDist');
  const covEl = document.getElementById('jointSummaryCoverage');
  const relaysEl = document.getElementById('jointSummaryRelays');
  const energyEl = document.getElementById('jointSummaryEnergy');

  if (nameEl) nameEl.textContent = `${candidate.candidate_id}: ${candidate.strategy_name || 'Route'}`;
  if (rankEl) {
    rankEl.textContent = candidate.is_pareto ? 'Pareto Rank 1' : 'Dominated';
    rankEl.style.background = candidate.is_pareto ? 'rgba(16,185,129,0.15)' : 'rgba(100,116,139,0.2)';
    rankEl.style.color = candidate.is_pareto ? '#10b981' : '#94a3b8';
  }
  if (distEl) distEl.textContent = `${distM} m`;
  if (covEl) covEl.textContent = `${covPct}%`;
  if (relaysEl) relaysEl.textContent = `${relays} towers`;
  if (energyEl) energyEl.textContent = `${energyKj} kJ`;

  // In-Theater Drawer telemetry
  const thCand = document.getElementById('jointTheaterCandidateId');
  const thDist = document.getElementById('jointTheaterDistance');
  const thCov = document.getElementById('jointTheaterCoverage');
  const thRelays = document.getElementById('jointTheaterRelays');
  const thEnergy = document.getElementById('jointTheaterEnergy');
  const thBadge = document.getElementById('jointMissionStatusBadge');

  if (thCand) thCand.textContent = `${candidate.candidate_id} (${candidate.strategy_name || 'Candidate'})`;
  if (thDist) thDist.textContent = `${distM} m`;
  if (thCov) thCov.textContent = `${covPct}% (${Math.round(m.max_blackout_duration_s || 0)}s gap)`;
  if (thRelays) thRelays.textContent = `${relays} (${(candidate.relays_deployed && candidate.relays_deployed.length > 0) ? candidate.relays_deployed.map(r => r.node_id).join(', ') : 'None'})`;
  if (thEnergy) thEnergy.textContent = `${energyKj} kJ (Waligora)`;
  if (thBadge) {
    thBadge.textContent = candidate.is_pareto ? 'PARETO RANK 1' : 'SUB-OPTIMAL';
    thBadge.className = `jointstudio-badge-status ${candidate.is_pareto ? 'pareto' : 'suboptimal'}`;
  }
}

function updateJointDecisionExplanation(candidate) {
  const card = document.getElementById('jointDecisionExplanationCard');
  const narrEl = document.getElementById('jointExplanationNarrative');
  const badgeEl = document.getElementById('jointExplanationBadge');
  if (!card || !narrEl) return;

  const expl = candidate.explanation || {};
  const m = candidate.metrics || {};
  const distDelta = expl.marginal_distance_vs_baseline_m || 0;
  const gapSaved = expl.blackout_reduction_s || 0;
  const text = expl.narrative_rationale || 
    `Candidate ${candidate.candidate_id} (${candidate.strategy_name}): achieves ${m.comms_coverage_pct.toFixed(1)}% line-of-sight connectivity with ${m.relay_count} deployed surface relays. Marginal trade-off: ${distDelta > 0 ? '+' : ''}${distDelta.toFixed(0)}m distance for ${gapSaved.toFixed(0)}s blackout reduction.`;

  narrEl.textContent = text;
  if (badgeEl) {
    badgeEl.textContent = candidate.is_pareto ? 'PARETO EFFICIENT' : 'DOMINATED ALTERNATIVE';
    badgeEl.style.color = candidate.is_pareto ? '#10b981' : '#94a3b8';
  }
}

// --------------------------------------------------------------------------
// 3D Mission Theater Trajectory Visualizer
// --------------------------------------------------------------------------

function renderJointTraversesIn3D(result, selectedId) {
  if (!jointMissionTraverseGroup) return;

  // Clear previous candidate meshes
  while (jointCandidatesGroup.children.length > 0) {
    const obj = jointCandidatesGroup.children.pop();
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) obj.material.dispose();
  }
  while (jointSelectedRouteGroup.children.length > 0) {
    const obj = jointSelectedRouteGroup.children.pop();
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) obj.material.dispose();
  }
  while (jointGapsGroup.children.length > 0) {
    const obj = jointGapsGroup.children.pop();
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) obj.material.dispose();
  }

  const candidates = result.all_candidates || [];

  candidates.forEach(c => {
    const isSelected = c.candidate_id === selectedId;
    const isPareto = c.is_pareto;
    const path = c.path_rc || [];
    if (path.length < 2) return;

    // Convert path_rc to 3D points
    const points3D = [];
    for (let i = 0; i < path.length; i++) {
      const r = path[i][0];
      const col = path[i][1];
      let elev = -2500;
      if (missionData && missionData.elevation_samples && missionData.elevation_samples[r]) {
        elev = missionData.elevation_samples[r][col];
      }
      const pos = rcToLocalPos(r, col, elev, currentExaggeration);
      // Lift slightly above surface
      pos.y += isSelected ? 3.0 : 1.5;
      points3D.push(pos);
    }

    if (isSelected) {
      // Bold Tube for Selected Route
      const curve = new THREE.CatmullRomCurve3(points3D);
      const tubeGeom = new THREE.TubeGeometry(curve, Math.min(path.length * 2, 200), 2.2, 8, false);
      const tubeMat = new THREE.MeshStandardMaterial({
        color: 0x00e5ff,
        emissive: 0x0088cc,
        emissiveIntensity: 0.6,
        roughness: 0.3,
        metalness: 0.4
      });
      const tubeMesh = new THREE.Mesh(tubeGeom, tubeMat);
      tubeMesh.name = `joint_selected_${c.candidate_id}`;
      tubeMesh.userData = { candidateData: c, is_selected: true, is_pareto: true };
      jointSelectedRouteGroup.add(tubeMesh);

      // Render Comms Gaps for Selected Route
      const gaps = c.blackout_gaps || [];
      gaps.forEach((gap, gIdx) => {
        const startIdx = Math.max(0, gap.start_step_idx || 0);
        const endIdx = Math.min(points3D.length - 1, gap.end_step_idx || (startIdx + 5));
        const gapPts = points3D.slice(startIdx, endIdx + 1);
        if (gapPts.length >= 2) {
          const gapCurve = new THREE.CatmullRomCurve3(gapPts);
          const gapGeom = new THREE.TubeGeometry(gapCurve, Math.min(gapPts.length * 2, 60), 3.0, 8, false);
          const gapMat = new THREE.MeshBasicMaterial({
            color: 0xef4444,
            transparent: true,
            opacity: 0.85
          });
          const gapMesh = new THREE.Mesh(gapGeom, gapMat);
          gapMesh.name = `joint_gap_${gap.gap_id || gIdx}`;
          gapMesh.userData = { gapData: gap, candidate_id: c.candidate_id };
          jointGapsGroup.add(gapMesh);
        }
      });

    } else if (isPareto) {
      // Dashed Violet Ribbon for Pareto Alternatives
      const geom = new THREE.BufferGeometry().setFromPoints(points3D);
      const mat = new THREE.LineDashedMaterial({
        color: 0xa855f7,
        dashSize: 12,
        gapSize: 6,
        linewidth: 2,
        transparent: true,
        opacity: 0.85
      });
      const lineMesh = new THREE.Line(geom, mat);
      lineMesh.computeLineDistances();
      lineMesh.name = `joint_pareto_${c.candidate_id}`;
      lineMesh.userData = { candidateData: c, is_pareto: true, is_selected: false };
      jointCandidatesGroup.add(lineMesh);

    } else {
      // Faint Slate Grey for Dominated Routes
      const geom = new THREE.BufferGeometry().setFromPoints(points3D);
      const mat = new THREE.LineBasicMaterial({
        color: 0x64748b,
        transparent: true,
        opacity: 0.35
      });
      const lineMesh = new THREE.Line(geom, mat);
      lineMesh.name = `joint_dominated_${c.candidate_id}`;
      lineMesh.userData = { candidateData: c, is_pareto: false, is_selected: false };
      jointCandidatesGroup.add(lineMesh);
    }
  });

  // Also update RelayNet 3D deployed towers to match selected configuration
  if (result.all_candidates) {
    const selCandidate = result.all_candidates.find(c => c.candidate_id === selectedId);
    if (selCandidate && selCandidate.relays_deployed) {
      deployJointSelectedRelays(selCandidate.relays_deployed);
    }
  }

  console.log(`[JointMissionStudio] Rendered ${candidates.length} co-design traverses in 3D Theater.`);
}

function deployJointSelectedRelays(relays) {
  if (!relayNetNodesGroup) return;

  // Clear previously deployed surface relay masts (keep BASE)
  const toRemove = [];
  relayNetNodesGroup.children.forEach(child => {
    if (child.userData && child.userData.nodeType === 'relay_node') {
      toRemove.push(child);
    }
  });
  toRemove.forEach(obj => {
    relayNetNodesGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) obj.material.dispose();
  });

  // Re-deploy selected relays
  relayNetActiveRelays = [];
  relays.forEach(r => {
    relayNetActiveRelays.push(r);
    const rc = r.rc || [130, 130];
    let elev = r.elevation_m || -2450;
    if (missionData && missionData.elevation_samples && missionData.elevation_samples[rc[0]]) {
      elev = missionData.elevation_samples[rc[0]][rc[1]];
    }
    const pos = rcToLocalPos(rc[0], rc[1], elev, currentExaggeration);
    const mastH = (r.antenna_height_m || 8.0) * currentExaggeration;

    const mastGeom = new THREE.CylinderGeometry(1.2, 2.0, mastH, 8);
    mastGeom.translate(0, mastH / 2, 0);
    const mastMat = new THREE.MeshStandardMaterial({
      color: 0x10b981,
      emissive: 0x059669,
      emissiveIntensity: 0.4,
      roughness: 0.3,
      metalness: 0.6
    });
    const mastMesh = new THREE.Mesh(mastGeom, mastMat);
    mastMesh.position.copy(pos);
    mastMesh.userData = {
      nodeType: 'relay_node',
      relayData: {
        node_id: r.node_id,
        row: rc[0],
        col: rc[1],
        elevation_m: elev,
        antenna_height_m: r.antenna_height_m || 8.0,
        effective_z_m: elev + (r.antenna_height_m || 8.0)
      }
    };
    relayNetNodesGroup.add(mastMesh);
  });
}

// --------------------------------------------------------------------------
// Interactive Pareto Frontier 2D Scatter Canvas
// --------------------------------------------------------------------------

let paretoPoints = [];

function renderParetoFrontier(result) {
  if (!paretoScatterCanvas) return;
  const ctx = paretoScatterCanvas.getContext('2d');
  const w = paretoScatterCanvas.width;
  const h = paretoScatterCanvas.height;
  ctx.clearRect(0, 0, w, h);

  const candidates = result.all_candidates || [];
  if (candidates.length === 0) return;

  // Find min and max for axes
  let minD = Infinity, maxD = -Infinity;
  let minG = 0, maxG = -Infinity;

  candidates.forEach(c => {
    const d = c.metrics ? c.metrics.total_distance_m : 0;
    const g = c.metrics ? c.metrics.max_blackout_duration_s : 0;
    if (d < minD) minD = d;
    if (d > maxD) maxD = d;
    if (g > maxG) maxG = g;
  });

  const padLeft = 45, padRight = 20, padTop = 20, padBottom = 30;
  const plotW = w - padLeft - padRight;
  const plotH = h - padTop - padBottom;

  const dSpan = Math.max(maxD - minD, 500);
  const gSpan = Math.max(maxG, 300);

  // Draw Grid Lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 4; i++) {
    const y = padTop + (plotH / 4) * i;
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - padRight, y);

    const x = padLeft + (plotW / 4) * i;
    ctx.moveTo(x, padTop);
    ctx.lineTo(x, h - padBottom);
  }
  ctx.stroke();

  // Axis Labels
  ctx.fillStyle = '#64748b';
  ctx.font = '8px ui-monospace, Consolas, monospace';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (let i = 0; i <= 4; i++) {
    const gVal = Math.round(maxG - (gSpan / 4) * i);
    const y = padTop + (plotH / 4) * i;
    ctx.fillText(`${gVal}s`, padLeft - 4, y);
  }

  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let i = 0; i <= 4; i++) {
    const dVal = Math.round(minD + (dSpan / 4) * i);
    const x = padLeft + (plotW / 4) * i;
    ctx.fillText(`${dVal}m`, x, h - padBottom + 4);
  }

  // Plot Points and build hit-test list
  paretoPoints = [];
  const paretoCoords = [];

  candidates.forEach(c => {
    const m = c.metrics || {};
    const d = m.total_distance_m || 0;
    const g = m.max_blackout_duration_s || 0;

    const px = padLeft + ((d - minD) / dSpan) * plotW;
    const py = padTop + (1.0 - (g / gSpan)) * plotH;

    const isSel = c.candidate_id === jointSelectedCandidateId;
    const isP = c.is_pareto;

    paretoPoints.push({
      x: px, y: py, radius: isSel ? 8 : (isP ? 6 : 4),
      candidate: c, is_pareto: isP, is_selected: isSel
    });

    if (isP) {
      paretoCoords.push({ x: px, y: py, d });
    }
  });

  // Sort Pareto coords by Distance to draw non-dominated efficiency boundary
  paretoCoords.sort((a, b) => a.d - b.d);
  if (paretoCoords.length > 1) {
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(paretoCoords[0].x, paretoCoords[0].y);
    for (let i = 1; i < paretoCoords.length; i++) {
      ctx.lineTo(paretoCoords[i].x, paretoCoords[i].y);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Draw Points
  paretoPoints.forEach(pt => {
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, pt.radius, 0, Math.PI * 2);
    if (pt.is_selected) {
      ctx.fillStyle = '#00e5ff';
      ctx.shadowColor = '#00e5ff';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.shadowBlur = 0;
    } else if (pt.is_pareto) {
      ctx.fillStyle = '#10b981';
      ctx.shadowColor = '#10b981';
      ctx.shadowBlur = 6;
      ctx.fill();
      ctx.strokeStyle = '#34d399';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.shadowBlur = 0;
    } else {
      ctx.fillStyle = '#64748b';
      ctx.fill();
    }
  });
}

function setupParetoCanvasEvents() {
  if (!paretoScatterCanvas) return;

  paretoScatterCanvas.addEventListener('mousemove', (e) => {
    const rect = paretoScatterCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    let hit = null;
    for (let i = 0; i < paretoPoints.length; i++) {
      const pt = paretoPoints[i];
      const dist = Math.hypot(pt.x - mx, pt.y - my);
      if (dist <= pt.radius + 4) {
        hit = pt;
        break;
      }
    }

    if (hit && paretoCanvasTooltip) {
      const c = hit.candidate;
      const m = c.metrics || {};
      paretoCanvasTooltip.innerHTML = `
        <div style="font-weight:700; color:${hit.is_pareto ? '#10b981' : '#cbd5e1'}; font-size:9px;">
          ${c.candidate_id}: ${c.strategy_name || 'Route'}
        </div>
        <div style="color:#94a3b8; font-size:8px; margin-top:2px;">
          ${hit.is_pareto ? '★ Non-Dominated (Rank 1)' : 'Dominated Alternative'}
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:3px; margin-top:4px; font-size:8px;">
          <span>Dist: ${Math.round(m.total_distance_m)}m</span>
          <span>Coverage: ${m.comms_coverage_pct.toFixed(1)}%</span>
          <span>Relays: ${m.relay_count}</span>
          <span>Gap: ${Math.round(m.max_blackout_duration_s)}s</span>
        </div>
      `;
      paretoCanvasTooltip.style.left = `${hit.x}px`;
      paretoCanvasTooltip.style.top = `${hit.y}px`;
      paretoCanvasTooltip.classList.remove('hidden');
    } else if (paretoCanvasTooltip) {
      paretoCanvasTooltip.classList.add('hidden');
    }
  });

  paretoScatterCanvas.addEventListener('mouseleave', () => {
    if (paretoCanvasTooltip) paretoCanvasTooltip.classList.add('hidden');
  });

  paretoScatterCanvas.addEventListener('click', (e) => {
    const rect = paretoScatterCanvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    for (let i = 0; i < paretoPoints.length; i++) {
      const pt = paretoPoints[i];
      const dist = Math.hypot(pt.x - mx, pt.y - my);
      if (dist <= pt.radius + 6) {
        selectJointConfiguration(pt.candidate.candidate_id);
        break;
      }
    }
  });
}

// --------------------------------------------------------------------------
// Plan Promotion & Artifact Export
// --------------------------------------------------------------------------

async function promoteJointConfiguration() {
  if (!jointMissionOptimizationResult || !jointSelectedCandidateId) {
    alert('Please execute co-design optimization and select a candidate first.');
    return;
  }

  const payload = {
    selected_candidate_id: jointSelectedCandidateId,
    configuration_id: jointMissionOptimizationResult.optimization_id || 'opt_joint_demo',
    campaign_id: 'cmp_conference_demo_jezero'
  };

  try {
    const res = await fetch('/api/joint-mission/promote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log('[JointMissionStudio] Successfully promoted candidate:', data);

    setPlanningStatus(`PROMOTED CO-DESIGN: Candidate ${jointSelectedCandidateId} is now active mission plan.`, 'success');
    alert(`Success! Co-Design Candidate ${jointSelectedCandidateId} has been promoted to the active mission plan.`);
  } catch (err) {
    console.error('[JointMissionStudio] Promotion failed:', err);
    alert(`Promotion failed: ${err.message}`);
  }
}

function exportJointMissionJson() {
  if (!jointMissionOptimizationResult) {
    alert('No joint mission optimization result to export.');
    return;
  }
  const jsonStr = JSON.stringify(jointMissionOptimizationResult, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `atlas_joint_mission_${jointSelectedCandidateId || 'codesign'}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportJointMissionMd() {
  if (!jointMissionOptimizationResult || !jointSelectedCandidateId) {
    alert('No joint mission optimization result to export.');
    return;
  }
  const cand = (jointMissionOptimizationResult.all_candidates || []).find(c => c.candidate_id === jointSelectedCandidateId);
  if (!cand) return;

  const m = cand.metrics || {};
  const md = `# MARSWALK 2.0 / PROJECT ATLAS
# JOINT MISSION CO-DESIGN DECISION DOSSIER
**Candidate ID:** ${cand.candidate_id} (${cand.strategy_name || 'Selected'})
**Pareto Classification:** ${cand.is_pareto ? 'Non-Dominated (Rank 1 Efficiency Frontier)' : 'Dominated Alternative'}
**Date Generated:** ${new Date().toISOString()}

---

## 1. Multi-Objective Co-Design Metrics
- **Total Traverse Distance:** ${m.total_distance_m.toFixed(1)} m
- **Communications Coverage:** ${m.comms_coverage_pct.toFixed(1)}%
- **Deployed Surface Relays:** ${m.relay_count} masts
- **Max Blackout Gap Distance:** ${m.max_blackout_distance_m.toFixed(1)} m
- **Max Blackout Gap Duration:** ${m.max_blackout_duration_s.toFixed(1)} s (${(m.max_blackout_duration_s/60).toFixed(1)} min)
- **Apollo Waligora Metabolic Work:** ${(m.metabolic_energy_j/1000).toFixed(1)} kJ

## 2. Decision Rationale & Marginal Rate of Substitution
${(cand.explanation && cand.explanation.narrative_rationale) || 'Coupled co-design achieves optimal compromise between terrain mobility cost and geometric line-of-sight visibility.'}

## 3. Scientific Provenance & Boundary Disclosure
- **Topographic Base:** USGS CTX 20m DTM (DOI: 10.5066/P906QQT8, SHA-256: 875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3)
- **Mars Spheroid:** IAU 2000 (R = 3,396,190 m)
- **Operational Safety Notice:** Modeled traverses and communication links are deterministic planning heuristics and are NOT certified astronaut flight paths.
`;

  const blob = new Blob([md], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `atlas_joint_mission_dossier_${jointSelectedCandidateId}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
'''

if __name__ == '__main__':
    js = get_joint_js()
    print(f"Generated {len(js)} chars of JS.")
