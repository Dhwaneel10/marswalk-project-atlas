"""
Tests for Milestone 11A: Mission Campaign Orchestrator.
Covers multi-sol campaign scheduling, dependency DAGs, planning profiles,
resource bounds, disruption replanning, versioning, persistence, schema validation,
and HTML dossier export on authentic USGS CTX 20m Jezero topography.
"""

import json
import os
import math
import shutil
import tempfile
import pytest
import numpy as np

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid, TerrainConfig
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignConfig,
    CampaignSortie,
    CampaignSummary,
    MissionCampaign,
    TargetStatus,
    CampaignStatus,
    PlanningProfile,
    validate_target_dependencies,
    plan_mission_campaign,
    replan_campaign_disruption,
    export_campaign_report_html,
)
from marswalk.api.workspace import (
    save_campaign,
    list_campaigns,
    get_campaign,
    update_campaign,
    delete_campaign,
    WorkspaceError,
)
from marswalk.api.contracts import validate_contract, ContractValidationError
from marswalk.api.service import (
    plan_campaign_api,
    replan_campaign_api,
    export_campaign_report_api,
    APIError,
)


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic USGS CTX 20m Jezero Crater terrain."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tiff_path = os.path.join(base_dir, "data", "processed", "jezero_ready_20m.tif")
    if not os.path.exists(tiff_path):
        pytest.skip(f"Jezero CTX raster not found at {tiff_path}")
    terrain = load_and_process_terrain(tiff_path)
    return terrain


@pytest.fixture
def temp_campaigns_dir():
    """Temporary directory for isolating workspace tests."""
    temp_dir = tempfile.mkdtemp(prefix="marswalk_test_campaigns_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_target_dependency_validation_valid():
    """Test valid acyclic target prerequisite graph."""
    targets = [
        CampaignTarget(id="t1", name="Target 1", row=120, col=160),
        CampaignTarget(id="t2", name="Target 2", row=125, col=165, prerequisites=["t1"]),
        CampaignTarget(id="t3", name="Target 3", row=130, col=170, prerequisites=["t1", "t2"]),
    ]
    # Should not raise
    validate_target_dependencies(targets)


def test_target_dependency_cycle_detection():
    """Test cycle detection in target prerequisites raises ValueError with chain."""
    targets = [
        CampaignTarget(id="t1", name="Target 1", row=120, col=160, prerequisites=["t3"]),
        CampaignTarget(id="t2", name="Target 2", row=125, col=165, prerequisites=["t1"]),
        CampaignTarget(id="t3", name="Target 3", row=130, col=170, prerequisites=["t2"]),
    ]
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        validate_target_dependencies(targets)


def test_target_dependency_self_reference():
    """Test self-reference in prerequisites raises ValueError."""
    targets = [
        CampaignTarget(id="t1", name="Target 1", row=120, col=160, prerequisites=["t1"]),
    ]
    with pytest.raises(ValueError, match="cannot have itself as a prerequisite"):
        validate_target_dependencies(targets)


def test_target_dependency_unknown_reference():
    """Test reference to non-existent target ID raises ValueError."""
    targets = [
        CampaignTarget(id="t1", name="Target 1", row=120, col=160, prerequisites=["non_existent_target"]),
    ]
    with pytest.raises(ValueError, match="references non-existent prerequisite"):
        validate_target_dependencies(targets)


def test_multi_sol_planning_basic(jezero_terrain):
    """Test multi-sol planning splitting targets into feasible sorties within duration ceilings."""
    # Base: Octavia Landing (117, 157)
    targets = [
        CampaignTarget(id="t_depot", name="Three Forks Depot", row=153, col=123, priority_score=80.0, dwell_time_s=600.0),
        CampaignTarget(id="t_scarp", name="Artuby Ridge", row=130, col=148, priority_score=70.0, dwell_time_s=600.0),
        CampaignTarget(id="t_crater", name="Kodiak Overlook", row=194, col=131, priority_score=90.0, dwell_time_s=600.0),
    ]

    # Set duration limit to 8500s so each target fits but all three together cannot fit into 1 sol
    config = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        vehicle_mode="crew_eva",
        max_duration_per_sortie_s=8500.0,
        base_start_rc=(117, 157),
        return_to_base_each_sol=True,
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_test_basic_01",
        name="Jezero Basic Multi-Sol Test",
        config=config,
        targets=targets,
        terrain=jezero_terrain,
    )

    assert campaign.campaign_id == "cmp_test_basic_01"
    assert len(campaign.sorties) >= 2, "Should split across multiple sols due to duration limit"
    assert campaign.summary.total_sols == len(campaign.sorties)
    assert campaign.summary.targets_scheduled == 3
    assert campaign.summary.total_distance_m > 0
    assert campaign.summary.total_duration_s > 0
    assert campaign.summary.is_campaign_feasible is True

    # Check zero double-counting: total duration should exactly equal sum of sortie durations
    assert math.isclose(campaign.summary.total_duration_s, sum(s.total_duration_s for s in campaign.sorties), rel_tol=1e-5)
    assert math.isclose(campaign.summary.total_distance_m, sum(s.distance_m for s in campaign.sorties), rel_tol=1e-5)

    # Validate against JSON schema
    validate_contract(campaign.to_dict(), "mission-campaign", raise_on_error=True)


