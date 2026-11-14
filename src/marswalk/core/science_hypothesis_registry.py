"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_hypothesis_registry.py
Structured scientific hypothesis management for planetary exploration.

Enforces:
- Explicit hypothesis lifecycle states (PROPOSED -> SUPERSEDED).
- Competing explanation tracking.
- Immutable transition audit records with evidence references.
- Mandatory rejection of state transitions lacking supporting evidence.
- Full provenance and version history.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class HypothesisStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    SUPPORTED_BY_EVIDENCE = "SUPPORTED_BY_EVIDENCE"
    WEAKENED_BY_EVIDENCE = "WEAKENED_BY_EVIDENCE"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    SUPERSEDED = "SUPERSEDED"


class EvidenceRelation(str, Enum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    NEUTRAL_CONTEXT = "NEUTRAL_CONTEXT"


@dataclass
class HypothesisTransitionRecord:
    transition_id: str
    timestamp_utc: float
    previous_status: HypothesisStatus
    new_status: HypothesisStatus
    reason: str
    evidence_ids: List[str]
    evaluation_method: str
    operator_or_agent: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "timestamp_utc": round(self.timestamp_utc, 3),
            "previous_status": self.previous_status.value,
            "new_status": self.new_status.value,
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
            "evaluation_method": self.evaluation_method,
            "operator_or_agent": self.operator_or_agent,
        }


@dataclass
class ScientificHypothesis:
    hypothesis_id: str
    campaign_id: str
    scientific_question: str
    title: str
    description: str
    target_region: Dict[str, Any]
    relevant_variables: List[str]
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)
    required_observation_types: List[str] = field(default_factory=list)
    competing_hypothesis_ids: List[str] = field(default_factory=list)
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    prior_probability: Optional[float] = None
    posterior_probability: Optional[float] = None
    scientific_provenance: str = "Standard planetary science investigation"
    falsification_criteria: List[str] = field(default_factory=list)
    revision_history: List[HypothesisTransitionRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "campaign_id": self.campaign_id,
            "scientific_question": self.scientific_question,
            "title": self.title,
            "description": self.description,
            "target_region": self.target_region,
            "relevant_variables": list(self.relevant_variables),
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "contradicting_evidence_ids": list(self.contradicting_evidence_ids),
            "required_observation_types": list(self.required_observation_types),
            "competing_hypothesis_ids": list(self.competing_hypothesis_ids),
            "status": self.status.value,
            "prior_probability": round(self.prior_probability, 4) if self.prior_probability is not None else None,
            "posterior_probability": round(self.posterior_probability, 4) if self.posterior_probability is not None else None,
            "scientific_provenance": self.scientific_provenance,
            "falsification_criteria": list(self.falsification_criteria),
            "revision_history": [r.to_dict() for r in self.revision_history],
            "metadata": self.metadata,
        }


