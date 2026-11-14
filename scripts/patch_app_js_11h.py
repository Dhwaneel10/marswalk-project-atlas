# scripts/patch_app_js_11h.py
import os

app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "app.js")

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add DOM elements
dom_target = "  let playbackVehicleMesh = null;"
dom_block = """  // Milestone 11H: Campaign Design Space Explorer DOM Elements
  const btnTabCampaignDesignSpace = document.getElementById('btnTabCampaignDesignSpace');
  const campaignDesignSpaceView = document.getElementById('campaignDesignSpaceView');
  const btnRunDesignSpace = document.getElementById('btnRunDesignSpace');
  const btnExportDesignSpaceJson = document.getElementById('btnExportDesignSpaceJson');
  const dsMaxCandidatesInput = document.getElementById('dsMaxCandidatesInput');
  const dsProfileScienceCheck = document.getElementById('dsProfileScienceCheck');
  const dsProfileTimeCheck = document.getElementById('dsProfileTimeCheck');
  const dsProfileConservativeCheck = document.getElementById('dsProfileConservativeCheck');
  const dsDurationLimitsSelect = document.getElementById('dsDurationLimitsSelect');
  const dsMaxSolsSelect = document.getElementById('dsMaxSolsSelect');
  const kpiDsConsidered = document.getElementById('kpiDsConsidered');
  const kpiDsDeduplicated = document.getElementById('kpiDsDeduplicated');
  const kpiDsEvaluated = document.getElementById('kpiDsEvaluated');
  const kpiDsLimitStatus = document.getElementById('kpiDsLimitStatus');
  const kpiDsParetoCount = document.getElementById('kpiDsParetoCount');
  const kpiDsDominatedCount = document.getElementById('kpiDsDominatedCount');
  const kpiDsInfeasibleCount = document.getElementById('kpiDsInfeasibleCount');
  const kpiDsCompletenessBadge = document.getElementById('kpiDsCompletenessBadge');
  const dsScopeNotesText = document.getElementById('dsScopeNotesText');
  const canvasParetoPlot = document.getElementById('canvasParetoPlot');
  const tblDesignSpaceCandidatesBody = document.getElementById('tblDesignSpaceCandidatesBody');
  const dsCandidateDetailCard = document.getElementById('dsCandidateDetailCard');
  const dsSelectedCandidateTitle = document.getElementById('dsSelectedCandidateTitle');
  const dsSelectedDominanceBadge = document.getElementById('dsSelectedDominanceBadge');
  const dsSelectedCandidateContent = document.getElementById('dsSelectedCandidateContent');
  const btnPromoteCandidate = document.getElementById('btnPromoteCandidate');
  const dsRecommendationsContainer = document.getElementById('dsRecommendationsContainer');

  let currentDesignSpaceEvaluation = null;
  let selectedDesignSpaceCandidate = null;

"""

if dom_target in content:
    content = content.replace(dom_target, dom_block + dom_target, 1)
    print("DOM elements added.")
else:
    print("Warning: dom_target not found.")

# 2. Update switchCampaignTab
tab_target = "      { id: 'analytics', btn: btnTabCampaignAnalytics, view: campaignAnalyticsView }"
tab_replacement = """      { id: 'analytics', btn: btnTabCampaignAnalytics, view: campaignAnalyticsView },
      { id: 'design_space', btn: btnTabCampaignDesignSpace, view: campaignDesignSpaceView }"""

if tab_target in content:
    content = content.replace(tab_target, tab_replacement, 1)
    print("Tab switcher array updated.")
else:
    print("Warning: tab_target not found.")

tab_call_target = """      } else if (tab === 'analytics') {
        loadAndRenderCampaignAnalytics(currentCampaignPlan.campaign_id);
      }"""

tab_call_replacement = """      } else if (tab === 'analytics') {
        loadAndRenderCampaignAnalytics(currentCampaignPlan.campaign_id);
      } else if (tab === 'design_space') {
        loadAndRenderCampaignDesignSpace(currentCampaignPlan.campaign_id);
      }"""

