"""
Updates web/styles.css for Milestone 13F
"""

with open("web/styles.css", "r", encoding="utf-8") as f:
    css = f.read()

# 1. Update stepper grid from 6 to 7 columns
old_grid = "  grid-template-columns: repeat(6, 1fr);\n"
new_grid = "  grid-template-columns: repeat(7, 1fr);\n"
assert old_grid in css, "Failed to find old_grid in styles.css"
css = css.replace(old_grid, new_grid, 1)

# 2. Add resource styles
resource_styles = """
/* =============================================================================
   Milestone 13F: Energy & Resource Intelligence Subsystems
   ============================================================================= */

/* Resource Presets Buttons */
.joint-resource-preset-btn {
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 5px 6px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 1px;
  transition: all 0.15s ease;
}
.joint-resource-preset-btn:hover {
  background: rgba(51, 65, 85, 0.85);
  border-color: rgba(0, 229, 255, 0.4);
}
.joint-resource-preset-btn.active {
  background: linear-gradient(135deg, rgba(0, 229, 255, 0.18) 0%, rgba(124, 58, 237, 0.18) 100%);
  border-color: var(--telemetry-cyan);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.2);
}
.joint-resource-preset-btn .preset-name {
  font-size: 8.5px;
  font-weight: 700;
  color: #f1f5f9;
}
.joint-resource-preset-btn.active .preset-name {
  color: var(--telemetry-cyan);
}
.joint-resource-preset-btn .preset-spec {
  font-size: 7px;
  color: #94a3b8;
  font-family: monospace;
}

/* Feasibility Badges */
.feasibility-badge {
  display: inline-block;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 7.5px;
  font-weight: 700;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.feasibility-badge.feasible {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.feasibility-badge.low-reserve {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.4);
}
.feasibility-badge.energy-violation {
  background: rgba(239, 68, 68, 0.25);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.5);
}
.feasibility-badge.time-violation {
  background: rgba(249, 115, 22, 0.25);
  color: #f97316;
  border: 1px solid rgba(249, 115, 22, 0.5);
}
.feasibility-badge.multi-violation {
  background: rgba(220, 38, 38, 0.3);
  color: #f87171;
  border: 1px solid rgba(220, 38, 38, 0.6);
}

/* Pareto Metric Dimension Switcher Buttons */
.joint-pareto-mode-btn {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 3px;
  padding: 3px 6px;
  font-size: 8px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s ease;
}
.joint-pareto-mode-btn:hover {
  background: rgba(51, 65, 85, 0.9);
  color: #f1f5f9;
}
.joint-pareto-mode-btn.active {
  background: rgba(0, 229, 255, 0.2);
  border-color: var(--telemetry-cyan);
  color: var(--telemetry-cyan);
  font-weight: 700;
}

/* In-Theater Battery Gauge */
.theater-battery-gauge-track {
  position: relative;
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 3px;
  overflow: hidden;
}
.theater-battery-gauge-fill {
  height: 100%;
  transition: width 0.2s ease, background 0.3s ease;
}
.theater-battery-reserve-marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #f59e0b;
  z-index: 2;
}
"""

if ".joint-resource-preset-btn" not in css:
    css = css + "\n" + resource_styles

with open("web/styles.css", "w", encoding="utf-8") as f:
    f.write(css)

print("web/styles.css updated successfully.")
