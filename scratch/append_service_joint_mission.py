import os

service_joint_mission_code = '''

# ==============================================================================
# Milestone 13E: Joint Mission Co-Design API Services
# ==============================================================================

from marswalk.core.joint_mission_planner import (
    JointMissionOptimizationResult,
    JointMissionConfiguration,
    optimize_joint_mission,
    evaluate_joint_mission,
    validate_joint_mission_input,
    OBJECTIVE_WEIGHT_PROFILES,
)
from marswalk.core.relay_planner import screen_relay_candidates


def joint_mission_evaluate_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Evaluates a specific pre-defined traverse route and relay infrastructure configuration.
    """
    try:
        traverse_path_raw = payload.get("traverse_path") or payload.get("path_rc")
        if not traverse_path_raw or len(traverse_path_raw) < 2:
            raise APIError("Missing or invalid traverse_path (must contain at least 2 points)", 400)

        traverse_path = [tuple(p) for p in traverse_path_raw]

        base_station = payload.get("base_station") or {"node_id": "BASE", "row": traverse_path[0][0], "col": traverse_path[0][1], "antenna_height_m": 10.0}
        deployed_relays = payload.get("deployed_relays") or []

        rover_h = float(payload.get("rover_antenna_h", 2.5))
        max_direct_m = float(payload.get("max_direct_range_m", 2500.0))
        max_relay_m = float(payload.get("max_relay_range_m", 5000.0))

        config = evaluate_joint_mission(
            traverse_path=traverse_path,
            terrain=terrain,
            base_station=base_station,
            deployed_relays=deployed_relays,
            rover_antenna_h=rover_h,
            max_direct_range_m=max_direct_m,
            max_relay_range_m=max_relay_m,
        )

        res_dict = config.to_dict()
        res_dict["schema_version"] = "1.0.0"
        res_dict["provenance"] = {
            "terrain_dataset": "USGS_CTX_DTM_JEZERO_20M",
            "doi": "10.5066/P906QQT8",
            "planetary_datum": "IAU 2000 Mars Spheroid (R=3,396,190m)",
        }
        return res_dict

    except APIError:
        raise
    except Exception as err:
        raise APIError(f"Joint mission evaluation failed: {str(err)}", 500)


def joint_mission_optimize_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Executes coupled co-design optimization across alternative traverses and relay placements.
    """
    try:
        # Validate input
        validated_input = validate_joint_mission_input(payload, terrain=terrain)

        # Run optimization
        opt_result = optimize_joint_mission(
            start_rc=validated_input.start_rc,
            goal_rc=validated_input.goal_rc,
            terrain=terrain,
            base_station=validated_input.base_station,
            waypoints=validated_input.waypoints,
            relay_budget=validated_input.relay_budget,
            max_direct_range_m=validated_input.max_direct_range_m,
            max_relay_range_m=validated_input.max_relay_range_m,
            rover_antenna_h=validated_input.rover_antenna_h,
            base_antenna_h=validated_input.base_antenna_h,
            relay_antenna_h=validated_input.relay_antenna_h,
            objective_profile=validated_input.objective_profile,
            custom_weights=validated_input.custom_weights,
            max_route_candidates=validated_input.max_route_candidates,
        )

        res_dict = opt_result.to_dict()
        res_dict["schema_version"] = "1.0.0"
        return res_dict

    except ValueError as val_err:
        raise APIError(f"Invalid joint mission parameters: {str(val_err)}", 400)
    except APIError:
        raise
    except Exception as err:
        raise APIError(f"Joint mission optimization failed: {str(err)}", 500)


def joint_mission_configurations_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Returns candidate promontory relay sites, supported objective profiles, and default parameters.
    """
    try:
        dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
        dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

        cands = screen_relay_candidates(
            elevation=terrain.elevation,
            slope_deg=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            dx_ground_m=dx,
            dy_ground_m=dy,
            max_slope_deg=12.0,
            min_elevation_m=-2500.0,
            min_separation_m=450.0,
            max_candidates=12,
        )

        return {
            "schema_version": "1.0.0",
            "objective_profiles": OBJECTIVE_WEIGHT_PROFILES,
            "candidate_promontories": cands,
            "default_parameters": {
                "base_station": {"node_id": "BASE", "row": 117, "col": 157, "antenna_height_m": 10.0, "label": "Octavia E. Butler Base"},
                "relay_budget": 2,
                "max_direct_range_m": 2500.0,
                "max_relay_range_m": 5000.0,
                "rover_antenna_h": 2.5,
                "base_antenna_h": 10.0,
                "relay_antenna_h": 10.0,
            },
            "provenance": {
                "terrain_dataset": "USGS_CTX_DTM_JEZERO_20M",
                "doi": "10.5066/P906QQT8",
            }
        }
    except Exception as err:
        raise APIError(f"Failed to retrieve joint mission configurations: {str(err)}", 500)


def joint_mission_compare_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Provides side-by-side trade-off comparison between two candidate co-design configurations.
    """
    try:
        config_a = payload.get("config_a")
        config_b = payload.get("config_b")
        if not config_a or not config_b:
            raise APIError("Payload must include both config_a and config_b for comparison.", 400)

        m_a = config_a.get("metrics", {}).get("physical_metrics", {})
        m_b = config_b.get("metrics", {}).get("physical_metrics", {})

        dist_a = float(m_a.get("distance_m", 0.0))
        dist_b = float(m_b.get("distance_m", 0.0))
        delta_dist = dist_b - dist_a

        gap_a = float(m_a.get("gap_distance_m", 0.0))
        gap_b = float(m_b.get("gap_distance_m", 0.0))
        delta_gap = gap_b - gap_a

        avail_a = float(m_a.get("availability_pct", 100.0))
        avail_b = float(m_b.get("availability_pct", 100.0))

        relays_a = int(m_a.get("relay_count", 0))
        relays_b = int(m_b.get("relay_count", 0))
        delta_relays = relays_b - relays_a

        narrative = (
            f"Comparing {config_a.get('configuration_id', 'A')} vs {config_b.get('configuration_id', 'B')}: "
            f"Config A is {abs(delta_dist):.1f}m {'shorter' if delta_dist > 0 else 'longer'}, "
            f"requires {abs(delta_relays)} {'fewer' if delta_relays > 0 else 'more'} relay(s), "
            f"and achieves {avail_a:.1f}% vs {avail_b:.1f}% comms availability."
        )

        return {
            "schema_version": "1.0.0",
            "comparison": {
                "config_a_id": config_a.get("configuration_id"),
                "config_b_id": config_b.get("configuration_id"),
                "delta_distance_m": round(delta_dist, 2),
                "delta_gap_distance_m": round(delta_gap, 2),
                "delta_availability_pct": round(avail_b - avail_a, 2),
                "delta_relays": delta_relays,
                "narrative_trade_off": narrative,
            }
        }
    except APIError:
        raise
    except Exception as err:
        raise APIError(f"Joint mission comparison failed: {str(err)}", 500)


def joint_mission_promote_api(payload: Dict[str, Any], terrain: TerrainGrid, transform: Any) -> Dict[str, Any]:
    """
    Promotes a selected co-design configuration into active mission persistence.
    """
    try:
        config = payload.get("configuration")
        if not config:
            raise APIError("Missing configuration in promotion payload.", 400)

        cfg_id = config.get("configuration_id", "PROMOTED_CO_DESIGN")
        trv = config.get("traverse", {})
        relays = config.get("relays", {})

        # Build dedicated joint mission workspace record
        workspace_dir = os.path.join("data", "workspaces", "joint_missions")
        os.makedirs(workspace_dir, exist_ok=True)

        rec_filename = f"{cfg_id}.json"
        rec_path = os.path.join(workspace_dir, rec_filename)

        promotion_record = {
            "promoted_at_utc": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
            "status": "PROMOTED",
            "configuration": config,
            "provenance": {
                "system": "MarsWalk 2.0 / Project Atlas Joint Mission Co-Design",
                "milestone": "13E",
                "terrain_doi": "10.5066/P906QQT8",
            }
        }

        # Atomic write
        tmp_path = f"{rec_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(promotion_record, f, indent=2)
        os.replace(tmp_path, rec_path)

        return {
            "schema_version": "1.0.0",
            "status": "SUCCESSFULLY_PROMOTED",
            "configuration_id": cfg_id,
            "record_path": rec_path,
            "promoted_traverse_label": trv.get("label", "Selected Traverse"),
            "active_relays_count": relays.get("relay_count", 0),
            "message": f"Successfully promoted co-design configuration {cfg_id} to active workspace.",
        }
    except APIError:
        raise
    except Exception as err:
        raise APIError(f"Joint mission promotion failed: {str(err)}", 500)
'''

with open('src/marswalk/api/service.py', 'a', encoding='utf-8') as f:
    f.write(service_joint_mission_code)

print('Appended Joint Mission API services to src/marswalk/api/service.py successfully!')
