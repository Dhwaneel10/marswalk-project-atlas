"""
MarsWalk 2.0 / Project Atlas — Mission 2 Integration & Reliability Test Suite
=============================================================================
Comprehensive automated verification of the Flagship Scenario 'WHEN MARS GOES DARK':
1. Test 1 — Nominal mission: Terrain ingestion, A* route generation, valid initial state.
2. Test 2 — Communications interruption: Topographic RF shadow, DTN local custody, 0 loss.
3. Test 3 — Communications restoration: Line-of-Sight clearing, priority custody drain, delivery.
4. Test 4 — Fault response: Scarp rockfall detection, traction motor alarm, autonomous safe hold.
5. Test 5 — Adaptive replanning: Obstruction avoidance, lateral detour via Ridge Terrace.
6. Test 6 — Mission comparison: Head-to-head consistency (Strategy A vs Strategy B).
7. Test 7 — Deterministic replay: Bit-exact Merkle tree root hash reproduction.
8. Test 8 — API failure handling: Invalid paths, schema bounds, error diagnostics.
"""

import json
import urllib.request
import urllib.error
import pytest
import numpy as np

from marswalk.core.when_mars_goes_dark import (
    WhenMarsGoesDarkEngine,
    MissionStageId,
)
from marswalk.core.atlas_dtn_engine import BundlePriority, BundleState, DataBundle


@pytest.fixture(scope="module")
def flagship_engine():
    """Shared WhenMarsGoesDarkEngine initialized with Jezero 20m terrain."""
    return WhenMarsGoesDarkEngine(geotiff_path="data/processed/jezero_ready_20m.tif")


@pytest.fixture(scope="module")
def executed_mission(flagship_engine):
    """Execute the flagship mission once for inspection across tests."""
    return flagship_engine.execute_flagship_mission()


# =============================================================================
# TEST 1 — NOMINAL MISSION EXECUTION
# =============================================================================
def test_nominal_mission_execution(executed_mission):
    """Verify nominal mission starts, generates valid A* traverse, and has qualified status."""
    assert executed_mission["status"] == "QUALIFIED"
    assert executed_mission["mission_id"] == "MISSION-MARS-DARK-001"
    assert executed_mission["snapshots_count"] == 7

    # Stage 1 snapshot verification
    s1 = executed_mission["snapshots"][0]
    assert s1["stage_id"] == MissionStageId.STAGE_1_NOMINAL.value
    assert s1["rover_rc"] == [117, 157]
    assert s1["comms_status"] == "ONLINE_128KBPS"
    assert s1["solar_flux_wm2"] > 500.0
    assert s1["speed_factor"] == 1.0
    assert len(s1["active_alarms"]) == 0
    assert s1["dtn_delivered_bundles"] == 2


# =============================================================================
# TEST 2 — COMMUNICATIONS INTERRUPTION & DTN CUSTODY
# =============================================================================
def test_communications_interruption_and_dtn_custody(executed_mission):
    """Verify communications blackout drops link, DTN asserts custody, zero data lost."""
    # Stage 3: Comms Blackout
    s3 = executed_mission["snapshots"][2]
    assert s3["stage_id"] == MissionStageId.STAGE_3_COMMS_BLACKOUT.value
    assert s3["comms_status"] == "BLOCKED_TERRAIN_OCCLUSION"
    assert "ALERT_RF_CARRIER_LOST" in s3["active_alarms"]

    # Stage 4: DTN Custody Buffering
    s4 = executed_mission["snapshots"][3]
    assert s4["stage_id"] == MissionStageId.STAGE_4_DTN_CUSTODY.value
    assert s4["dtn_buffer_bundles"] == 3
    assert s4["dtn_storage_utilization_pct"] > 5.0
    assert s4["dtn_delivered_bundles"] == 2  # No new deliveries while blackout is active

    # Summary audit
    dtn = executed_mission["dtn_summary"]
    assert dtn["dropped_bundles"] == 0
    assert dtn["delivery_success_pct"] == 100.0


# =============================================================================
# TEST 3 — COMMUNICATIONS RESTORATION & PRIORITY CUSTODY FLUSH
# =============================================================================
def test_communications_restoration_and_priority_flush(executed_mission):
    """Verify Line-of-Sight restoration triggers priority drain, delivering 100% of packets."""
    # Stage 7: Ridge Delivery
    s7 = executed_mission["snapshots"][6]
    assert s7["stage_id"] == MissionStageId.STAGE_7_RIDGE_DELIVERY.value
    assert s7["comms_status"] == "RESTORED_128KBPS"
    assert s7["rover_rc"] == [66, 128]
    assert s7["dtn_buffer_bundles"] == 0
    assert s7["dtn_delivered_bundles"] == 6
    assert s7["dtn_storage_utilization_pct"] == 0.0


