# Patch web/index.html to add Settlement Center tab and panel

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add tab button
tab_btn_target = """        <button class="inspector-tab" data-tab="tabEnvironmentValidation" id="tabBtnEnvironmentValidation" title="Atlas Mars Climate Data Assimilation &amp; Validation Lab: Real PDS Data &times; MCD NetCDF &times; Empirical Residuals &times; Bounded Calibration">&#129514; Assimilation Lab</button>"""

tab_btn_replacement = """        <button class="inspector-tab" data-tab="tabEnvironmentValidation" id="tabBtnEnvironmentValidation" title="Atlas Mars Climate Data Assimilation &amp; Validation Lab: Real PDS Data &times; MCD NetCDF &times; Empirical Residuals &times; Bounded Calibration">&#129514; Assimilation Lab</button>
        <button class="inspector-tab" data-tab="tabSettlement" id="tabBtnSettlement" title="Atlas Settlement Engine: Planetary Infrastructure Design, Autonomous Construction, ISRU &amp; Long-Duration Surface Operations">&#127960; Settlement Center</button>"""

assert tab_btn_target in content, "tab_btn_target not found in web/index.html"
content = content.replace(tab_btn_target, tab_btn_replacement, 1)

# 2. Add tab panel
tab_panel_target = """      </div>

      <div id="tabPlan" class="inspector-tab-panel hidden">"""

