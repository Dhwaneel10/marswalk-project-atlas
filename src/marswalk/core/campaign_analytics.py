# src/marswalk/core/campaign_analytics.py
"""
MarsWalk 2.0 — Milestone 11G: Campaign Performance Analytics, Deviation Analysis & Lessons Learned.

This module provides a deterministic planning-analysis and lessons learned diagnostic system
comparing planned multi-sol campaigns against simulated digital twin execution timelines.

Key Capabilities:
1. Exact planned vs simulated metric comparisons (duration, distance, target completion, operational holds).
2. Workload and energy decomposition across multiple exploration units with zero double-counting.
3. Rigorous causal deviation analysis classifying discrepancies as confirmed_cause, contributing_factor, or undetermined.
4. Grounded, actionable lessons learned recommendations with structured proposed changes and review states.
5. Deterministic, contract-valid schema compliance (campaign-analytics.schema.json).
"""

from __future__ import annotations

import copy
import enum
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from marswalk.api.contracts import (
    SCHEMA_VERSION,
    validate_campaign_analytics_record,
    sanitize_for_json,
)
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignSortie,
    CampaignConfig,
    MissionCampaign,
    TargetStatus,
)
from marswalk.core.campaign_coordination import (
    ExplorationUnit,
    CoordinationPlan,
    UnitType,
    create_default_units,
)
from marswalk.core.campaign_simulator import (
    CampaignDigitalTwin,
    ActivityType,
    SimulationEvent,
    TemporalConflict,
    MARTIAN_SOL_SECONDS,
)

ANALYTICS_DISCLAIMER = (
    "Campaign Performance Analytics & Lessons Learned is a deterministic planning-analysis system "
    "designed for simulated Mars exploration mission evaluation and rehearsal. "
    "It does NOT utilize live spacecraft telemetry, certified flight hardware diagnostics, or autonomous "
    "operational command authority. All causal attributions, workload breakdowns, and advisory recommendations "
    "are grounded in simulated model outputs and must be verified by mission operations personnel."
)


class DeviationCode(str, enum.Enum):
    DEV_TIME_BUDGET_EXCEEDED = "DEV_TIME_BUDGET_EXCEEDED"
    DEV_SORTIE_START_SLIP = "DEV_SORTIE_START_SLIP"
    DEV_SORTIE_DURATION_BLOWOUT = "DEV_SORTIE_DURATION_BLOWOUT"
    DEV_TARGET_ABANDONED = "DEV_TARGET_ABANDONED"
    DEV_TARGET_BLOCKED = "DEV_TARGET_BLOCKED"
    DEV_FLEET_IDLE_IMBALANCE = "DEV_FLEET_IDLE_IMBALANCE"
    DEV_CRITICAL_HOLD_PROLONGED = "DEV_CRITICAL_HOLD_PROLONGED"
    DEV_TEMPORAL_CONFLICT = "DEV_TEMPORAL_CONFLICT"


class CauseAttribution(str, enum.Enum):
    CONFIRMED_CAUSE = "confirmed_cause"
    CONTRIBUTING_FACTOR = "contributing_factor"
    UNDETERMINED = "undetermined"


class RecommendationCategory(str, enum.Enum):
    TIME_BUDGET = "time_budget"
    COORDINATION_STRATEGY = "coordination_strategy"
    TASK_SEQUENCING = "task_sequencing"
    SCENARIO_COVERAGE = "scenario_coverage"
    UNIT_ASSIGNMENT = "unit_assignment"


class RecommendationStatus(str, enum.Enum):
    ACTIVE = "active"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


@dataclass
class SortieDeviation:
    sortie_id: str
    sol_index: int
    planned_start_s: float
    simulated_start_s: float
    start_slip_s: float
    planned_end_s: float
    simulated_end_s: float
    end_slip_s: float
    planned_duration_s: float
    simulated_duration_s: float
    duration_delta_s: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sortie_id": self.sortie_id,
            "sol_index": self.sol_index,
            "planned_start_s": round(float(self.planned_start_s), 1),
            "simulated_start_s": round(float(self.simulated_start_s), 1),
            "start_slip_s": round(float(self.start_slip_s), 1),
            "planned_end_s": round(float(self.planned_end_s), 1),
            "simulated_end_s": round(float(self.simulated_end_s), 1),
            "end_slip_s": round(float(self.end_slip_s), 1),
            "planned_duration_s": round(float(self.planned_duration_s), 1),
            "simulated_duration_s": round(float(self.simulated_duration_s), 1),
            "duration_delta_s": round(float(self.duration_delta_s), 1),
            "status": self.status,
        }


