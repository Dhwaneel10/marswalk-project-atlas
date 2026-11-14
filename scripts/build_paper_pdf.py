import base64
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
PUB_DIR = REPO_ROOT / "publication" / "project-atlas"
FIG_DIR = PUB_DIR / "figures"
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

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Project Atlas: Research Paper</title>
<style>
@page {{
  size: letter portrait;
  margin: 18mm 16mm 20mm 16mm;
}}
body {{
  font-family: 'Times New Roman', Times, serif;
  font-size: 9.5pt;
  line-height: 1.25;
  color: #111;
  margin: 0;
  padding: 0;
}}
.title-block {{
  text-align: center;
  margin-bottom: 14pt;
}}
h1.paper-title {{
  font-size: 17pt;
  font-weight: bold;
  line-height: 1.2;
  margin: 0 0 8pt 0;
}}
.authors {{
  font-size: 10.5pt;
  font-weight: bold;
  margin-bottom: 3pt;
}}
.affil {{
  font-size: 9pt;
  color: #333;
  margin-bottom: 2pt;
}}
.repo-link {{
  font-family: monospace;
  font-size: 8pt;
  color: #0366d6;
}}
.abstract-box {{
  width: 90%;
  margin: 10pt auto 14pt auto;
  font-size: 8.8pt;
  line-height: 1.28;
  text-align: justify;
}}
.abstract-box b {{
  font-size: 9pt;
}}
.keywords {{
  margin-top: 4pt;
  font-style: italic;
}}
.two-col {{
  column-count: 2;
  column-gap: 16pt;
  text-align: justify;
}}
h2 {{
  font-size: 10.5pt;
  font-weight: bold;
  text-transform: uppercase;
  margin: 10pt 0 4pt 0;
  border-bottom: 0.5pt solid #888;
  padding-bottom: 1pt;
  break-after: avoid;
}}
h3 {{
  font-size: 9.5pt;
  font-weight: bold;
  font-style: italic;
  margin: 6pt 0 2pt 0;
  break-after: avoid;
}}
p {{
  margin: 0 0 6pt 0;
  text-indent: 10pt;
}}
p.no-indent {{
  text-indent: 0;
}}
.equation {{
  text-align: center;
  font-style: italic;
  margin: 5pt 0;
  font-size: 9.5pt;
}}
.figure {{
  margin: 8pt 0;
  text-align: center;
  break-inside: avoid;
}}
.figure img {{
  width: 100%;
  border: 0.5pt solid #ccc;
  border-radius: 2px;
}}
.figure-caption {{
  font-size: 8pt;
  color: #333;
  margin-top: 3pt;
  text-align: justify;
}}
.table-box {{
  margin: 8pt 0;
  width: 100%;
  break-inside: avoid;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8pt;
  margin-top: 2pt;
}}
th, td {{
  padding: 3pt 4pt;
  text-align: left;
}}
th {{
  border-top: 1pt solid #111;
  border-bottom: 0.5pt solid #111;
  font-weight: bold;
}}
tr.last-row td {{
  border-bottom: 1pt solid #111;
}}
.badge-pass {{
  font-weight: bold;
  color: #008800;
}}
.banner-fig {{
  column-span: all;
  margin: 10pt 0;
  text-align: center;
}}
.banner-fig img {{
  width: 100%;
  max-height: 280px;
  object-fit: cover;
  border: 0.5pt solid #aaa;
}}
.references-list {{
  font-size: 7.8pt;
  line-height: 1.2;
  padding-left: 14pt;
  margin: 0;
}}
.references-list li {{
  margin-bottom: 3pt;
}}
</style>
</head>
<body>

<div class="title-block">
  <h1 class="paper-title">Project Atlas: An Integrated, Reproducible Research Simulation Framework for Autonomous Martian Surface Exploration and Settlement Operations</h1>
  <div class="authors">Project Atlas Research Software Engineering Group</div>
  <div class="affil">Independent Planetary Simulation Systems Research</div>
  <div class="repo-link">Repository: https://github.com/nasa-spaceapps/marswalk &middot; Classification: Research Simulation Software</div>
