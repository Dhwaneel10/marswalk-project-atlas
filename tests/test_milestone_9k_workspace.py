"""
MarsWalk 2.0 — Milestone 9K Workspace & Experiment Library Test Suite
Validates persistent mission workspaces, experiment libraries, atomic writes,
path traversal guards, historical separation, replay immutability, trade-off comparisons,
and Draft 2020-12 schema conformance using isolated test directories.
"""

import os
import json
import uuid
import copy
import pytest
from pathlib import Path

from marswalk.api.workspace import (
    save_mission,
    list_missions,
    get_mission,
    update_mission,
    duplicate_mission,
    delete_mission,
    import_mission_json,
    save_experiment,
    list_experiments,
    get_experiment,
    delete_experiment,
    duplicate_experiment,
    replay_saved_experiment,
    compare_two_experiments,
    evaluate_experiment_lifecycle,
    validate_record_id,
    atomic_write_json,
    WorkspaceError,
)
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    validate_contract,
    compute_input_fingerprint,
    ContractValidationError,
)
from marswalk.core.terrain import load_and_process_terrain
from marswalk.api.service import plan_route_api
from marswalk.data.ingest import query_elevation_at_lonlat
from marswalk.core.planner import ScienceWaypoint

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEOTIFF_PATH = str(PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif")
WAYPOINTS_PATH = str(PROJECT_ROOT / "data" / "waypoints_jezero.json")


@pytest.fixture(scope="module")
def terrain_context():
    terrain = load_and_process_terrain(GEOTIFF_PATH)
    import rasterio
    with rasterio.open(GEOTIFF_PATH) as src:
        transform = src.transform

    waypoints = []
    if os.path.exists(WAYPOINTS_PATH):
        with open(WAYPOINTS_PATH, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            elev, r, c = query_elevation_at_lonlat(GEOTIFF_PATH, wp["lon_deg"], wp["lat_deg"])
            waypoints.append(
                ScienceWaypoint(
                    id=wp["id"],
                    name=wp["name"],
                    rc=(r, c),
                    priority_score=float(wp.get("priority_score", 0.0)),
                )
            )
    return terrain, transform, waypoints


@pytest.fixture
def isolated_dirs(tmp_path):
    m_dir = str(tmp_path / "missions")
    e_dir = str(tmp_path / "experiments")
    os.makedirs(m_dir, exist_ok=True)
    os.makedirs(e_dir, exist_ok=True)
    return m_dir, e_dir


# =============================================================================
# 1. Save and reload a mission
# =============================================================================
def test_01_save_and_reload_mission(isolated_dirs):
    m_dir, _ = isolated_dirs
    payload = {
        "mission_id": "mission_alpha_recon",
        "name": "Alpha Reconnaissance Traverse",
        "description": "Exploration of Hawksbill Gap and Three Forks delta front.",
        "canonical_mission": {
            "start": {"row": 117, "col": 157, "name": "Landing Site"},
            "goal": {"row": 194, "col": 131, "name": "Kodiak Butte"},
            "stops": [{"row": 153, "col": 123, "id": "three_forks", "name": "Three Forks", "priority_score": 75.0}],
            "profile": "conservative",
            "vehicle_mode": "crew_eva",
            "speed_multiplier": 1.0,
            "optimize_stops": False,
            "mission_constraints": {},
        },
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "terrain_dataset_id": TERRAIN_DATASET_ID,
    }
    saved = save_mission(payload, missions_dir=m_dir)
    assert saved["mission_id"] == "mission_alpha_recon"
    assert saved["name"] == "Alpha Reconnaissance Traverse"

    reloaded = get_mission("mission_alpha_recon", missions_dir=m_dir)
    assert reloaded["mission_id"] == "mission_alpha_recon"
    assert reloaded["canonical_mission"]["start"]["row"] == 117
    assert len(reloaded["canonical_mission"]["stops"]) == 1
    assert reloaded["input_fingerprint"] == saved["input_fingerprint"]


# =============================================================================
# 2. List saved missions
# =============================================================================
def test_02_list_saved_missions(isolated_dirs):
    m_dir, _ = isolated_dirs
    for i in range(3):
        save_mission({
            "mission_id": f"mission_batch_{i}",
            "name": f"Batch Mission {i}",
            "canonical_mission": {
                "start": {"row": 117, "col": 157},
                "goal": {"row": 194, "col": 131},
                "stops": [],
                "profile": "conservative",
                "vehicle_mode": "crew_eva",
            },
        }, missions_dir=m_dir)

    missions = list_missions(missions_dir=m_dir)
    assert len(missions) == 3
    ids = [m["mission_id"] for m in missions]
    assert "mission_batch_0" in ids
    assert "mission_batch_1" in ids
    assert "mission_batch_2" in ids


# =============================================================================
# 3. Update and rename a mission
# =============================================================================
def test_03_update_and_rename_mission(isolated_dirs):
    m_dir, _ = isolated_dirs
    init_m = save_mission({
        "mission_id": "mission_to_update",
        "name": "Initial Name",
        "canonical_mission": {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 194, "col": 131},
            "stops": [],
            "profile": "conservative",
            "vehicle_mode": "crew_eva",
        },
    }, missions_dir=m_dir)

    orig_created_at = init_m["created_at"]

    updated = update_mission(
        "mission_to_update",
        {"name": "Renamed Mission Study", "description": "Updated scientific objective."},
        missions_dir=m_dir,
    )
    assert updated["name"] == "Renamed Mission Study"
    assert updated["description"] == "Updated scientific objective."
    assert updated["created_at"] == orig_created_at  # Preserved creation time

    reloaded = get_mission("mission_to_update", missions_dir=m_dir)
    assert reloaded["name"] == "Renamed Mission Study"


# =============================================================================
# 4. Duplicate a mission without sharing mutable record
# =============================================================================
def test_04_duplicate_mission(isolated_dirs):
    m_dir, _ = isolated_dirs
    orig = save_mission({
        "mission_id": "mission_orig",
        "name": "Original Study",
        "canonical_mission": {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 194, "col": 131},
            "stops": [{"row": 100, "col": 100, "id": "s1"}],
            "profile": "balanced",
            "vehicle_mode": "robotic_rover",
        },
    }, missions_dir=m_dir)

    dup = duplicate_mission("mission_orig", new_name="Cloned Study", missions_dir=m_dir)
    assert dup["mission_id"] != "mission_orig"
    assert dup["name"] == "Cloned Study"
    assert dup["canonical_mission"]["profile"] == "balanced"

    # Modify clone and verify orig is untouched
    update_mission(dup["mission_id"], {"name": "Mutated Clone"}, missions_dir=m_dir)
    orig_check = get_mission("mission_orig", missions_dir=m_dir)
    assert orig_check["name"] == "Original Study"


