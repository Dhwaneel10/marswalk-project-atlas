import sys

def main():
    with open('web/index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Tab Button
    target_btn = '<button class="inspector-tab" data-tab="tabMissionAssurance" id="tabBtnMissionAssurance" title="Atlas Mission Assurance &amp; Counterfactual Operations Lab">&#128737; Assurance Lab</button>'
    new_btn = target_btn + '\n        <button class="inspector-tab" data-tab="tabFleetControl" id="tabBtnFleetControl" title="Atlas Fleet Intelligence: Multi-Rover Operations, Cooperative Traversal &amp; Distributed Science">&#128741; Fleet Control</button>'

    if target_btn not in html:
        print("Error: target_btn not found")
        return
    html = html.replace(target_btn, new_btn, 1)

    # 2. Tab Panel
    panel_html = '''
      <!-- TAB: ATLAS FLEET CONTROL (Multi-Rover Cooperative Exploration) -->
      <div id="tabFleetControl" class="inspector-tab-panel fleet-panel hidden">
        <div class="fleet-header-deck">
          <div class="fleet-header-title">
            <span class="fleet-badge-icon">&#128741;</span>
            <div>
              <h2 class="fleet-title-text">ATLAS FLEET OPERATIONS DIRECTOR</h2>
              <div class="fleet-subtitle-text">Multi-Rover Cooperative Exploration &bull; Distributed Science &bull; RelayNet Mesh &bull; Counterfactual Recovery</div>
            </div>
          </div>
          <div class="fleet-header-actions">
            <div class="fleet-selector-group">
              <label for="fleetSelect">ACTIVE FLEET:</label>
              <select id="fleetSelect" class="fleet-select-input">
                <option value="fleet_jezero_alpha" selected>Jezero Western Delta Fleet (4 Rovers)</option>
              </select>
            </div>
            <div class="fleet-status-pill" id="fleetStatusPill">FLEET NOMINAL</div>
          </div>
        </div>

        <!-- Action Control Bar -->
        <div class="fleet-action-bar">
          <button id="btnFleetAllocate" class="btn-primary-fleet">&#9889; Allocate Science</button>
          <button id="btnFleetPlanRoutes" class="btn-primary-fleet">&#128506; Coordinate Routes</button>
          <button id="btnFleetSchedule" class="btn-secondary-fleet">&#128197; Synchronize Schedule</button>
          <button id="btnFleetOptimize" class="btn-secondary-fleet">&#127919; 6D Pareto Optimize</button>
          <button id="btnFleetRecover" class="btn-danger-fleet">&#128680; Inject Disturbance (F1-F7)</button>
          <button id="btnFleetPromote" class="btn-success-fleet">&#9989; Promote Fleet Plan</button>
        </div>

        <div class="fleet-scrollable-content">
          <!-- 5-CARD FLEET OVERVIEW HUD -->
          <div class="fleet-hud-grid">
            <div class="fleet-hud-card" id="cardActiveRovers">
              <div class="fleet-hud-label">ACTIVE ROVERS</div>
              <div class="fleet-hud-value" id="valActiveRovers">4 / 4 Units</div>
              <div class="fleet-hud-sub" id="subActiveRovers">Alpha, Beta, Gamma, Delta</div>
            </div>
            <div class="fleet-hud-card" id="cardFleetDistance">
              <div class="fleet-hud-label">FLEET TRAVERSE</div>
              <div class="fleet-hud-value" id="valFleetDistance">18.4 km</div>
              <div class="fleet-hud-sub" id="subFleetDistance">4 Deconflicted Traverses</div>
            </div>
            <div class="fleet-hud-card" id="cardMinSoc">
              <div class="fleet-hud-label">MIN BATTERY MARGIN</div>
              <div class="fleet-hud-value text-emerald" id="valMinSoc">36.8%</div>
              <div class="fleet-hud-sub" id="subMinSoc">Rover Alpha (No Pooling)</div>
            </div>
            <div class="fleet-hud-card" id="cardFleetConnectivity">
              <div class="fleet-hud-label">RELAYNET CONNECTIVITY</div>
              <div class="fleet-hud-value text-cyan" id="valFleetConnectivity">100.0%</div>
              <div class="fleet-hud-sub" id="subFleetConnectivity">Base + 4 Relays + Mesh</div>
            </div>
            <div class="fleet-hud-card" id="cardScienceUtility">
              <div class="fleet-hud-label">FLEET SCIENCE YIELD</div>
              <div class="fleet-hud-value text-purple" id="valScienceUtility">2,840 pts</div>
              <div class="fleet-hud-sub" id="subScienceUtility">12/12 Targets Allocated</div>
            </div>
          </div>

          <!-- AREA 1: FOUR ROVER STATUS CARDS GRID -->
          <div class="fleet-section">
            <div class="fleet-section-header">
              <span class="fleet-section-title">&#128642; AREA 1: EXPLORATION UNITS OPERATIONAL STATUS</span>
              <span class="fleet-badge-sub">Zero Cross-Rover Energy Pooling Enforced &bull; Individual Flash Buffers</span>
            </div>
            <div class="rover-cards-grid" id="roverCardsGrid">
              <!-- Dynamically populated or default 4 cards -->
              <div class="rover-card rover-card-alpha" id="cardRoverAlpha">
                <div class="rover-card-header">
                  <div class="rover-card-name"><span class="rover-dot dot-alpha"></span> Rover Alpha (Science Lead)</div>
                  <div class="rover-unit-badge badge-alpha">ROBOTIC ROVER</div>
                </div>
                <div class="rover-card-body">
                  <div class="rover-stat-row">
                    <span>Location:</span> <strong id="alphaLoc">[128, 128] (-2510.4 m)</strong>
                  </div>
                  <div class="rover-stat-row">
                    <span>Battery SOC (5000 Wh):</span> <strong class="text-cyan" id="alphaSoc">88.5%</strong>
                  </div>
                  <div class="rover-progress-bar"><div class="rover-progress-fill fill-alpha" id="alphaSocBar" style="width: 88.5%;"></div></div>
                  <div class="rover-stat-row">
                    <span>Storage (65,536 MB):</span> <span id="alphaStorage">8,420 MB (12.8%)</span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Instruments:</span> <span class="rover-tag-group"><span class="rover-tag">PIXL</span><span class="rover-tag">SHERLOC</span><span class="rover-tag">MASTCAM-Z</span><span class="rover-tag">MEDA</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Assigned Targets:</span> <span id="alphaTargets" class="rover-target-pills"><span class="pill-tgt">TGT_HAWKSBILL_GAP</span><span class="pill-tgt">TGT_BELVA_CRATER</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Comms Status:</span> <strong class="text-emerald" id="alphaComms">&#9679; DIRECT LOS (28.4 dB)</strong>
                  </div>
                </div>
              </div>

              <div class="rover-card rover-card-beta" id="cardRoverBeta">
                <div class="rover-card-header">
                  <div class="rover-card-name"><span class="rover-dot dot-beta"></span> Rover Beta (Geophysical Surveyor)</div>
                  <div class="rover-unit-badge badge-beta">SUBSURFACE RADAR</div>
                </div>
                <div class="rover-card-body">
                  <div class="rover-stat-row">
                    <span>Location:</span> <strong id="betaLoc">[128, 128] (-2510.4 m)</strong>
                  </div>
                  <div class="rover-stat-row">
                    <span>Battery SOC (4800 Wh):</span> <strong class="text-emerald" id="betaSoc">92.0%</strong>
                  </div>
                  <div class="rover-progress-bar"><div class="rover-progress-fill fill-beta" id="betaSocBar" style="width: 92.0%;"></div></div>
                  <div class="rover-stat-row">
                    <span>Storage (65,536 MB):</span> <span id="betaStorage">14,200 MB (21.7%)</span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Instruments:</span> <span class="rover-tag-group"><span class="rover-tag">RIMFAX</span><span class="rover-tag">MASTCAM-Z</span><span class="rover-tag">MEDA</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Assigned Targets:</span> <span id="betaTargets" class="rover-target-pills"><span class="pill-tgt">TGT_SKINNER_RIDGE</span><span class="pill-tgt">TGT_DELTA_SCARP</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Comms Status:</span> <strong class="text-emerald" id="betaComms">&#9679; DIRECT LOS (26.1 dB)</strong>
                  </div>
                </div>
              </div>

              <div class="rover-card rover-card-gamma" id="cardRoverGamma">
                <div class="rover-card-header">
                  <div class="rover-card-name"><span class="rover-dot dot-gamma"></span> Rover Gamma (Coring Specialist)</div>
                  <div class="rover-unit-badge badge-gamma">SAMPLE CORING</div>
                </div>
                <div class="rover-card-body">
                  <div class="rover-stat-row">
                    <span>Location:</span> <strong id="gammaLoc">[128, 128] (-2510.4 m)</strong>
                  </div>
                  <div class="rover-stat-row">
                    <span>Battery SOC (5200 Wh):</span> <strong class="text-purple" id="gammaSoc">84.2%</strong>
                  </div>
                  <div class="rover-progress-bar"><div class="rover-progress-fill fill-gamma" id="gammaSocBar" style="width: 84.2%;"></div></div>
                  <div class="rover-stat-row">
                    <span>Storage (65,536 MB):</span> <span id="gammaStorage">6,180 MB (9.4%)</span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Instruments:</span> <span class="rover-tag-group"><span class="rover-tag">SHERLOC</span><span class="rover-tag">CORING_TOOL</span><span class="rover-tag">MASTCAM-Z</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Assigned Targets:</span> <span id="gammaTargets" class="rover-target-pills"><span class="pill-tgt">TGT_ENCHANTED_LAKE</span><span class="pill-tgt">TGT_KODIAK_BUTTE</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Comms Status:</span> <strong class="text-emerald" id="gammaComms">&#9679; RELAY HOP (21.4 dB)</strong>
                  </div>
                </div>
              </div>

              <div class="rover-card rover-card-delta" id="cardRoverDelta">
                <div class="rover-card-header">
                  <div class="rover-card-name"><span class="rover-dot dot-delta"></span> Rover Delta (Relay &amp; Sentinel)</div>
                  <div class="rover-unit-badge badge-delta">MOBILE RELAY</div>
                </div>
                <div class="rover-card-body">
                  <div class="rover-stat-row">
                    <span>Location:</span> <strong id="deltaLoc">[128, 128] (-2510.4 m)</strong>
                  </div>
                  <div class="rover-stat-row">
                    <span>Battery SOC (4400 Wh):</span> <strong class="text-amber" id="deltaSoc">79.6%</strong>
                  </div>
                  <div class="rover-progress-bar"><div class="rover-progress-fill fill-delta" id="deltaSocBar" style="width: 79.6%;"></div></div>
                  <div class="rover-stat-row">
                    <span>Storage (32,768 MB):</span> <span id="deltaStorage">3,400 MB (10.4%)</span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Instruments:</span> <span class="rover-tag-group"><span class="rover-tag">MASTCAM-Z</span><span class="rover-tag">MEDA</span><span class="rover-tag">X-BAND RELAY</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Assigned Targets:</span> <span id="deltaTargets" class="rover-target-pills"><span class="pill-tgt">TGT_NERETVA_VALLIS</span><span class="pill-tgt">TGT_JEZERO_FLOOR</span></span>
                  </div>
                  <div class="rover-stat-row">
                    <span>Mobile Relay Role:</span> <strong class="text-amber" id="deltaRelayRole">&#9650; ACTIVE RELAY NODE</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- AREA 2: DISTRIBUTED SCIENCE TASK ALLOCATION BOARD -->
          <div class="fleet-section">
            <div class="fleet-section-header">
              <span class="fleet-section-title">&#128302; AREA 2: DISTRIBUTED SCIENCE TASK ASSIGNMENT BOARD</span>
              <button id="btnToggleEligibilityModal" class="btn-subtle-fleet">&#128065; View Compatibility Rationale</button>
            </div>
            <div class="table-responsive">
              <table id="fleetAssignmentTable" class="fleet-table">
                <thead>
                  <tr>
                    <th>TARGET ID</th>
                    <th>TARGET NAME</th>
                    <th>LOCATION [R, C]</th>
                    <th>SCIENCE OBJECTIVE</th>
                    <th>PRIORITY</th>
                    <th>ASSIGNED ROVER</th>
                    <th>INSTRUMENT USED</th>
                    <th>DWELL (S)</th>
                    <th>STATUS</th>
                  </tr>
                </thead>
                <tbody id="fleetAssignmentBody">
                  <!-- Dynamically populated 12 targets -->
                </tbody>
              </table>
            </div>
          </div>

          <!-- AREA 3: MULTI-LANE SYNCHRONIZED FLEET TIMELINE -->
          <div class="fleet-section">
            <div class="fleet-section-header">
              <span class="fleet-section-title">&#9201; AREA 3: MULTI-LANE SYNCHRONIZED FLEET TIMELINE (SOLS 1-5)</span>
              <div class="sol-filter-pills" id="fleetSolFilterPills">
                <button class="filter-pill active" data-sol="1">Sol 1</button>
                <button class="filter-pill" data-sol="2">Sol 2</button>
                <button class="filter-pill" data-sol="3">Sol 3</button>
                <button class="filter-pill" data-sol="4">Sol 4</button>
                <button class="filter-pill" data-sol="5">Sol 5</button>
              </div>
            </div>
            <div class="fleet-timeline-wrapper">
              <div class="fleet-timeline-lanes" id="fleetTimelineLanes">
                <!-- 4 parallel lanes for Rover Alpha, Beta, Gamma, Delta -->
              </div>
            </div>
            <div class="fleet-timeline-legend">
              <span class="legend-chip chip-traverse"><span class="chip-color color-traverse"></span> Traverse (A*)</span>
              <span class="legend-chip chip-science"><span class="chip-color color-science"></span> Observation &amp; Science</span>
              <span class="legend-chip chip-downlink"><span class="chip-color color-downlink"></span> Relay Downlink</span>
              <span class="legend-chip chip-hold"><span class="chip-color color-hold"></span> Spatial Hold / Yield</span>
              <span class="legend-chip chip-sleep"><span class="chip-color color-sleep"></span> Diurnal Rest / Recharge</span>
            </div>
          </div>

          <!-- AREA 4: 6D PARETO OPTIMIZATION CHAMPIONS MATRIX -->
          <div class="fleet-section">
            <div class="fleet-section-header">
              <span class="fleet-section-title">&#127919; AREA 4: 6D PARETO FLEET OPTIMIZATION CHAMPIONS</span>
              <span class="fleet-badge-sub">Non-Dominated Tradeoff Space &bull; Science &bull; Distance &bull; Energy &bull; Comms &bull; Storage &bull; Duration</span>
            </div>
            <div class="table-responsive">
              <table id="fleetParetoTable" class="fleet-table">
                <thead>
                  <tr>
                    <th>CHAMPION PROFILE</th>
                    <th>DESCRIPTION</th>
                    <th>SCIENCE UTILITY</th>
                    <th>TRAVERSE DISTANCE</th>
                    <th>MIN SOC MARGIN</th>
                    <th>COMMS REACHABILITY</th>
                    <th>STORAGE BACKLOG</th>
                    <th>CAMPAIGN DURATION</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody id="fleetParetoBody">
                  <!-- Dynamically populated 5 champions -->
                </tbody>
              </table>
            </div>
          </div>

          <!-- AREA 5: COUNTERFACTUAL DISTURBANCE & RECOVERY LAB -->
          <div class="fleet-section">
            <div class="fleet-section-header">
              <span class="fleet-section-title">&#128680; AREA 5: COUNTERFACTUAL DISTURBANCE &amp; AUTONOMOUS RECOVERY LAB</span>
              <span class="fleet-badge-sub">3-Way Comparative Scorecard &bull; Fault Reallocation &bull; Cryptographic Promotion</span>
            </div>
            <div class="fleet-scenario-control-deck">
              <div class="scenario-field-group">
                <label for="fleetScenarioType">DISTURBANCE SCENARIO:</label>
                <select id="fleetScenarioType" class="fleet-select-input">
                  <option value="F1_ROVER_UNAVAILABLE" selected>F1: Rover Inoperability / Mobility Failure (e.g. Rover Alpha)</option>
                  <option value="F2_SHARED_RELAY_OUTAGE">F2: Shared Surface Relay Hardware Outage</option>
                  <option value="F3_FLEET_RESOURCE_IMBALANCE">F3: Fleet Battery Resource Depletion / Thermal Throttle</option>
                  <option value="F4_SCIENCE_TARGET_REASSIGNMENT">F4: Science Target Dynamic Priority Preemption</option>
                  <option value="F5_SCHEDULED_ROUTE_CONFLICT">F5: Spatiotemporal Route Contention / Chokepoint Gridlock</option>
                  <option value="F6_DATA_BACKLOG_CONCENTRATION">F6: Flash Buffer Memory Backlog Concentration</option>
                  <option value="F7_COMBINED_FLEET_DISTURBANCE">F7: Multi-Rover Combined Severe Disturbance</option>
                </select>
              </div>
              <div class="scenario-field-group">
                <label for="fleetDisturbedRover">TARGET ROVER:</label>
                <select id="fleetDisturbedRover" class="fleet-select-input">
                  <option value="ATLAS_ROVER_A" selected>Rover Alpha (Science Lead)</option>
                  <option value="ATLAS_ROVER_B">Rover Beta (Geophysical Surveyor)</option>
                  <option value="ATLAS_ROVER_C">Rover Gamma (Coring Specialist)</option>
                  <option value="ATLAS_ROVER_D">Rover Delta (Relay &amp; Sentinel)</option>
                </select>
              </div>
              <div class="scenario-field-group">
                <label for="fleetScenarioSol">ONSET SOL:</label>
                <input type="number" id="fleetScenarioSol" class="fleet-num-input" value="2" min="1" max="5">
              </div>
              <button id="btnExecuteFleetScenario" class="btn-danger-fleet">&#9888; Synthesize Fleet Recovery</button>
            </div>

            <!-- 3-Way Comparative Delta Table -->
            <div class="table-responsive" style="margin-top: 14px;">
              <table id="fleetThreeWayTable" class="fleet-table">
                <thead>
                  <tr>
                    <th>EVALUATION METRIC</th>
                    <th>BASELINE NOMINAL</th>
                    <th>DISTURBED UNMITIGATED</th>
                    <th>AUTONOMOUS RECOVERY</th>
                    <th>NET RECOVERY DELTA</th>
                    <th>OPERATIONAL STATUS</th>
                  </tr>
                </thead>
                <tbody id="fleetThreeWayBody">
                  <!-- Dynamically populated rows -->
                </tbody>
              </table>
            </div>

            <!-- Promotion & Cryptographic Handoff Drawer -->
            <div class="fleet-promotion-drawer" id="fleetPromotionDrawer">
              <div class="promotion-drawer-header">
                <span class="promotion-drawer-title">&#128220; FORMAL FLEET RECOVERY PROMOTION SIGN-OFF</span>
              </div>
              <div class="promotion-form-row">
                <div class="promotion-input-group">
                  <label for="fleetApproverCallsign">APPROVER CALLSIGN:</label>
                  <input type="text" id="fleetApproverCallsign" class="fleet-text-input" value="FLIGHT_DIRECTOR_ATLAS">
                </div>
                <div class="promotion-input-group" style="flex: 2;">
                  <label for="fleetPromotionRationale">TECHNICAL RATIONALE:</label>
                  <input type="text" id="fleetPromotionRationale" class="fleet-text-input" value="Autonomous target reallocation deconflicts traverse bottlenecks and preserves 94.2% science yield.">
                </div>
                <button id="btnConfirmFleetPromotion" class="btn-success-fleet">&#9989; Authorize Promotion</button>
              </div>
              <div class="promotion-audit-notice" id="promotionAuditNotice">
                State Fingerprint: <span class="font-mono" id="fleetFingerprintDisplay">e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</span> (SHA-256) &bull; Monotonic Concurrency Guard Enforced
              </div>
            </div>
          </div>
        </div>
      </div>
'''

    target_panel = '      <!-- TAB 1: PLAN (Surface Traverse Planning & Configuration) -->'
    if target_panel not in html:
        print("Error: target_panel not found")
        return
    html = html.replace(target_panel, panel_html + '\n      ' + target_panel, 1)

    with open('web/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Successfully inserted Fleet Control tab and panel into web/index.html!")

if __name__ == '__main__':
    main()