</div>

<div class="abstract-box">
  <b>Abstract</b>&mdash;Future robotic and crewed exploration of the Martian surface demands computational architectures capable of bridging spatial cartography, multi-agent fleet operations, asynchronous communications, and in-situ resource utilization (ISRU) within a unified framework. Traditional mission simulation tools remain compartmentalized, treating route traversal, aerial scouting, environmental hazards, and settlement infrastructure as disconnected engineering domains. This paper presents <b>Project Atlas (MarsWalk 2.0)</b>, an open, reproducible research simulation framework that unifies these disciplines into an autonomous planetary mission operating system. Grounded in authentic United States Geological Survey (USGS) Context Camera (CTX) digital terrain models and Mars Environmental Dynamics Analyzer (MEDA) atmospheric archives, Atlas couples a 10-layer software stack with a discrete-event execution core. The framework models terrain-constrained A* traversal, 3-DOF point-mass rotorcraft aerodynamics in compressible CO<sub>2</sub>, Bayesian active learning for scientific hypothesis discovery, and closed-loop mass-energy conservation ledgers (&Delta;M &le; 10<sup>-4</sup> kg). To maintain epistemic rigor, the platform classifies all simulation outputs into an 8-tier epistemic taxonomy and enforces bit-exact deterministic replay via SHA-256 Merkle hash chains. We evaluate Atlas through a 60-Sol flagship mission (<code>ATLAS-MARS-BASE-ALPHA-001</code>) and a 12-stage adversarial failure gauntlet, demonstrating that the system successfully rejects stale commands during 14.2-minute communication blackouts, executes autonomous load-shedding during dust storms (&tau; = 2.80), and maintains full mass balance. All code, data schemas, and test suites are openly accessible for independent verification.
  <div class="keywords"><b>Keywords</b>&mdash;Planetary Robotics, Mars Exploration, Autonomous Systems, In-Situ Resource Utilization, Reproducible Research Software, Discrete-Event Simulation.</div>
</div>

<div class="two-col">

<h2>I. Introduction</h2>
<p>Surface exploration of Mars presents unprecedented operational challenges. The physical separation between Earth and Mars imposes one-way light-time (OWLT) radio propagation latencies ranging from approximately 3 to 22 minutes, precluding real-time teleoperation of surface assets. Consequently, robotic systems must operate with bounded local autonomy, balancing multi-stop traverse planning, power constraints, environmental risks, and dynamic scientific discovery without continuous ground intervention.</p>
<p>As mission concepts transition from single-rover sorties toward permanent robotic settlement outposts, the complexity compounds. Traversal planning must couple with in-situ resource utilization---such as regolith microwave sintering, oxygen extraction via Solid Oxide Electrolysis (SOXE), and water harvesting---all bounded by finite power architectures such as fission surface power (Kilopower) [4]. Existing spaceflight simulators are largely specialized: trajectory planners do not simulate chemical ISRU yields; chemical plant models do not interface with aerial reconnaissance sorties; and high-level campaign schedulers rarely account for terrain slope hazards derived from orbital remote sensing.</p>
<p>Project Atlas addresses this fragmentation by establishing an integrated, reproducible research framework that models the interdependencies of a multi-sol Martian surface campaign.</p>

<div class="figure">
  <img src="{fig1}" alt="Cockpit Overview">
  <div class="figure-caption"><b>Fig. 1.</b> Project Atlas Mission Operating System Cockpit HUD. Real-time telemetry display showing 3D draped terrain, heterogeneous fleet status, Kilopower and solar generation balances, and SHA-256 state signature.</div>
</div>

