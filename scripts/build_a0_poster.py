"""
scripts/build_a0_poster.py
Generates the ISO A0 Technical Poster (841 x 1189 mm) in PDF format for Project Atlas.
"""

import base64
import subprocess
from pathlib import Path

REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
POSTER_DIR = REPO_ROOT / "publication" / "poster"
FIG_DIR = REPO_ROOT / "publication" / "project-atlas" / "figures"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def load_img_b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

fig1 = load_img_b64(FIG_DIR / "fig1_cockpit_overview.png")
fig2 = load_img_b64(FIG_DIR / "fig2_mission_dag.png")
fig3 = load_img_b64(FIG_DIR / "fig3_fleet_registry.png")
fig4 = load_img_b64(FIG_DIR / "fig4_bayesian_science.png")
fig5 = load_img_b64(FIG_DIR / "fig5_isru_hud.png")
fig6 = load_img_b64(FIG_DIR / "fig6_dust_storm_load_shed.png")
fig7 = load_img_b64(FIG_DIR / "fig7_merkle_replay_chain.png")

poster_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Project Atlas: ISO A0 Technical Poster</title>
<style>
@page {{
  size: 841mm 1189mm;
  margin: 0;
}}
* {{
  box-sizing: border-box;
}}
body {{
  margin: 0;
  padding: 24mm 24mm 20mm 24mm;
  width: 841mm;
  height: 1189mm;
  background: #050b12;
  color: #e6edf3;
  font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}}
/* HEADER */
.header-box {{
  background: linear-gradient(135deg, #091728 0%, #0c1a2e 100%);
  border: 2mm solid #00e5ff;
  border-radius: 8mm;
  padding: 12mm 18mm;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12mm;
  box-shadow: 0 10mm 30mm rgba(0, 229, 255, 0.15);
}}
.header-left {{
  flex: 1;
}}
.title {{
  font-size: 34pt;
  font-weight: 900;
  color: #ffffff;
  letter-spacing: -0.5px;
  margin-bottom: 4mm;
  text-transform: uppercase;
}}
.title span {{
  color: #00e5ff;
}}
.subtitle {{
  font-size: 16pt;
  font-weight: 600;
  color: #8899a6;
  margin-bottom: 4mm;
}}
.authors {{
  font-size: 13pt;
  color: #c9d1d9;
}}
.header-right {{
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 3mm;
}}
.badge-id {{
  font-size: 13pt;
  font-weight: 800;
  background: rgba(0, 229, 255, 0.15);
  color: #00e5ff;
  border: 1mm solid #00e5ff;
  padding: 3mm 8mm;
  border-radius: 4mm;
  display: inline-block;
}}
.meta-txt {{
  font-size: 10.5pt;
  color: #8899a6;
  font-family: monospace;
}}

/* 3-COLUMN GRID */
.poster-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10mm;
  flex: 1;
  margin-bottom: 10mm;
}}
.col {{
  display: flex;
  flex-direction: column;
  gap: 8mm;
}}

/* CARDS */
.card {{
  background: #091320;
  border: 1mm solid #1e334d;
  border-radius: 6mm;
  padding: 8mm 10mm;
  display: flex;
  flex-direction: column;
}}
.card-header {{
  display: flex;
  align-items: center;
  gap: 3mm;
  font-size: 15pt;
  font-weight: 800;
  color: #00e5ff;
  text-transform: uppercase;
  margin-bottom: 4mm;
  border-bottom: 0.5mm solid #1e334d;
  padding-bottom: 2mm;
}}
.card-body {{
  font-size: 10.5pt;
  line-height: 1.45;
  color: #c9d1d9;
}}
.card-body p {{
  margin: 0 0 3mm 0;
}}
.card-body ul {{
  margin: 0;
  padding-left: 6mm;
}}
.card-body li {{
  margin-bottom: 2mm;
}}
.equation {{
  background: #050b12;
  border: 0.5mm solid #1b2f48;
  padding: 2.5mm 4mm;
  border-radius: 2mm;
  text-align: center;
  font-family: 'Times New Roman', serif;
  font-style: italic;
  font-size: 11pt;
  margin: 3mm 0;
  color: #7ee787;
}}
.poster-img {{
  width: 100%;
  border-radius: 3mm;
  border: 0.8mm solid #254060;
  margin-top: 3mm;
  display: block;
}}
.metrics-strip {{
  display: flex;
  gap: 3mm;
  margin-top: 3mm;
}}
.m-pill {{
  background: #050b12;
  border: 0.5mm solid #1e334d;
  border-radius: 3mm;
  padding: 2mm 3mm;
  flex: 1;
  text-align: center;
}}
.m-label {{
  font-size: 7.5pt;
  color: #8899a6;
  text-transform: uppercase;
}}
.m-value {{
  font-size: 11pt;
  font-weight: 800;
  color: #7ee787;
}}

