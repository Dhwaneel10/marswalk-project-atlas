"""
API tests for Milestone 12C: Route Decision Workbench & Terrain Intelligence API.
Validates POST /api/route/terrain-analysis and POST /api/route/profile endpoints against
live Atlas server or in-memory service.
"""

import json
import pytest
import urllib.request
import urllib.error

ATLAS_BASE_URL = "http://127.0.0.1:3000"


def _post_json(endpoint: str, payload: dict) -> dict:
    url = f"{ATLAS_BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_api_route_terrain_analysis_with_path():
    # Provide a simple 10-step path in Jezero Crater basin
    path = [[120, 120 + i] for i in range(10)]
    payload = {
        "path": path,
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "route_id": "api-test-leg-1",
    }
    res = _post_json("/api/route/terrain-analysis", payload)

    assert res["status"] == "ok"
    assert "analysis" in res
    anl = res["analysis"]
    assert anl["route_id"] == "api-test-leg-1"
    assert anl["profile"] == "conservative"
    assert anl["vehicle_mode"] == "crew_eva"
    assert "terrain_profile" in anl
    assert anl["terrain_profile"]["sample_count"] == 10
    assert anl["terrain_profile"]["total_distance_m"] > 0
    assert "cost_decomposition" in anl
    assert anl["cost_decomposition"]["is_strictly_reconciled"] is True
    assert "slope_distribution" in anl
    assert "segments" in anl
    assert len(anl["decision_explanations"]) > 0


def test_api_route_terrain_analysis_onthefly_plan():
    # Let server plan from start to goal
    payload = {
        "start": [120, 120],
        "goal": [125, 125],
        "profile": "conservative",
    }
    res = _post_json("/api/route/terrain-analysis", payload)

    assert res["status"] == "ok"
    assert "analysis" in res
    anl = res["analysis"]
    assert anl["terrain_profile"]["sample_count"] >= 2
    assert anl["terrain_profile"]["data_completeness_pct"] == 100.0


def test_api_route_terrain_analysis_with_comparison():
    # Compare with science_first profile
    payload = {
        "start": [120, 120],
        "goal": [130, 130],
        "profile": "conservative",
        "compare_with_profile": "science_first",
    }
    res = _post_json("/api/route/terrain-analysis", payload)

    assert res["status"] == "ok"
    assert "analysis" in res
    assert "comparison" in res
    comp = res["comparison"]
    assert "deltas" in comp
    assert "metrics_table" in comp
    assert len(comp["tradeoff_narratives"]) > 0


def test_api_route_profile_alias():
    path = [[120, 120 + i] for i in range(5)]
    payload = {"path": path}
    res = _post_json("/api/route/profile", payload)

    assert res["status"] == "ok"
    assert "analysis" in res
    assert res["analysis"]["terrain_profile"]["sample_count"] == 5


def test_api_route_terrain_analysis_validation_error():
    # Send empty payload
    url = f"{ATLAS_BASE_URL}/api/route/terrain-analysis"
    req = urllib.request.Request(
        url,
        data=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)

    assert exc_info.value.code in (400, 422)
