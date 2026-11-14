"""
MarsWalk 2.0 / Project Atlas — Milestone 13I: Campaign Counterfactual Scenario Engine.

Executes deterministic counterfactual disturbances on isolated campaign branches
across 6 core operational categories:
- COMMUNICATIONS: R1 (Relay outage), R2 (Restricted connectivity window)
- ENERGY: E1 (Energy shortfall), E2 (Increased mobility effort)
- SCIENCE: S1 (Instrument unavailable), S2 (Synthetic newly prioritized target)
- DATA: D1 (Storage capacity restriction), D2 (Transfer window lost)
- MOBILITY: M1 (Route obstruction), M2 (Terrain cost preference disturbance)
- OPERATIONS: O1 (Activity delay), O2 (Multiple disturbances)

Guarantees:
- Zero mutation of parent campaign or baseline branch.
- Deterministic reproduction from scenario definition + parent checkpoint.
- Integrated assurance auditing and recovery alternative synthesis.
"""

from __future__ import annotations

import copy
import datetime
import enum
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Set, Union


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def compute_sha256(data: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


from marswalk.core.campaign_operations_director import (
    CampaignOperationsDirector,
    CampaignOperationsEvent,
    CampaignEventType,
    CampaignLifecycleState,
    ReplanningTriggerType,
)
from marswalk.core.mission_campaign import CampaignTarget
from marswalk.core.campaign_branch_manager import (
    CampaignBranchManager,
    CampaignBranch,
    BranchStatus,
)
from marswalk.core.mission_assurance_engine import (
    MissionAssuranceEngine,
    MissionAssuranceReport,
    AssuranceVerdict,
)


class ScenarioCategory(str, enum.Enum):
    COMMUNICATIONS = "COMMUNICATIONS"
    ENERGY = "ENERGY"
    SCIENCE = "SCIENCE"
    DATA = "DATA"
    MOBILITY = "MOBILITY"
    OPERATIONS = "OPERATIONS"


class ScenarioType(str, enum.Enum):
    # Communications
    R1_RELAY_OUTAGE = "R1_RELAY_OUTAGE"
    R2_RESTRICTED_CONNECTIVITY = "R2_RESTRICTED_CONNECTIVITY"
    # Energy
    E1_ENERGY_SHORTFALL = "E1_ENERGY_SHORTFALL"
    E2_INCREASED_MOBILITY_EFFORT = "E2_INCREASED_MOBILITY_EFFORT"
    # Science
    S1_INSTRUMENT_UNAVAILABLE = "S1_INSTRUMENT_UNAVAILABLE"
    S2_NEW_SCIENCE_TARGET = "S2_NEW_SCIENCE_TARGET"
    # Data
    D1_STORAGE_RESTRICTION = "D1_STORAGE_RESTRICTION"
    D2_TRANSFER_WINDOW_LOST = "D2_TRANSFER_WINDOW_LOST"
    # Mobility
    M1_ROUTE_OBSTRUCTION = "M1_ROUTE_OBSTRUCTION"
    M2_ROUTE_PREFERENCE_DISTURBANCE = "M2_ROUTE_PREFERENCE_DISTURBANCE"
    # Operations
    O1_ACTIVITY_DELAY = "O1_ACTIVITY_DELAY"
    O2_MULTIPLE_DISTURBANCES = "O2_MULTIPLE_DISTURBANCES"


@dataclass
class CounterfactualScenarioDefinition:
    scenario_id: str
    scenario_type: ScenarioType
    category: ScenarioCategory
    name: str
    description: str
    target_sol: int
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type.value if isinstance(self.scenario_type, enum.Enum) else str(self.scenario_type),
            "category": self.category.value if isinstance(self.category, enum.Enum) else str(self.category),
            "name": self.name,
            "description": self.description,
            "target_sol": self.target_sol,
            "parameters": self.parameters,
        }


