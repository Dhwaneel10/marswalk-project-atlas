import os
import re

INDEX_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\index.html"
STYLES_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\styles.css"
APP_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"

print("--- 1. Appending Styles to styles.css ---")
with open(STYLES_PATH, "r", encoding="utf-8") as f:
    css = f.read()

deep_space_css = """
/* =========================================================================
   MILESTONE 13O: DEEP SPACE AUTONOMY CONTROL CENTER STYLES
   ========================================================================= */
.deep-space-panel {
  color: #cbd5e1;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.deep-space-card {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 27, 75, 0.92));
  border: 1px solid rgba(139, 92, 246, 0.4);
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}
.deep-space-header-badge {
  background: rgba(139, 92, 246, 0.2);
  color: #c084fc;
  border: 1px solid rgba(139, 92, 246, 0.6);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.deep-space-metric-box {
  background: rgba(0, 0, 0, 0.35);
  border-radius: 4px;
  padding: 6px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.05);
}
.deep-space-stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  margin-bottom: 4px;
  border-left: 3px solid #8b5cf6;
  font-size: 9px;
}
.deep-space-stage-item.completed {
  border-left-color: #10b981;
}
.deep-space-dual-track {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(0, 0, 0, 0.4);
  padding: 8px;
  border-radius: 4px;
}
.deep-space-track-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 9px;
}
.deep-space-track-lane {
  flex: 1;
  height: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 0 6px;
}
"""

if "MILESTONE 13O: DEEP SPACE AUTONOMY CONTROL CENTER STYLES" not in css:
    with open(STYLES_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + deep_space_css)
    print("styles.css updated with Deep Space styles.")
else:
    print("styles.css already contains Deep Space styles.")

print("--- 2. Updating index.html ---")
with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Add Tab Button
old_tab_btn = '<button class="inspector-tab" data-tab="tabEnvironmentValidation" id="tabBtnEnvironmentValidation"'
new_tab_btn = '<button class="inspector-tab" data-tab="tabDeepSpaceAutonomy" id="tabBtnDeepSpaceAutonomy" title="Atlas Deep Space Autonomy Lab: Earth–Mars Communication, Distributed Intelligence &amp; Bounded Autonomous Operations">&#128760; Deep Space Autonomy</button>\n        <button class="inspector-tab" data-tab="tabEnvironmentValidation" id="tabBtnEnvironmentValidation"'

if 'id="tabBtnDeepSpaceAutonomy"' not in html:
    html = html.replace(old_tab_btn, new_tab_btn, 1)
    print("Added tabBtnDeepSpaceAutonomy to index.html")
else:
    print("tabBtnDeepSpaceAutonomy already exists in index.html")