/* FOOTER */
.footer-banner {{
  background: #091320;
  border: 1mm solid #1e334d;
  border-radius: 5mm;
  padding: 6mm 14mm;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11pt;
  color: #8899a6;
}}
.footer-banner b {{
  color: #00e5ff;
}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header-box">
  <div class="header-left">
    <div class="title">PROJECT ATLAS <span>(MarsWalk 2.0)</span></div>
    <div class="subtitle">An Integrated, Reproducible Research Simulation Framework for Autonomous Martian Surface Exploration</div>
    <div class="authors"><b>Project Atlas Research Software Engineering Group</b> &middot; Independent Planetary Simulation Systems Research</div>
  </div>
  <div class="header-right">
    <div><span class="badge-id">RESEARCH PREVIEW 1.0</span></div>
    <div class="meta-txt">BUILD: 13V-RC1 &middot; ISO A0 EDITION</div>
    <div class="meta-txt">REPO: github.com/nasa-spaceapps/marswalk</div>
  </div>
</div>

<!-- 3 COLUMNS -->
<div class="poster-grid">

  <!-- COLUMN 1: MOTIVATION, ARCHITECTURE & TOPOGRAPHY -->
  <div class="col">
    <div class="card">
      <div class="card-header">1. Research Motivation & Problem</div>
      <div class="card-body">
        <p>Interplanetary light-time delays (3&ndash;22 min OWLT) prevent real-time ground control of surface rovers and aerial robotics. Traditional simulators are silod: routing tools ignore ISRU; chemical models ignore topography; and schedulers assume instantaneous communication.</p>
        <p><b>Project Atlas</b> integrates spatial cartography, multi-agent fleet operations, Bayesian active learning, and nuclear/solar infrastructure into a closed-loop planetary mission operating system.</p>
        <div class="metrics-strip">
          <div class="m-pill"><div class="m-label">OWLT Latency</div><div class="m-value">14.2 min</div></div>
          <div class="m-pill"><div class="m-label">Mission Horizon</div><div class="m-value">60 Sols</div></div>
          <div class="m-pill"><div class="m-label">Test Suite</div><div class="m-value">1,126 PASS</div></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">2. 10-Layer Modular Architecture</div>
      <div class="card-body">
        <p>Decouples pure mathematical computation from discrete-event state orchestration across 10 structured layers (Remote Sensing &rarr; Science &rarr; Simulation &rarr; Planning &rarr; Autonomy &rarr; Fleet &rarr; Settlement &rarr; Mission OS &rarr; WebGL &rarr; Merkle Replay).</p>
        <img class="poster-img" src="{fig2}" alt="Mission DAG">
      </div>
    </div>

    <div class="card">
      <div class="card-header">3. Topographic Cartography: USGS DTM</div>
      <div class="card-body">
        <p><b>Strict Rule: Zero Synthetic Topography.</b> Grounded in authentic USGS Context Camera (CTX) 20 m/pixel Digital Terrain Model covering a 25 km&sup2; sector of Jezero Crater (SHA-256: <code>875e7e...</code> verified).</p>
        <p>Surface slope vectors calculated via Horn's 8-neighborhood convolution kernel:</p>
        <div class="equation">&theta;<sub>slope</sub> = arctan(&radic;[(&part;z/&part;x)<sup>2</sup> + (&part;z/&part;y)<sup>2</sup>])</div>
        <p>Robotic rovers enforce slope ceiling &le; 15.0&deg;; crew EVA analogues &le; 20.0&deg;.</p>
        <img class="poster-img" src="{fig1}" alt="Terrain Cockpit">
      </div>
    </div>
  </div>

  <!-- COLUMN 2: AERODYNAMICS, SCIENCE & ISRU -->
  <div class="col">
    <div class="card">
      <div class="card-header">4. Rotorcraft Aerodynamics in Thin CO2</div>
      <div class="card-body">
        <p>Point-mass momentum theory in compressible CO<sub>2</sub> (&gamma; = 1.29, a &approx; 226.2 m/s). Density varies hypsometrically: &rho;(z) = &rho;<sub>0</sub> exp(-(z - z<sub>0</sub>)/H<sub>&rho;</sub>) with H<sub>&rho;</sub> = 11.1 km.</p>
        <div class="equation">V<sub>tip</sub> = &omega; &middot; R<sub>blade</sub> = 150.8 m/s &nbsp;&rarr;&nbsp; M<sub>tip</sub> = 0.667 &lt; 0.75</div>
        <p>Ensures rotor operates in the high subsonic regime, avoiding transonic shock stall.</p>
        <img class="poster-img" src="{fig3}" alt="Fleet Registry">
      </div>
    </div>

    <div class="card">
      <div class="card-header">5. Bayesian Active Discovery & Information Gain</div>
      <div class="card-body">
        <p>Autonomous discovery updates mineralogical hypotheses via Bayes' rule in odds formulation:</p>
        <div class="equation">Odds(H | E) = Odds(H) &middot; [P(E | H) / P(E | &not;H)]</div>
        <p>Quantifies scientific return via Shannon binary entropy reduction:</p>
        <div class="equation">&Delta;I = H(P<sub>prior</sub>) - H(P<sub>posterior</sub>) [bits]</div>
        <p>Delta Scarp PIXL geochemical ingestion (&Lambda; = 8.5) increases posterior from 65% &rarr; 94%, gaining +0.607 bits of empirical information.</p>
        <img class="poster-img" src="{fig4}" alt="Bayesian Science">
      </div>
    </div>

    <div class="card">
      <div class="card-header">6. Closed Stoichiometric ISRU Systems</div>
      <div class="card-body">
        <p>Powered by a 40 kWe Kilopower fission reactor baseline and solar PV. Chemical plants satisfy exact elemental mass conservation (&Delta;m = 0.000 g):</p>
        <div class="equation">2 CO<sub>2</sub> &rarr; 2 CO + O<sub>2</sub> &nbsp;&nbsp;|&nbsp;&nbsp; CO<sub>2</sub> + 4 H<sub>2</sub> &rarr; CH<sub>4</sub> + 2 H<sub>2</sub>O</div>
        <p>Microwave regolith sintering line (28 kWe draw) produced 420 structural radiation berm blocks at 1.4 kWh per 20 kg block.</p>
        <img class="poster-img" src="{fig5}" alt="ISRU HUD">
      </div>
    </div>
  </div>

  <!-- COLUMN 3: RESILIENCE, AUDIT & LIMITATIONS -->
  <div class="col">
    <div class="card">
      <div class="card-header">7. FDIR Load-Shedding & Dust Storms</div>
      <div class="card-body">
        <p>Sol 48 convective dust storm (&tau; = 2.80) drops solar flux by 75%. Autonomous FDIR sheds 28 kWe microwave sintering line within 1 Sol, holding habitat core steady at 294.15 K (+21&deg;C).</p>
        <img class="poster-img" src="{fig6}" alt="Dust Storm Load Shedding">
      </div>
    </div>

    <div class="card">
      <div class="card-header">8. Deterministic Replay & Merkle Hash Chains</div>
      <div class="card-body">
        <p>Replay executions from pristine memory produce bit-exact root hash <code>f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14</code> across 61 timeline snapshots. Net mass discrepancy: &Delta;M = 0.000000 kg.</p>
        <img class="poster-img" src="{fig7}" alt="Merkle Replay Chain">
      </div>
    </div>

    <div class="card">
      <div class="card-header">9. Verification Battery & Epistemic Limits</div>
      <div class="card-body">
        <ul style="font-size:9.5pt;">
          <li><b>Automated Tests:</b> 1,126 / 1,126 passed (100.0%) in 183.94s.</li>
          <li><b>Adversarial Gauntlet:</b> 20 dedicated tests (Challenges A&ndash;L) passed.</li>
          <li><b>Preflight Check:</b> 12/12 checkpoints verified in 366.7 ms.</li>
          <li><b>No Astronaut Safety Certification:</b> Research simulation only.</li>
          <li><b>Point-Mass Aero:</b> 3-DOF model without aeroelastic flutter.</li>
          <li><b>Stoichiometric Yields:</b> No dynamic catalyst poisoning modeled.</li>
        </ul>
      </div>
    </div>

    <div class="card" style="background:#0c1d30; border-color:#00e5ff;">
      <div class="card-header" style="color:#7ee787;">10. One-Command Flagship Reproduction</div>
      <div class="card-body" style="font-family:monospace; font-size:10pt;">
        <code>python scripts/run_flagship_mission.py</code><br>
        <span style="font-size:8.5pt; color:#8899a6; font-family:sans-serif;">Generates full dossier, event ledger, and verified root hash offline.</span>
      </div>
    </div>
  </div>

</div>

<!-- FOOTER -->
<div class="footer-banner">
  <div><b>Project Atlas (MarsWalk 2.0)</b> &middot; Academic Research Simulation Framework &middot; Non-Flight-Certified</div>
  <div><b>One-Command Flagship Replay:</b> <code>python scripts/run_flagship_mission.py</code></div>
  <div><b>Test Coverage:</b> 1,126 / 1,126 Passed (100%) &middot; Merkle Root: <code>f9d124...bd14</code></div>
</div>

</body>
</html>
"""

poster_html_path = POSTER_DIR / "poster_layout.html"
with open(poster_html_path, "w", encoding="utf-8") as f:
    f.write(poster_html)
print(f"Poster HTML written to {poster_html_path}")

pdf_out = POSTER_DIR / "Project_Atlas_A0_Poster.pdf"
cmd = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={str(pdf_out)}",
    f"file:///{str(poster_html_path).replace(chr(92), '/')}"
]
print("Compiling A0 Poster PDF with Chromium PDF engine...")
proc = subprocess.run(cmd, capture_output=True, text=True)
if pdf_out.exists() and pdf_out.stat().st_size > 1000:
    print(f"SUCCESS: Generated A0 Poster PDF at {pdf_out} ({pdf_out.stat().st_size} bytes)")
else:
    print(f"FAILED to generate A0 poster PDF")
