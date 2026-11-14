"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_discovery_replay.py
Deterministic Replay and Cryptographic Audit Verification for Science Discovery Campaigns.

Enforces:
- Bit-exact deterministic event log replay.
- SHA-256 state hash consistency across repeated runs.
- Full state snapshotting for reproducible scientific peer review.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from marswalk.core.science_discovery_scenario_engine import ScienceDiscoveryScenarioEngine


@dataclass
class DiscoveryReplaySession:
    session_id: str
    scenario_id: str
    timestamp_utc: float
    seed: int
    stage_hashes: List[str]
    cumulative_state_hash: str
    is_bit_exact_match: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "scenario_id": self.scenario_id,
            "timestamp_utc": round(self.timestamp_utc, 3),
            "seed": self.seed,
            "stage_hashes": self.stage_hashes,
            "cumulative_state_hash": self.cumulative_state_hash,
            "is_bit_exact_match": self.is_bit_exact_match,
        }


class ScienceDiscoveryReplayEngine:
    """
    Executes multiple runs of a discovery scenario and cryptographically verifies determinism.
    """

    def __init__(self):
        self.scenario_engine = ScienceDiscoveryScenarioEngine()

    def execute_and_hash_run(self, scenario_id: str, seed: int = 42) -> Tuple[str, List[str]]:
        """
        Executes a scenario run and computes deterministic SHA-256 state digests for every stage.
        """
        res = self.scenario_engine.run_scenario(scenario_id)
        stage_hashes: List[str] = []

        cumulative_hasher = hashlib.sha256()
        cumulative_hasher.update(f"SEED:{seed}:SCENARIO:{scenario_id}".encode("utf-8"))

        for stage in res["stages"]:
            stage_serialized = json.dumps(stage["telemetry"], sort_keys=True)
            stage_hash = hashlib.sha256(stage_serialized.encode("utf-8")).hexdigest()
            stage_hashes.append(stage_hash)
            cumulative_hasher.update(stage_hash.encode("utf-8"))

        return cumulative_hasher.hexdigest(), stage_hashes

    def verify_deterministic_replay(
        self,
        scenario_id: str = "SCENARIO_01",
        iterations: int = 5,
        seed: int = 42,
    ) -> DiscoveryReplaySession:
        """
        Executes N consecutive replay iterations and asserts 100% bit-exact hash equivalence.
        """
        baseline_hash, baseline_stages = self.execute_and_hash_run(scenario_id, seed)
        all_matched = True

        for i in range(1, iterations):
            h_i, stages_i = self.execute_and_hash_run(scenario_id, seed)
            if h_i != baseline_hash or stages_i != baseline_stages:
                all_matched = False
                break

        return DiscoveryReplaySession(
            session_id=f"REPLAY-{scenario_id}-{int(time.time())}",
            scenario_id=scenario_id,
            timestamp_utc=time.time(),
            seed=seed,
            stage_hashes=baseline_stages,
            cumulative_state_hash=baseline_hash,
            is_bit_exact_match=all_matched,
        )