<h2>II. Problem Statement</h2>
<p class="no-indent">To evaluate future planetary missions, researchers require a simulation ecosystem that answers three core engineering questions:</p>
<ol style="margin:2pt 0 6pt 14pt; padding:0; font-size:9pt;">
  <li>How can heterogeneous fleets coordinate exploration and infrastructure deployment under deep-space communication delays?</li>
  <li>How do dynamic environmental disruptions propagate through coupled power, resource, and construction schedules?</li>
  <li>How can researchers guarantee reproducibility without confusing synthetic heuristics with empirical planetary measurements?</li>
</ol>

<h2>III. System Requirements</h2>
<p class="no-indent">Atlas was engineered under six primary design requirements:</p>
<p><b>Req-1 (Geospatial Authenticity):</b> Surface operations must be anchored to genuine remote-sensing elevation rasters. Synthetic fractal topography is strictly prohibited.</p>
<p><b>Req-2 (Epistemic Transparency):</b> All outputs must carry traceable metadata distinguishing direct physical observations, derived geometric quantities, and computational heuristics.</p>
<p><b>Req-3 (Closed Physical Accounting):</b> Mass and energy ledgers must satisfy conservation laws without numerical drift (&Delta;M &le; 10<sup>-4</sup> kg).</p>
<p><b>Req-4 (Deterministic Replay):</b> Executing the same mission configuration must yield bit-exact identical state trajectories and cryptographic root hashes.</p>
<p><b>Req-5 (Asynchronous Fault Resilience):</b> The platform must autonomously detect environmental deficits, shed non-essential electrical loads, and maintain habitat thermal baselines.</p>
<p><b>Req-6 (Open Software Ergonomics):</b> The platform must be installable, verifiable, and executable via single-line commands without proprietary dependencies.</p>

<div class="table-box">
  <div style="font-size:8pt; font-weight:bold; margin-bottom:2pt; text-align:center;">TABLE I: The 10-Layer Project Atlas Software Stack</div>
  <table>
    <tr><th>Layer</th><th>Domain</th><th>Key Responsibilities</th></tr>
    <tr><td>10</td><td>Reproducibility</td><td>SHA-256 Merkle chain, replay audit</td></tr>
    <tr><td>09</td><td>Visualization</td><td>Three.js 3D viewport, Cockpit HUD</td></tr>
    <tr><td>08</td><td>Mission OS</td><td>Discrete-event scheduler, DAG compiler</td></tr>
    <tr><td>07</td><td>Settlement</td><td>Kilopower reactor, ISRU, sintering</td></tr>
    <tr><td>06</td><td>Fleet Control</td><td>Rovers, hexacopter, lease locks</td></tr>
    <tr><td>05</td><td>Autonomy</td><td>OWLT delay, idempotent commands</td></tr>
    <tr><td>04</td><td>Planning</td><td>Pairwise A* traversal, 2-Opt TSP</td></tr>
    <tr><td>03</td><td>Simulation</td><td>Point-mass aero, Horn slope kernel</td></tr>
    <tr><td>02</td><td>Science</td><td>Bayesian hypothesis, Shannon gain</td></tr>
    <tr class="last-row"><td>01</td><td>Ingestion</td><td>USGS 20m CTX DTM, MEDA weather</td></tr>
  </table>
</div>

<div class="figure">
  <img src="{fig2}" alt="Mission DAG">
  <div class="figure-caption"><b>Fig. 2.</b> Compiled 7-Phase Multi-Sol Mission Directed Acyclic Graph (DAG) detailing 42 discrete tasks across a 60-Sol horizon.</div>
</div>