if tab_call_target in content:
    content = content.replace(tab_call_target, tab_call_replacement, 1)
    print("Tab call routing updated.")
else:
    print("Warning: tab_call_target not found.")

# 3. Add Design Space functions
fn_target = "  async function runGauntletStressTest(scenarioIdParam = null) {"
fn_block = """  // Milestone 11H: Campaign Design Space Explorer Implementation
  async function loadAndRenderCampaignDesignSpace(campaignId) {
    if (!campaignId && currentCampaignPlan) campaignId = currentCampaignPlan.campaign_id;
    if (!campaignId) return;

    try {
      const resp = await fetch(`/api/campaign/design-spaces?campaign_id=${encodeURIComponent(campaignId)}`);
      if (resp.ok) {
        const evals = await resp.json();
        if (Array.isArray(evals) && evals.length > 0) {
          currentDesignSpaceEvaluation = evals[0];
          renderCampaignDesignSpaceView(currentDesignSpaceEvaluation);
          return;
        }
      }
      await runCampaignDesignSpaceExploration();
    } catch (err) {
      console.error('[MarsWalk Atlas] Error loading design space:', err);
    }
  }

  async function runCampaignDesignSpaceExploration() {
    if (!currentCampaignPlan) {
      setPlanningStatus("Please plan a campaign before running design space exploration.", "warning");
      return;
    }

    setPlanningStatus("EVALUATING CAMPAIGN DESIGN SPACE & PARETO FRONTIER...", "calculating");

    try {
      const maxCands = dsMaxCandidatesInput ? parseInt(dsMaxCandidatesInput.value, 10) || 10 : 10;
      const profiles = [];
      if (!dsProfileScienceCheck || dsProfileScienceCheck.checked) profiles.push('science_priority');
      if (!dsProfileTimeCheck || dsProfileTimeCheck.checked) profiles.push('time_constrained');
      if (!dsProfileConservativeCheck || dsProfileConservativeCheck.checked) profiles.push('conservative');
      if (profiles.length === 0) profiles.push('science_priority');

      let durLimits = [21600.0, 28800.0, 32400.0];
      if (dsDurationLimitsSelect) {
        const val = dsDurationLimitsSelect.value;
        if (val === 'conservative') durLimits = [21600.0, 28800.0];
        else if (val === 'expanded') durLimits = [28800.0, 36000.0];
      }

      let maxSols = [2, 3, 4];
      if (dsMaxSolsSelect) {
        const val = dsMaxSolsSelect.value;
        if (val === '3_4_5') maxSols = [3, 4, 5];
        else if (val === 'exact') maxSols = [currentCampaignPlan.config ? currentCampaignPlan.config.max_sols || 3 : 3];
      }

      const payload = {
        campaign_id: currentCampaignPlan.campaign_id,
        search_dimensions: {
          profiles: profiles,
          duration_limits_s: durLimits,
          max_sols_options: maxSols
        },
        search_bounds: {
          max_candidates: maxCands,
          max_planner_calls: maxCands + 4
        },
        persist: true
      };

      const resp = await fetch('/api/campaign/design-space/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.error || `HTTP ${resp.status}`);
      }

      currentDesignSpaceEvaluation = await resp.json();
      renderCampaignDesignSpaceView(currentDesignSpaceEvaluation);
      setPlanningStatus("Design space explored: Pareto frontier identified.", "success");
    } catch (err) {
      console.error('[MarsWalk Atlas] Error evaluating design space:', err);
      setPlanningStatus(`EXPLORATION FAILED: ${err.message || err}`, "error");
    }
  }

  function renderCampaignDesignSpaceView(evalData) {
    if (!evalData) return;

    // 1. Completeness & Summary KPIs
    const comp = evalData.search_completeness || {};
    const pareto = evalData.pareto_candidates || [];
    const dominated = evalData.dominated_candidates || [];
    const infeasible = evalData.infeasible_candidates || [];

    if (kpiDsConsidered) kpiDsConsidered.textContent = comp.candidates_considered || 0;
    if (kpiDsDeduplicated) kpiDsDeduplicated.textContent = `${comp.candidates_deduplicated || 0} Deduplicated`;
    if (kpiDsEvaluated) kpiDsEvaluated.textContent = comp.candidates_evaluated || 0;
    if (kpiDsLimitStatus) {
      kpiDsLimitStatus.textContent = comp.limit_reached ? "Limit Reached" : "Budget Preserved";
      kpiDsLimitStatus.style.color = comp.limit_reached ? "#fbbf24" : "var(--text-tertiary)";
    }
    if (kpiDsParetoCount) kpiDsParetoCount.textContent = `${pareto.length} EFFICIENT`;
    if (kpiDsDominatedCount) kpiDsDominatedCount.textContent = `${dominated.length} Dominated`;
    if (kpiDsInfeasibleCount) kpiDsInfeasibleCount.textContent = infeasible.length;
    if (kpiDsCompletenessBadge) {
      kpiDsCompletenessBadge.textContent = comp.is_exhaustive ? "EXHAUSTIVE" : "BOUNDED";
      kpiDsCompletenessBadge.style.color = comp.is_exhaustive ? "#34d399" : "#fbbf24";
    }
    if (dsScopeNotesText) {
      dsScopeNotesText.textContent = comp.unexplored_scope_notes || "All bounded configurations evaluated.";
      dsScopeNotesText.title = comp.unexplored_scope_notes || "";
    }

    // 2. Draw 2D Pareto Scatter Plot
    drawParetoScatterPlot(evalData);

    // 3. Populate Candidate Comparison Table
    if (tblDesignSpaceCandidatesBody) {
      const allCands = [...pareto, ...dominated, ...infeasible];
      if (allCands.length === 0) {
        tblDesignSpaceCandidatesBody.innerHTML = '<tr><td colspan="7" style="padding:8px 6px; color:var(--text-tertiary); text-align:center;">No candidates evaluated.</td></tr>';
      } else {
        tblDesignSpaceCandidatesBody.innerHTML = allCands.map(c => {
          const objs = c.objectives || {};
          const cov = objs.science_coverage_pct !== undefined ? `${objs.science_coverage_pct}%` : '--';
          const durH = objs.total_duration_s ? `${(objs.total_duration_s / 3600).toFixed(1)}h` : '--';
          const distKm = objs.total_distance_m ? `${(objs.total_distance_m / 1000).toFixed(1)}km` : '--';

          let domBadge = '';
          if (c.dominance_status === 'PARETO_EFFICIENT') {
            domBadge = '<span class="badge" style="background:rgba(16,185,129,0.2); color:#34d399; border:1px solid rgba(16,185,129,0.4); font-size:7.5px;">PARETO</span>';
          } else if (c.dominance_status === 'DOMINATED') {
            domBadge = '<span class="badge" style="background:rgba(255,255,255,0.08); color:#9ca3af; font-size:7.5px;">DOMINATED</span>';
          } else {
            domBadge = '<span class="badge" style="background:rgba(239,68,68,0.2); color:#f87171; border:1px solid rgba(239,68,68,0.4); font-size:7.5px;">INFEASIBLE</span>';
          }

          const prof = (c.configuration && c.configuration.planning_profile) ? c.configuration.planning_profile : 'standard';

          return `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05); cursor:pointer;" class="ds-cand-row" data-cand-id="${escapeHtml(c.candidate_id)}">
              <td style="padding:4px 6px; color:#fff; font-weight:600;">${escapeHtml(c.candidate_id)}</td>
              <td style="padding:4px 6px; color:var(--text-secondary);">${escapeHtml(prof)}</td>
              <td style="padding:4px 6px; color:#34d399; font-weight:600;">${cov}</td>
              <td style="padding:4px 6px; color:#38bdf8;">${durH}</td>
              <td style="padding:4px 6px; color:#e2e8f0;">${distKm}</td>
              <td style="padding:4px 6px;">${domBadge}</td>
              <td style="padding:4px 6px;">
                <button class="btn-picker-secondary btn-inspect-cand" data-cand-id="${escapeHtml(c.candidate_id)}" style="font-size:7px; padding:2px 5px;">Inspect</button>
              </td>
            </tr>
          `;
        }).join('');

        // Wire click handlers on table rows
        tblDesignSpaceCandidatesBody.querySelectorAll('.ds-cand-row').forEach(row => {
          row.addEventListener('click', (e) => {
            const cid = e.currentTarget.getAttribute('data-cand-id');
            if (cid) selectDesignSpaceCandidate(cid);
          });
        });
      }
    }

    // 4. Populate Grounded Recommendations
    if (dsRecommendationsContainer) {
      const recs = evalData.recommendations || [];
      if (recs.length === 0) {
        dsRecommendationsContainer.innerHTML = '<div style="font-size:8.5px; color:var(--text-tertiary); text-align:center; padding:12px 0;">No frontier recommendations generated.</div>';
      } else {
        dsRecommendationsContainer.innerHTML = recs.map(r => {
          return `
            <div style="padding:6px 8px; background:rgba(0,0,0,0.3); border:1px solid rgba(6,182,212,0.25); border-radius:3px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="font-size:8.5px; color:#67e8f9;">${escapeHtml(r.headline)}</strong>
                <button class="btn-picker-secondary btn-inspect-cand" data-cand-id="${escapeHtml(r.candidate_id)}" style="font-size:7px; padding:1px 4px;">Select</button>
              </div>
              <div style="font-size:8px; color:#cbd5e1; margin-top:3px; line-height:1.3;">${escapeHtml(r.tradeoff_summary)}</div>
              <div style="font-size:7.5px; color:#34d399; margin-top:2px;">&bull; ${escapeHtml(r.selection_rationale)}</div>
            </div>
          `;
        }).join('');

        dsRecommendationsContainer.querySelectorAll('.btn-inspect-cand').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const cid = e.currentTarget.getAttribute('data-cand-id');
            if (cid) selectDesignSpaceCandidate(cid);
          });
        });
      }
    }

    // Select first Pareto candidate by default
    if (pareto.length > 0) {
      selectDesignSpaceCandidate(pareto[0].candidate_id);
    } else if (dominated.length > 0) {
      selectDesignSpaceCandidate(dominated[0].candidate_id);
    }
  }

  function drawParetoScatterPlot(evalData) {
    if (!canvasParetoPlot) return;
    const ctx = canvasParetoPlot.getContext('2d');
    const width = canvasParetoPlot.width;
    const height = canvasParetoPlot.height;

    ctx.clearRect(0, 0, width, height);

    const pareto = evalData.pareto_candidates || [];
    const dominated = evalData.dominated_candidates || [];
    const infeasible = evalData.infeasible_candidates || [];
    const allCands = [...pareto, ...dominated, ...infeasible];

    if (allCands.length === 0) {
      ctx.fillStyle = "#9ca3af";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("No candidate data to plot", width / 2, height / 2);
      return;
    }

    // Compute bounding boxes for Duration (X) and Science Coverage (Y)
    let minDurH = Infinity, maxDurH = -Infinity;
    let minCov = 0.0, maxCov = 100.0;

    allCands.forEach(c => {
      const dH = (c.objectives && c.objectives.total_duration_s) ? c.objectives.total_duration_s / 3600.0 : 0;
      if (dH > 0) {
        if (dH < minDurH) minDurH = dH;
        if (dH > maxDurH) maxDurH = dH;
      }
    });

    if (minDurH === Infinity) { minDurH = 4.0; maxDurH = 12.0; }
    minDurH = Math.max(0, minDurH - 1.0);
    maxDurH = maxDurH + 1.0;

    const padLeft = 40, padRight = 20, padTop = 20, padBottom = 25;
    const plotW = width - padLeft - padRight;
    const plotH = height - padTop - padBottom;

    // Helper coordinates mapper
    const toX = (durH) => padLeft + ((durH - minDurH) / Math.max(0.1, maxDurH - minDurH)) * plotW;
    const toY = (cov) => padTop + (1.0 - (cov - minCov) / Math.max(1.0, maxCov - minCov)) * plotH;

    // Draw Grid Lines & Axes
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;

    // Horizontal grid lines (0%, 25%, 50%, 75%, 100%)
    [0, 25, 50, 75, 100].forEach(covVal => {
      const y = toY(covVal);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();

      ctx.fillStyle = "#9ca3af";
      ctx.font = "7.5px monospace";
      ctx.textAlign = "right";
      ctx.fillText(`${covVal}%`, padLeft - 4, y + 3);
    });

    // Vertical grid lines for duration
    const durStep = Math.max(1, Math.round((maxDurH - minDurH) / 4));
    for (let d = Math.ceil(minDurH); d <= maxDurH; d += durStep) {
      const x = toX(d);
      ctx.beginPath();
      ctx.moveTo(x, padTop);
      ctx.lineTo(x, height - padBottom);
      ctx.stroke();

      ctx.fillStyle = "#9ca3af";
      ctx.font = "7.5px monospace";
      ctx.textAlign = "center";
      ctx.fillText(`${d}h`, x, height - padBottom + 12);
    }

    // Axis Labels
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "8px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Duration (hours)", padLeft + plotW / 2, height - 2);

    ctx.save();
    ctx.translate(10, padTop + plotH / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText("Science Coverage (%)", 0, 0);
    ctx.restore();

    // Draw Pareto Frontier step curve
    if (pareto.length > 1) {
      const sortedP = [...pareto].sort((a, b) => a.objectives.total_duration_s - b.objectives.total_duration_s);
      ctx.strokeStyle = "rgba(52, 211, 153, 0.7)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      sortedP.forEach((p, idx) => {
        const px = toX(p.objectives.total_duration_s / 3600.0);
        const py = toY(p.objectives.science_coverage_pct);
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 1. Draw Dominated Points (Gray circles)
    dominated.forEach(c => {
      const cx = toX(c.objectives.total_duration_s / 3600.0);
      const cy = toY(c.objectives.science_coverage_pct);
      ctx.fillStyle = "rgba(156, 163, 175, 0.6)";
      ctx.beginPath();
      ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
      ctx.fill();
    });

    // 2. Draw Infeasible Points (Red cross)
    infeasible.forEach(c => {
      const cx = toX((c.objectives.total_duration_s || 0) / 3600.0);
      const cy = toY(c.objectives.science_coverage_pct || 0);
      ctx.strokeStyle = "rgba(248, 113, 113, 0.8)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(cx - 3, cy - 3); ctx.lineTo(cx + 3, cy + 3);
      ctx.moveTo(cx + 3, cy - 3); ctx.lineTo(cx - 3, cy + 3);
      ctx.stroke();
    });

    // 3. Draw Pareto Points (Emerald / Cyan glowing circles)
    pareto.forEach(c => {
      const cx = toX(c.objectives.total_duration_s / 3600.0);
      const cy = toY(c.objectives.science_coverage_pct);

      ctx.fillStyle = "#34d399";
      ctx.beginPath();
      ctx.arc(cx, cy, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }

  function selectDesignSpaceCandidate(candidateId) {
    if (!currentDesignSpaceEvaluation) return;
    const allCands = [
      ...(currentDesignSpaceEvaluation.pareto_candidates || []),
      ...(currentDesignSpaceEvaluation.dominated_candidates || []),
      ...(currentDesignSpaceEvaluation.infeasible_candidates || [])
    ];

    const cand = allCands.find(c => c.candidate_id === candidateId);
    if (!cand) return;

    selectedDesignSpaceCandidate = cand;

    if (dsSelectedCandidateTitle) {
      dsSelectedCandidateTitle.textContent = `${cand.candidate_id} (${cand.configuration ? cand.configuration.planning_profile || 'baseline' : 'candidate'})`;
    }

    if (dsSelectedDominanceBadge) {
      if (cand.dominance_status === 'PARETO_EFFICIENT') {
        dsSelectedDominanceBadge.textContent = 'PARETO EFFICIENT';
        dsSelectedDominanceBadge.style.background = 'rgba(16,185,129,0.2)';
        dsSelectedDominanceBadge.style.color = '#34d399';
        dsSelectedDominanceBadge.style.border = '1px solid rgba(16,185,129,0.4)';
      } else if (cand.dominance_status === 'DOMINATED') {
        dsSelectedDominanceBadge.textContent = 'DOMINATED';
        dsSelectedDominanceBadge.style.background = 'rgba(255,255,255,0.08)';
        dsSelectedDominanceBadge.style.color = '#9ca3af';
        dsSelectedDominanceBadge.style.border = '1px solid rgba(255,255,255,0.15)';
      } else {
        dsSelectedDominanceBadge.textContent = 'INFEASIBLE';
        dsSelectedDominanceBadge.style.background = 'rgba(239,68,68,0.2)';
        dsSelectedDominanceBadge.style.color = '#f87171';
        dsSelectedDominanceBadge.style.border = '1px solid rgba(239,68,68,0.4)';
      }
    }

    if (dsSelectedCandidateContent) {
      const objs = cand.objectives || {};
      const cfg = cand.configuration || {};
      const durH = objs.total_duration_s ? (objs.total_duration_s / 3600.0).toFixed(1) : '--';
      const distKm = objs.total_distance_m ? (objs.total_distance_m / 1000.0).toFixed(2) : '--';

      let infHtml = '';
      if (cand.infeasibility_reasons && cand.infeasibility_reasons.length > 0) {
        infHtml = `<div style="margin-top:6px; padding:4px 6px; background:rgba(239,68,68,0.1); border-left:2px solid #ef4444; color:#f87171; font-size:7.5px;"><strong>Infeasibility:</strong> ${cand.infeasibility_reasons.map(r => escapeHtml(r)).join('; ')}</div>`;
      }

      dsSelectedCandidateContent.innerHTML = `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-family:var(--font-mono); font-size:8px;">
          <div>Coverage: <span style="color:#34d399; font-weight:700;">${objs.science_coverage_pct}%</span></div>
          <div>Duration: <span style="color:#38bdf8; font-weight:700;">${durH}h</span></div>
          <div>Traverse: <span style="color:#e2e8f0;">${distKm}km</span></div>
          <div>Sorties: <span style="color:#e2e8f0;">${objs.sortie_count} Sols</span></div>
        </div>
        <div style="font-size:8px; color:#cbd5e1; margin-top:6px; line-height:1.3;">
          ${escapeHtml(cand.tradeoff_explanation || '')}
        </div>
        ${infHtml}
        <details style="margin-top:6px;">
          <summary style="font-size:7.5px; color:#38bdf8; cursor:pointer; font-family:var(--font-mono);">Configuration Delta</summary>
          <pre style="margin-top:2px; padding:4px 6px; background:rgba(0,0,0,0.5); border-radius:2px; font-size:7.5px; font-family:var(--font-mono); color:#e2e8f0; overflow-x:auto;">${escapeHtml(JSON.stringify(cfg, null, 2))}</pre>
        </details>
      `;
    }

    if (btnPromoteCandidate) {
      if (cand.status === 'FEASIBLE') {
        btnPromoteCandidate.disabled = false;
        btnPromoteCandidate.style.opacity = '1.0';
        btnPromoteCandidate.style.cursor = 'pointer';
      } else {
        btnPromoteCandidate.disabled = true;
        btnPromoteCandidate.style.opacity = '0.4';
        btnPromoteCandidate.style.cursor = 'not-allowed';
      }
    }
  }

  async function promoteSelectedCandidateAction() {
    if (!currentDesignSpaceEvaluation || !selectedDesignSpaceCandidate) return;
    if (selectedDesignSpaceCandidate.status !== 'FEASIBLE') {
      setPlanningStatus("Cannot promote an infeasible candidate.", "error");
      return;
    }

    setPlanningStatus(`PROMOTING CANDIDATE ${selectedDesignSpaceCandidate.candidate_id} TO NEW CAMPAIGN VERSION...`, "calculating");

    try {
      const payload = {
        design_space_id: currentDesignSpaceEvaluation.design_space_id,
        candidate_id: selectedDesignSpaceCandidate.candidate_id,
        new_campaign_name: `${currentCampaignPlan.name} (Pareto Optimized)`
      };

      const resp = await fetch('/api/campaign/design-space/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.error || `HTTP ${resp.status}`);
      }

      const resData = await resp.json();
      currentCampaignPlan = resData.campaign;
      renderCampaignPlanningView(currentCampaignPlan);
      setPlanningStatus(`SUCCESS: Promoted to Campaign Version ${resData.new_version} (${resData.new_campaign_id}). Baseline preserved.`, "success");
    } catch (err) {
      console.error('[MarsWalk Atlas] Error promoting candidate:', err);
      setPlanningStatus(`PROMOTION FAILED: ${err.message || err}`, "error");
    }
  }

  function exportDesignSpaceJson() {
    if (!currentDesignSpaceEvaluation) {
      setPlanningStatus("No active design space evaluation to export.", "warning");
      return;
    }

    const blob = new Blob([JSON.stringify(currentDesignSpaceEvaluation, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `campaign_design_space_${currentDesignSpaceEvaluation.design_space_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setPlanningStatus("Exported Campaign Design Space JSON.", "success");
  }

"""