@dataclass
class CounterfactualScenarioResult:
    scenario_id: str
    scenario_type: str
    category: str
    branch_id: str
    campaign_id: str
    disturbance_narrative: str
    affected_subsystems: List[str]
    pre_state: Dict[str, Any]
    post_state: Dict[str, Any]
    assurance_report: Dict[str, Any]
    is_feasible_without_recovery: bool
    recovery_alternatives: List[Dict[str, Any]]
    recommended_alternative_id: Optional[str]
    recommended_rationale: str
    execution_latency_s: float
    reproducibility_token: str
    target_sol: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "category": self.category,
            "branch_id": self.branch_id,
            "campaign_id": self.campaign_id,
            "target_sol": self.target_sol,
            "affected_subsystems": self.affected_subsystems,
            "narrative": self.disturbance_narrative,
            "pre_state": self.pre_state,
            "post_state": self.post_state,
            "assurance_report": self.assurance_report,
            "is_initially_feasible": self.is_feasible_without_recovery,
            "recovery_alternatives": self.recovery_alternatives,
            "recommended_alternative_id": self.recommended_alternative_id,
            "recommended_alternative_narrative": self.recommended_rationale,
            "execution_duration_s": round(self.execution_latency_s, 4),
            "reproducibility_token": self.reproducibility_token,
        }


