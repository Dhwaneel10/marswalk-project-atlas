import sys

def main():
    styles = '''
/* =========================================================================
   MILESTONE 13J: ATLAS FLEET INTELLIGENCE & COOPERATIVE OPERATIONS
   Multi-Rover Control, Status Cards, Task Allocator, Synchronized Timelines,
   6D Pareto Matrix, Counterfactual Scenarios & Promotion Sign-Off
   ========================================================================= */

.fleet-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px 18px 28px 18px;
  background: #090d16;
  color: #e2e8f0;
  overflow-y: auto;
  box-sizing: border-box;
  width: 100%;
}

.fleet-header-deck {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, rgba(14, 23, 42, 0.95), rgba(15, 23, 42, 0.8));
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 8px;
  padding: 12px 18px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.fleet-header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fleet-badge-icon {
  font-size: 24px;
  background: rgba(56, 189, 248, 0.15);
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 8px;
  padding: 6px 10px;
}

.fleet-title-text {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: #38bdf8;
  margin: 0;
  text-transform: uppercase;
}

.fleet-subtitle-text {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.fleet-header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.fleet-selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 700;
  color: #cbd5e1;
}

.fleet-select-input {
  background: #0f172a;
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  outline: none;
}

.fleet-status-pill {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: #10b981;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 9999px;
  letter-spacing: 0.04em;
}

/* Action Control Bar */
.fleet-action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 8px;
}

.btn-primary-fleet {
  background: linear-gradient(135deg, #0284c7, #0369a1);
  color: #ffffff;
  border: 1px solid rgba(56, 189, 248, 0.4);
  border-radius: 6px;
  padding: 7px 14px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
}
.btn-primary-fleet:hover {
  background: linear-gradient(135deg, #0369a1, #075985);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
}

.btn-secondary-fleet {
  background: rgba(30, 41, 59, 0.8);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 7px 14px;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-secondary-fleet:hover {
  background: rgba(51, 65, 85, 0.9);
  color: #ffffff;
}

.btn-danger-fleet {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: 6px;
  padding: 7px 14px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-danger-fleet:hover {
  background: rgba(239, 68, 68, 0.3);
  color: #ffffff;
}

.btn-success-fleet {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.35);
  border-radius: 6px;
  padding: 7px 14px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-success-fleet:hover {
  background: rgba(16, 185, 129, 0.3);
  color: #ffffff;
}

.btn-subtle-fleet {
  background: transparent;
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 10.5px;
  font-weight: 600;
  cursor: pointer;
}
.btn-subtle-fleet:hover {
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.3);
}

.fleet-scrollable-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 5-Card HUD Grid */
.fleet-hud-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

.fleet-hud-card {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 10px 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  transition: border-color 0.2s ease;
}
.fleet-hud-card:hover {
  border-color: rgba(56, 189, 248, 0.3);
}

.fleet-hud-label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.fleet-hud-value {
  font-size: 18px;
  font-weight: 800;
  color: #f1f5f9;
  margin: 4px 0 2px 0;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", monospace;
}

.fleet-hud-sub {
  font-size: 10px;
  color: #94a3b8;
}

/* Rover Cards Grid */
.rover-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.rover-card {
  background: rgba(15, 23, 42, 0.85);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
}

.rover-card-alpha { border-top: 3px solid #38bdf8; }
.rover-card-beta { border-top: 3px solid #10b981; }
.rover-card-gamma { border-top: 3px solid #a855f7; }
.rover-card-delta { border-top: 3px solid #f59e0b; }

.rover-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.rover-card-name {
  font-size: 11.5px;
  font-weight: 700;
  color: #f8fafc;
  display: flex;
  align-items: center;
  gap: 6px;
}

.rover-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot-alpha { background: #38bdf8; box-shadow: 0 0 6px #38bdf8; }
.dot-beta { background: #10b981; box-shadow: 0 0 6px #10b981; }
.dot-gamma { background: #a855f7; box-shadow: 0 0 6px #a855f7; }
.dot-delta { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }

.rover-unit-badge {
  font-size: 9px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}
.badge-alpha { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
.badge-beta { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.badge-gamma { background: rgba(168, 85, 247, 0.15); color: #a855f7; }
.badge-delta { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }

.rover-card-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
}

.rover-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rover-progress-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin: 2px 0;
}

.rover-progress-fill {
  height: 100%;
  border-radius: 3px;
}
.fill-alpha { background: #38bdf8; }
.fill-beta { background: #10b981; }
.fill-gamma { background: #a855f7; }
.fill-delta { background: #f59e0b; }

.rover-tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.rover-tag {
  background: rgba(255, 255, 255, 0.06);
  color: #94a3b8;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}

.rover-target-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.pill-tgt {
  background: rgba(56, 189, 248, 0.12);
  color: #7dd3fc;
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", monospace;
}

/* Sections & Tables */
.fleet-section {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.fleet-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.fleet-section-title {
  font-size: 12.5px;
  font-weight: 800;
  color: #f8fafc;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.fleet-badge-sub {
  font-size: 10.5px;
  color: #64748b;
}

.fleet-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.fleet-table th {
  background: rgba(30, 41, 59, 0.6);
  color: #94a3b8;
  font-weight: 700;
  text-align: left;
  padding: 7px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 10px;
  letter-spacing: 0.03em;
}

.fleet-table td {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
}

.fleet-table tr:hover td {
  background: rgba(56, 189, 248, 0.04);
}

/* Multi-Lane Timeline */
.sol-filter-pills {
  display: flex;
  gap: 6px;
}

.fleet-timeline-wrapper {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 10px;
  overflow-x: auto;
}

.fleet-timeline-lanes {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 650px;
}

.timeline-lane {
  display: flex;
  align-items: center;
  gap: 10px;
}

.lane-label {
  width: 120px;
  font-size: 10.5px;
  font-weight: 700;
  color: #cbd5e1;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.lane-track {
  flex: 1;
  height: 24px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  display: flex;
  position: relative;
  overflow: hidden;
}

.timeline-block {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  color: #ffffff;
  padding: 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.timeline-block:hover {
  opacity: 0.85;
}

.block-traverse { background: #0284c7; }
.block-science { background: #059669; }
.block-downlink { background: #7c3aed; }
.block-hold { background: #d97706; }
.block-sleep { background: #475569; }

.fleet-timeline-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 8px;
  font-size: 10px;
  color: #94a3b8;
}

.legend-chip {
  display: flex;
  align-items: center;
  gap: 6px;
}

.chip-color {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.color-traverse { background: #0284c7; }
.color-science { background: #059669; }
.color-downlink { background: #7c3aed; }
.color-hold { background: #d97706; }
.color-sleep { background: #475569; }

/* Scenario Control Deck */
.fleet-scenario-control-deck {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 10px 14px;
}

.scenario-field-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.scenario-field-group label {
  font-size: 9.5px;
  font-weight: 700;
  color: #94a3b8;
}

.fleet-num-input {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #f1f5f9;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 11px;
  width: 50px;
}

.fleet-text-input {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #f1f5f9;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 11px;
  width: 100%;
}

/* Promotion Drawer */
.fleet-promotion-drawer {
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 6px;
  padding: 12px 14px;
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.promotion-drawer-header {
  font-size: 11.5px;
  font-weight: 800;
  color: #34d399;
  letter-spacing: 0.03em;
}

.promotion-form-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.promotion-input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}
.promotion-input-group label {
  font-size: 9.5px;
  font-weight: 700;
  color: #94a3b8;
}

.promotion-audit-notice {
  font-size: 10px;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 6px;
}

/* Responsive Overrides */
@media (max-width: 1440px) {
  .fleet-hud-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .rover-cards-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 1024px) {
  .fleet-hud-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .rover-cards-grid {
    grid-template-columns: 1fr;
  }
}
'''
    with open('web/styles.css', 'a', encoding='utf-8') as f:
        f.write('\n' + styles)
    print("Successfully appended fleet styles to web/styles.css!")

if __name__ == '__main__':
    main()
