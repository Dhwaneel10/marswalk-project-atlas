# scripts/patch_index_html.py
import os

html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "index.html")

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update the tab switcher
old_str = """        <button id="btnTabCampaignSimulation" class="btn-picker-secondary" style="font-size:9.5px; padding:4px 12px; border-radius:3px; font-weight:600;">
          &#9201; Digital Twin &amp; Timeline
        </button>
      </div>"""

new_str = """        <button id="btnTabCampaignSimulation" class="btn-picker-secondary" style="font-size:9.5px; padding:4px 12px; border-radius:3px; font-weight:600;">
          &#9201; Digital Twin &amp; Timeline
        </button>
        <button id="btnTabCampaignAnalytics" class="btn-picker-secondary" style="font-size:9.5px; padding:4px 12px; border-radius:3px; font-weight:600;">
          &#128202; Performance Analytics &amp; Lessons Learned
        </button>
      </div>"""

if old_str in content:
    content = content.replace(old_str, new_str, 1)
    print("Tab button added.")
else:
    print("Warning: old_str for tab button not found.")

# 2. Add View 7
view_target = "      <!-- Bottom Disclaimer -->"

view_block = """      <!-- VIEW 7: Campaign Performance Analytics & Lessons Learned (Milestone 11G) -->
      <div id="campaignAnalyticsView" class="hidden">
        <!-- Controls & Action Toolbar -->
        <div style="padding:10px 12px; background:rgba(15,22,34,0.7); border:1px solid rgba(255,255,255,0.08); border-radius:4px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <div>
              <div style="font-size:8px; text-transform:uppercase; color:var(--text-secondary); letter-spacing:0.5px;">Campaign Performance Analytics &bull; Lessons Learned Engine</div>
              <div style="font-size:11px; font-weight:600; color:#fff; margin-top:2px;">Compare planned multi-sol sorties against simulated execution timelines, uncover root causes, and review grounded advisory recommendations.</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <button id="btnRunCampaignAnalytics" class="btn-primary" style="font-size:8.5px; padding:4px 10px; background:linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-color:#8b5cf6; font-weight:700;">
                &#9654; RUN PERFORMANCE ANALYSIS
              </button>
              <button id="btnExportAnalyticsJson" class="btn-secondary" style="font-size:8.5px; padding:4px 8px; border-color:rgba(139,92,246,0.4); color:#c4b5fd;" title="Export Campaign Analytics JSON Record">
                &#128190; EXPORT ANALYTICS JSON
              </button>
            </div>
          </div>
        </div>

        <!-- Executive Summary KPI Cards -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-bottom:12px;">
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Duration Delta</div>
            <div id="kpiDurationDelta" style="font-size:14px; font-weight:700; color:#fff; font-family:var(--font-mono); margin-top:2px;">--</div>
            <div id="kpiDurationSub" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">Planned: -- | Sim: --</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Target Completion</div>
            <div id="kpiTargetCompletion" style="font-size:14px; font-weight:700; color:#34d399; font-family:var(--font-mono); margin-top:2px;">--%</div>
            <div id="kpiTargetSub" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">0 of 0 Completed</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Fleet Utilization</div>
            <div id="kpiFleetUtilization" style="font-size:14px; font-weight:700; color:#38bdf8; font-family:var(--font-mono); margin-top:2px;">--%</div>
            <div id="kpiFleetSub" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">Active / Total Span</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Operational Holds</div>
            <div id="kpiOperationalHolds" style="font-size:14px; font-weight:700; color:#fbbf24; font-family:var(--font-mono); margin-top:2px;">0 (0.0s)</div>
            <div id="kpiHoldsSub" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">Non-productive dwell</div>
          </div>
          <div style="padding:8px 10px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:7.5px; text-transform:uppercase; color:var(--text-secondary);">Temporal Conflicts</div>
            <div id="kpiTemporalConflicts" style="font-size:14px; font-weight:700; color:#f87171; font-family:var(--font-mono); margin-top:2px;">0</div>
            <div id="kpiConflictsSub" style="font-size:7.5px; color:var(--text-tertiary); margin-top:1px;">Bottlenecks detected</div>
          </div>
        </div>

        <!-- 2-Column Split: Planned vs Simulated Sortie Deviations & Unit Workload Breakdown -->
        <div style="display:grid; grid-template-columns:1.1fr 0.9fr; gap:12px; margin-bottom:12px;">
          <!-- Sortie Deviations Table -->
          <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px; margin-bottom:6px;">
              &#128197; Sortie Timeline Slips (Planned vs Simulated)
            </div>
            <div style="max-height:220px; overflow-y:auto;">
              <table style="width:100%; border-collapse:collapse; font-size:8.5px; font-family:var(--font-mono);">
                <thead>
                  <tr style="border-bottom:1px solid rgba(255,255,255,0.1); color:var(--text-tertiary); text-align:left;">
                    <th style="padding:4px 6px;">Sortie</th>
                    <th style="padding:4px 6px;">Sol</th>
                    <th style="padding:4px 6px;">Planned Start</th>
                    <th style="padding:4px 6px;">Start Slip</th>
                    <th style="padding:4px 6px;">Duration &Delta;</th>
                    <th style="padding:4px 6px;">Status</th>
                  </tr>
                </thead>
                <tbody id="tblSortieDeviationsBody">
                  <tr><td colspan="6" style="padding:8px 6px; color:var(--text-tertiary); text-align:center;">Run performance analysis to inspect sortie timing slips.</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Unit Workloads Decomposition -->
          <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px;">
            <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px; margin-bottom:6px;">
              &#128101; Exploration Unit Workload &amp; Energy Decomposition
            </div>
            <div id="unitWorkloadContainer" style="display:flex; flex-direction:column; gap:8px; max-height:220px; overflow-y:auto;">
              <div style="font-size:8.5px; color:var(--text-tertiary); text-align:center; padding:12px 0;">No unit workload data loaded.</div>
            </div>
          </div>
        </div>

        <!-- Deviations & Root Cause Inspector -->
        <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px;">
              &#129504; Root Cause &amp; Deviation Diagnostic Inspector
            </div>
            <span id="deviationCountBadge" class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3); font-size:8px;">0 DEVIATIONS</span>
          </div>
          <div id="deviationsContainer" style="display:flex; flex-direction:column; gap:6px; max-height:200px; overflow-y:auto;">
            <div style="font-size:8.5px; color:var(--text-tertiary); text-align:center; padding:12px 0;">No deviations detected. Execution matches nominal campaign baseline.</div>
          </div>
        </div>

        <!-- Lessons Learned & Actionable Recommendations Center -->
        <div style="padding:10px 12px; background:rgba(15,22,34,0.6); border:1px solid rgba(255,255,255,0.08); border-radius:4px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="font-size:8.5px; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.5px;">
              &#128221; Lessons Learned &amp; Advisory Recommendations (Grounded Planning Changes)
            </div>
            <span id="recommendationsCountBadge" class="badge" style="background:rgba(99,102,241,0.15); color:#a5b4fc; border:1px solid rgba(99,102,241,0.3); font-size:8px;">0 RECOMMENDATIONS</span>
          </div>
          <div id="lessonsLearnedContainer" style="display:flex; flex-direction:column; gap:8px; max-height:260px; overflow-y:auto;">
            <div style="font-size:8.5px; color:var(--text-tertiary); text-align:center; padding:12px 0;">No lessons learned recommendations generated. Run analysis to produce advisory suggestions.</div>
          </div>
        </div>

        <!-- Limitations & Attribution Disclaimer -->
        <div style="margin-top:10px; padding:6px 8px; background:rgba(99,102,241,0.05); border:1px solid rgba(99,102,241,0.2); border-radius:3px; font-size:7.5px; color:#a5b4fc; line-height:1.3;">
          &bull; <strong>Campaign Performance Analytics Disclaimer:</strong> All metrics, deviations, causal classifications, and advisory recommendations are derived from deterministic planning simulation models. They do NOT represent live telemetry, certified flight hardware diagnostics, or autonomous operations.
        </div>
      </div>

"""

if view_target in content:
    content = content.replace(view_target, view_block + view_target, 1)
    print("View 7 added.")
else:
    print("Warning: view_target not found.")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated web/index.html.")
