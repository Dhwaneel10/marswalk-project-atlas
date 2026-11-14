"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_observation_value.py
Active Learning, Expected Information Gain (EIG), and Cost-Aware
Scientific Observation Utility Engine.

Enforces:
- Formal Shannon Entropy & Expected Information Gain computation.
- Explicit labeling of deterministic interval-reduction vs probabilistic EIG.
- Multi-component cost & resource exposure (Energy, Duration, Data Volume, Comm windows).
- Six distinct observation selection strategies for rigorous scientific benchmarking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class SelectionStrategy(str, Enum):
    RANDOM_SELECTION = "RANDOM_SELECTION"
    FIXED_PREDETERMINED_SURVEY = "FIXED_PREDETERMINED_SURVEY"
    GREEDY_ANOMALY = "GREEDY_ANOMALY"
    GREEDY_UNCERTAINTY = "GREEDY_UNCERTAINTY"
    EXPECTED_INFO_GAIN = "EXPECTED_INFO_GAIN"
    COST_AWARE_DISCOVERY = "COST_AWARE_DISCOVERY"


@dataclass
class ObservationCostProfile:
    energy_wh: float
    transit_duration_s: float
    observation_duration_s: float
    data_volume_mb: float
    comm_window_required_s: float
    risk_factor: float  # 0.0 (safe) to 1.0 (extreme terrain / dust)

    @property
    def total_duration_s(self) -> float:
        return self.transit_duration_s + self.observation_duration_s

    def compute_composite_cost(
        self,
        weight_energy: float = 1.0,
        weight_time: float = 0.5,
        weight_data: float = 0.2,
        weight_risk: float = 2.0,
    ) -> float:
        """
        Normalized cost index.
        """
        norm_e = self.energy_wh / 50.0       # Normalized to 50 Wh baseline
        norm_t = self.total_duration_s / 600.0 # Normalized to 10 min baseline
        norm_d = self.data_volume_mb / 20.0    # Normalized to 20 MB baseline
        norm_r = self.risk_factor
        return (
            weight_energy * norm_e
            + weight_time * norm_t
            + weight_data * norm_d
            + weight_risk * norm_r
        )


@dataclass
class CandidateObservationAction:
    action_id: str
    target_id: str
    target_name: str
    coordinates_xy_m: Tuple[float, float]
    required_instrument_id: str
    required_platform: str  # ROVER or ROTORCRAFT
    cost: ObservationCostProfile
    current_anomaly_score: float = 0.0
    spatial_uncertainty: float = 1.0
    expected_info_gain_bits: float = 0.0
    expected_interval_reduction: float = 0.0
    is_probabilistic_eig: bool = True
    competing_hypothesis_ids: List[str] = field(default_factory=list)
    discriminating_power: float = 0.5

    def compute_utility(self, strategy: SelectionStrategy) -> float:
        """
        Computes score according to the designated active learning selection strategy.
        """
        if strategy == SelectionStrategy.RANDOM_SELECTION:
            # Deterministic hash pseudo-random
            return float((hash(self.action_id) % 1000) / 1000.0)

        elif strategy == SelectionStrategy.FIXED_PREDETERMINED_SURVEY:
            # Predetermined sequence ordering based on target coordinate X
            return -self.coordinates_xy_m[0]

        elif strategy == SelectionStrategy.GREEDY_ANOMALY:
            return self.current_anomaly_score

        elif strategy == SelectionStrategy.GREEDY_UNCERTAINTY:
            return self.spatial_uncertainty

        elif strategy == SelectionStrategy.EXPECTED_INFO_GAIN:
            return self.expected_info_gain_bits

        elif strategy == SelectionStrategy.COST_AWARE_DISCOVERY:
            c = max(0.05, self.cost.compute_composite_cost())
            val = self.expected_info_gain_bits * (1.0 + self.discriminating_power)
            return val / c

        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "coordinates_xy_m": [round(c, 2) for c in self.coordinates_xy_m],
            "required_instrument_id": self.required_instrument_id,
            "required_platform": self.required_platform,
            "cost": {
                "energy_wh": round(self.cost.energy_wh, 2),
                "total_duration_s": round(self.cost.total_duration_s, 1),
                "data_volume_mb": round(self.cost.data_volume_mb, 2),
                "composite_cost": round(self.cost.compute_composite_cost(), 3),
            },
            "metrics": {
                "current_anomaly_score": round(self.current_anomaly_score, 3),
                "spatial_uncertainty": round(self.spatial_uncertainty, 3),
                "expected_info_gain_bits": round(self.expected_info_gain_bits, 4),
                "discriminating_power": round(self.discriminating_power, 3),
                "is_probabilistic_eig": self.is_probabilistic_eig,
            },
        }


