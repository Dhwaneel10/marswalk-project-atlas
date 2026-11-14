"""
MarsWalk 2.0 — Workspace & Experiment Library Persistence Service
Provides safe, atomic, versioned JSON filesystem storage for:
  1. Mission Definitions (data/workspaces/missions/)
  2. Simulation Experiments (data/workspaces/experiments/)
Includes historical separation, experiment replaying, side-by-side trade-off comparison,
and strict Draft 2020-12 contract validation.
"""

import os
import re
import json
import uuid
import copy
import datetime
import math
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import rasterio

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import ScienceWaypoint
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    validate_contract,
    sanitize_for_json,
    calculate_safe_pct_delta,
    compute_input_fingerprint,
    create_api_error_response,
    ContractValidationError,
)

# Base directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_MISSIONS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "missions")
DEFAULT_EXPERIMENTS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "experiments")
DEFAULT_CAMPAIGNS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaigns")
DEFAULT_OBSERVATIONS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "observations")
DEFAULT_CAMPAIGN_PROGRESS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_progress")
DEFAULT_RECOMMENDATIONS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "recommendations")
DEFAULT_CAMPAIGN_SCENARIOS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_scenarios")
DEFAULT_COORDINATION_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "coordination")
DEFAULT_HANDOFFS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "handoffs")
DEFAULT_SIMULATION_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_simulations")
DEFAULT_CAMPAIGN_ANALYTICS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_analytics")
DEFAULT_DESIGN_SPACE_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_design_spaces")
DEFAULT_CAMPAIGN_BENCHMARKS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_benchmarks")
DEFAULT_ROBUSTNESS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "mission_robustness")
DEFAULT_REHEARSALS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "rehearsals")
DEFAULT_CAMPAIGN_EXPERIMENTS_DIR = os.path.join(PROJECT_ROOT, "data", "workspaces", "campaign_experiments")

# Validation regex for secure record IDs (prevents directory traversal)
SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