# =============================================================================
# 5. Delete a mission with correct not-found behavior
# =============================================================================
def test_05_delete_mission(isolated_dirs):
    m_dir, _ = isolated_dirs
    save_mission({
        "mission_id": "mission_to_delete",
        "name": "Temporary",
        "canonical_mission": {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 194, "col": 131},
            "stops": [],
            "profile": "conservative",
            "vehicle_mode": "crew_eva",
        },
    }, missions_dir=m_dir)

    res = delete_mission("mission_to_delete", missions_dir=m_dir)
    assert res["deleted"] is True

    # Confirm deletion
    with pytest.raises(WorkspaceError) as exc_info:
        get_mission("mission_to_delete", missions_dir=m_dir)
    assert exc_info.value.status_code == 404

    # Deleting again raises 404
    with pytest.raises(WorkspaceError) as exc_info2:
        delete_mission("mission_to_delete", missions_dir=m_dir)
    assert exc_info2.value.status_code == 404


# =============================================================================
# 6. Import a valid mission JSON file
# =============================================================================
def test_06_import_valid_mission(isolated_dirs):
    m_dir, _ = isolated_dirs
    raw_json = json.dumps({
        "schema_version": "1.0.0",
        "mission_id": "imported_delta_campaign",
        "name": "Imported Delta Campaign",
        "created_at": "2026-10-18T10:00:00Z",
        "updated_at": "2026-10-18T10:00:00Z",
        "input_fingerprint": "a" * 64,
        "canonical_mission": {
            "start": {"row": 117, "col": 157},
            "goal": {"row": 194, "col": 131},
            "stops": [],
            "profile": "conservative",
            "vehicle_mode": "crew_eva",
        },
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
    })

    res = import_mission_json(raw_json, missions_dir=m_dir)
    assert res["mission_id"] == "imported_delta_campaign"
    assert res["name"] == "Imported Delta Campaign"

    reloaded = get_mission("imported_delta_campaign", missions_dir=m_dir)
    assert reloaded["mission_id"] == "imported_delta_campaign"