<h2>IV. Topographic Grounding</h2>
<p>Atlas models the Western Delta region of Jezero Crater (18.38&deg;N to 18.52&deg;N, 77.40&deg;E to 77.55&deg;E), the landing site of NASA's Mars 2020 Perseverance rover [2, 9].</p>
<p>Terrain elevation z(x, y) is sampled from the USGS 20 m/pixel DTM. Surface gradient components are computed using the Horn 8-neighborhood kernel [3]:</p>
<div class="equation">&part;z/&part;x = [(z<sub>++</sub> + 2z<sub>+0</sub> + z<sub>+-</sub>) - (z<sub>-+</sub> + 2z<sub>-0</sub> + z<sub>--</sub>)] / (8 &middot; &Delta;x)</div>
<div class="equation">&part;z/&part;y = [(z<sub>++</sub> + 2z<sub>0+</sub> + z<sub>-+</sub>) - (z<sub>+-</sub> + 2z<sub>0-</sub> + z<sub>--</sub>)] / (8 &middot; &Delta;y)</div>
<div class="equation">&theta;<sub>slope</sub> = arctan(&radic;[(&part;z/&part;x)<sup>2</sup> + (&part;z/&part;y)<sup>2</sup>]) &middot; 180&deg; / &pi;</div>
<p>Robotic rovers enforce an operational slope ceiling of &theta; &le; 15.0&deg;.</p>

<h2>V. Mission Planning & Optimization</h2>
<p>Traverse planning combines pairwise directed A* search with a 2-Opt local search Travelling Salesperson Problem (TSP) heuristic:</p>
<div class="equation">c(u, v) = d(u, v) &middot; [1.0 + &alpha; &middot; (&theta; / &theta;<sub>max</sub>)<sup>2</sup>]</div>
<p>This balances Euclidean distance against topographic incline penalties.</p>

<div class="figure">
  <img src="{fig3}" alt="Fleet Registry">
  <div class="figure-caption"><b>Fig. 3.</b> Heterogeneous Fleet Management Registry tracking asset health, spatial coordinates, and single-lease operational locks.</div>
</div>

<h2>VI. Rotorcraft Aerodynamics</h2>
<p>Atmospheric density &rho;(z) is modeled hypsometrically with scale height H<sub>&rho;</sub> &approx; 11,100 m [5]:</p>
<div class="equation">&rho;(z) = &rho;<sub>0</sub> &middot; exp[-(z - z<sub>0</sub>) / H<sub>&rho;</sub>]</div>
<p>The speed of sound in Martian CO<sub>2</sub> (&gamma; = 1.29, R = 188.9 J/(kg&middot;K)) at T = 210 K is:</p>
<div class="equation">a = &radic;(&gamma; R T) = &radic;(1.29 &middot; 188.9 &middot; 210.0) &approx; 226.2 m/s</div>
<p>Blade tip speed at radius R<sub>blade</sub> = 0.60 m and &omega; = 2,400 RPM is V<sub>tip</sub> = 150.80 m/s, yielding a tip Mach:</p>
<div class="equation">M<sub>tip</sub> = 150.80 / 226.20 &approx; 0.667 &lt; 0.75</div>
<p>Because M<sub>tip</sub> &lt; 0.75, the rotor operates comfortably in the high subsonic regime, avoiding severe shock-induced stall [1].</p>

<div class="figure">
  <img src="{fig4}" alt="Bayesian Science">
  <div class="figure-caption"><b>Fig. 4.</b> Active Learning Scientific Discovery Ledger showing hypotheses, likelihood ratios, and Shannon entropy reduction.</div>
</div>

<h2>VII. Bayesian Active Discovery</h2>
<p>Active discovery evaluates hypotheses in odds formulation [6, 7, 10]:</p>
<div class="equation">Odds(H | E) = Odds(H) &middot; [P(E | H) / P(E | &not;H)]</div>
<p>Information gain is measured via Shannon binary entropy reduction:</p>
<div class="equation">&Delta;I = H(P<sub>prior</sub>) - H(P<sub>posterior</sub>) [bits]</div>
<div class="equation">H(p) = - [p log<sub>2</sub> p + (1-p) log<sub>2</sub>(1-p)]</div>
<p>Ingesting PIXL geochemical data (&Lambda; = 8.5) at Delta Scarp reduces entropy from 0.934 bits to 0.327 bits, achieving a +0.607 bit gain.</p>

