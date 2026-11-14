"""
MarsWalk 2.0 — Milestone 10C: Sortie Black Box Mission Event Ledger.
Provides an append-only, validated, auditable mission event recording service
for mission tracking, mid-sortie emergency handoffs, and incident reconstruction.
"""

from __future__ import annotations

import os
import re
import json
import uuid
import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from marswalk.api.contracts import (
    validate_contract,
    sanitize_for_json,
    ContractValidationError,
)

# Project base directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_EVENTS_DIR = PROJECT_ROOT / "data" / "workspaces" / "events"

SAFE_MISSION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")
SAFE_EVENT_ID_REGEX = re.compile(r"^evt_[a-zA-Z0-9_-]{1,64}$")

MAX_EVENTS_PER_MISSION = 10000
MAX_EVENT_PAYLOAD_BYTES = 1024 * 1024  # 1 MB

VALID_EVENT_TYPES = frozenset([
    "sortie_started",
    "playback_checkpoint",
    "target_reached",
    "science_dwell_started",
    "science_dwell_completed",
    "operational_hold_started",
    "operational_hold_ended",
    "contingency_injected",
    "route_recalculated",
    "continuation_selected",
    "mission_completed",
    "mission_suspended",
    "mission_infeasible",
    "decision_pack_exported",
])

VALID_ROUTE_VARIANTS = frozenset([
    "nominal",
    "disrupted",
    "adaptive",
    "continuation",
])