# =============================================================================
# TEST 4 — FAULT RESPONSE & AUTONOMOUS SAFE HOLD
# =============================================================================
def test_fault_response_and_safe_hold(executed_mission):
    """Verify scarp rockfall triggers occlusion alarm, motor overtemp, and halts vehicle."""
    # Stage 5: Corridor Rockfall Fault
    s5 = executed_mission["snapshots"][4]
    assert s5["stage_id"] == MissionStageId.STAGE_5_CORRIDOR_FAULT.value
    assert s5["speed_factor"] == 0.0
    assert "FAULT_CORRIDOR_OCCLUSION" in s5["active_alarms"]
    assert "ALERT_SAFE_HOLD_ACTIVE" in s5["active_alarms"]
    assert "Hawksbill Gap" in s5["narrative"] or "scarp rockfall" in s5["narrative"]


# =============================================================================
# TEST 5 — ADAPTIVE REPLANNING & LATERAL DETOUR
# =============================================================================
def test_adaptive_replanning_avoidance(executed_mission):
    """Verify adaptive replanner routes around rockfall via Ridge Terrace."""
    routes = executed_mission["routes"]
    nom_dist = routes["nominal_distance_m"]
    detour_dist = routes["detour_distance_m"]

    # Detour must be longer due to lateral avoidance
    assert detour_dist > nom_dist
    assert len(routes["detour_path_rc"]) > 10
    assert routes["ridge_relay_rc"] == [102, 110]

    # Rockfall cells must NOT be in detour path
    rf_center = routes["rockfall_center_rc"]
    detour_path = routes["detour_path_rc"]
    assert tuple(rf_center) not in [tuple(p) for p in detour_path]


# =============================================================================
# TEST 6 — MISSION STRATEGY COMPARISON CONSISTENCY
# =============================================================================
def test_mission_strategy_comparison_consistency(executed_mission):
    """Verify side-by-side Strategy Comparison metrics are computed honestly and consistently."""
    comp = executed_mission["strategy_comparison"]
    assert len(comp) >= 6

    # Verify key metrics
    comp_map = {item["metric"]: item for item in comp}
    assert "Mission Completion Status" in comp_map
    assert comp_map["Mission Completion Status"]["nominal_strategy"] == "FAILED_TRAPPED"
    assert comp_map["Mission Completion Status"]["adaptive_strategy"] == "COMPLETED_SUCCESS"

    assert "Scientific Data Preservation Rate" in comp_map
    assert "40.0%" in comp_map["Scientific Data Preservation Rate"]["nominal_strategy"]
    assert "100.0%" in comp_map["Scientific Data Preservation Rate"]["adaptive_strategy"]

    assert "Data Lost Under Blackout" in comp_map
    assert "0 KB" in comp_map["Data Lost Under Blackout"]["adaptive_strategy"]


# =============================================================================
# TEST 7 — DETERMINISTIC REPLAY & MERKLE CHAIN CONTINUITY
# =============================================================================
def test_deterministic_replay_and_merkle_continuity(flagship_engine):
    """Verify running the engine multiple times produces identical SHA-256 Merkle root hash."""
    run1 = flagship_engine.execute_flagship_mission()
    run2 = flagship_engine.execute_flagship_mission()

    assert run1["root_merkle_hash"] == run2["root_merkle_hash"]
    assert len(run1["root_merkle_hash"]) == 64  # Valid SHA-256 hex string
    assert run1["root_merkle_hash"] == "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8"