# Add Tab Panel
deep_space_panel_html = """      <!-- TAB: ATLAS DEEP SPACE AUTONOMY CONTROL CENTER (Milestone 13O) -->
      <div id="tabDeepSpaceAutonomy" class="inspector-tab-panel hidden deep-space-panel">
        <!-- 0. Header & Mission Control Bar -->
        <div class="deep-space-card" style="border-color:rgba(168,85,247,0.7); box-shadow:0 0 15px rgba(168,85,247,0.2);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <span class="control-label" style="font-size:12px; font-weight:800; color:#c084fc; letter-spacing:0.5px;">&#128760; DEEP SPACE AUTONOMY CONTROL CENTER</span>
              <div style="font-size:9.5px; color:#cbd5e1; margin-top:2px;">Earth–Mars Delay Simulation &bull; Bounded Onboard Intelligence &bull; Stale Plan Interception &bull; 10 Scenarios</div>
            </div>
            <span id="dsAutonomyStatusBadge" class="deep-space-header-badge">EARTH–MARS AUTONOMY ENGAGED</span>
          </div>

          <!-- Scenario Director Selector Bar -->
          <div style="display:flex; gap:6px; margin-top:8px; align-items:center; flex-wrap:wrap;">
            <select id="dsScenarioSelect" class="hud-select" style="font-size:9.5px; padding:3px 6px; flex:1; min-width:200px; background:#0f172a; border-color:#8b5cf6; color:#e2e8f0;">
              <!-- Populated by app.js -->
            </select>
            <button id="btnDsRunScenario" class="btn-primary" style="font-size:9.5px; padding:4px 10px; background:linear-gradient(135deg, #a855f7 0%, #7e22ce 100%); color:#ffffff; font-weight:700; border:1px solid #c084fc;">&#9654; RUN SCENARIO</button>
            <button id="btnDsAdvanceTime" class="btn-secondary" style="font-size:9.5px; padding:4px 8px;">&#9203; ADVANCE (+5 MIN)</button>
            <button id="btnDsInjectHazard" class="btn-secondary" style="font-size:9.5px; padding:4px 8px; color:#f87171;">&#9888; INJECT OBSTACLE</button>
            <button id="btnDsResetSim" class="btn-secondary" style="font-size:9.5px; padding:4px 8px;">&#128260; RESET</button>
          </div>
        </div>

        <!-- 1. Earth–Mars Communications & Latency HUD -->
        <div class="deep-space-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">1. DEEP SPACE PROPAGATION &amp; CONTACT STATE</span>
            <span id="dsContactStateBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; border:1px solid rgba(16,185,129,0.6); font-size:8.5px;">DSN X-BAND ACTIVE</span>
          </div>
          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; margin-bottom:6px;">
            <div class="deep-space-metric-box">
              <span style="font-size:8px; color:#94a3b8; display:block;">ONE-WAY UPLINK</span>
              <strong id="dsUplinkDelayText" style="font-size:13px; color:#38bdf8; font-family:monospace;">14.2 min</strong>
              <div style="font-size:7.5px; color:#94a3b8;">Earth &rarr; Mars</div>
            </div>
            <div class="deep-space-metric-box">
              <span style="font-size:8px; color:#94a3b8; display:block;">ONE-WAY DOWNLINK</span>
              <strong id="dsDownlinkDelayText" style="font-size:13px; color:#38bdf8; font-family:monospace;">14.2 min</strong>
              <div style="font-size:7.5px; color:#94a3b8;">Mars &rarr; Earth</div>
            </div>
            <div class="deep-space-metric-box">
              <span style="font-size:8px; color:#94a3b8; display:block;">ROUND-TRIP LIGHT TIME</span>
              <strong id="dsRtltText" style="font-size:13px; color:#c084fc; font-family:monospace;">28.4 min</strong>
              <div style="font-size:7.5px; color:#94a3b8;">RTLT Total Lag</div>
            </div>
            <div class="deep-space-metric-box">
              <span style="font-size:8px; color:#94a3b8; display:block;">IN-FLIGHT PACKETS</span>
              <strong id="dsInFlightText" style="font-size:13px; color:#f59e0b; font-family:monospace;">0 UP / 0 DN</strong>
              <div style="font-size:7.5px; color:#94a3b8;">Signal Channels</div>
            </div>
          </div>
        </div>

        <!-- 2. Dual-Track Timeline Visualization (Earth vs Mars) -->
        <div class="deep-space-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">2. DUAL-TRACK MISSION TIMELINE (TIME-DELAYED CAUSALITY)</span>
            <span style="font-size:8.5px; color:#38bdf8;">SIMULATED CLOCK: <span id="dsSimTimeText" style="font-family:monospace;">00:00:00</span></span>
          </div>
          <div class="deep-space-dual-track">
            <div class="deep-space-track-row">
              <span style="width:65px; color:#38bdf8; font-weight:700;">EARTH:</span>
              <div class="deep-space-track-lane" id="dsEarthTimelineTrack">
                <span id="dsEarthTimelineContent" style="color:#94a3b8; font-style:italic;">Awaiting telecommand authoring...</span>
              </div>
            </div>
            <div class="deep-space-track-row">
              <span style="width:65px; color:#c084fc; font-weight:700;">CHANNEL:</span>
              <div class="deep-space-track-lane" id="dsChannelTimelineTrack">
                <span id="dsChannelTimelineContent" style="color:#94a3b8; font-style:italic;">Propagation delay: 14.2 min one-way light time</span>
              </div>
            </div>
            <div class="deep-space-track-row">
              <span style="width:65px; color:#10b981; font-weight:700;">MARS:</span>
              <div class="deep-space-track-lane" id="dsMarsTimelineTrack">
                <span id="dsMarsTimelineContent" style="color:#94a3b8; font-style:italic;">Rover Alpha standing by in BOUNDED_AUTONOMY mode</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Rover Autonomy Cockpit & Decision Explanation -->
        <div class="deep-space-card" style="border-left:3px solid #10b981;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#10b981;">3. ONBOARD ROVER AUTONOMY COCKPIT</span>
            <span id="dsRoverModeBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; border:1px solid rgba(16,185,129,0.6); font-size:8.5px;">MODE: BOUNDED_AUTONOMY</span>
          </div>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:9.5px; margin-bottom:6px;">
            <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
              <span style="color:#94a3b8; display:block;">BATTERY &amp; ENERGY RESERVE</span>
              <strong id="dsBatteryChargeText" style="color:#10b981; font-family:monospace;">900.0 Wh (75%)</strong>
              <div style="font-size:8px; color:#cbd5e1; margin-top:2px;">Hard reserve limit: 200.0 Wh</div>
            </div>
            <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
              <span style="color:#94a3b8; display:block;">IN-SITU STATE VERSION</span>
              <strong id="dsRoverStateVerText" style="color:#38bdf8; font-family:monospace;">Version 1</strong>
              <div style="font-size:8px; color:#cbd5e1; margin-top:2px;">Waypoint: WP_BASE_OCTAVIA</div>
            </div>
          </div>

          <!-- Stale Command / Decision Explanation Box -->
          <div id="dsDecisionExplanationBox" style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.08); border-radius:4px; padding:6px 8px; font-size:9px; line-height:1.4;">
            <strong style="color:#f59e0b; display:block; margin-bottom:2px;">LATEST AUTONOMOUS DECISION RECORD:</strong>
            <div id="dsDecisionText" style="color:#cbd5e1;">Standing by for incoming command evaluation.</div>
          </div>
        </div>

        <!-- 4. Scenario Execution Director & Live Stage Progression -->
        <div class="deep-space-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">4. SCENARIO STAGE EXECUTION PROGRESSION</span>
            <span id="dsScenarioStageCountBadge" class="badge" style="background:rgba(139,92,246,0.2); color:#c084fc; border:1px solid rgba(139,92,246,0.6); font-size:8.5px;">STAGE 0 / 8</span>
          </div>
          <div id="dsScenarioStagesContainer" style="max-height:150px; overflow-y:auto;">
            <!-- Populated dynamically by app.js -->
          </div>
        </div>

        <!-- 5. Mandatory Astronaut Safety Disclosure Notice -->
        <div style="padding:8px 10px; border-radius:4px; font-size:8px; line-height:1.4; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); color:#fca5a5; margin-bottom:8px;">
          <strong>MANDATORY SCIENTIFIC &amp; SAFETY DISCLOSURE:</strong> All deep space communications, one-way propagation delays, link margins, contact windows, and autonomous rover decisions are computational research simulations for robotic planetary exploration. Under NASA planetary mission assurance standards, these simulated outputs must <strong>NEVER be interpreted as certified safe for human astronauts or operational extravehicular activity (EVA)</strong>.
        </div>
      </div>
"""

target_split = '<div id="tabPlan" class="inspector-tab-panel hidden">'
if target_split in html and 'id="tabDeepSpaceAutonomy"' not in html:
    html = html.replace(target_split, deep_space_panel_html + target_split, 1)
    print("Added tabDeepSpaceAutonomy panel to index.html")
else:
    print("tabDeepSpaceAutonomy panel already exists or target_split not found.")

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print("index.html updated successfully.")
