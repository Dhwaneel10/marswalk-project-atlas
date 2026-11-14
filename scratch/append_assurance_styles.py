# Mission Assurance Styles to append to web/styles.css
from pathlib import Path

css_path = Path("web/styles.css")
content = css_path.read_text(encoding="utf-8")

assurance_css = """
/* ==========================================================================
   MILESTONE 13I: ATLAS MISSION ASSURANCE & COUNTERFACTUAL OPERATIONS LAB
   Immutable Branching, Invariant Audit, Replay, Fault Injection & Merkle Dossier
   ========================================================================== */

.assurance-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--bg-primary, #0c1017);
  color: var(--text-primary, #e6edf3);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  box-sizing: border-box;
  width: 100%;
}

.assurance-panel.hidden {
  display: none !important;
}

/* Toolbar & Header Deck */
.assurance-toolbar-deck {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  background: rgba(18, 26, 38, 0.85);
  border: 1px solid rgba(56, 139, 253, 0.25);
  border-radius: 6px;
  padding: 8px 12px;
}

.assurance-toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.assurance-badge {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: #38bdf8;
  text-transform: uppercase;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 4px 8px;
  border-radius: 4px;
}

.assurance-select {
  background: #0d1520;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #e6edf3;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
}

.assurance-status-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 12px;
  text-transform: uppercase;
}

.assurance-status-pill.pill-active {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.35);
}

.assurance-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.assurance-toolbar-actions button {
  font-size: 11px;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

/* KPI & HUD Deck */
.assurance-hud-deck {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.assurance-hud-card {
  background: rgba(18, 26, 38, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.assurance-hud-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: #8b949e;
  text-transform: uppercase;
}

.assurance-hud-val {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
}

.assurance-hud-sub {
  font-size: 9px;
  color: #8b949e;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Scientific Disclosure */
.assurance-scientific-disclosure {
  font-size: 10px;
  line-height: 1.4;
  color: #c9d1d9;
  background: rgba(22, 27, 34, 0.9);
  border-left: 3px solid #f59e0b;
  padding: 6px 10px;
  border-radius: 0 4px 4px 0;
}

/* Sub-Sections */
.assurance-subsections {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.assurance-section {
  background: rgba(13, 17, 23, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.assurance-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding-bottom: 6px;
}

.assurance-section-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: #58a6ff;
  text-transform: uppercase;
}

.assurance-section-sub {
  font-size: 10px;
  color: #8b949e;
}

/* Filter Pills */
.assurance-filter-pills {
  display: flex;
  gap: 4px;
}

.filter-pill {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #8b949e;
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-pill:hover,
.filter-pill.active {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.4);
}

/* Fork Control Strip */
.assurance-fork-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  background: rgba(22, 27, 34, 0.6);
  padding: 6px 8px;
  border-radius: 4px;
}

.assurance-input {
  background: #0d1520;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #e6edf3;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  flex: 1;
  min-width: 140px;
}

.assurance-input-num {
  background: #0d1520;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #e6edf3;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 11px;
  width: 50px;
}

/* Branch Tree */
.branch-tree-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.branch-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(18, 26, 38, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 11px;
  transition: all 0.2s ease;
}

.branch-card:hover {
  border-color: rgba(56, 189, 248, 0.4);
  background: rgba(18, 26, 38, 0.9);
}

.branch-card.active-branch {
  border-left: 3px solid #38bdf8;
  background: rgba(56, 189, 248, 0.05);
}

.branch-card-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.branch-tag {
  font-weight: 600;
  color: #e6edf3;
}

.branch-type-pill {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 8px;
  text-transform: uppercase;
}

.branch-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Scenario Lab */
.scenario-lab-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.3fr;
  gap: 10px;
}

.scenario-config-card {
  background: rgba(18, 26, 38, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scenario-params-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.control-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.scenario-narrative-card {
  background: rgba(18, 26, 38, 0.85);
  border: 1px solid rgba(56, 139, 253, 0.2);
  border-radius: 4px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.narrative-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.narrative-tag {
  font-size: 10px;
  font-weight: 700;
  color: #f59e0b;
}

.narrative-status {
  font-size: 9px;
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  padding: 2px 6px;
  border-radius: 4px;
}

.narrative-body {
  font-size: 10.5px;
  line-height: 1.45;
  color: #c9d1d9;
  margin: 0;
}

.narrative-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.metric-chip {
  font-size: 9.5px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 3px 6px;
  border-radius: 4px;
  color: #8b949e;
}

/* Layer Overlays */
.assurance-layer-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.assurance-chk-label {
  font-size: 10px;
  color: #c9d1d9;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.chk-color {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.chk-cyan { background: #38bdf8; }
.chk-amber { background: #f59e0b; }
.chk-emerald { background: #10b981; }
.chk-rose { background: #f43f5e; }

/* Tables */
.assurance-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10.5px;
}

.assurance-table th,
.assurance-table td {
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.assurance-table th {
  background: rgba(255, 255, 255, 0.03);
  color: #8b949e;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.assurance-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.badge-verdict {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.badge-verdict.pass {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-verdict.fail {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.3);
}

.badge-verdict.warn {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-verdict.na {
  background: rgba(139, 148, 158, 0.15);
  color: #8b949e;
  border: 1px solid rgba(139, 148, 158, 0.3);
}

.badge-severity {
  font-size: 8.5px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}

.badge-severity.critical { color: #f43f5e; }
.badge-severity.warning { color: #f59e0b; }
.badge-severity.info { color: #38bdf8; }

.badge-evidence {
  font-size: 8.5px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.06);
  color: #8b949e;
}

.badge-evidence.confirmed { color: #10b981; }
.badge-evidence.derived { color: #38bdf8; }
.badge-evidence.unresolved { color: #f59e0b; }
.badge-evidence.conflicting { color: #f43f5e; }
.badge-evidence.missing { color: #94a3b8; }

/* Promotion Drawer */
.promotion-drawer-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 10px;
}

.promo-info-card,
.promo-action-card {
  background: rgba(18, 26, 38, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.promo-header {
  font-size: 10px;
  font-weight: 700;
  color: #38bdf8;
  letter-spacing: 0.5px;
}

.promo-desc {
  font-size: 10.5px;
  line-height: 1.4;
  color: #c9d1d9;
  margin: 0;
}

.promo-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.promo-meta-tag {
  font-size: 9.5px;
  color: #8b949e;
  background: rgba(255, 255, 255, 0.03);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Monospace Dossier */
.font-mono-table td {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  font-size: 9.5px;
}

/* Responsiveness */
@media (max-width: 1440px) {
  .assurance-hud-deck {
    grid-template-columns: repeat(3, 1fr);
  }
  .scenario-lab-grid {
    grid-template-columns: 1fr;
  }
  .promotion-drawer-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1024px) {
  .assurance-hud-deck {
    grid-template-columns: repeat(2, 1fr);
  }
}
"""

if "MILESTONE 13I: ATLAS MISSION ASSURANCE" not in content:
    content += "\n" + assurance_css
    css_path.write_text(content, encoding="utf-8")
    print("Successfully appended Mission Assurance styles to web/styles.css!")
else:
    print("Mission Assurance styles already present in web/styles.css.")