# =============================================================================
# TEST 8 — CONTINUOUS PHYSICAL POWER BALANCE MODEL
# =============================================================================
def test_power_balance_differential_model(flagship_engine):
    """Verify continuous physical power balance model matches Jezero physics."""
    # 1. Nominal daylight conditions (tau=0.82, speed=1.0x, slope=0)
    p_nom = flagship_engine.calculate_power_balance(optical_depth_tau=0.82, speed_factor=1.0, slope_deg=0.0)
    assert p_nom["p_solar_w"] == 370.0
    assert p_nom["p_hotel_w"] == 120.0
    assert p_nom["p_drive_w"] == 260.0
    assert p_nom["p_net_w"] == -10.0  # slight net battery draw during drive

    # 2. Severe dust storm derating (tau=3.25)
    p_storm = flagship_engine.calculate_power_balance(optical_depth_tau=3.25, speed_factor=0.60, slope_deg=5.0)
    assert p_storm["p_solar_w"] < 150.0
    assert p_storm["p_net_w"] < -100.0

    # 3. Safe hold (speed=0.0, drive=0)
    p_hold = flagship_engine.calculate_power_balance(optical_depth_tau=3.50, speed_factor=0.0, is_safe_hold=True)
    assert p_hold["p_drive_w"] == 0.0
    assert p_hold["p_hotel_w"] == 120.0

    # 4. Motor stall in Strategy A
    p_stall = flagship_engine.calculate_power_balance(optical_depth_tau=3.50, speed_factor=0.0, is_motor_stalled=True)
    assert p_stall["p_drive_w"] == 650.0


# =============================================================================
# TEST 9 — API ENDPOINTS & ERROR HANDLING
# =============================================================================
def test_api_endpoints_and_error_handling():
    """Verify live HTTP endpoints respond with correct schemas and handle errors gracefully."""
    base_url = "http://127.0.0.1:3000"

    # 1. Flagship run endpoint (GET)
    req_run = urllib.request.Request(f"{base_url}/api/flagship/when-mars-goes-dark/run", headers={"User-Agent": "Pytest"})
    with urllib.request.urlopen(req_run) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "QUALIFIED"
        assert data["mission_id"] == "MISSION-MARS-DARK-001"

    # 2. Flagship replay endpoint
    req_replay = urllib.request.Request(f"{base_url}/api/flagship/when-mars-goes-dark/replay", headers={"User-Agent": "Pytest"})
    with urllib.request.urlopen(req_replay) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["is_valid"] is True
        assert "bit-exact" in data["verification_message"]

    # 3. Flagship comparison endpoint
    req_comp = urllib.request.Request(f"{base_url}/api/flagship/when-mars-goes-dark/comparison", headers={"User-Agent": "Pytest"})
    with urllib.request.urlopen(req_comp) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["comparison_metrics"]) >= 6

    # 4. POST with input validation: negative tau should fail with 400
    bad_payload = json.dumps({"tau": -2.5}).encode("utf-8")
    req_bad = urllib.request.Request(
        f"{base_url}/api/flagship/when-mars-goes-dark/run",
        data=bad_payload,
        headers={"Content-Type": "application/json", "User-Agent": "Pytest"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_bad)
        pytest.fail("Expected HTTP 400 for negative tau")
    except urllib.error.HTTPError as e:
        assert e.code == 400

    # 5. POST with input validation: out-of-bounds rockfall coordinate should fail with 400
    bad_coords = json.dumps({"rockfall_center": [99999, 99999]}).encode("utf-8")
    req_bad_coords = urllib.request.Request(
        f"{base_url}/api/flagship/when-mars-goes-dark/run",
        data=bad_coords,
        headers={"Content-Type": "application/json", "User-Agent": "Pytest"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_bad_coords)
        pytest.fail("Expected HTTP 400 for out-of-bounds coordinates")
    except urllib.error.HTTPError as e:
        assert e.code == 400

    # 6. POST with input validation: non-integer seed should fail with 400
    bad_seed = json.dumps({"seed": "not_an_int"}).encode("utf-8")
    req_bad_seed = urllib.request.Request(
        f"{base_url}/api/flagship/when-mars-goes-dark/run",
        data=bad_seed,
        headers={"Content-Type": "application/json", "User-Agent": "Pytest"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req_bad_seed)
        pytest.fail("Expected HTTP 400 for string seed")
    except urllib.error.HTTPError as e:
        assert e.code == 400

    # 7. POST with valid parameter override: tau = 4.0
    valid_payload = json.dumps({"tau": 4.0}).encode("utf-8")
    req_valid = urllib.request.Request(
        f"{base_url}/api/flagship/when-mars-goes-dark/run",
        data=valid_payload,
        headers={"Content-Type": "application/json", "User-Agent": "Pytest"},
        method="POST"
    )
    with urllib.request.urlopen(req_valid) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["snapshots"][1]["tau_optical_depth"] == 4.0

    # 8. Error handling: non-existent endpoint must return HTTP 404
    try:
        urllib.request.urlopen(f"{base_url}/api/flagship/nonexistent_scenario")
        pytest.fail("Expected HTTP 404 for nonexistent scenario")
    except urllib.error.HTTPError as e:
        assert e.code == 404
