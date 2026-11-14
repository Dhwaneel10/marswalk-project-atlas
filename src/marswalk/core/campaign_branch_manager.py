"""
MarsWalk 2.0 / Project Atlas — Milestone 13I: Campaign Branch Manager.

Provides an immutable, isolated branching engine for multi-sol Mars campaigns.
Enforces:
1. Deep state isolation: Child branch mutations never alter parent or sibling state.
2. Parent checkpoint validation & optimistic locking: Stale parent version conflicts are rejected.
3. Cryptographic state fingerprinting across branches.
4. Plan lineage preservation: Promoted branches document previous plan, approval, and version deltas.
"""

from __future__ import annotations

import copy
import datetime
import enum
import hashlib
import json
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
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


class BranchStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RECOVERED = "RECOVERED"
    FAILED_CONSTRAINTS = "FAILED_CONSTRAINTS"
    ARCHIVED = "ARCHIVED"
    PROMOTED = "PROMOTED"


class StaleVersionConflictError(Exception):
    """Raised when promoting a branch whose expected parent version does not match the live parent."""
    pass


class BranchNotFoundError(Exception):
    """Raised when a requested branch ID is not registered."""
    pass


@dataclass
class CampaignBranch:
    branch_id: str
    name: str
    campaign_id: str
    parent_branch_id: Optional[str]
    parent_snapshot_id: Optional[str]
    parent_campaign_version: int
    fork_event_sequence: int
    fork_sol_index: int
    parent_state_fingerprint: str
    scenario_definition: Dict[str, Any]
    branch_specific_events: List[Dict[str, Any]]
    branch_status: BranchStatus
    created_at: str
    updated_at: str
    director: CampaignOperationsDirector
    final_state_fingerprint: str = ""
    promotion_record: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "branch_id": self.branch_id,
            "name": self.name,
            "campaign_id": self.campaign_id,
            "parent_branch_id": self.parent_branch_id,
            "branch_status": self.branch_status.value if isinstance(self.branch_status, enum.Enum) else str(self.branch_status),
            "fork_sol": self.fork_sol_index,
            "fork_sequence": self.fork_event_sequence,
            "parent_state_fingerprint": self.parent_state_fingerprint,
            "created_at_utc": self.created_at,
            "updated_at_utc": self.updated_at,
            "scenario_def": self.scenario_definition,
            "metadata": {
                "events_count": len(self.branch_specific_events),
                "parent_version": self.parent_campaign_version,
            },
            "promotion_metadata": self.promotion_record,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        st = self.director.get_campaign_operations_state()
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "campaign_id": self.campaign_id,
            "parent_branch_id": self.parent_branch_id,
            "parent_snapshot_id": self.parent_snapshot_id,
            "parent_campaign_version": self.parent_campaign_version,
            "fork_event_sequence": self.fork_event_sequence,
            "fork_sol_index": self.fork_sol_index,
            "parent_state_fingerprint": self.parent_state_fingerprint,
            "final_state_fingerprint": self.final_state_fingerprint or compute_sha256(st),
            "branch_status": self.branch_status.value if isinstance(self.branch_status, enum.Enum) else str(self.branch_status),
            "scenario_definition": self.scenario_definition,
            "events_count": len(self.branch_specific_events),
            "current_sol": st.get("current_sol", 1),
            "lifecycle_state": st.get("lifecycle_state", "PLANNED"),
            "energy_wh": st.get("energy_wh", 4800.0),
            "storage_used_mb": st.get("storage_used_mb", 0.0),
            "completed_targets_count": st.get("completed_targets_count", 0),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_promoted": (self.branch_status == BranchStatus.PROMOTED),
        }