class EventLedgerError(Exception):
    """Exception raised for event ledger errors."""

    def __init__(self, message: str, status_code: int = 400, error_code: str = "ERR_EVENT_LEDGER"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def generate_event_id() -> str:
    """Generate a random stable event identifier with standard prefix."""
    return f"evt_{uuid.uuid4().hex[:12]}"


def get_current_iso_time() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def validate_mission_id(mission_id: str) -> str:
    """Validate that mission_id conforms to safe regex."""
    if not mission_id or not isinstance(mission_id, str):
        raise EventLedgerError("source_mission_id must be a non-empty string", 400, "ERR_INVALID_MISSION_ID")
    clean_id = mission_id.strip()
    if not SAFE_MISSION_ID_REGEX.match(clean_id):
        raise EventLedgerError(
            f"source_mission_id '{clean_id}' contains invalid characters. Must be 3-64 alphanumeric, dash, or underscore characters.",
            400,
            "ERR_INVALID_MISSION_ID",
        )
    return clean_id


def validate_event_id(event_id: str) -> str:
    """Validate that event_id conforms to safe regex."""
    if not event_id or not isinstance(event_id, str):
        raise EventLedgerError("event_id must be a non-empty string", 400, "ERR_INVALID_EVENT_ID")
    clean_id = event_id.strip()
    if not SAFE_EVENT_ID_REGEX.match(clean_id):
        raise EventLedgerError(
            f"event_id '{clean_id}' contains invalid characters. Must start with 'evt_' followed by 4-64 alphanumeric, dash, or underscore characters.",
            400,
            "ERR_INVALID_EVENT_ID",
        )
    return clean_id


@dataclass(frozen=True)
class MissionEvent:
    """
    Immutable representation of an individual mission event in the Sortie Black Box.
    """
    event_id: str
    source_mission_id: str
    event_type: str
    mission_time_s: float
    playback_elapsed_s: float
    recorded_at_utc: str
    route_variant: str = "nominal"
    continuation_id: Optional[str] = None
    rover_rc: Optional[Tuple[int, int]] = None
    rover_float_rc: Optional[Tuple[float, float]] = None
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    speed_m_s: Optional[float] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(
        default_factory=lambda: {"source": "runtime", "is_recomputed": False, "algorithm_version": "10C"}
    )
    schema_version: str = "1.0.0"

    def __post_init__(self):
        # Validate event type
        if self.event_type not in VALID_EVENT_TYPES:
            raise EventLedgerError(
                f"Invalid event_type '{self.event_type}'. Must be one of: {sorted(VALID_EVENT_TYPES)}",
                400,
                "ERR_INVALID_EVENT_TYPE",
            )
        # Validate route variant
        if self.route_variant not in VALID_ROUTE_VARIANTS:
            raise EventLedgerError(
                f"Invalid route_variant '{self.route_variant}'. Must be one of: {sorted(VALID_ROUTE_VARIANTS)}",
                400,
                "ERR_INVALID_ROUTE_VARIANT",
            )
        # Validate times
        if self.mission_time_s < 0.0:
            raise EventLedgerError("mission_time_s cannot be negative", 400, "ERR_INVALID_TIME")
        if self.playback_elapsed_s < 0.0:
            raise EventLedgerError("playback_elapsed_s cannot be negative", 400, "ERR_INVALID_TIME")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSON serialization and contract validation."""
        d: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source_mission_id": self.source_mission_id,
            "continuation_id": self.continuation_id,
            "event_type": self.event_type,
            "mission_time_s": float(self.mission_time_s),
            "playback_elapsed_s": float(self.playback_elapsed_s),
            "recorded_at_utc": self.recorded_at_utc,
            "route_variant": self.route_variant,
            "rover_rc": list(self.rover_rc) if self.rover_rc is not None else None,
            "rover_float_rc": list(self.rover_float_rc) if self.rover_float_rc is not None else None,
            "elevation_m": float(self.elevation_m) if self.elevation_m is not None else None,
            "slope_deg": float(self.slope_deg) if self.slope_deg is not None else None,
            "speed_m_s": float(self.speed_m_s) if self.speed_m_s is not None else None,
            "payload": self.payload or {},
            "provenance": self.provenance or {"source": "runtime", "is_recomputed": False},
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MissionEvent:
        """Construct a MissionEvent from a dictionary with strict validation."""
        if not isinstance(data, dict):
            raise EventLedgerError("Event data must be a JSON dictionary", 400, "ERR_MALFORMED_EVENT")

        # Validate against JSON schema
        validate_contract(data, "mission-event")

        rover_rc_raw = data.get("rover_rc")
        rover_rc = (int(rover_rc_raw[0]), int(rover_rc_raw[1])) if rover_rc_raw else None

        rover_float_raw = data.get("rover_float_rc")
        rover_float_rc = (float(rover_float_raw[0]), float(rover_float_raw[1])) if rover_float_raw else None

        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            event_id=validate_event_id(str(data["event_id"])),
            source_mission_id=validate_mission_id(str(data["source_mission_id"])),
            continuation_id=str(data["continuation_id"]) if data.get("continuation_id") else None,
            event_type=str(data["event_type"]),
            mission_time_s=float(data.get("mission_time_s", 0.0)),
            playback_elapsed_s=float(data.get("playback_elapsed_s", 0.0)),
            recorded_at_utc=str(data.get("recorded_at_utc", get_current_iso_time())),
            route_variant=str(data.get("route_variant", "nominal")),
            rover_rc=rover_rc,
            rover_float_rc=rover_float_rc,
            elevation_m=float(data["elevation_m"]) if data.get("elevation_m") is not None else None,
            slope_deg=float(data["slope_deg"]) if data.get("slope_deg") is not None else None,
            speed_m_s=float(data["speed_m_s"]) if data.get("speed_m_s") is not None else None,
            payload=dict(data.get("payload", {})),
            provenance=dict(data.get("provenance", {"source": "runtime", "is_recomputed": False})),
        )


def get_ledger_dir(base_dir: Optional[Union[str, Path]] = None) -> Path:
    """Return Path to event ledger storage directory."""
    d = Path(base_dir) if base_dir else DEFAULT_EVENTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_ledger_filepath(source_mission_id: str, base_dir: Optional[Union[str, Path]] = None) -> Path:
    """Return Path to the event ledger JSON file for a mission."""
    clean_id = validate_mission_id(source_mission_id)
    return get_ledger_dir(base_dir) / f"{clean_id}_events.json"


def record_event(
    event: Union[MissionEvent, Dict[str, Any]],
    base_dir: Optional[Union[str, Path]] = None,
) -> MissionEvent:
    """
    Append an event to the mission's persistent Sortie Black Box ledger atomically.
    Ensures idempotency: if an event with identical event_id already exists, it is not duplicated.
    """
    if isinstance(event, dict):
        if "event_id" not in event or not event["event_id"]:
            event["event_id"] = generate_event_id()
        if "recorded_at_utc" not in event or not event["recorded_at_utc"]:
            event["recorded_at_utc"] = get_current_iso_time()
        evt_obj = MissionEvent.from_dict(event)
    elif isinstance(event, MissionEvent):
        evt_obj = event
    else:
        raise EventLedgerError("event must be a MissionEvent or dictionary", 400, "ERR_INVALID_EVENT")

    ledger_path = get_ledger_filepath(evt_obj.source_mission_id, base_dir=base_dir)
    existing_events = _read_ledger_file(ledger_path)

    # Check for duplicate event_id (idempotent retry safety)
    for existing in existing_events:
        if existing.event_id == evt_obj.event_id:
            return existing

    if len(existing_events) >= MAX_EVENTS_PER_MISSION:
        raise EventLedgerError(
            f"Mission event ledger reached maximum capacity of {MAX_EVENTS_PER_MISSION} events.",
            400,
            "ERR_LEDGER_CAPACITY_EXCEEDED",
        )

    updated_events = existing_events + [evt_obj]
    _write_ledger_file(ledger_path, updated_events)
    return evt_obj


def record_events_batch(
    events: List[Union[MissionEvent, Dict[str, Any]]],
    source_mission_id: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> List[MissionEvent]:
    """
    Append a batch of events to the mission event ledger atomically.
    """
    if not isinstance(events, list):
        raise EventLedgerError("events must be a list", 400, "ERR_INVALID_BATCH")

    if not events:
        return []

    if len(events) > 500:
        raise EventLedgerError("Batch event limit is 500 events per request", 400, "ERR_BATCH_TOO_LARGE")

    # Parse and validate all events in memory
    parsed_events: List[MissionEvent] = []
    target_mission_id = source_mission_id

    for raw in events:
        if isinstance(raw, dict):
            if target_mission_id and "source_mission_id" not in raw:
                raw["source_mission_id"] = target_mission_id
            if "event_id" not in raw or not raw["event_id"]:
                raw["event_id"] = generate_event_id()
            if "recorded_at_utc" not in raw or not raw["recorded_at_utc"]:
                raw["recorded_at_utc"] = get_current_iso_time()
            evt = MissionEvent.from_dict(raw)
        elif isinstance(raw, MissionEvent):
            evt = raw
        else:
            raise EventLedgerError("All batch elements must be MissionEvent or dict", 400, "ERR_INVALID_EVENT")

        if target_mission_id is None:
            target_mission_id = evt.source_mission_id
        elif evt.source_mission_id != target_mission_id:
            raise EventLedgerError(
                f"Batch contains mixed source_mission_ids: '{target_mission_id}' vs '{evt.source_mission_id}'",
                400,
                "ERR_MIXED_BATCH_MISSIONS",
            )
        parsed_events.append(evt)

    assert target_mission_id is not None
    ledger_path = get_ledger_filepath(target_mission_id, base_dir=base_dir)
    existing_events = _read_ledger_file(ledger_path)
    existing_ids = {e.event_id for e in existing_events}

    new_events = [e for e in parsed_events if e.event_id not in existing_ids]

    if len(existing_events) + len(new_events) > MAX_EVENTS_PER_MISSION:
        raise EventLedgerError(
            f"Batch would exceed maximum ledger capacity of {MAX_EVENTS_PER_MISSION} events.",
            400,
            "ERR_LEDGER_CAPACITY_EXCEEDED",
        )

    all_events = existing_events + new_events
    _write_ledger_file(ledger_path, all_events)
    return parsed_events


def get_mission_events(
    source_mission_id: str,
    continuation_id: Optional[str] = None,
    event_type: Optional[str] = None,
    since_time_s: Optional[float] = None,
    until_time_s: Optional[float] = None,
    limit: Optional[int] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> List[MissionEvent]:
    """
    Retrieve chronological events for a mission with optional filtering.
    Always returns events deterministically ordered by (mission_time_s, playback_elapsed_s, event_id).
    If the mission has no recorded event ledger, returns an empty list without error.
    """
    ledger_path = get_ledger_filepath(source_mission_id, base_dir=base_dir)
    events = _read_ledger_file(ledger_path)

    # Sort deterministically
    events.sort(key=lambda e: (e.mission_time_s, e.playback_elapsed_s, e.event_id))

    # Apply filters
    filtered = events
    if continuation_id is not None:
        filtered = [e for e in filtered if e.continuation_id == continuation_id]
    if event_type is not None:
        filtered = [e for e in filtered if e.event_type == event_type]
    if since_time_s is not None:
        filtered = [e for e in filtered if e.mission_time_s >= since_time_s]
    if until_time_s is not None:
        filtered = [e for e in filtered if e.mission_time_s <= until_time_s]

    if limit is not None and limit > 0:
        filtered = filtered[:limit]

    return filtered


def clear_mission_events(source_mission_id: str, base_dir: Optional[Union[str, Path]] = None) -> bool:
    """Safely clear/delete the event ledger for a mission."""
    ledger_path = get_ledger_filepath(source_mission_id, base_dir=base_dir)
    if ledger_path.exists():
        try:
            ledger_path.unlink()
            return True
        except OSError:
            return False
    return False


def _read_ledger_file(filepath: Path) -> List[MissionEvent]:
    """Read and deserialize events from a JSON file."""
    if not filepath.exists():
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        events: List[MissionEvent] = []
        for item in data:
            try:
                events.append(MissionEvent.from_dict(item))
            except Exception:
                # Discard corrupted records without crashing entire history
                continue
        return events
    except Exception:
        return []


def _write_ledger_file(filepath: Path, events: List[MissionEvent]) -> None:
    """Atomically write a list of events to JSON file using a sibling temp file."""
    target_dir = filepath.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    temp_path = filepath.with_suffix(f".tmp_{uuid.uuid4().hex[:8]}")
    payload = [e.to_dict() for e in events]
    clean_data = sanitize_for_json(payload)

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)

    os.replace(temp_path, filepath)
