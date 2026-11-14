"""
Script to safely inject Milestone 9K Persistent Workspace & Experiment Library logic into web/app.js
"""

import re
from pathlib import Path

APP_JS = Path("web/app.js")
text = APP_JS.read_text(encoding="utf-8")

# 1. DOM Elements & State Insertion
dom_state_block = """
  // Milestone 9K DOM Elements & State
  const activeMissionNameDisplay = document.getElementById('activeMissionNameDisplay');
  const unsavedChangesBadge = document.getElementById('unsavedChangesBadge');
  const inputMissionName = document.getElementById('inputMissionName');
  const btnSaveMission = document.getElementById('btnSaveMission');
  const btnOpenMissionLibrary = document.getElementById('btnOpenMissionLibrary');
  const btnSaveExperiment = document.getElementById('btnSaveExperiment');
  const btnOpenExperimentLibrary = document.getElementById('btnOpenExperimentLibrary');

  const missionLibraryModal = document.getElementById('missionLibraryModal');
  const btnCloseMissionLibrary = document.getElementById('btnCloseMissionLibrary');
  const fileImportMission = document.getElementById('fileImportMission');
  const missionLibraryTableBody = document.getElementById('missionLibraryTableBody');

  const experimentLibraryModal = document.getElementById('experimentLibraryModal');
  const btnCloseExperimentLibrary = document.getElementById('btnCloseExperimentLibrary');
  const btnOpenCompareFromLib = document.getElementById('btnOpenCompareFromLib');
  const experimentLibraryTableBody = document.getElementById('experimentLibraryTableBody');

  const experimentComparisonModal = document.getElementById('experimentComparisonModal');
  const btnCloseExperimentComparison = document.getElementById('btnCloseExperimentComparison');
  const selectCompareExpA = document.getElementById('selectCompareExpA');
  const selectCompareExpB = document.getElementById('selectCompareExpB');
  const btnExecuteCompare = document.getElementById('btnExecuteCompare');
  const compareResultsContainer = document.getElementById('compareResultsContainer');
  const compareTableBody = document.getElementById('compareTableBody');
  const compareTradeOffsList = document.getElementById('compareTradeOffsList');
  const thExpAName = document.getElementById('thExpAName');
  const thExpBName = document.getElementById('thExpBName');

  let activeSavedMissionId = null;
  let activeSavedMissionName = 'Untitled Mission';
  let hasUnsavedChanges = false;
  let activeHistoricalExperiment = null;

  function setUnsavedChanges(hasChanges) {
    hasUnsavedChanges = !!hasChanges;
    if (unsavedChangesBadge) {
      if (hasUnsavedChanges) unsavedChangesBadge.classList.remove('hidden');
      else unsavedChangesBadge.classList.add('hidden');
    }
  }
"""

if "activeMissionNameDisplay" not in text:
    target_needle = "let activeMissionFingerprint = null;"
    assert target_needle in text, "Could not find activeMissionFingerprint needle"
    text = text.replace(target_needle, target_needle + "\n" + dom_state_block)

