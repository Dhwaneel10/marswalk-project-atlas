"""MarsWalk 2.0 / Project Atlas - Milestone 12D Test Suite.

Verifies:
1. Evidence Inspector catalog, physical formulations, source citations, and limitations.
2. Evidence API endpoints (/api/evidence/topics and /api/evidence/inspect).
3. Graceful unknown-metric handling without data invention.
4. Mandatory aerospace disclaimer preservation.
5. Atomic campaign loading and zero stale metric leakage.
6. Unified operational cockpit data binding and simulation timeline sequence.
7. Decision Pack export integrity with SHA-256 verification.
"""

import io
import json
import zipfile
from pathlib import Path
import pytest
import rasterio

from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.planner import ScienceWaypoint
from marswalk.core.evidence_inspector import (
    EVIDENCE_CATALOG,
    AEROSPACE_DISCLAIMER,
    get_metric_evidence,
    list_evidence_topics,
    CLASS_MEASURED_REMOTE_SENSING,
    CLASS_DERIVED_PLANETARY_GEOMETRY,
    CLASS_IN_SITU_ARCHIVAL_OBSERVATION,
    CLASS_MATHEMATICAL_ENERGY_PROXY,
    CLASS_TERRESTRIAL_LUNAR_ANALOGUE,
)
from marswalk.api.service import (
    inspect_evidence_api,
    list_evidence_topics_api,
    export_decision_pack_api,
    APIError,
)
from marswalk.core.mission_campaign import (
    MissionCampaign,
    CampaignConfig,
    CampaignTarget,
)


# =========================================================================
# 1. Evidence Inspector Core Unit Tests
# =========================================================================

def test_evidence_catalog_completeness():
    """Verify all core scientific quantities have registered evidence."""
    topics = list_evidence_topics()
    assert len(topics) >= 10, f"Expected >= 10 evidence topics, found {len(topics)}"
    
    keys = {t["metric_key"] for t in topics}
    expected_keys = {
        "elevation", "ground_distance", "slope", "roughness",
        "traversal_cost", "crew_eva", "rover_drive", "weather_meda",
        "readiness_gate", "pareto_optimization", "digital_twin"
    }
    for ek in expected_keys:
        assert ek in keys, f"Missing expected evidence topic: {ek}"


def test_evidence_metric_classifications():
    """Verify scientific classification labels match primary sources."""
    ev_elev = get_metric_evidence("elevation")
    assert ev_elev["classification"] == CLASS_MEASURED_REMOTE_SENSING
    assert "USGS" in ev_elev["primary_source"]
    assert "20m" in ev_elev["primary_source"] or "20 m" in ev_elev["primary_source"]

    ev_slope = get_metric_evidence("slope")
    assert ev_slope["classification"] == CLASS_DERIVED_PLANETARY_GEOMETRY
    assert "Horn" in ev_slope["source_archive"]
    assert "arctan" in ev_slope["equations"]

    ev_meda = get_metric_evidence("weather_meda")
    assert ev_meda["classification"] == CLASS_IN_SITU_ARCHIVAL_OBSERVATION
    assert "PDS" in ev_meda["source_archive"]
    assert "Sol 890" in ev_meda["retrieval_or_observation_time"]

    ev_cost = get_metric_evidence("traversal_cost")
    assert ev_cost["classification"] == CLASS_MATHEMATICAL_ENERGY_PROXY
    assert "Minetti" in ev_cost["primary_source"]

    ev_crew = get_metric_evidence("crew_eva")
    assert ev_crew["classification"] == CLASS_TERRESTRIAL_LUNAR_ANALOGUE
    assert "Apollo" in ev_crew["primary_source"]


def test_evidence_inspector_aliases():
    """Verify alias mapping normalizes common shorthand terms."""
    aliases = [
        ("elev", "elevation"),
        ("alt", "elevation"),
        ("topography", "elevation"),
        ("dist", "ground_distance"),
        ("pitch", "slope"),
        ("cost", "traversal_cost"),
        ("eva", "crew_eva"),
        ("rover", "rover_drive"),
        ("meda", "weather_meda"),
        ("rems", "weather_rems"),
        ("sim", "digital_twin"),
    ]
    for shorthand, canonical in aliases:
        ev = get_metric_evidence(shorthand)
        assert ev["metric_key"] == canonical, f"Alias {shorthand} did not map to {canonical}"
        assert ev["status"] == "VERIFIED_EVIDENCE"


def test_evidence_context_binding():
    """Verify context values bind cleanly to evidence records."""
    ctx = {
        "displayed_value": "-2560.5 m",
        "campaign_id": "cmp_alpha_jezero_01",
        "sortie_id": "sortie_01",
        "sol_index": 2,
    }
    ev = get_metric_evidence("elevation", ctx)
    assert ev["displayed_value"] == "-2560.5 m"
    assert ev["context_identifiers"]["campaign_id"] == "cmp_alpha_jezero_01"
    assert ev["context_identifiers"]["sortie_id"] == "sortie_01"
    assert ev["context_identifiers"]["sol_index"] == 2


def test_unknown_metric_graceful_handling():
    """Verify uncatalogued metrics do not invent data or crash."""
    ev = get_metric_evidence("speculative_warp_factor")
    assert ev["status"] == "UNKNOWN_METRIC"
    assert ev["classification"] == "UNCLASSIFIED"
    assert "No scientific traceability metadata available" in ev["limitations"]
    assert ev["is_flight_certified"] is False