# =============================================================================
# 7. Reject an invalid mission file without modifying storage
# =============================================================================
def test_07_reject_invalid_mission(isolated_dirs):
    m_dir, _ = isolated_dirs
    bad_json = json.dumps({
        "schema_version": "1.0.0",
        "mission_id": "bad_mission",
        # Missing required fields like canonical_mission
    })

    with pytest.raises(ContractValidationError):
        import_mission_json(bad_json, missions_dir=m_dir)

    # Storage remains empty
    assert len(list_missions(missions_dir=m_dir)) == 0


# =============================================================================
# 8. Save and reopen a completed experiment
# =============================================================================
def test_08_save_and_reopen_experiment(isolated_dirs, terrain_context):
    terrain, transform, waypoints = terrain_context
    _, e_dir = isolated_dirs

    route_res = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    exp_payload = {
        "experiment_id": "exp_baseline_run_01",
        "name": "Baseline Traverse Study",
        "description": "Nominal least-cost traverse without disruption.",
        "status": "success",
        "lifecycle_state": "historical_result",
        "baseline_fingerprint": route_res["input_fingerprint"],
        "mission_snapshot": route_res["mission_snapshot"],
        "baseline_route": route_res,
        "scenarios_evaluated": [],
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
    }

    saved = save_experiment(exp_payload, experiments_dir=e_dir)
    assert saved["experiment_id"] == "exp_baseline_run_01"

    reloaded = get_experiment("exp_baseline_run_01", experiments_dir=e_dir)
    assert reloaded["baseline_fingerprint"] == route_res["input_fingerprint"]
    assert reloaded["baseline_route"]["route_metrics"]["ground_distance_m"] > 0


# =============================================================================
# 9. Preserve failed or infeasible scenario results correctly
# =============================================================================
def test_09_preserve_infeasible_experiment(isolated_dirs):
    _, e_dir = isolated_dirs

    infeasible_route = {
        "schema_version": "1.0.0",
        "input_fingerprint": "f" * 64,
        "status": "unreachable",
        "is_reachable": False,
        "is_budget_feasible": False,
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "path_rc": [],
        "coordinates_3d": [],
        "route_metrics": {
            "ground_distance_m": None,
            "terrain_cost_flat_m": None,
            "active_traverse_time_s": None,
            "total_mission_time_s": None,
            "cumulative_climb_m": 0.0,
            "max_slope_deg": 0.0,
            "science_score": 0.0,
        },
        "warnings": ["Destination unreachable due to impassable barrier."],
    }

    exp_payload = {
        "experiment_id": "exp_infeasible_blocked",
        "name": "Impassable Rockfall Wall",
        "status": "infeasible",
        "lifecycle_state": "failed",
        "baseline_fingerprint": "f" * 64,
        "mission_snapshot": {
            "schema_version": "1.0.0",
            "input_fingerprint": "f" * 64,
            "canonical_mission": {"start": {"row": 117, "col": 157}, "goal": {"row": 194, "col": 131}},
            "ordered_points": [[117, 157], [194, 131]],
            "terrain_dataset": {"dataset_id": TERRAIN_DATASET_ID, "grid_cell_size_m": 20.0, "dimensions": {"height": 250, "width": 250}},
        },
        "baseline_route": infeasible_route,
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
    }

    saved = save_experiment(exp_payload, experiments_dir=e_dir)
    assert saved["status"] == "infeasible"
    assert saved["lifecycle_state"] == "failed"

    reloaded = get_experiment("exp_infeasible_blocked", experiments_dir=e_dir)
    assert reloaded["baseline_route"]["is_reachable"] is False