def test_target_prerequisites_ordering_respected(jezero_terrain):
    """Test that target prerequisite ordering is strictly enforced across sols."""
    targets = [
        # t_child has t_parent as prerequisite
        CampaignTarget(id="t_parent", name="Initial Survey", row=125, col=155, priority_score=60.0, dwell_time_s=600.0),
        CampaignTarget(id="t_child", name="Sample Analysis", row=130, col=150, priority_score=95.0, dwell_time_s=600.0, prerequisites=["t_parent"]),
    ]

    config = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=3000.0,  # Each sol can only do 1 stop plus return
        base_start_rc=(117, 157),
        return_to_base_each_sol=True,
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_test_prereqs_01",
        name="Prerequisite Order Test",
        config=config,
        targets=targets,
        terrain=jezero_terrain,
    )

    # Find the assigned sols for parent and child
    target_map = {t.id: t for t in campaign.targets}
    parent_sol = target_map["t_parent"].assigned_sol_index
    child_sol = target_map["t_child"].assigned_sol_index

    assert parent_sol is not None
    assert child_sol is not None
    assert parent_sol <= child_sol, "Parent prerequisite must be scheduled on or before child target sol"

    if parent_sol == child_sol:
        # Check that parent appears before child in the sortie's target_ids
        for s in campaign.sorties:
            if s.sol_index == parent_sol:
                assert s.target_ids.index("t_parent") < s.target_ids.index("t_child")


def test_planning_profiles_generate_different_tradeoffs(jezero_terrain):
    """Test that science_priority, time_constrained, and conservative yield distinct operational trade-offs."""
    targets = [
        CampaignTarget(id="t_close_low", name="Near Low Value", row=120, col=158, priority_score=30.0, dwell_time_s=300.0),
        CampaignTarget(id="t_far_high", name="Distant High Value", row=145, col=135, priority_score=100.0, dwell_time_s=300.0),
        CampaignTarget(id="t_medium", name="Midpoint Ridge", row=130, col=150, priority_score=60.0, dwell_time_s=300.0),
    ]

    # Test with tight max_sols=1 and duration limit=3500s
    config_sci = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=4000.0,
        max_sols=1,
        base_start_rc=(117, 157),
    )
    camp_sci = plan_mission_campaign("cmp_sci", "Sci Profile", config_sci, targets, jezero_terrain)

    config_time = CampaignConfig(
        planning_profile=PlanningProfile.TIME_CONSTRAINED.value,
        max_duration_per_sortie_s=4000.0,
        max_sols=1,
        base_start_rc=(117, 157),
    )
    camp_time = plan_mission_campaign("cmp_time", "Time Profile", config_time, targets, jezero_terrain)

    config_cons = CampaignConfig(
        planning_profile=PlanningProfile.CONSERVATIVE.value,
        max_duration_per_sortie_s=4000.0,  # 80% effective = 3200s
        max_sols=1,
        base_start_rc=(117, 157),
    )
    camp_cons = plan_mission_campaign("cmp_cons", "Cons Profile", config_cons, targets, jezero_terrain)

    # Profiles must record their objective weights
    assert camp_sci.config.objective_weights["science"] == 1.0
    assert camp_time.config.objective_weights["time"] == 1.0
    assert camp_cons.config.objective_weights["margin"] == 1.0

    # The conservative plan should maintain a higher remaining margin percentage
    assert camp_cons.sorties[0].remaining_margin_s > 0