# 2. Workspace functions insertion before setupEventListeners
workspace_funcs = """
  // =========================================================================
  // Milestone 9K: Persistent Mission Workspace & Experiment Library
  // =========================================================================

  // Save Current Mission to Library
  async function saveCurrentMission(nameOverride) {
    const missionName = nameOverride || (inputMissionName ? inputMissionName.value.trim() : '') || activeSavedMissionName;
    if (!customStart || !customGoal) {
      setPlanningStatus("Please define start and destination before saving mission.", "error");
      return null;
    }

    const payload = {
      schema_version: "1.0.0",
      mission_id: activeSavedMissionId || undefined,
      name: missionName,
      canonical_mission: {
        start: { row: customStart.row, col: customStart.col, name: customStart.name },
        goal: { row: customGoal.row, col: customGoal.col, name: customGoal.name },
        stops: activeIntermediateStops.map(s => ({
          row: s.row,
          col: s.col,
          id: s.id,
          name: s.name,
          priority_score: s.priority_score || 50,
          dwell_time_s: s.dwell_time_s || 900
        })),
        profile: currentProfile,
        vehicle_mode: currentVehicleMode,
        speed_multiplier: 1.0,
        optimize_stops: false,
        mission_constraints: {}
      },
      profile: currentProfile,
      vehicle_mode: currentVehicleMode,
      terrain_dataset_id: "USGS_CTX_DTM_JEZERO_20M",
      model_version: "2.0.0",
      assumptions_version: "1.0.0",
      tags: ["jezero", currentProfile, currentVehicleMode]
    };

    try {
      const resp = await fetch('/api/missions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);

      activeSavedMissionId = res.mission_id;
      activeSavedMissionName = res.name;
      if (activeMissionNameDisplay) activeMissionNameDisplay.textContent = res.name;
      if (inputMissionName) inputMissionName.value = res.name;
      setUnsavedChanges(false);
      setPlanningStatus(`MISSION SAVED: ${res.name} (ID: ${res.mission_id})`, "success");
      return res;
    } catch (err) {
      console.error('[MarsWalk Atlas] Save mission error:', err);
      setPlanningStatus(`Failed to save mission: ${err.message}`, "error");
      return null;
    }
  }

  // Load Mission by ID
  async function loadMissionById(missionId) {
    try {
      const resp = await fetch(`/api/missions/${missionId}`);
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);

      const canon = res.canonical_mission || {};
      if (canon.start) {
        customStart = { row: canon.start.row, col: canon.start.col, name: canon.start.name || `Departure (${canon.start.row}, ${canon.start.col})` };
        if (startPointVal) startPointVal.textContent = customStart.name;
        updateStartMarker(customStart.row, customStart.col);
      }
      if (canon.goal) {
        customGoal = { row: canon.goal.row, col: canon.goal.col, name: canon.goal.name || `Destination (${canon.goal.row}, ${canon.goal.col})` };
        if (goalPointVal) goalPointVal.textContent = customGoal.name;
        updateGoalMarker(customGoal.row, customGoal.col);
      }

      activeIntermediateStops = (canon.stops || []).map(s => ({
        row: s.row,
        col: s.col,
        id: s.id,
        name: s.name || s.id,
        priority_score: s.priority_score,
        dwell_time_s: s.dwell_time_s
      }));
      renderActiveStopsList();
      populateAddStopDropdown();

      if (canon.profile) {
        currentProfile = canon.profile;
        routeTabs.forEach(tab => {
          if (tab.dataset.route === currentProfile) tab.classList.add('active');
          else tab.classList.remove('active');
        });
      }

      if (canon.vehicle_mode) {
        currentVehicleMode = canon.vehicle_mode;
        vehicleModePills.forEach(p => {
          if (p.dataset.mode === currentVehicleMode) p.classList.add('active');
          else p.classList.remove('active');
        });
        if (statTravelTimeLabel) {
          statTravelTimeLabel.textContent = (currentVehicleMode === 'robotic_rover')
            ? 'Estimated Rover Drive Time (Mars 2020 0.035 m/s Model)'
            : 'Estimated EVA Traverse Time (Apollo Walk Model)';
        }
      }

      activeSavedMissionId = res.mission_id;
      activeSavedMissionName = res.name;
      if (activeMissionNameDisplay) activeMissionNameDisplay.textContent = res.name;
      if (inputMissionName) inputMissionName.value = res.name;
      setUnsavedChanges(false);

      if (missionLibraryModal) missionLibraryModal.classList.add('hidden');
      await calculateTraverse();
      setPlanningStatus(`MISSION RESTORED: ${res.name}`, "success");
      return res;
    } catch (err) {
      console.error('[MarsWalk Atlas] Load mission error:', err);
      setPlanningStatus(`Failed to load mission: ${err.message}`, "error");
      return null;
    }
  }

  // Refresh Mission Library Table
  async function refreshMissionLibraryTable() {
    if (!missionLibraryTableBody) return;
    missionLibraryTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-tertiary);">Loading saved missions...</td></tr>';

    try {
      const resp = await fetch('/api/missions');
      const data = await resp.json();
      const list = data.missions || [];

      if (list.length === 0) {
        missionLibraryTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-tertiary); padding:16px;">No saved missions found. Save your current mission above.</td></tr>';
        return;
      }

      missionLibraryTableBody.innerHTML = '';
      list.forEach(m => {
        const tr = document.createElement('tr');
        const dtStr = m.updated_at ? new Date(m.updated_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—';
        tr.innerHTML = `
          <td><strong>${m.name}</strong><br><span style="font-size:8.5px; color:var(--text-tertiary);">${m.mission_id}</span></td>
          <td><span class="wp-badge">${m.profile.toUpperCase()}</span></td>
          <td><span class="wp-badge">${m.vehicle_mode.replace('_', ' ').toUpperCase()}</span></td>
          <td>${m.num_stops}</td>
          <td style="font-size:9px;">${dtStr}</td>
          <td>
            <button class="table-action-btn btn-load-m" data-id="${m.mission_id}">Load</button>
            <button class="table-action-btn btn-dup-m" data-id="${m.mission_id}">Duplicate</button>
            <button class="table-action-btn btn-exp-m" data-id="${m.mission_id}">Export</button>
            <button class="table-action-btn danger btn-del-m" data-id="${m.mission_id}">Delete</button>
          </td>
        `;
        missionLibraryTableBody.appendChild(tr);
      });

      // Hook action buttons
      missionLibraryTableBody.querySelectorAll('.btn-load-m').forEach(b => {
        b.addEventListener('click', () => loadMissionById(b.dataset.id));
      });
      missionLibraryTableBody.querySelectorAll('.btn-dup-m').forEach(b => {
        b.addEventListener('click', async () => {
          await duplicateMissionById(b.dataset.id);
        });
      });
      missionLibraryTableBody.querySelectorAll('.btn-exp-m').forEach(b => {
        b.addEventListener('click', async () => {
          const resp = await fetch(`/api/missions/${b.dataset.id}`);
          const mData = await resp.json();
          const blob = new Blob([JSON.stringify(mData, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `marswalk_mission_${b.dataset.id}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        });
      });
      missionLibraryTableBody.querySelectorAll('.btn-del-m').forEach(b => {
        b.addEventListener('click', async () => {
          if (confirm(`Are you sure you want to delete saved mission '${b.dataset.id}'?`)) {
            await deleteMissionById(b.dataset.id);
          }
        });
      });
    } catch (err) {
      missionLibraryTableBody.innerHTML = `<tr><td colspan="6" style="color:#ff5252; padding:12px;">Failed loading missions: ${err.message}</td></tr>`;
    }
  }

  // Duplicate Mission
  async function duplicateMissionById(missionId) {
    try {
      const resp = await fetch(`/api/missions/${missionId}/duplicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);
      setPlanningStatus(`MISSION DUPLICATED: ID ${res.mission_id}`, "success");
      await refreshMissionLibraryTable();
      return res;
    } catch (err) {
      setPlanningStatus(`Failed to duplicate mission: ${err.message}`, "error");
      return null;
    }
  }

  // Delete Mission
  async function deleteMissionById(missionId) {
    try {
      const resp = await fetch(`/api/missions/${missionId}`, {
        method: 'DELETE'
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);
      if (activeSavedMissionId === missionId) {
        activeSavedMissionId = null;
        activeSavedMissionName = 'Untitled Mission';
        if (activeMissionNameDisplay) activeMissionNameDisplay.textContent = 'Untitled Mission';
      }
      setPlanningStatus(`MISSION DELETED: ${missionId}`, "ready");
      await refreshMissionLibraryTable();
      return res;
    } catch (err) {
      setPlanningStatus(`Failed to delete mission: ${err.message}`, "error");
      return null;
    }
  }

  // Save Current Simulation Run as Experiment
  async function saveCurrentExperiment(nameOverride) {
    if (!activeBaselineRouteResult) {
      await calculateTraverse();
    }
    if (!activeBaselineRouteResult) {
      setPlanningStatus("No active baseline calculation to save.", "error");
      return null;
    }

    const expName = nameOverride || `Study ${activeSavedMissionName} (${new Date().toLocaleTimeString()})`;
    const snapshot = activeBaselineRouteResult.mission_snapshot || {
      schema_version: "1.0.0",
      input_fingerprint: activeMissionFingerprint || "",
      canonical_mission: {
        start: customStart,
        goal: customGoal,
        stops: activeIntermediateStops,
        profile: currentProfile,
        vehicle_mode: currentVehicleMode
      },
      ordered_points: activeBaselineRouteResult.path_rc || [],
      terrain_dataset: {
        dataset_id: "USGS_CTX_DTM_JEZERO_20M",
        grid_cell_size_m: 20.0,
        dimensions: { height: 250, width: 250 }
      }
    };

    const payload = {
      schema_version: "1.0.0",
      name: expName,
      description: `Persistent experiment study for mission ${activeSavedMissionName}.`,
      mission_id: activeSavedMissionId || undefined,
      status: activeBaselineRouteResult.is_reachable ? "success" : "infeasible",
      lifecycle_state: "historical_result",
      baseline_fingerprint: activeBaselineRouteResult.input_fingerprint || activeMissionFingerprint || "",
      mission_snapshot: snapshot,
      baseline_route: activeBaselineRouteResult,
      scenarios_evaluated: lastComparisonResult ? (lastComparisonResult.scenarios || []) : [],
      sensitivity_sweep: lastSensitivityResult || null,
      recovery_plan: lastRecoveryPlan || null,
      reproducibility_notes: `Recorded on ${new Date().toISOString()} under MarsWalk 2.0.`,
      terrain_dataset_id: "USGS_CTX_DTM_JEZERO_20M",
      model_version: "2.0.0",
      assumptions_version: "1.0.0"
    };

    try {
      const resp = await fetch('/api/experiments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);

      setPlanningStatus(`EXPERIMENT PERSISTED: ${res.name} (ID: ${res.experiment_id})`, "success");
      return res;
    } catch (err) {
      console.error('[MarsWalk Atlas] Save experiment error:', err);
      setPlanningStatus(`Failed to save experiment: ${err.message}`, "error");
      return null;
    }
  }

  // Refresh Experiment Library Table
  async function refreshExperimentLibraryTable() {
    if (!experimentLibraryTableBody) return;
    experimentLibraryTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-tertiary);">Loading saved experiments...</td></tr>';

    try {
      const resp = await fetch('/api/experiments');
      const data = await resp.json();
      const list = data.experiments || [];

      if (list.length === 0) {
        experimentLibraryTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-tertiary); padding:16px;">No saved experiments found. Run a simulation and click "Save Run" above.</td></tr>';
        return;
      }

      experimentLibraryTableBody.innerHTML = '';
      list.forEach(exp => {
        const tr = document.createElement('tr');
        const dtStr = exp.created_at ? new Date(exp.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—';
        const distStr = (exp.ground_distance_m !== null && exp.ground_distance_m !== undefined) ? `${exp.ground_distance_m.toFixed(1)} m` : '—';
        const timeStr = exp.active_traverse_time_s ? formatDuration(exp.active_traverse_time_s) : '—';

        let badgeClass = 'lifecycle-historical';
        let badgeLabel = 'HISTORICAL';
        if (exp.lifecycle_state === 'reproducible') {
          badgeClass = 'lifecycle-reproducible';
          badgeLabel = 'REPRODUCIBLE';
        } else if (exp.lifecycle_state === 'recalculation_required') {
          badgeClass = 'lifecycle-recalc';
          badgeLabel = 'RECALC REQUIRED';
        } else if (exp.lifecycle_state === 'stale_incompatible') {
          badgeClass = 'lifecycle-stale';
          badgeLabel = 'INCOMPATIBLE';
        } else if (exp.lifecycle_state === 'failed') {
          badgeClass = 'lifecycle-failed';
          badgeLabel = 'FAILED';
        }

        tr.innerHTML = `
          <td><strong>${exp.name}</strong><br><span style="font-size:8.5px; color:var(--text-tertiary);">${exp.experiment_id}</span></td>
          <td><span class="lifecycle-badge ${badgeClass}">${badgeLabel}</span></td>
          <td>${distStr}</td>
          <td>${timeStr}</td>
          <td>${exp.num_scenarios}</td>
          <td style="font-size:9px;">${dtStr}</td>
          <td>
            <button class="table-action-btn btn-view-e" data-id="${exp.experiment_id}">View</button>
            <button class="table-action-btn btn-replay-e" data-id="${exp.experiment_id}">Replay</button>
            <button class="table-action-btn danger btn-del-e" data-id="${exp.experiment_id}">Delete</button>
          </td>
        `;
        experimentLibraryTableBody.appendChild(tr);
      });

      experimentLibraryTableBody.querySelectorAll('.btn-view-e').forEach(b => {
        b.addEventListener('click', () => viewExperimentById(b.dataset.id));
      });
      experimentLibraryTableBody.querySelectorAll('.btn-replay-e').forEach(b => {
        b.addEventListener('click', () => replayExperimentById(b.dataset.id));
      });
      experimentLibraryTableBody.querySelectorAll('.btn-del-e').forEach(b => {
        b.addEventListener('click', async () => {
          if (confirm(`Are you sure you want to delete experiment '${b.dataset.id}'?`)) {
            await deleteExperimentById(b.dataset.id);
          }
        });
      });
    } catch (err) {
      experimentLibraryTableBody.innerHTML = `<tr><td colspan="7" style="color:#ff5252; padding:12px;">Failed loading experiments: ${err.message}</td></tr>`;
    }
  }

  // View Historical Experiment
  async function viewExperimentById(expId) {
    try {
      const resp = await fetch(`/api/experiments/${expId}`);
      const expData = await resp.json();
      if (!resp.ok) throw new Error(expData.message || expData.error || `HTTP ${resp.status}`);

      activeHistoricalExperiment = expData;
      const bRoute = expData.baseline_route || {};
      if (bRoute.coordinates_3d && bRoute.coordinates_3d.length > 0) {
        drawCalculatedRoute(bRoute.coordinates_3d);
      }
      updateTelemetryFromData(bRoute);

      if (experimentLibraryModal) experimentLibraryModal.classList.add('hidden');
      setPlanningStatus(`VIEWING HISTORICAL EXPERIMENT: ${expData.name} (${expData.lifecycle_state.toUpperCase()})`, "ready");
      return expData;
    } catch (err) {
      setPlanningStatus(`Failed to view experiment: ${err.message}`, "error");
      return null;
    }
  }

  // Replay Saved Experiment
  async function replayExperimentById(expId) {
    setPlanningStatus(`Replaying experiment ${expId} under current simulation engine...`, "calculating");
    try {
      const resp = await fetch(`/api/experiments/${expId}/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);

      const matchMsg = res.is_exact_match
        ? "REPLAY VERIFIED: Exact mathematical match to historical study."
        : "REPLAY COMPLETED: Output differs from historical baseline (see notes).";
      setPlanningStatus(`${matchMsg} Saved as: ${res.experiment_id}`, "success");
      await refreshExperimentLibraryTable();
      return res;
    } catch (err) {
      setPlanningStatus(`Replay failed: ${err.message}`, "error");
      return null;
    }
  }

  // Delete Experiment
  async function deleteExperimentById(expId) {
    try {
      const resp = await fetch(`/api/experiments/${expId}`, {
        method: 'DELETE'
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);
      setPlanningStatus(`EXPERIMENT DELETED: ${expId}`, "ready");
      await refreshExperimentLibraryTable();
      return res;
    } catch (err) {
      setPlanningStatus(`Failed to delete experiment: ${err.message}`, "error");
      return null;
    }
  }

  // Open Experiment Comparison Modal
  async function openExperimentComparisonModal() {
    if (!selectCompareExpA || !selectCompareExpB) return;
    try {
      const resp = await fetch('/api/experiments');
      const data = await resp.json();
      const list = data.experiments || [];

      if (list.length < 2) {
        setPlanningStatus("At least 2 saved experiments are required for trade-off comparison.", "error");
        return;
      }

      selectCompareExpA.innerHTML = '';
      selectCompareExpB.innerHTML = '';
      list.forEach((exp, idx) => {
        const optA = document.createElement('option');
        optA.value = exp.experiment_id;
        optA.textContent = `${exp.name} (${exp.experiment_id})`;
        selectCompareExpA.appendChild(optA);

        const optB = document.createElement('option');
        optB.value = exp.experiment_id;
        optB.textContent = `${exp.name} (${exp.experiment_id})`;
        if (idx === 1) optB.selected = true;
        selectCompareExpB.appendChild(optB);
      });

      if (experimentLibraryModal) experimentLibraryModal.classList.add('hidden');
      if (experimentComparisonModal) experimentComparisonModal.classList.remove('hidden');
    } catch (err) {
      setPlanningStatus(`Failed opening comparison modal: ${err.message}`, "error");
    }
  }

  // Execute Side-by-Side Trade-off Comparison
  async function executeExperimentComparison(idAOverride, idBOverride) {
    const idA = idAOverride || (selectCompareExpA ? selectCompareExpA.value : null);
    const idB = idBOverride || (selectCompareExpB ? selectCompareExpB.value : null);

    if (!idA || !idB) {
      setPlanningStatus("Please select two experiments to compare.", "error");
      return null;
    }
    if (idA === idB) {
      setPlanningStatus("Please select two distinct experiments for comparison.", "error");
      return null;
    }

    try {
      const resp = await fetch('/api/experiments/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          schema_version: "1.0.0",
          experiment_id_a: idA,
          experiment_id_b: idB
        })
      });
      const res = await resp.json();
      if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);

      if (thExpAName) thExpAName.textContent = res.experiment_a.name;
      if (thExpBName) thExpBName.textContent = res.experiment_b.name;

      if (compareTableBody) {
        const d = res.deltas || {};
        const distDeltaStr = (d.distance_delta_m !== null) ? `${(d.distance_delta_m > 0 ? '+' : '')}${d.distance_delta_m.toFixed(1)} m (${d.distance_pct_delta !== null ? (d.distance_pct_delta > 0 ? '+' : '') + d.distance_pct_delta + '%' : '—'})` : '—';
        const timeDeltaStr = (d.active_time_delta_s !== null) ? `${(d.active_time_delta_s > 0 ? '+' : '')}${formatDuration(Math.abs(d.active_time_delta_s))} (${d.active_time_pct_delta !== null ? (d.active_time_pct_delta > 0 ? '+' : '') + d.active_time_pct_delta + '%' : '—'})` : '—';
        const effortDeltaStr = (d.effort_delta_flat_m !== null) ? `${(d.effort_delta_flat_m > 0 ? '+' : '')}${d.effort_delta_flat_m.toFixed(1)} flat-m` : '—';
        const sciDeltaStr = (d.science_score_delta !== null) ? `${(d.science_score_delta > 0 ? '+' : '')}${d.science_score_delta.toFixed(1)} pts` : '—';

        compareTableBody.innerHTML = `
          <tr>
            <td><strong>Ground Distance</strong></td>
            <td>${res.experiment_a.distance_m ? res.experiment_a.distance_m.toFixed(1) + ' m' : '—'}</td>
            <td>${res.experiment_b.distance_m ? res.experiment_b.distance_m.toFixed(1) + ' m' : '—'}</td>
            <td><strong style="color:var(--telemetry-cyan);">${distDeltaStr}</strong></td>
          </tr>
          <tr>
            <td><strong>Active Traverse Time</strong></td>
            <td>${res.experiment_a.active_traverse_time_s ? formatDuration(res.experiment_a.active_traverse_time_s) : '—'}</td>
            <td>${res.experiment_b.active_traverse_time_s ? formatDuration(res.experiment_b.active_traverse_time_s) : '—'}</td>
            <td><strong style="color:var(--telemetry-cyan);">${timeDeltaStr}</strong></td>
          </tr>
          <tr>
            <td><strong>Terrain Effort</strong></td>
            <td>${res.experiment_a.terrain_cost_flat_m ? res.experiment_a.terrain_cost_flat_m.toFixed(1) + ' flat-m' : '—'}</td>
            <td>${res.experiment_b.terrain_cost_flat_m ? res.experiment_b.terrain_cost_flat_m.toFixed(1) + ' flat-m' : '—'}</td>
            <td><strong style="color:var(--telemetry-cyan);">${effortDeltaStr}</strong></td>
          </tr>
          <tr>
            <td><strong>Scientific Harvest</strong></td>
            <td>${res.experiment_a.science_score ? res.experiment_a.science_score.toFixed(1) + ' pts' : '—'}</td>
            <td>${res.experiment_b.science_score ? res.experiment_b.science_score.toFixed(1) + ' pts' : '—'}</td>
            <td><strong style="color:var(--telemetry-cyan);">${sciDeltaStr}</strong></td>
          </tr>
          <tr>
            <td><strong>Evaluated Scenarios</strong></td>
            <td>${res.experiment_a.num_scenarios} scenarios</td>
            <td>${res.experiment_b.num_scenarios} scenarios</td>
            <td>—</td>
          </tr>
        `;
      }

      if (compareTradeOffsList) {
        compareTradeOffsList.innerHTML = '';
        (res.trade_offs_summary || []).forEach(item => {
          const div = document.createElement('div');
          div.innerHTML = `&bull; ${item}`;
          compareTradeOffsList.appendChild(div);
        });
      }

      if (compareResultsContainer) compareResultsContainer.classList.remove('hidden');
      setPlanningStatus(`EXPERIMENT COMPARISON COMPLETE: ${res.experiment_a.name} vs ${res.experiment_b.name}`, "success");
      return res;
    } catch (err) {
      setPlanningStatus(`Comparison calculation failed: ${err.message}`, "error");
      return null;
    }
  }
"""

