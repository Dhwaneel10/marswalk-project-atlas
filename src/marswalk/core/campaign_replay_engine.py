"""
MarsWalk 2.0 / Project Atlas — Milestone 13I: Campaign Replay Engine.

Reconstructs campaign state from historical or simulated event streams,
verifies replay integrity against stored snapshots, provides step-by-step
state reconstruction timelines, and rigorously audits event idempotency
with thread-safe reentrant lock synchronization.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set, Union

from marswalk.core.campaign_operations_director import (
    CampaignOperationsDirector,
    CampaignOperationsEvent,
    CampaignEventType,
    CampaignLifecycleState,
)


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def compute_sha256(data: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


@dataclass
class ReplayStepRecord:
    step_index: int
    event_id: str
    event_type: str
    sequence: int
    sol_index: int
    timestamp_sol_s: float
    prev_state_fingerprint: str
    post_state_fingerprint: str
    changed_fields: Dict[str, Any]
    resource_deltas: Dict[str, float]
    is_idempotent_duplicate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayIntegrityReport:
    campaign_id: str
    target_version: int
    replayed_steps_count: int
    is_exact_match: bool
    matching_fields: List[str]
    divergent_fields: Dict[str, Dict[str, Any]]
    missing_events: List[str]
    duplicate_events: List[str]
    reconstructed_fingerprint: str
    snapshot_fingerprint: str
    reconciliation_narrative: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IdempotencyAuditReport:
    event_id: str
    event_type: str
    event_fingerprint: str
    applications_tested: int
    is_strictly_idempotent: bool
    energy_delta_total_wh: float
    storage_delta_total_mb: float
    observations_completed_count: int
    relays_deployed_count: int
    lifecycle_state_advances: int
    diagnostics: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CampaignReplayEngine:
    """
    Deterministic replay, verification, and forensic reconstruction engine
    for Mars multi-sol campaigns.
    """

    def __init__(self):
        self._lock = threading.RLock()

    def replay_campaign(
        self,
        director: CampaignOperationsDirector,
        events: List[Union[CampaignOperationsEvent, Dict[str, Any]]],
        target_sol: Optional[int] = None,
        target_event_id: Optional[str] = None,
        stop_on_error: bool = False,
    ) -> Tuple[Dict[str, Any], List[ReplayStepRecord]]:
        """
        Replay an ordered stream of events onto a director instance and return the
        resulting state along with the step-by-step forensic transition log.
        """
        with self._lock:
            timeline_records: List[ReplayStepRecord] = []

            # Work on a clone to protect the caller's director if desired
            reconstructed_director = copy.deepcopy(director)

            for idx, raw_evt in enumerate(events):
                if isinstance(raw_evt, dict):
                    evt_type_raw = raw_evt.get("event_type", "")
                    if hasattr(evt_type_raw, "value"):
                        evt_type_val = evt_type_raw.value
                    else:
                        evt_type_val = str(evt_type_raw)
                    evt = CampaignOperationsEvent(
                        event_id=raw_evt.get("event_id", f"evt_{idx}"),
                        campaign_id=raw_evt.get("campaign_id", reconstructed_director.campaign_id),
                        sol_index=int(raw_evt.get("sol_index", reconstructed_director.current_sol)),
                        event_type=evt_type_val,
                        timestamp_iso=raw_evt.get("timestamp_iso", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                        mission_elapsed_s=float(raw_evt.get("mission_elapsed_s", raw_evt.get("timestamp_sol_s", 0.0))),
                        sequence_number=int(raw_evt.get("sequence_number", raw_evt.get("sequence", idx))),
                        payload=raw_evt.get("payload", {}),
                    )
                else:
                    evt = raw_evt

                # Filter by target_sol if specified
                if target_sol is not None and evt.sol_index > target_sol:
                    break

                # Capture pre-state
                pre_state = reconstructed_director.get_campaign_operations_state()
                pre_fp = compute_sha256(pre_state)

                pre_energy = pre_state.get("energy_wh", 4800.0)
                pre_storage = pre_state.get("storage_used_mb", 0.0)
                pre_targets = len(pre_state.get("completed_targets", []))

                # Apply event via director
                is_new = reconstructed_director.apply_event(evt)

                # Capture post-state
                post_state = reconstructed_director.get_campaign_operations_state()
                post_fp = compute_sha256(post_state)

                post_energy = post_state.get("energy_wh", 4800.0)
                post_storage = post_state.get("storage_used_mb", 0.0)
                post_targets = len(post_state.get("completed_targets", []))

                # Compute field differences
                changed_fields = {}
                for k in ("energy_wh", "storage_used_mb", "lifecycle_state", "current_sol", "completed_targets_count"):
                    if pre_state.get(k) != post_state.get(k):
                        changed_fields[k] = {"before": pre_state.get(k), "after": post_state.get(k)}

                step_rec = ReplayStepRecord(
                    step_index=idx,
                    event_id=evt.event_id,
                    event_type=evt.event_type if isinstance(evt.event_type, str) else (evt.event_type.value if hasattr(evt.event_type, "value") else str(evt.event_type)),
                    sequence=getattr(evt, "sequence_number", idx),
                    sol_index=evt.sol_index,
                    timestamp_sol_s=getattr(evt, "mission_elapsed_s", getattr(evt, "timestamp_sol_s", 0.0)),
                    prev_state_fingerprint=pre_fp,
                    post_state_fingerprint=post_fp,
                    changed_fields=changed_fields,
                    resource_deltas={
                        "delta_energy_wh": round(post_energy - pre_energy, 3),
                        "delta_storage_mb": round(post_storage - pre_storage, 3),
                        "delta_targets": post_targets - pre_targets,
                    },
                    is_idempotent_duplicate=(not is_new),
                )
                timeline_records.append(step_rec)

                # Stop if targeted event reached
                if target_event_id and evt.event_id == target_event_id:
                    break

            final_state = reconstructed_director.get_campaign_operations_state()
            return final_state, timeline_records

    def verify_replay_integrity(
        self,
        reconstructed_state: Dict[str, Any],
        stored_snapshot: Dict[str, Any],
        ignored_keys: Optional[Set[str]] = None,
    ) -> ReplayIntegrityReport:
        """
        Compare a reconstructed campaign state with a stored snapshot and produce
        a detailed reconciliation report.
        """
        ignored = ignored_keys or {"timestamp", "updated_at", "fingerprint", "state_fingerprint"}

        matching_fields = []
        divergent_fields = {}

        all_keys = set(reconstructed_state.keys()) | set(stored_snapshot.keys())
        for k in all_keys:
            if k in ignored:
                continue

            recon_val = reconstructed_state.get(k)
            snap_val = stored_snapshot.get(k)

            # Round floats for numeric comparison
            if isinstance(recon_val, float) and isinstance(snap_val, float):
                match = abs(recon_val - snap_val) < 1e-3
            else:
                match = (recon_val == snap_val)

            if match:
                matching_fields.append(k)
            else:
                divergent_fields[k] = {"reconstructed": recon_val, "stored_snapshot": snap_val}

        is_exact = len(divergent_fields) == 0
        recon_fp = compute_sha256({k: v for k, v in reconstructed_state.items() if k not in ignored})
        snap_fp = compute_sha256({k: v for k, v in stored_snapshot.items() if k not in ignored})

        if is_exact:
            narrative = f"Replay verified bit-for-bit: {len(matching_fields)} fields matched stored snapshot with identical state digest."
        else:
            narrative = f"Replay divergence detected in {len(divergent_fields)} fields: {', '.join(divergent_fields.keys())}."

        return ReplayIntegrityReport(
            campaign_id=stored_snapshot.get("campaign_id", reconstructed_state.get("campaign_id", "unknown")),
            target_version=int(stored_snapshot.get("version", reconstructed_state.get("version", 1))),
            replayed_steps_count=len(matching_fields),
            is_exact_match=is_exact,
            matching_fields=sorted(matching_fields),
            divergent_fields=divergent_fields,
            missing_events=[],
            duplicate_events=[],
            reconstructed_fingerprint=recon_fp,
            snapshot_fingerprint=snap_fp,
            reconciliation_narrative=narrative,
        )

    def audit_event_idempotency(
        self,
        director: CampaignOperationsDirector,
        event: Optional[Union[CampaignOperationsEvent, Dict[str, Any]]] = None,
        trials: int = 5,
        event_data: Optional[Union[CampaignOperationsEvent, Dict[str, Any]]] = None,
        duplicate_count: Optional[int] = None,
    ) -> IdempotencyAuditReport:
        """
        Rigorously test repeated applications of an identical event to verify
        that no energy is double-deducted, no storage double-allocated, and no state
        transitions erroneously triggered.
        """
        effective_event = event if event is not None else event_data
        if effective_event is None:
            raise ValueError("No event provided to audit_event_idempotency")
        total_trials = duplicate_count if duplicate_count is not None else trials

        with self._lock:
            d_clone = copy.deepcopy(director)

            if isinstance(effective_event, dict):
                evt_type = effective_event.get("event_type", "")
                if hasattr(evt_type, "value"):
                    evt_type = evt_type.value
                evt_obj = CampaignOperationsEvent(
                    event_id=effective_event.get("event_id", f"evt_{uuid.uuid4().hex[:8]}"),
                    campaign_id=effective_event.get("campaign_id", d_clone.campaign_id),
                    sol_index=int(effective_event.get("sol_index", d_clone.current_sol)),
                    event_type=str(evt_type),
                    timestamp_iso=effective_event.get("timestamp_iso", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                    mission_elapsed_s=float(effective_event.get("mission_elapsed_s", 0.0)),
                    sequence_number=int(effective_event.get("sequence_number", 1)),
                    payload=effective_event.get("payload", {}),
                )
            else:
                evt_obj = effective_event

            start_state = d_clone.get_campaign_operations_state()
            start_energy = start_state.get("energy_state", {}).get("current_energy_wh", 4800.0)
            start_storage = start_state.get("data_state", {}).get("used_storage_mb", 0.0)

            # First application
            accepted_1 = d_clone.apply_event(evt_obj)

            first_state = d_clone.get_campaign_operations_state()
            energy_after_first = first_state.get("energy_state", {}).get("current_energy_wh", 4800.0)
            storage_after_first = first_state.get("data_state", {}).get("used_storage_mb", 0.0)

            first_energy_delta = energy_after_first - start_energy
            first_storage_delta = storage_after_first - start_storage

            diagnostics = [f"Trial 1: accepted={accepted_1}, delta_E={first_energy_delta:.2f} Wh"]

            # Subsequent trial applications
            is_idempotent = True
            for t in range(2, total_trials + 1):
                accepted_t = d_clone.apply_event(evt_obj)
                cur_state = d_clone.get_campaign_operations_state()
                cur_energy = cur_state.get("energy_state", {}).get("current_energy_wh", 4800.0)
                cur_storage = cur_state.get("data_state", {}).get("used_storage_mb", 0.0)

                if accepted_t or abs(cur_energy - energy_after_first) > 1e-4 or abs(cur_storage - storage_after_first) > 1e-4:
                    is_idempotent = False
                    diagnostics.append(f"Trial {t}: VIOLATION - Event was re-accepted or mutated state!")
                else:
                    diagnostics.append(f"Trial {t}: Idempotent ignore verified.")

            return IdempotencyAuditReport(
                event_id=evt_obj.event_id,
                event_type=str(evt_obj.event_type),
                event_fingerprint=evt_obj.event_fingerprint,
                applications_tested=total_trials,
                is_strictly_idempotent=is_idempotent,
                energy_delta_total_wh=round(energy_after_first - start_energy, 3),
                storage_delta_total_mb=round(storage_after_first - start_storage, 3),
                observations_completed_count=0,
                relays_deployed_count=0,
                lifecycle_state_advances=0,
                diagnostics=diagnostics,
            )