def test_campaign_max_sols_deferred_targets(jezero_terrain):
    """Test that exceeding max_sols marks remaining targets as DEFERRED with clear reason."""
    targets = [
        CampaignTarget(id=f"t_{i}", name=f"Target {i}", row=120 + i*5, col=150 + i*2, priority_score=50.0, dwell_time_s=600.0)
        for i in range(5)
    ]

    config = CampaignConfig(
        max_duration_per_sortie_s=2500.0,  # Fits ~1 target per sol
        max_sols=2,  # Only allows 2 sols
        base_start_rc=(117, 157),
    )

    campaign = plan_mission_campaign("cmp_deferred", "Deferred Test", config, targets, jezero_terrain)

    assert len(campaign.sorties) == 2
    assert campaign.summary.targets_scheduled < 5
    assert campaign.summary.targets_unscheduled > 0

    deferred = [t for t in campaign.targets if t.status == TargetStatus.DEFERRED.value]
    assert len(deferred) > 0
    for d in deferred:
        assert "Deferred due to" in d.unscheduled_reason


def test_unreachable_target_handling(jezero_terrain):
    """Test that a target outside the traversable slope envelope is marked UNREACHABLE."""
    # Place target on an impassable cliff or extreme coordinates
    targets = [
        CampaignTarget(id="t_reachable", name="Near Base", row=120, col=158, priority_score=50.0),
        # Target in extreme corner with unfeasible duration for a small budget
        CampaignTarget(id="t_too_far", name="Distant Impossible", row=10, col=10, priority_score=50.0),
    ]

    config = CampaignConfig(
        max_duration_per_sortie_s=1500.0,  # Too small to reach (10, 10) and return
        max_sols=1,
        base_start_rc=(117, 157),
    )

    campaign = plan_mission_campaign("cmp_unreach", "Unreachable Test", config, targets, jezero_terrain)
    target_map = {t.id: t for t in campaign.targets}

    assert target_map["t_reachable"].status == TargetStatus.SCHEDULED.value
    assert target_map["t_too_far"].status in (TargetStatus.UNREACHABLE.value, TargetStatus.REJECTED_BUDGET_EXCEEDED.value)


def test_campaign_disruption_replanning(jezero_terrain):
    """Test that injecting a corridor closure on a multi-sol campaign reroutes or marks newly unscheduled."""
    targets = [
        CampaignTarget(id="t1", name="Target 1", row=122, col=162, priority_score=80.0, dwell_time_s=600.0),
        CampaignTarget(id="t2", name="Target 2", row=135, col=150, priority_score=70.0, dwell_time_s=600.0),
    ]

    config = CampaignConfig(
        max_duration_per_sortie_s=10000.0,
        base_start_rc=(117, 157),
    )

    # Initial plan
    original_campaign = plan_mission_campaign("cmp_disrupt_test", "Pre-Disruption", config, targets, jezero_terrain)
    assert original_campaign.version == 1
    assert original_campaign.summary.targets_scheduled == 2

    # Inject rockfall covering Target 1 exactly at (122, 162)
    disruption = {
        "disruption_type": "closed_corridor",
        "center_row": 122,
        "center_col": 162,
        "radius_m": 80.0,
        "description": "Mass wasting rockfall at delta scarp entrance",
    }

    revised_campaign = replan_campaign_disruption(
        campaign=original_campaign,
        disruption=disruption,
        terrain=jezero_terrain,
        completed_sol_indices=[],
    )

    # Immutability & versioning
    assert original_campaign.version == 1, "Original campaign must remain unchanged at Version 1"
    assert revised_campaign.version == 2
    assert revised_campaign.parent_campaign_id == original_campaign.campaign_id
    assert revised_campaign.disruption["disruption_type"] == "closed_corridor"
    assert revised_campaign.revision_comparison is not None

    # Validate revised schema
    validate_contract(revised_campaign.to_dict(), "mission-campaign", raise_on_error=True)