if "saveCurrentMission" not in text:
    target_needle_func = "function setupEventListeners() {"
    assert target_needle_func in text, "Could not find setupEventListeners needle"
    text = text.replace(target_needle_func, workspace_funcs + "\n  " + target_needle_func)

# 3. Add Event Listeners inside setupEventListeners
event_listeners_block = """
    // Milestone 9K: Workspace & Experiment Library Listeners
    if (btnSaveMission) btnSaveMission.addEventListener('click', () => saveCurrentMission());
    if (btnOpenMissionLibrary) {
      btnOpenMissionLibrary.addEventListener('click', () => {
        refreshMissionLibraryTable();
        if (missionLibraryModal) missionLibraryModal.classList.remove('hidden');
      });
    }
    if (btnCloseMissionLibrary) {
      btnCloseMissionLibrary.addEventListener('click', () => {
        if (missionLibraryModal) missionLibraryModal.classList.add('hidden');
      });
    }
    if (btnSaveExperiment) btnSaveExperiment.addEventListener('click', () => saveCurrentExperiment());
    if (btnOpenExperimentLibrary) {
      btnOpenExperimentLibrary.addEventListener('click', () => {
        refreshExperimentLibraryTable();
        if (experimentLibraryModal) experimentLibraryModal.classList.remove('hidden');
      });
    }
    if (btnCloseExperimentLibrary) {
      btnCloseExperimentLibrary.addEventListener('click', () => {
        if (experimentLibraryModal) experimentLibraryModal.classList.add('hidden');
      });
    }
    if (btnOpenCompareFromLib) btnOpenCompareFromLib.addEventListener('click', () => openExperimentComparisonModal());
    if (btnCloseExperimentComparison) {
      btnCloseExperimentComparison.addEventListener('click', () => {
        if (experimentComparisonModal) experimentComparisonModal.classList.add('hidden');
      });
    }
    if (btnExecuteCompare) btnExecuteCompare.addEventListener('click', () => executeExperimentComparison());

    if (fileImportMission) {
      fileImportMission.addEventListener('change', async (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        try {
          const text = await file.text();
          const resp = await fetch('/api/missions/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: text
          });
          const res = await resp.json();
          if (!resp.ok) throw new Error(res.message || res.error || `HTTP ${resp.status}`);
          setPlanningStatus(`MISSION IMPORTED: ${res.name} (ID: ${res.mission_id})`, "success");
          await refreshMissionLibraryTable();
        } catch (err) {
          setPlanningStatus(`Import failed: ${err.message}`, "error");
        }
      });
    }
"""