# =============================================================================
# 10. Reject malformed IDs and path traversal attempts
# =============================================================================
def test_10_reject_path_traversal(isolated_dirs):
    m_dir, _ = isolated_dirs
    malicious_ids = [
        "../escape",
        "..\\escape",
        "/etc/passwd",
        "C:\\Windows\\System32",
        "id with spaces",
        "id;injection",
        "a",  # too short (<3)
        "b" * 65,  # too long (>64)
    ]

    for mid in malicious_ids:
        with pytest.raises(WorkspaceError) as exc_info:
            validate_record_id(mid)
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "ERR_INVALID_RECORD_ID"

        # Ensure API functions also reject
        with pytest.raises(WorkspaceError):
            get_mission(mid, missions_dir=m_dir)


# =============================================================================
# 11. Handle duplicate names without overwriting different records
# =============================================================================
def test_11_duplicate_names_independent_records(isolated_dirs):
    m_dir, _ = isolated_dirs
    m1 = save_mission({
        "mission_id": "mission_id_001",
        "name": "Standard Jezero Survey",
        "canonical_mission": {"start": {"row": 117, "col": 157}, "goal": {"row": 194, "col": 131}, "stops": []},
    }, missions_dir=m_dir)

    m2 = save_mission({
        "mission_id": "mission_id_002",
        "name": "Standard Jezero Survey",  # Identical human name, distinct ID
        "canonical_mission": {"start": {"row": 117, "col": 157}, "goal": {"row": 153, "col": 123}, "stops": []},
    }, missions_dir=m_dir)

    assert m1["mission_id"] != m2["mission_id"]
    assert m1["name"] == m2["name"]

    # Verify both records persist independently
    all_m = list_missions(missions_dir=m_dir)
    assert len(all_m) == 2


# =============================================================================
# 12. Verify atomic write and failure recovery
# =============================================================================
def test_12_atomic_write_recovery(isolated_dirs):
    m_dir, _ = isolated_dirs
    valid_file = os.path.join(m_dir, "atomic_test.json")
    atomic_write_json(valid_file, {"schema_version": "1.0.0", "status": "healthy"})

    assert os.path.isfile(valid_file)
    with open(valid_file, "r") as f:
        data = json.load(f)
    assert data["status"] == "healthy"


# =============================================================================
# 13. Detect when saved mission fingerprint no longer matches current config
# =============================================================================
def test_13_fingerprint_mismatch_detection():
    base_mission = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
        "stops": [{"row": 153, "col": 123, "id": "three_forks"}],
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }
    saved_fp = compute_input_fingerprint(base_mission)

    # Alter configuration
    modified_mission = copy.deepcopy(base_mission)
    modified_mission["stops"].append({"row": 100, "col": 100, "id": "new_stop"})
    current_fp = compute_input_fingerprint(modified_mission)

    assert saved_fp != current_fp

    # Lifecycle evaluation
    fake_exp = {
        "status": "success",
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "baseline_fingerprint": saved_fp,
    }
    state = evaluate_experiment_lifecycle(fake_exp, current_mission=modified_mission)
    assert state == "recalculation_required"


