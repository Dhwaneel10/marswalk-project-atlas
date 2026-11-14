"""
scripts/assemble_release_package.py
Assembles the complete publication and reviewer release package in publication/Atlas_Research_Preview_1.0/
and generates the SHA-256 cryptographic manifest.
"""

import hashlib
import os
import shutil
from pathlib import Path

REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
PKG_DIR = REPO_ROOT / "publication" / "Atlas_Research_Preview_1.0"
PKG_DIR.mkdir(parents=True, exist_ok=True)

# 1. Copy Research Paper PDF & LaTeX sources
paper_pdf = REPO_ROOT / "publication" / "project-atlas" / "project-atlas-paper.pdf"
shutil.copy2(paper_pdf, PKG_DIR / "project-atlas-paper.pdf")

latex_src_dir = PKG_DIR / "latex_source"
latex_src_dir.mkdir(exist_ok=True)
shutil.copy2(REPO_ROOT / "publication" / "project-atlas" / "main.tex", latex_src_dir / "main.tex")
shutil.copy2(REPO_ROOT / "publication" / "project-atlas" / "references.bib", latex_src_dir / "references.bib")

latex_fig_dir = latex_src_dir / "figures"
if latex_fig_dir.exists():
    shutil.rmtree(latex_fig_dir)
shutil.copytree(REPO_ROOT / "publication" / "project-atlas" / "figures", latex_fig_dir)

# 2. Copy Conference Presentation Deck (PPTX & PDF)
conf_pptx = REPO_ROOT / "publication" / "conference" / "Project_Atlas_Research_Presentation.pptx"
shutil.copy2(conf_pptx, PKG_DIR / "Project_Atlas_Research_Presentation.pptx")

conf_pdf = REPO_ROOT / "publication" / "conference" / "Project_Atlas_Research_Presentation.pdf"
shutil.copy2(conf_pdf, PKG_DIR / "Project_Atlas_Research_Presentation.pdf")

# 3. Copy A0 Technical Poster
poster_pdf = REPO_ROOT / "publication" / "poster" / "Project_Atlas_A0_Poster.pdf"
shutil.copy2(poster_pdf, PKG_DIR / "Project_Atlas_A0_Poster.pdf")

# 4. Copy Documentation & Reviewer Guides
shutil.copy2(REPO_ROOT / "docs" / "13v-external-reviewer-guide.md", PKG_DIR / "EXTERNAL_REVIEWER_GUIDE.md")
shutil.copy2(REPO_ROOT / "docs" / "research" / "known-limitations.md", PKG_DIR / "KNOWN_LIMITATIONS.md")
shutil.copy2(REPO_ROOT / "THIRD_PARTY_NOTICES.md", PKG_DIR / "THIRD_PARTY_NOTICES.md")
shutil.copy2(REPO_ROOT / "DATA_PROVENANCE_AND_LICENSES.md", PKG_DIR / "DATA_PROVENANCE_AND_LICENSES.md")

# 5. Create Installation Quickstart & Flagship Reproduction guides
quickstart_txt = """# Project Atlas — Installation Quickstart Guide

Release Identifier: Atlas Research Preview 1.0 (Build 13V-RC1)
Classification: Academic Research Simulation Software (Non-Flight-Certified)

## System Requirements
- Supported OS: Windows 10/11 (64-bit), Linux (Ubuntu 22.04+), macOS (13.0+)
- Python Runtime: Python 3.10+ (Python 3.12 recommended)
- Disk Storage: ~2.5 GB (including USGS CTX DTM raster)
- GPU: Not required (pure CPU numerical modeling & point-mass physics)

## Installation (Windows PowerShell)
```powershell
# 1. Automated environment setup
.\\scripts\\setup_atlas.ps1

# 2. Verify environment, imports, and DTM dataset hash
python scripts/verify_installation.py
```

## Installation (Linux / macOS)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src
python scripts/verify_installation.py
```

## Verification
Executing `scripts/verify_installation.py` checks 26 system health parameters.
All checks must report [PASSED].
"""
with open(PKG_DIR / "QUICKSTART_INSTALLATION.md", "w", encoding="utf-8") as f:
    f.write(quickstart_txt)

reproduction_txt = """# Project Atlas — Flagship Mission Reproduction Guide

Campaign Identifier: ATLAS-MARS-BASE-ALPHA-001
Horizon: 60 Martian Sols across 12 Operational Phases
Target Feature: Jezero Crater Western Delta Outwash

## One-Command Execution
```bash
python scripts/run_flagship_mission.py
```

## Expected Verification Outputs
1. Merkle Root Hash:
   `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`
2. Phase F Readiness Score: 100.0% (QUALIFIED)
3. Net Mass Balance Error: 0.000000 kg (strictly <= 1e-4 kg)
4. Sintered Regolith Blocks: 420 blocks produced
5. Hypotheses Empirically Confirmed: 2 (Delta Scarp & Seitah)

## Offline Verification Mode
```bash
python scripts/run_flagship_mission.py --validate-only
```

## Sensitivity Test (Controlled Power Throttle)
```bash
python scripts/run_flagship_mission.py --perturb-power-kw 20.0 --output-dir data/workspaces/test_perturb
```
Expected Result: Explainable causal divergence to hash `c34011dc536adcbb6562991b5440031919a5bb9dabb6fca1da4e11bd8981b53c` and Readiness 92.0% (DEGRADED).
"""
with open(PKG_DIR / "FLAGSHIP_REPRODUCTION.md", "w", encoding="utf-8") as f:
    f.write(reproduction_txt)

# 6. Generate SHA-256 Manifest
manifest_lines = []
for root, dirs, files in os.walk(PKG_DIR):
    for fname in sorted(files):
        if fname == "SHA256SUMS.txt":
            continue
        fpath = Path(root) / fname
        rel_path = fpath.relative_to(PKG_DIR)
        hasher = hashlib.sha256()
        with open(fpath, "rb") as f_in:
            for chunk in iter(lambda: f_in.read(65536), b""):
                hasher.update(chunk)
        manifest_lines.append(f"{hasher.hexdigest()}  {rel_path.as_posix()}")

manifest_path = PKG_DIR / "SHA256SUMS.txt"
with open(manifest_path, "w", encoding="utf-8") as f_out:
    f_out.write("\n".join(manifest_lines) + "\n")

print(f"Package assembled in {PKG_DIR}")
print(f"Generated SHA256SUMS.txt with {len(manifest_lines)} entries.")