if "btnSaveMission.addEventListener" not in text:
    target_listener_needle = """    if (btnExportBriefingJson) {
      btnExportBriefingJson.addEventListener('click', () => exportMissionBriefing('json'));
    }"""
    assert target_listener_needle in text, "Could not find btnExportBriefingJson listener needle"
    text = text.replace(target_listener_needle, target_listener_needle + "\n\n" + event_listeners_block)

# 4. Mark unsaved on modifications in window.__atlas
atlas_target = """        setCustomGoal: (wp) => {
          customGoal = { row: wp.row, col: wp.col, id: wp.id, name: wp.name };
          if (goalPointVal) goalPointVal.textContent = wp.name;
          updateGoalMarker(wp.row, wp.col);
          populateAddStopDropdown();
          setSimulationStale(true);
        },"""

atlas_replacement = """        setCustomGoal: (wp) => {
          customGoal = { row: wp.row, col: wp.col, id: wp.id, name: wp.name };
          if (goalPointVal) goalPointVal.textContent = wp.name;
          updateGoalMarker(wp.row, wp.col);
          populateAddStopDropdown();
          setSimulationStale(true);
          setUnsavedChanges(true);
        },"""

if "setUnsavedChanges(true);" not in text:
    text = text.replace(atlas_target, atlas_replacement)