@dataclass
class UnitWorkload:
    unit_id: str
    unit_name: str
    unit_type: str
    active_duration_s: float
    idle_duration_s: float
    utilization_pct: float
    total_distance_m: float
    energy_consumed_kwh: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "unit_name": self.unit_name,
            "unit_type": self.unit_type,
            "active_duration_s": round(float(self.active_duration_s), 1),
            "idle_duration_s": round(float(self.idle_duration_s), 1),
            "utilization_pct": round(float(self.utilization_pct), 1),
            "total_distance_m": round(float(self.total_distance_m), 1),
            "energy_consumed_kwh": round(float(self.energy_consumed_kwh), 3),
        }


@dataclass
class CampaignDeviation:
    deviation_id: str
    code: str
    severity: str  # blocker, warning, info
    simulated_time_s: float
    cause_attribution: str  # confirmed_cause, contributing_factor, undetermined
    explanation: str
    recommended_action: str
    affected_sortie_id: Optional[str] = None
    affected_unit_id: Optional[str] = None
    affected_target_id: Optional[str] = None
    planned_value: Optional[Dict[str, Any]] = None
    simulated_value: Optional[Dict[str, Any]] = None
    delta_value: Optional[Dict[str, Any]] = None
    triggering_event_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "deviation_id": self.deviation_id,
            "code": self.code,
            "severity": self.severity,
            "affected_sortie_id": self.affected_sortie_id,
            "affected_unit_id": self.affected_unit_id,
            "affected_target_id": self.affected_target_id,
            "simulated_time_s": round(float(self.simulated_time_s), 1),
            "triggering_event_ids": list(self.triggering_event_ids),
            "cause_attribution": self.cause_attribution,
            "explanation": self.explanation,
            "recommended_action": self.recommended_action,
        }
        if self.planned_value:
            data["planned_value"] = self.planned_value
        if self.simulated_value:
            data["simulated_value"] = self.simulated_value
        if self.delta_value:
            data["delta_value"] = self.delta_value
        return data


@dataclass
class LessonsLearnedRecommendation:
    recommendation_id: str
    category: str
    title: str
    evidence_references: List[str]
    rationale: str
    expected_impact: str
    assumptions_and_limitations: str
    proposed_change: Dict[str, Any]
    status: str = RecommendationStatus.ACTIVE.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "category": self.category,
            "title": self.title,
            "evidence_references": list(self.evidence_references),
            "rationale": self.rationale,
            "expected_impact": self.expected_impact,
            "assumptions_and_limitations": self.assumptions_and_limitations,
            "proposed_change": self.proposed_change,
            "status": self.status,
        }