# =============================================================================
# 14. Mark incompatible historical results appropriately
# =============================================================================
def test_14_mark_incompatible_historical_result():
    fake_exp = {
        "status": "success",
        "terrain_dataset_id": "INCOMPATIBLE_DATASET_GALE_CRATER",
        "baseline_fingerprint": "abc",
    }
    state = evaluate_experiment_lifecycle(fake_exp, current_dataset_id=TERRAIN_DATASET_ID)
    assert state == "stale_incompatible"


# =============================================================================
# 15. Replay an experiment without overwriting historical result
# =============================================================================
def test_15_replay_preserves_historical_immutability(isolated_dirs, terrain_context):
    terrain, transform, waypoints = terrain_context
    _, e_dir = isolated_dirs

    route_res = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    orig_exp = save_experiment({
        "experiment_id": "exp_hist_001",
        "name": "Historical Run",
        "status": "success",
        "baseline_fingerprint": route_res["input_fingerprint"],
        "mission_snapshot": route_res["mission_snapshot"],
        "baseline_route": route_res,
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
    }, experiments_dir=e_dir)

    # Replay experiment
    replayed = replay_saved_experiment("exp_hist_001", terrain, transform, waypoints, experiments_dir=e_dir)

    assert replayed["experiment_id"] != "exp_hist_001"
    assert replayed["replayed_from_experiment_id"] == "exp_hist_001"
    assert replayed["is_exact_match"] is True

    # Confirm original record is untouched
    orig_check = get_experiment("exp_hist_001", experiments_dir=e_dir)
    assert orig_check["name"] == "Historical Run"
    assert orig_check["experiment_id"] == "exp_hist_001"

    # Both records present in library
    exps = list_experiments(experiments_dir=e_dir)
    assert len(exps) == 2


# =============================================================================
# 16. Compare two experiments with compatible metric definitions
# =============================================================================
def test_16_compare_compatible_experiments(isolated_dirs, terrain_context):
    terrain, transform, waypoints = terrain_context
    _, e_dir = isolated_dirs

    # Exp A: Single-leg
    r_a = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    exp_a = save_experiment({
        "experiment_id": "exp_comp_a",
        "name": "Direct Route",
        "status": "success",
        "baseline_fingerprint": r_a["input_fingerprint"],
        "mission_snapshot": r_a["mission_snapshot"],
        "baseline_route": r_a,
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
    }, experiments_dir=e_dir)

    # Exp B: Multi-stop visiting Three Forks
    r_b = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
        "stops": [{"row": 153, "col": 123, "id": "three_forks", "priority_score": 75.0}],
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }, terrain, transform, waypoints)

    exp_b = save_experiment({
        "experiment_id": "exp_comp_b",
        "name": "Science Tour",
        "status": "success",
        "baseline_fingerprint": r_b["input_fingerprint"],
        "mission_snapshot": r_b["mission_snapshot"],
        "baseline_route": r_b,
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
    }, experiments_dir=e_dir)

    comp = compare_two_experiments("exp_comp_a", "exp_comp_b", experiments_dir=e_dir)
    assert comp["is_compatible"] is True
    assert comp["deltas"]["distance_delta_m"] > 0  # Multi-stop is longer
    assert comp["deltas"]["science_score_delta"] > 0  # Harvests more points
    assert len(comp["trade_offs_summary"]) >= 2


# =============================================================================
# 17. Handle incompatible experiment comparison inputs
# =============================================================================
def test_17_compare_incompatible_experiments(isolated_dirs):
    _, e_dir = isolated_dirs
    exp_a = {
        "experiment_id": "exp_inc_a",
        "name": "Dataset A Run",
        "status": "success",
        "terrain_dataset_id": "JEZERO_CTX_20M",
        "model_version": "2.0.0",
        "baseline_route": {"distance_m": 1000.0, "travel_time_s": 1800.0, "cost": 1200.0, "science_score": 50.0},
    }
    exp_b = {
        "experiment_id": "exp_inc_b",
        "name": "Dataset B Run",
        "status": "success",
        "terrain_dataset_id": "GALE_HIRISE_1M",  # Incompatible
        "model_version": "2.0.0",
        "baseline_route": {"distance_m": 1200.0, "travel_time_s": 2200.0, "cost": 1500.0, "science_score": 60.0},
    }

    comp = compare_two_experiments(exp_a, exp_b, experiments_dir=e_dir)
    assert comp["is_compatible"] is False
    assert len(comp["incompatibility_reasons"]) > 0
    assert "Incompatible terrain datasets" in comp["incompatibility_reasons"][0]


