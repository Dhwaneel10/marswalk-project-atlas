# scripts/patch_index_html_11h.py
import os

html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html")

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the tab switcher
old_btn = """        <button id="btnTabCampaignAnalytics" class="btn-picker-secondary" style="font-size:9.5px; padding:4px 12px; border-radius:3px; font-weight:600;">
          &#128202; Performance Analytics &amp; Lessons Learned
        </button>
      </div>"""

new_btn = """        <button id="btnTabCampaignAnalytics" class="btn-picker-secondary" style="font-size:9.5px; padding:4px 12px; border-radius:3px; font-weight:600;">
          &#128202; Performance Analytics &amp; Lessons Learned
        </button>
        <button id="btnTabCampaignDesignSpace" class="btn-picker-secondary" style="font-size:9.5px; padding:4px 12px; border-radius:3px; font-weight:600;">
          &#127919; Design Space &amp; Pareto Explorer
        </button>
      </div>"""

if old_btn in content:
    content = content.replace(old_btn, new_btn, 1)
    print("Tab button added.")
else:
    print("Warning: old_btn not found.")

# 2. Add View 8
view_target = "      <!-- Bottom Disclaimer -->"

view_block = """      <!-- VIEW 8: Campaign Design Space Explorer & Pareto Optimization (Milestone 11H) -->
      <div id="campaignDesignSpaceView" class="hidden">
        <!-- Controls & Search Bounds Toolbar -->
        <div style="padding:10px 12px; background:rgba(15,22,34,0.7); border:1px solid rgba(255,255,255,0.08); border-radius:4px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
              <div style="font-size:8px; text-transform:uppercase; color:var(--text-secondary); letter-spacing:0.5px;">Campaign Design Space Explorer &bull; Pareto Frontier Multi-Objective Optimization</div>
              <div style="font-size:11px; font-weight:600; color:#fff; margin-top:2px;">Evaluate bounded alternative campaign configurations, extract Pareto-efficient trade-offs, and promote optimal revisions.</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <button id="btnRunDesignSpace" class="btn-primary" style="font-size:8.5px; padding:4px 10px; background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%); border-color:#06b6d4; font-weight:700;">
                &#9654; EXPLORE DESIGN SPACE
              </button>
              <button id="btnExportDesignSpaceJson" class="btn-secondary" style="font-size:8.5px; padding:4px 8px; border-color:rgba(6,182,212,0.4); color:#67e8f9;" title="Export Design Space & Pareto Analysis JSON">
                &#128190; EXPORT DESIGN SPACE JSON
              </button>
            </div>
          </div>

          <!-- Exploration Configuration Bar -->
          <div style="display:flex; gap:14px; align-items:center; flex-wrap:wrap; margin-top:10px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.05); font-size:8.5px;">
            <div style="display:flex; align-items:center; gap:4px;">
              <label for="dsMaxCandidatesInput" style="color:var(--text-secondary); text-transform:uppercase;">Max Candidates:</label>
              <input type="number" id="dsMaxCandidatesInput" value="10" min="2" max="25" step="1" style="width:45px; font-size:9.5px; padding:2px 5px; background:rgba(0,0,0,0.4); border:1px solid var(--border-subtle); color:#fff; border-radius:3px;">
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="color:var(--text-secondary); text-transform:uppercase;">Profiles:</span>
              <label style="color:#e2e8f0; display:flex; align-items:center; gap:3px;"><input type="checkbox" id="dsProfileScienceCheck" checked> Science</label>
              <label style="color:#e2e8f0; display:flex; align-items:center; gap:3px;"><input type="checkbox" id="dsProfileTimeCheck" checked> Time</label>
              <label style="color:#e2e8f0; display:flex; align-items:center; gap:3px;"><input type="checkbox" id="dsProfileConservativeCheck" checked> Conservative</label>
            </div>
            <div style="display:flex; align-items:center; gap:4px;">
              <label for="dsDurationLimitsSelect" style="color:var(--text-secondary); text-transform:uppercase;">Duration Limits:</label>
              <select id="dsDurationLimitsSelect" class="hud-select" style="font-size:9px; padding:2px 6px;">
                <option value="standard">6h, 8h, 9h (Multi-Tier)</option>
                <option value="conservative">6h, 8h (Conservative)</option>
                <option value="expanded">8h, 10h (Long Duration)</option>
              </select>
            </div>
            <div style="display:flex; align-items:center; gap:4px;">
              <label for="dsMaxSolsSelect" style="color:var(--text-secondary); text-transform:uppercase;">Max Sols:</label>
              <select id="dsMaxSolsSelect" class="hud-select" style="font-size:9px; padding:2px 6px;">
                <option value="2_3_4">2, 3, 4 Sols</option>
                <option value="3_4_5">3, 4, 5 Sols</option>
                <option value="exact">Keep Baseline Sols</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Search Completeness & Summary KPI Banners -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:12px;">
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Candidates Considered</div>
            <div id="kpiDsConsidered" style="font-size:14px; font-weight:700; color:#fff; font-family:var(--font-mono); margin-top:2px;">0</div>
            <div id="kpiDsDeduplicated" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">0 Deduplicated</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Evaluated Candidates</div>
            <div id="kpiDsEvaluated" style="font-size:14px; font-weight:700; color:#38bdf8; font-family:var(--font-mono); margin-top:2px;">0</div>
            <div id="kpiDsLimitStatus" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">Within Bounds</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Pareto Frontier</div>
            <div id="kpiDsParetoCount" style="font-size:14px; font-weight:700; color:#34d399; font-family:var(--font-mono); margin-top:2px;">0 EFFICIENT</div>
            <div id="kpiDsDominatedCount" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">0 Dominated</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Infeasible Rejections</div>
            <div id="kpiDsInfeasibleCount" style="font-size:14px; font-weight:700; color:#f87171; font-family:var(--font-mono); margin-top:2px;">0</div>
            <div style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">Violated Constraints</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Search Scope</div>
            <div id="kpiDsCompletenessBadge" style="font-size:11px; font-weight:700; color:#fbbf24; font-family:var(--font-mono); margin-top:3px;">BOUNDED</div>
            <div id="dsScopeNotesText" style="font-size:7px; color:var(--text-tertiary); margin-top:2px; line-height:1.2; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">No exploration active</div>
          </div>
        </div>

        <!-- 2-Column Split: Visual Scatter Plot & Candidate Table vs Inspector & Recommendations -->
        <div style="display:grid; grid-template-columns:1.2fr 0.8fr; gap:12px; margin-bottom:12px;">
          <!-- Left Column: 2D Pareto Scatter Plot & Candidate Comparison Table -->
          <div style="display:flex; flex-direction:column; gap:10px;">
            <!-- 2D Pareto Scatter Plot Canvas -->
            <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px;">
                  &#128200; Multi-Objective Trade-Off Scatter (Duration vs Science Coverage)
                </div>
                <div style="display:flex; gap:8px; font-size:7.5px;">
                  <span style="color:#34d399;">&#9679; Pareto Frontier</span>
                  <span style="color:#9ca3af;">&#9679; Dominated</span>
                  <span style="color:#f87171;">&#9679; Infeasible</span>
                </div>
              </div>
              <canvas id="canvasParetoPlot" width="480" height="190" style="width:100%; height:190px; background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.05); border-radius:3px; display:block;"></canvas>
            </div>

            <!-- Candidate Comparison Table -->
            <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
              <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px; margin-bottom:6px;">
                &#128196; Evaluated Campaign Configurations
              </div>
              <div style="max-height:210px; overflow-y:auto;">
                <table style="width:100%; border-collapse:collapse; font-size:8.5px; font-family:var(--font-mono);">
                  <thead>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1); color:var(--text-tertiary); text-align:left;">
                      <th style="padding:4px 6px;">Candidate</th>
                      <th style="padding:4px 6px;">Profile</th>
                      <th style="padding:4px 6px;">Coverage</th>
                      <th style="padding:4px 6px;">Duration</th>
                      <th style="padding:4px 6px;">Distance</th>
                      <th style="padding:4px 6px;">Dominance</th>
                      <th style="padding:4px 6px;">Action</th>
                    </tr>
                  </thead>
                  <tbody id="tblDesignSpaceCandidatesBody">
                    <tr><td colspan="7" style="padding:8px 6px; color:var(--text-tertiary); text-align:center;">Click 'EXPLORE DESIGN SPACE' to evaluate alternative campaign candidates.</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Right Column: Selected Candidate Inspector & Grounded Recommendations -->
          <div style="display:flex; flex-direction:column; gap:10px;">
            <!-- Candidate Detail Inspector Card -->
            <div id="dsCandidateDetailCard" style="padding:10px 12px; background:rgba(15,22,34,0.7); border:1px solid rgba(6,182,212,0.3); border-radius:4px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span id="dsSelectedCandidateTitle" style="font-size:10px; font-weight:700; color:#fff;">Candidate Detail Inspector</span>
                <span id="dsSelectedDominanceBadge" class="badge" style="background:rgba(255,255,255,0.08); color:#d1d5db; font-size:7.5px;">NO SELECTION</span>
              </div>
              <div id="dsSelectedCandidateContent" style="margin-top:6px; font-size:8.5px; color:#cbd5e1; line-height:1.4;">
                Select a candidate from the table or scatter plot to inspect multi-objective trade-offs, feasibility findings, and configuration deltas.
              </div>
              <button id="btnPromoteCandidate" class="btn-primary" style="margin-top:10px; width:100%; font-size:9px; padding:5px 10px; background:linear-gradient(135deg, #059669 0%, #10b981 100%); border-color:#10b981; font-weight:700;" disabled>
                &#128640; PROMOTE CANDIDATE TO NEW CAMPAIGN VERSION
              </button>
            </div>

            <!-- Grounded Trade-off Recommendations Center -->
            <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px; flex:1;">
              <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px; margin-bottom:6px;">
                &#129504; Grounded Frontier Trade-Off Rationales
              </div>
              <div id="dsRecommendationsContainer" style="display:flex; flex-direction:column; gap:6px; max-height:220px; overflow-y:auto;">
                <div style="font-size:8.5px; color:var(--text-tertiary); text-align:center; padding:12px 0;">No frontier recommendations generated. Run exploration to evaluate alternatives.</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Limitations & Reality Disclaimer -->
        <div style="margin-top:10px; padding:6px 8px; background:rgba(6,182,212,0.05); border:1px solid rgba(6,182,212,0.2); border-radius:3px; font-size:7.5px; color:#67e8f9; line-height:1.3;">
          &bull; <strong>Design Space Explorer Disclaimer:</strong> The Campaign Design Space Explorer is a deterministic multi-objective evaluation tool for simulated Mars mission evaluation. It does NOT guarantee global mathematical optimality, employ probabilistic forecasting, or represent certified flight operations software. All candidate trade-offs are grounded in simulated route planning across authentic USGS CTX 20m topography.
        </div>
      </div>

"""

if view_target in content:
    content = content.replace(view_target, view_block + view_target, 1)
    print("View 8 added.")
else:
    print("Warning: view_target not found.")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated web/index.html with Milestone 11H UI.")