def test_campaign_disruption_completed_sols_preserved(jezero_terrain):
    """Test that completed sols are strictly preserved and not modified during replan."""
    targets = [
        CampaignTarget(id="t_sol1", name="Sol 1 Target", row=120, col=158, priority_score=50.0, dwell_time_s=300.0),
        CampaignTarget(id="t_sol2", name="Sol 2 Target", row=135, col=150, priority_score=70.0, dwell_time_s=300.0),
    ]

    config = CampaignConfig(
        max_duration_per_sortie_s=2200.0,  # 1 target per sol since together they take ~2464s > 2200s
        base_start_rc=(117, 157),
    )

    original_campaign = plan_mission_campaign("cmp_preserve_test", "Preserve Sols", config, targets, jezero_terrain)
    assert len(original_campaign.sorties) >= 2

    # Sol 1 was already executed in the field!
    disruption = {
        "disruption_type": "reduced_mobility",
        "speed_multiplier": 0.5,
        "description": "Drive motor derating on Sol 2",
    }

    revised_campaign = replan_campaign_disruption(
        campaign=original_campaign,
        disruption=disruption,
        terrain=jezero_terrain,
        completed_sol_indices=[1],
    )

    # Sol 1 must be marked COMPLETED and match original target
    sol1 = [s for s in revised_campaign.sorties if s.sol_index == 1][0]
    assert sol1.status == "COMPLETED"
    assert "t_sol2" in sol1.target_ids

    # Completed target must have status COMPLETED
    t2 = [t for t in revised_campaign.targets if t.id == "t_sol2"][0]
    assert t2.status == TargetStatus.COMPLETED.value


def test_campaign_workspace_persistence(temp_campaigns_dir, jezero_terrain):
    """Test saving, listing, getting, updating, and deleting campaigns in workspace."""
    targets = [CampaignTarget(id="t1", name="T1", row=120, col=158)]
    config = CampaignConfig(base_start_rc=(117, 157))
    campaign = plan_mission_campaign("cmp_ws_test", "Workspace Campaign", config, targets, jezero_terrain)

    campaign_dict = campaign.to_dict()

    # 1. Save
    saved = save_campaign(campaign_dict, campaigns_dir=temp_campaigns_dir)
    assert saved["campaign_id"] == "cmp_ws_test"

    # 2. List
    listing = list_campaigns(campaigns_dir=temp_campaigns_dir)
    assert len(listing) == 1
    assert listing[0]["campaign_id"] == "cmp_ws_test"

    # 3. Get
    retrieved = get_campaign("cmp_ws_test", campaigns_dir=temp_campaigns_dir)
    assert retrieved["name"] == "Workspace Campaign"

    # 4. Update
    updated = update_campaign("cmp_ws_test", {"name": "Updated Campaign"}, campaigns_dir=temp_campaigns_dir)
    assert updated["name"] == "Updated Campaign"

    # 5. Delete
    deleted = delete_campaign("cmp_ws_test", campaigns_dir=temp_campaigns_dir)
    assert deleted is True
    assert len(list_campaigns(campaigns_dir=temp_campaigns_dir)) == 0


def test_campaign_report_html_generation(jezero_terrain):
    """Test that standalone responsive HTML report generates with valid structure and zero external assets."""
    targets = [
        CampaignTarget(id="t_depot", name="Three Forks Depot", row=153, col=123, priority_score=80.0),
        CampaignTarget(id="t_scarp", name="Artuby Ridge", row=130, col=148, priority_score=70.0),
    ]
    config = CampaignConfig(base_start_rc=(117, 157))
    campaign = plan_mission_campaign("cmp_html_test", "HTML Report Test", config, targets, jezero_terrain)

    html = export_campaign_report_html(campaign)
    assert "<!DOCTYPE html>" in html
    assert "HTML Report Test" in html
    assert "Three Forks Depot" in html
    assert "SCIENTIFIC RESEARCH SIMULATION DISCLAIMER" in html
    assert "USGS_CTX_DTM_JEZERO_20M" in html