class ScienceHypothesisRegistry:
    """
    Central repository for scientific hypotheses, validation states, and competing explanations.
    """

    # Permitted state transitions
    VALID_TRANSITIONS: Dict[HypothesisStatus, Set[HypothesisStatus]] = {
        HypothesisStatus.PROPOSED: {
            HypothesisStatus.ACTIVE,
            HypothesisStatus.UNDER_INVESTIGATION,
            HypothesisStatus.SUPPORTED_BY_EVIDENCE,
            HypothesisStatus.WEAKENED_BY_EVIDENCE,
            HypothesisStatus.REJECTED,
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.ACTIVE: {
            HypothesisStatus.UNDER_INVESTIGATION,
            HypothesisStatus.SUPPORTED_BY_EVIDENCE,
            HypothesisStatus.WEAKENED_BY_EVIDENCE,
            HypothesisStatus.REJECTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.UNDER_INVESTIGATION: {
            HypothesisStatus.SUPPORTED_BY_EVIDENCE,
            HypothesisStatus.WEAKENED_BY_EVIDENCE,
            HypothesisStatus.REJECTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.SUPPORTED_BY_EVIDENCE: {
            HypothesisStatus.UNDER_INVESTIGATION,
            HypothesisStatus.WEAKENED_BY_EVIDENCE,
            HypothesisStatus.REJECTED,
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.WEAKENED_BY_EVIDENCE: {
            HypothesisStatus.UNDER_INVESTIGATION,
            HypothesisStatus.SUPPORTED_BY_EVIDENCE,
            HypothesisStatus.REJECTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.INCONCLUSIVE: {
            HypothesisStatus.UNDER_INVESTIGATION,
            HypothesisStatus.SUPPORTED_BY_EVIDENCE,
            HypothesisStatus.WEAKENED_BY_EVIDENCE,
            HypothesisStatus.REJECTED,
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.REJECTED: {
            # Once formally rejected, cannot reopen without explicit supersession
            HypothesisStatus.SUPERSEDED,
        },
        HypothesisStatus.SUPERSEDED: set(),
    }

    def __init__(self):
        self._hypotheses: Dict[str, ScientificHypothesis] = {}

    def register_hypothesis(self, hypothesis: ScientificHypothesis) -> ScientificHypothesis:
        if hypothesis.hypothesis_id in self._hypotheses:
            raise ValueError(f"Hypothesis '{hypothesis.hypothesis_id}' already registered.")
        
        # Self-competing check
        if hypothesis.hypothesis_id in hypothesis.competing_hypothesis_ids:
            raise ValueError("Hypothesis cannot compete with itself.")

        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return hypothesis

    def get_hypothesis(self, hypothesis_id: str) -> Optional[ScientificHypothesis]:
        return self._hypotheses.get(hypothesis_id)

    def list_hypotheses(
        self,
        campaign_id: Optional[str] = None,
        status: Optional[HypothesisStatus] = None,
    ) -> List[ScientificHypothesis]:
        res = list(self._hypotheses.values())
        if campaign_id:
            res = [h for h in res if h.campaign_id == campaign_id]
        if status:
            res = [h for h in res if h.status == status]
        return res

    def link_competing(self, hypothesis_id_a: str, hypothesis_id_b: str) -> None:
        if hypothesis_id_a == hypothesis_id_b:
            raise ValueError("Cannot link hypothesis as competing with itself.")
        h_a = self.get_hypothesis(hypothesis_id_a)
        h_b = self.get_hypothesis(hypothesis_id_b)
        if not h_a or not h_b:
            raise KeyError(f"Both hypotheses must exist ({hypothesis_id_a}, {hypothesis_id_b})")

        if hypothesis_id_b not in h_a.competing_hypothesis_ids:
            h_a.competing_hypothesis_ids.append(hypothesis_id_b)
        if hypothesis_id_a not in h_b.competing_hypothesis_ids:
            h_b.competing_hypothesis_ids.append(hypothesis_id_a)

    def attach_evidence(
        self,
        hypothesis_id: str,
        evidence_id: str,
        relationship: EvidenceRelation,
    ) -> None:
        hyp = self.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found.")

        if relationship == EvidenceRelation.SUPPORTING:
            if evidence_id not in hyp.supporting_evidence_ids:
                hyp.supporting_evidence_ids.append(evidence_id)
            if evidence_id in hyp.contradicting_evidence_ids:
                hyp.contradicting_evidence_ids.remove(evidence_id)
        elif relationship == EvidenceRelation.CONTRADICTING:
            if evidence_id not in hyp.contradicting_evidence_ids:
                hyp.contradicting_evidence_ids.append(evidence_id)
            if evidence_id in hyp.supporting_evidence_ids:
                hyp.supporting_evidence_ids.remove(evidence_id)

    def transition_status(
        self,
        hypothesis_id: str,
        new_status: HypothesisStatus,
        reason: str,
        evidence_ids: List[str],
        evaluation_method: str,
        operator_or_agent: str = "ATLAS_DISCOVERY_ENGINE",
    ) -> ScientificHypothesis:
        hyp = self.get_hypothesis(hypothesis_id)
        if not hyp:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found.")

        current = hyp.status

        # 1. Check valid state graph transition
        allowed = self.VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(
                f"Illegal state transition from {current.value} to {new_status.value} for hypothesis '{hypothesis_id}'."
            )

        # 2. Strict Invariant: No hypothesis can transition to SUPPORTED without supporting evidence
        if new_status == HypothesisStatus.SUPPORTED_BY_EVIDENCE:
            if not evidence_ids and not hyp.supporting_evidence_ids:
                raise ValueError(
                    f"Invariant violation: Cannot transition '{hypothesis_id}' to SUPPORTED_BY_EVIDENCE without valid supporting evidence."
                )
            if not evaluation_method:
                raise ValueError("Evaluation method is mandatory when supporting a hypothesis.")

        # 3. Strict Invariant: No hypothesis can be REJECTED without evidence or clear falsification
        if new_status == HypothesisStatus.REJECTED:
            if not evidence_ids and not hyp.contradicting_evidence_ids:
                raise ValueError(
                    f"Invariant violation: Cannot transition '{hypothesis_id}' to REJECTED without contradictory evidence or falsification record."
                )

        # Record transition
        record = HypothesisTransitionRecord(
            transition_id=f"TRANS-{uuid.uuid4().hex[:8].upper()}",
            timestamp_utc=time.time(),
            previous_status=current,
            new_status=new_status,
            reason=reason,
            evidence_ids=list(evidence_ids),
            evaluation_method=evaluation_method,
            operator_or_agent=operator_or_agent,
        )

        hyp.status = new_status
        hyp.revision_history.append(record)
        return hyp

    def create_competing_hypothesis_set(
        self,
        campaign_id: str,
        scientific_question: str,
        target_region: Dict[str, Any],
        hypotheses_specs: List[Dict[str, Any]],
    ) -> List[ScientificHypothesis]:
        """
        Creates and mutually links an ensemble of competing explanations for an observed phenomenon.
        """
        created: List[ScientificHypothesis] = []
        hyp_ids = [s["hypothesis_id"] for s in hypotheses_specs]

        for spec in hypotheses_specs:
            other_ids = [h for h in hyp_ids if h != spec["hypothesis_id"]]
            hyp = ScientificHypothesis(
                hypothesis_id=spec["hypothesis_id"],
                campaign_id=campaign_id,
                scientific_question=scientific_question,
                title=spec["title"],
                description=spec["description"],
                target_region=target_region,
                relevant_variables=spec.get("relevant_variables", []),
                required_observation_types=spec.get("required_observation_types", []),
                competing_hypothesis_ids=other_ids,
                status=HypothesisStatus.PROPOSED,
                prior_probability=spec.get("prior_probability"),
                scientific_provenance=spec.get("scientific_provenance", "Autonomous candidate generation"),
                falsification_criteria=spec.get("falsification_criteria", []),
            )
            self.register_hypothesis(hyp)
            created.append(hyp)

        return created
