"""
MarsWalk Core Dynamic Mission Connectivity Engine (Milestone 13D - Atlas Mars RelayNet).

Connects kinematic exploration-unit trajectories P(tau) to time-varying network connectivity states:
- At discrete timeline checkpoints, evaluates instantaneous line-of-sight to Base Station and active Relays.
- Resolves state hierarchy: CONNECTED_DIRECT (1 hop) -> CONNECTED_RELAYED (K >= 2 hops) -> SIMULATED_GEOMETRIC_CONNECTIVITY_GAP.
- Identifies gap root causes: TERRAIN_BLOCKED (with first contact obstruction coordinates) vs OUT_OF_RANGE.
- Coalesces contiguous gap checkpoints into continuous operational intervals.
- Generates summary statistics: total mission duration, connected availability percentage, max gap duration.
- Enforces cryptographic SHA-256 fingerprinting and deterministic in-memory caching for zero-latency client playback.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from typing import Dict, List, Tuple, Set, Optional, Any
import numpy as np

from marswalk.core.terrain_visibility import (
    calculate_line_of_sight,
    sample_bilinear_elevation,
    DEFAULT_DX_M,
    DEFAULT_DY_M,
)


class DynamicCommState(str, Enum):
    CONNECTED_DIRECT = "CONNECTED_DIRECT"
    CONNECTED_RELAYED = "CONNECTED_RELAYED"
    SIMULATED_GEOMETRIC_CONNECTIVITY_GAP = "SIMULATED_GEOMETRIC_CONNECTIVITY_GAP"


@dataclass(frozen=True)
class ConnectivityCheckpoint:
    time_s: float
    rc: Tuple[float, float]
    elevation_m: float
    communication_state: str  # DynamicCommState value
    active_path: List[str]
    hop_count: int
    primary_link_distance_m: Optional[float]
    min_path_clearance_m: Optional[float]
    gap_reason: Optional[str]  # "TERRAIN_BLOCKED", "OUT_OF_RANGE", or None
    nearest_node_id: Optional[str]
    nearest_node_distance_m: Optional[float]
    obstruction_rc: Optional[Tuple[float, float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_s": round(float(self.time_s), 2),
            "rc": [round(float(self.rc[0]), 2), round(float(self.rc[1]), 2)],
            "elevation_m": round(float(self.elevation_m), 2),
            "communication_state": self.communication_state,
            "active_path": self.active_path,
            "hop_count": self.hop_count,
            "primary_link_distance_m": round(float(self.primary_link_distance_m), 2) if self.primary_link_distance_m is not None else None,
            "min_path_clearance_m": round(float(self.min_path_clearance_m), 2) if self.min_path_clearance_m is not None else None,
            "gap_reason": self.gap_reason,
            "nearest_node_id": self.nearest_node_id,
            "nearest_node_distance_m": round(float(self.nearest_node_distance_m), 2) if self.nearest_node_distance_m is not None else None,
            "obstruction_rc": [round(float(self.obstruction_rc[0]), 2), round(float(self.obstruction_rc[1]), 2)] if self.obstruction_rc is not None else None,
        }


@dataclass(frozen=True)
class ConnectivityGapInterval:
    gap_id: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    reason: str  # "TERRAIN_BLOCKED" or "OUT_OF_RANGE"
    start_rc: Tuple[float, float]
    end_rc: Tuple[float, float]
    nearest_node_id: Optional[str]
    nearest_node_distance_m: Optional[float]
    obstruction_rc: Optional[Tuple[float, float]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "start_time_s": round(float(self.start_time_s), 2),
            "end_time_s": round(float(self.end_time_s), 2),
            "duration_s": round(float(self.duration_s), 2),
            "reason": self.reason,
            "start_rc": [round(float(self.start_rc[0]), 2), round(float(self.start_rc[1]), 2)],
            "end_rc": [round(float(self.end_rc[0]), 2), round(float(self.end_rc[1]), 2)],
            "nearest_node_id": self.nearest_node_id,
            "nearest_node_distance_m": round(float(self.nearest_node_distance_m), 2) if self.nearest_node_distance_m is not None else None,
            "obstruction_rc": [round(float(self.obstruction_rc[0]), 2), round(float(self.obstruction_rc[1]), 2)] if self.obstruction_rc is not None else None,
        }


# In-memory LRU cache for computed connectivity timelines
_TIMELINE_CACHE: Dict[str, Dict[str, Any]] = {}


def coalesce_gap_intervals(checkpoints: List[ConnectivityCheckpoint]) -> List[ConnectivityGapInterval]:
    """
    Coalesce contiguous gap checkpoints into continuous operational intervals.
    """
    gaps: List[ConnectivityGapInterval] = []
    current_gap: Optional[Dict[str, Any]] = None

    for cp in checkpoints:
        if cp.communication_state == DynamicCommState.SIMULATED_GEOMETRIC_CONNECTIVITY_GAP.value:
            if current_gap is None:
                current_gap = {
                    "gap_id": f"GAP_{len(gaps) + 1:03d}",
                    "start_time_s": cp.time_s,
                    "end_time_s": cp.time_s,
                    "reason": cp.gap_reason or "TERRAIN_BLOCKED",
                    "start_rc": cp.rc,
                    "end_rc": cp.rc,
                    "nearest_node_id": cp.nearest_node_id,
                    "nearest_node_distance_m": cp.nearest_node_distance_m,
                    "obstruction_rc": cp.obstruction_rc,
                }
            else:
                current_gap["end_time_s"] = cp.time_s
                current_gap["end_rc"] = cp.rc
                if current_gap["reason"] != "TERRAIN_BLOCKED" and cp.gap_reason == "TERRAIN_BLOCKED":
                    current_gap["reason"] = "TERRAIN_BLOCKED"
                if current_gap["obstruction_rc"] is None and cp.obstruction_rc is not None:
                    current_gap["obstruction_rc"] = cp.obstruction_rc
        else:
            if current_gap is not None:
                dur = max(0.0, current_gap["end_time_s"] - current_gap["start_time_s"])
                gaps.append(ConnectivityGapInterval(
                    gap_id=current_gap["gap_id"],
                    start_time_s=current_gap["start_time_s"],
                    end_time_s=current_gap["end_time_s"],
                    duration_s=round(dur, 2),
                    reason=current_gap["reason"],
                    start_rc=current_gap["start_rc"],
                    end_rc=current_gap["end_rc"],
                    nearest_node_id=current_gap["nearest_node_id"],
                    nearest_node_distance_m=current_gap["nearest_node_distance_m"],
                    obstruction_rc=current_gap["obstruction_rc"],
                ))
                current_gap = None

    if current_gap is not None:
        dur = max(0.0, current_gap["end_time_s"] - current_gap["start_time_s"])
        gaps.append(ConnectivityGapInterval(
            gap_id=current_gap["gap_id"],
            start_time_s=current_gap["start_time_s"],
            end_time_s=current_gap["end_time_s"],
            duration_s=round(dur, 2),
            reason=current_gap["reason"],
            start_rc=current_gap["start_rc"],
            end_rc=current_gap["end_rc"],
            nearest_node_id=current_gap["nearest_node_id"],
            nearest_node_distance_m=current_gap["nearest_node_distance_m"],
            obstruction_rc=current_gap["obstruction_rc"],
        ))

    return gaps


def compute_mission_connectivity_timeline(
    elevation: np.ndarray,
    trajectory_points: List[Tuple[float, float, float]],  # List of (time_s, row, col)
    base_station: Dict[str, Any],  # {"id": "BASE", "rc": (117, 157), "antenna_h": 10.0}
    relays: List[Dict[str, Any]],  # List of {"id": "RELAY_01", "rc": (r, c), "antenna_h": 10.0}
    direct_range_m: float = 2500.0,
    relay_range_m: float = 5000.0,
    rover_antenna_h_m: float = 2.5,
    dx_ground_m: float = DEFAULT_DX_M,
    dy_ground_m: float = DEFAULT_DY_M,
    invalid_mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Computes time-varying communication connectivity across a mission traverse.

    Parameters
    ----------
    elevation : np.ndarray
        Elevation matrix [H, W].
    trajectory_points : List[Tuple[float, float, float]]
        Chronological checkpoints (time_s, row, col).
    base_station : Dict[str, Any]
        Base station specification.
    relays : List[Dict[str, Any]]
        Active relay stations.
    direct_range_m : float
        Max range for rover-to-base direct link (default 2500m).
    relay_range_m : float
        Max range for rover-to-relay and relay-to-base links (default 5000m).
    rover_antenna_h_m : float
        Rover antenna height (default 2.5m).
    dx_ground_m : float
        East-West pixel size.
    dy_ground_m : float
        North-South pixel size.
    invalid_mask : Optional[np.ndarray]
        Invalid terrain mask.

    Returns
    -------
    Dict[str, Any]
        Complete timeline JSON payload matching the contract.
    """
    # Build cache key
    base_id = base_station.get("id", "BASE")
    base_rc = tuple(base_station["rc"])
    base_h = float(base_station.get("antenna_h", 10.0))

    sorted_relays = sorted(
        [{"id": r["id"], "rc": tuple(r["rc"]), "h": float(r.get("antenna_h", 10.0))} for r in relays],
        key=lambda x: x["id"],
    )

    cache_str = json.dumps({
        "base": [base_id, base_rc, base_h],
        "relays": [(r["id"], r["rc"], r["h"]) for r in sorted_relays],
        "traj_len": len(trajectory_points),
        "traj_bounds": [trajectory_points[0], trajectory_points[-1]] if trajectory_points else [],
        "ranges": [direct_range_m, relay_range_m, rover_antenna_h_m],
    }, sort_keys=True)
    fingerprint = hashlib.sha256(cache_str.encode("utf-8")).hexdigest()[:16]

    if fingerprint in _TIMELINE_CACHE:
        return _TIMELINE_CACHE[fingerprint]

    # Pre-evaluate static Relay <-> Base connectivity
    active_relays_connected_to_base: Set[str] = set()
    relay_to_base_los: Dict[str, Any] = {}

    for r in sorted_relays:
        res = calculate_line_of_sight(
            elevation_grid=elevation,
            point_a=r["rc"],
            point_b=base_rc,
            antenna_h_a=r["h"],
            antenna_h_b=base_h,
            dx_m=dx_ground_m,
            dy_m=dy_ground_m,
            max_range_m=relay_range_m,
            invalid_mask=invalid_mask,
            endpoint_a_id=r["id"],
            endpoint_b_id=base_id,
        )
        relay_to_base_los[r["id"]] = res
        if res.is_visible:
            active_relays_connected_to_base.add(r["id"])

    checkpoints: List[ConnectivityCheckpoint] = []

    for t_s, r_row, r_col in trajectory_points:
        z_rover, _ = sample_bilinear_elevation(elevation, r_row, r_col, invalid_mask)
        z_rover = z_rover if z_rover is not None else float(elevation[int(round(r_row)), int(round(r_col))])

        # 1. Try Direct to Base
        direct_los = calculate_line_of_sight(
            elevation_grid=elevation,
            point_a=(r_row, r_col),
            point_b=base_rc,
            antenna_h_a=rover_antenna_h_m,
            antenna_h_b=base_h,
            dx_m=dx_ground_m,
            dy_m=dy_ground_m,
            max_range_m=direct_range_m,
            invalid_mask=invalid_mask,
            endpoint_a_id="ROVER",
            endpoint_b_id=base_id,
        )

        if direct_los.is_visible:
            checkpoints.append(ConnectivityCheckpoint(
                time_s=t_s,
                rc=(r_row, r_col),
                elevation_m=z_rover,
                communication_state=DynamicCommState.CONNECTED_DIRECT.value,
                active_path=["ROVER", base_id],
                hop_count=1,
                primary_link_distance_m=direct_los.ground_distance_m,
                min_path_clearance_m=direct_los.min_clearance_m,
                gap_reason=None,
                nearest_node_id=base_id,
                nearest_node_distance_m=direct_los.ground_distance_m,
                obstruction_rc=None,
            ))
            continue

        # 2. Try Relayed through active relays connected to base
        relayed_success = False
        best_relay_id = None
        best_relay_dist = float("inf")
        best_relay_clearance = -float("inf")

        for r in sorted_relays:
            if r["id"] not in active_relays_connected_to_base:
                continue

            r_los = calculate_line_of_sight(
                elevation_grid=elevation,
                point_a=(r_row, r_col),
                point_b=r["rc"],
                antenna_h_a=rover_antenna_h_m,
                antenna_h_b=r["h"],
                dx_m=dx_ground_m,
                dy_m=dy_ground_m,
                max_range_m=relay_range_m,
                invalid_mask=invalid_mask,
                endpoint_a_id="ROVER",
                endpoint_b_id=r["id"],
            )

            if r_los.is_visible:
                relayed_success = True
                path_min_clear = min(r_los.min_clearance_m or 0.0, relay_to_base_los[r["id"]].min_clearance_m or 0.0)
                if path_min_clear > best_relay_clearance:
                    best_relay_clearance = path_min_clear
                    best_relay_id = r["id"]
                    best_relay_dist = r_los.ground_distance_m

        if relayed_success and best_relay_id is not None:
            checkpoints.append(ConnectivityCheckpoint(
                time_s=t_s,
                rc=(r_row, r_col),
                elevation_m=z_rover,
                communication_state=DynamicCommState.CONNECTED_RELAYED.value,
                active_path=["ROVER", best_relay_id, base_id],
                hop_count=2,
                primary_link_distance_m=best_relay_dist,
                min_path_clearance_m=best_relay_clearance,
                gap_reason=None,
                nearest_node_id=best_relay_id,
                nearest_node_distance_m=best_relay_dist,
                obstruction_rc=None,
            ))
            continue

        # 3. Connectivity Gap
        gap_reason = "TERRAIN_BLOCKED" if direct_los.is_terrain_blocked else "OUT_OF_RANGE"
        obs_rc = None
        if direct_los.first_obstruction is not None:
            obs_rc = (direct_los.first_obstruction.row, direct_los.first_obstruction.col)

        checkpoints.append(ConnectivityCheckpoint(
            time_s=t_s,
            rc=(r_row, r_col),
            elevation_m=z_rover,
            communication_state=DynamicCommState.SIMULATED_GEOMETRIC_CONNECTIVITY_GAP.value,
            active_path=[],
            hop_count=0,
            primary_link_distance_m=None,
            min_path_clearance_m=direct_los.min_clearance_m,
            gap_reason=gap_reason,
            nearest_node_id=base_id,
            nearest_node_distance_m=direct_los.ground_distance_m,
            obstruction_rc=obs_rc,
        ))

    gap_intervals = coalesce_gap_intervals(checkpoints)

    total_time = (trajectory_points[-1][0] - trajectory_points[0][0]) if len(trajectory_points) > 1 else 0.0
    direct_count = sum(1 for cp in checkpoints if cp.communication_state == DynamicCommState.CONNECTED_DIRECT.value)
    relayed_count = sum(1 for cp in checkpoints if cp.communication_state == DynamicCommState.CONNECTED_RELAYED.value)
    gap_count = sum(1 for cp in checkpoints if cp.communication_state == DynamicCommState.SIMULATED_GEOMETRIC_CONNECTIVITY_GAP.value)
    total_samples = max(1, len(checkpoints))

    total_gap_duration = sum(g.duration_s for g in gap_intervals)
    max_gap_duration = max([g.duration_s for g in gap_intervals], default=0.0)
    avail_pct = round(100.0 * float(direct_count + relayed_count) / float(total_samples), 1)

    result_payload = {
        "schema_version": "1.0.0",
        "fingerprint": fingerprint,
        "checkpoints": [cp.to_dict() for cp in checkpoints],
        "gap_intervals": [g.to_dict() for g in gap_intervals],
        "summary": {
            "total_mission_time_s": round(total_time, 2),
            "total_checkpoints": total_samples,
            "connected_direct_checkpoints": direct_count,
            "connected_relayed_checkpoints": relayed_count,
            "gap_checkpoints": gap_count,
            "total_gap_time_s": round(total_gap_duration, 2),
            "max_consecutive_gap_s": round(max_gap_duration, 2),
            "connectivity_availability_pct": avail_pct,
            "gap_count": len(gap_intervals),
        },
        "provenance": {
            "dataset_id": "USGS_CTX_DTM_JEZERO_20M",
            "source_doi": "10.5066/P906QQT8",
            "coordinate_reference_system": "ESRI:103885 (Equirectangular Mars Sphere)",
            "model_disclosures": [
                f"Direct rover-to-base maximum range assumption: {direct_range_m}m",
                f"Relay link maximum range assumption: {relay_range_m}m",
                f"Antenna mast heights: Base {base_h}m, Rover {rover_antenna_h_m}m",
                "Geometric line-of-sight based strictly on terrain surface clearance; does not model RF propagation.",
                "Simulated planning estimate only; not certified for astronaut operational safety."
            ],
        },
    }

    _TIMELINE_CACHE[fingerprint] = result_payload
    return result_payload