atlas_start_target = """        setCustomStart: (wp) => {
          customStart = { row: wp.row, col: wp.col, id: wp.id, name: wp.name };
          if (startPointVal) startPointVal.textContent = wp.name;
          updateStartMarker(wp.row, wp.col);
          populateAddStopDropdown();
          setSimulationStale(true);
        },"""

atlas_start_replacement = """        setCustomStart: (wp) => {
          customStart = { row: wp.row, col: wp.col, id: wp.id, name: wp.name };
          if (startPointVal) startPointVal.textContent = wp.name;
          updateStartMarker(wp.row, wp.col);
          populateAddStopDropdown();
          setSimulationStale(true);
          setUnsavedChanges(true);
        },"""

text = text.replace(atlas_start_target, atlas_start_replacement)

atlas_stop_target = """        addIntermediateStop: (wp) => {
          activeIntermediateStops.push(wp);
          renderActiveStopsList();
          populateAddStopDropdown();
          setSimulationStale(true);
        },"""

atlas_stop_replacement = """        addIntermediateStop: (wp) => {
          activeIntermediateStops.push(wp);
          renderActiveStopsList();
          populateAddStopDropdown();
          setSimulationStale(true);
          setUnsavedChanges(true);
        },"""

text = text.replace(atlas_stop_target, atlas_stop_replacement)

