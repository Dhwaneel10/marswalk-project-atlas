"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Atlas Mission Replay & Cryptographic Audit Engine.

Provides bit-exact deterministic replay, verification of SHA-256 hash chains,
and state snapshot scrubbing for external reviewers and Phase F readiness tribunals.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from .atlas_mission_contracts import StateSnapshot


class MissionReplayVerifier:
    """Verifies cryptographic hash chains and provides deterministic replay scrubbing."""

    @staticmethod
    def verify_hash_chain(snapshots: List[StateSnapshot], expected_root_hash: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Verify unbroken cryptographic SHA-256 continuity across all state snapshots."""
        if not snapshots:
            return (False, "Snapshot list is empty", {})

        hasher = hashlib.sha256()

        for idx, snap in enumerate(snapshots):
            # Check sequential step index
            if snap.step_index != idx:
                return (
                    False,
                    f"Step index discontinuity at position {idx}: expected {idx}, found {snap.step_index}",
                    {"failed_index": idx},
                )

            # Check predecessor hash continuity
            if idx > 0:
                expected_prev = snapshots[idx - 1].state_hash
                if snap.prev_state_hash != expected_prev:
                    return (
                        False,
                        f"Hash link broken at step {idx}: prev_state_hash does not match preceding snapshot hash",
                        {"failed_index": idx, "expected": expected_prev, "actual": snap.prev_state_hash},
                    )

            hasher.update(snap.state_hash.encode("utf-8"))

        computed_root = hasher.hexdigest()
        is_valid = (computed_root == expected_root_hash)
        msg = "Cryptographic hash chain 100% verified" if is_valid else f"Root hash mismatch: {computed_root} != {expected_root_hash}"

        return (
            is_valid,
            msg,
            {
                "snapshot_count": len(snapshots),
                "computed_root_hash": computed_root,
                "expected_root_hash": expected_root_hash,
                "start_sol": snapshots[0].current_sol,
                "end_sol": snapshots[-1].current_sol,
            },
        )

    @staticmethod
    def scrub_to_step(snapshots: List[StateSnapshot], target_step: int) -> Optional[Dict[str, Any]]:
        """Scrub to a specific simulation step index and retrieve full snapshot telemetry."""
        if 0 <= target_step < len(snapshots):
            snap = snapshots[target_step]
            return snap.to_dict()
        return None
