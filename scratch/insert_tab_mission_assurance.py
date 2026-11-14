# Insert #tabMissionAssurance into web/index.html
from pathlib import Path

index_html = Path("web/index.html")
content = index_html.read_text(encoding="utf-8")

target = """              <button id="btnMoccPromotePlan" class="btn-primary mocc-btn-promote">&#128640; Approve &amp; Promote Plan</button>
            </div>
          </div>
        </div>
      </div>"""

# Test if target in content
if target not in content:
    # Try with CRLF
    target = target.replace("\n", "\r\n")
    if target not in content:
        raise ValueError("Target not found in index.html!")

panel_html = """

      <!-- TAB: MISSION ASSURANCE & COUNTERFACTUAL OPERATIONS LAB -->
      <div id="tabMissionAssurance" class="inspector-tab-panel assurance-panel hidden">
        <!-- Top Toolbar & Status Deck -->
        <div class="assurance-toolbar-deck">
          <div class="assurance-toolbar-left">
            <span class="assurance-badge">&#128737; MISSION ASSURANCE LAB</span>
            <select id="assuranceCampaignSelect" class="assurance-select" title="Active Campaign Target">
              <option value="jezero_western_delta_campaign">Jezero Western Delta 5-Sol Campaign</option>
              <option value="neretva_vallis_traverse">Neretva Vallis Traverse Campaign</option>
            </select>
            <span id="assuranceBranchBadge" class="assurance-status-pill pill-active">Branch: main (v1)</span>
          </div>
          <div class="assurance-toolbar-actions">
            <button id="btnAssuranceEvaluate" class="btn-primary assurance-btn-audit" title="Run 20-Rule Invariant Audit">&#9989; Audit Invariants</button>
            <button id="btnAssuranceRobustness" class="btn-secondary assurance-btn-stress" title="Run Multi-Scenario Stress Matrix">&#128293; Stress Test</button>
            <button id="btnAssuranceDossier" class="btn-secondary assurance-btn-dossier" title="Generate Cryptographic Dossier">&#128272; Merkle Dossier</button>
            <button id="btnAssuranceReset" class="btn-secondary" title="Reset Branch to Clean Root">&#128260; Reset</button>
          </div>
        </div>

        <!-- Mission Assurance KPI & HUD Deck -->
        <div class="assurance-hud-deck">
          <div class="assurance-hud-card">
            <span class="assurance-hud-label">ASSURANCE VERDICT</span>
            <strong id="hudAssuranceVerdict" class="assurance-hud-val text-emerald">PASS</strong>
            <span class="assurance-hud-sub" id="hudAssuranceVerdictSub">20 / 20 Invariants Verified</span>
          </div>
          <div class="assurance-hud-card">
            <span class="assurance-hud-label">BRANCH LINEAGE</span>
            <strong id="hudAssuranceBranch" class="assurance-hud-val text-cyan">main</strong>
            <span class="assurance-hud-sub" id="hudAssuranceBranchSub">Root Campaign &bull; Immutable Parent</span>
          </div>
          <div class="assurance-hud-card">
            <span class="assurance-hud-label">ROBUSTNESS SCORE</span>
            <strong id="hudAssuranceRobustness" class="assurance-hud-val text-emerald">94.8%</strong>
            <span class="assurance-hud-sub" id="hudAssuranceRobustnessSub">12 / 12 Scenarios Feasible</span>
          </div>
          <div class="assurance-hud-card">
            <span class="assurance-hud-label">VIOLATIONS DETECTED</span>
            <strong id="hudAssuranceViolations" class="assurance-hud-val text-white">0</strong>
            <span class="assurance-hud-sub" id="hudAssuranceViolationsSub">0 Critical &bull; 0 Warning</span>
          </div>
          <div class="assurance-hud-card">
            <span class="assurance-hud-label">MERKLE ROOT DIGEST</span>
            <strong id="hudAssuranceRootDigest" class="assurance-hud-val text-cyan font-mono">e3b0c442...</strong>
            <span class="assurance-hud-sub" id="hudAssuranceRootDigestSub">SHA-256 Tamper Proof</span>
          </div>
        </div>

        <!-- Scientific Truth & Provenance Disclosure -->
        <div class="coverage-badge assurance-scientific-disclosure">
          <strong>MISSION ASSURANCE &amp; EVIDENCE INTEGRITY CONTRACT</strong>
          Preserving USGS CTX 20m DTM (DOI 10.5066/P906QQT8) &bull; IAU 2000 Mars Spheroid (R=3,396,190 m). All counterfactual trajectories and fault simulations are derived planning heuristics, NOT flight telemetry, and are never designated operationally safe for astronauts.
        </div>

        <!-- Main Assurance Workspace Sub-Sections -->
        <div class="assurance-subsections">
          <!-- AREA A: CAMPAIGN BRANCH TREE & ISOLATION -->
          <div class="assurance-section">
            <div class="assurance-section-header">
              <span class="assurance-section-title">&#127795; AREA A: CAMPAIGN BRANCH TREE &amp; EXPERIMENTAL ISOLATION</span>
              <div class="assurance-filter-pills" id="branchFilterPills">
                <button class="filter-pill active" data-filter="all">All Branches</button>
                <button class="filter-pill" data-filter="active">Active</button>
                <button class="filter-pill" data-filter="candidate">Candidates</button>
                <button class="filter-pill" data-filter="archived">Archived</button>
              </div>
            </div>

            <!-- Fork New Branch Control Strip -->
            <div class="assurance-fork-strip">
              <input type="text" id="inputNewBranchName" class="assurance-input" placeholder="Branch Name (e.g. branch_sol2_relay_loss)" value="branch_eval_01">
              <select id="selectForkSol" class="assurance-select">
                <option value="0">Fork from Sol 1 (Start)</option>
                <option value="1">Fork from Sol 2</option>
                <option value="2">Fork from Sol 3</option>
                <option value="3">Fork from Sol 4</option>
                <option value="4">Fork from Sol 5</option>
              </select>
              <select id="selectBranchPurpose" class="assurance-select">
                <option value="counterfactual">Counterfactual Exploration</option>
                <option value="fault_injection">Fault Injection Stress</option>
                <option value="reoptimization">Recovery Re-optimization</option>
              </select>
              <button id="btnCreateBranch" class="btn-primary">&#10133; Fork Child Branch</button>
            </div>

            <!-- Branch Hierarchy List Container -->
            <div id="branchTreeContainer" class="branch-tree-container">
              <!-- Dynamically populated branch cards -->
            </div>
          </div>

          <!-- AREA B: COUNTERFACTUAL SCENARIO & FAULT INJECTION LAB -->
          <div class="assurance-section">
            <div class="assurance-section-header">
              <span class="assurance-section-title">&#9888; AREA B: COUNTERFACTUAL SCENARIO &amp; FAULT INJECTION LAB</span>
              <span class="assurance-section-sub">12 Standardized Planetary Disturbance Models</span>
            </div>

            <div class="scenario-lab-grid">
              <div class="scenario-config-card">
                <div class="control-row">
                  <span class="control-label">Scenario Model:</span>
                  <select id="selectScenarioType" class="assurance-select full-width">
                    <optgroup label="Communication Disturbances">
                      <option value="R1_RELAY_LOSS">R1: Critical Relay Loss (Power/Thermal Failure)</option>
                      <option value="R2_COMMS_DEGRADATION">R2: Dust Scatter Comms Degradation (-40% Rate)</option>
                    </optgroup>
                    <optgroup label="Energy & Power Disturbances">
                      <option value="E1_BATTERY_DEGRADATION">E1: Battery Cell Failure (-25% Capacity)</option>
                      <option value="E2_DUST_STORM_SOLAR_LOSS">E2: Regional Dust Storm Solar Loss (-50% Solar)</option>
                    </optgroup>
                    <optgroup label="Science Discovery & Timing">
                      <option value="S1_HIGH_UTILITY_DISCOVERY">S1: High-Utility Science Discovery (+150 pts, +60 min)</option>
                      <option value="S2_SCIENCE_TIME_OVERRUN">S2: Drilling Anomaly Time Overrun (+90 min)</option>
                    </optgroup>
                    <optgroup label="Storage & Downlink">
                      <option value="D1_FLASH_STORAGE_FAULT">D1: Flash Memory Bank Sector Lockout (-30%)</option>
                      <option value="D2_DOWNLINK_BOTTLENECK">D2: Earth Orbital Pass Truncation (-50% Downlink)</option>
                    </optgroup>
                    <optgroup label="Mobility & Terrain">
                      <option value="M1_WHEEL_DRIVE_ANOMALY">M1: Actuator Slip / Drive Degradation (Speed -40%)</option>
                      <option value="M2_OBSTACLE_SLIP_HAZARD">M2: High-Slope Sand Ripple Detour (+1.8 km Traverse)</option>
                    </optgroup>
                    <optgroup label="Operational Contingencies">
                      <option value="O1_SOL_EARLY_TERMINATION">O1: Safe-Mode Precautionary Sol Termination</option>
                      <option value="O2_INSTRUMENT_CALIBRATION_FAULT">O2: Spectrometer Calibration Thermal Drift</option>
                    </optgroup>
                  </select>
                </div>

                <div class="scenario-params-row">
                  <div class="control-col">
                    <span class="control-label">Target Sol:</span>
                    <input type="number" id="inputScenarioTargetSol" class="assurance-input-num" min="1" max="5" value="2">
                  </div>
                  <div class="control-col">
                    <span class="control-label">Severity:</span>
                    <select id="selectScenarioSeverity" class="assurance-select">
                      <option value="LOW">LOW</option>
                      <option value="NOMINAL">NOMINAL</option>
                      <option value="HIGH" selected>HIGH</option>
                      <option value="CRITICAL">CRITICAL</option>
                    </select>
                  </div>
                  <div class="control-col">
                    <span class="control-label">Loss / Delta:</span>
                    <input type="number" id="inputScenarioDeltaVal" class="assurance-input-num" min="1" max="100" value="35">
                    <span class="unit-label">%</span>
                  </div>
                </div>

                <div class="scenario-actions">
                  <button id="btnRunScenario" class="btn-primary full-width">&#9889; Inject Disturbance &amp; Synthesize Recovery</button>
                </div>
              </div>

              <!-- Scenario Narrative & Recovery Forecast Card -->
              <div id="scenarioNarrativeCard" class="scenario-narrative-card">
                <div class="narrative-header">
                  <span class="narrative-tag" id="scenarioNarrativeTag">SCENARIO: R1_RELAY_LOSS (Sol 2)</span>
                  <span class="narrative-status" id="scenarioNarrativeStatus">PREVIEW READY</span>
                </div>
                <p id="scenarioNarrativeText" class="narrative-body">
                  Simulates sudden geometric or hardware loss of primary relay orbiter contact on Sol 2 during Jezero western fan ascent. Predicts communication blackout along traverse segments 3-5, risking telemetry starvation and science deferral.
                </p>
                <div class="narrative-metrics" id="scenarioNarrativeMetrics">
                  <span class="metric-chip">Baseline Feasibility: <strong class="text-emerald">PASS</strong></span>
                  <span class="metric-chip">Disturbed Feasibility: <strong class="text-rose">FAIL (COMM-001)</strong></span>
                  <span class="metric-chip">Automated Recovery: <strong class="text-cyan">REROUTE_VIA_DELTA_CREST</strong></span>
                </div>
              </div>
            </div>
          </div>

          <!-- AREA C: 3-WAY COMPARATIVE WORKSPACE -->
          <div class="assurance-section">
            <div class="assurance-section-header">
              <span class="assurance-section-title">&#9878; AREA C: 3-WAY COMPARATIVE WORKSPACE (BASELINE vs DISTURBED vs RECOVERY)</span>
              <!-- 3D Layer Overlays Toggle Controls -->
              <div class="assurance-layer-controls">
                <label class="assurance-chk-label"><input type="checkbox" id="chkShowBaselineRoute" checked> <span class="chk-color chk-cyan"></span> Baseline Route</label>
                <label class="assurance-chk-label"><input type="checkbox" id="chkShowDisturbedRoute" checked> <span class="chk-color chk-amber"></span> Disturbed Route</label>
                <label class="assurance-chk-label"><input type="checkbox" id="chkShowRecoveryRoute" checked> <span class="chk-color chk-emerald"></span> Recovery Candidate</label>
                <label class="assurance-chk-label"><input type="checkbox" id="chkShowFaultMarkers" checked> <span class="chk-color chk-rose"></span> Fault Markers</label>
              </div>
            </div>

            <!-- 3-Way Comparative Table -->
            <div class="table-responsive">
              <table id="branchCompareTable" class="assurance-table">
                <thead>
                  <tr>
                    <th>METRIC / KPI</th>
                    <th>BASELINE (main)</th>
                    <th>DISTURBED (Unmitigated)</th>
                    <th>RECOVERY CANDIDATE</th>
                    <th>NET RECOVERY DELTA</th>
                    <th>VERDICT</th>
                  </tr>
                </thead>
                <tbody id="branchCompareTableBody">
                  <tr>
                    <td><strong>Assurance Invariants</strong></td>
                    <td><span class="badge-verdict pass">20 / 20 PASS</span></td>
                    <td><span class="badge-verdict fail">17 / 20 FAIL</span></td>
                    <td><span class="badge-verdict pass">20 / 20 PASS</span></td>
                    <td class="text-emerald">+3 Repaired</td>
                    <td><strong class="text-emerald">CLEARED</strong></td>
                  </tr>
                  <tr>
                    <td><strong>Total Traverse Distance</strong></td>
                    <td>14.82 km</td>
                    <td>16.20 km (+9.3%)</td>
                    <td>15.45 km</td>
                    <td class="text-emerald">-0.75 km vs Disturbed</td>
                    <td><strong class="text-emerald">OPTIMAL</strong></td>
                  </tr>
                  <tr>
                    <td><strong>Energy Feasibility Margin</strong></td>
                    <td>38.2% min SOC</td>
                    <td>14.5% (VIOLATION &lt;20%)</td>
                    <td>31.8% min SOC</td>
                    <td class="text-emerald">+17.3% Margin Restored</td>
                    <td><strong class="text-emerald">FEASIBLE</strong></td>
                  </tr>
                  <tr>
                    <td><strong>Science Utility Yield</strong></td>
                    <td>485.0 pts</td>
                    <td>320.0 pts (-34.0%)</td>
                    <td>462.5 pts</td>
                    <td class="text-emerald">+142.5 pts Recovered</td>
                    <td><strong class="text-emerald">95.4% YIELD</strong></td>
                  </tr>
                  <tr>
                    <td><strong>Data Storage Backlog</strong></td>
                    <td>0.0 MB (Cleared)</td>
                    <td>142.0 MB (High Pressure)</td>
                    <td>12.5 MB</td>
                    <td class="text-emerald">-129.5 MB Downlinked</td>
                    <td><strong class="text-emerald">NOMINAL</strong></td>
                  </tr>
                  <tr>
                    <td><strong>LOS Comms Coverage</strong></td>
                    <td>98.4%</td>
                    <td>68.1% (Blackout Hazard)</td>
                    <td>95.2%</td>
                    <td class="text-emerald">+27.1% Restored</td>
                    <td><strong class="text-emerald">STABLE</strong></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- AREA D: MISSION ASSURANCE INVARIANT SCORECARD -->
          <div class="assurance-section">
            <div class="assurance-section-header">
              <span class="assurance-section-title">&#128221; AREA D: 20-RULE INVARIANT AUDIT SCORECARD</span>
              <div class="assurance-filter-pills" id="scorecardCategoryPills">
                <button class="filter-pill active" data-cat="all">All (20)</button>
                <button class="filter-pill" data-cat="energy">Energy &amp; Power</button>
                <button class="filter-pill" data-cat="data">Data &amp; Memory</button>
                <button class="filter-pill" data-cat="comms">Comms &amp; Visibility</button>
                <button class="filter-pill" data-cat="mobility">Mobility &amp; Kinematics</button>
                <button class="filter-pill" data-cat="science">Science &amp; Timing</button>
                <button class="filter-pill" data-cat="replay">Replay &amp; Branching</button>
              </div>
            </div>

            <!-- Invariant Scorecard Table -->
            <div class="table-responsive">
              <table id="assuranceScorecardTable" class="assurance-table">
                <thead>
                  <tr>
                    <th>RULE ID</th>
                    <th>INVARIANT DESCRIPTION</th>
                    <th>CATEGORY</th>
                    <th>SEVERITY</th>
                    <th>VERDICT</th>
                    <th>EVIDENCE CLASSIFICATION</th>
                    <th>QUANTITATIVE AUDIT RESULT</th>
                  </tr>
                </thead>
                <tbody id="assuranceScorecardBody">
                  <!-- Dynamically populated 20 rules -->
                </tbody>
              </table>
            </div>
          </div>

          <!-- AREA E: RECOVERY APPROVAL & BRANCH PROMOTION DRAWER -->
          <div class="assurance-section">
            <div class="assurance-section-header">
              <span class="assurance-section-title">&#128640; AREA E: RECOVERY APPROVAL &amp; PROMOTION DRAWER</span>
              <span class="assurance-section-sub">Optimistic Concurrency &amp; Immutable Audit Trail</span>
            </div>

            <div class="promotion-drawer-grid">
              <div class="promo-info-card">
                <span class="promo-header">&#128736; RECOMMENDED RECOVERY STRATEGY</span>
                <p id="promoRecommendedStrategy" class="promo-desc">
                  Candidate Branch <code id="promoBranchName">branch_sol2_recovery_opt</code> exhibits superior energy feasibility (+17.3% margin) and clears all 20 mission invariants. Re-routes Sol 2 via Jezero delta crest waypoint <code>WP-DCR-04</code> to maintain continuous LOS to Relay Alpha.
                </p>
                <div class="promo-meta-row">
                  <span class="promo-meta-tag">Target Branch: <strong id="promoTargetBranchId">branch_sol2_recovery_opt</strong></span>
                  <span class="promo-meta-tag">Base Campaign Version: <strong id="promoBaseVersion">v1</strong></span>
                  <span class="promo-meta-tag">Concurrency Guard: <strong class="text-emerald">UNCONTESTED</strong></span>
                </div>
              </div>

              <div class="promo-action-card">
                <div class="control-row">
                  <span class="control-label">Approver Call-Sign:</span>
                  <input type="text" id="inputApproverName" class="assurance-input" value="FLIGHT_DIRECTOR_ATLAS">
                </div>
                <div class="control-row">
                  <span class="control-label">Promotion Rationale:</span>
                  <input type="text" id="inputPromotionRationale" class="assurance-input" value="Pre-cleared counterfactual branch restoring Sol 2 comms and science feasibility under Relay loss disturbance.">
                </div>
                <button id="btnPromoteBranch" class="btn-primary mocc-btn-promote full-width">&#128640; Approve &amp; Promote Candidate to Main</button>
              </div>
            </div>
          </div>

          <!-- AREA F: TAMPER-EVIDENT DOSSIER & VERIFICATION PACKAGE -->
          <div class="assurance-section">
            <div class="assurance-section-header">
              <span class="assurance-section-title">&#128272; AREA F: TAMPER-EVIDENT CRYPTOGRAPHIC DOSSIER</span>
              <div class="assurance-header-actions">
                <button id="btnExportDossierPackage" class="btn-secondary">&#128196; Export Verification Package (JSON)</button>
              </div>
            </div>

            <!-- Merkle Dossier Manifest Table -->
            <div class="table-responsive">
              <table id="dossierManifestTable" class="assurance-table font-mono-table">
                <thead>
                  <tr>
                    <th>ARTIFACT / COMPONENT</th>
                    <th>CONTENT HASH (SHA-256)</th>
                    <th>SIZE (BYTES)</th>
                    <th>PROVENANCE STATUS</th>
                  </tr>
                </thead>
                <tbody id="dossierManifestBody">
                  <!-- Dynamically populated manifest hashes -->
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>"""

if "\r\n" in target:
    panel_html = panel_html.replace("\n", "\r\n")

replacement = target + panel_html
new_content = content.replace(target, replacement, 1)

if new_content == content:
    raise RuntimeError("Replacement failed to modify content!")

index_html.write_text(new_content, encoding="utf-8")
print("Successfully inserted #tabMissionAssurance into web/index.html!")
