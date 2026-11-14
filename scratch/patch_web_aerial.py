import re

# 1. Patch styles.css
aerial_css = """
/* =========================================================================
   MILESTONE 13P: ATLAS AERIAL CORPS FLIGHT OPERATIONS STYLES
   ========================================================================= */
.aerial-corps-panel {
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.aerial-corps-card {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(12, 74, 110, 0.90));
  border: 1px solid rgba(14, 165, 233, 0.4);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
}
.aerial-corps-header-badge {
  background: rgba(14, 165, 233, 0.2);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.6);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.aerial-corps-metric-box {
  background: rgba(0, 0, 0, 0.35);
  border-radius: 4px;
  padding: 6px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.aerial-corps-aircraft-card {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 5px;
  padding: 8px;
  margin-bottom: 6px;
}
.aerial-corps-aircraft-card.active-aircraft {
  border-color: #38bdf8;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
}
.aerial-corps-stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  margin-bottom: 4px;
  font-size: 9px;
  border-left: 3px solid #64748b;
}
.aerial-corps-stage-item.completed {
  border-left-color: #10b981;
}
.aerial-corps-stage-item.active {
  border-left-color: #38bdf8;
  background: rgba(14, 165, 233, 0.15);
}
"""

with open("web/styles.css", "a", encoding="utf-8") as f:
    f.write(aerial_css)
print("Updated web/styles.css with aerial corps styling.")