settlement_panel_html = """      </div>

      <!-- ================================================================= -->
      <!-- MILESTONE 13S: ATLAS PLANETARY SETTLEMENT OPERATIONS CENTER       -->
      <!-- ================================================================= -->
      <div id="tabSettlement" class="inspector-tab-panel hidden settlement-panel">
        <div class="settlement-header">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <h2 class="settlement-title">&#127960; ATLAS PLANETARY SETTLEMENT OPERATIONS CENTER</h2>
              <div class="settlement-subtitle">Moon-to-Mars Infrastructure Architecture &bull; Closed ISRU Mass Conservation &bull; 15-Stage Autonomous Construction &bull; Phase F Readiness Review</div>
            </div>
            <div style="display:flex; gap:6px;">
              <button id="btnSettlementReset" class="btn-picker-secondary" style="padding:4px 8px; font-size:10px;">&#8635; RESET</button>
              <button id="btnSettlementAdvanceSol" class="btn-picker" style="padding:4px 10px; font-size:10px;">+1 SOL &gt;&gt;</button>
            </div>
          </div>
        </div>

        <!-- Mandatory Scientific Disclosure Alert -->
        <div class="settlement-disclosure-banner">
          <strong>&#9888; MANDATORY SCIENTIFIC DISCLOSURE:</strong> All planetary settlement models, power balances, In-Situ Resource Utilization (ISRU) reaction rates, and habitat thermal envelopes are computational research simulations. They do NOT constitute operational flight qualification or certify human life-support safety for NASA astronauts.
        </div>

        <!-- Settlement Status & Telemetry Bar -->
        <div class="settlement-card">
          <div class="settlement-status-bar">
            <div>
              <span class="control-label" style="font-size:9px;">LIFECYCLE STATE:</span>
              <span id="settlementLifecycleBadge" class="settlement-badge badge-nominal">OPERATIONAL_SIMULATION</span>
            </div>
            <div>
              <span class="control-label" style="font-size:9px;">CURRENT SOL:</span>
              <span id="settlementSolVal" style="font-family:monospace; font-weight:700; color:var(--telemetry-cyan);">Sol 1</span>
            </div>
            <div>
              <span class="control-label" style="font-size:9px;">CANDIDATE SITE:</span>
              <select id="settlementSiteSelect" class="hud-select" style="font-size:10px; padding:2px 4px;">
                <option value="SITE-DELTA-NORTH" selected>SITE-DELTA-NORTH (Jezero Delta Fan)</option>
                <option value="SITE-CRATER-FLOOR">SITE-CRATER-FLOOR (Jezero Floor)</option>
                <option value="SITE-NERETVA-VALIS">SITE-NERETVA-VALIS (Inflow Valley)</option>
                <option value="SITE-DELTA-SCARP">SITE-DELTA-SCARP (Delta Cliff)</option>
                <option value="SITE-RIM-TERRACE">SITE-RIM-TERRACE (Crater Rim)</option>
              </select>
            </div>
            <div>
              <span class="control-label" style="font-size:9px;">ARCHETYPE:</span>
              <select id="settlementArchSelect" class="hud-select" style="font-size:10px; padding:2px 4px;">
                <option value="MARS_BASE_ALPHA" selected>Mars Base Alpha (8-20 Crew, 260 kW)</option>
                <option value="EXPEDITION_BASE">Expedition Base (6 Crew, 120 kW)</option>
                <option value="SMALL_OUTPOST">Small Outpost (4 Crew, 55 kW)</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Grid 1: Surface Power & ISRU Factories -->
        <div class="settlement-grid-2">
          <!-- Power Architecture Card -->
          <div class="settlement-card">
            <div class="settlement-card-header">
              <span>&#9889; Surface Power Architecture (NASA ACR 2024)</span>
              <span id="settlementPowerSourceBadge" class="settlement-badge badge-info">100 kWe FISSION BASELOAD</span>
            </div>
            <div class="settlement-metrics-grid">
              <div class="settlement-metric-cell">
                <div class="cell-label">GROSS GENERATION</div>
                <div id="settlementGrossGenVal" class="cell-value" style="color:var(--status-green);">260.0 kW</div>
              </div>
              <div class="settlement-metric-cell">
                <div class="cell-label">TOTAL DEMAND</div>
                <div id="settlementDemandVal" class="cell-value" style="color:var(--telemetry-yellow);">90.5 kW</div>
              </div>
              <div class="settlement-metric-cell">
                <div class="cell-label">DELIVERED POWER</div>
                <div id="settlementDeliveredVal" class="cell-value" style="color:var(--telemetry-cyan);">90.5 kW</div>
              </div>
              <div class="settlement-metric-cell">
                <div class="cell-label">BATTERY STORAGE SOC</div>
                <div id="settlementBatterySocVal" class="cell-value" style="color:var(--telemetry-cyan);">80.0%</div>
              </div>
            </div>

            <!-- Priority Load Shedding Status -->
            <div style="margin-top:8px;">
              <span class="control-label" style="font-size:9px;">ACTIVE LOAD SHEDDING (7 PRIORITY TIERS):</span>
              <div id="settlementShedLoadsContainer" class="settlement-shed-container">
                <span style="color:var(--status-green); font-size:10px;">&check; Zero loads shed &bull; All 7 tiers fully energized</span>
              </div>
            </div>

            <!-- Power Source Comparison Controls -->
            <div style="margin-top:8px; display:flex; gap:6px; align-items:center;">
              <button id="btnSimulatePowerFission" class="btn-picker-secondary" style="padding:2px 6px; font-size:9px;">Test Fission Baseloader</button>
              <button id="btnSimulatePowerSolarStorm" class="btn-picker-secondary" style="padding:2px 6px; font-size:9px;">Inject Solar Tau 2.8 Storm</button>
            </div>
          </div>

          <!-- ISRU Production & Mass Conservation Card -->
          <div class="settlement-card">
            <div class="settlement-card-header">
              <span>&#9874; In-Situ Resource Utilization (ISRU) Factories</span>
              <span class="settlement-badge badge-conserved">&Delta;m &lt; 1e-4 kg CONSERVED</span>
            </div>
            <div class="settlement-metrics-grid">
              <div class="settlement-metric-cell">
                <div class="cell-label">POTABLE WATER CACHE</div>
                <div id="settlementWaterStockVal" class="cell-value" style="color:var(--telemetry-cyan);">15,000 kg</div>
              </div>
              <div class="settlement-metric-cell">
                <div class="cell-label">LIQUID O2 CACHE</div>
                <div id="settlementO2StockVal" class="cell-value" style="color:var(--telemetry-cyan);">8,500 kg</div>
              </div>
              <div class="settlement-metric-cell">
                <div class="cell-label">LIQUID CH4 (PROP)</div>
                <div id="settlementCh4StockVal" class="cell-value" style="color:var(--telemetry-yellow);">2,100 kg</div>
              </div>
              <div class="settlement-metric-cell">
                <div class="cell-label">SINTERED BLOCKS</div>
                <div id="settlementSinteredBlocksVal" class="cell-value" style="color:var(--status-green);">980 blocks</div>
              </div>
            </div>

            <div style="margin-top:8px; font-size:9.5px; color:var(--text-secondary);">
              <div><strong>Water:</strong> Clay Thermal Desorption (450&deg;C) &bull; 7.5 wt% yield &bull; 92% recycling loop</div>
              <div><strong>Oxygen:</strong> MOXIE Solid Oxide Electrolysis (SOXE 800&deg;C) &bull; 88% ECLSS recovery</div>
              <div><strong>Methane:</strong> Ruthenium-Catalyzed Sabatier Methanation &bull; Tracked H2 conservation</div>
            </div>

            <div style="margin-top:8px; display:flex; gap:6px;">
              <button id="btnRunIsruWaterBatch" class="btn-picker" style="padding:3px 8px; font-size:9px;">Extract Water (500kg)</button>
              <button id="btnRunIsruOxygenBatch" class="btn-picker" style="padding:3px 8px; font-size:9px;">Generate O2 (250kg)</button>
              <button id="btnRunIsruSinterBatch" class="btn-picker-secondary" style="padding:3px 8px; font-size:9px;">Sinter Regolith (1200kg)</button>
            </div>
          </div>
        </div>

        <!-- Grid 2: Habitat Thermal & Autonomous Construction -->
        <div class="settlement-grid-2" style="margin-top:10px;">
          <!-- Habitat Digital Twin Card -->
          <div class="settlement-card">
            <div class="settlement-card-header">
              <span>&#128716; Habitat Digital Twin &bull; Active Thermal Network</span>
              <span class="settlement-badge badge-nominal">56.5 kPa NOMINAL</span>
            </div>
            <div id="settlementHabitatList" style="margin-top:6px; max-height:160px; overflow-y:auto;">
              <!-- Dynamically populated habitat modules -->
            </div>
            <div style="margin-top:8px; font-size:9px; color:var(--text-tertiary);">
              Shielding: 2.0m Sintered Regolith Arch &bull; Dose Reduction: 82.5% &bull; Cold Soak Night Temp: -115&deg;C
            </div>
          </div>

          <!-- Autonomous Robotic Construction Fleet Card -->
          <div class="settlement-card">
            <div class="settlement-card-header">
              <span>&#129302; Autonomous Construction Fleet &bull; 15-Stage Gantt</span>
              <span id="settlementConstructionStatusBadge" class="settlement-badge badge-nominal">1/15 STAGES COMPLETE</span>
            </div>
            <div id="settlementConstructionOperationsList" style="margin-top:6px; max-height:160px; overflow-y:auto;">
              <!-- Dynamically populated construction tasks -->
            </div>
            <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
              <span style="font-size:9px; color:var(--text-tertiary);">Earth Delay Guard: &gt;1200s stale commands rejected</span>
              <button id="btnStepConstructionStage" class="btn-picker" style="padding:3px 8px; font-size:9px;">Advance Next Operation</button>
            </div>
          </div>
        </div>

        <!-- Phase F Hypothetical Crew-Arrival Readiness Review Card -->
        <div class="settlement-card" style="margin-top:10px;">
          <div class="settlement-card-header">
            <span>&#128119; Phase F Hypothetical Crew-Arrival Readiness Review</span>
            <span id="settlementReadinessScoreBadge" class="settlement-badge badge-warning">EVALUATING GATES</span>
          </div>

          <div style="display:flex; gap:16px; align-items:center; margin-top:8px;">
            <div style="flex:1;">
              <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px;">
                <span>READINESS SCORE:</span>
                <span id="settlementReadinessScorePct" style="font-weight:700; color:var(--telemetry-cyan);">-- %</span>
              </div>
              <div class="settlement-progress-track">
                <div id="settlementReadinessProgressBar" class="settlement-progress-fill" style="width:0%;"></div>
              </div>
            </div>
            <button id="btnExecuteReadinessReview" class="btn-picker" style="padding:6px 14px; font-size:10.5px;">RUN READINESS REVIEW</button>
          </div>

          <!-- Verified Checkpoints vs Unmet Gaps -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
            <div>
              <span class="control-label" style="font-size:9.5px; color:var(--status-green);">&check; VERIFIED CHECKPOINTS:</span>
              <ul id="settlementVerifiedCheckpointsList" class="settlement-checklist" style="margin-top:4px;">
                <li>Click 'RUN READINESS REVIEW' to audit active infrastructure...</li>
              </ul>
            </div>
            <div>
              <span class="control-label" style="font-size:9.5px; color:var(--status-red);">&#9888; UNMET GAPS:</span>
              <ul id="settlementUnmetGapsList" class="settlement-checklist" style="margin-top:4px;">
                <li>Audit pending...</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 10 Deterministic Scenarios Runner & Replay Cryptographic Hash Card -->
        <div class="settlement-card" style="margin-top:10px;">
          <div class="settlement-card-header">
            <span>&#128220; 10 Deterministic Scenarios &bull; Cryptographic Replay</span>
            <span class="settlement-badge badge-info">SHA-256 BIT-EXACT</span>
          </div>

          <div style="display:flex; gap:8px; align-items:center; margin-top:8px;">
            <select id="settlementScenarioSelect" class="hud-select" style="flex:1; font-size:10.5px; padding:4px 6px;">
              <option value="SCENARIO-01-FIRST-OUTPOST">Scenario 01: The First Outpost (Precursor & Fission)</option>
              <option value="SCENARIO-02-HUNT-FOR-WATER">Scenario 02: The Hunt for Water (SWIM Uncertainty)</option>
              <option value="SCENARIO-03-POWER-DILEMMA">Scenario 03: The Power Dilemma (Nuclear vs Solar Tau 2.8)</option>
              <option value="SCENARIO-04-AUTONOMOUS-CONSTRUCTION">Scenario 04: The Autonomous Construction Crew (Fleet Gantt)</option>
              <option value="SCENARIO-05-WATER-FACTORY">Scenario 05: The Water Factory (Thermal Desorption & Recycling)</option>
              <option value="SCENARIO-06-OXYGEN-FACTORY">Scenario 06: The Oxygen Factory (SOXE & Sabatier Methanation)</option>
              <option value="SCENARIO-07-HABITAT-COMMISSIONING">Scenario 07: The Habitat Commissioning Test (Cold Soak -115C)</option>
              <option value="SCENARIO-08-LOGISTICS-NIGHTMARE">Scenario 08: The Logistics Nightmare (180-Sol Cargo Scrub)</option>
              <option value="SCENARIO-09-SETTLEMENT-APOCALYPSE">Scenario 09: The Settlement Apocalypse (Compound Failure & Safe Harbor)</option>
              <option value="SCENARIO-10-MARS-BASE-ALPHA" selected>Scenario 10: Mars Base Alpha (Flagship End-to-End Campaign)</option>
            </select>
            <button id="btnRunSettlementScenario" class="btn-picker" style="padding:4px 14px; font-size:10.5px;">RUN SCENARIO</button>
          </div>

          <!-- Scenario Execution Output Log -->
          <div id="settlementScenarioConsole" class="settlement-console" style="margin-top:8px;">
            [READY] Select a deterministic settlement scenario and click 'RUN SCENARIO' to execute.
          </div>

          <!-- Replay Cryptographic SHA-256 Hash Display -->
          <div style="margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:9.5px; color:var(--text-tertiary);">STATE CHAIN HASH (SHA-256):</span>
            <span id="settlementStateHashVal" style="font-family:monospace; font-size:10px; color:var(--telemetry-cyan);">e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</span>
          </div>
        </div>
      </div>

      <div id="tabPlan" class="inspector-tab-panel hidden">"""

assert tab_panel_target in content, "tab_panel_target not found in web/index.html"
content = content.replace(tab_panel_target, settlement_panel_html, 1)

with open('web/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("web/index.html patched with settlement button and panel successfully!")
