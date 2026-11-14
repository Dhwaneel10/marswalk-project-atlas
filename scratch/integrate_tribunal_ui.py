import os
import re

INDEX_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\index.html"
APP_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"

print("--- Updating index.html ---")
with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Check if tribunal already added
if 'id="envValTribunalSection"' in html:
    print("index.html already has envValTribunalSection.")
else:
    # Target: the beginning of tabEnvironmentValidation
    # <div id="tabEnvironmentValidation" class="inspector-tab-panel hidden">
    # We want to insert the subnav bar, open envValAssimilationSection, add the switch button,
    # and at the end of tabEnvironmentValidation before <div id="tabPlan", close envValAssimilationSection
    # and add envValTribunalSection.

    # 1. Add switch button to header card
    old_btns = '<button id="btnValRunExperiments" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#129514; RUN EXPERIMENTS</button>'
    new_btns = old_btns + '\n            <button id="btnValSwitchTribunal" class="btn-primary" style="font-size:10px; padding:4px 10px; background:linear-gradient(135deg, #a855f7 0%, #7e22ce 100%); color:#ffffff; font-weight:700; border:1px solid #c084fc;">&#9878; REPRODUCIBILITY TRIBUNAL</button>'

    html = html.replace(old_btns, new_btns, 1)

    # 2. Insert Subnav and wrap assimilation section
    subnav_html = """      <div id="tabEnvironmentValidation" class="inspector-tab-panel hidden">
        <!-- Sub-Navigation Toggle for Assimilation Lab vs Reproducibility Tribunal -->
        <div class="tribunal-subnav" style="display:flex; gap:6px; margin-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:6px;">
          <button id="btnSubNavAssimilation" class="btn-subnav active">&#129514; 13M: DATA ASSIMILATION &amp; VALIDATION</button>
          <button id="btnSubNavTribunal" class="btn-subnav">&#9878; 13N: SCIENTIFIC REPRODUCIBILITY TRIBUNAL</button>
        </div>

        <!-- 13M DATA ASSIMILATION LAB SECTION -->
        <div id="envValAssimilationSection">"""

    html = html.replace('      <div id="tabEnvironmentValidation" class="inspector-tab-panel hidden">', subnav_html, 1)

    # 3. Close assimilation section and insert Tribunal Section right before <div id="tabPlan"
    tribunal_section = """        </div><!-- /envValAssimilationSection -->

        <!-- 13N SCIENTIFIC REPRODUCIBILITY TRIBUNAL SECTION -->
        <div id="envValTribunalSection" class="hidden">
          <!-- Tribunal Header Card -->
          <div class="control-card" style="margin-bottom:8px; padding:10px 12px; background:linear-gradient(135deg, rgba(30,27,75,0.95), rgba(15,23,42,0.95)); border:1px solid rgba(168,85,247,0.6); border-radius:6px; box-shadow:0 0 15px rgba(168,85,247,0.15);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <span class="control-label" style="font-size:12px; font-weight:800; color:#c084fc; letter-spacing:0.5px;">&#9878; THE SCIENTIFIC REPRODUCIBILITY TRIBUNAL</span>
                <div style="font-size:10px; color:#cbd5e1; margin-top:2px;">Independent Verification &amp; Adversarial Audit of Milestone 13M &bull; Provenance &bull; 52.1% Claim &bull; Zero Overfitting &bull; Sensor Gating</div>
              </div>
              <span id="tribunalOverallBadge" class="badge" style="background:rgba(245,158,11,0.2); color:#fbbf24; border:1px solid rgba(245,158,11,0.6); font-size:9px; padding:3px 8px; font-weight:700;">QUALIFIED WITH SCIENTIFIC DISCLOSURES</span>
            </div>
            <div style="display:flex; gap:6px; margin-top:8px; flex-wrap:wrap;">
              <button id="btnTribunalRefresh" class="btn-primary" style="font-size:10px; padding:4px 10px; background:#a855f7; color:#fff; font-weight:700; border:1px solid #c084fc;">&#128260; RERUN AUDIT</button>
              <button id="btnTribunalDownloadJson" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#128229; DOWNLOAD CERTIFICATE</button>
              <button id="btnTribunalFilterVerified" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#9989; SHOW VERIFIED</button>
              <button id="btnTribunalFilterQualified" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#9888; SHOW QUALIFIED</button>
            </div>
          </div>

          <!-- 1. Evidence Overview Metrics HUD (4 grid cards) -->
          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; margin-bottom:8px;">
            <div class="control-card" style="margin-bottom:0; padding:8px 6px; text-align:center; background:rgba(0,0,0,0.35); border-left:3px solid #38bdf8;">
              <span style="font-size:8px; color:#94a3b8; display:block;">CLAIMS AUDITED</span>
              <strong id="tribStatAudited" style="font-size:14px; color:#38bdf8; font-family:monospace;">9</strong>
              <div style="font-size:8px; color:#cbd5e1; margin-top:1px;">Formal PDS/GCM Claims</div>
            </div>
            <div class="control-card" style="margin-bottom:0; padding:8px 6px; text-align:center; background:rgba(0,0,0,0.35); border-left:3px solid #10b981;">
              <span style="font-size:8px; color:#94a3b8; display:block;">STRICTLY VERIFIED</span>
              <strong id="tribStatVerified" style="font-size:14px; color:#10b981; font-family:monospace;">7</strong>
              <div style="font-size:8px; color:#cbd5e1; margin-top:1px;">100% Match &amp; Keplerian Math</div>
            </div>
            <div class="control-card" style="margin-bottom:0; padding:8px 6px; text-align:center; background:rgba(0,0,0,0.35); border-left:3px solid #f59e0b;">
              <span style="font-size:8px; color:#94a3b8; display:block;">QUALIFIED DISCLOSURES</span>
              <strong id="tribStatQualified" style="font-size:14px; color:#f59e0b; font-family:monospace;">2</strong>
              <div style="font-size:8px; color:#cbd5e1; margin-top:1px;">52.1% Slice &amp; Modulo Split</div>
            </div>
            <div class="control-card" style="margin-bottom:0; padding:8px 6px; text-align:center; background:rgba(0,0,0,0.35); border-left:3px solid #ef4444;">
              <span style="font-size:8px; color:#94a3b8; display:block;">REJECTED / FABRICATED</span>
              <strong id="tribStatRejected" style="font-size:14px; color:#ef4444; font-family:monospace;">0</strong>
              <div style="font-size:8px; color:#cbd5e1; margin-top:1px;">Zero Synthetic Spoofs</div>
            </div>
          </div>

          <!-- 2. The 52.1% Held-Out RMSE Reduction Claim Deep Investigation -->
          <div class="control-card" style="margin-bottom:8px; padding:10px 12px; border-left:3px solid #f59e0b;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:700; color:#fbbf24;">CLAIM 5 &amp; 6 INVESTIGATION: 52.1% HELD-OUT RMSE REDUCTION &amp; OVERFITTING</span>
              <span class="badge" style="background:rgba(245,158,11,0.2); color:#fbbf24; border:1px solid rgba(245,158,11,0.6); font-size:8.5px;">REPRODUCED WITH DEVIATION</span>
            </div>
            <div style="font-size:9.5px; color:#cbd5e1; margin-bottom:8px; line-height:1.4;">
              <strong>Tribunal Finding:</strong> The reported 52.1% held-out RMSE reduction is <span style="color:#10b981; font-weight:700;">REPRODUCED EXACTLY</span> on the 300-record benchmark slice (<span style="font-family:monospace; color:#38bdf8;">train: -59.16%, test: -52.10%, 95% CI: [46.8%, 56.4%]</span>). However, testing across the entire 1,527-sol mission archive (<span style="font-family:monospace; color:#38bdf8;">N=4,573</span>) reveals generalization collapse to <span style="color:#f59e0b; font-weight:700;">4.22%</span>, and the 13M splitting protocol used an interleaved modulo split (<span style="font-family:monospace;">sol % 10 &lt; 6</span>) rather than a chronological cutoff at Sol 916.
            </div>
            <!-- Side-by-side comparison table -->
            <table class="tribunal-table" style="width:100%; border-collapse:collapse; font-size:9px; background:rgba(0,0,0,0.3); border-radius:4px; overflow:hidden;">
              <thead>
                <tr style="background:rgba(255,255,255,0.05); color:#94a3b8; text-align:left; border-bottom:1px solid rgba(255,255,255,0.1);">
                  <th style="padding:4px 6px;">EVALUATION SLICE</th>
                  <th style="padding:4px 6px;">SAMPLE N</th>
                  <th style="padding:4px 6px;">SPLIT METHOD</th>
                  <th style="padding:4px 6px;">BASELINE TEST RMSE</th>
                  <th style="padding:4px 6px;">CALIBRATED TEST RMSE</th>
                  <th style="padding:4px 6px;">TEST RMSE REDUCTION</th>
                  <th style="padding:4px 6px;">VERDICT</th>
                </tr>
              </thead>
              <tbody id="tribunalCalibrationTableBody">
                <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                  <td style="padding:4px 6px; font-weight:700; color:#e2e8f0;">Benchmark Slice (13M Test Protocol)</td>
                  <td style="padding:4px 6px; font-family:monospace;">300</td>
                  <td style="padding:4px 6px; color:#f59e0b;">Modulo 10 (sol%10 &lt; 6)</td>
                  <td style="padding:4px 6px; font-family:monospace;">50.64 K</td>
                  <td style="padding:4px 6px; font-family:monospace; color:#10b981; font-weight:700;">24.26 K</td>
                  <td style="padding:4px 6px; font-family:monospace; color:#10b981; font-weight:700;">-52.10% (CI: [46.8%, 56.4%])</td>
                  <td style="padding:4px 6px;"><span style="color:#10b981; font-weight:700;">VERIFIED (Exact Match)</span></td>
                </tr>
                <tr>
                  <td style="padding:4px 6px; font-weight:700; color:#e2e8f0;">Full Mission Archive (Multi-Year Drift)</td>
                  <td style="padding:4px 6px; font-family:monospace;">4,573</td>
                  <td style="padding:4px 6px; color:#f59e0b;">Chronological Multi-Year</td>
                  <td style="padding:4px 6px; font-family:monospace;">25.32 K</td>
                  <td style="padding:4px 6px; font-family:monospace; color:#38bdf8;">24.25 K</td>
                  <td style="padding:4px 6px; font-family:monospace; color:#f59e0b; font-weight:700;">-4.22% (Generalization Drift)</td>
                  <td style="padding:4px 6px;"><span style="color:#f59e0b; font-weight:700;">QUALIFIED DISCLOSURE</span></td>
                </tr>
              </tbody>
            </table>
            <!-- Zero Overfitting Formal Revocation Notice -->
            <div style="margin-top:6px; padding:6px 8px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); border-radius:4px; font-size:8.5px; color:#fca5a5;">
              <strong>FORMAL REVOCATION:</strong> The Milestone 13M claim of <em>"zero overfitting"</em> is formally revoked as scientifically invalid. While generalization gap is small on the benchmark slice (7.06% gap), testing across full multi-year orbital cycles ($L_s = 0&deg; \\text{ to } 360&deg;$) proves that a static 3-parameter diurnal spline does not generalize to changing Martian orbital distance and atmospheric dust loading without periodic parameter updates.
            </div>
          </div>

          <!-- 3. Collocation Sensitivity & Gating Matrix -->
          <div class="control-card" style="margin-bottom:8px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:700; color:#e2e8f0;">CLAIM 3 AUDIT: 4D COLLOCATION GATING &amp; SENSITIVITY MATRIX</span>
              <span id="tribCollocSummaryBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; border:1px solid rgba(16,185,129,0.6); font-size:8.5px;">GATING DISCIPLINE VERIFIED</span>
            </div>
            <div style="font-size:9.5px; color:#cbd5e1; margin-bottom:6px;">
              Audited 4,573 normalized MEDA observations against MCD 6.2 GCM under three spatial and temporal tolerance regimes:
            </div>
            <table class="tribunal-table" style="width:100%; border-collapse:collapse; font-size:9px; background:rgba(0,0,0,0.3); border-radius:4px; overflow:hidden;">
              <thead>
                <tr style="background:rgba(255,255,255,0.05); color:#94a3b8; text-align:left; border-bottom:1px solid rgba(255,255,255,0.1);">
                  <th style="padding:4px 6px;">FILTER TIER</th>
                  <th style="padding:4px 6px;">MAX DIST (&Delta;d)</th>
                  <th style="padding:4px 6px;">MAX TIME (&Delta;LTST)</th>
                  <th style="padding:4px 6px;">MAX Ls (&Delta;Ls)</th>
                  <th style="padding:4px 6px;">QUALIFIED</th>
                  <th style="padding:4px 6px;">REJECTED</th>
                  <th style="padding:4px 6px;">PRIMARY REJECTION REASON</th>
                </tr>
              </thead>
              <tbody id="tribunalCollocationTableBody">
                <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                  <td style="padding:4px 6px; font-weight:700; color:#38bdf8;">Strict Gate</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 2.5 km</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 0.25 h</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 2.5&deg;</td>
                  <td style="padding:4px 6px; color:#10b981; font-weight:700; font-family:monospace;">2,548 (55.7%)</td>
                  <td style="padding:4px 6px; color:#ef4444; font-family:monospace;">2,025 (44.3%)</td>
                  <td style="padding:4px 6px; color:#f87171;">EXCEEDS_SPATIAL_TOLERANCE (Rover traverse &gt; 2.5km)</td>
                </tr>
                <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                  <td style="padding:4px 6px; font-weight:700; color:#10b981;">Nominal Gate (13M Standard)</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 50.0 km</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 0.50 h</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 5.0&deg;</td>
                  <td style="padding:4px 6px; color:#10b981; font-weight:700; font-family:monospace;">4,573 (100.0%)</td>
                  <td style="padding:4px 6px; color:#94a3b8; font-family:monospace;">0 (0.0%)</td>
                  <td style="padding:4px 6px; color:#94a3b8;">None (All Jezero crater traverse points pass)</td>
                </tr>
                <tr>
                  <td style="padding:4px 6px; font-weight:700; color:#94a3b8;">Permissive Gate</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 150.0 km</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 1.00 h</td>
                  <td style="padding:4px 6px; font-family:monospace;">&le; 15.0&deg;</td>
                  <td style="padding:4px 6px; color:#10b981; font-weight:700; font-family:monospace;">4,573 (100.0%)</td>
                  <td style="padding:4px 6px; color:#94a3b8; font-family:monospace;">0 (0.0%)</td>
                  <td style="padding:4px 6px; color:#94a3b8;">None (Regional mesoscale envelope)</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 4. Parameter Identifiability & Sensitivity HUD -->
          <div class="control-card" style="margin-bottom:8px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:700; color:#e2e8f0;">PARAMETER IDENTIFIABILITY &amp; SENSITIVITY GRADIENTS</span>
              <span class="badge" style="background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid rgba(56,189,248,0.6); font-size:8.5px;">HESSIAN &kappa; = 142.8</span>
            </div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:6px; font-size:9.5px; text-align:center; margin-bottom:6px;">
              <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
                <span style="font-size:8px; color:#94a3b8; display:block;">&part;RMSE / &part;T_mean</span>
                <strong style="color:#38bdf8; font-size:12px; font-family:monospace;">0.98 K/K</strong>
                <div style="font-size:7.5px; color:#94a3b8;">Linear offset sensitivity</div>
              </div>
              <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
                <span style="font-size:8px; color:#94a3b8; display:block;">&part;RMSE / &part;A_1 (Amp)</span>
                <strong style="color:#38bdf8; font-size:12px; font-family:monospace;">0.54 K/K</strong>
                <div style="font-size:7.5px; color:#94a3b8;">Diurnal amplitude sensitivity</div>
              </div>
              <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px; border:1px solid rgba(239,68,68,0.4);">
                <span style="font-size:8px; color:#fca5a5; display:block;">&part;RMSE / &part;&phi; (Phase)</span>
                <strong style="color:#ef4444; font-size:12px; font-family:monospace;">34.57 K/hr</strong>
                <div style="font-size:7.5px; color:#fca5a5; font-weight:700;">Critical Dawn/Dusk Shift</div>
              </div>
            </div>
            <div style="font-size:8.5px; color:#cbd5e1; background:rgba(0,0,0,0.25); padding:6px; border-radius:4px; line-height:1.3;">
              <strong>Physical Insight:</strong> Diurnal phase shift (&phi;) exhibits extreme gradient sensitivity (34.57 K/hour) because Martian sunrise and sunset induce thermal gradients exceeding 15 K/hour. A 30-minute timing error shifts predicted ground temperature by ~8 K, directly impacting dawn instrument operations.
            </div>
          </div>

          <!-- 5. Competitive Baselines & 32 Cold-Sol Counterexamples -->
          <div class="control-card" style="margin-bottom:8px; padding:10px 12px; border-left:3px solid #38bdf8;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:700; color:#e2e8f0;">COMPETITIVE BASELINES &amp; 32 COLD-SOL COUNTEREXAMPLES</span>
              <span class="badge" style="background:rgba(239,68,68,0.2); color:#f87171; border:1px solid rgba(239,68,68,0.6); font-size:8.5px;">32 DEGRADATION SOLS IDENTIFIED</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; margin-bottom:6px;">
              <!-- Baseline Comparison Box -->
              <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
                <span style="font-size:8.5px; font-weight:700; color:#38bdf8; display:block; margin-bottom:4px;">1-SOL PERSISTENCE BASELINE</span>
                <div style="font-size:9px; color:#cbd5e1; line-height:1.4;">
                  Predictor: <code style="color:#f59e0b;">T_t = T_{t-1}</code><br>
                  Persistence RMSE: <strong style="color:#10b981; font-family:monospace;">20.53 K</strong> (MAE 5.01 K)<br>
                  Static Spline RMSE: <strong style="color:#f87171; font-family:monospace;">24.26 K</strong><br>
                  <span style="font-size:8px; color:#94a3b8;">Persistence outperforms static diurnal spline for tactical 24h forecasting!</span>
                </div>
              </div>
              <!-- Counterexample Summary Box -->
              <div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px;">
                <span style="font-size:8.5px; font-weight:700; color:#f87171; display:block; margin-bottom:4px;">NOCTURNAL RADIATIVE COOLING</span>
                <div style="font-size:9px; color:#cbd5e1; line-height:1.4;">
                  Degraded Sols: <strong style="color:#f87171;">32 Sols</strong> (e.g. Sols 29, 36, 37, 38, 39)<br>
                  Min Ground Temp: <strong style="color:#38bdf8; font-family:monospace;">174.1 K (-99.0&deg;C)</strong><br>
                  Error Increase: <strong style="color:#f87171; font-family:monospace;">+5.6 K to +8.6 K</strong><br>
                  <span style="font-size:8px; color:#94a3b8;">Spline under-predicts deep nocturnal radiative chill.</span>
                </div>
              </div>
            </div>
            <!-- Counterexample list container -->
            <div id="tribunalCounterexampleContainer" style="max-height:85px; overflow-y:auto; font-size:8.5px; font-family:monospace; background:rgba(0,0,0,0.4); padding:4px 6px; border-radius:4px; color:#fca5a5;">
              <!-- Rendered dynamically -->
            </div>
          </div>

          <!-- 6. Science Evidence Registry Table (All 9 Formal Claims) -->
          <div class="control-card" style="margin-bottom:8px; padding:10px 12px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:11px; font-weight:700; color:#e2e8f0;">MASTER EVIDENCE REGISTRY &bull; 9 AUDITED CLAIMS</span>
              <span style="font-size:8.5px; color:#38bdf8;">100% COVERAGE AUDIT</span>
            </div>
            <div id="tribunalEvidenceRegistryContainer" style="max-height:220px; overflow-y:auto; background:rgba(0,0,0,0.3); border-radius:4px;">
              <!-- Rendered dynamically by app.js -->
            </div>
          </div>

          <!-- 7. Mandatory Mission Assurance & Human Astronaut Safety Notice -->
          <div style="padding:8px 10px; border-radius:4px; font-size:8px; line-height:1.4; background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); color:#fca5a5; margin-bottom:8px;">
            <strong>MANDATORY SCIENTIFIC &amp; SAFETY DISCLOSURE:</strong> All environmental digital twins, diurnal spline calibrations, sensor representativeness indices (CRI), and qualification certificates in MarsWalk 2.0 / Project Atlas are mathematical simulation and robotic mission planning tools. They rely on simplified physical models, finite in-situ MEDA soundings, and numerical GCM reanalysis. Under NASA planetary mission assurance standards, these simulated outputs must <strong>NEVER be interpreted as certified safe for human astronauts or operational extravehicular activity (EVA)</strong>.
          </div>
        </div><!-- /envValTribunalSection -->
"""

    target_split = '      </div>\n<div id="tabPlan" class="inspector-tab-panel hidden">'
    if target_split in html:
        html = html.replace(target_split, tribunal_section + target_split, 1)
        print("Replaced target_split in index.html")
    else:
        # Try alternate CRLF
        target_split_crlf = '      </div>\r\n<div id="tabPlan" class="inspector-tab-panel hidden">'
        if target_split_crlf in html:
            html = html.replace(target_split_crlf, tribunal_section + target_split_crlf, 1)
            print("Replaced target_split_crlf in index.html")
        else:
            print("WARNING: Could not find target_split in index.html!")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html updated successfully.")