atlas_clear_target = """        clearIntermediateStops: () => {
          activeIntermediateStops = [];
          renderActiveStopsList();
          populateAddStopDropdown();
          setSimulationStale(true);
        }"""

atlas_clear_replacement = """        clearIntermediateStops: () => {
          activeIntermediateStops = [];
          renderActiveStopsList();
          populateAddStopDropdown();
          setSimulationStale(true);
          setUnsavedChanges(true);
        },
        // Milestone 9K: Persistent Mission Workspace & Experiment Library
        saveMission: (name) => saveCurrentMission(name),
        loadMission: (id) => loadMissionById(id),
        listMissions: () => fetch('/api/missions').then(r => r.json()),
        deleteMission: (id) => deleteMissionById(id),
        duplicateMission: (id) => duplicateMissionById(id),
        saveExperiment: (name) => saveCurrentExperiment(name),
        loadExperiment: (id) => viewExperimentById(id),
        listExperiments: () => fetch('/api/experiments').then(r => r.json()),
        replayExperiment: (id) => replayExperimentById(id),
        compareExperiments: (idA, idB) => executeExperimentComparison(idA, idB),
        getActiveMissionId: () => activeSavedMissionId,
        getActiveMissionName: () => activeSavedMissionName,
        hasUnsavedChanges: () => hasUnsavedChanges,
        getActiveHistoricalExperiment: () => activeHistoricalExperiment"""

text = text.replace(atlas_clear_target, atlas_clear_replacement)

APP_JS.write_text(text, encoding="utf-8")
print("web/app.js successfully updated with Milestone 9K workspace logic!")
