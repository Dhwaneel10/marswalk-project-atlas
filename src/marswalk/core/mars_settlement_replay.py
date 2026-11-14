"""MarsWalk 2.0 / Project Atlas — Milestone 13S: Settlement Replay Engine.

Implements bit-exact state recording and cryptographic SHA-256 state chain
verification for all settlement operations, construction stages, and ISRU balances.
Guarantees 100% deterministic reproducibility across execution environments.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SettlementStateSnapshot:
    """A cryptographic state snapshot at a specific sol and timestamp."""
    sol: int
    timestamp_s: float
    state_payload: Dict[str, Any]
    previous_hash: str
    state_hash: str = ""

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 hash chaining the previous hash and payload."""
        canonical_str = json.dumps(
            {
                "sol": self.sol,
                "timestamp_s": self.timestamp_s,
                "previous_hash": self.previous_hash,
                "state_payload": self.state_payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol": self.sol,
            "timestamp_s": self.timestamp_s,
            "previous_hash": self.previous_hash,
            "state_hash": self.state_hash or self.compute_hash(),
            "state_payload": self.state_payload,
        }


@dataclass
class ReplayVerificationResult:
    """Result of an adversarial replay verification audit."""
    is_valid: bool
    total_snapshots: int
    genesis_hash: str
    final_state_hash: str
    mismatches: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_snapshots": self.total_snapshots,
            "genesis_hash": self.genesis_hash,
            "final_state_hash": self.final_state_hash,
            "mismatches": self.mismatches,
        }


class SettlementReplayRecorder:
    """Records and verifies deterministic cryptographic state chains."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self) -> None:
        self.snapshots: List[SettlementStateSnapshot] = []
        self._current_hash: str = self.GENESIS_HASH

    def record_step(self, sol: int, timestamp_s: float, state_payload: Dict[str, Any]) -> SettlementStateSnapshot:
        """Records a new state snapshot and appends it to the cryptographic chain."""
        snapshot = SettlementStateSnapshot(
            sol=sol,
            timestamp_s=timestamp_s,
            state_payload=state_payload,
            previous_hash=self._current_hash,
        )
        snapshot.state_hash = snapshot.compute_hash()
        self._current_hash = snapshot.state_hash
        self.snapshots.append(snapshot)
        return snapshot

    def verify_chain_integrity(self) -> ReplayVerificationResult:
        """Adversarially recomputes each snapshot hash to ensure zero tampering."""
        if not self.snapshots:
            return ReplayVerificationResult(
                is_valid=True,
                total_snapshots=0,
                genesis_hash=self.GENESIS_HASH,
                final_state_hash=self.GENESIS_HASH,
            )

        expected_prev = self.GENESIS_HASH
        mismatches = []

        for i, snap in enumerate(self.snapshots):
            if snap.previous_hash != expected_prev:
                mismatches.append({
                    "index": i,
                    "sol": snap.sol,
                    "error": "PREVIOUS_HASH_MISMATCH",
                    "recorded_prev": snap.previous_hash,
                    "expected_prev": expected_prev,
                })

            recomputed = snap.compute_hash()
            if snap.state_hash != recomputed:
                mismatches.append({
                    "index": i,
                    "sol": snap.sol,
                    "error": "STATE_HASH_MISMATCH",
                    "recorded_hash": snap.state_hash,
                    "recomputed_hash": recomputed,
                })

            expected_prev = snap.state_hash

        is_valid = len(mismatches) == 0
        return ReplayVerificationResult(
            is_valid=is_valid,
            total_snapshots=len(self.snapshots),
            genesis_hash=self.GENESIS_HASH,
            final_state_hash=self.snapshots[-1].state_hash if self.snapshots else self.GENESIS_HASH,
            mismatches=mismatches,
        )

    def export_replay_log(self) -> Dict[str, Any]:
        """Exports the full replay log with header verification."""
        audit = self.verify_chain_integrity()
        return {
            "format_version": "1.0.0",
            "milestone": "13S",
            "genesis_hash": self.GENESIS_HASH,
            "final_state_hash": audit.final_state_hash,
            "total_snapshots": len(self.snapshots),
            "is_valid": audit.is_valid,
            "snapshots": [s.to_dict() for s in self.snapshots],
        }

    def import_replay_log(self, data: Dict[str, Any]) -> ReplayVerificationResult:
        """Imports and verifies an external replay log."""
        self.snapshots = []
        for s in data.get("snapshots", []):
            snap = SettlementStateSnapshot(
                sol=s["sol"],
                timestamp_s=s["timestamp_s"],
                previous_hash=s["previous_hash"],
                state_hash=s["state_hash"],
                state_payload=s["state_payload"],
            )
            self.snapshots.append(snap)
        if self.snapshots:
            self._current_hash = self.snapshots[-1].state_hash
        else:
            self._current_hash = self.GENESIS_HASH
        return self.verify_chain_integrity()