def analyze_campaign_performance(
    campaign: Union[MissionCampaign, Dict[str, Any]],
    simulation: Union[CampaignDigitalTwin, Dict[str, Any]],
    coordination_plan: Optional[Union[CoordinationPlan, Dict[str, Any]]] = None,
    whatif_scenarios: Optional[List[Dict[str, Any]]] = None,
    analysis_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes comprehensive performance analytics and root-cause deviation analysis
    comparing a planned multi-sol campaign against a simulated digital twin run.
    """
    # 1. Normalize Campaign Object / Dictionary
    if isinstance(campaign, dict):
        camp_obj = MissionCampaign.from_dict(campaign)
        camp_dict = campaign
    else:
        camp_obj = campaign
        camp_dict = campaign.to_dict()

    camp_id = camp_dict.get("campaign_id", "cmp_default")
    camp_version = int(camp_dict.get("version", 1))

    # 2. Normalize Simulation Object / Dictionary
    if isinstance(simulation, dict):
        sim_dict = simulation
    else:
        sim_dict = simulation.to_dict()

    sim_id = sim_dict.get("simulation_id", f"sim_{uuid.uuid4().hex[:8]}")
    timeline_intervals = sim_dict.get("timeline_intervals", [])
    sim_events = sim_dict.get("events", [])
    sim_conflicts = sim_dict.get("conflicts", [])
    sim_target_states = sim_dict.get("statistics", {})

    # 3. Normalize Units & Coordination
    coord_dict = coordination_plan.to_dict() if hasattr(coordination_plan, "to_dict") else (coordination_plan or {})
    units_list = coord_dict.get("units", [])
    if not units_list:
        # Fallback to simulation units or default units
        units_list = sim_dict.get("units", [])
    if not units_list:
        units_list = [u.to_dict() for u in create_default_units()]

    unit_map: Dict[str, Dict[str, Any]] = {u["unit_id"]: u for u in units_list}

    # 4. Sortie Planned vs Simulated Deviations
    planned_sorties = camp_dict.get("sorties", [])
    sortie_deviations: List[SortieDeviation] = []

    planned_total_duration_s = sum(s.get("total_duration_s", 0.0) for s in planned_sorties)
    if planned_total_duration_s <= 0.0:
        planned_total_duration_s = float(camp_dict.get("summary", {}).get("total_duration_s", 0.0))
    if planned_total_duration_s <= 0.0:
        planned_total_duration_s = float(len(planned_sorties) * 28800.0)

    # Map intervals by sortie_id
    intervals_by_sortie: Dict[str, List[Dict[str, Any]]] = {}
    for iv in timeline_intervals:
        sid = iv.get("sortie_id")
        if sid:
            intervals_by_sortie.setdefault(sid, []).append(iv)

    for idx, s in enumerate(planned_sorties):
        sid = s.get("sortie_id", f"sortie_{idx+1}")
        sol_idx = int(s.get("sol_index", idx + 1))
        p_dur = float(s.get("total_duration_s", 28800.0))
        p_start = float((sol_idx - 1) * MARTIAN_SOL_SECONDS)
        p_end = p_start + p_dur

        s_ivs = intervals_by_sortie.get(sid, [])
        if s_ivs:
            s_start = min(iv.get("start_time_s", p_start) for iv in s_ivs)
            s_end = max(iv.get("end_time_s", p_end) for iv in s_ivs)
            s_dur = max(0.0, s_end - s_start)
            st_status = "COMPLETED"
        else:
            # Check by sol_index
            sol_ivs = [iv for iv in timeline_intervals if iv.get("sol_index") == sol_idx]
            if sol_ivs:
                s_start = min(iv.get("start_time_s", p_start) for iv in sol_ivs)
                s_end = max(iv.get("end_time_s", p_end) for iv in sol_ivs)
                s_dur = max(0.0, s_end - s_start)
                st_status = "COMPLETED"
            else:
                s_start = p_start
                s_end = p_end
                s_dur = p_dur
                st_status = s.get("status", "PLANNED")

        p_start_r = round(p_start, 1)
        p_dur_r = round(p_dur, 1)
        p_end_r = round(p_start_r + p_dur_r, 1)

        s_start_r = round(s_start, 1)
        s_dur_r = round(s_dur, 1)
        s_end_r = round(s_end, 1)

        s_dev = SortieDeviation(
            sortie_id=sid,
            sol_index=sol_idx,
            planned_start_s=p_start_r,
            simulated_start_s=s_start_r,
            start_slip_s=round(s_start_r - p_start_r, 1),
            planned_end_s=p_end_r,
            simulated_end_s=s_end_r,
            end_slip_s=round(s_end_r - p_end_r, 1),
            planned_duration_s=p_dur_r,
            simulated_duration_s=s_dur_r,
            duration_delta_s=round(s_dur_r - p_dur_r, 1),
            status=st_status,
        )
        sortie_deviations.append(s_dev)

    # 5. Target Completion & Priority Breakdown Analytics
    all_targets = camp_dict.get("targets", [])
    total_targets_count = len(all_targets)

    # Gather target completion from simulation intervals or simulation target states
    completed_target_ids = set()
    blocked_target_ids = set()
    deferred_target_ids = set()

    for iv in timeline_intervals:
        tid = iv.get("target_id")
        act = iv.get("activity_type")
        st = iv.get("status")
        if tid and act == ActivityType.DWELL.value and st == "COMPLETED":
            completed_target_ids.add(tid)
        elif tid and st == "BLOCKED":
            blocked_target_ids.add(tid)
        elif tid and st == "DEFERRED":
            deferred_target_ids.add(tid)

    # Complement with simulation target states if available
    sim_stats = sim_dict.get("statistics", {})
    if not completed_target_ids and sim_stats.get("completed_targets"):
        # Target state dictionary inspection
        for iv in timeline_intervals:
            if iv.get("target_id"):
                completed_target_ids.add(iv["target_id"])

    completed_count = len(completed_target_ids)
    blocked_count = len(blocked_target_ids)
    deferred_count = len(deferred_target_ids)
    unallocated_count = max(0, total_targets_count - (completed_count + blocked_count + deferred_count))

    prio_stats = {
        "high": {"total": 0, "completed": 0, "completion_rate_pct": 0.0},
        "medium": {"total": 0, "completed": 0, "completion_rate_pct": 0.0},
        "low": {"total": 0, "completed": 0, "completion_rate_pct": 0.0},
    }

    for tgt in all_targets:
        score = float(tgt.get("priority_score", 50.0))
        tid = tgt.get("id")
        if score >= 70.0:
            band = "high"
        elif score >= 40.0:
            band = "medium"
        else:
            band = "low"

        prio_stats[band]["total"] += 1
        if tid in completed_target_ids:
            prio_stats[band]["completed"] += 1

    for band in ("high", "medium", "low"):
        tot = prio_stats[band]["total"]
        comp = prio_stats[band]["completed"]
        prio_stats[band]["completion_rate_pct"] = round((comp / max(1, tot)) * 100.0, 1) if tot > 0 else 100.0

    target_completion_rate_pct = round((completed_count / max(1, total_targets_count)) * 100.0, 1)

    # 6. Unit Workload, Distance & Energy Decomposition (Zero Double-Counting)
    unit_workloads: List[UnitWorkload] = []
    total_distance_m = 0.0

    # Accumulate mutually-exclusive interval durations per unit
    unit_active_s: Dict[str, float] = {u["unit_id"]: 0.0 for u in units_list}
    unit_idle_s: Dict[str, float] = {u["unit_id"]: 0.0 for u in units_list}
    unit_dist_m: Dict[str, float] = {u["unit_id"]: 0.0 for u in units_list}

    for iv in timeline_intervals:
        uid = iv.get("unit_id")
        if uid not in unit_active_s:
            unit_active_s[uid] = 0.0
            unit_idle_s[uid] = 0.0
            unit_dist_m[uid] = 0.0

        dur = float(iv.get("duration_s", 0.0))
        dist = float(iv.get("distance_m", 0.0))
        act = iv.get("activity_type", ActivityType.IDLE.value)

        unit_dist_m[uid] += dist
        total_distance_m += dist

        if act in (ActivityType.TRANSIT.value, ActivityType.DWELL.value, ActivityType.HANDOFF.value):
            unit_active_s[uid] += dur
        elif act in (ActivityType.IDLE.value, ActivityType.HOLD.value, ActivityType.REST.value, ActivityType.OFFLINE.value):
            unit_idle_s[uid] += dur
        else:
            unit_active_s[uid] += dur

    for u in units_list:
        uid = u["unit_id"]
        uname = u.get("name", uid)
        utype = u.get("unit_type", UnitType.ROBOTIC_ROVER.value)
        act_s = unit_active_s.get(uid, 0.0)
        idl_s = unit_idle_s.get(uid, 0.0)
        tot_u_s = act_s + idl_s
        u_pct = round((act_s / max(1.0, tot_u_s)) * 100.0, 1) if tot_u_s > 0 else 0.0
        u_dist = unit_dist_m.get(uid, 0.0)

        # Modeled energy: rover ~ 18.5 Wh/km + active electronics, crew ~ 92 Wh/km life support
        rate_wh_per_km = 18.5 if utype == UnitType.ROBOTIC_ROVER.value else 92.0
        energy_kwh = round((u_dist / 1000.0) * (rate_wh_per_km / 1000.0), 3)

        uw = UnitWorkload(
            unit_id=uid,
            unit_name=uname,
            unit_type=utype,
            active_duration_s=act_s,
            idle_duration_s=idl_s,
            utilization_pct=u_pct,
            total_distance_m=u_dist,
            energy_consumed_kwh=energy_kwh,
        )
        unit_workloads.append(uw)

    # 7. Operational Holds Decomposition
    hold_intervals = [iv for iv in timeline_intervals if iv.get("activity_type") == ActivityType.HOLD.value]
    total_operational_holds = len(hold_intervals)
    total_hold_duration_s = sum(float(iv.get("duration_s", 0.0)) for iv in hold_intervals)

    # 8. Executive Summary Aggregates
    simulated_duration_s = float(sim_dict.get("total_duration_s", 0.0))
    if simulated_duration_s <= 0.0:
        simulated_duration_s = max((iv.get("end_time_s", 0.0) for iv in timeline_intervals), default=planned_total_duration_s)

    p_tot_r = round(planned_total_duration_s, 1)
    s_tot_r = round(simulated_duration_s, 1)
    duration_delta_s = round(s_tot_r - p_tot_r, 1)
    fleet_utilization_pct = round(
        sum(uw.utilization_pct for uw in unit_workloads) / max(1, len(unit_workloads)), 1
    ) if unit_workloads else 0.0
    temporal_conflicts_count = len(sim_conflicts)

    executive_summary = {
        "planned_duration_s": p_tot_r,
        "simulated_duration_s": s_tot_r,
        "duration_delta_s": duration_delta_s,
        "target_completion_rate_pct": target_completion_rate_pct,
        "total_distance_m": round(total_distance_m, 1),
        "total_operational_holds": total_operational_holds,
        "total_hold_duration_s": round(total_hold_duration_s, 1),
        "fleet_utilization_pct": fleet_utilization_pct,
        "temporal_conflicts_count": temporal_conflicts_count,
    }

    # 9. Deviation Detection & Causal Attribution Engine
    deviations: List[CampaignDeviation] = []

    # A. Sortie duration blowouts & start slips
    for s_dev in sortie_deviations:
        if s_dev.duration_delta_s > 300.0:
            # Find triggering events for this sortie's time range
            evts_in_range = [
                e for e in sim_events
                if s_dev.simulated_start_s <= e.get("simulated_time_s", 0.0) <= s_dev.simulated_end_s
            ]
            hold_evts = [
                e for e in evts_in_range
                if "HOLD" in e.get("event_type", "").upper() or "HAZARD" in e.get("event_type", "").upper() or "INTERRUPT" in e.get("event_type", "").upper()
            ]

            if hold_evts:
                causality = CauseAttribution.CONFIRMED_CAUSE.value
                trig_ids = [e.get("event_id", "") for e in hold_evts]
                explanation = (
                    f"Sortie '{s_dev.sortie_id}' exceeded planned duration by {s_dev.duration_delta_s:.1f}s "
                    f"due to verified operational hold/contingency events ({', '.join(trig_ids[:3])})."
                )
            elif evts_in_range:
                causality = CauseAttribution.CONTRIBUTING_FACTOR.value
                trig_ids = [e.get("event_id", "") for e in evts_in_range[:3]]
                explanation = (
                    f"Sortie '{s_dev.sortie_id}' experienced a duration increase of {s_dev.duration_delta_s:.1f}s "
                    f"with concurrent operational events occurring during execution."
                )
            else:
                causality = CauseAttribution.UNDETERMINED.value
                trig_ids = []
                explanation = (
                    f"Sortie '{s_dev.sortie_id}' executed slower than modeled baseline (+{s_dev.duration_delta_s:.1f}s) "
                    "without explicit discrete disruption events recorded."
                )

            severity = "blocker" if s_dev.duration_delta_s > 1800.0 else "warning"
            deviations.append(CampaignDeviation(
                deviation_id=f"dev_blowout_{s_dev.sortie_id}",
                code=DeviationCode.DEV_SORTIE_DURATION_BLOWOUT.value,
                severity=severity,
                affected_sortie_id=s_dev.sortie_id,
                planned_value={"value": s_dev.planned_duration_s, "unit": "seconds"},
                simulated_value={"value": s_dev.simulated_duration_s, "unit": "seconds"},
                delta_value={"value": s_dev.duration_delta_s, "unit": "seconds"},
                simulated_time_s=s_dev.simulated_start_s,
                triggering_event_ids=trig_ids,
                cause_attribution=causality,
                explanation=explanation,
                recommended_action=f"Expand duration margin for Sol {s_dev.sol_index} by at least {math.ceil(s_dev.duration_delta_s/60)} minutes.",
            ))

        if abs(s_dev.start_slip_s) > 300.0:
            deviations.append(CampaignDeviation(
                deviation_id=f"dev_startslip_{s_dev.sortie_id}",
                code=DeviationCode.DEV_SORTIE_START_SLIP.value,
                severity="info" if abs(s_dev.start_slip_s) < 1200.0 else "warning",
                affected_sortie_id=s_dev.sortie_id,
                planned_value={"value": s_dev.planned_start_s, "unit": "seconds"},
                simulated_value={"value": s_dev.simulated_start_s, "unit": "seconds"},
                delta_value={"value": s_dev.start_slip_s, "unit": "seconds"},
                simulated_time_s=s_dev.simulated_start_s,
                triggering_event_ids=[],
                cause_attribution=CauseAttribution.CONTRIBUTING_FACTOR.value if s_dev.sol_index > 1 else CauseAttribution.UNDETERMINED.value,
                explanation=f"Sortie '{s_dev.sortie_id}' departed with a start slip of {s_dev.start_slip_s:+.1f}s relative to planned Sol start.",
                recommended_action="Synchronize inter-sol reset procedures and stagger asset departures.",
            ))

    # B. Target abandonment or blocked targets
    for tgt in all_targets:
        tid = tgt.get("id")
        score = float(tgt.get("priority_score", 50.0))
        if tid not in completed_target_ids:
            # Check if blocked or deferred
            is_blocked = tid in blocked_target_ids
            dev_code = DeviationCode.DEV_TARGET_BLOCKED.value if is_blocked else DeviationCode.DEV_TARGET_ABANDONED.value
            severity = "blocker" if score >= 70.0 else "warning"

            # Check if any prerequisite failed
            prereqs = tgt.get("prerequisites", [])
            unmet_prereqs = [p for p in prereqs if p not in completed_target_ids]
            if unmet_prereqs:
                causality = CauseAttribution.CONFIRMED_CAUSE.value
                expl = f"Target '{tid}' ({tgt.get('name', '')}) was uncompleted because prerequisite target(s) {unmet_prereqs} were not completed."
            elif duration_delta_s > 0:
                causality = CauseAttribution.CONTRIBUTING_FACTOR.value
                expl = f"Target '{tid}' was uncompleted due to operational timeline constraints and duration compression."
            else:
                causality = CauseAttribution.UNDETERMINED.value
                expl = f"Target '{tid}' was scheduled but not reached during simulated campaign execution."

            deviations.append(CampaignDeviation(
                deviation_id=f"dev_tgt_{tid}",
                code=dev_code,
                severity=severity,
                affected_target_id=tid,
                simulated_time_s=simulated_duration_s,
                cause_attribution=causality,
                explanation=expl,
                recommended_action=f"Reallocate target '{tid}' to an alternate asset or include in subsequent campaign iteration.",
            ))

    # C. Operational hold prolonged
    if total_hold_duration_s > 900.0:
        hold_evt_ids = [e.get("event_id", "") for e in sim_events if "HOLD" in e.get("event_type", "").upper()]
        deviations.append(CampaignDeviation(
            deviation_id=f"dev_hold_prolonged_{uuid.uuid4().hex[:6]}",
            code=DeviationCode.DEV_CRITICAL_HOLD_PROLONGED.value,
            severity="warning" if total_hold_duration_s < 3600.0 else "blocker",
            simulated_time_s=float(hold_intervals[0].get("start_time_s", 0.0)) if hold_intervals else 0.0,
            planned_value={"value": 0.0, "unit": "seconds"},
            simulated_value={"value": total_hold_duration_s, "unit": "seconds"},
            delta_value={"value": total_hold_duration_s, "unit": "seconds"},
            triggering_event_ids=hold_evt_ids[:5],
            cause_attribution=CauseAttribution.CONFIRMED_CAUSE.value if hold_evt_ids else CauseAttribution.CONTRIBUTING_FACTOR.value,
            explanation=f"Fleet experienced {total_operational_holds} operational hold(s) totaling {total_hold_duration_s:.1f}s of non-productive dwell.",
            recommended_action="Audit terrain roughness and communication line-of-sight near hold waypoints.",
        ))

    # D. Fleet utilization imbalance
    if len(unit_workloads) > 1:
        u_pcts = [uw.utilization_pct for uw in unit_workloads]
        diff_pct = max(u_pcts) - min(u_pcts)
        if diff_pct > 30.0:
            least_used = min(unit_workloads, key=lambda u: u.utilization_pct)
            most_used = max(unit_workloads, key=lambda u: u.utilization_pct)
            deviations.append(CampaignDeviation(
                deviation_id=f"dev_imbalance_{uuid.uuid4().hex[:6]}",
                code=DeviationCode.DEV_FLEET_IDLE_IMBALANCE.value,
                severity="warning",
                affected_unit_id=least_used.unit_id,
                planned_value={"value": 50.0, "unit": "pct"},
                simulated_value={"value": least_used.utilization_pct, "unit": "pct"},
                delta_value={"value": round(least_used.utilization_pct - most_used.utilization_pct, 1), "unit": "pct"},
                simulated_time_s=0.0,
                cause_attribution=CauseAttribution.CONTRIBUTING_FACTOR.value,
                explanation=(
                    f"Fleet utilization imbalance of {diff_pct:.1f}% detected between '{most_used.unit_name}' "
                    f"({most_used.utilization_pct}%) and '{least_used.unit_name}' ({least_used.utilization_pct}%)."
                ),
                recommended_action=f"Shift target assignments from '{most_used.unit_id}' to underutilized asset '{least_used.unit_id}'.",
            ))

    # E. Temporal conflicts
    for c in sim_conflicts:
        cid = c.get("conflict_id", f"conf_{uuid.uuid4().hex[:6]}")
        deviations.append(CampaignDeviation(
            deviation_id=f"dev_conf_{cid}",
            code=DeviationCode.DEV_TEMPORAL_CONFLICT.value,
            severity=c.get("severity", "blocker"),
            affected_unit_id=c.get("affected_units", [None])[0] if c.get("affected_units") else None,
            affected_target_id=c.get("affected_targets", [None])[0] if c.get("affected_targets") else None,
            simulated_time_s=float(c.get("simulated_time_s", 0.0)),
            cause_attribution=CauseAttribution.CONFIRMED_CAUSE.value,
            explanation=c.get("message", "Temporal coordination conflict detected in timeline."),
            recommended_action=c.get("recommendation", "Adjust waypoint schedule or unit separation."),
        ))

    # 10. Grounded Lessons Learned Recommendations Engine
    lessons_learned: List[LessonsLearnedRecommendation] = []

    # Rule 1: Time Budget Calibration
    blowout_devs = [d for d in deviations if d.code == DeviationCode.DEV_SORTIE_DURATION_BLOWOUT.value]
    if blowout_devs or total_hold_duration_s > 1800.0:
        max_blowout = max([d.delta_value["value"] for d in blowout_devs if d.delta_value], default=total_hold_duration_s)
        rec_margin_s = math.ceil(max_blowout / 300.0) * 300.0 + 900.0
        lessons_learned.append(LessonsLearnedRecommendation(
            recommendation_id=f"rec_tb_{uuid.uuid4().hex[:6]}",
            category=RecommendationCategory.TIME_BUDGET.value,
            title="Expand Sortie Contingency Time Margin",
            evidence_references=[d.deviation_id for d in blowout_devs] + [d.deviation_id for d in deviations if d.code == DeviationCode.DEV_CRITICAL_HOLD_PROLONGED.value],
            rationale=(
                f"Simulated execution revealed sortie duration overruns up to {max_blowout:.0f}s and "
                f"{total_hold_duration_s:.0f}s of operational holds. Baseline duration buffers were insufficient."
            ),
            expected_impact=f"Provides {rec_margin_s/60:.0f} minutes of additional operational buffer, preventing late sol cutoffs.",
            assumptions_and_limitations="Assumes crew EVA life support reserves or rover battery depth of discharge allows extended margin.",
            proposed_change={
                "type": "parameter_adjustment",
                "parameter": "max_duration_per_sortie_s",
                "current_value": camp_dict.get("config", {}).get("max_duration_per_sortie_s", 28800.0),
                "recommended_value": min(36000.0, float(camp_dict.get("config", {}).get("max_duration_per_sortie_s", 28800.0)) + rec_margin_s),
            },
            status=RecommendationStatus.ACTIVE.value,
        ))

    # Rule 2: Coordination Strategy Adaptation
    conflict_devs = [d for d in deviations if d.code == DeviationCode.DEV_TEMPORAL_CONFLICT.value]
    if conflict_devs:
        lessons_learned.append(LessonsLearnedRecommendation(
            recommendation_id=f"rec_coord_{uuid.uuid4().hex[:6]}",
            category=RecommendationCategory.COORDINATION_STRATEGY.value,
            title="Adopt Zone-Split Spatial Deconfliction",
            evidence_references=[d.deviation_id for d in conflict_devs],
            rationale=f"Encountered {len(conflict_devs)} temporal conflict(s) where multiple units had overlapping spatial/target windows.",
            expected_impact="Eliminates spatial interference by partitioning Jezero exploration zones geographically.",
            assumptions_and_limitations="Requires adequate science targets within each geographic sector to keep all units productive.",
            proposed_change={
                "type": "coordination_strategy",
                "strategy": "ZONE_SPLIT",
                "separation_distance_m": 150.0,
            },
            status=RecommendationStatus.ACTIVE.value,
        ))

    # Rule 3: Task Sequencing & Prerequisite Alignment
    unmet_tgt_devs = [d for d in deviations if d.code in (DeviationCode.DEV_TARGET_ABANDONED.value, DeviationCode.DEV_TARGET_BLOCKED.value)]
    high_unmet = [d for d in unmet_tgt_devs if d.severity == "blocker"]
    if high_unmet:
        lessons_learned.append(LessonsLearnedRecommendation(
            recommendation_id=f"rec_seq_{uuid.uuid4().hex[:6]}",
            category=RecommendationCategory.TASK_SEQUENCING.value,
            title="Front-Load High-Priority Prerequisite Targets",
            evidence_references=[d.deviation_id for d in high_unmet],
            rationale=f"{len(high_unmet)} high-priority target(s) were missed due to prerequisite cascading or late scheduling.",
            expected_impact="Guarantees core primary mission science objectives are achieved early before contingency accumulation.",
            assumptions_and_limitations="May increase initial traverse distances on Sol 1 to reach high-value reconnaissance waypoints.",
            proposed_change={
                "type": "task_reordering",
                "action": "PRIORITIZE_PREREQUISITES",
                "affected_target_ids": [d.affected_target_id for d in high_unmet if d.affected_target_id],
            },
            status=RecommendationStatus.ACTIVE.value,
        ))

    # Rule 4: Unit Workload Reallocation
    imbalance_devs = [d for d in deviations if d.code == DeviationCode.DEV_FLEET_IDLE_IMBALANCE.value]
    if imbalance_devs:
        imb_dev = imbalance_devs[0]
        lessons_learned.append(LessonsLearnedRecommendation(
            recommendation_id=f"rec_alloc_{uuid.uuid4().hex[:6]}",
            category=RecommendationCategory.UNIT_ASSIGNMENT.value,
            title="Rebalance Target Allocations Across Fleet Assets",
            evidence_references=[imb_dev.deviation_id],
            rationale="Disproportionate workload distribution led to asset idling while other units were over-utilized.",
            expected_impact="Balances fleet utilization closer to parity and reduces single-asset wear and tear.",
            assumptions_and_limitations="Assumes secondary asset has instrument capabilities matching assigned targets.",
            proposed_change={
                "type": "unit_rebalance",
                "target_utilization_pct": 50.0,
                "underutilized_unit_id": imb_dev.affected_unit_id,
            },
            status=RecommendationStatus.ACTIVE.value,
        ))

    # Rule 5: Scenario Coverage Expansion (Always generate at least 1 grounded advisory)
    if not lessons_learned:
        lessons_learned.append(LessonsLearnedRecommendation(
            recommendation_id=f"rec_cov_{uuid.uuid4().hex[:6]}",
            category=RecommendationCategory.SCENARIO_COVERAGE.value,
            title="Stress-Test Against Dust Storm and Solar Degradation Scenarios",
            evidence_references=[],
            rationale="Current campaign plan demonstrated nominal performance, but environmental margin under adverse dust optical depth remains unverified.",
            expected_impact="Quantifies operational resilience thresholds before committing to physical surface traverse.",
            assumptions_and_limitations="Contingency simulations depend on modeled tau optical depth degradation curves.",
            proposed_change={
                "type": "whatif_simulation_suite",
                "recommended_scenarios": ["dust_storm_tau_2.0", "battery_capacity_degraded_20pct"],
            },
            status=RecommendationStatus.ACTIVE.value,
        ))

    # 11. Assemble Master Analytics Record
    anl_id = analysis_id or f"anl_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    analysis_record = {
        "schema_version": SCHEMA_VERSION,
        "analysis_id": anl_id,
        "campaign_id": camp_id,
        "campaign_version": camp_version,
        "simulation_id": sim_id,
        "created_at_utc": now_iso,
        "executive_summary": executive_summary,
        "sortie_deviations": [s.to_dict() for s in sortie_deviations],
        "target_analytics": {
            "total_targets": total_targets_count,
            "completed_count": completed_count,
            "deferred_count": deferred_count,
            "blocked_count": blocked_count,
            "unallocated_count": unallocated_count,
            "priority_breakdown": prio_stats,
        },
        "unit_workloads": [uw.to_dict() for uw in unit_workloads],
        "deviations": [d.to_dict() for d in deviations],
        "lessons_learned": [rec.to_dict() for rec in lessons_learned],
        "limitations_disclaimer": ANALYTICS_DISCLAIMER,
    }

    clean_record = sanitize_for_json(analysis_record)
    validate_campaign_analytics_record(clean_record)
    return clean_record
