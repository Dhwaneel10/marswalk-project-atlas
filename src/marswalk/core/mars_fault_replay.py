"""MarsWalk 2.0 / Project Atlas  Milestone 13R: Deterministic Fault Replay Engine.

Records and replays sequence-stamped resilience events with cryptographic
SHA-256 state hashing for bit-exact scientific reproducibility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReplayEventType(str, Enum):
    """Categorization of recordable resilience events."""
    FAULT_INJECTED = "FAULT_INJECTED"
    SYMPTOM_OBSERVED = "SYMPTOM_OBSERVED"
    DIAGNOSIS_CONFIRMED = "DIAGNOSIS_CONFIRMED"
    CASCADE_TRIGGERED = "CASCADE_TRIGGERED"
    BARRIER_ACTIVATED = "BARRIER_ACTIVATED"
    RECOVERY_DISPATCHED = "RECOVERY_DISPATCHED"
    METRIC_SNAPSHOT = "METRIC_SNAPSHOT"


@dataclass
class ReplayEvent:
    """An immutable, sequence-stamped operational resilience event."""
    sequence_id: int
    timestamp_sol_s: float
    event_type: ReplayEventType
    asset_id: str
    payload: Dict[str, Any]
    cumulative_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "timestamp_sol_s": self.timestamp_sol_s,
            "event_type": self.event_type.value,
            "asset_id": self.asset_id,
            "payload": self.payload,
            "cumulative_hash": self.cumulative_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReplayEvent:
        return cls(
            sequence_id=int(data["sequence_id"]),
            timestamp_sol_s=float(data["timestamp_sol_s"]),
            event_type=ReplayEventType(data["event_type"]),
            asset_id=data["asset_id"],
            payload=data["payload"],
            cumulative_hash=data.get("cumulative_hash", ""),
        )


class DeterministicFaultReplayEngine:
    """Records and verifies execution logs for bit-exact reproducibility."""

    def __init__(self):
        self._events: List[ReplayEvent] = []
        self._current_hash: str = "0000000000000000000000000000000000000000000000000000000000000000"

    def record_event(
        self,
        event_type: ReplayEventType,
        asset_id: str,
        timestamp_sol_s: float,
        payload: Dict[str, Any],
    ) -> ReplayEvent:
        """Appends an event and updates the running SHA-256 cryptographic chain."""
        seq = len(self._events) + 1

        # Calculate cumulative hash
        hasher = hashlib.sha256()
        hasher.update(self._current_hash.encode("utf-8"))
        hasher.update(str(seq).encode("utf-8"))
        hasher.update(str(timestamp_sol_s).encode("utf-8"))
        hasher.update(event_type.value.encode("utf-8"))
        hasher.update(asset_id.encode("utf-8"))
        hasher.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
        new_hash = hasher.hexdigest()

        event = ReplayEvent(
            sequence_id=seq,
            timestamp_sol_s=timestamp_sol_s,
            event_type=event_type,
            asset_id=asset_id,
            payload=payload,
            cumulative_hash=new_hash,
        )
        self._current_hash = new_hash
        self._events.append(event)
        return event

    def replay_log(self, event_log: List[ReplayEvent]) -> Dict[str, Any]:
        """Re-executes an event log and verifies cryptographic state hash continuity."""
        running_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        mismatches: List[Dict[str, Any]] = []

        for evt in event_log:
            hasher = hashlib.sha256()
            hasher.update(running_hash.encode("utf-8"))
            hasher.update(str(evt.sequence_id).encode("utf-8"))
            hasher.update(str(evt.timestamp_sol_s).encode("utf-8"))
            hasher.update(evt.event_type.value.encode("utf-8"))
            hasher.update(evt.asset_id.encode("utf-8"))
            hasher.update(json.dumps(evt.payload, sort_keys=True).encode("utf-8"))
            computed_hash = hasher.hexdigest()

            if computed_hash != evt.cumulative_hash:
                mismatches.append({
                    "sequence_id": evt.sequence_id,
                    "expected_hash": evt.cumulative_hash,
                    "computed_hash": computed_hash,
                })
            running_hash = computed_hash

        is_valid = (len(mismatches) == 0)
        return {
            "replayed_events_count": len(event_log),
            "is_bit_exact_reproducible": is_valid,
            "final_state_hash": running_hash,
            "hash_mismatches": mismatches,
        }

    def get_log(self) -> List[ReplayEvent]:
        return list(self._events)

    def get_final_hash(self) -> str:
        return self._current_hash

    def clear(self) -> None:
        self._events.clear()
        self._current_hash = "0000000000000000000000000000000000000000000000000000000000000000"
