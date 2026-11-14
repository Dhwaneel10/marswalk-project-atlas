# Build Milestone 13E styles to append to web/styles.css

def get_joint_css():
    return '''
/* ==========================================================================
   Milestone 13E: Joint Mission Co-Design Studio & In-Theater Drawer Styles
   ========================================================================== */

/* Mission Theater HUD Button */
.theater-jointstudio-btn {
  background: rgba(0, 229, 255, 0.15);
  border: 1px solid rgba(0, 229, 255, 0.45);
  color: #00e5ff;
}
.theater-jointstudio-btn:hover {
  background: rgba(0, 229, 255, 0.3);
  box-shadow: 0 0 12px rgba(0, 229, 255, 0.35);
  color: #ffffff;
}
.theater-jointstudio-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.35) 0%, rgba(124, 58, 237, 0.45) 100%);
  border-color: #00e5ff;
  color: #ffffff;
  box-shadow: 0 0 14px rgba(0, 229, 255, 0.4);
}

/* In-Theater Floating Control Drawer */
.jointstudio-control-panel {
  position: absolute;
  top: 130px;
  right: 20px;
  width: 340px;
  max-width: calc(100vw - 40px);
  background: rgba(15, 23, 42, 0.94);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(0, 229, 255, 0.35);
  border-radius: 8px;
  z-index: 105;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.65), 0 0 15px rgba(0, 229, 255, 0.15);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 160px);
  overflow: hidden;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.jointstudio-control-panel.hidden {
  display: none !important;
}

.jointstudio-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid rgba(0, 229, 255, 0.25);
}
.jointstudio-panel-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-weight: 800;
  font-size: 11px;
  letter-spacing: 0.8px;
  color: #00e5ff;
}
.jointstudio-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.jointstudio-btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
}
.jointstudio-btn-close:hover {
  color: #ffffff;
}

.jointstudio-badge-status {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}
.jointstudio-badge-status.pareto {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.35);
}
.jointstudio-badge-status.suboptimal {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.35);
}

.jointstudio-panel-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}

.jointstudio-telemetry-box {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.jointstudio-telemetry-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.jointstudio-telemetry-key {
  color: #64748b;
  font-size: 9.5px;
  font-weight: 600;
}
.jointstudio-telemetry-val {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-weight: 700;
  font-size: 10px;
  color: #f1f5f9;
}

.jointstudio-section-title {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.8px;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 5px;
}

.jointstudio-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #cbd5e1;
  font-size: 10px;
  margin-bottom: 4px;
}
.jointstudio-legend-indicator {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}

.jointstudio-action-button {
  width: 100%;
  padding: 8px 12px;
  border-radius: 6px;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s ease;
}
.jointstudio-action-button.primary {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  border: 1px solid #00e5ff;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 229, 255, 0.25);
}
.jointstudio-action-button.primary:hover {
  background: linear-gradient(135deg, #00e5ff 0%, #0284c7 100%);
  box-shadow: 0 6px 18px rgba(0, 229, 255, 0.45);
}
.jointstudio-action-button.secondary {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
  font-size: 10px;
}
.jointstudio-action-button.secondary:hover {
  background: rgba(51, 65, 85, 0.9);
  color: #ffffff;
}

/* 6-Step Guided Wizard Stepper */
.joint-stepper-container {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 4px;
}
.joint-stepper-nav {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 3px;
}
.joint-step-btn {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 5px 2px;
  color: #94a3b8;
  font-size: 9px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  transition: all 0.15s ease;
}
.joint-step-btn:hover {
  background: rgba(51, 65, 85, 0.8);
  color: #f1f5f9;
}
.joint-step-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.25) 0%, rgba(124, 58, 237, 0.25) 100%);
  border-color: var(--telemetry-cyan);
  color: var(--telemetry-cyan);
  font-weight: 700;
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.25);
}
.joint-step-btn.completed {
  border-color: rgba(16, 185, 129, 0.4);
  color: #34d399;
}
.joint-step-btn .step-num {
  font-weight: 800;
  font-size: 9.5px;
}
.joint-step-btn .step-name {
  font-size: 7.5px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.joint-step-content {
  display: block;
}
.joint-step-content.hidden {
  display: none !important;
}

/* Weight Presets */
.joint-preset-pill {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  padding: 2px 7px;
  font-size: 8px;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.15s ease;
}
.joint-preset-pill:hover {
  background: rgba(51, 65, 85, 0.9);
  color: #ffffff;
}
.joint-preset-pill.active {
  background: rgba(0, 229, 255, 0.2);
  border-color: var(--telemetry-cyan);
  color: var(--telemetry-cyan);
  font-weight: 700;
}

/* Solver Status Animation */
.joint-status-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid rgba(0, 229, 255, 0.3);
  color: var(--telemetry-cyan);
  font-size: 9px;
}
.joint-spinner {
  display: inline-block;
  animation: jointSpin 1s linear infinite;
  font-size: 14px;
}
@keyframes jointSpin {
  100% { transform: rotate(360deg); }
}

/* Pareto Frontier Scatter Canvas Tooltip */
.pareto-canvas-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid var(--telemetry-cyan);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 8.5px;
  color: #f1f5f9;
  z-index: 50;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
  max-width: 220px;
  transform: translate(10px, -50%);
}
.pareto-canvas-tooltip.hidden {
  display: none !important;
}

/* Pareto Comparative Scorecard Table */
.pareto-scorecard-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8.5px;
  color: #cbd5e1;
}
.pareto-scorecard-table th {
  background: rgba(15, 23, 42, 0.9);
  color: #94a3b8;
  font-weight: 700;
  text-align: left;
  padding: 5px 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  white-space: nowrap;
}
.pareto-scorecard-table td {
  padding: 5px 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  white-space: nowrap;
}
.pareto-scorecard-table tr:hover td {
  background: rgba(30, 41, 59, 0.5);
  cursor: pointer;
}
.pareto-scorecard-table tr.pareto-row-selected td {
  background: rgba(0, 229, 255, 0.15) !important;
  color: #ffffff;
  border-color: rgba(0, 229, 255, 0.3);
}
.pareto-rank-badge {
  display: inline-block;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 7.5px;
  font-weight: 700;
}
.pareto-rank-badge.rank1 {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.pareto-rank-badge.dominated {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.pareto-btn-action {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  color: #cbd5e1;
  font-size: 7.5px;
  padding: 1px 5px;
  cursor: pointer;
}
.pareto-btn-action:hover {
  background: rgba(0, 229, 255, 0.25);
  border-color: var(--telemetry-cyan);
  color: #ffffff;
}
'''

if __name__ == '__main__':
    css = get_joint_css()
    print(f"Generated {len(css)} chars of CSS.")