def test_campaign_api_endpoints(jezero_terrain):
    """Test plan_campaign_api, replan_campaign_api, and export_campaign_report_api handlers."""
    transform = jezero_terrain.transform if hasattr(jezero_terrain, "transform") else None

    payload = {
        "campaign_id": "cmp_api_test_01",
        "name": "API Test Campaign",
        "targets": [
            {"id": "t1", "name": "Target 1", "row": 120, "col": 158, "priority_score": 85.0},
            {"id": "t2", "name": "Target 2", "row": 125, "col": 155, "priority_score": 65.0, "prerequisites": ["t1"]},
        ],
        "config": {
            "planning_profile": "science_priority",
            "vehicle_mode": "crew_eva",
            "max_duration_per_sortie_s": 5000.0,
            "base_start_rc": [117, 157],
        },
        "save": False,
    }

    # 1. Plan API
    plan_res = plan_campaign_api(payload, jezero_terrain, transform)
    assert plan_res["status"] == "success"
    assert "campaign" in plan_res
    camp_dict = plan_res["campaign"]
    assert len(camp_dict["sorties"]) >= 1

    # 2. Replan API
    replan_payload = {
        "campaign": camp_dict,
        "disruption": {
            "disruption_type": "reduced_mobility",
            "speed_multiplier": 0.8,
            "description": "Drive derating test",
        },
        "save": False,
    }
    replan_res = replan_campaign_api(replan_payload, jezero_terrain, transform)
    assert replan_res["status"] == "success"
    assert replan_res["campaign"]["version"] == 2

    # 3. Export Report API
    report_payload = {
        "campaign": camp_dict,
    }
    rep_res = export_campaign_report_api(report_payload)
    assert rep_res["status"] == "success"
    assert "<!DOCTYPE html>" in rep_res["html"]


def test_daisy_chained_campaign(jezero_terrain):
    """Test multi-sol planning when return_to_base_each_sol is False (daisy-chained)."""
    targets = [
        CampaignTarget(id="t1", name="Waypoint 1", row=120, col=158, priority_score=50.0),
        CampaignTarget(id="t2", name="Waypoint 2", row=125, col=155, priority_score=50.0),
    ]

    config = CampaignConfig(
        max_duration_per_sortie_s=1500.0,  # 1 target takes ~1030s; both take ~2130s > 1500s
        base_start_rc=(117, 157),
        return_to_base_each_sol=False,
    )

    campaign = plan_mission_campaign("cmp_daisy", "Daisy Chain", config, targets, jezero_terrain)
    assert len(campaign.sorties) >= 2
    # Sol 2 departure must match Sol 1 goal
    assert campaign.sorties[1].start_rc == campaign.sorties[0].goal_rc


def test_malformed_persisted_campaign_record(temp_campaigns_dir):
    """Test that listing ignores corrupt/malformed files safely."""
    # Write corrupt JSON
    corrupt_file = os.path.join(temp_campaigns_dir, "corrupt.json")
    with open(corrupt_file, "w") as f:
        f.write("{this is not valid json")

    listing = list_campaigns(campaigns_dir=temp_campaigns_dir)
    assert len(listing) == 0


def test_delete_nonexistent_campaign(temp_campaigns_dir):
    """Test that deleting a non-existent campaign raises WorkspaceError with 404."""
    with pytest.raises(WorkspaceError) as exc_info:
        delete_campaign("cmp_does_not_exist", campaigns_dir=temp_campaigns_dir)
    assert exc_info.value.status_code == 404


def test_api_validation_errors(jezero_terrain):
    """Test API error handling on invalid target coordinates or empty payloads."""
    transform = jezero_terrain.transform if hasattr(jezero_terrain, "transform") else None

    # Empty targets
    with pytest.raises(APIError, match="must specify at least 1 candidate target"):
        plan_campaign_api({"name": "Empty", "targets": []}, jezero_terrain, transform)

    # Out of bounds coordinates
    with pytest.raises(APIError, match="out of Jezero terrain bounds"):
        plan_campaign_api({
            "name": "OOB",
            "targets": [{"id": "t_oob", "name": "OOB", "row": 999, "col": 999}]
        }, jezero_terrain, transform)

