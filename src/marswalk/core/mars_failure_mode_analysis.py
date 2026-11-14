"""MarsWalk 2.0 / Project Atlas  Milestone 13R: Failure Mode and Effects Analysis (FMEA) & Fault Trees.

Provides formal FMEA table generation, Risk Priority Number (RPN) computation,
top-level Boolean Fault Tree synthesis, and Minimal Cut Set analysis for planetary missions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


@dataclass
class FMEARecord:
    """Formal Failure Mode and Effects Analysis record."""
    item_id: str
    subsystem: str
    failure_mode: str
    potential_cause: str
    local_effect: str
    system_effect: str
    end_mission_effect: str
    severity: int                     # 1 to 10 (10 = catastrophic loss of asset)
    occurrence: int                   # 1 to 10 (10 = almost inevitable)
    detection: int                    # 1 to 10 (10 = unobservable / undetected)
    rpn: int = 0                      # S * O * D (1 to 1000)
    recommended_mitigation: str = ""
    mitigated_severity: int = 0
    mitigated_occurrence: int = 0
    mitigated_detection: int = 0
    mitigated_rpn: int = 0

    def __post_init__(self):
        self.rpn = self.severity * self.occurrence * self.detection
        if self.mitigated_severity and self.mitigated_occurrence and self.mitigated_detection:
            self.mitigated_rpn = self.mitigated_severity * self.mitigated_occurrence * self.mitigated_detection
        else:
            self.mitigated_rpn = int(self.rpn * 0.35)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "subsystem": self.subsystem,
            "failure_mode": self.failure_mode,
            "potential_cause": self.potential_cause,
            "local_effect": self.local_effect,
            "system_effect": self.system_effect,
            "end_mission_effect": self.end_mission_effect,
            "severity": self.severity,
            "occurrence": self.occurrence,
            "detection": self.detection,
            "rpn": self.rpn,
            "recommended_mitigation": self.recommended_mitigation,
            "mitigated_severity": self.mitigated_severity or max(1, self.severity - 2),
            "mitigated_occurrence": self.mitigated_occurrence or max(1, self.occurrence - 3),
            "mitigated_detection": self.mitigated_detection or max(1, self.detection - 4),
            "mitigated_rpn": self.mitigated_rpn,
        }


class FaultTreeNodeType(str, Enum):
    """Types of nodes in a Boolean Fault Tree."""
    TOP_EVENT = "TOP_EVENT"
    INTERMEDIATE_GATE = "INTERMEDIATE_GATE"
    BASIC_EVENT = "BASIC_EVENT"
    CONDITIONING_EVENT = "CONDITIONING_EVENT"


@dataclass
class FaultTreeNode:
    """Node in a hierarchical Boolean Fault Tree."""
    node_id: str
    name: str
    node_type: FaultTreeNodeType
    gate: str = "OR"                  # "OR", "AND", or "NONE" for basic events
    probability: float = 0.01         # Unmitigated probability per campaign sol
    children: List[FaultTreeNode] = field(default_factory=list)
    description: str = ""

    def evaluate_probability(self) -> float:
        """Recursively computes event probability using standard Boolean probability algebra."""
        if not self.children:
            return self.probability

        child_probs = [c.evaluate_probability() for c in self.children]
        if self.gate == "AND":
            prob = 1.0
            for p in child_probs:
                prob *= p
            self.probability = prob
        elif self.gate == "OR":
            # P(A U B) = 1 - product(1 - p_i)
            inv = 1.0
            for p in child_probs:
                inv *= (1.0 - p)
            self.probability = 1.0 - inv
        return self.probability

    def find_minimal_cut_sets(self) -> List[List[str]]:
        """Extracts minimal combinations of basic events that cause the event."""
        if not self.children:
            return [[self.node_id]]

        if self.gate == "OR":
            cut_sets = []
            for child in self.children:
                cut_sets.extend(child.find_minimal_cut_sets())
            return cut_sets
        elif self.gate == "AND":
            # Cartesian product of children's cut sets
            cut_sets = [[]]
            for child in self.children:
                child_cuts = child.find_minimal_cut_sets()
                new_cuts = []
                for current in cut_sets:
                    for c in child_cuts:
                        new_cuts.append(current + c)
                cut_sets = new_cuts
            return cut_sets

        return [[self.node_id]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "gate": self.gate,
            "probability": round(self.probability, 6),
            "description": self.description,
            "children": [c.to_dict() for c in self.children],
        }


class FailureModeAnalysisEngine:
    """Generates standard FMEA tables and top-level planetary Fault Trees."""

    @staticmethod
    def generate_campaign_fmea() -> List[FMEARecord]:
        """Produces formal FMEA records for Jezero Crater exploration campaign."""
        return [
            FMEARecord(
                item_id="FMEA-01",
                subsystem="Rover Mobility Actuation",
                failure_mode="Drive motor gear seizure / thermal breakdown",
                potential_cause="Rock jamming or bearing fatigue on steep talus",
                local_effect="Wheel locked, excessive current surge",
                system_effect="45% reduction in drive speed, directional crab bias",
                end_mission_effect="Traverse incomplete; sample return rendezvous missed",
                severity=8, occurrence=4, detection=3,  # RPN = 96
                recommended_mitigation="Actuator power isolation; autonomous 5-wheel kinematic replanning",
                mitigated_severity=6, mitigated_occurrence=3, mitigated_detection=2, # RPN = 36
            ),
            FMEARecord(
                item_id="FMEA-02",
                subsystem="Rotorcraft Propulsion",
                failure_mode="Rotor blade dust pitting & tip abrasion",
                potential_cause="High-velocity Martian dust ingestion during low-altitude hover",
                local_effect="Aerodynamic boundary layer separation, lift deficit",
                system_effect="High RPM motor overheat, rapid battery depletion",
                end_mission_effect="Catastrophic rotorcraft loss in rocky field",
                severity=9, occurrence=5, detection=4,  # RPN = 180
                recommended_mitigation="Flight ceiling limiting, abort sortie to flat terrain",
                mitigated_severity=5, mitigated_occurrence=3, mitigated_detection=2, # RPN = 30
            ),
            FMEARecord(
                item_id="FMEA-03",
                subsystem="Telecommunications",
                failure_mode="Primary UHF Electra transceiver failure",
                potential_cause="Cold-plate thermal stress or RF amplifier lockup",
                local_effect="Loss of high-rate orbiter downlink during pass",
                system_effect="Onboard flash buffer saturation, storage throttling",
                end_mission_effect="Telemetry silence, unrecoverable science data drop",
                severity=7, occurrence=3, detection=2,  # RPN = 42
                recommended_mitigation="Fallback to DTE X-band steerable HGA; prioritize loss-less compression",
                mitigated_severity=4, mitigated_occurrence=2, mitigated_detection=2, # RPN = 16
            ),
            FMEARecord(
                item_id="FMEA-04",
                subsystem="Power & Thermal",
                failure_mode="Atmospheric dust storm solar deposition",
                potential_cause="Synoptic dust storm tau increase > 2.5",
                local_effect="Solar array insolation dropped by 75%",
                system_effect="Survival heaters take 90% of bus energy",
                end_mission_effect="Deep battery depletion, cold-soak computer death",
                severity=9, occurrence=4, detection=2,  # RPN = 72
                recommended_mitigation="Enter low-power hibernation; suspend all mobility and active science",
                mitigated_severity=5, mitigated_occurrence=3, mitigated_detection=1, # RPN = 15
            ),
            FMEARecord(
                item_id="FMEA-05",
                subsystem="Science Payloads (PIXL)",
                failure_mode="X-ray detector energy calibration shift",
                potential_cause="Diurnal thermal cycling exceeding -80C to +15C tolerance",
                local_effect="Peak centroid shifts +0.18 keV",
                system_effect="Misidentification of primary rock forming minerals",
                end_mission_effect="Spurious biogenic carbonate claim published",
                severity=7, occurrence=5, detection=6,  # RPN = 210
                recommended_mitigation="Autonomous recalibration against onboard calibration target disk",
                mitigated_severity=3, mitigated_occurrence=3, mitigated_detection=2, # RPN = 18
            ),
        ]

    @staticmethod
    def build_top_level_campaign_fault_tree() -> FaultTreeNode:
        """Constructs Boolean Fault Tree for TOP_LEVEL_SCIENCE_CAMPAIGN_FAILURE."""
        top = FaultTreeNode(
            node_id="TOP_CAMPAIGN_FAILURE",
            name="Catastrophic Mars Exploration Campaign Failure",
            node_type=FaultTreeNodeType.TOP_EVENT,
            gate="OR",
            description="Mission fails to return primary samples and conclusive science within designated sol window.",
        )

        # Branch 1: Fleet Mobility Collapse
        b1 = FaultTreeNode(
            node_id="GATE_MOBILITY_COLLAPSE",
            name="Fleet Mobility Incapacitation",
            node_type=FaultTreeNodeType.INTERMEDIATE_GATE,
            gate="AND",
            description="Both ground rover and aerial scout become unable to traverse to sampling locations.",
        )
        b1_1 = FaultTreeNode(
            node_id="EVENT_ROV_MOBILITY_LOST",
            name="Perseverance Complete Drive Seizure",
            node_type=FaultTreeNodeType.BASIC_EVENT,
            probability=0.012,
            description="Multiple drive wheels permanently disabled or trapped in dune crest.",
        )
        b1_2 = FaultTreeNode(
            node_id="EVENT_AERO_SCOUT_CRASH",
            name="Ingenuity Total Crash / Rotor Separation",
            node_type=FaultTreeNodeType.BASIC_EVENT,
            probability=0.025,
            description="Flight control aerodynamic loss resulting in ground impact.",
        )
        b1.children = [b1_1, b1_2]

        # Branch 2: Data Loss & Telemetry Blackout
        b2 = FaultTreeNode(
            node_id="GATE_DATA_LOSS_BLACKOUT",
            name="Total Scientific Data Loss",
            node_type=FaultTreeNodeType.INTERMEDIATE_GATE,
            gate="AND",
            description="Loss of both primary UHF orbiter relay and secondary Direct-to-Earth X-band.",
        )
        b2_1 = FaultTreeNode(
            node_id="EVENT_UHF_FAILURE",
            name="UHF Transceiver Hardware Failure",
            node_type=FaultTreeNodeType.BASIC_EVENT,
            probability=0.035,
            description="Electra relay amplifier electronics failure.",
        )
        b2_2 = FaultTreeNode(
            node_id="EVENT_HGA_GIMBAL_STALL",
            name="High-Gain Antenna Gimbal Lock",
            node_type=FaultTreeNodeType.BASIC_EVENT,
            probability=0.028,
            description="Elevation drive mechanical motor jam prevents Earth tracking.",
        )
        b2.children = [b2_1, b2_2]

        # Branch 3: Environmental Depletion
        b3 = FaultTreeNode(
            node_id="GATE_THERMAL_POWER_COLLAPSE",
            name="Complete Power and Thermal Collapse",
            node_type=FaultTreeNodeType.INTERMEDIATE_GATE,
            gate="OR",
            description="Power generation insufficient to maintain survival thermal envelope.",
        )
        b3_1 = FaultTreeNode(
            node_id="EVENT_PLANET_DUST_STORM",
            name="Global Encircling Dust Storm (Tau > 4.5)",
            node_type=FaultTreeNodeType.BASIC_EVENT,
            probability=0.045,
            description="Atmospheric dust storm blocks 95% of solar energy for >30 sols.",
        )
        b3_2 = FaultTreeNode(
            node_id="EVENT_MMRTG_SHORT",
            name="Rover Thermoelectric Bus Short",
            node_type=FaultTreeNodeType.BASIC_EVENT,
            probability=0.005,
            description="Severe internal degradation of MMRTG power distribution unit.",
        )
        b3.children = [b3_1, b3_2]

        top.children = [b1, b2, b3]
        top.evaluate_probability()
        return top
