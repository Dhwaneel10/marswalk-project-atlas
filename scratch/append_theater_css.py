css_theater = '''
/* ==========================================================================
   Milestone 13C: Atlas 3D Mission Theater & Spatial Digital Twin Styles
   ========================================================================== */

body.theater-mode-active #inspectorPanel,
body.theater-mode-active #devDiagnosticsPanel,
body.theater-mode-active #categoryFilterBar,
body.theater-mode-active #locationCard {
  display: none !important;
}

body.theater-mode-active #viewport3d {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 20 !important;
  display: block !important;
}

body.theater-mode-active .hud-header {
  transform: translateY(-100%);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.mission-theater-hud {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  pointer-events: none;
  z-index: 25;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #f1f5f9;
}

.mission-theater-hud.hidden {
  display: none !important;
}

/* Top Theater Command Bar */
.theater-top-bar {
  position: absolute;
  top: 14px;
  left: 18px;
  right: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 18px;
  background: rgba(10, 15, 24, 0.88);
  border: 1px solid rgba(0, 229, 255, 0.45);
  border-radius: 8px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 16px rgba(0, 229, 255, 0.15);
  pointer-events: auto;
}

.theater-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.theater-pill {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1px;
  color: #00e5ff;
  text-transform: uppercase;
  background: rgba(0, 229, 255, 0.12);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 4px;
  padding: 3px 8px;
}

.theater-dataset-tag {
  font-size: 10px;
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.theater-badge-truth {
  font-size: 9px;
  font-weight: 700;
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  border-radius: 3px;
  padding: 2px 6px;
  letter-spacing: 0.5px;
}

.theater-telemetry-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.theater-telemetry-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.theater-telemetry-label {
  font-size: 9.5px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.8px;
}

.theater-telemetry-val {
  font-size: 11px;
  font-weight: 700;
  color: #38bdf8;
  font-family: ui-monospace, monospace;
}

.theater-controls-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.theater-exaggeration-control {
  display: flex;
  align-items: center;
  gap: 6px;
}

.theater-control-label {
  font-size: 9.5px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.5px;
}

.theater-select {
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f8fafc;
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
}

.theater-action-btn {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid rgba(0, 229, 255, 0.4);
  color: #00e5ff;
  font-size: 10px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theater-action-btn:hover {
  background: rgba(0, 229, 255, 0.25);
}

.theater-exit-btn {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #f87171;
  font-size: 10px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theater-exit-btn:hover {
  background: rgba(239, 68, 68, 0.35);
  color: #ffffff;
}

/* Subpanels Common */
.theater-subpanel-title {
  font-size: 9.5px;
  font-weight: 800;
  color: #94a3b8;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.theater-director-bar {
  position: absolute;
  top: 72px;
  left: 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 14px;
  background: rgba(10, 15, 24, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  pointer-events: auto;
}

.theater-cam-pills {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.theater-pill-btn {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 10px;
  font-weight: 700;
  padding: 5px 10px;
  border-radius: 4px;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
}

.theater-pill-btn:hover {
  background: rgba(51, 65, 85, 0.9);
  color: #ffffff;
}

.theater-pill-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.3) 0%, rgba(3, 105, 161, 0.4) 100%);
  border-color: #00e5ff;
  color: #00e5ff;
  box-shadow: 0 0 10px rgba(0, 229, 255, 0.25);
}

.theater-layers-bar {
  position: absolute;
  top: 72px;
  right: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(10, 15, 24, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
  pointer-events: auto;
}

.theater-layer-pills {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}

.theater-trajectory-toggles {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.theater-traj-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  color: #cbd5e1;
  cursor: pointer;
}

.theater-traj-legend {
  display: inline-block;
  width: 12px;
  height: 4px;
  border-radius: 2px;
}

/* Bottom Unified Transport Bar */
.theater-transport-bar {
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  width: min(920px, calc(100vw - 36px));
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 20px;
  background: rgba(10, 15, 24, 0.92);
  border: 1px solid rgba(0, 229, 255, 0.5);
  border-radius: 12px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8), 0 0 24px rgba(0, 229, 255, 0.2);
  pointer-events: auto;
}

.theater-playback-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
}

.theater-transport-btn {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #f1f5f9;
  font-size: 11px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theater-transport-btn:hover {
  background: rgba(51, 65, 85, 1);
  border-color: #00e5ff;
}

.theater-play-btn {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  border-color: #38bdf8;
  color: #ffffff;
  padding: 6px 14px;
}

.theater-play-btn:hover {
  background: linear-gradient(135deg, #0369a1 0%, #0284c7 100%);
}

.theater-scrubber-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.theater-scrubber-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  font-family: ui-monospace, monospace;
  color: #94a3b8;
}

.theater-scrubber-status {
  font-size: 9.5px;
  font-weight: 700;
  color: #38bdf8;
  letter-spacing: 0.5px;
}

.theater-scrubber-slider {
  width: 100%;
  accent-color: #00e5ff;
  cursor: pointer;
}

.theater-speed-pills {
  display: flex;
  gap: 4px;
}

.theater-speed-btn {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  padding: 4px 7px;
  border-radius: 4px;
  cursor: pointer;
}

.theater-speed-btn.active {
  background: rgba(0, 229, 255, 0.2);
  border-color: #00e5ff;
  color: #00e5ff;
}

.theater-transport-extra {
  display: flex;
  gap: 6px;
}

/* Floating Raycast Spatial Inspector Card */
.theater-inspector-card {
  position: absolute;
  bottom: 88px;
  right: 18px;
  width: 330px;
  max-width: calc(100vw - 36px);
  background: rgba(10, 15, 24, 0.94);
  border: 1px solid rgba(0, 229, 255, 0.5);
  border-radius: 8px;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7), 0 0 16px rgba(0, 229, 255, 0.15);
  z-index: 30;
  pointer-events: auto;
  font-size: 11px;
}

.theater-inspector-card.hidden {
  display: none !important;
}

.theater-inspector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px 8px 0 0;
}

.theater-inspector-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: #00e5ff;
}

.theater-inspector-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
}

.theater-inspector-close:hover {
  color: #ffffff;
}

.theater-inspector-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.theater-inspector-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10.5px;
}

.theater-inspector-key {
  color: #64748b;
  font-weight: 600;
}

.theater-inspector-val {
  color: #f1f5f9;
  font-weight: 700;
  font-family: ui-monospace, monospace;
}

.theater-inspector-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.6);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0 0 8px 8px;
}

.theater-inspector-citation {
  font-size: 8.5px;
  color: #64748b;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theater-inspector-btn {
  background: rgba(0, 229, 255, 0.15);
  border: 1px solid rgba(0, 229, 255, 0.4);
  color: #00e5ff;
  font-size: 9.5px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.theater-inspector-btn:hover {
  background: rgba(0, 229, 255, 0.3);
}
'''

styles_path = r"E:\Python\NASA-Spaceapps\Marswalk\web\styles.css"
with open(styles_path, "r", encoding="utf-8") as f:
    existing = f.read()

if "Milestone 13C: Atlas 3D Mission Theater" not in existing:
    with open(styles_path, "a", encoding="utf-8") as f:
        f.write("\n" + css_theater)
    print("Appended Mission Theater CSS successfully.")
else:
    print("Mission Theater CSS already present.")