class WorkspaceError(Exception):
    """Custom exception for workspace operations with status codes and machine error codes."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "ERR_WORKSPACE",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []


def validate_record_id(record_id: str, label: str = "Record") -> str:
    """Validate that record ID conforms to safe slug regex and is not a path traversal attempt."""
    if not record_id or not isinstance(record_id, str):
        raise WorkspaceError(
            f"{label} ID must be a non-empty string",
            status_code=400,
            error_code="ERR_INVALID_RECORD_ID",
        )
    clean_id = record_id.strip()
    if not SAFE_ID_REGEX.match(clean_id):
        raise WorkspaceError(
            f"{label} ID '{clean_id}' contains invalid characters. Must be 3-64 alphanumeric, dash, or underscore characters without path separators.",
            status_code=400,
            error_code="ERR_INVALID_RECORD_ID",
            details=[{"field": "record_id", "issue": "Must match ^[a-zA-Z0-9_-]{3,64}$", "value": clean_id}],
        )
    return clean_id


def get_current_iso_time() -> str:
    """Return UTC ISO 8601 timestamp string."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_write_json(filepath: str, data: Dict[str, Any]) -> None:
    """
    Safely write JSON dictionary to disk atomically using a sibling temp file and os.replace.
    Ensures that interrupted writes never corrupt or partially overwrite existing files.
    """
    target_dir = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(target_dir, exist_ok=True)

    temp_path = f"{filepath}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        clean_data = sanitize_for_json(data)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=2, ensure_ascii=False)
        # Atomic replace on Windows and POSIX
        os.replace(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise WorkspaceError(
            f"Failed to atomically persist record: {str(e)}",
            status_code=500,
            error_code="ERR_STORAGE_WRITE_FAILED",
        )


# =============================================================================
# 1. MISSION LIBRARY MANAGEMENT
# =============================================================================

def save_mission(
    mission_payload: Dict[str, Any],
    missions_dir: Optional[str] = None,
    allow_overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Save or update a mission configuration in the persistent mission library.
    Validates against saved-mission.schema.json and performs atomic write.
    """
    target_dir = missions_dir or DEFAULT_MISSIONS_DIR
    os.makedirs(target_dir, exist_ok=True)

    # 1. ID resolution
    mission_id = mission_payload.get("mission_id")
    if not mission_id:
        # Generate stable ID from name or timestamp
        name_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", mission_payload.get("name", "mission")).strip("_").lower()[:24]
        mission_id = f"m_{name_slug}_{uuid.uuid4().hex[:6]}"
    mission_id = validate_record_id(mission_id, "Mission")

    file_path = os.path.join(target_dir, f"{mission_id}.json")
    record_exists = os.path.exists(file_path)

    if record_exists and not allow_overwrite:
        raise WorkspaceError(
            f"Mission with ID '{mission_id}' already exists.",
            status_code=409,
            error_code="ERR_MISSION_ALREADY_EXISTS",
        )

    # 2. Extract or canonicalize inputs
    raw_cm = mission_payload.get("canonical_mission")
    if not isinstance(raw_cm, dict):
        raw_cm = {}

    canonical_mission = {
        "start": raw_cm.get("start") or mission_payload.get("start", {"row": 117, "col": 157}),
        "goal": raw_cm.get("goal") or mission_payload.get("goal", {"row": 194, "col": 131}),
        "stops": raw_cm.get("stops", mission_payload.get("stops", [])),
        "profile": raw_cm.get("profile", mission_payload.get("profile", "conservative")),
        "vehicle_mode": raw_cm.get("vehicle_mode", mission_payload.get("vehicle_mode", "crew_eva")),
        "speed_multiplier": raw_cm.get("speed_multiplier", mission_payload.get("speed_multiplier", 1.0)),
        "optimize_stops": raw_cm.get("optimize_stops", mission_payload.get("optimize_stops", False)),
        "mission_constraints": raw_cm.get("mission_constraints", mission_payload.get("mission_constraints", {})),
    }

    # 3. Input fingerprint
    input_fp = mission_payload.get("input_fingerprint")
    if not input_fp:
        input_fp = compute_input_fingerprint(
            canonical_mission,
            dataset_id=mission_payload.get("terrain_dataset_id", TERRAIN_DATASET_ID),
        )

    # 4. Timestamps
    now_iso = get_current_iso_time()
    created_at = mission_payload.get("created_at")
    if not created_at or not record_exists:
        created_at = now_iso
    updated_at = now_iso

    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mission_id": mission_id,
        "name": str(mission_payload.get("name", f"Mission {mission_id}")).strip()[:100],
        "description": str(mission_payload.get("description", ""))[:2000],
        "created_at": created_at,
        "updated_at": updated_at,
        "input_fingerprint": input_fp,
        "canonical_mission": canonical_mission,
        "terrain_dataset_id": mission_payload.get("terrain_dataset_id", TERRAIN_DATASET_ID),
        "model_version": mission_payload.get("model_version", "2.0.0"),
        "assumptions_version": mission_payload.get("assumptions_version", "1.0.0"),
        "tags": list(mission_payload.get("tags", [])),
    }

    # 5. Schema validation
    validate_contract(record, "saved-mission", raise_on_error=True)

    # 6. Atomic write
    atomic_write_json(file_path, record)
    return record


def list_missions(missions_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all saved missions with summary metadata, sorted by updated_at descending."""
    target_dir = missions_dir or DEFAULT_MISSIONS_DIR
    if not os.path.exists(target_dir):
        return []

    missions = []
    for entry in os.listdir(target_dir):
        if entry.endswith(".json"):
            file_path = os.path.join(target_dir, entry)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                canon = data.get("canonical_mission", {})
                missions.append({
                    "mission_id": data.get("mission_id", entry[:-5]),
                    "name": data.get("name", "Untitled Mission"),
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "input_fingerprint": data.get("input_fingerprint"),
                    "profile": canon.get("profile", "conservative"),
                    "vehicle_mode": canon.get("vehicle_mode", "crew_eva"),
                    "num_stops": len(canon.get("stops", [])),
                    "tags": data.get("tags", []),
                })
            except Exception:
                # Corrupt or partial file skipped gracefully
                continue

    missions.sort(key=lambda m: str(m.get("updated_at", "")), reverse=True)
    return missions


def get_mission(mission_id: str, missions_dir: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve full mission definition by ID."""
    clean_id = validate_record_id(mission_id, "Mission")
    target_dir = missions_dir or DEFAULT_MISSIONS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.isfile(file_path):
        raise WorkspaceError(
            f"Mission with ID '{clean_id}' was not found.",
            status_code=404,
            error_code="ERR_MISSION_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise WorkspaceError(
            f"Failed to read mission record '{clean_id}': {str(e)}",
            status_code=500,
            error_code="ERR_STORAGE_READ_FAILED",
        )


def update_mission(
    mission_id: str,
    update_data: Dict[str, Any],
    missions_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing mission. Preserves creation time and applies changes atomically."""
    clean_id = validate_record_id(mission_id, "Mission")
    existing = get_mission(clean_id, missions_dir=missions_dir)

    # Merge updates
    merged = copy.deepcopy(existing)
    if "name" in update_data:
        merged["name"] = str(update_data["name"]).strip()[:100]
    if "description" in update_data:
        merged["description"] = str(update_data["description"])[:2000]
    if "tags" in update_data:
        merged["tags"] = list(update_data["tags"])
    if "canonical_mission" in update_data:
        merged["canonical_mission"] = update_data["canonical_mission"]
        merged["input_fingerprint"] = compute_input_fingerprint(
            merged["canonical_mission"],
            dataset_id=merged.get("terrain_dataset_id", TERRAIN_DATASET_ID),
        )

    merged["mission_id"] = clean_id
    merged["updated_at"] = get_current_iso_time()

    validate_contract(merged, "saved-mission", raise_on_error=True)
    target_dir = missions_dir or DEFAULT_MISSIONS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")
    atomic_write_json(file_path, merged)
    return merged


def duplicate_mission(
    mission_id: str,
    new_name: Optional[str] = None,
    new_mission_id: Optional[str] = None,
    missions_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Duplicate an existing mission into an independent record with no shared mutable state."""
    clean_id = validate_record_id(mission_id, "Mission")
    orig = get_mission(clean_id, missions_dir=missions_dir)

    target_dir = missions_dir or DEFAULT_MISSIONS_DIR
    target_id = new_mission_id or f"{clean_id}_copy_{uuid.uuid4().hex[:4]}"
    target_id = validate_record_id(target_id, "Mission Copy")

    clone = copy.deepcopy(orig)
    clone["mission_id"] = target_id
    clone["name"] = new_name or f"{orig.get('name', clean_id)} (Copy)"
    now_iso = get_current_iso_time()
    clone["created_at"] = now_iso
    clone["updated_at"] = now_iso

    return save_mission(clone, missions_dir=target_dir, allow_overwrite=False)


def delete_mission(mission_id: str, missions_dir: Optional[str] = None) -> Dict[str, Any]:
    """Delete a mission record after ID validation."""
    clean_id = validate_record_id(mission_id, "Mission")
    target_dir = missions_dir or DEFAULT_MISSIONS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.isfile(file_path):
        raise WorkspaceError(
            f"Cannot delete mission '{clean_id}': record not found.",
            status_code=404,
            error_code="ERR_MISSION_NOT_FOUND",
        )

    try:
        os.remove(file_path)
        return {"deleted": True, "mission_id": clean_id, "message": f"Mission '{clean_id}' deleted successfully."}
    except Exception as e:
        raise WorkspaceError(
            f"Failed to delete mission '{clean_id}': {str(e)}",
            status_code=500,
            error_code="ERR_STORAGE_DELETE_FAILED",
        )


def import_mission_json(
    raw_json_str: str,
    missions_dir: Optional[str] = None,
    override_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse, validate, and persist an imported mission JSON string."""
    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as e:
        raise WorkspaceError(
            f"Malformed JSON: {str(e)}",
            status_code=400,
            error_code="ERR_MALFORMED_JSON",
        )

    if override_id:
        data["mission_id"] = override_id

    # Validate against saved-mission schema
    validate_contract(data, "saved-mission", raise_on_error=True)
    return save_mission(data, missions_dir=missions_dir, allow_overwrite=True)


# =============================================================================
# 2. EXPERIMENT LIBRARY & HISTORICAL SEPARATION
# =============================================================================

def evaluate_experiment_lifecycle(
    experiment: Dict[str, Any],
    current_mission: Optional[Dict[str, Any]] = None,
    current_dataset_id: str = TERRAIN_DATASET_ID,
) -> str:
    """
    Evaluate the reproducibility status of a saved experiment against current planner context.
    Returns one of:
      - 'failed': Computation failed at save time.
      - 'stale_incompatible': Dataset or model version mismatch.
      - 'reproducible': Current mission input fingerprint matches baseline fingerprint.
      - 'recalculation_required': Current mission inputs differ from experiment baseline.
      - 'historical_result': Standalone viewing of preserved historical run.
    """
    if experiment.get("status") in ("failed", "infeasible"):
        return "failed"

    if experiment.get("terrain_dataset_id") != current_dataset_id:
        return "stale_incompatible"

    if current_mission is not None:
        curr_fp = compute_input_fingerprint(current_mission, dataset_id=current_dataset_id)
        base_fp = experiment.get("baseline_fingerprint")
        if curr_fp == base_fp:
            return "reproducible"
        else:
            return "recalculation_required"

    return experiment.get("lifecycle_state", "historical_result")


def save_experiment(
    experiment_payload: Dict[str, Any],
    experiments_dir: Optional[str] = None,
    allow_overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Save an immutable simulation run to the experiment library.
    Validates against saved-experiment.schema.json and performs atomic write.
    """
    target_dir = experiments_dir or DEFAULT_EXPERIMENTS_DIR
    os.makedirs(target_dir, exist_ok=True)

    exp_id = experiment_payload.get("experiment_id")
    if not exp_id:
        name_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", experiment_payload.get("name", "experiment")).strip("_").lower()[:24]
        exp_id = f"exp_{name_slug}_{uuid.uuid4().hex[:6]}"
    exp_id = validate_record_id(exp_id, "Experiment")

    file_path = os.path.join(target_dir, f"{exp_id}.json")
    if os.path.exists(file_path) and not allow_overwrite:
        raise WorkspaceError(
            f"Experiment with ID '{exp_id}' already exists. Historical experiment records are immutable.",
            status_code=409,
            error_code="ERR_EXPERIMENT_ALREADY_EXISTS",
        )

    # Validate mission snapshot and baseline route
    mission_snapshot = experiment_payload.get("mission_snapshot")
    baseline_route = experiment_payload.get("baseline_route")
    if not mission_snapshot or not isinstance(mission_snapshot, dict):
        raise WorkspaceError(
            "Experiment must contain an authoritative 'mission_snapshot'",
            status_code=400,
            error_code="ERR_VALIDATION_FAILED",
        )
    if not baseline_route or not isinstance(baseline_route, dict):
        raise WorkspaceError(
            "Experiment must contain a baseline 'baseline_route' result",
            status_code=400,
            error_code="ERR_VALIDATION_FAILED",
        )

    base_fp = experiment_payload.get("baseline_fingerprint") or mission_snapshot.get("input_fingerprint")
    if not base_fp:
        base_fp = baseline_route.get("input_fingerprint") or ""

    status_val = experiment_payload.get("status", "success")
    if not baseline_route.get("is_reachable", True):
        status_val = "infeasible"

    lifecycle_state = experiment_payload.get("lifecycle_state", "historical_result")

    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": exp_id,
        "name": str(experiment_payload.get("name", f"Experiment {exp_id}")).strip()[:100],
        "description": str(experiment_payload.get("description", ""))[:2000],
        "created_at": experiment_payload.get("created_at") or get_current_iso_time(),
        "mission_id": experiment_payload.get("mission_id"),
        "status": status_val,
        "lifecycle_state": lifecycle_state,
        "baseline_fingerprint": base_fp,
        "mission_snapshot": mission_snapshot,
        "baseline_route": baseline_route,
        "scenarios_evaluated": list(experiment_payload.get("scenarios_evaluated", [])),
        "sensitivity_sweep": experiment_payload.get("sensitivity_sweep"),
        "recovery_plan": experiment_payload.get("recovery_plan"),
        "replayed_from_experiment_id": experiment_payload.get("replayed_from_experiment_id"),
        "reproducibility_notes": str(experiment_payload.get("reproducibility_notes", ""))[:2000],
        "terrain_dataset_id": experiment_payload.get("terrain_dataset_id", TERRAIN_DATASET_ID),
        "model_version": experiment_payload.get("model_version", "2.0.0"),
        "assumptions_version": experiment_payload.get("assumptions_version", "1.0.0"),
    }

    validate_contract(record, "saved-experiment", raise_on_error=True)
    atomic_write_json(file_path, record)
    return record


def list_experiments(experiments_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all saved experiments with summary metadata, sorted by created_at descending."""
    target_dir = experiments_dir or DEFAULT_EXPERIMENTS_DIR
    if not os.path.exists(target_dir):
        return []

    experiments = []
    for entry in os.listdir(target_dir):
        if entry.endswith(".json"):
            file_path = os.path.join(target_dir, entry)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                b_route = data.get("baseline_route", {})
                b_metrics = b_route.get("route_metrics", {})
                dist_m = b_metrics.get("ground_distance_m") if b_metrics else b_route.get("distance_m")
                active_s = b_metrics.get("active_traverse_time_s") if b_metrics else b_route.get("travel_time_s")

                experiments.append({
                    "experiment_id": data.get("experiment_id", entry[:-5]),
                    "name": data.get("name", "Untitled Experiment"),
                    "created_at": data.get("created_at"),
                    "mission_id": data.get("mission_id"),
                    "status": data.get("status", "success"),
                    "lifecycle_state": data.get("lifecycle_state", "historical_result"),
                    "baseline_fingerprint": data.get("baseline_fingerprint"),
                    "ground_distance_m": dist_m,
                    "active_traverse_time_s": active_s,
                    "num_scenarios": len(data.get("scenarios_evaluated", [])),
                    "replayed_from_experiment_id": data.get("replayed_from_experiment_id"),
                })
            except Exception:
                continue

    experiments.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return experiments


def get_experiment(experiment_id: str, experiments_dir: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve full experiment record by ID."""
    clean_id = validate_record_id(experiment_id, "Experiment")
    target_dir = experiments_dir or DEFAULT_EXPERIMENTS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.isfile(file_path):
        raise WorkspaceError(
            f"Experiment with ID '{clean_id}' was not found.",
            status_code=404,
            error_code="ERR_EXPERIMENT_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise WorkspaceError(
            f"Failed to read experiment record '{clean_id}': {str(e)}",
            status_code=500,
            error_code="ERR_STORAGE_READ_FAILED",
        )


def delete_experiment(experiment_id: str, experiments_dir: Optional[str] = None) -> Dict[str, Any]:
    """Delete an experiment record by ID."""
    clean_id = validate_record_id(experiment_id, "Experiment")
    target_dir = experiments_dir or DEFAULT_EXPERIMENTS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.isfile(file_path):
        raise WorkspaceError(
            f"Cannot delete experiment '{clean_id}': record not found.",
            status_code=404,
            error_code="ERR_EXPERIMENT_NOT_FOUND",
        )

    try:
        os.remove(file_path)
        return {"deleted": True, "experiment_id": clean_id, "message": f"Experiment '{clean_id}' deleted successfully."}
    except Exception as e:
        raise WorkspaceError(
            f"Failed to delete experiment '{clean_id}': {str(e)}",
            status_code=500,
            error_code="ERR_STORAGE_DELETE_FAILED",
        )


def duplicate_experiment(
    experiment_id: str,
    new_name: Optional[str] = None,
    new_experiment_id: Optional[str] = None,
    experiments_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Duplicate an existing experiment record into an independent record with no shared mutable state."""
    clean_id = validate_record_id(experiment_id, "Experiment")
    orig = get_experiment(clean_id, experiments_dir=experiments_dir)

    target_dir = experiments_dir or DEFAULT_EXPERIMENTS_DIR
    target_id = new_experiment_id or f"{clean_id}_copy_{uuid.uuid4().hex[:4]}"
    target_id = validate_record_id(target_id, "Experiment Copy")

    clone = copy.deepcopy(orig)
    clone["experiment_id"] = target_id
    clone["name"] = new_name or f"{orig.get('name', clean_id)} (Copy)"
    now_iso = get_current_iso_time()
    clone["created_at"] = now_iso

    return save_experiment(clone, experiments_dir=target_dir, allow_overwrite=False)



def replay_saved_experiment(
    experiment_id: str,
    terrain: TerrainGrid,
    transform: rasterio.Affine,
    waypoints: List[ScienceWaypoint],
    experiments_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Re-run a saved experiment under the active simulation engine and persist as a NEW distinct run.
    The original historical experiment record is strictly preserved without mutation.
    """
    orig_exp = get_experiment(experiment_id, experiments_dir=experiments_dir)
    snapshot = orig_exp.get("mission_snapshot", {})
    canon_mission = snapshot.get("canonical_mission", {})

    from marswalk.api.service import plan_route_api, scenario_comparison_api, scenario_sensitivity_api

    # 1. Recalculate baseline
    new_baseline = plan_route_api(canon_mission, terrain, transform, waypoints)

    # 2. Re-run scenarios if present
    orig_scenarios = orig_exp.get("scenarios_evaluated", [])
    new_scenarios = []
    new_rec_plan = None
    if orig_scenarios:
        comp_payload = {
            "baseline_mission": canon_mission,
            "scenario_ids": [s.get("scenario_id") for s in orig_scenarios if s.get("scenario_id")],
        }
        comp_res = scenario_comparison_api(comp_payload, terrain, transform, waypoints)
        new_scenarios = comp_res.get("scenarios", [])
        new_rec_plan = comp_res.get("recommended_recovery_plan")

    # 3. Create fresh run ID
    now_ts = int(datetime.datetime.now().timestamp())
    new_exp_id = f"{experiment_id}_replay_{now_ts}"
    new_exp_id = validate_record_id(new_exp_id, "Replay Experiment")

    # 4. Check exact match
    orig_b = orig_exp.get("baseline_route", {})
    orig_dist = orig_b.get("distance_m", orig_b.get("route_metrics", {}).get("ground_distance_m", 0.0))
    new_dist = new_baseline.get("distance_m", new_baseline.get("route_metrics", {}).get("ground_distance_m", 0.0))
    is_exact_match = (
        round(float(orig_dist), 1) == round(float(new_dist), 1)
        and orig_exp.get("baseline_fingerprint") == new_baseline.get("input_fingerprint")
    )

    repro_note = (
        f"Replay verified exact match ({new_dist:.1f} m)."
        if is_exact_match
        else f"Replay divergence detected: original={orig_dist:.1f} m, recomputed={new_dist:.1f} m."
    )

    new_payload = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": new_exp_id,
        "name": f"{orig_exp.get('name', experiment_id)} (Replay)",
        "description": f"Reproducibility replay of historical experiment {experiment_id}.",
        "created_at": get_current_iso_time(),
        "mission_id": orig_exp.get("mission_id"),
        "status": "success" if new_baseline.get("is_reachable") else "infeasible",
        "lifecycle_state": "reproducible" if is_exact_match else "historical_result",
        "baseline_fingerprint": new_baseline.get("input_fingerprint"),
        "mission_snapshot": new_baseline.get("mission_snapshot", snapshot),
        "baseline_route": new_baseline,
        "scenarios_evaluated": new_scenarios,
        "sensitivity_sweep": orig_exp.get("sensitivity_sweep"),
        "recovery_plan": new_rec_plan,
        "replayed_from_experiment_id": experiment_id,
        "reproducibility_notes": repro_note,
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "model_version": "2.0.0",
        "assumptions_version": "1.0.0",
    }

    # Save as new record
    saved_new = save_experiment(new_payload, experiments_dir=experiments_dir, allow_overwrite=False)
    saved_new["is_exact_match"] = is_exact_match
    return saved_new


# =============================================================================
# 3. EXPERIMENT TRADE-OFF COMPARISON ENGINE
# =============================================================================

def compare_two_experiments(
    exp_a_data: Union[str, Dict[str, Any]],
    exp_b_data: Union[str, Dict[str, Any]],
    experiments_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compare two saved experiments side-by-side with scientific honesty.
    Evaluates compatibility, multi-dimensional metric deltas, scenario parameter differences,
    and trade-offs without declaring a blind scalar winner.
    """
    # 1. Resolve experiment objects
    exp_a = get_experiment(exp_a_data, experiments_dir=experiments_dir) if isinstance(exp_a_data, str) else exp_a_data
    exp_b = get_experiment(exp_b_data, experiments_dir=experiments_dir) if isinstance(exp_b_data, str) else exp_b_data

    # 2. Compatibility check
    is_compatible = True
    incompat_reasons = []

    ds_a = exp_a.get("terrain_dataset_id", "")
    ds_b = exp_b.get("terrain_dataset_id", "")
    if ds_a != ds_b:
        is_compatible = False
        incompat_reasons.append(f"Incompatible terrain datasets: '{ds_a}' vs '{ds_b}'.")

    mv_a = exp_a.get("model_version", "")
    mv_b = exp_b.get("model_version", "")
    if mv_a != mv_b:
        is_compatible = False
        incompat_reasons.append(f"Incompatible planner model versions: '{mv_a}' vs '{mv_b}'.")

    # 3. Metric extraction
    b_route_a = exp_a.get("baseline_route", {})
    m_a = b_route_a.get("route_metrics", {})
    dist_a = m_a.get("ground_distance_m", b_route_a.get("distance_m"))
    time_a = m_a.get("active_traverse_time_s", b_route_a.get("travel_time_s"))
    tot_time_a = m_a.get("total_mission_time_s", time_a)
    effort_a = m_a.get("terrain_cost_flat_m", b_route_a.get("cost"))
    sci_a = m_a.get("science_score", b_route_a.get("science_score", 0.0))

    b_route_b = exp_b.get("baseline_route", {})
    m_b = b_route_b.get("route_metrics", {})
    dist_b = m_b.get("ground_distance_m", b_route_b.get("distance_m"))
    time_b = m_b.get("active_traverse_time_s", b_route_b.get("travel_time_s"))
    tot_time_b = m_b.get("total_mission_time_s", time_b)
    effort_b = m_b.get("terrain_cost_flat_m", b_route_b.get("cost"))
    sci_b = m_b.get("science_score", b_route_b.get("science_score", 0.0))

    # 4. Delta calculations
    dist_delta = round(dist_b - dist_a, 2) if (dist_a is not None and dist_b is not None) else None
    dist_pct = calculate_safe_pct_delta(dist_b, dist_a)

    time_delta = round(time_b - time_a, 1) if (time_a is not None and time_b is not None) else None
    time_pct = calculate_safe_pct_delta(time_b, time_a)

    tot_time_delta = round(tot_time_b - tot_time_a, 1) if (tot_time_a is not None and tot_time_b is not None) else None
    tot_time_pct = calculate_safe_pct_delta(tot_time_b, tot_time_a)

    effort_delta = round(effort_b - effort_a, 2) if (effort_a is not None and effort_b is not None) else None
    effort_pct = calculate_safe_pct_delta(effort_b, effort_a)

    sci_delta = round(sci_b - sci_a, 1) if (sci_a is not None and sci_b is not None) else None

    # 5. Science targets comparison
    stops_a = set(exp_a.get("mission_snapshot", {}).get("ordered_stop_ids", []))
    stops_b = set(exp_b.get("mission_snapshot", {}).get("ordered_stop_ids", []))
    retained = sorted(list(stops_a.intersection(stops_b)))
    lost = sorted(list(stops_a.difference(stops_b)))

    # 6. Scenario differences
    scen_a_ids = {s.get("scenario_id"): s.get("name") for s in exp_a.get("scenarios_evaluated", [])}
    scen_b_ids = {s.get("scenario_id"): s.get("name") for s in exp_b.get("scenarios_evaluated", [])}

    scenario_diffs: List[str] = []
    only_in_a = set(scen_a_ids.keys()) - set(scen_b_ids.keys())
    only_in_b = set(scen_b_ids.keys()) - set(scen_a_ids.keys())
    if only_in_a:
        scenario_diffs.append(f"Scenarios evaluated in A only: {', '.join(scen_a_ids[k] for k in only_in_a)}")
    if only_in_b:
        scenario_diffs.append(f"Scenarios evaluated in B only: {', '.join(scen_b_ids[k] for k in only_in_b)}")
    if not scenario_diffs:
        scenario_diffs.append("Both experiments evaluated identical scenario sets.")

    # 7. Honest Trade-offs synthesis
    trade_offs: List[str] = []
    if dist_delta is not None:
        if dist_delta < 0:
            trade_offs.append(f"Experiment B ground distance is shorter by {abs(dist_delta):.1f} m ({dist_pct}%).")
        elif dist_delta > 0:
            trade_offs.append(f"Experiment B ground distance is longer by {dist_delta:.1f} m (+{dist_pct}%).")
        else:
            trade_offs.append("Ground traverse distance is identical between both experiments.")

    if sci_delta is not None:
        if sci_delta < 0:
            trade_offs.append(f"Scientific return decreased by {abs(sci_delta):.1f} points in B ({len(lost)} stops omitted).")
        elif sci_delta > 0:
            trade_offs.append(f"Scientific return increased by {sci_delta:.1f} points in B.")
        else:
            trade_offs.append("Scientific score is identical between both runs.")

    if effort_delta is not None and effort_delta != 0:
        dir_text = "more" if effort_delta > 0 else "less"
        trade_offs.append(f"Terrain effort in B requires {abs(effort_delta):.1f} flat-m {dir_text} energy.")

    trade_offs.append(
        "Scientific Integrity Note: A shorter physical traverse does not inherently constitute an operationally superior plan "
        "if science objectives, terrain clearance, or consumable safety margins are compromised."
    )

    comparison_res: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "is_compatible": is_compatible,
        "incompatibility_reasons": incompat_reasons,
        "experiment_a": {
            "experiment_id": exp_a.get("experiment_id", "A"),
            "name": exp_a.get("name", "Experiment A"),
            "status": exp_a.get("status", "success"),
            "baseline_fingerprint": exp_a.get("baseline_fingerprint", ""),
            "distance_m": dist_a,
            "active_traverse_time_s": time_a,
            "total_mission_time_s": tot_time_a,
            "terrain_cost_flat_m": effort_a,
            "science_score": sci_a,
            "num_scenarios": len(exp_a.get("scenarios_evaluated", [])),
        },
        "experiment_b": {
            "experiment_id": exp_b.get("experiment_id", "B"),
            "name": exp_b.get("name", "Experiment B"),
            "status": exp_b.get("status", "success"),
            "baseline_fingerprint": exp_b.get("baseline_fingerprint", ""),
            "distance_m": dist_b,
            "active_traverse_time_s": time_b,
            "total_mission_time_s": tot_time_b,
            "terrain_cost_flat_m": effort_b,
            "science_score": sci_b,
            "num_scenarios": len(exp_b.get("scenarios_evaluated", [])),
        },
        "deltas": {
            "distance_delta_m": dist_delta,
            "distance_pct_delta": dist_pct,
            "active_time_delta_s": time_delta,
            "active_time_pct_delta": time_pct,
            "total_mission_time_delta_s": tot_time_delta,
            "total_mission_time_pct_delta": tot_time_pct,
            "effort_delta_flat_m": effort_delta,
            "effort_pct_delta": effort_pct,
            "science_score_delta": sci_delta,
        },
        "science_comparison": {
            "score_a": sci_a,
            "score_b": sci_b,
            "retained_targets": retained,
            "lost_targets": lost,
        },
        "scenario_differences": scenario_diffs,
        "trade_offs_summary": trade_offs,
    }

    validate_contract(comparison_res, "experiment-comparison-response", raise_on_error=True)
    return comparison_res


# =============================================================================
# 3. MISSION CAMPAIGN MANAGEMENT
# =============================================================================

def save_campaign(
    campaign_payload: Dict[str, Any],
    campaigns_dir: Optional[str] = None,
    allow_overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Save or update a multi-sol mission campaign in the persistent campaign library.
    Validates against mission-campaign.schema.json and performs atomic write.
    """
    target_dir = campaigns_dir or DEFAULT_CAMPAIGNS_DIR
    os.makedirs(target_dir, exist_ok=True)

    campaign_id = campaign_payload.get("campaign_id")
    if not campaign_id:
        name_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", campaign_payload.get("name", "campaign")).strip("_").lower()[:24]
        campaign_id = f"cmp_{name_slug}_{uuid.uuid4().hex[:6]}"
    campaign_id = validate_record_id(campaign_id, "Campaign")
    campaign_payload["campaign_id"] = campaign_id

    file_path = os.path.join(target_dir, f"{campaign_id}.json")
    if os.path.exists(file_path) and not allow_overwrite:
        raise WorkspaceError(
            f"Campaign with ID '{campaign_id}' already exists.",
            status_code=409,
            error_code="ERR_CAMPAIGN_ALREADY_EXISTS",
        )

    # Validate against schema
    validate_contract(campaign_payload, "mission-campaign", raise_on_error=True)

    atomic_write_json(file_path, campaign_payload)

    # Immutably archive this version snapshot if not already a versioned file
    version = int(campaign_payload.get("version", 1))
    if not re.search(r"_v\d+$", campaign_id):
        version_snapshot_path = os.path.join(target_dir, f"{campaign_id}_v{version}.json")
        atomic_write_json(version_snapshot_path, campaign_payload)

    return campaign_payload


def list_campaigns(campaigns_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all saved campaign summaries in data/workspaces/campaigns/."""
    target_dir = campaigns_dir or DEFAULT_CAMPAIGNS_DIR
    if not os.path.exists(target_dir):
        return []

    campaigns = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            # Exclude historical version snapshots from top-level library listing
            base_name = filename.replace(".json", "")
            if re.search(r"_v\d+$", base_name):
                continue
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    campaigns.append({
                        "campaign_id": data.get("campaign_id", filename.replace(".json", "")),
                        "name": data.get("name", "Untitled Campaign"),
                        "description": data.get("description", ""),
                        "version": data.get("version", 1),
                        "revision_id": data.get("revision_id", "rev_01"),
                        "created_at_utc": data.get("created_at_utc", ""),
                        "updated_at_utc": data.get("updated_at_utc", ""),
                        "total_sols": data.get("summary", {}).get("total_sols", 0),
                        "total_distance_m": data.get("summary", {}).get("total_distance_m", 0.0),
                        "total_duration_s": data.get("summary", {}).get("total_duration_s", 0.0),
                        "total_science_score": data.get("summary", {}).get("total_science_score", 0.0),
                        "targets_scheduled": data.get("summary", {}).get("targets_scheduled", 0),
                        "targets_total": data.get("summary", {}).get("targets_total", 0),
                        "overall_status": data.get("summary", {}).get("overall_status", "FEASIBLE"),
                    })
            except Exception:
                continue
    return campaigns


def get_campaign(campaign_id: str, campaigns_dir: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve full campaign JSON by campaign_id."""
    clean_id = validate_record_id(campaign_id, "Campaign")
    target_dir = campaigns_dir or DEFAULT_CAMPAIGNS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign with ID '{clean_id}' not found.",
            status_code=404,
            error_code="ERR_CAMPAIGN_NOT_FOUND",
        )

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def update_campaign(
    campaign_id: str,
    update_data: Dict[str, Any],
    campaigns_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Update existing campaign record atomically."""
    clean_id = validate_record_id(campaign_id, "Campaign")
    existing = get_campaign(clean_id, campaigns_dir)
    existing.update(update_data)
    existing["campaign_id"] = clean_id
    existing["updated_at_utc"] = get_current_iso_time()

    return save_campaign(existing, campaigns_dir, allow_overwrite=True)


def delete_campaign(campaign_id: str, campaigns_dir: Optional[str] = None) -> bool:
    """Safely delete campaign record by ID."""
    clean_id = validate_record_id(campaign_id, "Campaign")
    target_dir = campaigns_dir or DEFAULT_CAMPAIGNS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign with ID '{clean_id}' not found.",
            status_code=404,
            error_code="ERR_CAMPAIGN_NOT_FOUND",
        )

    os.remove(file_path)
    return True


# =============================================================================
# 7. SCIENCE OBSERVATION REGISTRY & CAMPAIGN PROGRESS WORKSPACE
# =============================================================================

def save_observation(
    observation_payload: Dict[str, Any],
    observations_dir: Optional[str] = None,
    allow_overwrite: bool = True,
) -> Dict[str, Any]:
    """Save a validated science observation record atomically in data/workspaces/observations/."""
    target_dir = observations_dir or DEFAULT_OBSERVATIONS_DIR
    os.makedirs(target_dir, exist_ok=True)

    obs_id = observation_payload.get("observation_id")
    if not obs_id:
        obs_id = f"obs_{uuid.uuid4().hex[:10]}"
    obs_id = validate_record_id(obs_id, "Science Observation")
    observation_payload["observation_id"] = obs_id

    file_path = os.path.join(target_dir, f"{obs_id}.json")
    if os.path.exists(file_path) and not allow_overwrite:
        raise WorkspaceError(
            f"Observation with ID '{obs_id}' already exists.",
            status_code=409,
            error_code="ERR_OBSERVATION_ALREADY_EXISTS",
        )

    # Validate against schema
    validate_contract(observation_payload, "science-observation", raise_on_error=True)
    atomic_write_json(file_path, observation_payload)
    return observation_payload


def get_observation(observation_id: str, observations_dir: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve science observation by ID."""
    clean_id = validate_record_id(observation_id, "Science Observation")
    target_dir = observations_dir or DEFAULT_OBSERVATIONS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Observation with ID '{clean_id}' not found.",
            status_code=404,
            error_code="ERR_OBSERVATION_NOT_FOUND",
        )

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_observations(
    campaign_id: Optional[str] = None,
    target_id: Optional[str] = None,
    observations_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List saved science observations with optional campaign/target filtering."""
    target_dir = observations_dir or DEFAULT_OBSERVATIONS_DIR
    if not os.path.exists(target_dir):
        return []

    results = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    if target_id and data.get("target_id") != target_id:
                        continue
                    results.append(data)
            except Exception:
                continue
    return results


def save_progress_event(
    event_payload: Dict[str, Any],
    progress_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a campaign progress event record atomically."""
    target_dir = progress_dir or DEFAULT_CAMPAIGN_PROGRESS_DIR
    os.makedirs(target_dir, exist_ok=True)

    ev_id = event_payload.get("event_id")
    if not ev_id:
        ev_id = f"cpe_{uuid.uuid4().hex[:10]}"
    ev_id = validate_record_id(ev_id, "Progress Event")
    event_payload["event_id"] = ev_id

    file_path = os.path.join(target_dir, f"{ev_id}.json")

    # Validate against schema
    validate_contract(event_payload, "campaign-progress-event", raise_on_error=True)
    atomic_write_json(file_path, event_payload)
    return event_payload


def list_progress_events(
    campaign_id: Optional[str] = None,
    progress_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all recorded campaign progress events chronologically."""
    target_dir = progress_dir or DEFAULT_CAMPAIGN_PROGRESS_DIR
    if not os.path.exists(target_dir):
        return []

    events = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    events.append(data)
            except Exception:
                continue

    # Sort by timestamp
    events.sort(key=lambda x: str(x.get("timestamp_utc", "")))
    return events


# ==============================================================================
# Milestone 11C: Campaign Intelligence Recommendation Persistence
# ==============================================================================

def save_recommendation(
    recommendation_payload: Dict[str, Any],
    recommendations_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Save an observation-driven campaign intelligence recommendation record atomically."""
    target_dir = recommendations_dir or DEFAULT_RECOMMENDATIONS_DIR
    os.makedirs(target_dir, exist_ok=True)

    rec_id = recommendation_payload.get("proposed_revision_id")
    cid = recommendation_payload.get("campaign_id", "cmp")
    if not rec_id:
        rec_id = f"rec_{uuid.uuid4().hex[:10]}"

    filename = f"{cid}_{rec_id}.json"
    file_path = os.path.join(target_dir, filename)

    # Validate against schema
    validate_contract(recommendation_payload, "campaign-reprioritization", raise_on_error=True)
    atomic_write_json(file_path, recommendation_payload)
    return recommendation_payload


def get_recommendation(
    campaign_id: str,
    revision_id: str,
    recommendations_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific campaign recommendation record by campaign ID and revision ID."""
    target_dir = recommendations_dir or DEFAULT_RECOMMENDATIONS_DIR
    filename = f"{campaign_id}_{revision_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Recommendation '{revision_id}' for campaign '{campaign_id}' not found",
            status_code=404,
            error_code="ERR_RECOMMENDATION_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt recommendation record: {err}", status_code=500)


def list_recommendations(
    campaign_id: Optional[str] = None,
    recommendations_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved campaign recommendations, optionally filtered by campaign_id."""
    target_dir = recommendations_dir or DEFAULT_RECOMMENDATIONS_DIR
    if not os.path.exists(target_dir):
        return []

    recs = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    recs.append(data)
            except Exception:
                continue

    recs.sort(key=lambda x: str(x.get("created_at_utc", "")), reverse=True)
    return recs


# ==============================================================================
# Milestone 11D: Campaign What-If Simulation Scenario Persistence
# ==============================================================================

def save_campaign_scenario(
    scenario_payload: Dict[str, Any],
    scenarios_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a campaign what-if simulation scenario record atomically."""
    target_dir = scenarios_dir or DEFAULT_CAMPAIGN_SCENARIOS_DIR
    os.makedirs(target_dir, exist_ok=True)

    scen_id = scenario_payload.get("scenario_id")
    if not scen_id:
        scen_id = f"scen_{uuid.uuid4().hex[:10]}"
        scenario_payload["scenario_id"] = scen_id

    filename = f"{scen_id}.json"
    file_path = os.path.join(target_dir, filename)

    # Validate against schema
    validate_contract(scenario_payload, "campaign-scenario", raise_on_error=True)
    atomic_write_json(file_path, scenario_payload)
    return scenario_payload


def get_campaign_scenario(
    scenario_id: str,
    scenarios_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific campaign what-if scenario record by scenario ID."""
    target_dir = scenarios_dir or DEFAULT_CAMPAIGN_SCENARIOS_DIR
    clean_id = validate_record_id(scenario_id, "Scenario")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign scenario '{scenario_id}' not found",
            status_code=404,
            error_code="ERR_SCENARIO_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt scenario record: {err}", status_code=500)


def list_campaign_scenarios(
    campaign_id: Optional[str] = None,
    scenarios_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved campaign what-if scenarios, optionally filtered by campaign_id."""
    target_dir = scenarios_dir or DEFAULT_CAMPAIGN_SCENARIOS_DIR
    if not os.path.exists(target_dir):
        return []

    scenarios = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    scenarios.append(data)
            except Exception:
                continue

    scenarios.sort(key=lambda x: str(x.get("created_at_utc", "")), reverse=True)
    return scenarios


# ==============================================================================
# Milestone 11E: Multi-Unit Campaign Coordination & Resource Handoffs Persistence
# ==============================================================================

def save_coordination_plan(
    coordination_data: Dict[str, Any],
    coordination_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save or update a multi-unit campaign coordination plan.
    Validates schema contract and writes atomically via temporary file.
    """
    target_dir = coordination_dir or DEFAULT_COORDINATION_DIR
    os.makedirs(target_dir, exist_ok=True)

    coord_id = coordination_data.get("coordination_id")
    if not coord_id:
        coord_id = f"coord_{uuid.uuid4().hex[:12]}"
        coordination_data["coordination_id"] = coord_id

    clean_id = validate_record_id(coord_id, "Coordination Plan")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    from marswalk.api.contracts import validate_campaign_coordination_record
    validate_campaign_coordination_record(coordination_data)

    clean_payload = sanitize_for_json(coordination_data)
    temp_path = f"{file_path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as err:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist coordination plan '{coord_id}': {err}", status_code=500)

    return clean_payload


def get_coordination_plan(
    coordination_id: str,
    coordination_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific campaign coordination plan by coordination ID."""
    target_dir = coordination_dir or DEFAULT_COORDINATION_DIR
    clean_id = validate_record_id(coordination_id, "Coordination Plan")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign coordination plan '{coordination_id}' not found",
            status_code=404,
            error_code="ERR_COORDINATION_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt coordination plan record: {err}", status_code=500)


def list_coordination_plans(
    campaign_id: Optional[str] = None,
    coordination_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved campaign coordination plans, optionally filtered by campaign_id."""
    target_dir = coordination_dir or DEFAULT_COORDINATION_DIR
    if not os.path.exists(target_dir):
        return []

    plans = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    plans.append(data)
            except Exception:
                continue

    plans.sort(key=lambda x: str(x.get("created_at_utc", "")), reverse=True)
    return plans


def save_task_handoff(
    handoff_data: Dict[str, Any],
    handoffs_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save or update a task responsibility handoff record.
    Writes atomically via temporary file.
    """
    target_dir = handoffs_dir or DEFAULT_HANDOFFS_DIR
    os.makedirs(target_dir, exist_ok=True)

    handoff_id = handoff_data.get("handoff_id")
    if not handoff_id:
        handoff_id = f"hnd_{uuid.uuid4().hex[:12]}"
        handoff_data["handoff_id"] = handoff_id

    clean_id = validate_record_id(handoff_id, "Task Handoff")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    clean_payload = sanitize_for_json(handoff_data)
    temp_path = f"{file_path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as err:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist task handoff '{handoff_id}': {err}", status_code=500)

    return clean_payload


def get_task_handoff(
    handoff_id: str,
    handoffs_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific task responsibility handoff record by handoff ID."""
    target_dir = handoffs_dir or DEFAULT_HANDOFFS_DIR
    clean_id = validate_record_id(handoff_id, "Task Handoff")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Task handoff '{handoff_id}' not found",
            status_code=404,
            error_code="ERR_HANDOFF_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt handoff record: {err}", status_code=500)


def list_task_handoffs(
    campaign_id: Optional[str] = None,
    handoffs_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved task handoffs, optionally filtered by campaign_id."""
    target_dir = handoffs_dir or DEFAULT_HANDOFFS_DIR
    if not os.path.exists(target_dir):
        return []

    handoffs = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    handoffs.append(data)
            except Exception:
                continue

    handoffs.sort(key=lambda x: str(x.get("created_at_utc", "")), reverse=True)
    return handoffs


# ==============================================================================
# Milestone 11F: Campaign Digital Twin Simulation Persistence
# ==============================================================================

def save_campaign_simulation(
    simulation_data: Dict[str, Any],
    simulation_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save or update a Campaign Digital Twin simulation record.
    Validates schema contract and writes atomically via temporary file.
    """
    target_dir = simulation_dir or DEFAULT_SIMULATION_DIR
    os.makedirs(target_dir, exist_ok=True)

    sim_id = simulation_data.get("simulation_id")
    if not sim_id:
        sim_id = f"sim_{uuid.uuid4().hex[:12]}"
        simulation_data["simulation_id"] = sim_id

    clean_id = validate_record_id(sim_id, "Campaign Simulation")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    from marswalk.api.contracts import validate_campaign_simulation_record
    validate_campaign_simulation_record(simulation_data)

    clean_payload = sanitize_for_json(simulation_data)
    temp_path = f"{file_path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as err:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist campaign simulation '{sim_id}': {err}", status_code=500)

    return clean_payload


def get_campaign_simulation(
    simulation_id: str,
    simulation_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific campaign simulation record by simulation ID."""
    target_dir = simulation_dir or DEFAULT_SIMULATION_DIR
    clean_id = validate_record_id(simulation_id, "Campaign Simulation")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign simulation '{simulation_id}' not found",
            status_code=404,
            error_code="ERR_SIMULATION_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt campaign simulation record: {err}", status_code=500)


def list_campaign_simulations(
    campaign_id: Optional[str] = None,
    simulation_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved campaign simulations, optionally filtered by campaign_id."""
    target_dir = simulation_dir or DEFAULT_SIMULATION_DIR
    if not os.path.exists(target_dir):
        return []

    simulations = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    simulations.append(data)
            except Exception:
                continue

    simulations.sort(key=lambda x: str(x.get("updated_at_utc", x.get("created_at_utc", ""))), reverse=True)
    return simulations


def save_campaign_analysis(
    analysis_data: Dict[str, Any],
    analytics_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist a campaign performance analytics record atomically to workspace.
    Validates against campaign-analytics.schema.json.
    """
    target_dir = analytics_dir or DEFAULT_CAMPAIGN_ANALYTICS_DIR
    os.makedirs(target_dir, exist_ok=True)

    anl_id = analysis_data.get("analysis_id")
    if not anl_id:
        raise WorkspaceError("Campaign analysis record missing 'analysis_id'", status_code=400)
    clean_id = validate_record_id(anl_id, "Campaign Analysis")

    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    from marswalk.api.contracts import validate_campaign_analytics_record
    validate_campaign_analytics_record(analysis_data)

    clean_payload = sanitize_for_json(analysis_data)
    temp_path = f"{file_path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as err:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist campaign analysis '{anl_id}': {err}", status_code=500)

    return clean_payload


def get_campaign_analysis(
    analysis_id: str,
    analytics_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific campaign performance analysis record by analysis ID."""
    target_dir = analytics_dir or DEFAULT_CAMPAIGN_ANALYTICS_DIR
    clean_id = validate_record_id(analysis_id, "Campaign Analysis")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign analysis '{analysis_id}' not found",
            status_code=404,
            error_code="ERR_ANALYSIS_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt campaign analysis record: {err}", status_code=500)


def list_campaign_analyses(
    campaign_id: Optional[str] = None,
    analytics_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved campaign performance analyses, optionally filtered by campaign_id."""
    target_dir = analytics_dir or DEFAULT_CAMPAIGN_ANALYTICS_DIR
    if not os.path.exists(target_dir):
        return []

    analyses = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    analyses.append(data)
            except Exception:
                continue

    analyses.sort(key=lambda x: str(x.get("created_at_utc", "")), reverse=True)
    return analyses


def update_recommendation_status(
    analysis_id: str,
    recommendation_id: str,
    status: str,
    analytics_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update the review status ('active', 'reviewed', 'dismissed') of a lessons learned recommendation.
    Persists updated analysis record atomically.
    """
    target_dir = analytics_dir or DEFAULT_CAMPAIGN_ANALYTICS_DIR
    clean_status = status.lower().strip()
    if clean_status not in ["active", "reviewed", "dismissed"]:
        raise WorkspaceError(
            f"Invalid recommendation status '{status}'. Must be 'active', 'reviewed', or 'dismissed'.",
            status_code=400,
            error_code="ERR_INVALID_STATUS",
        )

    analysis = get_campaign_analysis(analysis_id, analytics_dir=target_dir)
    found = False
    for rec in analysis.get("lessons_learned", []):
        if rec.get("recommendation_id") == recommendation_id:
            rec["status"] = clean_status
            found = True
            break

    if not found:
        raise WorkspaceError(
            f"Recommendation '{recommendation_id}' not found in analysis '{analysis_id}'.",
            status_code=404,
            error_code="ERR_RECOMMENDATION_NOT_FOUND",
        )

    return save_campaign_analysis(analysis, analytics_dir=target_dir)


def save_design_space_evaluation(
    data: Dict[str, Any],
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist a campaign design space exploration and Pareto record atomically to workspace.
    Validates against campaign-design-space.schema.json.
    """
    target_dir = workspace_dir or DEFAULT_DESIGN_SPACE_DIR
    os.makedirs(target_dir, exist_ok=True)

    ds_id = data.get("design_space_id")
    if not ds_id:
        raise WorkspaceError("Design space record missing 'design_space_id'", status_code=400)
    clean_id = validate_record_id(ds_id, "Campaign Design Space")

    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    from marswalk.api.contracts import validate_campaign_design_space_record
    validate_campaign_design_space_record(data)

    clean_payload = sanitize_for_json(data)
    temp_path = f"{file_path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as err:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist design space '{ds_id}': {err}", status_code=500)

    return clean_payload


def get_design_space_evaluation(
    design_space_id: str,
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve a specific design space evaluation by design_space_id."""
    target_dir = workspace_dir or DEFAULT_DESIGN_SPACE_DIR
    clean_id = validate_record_id(design_space_id, "Campaign Design Space")
    filename = f"{clean_id}.json"
    file_path = os.path.join(target_dir, filename)

    if not os.path.exists(file_path):
        raise WorkspaceError(
            f"Campaign design space '{design_space_id}' not found",
            status_code=404,
            error_code="ERR_DESIGN_SPACE_NOT_FOUND",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as err:
        raise WorkspaceError(f"Corrupt design space record: {err}", status_code=500)


def list_design_space_evaluations(
    campaign_id: Optional[str] = None,
    workspace_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all saved design space explorations, optionally filtered by campaign_id."""
    target_dir = workspace_dir or DEFAULT_DESIGN_SPACE_DIR
    if not os.path.exists(target_dir):
        return []

    results = []
    for filename in sorted(os.listdir(target_dir)):
        if filename.endswith(".json") and not filename.startswith("."):
            path = os.path.join(target_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if campaign_id and data.get("campaign_id") != campaign_id:
                        continue
                    results.append(data)
            except Exception:
                continue

    results.sort(key=lambda x: str(x.get("created_at_utc", "")), reverse=True)
    return results


def promote_design_space_candidate(
    design_space_id: str,
    candidate_id: str,
    new_campaign_name: Optional[str] = None,
    workspace_dir: Optional[str] = None,
    campaigns_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Promote a feasible design space candidate into a new campaign plan version (v{n+1}).
    Preserves the baseline campaign and past versions without modification.
    """
    clean_ds_id = validate_record_id(design_space_id, "Campaign Design Space")
    clean_cand_id = validate_record_id(candidate_id, "Candidate")

    ds_eval = get_design_space_evaluation(clean_ds_id, workspace_dir=workspace_dir)

    all_candidates = (
        ds_eval.get("pareto_candidates", []) +
        ds_eval.get("dominated_candidates", []) +
        ds_eval.get("infeasible_candidates", [])
    )
    candidate = next((c for c in all_candidates if c.get("candidate_id") == clean_cand_id), None)
    if not candidate:
        raise WorkspaceError(
            f"Candidate '{candidate_id}' not found in design space '{design_space_id}'",
            status_code=404,
            error_code="ERR_CANDIDATE_NOT_FOUND",
        )

    if candidate.get("status") != "FEASIBLE":
        reasons = candidate.get("infeasibility_reasons", ["Infeasible candidate configuration"])
        raise WorkspaceError(
            f"Cannot promote infeasible candidate '{candidate_id}': {'; '.join(reasons)}",
            status_code=400,
            error_code="ERR_CANDIDATE_INFEASIBLE",
        )

    camp_target_dir = campaigns_dir or workspace_dir
    base_campaign_id = ds_eval.get("campaign_id")
    base_campaign = get_campaign(base_campaign_id, campaigns_dir=camp_target_dir)

    new_version = int(base_campaign.get("version", 1)) + 1
    new_campaign_id = f"{base_campaign_id}_v{new_version}"
    name_str = new_campaign_name or f"{base_campaign.get('name', 'Campaign')} (Optimized v{new_version})"

    new_campaign_dict = copy.deepcopy(base_campaign)
    new_campaign_dict["campaign_id"] = new_campaign_id
    new_campaign_dict["version"] = new_version
    new_campaign_dict["name"] = name_str
    new_campaign_dict["parent_campaign_id"] = base_campaign_id

    # If candidate has planned sortie output or configuration deltas, apply them
    config_delta = candidate.get("configuration", {})
    base_cfg = new_campaign_dict.get("config", {})
    if "planning_profile" in config_delta:
        base_cfg["planning_profile"] = config_delta["planning_profile"]
    if "max_duration_per_sortie_s" in config_delta:
        base_cfg["max_duration_per_sortie_s"] = config_delta["max_duration_per_sortie_s"]
    if "max_sols" in config_delta:
        base_cfg["max_sols"] = config_delta["max_sols"]
    new_campaign_dict["config"] = base_cfg

    # If candidate had full planned campaign sorties stored
    if "sorties" in candidate:
        new_campaign_dict["sorties"] = candidate["sorties"]
    if "summary" in candidate:
        new_campaign_dict["summary"] = candidate["summary"]

    # Re-save campaign as a distinct new version
    saved_new_campaign = save_campaign(new_campaign_dict, campaigns_dir=camp_target_dir)

    return {
        "status": "success",
        "design_space_id": clean_ds_id,
        "promoted_candidate_id": clean_cand_id,
        "new_campaign_id": new_campaign_id,
        "new_version": new_version,
        "campaign": saved_new_campaign,
    }


def save_campaign_benchmark_result(
    record: Dict[str, Any],
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves a campaign benchmark suite result record atomically to workspace storage.
    Validates against campaign-benchmark.schema.json.
    """
    if not isinstance(record, dict):
        raise WorkspaceError("Benchmark record must be a JSON object", 400, "ERR_INVALID_PAYLOAD")

    suite_id = record.get("suite_id")
    if not suite_id:
        raise WorkspaceError("Benchmark record missing 'suite_id'", 400, "ERR_INVALID_PAYLOAD")

    clean_id = validate_record_id(suite_id, "Benchmark Suite")
    validate_contract(record, "campaign-benchmark", raise_on_error=True)

    target_dir = workspace_dir or DEFAULT_CAMPAIGN_BENCHMARKS_DIR
    os.makedirs(target_dir, exist_ok=True)

    file_path = os.path.join(target_dir, f"{clean_id}.json")
    tmp_path = f"{file_path}.tmp.{uuid.uuid4().hex[:8]}"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
        os.replace(tmp_path, file_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist benchmark record: {str(e)}", 500, "ERR_WRITE_FAILED")

    return record


def get_campaign_benchmark_result(
    suite_id: str,
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves a campaign benchmark suite result record by suite_id."""
    clean_id = validate_record_id(suite_id, "Benchmark Suite")
    target_dir = workspace_dir or DEFAULT_CAMPAIGN_BENCHMARKS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.exists(file_path):
        raise WorkspaceError(f"Benchmark suite '{clean_id}' not found", 404, "ERR_RECORD_NOT_FOUND")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise WorkspaceError(f"Failed to read benchmark record: {str(e)}", 500, "ERR_READ_FAILED")


def list_campaign_benchmark_results(
    workspace_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists saved campaign benchmark suite summary records, sorted by timestamp descending."""
    target_dir = workspace_dir or DEFAULT_CAMPAIGN_BENCHMARKS_DIR
    if not os.path.exists(target_dir):
        return []

    results = []
    for fname in os.listdir(target_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(target_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append({
                    "suite_id": data.get("suite_id"),
                    "timestamp_utc": data.get("timestamp_utc"),
                    "total_scenarios": data.get("total_scenarios", 0),
                    "passed_scenarios": data.get("passed_scenarios", 0),
                    "failed_scenarios": data.get("failed_scenarios", 0),
                    "total_candidates_evaluated": data.get("total_candidates_evaluated", 0),
                    "execution_time_s": data.get("execution_time_s", 0.0),
                    "reproducibility_verified": data.get("reproducibility_verified", False),
                })
            except Exception:
                continue

    results.sort(key=lambda r: r.get("timestamp_utc", ""), reverse=True)
    return results


def save_robustness_experiment(
    experiment_dict: Dict[str, Any],
    workspace_dir: Optional[str] = None,
    allow_overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Persists a Mission Robustness Lab experiment record to workspace storage.
    Validates contract against mission-robustness-experiment.json before saving.
    """
    if not isinstance(experiment_dict, dict):
        raise WorkspaceError("Experiment data must be a JSON dictionary", 400, "ERR_INVALID_PAYLOAD")

    exp_id = experiment_dict.get("experiment_id")
    if not exp_id:
        raise WorkspaceError("Experiment record missing required 'experiment_id'", 400, "ERR_MISSING_ID")

    clean_id = validate_record_id(exp_id, "Robustness Experiment")
    target_dir = workspace_dir or DEFAULT_ROBUSTNESS_DIR
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not allow_overwrite and os.path.exists(file_path):
        raise WorkspaceError(f"Experiment '{clean_id}' already exists", 409, "ERR_RECORD_EXISTS")

    clean_record = sanitize_for_json(experiment_dict)
    validate_contract(clean_record, "mission-robustness-experiment", raise_on_error=True)

    tmp_path = f"{file_path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(clean_record, f, indent=2)
        os.replace(tmp_path, file_path)
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise WorkspaceError(f"Failed to persist robustness experiment: {str(e)}", 500, "ERR_WRITE_FAILED")

    return clean_record


def get_robustness_experiment(
    experiment_id: str,
    workspace_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves a Mission Robustness Lab experiment record by experiment_id."""
    clean_id = validate_record_id(experiment_id, "Robustness Experiment")
    target_dir = workspace_dir or DEFAULT_ROBUSTNESS_DIR
    file_path = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.exists(file_path):
        raise WorkspaceError(f"Robustness experiment '{clean_id}' not found", 404, "ERR_RECORD_NOT_FOUND")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise WorkspaceError(f"Failed to read robustness experiment record: {str(e)}", 500, "ERR_READ_FAILED")


def list_robustness_experiments(
    target_id: Optional[str] = None,
    workspace_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists saved Mission Robustness Lab experiment summary records, sorted by timestamp descending."""
    target_dir = workspace_dir or DEFAULT_ROBUSTNESS_DIR
    if not os.path.exists(target_dir):
        return []

    results = []
    for fname in os.listdir(target_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(target_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if target_id and data.get("target_id") != target_id:
                    continue
                envelope = data.get("feasibility_envelope") or {}
                results.append({
                    "experiment_id": data.get("experiment_id"),
                    "created_at_utc": data.get("created_at_utc"),
                    "target_type": data.get("target_type"),
                    "target_id": data.get("target_id"),
                    "target_title": data.get("target_title"),
                    "suite_evaluated": data.get("suite_evaluated"),
                    "tested_cases_count": envelope.get("tested_cases_count", 0),
                    "feasible_cases_count": envelope.get("feasible_cases_count", 0),
                    "tested_feasibility_pct": envelope.get("tested_feasibility_pct", 0.0),
                    "recommended_strategy_id": data.get("recommended_strategy_id"),
                })
            except Exception:
                continue

    results.sort(key=lambda r: r.get("created_at_utc", ""), reverse=True)
    return results


def save_rehearsal_record(
    data: Dict[str, Any],
    rehearsals_dir: Optional[str] = None,
) -> str:
    """
    Saves a validated Mission Rehearsal Record to persistent workspace JSON.
    Guarantees atomic write and Draft 2020-12 contract compliance.
    """
    from marswalk.api.contracts import validate_mission_rehearsal_record

    target_dir = rehearsals_dir or DEFAULT_REHEARSALS_DIR
    os.makedirs(target_dir, exist_ok=True)

    if hasattr(data, "to_dict"):
        data = data.to_dict()

    rehearsal_id = data.get("rehearsal_id")
    if not rehearsal_id:
        raise WorkspaceError("Missing required 'rehearsal_id'", 400, "ERR_MISSING_ID")

    clean_id = validate_record_id(rehearsal_id, "Rehearsal")
    clean_data = sanitize_for_json(data)
    validate_mission_rehearsal_record(clean_data)

    filepath = os.path.join(target_dir, f"{clean_id}.json")
    try:
        atomic_write_json(filepath, clean_data)
        return clean_id
    except Exception as e:
        raise WorkspaceError(f"Failed to persist rehearsal record: {str(e)}", 500, "ERR_WRITE_FAILED")


def get_rehearsal_record(
    rehearsal_id: str,
    rehearsals_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves a saved Mission Rehearsal Record by ID."""
    clean_id = validate_record_id(rehearsal_id, "Rehearsal")
    target_dir = rehearsals_dir or DEFAULT_REHEARSALS_DIR
    filepath = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise WorkspaceError(f"Failed to read rehearsal record: {str(e)}", 500, "ERR_READ_FAILED")


def list_rehearsal_records(
    campaign_id: Optional[str] = None,
    rehearsals_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists saved Mission Rehearsal summary records, sorted by timestamp descending."""
    target_dir = rehearsals_dir or DEFAULT_REHEARSALS_DIR
    if not os.path.exists(target_dir):
        return []

    results = []
    for fname in os.listdir(target_dir):
        if fname.endswith(".json"):
            fpath = os.path.join(target_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if campaign_id and data.get("campaign_id") != campaign_id:
                    continue
                comp = data.get("comparison") or {}
                rec_m = data.get("recovered_metrics") or {}
                results.append({
                    "rehearsal_id": data.get("rehearsal_id"),
                    "campaign_id": data.get("campaign_id"),
                    "title": data.get("title"),
                    "status": data.get("status"),
                    "outcome_status": data.get("outcome_status"),
                    "created_at": data.get("created_at"),
                    "computation_fingerprint": data.get("computation_fingerprint"),
                    "disturbances_count": len(data.get("disturbances", [])),
                    "science_preservation_pct": comp.get("science_preservation_pct", 0.0),
                    "recovered_min_margin_s": rec_m.get("min_margin_s", 0.0),
                    "targets_retained_count": comp.get("targets_retained_count", 0),
                    "targets_dropped_count": comp.get("targets_dropped_count", 0),
                    "executive_assessment": comp.get("executive_assessment", ""),
                })
            except Exception:
                continue

    results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return results


def delete_rehearsal_record(
    rehearsal_id: str,
    rehearsals_dir: Optional[str] = None,
) -> bool:
    """Deletes a saved Mission Rehearsal Record by ID."""
    clean_id = validate_record_id(rehearsal_id, "Rehearsal")
    target_dir = rehearsals_dir or DEFAULT_REHEARSALS_DIR
    filepath = os.path.join(target_dir, f"{clean_id}.json")

    if not os.path.isfile(filepath):
        return False

    try:
        os.remove(filepath)
        return True
    except Exception as e:
        raise WorkspaceError(f"Failed to delete rehearsal record: {str(e)}", 500, "ERR_DELETE_FAILED")


# ==============================================================================
# MILESTONE 12H: ORCHESTRATED CAMPAIGN EXPERIMENT RECORD PERSISTENCE
# ==============================================================================

def save_experiment_record(
    data: Dict[str, Any],
    experiments_dir: Optional[str] = None,
    allow_overwrite: bool = False,
) -> str:
    """
    Saves a validated Orchestrated Mission Experiment Record to persistent workspace JSON.
    Guarantees atomic write and Draft 2020-12 contract compliance.
    """
    from marswalk.api.contracts import validate_mission_experiment_record

    target_dir = experiments_dir or DEFAULT_CAMPAIGN_EXPERIMENTS_DIR
    os.makedirs(target_dir, exist_ok=True)

    if hasattr(data, "to_dict"):
        data = data.to_dict()

    experiment_id = data.get("experiment_id")
    if not experiment_id:
        raise WorkspaceError("Missing required 'experiment_id'", 400, "ERR_MISSING_ID")

    clean_id = validate_record_id(experiment_id, "Experiment")
    clean_data = sanitize_for_json(data)
    validate_mission_experiment_record(clean_data)

    filepath = os.path.join(target_dir, f"{clean_id}.json")
    if not allow_overwrite and os.path.exists(filepath):
        raise WorkspaceError(
            f"Experiment record '{clean_id}' already exists and allow_overwrite is False",
            409,
            "ERR_RECORD_EXISTS",
        )

    try:
        atomic_write_json(filepath, clean_data)
        return clean_id
    except Exception as e:
        raise WorkspaceError(f"Failed to persist experiment record: {str(e)}", 500, "ERR_WRITE_FAILED")


def get_experiment_record(
    experiment_id: str,
    experiments_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves an orchestrated experiment record by ID."""
    clean_id = validate_record_id(experiment_id, "Experiment")
    target_dir = experiments_dir or DEFAULT_CAMPAIGN_EXPERIMENTS_DIR
    filepath = os.path.join(target_dir, f"{clean_id}.json")
    if not os.path.exists(filepath):
        raise WorkspaceError(f"Experiment record '{clean_id}' not found", 404, "ERR_NOT_FOUND")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sanitize_for_json(data)
    except Exception as e:
        raise WorkspaceError(f"Failed to read experiment record: {str(e)}", 500, "ERR_READ_FAILED")


def list_experiment_records(
    experiments_dir: Optional[str] = None,
    campaign_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists summary cards for all orchestrated experiment records."""
    target_dir = experiments_dir or DEFAULT_CAMPAIGN_EXPERIMENTS_DIR
    if not os.path.isdir(target_dir):
        return []

    results = []
    for fname in sorted(os.listdir(target_dir)):
        if not fname.endswith(".json"):
            continue
        filepath = os.path.join(target_dir, fname)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                d = json.load(f)
            if campaign_id and d.get("campaign_id") != campaign_id:
                continue
            results.append({
                "experiment_id": d.get("experiment_id"),
                "campaign_id": d.get("campaign_id"),
                "campaign_version": d.get("campaign_version"),
                "title": d.get("title"),
                "created_at_utc": d.get("created_at_utc"),
                "status": d.get("status"),
                "scenarios_count": len(d.get("scenarios", [])),
                "summary_metrics": d.get("summary_metrics", {}),
            })
        except Exception:
            continue
    return sorted(results, key=lambda x: x.get("created_at_utc", ""), reverse=True)


def delete_experiment_record(
    experiment_id: str,
    experiments_dir: Optional[str] = None,
) -> bool:
    """Deletes an orchestrated experiment record."""
    clean_id = validate_record_id(experiment_id, "Experiment")
    target_dir = experiments_dir or DEFAULT_CAMPAIGN_EXPERIMENTS_DIR
    filepath = os.path.join(target_dir, f"{clean_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


save_orchestrated_experiment = save_experiment_record
get_orchestrated_experiment = get_experiment_record
list_orchestrated_experiments = list_experiment_records
delete_orchestrated_experiment = delete_experiment_record









