"""
Append Milestone 13D RelayNet CSS styles to web/styles.css.
"""

styles_code = """

/* ==========================================================================
   Milestone 13D: Atlas Mars RelayNet Glassmorphic Control Panel
   ========================================================================== */

.theater-relaynet-btn {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.45);
  color: #34d399;
}
.theater-relaynet-btn:hover {
  background: rgba(16, 185, 129, 0.3);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.35);
  color: #ffffff;
}
.theater-relaynet-btn.active {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.35) 0%, rgba(5, 150, 105, 0.45) 100%);
  border-color: #10b981;
  color: #10b981;
  box-shadow: 0 0 14px rgba(16, 185, 129, 0.4);
}

.relaynet-status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-left: 4px;
}
.relaynet-status-dot.online {
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}
.relaynet-status-dot.gap {
  background: #ef4444;
  box-shadow: 0 0 6px #ef4444;
  animation: relayPulseGap 1s infinite alternate;
}

@keyframes relayPulseGap {
  from { opacity: 0.4; }
  to { opacity: 1.0; }
}

.relaynet-control-panel {
  position: absolute;
  top: 130px;
  right: 20px;
  width: 320px;
  max-width: calc(100vw - 40px);
  max-height: calc(100vh - 280px);
  background: rgba(10, 15, 24, 0.94);
  border: 1px solid rgba(16, 185, 129, 0.45);
  border-radius: 8px;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7), 0 0 16px rgba(16, 185, 129, 0.15);
  z-index: 28;
  pointer-events: auto;
  font-size: 11px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.relaynet-control-panel.hidden {
  display: none !important;
}

.relaynet-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.relaynet-panel-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-weight: 800;
  letter-spacing: 0.8px;
  color: #34d399;
}

.relaynet-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.relaynet-btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
}
.relaynet-btn-close:hover {
  color: #ffffff;
}

.relaynet-badge-status {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}
.relaynet-badge-status.direct {
  background: rgba(0, 229, 255, 0.15);
  color: #00e5ff;
  border: 1px solid rgba(0, 229, 255, 0.3);
}
.relaynet-badge-status.relayed {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.relaynet-badge-status.gap {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.relaynet-panel-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.relaynet-telemetry-box {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.relaynet-telemetry-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.relaynet-telemetry-key {
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
}

.relaynet-telemetry-val {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-weight: 700;
  font-size: 10px;
  color: #f1f5f9;
}

.relaynet-section-title {
  font-size: 9.5px;
  font-weight: 800;
  letter-spacing: 0.8px;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.relaynet-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #cbd5e1;
  font-size: 10.5px;
  margin-bottom: 5px;
}

.relaynet-legend-indicator {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}

.relaynet-action-button {
  width: 100%;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.relaynet-action-button.primary {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  border: 1px solid #10b981;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}
.relaynet-action-button.primary:hover {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 6px 18px rgba(16, 185, 129, 0.5);
}

.relaynet-actions-subgroup {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 6px;
}

.relaynet-action-button.secondary {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
  font-size: 10px;
}
.relaynet-action-button.secondary:hover {
  background: rgba(51, 65, 85, 0.9);
  color: #ffffff;
}

.relaynet-summary-box {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  border-radius: 6px;
  padding: 8px 10px;
}
.relaynet-summary-title {
  color: #10b981;
  font-weight: 800;
  margin-bottom: 4px;
}
.relaynet-summary-stats {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: #cbd5e1;
  font-size: 10px;
}
"""

with open("web/styles.css", "a", encoding="utf-8") as f:
    f.write(styles_code)

print("Successfully appended RelayNet styles to web/styles.css!")
