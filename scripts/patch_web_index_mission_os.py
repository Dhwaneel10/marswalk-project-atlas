"""Patch web/index.html to insert Milestone 13T tab button and Mission OS panel."""
import sys

def patch():
    with open("web/index.html", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add tab button
    btn_target = '<button class="inspector-tab" data-tab="tabSettlement" id="tabBtnSettlement" title="Atlas Settlement Engine: Planetary Infrastructure Design, Autonomous Construction, ISRU &amp; Long-Duration Surface Operations">&#127960; Settlement Center</button>'
    btn_repl = (
        btn_target + "\n"
        '        <button class="inspector-tab" data-tab="tabMissionOS" id="tabBtnMissionOS" title="Atlas Planetary Mission OS: Unified Planetary Operations, End-to-End Mission Orchestration, Digital Twin Integration &amp; Autonomous Campaign Execution">&#127757; Mission OS</button>'
    )
    if btn_target in content:
        content = content.replace(btn_target, btn_repl, 1)
    else:
        print("Tab button target not found!")
        sys.exit(1)

    # 2. Add panel HTML before <div id="tabPlan"
    panel_target = '      <div id="tabPlan" class="inspector-tab-panel hidden">'
    panel_html = '''      <!-- ============================================================================ -->
      <!-- TAB 13T: ATLAS PLANETARY MISSION OPERATING SYSTEM (Milestone 13T) -->
      <!-- ============================================================================ -->
      <div id="tabMissionOS" class="inspector-tab-panel hidden mission-os-panel">
        <div class="control-card mission-os-header-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div>
              <span class="control-label" style="font-size:11px; font-weight:800; color:var(--telemetry-cyan); letter-spacing:1px;">&#127757; ATLAS PLANETARY MISSION OS &times; AUTONOMOUS CAMPAIGN OPERATING SYSTEM</span>
              <div style="font-size:9px; color:#8899a6; margin-top:2px;">Milestone 13T: Unified Planetary Operations · Multi-Phase Campaign DAG · Deep-Space Autonomy · Closed-Loop ISRU</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <span id="missionOSStatusBadge" class="badge" style="background:#00e5ff22; color:var(--telemetry-cyan); border:1px solid #00e5ff66; font-size:10px; font-weight:700; padding:3px 8px; border-radius:4px;">INITIALIZING</span>
            </div>
          </div>

          <!-- Intent Input Bar -->
          <div style="display:flex; flex-direction:column; gap:6px; background:#081018; border:1px solid #1a2a3a; border-radius:6px; padding:8px 10px; margin-bottom:10px;">
            <div style="font-size:9px; font-weight:700; color:#58a6ff; letter-spacing:0.5px;">HIGH-LEVEL MISSION OBJECTIVE INTENT</div>
            <textarea id="txtMissionOSIntent" rows="2" style="width:100%; background:#050b12; border:1px solid #243b55; color:#e6edf3; font-size:10px; font-family:monospace; padding:6px 8px; border-radius:4px; resize:none;">Establish a robotic research settlement in Jezero, investigate scientifically valuable geological regions, deploy supporting infrastructure and prepare a hypothetical long-duration expedition.</textarea>
            <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:4px;">
              <button id="btnRunFlagshipMissionOS" class="hud-btn hud-btn-primary" style="font-size:10px; font-weight:700; padding:5px 12px; background:linear-gradient(135deg, #0088cc, #00e5ff); border:none; color:#000; cursor:pointer; border-radius:4px;">&#9654; EXECUTE FLAGSHIP DEMO (12 PHASES)</button>
              <button id="btnAdvanceSolMissionOS" class="hud-btn" style="font-size:10px; padding:5px 10px; background:#162436; border:1px solid #2c4766; color:#58a6ff; cursor:pointer; border-radius:4px;">+1 SOL</button>
              <button id="btnAdvance5SolMissionOS" class="hud-btn" style="font-size:10px; padding:5px 10px; background:#162436; border:1px solid #2c4766; color:#58a6ff; cursor:pointer; border-radius:4px;">+5 SOLS</button>
              <button id="btnDispatchEarthCmdMissionOS" class="hud-btn" style="font-size:10px; padding:5px 10px; background:#162436; border:1px solid #2c4766; color:#e6edf3; cursor:pointer; border-radius:4px;">DISPATCH EARTH CMD</button>
              <button id="btnInjectDustStormMissionOS" class="hud-btn" style="font-size:10px; padding:5px 10px; background:#3d1a1a; border:1px solid #aa3333; color:#ff7b72; cursor:pointer; border-radius:4px;">INJECT DUST STORM</button>
              <button id="btnVerifyReplayMissionOS" class="hud-btn" style="font-size:10px; padding:5px 10px; background:#162436; border:1px solid #2c4766; color:#7ee787; cursor:pointer; border-radius:4px;">VERIFY REPLAY</button>
              <button id="btnExportDossierMissionOS" class="hud-btn" style="font-size:10px; padding:5px 10px; background:#162436; border:1px solid #2c4766; color:#d2a8ff; cursor:pointer; border-radius:4px;">EXPORT DOSSIER</button>
            </div>
          </div>

          <!-- Live Mission Telemetry KPI Grid -->
          <div class="metrics-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:6px; margin-bottom:10px;">
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">MISSION SOL / TIME</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#00e5ff;"><span id="missionOSSol">SOL 01</span> <span id="missionOSSolTime" style="font-size:9px; color:#8899a6;">06:00:00</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">SOLAR LONGITUDE L_s</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#58a6ff;"><span id="missionOSLs">56.40&deg;</span> <span style="font-size:8px; color:#8899a6;">(SPRING)</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">POWER GENERATION / LOAD</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#7ee787;"><span id="missionOSPower">142.5 / 78.5</span> <span style="font-size:8px; color:#8899a6;">kWe</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">BATTERY STORAGE SOC</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#7ee787;"><span id="missionOSBattery">94.2%</span> <span style="font-size:8px; color:#8899a6;">(235 kWh)</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">LIFE SUPPORT (H2O / O2)</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#00e5ff;"><span id="missionOSWater">3,450</span> / <span id="missionOSOxygen">1,250</span> <span style="font-size:8px; color:#8899a6;">kg</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">SINTERED BERM BLOCKS</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#d2a8ff;"><span id="missionOSSinteredBlocks">120</span> <span style="font-size:8px; color:#8899a6;">/ 240 REQ</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">HABITAT CORE STATUS</div>
              <div class="metric-value" style="font-size:13px; font-weight:800; color:#7ee787;"><span id="missionOSHabStatus">101.3 kPa · 294 K</span></div>
            </div>
            <div class="metric-card" style="background:#091420; border:1px solid #1a2c40; padding:6px 8px; border-radius:4px;">
              <div class="metric-label" style="font-size:8px; color:#8899a6;">STATE SIGNATURE (SHA-256)</div>
              <div class="metric-value" style="font-size:10px; font-family:monospace; color:#8899a6;"><span id="missionOSStateHash">c8f9...31a2</span></div>
            </div>
          </div>
        </div>

        <!-- 7-Phase Multi-Sol Campaign Timeline / Workstream Gantt -->
        <div class="control-card" style="margin-bottom:8px; padding:10px;">
          <div style="font-size:10px; font-weight:700; color:#58a6ff; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <span>&#128197; 7-PHASE MULTI-SOL CAMPAIGN TIMELINE &times; WORKSTREAM DAG</span>
            <span style="font-size:9px; color:#8899a6;">TOTAL HORIZON: 60 SOLS · JEZERO CRATER</span>
          </div>
          <div id="missionOSPhasesContainer" style="display:flex; flex-direction:column; gap:6px;">
            <!-- Dynamically populated or rendered fallback -->
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#00e5ff;">PHASE A: Site Reconnaissance &amp; Geotechnical Survey (Sols 1-8)</span>
                <span id="phaseAProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseABar" style="background:#00e5ff; height:100%; width:100%;"></div>
              </div>
            </div>
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#58a6ff;">PHASE B: Infrastructure Staging &amp; Power Grid Deployment (Sols 9-16)</span>
                <span id="phaseBProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseBBar" style="background:#58a6ff; height:100%; width:100%;"></div>
              </div>
            </div>
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#7ee787;">PHASE C: Primary Habitat Pressurization &amp; Thermal Balance (Sols 17-25)</span>
                <span id="phaseCProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseCBar" style="background:#7ee787; height:100%; width:100%;"></div>
              </div>
            </div>
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#d2a8ff;">PHASE D: Pilot In-Situ Resource Utilization (ISRU) Operations (Sols 26-36)</span>
                <span id="phaseDProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseDBar" style="background:#d2a8ff; height:100%; width:100%;"></div>
              </div>
            </div>
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#f2cc60;">PHASE E: Distributed Planetary Science &amp; Sample Caching (Sols 37-46)</span>
                <span id="phaseEProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseEBar" style="background:#f2cc60; height:100%; width:100%;"></div>
              </div>
            </div>
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#ff7b72;">PHASE F: Deep-Space Autonomy &amp; Resilient Contingency Response (Sols 47-54)</span>
                <span id="phaseFProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseFBar" style="background:#ff7b72; height:100%; width:100%;"></div>
              </div>
            </div>
            <div class="phase-row" style="background:#081018; border:1px solid #1b2838; border-radius:4px; padding:6px 10px;">
              <div style="display:flex; justify-content:space-between; font-size:9px; font-weight:700; margin-bottom:4px;">
                <span style="color:#00e5ff;">PHASE G: Long-Duration Expedition Readiness &amp; Final Review (Sols 55-60)</span>
                <span id="phaseGProgress" style="color:#7ee787;">100% COMPLETE</span>
              </div>
              <div style="background:#14202e; height:6px; border-radius:3px; overflow:hidden;">
                <div id="phaseGBar" style="background:#00e5ff; height:100%; width:100%;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Heterogeneous Asset Fleet Telemetry Table -->
        <div class="control-card" style="margin-bottom:8px; padding:10px;">
          <div style="font-size:10px; font-weight:700; color:#58a6ff; margin-bottom:8px;">&#129302; HETEROGENEOUS PLANETARY FLEET &times; INFRASTRUCTURE REGISTRY</div>
          <div style="overflow-x:auto;">
            <table style="width:100%; font-size:9px; border-collapse:collapse; text-align:left;">
              <thead>
                <tr style="border-bottom:1px solid #223448; color:#8899a6;">
                  <th style="padding:4px 6px;">ASSET ID</th>
                  <th style="padding:4px 6px;">TYPE</th>
                  <th style="padding:4px 6px;">HEALTH</th>
                  <th style="padding:4px 6px;">BATTERY / FUEL</th>
                  <th style="padding:4px 6px;">POWER DRAW</th>
                  <th style="padding:4px 6px;">ACTIVE TASK</th>
                  <th style="padding:4px 6px;">COORDINATES</th>
                </tr>
              </thead>
              <tbody id="missionOSFleetTableBody">
                <tr style="border-bottom:1px solid #111e2e;">
                  <td style="padding:4px 6px; font-weight:700; color:#00e5ff;">ATLAS-ROVER-01</td>
                  <td style="padding:4px 6px;">GROUND_ROVER</td>
                  <td style="padding:4px 6px;"><span class="badge" style="background:#1b3d2f; color:#7ee787; padding:2px 4px; border-radius:2px;">NOMINAL</span></td>
                  <td style="padding:4px 6px;">98.5%</td>
                  <td style="padding:4px 6px;">1.20 kWe</td>
                  <td style="padding:4px 6px; color:#58a6ff;">TASK-E-01 (Delta Scarp)</td>
                  <td style="padding:4px 6px; font-family:monospace;">18.4520&deg;N, 77.4350&deg;E</td>
                </tr>
                <tr style="border-bottom:1px solid #111e2e;">
                  <td style="padding:4px 6px; font-weight:700; color:#00e5ff;">HEXACOPTER-SURVEYOR-02</td>
                  <td style="padding:4px 6px;">AERIAL_ROTORCRAFT</td>
                  <td style="padding:4px 6px;"><span class="badge" style="background:#1b3d2f; color:#7ee787; padding:2px 4px; border-radius:2px;">NOMINAL</span></td>
                  <td style="padding:4px 6px;">95.0%</td>
                  <td style="padding:4px 6px;">0.10 kWe</td>
                  <td style="padding:4px 6px; color:#58a6ff;">TASK-E-02 (Séítah Scan)</td>
                  <td style="padding:4px 6px; font-family:monospace;">18.4380&deg;N, 77.4420&deg;E</td>
                </tr>
                <tr style="border-bottom:1px solid #111e2e;">
                  <td style="padding:4px 6px; font-weight:700; color:#00e5ff;">CONSTRUCTION-BOT-01</td>
                  <td style="padding:4px 6px;">CONSTRUCTION_BOT</td>
                  <td style="padding:4px 6px;"><span class="badge" style="background:#1b3d2f; color:#7ee787; padding:2px 4px; border-radius:2px;">NOMINAL</span></td>
                  <td style="padding:4px 6px;">92.0%</td>
                  <td style="padding:4px 6px;">2.00 kWe</td>
                  <td style="padding:4px 6px; color:#7ee787;">BERM SINTERING COMPLETE</td>
                  <td style="padding:4px 6px; font-family:monospace;">18.4450&deg;N, 77.4512&deg;E</td>
                </tr>
                <tr style="border-bottom:1px solid #111e2e;">
                  <td style="padding:4px 6px; font-weight:700; color:#00e5ff;">KILOPOWER-REACTOR-01</td>
                  <td style="padding:4px 6px;">POWER_STATION</td>
                  <td style="padding:4px 6px;"><span class="badge" style="background:#1b3d2f; color:#7ee787; padding:2px 4px; border-radius:2px;">NOMINAL</span></td>
                  <td style="padding:4px 6px;">100.0%</td>
                  <td style="padding:4px 6px;">120.0 kWe</td>
                  <td style="padding:4px 6px; color:#7ee787;">BASELOAD GRID SUPPLY</td>
                  <td style="padding:4px 6px; font-family:monospace;">18.4480&deg;N, 77.4540&deg;E</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Deep-Space Autonomy & Science Hypotheses Split Grid -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
          <!-- Autonomy & Delay -->
          <div class="control-card" style="padding:10px;">
            <div style="font-size:10px; font-weight:700; color:#58a6ff; margin-bottom:6px;">&#128760; DEEP-SPACE AUTONOMY &times; LIGHT-TIME LAG</div>
            <div style="font-size:9px; color:#8899a6; line-height:1.5;">
              <div>Orbital Geometry: <strong>1.708 AU</strong> (~255.5M km)</div>
              <div>One-Way Light Time (OWLT): <strong style="color:#00e5ff;">14.2 min (852.3 s)</strong></div>
              <div>Round-Trip Light Time (RTLT): <strong>28.4 min</strong></div>
              <div>Stale Command State Guard: <strong style="color:#7ee787;">ACTIVE (Hash Verified)</strong></div>
              <div style="margin-top:4px; padding:4px 6px; background:#081018; border-radius:3px; font-size:8px; color:#7ee787; border:1px solid #1b3d2f;">
                &#10004; Outdated command packets targeting divergent Martian state hashes automatically rejected with STALE_STATE_HASH_REJECTED.
              </div>
            </div>
          </div>

          <!-- Science Discovery Hypotheses -->
          <div class="control-card" style="padding:10px;">
            <div style="font-size:10px; font-weight:700; color:#58a6ff; margin-bottom:6px;">&#129504; AUTONOMOUS SCIENCE &times; BAYESIAN HYPOTHESES</div>
            <div style="font-size:9px; color:#8899a6; line-height:1.5;">
              <div>Delta Scarp Clays: <strong style="color:#7ee787;">p = 0.942</strong> (Prior: 0.65 · +0.65 bits)</div>
              <div>Séítah Olivine Cumulate: <strong style="color:#7ee787;">p = 0.885</strong> (Prior: 0.50 · +0.48 bits)</div>
              <div>Regolith Perchlorate: <strong style="color:#f2cc60;">p = 0.400</strong> (Prior: 0.40)</div>
              <div>Belva Rim Fault Hydrothermal: <strong style="color:#8899a6;">p = 0.200</strong> (Prior: 0.20)</div>
              <div style="margin-top:4px; font-size:8px; color:#00e5ff;">
                Total Information Gain: <strong>+1.134 Shannon Bits</strong> · Provenance: USGS CTX Jezero 20m
              </div>
            </div>
          </div>
        </div>

        <!-- Resilience Recovery & Phase F Review Split Grid -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px;">
          <!-- Resilience Console -->
          <div class="control-card" style="padding:10px;">
            <div style="font-size:10px; font-weight:700; color:#ff7b72; margin-bottom:6px;">&#9762; CONTINGENCY INJECTION &times; FDDI RECOVERY</div>
            <div style="font-size:9px; color:#8899a6; line-height:1.5;">
              <div>Active Contingency: <strong id="missionOSContingencyStatus" style="color:#7ee787;">NONE (NOMINAL CRUISE)</strong></div>
              <div>Autonomous FDDI Diagnosis: <span id="missionOSDiagnosisText">Subsystem watchdogs fully nominal.</span></div>
              <div>Load-Shedding Hierarchy: <span>1. Sintering &rarr; 2. Standby Electrolysis &rarr; 3. Baseline Reactor</span></div>
              <div style="margin-top:4px; font-size:8px; color:#7ee787;">
                Thermal Core Safeguard: Habitat temperature maintained at <strong>294.15 K (+21.0&deg;C)</strong> throughout dust storms.
              </div>
            </div>
          </div>

          <!-- Phase F Readiness Review -->
          <div class="control-card" style="padding:10px;">
            <div style="font-size:10px; font-weight:700; color:#7ee787; margin-bottom:6px;">&#127942; PHASE F EXPEDITION READINESS REVIEW</div>
            <div style="font-size:9px; color:#8899a6; line-height:1.5;">
              <div>Readiness Qualification Score: <strong id="missionOSReadinessScore" style="color:#7ee787; font-size:13px;">100.0% / PASSED</strong></div>
              <div>Mass Conservation Discrepancy: <strong style="color:#7ee787;">0.000 kg (100% Closed Loop)</strong></div>
              <div>Consumable Reserve Margin: <strong>345+ Sols H2O · 412+ Sols O2</strong></div>
              <div>Cryptographic Replay Audit: <strong id="missionOSReplayAuditBadge" style="color:#7ee787;">100% BIT-EXACT VERIFIED</strong></div>
            </div>
          </div>
        </div>

        <!-- Mandatory NASA Space Apps Scientific Integrity Notice -->
        <div style="background:#091420; border:1px solid #1a2c40; border-radius:4px; padding:8px 10px; font-size:8px; color:#8899a6; line-height:1.4;">
          <strong style="color:var(--telemetry-cyan);">&#9888; NASA Space Apps Scientific Integrity Notice:</strong>
          All simulated routes, life-support consumable balances, and schedules generated by Atlas Planetary Mission OS represent remote-sensing heuristics and computational simulations. They do not constitute human flight-certified operations or operational safety guarantees. Terrain datasets derived strictly from authentic USGS CTX 20m Jezero Crater DTM (<code style="color:#58a6ff;">SHA-256: 875e7e...f5b3</code>).
        </div>
      </div>
'''
    if panel_target in content:
        content = content.replace(panel_target, panel_html + "\n" + panel_target, 1)
    else:
        print("Panel target not found!")
        sys.exit(1)

    with open("web/index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched web/index.html with Mission OS tab and panel!")

if __name__ == "__main__":
    patch()
