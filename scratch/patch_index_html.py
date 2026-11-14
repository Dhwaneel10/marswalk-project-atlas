"""
Patch web/index.html with RelayNet HUD controls and drawer panel.
"""

with open("web/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Insert button into theater-controls-right
target_btn = '<button id="btnTheaterExplain" class="theater-action-btn" title="Open Technical Explainability Formulary">&#129504; Formulary</button>'
replacement_btn = """<button id="btnToggleRelayNet" class="theater-action-btn theater-relaynet-btn active" title="Toggle Atlas Mars RelayNet Mesh & Connectivity Twin">
          <span class="btn-icon">&#128225;</span> RELAYNET
          <span id="theaterRelayStatusDot" class="relaynet-status-dot online"></span>
        </button>
        <button id="btnTheaterExplain" class="theater-action-btn" title="Open Technical Explainability Formulary">&#129504; Formulary</button>"""

assert target_btn in content, "target_btn not found in web/index.html"
content = content.replace(target_btn, replacement_btn, 1)

# 2. Insert RelayNet panel right after theaterInspectorCard
target_panel = '  <!-- Milestone 13C: Interactive Raycast Spatial Inspector Card -->'
relaynet_panel_html = """  <!-- Milestone 13D: Atlas Mars RelayNet Control Drawer Panel -->
  <div id="relayNetPanel" class="relaynet-control-panel">
    <div class="relaynet-panel-header">
      <div class="relaynet-panel-title">
        <span class="relaynet-icon">&#128225;</span>
        <span>MARS RELAYNET TWIN</span>
      </div>
      <div class="relaynet-header-actions">
        <span id="relayNetConnectivityBadge" class="relaynet-badge-status direct">DIRECT LINK</span>
        <button id="btnCloseRelayNetPanel" class="relaynet-btn-close">&times;</button>
      </div>
    </div>

    <div class="relaynet-panel-body">
      <!-- Real-time Connectivity Telemetry -->
      <div class="relaynet-telemetry-box">
        <div class="relaynet-telemetry-row">
          <span class="relaynet-telemetry-key">COMM STATUS:</span>
          <span id="relayTelemetryStatus" class="relaynet-telemetry-val text-emerald">NOMINAL (100% COVERAGE)</span>
        </div>
        <div class="relaynet-telemetry-row">
          <span class="relaynet-telemetry-key">ACTIVE HOPS:</span>
          <span id="relayTelemetryHops" class="relaynet-telemetry-val">0 (Direct to Base)</span>
        </div>
        <div class="relaynet-telemetry-row">
          <span class="relaynet-telemetry-key">MIN LOS CLEARANCE:</span>
          <span id="relayTelemetryClearance" class="relaynet-telemetry-val">+14.2 m</span>
        </div>
        <div class="relaynet-telemetry-row">
          <span class="relaynet-telemetry-key">PROPAGATION DELAY:</span>
          <span id="relayTelemetryLatency" class="relaynet-telemetry-val">0.008 ms</span>
        </div>
      </div>

      <!-- Visual Layer Toggles -->
      <div class="relaynet-toggles-section">
        <div class="relaynet-section-title">VISUAL DISPLAY LAYERS</div>
        <label class="relaynet-checkbox-label">
          <input type="checkbox" id="chkRelayActiveRoute" checked>
          <span class="relaynet-legend-indicator" style="background: #00e5ff; box-shadow: 0 0 6px #00e5ff;"></span>
          <span>Active Multi-Hop Beam</span>
        </label>
        <label class="relaynet-checkbox-label">
          <input type="checkbox" id="chkRelayClearLinks" checked>
          <span class="relaynet-legend-indicator" style="background: #10b981;"></span>
          <span>Clear Line-of-Sight Mesh</span>
        </label>
        <label class="relaynet-checkbox-label">
          <input type="checkbox" id="chkRelayObstructedRays" checked>
          <span class="relaynet-legend-indicator" style="background: #ef4444;"></span>
          <span>Obstructed Rays &amp; Impact Hazards</span>
        </label>
        <label class="relaynet-checkbox-label">
          <input type="checkbox" id="chkRelayCandidates" checked>
          <span class="relaynet-legend-indicator" style="background: #f59e0b;"></span>
          <span>Promontory Candidate Sites</span>
        </label>
      </div>

      <!-- Network Optimization Action Controls -->
      <div class="relaynet-actions-section">
        <div class="relaynet-section-title">AUTONOMOUS RELAY OPTIMIZATION</div>
        <button id="btnRelayAutoPlan" class="relaynet-action-button primary" title="Run Greedy Optimization to connect traverse blindspots">
          <span class="btn-icon">&#9889;</span> Auto-Plan Optimal Relays
        </button>
        <div class="relaynet-actions-subgroup">
          <button id="btnRelayDeployManual" class="relaynet-action-button secondary" title="Deploy field relay tower">
            <span class="btn-icon">&#128205;</span> Drop Tower
          </button>
          <button id="btnRelayResetMesh" class="relaynet-action-button secondary" title="Reset network to Base Station only">
            <span class="btn-icon">&#8635;</span> Reset Baseline
          </button>
        </div>
      </div>

      <!-- Optimization Outcome Comparison Pill -->
      <div id="relayOptimizationSummary" class="relaynet-summary-box hidden">
        <div class="relaynet-summary-title">&#10004; RELAY MESH OPTIMIZED</div>
        <div class="relaynet-summary-stats">
          <div>Traverse Coverage: <span class="text-emerald" id="relayStatCoverage">62% &rarr; 100%</span></div>
          <div>Towers Added: <span id="relayStatTowers">2 (MRN-01, MRN-02)</span></div>
          <div>Blindspot Cleared: <span class="text-cyan" id="relayStatBlindspot">1.4 km restored</span></div>
        </div>
      </div>
    </div>
  </div>

"""

assert target_panel in content, "target_panel not found in web/index.html"
content = content.replace(target_panel, relaynet_panel_html + target_panel, 1)

with open("web/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully patched web/index.html with RelayNet elements!")
