"""
Adds Milestone 13F resource endpoints to src/marswalk/api/service.py
"""

with open("src/marswalk/api/service.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add imports
import_target = "from marswalk.core.relay_planner import screen_relay_candidates\n"
import_addition = """from marswalk.core.relay_planner import screen_relay_candidates
from marswalk.core.mission_resource_model import (
    RoverResourceConfig,
    RelayResourceConfig,
    evaluate_mission_resource_ledger,
    evaluate_resource_sensitivity,
)
"""

if "from marswalk.core.mission_resource_model import" not in code:
    assert import_target in code, "Failed to find import_target"
    code = code.replace(import_target, import_addition, 1)

# 2. Append endpoints
endpoints_code = """

def joint_mission_resource_evaluate_api(
    payload: Dict[str, Any],
    terrain: TerrainGrid,
    transform: Any,
) -> Dict[str, Any]:
    \"\"\"
    Evaluates a specific traverse trajectory and relay topology against energy, power, and time feasibility constraints.
    Validates input parameters, calculates mechanical rolling/grade work without unmodeled regen,
    accounts for intermediate science dwells and relay mast electrical power,
    and returns a structured MissionResourceLedger conforming to Draft 2020-12 schema.
    \"\"\"
    try:
        path_raw = payload.get("path_rc") or payload.get("traverse_path") or []
        if not path_raw or len(path_raw) < 2:
            raise APIError("Path must contain at least 2 coordinate points.", 400)

        path_rc = [tuple(p) for p in path_raw]
        dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
        dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

        rover_data = payload.get("rover_config") or payload.get("rover_resource_config") or {}
        valid_rover_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
        rover_cfg = RoverResourceConfig(**{k: v for k, v in rover_data.items() if k in valid_rover_keys})

        relay_data = payload.get("relay_config") or payload.get("relay_resource_config") or {}
        valid_relay_keys = {f.name for f in RelayResourceConfig.__dataclass_fields__.values()}
        relay_cfg = RelayResourceConfig(**{k: v for k, v in relay_data.items() if k in valid_relay_keys})

        relays_deployed = payload.get("relays_deployed") or []
        waypoints = payload.get("waypoints") or payload.get("intermediate_waypoints") or []
        active_tx_times = payload.get("active_relay_tx_times_s") or {}

        ledger = evaluate_mission_resource_ledger(
            path_rc=path_rc,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=dx,
            ground_dy_m=dy,
            rover_config=rover_cfg,
            relay_config=relay_cfg,
            relays_deployed=relays_deployed,
            intermediate_waypoints=waypoints,
            active_relay_tx_times_s=active_tx_times,
        )

        ledger_dict = ledger.to_dict()
        ledger_dict["schema_version"] = "1.0.0"
        return ledger_dict
    except APIError:
        raise
    except Exception as err:
        raise APIError(f"Resource evaluation failed: {str(err)}", 500)


def joint_mission_resource_sensitivity_api(
    payload: Dict[str, Any],
    terrain: TerrainGrid,
    transform: Any,
) -> Dict[str, Any]:
    \"\"\"
    Executes multi-parameter sensitivity sweeps across vehicle and environmental assumptions.
    Calculates parameter elasticities, ranks factors by operational impact,
    and returns a structured ResourceSensitivityResult conforming to Draft 2020-12 schema.
    \"\"\"
    try:
        path_raw = payload.get("path_rc") or payload.get("traverse_path") or []
        if not path_raw or len(path_raw) < 2:
            raise APIError("Path must contain at least 2 coordinate points.", 400)

        path_rc = [tuple(p) for p in path_raw]
        dx = terrain.dx_ground_m if terrain.dx_ground_m else DEFAULT_DX_M
        dy = terrain.dy_ground_m if terrain.dy_ground_m else DEFAULT_DY_M

        rover_data = payload.get("rover_config") or payload.get("rover_resource_config") or {}
        valid_rover_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
        rover_cfg = RoverResourceConfig(**{k: v for k, v in rover_data.items() if k in valid_rover_keys})

        param_sweeps = payload.get("parameter_sweeps") or payload.get("sweep_factors")

        sens = evaluate_resource_sensitivity(
            path_rc=path_rc,
            elevation_grid=terrain.elevation,
            slope_grid=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            ground_dx_m=dx,
            ground_dy_m=dy,
            rover_config=rover_cfg,
            sweep_factors=param_sweeps,
        )

        sens_dict = sens.to_dict()
        sens_dict["schema_version"] = "1.0.0"
        return sens_dict
    except APIError:
        raise
    except Exception as err:
        raise APIError(f"Resource sensitivity analysis failed: {str(err)}", 500)
"""

if "def joint_mission_resource_evaluate_api" not in code:
    code = code + endpoints_code

with open("src/marswalk/api/service.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Service API update complete.")