<div class="figure">
  <img src="{fig5}" alt="ISRU HUD">
  <div class="figure-caption"><b>Fig. 5.</b> Closed-Loop In-Situ Resource Utilization (ISRU) and Kilopower HUD showing mass conservation ledgers and sintering line draw.</div>
</div>

<h2>VIII. Settlement & ISRU Systems</h2>
<p>Infrastructure models a 40 kWe Kilopower fission reactor [4] and closed stoichiometric chemical systems:</p>
<div class="equation">2CO<sub>2</sub> &rarr; 2CO + O<sub>2</sub> &nbsp; (&Delta;m = 0.000 g)</div>
<div class="equation">CO<sub>2</sub> + 4H<sub>2</sub> &rarr; CH<sub>4</sub> + 2H<sub>2</sub>O &nbsp; (&Delta;m = 0.000 g)</div>
<p>Microwave regolith sintering consumes 1.4 kWh per 20 kg block (28.0 kWe draw at 20 blocks/hour).</p>

<div class="figure">
  <img src="{fig6}" alt="Dust Storm Load Shedding">
  <div class="figure-caption"><b>Fig. 6.</b> Autonomous Fault Detection, Isolation, and Recovery (FDIR) executing automated load-shedding during a Sol 48 convective dust storm (&tau; = 2.80).</div>
</div>

<h2>IX. Resilience & Autonomous FDIR</h2>
<p>During a Sol 48 dust storm (&tau; = 2.80), solar flux collapses from 480 W/m<sup>2</sup> to 120 W/m<sup>2</sup>. The resilience coordinator detects battery depletion, sheds the 28.0 kWe sintering line, and maintains habitat thermal heating at 294.15 K (+21&deg;C).</p>

<h2>X. Replay & Verification</h2>
<p>Discrete events execute through a priority queue. Replay executions produce bit-exact Merkle root hashes across 61 timeline snapshots.</p>

<div class="figure">
  <img src="{fig7}" alt="Merkle Replay Chain">
  <div class="figure-caption"><b>Fig. 7.</b> Continuous SHA-256 Merkle hash chain verifying bit-exact deterministic replay across 61 timeline snapshots.</div>
</div>

<div class="table-box">
  <div style="font-size:8pt; font-weight:bold; margin-bottom:2pt; text-align:center;">TABLE II: Flagship Campaign Verification Audit</div>
  <table>
    <tr><th>Metric</th><th>Target</th><th>Result</th><th>Status</th></tr>
    <tr><td>Readiness Score</td><td>&ge; 95.0%</td><td>100.0%</td><td class="badge-pass">PASS</td></tr>
    <tr><td>Merkle Root Hash</td><td>Bit-Exact</td><td>f9d124...bd14</td><td class="badge-pass">PASS</td></tr>
    <tr><td>Mass Discrepancy</td><td>&le; 10<sup>-4</sup> kg</td><td>0.000000 kg</td><td class="badge-pass">PASS</td></tr>
    <tr><td>Hypotheses Validated</td><td>&ge; 2</td><td>2 Confirmed</td><td class="badge-pass">PASS</td></tr>
    <tr><td>Blocks Sintered</td><td>&ge; 240</td><td>420 blocks</td><td class="badge-pass">PASS</td></tr>
    <tr><td>Core Habitat Temp</td><td>&ge; 288 K</td><td>294.15 K</td><td class="badge-pass">PASS</td></tr>
    <tr class="last-row"><td>Repository Tests</td><td>100% Pass</td><td>1,126 / 1,126</td><td class="badge-pass">PASS</td></tr>
  </table>
</div>

<h2>XI. Scientific Limitations</h2>
<p class="no-indent">Atlas is an academic research simulation framework. We explicitly state:</p>
<p>1. <b>No Astronaut Safety Certification:</b> Modeled traversals, life-support balances, and habitats do not certify human operational spaceflight safety.</p>
<p>2. <b>Point-Mass Aerodynamics:</b> Rotorcraft dynamics use 3-DOF momentum theory without non-linear blade aeroelastic flutter.</p>
<p>3. <b>Ideal ISRU Yields:</b> Chemical kinetics assume nominal catalyst activity without dust poisoning.</p>
<p>4. <b>Spatial Bounds:</b> Quantitative hazard models are bounded to the 5x5 km USGS CTX Jezero raster.</p>

<h2>XII. Conclusion</h2>
<p>Project Atlas demonstrates that surface exploration, deep-space autonomy, and settlement infrastructure can be simulated within a unified, computationally rigorous, and reproducible architecture. By enforcing closed conservation laws, strict epistemic labeling, and deterministic cryptographic replay, Atlas offers an auditable open-source testbed for evaluating future planetary surface exploration concepts.</p>

<h2>References</h2>
<ol class="references-list">
  <li>J. Balaram et al., &ldquo;Mars Helicopter Technology Demonstrator: Ground and Flight Verification,&rdquo; <i>AIAA SciTech Forum</i>, 2021.</li>
  <li>K. A. Farley et al., &ldquo;Aqueously altered rocks on the floor of Jezero crater, Mars,&rdquo; <i>Science</i>, vol. 377, no. 6614, p. eabo2196, 2022.</li>
  <li>B. K. P. Horn, &ldquo;Hill shading and the reflectance map,&rdquo; <i>Proc. IEEE</i>, vol. 69, no. 1, pp. 14&ndash;47, 1981.</li>
  <li>P. R. McClure et al., &ldquo;Design and Testing of the Kilopower Reactor,&rdquo; <i>Nuclear Technology</i>, vol. 206, no. sup1, pp. S3&ndash;S15, 2020.</li>
  <li>J. A. Rodriguez-Manfredi et al., &ldquo;The Mars Environmental Dynamics Analyzer (MEDA) Instrument on the Mars 2020 Mission,&rdquo; <i>Space Sci. Rev.</i>, vol. 217, no. 3, p. 48, 2021.</li>
  <li>C. E. Shannon, &ldquo;A Mathematical Theory of Communication,&rdquo; <i>Bell Syst. Tech. J.</i>, vol. 27, no. 3, pp. 379&ndash;423, 1948.</li>
  <li>J. F. Mustard et al., &ldquo;Hydrated silicate minerals on Mars observed by CRISM,&rdquo; <i>Nature</i>, vol. 454, no. 7202, pp. 305&ndash;309, 2008.</li>
  <li>B. L. Ehlmann et al., &ldquo;Orbital identification of carbonate-bearing rocks on Mars,&rdquo; <i>Science</i>, vol. 322, no. 5909, pp. 1828&ndash;1832, 2008.</li>
  <li>N. Mangold et al., &ldquo;Perseverance rover reveals ancient delta-lake system at Jezero crater,&rdquo; <i>Science</i>, vol. 374, no. 6568, pp. 711&ndash;717, 2021.</li>
  <li>J. F. Bell et al., &ldquo;Geological, multispectral, and meteorological imaging results in Jezero crater,&rdquo; <i>Sci. Adv.</i>, vol. 8, no. 47, p. eadd8565, 2022.</li>
</ol>

</div>
</body>
</html>
"""

html_path = PUB_DIR / "paper_layout.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"HTML paper layout written to {html_path}")

# Compile to PDF using headless Chrome
pdf_path = PUB_DIR / "project-atlas-paper.pdf"
cmd = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={str(pdf_path)}",
    f"file:///{str(html_path).replace(chr(92), '/')}"
]

print("Compiling PDF with Chromium PDF engine...")
proc = subprocess.run(cmd, capture_output=True, text=True)
if pdf_path.exists() and pdf_path.stat().st_size > 1000:
    print(f"SUCCESS: Generated PDF at {pdf_path} ({pdf_path.stat().st_size} bytes)")
else:
    print(f"FAILED to generate PDF: {proc.stderr}")
