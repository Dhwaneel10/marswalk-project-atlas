"""
scripts/build_presentation_deck.py
Builds the 20-slide Conference Presentation Deck in PDF and OpenXML PPTX formats for Project Atlas.
"""

import base64
import os
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
CONF_DIR = REPO_ROOT / "publication" / "conference"
SHOWCASE_DIR = REPO_ROOT / "outputs" / "conference_showcase" / "mission_os"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

SLIDES_DATA = [
    {
        "num": 1,
        "title": "PROJECT ATLAS (MarsWalk 2.0)",
        "subtitle": "An Integrated, Reproducible Research Simulation Framework for Autonomous Martian Surface Exploration and Settlement Operations",
        "tag": "ACADEMIC RESEARCH PREVIEW 1.0",
        "points": [
            "Modular 10-layer planetary mission operating system.",
            "Grounded in authentic USGS CTX 20m DTM and MEDA atmospheric archives.",
            "Coupled robotics, aerodynamics, Bayesian active science, and chemical ISRU.",
            "Bit-exact deterministic replay with SHA-256 Merkle hash chain auditing."
        ],
        "image": "01_mission_os_cockpit_initial_overview.png",
        "metrics": [("STATUS", "RELEASE PACKAGED"), ("BUILD", "13V-RC1"), ("TESTS", "1,126 PASS (100%)")]
    },
    {
        "num": 2,
        "title": "The Planetary Exploration Dilemma",
        "subtitle": "Fragmented Simulators vs. Coupled Interplanetary Reality",
        "tag": "OPERATIONAL MOTIVATION",
        "points": [
            "Interplanetary latency (OWLT: 3 to 22 min) precludes real-time teleoperation.",
            "Traditional simulation is silod: traverse planners ignore chemical ISRU; chemical models ignore topography.",
            "How do coupled environmental, power, and logistical constraints interact during multi-sol campaigns?",
            "Need for rigorous epistemic boundaries to prevent synthetic heuristics from masquerading as planetary facts."
        ],
        "image": "02_high_level_intent_ingestion.png",
        "metrics": [("LATENCY", "14.2 min OWLT"), ("STUDY ZONE", "Jezero Delta (5x5 km)"), ("DTM RESOLUTION", "20 m/pixel")]
    },
    {
        "num": 3,
        "title": "10-Layer Software Architecture Stack",
        "subtitle": "Decoupling Computational Engines from Orchestration Managers",
        "tag": "SYSTEMS ARCHITECTURE",
        "points": [
            "Layer 01-03: Cartographic ingestion (USGS DTM), Bayesian science, and Horn physical slope kernels.",
            "Layer 04-06: Pairwise A* traversal, deep-space autonomy, and heterogeneous fleet control.",
            "Layer 07-08: Settlement systems (Kilopower, MOXIE, Sabatier) and discrete-event DAG execution.",
            "Layer 09-10: Three.js WebGL visualization and Merkle replay verification."
        ],
        "image": "03_mission_compilation_7_phases.png",
        "metrics": [("LAYERS", "10 Modular"), ("DISCRETE TASKS", "42 DAG Tasks"), ("CYCLIC DEPS", "0 (Strictly DAG)")]
    },
    {
        "num": 4,
        "title": "Topographic Grounding: USGS CTX DTM",
        "subtitle": "Authentic Remote Sensing vs. Synthetic Fractal Illusions",
        "tag": "PLANETARY CARTOGRAPHY",
        "points": [
            "Anchored to USGS Jezero Crater 20m CTX Digital Terrain Model (SHA-256: 875e7e... verified).",
            "Zero synthetic topography: surface routing is strictly confined to surveyed elevations.",
            "Horn 8-neighborhood convolution kernel computes true terrain gradient vectors:",
            "Operational slope ceilings enforced: robotic rovers <= 15.0 deg, crew analogues <= 20.0 deg."
        ],
        "image": "09_phase_02_site_selection_delta.png",
        "metrics": [("SURVEY AREA", "25 sq km"), ("BEARING CAP", "185.0 kPa"), ("MAX SLOPE", "4.2 deg (Delta Floor)")]
    },
    {
        "num": 5,
        "title": "High-Level Intent & 7-Phase Mission DAG",
        "subtitle": "Autonomous Mission Compilation from Natural Language Objectives",
        "tag": "MISSION ORCHESTRATION",
        "points": [
            "Input: High-level intent ('Establish research settlement in Jezero, investigate Delta Scarp').",
            "Compiler synthesizes topologically sorted 7-phase Directed Acyclic Graph with 42 tasks.",
            "Each task carries explicit resource prerequisites, asset lease requirements, and deadlines.",
            "Acyclic dependency guarantee eliminates runtime deadlocks and circular blocking."
        ],
        "image": "03_mission_compilation_7_phases.png",
        "metrics": [("PHASES", "7 Major Phases"), ("TASKS", "42 Compiled Tasks"), ("SOL HORIZON", "60 Sols")]
    },
    {
        "num": 6,
        "title": "Heterogeneous Fleet Operations",
        "subtitle": "Ground Rovers, Autonomous Rotorcraft & Construction Robots",
        "tag": "ROBOTICS & ASSET LOGISTICS",
        "points": [
            "Heterogeneous fleet: ATLAS-ROVER-01 (heavy traversal), HEXACOPTER-02 (aerial scout), CONSTRUCTION-BOT-01.",
            "Single-lease asset allocation protocol prevents task double-booking and resource races.",
            "Ground velocity modeled at engineering drive speeds (0.035 m/s) with power draw accounting.",
            "Coordinated sorties: hexacopter performs high-elevation reconnaissance before rover dispatch."
        ],
        "image": "04_heterogeneous_fleet_registry.png",
        "metrics": [("FLEET SIZE", "4 Active Assets"), ("ROVER SPEED", "0.035 m/s"), ("LEASE LOCKS", "Single-Lease Enforced")]
    },
    {
        "num": 7,
        "title": "Martian Rotorcraft Aerodynamics",
        "subtitle": "Momentum Theory & Compressibility Corrections in Thin CO2",
        "tag": "AEROSPACE FLIGHT MECHANICS",
        "points": [
            "Hypsometric density model: rho(z) = rho_0 * exp(-(z - z_0) / H_rho) with H_rho = 11.1 km.",
            "Speed of sound in Martian CO2 (gamma = 1.29, R = 188.9 J/kg-K) at 210 K is a = 226.2 m/s.",
            "At 2,400 RPM and R_blade = 0.60 m, tip velocity V_tip = 150.8 m/s, yielding M_tip = 0.667.",
            "Because M_tip < 0.75, rotor operates in subsonic regime, avoiding transonic shock stall."
        ],
        "image": "04_heterogeneous_fleet_registry.png",
        "metrics": [("SPEED OF SOUND", "226.2 m/s"), ("BLADE TIP MACH", "0.667 (< 0.75)"), ("CEILING", "Subsonic Regime")]
    },
    {
        "num": 8,
        "title": "Active Learning & Scientific Discovery",
        "subtitle": "Bayesian Hypothesis Testing over Jezero Geological Features",
        "tag": "PLANETARY SCIENCE",
        "points": [
            "Formulates scientific discovery via Bayesian active learning with likelihood ratio odds updating:",
            "Hypotheses target Delta Scarp lacustrine clays (HYP-01) and Seitah olivine cumulates (HYP-02).",
            "PIXL XRF spectrometer and multispectral reflectance observations ingested dynamically.",
            "Empirical confirmation declared when posterior probability reaches P(H|E) >= 0.95 (95.0%)."
        ],
        "image": "06_bayesian_science_hypotheses_ledger.png",
        "metrics": [("HYPOTHESES", "4 Canonical"), ("LIKELIHOOD RATIO", "Lambda = 8.5"), ("POSTERIOR", "94.0% Delta Scarp")]
    },
    {
        "num": 9,
        "title": "Shannon Information Theory in Planetary Science",
        "subtitle": "Quantifying Epistemic Uncertainty Reduction in Bits",
        "tag": "INFORMATION GAIN",
        "points": [
            "Information entropy computed as H(p) = - [p log2 p + (1-p) log2(1-p)] bits.",
            "Information Gain Delta I measures the exact reduction in epistemic uncertainty.",
            "Delta Scarp observation ingestion drops entropy from 0.934 bits to 0.327 bits.",
            "Yields a net scientific return of +0.607 bits of empirical information gain."
        ],
        "image": "13_phase_08_bayesian_discovery_delta.png",
        "metrics": [("PRIOR ENTROPY", "0.934 bits"), ("POSTERIOR ENTROPY", "0.327 bits"), ("INFO GAIN", "+0.607 bits")]
    },
    {
        "num": 10,
        "title": "Deep-Space Autonomy & Interplanetary Delay",
        "subtitle": "Bounded Autonomy, State-Hash Gating & Idempotent Command Rings",
        "tag": "DEEP SPACE COMMUNICATIONS",
        "points": [
            "Explicit discrete-event simulation of One-Way Light-Time (OWLT: 14.2 min) propagation.",
            "Inbound Earth commands carry expected state signature H_expected for validation.",
            "If local Martian state has diverged upon arrival, command is rejected (REJECTED_STALE_HASH).",
            "Cryptographic command hash ring deduplicates retransmitted packets, preventing duplicate actuation."
        ],
        "image": "05_interplanetary_owlt_rf_telemetry.png",
        "metrics": [("OWLT DELAY", "14.2 minutes"), ("STALE REJECTION", "100% Enforced"), ("IDEMPOTENCY", "Deduplicated")]
    },
    {
        "num": 11,
        "title": "Base Power Grid: Nuclear & Solar Architecture",
        "subtitle": "NASA Kilopower Fission Baseline & Secondary Solar Arrays",
        "tag": "SETTLEMENT SYSTEMS",
        "points": [
            "Primary power: 40 kWe Kilopower KRUSTY-class Stirling fission reactor (continuous baseline).",
            "Secondary power: Solar PV array subject to atmospheric optical depth attenuation (tau).",
            "Lithium-ion battery storage buffer with dynamic state-of-charge (SOC %) modeling.",
            "Power allocator prioritizes critical thermal life-support heating over industrial ISRU."
        ],
        "image": "10_phase_03_kilopower_reactor_sizing.png",
        "metrics": [("KILOPOWER RATING", "40.0 kWe net"), ("SOLAR GRID", "Variable insolation"), ("BATTERY BUFFER", "250 kWh")]
    },
    {
        "num": 12,
        "title": "Chemical ISRU & Closed Stoichiometry",
        "subtitle": "Solid Oxide Electrolysis (MOXIE) & Sabatier Methanation",
        "tag": "CHEMICAL ENGINEERING",
        "points": [
            "Solid Oxide Electrolysis: 2 CO2 -> 2 CO + O2 (88.02 g CO2 -> 56.02 g CO + 32.00 g O2; dm = 0.000 g).",
            "Sabatier Methanation: CO2 + 4 H2 -> CH4 + 2 H2O (52.07 g reactants -> 52.07 g products).",
            "Closed conservation ledger satisfies dM = |M_final - (M_init + M_in - M_out)| <= 1e-4 kg.",
            "Water and oxygen extraction rates dynamically track crew and fuel requirements."
        ],
        "image": "07_closed_loop_isru_power_hud.png",
        "metrics": [("SOXE O2 YIELD", "32.00 g / 2mol"), ("SABATIER CH4", "16.04 g / mol"), ("MASS ERROR", "0.000000 kg")]
    },
    {
        "num": 13,
        "title": "Regolith Microwave Sintering & Construction",
        "subtitle": "Manufacturing Structural Radiation Berm Blocks",
        "tag": "INFRASTRUCTURE DEVELOPMENT",
        "points": [
            "Microwave sintering consumes 1.4 kWh per 20 kg basaltic block (70 kWh/tonne).",
            "Industrial sintering line draws 28.0 kWe, producing 20 blocks/hour under nominal power.",
            "Manufactured 420 structural blocks for habitat radiation shielding and landing pad berms.",
            "Construction bot excavates regolith feedstock in strict mass equilibrium."
        ],
        "image": "16_phase_10_regolith_sintering_blocks.png",
        "metrics": [("BLOCK MASS", "20.0 kg/block"), ("ENERGY DRAW", "1.4 kWh/block"), ("BLOCKS SINTERED", "420 Produced")]
    },
    {
        "num": 14,
        "title": "Fault Injection: Sol 48 Convective Dust Storm",
        "subtitle": "Cascading Failures & Extreme Atmospheric Obscuration",
        "tag": "MISSION ASSURANCE",
        "points": [
            "Severe regional dust storm injected at Sol 48: atmospheric optical depth tau surges from 0.45 to 2.80.",
            "Direct solar insolation collapses from 480 W/m2 to 120 W/m2, creating severe power deficit.",
            "Battery state-of-charge depletion rate exceeds safety threshold (> 5.0%/hour).",
            "How does the autonomous operating system respond without Earth intervention?"
        ],
        "image": "14_phase_09_contingency_dust_storm.png",
        "metrics": [("OPTICAL DEPTH", "tau = 2.80"), ("SOLAR FLUX DROP", "75.0% Collapse"), ("EVENT TIME", "Sol 48.0")]
    },
    {
        "num": 15,
        "title": "Autonomous Load-Shedding & FDIR Recovery",
        "subtitle": "Preserving Life-Support Thermal Margins During Deficits",
        "tag": "SYSTEMS RESILIENCE",
        "points": [
            "Autonomous FDIR detects electrical deficit and triggers automated load-shedding hierarchy.",
            "Cuts non-essential 28.0 kWe microwave sintering line within 1 Sol of event onset.",
            "Preserves base thermal life support: habitat core holds steady at 294.15 K (+21 deg C).",
            "Downstream construction tasks in the mission DAG are safely paused until optical depth normalizes."
        ],
        "image": "15_phase_09_autonomous_load_shedding.png",
        "metrics": [("LOAD SHED", "28.0 kWe Sintering"), ("HABITAT CORE TEMP", "294.15 K (+21 C)"), ("CREW SAFETY", "Sustained")]
    },
    {
        "num": 16,
        "title": "Closed Mass & Energy Accounting Ledger",
        "subtitle": "Rigorous Reconciliation Across a 60-Sol Mission Horizon",
        "tag": "PHYSICAL CONSERVATION",
        "points": [
            "Tracks all inputs, generation, consumption, and venting across the 60-Sol flagship run.",
            "Water storage: 500 kg initial + 3,960.5 kg harvested - 1,020.0 kg consumed = 3,440.50 kg reserve.",
            "Oxygen storage: 350 kg initial + 1,627.35 kg extracted - 740.0 kg consumed = 1,237.35 kg reserve.",
            "Net cumulative mass discrepancy across all physical phases: exactly 0.000000 kg."
        ],
        "image": "17_phase_11_closed_mass_energy_balance.png",
        "metrics": [("FINAL WATER", "3,440.50 kg"), ("FINAL OXYGEN", "1,237.35 kg"), ("NET DISCREPANCY", "0.000000 kg")]
    },
    {
        "num": 17,
        "title": "Deterministic Replay & SHA-256 Merkle Chain",
        "subtitle": "Eliminating Simulation Non-Determinism via Cryptographic Hashing",
        "tag": "REPRODUCIBILITY",
        "points": [
            "Continuous SHA-256 Merkle hash chain calculated across all 61 timeline snapshots.",
            "Clean-room replay from pristine memory produces identical root hash:",
            "Root Hash: f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14.",
            "Controlled 20 kWe reactor throttle perturbation produces explainable divergent hash (c34011...)."
        ],
        "image": "19_cryptographic_replay_hash_chain.png",
        "metrics": [("SNAPSHOTS", "61 Steps"), ("ROOT HASH", "f9d124...bd14"), ("REPLAY STATUS", "BIT-EXACT MATCH")]
    },
    {
        "num": 18,
        "title": "Complete Verification Battery Results",
        "subtitle": "1,126 Automated Tests, Preflight Checks & Adversarial Gauntlets",
        "tag": "QUALITY ASSURANCE",
        "points": [
            "1,126 / 1,126 repository tests passed (100.0%) with zero failures in 183.94s.",
            "20 / 20 dedicated adversarial tests passed (Challenges A through L: corrupt packets, comm blackouts).",
            "12 / 12 preflight diagnostic checkpoints verified in 366.7 ms on port 3000.",
            "20 / 20 CDP browser showcase screenshots captured across 1920x1080 and 1366x768 viewports."
        ],
        "image": "18_phase_12_phase_f_readiness_100pct.png",
        "metrics": [("REPO TESTS", "1,126 / 1,126 (100%)"), ("ADVERSARIAL", "20 / 20 PASS"), ("PREFLIGHT", "12 / 12 (366ms)")]
    },
    {
        "num": 19,
        "title": "Scientific Boundaries & Honest Limitations",
        "subtitle": "Transparent Epistemic Disclosures for Independent Reviewers",
        "tag": "SCIENTIFIC INTEGRITY",
        "points": [
            "Research Software Only: Atlas is an academic simulation framework; not operational flight software.",
            "No Human Safety Certification: Traversal routes and life support do not certify astronaut spaceflight safety.",
            "Point-Mass Dynamics: Rotorcraft model uses 3-DOF momentum theory without non-linear blade aeroelasticity.",
            "Stoichiometric ISRU: Assumes nominal catalytic conversion yields without dynamic catalyst poisoning."
        ],
        "image": "11_phase_06_habitat_pressurization.png",
        "metrics": [("CLASSIFICATION", "Research Software"), ("FLIGHT STATUS", "Non-Flight-Certified"), ("SAFETY CLAIMS", "0 (None)")]
    },
    {
        "num": 20,
        "title": "Conclusion & One-Command Flagship Reproduction",
        "subtitle": "Open-Source Research Software Release Ready for Independent Review",
        "tag": "SUMMARY & ACCESS",
        "points": [
            "Project Atlas unifies cartography, robotics, active science, and ISRU into a reproducible operating system.",
            "Complete open-source release: source code, Draft 2020-12 data schemas, tests, and documentation.",
            "One-Command Reproduction: python scripts/run_flagship_mission.py",
            "Review Evidence Dashboard available locally at http://127.0.0.1:3000/api/review-evidence."
        ],
        "image": "20_tactical_laptop_responsive_layout_1366x768.png",
        "metrics": [("RELEASE", "Preview 1.0"), ("REPRO COMMAND", "run_flagship_mission.py"), ("LICENSE", "Permissive / Open Data")]
    }
]

