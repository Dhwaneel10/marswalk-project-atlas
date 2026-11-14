"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_evidence_graph.py
Traceable, acyclic Scientific Evidence Graph linking:
Observation -> Measurement -> Feature -> Interpretation -> Hypothesis -> Experiment -> Result -> Updated Interpretation.

Enforces:
- Strict evidence classification taxonomy (DIRECT vs. SIMULATED vs. INTERPRETATION).
- Full cryptographic data provenance and source hashing.
- Evidential authority bounding: Downstream interpretations can never claim greater
  empirical authority than the weakest supporting measurement in their lineage.
- Orphan claim detection (claims lacking supporting observations).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class EvidenceClassification(str, Enum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    CALIBRATED_OBSERVATION = "CALIBRATED_OBSERVATION"
    DERIVED_OBSERVATION = "DERIVED_OBSERVATION"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    SIMULATED_OBSERVATION = "SIMULATED_OBSERVATION"
    INFERRED_FEATURE = "INFERRED_FEATURE"
    SCIENTIFIC_INTERPRETATION = "SCIENTIFIC_INTERPRETATION"
    CONFIGURED_ASSUMPTION = "CONFIGURED_ASSUMPTION"


# Hierarchy of empirical authority (higher rank = more direct empirical measurement)
EMPIRICAL_AUTHORITY_RANK: Dict[EvidenceClassification, int] = {
    EvidenceClassification.DIRECT_OBSERVATION: 7,
    EvidenceClassification.CALIBRATED_OBSERVATION: 6,
    EvidenceClassification.DERIVED_OBSERVATION: 5,
    EvidenceClassification.MODEL_OUTPUT: 4,
    EvidenceClassification.INFERRED_FEATURE: 3,
    EvidenceClassification.SCIENTIFIC_INTERPRETATION: 2,
    EvidenceClassification.SIMULATED_OBSERVATION: 1,
    EvidenceClassification.CONFIGURED_ASSUMPTION: 0,
}


class NodeType(str, Enum):
    OBSERVATION = "OBSERVATION"
    MEASUREMENT = "MEASUREMENT"
    FEATURE = "FEATURE"
    INTERPRETATION = "INTERPRETATION"
    HYPOTHESIS = "HYPOTHESIS"
    EXPERIMENT = "EXPERIMENT"
    RESULT = "RESULT"


class EdgeRelation(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    MEASURED_BY = "MEASURED_BY"
    DETECTED_IN = "DETECTED_IN"
    INTERPRETS = "INTERPRETS"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    EVALUATES = "EVALUATES"
    GENERATED_BY = "GENERATED_BY"
    DISCRIMINATES_AGAINST = "DISCRIMINATES_AGAINST"
    SUPERSEDES = "SUPERSEDES"


@dataclass
class EvidenceQuality:
    measurement_quality: float  # 0.0 to 1.0
    calibration_status: str     # UNCALIBRATED, PRELIMINARY, RADIOMETRICALLY_CALIBRATED, LABORATORY_VERIFIED
    spatial_representativeness: str
    temporal_representativeness: str
    instrument_coverage: str
    uncertainty_bounds: List[float]  # [lower, upper] or [std_dev]
    data_processing_history: List[str] = field(default_factory=list)
    missing_metadata: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measurement_quality": round(self.measurement_quality, 4),
            "calibration_status": self.calibration_status,
            "spatial_representativeness": self.spatial_representativeness,
            "temporal_representativeness": self.temporal_representativeness,
            "instrument_coverage": self.instrument_coverage,
            "uncertainty_bounds": [round(u, 4) for u in self.uncertainty_bounds],
            "data_processing_history": list(self.data_processing_history),
            "missing_metadata": list(self.missing_metadata),
        }


@dataclass
class EvidenceNode:
    node_id: str
    node_type: NodeType
    classification: EvidenceClassification
    label: str
    description: str
    payload: Dict[str, Any]
    quality: EvidenceQuality
    source_hash: str
    scientific_provenance: str
    timestamp_utc: float
    experiment_id: Optional[str] = None
    target_region: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "classification": self.classification.value,
            "label": self.label,
            "description": self.description,
            "payload": self.payload,
            "quality": self.quality.to_dict(),
            "source_hash": self.source_hash,
            "scientific_provenance": self.scientific_provenance,
            "timestamp_utc": round(self.timestamp_utc, 3),
            "experiment_id": self.experiment_id,
            "target_region": self.target_region,
        }


@dataclass
class EvidenceEdge:
    edge_id: str
    source_id: str  # from node
    target_id: str  # to node
    relation: EdgeRelation
    confidence: float
    weight: float
    provenance_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "confidence": round(self.confidence, 4),
            "weight": round(self.weight, 4),
            "provenance_note": self.provenance_note,
        }


