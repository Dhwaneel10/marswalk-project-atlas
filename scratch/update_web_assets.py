"""Script to inject Milestone 13E Joint Mission Design Studio into web/index.html, web/styles.css, and web/app.js"""
import os

HTML_PATH = 'web/index.html'
CSS_PATH = 'web/styles.css'
JS_PATH = 'web/app.js'

# 1. HTML Snippets
HUD_BUTTON_SNIPPET = '''        <button id="btnToggleJointStudio" class="theater-action-btn theater-jointstudio-btn active" title="Toggle Joint Mission Co-Design Studio Drawer">
          <span class="btn-icon">&#9881;</span> CO-DESIGN
          <span id="theaterJointStatusDot" class="relaynet-status-dot online"></span>
        </button>
'''

TAB_BUTTON_SNIPPET = '''        <button class="inspector-tab" data-tab="tabJointMissionStudio" id="tabBtnJointMissionStudio" title="Joint Mission Co-Design: Traverse Planning &times; RelayNet">&#9881; Co-Design</button>
'''

THEATER_DRAWER_SNIPPET = '''  <!-- Milestone 13E: Joint Mission Co-Design In-Theater Control Drawer Panel -->
  <div id="jointMissionStudioPanel" class="jointstudio-control-panel">
    <div class="jointstudio-panel-header">
      <div class="jointstudio-panel-title">
        <span class="jointstudio-icon">&#9881;</span>
        <span>JOINT CO-DESIGN TWIN</span>
      </div>
      <div class="jointstudio-header-actions">
        <span id="jointMissionStatusBadge" class="jointstudio-badge-status pareto">PARETO RANK 1</span>
        <button id="btnCloseJointStudioPanel" class="jointstudio-btn-close">&times;</button>
      </div>
    </div>

    <div class="jointstudio-panel-body">
      <!-- Active Co-Design Candidate Telemetry -->
      <div class="jointstudio-telemetry-box">
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">ACTIVE CANDIDATE:</span>
          <span id="jointTheaterCandidateId" class="jointstudio-telemetry-val text-cyan">JMC-01 (Nominal Balanced)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">TRAVERSE DISTANCE:</span>
          <span id="jointTheaterDistance" class="jointstudio-telemetry-val">3,412 m (&plusmn;0 m)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">COMMS COVERAGE:</span>
          <span id="jointTheaterCoverage" class="jointstudio-telemetry-val text-emerald">100.0% (0s gap)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">RELAYS DEPLOYED:</span>
          <span id="jointTheaterRelays" class="jointstudio-telemetry-val">1 (MRN-01 Scarp Promontory)</span>
        </div>
        <div class="jointstudio-telemetry-row">
          <span class="jointstudio-telemetry-key">METABOLIC WORK:</span>
          <span id="jointTheaterEnergy" class="jointstudio-telemetry-val">1,240 kJ (Waligora Model)</span>
        </div>
      </div>

      <!-- Quick Candidate Selector -->
      <div class="jointstudio-candidate-picker">
        <div class="jointstudio-section-title">SELECT CO-DESIGN CANDIDATE</div>
        <select id="jointTheaterCandidateSelect" class="hud-select" style="width:100%; font-size:10px; font-weight:600; padding:4px 6px;">
          <option value="">Run Co-Design Optimization...</option>
        </select>
      </div>

      <!-- Trajectory Display Toggles -->
      <div class="jointstudio-toggles-section">
        <div class="jointstudio-section-title">TRAJECTORY &amp; GAP LAYERS</div>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowSelected" checked>
          <span class="jointstudio-legend-indicator" style="background: #00e5ff; box-shadow: 0 0 6px #00e5ff;"></span>
          <span>Selected Co-Design Ribbon</span>
        </label>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowParetoAlts" checked>
          <span class="jointstudio-legend-indicator" style="background: #a855f7;"></span>
          <span>Pareto Alternative Routes (Dashed)</span>
        </label>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowDominated" checked>
          <span class="jointstudio-legend-indicator" style="background: #64748b;"></span>
          <span>Dominated Routes (Muted Grey)</span>
        </label>
        <label class="jointstudio-checkbox-label">
          <input type="checkbox" id="chkJointShowGaps" checked>
          <span class="jointstudio-legend-indicator" style="background: #ef4444; box-shadow: 0 0 6px #ef4444;"></span>
          <span>Blackout Comms Gaps (Pulsating)</span>
        </label>
      </div>

      <!-- Quick Actions -->
      <div class="jointstudio-actions-section">
        <button id="btnTheaterRunJointOptimize" class="jointstudio-action-button primary">
          <span class="btn-icon">&#9889;</span> Optimize Co-Design Candidates
        </button>
        <button id="btnTheaterPromoteJoint" class="jointstudio-action-button secondary" style="margin-top:6px;">
          <span class="btn-icon">&#128640;</span> Promote to Active Mission Plan
        </button>
      </div>
    </div>
  </div>
'''

print("Checking snippet syntax...")