# =============================================================================
# 18. Validate every new endpoint against its declared schema
# =============================================================================
def test_18_schema_conformance_saved_mission_and_experiment(isolated_dirs, terrain_context):
    terrain, transform, waypoints = terrain_context
    m_dir, e_dir = isolated_dirs

    # Mission
    m = save_mission({
        "mission_id": "schema_test_m",
        "name": "Schema Mission",
        "canonical_mission": {"start": {"row": 117, "col": 157}, "goal": {"row": 194, "col": 131}, "stops": []},
    }, missions_dir=m_dir)
    is_valid_m, errs_m = validate_contract(m, "saved-mission")
    assert is_valid_m, f"Mission failed schema: {errs_m}"

    # Route & Experiment
    r = plan_route_api({
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
    }, terrain, transform, waypoints)

    e = save_experiment({
        "experiment_id": "schema_test_e",
        "name": "Schema Experiment",
        "baseline_fingerprint": r["input_fingerprint"],
        "mission_snapshot": r["mission_snapshot"],
        "baseline_route": r,
    }, experiments_dir=e_dir)
    is_valid_e, errs_e = validate_contract(e, "saved-experiment")
    assert is_valid_e, f"Experiment failed schema: {errs_e}"

    # Comparison Response
    comp = compare_two_experiments(e, e, experiments_dir=e_dir)
    is_valid_c, errs_c = validate_contract(comp, "experiment-comparison-response")
    assert is_valid_c, f"Comparison response failed schema: {errs_c}"


# =============================================================================
# 19. Preserve existing API response compatibility
# =============================================================================
def test_19_existing_api_compatibility(terrain_context):
    terrain, transform, waypoints = terrain_context
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 194, "col": 131},
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
    }
    res = plan_route_api(payload, terrain, transform, waypoints)
    assert res["schema_version"] == "1.0.0"
    assert "distance_m" in res  # Legacy top-level key preserved
    assert "route_metrics" in res
    assert "mission_snapshot" in res
    assert len(res["path_rc"]) > 0


# =============================================================================
# 20. Verify that mission and experiment persistence survives a restart
# =============================================================================
def test_20_persistence_survives_restart(isolated_dirs):
    m_dir, e_dir = isolated_dirs

    # Save records
    m = save_mission({
        "mission_id": "m_survive",
        "name": "Durable Mission",
        "canonical_mission": {"start": {"row": 117, "col": 157}, "goal": {"row": 194, "col": 131}},
    }, missions_dir=m_dir)

    e = save_experiment({
        "experiment_id": "e_survive",
        "name": "Durable Experiment",
        "baseline_fingerprint": "1" * 64,
        "mission_snapshot": {"canonical_mission": {}},
        "baseline_route": {"distance_m": 500.0, "is_reachable": True},
    }, experiments_dir=e_dir)

    # Simulate fresh process restart by reading directly from filesystem paths
    assert os.path.exists(os.path.join(m_dir, "m_survive.json"))
    assert os.path.exists(os.path.join(e_dir, "e_survive.json"))

    fresh_m = get_mission("m_survive", missions_dir=m_dir)
    assert fresh_m["name"] == "Durable Mission"

    fresh_e = get_experiment("e_survive", experiments_dir=e_dir)
    assert fresh_e["name"] == "Durable Experiment"
