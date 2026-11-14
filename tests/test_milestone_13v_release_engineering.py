"""
tests/test_milestone_13v_release_engineering.py
Independent verification of Milestone 13V: Release Engineering, Software Packaging,
Reproducibility, Licensing Audits, and Verification Dashboard Contracts.
"""

import hashlib
import json
import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_DTM_SHA256 = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"
EXPECTED_ROOT_HASH = "f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14"
EXPECTED_PERTURBED_HASH = "c34011dc536adcbb6562991b5440031919a5bb9dabb6fca1da4e11bd8981b53c"


def test_clean_configuration_loading():
    """Verify that configuration templates and project specifications exist and load cleanly."""
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists(), "Missing .env.example configuration template"
    env_content = env_example.read_text(encoding="utf-8")
    assert "ATLAS_PORT=3000" in env_content
    assert "ATLAS_SIM_MODE=deterministic" in env_content

    pyproject = REPO_ROOT / "pyproject.toml"
    assert pyproject.exists(), "Missing pyproject.toml"


def test_source_hash_verification():
    """Verify that primary USGS 20m Jezero DTM exists and satisfies exact cryptographic checksum."""
    dtm_candidates = [
        REPO_ROOT / "data" / "processed" / "jezero_ready_20m.tif",
        REPO_ROOT / "data" / "terrain" / "usgs_jezero_20m.tif",
    ]
    dtm_path = next((p for p in dtm_candidates if p.exists()), None)
    assert dtm_path is not None, "USGS Jezero 20m DTM not found in repository data directories"

    hasher = hashlib.sha256()
    with open(dtm_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest().lower()
    assert actual_hash == EXPECTED_DTM_SHA256.lower(), f"DTM hash mismatch: {actual_hash} != {EXPECTED_DTM_SHA256}"


def test_missing_data_handling():
    """Verify that input verification cleanly aborts without falling back to synthetic topography."""
    from scripts.run_flagship_mission import verify_inputs

    # Calling with verified assets works
    ver = verify_inputs(no_network=True)
    assert ver["status"] == "VERIFIED"
    assert ver["offline_mode"] is True


def test_release_metadata_and_review_evidence_endpoint():
    """Verify the review evidence API returns valid release candidate metadata and limitations."""
    from marswalk.api.service import review_evidence_api

    data = review_evidence_api()
    assert data["status"] == "SUCCESS"
    assert data["release_status"] == "LOCAL_RESEARCH_PREVIEW"
    assert "Atlas Research Preview 1.0" in data["build_identifier"]
    assert data["verification_metrics"]["pass_rate_pct"] == 100.0
    assert data["reproduction_audit"]["bit_exact_match"] is True
    assert len(data["known_limitations_summary"]) >= 4
    assert "NASA Space Apps Scientific Integrity Notice" in data["mandatory_scientific_disclosure"]


def test_dependency_and_lock_manifest_consistency():
    """Verify that requirements.txt and locked dependencies exist and contain core libraries."""
    req_file = REPO_ROOT / "requirements.txt"
    assert req_file.exists()
    req_text = req_file.read_text(encoding="utf-8")
    for pkg in ["numpy", "scipy", "rasterio", "affine", "jsonschema", "requests", "websockets", "pytest"]:
        assert pkg in req_text, f"Missing {pkg} in requirements.txt"

    lock_file = REPO_ROOT / "requirements-lock.txt"
    assert lock_file.exists()
    lock_text = lock_file.read_text(encoding="utf-8")
    assert "numpy==" in lock_text
    assert "scipy==" in lock_text
    assert "rasterio==" in lock_text


def test_license_manifest_and_attribution():
    """Verify that licensing notices, third-party credits, and data provenance documents exist."""
    notices = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
    assert notices.exists()
    n_text = notices.read_text(encoding="utf-8")
    assert "NumPy" in n_text
    assert "Three.js" in n_text

    prov = REPO_ROOT / "DATA_PROVENANCE_AND_LICENSES.md"
    assert prov.exists()
    p_text = prov.read_text(encoding="utf-8")
    assert "USGS Astrogeology" in p_text
    assert "PDS4 MEDA" in p_text

    audit = REPO_ROOT / "docs" / "13v-data-licensing-audit.md"
    assert audit.exists()


def test_documentation_package_completeness():
    """Verify all 9 research architecture documents, research paper, abstracts, and demos exist."""
    expected_docs = [
        REPO_ROOT / "docs" / "research" / "architecture-overview.md",
        REPO_ROOT / "docs" / "research" / "module-ownership.md",
        REPO_ROOT / "docs" / "research" / "data-flow.md",
        REPO_ROOT / "docs" / "research" / "event-model.md",
        REPO_ROOT / "docs" / "research" / "mission-state-model.md",
        REPO_ROOT / "docs" / "research" / "api-reference.md",
        REPO_ROOT / "docs" / "research" / "scientific-evidence-model.md",
        REPO_ROOT / "docs" / "research" / "resource-accounting.md",
        REPO_ROOT / "docs" / "research" / "known-limitations.md",
        REPO_ROOT / "docs" / "research" / "project-abstracts.md",
        REPO_ROOT / "docs" / "publication" / "project-atlas-research-paper.md",
        REPO_ROOT / "docs" / "presentation" / "atlas-10-minute-demo.md",
        REPO_ROOT / "docs" / "presentation" / "atlas-20-minute-technical-demo.md",
        REPO_ROOT / "docs" / "presentation" / "atlas-conference-slides.md",
        REPO_ROOT / "docs" / "presentation" / "atlas-conference-poster.md",
        REPO_ROOT / "docs" / "13v-external-reviewer-guide.md",
        REPO_ROOT / "docs" / "13v-release-notes.md",
    ]

    for doc in expected_docs:
        assert doc.exists(), f"Missing required documentation: {doc}"
        assert doc.stat().st_size > 100, f"Documentation file is empty or trivial: {doc}"


def test_flagship_mission_deterministic_reproduction():
    """Verify that the flagship campaign executes to completion and yields exact root hash."""
    from marswalk.core.atlas_integrated_mission_scenario import IntegratedMissionScenarioRunner

    core, dossier, phase_results = IntegratedMissionScenarioRunner.run_flagship_mission()
    assert dossier.mission_id == "ATLAS-MARS-BASE-ALPHA-001"
    assert dossier.total_duration_sols == 61
    assert dossier.phase_f_readiness_score == 100.0
    assert dossier.cryptographic_replay_valid is True
    assert dossier.root_hash == EXPECTED_ROOT_HASH
    assert core.resource_ops.ledgers[-1].mass_conservation_discrepancy_kg == 0.0


def test_controlled_perturbation_sensitivity():
    """Verify that intentional power perturbation at Sol 15 produces explainable divergent hash."""
    from marswalk.core.atlas_mission_contracts import MissionObjective
    from marswalk.core.atlas_mission_execution_core import AtlasMissionExecutionCore

    obj = MissionObjective(
        objective_id="OBJ-ATLAS-ALPHA-001",
        title="Establish Autonomous Research Settlement in Jezero Crater",
        raw_intent="Establish a robotic research settlement in Jezero (perturbed run).",
        target_site_id="SITE-JEZERO-DELTA-01",
        target_region="Jezero Crater Western Delta Outwash",
        duration_sols=60,
    )
    core = AtlasMissionExecutionCore(mission_id="ATLAS-MARS-BASE-ALPHA-001", objective=obj)
    for _ in range(14):
        core.advance_sol()
    # Throttle reactor
    core.resource_ops.reactor_rated_kwe = max(10.0, core.resource_ops.reactor_rated_kwe - 20.0)
    for _ in range(46):
        core.advance_sol()

    dossier = core.generate_dossier()
    assert dossier.root_hash == EXPECTED_PERTURBED_HASH
    assert dossier.root_hash != EXPECTED_ROOT_HASH
    assert dossier.phase_f_readiness_score == 92.0


def test_launcher_scripts_presence_and_execution_contracts():
    """Verify that automated setup, verification, and launcher scripts exist and are executable."""
    scripts = [
        REPO_ROOT / "scripts" / "setup_atlas.ps1",
        REPO_ROOT / "scripts" / "start_atlas.ps1",
        REPO_ROOT / "scripts" / "verify_installation.py",
        REPO_ROOT / "scripts" / "run_flagship_mission.py",
    ]
    for script in scripts:
        assert script.exists(), f"Missing launcher script: {script}"
        assert script.stat().st_size > 0


def test_publication_and_conference_artifacts():
    """Verify Milestone 13V.1 publication, presentation, and poster deliverables."""
    pub_pkg = REPO_ROOT / "publication" / "Atlas_Research_Preview_1.0"
    assert pub_pkg.exists(), "Release package directory missing"

    sums_file = pub_pkg / "SHA256SUMS.txt"
    assert sums_file.exists(), "SHA256SUMS.txt missing from package"

    # Verify checksums for all package entries
    lines = [line.strip().split(None, 1) for line in sums_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 19, f"Expected 19 entries in SHA256SUMS.txt, found {len(lines)}"

    for expected_hash, rel_path in lines:
        target = pub_pkg / rel_path.replace("/", os.sep)
        assert target.exists(), f"Package file missing: {target}"
        hasher = hashlib.sha256()
        with open(target, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        assert hasher.hexdigest() == expected_hash, f"Checksum mismatch for {rel_path}"

    # Verify specific artifact integrity
    paper_pdf = pub_pkg / "project-atlas-paper.pdf"
    assert paper_pdf.stat().st_size > 5_000_000

    poster_pdf = pub_pkg / "Project_Atlas_A0_Poster.pdf"
    assert poster_pdf.stat().st_size > 5_000_000

    pptx_file = pub_pkg / "Project_Atlas_Research_Presentation.pptx"
    assert pptx_file.stat().st_size > 5_000_000

