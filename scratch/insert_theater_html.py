import os

index_path = r"E:\Python\NASA-Spaceapps\Marswalk\web\index.html"
with open(index_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Header Button
header_target = '<button id="btnHeaderDemoMode"'
theater_header_btn = '''<button id="btnHeaderMissionTheater" class="btn-primary btn-header-theater" style="font-size: 10px; padding: 4px 10px; background: linear-gradient(135deg, #059669 0%, #10b981 100%); border-color: #34d399;" title="Launch Atlas 3D Mission Theater Mode (Key: T)">
        &#127917; 3D THEATER
      </button>

      <button id="btnHeaderDemoMode"'''

if 'id="btnHeaderMissionTheater"' not in content:
    content = content.replace(header_target, theater_header_btn, 1)

# 2. Demo Banner Button
demo_banner_target = '<button id="btnToggleDemoExplain"'
demo_theater_btn = '''<button id="btnDemoMissionTheater" class="btn-demo-exit" style="border-color:rgba(16,185,129,0.5); color:#34d399;" title="Launch Atlas 3D Mission Theater">
        &#127917; 3D Theater
      </button>
      <button id="btnToggleDemoExplain"'''

if 'id="btnDemoMissionTheater"' not in content:
    content = content.replace(demo_banner_target, demo_theater_btn, 1)

# 3. Mission Theater HUD and Inspector Card
cockpit_end = '    </div>\n  </div>\n\n  <!-- HUD Header Bar -->'
if cockpit_end not in content:
    cockpit_end = '    </div>\r\n  </div>\r\n\r\n  <!-- HUD Header Bar -->'

theater_hud_html = '''    </div>
  </div>

  <!-- Milestone 13C: Atlas 3D Mission Theater HUD & Spatial Digital Twin Controls -->
  <div id="missionTheaterHUD" class="mission-theater-hud hidden">
    <!-- Top Theater Command Bar -->
    <div class="theater-top-bar">
      <div class="theater-brand">
        <span class="theater-pill">&#127917; 3D MISSION THEATER</span>
        <span class="theater-dataset-tag" title="USGS Jezero 20m DTM (DOI: 10.5066/P906QQT8) • IAU 2000 Mars Spheroid">USGS CTX 20m DTM &bull; IAU 2000 MARS</span>
        <span class="theater-badge-truth">SPATIAL DIGITAL TWIN</span>
      </div>

      <!-- Telemetry Readouts -->
      <div class="theater-telemetry-row">
        <div class="theater-telemetry-item">
          <span class="theater-telemetry-label">SOL</span>
          <span id="theaterSolDisplay" class="theater-telemetry-val">1619</span>
        </div>
        <div class="theater-telemetry-item">
          <span class="theater-telemetry-label">MET</span>
          <span id="theaterClockDisplay" class="theater-telemetry-val">00:00:00</span>
        </div>
        <div class="theater-telemetry-item">
          <span class="theater-telemetry-label">PHASE</span>
          <span id="theaterPhaseDisplay" class="theater-telemetry-val">STANDBY</span>
        </div>
        <div class="theater-telemetry-item">
          <span class="theater-telemetry-label">UNIT</span>
          <span id="theaterUnitDisplay" class="theater-telemetry-val">ROVER-1</span>
        </div>
      </div>

      <!-- Exaggeration & Mode Controls -->
      <div class="theater-controls-right">
        <div class="theater-exaggeration-control">
          <span class="theater-control-label">EXAGGERATION:</span>
          <select id="theaterExaggerationSelect" class="theater-select" title="Visual Vertical Exaggeration (Does not alter analytical elevations)">
            <option value="1.0">1.0&times; (True 1:1 Scale)</option>
            <option value="1.5" selected>1.5&times; (Default Exploration)</option>
            <option value="2.0">2.0&times; (Relief Emphasis)</option>
            <option value="2.5">2.5&times; (Steep Scarp Analysis)</option>
            <option value="3.0">3.0&times; (High Relief)</option>
          </select>
        </div>
        <button id="btnTheaterExplain" class="theater-action-btn" title="Open Technical Explainability Formulary">&#129504; Formulary</button>
        <button id="btnExitTheaterMode" class="theater-exit-btn" title="Exit 3D Mission Theater Mode">&times; Exit Theater</button>
      </div>
    </div>

    <!-- Floating Top-Left Camera Director Bar -->
    <div class="theater-director-bar">
      <div class="theater-subpanel-title">&#127909; CAMERA DIRECTOR</div>
      <div class="theater-cam-pills" id="theaterCamPills">
        <button class="theater-pill-btn active" data-mode="orbit" title="Free Orbit View (User Controls)">&#127757; ORBIT</button>
        <button class="theater-pill-btn" data-mode="topographic" title="Oblique Topographic Scarp Perspective">&#127956; TOPOGRAPHIC</button>
        <button class="theater-pill-btn" data-mode="follow" title="Third-Person Unit Chase Camera">&#128640; FOLLOW UNIT</button>
        <button class="theater-pill-btn" data-mode="overview" title="Full Campaign Jezero Bounding Overview">&#128506; OVERVIEW</button>
        <button class="theater-pill-btn" data-mode="focus" title="Center Disturbance / Active Event Beacon">&#127919; EVENT FOCUS</button>
      </div>
    </div>

    <!-- Floating Top-Right Visual Layer & Trajectory Bar -->
    <div class="theater-layers-bar">
      <div class="theater-subpanel-title">&#128506; SURFACE &amp; TRAJECTORIES</div>
      <div class="theater-layer-pills" id="theaterLayerPills">
        <button class="theater-pill-btn active" data-layer="ortho" title="MRO CTX High-Res Orthomosaic Drape">CTX ORTHO</button>
        <button class="theater-pill-btn" data-layer="slope" title="Horn 3x3 Slope Gradient Coloration">SLOPE HAZARD</button>
        <button class="theater-pill-btn" data-layer="elevation" title="Hypsometric Color Tinting">HYPSOMETRIC</button>
        <button class="theater-pill-btn" data-layer="contour" title="Elevation Contour Lines">CONTOURS</button>
      </div>
      <div class="theater-trajectory-toggles" id="theaterTrajectoryToggles">
        <label class="theater-traj-toggle">
          <input type="checkbox" id="chkTheaterNominal" checked>
          <span class="theater-traj-legend" style="background:#00e5ff;"></span>
          <span>Nominal</span>
        </label>
        <label class="theater-traj-toggle">
          <input type="checkbox" id="chkTheaterDisturbed" checked>
          <span class="theater-traj-legend" style="background:#ef4444;"></span>
          <span>Disturbed</span>
        </label>
        <label class="theater-traj-toggle">
          <input type="checkbox" id="chkTheaterRecovered" checked>
          <span class="theater-traj-legend" style="background:#f59e0b;"></span>
          <span>Recovered</span>
        </label>
      </div>
    </div>

    <!-- Bottom Unified Simulation Transport Bar -->
    <div class="theater-transport-bar" id="theaterTransportBar">
      <div class="theater-playback-buttons">
        <button id="btnTheaterReset" class="theater-transport-btn" title="Reset Timeline to Start">&#9198;</button>
        <button id="btnTheaterStepBack" class="theater-transport-btn" title="Step Back 5 Seconds">&#9194; -5s</button>
        <button id="btnTheaterPlayPause" class="theater-transport-btn theater-play-btn" title="Play / Pause Rehearsal Playback">&#9654; PLAY</button>
        <button id="btnTheaterStepForward" class="theater-transport-btn" title="Step Forward 5 Seconds">&#9193; +5s</button>
      </div>

      <!-- Scrubber & Time -->
      <div class="theater-scrubber-container">
        <div class="theater-scrubber-labels">
          <span id="theaterTimeElapsed">00:00:00</span>
          <span id="theaterPlaybackStatus" class="theater-scrubber-status">NOMINAL TRAVERSE</span>
          <span id="theaterTimeTotal">00:00:00</span>
        </div>
        <input type="range" id="theaterTimelineScrubber" class="theater-scrubber-slider" min="0" max="100" value="0" step="0.1">
      </div>

      <!-- Speed Multipliers -->
      <div class="theater-speed-pills" id="theaterSpeedPills">
        <button class="theater-speed-btn active" data-speed="1">1&times;</button>
        <button class="theater-speed-btn" data-speed="2">2&times;</button>
        <button class="theater-speed-btn" data-speed="5">5&times;</button>
        <button class="theater-speed-btn" data-speed="10">10&times;</button>
      </div>

      <!-- Audio & Units -->
      <div class="theater-transport-extra">
        <button id="btnTheaterAudio" class="theater-transport-btn" title="Toggle Synthesized Mission Audio Cues">&#128266;</button>
        <button id="btnTheaterCenterUnit" class="theater-transport-btn" title="Center Camera on Active Exploration Unit">&#127919;</button>
      </div>
    </div>
  </div>

  <!-- Milestone 13C: Interactive Raycast Spatial Inspector Card -->
  <div id="theaterInspectorCard" class="theater-inspector-card hidden">
    <div class="theater-inspector-header">
      <div class="theater-inspector-title">
        <span class="status-dot"></span>
        <span id="theaterInspectorType">TERRAIN CELL</span>
      </div>
      <button id="btnCloseTheaterInspector" class="theater-inspector-close">&times;</button>
    </div>
    <div class="theater-inspector-body" id="theaterInspectorBody">
      <!-- Populated dynamically via raycast -->
    </div>
    <div class="theater-inspector-footer">
      <span class="theater-inspector-citation" id="theaterInspectorCitation">USGS CTX 20m DTM (DOI: 10.5066/P906QQT8)</span>
      <button id="btnTheaterInspectProvenance" class="theater-inspector-btn">Inspect Provenance &rarr;</button>
    </div>
  </div>

  <!-- HUD Header Bar -->'''

if 'id="missionTheaterHUD"' not in content:
    content = content.replace(cockpit_end, theater_hud_html, 1)

with open(index_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Inserted Mission Theater HTML successfully.")