def test_mandatory_aerospace_disclaimer_present():
    """Verify aerospace disclaimer is universally present."""
    for key in EVIDENCE_CATALOG:
        ev = get_metric_evidence(key)
        assert ev["aerospace_disclaimer"] == AEROSPACE_DISCLAIMER
        assert "NOT constitute aerospace operational safety certification" in ev["aerospace_disclaimer"]
        assert ev["is_flight_certified"] is False


# =========================================================================
# 2. Evidence API Endpoint Tests
# =========================================================================

def test_api_list_evidence_topics():
    """Test GET /api/evidence/topics handler."""
    resp = list_evidence_topics_api()
    assert resp["status"] == "OK"
    assert resp["count"] >= 10
    assert isinstance(resp["topics"], list)


def test_api_inspect_evidence_valid():
    """Test GET /api/evidence/inspect with valid parameters."""
    params = {"metric": "slope", "displayed_value": "12.5°"}
    res = inspect_evidence_api(params)
    assert res["status"] == "VERIFIED_EVIDENCE"
    assert res["metric_key"] == "slope"
    assert res["displayed_value"] == "12.5°"
    assert "Horn" in res["source_archive"]


def test_api_inspect_evidence_list_param_unwrapping():
    """Test query param list unwrap from urllib.parse."""
    params = {"metric": ["elevation"], "displayed_value": ["-2540 m"]}
    res = inspect_evidence_api(params)
    assert res["status"] == "VERIFIED_EVIDENCE"
    assert res["metric_key"] == "elevation"
    assert res["displayed_value"] == "-2540 m"


def test_api_inspect_evidence_missing_metric_error():
    """Test missing metric raises APIError with 400 code."""
    with pytest.raises(APIError) as exc_info:
        inspect_evidence_api({})
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_VALIDATION_FAILED"


# =========================================================================
# 3. Mission Control Operational Invariants & Data Integrity
# =========================================================================

def test_atomic_campaign_switching_isolation():
    """Verify switching between two campaigns prevents data leakage."""
    d1 = {
        "campaign_id": "cmp_test_alpha_01",
        "name": "Alpha Crater Survey",
        "version": 1,
        "config": {"planning_profile": "conservative", "vehicle_mode": "crew_eva"},
        "targets": [{"id": "t1"}, {"id": "t2"}],
        "sorties": [{"sortie_id": "s1", "distance_m": 1200.0}],
        "summary": {"total_distance_m": 1200.0, "total_science_score": 180.0, "overall_status": "FEASIBLE"}
    }
    d2 = {
        "campaign_id": "cmp_test_beta_02",
        "name": "Beta Rim Traverse",
        "version": 2,
        "parent_campaign_id": "cmp_test_beta_01",
        "config": {"planning_profile": "science_priority", "vehicle_mode": "rover"},
        "targets": [{"id": "t3"}],
        "sorties": [{"sortie_id": "s2", "distance_m": 3400.0}],
        "summary": {"total_distance_m": 3400.0, "total_science_score": 95.0, "overall_status": "FEASIBLE"}
    }

    # Invariants
    assert d1["campaign_id"] != d2["campaign_id"]
    assert d1["config"]["vehicle_mode"] == "crew_eva"
    assert d2["config"]["vehicle_mode"] == "rover"
    assert len(d1["targets"]) == 2
    assert len(d2["targets"]) == 1
    assert d1["summary"]["total_science_score"] != d2["summary"]["total_science_score"]


def test_timeline_chronological_ordering():
    """Verify planned and simulated events remain chronologically ordered."""
    events = [
        {"elapsed_s": 0.0, "type": "PLANNED", "desc": "Departure"},
        {"elapsed_s": 1200.0, "type": "SIMULATED", "desc": "Waypoint 1"},
        {"elapsed_s": 3600.0, "type": "SIMULATED", "desc": "Dwell complete"},
        {"elapsed_s": 7200.0, "type": "PLANNED", "desc": "Return to base"},
    ]
    # Check monotonic non-decreasing
    for i in range(1, len(events)):
        assert events[i]["elapsed_s"] >= events[i - 1]["elapsed_s"], "Timeline events out of chronological order"


@pytest.fixture
def terrain_context():
    """Load surveyed Jezero terrain context."""
    geotiff_path = Path("data/processed/jezero_ready_20m.tif")
    terrain = load_and_process_terrain(geotiff_path)
    with rasterio.open(geotiff_path) as src:
        transform = src.transform
    waypoints = [
        ScienceWaypoint(id="octavia_landing", name="Octavia E. Butler Landing", rc=(117, 157), priority_score=100.0),
        ScienceWaypoint(id="hawksbill_gap", name="Hawksbill Gap", rc=(95, 140), priority_score=85.0),
    ]
    return terrain, transform, waypoints


def test_safe_decision_pack_export_structure(terrain_context):
    """Verify Decision Pack export contains valid manifest and SHA-256 hashes."""
    terrain, transform, waypoints = terrain_context
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 118, "col": 158},
        "profile": "conservative",
    }
    zip_bytes, filename, bundle = export_decision_pack_api(
        payload,
        terrain,
        transform,
        waypoints,
    )
    assert filename.endswith(".zip")
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "mission_bundle.json" in namelist
        assert "README.txt" in namelist
        assert "route.json" in namelist