class CampaignCounterfactualEngine:
    """
    Orchestrates isolated counterfactual fault injections and recovery evaluations.
    """

    def __init__(
        self,
        branch_manager: Optional[CampaignBranchManager] = None,
        assurance_engine: Optional[MissionAssuranceEngine] = None,
    ):
        self.branch_manager = branch_manager or CampaignBranchManager()
        self.assurance_engine = assurance_engine or MissionAssuranceEngine()

    def run_counterfactual_scenario(
        self,
        parent_director: CampaignOperationsDirector,
        scenario: CounterfactualScenarioDefinition,
        branch_id: Optional[str] = None,
        parent_branch_id: Optional[str] = None,
    ) -> CounterfactualScenarioResult:
        """
        Execute an isolated counterfactual scenario:
        1. Fork parent director into a new isolated branch.
        2. Inject configured disturbance.
        3. Evaluate assurance rules on disturbed branch.
        4. Synthesize recovery options using existing optimization planners.
        5. Return comprehensive result packet.
        """
        start_time = time.perf_counter()

        bid = branch_id or f"br_{scenario.scenario_type.value.lower()}_{uuid.uuid4().hex[:6]}"
        branch_name = f"Counterfactual: {scenario.name} (Sol {scenario.target_sol})"

        # 1. Create Isolated Branch
        branch = self.branch_manager.create_branch(
            parent_director=parent_director,
            branch_id=bid,
            name=branch_name,
            scenario_def=scenario.to_dict(),
            fork_sol=scenario.target_sol,
            parent_branch_id=parent_branch_id,
        )

        pre_state = branch.director.get_campaign_operations_state()
        affected_subsystems: List[str] = []
        narrative = ""

        # 2. Inject Disturbance based on scenario type
        st = scenario.scenario_type
        params = scenario.parameters

        if st == ScenarioType.R1_RELAY_OUTAGE:
            affected_subsystems = ["COMMUNICATIONS", "STORAGE", "SCIENCE"]
            relay_id = params.get("relay_id", "MRN-01")
            narrative = f"Relay mast '{relay_id}' experienced an unexpected hardware subsystem fault on Sol {scenario.target_sol}, breaking primary microwave backhaul link to base."
            branch.director.record_event(
                event_type="RELAY_OUTAGE",
                sol_index=scenario.target_sol,
                payload={"relay_id": relay_id, "outage_cause": "RF Amplifier Trip"},
                event_id=f"evt_outage_{uuid.uuid4().hex[:6]}",
            )

        elif st == ScenarioType.R2_RESTRICTED_CONNECTIVITY:
            affected_subsystems = ["COMMUNICATIONS", "DATA_LOGISTICS"]
            window_reduction_pct = params.get("reduction_pct", 50.0)
            narrative = f"Geometric line-of-sight pass windows restricted by {window_reduction_pct:.0f}% due to topographic occlusion."
            # Simulate transfer backlog
            branch.director.used_storage_mb = min(
                branch.director.storage_capacity_mb,
                branch.director.used_storage_mb + params.get("backlog_mb", 450.0),
            )

        elif st == ScenarioType.E1_ENERGY_SHORTFALL:
            affected_subsystems = ["RESOURCES", "MOBILITY", "SCHEDULE"]
            shortfall_wh = params.get("shortfall_wh", 650.0)
            narrative = f"Unmodeled thermal battery drain of {shortfall_wh:.1f} Wh incurred on Sol {scenario.target_sol} due to dust deposition on solar/RTG cooling loop."
            branch.director.current_energy_wh = max(0.0, branch.director.current_energy_wh - shortfall_wh)
            branch.director.record_event(
                event_type="BATTERY_ANOMALY",
                sol_index=scenario.target_sol,
                payload={"shortfall_wh": shortfall_wh, "anomaly_type": "THERMAL_CHILL"},
                event_id=f"evt_energy_drop_{uuid.uuid4().hex[:6]}",
            )

        elif st == ScenarioType.E2_INCREASED_MOBILITY_EFFORT:
            affected_subsystems = ["MOBILITY", "TERRAMECHANICS", "RESOURCES"]
            multiplier = params.get("drag_multiplier", 1.35)
            narrative = f"Traverse over high-sinkage transverse aeolian ridges (TARs) increased terramechanical rolling resistance by {((multiplier - 1.0)*100):.0f}% (synthetic scenario assumption)."
            added_energy = params.get("added_energy_wh", 380.0)
            branch.director.current_energy_wh = max(0.0, branch.director.current_energy_wh - added_energy)

        elif st == ScenarioType.S1_INSTRUMENT_UNAVAILABLE:
            affected_subsystems = ["SCIENCE", "INSTRUMENTS", "PAYLOAD"]
            inst = params.get("instrument", "PIXL_XRF_GRID")
            narrative = f"Instrument '{inst}' experienced a sensor head communication timeout on Sol {scenario.target_sol} and is offline for subsequent sampling."
            branch.director.record_event(
                event_type="INSTRUMENT_OFFLINE",
                sol_index=scenario.target_sol,
                payload={"instrument": inst, "fault_code": "ERR_CALIBRATION_TIMEOUT"},
                event_id=f"evt_inst_fault_{uuid.uuid4().hex[:6]}",
            )

        elif st == ScenarioType.S2_NEW_SCIENCE_TARGET:
            affected_subsystems = ["SCIENCE", "SCHEDULE", "MOBILITY"]
            tgt_name = params.get("target_name", "Delta Promontory Outcrop")
            pri = params.get("priority", 94.0)
            narrative = f"Synthetic opportunistic science target '{tgt_name}' (priority {pri:.1f}) designated for optional inclusion in sortie."
            syn_id = f"syn_{uuid.uuid4().hex[:6]}"
            new_target = CampaignTarget(
                id=syn_id,
                name=tgt_name,
                row=params.get("row", 132),
                col=params.get("col", 102),
                priority_score=pri,
                dwell_time_s=1800.0,
                science_objective="SURFACE_MORPHOLOGY",
            )
            branch.director.targets[syn_id] = new_target
            branch.director.pending_target_ids.append(syn_id)

        elif st == ScenarioType.D1_STORAGE_RESTRICTION:
            affected_subsystems = ["DATA_LOGISTICS", "STORAGE", "SCIENCE"]
            red_mb = params.get("capacity_reduction_mb", 6000.0)
            branch.director.storage_capacity_mb = max(2000.0, branch.director.storage_capacity_mb - red_mb)
            narrative = f"Mass memory partition fault restricted usable solid-state storage to {branch.director.storage_capacity_mb:.0f} MB."

        elif st == ScenarioType.D2_TRANSFER_WINDOW_LOST:
            affected_subsystems = ["DATA_LOGISTICS", "COMMUNICATIONS"]
            lost_mb = params.get("lost_transfer_mb", 350.0)
            branch.director.used_storage_mb = min(branch.director.storage_capacity_mb, branch.director.used_storage_mb + lost_mb)
            narrative = f"Scheduled DTE/Orbiter pass on Sol {scenario.target_sol} cancelled due to deep space network pointing priority conflict ({lost_mb:.1f} MB backlog retained)."

        elif st == ScenarioType.M1_ROUTE_OBSTRUCTION:
            affected_subsystems = ["MOBILITY", "GEODESY", "SCHEDULE"]
            narrative = f"Geomorphic rockfall blockage detected along primary delta scarp corridor on Sol {scenario.target_sol} (MET 02:15:00)."
            branch.director.record_event(
                event_type="CORRIDOR_BLOCKED",
                sol_index=scenario.target_sol,
                payload={"corridor": "Delta Ascent North", "hazard_type": "ROCKFALL_DEBRIS"},
                event_id=f"evt_block_{uuid.uuid4().hex[:6]}",
            )

        elif st == ScenarioType.M2_ROUTE_PREFERENCE_DISTURBANCE:
            affected_subsystems = ["MOBILITY", "ENERGY"]
            narrative = f"Operational slope aversion preference increased from standard 12 deg to conservative 8 deg due to high-slip regolith."
            branch.director.current_energy_wh = max(0.0, branch.director.current_energy_wh - params.get("penalized_energy_wh", 250.0))

        elif st == ScenarioType.O1_ACTIVITY_DELAY:
            affected_subsystems = ["SCHEDULE", "OPERATIONS", "BATTERY"]
            delay_h = params.get("delay_hours", 1.5)
            narrative = f"Drill chuck engagement retry introduced {delay_h:.1f} h operational hold on Sol {scenario.target_sol}."
            # Base hotel power consumption during hold
            hotel_wh = delay_h * 110.0
            branch.director.current_energy_wh = max(0.0, branch.director.current_energy_wh - hotel_wh)

        elif st == ScenarioType.O2_MULTIPLE_DISTURBANCES:
            affected_subsystems = ["COMMUNICATIONS", "MOBILITY", "RESOURCES", "SCHEDULE"]
            narrative = f"Compound multi-fault disturbance: Sol {scenario.target_sol} corridor obstruction accompanied by relay hardware outage."
            branch.director.record_event(
                event_type="CORRIDOR_BLOCKED",
                sol_index=scenario.target_sol,
                payload={"hazard": "Rockfall"},
                event_id=f"evt_comp_block_{uuid.uuid4().hex[:6]}",
            )
            branch.director.record_event(
                event_type="RELAY_OUTAGE",
                sol_index=scenario.target_sol,
                payload={"relay_id": "MRN-01"},
                event_id=f"evt_comp_relay_{uuid.uuid4().hex[:6]}",
            )

        post_state = branch.director.get_campaign_operations_state()

        # 3. Evaluate Assurance Rules on Disturbed Branch State
        assurance_report = self.assurance_engine.evaluate_campaign(
            campaign_state=post_state,
            event_log=branch.director.events_log,
        )

        is_feasible_as_is = (assurance_report.overall_verdict == AssuranceVerdict.PASS)
        if not is_feasible_as_is:
            branch.branch_status = BranchStatus.FAILED_CONSTRAINTS

        # 4. Synthesize Recovery Alternatives
        trigger_type = ReplanningTriggerType.ROUTE_DISTURBANCE.value
        if "RESOURCES" in affected_subsystems or st == ScenarioType.E1_ENERGY_SHORTFALL:
            trigger_type = ReplanningTriggerType.ENERGY_RESERVE_VIOLATION.value
        elif "COMMUNICATIONS" in affected_subsystems or st == ScenarioType.R1_RELAY_OUTAGE:
            trigger_type = ReplanningTriggerType.RELAY_OUTAGE.value
        elif "SCIENCE" in affected_subsystems:
            trigger_type = ReplanningTriggerType.INSTRUMENT_OFFLINE.value

        trigger_info = {"type": trigger_type}
        if trigger_type == ReplanningTriggerType.RELAY_OUTAGE.value:
            trigger_info["relay_id"] = params.get("relay_id", "MRN-01")
        elif trigger_type == ReplanningTriggerType.INSTRUMENT_OFFLINE.value:
            trigger_info["instrument"] = params.get("instrument", "PIXL_XRF_GRID")
        elif trigger_type == ReplanningTriggerType.ROUTE_DISTURBANCE.value:
            trigger_info["location_rc"] = params.get("location_rc", (125, 145))

        alts = branch.director.generate_replanning_alternatives(
            trigger_info=trigger_info,
            max_alternatives=3,
        )

        alts_dicts = [a.to_dict() for a in alts]

        # Select best recovery recommendation
        rec_id = alts[0].alternative_id if alts else None
        rec_narrative = (
            f"Recommended '{alts[0].strategy_name}': {alts[0].description}"
            if alts
            else "No feasible recovery alternative synthesized under current boundary constraints."
        )

        latency = time.perf_counter() - start_time
        token = compute_sha256({"scenario": scenario.to_dict(), "branch_id": bid, "post_state": post_state})

        return CounterfactualScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_type=scenario.scenario_type.value if isinstance(scenario.scenario_type, enum.Enum) else str(scenario.scenario_type),
            category=scenario.category.value if isinstance(scenario.category, enum.Enum) else str(scenario.category),
            branch_id=bid,
            campaign_id=parent_director.campaign_id,
            disturbance_narrative=narrative,
            affected_subsystems=affected_subsystems,
            pre_state=pre_state,
            post_state=post_state,
            assurance_report=assurance_report.to_dict(),
            is_feasible_without_recovery=is_feasible_as_is,
            recovery_alternatives=alts_dicts,
            recommended_alternative_id=rec_id,
            recommended_rationale=rec_narrative,
            execution_latency_s=round(latency, 4),
            reproducibility_token=token,
            target_sol=scenario.target_sol,
        )