if fn_target in content:
    content = content.replace(fn_target, fn_block + fn_target, 1)
    print("Design Space functions added.")
else:
    print("Warning: fn_target not found.")

# 4. Add Event Listeners
listener_target = "    // Milestone 11G: Campaign Performance Analytics Listeners"
listener_block = """    // Milestone 11H: Campaign Design Space Listeners
    if (btnTabCampaignDesignSpace) {
      btnTabCampaignDesignSpace.addEventListener('click', () => switchCampaignTab('design_space'));
    }
    if (btnRunDesignSpace) {
      btnRunDesignSpace.addEventListener('click', runCampaignDesignSpaceExploration);
    }
    if (btnExportDesignSpaceJson) {
      btnExportDesignSpaceJson.addEventListener('click', exportDesignSpaceJson);
    }
    if (btnPromoteCandidate) {
      btnPromoteCandidate.addEventListener('click', promoteSelectedCandidateAction);
    }

"""

if listener_target in content:
    content = content.replace(listener_target, listener_block + listener_target, 1)
    print("Listeners added.")
else:
    print("Warning: listener_target not found.")

# 5. Expose on window.MarsWalkAtlas
api_target = "        getCampaignAnalysis: () => currentCampaignAnalysis,\n        exportCampaignAnalytics: () => exportCampaignAnalyticsJson()"
api_replacement = """        getCampaignAnalysis: () => currentCampaignAnalysis,
        exportCampaignAnalytics: () => exportCampaignAnalyticsJson(),
        // Milestone 11H: Campaign Design Space API
        exploreDesignSpace: () => runCampaignDesignSpaceExploration(),
        getDesignSpace: () => currentDesignSpaceEvaluation,
        promoteCandidate: () => promoteSelectedCandidateAction(),
        exportDesignSpace: () => exportDesignSpaceJson()"""

if api_target in content:
    content = content.replace(api_target, api_replacement, 1)
    print("Public API exposed.")
else:
    print("Warning: api_target not found.")

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated web/app.js with Milestone 11H logic.")