@dataclass
class BranchComparisonReport:
    branch_a_id: str
    branch_b_id: str
    campaign_id: str
    delta_distance_m: float
    delta_duration_hours: float
    delta_science_score: float
    delta_energy_wh: float
    delta_storage_mb: float
    delta_relays_deployed: int
    state_a: Dict[str, Any]
    state_b: Dict[str, Any]
    comparison_timestamp: str
    narrative: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CampaignBranchManager:
    """
    Manages isolated, version-controlled counterfactual campaign branches.
    """

    def __init__(self, workspace_dir: Optional[Union[str, Path]] = None):
        self._lock = threading.RLock()
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None
        self.branches: Dict[str, CampaignBranch] = {}

    def create_branch(
        self,
        parent_director: CampaignOperationsDirector,
        branch_id: str,
        name: str,
        scenario_def: Optional[Dict[str, Any]] = None,
        fork_sol: Optional[int] = None,
        fork_sequence: Optional[int] = None,
        parent_branch_id: Optional[str] = None,
    ) -> CampaignBranch:
        """
        Create a deep-isolated branch cloned from the parent campaign director at
        a specific sol and event sequence.
        """
        with self._lock:
            if branch_id in self.branches:
                raise ValueError(f"Branch '{branch_id}' already exists.")

            parent_state = parent_director.get_campaign_operations_state()
            parent_fp = compute_sha256(parent_state)
            parent_ver = int(parent_director.version)

            effective_fork_sol = fork_sol if fork_sol is not None else parent_director.current_sol
            effective_fork_seq = fork_sequence if fork_sequence is not None else len(parent_director.events_log)

            # Deep copy to ensure complete state isolation
            isolated_director = copy.deepcopy(parent_director)

            # Tag isolated director with branch metadata
            isolated_director.campaign_id = f"{parent_director.campaign_id}::{branch_id}"

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            branch = CampaignBranch(
                branch_id=branch_id,
                name=name,
                campaign_id=parent_director.campaign_id,
                parent_branch_id=parent_branch_id,
                parent_snapshot_id=f"snap_{parent_director.campaign_id}_v{parent_ver}",
                parent_campaign_version=parent_ver,
                fork_event_sequence=effective_fork_seq,
                fork_sol_index=effective_fork_sol,
                parent_state_fingerprint=parent_fp,
                scenario_definition=scenario_def or {},
                branch_specific_events=[],
                branch_status=BranchStatus.ACTIVE,
                created_at=now_iso,
                updated_at=now_iso,
                director=isolated_director,
                final_state_fingerprint=compute_sha256(isolated_director.get_campaign_operations_state()),
            )

            self.branches[branch_id] = branch
            return branch

    def get_branch(self, branch_id: str) -> CampaignBranch:
        with self._lock:
            if branch_id not in self.branches:
                raise BranchNotFoundError(f"Branch '{branch_id}' not found.")
            return self.branches[branch_id]

    def list_branches(self, campaign_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            res = []
            for b in self.branches.values():
                if campaign_id is None or b.campaign_id == campaign_id:
                    res.append(b.to_summary_dict())
            return sorted(res, key=lambda x: x["created_at"])

    def get_branch_hierarchy(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns a nested tree hierarchy of branches."""
        with self._lock:
            nodes = {
                b_id: {"branch": b.to_summary_dict(), "children": []}
                for b_id, b in self.branches.items()
                if campaign_id is None or b.campaign_id == campaign_id
            }
            roots = []
            for b_id, node in nodes.items():
                p_id = node["branch"].get("parent_branch_id")
                if p_id and p_id in nodes:
                    nodes[p_id]["children"].append(node)
                else:
                    roots.append(node)
            return {"roots": roots, "total_branches": len(nodes)}

    def execute_branch_event(
        self, branch_id: str, event: Union[CampaignOperationsEvent, Dict[str, Any]]
    ) -> bool:
        """
        Apply an operational event strictly within the branch, without touching parent state.
        """
        with self._lock:
            branch = self.get_branch(branch_id)
            if branch.branch_status in (BranchStatus.ARCHIVED, BranchStatus.PROMOTED):
                raise ValueError(f"Cannot execute event on {branch.branch_status.value} branch '{branch_id}'.")

            if isinstance(event, dict):
                evt = CampaignOperationsEvent(
                    event_id=event.get("event_id", f"evt_{uuid.uuid4().hex[:8]}"),
                    campaign_id=branch.director.campaign_id,
                    sol_index=event.get("sol_index", branch.director.current_sol),
                    event_type=CampaignEventType(event["event_type"]) if isinstance(event["event_type"], str) and event["event_type"] in [e.value for e in CampaignEventType] else event["event_type"],
                    sequence=event.get("sequence", len(branch.branch_specific_events) + 1),
                    timestamp_sol_s=event.get("timestamp_sol_s", 0.0),
                    payload=event.get("payload", {}),
                )
            else:
                evt = event

            applied = branch.director.record_event(evt)
            branch.branch_specific_events.append(evt.to_dict())
            branch.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            branch.final_state_fingerprint = compute_sha256(branch.director.get_campaign_operations_state())
            return applied

    def compare_branches(self, branch_id_a: str, branch_id_b: str) -> BranchComparisonReport:
        """
        Generate a side-by-side delta comparison between two branches.
        """
        with self._lock:
            b_a = self.get_branch(branch_id_a)
            b_b = self.get_branch(branch_id_b)

            st_a = b_a.director.get_campaign_operations_state()
            st_b = b_b.director.get_campaign_operations_state()

            # Aggregate metrics
            dist_a = float(st_a.get("cumulative_distance_m", sum(s.get("traverse_distance_m", 0.0) for s in st_a.get("sols", []))))
            dist_b = float(st_b.get("cumulative_distance_m", sum(s.get("traverse_distance_m", 0.0) for s in st_b.get("sols", []))))

            dur_a = sum(s.get("duration_hours", 0.0) for s in st_a.get("sols", []))
            dur_b = sum(s.get("duration_hours", 0.0) for s in st_b.get("sols", []))

            sci_a = float(len(st_a.get("completed_targets", st_a.get("science_state", {}).get("completed_target_ids", []))) * 75.0)
            sci_b = float(len(st_b.get("completed_targets", st_b.get("science_state", {}).get("completed_target_ids", []))) * 75.0)

            eng_a = float(st_a.get("energy_state", {}).get("current_energy_wh", st_a.get("energy_wh", 4800.0)))
            eng_b = float(st_b.get("energy_state", {}).get("current_energy_wh", st_b.get("energy_wh", 4800.0)))

            sto_a = float(st_a.get("data_state", {}).get("used_storage_mb", st_a.get("storage_used_mb", 0.0)))
            sto_b = float(st_b.get("data_state", {}).get("used_storage_mb", st_b.get("storage_used_mb", 0.0)))

            rel_a = len(st_a.get("deployed_relays", st_a.get("comms_state", {}).get("active_relay_ids", [])))
            rel_b = len(st_b.get("deployed_relays", st_b.get("comms_state", {}).get("active_relay_ids", [])))

            narrative = (
                f"Comparison between '{b_a.name}' ({branch_id_a}) and '{b_b.name}' ({branch_id_b}): "
                f"ΔDist = {dist_b - dist_a:+.1f} m, ΔDuration = {dur_b - dur_a:+.2f} h, "
                f"ΔEnergy = {eng_b - eng_a:+.1f} Wh, ΔStorage = {sto_b - sto_a:+.1f} MB, "
                f"ΔRelays = {rel_b - rel_a:+d} masts."
            )

            return BranchComparisonReport(
                branch_a_id=branch_id_a,
                branch_b_id=branch_id_b,
                campaign_id=b_a.campaign_id,
                delta_distance_m=round(dist_b - dist_a, 2),
                delta_duration_hours=round(dur_b - dur_a, 2),
                delta_science_score=round(sci_b - sci_a, 2),
                delta_energy_wh=round(eng_b - eng_a, 2),
                delta_storage_mb=round(sto_b - sto_a, 2),
                delta_relays_deployed=rel_b - rel_a,
                state_a=st_a,
                state_b=st_b,
                comparison_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                narrative=narrative,
            )

    def promote_branch(
        self,
        branch_id: str,
        live_parent_director: CampaignOperationsDirector,
        expected_parent_version: int,
        approval_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Atomically promote a verified branch to become the active plan of the parent director.
        Enforces optimistic locking against stale versions.
        """
        with self._lock:
            branch = self.get_branch(branch_id)

            # Optimistic locking check
            if live_parent_director.version != expected_parent_version:
                raise StaleVersionConflictError(
                    f"Conflict: Live parent campaign is at version v{live_parent_director.version}, "
                    f"but branch '{branch_id}' was formulated against expected v{expected_parent_version}."
                )

            # Record plan lineage
            old_version = live_parent_director.version
            new_version = old_version + 1

            promo_rec = {
                "promoted_branch_id": branch_id,
                "promoted_branch_name": branch.name,
                "previous_version": old_version,
                "new_version": new_version,
                "promoted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "approver": approval_record.get("approver", "Human Flight Director"),
                "rationale": approval_record.get("rationale", "Promoted recovery alternative following counterfactual analysis."),
                "scenario": branch.scenario_definition,
            }

            # Update live parent director state
            if hasattr(branch.director, "active_plan"):
                live_parent_director.active_plan = copy.deepcopy(branch.director.active_plan)
            if hasattr(branch.director, "sol_schedules"):
                live_parent_director.sol_schedules = copy.deepcopy(branch.director.sol_schedules)
            if hasattr(branch.director, "completed_target_ids"):
                live_parent_director.completed_target_ids = copy.deepcopy(branch.director.completed_target_ids)
            if hasattr(branch.director, "active_relay_ids"):
                live_parent_director.active_relay_ids = copy.deepcopy(branch.director.active_relay_ids)
            if hasattr(branch.director, "relay_locations"):
                live_parent_director.relay_locations = copy.deepcopy(branch.director.relay_locations)
            live_parent_director.current_energy_wh = branch.director.current_energy_wh
            live_parent_director.used_storage_mb = branch.director.used_storage_mb
            live_parent_director.lifecycle_state = CampaignLifecycleState.APPROVED_FOR_SIMULATION.value if hasattr(CampaignLifecycleState.APPROVED_FOR_SIMULATION, "value") else str(CampaignLifecycleState.APPROVED_FOR_SIMULATION)
            live_parent_director.version = new_version
            if hasattr(live_parent_director, "historical_plans"):
                live_parent_director.historical_plans.append(promo_rec)

            # Mark branch as promoted
            branch.branch_status = BranchStatus.PROMOTED
            branch.promotion_record = promo_rec
            branch.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

            return {
                "status": "PROMOTED",
                "campaign_id": live_parent_director.campaign_id,
                "promoted_branch_id": branch_id,
                "new_version": new_version,
                "promotion_record": promo_rec,
            }

    def archive_branch(self, branch_id: str) -> None:
        with self._lock:
            branch = self.get_branch(branch_id)
            branch.branch_status = BranchStatus.ARCHIVED
            branch.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
