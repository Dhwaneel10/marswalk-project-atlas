"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Unified Scientific Operations & Autonomous Discovery Engine.

Bridges observation registries (13G), PDS MEDA climate data (13M), reproducibility
tribunals (13N), aerial multispectral reconnaissance (13P), and Bayesian active
learning hypothesis testers (13Q).
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple

from .atlas_mission_contracts import ObservationRecord, ScienceInvestigation

USGS_CTX_JEZERO_HASH = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"


def compute_shannon_entropy(probability: float) -> float:
    """Calculate Shannon binary entropy H(p) in bits."""
    p = max(1e-6, min(1.0 - 1e-6, probability))
    return - (p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


class ScientificOperationsManager:
    """Orchestrates autonomous science discovery, hypothesis testing, and evidence registration."""

    def __init__(self) -> None:
        self.investigations: Dict[str, ScienceInvestigation] = {}
        self.observations: List[ObservationRecord] = []
        self._initialize_canonical_hypotheses()

    def _initialize_canonical_hypotheses(self) -> None:
        """Instantiate the 4 primary planetary science hypotheses for Jezero Crater."""
        hyps = [
            ScienceInvestigation(
                hypothesis_id="HYP-JEZERO-01",
                target_feature="Delta Scarp",
                statement="Delta Scarp strata preserve lacustrine mudstones rich in Fe/Mg-smectite clays and carbonates.",
                prior_probability=0.65,
                posterior_probability=0.65,
                information_entropy_bits=compute_shannon_entropy(0.65),
                status="ACTIVE",
            ),
            ScienceInvestigation(
                hypothesis_id="HYP-JEZERO-02",
                target_feature="Séítah Floor",
                statement="Séítah floor formation represents cumulate olivine-bearing igneous intrusion weathered by early carbonated waters.",
                prior_probability=0.50,
                posterior_probability=0.50,
                information_entropy_bits=compute_shannon_entropy(0.50),
                status="ACTIVE",
            ),
            ScienceInvestigation(
                hypothesis_id="HYP-JEZERO-03",
                target_feature="Regional Regolith",
                statement="Diurnal atmospheric water vapor exchange induces transient deliquescence of perchlorate salts in surface regolith.",
                prior_probability=0.40,
                posterior_probability=0.40,
                information_entropy_bits=compute_shannon_entropy(0.40),
                status="ACTIVE",
            ),
            ScienceInvestigation(
                hypothesis_id="HYP-JEZERO-04",
                target_feature="Belva Crater Rim",
                statement="Impact-induced hydrothermal circulation along Belva ring faults created low-temperature silica sinter deposits.",
                prior_probability=0.20,
                posterior_probability=0.20,
                information_entropy_bits=compute_shannon_entropy(0.20),
                status="ACTIVE",
            ),
        ]
        for h in hyps:
            self.investigations[h.hypothesis_id] = h

    def ingest_observation(
        self,
        observation_id: str,
        source_asset_id: str,
        sol: int,
        sol_time: str,
        location: Dict[str, float],
        instrument_type: str,
        modality: str,
        data: Dict[str, Any],
        uncertainty: Dict[str, float],
    ) -> ObservationRecord:
        """Record an authentic remote sensing observation with cryptographic provenance."""
        raw_sig = f"{observation_id}|{source_asset_id}|{sol}|{sol_time}|{location['lat']}|{location['lon']}|{instrument_type}"
        prov_hash = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

        obs = ObservationRecord(
            observation_id=observation_id,
            source_asset_id=source_asset_id,
            sol=sol,
            sol_time=sol_time,
            location=location,
            instrument_type=instrument_type,
            scientific_modality=modality,
            measurement_data=data,
            uncertainty=uncertainty,
            provenance_hash=prov_hash,
            shannon_information_gain_bits=0.0,
        )
        self.observations.append(obs)
        return obs

    def update_hypothesis_evidence(
        self,
        hypothesis_id: str,
        observation_id: str,
        likelihood_ratio: float,
    ) -> Tuple[float, float]:
        """Update Bayesian hypothesis probability via Bayes' rule and compute Shannon information gain."""
        hyp = self.investigations.get(hypothesis_id)
        if not hyp:
            return (0.0, 0.0)

        prior_odds = hyp.posterior_probability / max(1e-6, 1.0 - hyp.posterior_probability)
        posterior_odds = prior_odds * likelihood_ratio
        new_posterior = min(0.999, max(0.001, posterior_odds / (1.0 + posterior_odds)))

        old_entropy = hyp.information_entropy_bits
        new_entropy = compute_shannon_entropy(new_posterior)
        info_gain = max(0.0, old_entropy - new_entropy)

        hyp.posterior_probability = round(new_posterior, 4)
        hyp.information_entropy_bits = round(new_entropy, 4)
        if observation_id not in hyp.observations:
            hyp.observations.append(observation_id)

        # Update observation record if present
        for obs in self.observations:
            if obs.observation_id == observation_id:
                obs.shannon_information_gain_bits = round(info_gain, 4)
                break

        return (hyp.posterior_probability, info_gain)

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Aggregate scientific metrics across all hypotheses and collected observations."""
        total_info_gain = sum(obs.shannon_information_gain_bits for obs in self.observations)
        validated_count = sum(1 for h in self.investigations.values() if h.posterior_probability >= 0.80)
        mean_posterior = sum(h.posterior_probability for h in self.investigations.values()) / max(1, len(self.investigations))

        return {
            "total_observations": len(self.observations),
            "hypotheses_count": len(self.investigations),
            "validated_hypotheses_count": validated_count,
            "mean_posterior_probability": round(mean_posterior, 4),
            "cumulative_information_gain_bits": round(total_info_gain, 4),
            "reference_dtm_provenance": USGS_CTX_JEZERO_HASH,
        }

    def list_investigations(self) -> List[ScienceInvestigation]:
        return list(self.investigations.values())