class ScienceObservationValueEngine:
    """
    Computes Shannon entropy, Bayesian posteriors, and Expected Information Gain (EIG).
    """

    @staticmethod
    def shannon_entropy(probabilities: List[float]) -> float:
        """
        H(H) = - sum(P(Hi) * log2(P(Hi)))
        """
        h = 0.0
        for p in probabilities:
            if p > 1e-12:
                h -= p * math.log2(p)
        return max(0.0, h)

    @staticmethod
    def compute_expected_information_gain(
        prior_probs: List[float],
        likelihood_matrix: List[List[float]],
    ) -> Tuple[float, float, List[float]]:
        """
        Calculates EIG over a finite hypothesis set and discrete observation outcomes.
        EIG = H(prior) - E_y[H(posterior | y)]

        Parameters:
        - prior_probs: P(H_i), length N
        - likelihood_matrix: P(y_j | H_i), shape [N hypotheses x M outcomes]
          Each row i must sum to 1.0 across outcomes j.

        Returns:
        - eig_bits: Expected information gain in bits
        - prior_entropy: Baseline entropy before observation
        - expected_posterior_entropy: Weighted average entropy after observation
        """
        n_hypotheses = len(prior_probs)
        if n_hypotheses == 0:
            return 0.0, 0.0, []

        prior_ent = ScienceObservationValueEngine.shannon_entropy(prior_probs)
        if prior_ent < 1e-6:
            # Already certain, no information to gain
            return 0.0, prior_ent, []

        n_outcomes = len(likelihood_matrix[0])

        # 1. Marginal outcome probabilities: P(y_j) = sum_i P(y_j | H_i) * P(H_i)
        p_outcomes = [0.0] * n_outcomes
        for j in range(n_outcomes):
            for i in range(n_hypotheses):
                p_outcomes[j] += likelihood_matrix[i][j] * prior_probs[i]

        # 2. For each outcome, compute posterior P(H_i | y_j) = (P(y_j | H_i) * P(H_i)) / P(y_j)
        expected_post_ent = 0.0
        for j in range(n_outcomes):
            if p_outcomes[j] < 1e-12:
                continue

            posterior_j = [0.0] * n_hypotheses
            for i in range(n_hypotheses):
                posterior_j[i] = (likelihood_matrix[i][j] * prior_probs[i]) / p_outcomes[j]

            h_j = ScienceObservationValueEngine.shannon_entropy(posterior_j)
            expected_post_ent += p_outcomes[j] * h_j

        eig = max(0.0, prior_ent - expected_post_ent)
        return round(eig, 5), round(prior_ent, 5), [round(p, 4) for p in p_outcomes]

    def rank_actions(
        self,
        actions: List[CandidateObservationAction],
        strategy: SelectionStrategy,
        max_budget_wh: Optional[float] = None,
        max_time_s: Optional[float] = None,
    ) -> List[Tuple[CandidateObservationAction, float]]:
        """
        Filters by budget constraints and ranks actions according to designated strategy.
        """
        valid: List[CandidateObservationAction] = []
        for a in actions:
            if max_budget_wh is not None and a.cost.energy_wh > max_budget_wh:
                continue
            if max_time_s is not None and a.cost.total_duration_s > max_time_s:
                continue
            valid.append(a)

        scored = [(a, a.compute_utility(strategy)) for a in valid]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored
