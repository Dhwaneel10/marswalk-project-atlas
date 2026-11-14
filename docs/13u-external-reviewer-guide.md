# Milestone 13U: External Research Reviewer Guide

**Project:** Project Atlas / MarsWalk 2.0  
**Target Audience:** Independent University Researchers, Planetary Scientists & Aerospace Verification Engineers  
**Classification:** Research Software Evaluation Package (Non-Flight-Certified)

---

## 1. Quick-Start Reproducibility Instructions

An external reviewer can reproduce the entire platform from a clean Python 3.12 environment with four shell commands:

```bash
# 1. Clone or navigate to the repository root
cd E:\Python\NASA-Spaceapps\Marswalk

# 2. Activate Python virtual environment and set PYTHONPATH
source .venv/Scripts/activate     # Windows PowerShell: .\.venv\Scripts\Activate.ps1
export PYTHONPATH=src            # Windows PowerShell: $env:PYTHONPATH='src'

# 3. Execute the full repository verification test suite (1,096 tests)
python -m pytest -q

# 4. Launch the Atlas Mission OS daemon on localhost port 3000
python scripts/run_atlas.py --port 3000 --no-browser
```

To run the flagship 60-Sol campaign `ATLAS-MARS-BASE-ALPHA-001` directly from CLI:
```bash
python -c "
import urllib.request, json
res = urllib.request.urlopen('http://127.0.0.1:3000/api/mission-os/flagship/run')
data = json.loads(res.read().decode())
print('Phase F Readiness Score:', data['dossier']['phase_f_readiness_score'])
print('Root Hash:', data['dossier']['root_hash'])
"
```

---

## 2. Remote-Sensing Data Provenance

All spatial, elevation, and terrain calculations originate from verified NASA/USGS primary sources:
- **Terrain DTM:** USGS Jezero Crater Digital Terrain Model (20 m spatial resolution).
  - Path: `data/terrain/usgs_jezero_20m.tif`
  - SHA-256 Hash: `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`
- **Surface Imagery:** High-resolution CTX optical orthomosaic covering $5.0 \times 5.0\text{ km}$ study zone.
- **Atmospheric Climate Data:** NASA PDS4 archived MEDA observations from the Perseverance rover at Octavia E. Butler Landing.

---

## 3. Epistemic Guardrails & Known Limitations

To maintain scientific integrity, external reviewers should note the following bounded assumptions:
1. **Simulation vs Spaceflight Reality:** Model outputs are computational research heuristics; they do not certify operational spaceflight safety for human astronauts.
2. **Point-Mass Aerodynamics:** Rotorcraft flight dynamics use 3-DOF point-mass momentum theory with compressibility drag corrections; they do not model full non-linear blade aeroelastic flutter.
3. **Local Regolith Homogeneity:** Sintering energy assumes bulk basaltic regolith properties; regional dielectric variations may alter real microwave penetration depths.
4. **Deterministic Gauntlets:** The evaluated scenarios represent explicitly tested failure configurations rather than empirical physical probability distributions.
