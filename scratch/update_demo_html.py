# UTF-8 replacement for demo HUD in web/index.html
replacement_block = """  <!-- Floating Demo Mode Active Notification Banner (Milestone 13B) -->
  <div id="demoModeBanner" class="demo-mode-banner hidden">
    <div class="demo-banner-content">
      <span class="demo-badge">&#9733; CONFERENCE DEMO MODE</span>
      <span class="demo-banner-text">Science-Grounded Planetary Rehearsal &bull; Transient Fixture Active</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <button id="btnToggleDemoExplain" class="btn-demo-exit" style="border-color:rgba(0,229,255,0.4); color:var(--telemetry-cyan);" title="Open Technical Explainability Formulary">
        &#129504; Formulary
      </button>
      <button id="btnExitDemoMode" class="btn-demo-exit" title="Exit Demo Mode and restore previous session">
        &times; Exit Demo
      </button>
    </div>
  </div>

  <!-- Interactive 9-Step Guided Showcase Floating HUD Card (Milestone 13B) -->
  <div id="demoShowcaseHUD" class="demo-showcase-hud hidden">
    <div class="showcase-header">
      <div class="showcase-title-row" style="flex:1;">
        <span class="showcase-pill">&#9733; CONFERENCE WALKTHROUGH</span>
        <span id="showcaseStepIndicator" class="showcase-step-indicator">STEP 01 / 09</span>
      </div>
      <button id="btnCloseShowcase" class="showcase-close-btn" title="Exit Demonstration Mode">&times;</button>
    </div>
    <div class="showcase-progress-track">
      <div id="showcaseProgressBar" class="showcase-progress-fill" style="width: 11%;"></div>
    </div>
    <div class="showcase-body">
      <h3 id="showcaseStepTitle" class="showcase-step-title">01. Global Cartography</h3>
      <p id="showcaseStepDesc" class="showcase-step-desc">
        Explore Mars on the IAU 2000 planetocentric sphere using USGS Viking MDIM 2.1 color imagery and search over 2,000 verified landmarks.
      </p>
      <div id="showcaseTruthNote" class="showcase-truth-note">
        High-resolution surface routing is strictly confined to surveyed basins where calibrated elevation models exist.
      </div>
      <div id="showcaseActionRow" class="showcase-action-row">
        <button id="btnShowcaseAction" class="btn-showcase-action">Fly to Jezero Crater &rarr;</button>
      </div>
      <button id="btnShowcaseStepExplain" style="background:rgba(0,229,255,0.08); border:1px solid rgba(0,229,255,0.25); color:var(--telemetry-cyan); font-family:var(--font-mono); font-size:9.5px; padding:4px 8px; border-radius:var(--radius-sm); cursor:pointer; margin-top:4px; width:100%; display:flex; align-items:center; justify-content:center; gap:5px;">
        &#129504; Technical &amp; Scientific Specifications
      </button>
    </div>
    <div class="showcase-footer">
      <button id="btnShowcasePrev" class="btn-showcase-nav" disabled>&larr; Prev</button>
      <button id="btnShowcaseSkip" class="btn-showcase-nav">Skip</button>
      <button id="btnShowcaseNext" class="btn-showcase-nav btn-showcase-next">Next &rarr;</button>
    </div>
  </div>

  <!-- Conference Demo Mode: Technical Explainability Drawer (Milestone 13B) -->
  <div id="demoExplainabilityDrawer" class="demo-explainability-drawer hidden">
    <!-- Drawer Header -->
    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:linear-gradient(135deg, rgba(0,229,255,0.12), rgba(0,0,0,0.4)); border-bottom:1px solid rgba(0,229,255,0.2);">
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:12px; color:var(--telemetry-cyan); font-weight:700;">&#129504; TECHNICAL EXPLAINABILITY</span>
        <span class="wp-badge" style="font-size:7.5px; background:rgba(0,229,255,0.15); color:var(--telemetry-cyan); border-color:rgba(0,229,255,0.3);">CONFERENCE DEFENSE</span>
      </div>
      <button id="btnCloseDemoExplainability" style="background:transparent; border:none; color:var(--text-secondary); font-size:16px; cursor:pointer;" title="Close Drawer">&times;</button>
    </div>

    <!-- Content Body: Progressive Disclosure Accordion -->
    <div style="padding:12px; overflow-y:auto; display:flex; flex-direction:column; gap:10px; font-size:10px; max-height:calc(75vh - 70px);">
      <!-- Topic 1: Equirectangular Cosine Metric Scaling -->
      <details class="explain-accordion-item" open style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:5px; padding:6px 10px;">
        <summary style="cursor:pointer; font-weight:600; color:var(--text-primary); display:flex; justify-content:space-between; align-items:center;">
          <span>01. Equirectangular Cosine Metric Scaling</span>
          <span class="wp-badge" style="font-size:7px; background:rgba(16,185,129,0.15); color:var(--status-green);">TIER I VERIFIED</span>
        </summary>
        <div style="margin-top:6px; color:var(--text-secondary); line-height:1.4;">
          <p style="margin-bottom:6px;"><strong>Intuitive Overview:</strong> Mars is a sphere; meridians converge toward the poles. At Jezero Crater (18.442&deg; N), East-West ground spacing contracts to 18.973 m while North-South spacing remains 20.000 m. MarsWalk applies exact cosine scaling, preventing a 2.53% distance distortion that would otherwise falsely inflate astronaut metabolic costs.</p>
          <div style="background:rgba(0,0,0,0.4); padding:6px; border-radius:3px; font-family:var(--font-mono); font-size:9px; color:#38bdf8;">
            dx = C &times; cos(&phi;<sub>ref</sub>) = 20.0 &times; cos(18.442&deg;) = 18.972887 m<br>
            dy = C = 20.000000 m (meridional parallel invariant)<br>
            d<sub>diag</sub> = &radic;(dx&sup2; + dy&sup2;) = 27.567562 m
          </div>
          <div style="font-size:8px; color:var(--text-tertiary); margin-top:4px;">
            Proven in <code>tests/test_milestone_13a_validation.py::test_01</code> (Discrepancy: &lt; 10<sup>-14</sup> m).
          </div>
        </div>
      </details>

      <!-- Topic 2: Horn 3x3 Gradient & Side-Hill Protection -->
      <details class="explain-accordion-item" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:5px; padding:6px 10px;">
        <summary style="cursor:pointer; font-weight:600; color:var(--text-primary); display:flex; justify-content:space-between; align-items:center;">
          <span>02. Horn 3x3 Gradient &amp; Side-Hill Protection</span>
          <span class="wp-badge" style="font-size:7px; background:rgba(16,185,129,0.15); color:var(--status-green);">TIER I VERIFIED</span>
        </summary>
        <div style="margin-top:6px; color:var(--text-secondary); line-height:1.4;">
          <p style="margin-bottom:6px;"><strong>Intuitive Overview:</strong> To prevent rovers and astronauts from rolling over or sliding down steep scarps, MarsWalk computes full 2D terrain facet tilt using an 8-neighbor Horn (1981) convolution. The dual-slope operator &theta;<sub>uv</sub> = max(&theta;<sub>dest</sub>, &theta;<sub>step</sub>) prevents planners from treating contour paths on steep scarps as 'flat' just because elevation delta is zero.</p>
          <div style="background:rgba(0,0,0,0.4); padding:6px; border-radius:3px; font-family:var(--font-mono); font-size:9px; color:#38bdf8;">
            &part;z/&part;x = [(z<sub>13</sub>+2z<sub>23</sub>+z<sub>33</sub>) - (z<sub>11</sub>+2z<sub>21</sub>+z<sub>31</sub>)] / (8 &times; dx)<br>
            &part;z/&part;y = [(z<sub>11</sub>+2z<sub>12</sub>+z<sub>13</sub>) - (z<sub>31</sub>+2z<sub>32</sub>+z<sub>33</sub>)] / (8 &times; dy)<br>
            &theta;<sub>uv</sub> = max(&theta;<sub>Horn</sub>, &theta;<sub>step</sub>) &rarr; Penalizes 20&deg; scarp contour by +800%
          </div>
          <div style="font-size:8px; color:var(--text-tertiary); margin-top:4px;">
            Proven in <code>tests/test_milestone_13a_validation.py::test_02</code> (Discrepancy: &lt; 10<sup>-6&deg;</sup>).
          </div>
        </div>
      </details>

      <!-- Topic 3: Octile Heuristic Admissibility & A* Optimality -->
      <details class="explain-accordion-item" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:5px; padding:6px 10px;">
        <summary style="cursor:pointer; font-weight:600; color:var(--text-primary); display:flex; justify-content:space-between; align-items:center;">
          <span>03. Octile Heuristic &amp; A* Global Optimality</span>
          <span class="wp-badge" style="font-size:7px; background:rgba(16,185,129,0.15); color:var(--status-green);">TIER I PROVEN</span>
        </summary>
        <div style="margin-top:6px; color:var(--text-secondary); line-height:1.4;">
          <p style="margin-bottom:6px;"><strong>Intuitive Overview:</strong> MarsWalk guarantees mathematically optimal shortest-effort paths. Because our generalized octile heuristic strictly underestimates ground distance (h &le; h*), A* produces costs identical to exhaustive Dijkstra search (0.000 m delta) while pruning over 97% of search expansions.</p>
          <div style="background:rgba(0,0,0,0.4); padding:6px; border-radius:3px; font-family:var(--font-mono); font-size:9px; color:#38bdf8;">
            h(u, v) = min(|&Delta;r|, |&Delta;c|) &times; d<sub>diag</sub> + ||&Delta;r| - |&Delta;c|| &times; d<sub>step</sub><br>
            Admissibility: &forall;u, h(u) &le; h*(u) since C(u&rarr;v) &ge; d(u, v)<br>
            Monotonicity: h(u) &le; C(u&rarr;v) + h(v) &rarr; Global Dijkstra equivalence
          </div>
          <div style="font-size:8px; color:var(--text-tertiary); margin-top:4px;">
            Proven in <code>tests/test_milestone_13a_validation.py::test_04</code> (Cost delta: 0.000000 m).
          </div>
        </div>
      </details>

      <!-- Topic 4: Multi-Objective Pareto Dominance -->
      <details class="explain-accordion-item" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:5px; padding:6px 10px;">
        <summary style="cursor:pointer; font-weight:600; color:var(--text-primary); display:flex; justify-content:space-between; align-items:center;">
          <span>04. Multi-Objective Pareto Frontier</span>
          <span class="wp-badge" style="font-size:7px; background:rgba(16,185,129,0.15); color:var(--status-green);">TIER I VERIFIED</span>
        </summary>
        <div style="margin-top:6px; color:var(--text-secondary); line-height:1.4;">
          <p style="margin-bottom:6px;"><strong>Intuitive Overview:</strong> Rather than collapsing distance, time, and science into arbitrary weighting multipliers, MarsWalk evaluates the multi-objective Pareto trade-off curve. Candidates violating consumable limits are quarantined into an infeasible partition, giving flight directors authentic choices.</p>
          <div style="background:rgba(0,0,0,0.4); padding:6px; border-radius:3px; font-family:var(--font-mono); font-size:9px; color:#38bdf8;">
            A &succ; B &hArr; (&forall;i, f<sub>i</sub>(A) &le; f<sub>i</sub>(B)) &and; (&exist;j, f<sub>j</sub>(A) &lt; f<sub>j</sub>(B))<br>
            Infeasibility Rule: A &isin; Feasible, B &notin; Feasible &rArr; A &succ; B strictly<br>
            Objectives: Distance &darr;, Duration &darr;, Slope &darr;, Science Diversity &uarr;
          </div>
          <div style="font-size:8px; color:var(--text-tertiary); margin-top:4px;">
            Proven in <code>tests/test_milestone_13a_validation.py::test_06</code>.
          </div>
        </div>
      </details>

      <!-- Topic 5: 4-Tier Closed-Loop Disruption Triage -->
      <details class="explain-accordion-item" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:5px; padding:6px 10px;">
        <summary style="cursor:pointer; font-weight:600; color:var(--text-primary); display:flex; justify-content:space-between; align-items:center;">
          <span>05. 4-Tier Closed-Loop Disruption Triage</span>
          <span class="wp-badge" style="font-size:7px; background:rgba(56,189,248,0.15); color:#38bdf8;">TIER II TESTED</span>
        </summary>
        <div style="margin-top:6px; color:var(--text-secondary); line-height:1.4;">
          <p style="margin-bottom:6px;"><strong>Intuitive Overview:</strong> When obstacles or anomalies occur during a sortie, MarsWalk uses a deterministic 4-tier recovery hierarchy: Level 1 pause in-place, Level 2 local graph detour, Level 3 science target pruning, or Level 4 immediate habitat return. All decisions are immutably logged for forensic replay.</p>
          <div style="background:rgba(0,0,0,0.4); padding:6px; border-radius:3px; font-family:var(--font-mono); font-size:9px; color:#38bdf8;">
            Level 1 (In-Situ Resume): Transient glitch &rarr; dwell &Delta;t, path invariant<br>
            Level 2 (Local A* Detour): Spatial barrier &rarr; C<sub>hazard</sub> = &infin;, minimal detour<br>
            Level 3 (Target Pruning): Velocity/O<sub>2</sub> loss &rarr; prune lowest-value science<br>
            Level 4 (Direct Abort): Critical emergency &rarr; direct fastest route to base
          </div>
          <div style="font-size:8px; color:var(--text-tertiary); margin-top:4px;">
            Validated in <code>tests/test_milestone_12f_rehearsal_director.py</code>.
          </div>
        </div>
      </details>

      <!-- Topic 6: Non-Probabilistic Truth Disclosures -->
      <details class="explain-accordion-item" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:5px; padding:6px 10px;">
        <summary style="cursor:pointer; font-weight:600; color:var(--text-primary); display:flex; justify-content:space-between; align-items:center;">
          <span>06. Truth Disclosures &amp; Operational Boundaries</span>
          <span class="wp-badge" style="font-size:7px; background:rgba(245,158,11,0.15); color:#f59e0b;">GOVERNANCE</span>
        </summary>
        <div style="margin-top:6px; color:var(--text-secondary); line-height:1.4;">
          <p style="margin-bottom:6px;"><strong>Operational Disclosure:</strong> MarsWalk operates strictly on calibrated planetary remote sensing data. Traverses are computed using deterministic heuristics grounded in published NASA/USGS datasets. Modeled paths are planning decision-support aids and MUST NEVER be certified as operationally safe for astronauts without in-situ ground truthing.</p>
          <div style="background:rgba(0,0,0,0.4); padding:6px; border-radius:3px; font-family:var(--font-mono); font-size:9px; color:#38bdf8;">
            Primary Terrain: USGS CTX 20m DTM (DOI: 10.5066/P906QQT8)<br>
            Cartographic Reference: IAU 2000 Mars Spheroid (R = 3,396,190 m)<br>
            Environmental Telemetry: PDS4 MEDA (Perseverance Rover, Sol 1619 tranche)
          </div>
        </div>
      </details>
    </div>

    <!-- Footer Disclaimers -->
    <div style="padding:8px 12px; background:rgba(0,0,0,0.5); border-top:1px dashed rgba(255,255,255,0.08); font-size:8px; color:var(--text-tertiary); line-height:1.3;">
      <strong>Scientific Integrity Guardrail:</strong> Grounded in USGS CTX 20m DTM. Modeled routes and triage recommendations are planning heuristics and are NOT flight-certified safe for astronauts.
    </div>
  </div>"""

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "  <!-- Floating Demo Mode Active Notification Banner"
end_marker = "  <!-- Preflight System Readiness Diagnostic Modal"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Error: markers not found. start_idx={start_idx}, end_idx={end_idx}")
    exit(1)

new_content = content[:start_idx] + replacement_block + "\n\n" + content[end_idx:]

with open('web/index.html', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(new_content)

print(f"Successfully replaced demo block ({start_idx} to {end_idx})")