def build_pdf_presentation():
    slides_html = ""
    for s in SLIDES_DATA:
        img_path = SHOWCASE_DIR / s["image"]
        img_b64 = ""
        if img_path.exists():
            with open(img_path, "rb") as f:
                img_b64 = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
        
        pts_html = "".join(f"<li>{pt}</li>" for pt in s["points"])
        metrics_html = "".join(
            f'<div class="metric-card"><div class="m-label">{m[0]}</div><div class="m-val">{m[1]}</div></div>'
            for m in s["metrics"]
        )

        slides_html += f"""
        <div class="slide">
          <div class="slide-header">
            <div class="slide-num">SLIDE {s['num']:02d} / 20</div>
            <div class="slide-tag">{s['tag']}</div>
          </div>
          <div class="slide-title">{s['title']}</div>
          <div class="slide-subtitle">{s['subtitle']}</div>
          <div class="slide-body">
            <div class="slide-left">
              <ul class="points-list">
                {pts_html}
              </ul>
              <div class="metrics-row">
                {metrics_html}
              </div>
            </div>
            <div class="slide-right">
              <div class="img-wrapper">
                <img src="{img_b64}" alt="{s['title']}">
              </div>
            </div>
          </div>
          <div class="slide-footer">
            <span>PROJECT ATLAS &middot; MARSWALK 2.0 &middot; RESEARCH PREVIEW 1.0</span>
            <span>ACADEMIC RESEARCH SIMULATION SOFTWARE &middot; NON-FLIGHT-CERTIFIED</span>
          </div>
        </div>
        """

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Project Atlas Conference Presentation</title>
<style>
@page {{
  size: 16in 9in;
  margin: 0;
}}
body {{
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
  background: #060b12;
  color: #e6edf3;
}}
.slide {{
  width: 16in;
  height: 9in;
  box-sizing: border-box;
  padding: 0.6in 0.8in 0.4in 0.8in;
  page-break-after: always;
  display: flex;
  flex-direction: column;
  position: relative;
  background: radial-gradient(circle at 80% 20%, #0e1a2b 0%, #060b12 70%);
  overflow: hidden;
}}
.slide-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.15in;
}}
.slide-num {{
  font-family: monospace;
  font-size: 14pt;
  font-weight: 700;
  color: #00e5ff;
  letter-spacing: 1px;
}}
.slide-tag {{
  font-size: 11pt;
  font-weight: 800;
  letter-spacing: 1.5px;
  background: rgba(0, 229, 255, 0.12);
  color: #00e5ff;
  border: 1px solid rgba(0, 229, 255, 0.4);
  padding: 4px 14px;
  border-radius: 4px;
}}
.slide-title {{
  font-size: 32pt;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 0.08in;
  letter-spacing: -0.5px;
}}
.slide-subtitle {{
  font-size: 16pt;
  font-weight: 500;
  color: #8899a6;
  margin-bottom: 0.35in;
}}
.slide-body {{
  display: flex;
  flex: 1;
  gap: 0.6in;
  align-items: flex-start;
}}
.slide-left {{
  flex: 1.1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}}