# 2. Patch index.html
with open("web/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Add Tab Button
old_btn = '<button class="inspector-tab" data-tab="tabDeepSpaceAutonomy" id="tabBtnDeepSpaceAutonomy" title="Atlas Deep Space Autonomy Lab: Earth-Mars Communication, Distributed Intelligence &amp; Bounded Autonomous Operations">&#128760; Deep Space Autonomy</button>'
new_btn = old_btn + '\n        <button class="inspector-tab" data-tab="tabAerialCorps" id="tabBtnAerialCorps" title="Atlas Aerial Corps: Multi-Rotorcraft Intelligence, Aerial Science, Flight Dynamics &amp; Rover-Aircraft Cooperation">&#128641; Aerial Corps</button>'

if 'id="tabBtnAerialCorps"' not in html:
    html = html.replace(old_btn, new_btn, 1)

# Add Tab Panel
aerial_panel_html = """
      <!-- TAB: ATLAS AERIAL CORPS FLIGHT OPERATIONS CENTER (Milestone 13P) -->
      <div id="tabAerialCorps" class="inspector-tab-panel hidden aerial-corps-panel">
        <!-- 0. Header & Flight Control Bar -->
        <div class="aerial-corps-card" style="border-color:rgba(14,165,233,0.7); box-shadow:0 0 15px rgba(14,165,233,0.25);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <span class="control-label" style="font-size:12px; font-weight:800; color:#38bdf8; letter-spacing:0.5px;">&#128641; ATLAS AERIAL CORPS &mdash; FLIGHT OPERATIONS CENTER</span>
              <div style="font-size:9.5px; color:#cbd5e1; margin-top:2px;">Planetary Rotorcraft Intelligence &bull; Rotor Aerodynamics &bull; 3D Navigation &bull; Rover-Aircraft Synergy</div>
            </div>
            <span id="acFlightStatusBadge" class="aerial-corps-header-badge">AERIAL OPERATIONS ACTIVE</span>
          </div>

          <!-- Scenario Director & Scenario Selector -->
          <div style="display:flex; gap:6px; margin-top:8px; align-items:center; flex-wrap:wrap;">
            <select id="acScenarioSelect" class="hud-select" style="font-size:9.5px; padding:3px 6px; flex:1; min-width:200px; background:#0f172a; border-color:#0284c7; color:#e2e8f0;">
              <!-- Populated by app.js -->
            </select>
            <button id="btnAcRunScenario" class="btn-primary" style="font-size:9.5px; padding:4px 10px; background:linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%); color:#ffffff; font-weight:700; border:1px solid #38bdf8;">&#9654; EXECUTE MISSION</button>
            <button id="btnAcEvalPerf" class="btn-secondary" style="font-size:9.5px; padding:4px 8px;">&#9881; EVAL ENVELOPE</button>
            <button id="btnAcJointPlan" class="btn-secondary" style="font-size:9.5px; padding:4px 8px; color:#38bdf8;">&#129309; JOINT RECON</button>
            <button id="btnAcReset" class="btn-secondary" style="font-size:9.5px; padding:4px 8px;">&#128260; RESET FLEET</button>
          </div>
        </div>

        <!-- 1. Planetary Flight Fleet HUD -->
        <div class="aerial-corps-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">1. PLANETARY AIRCRAFT FLEET HUD</span>
            <span id="acFleetCountBadge" class="badge" style="background:rgba(14,165,233,0.2); color:#38bdf8; border:1px solid rgba(14,165,233,0.5); font-size:8.5px;">3 AIRCRAFT REGISTERED</span>
          </div>
          <div id="acFleetCardsContainer">
            <!-- Roster cards populated dynamically -->
          </div>
        </div>

        <!-- 2. Aerodynamics Laboratory Panel -->
        <div class="aerial-corps-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">2. MARTIAN AERODYNAMICS LABORATORY</span>
            <span id="acAeroFidelityBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#34d399; font-size:8.5px;">MOMENTUM &amp; BEM (LEVEL 1-2)</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px; margin-bottom:6px;">
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">ATMOS DENSITY (&rho;)</div>
              <div id="acMetricDensity" style="font-size:11px; font-weight:700; color:#38bdf8;">0.0150 kg/m&sup3;</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">SPEED OF SOUND</div>
              <div id="acMetricSound" style="font-size:11px; font-weight:700; color:#38bdf8;">228.9 m/s</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">TIP MACH (M_tip)</div>
              <div id="acMetricMach" style="font-size:11px; font-weight:700; color:#f59e0b;">0.702</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">THRUST MARGIN</div>
              <div id="acMetricThrustMargin" style="font-size:11px; font-weight:700; color:#10b981;">1.28 &ge; 1.15</div>
            </div>
          </div>
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px;">
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">HOVER POWER</div>
              <div id="acMetricHoverPower" style="font-size:11px; font-weight:700; color:#f87171;">362.4 W</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">BEST CRUISE SPEED</div>
              <div id="acMetricCruiseSpeed" style="font-size:11px; font-weight:700; color:#38bdf8;">6.5 m/s</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">EST. ENDURANCE</div>
              <div id="acMetricEndurance" style="font-size:11px; font-weight:700; color:#10b981;">142.5 s</div>
            </div>
          </div>
        </div>

        <!-- 3. 3D Flight Planning & Terrain Clearance Studio -->
        <div class="aerial-corps-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">3. 3D TERRAIN FLIGHT CORRIDOR &amp; LANDING EVALUATION</span>
            <span id="acCorridorStatusBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#34d399; font-size:8.5px;">CLEARANCE VERIFIED (&ge; 8m)</span>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:9px; margin-bottom:6px;">
            <div style="background:rgba(0,0,0,0.35); padding:6px; border-radius:4px;">
              <strong style="color:#38bdf8;">PLANNED 3D CORRIDOR:</strong>
              <div id="acCorridorDetails" style="margin-top:2px; color:#cbd5e1;">Airfield Alpha (0, 0) &rarr; Airfield Bravo (80, 95) &bull; 128.5m 3D Flight Dist &bull; Alt 15.0m AGL</div>
            </div>
            <div style="background:rgba(0,0,0,0.35); padding:6px; border-radius:4px;">
              <strong style="color:#10b981;">TOUCHDOWN SUITABILITY:</strong>
              <div id="acLandingSuitabilityDetails" style="margin-top:2px; color:#cbd5e1;">Slope: 3.2&deg; (&le; 8&deg;) &bull; Roughness: 0.04m &bull; Obstacles: 0 within 12m => SAFE</div>
            </div>
          </div>
        </div>

        <!-- 4. Aerial Science & Radar Sounding Panel -->
        <div class="aerial-corps-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">4. AERIAL SCIENCE OPERATIONS &amp; OBSERVATIONS</span>
            <span id="acScienceObsBadge" class="badge" style="background:rgba(245,158,11,0.2); color:#fbbf24; font-size:8.5px;">1 OBSERVATION LOGGED</span>
          </div>
          <div id="acScienceDetailsBox" style="background:rgba(0,0,0,0.35); border-radius:4px; padding:6px 8px; font-size:9px; line-height:1.4;">
            <div style="display:flex; justify-content:space-between;">
              <strong style="color:#fbbf24;">HIGH-RESOLUTION AERIAL OPTICAL STEREO (0.78 cm/px)</strong>
              <span style="color:#94a3b8;">OBS-VIS-0842</span>
            </div>
            <div style="color:#cbd5e1; margin-top:2px;">Target: Jezero Delta Rim Escarpment &bull; Footprint Radius: 12.4m &bull; Albedo: 0.235</div>
            <div style="color:#f87171; font-weight:700; margin-top:2px;">&#9888; DISCOVERY: 14 boulders (&gt; 0.85m) mapped along baseline ground traverse path.</div>
          </div>
        </div>

        <!-- 5. Rover-Aircraft Cooperative Reconnaissance Center -->
        <div class="aerial-corps-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">5. ROVER&ndash;AIRCRAFT COOPERATIVE VALUE QUANTIFICATION</span>
            <span id="acCoopStatusBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#34d399; font-size:8.5px;">COOPERATION HIGH VALUE</span>
          </div>
          <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:6px;">
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">ROVER DIST SAVED</div>
              <div id="acMetricDistSaved" style="font-size:11px; font-weight:700; color:#10b981;">62.4 m</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">UNCERTAINTY DROP</div>
              <div id="acMetricUncertaintyDrop" style="font-size:11px; font-weight:700; color:#38bdf8;">68% &rarr; 8.5%</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">HAZARDS AVOIDED</div>
              <div id="acMetricHazardsCount" style="font-size:11px; font-weight:700; color:#fbbf24;">14 Boulders</div>
            </div>
            <div class="aerial-corps-metric-box">
              <div style="font-size:8px; color:#94a3b8;">NET ENERGY SAVINGS</div>
              <div id="acMetricNetEnergy" style="font-size:11px; font-weight:700; color:#10b981;">+82.4 Wh</div>
            </div>
          </div>
        </div>

        <!-- 6. Scenario Execution Director & Live Stage Progression -->
        <div class="aerial-corps-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">6. SCENARIO STAGE EXECUTION PROGRESSION</span>
            <span id="acScenarioStageCountBadge" class="badge" style="background:rgba(14,165,233,0.2); color:#38bdf8; border:1px solid rgba(14,165,233,0.5); font-size:8.5px;">STAGE 0 / 6</span>
          </div>
          <div id="acScenarioStagesContainer" style="max-height:160px; overflow-y:auto;">
            <!-- Populated dynamically by app.js -->
          </div>
        </div>

        <!-- 7. Mandatory Astronaut Safety Disclosure Notice -->
        <div style="padding:8px 10px; border-radius:4px; font-size:8px; line-height:1.4; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); color:#fca5a5; margin-bottom:8px;">
          <strong>MANDATORY SCIENTIFIC &amp; SAFETY DISCLOSURE:</strong> All planetary flight aerodynamics, rotor performance envelopes, aerial navigation corridors, and multi-rotorcraft fleet coordination algorithms developed in Milestone 13P are robotic research and aerospace simulation tools. Under planetary aerospace standards, these simulated outputs must <strong>NEVER be interpreted as certified safe for human astronauts or crewed planetary landing systems</strong>.
        </div>
      </div>
"""

target_insert = '<!-- TAB: ATLAS DEEP SPACE AUTONOMY CONTROL CENTER (Milestone 13O) -->'
# Insert right after tabDeepSpaceAutonomy closing tag
deep_space_close = '</div>\n<div id="tabPlan" class="inspector-tab-panel hidden">'
new_deep_space_close = '</div>\n' + aerial_panel_html + '\n<div id="tabPlan" class="inspector-tab-panel hidden">'

if 'id="tabAerialCorps"' not in html:
    html = html.replace(deep_space_close, new_deep_space_close, 1)

with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Updated web/index.html with aerial corps panel.")