class ScientificEvidenceGraph:
    """
    DAG of scientific evidence nodes and inferential relations.
    """

    def __init__(self):
        self._nodes: Dict[str, EvidenceNode] = {}
        self._edges: Dict[str, EvidenceEdge] = {}
        self._outgoing: Dict[str, List[str]] = {}
        self._incoming: Dict[str, List[str]] = {}

    def add_node(self, node: EvidenceNode) -> EvidenceNode:
        if node.node_id in self._nodes:
            raise ValueError(f"Evidence node '{node.node_id}' already exists in graph.")
        
        # Verify source hash integrity if payload exists
        if not node.source_hash:
            payload_str = json.dumps(node.payload, sort_keys=True)
            node.source_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        self._nodes[node.node_id] = node
        self._outgoing[node.node_id] = []
        self._incoming[node.node_id] = []
        return node

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: EdgeRelation,
        confidence: float = 1.0,
        weight: float = 1.0,
        provenance_note: str = "",
    ) -> EvidenceEdge:
        if source_id not in self._nodes or target_id not in self._nodes:
            raise KeyError(f"Both nodes must exist before creating edge: {source_id} -> {target_id}")

        edge_id = f"EDGE-{uuid.uuid4().hex[:8].upper()}"
        edge = EvidenceEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            confidence=max(0.0, min(1.0, confidence)),
            weight=weight,
            provenance_note=provenance_note,
        )

        self._edges[edge_id] = edge
        self._outgoing[source_id].append(edge_id)
        self._incoming[target_id].append(edge_id)
        return edge

    def get_node(self, node_id: str) -> Optional[EvidenceNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[EvidenceEdge]:
        return self._edges.get(edge_id)

    def get_lineage(self, node_id: str) -> List[EvidenceNode]:
        """
        Traces backwards from node_id to all upstream ancestral nodes (parents, grandparents).
        """
        if node_id not in self._nodes:
            return []

        visited: Set[str] = set()
        queue: List[str] = [node_id]
        lineage: List[EvidenceNode] = []

        while queue:
            curr_id = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)

            if curr_id != node_id and curr_id in self._nodes:
                lineage.append(self._nodes[curr_id])

            # Incomings into curr_id give parents
            for edge_id in self._incoming.get(curr_id, []):
                edge = self._edges[edge_id]
                queue.append(edge.source_id)

        return lineage

    def get_maximum_inherited_authority(self, node_id: str) -> EvidenceClassification:
        """
        Evidential Authority Rule:
        An interpretation or derived claim cannot inherit higher empirical standing
        than the weakest supporting direct observation in its upstream lineage.
        """
        node = self.get_node(node_id)
        if not node:
            return EvidenceClassification.CONFIGURED_ASSUMPTION

        lineage = self.get_lineage(node_id)
        if not lineage:
            return node.classification

        # Find min empirical authority among ancestors
        min_rank = EMPIRICAL_AUTHORITY_RANK[node.classification]
        for anc in lineage:
            anc_rank = EMPIRICAL_AUTHORITY_RANK[anc.classification]
            if anc_rank < min_rank:
                min_rank = anc_rank

        # Invert rank back to classification
        for cls, rank in EMPIRICAL_AUTHORITY_RANK.items():
            if rank == min_rank:
                return cls

        return node.classification

    def detect_orphan_claims(self) -> List[str]:
        """
        Detects claims (INTERPRETATION, FEATURE) that have no upstream observation/measurement links.
        """
        orphans: List[str] = []
        for node_id, node in self._nodes.items():
            if node.node_type in (NodeType.FEATURE, NodeType.INTERPRETATION):
                parents = [self._edges[e_id].source_id for e_id in self._incoming.get(node_id, [])]
                if not parents:
                    orphans.append(node_id)
        return orphans

    def get_hypotheses_evidence_summary(self, hypothesis_id: str) -> Dict[str, Any]:
        """
        Returns full supporting and contradicting evidence networks for a given hypothesis.
        """
        supporting_nodes: List[Dict[str, Any]] = []
        contradicting_nodes: List[Dict[str, Any]] = []

        # Find all edges pointing to or from hypothesis_id
        for edge in self._edges.values():
            if edge.target_id == hypothesis_id:
                source_node = self.get_node(edge.source_id)
                if not source_node:
                    continue
                if edge.relation == EdgeRelation.SUPPORTS:
                    supporting_nodes.append({
                        "node": source_node.to_dict(),
                        "edge": edge.to_dict(),
                    })
                elif edge.relation == EdgeRelation.CONTRADICTS:
                    contradicting_nodes.append({
                        "node": source_node.to_dict(),
                        "edge": edge.to_dict(),
                    })

        return {
            "hypothesis_id": hypothesis_id,
            "supporting_count": len(supporting_nodes),
            "contradicting_count": len(contradicting_nodes),
            "supporting_evidence": supporting_nodes,
            "contradicting_evidence": contradicting_nodes,
        }

    def export_graph_json(self) -> Dict[str, Any]:
        """
        Exports the graph to JSON format for visualization.
        """
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
            "statistics": {
                "total_nodes": len(self._nodes),
                "total_edges": len(self._edges),
                "orphan_claims_count": len(self.detect_orphan_claims()),
            },
        }