.slide-right {{
  flex: 0.9;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}}
.points-list {{
  margin: 0;
  padding-left: 24pt;
  font-size: 15.5pt;
  line-height: 1.55;
  color: #c9d1d9;
}}
.points-list li {{
  margin-bottom: 12pt;
}}
.metrics-row {{
  display: flex;
  gap: 16pt;
  margin-top: 20pt;
}}
.metric-card {{
  background: #091420;
  border: 1px solid #1a2c40;
  padding: 10pt 16pt;
  border-radius: 6pt;
  flex: 1;
}}
.m-label {{
  font-size: 9.5pt;
  font-weight: 700;
  color: #8899a6;
  text-transform: uppercase;
  margin-bottom: 4pt;
}}
.m-val {{
  font-size: 14pt;
  font-weight: 800;
  color: #7ee787;
}}
.img-wrapper {{
  width: 100%;
  max-height: 4.8in;
  border: 1.5px solid #243b55;
  border-radius: 8pt;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.7);
  background: #000;
}}
.img-wrapper img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}}
.slide-footer {{
  display: flex;
  justify-content: space-between;
  font-size: 9pt;
  color: #556677;
  border-top: 1px solid #132030;
  padding-top: 8pt;
  margin-top: 10pt;
  letter-spacing: 0.5px;
}}
</style>
</head>
<body>
{slides_html}
</body>
</html>
"""
    deck_html_path = CONF_DIR / "presentation_deck.html"
    with open(deck_html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"Presentation HTML written to {deck_html_path}")

    pdf_out = CONF_DIR / "Project_Atlas_Research_Presentation.pdf"
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(pdf_out)}",
        f"file:///{str(deck_html_path).replace(chr(92), '/')}"
    ]
    print("Compiling presentation PDF...")
    subprocess.run(cmd, capture_output=True, text=True)
    if pdf_out.exists() and pdf_out.stat().st_size > 1000:
        print(f"SUCCESS: Generated Presentation PDF at {pdf_out} ({pdf_out.stat().st_size} bytes)")
    else:
        print(f"FAILED to generate presentation PDF")


def xml_escape(text: str) -> str:
    """Escapes special characters for XML."""
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_pptx_presentation():
    """Builds a compliant OpenXML .pptx presentation file containing all 20 slides."""
    pptx_path = CONF_DIR / "Project_Atlas_Research_Presentation.pptx"
    
    # We construct the OpenXML ZIP structure
    with zipfile.ZipFile(pptx_path, "w", zipfile.ZIP_DEFLATED) as z:
        # [Content_Types].xml
        content_types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Default Extension="png" ContentType="image/png"/>',
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        ]
        for i in range(1, 21):
            content_types.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
        content_types.append('</Types>')
        z.writestr("[Content_Types].xml", "".join(content_types))

        # _rels/.rels
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""")

        # ppt/_rels/presentation.xml.rels
        pres_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i in range(1, 21):
            pres_rels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')
        pres_rels.append('</Relationships>')
        z.writestr("ppt/_rels/presentation.xml.rels", "".join(pres_rels))

        # ppt/presentation.xml (16:9 widescreen 12192000 x 6858000 EMUs)
        slide_id_list = "".join(f'<p:sldId id="{255+i}" r:id="rId{i}"/>' for i in range(1, 21))
        z.writestr("ppt/presentation.xml", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst/>
  <p:sldIdLst>
    {slide_id_list}
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>""")

        # Build each of the 20 slides
        for i, s in enumerate(SLIDES_DATA, 1):
            img_filename = s["image"]
            img_path = SHOWCASE_DIR / img_filename
            img_rel_id = f"rIdImg{i}"
            
            # Embed image into ppt/media/
            if img_path.exists():
                with open(img_path, "rb") as img_f:
                    z.writestr(f"ppt/media/image{i}.png", img_f.read())
            
            # Slide rels
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="{img_rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image{i}.png"/>
</Relationships>""")

            # Construct slide text paragraphs
            body_p_xml = ""
            for pt in s["points"]:
                escaped_pt = xml_escape(pt)
                body_p_xml += f"""
                <a:p>
                  <a:pPr lvl="0" marL="288000"><a:buFont typeface="Arial"/><a:buChar char="•"/></a:pPr>
                  <a:r>
                    <a:rPr lang="en-US" sz="1500" b="0"><a:solidFill><a:srgbClr val="C9D1D9"/></a:solidFill></a:rPr>
                    <a:t>{escaped_pt}</a:t>
                  </a:r>
                </a:p>"""

            # Slide XML
            escaped_tag = xml_escape(s['tag'])
            escaped_title = xml_escape(s['title'])
            escaped_subtitle = xml_escape(s['subtitle'])
            slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      
      <!-- Background Shape -->
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Background"/><p:cNvSpPr><a:spLocks noSelect="1"/></p:cNvSpPr><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm>
          <a:solidFill><a:srgbClr val="060B12"/></a:solidFill>
          <a:ln><a:noFill/></a:ln>
        </p:spPr>
      </p:sp>

      <!-- Slide Title & Tag -->
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="TitleBox"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="685800" y="457200"/><a:ext cx="10820400" cy="1143000"/></a:xfrm></p:spPr>
        <p:txBody>
          <a:bodyPr rtlCol="0" anchor="top"/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr lang="en-US" sz="1100" b="1"><a:solidFill><a:srgbClr val="00E5FF"/></a:solidFill></a:rPr>
              <a:t>SLIDE {s['num']:02d} / 20 &#183; {escaped_tag}</a:t>
            </a:r>
          </a:p>
          <a:p>
            <a:r>
              <a:rPr lang="en-US" sz="2600" b="1"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a:rPr>
              <a:t>{escaped_title}</a:t>
            </a:r>
          </a:p>
          <a:p>
            <a:r>
              <a:rPr lang="en-US" sz="1300" b="0"><a:solidFill><a:srgbClr val="8899A6"/></a:solidFill></a:rPr>
              <a:t>{escaped_subtitle}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>

      <!-- Content Text Box (Left) -->
      <p:sp>
        <p:nvSpPr><p:cNvPr id="4" name="ContentBox"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="685800" y="1828800"/><a:ext cx="5486400" cy="4572000"/></a:xfrm></p:spPr>
        <p:txBody>
          <a:bodyPr rtlCol="0" anchor="top"/>
          <a:lstStyle/>
          {body_p_xml}
        </p:txBody>
      </p:sp>

      <!-- Embedded Image (Right) -->
      <p:pic>
        <p:nvPicPr><p:cNvPr id="5" name="ShowcaseImg"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
        <p:blipFill>
          <a:blip r:embed="{img_rel_id}"/>
          <a:stretch><a:fillRect/></a:stretch>
        </p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="6400800" y="1828800"/><a:ext cx="5105400" cy="4343400"/></a:xfrm>
          <a:ln w="19050"><a:solidFill><a:srgbClr val="243B55"/></a:solidFill></a:ln>
        </p:spPr>
      </p:pic>

    </p:spTree>
  </p:cSld>
</p:sld>"""
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml)

    print(f"SUCCESS: Generated PPTX at {pptx_path} ({pptx_path.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf_presentation()
    build_pptx_presentation()
