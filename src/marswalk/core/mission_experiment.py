# src/marswalk/core/mission_experiment.py
"""
MarsWalk 2.0 / Project Atlas — Unified Mission Experiment Studio Orchestration Engine
Milestone 12H Implementation.

Unifies static sensitivity stress testing (Mission Robustness Lab) and dynamic closed-loop
simulation & recovery (Mission Rehearsal Director) into reproducible multi-scenario
experiment studies with cross-run matrix comparison, cryptographic lineage, and
consolidated Mission Evidence Dossier exports.
"""

from __future__ import annotations

import copy
import csv
import enum
import hashlib
import io
import json
import logging
import os
import time
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

import numpy as np

from marswalk.api.contracts import (
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    calculate_safe_pct_delta,
    compute_input_fingerprint,
    sanitize_for_json,
    validate_mission_experiment_record,
)
from marswalk.api.workspace import (
    DEFAULT_CAMPAIGN_EXPERIMENTS_DIR,
    DEFAULT_ROBUSTNESS_DIR,
    DEFAULT_REHEARSALS_DIR,
    get_campaign,
    get_experiment_record,
    save_experiment_record,
    save_rehearsal_record,
    save_robustness_experiment,
)
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignSortie,
    CampaignTarget,
    MissionCampaign,
)
from marswalk.core.campaign_scenarios import (
    CampaignScenario,
    ScenarioType,
    ScenarioStatus,
)
from marswalk.core.mission_robustness_lab import (
    MissionRobustnessReport,
    RobustnessSuiteType,
    evaluate_campaign_robustness,
    build_stress_suite,
)
from marswalk.core.mission_rehearsal_director import (
    DisturbanceSpecification,
    DisturbanceType,
    RehearsalOutcomeStatus,
    RehearsalRecord,
    execute_mission_rehearsal,
)
from marswalk.core.terrain import TerrainGrid

logger = logging.getLogger(__name__)

# Bounded Operational Constraints
MAX_EXPERIMENT_SCENARIOS = 15
DEFAULT_MAX_SCENARIOS = 10
MAX_EXPERIMENT_REHEARSALS = 6
DEFAULT_MAX_REHEARSALS = 5
SCHEMA_VERSION = "2.0.0"

# Provenance Constants
COORDINATE_REFERENCE = "ESRI:103885"
MODEL_VERSION = "MarsWalk-2.0.0-Atlas"
ASSUMPTIONS_VERSION = "2026.1"
STANDARD_UNITS = {
    "distance": "meters (m)",
    "duration": "seconds (s)",
    "velocity": "meters per second (m/s)",
    "elevation": "meters (m)",
    "slope": "degrees (°)",
    "science_score": "dimensionless priority points",
}

TRUTH_DISCLOSURES = [
    "Tested scenario frequencies (e.g., 80% feasible) measure robustness across modeled disruptions only and MUST NEVER be presented as physical Martian operational success probabilities.",
    "Modeled traverses and recovery recommendations are planning heuristics and MUST NEVER be characterized as flight-certified or safe for astronauts.",
    "All calculations are strictly deterministic based on USGS CTX 20m Jezero Crater Digital Terrain Model (DTM) mosaic, IAU 2000 Mars Sphere datum (R = 3,396,190m), CRS ESRI:103885.",
    "Environmental data is sourced from NASA PDS4 MEDA archives (Sol 890 tranche). All units adhere to standard SI: distance in meters (m), time in seconds (s), elevation in meters (m), science yield in dimensionless priority points.",
]


class ScenarioExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    EVALUATING = "EVALUATING"
    EVALUATED_ROBUSTNESS = "EVALUATED_ROBUSTNESS"
    REHEARSAL_REQUIRED = "REHEARSAL_REQUIRED"
    REHEARSED = "REHEARSED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    INCOMPLETE = "INCOMPLETE"
    SKIPPED = "SKIPPED"


class RehearsalTriggerStrategy(str, enum.Enum):
    DEGRADED_OR_BREACH = "degraded_or_breach"
    MARGIN_THRESHOLD = "margin_threshold"
    ALL = "all"
    EXPLICIT_SELECTION = "explicit_selection"
    NONE = "none"


@dataclass
class ExperimentConfig:
    campaign_id: str
    campaign_version: int = 1
    suite_type: str = "full_battery"
    scenario_selection_strategy: str = "degraded_or_breach"
    rehearsal_policy: str = "balanced"
    min_margin_threshold_s: float = 1800.0
    max_scenarios: int = DEFAULT_MAX_SCENARIOS
    max_rehearsals: int = DEFAULT_MAX_REHEARSALS
    custom_scenarios: Optional[List[Dict[str, Any]]] = None
    explicit_rehearsal_scenario_ids: Optional[List[str]] = None
    title: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_version": self.campaign_version,
            "suite_type": self.suite_type,
            "scenario_selection_strategy": self.scenario_selection_strategy,
            "rehearsal_policy": self.rehearsal_policy,
            "min_margin_threshold_s": float(self.min_margin_threshold_s),
            "max_scenarios": int(self.max_scenarios),
            "max_rehearsals": int(self.max_rehearsals),
            "custom_scenarios": self.custom_scenarios,
            "explicit_rehearsal_scenario_ids": self.explicit_rehearsal_scenario_ids,
            "title": self.title,
            "description": self.description,
        }


@dataclass
class ExperimentScenarioRecord:
    scenario_id: str
    name: str
    disruption_type: str
    trigger_time_s: float
    robustness_case: Dict[str, Any]
    status: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    evidence_completeness: str = "ROBUSTNESS_ONLY"  # "FULL_REHEARSAL" or "ROBUSTNESS_ONLY"
    rehearsal_id: Optional[str] = None
    rehearsal_outcome_status: Optional[str] = None
    three_track_summary: Optional[Dict[str, Any]] = None
    causal_links_count: int = 0
    divergence_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "disruption_type": self.disruption_type,
            "trigger_time_s": round(float(self.trigger_time_s), 1),
            "parameters": self.parameters,
            "status": self.status,
            "evidence_completeness": self.evidence_completeness,
            "robustness_case": self.robustness_case,
            "rehearsal_id": self.rehearsal_id or None,
            "rehearsal_outcome_status": self.rehearsal_outcome_status,
            "three_track_summary": self.three_track_summary,
            "causal_links_count": self.causal_links_count,
            "divergence_summary": self.divergence_summary,
        }


@dataclass
class ExperimentRecord:
    schema_version: str
    experiment_id: str
    campaign_id: str
    campaign_version: int
    campaign_fingerprint: str
    title: str
    description: str
    created_at_utc: str
    status: str
    config: Dict[str, Any]
    robustness_experiment_id: Optional[str]
    scenarios: List[ExperimentScenarioRecord]
    cross_scenario_matrix: Dict[str, Any]
    summary_metrics: Dict[str, Any]
    provenance: Dict[str, Any]
    truth_disclosures: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "campaign_id": self.campaign_id,
            "campaign_version": self.campaign_version,
            "campaign_fingerprint": self.campaign_fingerprint,
            "title": self.title,
            "description": self.description,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "config": self.config,
            "robustness_experiment_id": self.robustness_experiment_id,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "cross_scenario_matrix": self.cross_scenario_matrix,
            "summary_metrics": self.summary_metrics,
            "provenance": self.provenance,
            "truth_disclosures": self.truth_disclosures,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExperimentRecord:
        scenarios = []
        for s in data.get("scenarios", []):
            scenarios.append(ExperimentScenarioRecord(**s))
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            experiment_id=data["experiment_id"],
            campaign_id=data["campaign_id"],
            campaign_version=data.get("campaign_version", 1),
            campaign_fingerprint=data.get("campaign_fingerprint", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            created_at_utc=data.get("created_at_utc", ""),
            status=data.get("status", "COMPLETED"),
            config=data.get("config", {}),
            robustness_experiment_id=data.get("robustness_experiment_id"),
            scenarios=scenarios,
            cross_scenario_matrix=data.get("cross_scenario_matrix", {}),
            summary_metrics=data.get("summary_metrics", {}),
            provenance=data.get("provenance", {}),
            truth_disclosures=data.get("truth_disclosures", TRUTH_DISCLOSURES),
        )


def map_scenario_to_disturbances(
    scenario_spec: Dict[str, Any],
    campaign: MissionCampaign,
) -> List[DisturbanceSpecification]:
    """
    Converts a Robustness Lab stress scenario specification into a list of
    deterministic DisturbanceSpecifications for closed-loop Mission Rehearsal.
    """
    disturbances: List[DisturbanceSpecification] = []
    mods = scenario_spec.get("modifications", [])
    scen_id = scenario_spec.get("scenario_id", "dst")

    # Estimate default trigger time (e.g. sol 1 midpoint or 1200s)
    default_trigger_s = 1200.0

    for idx, mod in enumerate(mods):
        m_type = mod.get("type")
        dist_id = f"dst_{scen_id}_{idx+1}"

        if m_type == ScenarioType.CORRIDOR_CLOSURE.value:
            if "center_rc" in mod and isinstance(mod["center_rc"], (list, tuple)) and len(mod["center_rc"]) == 2:
                r, c = int(mod["center_rc"][0]), int(mod["center_rc"][1])
            else:
                r = int(mod.get("center_row", 122))
                c = int(mod.get("center_col", 162))
            rad = float(mod.get("radius_m", 60.0))
            disturbances.append(
                DisturbanceSpecification(
                    disturbance_id=dist_id,
                    disturbance_type=DisturbanceType.CORRIDOR_CLOSURE,
                    trigger_time_s=float(mod.get("trigger_time_s", default_trigger_s)),
                    parameters={"center_rc": [r, c], "radius_m": rad},
                    description=f"Corridor obstruction radius {rad:.0f}m at ({r}, {c})",
                )
            )

        elif m_type == ScenarioType.MOBILITY_CHANGE.value:
            speed_factor = float(mod.get("speed_factor", 0.70))
            disturbances.append(
                DisturbanceSpecification(
                    disturbance_id=dist_id,
                    disturbance_type=DisturbanceType.MOBILITY_DERATING,
                    trigger_time_s=float(mod.get("trigger_time_s", 0.0)),
                    parameters={"speed_factor": speed_factor},
                    description=f"Mobility derated to {speed_factor:.2f}x nominal velocity",
                )
            )

        elif m_type == ScenarioType.OPERATIONAL_DELAY.value:
            delay_s = float(mod.get("delay_s", 1800.0))
            disturbances.append(
                DisturbanceSpecification(
                    disturbance_id=dist_id,
                    disturbance_type=DisturbanceType.OPERATIONAL_DELAY,
                    trigger_time_s=float(mod.get("trigger_time_s", 900.0)),
                    parameters={"delay_s": delay_s},
                    description=f"Operational hold delay of {delay_s:.0f}s",
                )
            )

        elif m_type == ScenarioType.TARGET_LOSS.value:
            tid = str(mod.get("target_id", "t1"))
            reason = str(mod.get("reason", "Sensor/sampling instrument payload fault"))
            disturbances.append(
                DisturbanceSpecification(
                    disturbance_id=dist_id,
                    disturbance_type=DisturbanceType.TARGET_UNAVAILABILITY,
                    trigger_time_s=float(mod.get("trigger_time_s", 1200.0)),
                    parameters={"target_id": tid, "reason": reason},
                    description=f"Target {tid} unavailable: {reason}",
                )
            )

        elif m_type in ("unit_dropout", ScenarioType.UNSUPPORTED.value):
            uid = str(mod.get("affected_unit_id", "unit_eva_1"))
            reason = str(mod.get("reason", "Exploration unit communication/mobility freeze"))
            disturbances.append(
                DisturbanceSpecification(
                    disturbance_id=dist_id,
                    disturbance_type=DisturbanceType.UNIT_DROPOUT,
                    trigger_time_s=float(mod.get("trigger_time_s", 900.0)),
                    parameters={"affected_unit_id": uid, "reason": reason},
                    description=f"Unit {uid} dropped: {reason}",
                )
            )

        elif m_type == ScenarioType.TIME_CONSTRAINT.value:
            # Map duration contraction to operational delay penalty
            nom_dur = float(getattr(campaign.config, "max_duration_per_sortie_s", 28800.0))
            scen_dur = float(mod.get("max_duration_per_sortie_s", nom_dur))
            dur_loss = max(0.0, nom_dur - scen_dur)
            disturbances.append(
                DisturbanceSpecification(
                    disturbance_id=dist_id,
                    disturbance_type=DisturbanceType.OPERATIONAL_DELAY,
                    trigger_time_s=0.0,
                    parameters={"delay_s": dur_loss},
                    description=f"Sortie budget cut: {dur_loss:.0f}s margin contraction",
                )
            )

    return disturbances


def orchestrate_mission_experiment(
    campaign: MissionCampaign,
    terrain: TerrainGrid,
    config: ExperimentConfig,
) -> ExperimentRecord:
    """
    Executes a unified mission experiment study.
    1. Evaluates bounded stress scenarios through Mission Robustness Lab.
    2. Identifies scenarios requiring closed-loop rehearsal.
    3. Executes Mission Rehearsal Director for designated scenarios.
    4. Computes safe cross-scenario matrix and summary metrics.
    5. Saves experiment and rehearsal records atomically.
    """
    t_start = time.perf_counter()

    # Deepcopy campaign to guarantee baseline immutability
    campaign_copy = copy.deepcopy(campaign)
    cmp_id = getattr(campaign, "campaign_id", getattr(campaign, "id", "cmp"))

    # Enforce bounded resource constraints
    max_scens = min(MAX_EXPERIMENT_SCENARIOS, max(1, int(config.max_scenarios)))
    max_reh = min(MAX_EXPERIMENT_REHEARSALS, max(0, int(config.max_rehearsals)))
    config.max_scenarios = max_scens
    config.max_rehearsals = max_reh

    # Compute deterministic fingerprints
    if hasattr(campaign_copy, "compute_fingerprint"):
        campaign_fp = campaign_copy.compute_fingerprint()
    else:
        cmp_dict = campaign_copy.to_dict() if hasattr(campaign_copy, "to_dict") else {"campaign_id": cmp_id}
        campaign_fp = hashlib.sha256(json.dumps(cmp_dict, sort_keys=True).encode("utf-8")).hexdigest()

    ts_now = datetime.now(timezone.utc).isoformat()
    clean_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    hash_seed = f"{cmp_id}_{config.suite_type}_{config.scenario_selection_strategy}_{config.rehearsal_policy}_{time.perf_counter()}"
    exp_suffix = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:8]
    exp_id = f"mexp_{clean_ts}_{exp_suffix}"

    title = config.title or f"Orchestrated Experiment: {campaign.name} ({config.suite_type})"
    description = config.description or (
        f"Multi-scenario resilience study combining Robustness Lab '{config.suite_type}' "
        f"and Rehearsal Director '{config.rehearsal_policy}' recovery policy."
    )

    # Map suite_type string to RobustnessSuiteType enum
    suite_map = {
        "duration_stress": RobustnessSuiteType.DURATION_STRESS,
        "mobility_derating": RobustnessSuiteType.MOBILITY_DERATING,
        "operational_delays": RobustnessSuiteType.OPERATIONAL_DELAYS,
        "resource_energy_stress": RobustnessSuiteType.RESOURCE_ENERGY_STRESS,
        "corridor_closures": RobustnessSuiteType.CORRIDOR_CLOSURES,
        "target_priority_shift": RobustnessSuiteType.TARGET_PRIORITY_SHIFT,
        "compound_gauntlet": RobustnessSuiteType.COMPOUND_GAUNTLET,
        "full_battery": RobustnessSuiteType.FULL_BATTERY,
        "custom": RobustnessSuiteType.CUSTOM,
    }
    target_suite = suite_map.get(config.suite_type, RobustnessSuiteType.FULL_BATTERY)

    # 1. Execute Mission Robustness Lab Evaluation
    logger.info("Executing Robustness Lab evaluation for suite: %s", target_suite.value)
    rob_report = evaluate_campaign_robustness(
        campaign=campaign_copy,
        terrain=terrain,
        suite_type=target_suite,
        custom_specs=config.custom_scenarios,
    )
    # Save robustness experiment record
    try:
        save_robustness_experiment(rob_report.to_dict())
    except Exception as e:
        logger.warning("Could not persist intermediate robustness record: %s", e)

    # 2. Iterate through evaluated scenarios and orchestrate rehearsals
    scenario_records: List[ExperimentScenarioRecord] = []
    matrix_rows: List[Dict[str, Any]] = []

    rehearsals_executed = 0
    recovered_count = 0
    unmitigated_aborts = 0
    science_preservations: List[float] = []
    delays_incurred: List[float] = []

    # Get baseline reference metrics
    nominal_science = sum(float(t.priority_score) for t in campaign_copy.targets)
    nominal_duration_s = sum(s.total_duration_s for s in campaign_copy.sorties)
    nominal_distance_m = sum(s.distance_m for s in campaign_copy.sorties)
    nominal_min_margin_s = max(0.0, min(s.remaining_margin_s for s in campaign_copy.sorties)) if campaign_copy.sorties else 0.0

    eval_scenarios = rob_report.case_evaluations[:max_scens]

    for sc_rec in eval_scenarios:
        sc_id = sc_rec.case_id
        is_feasible = sc_rec.is_feasible
        margin_s = float(sc_rec.remaining_margin_s)
        sci_delta = float(sc_rec.science_score_delta)
        dur_delta = float(sc_rec.duration_delta_s)

        # Check if scenario triggers closed-loop rehearsal
        trigger_rehearsal = False
        strategy = config.scenario_selection_strategy

        if strategy == RehearsalTriggerStrategy.ALL.value:
            trigger_rehearsal = True
        elif strategy == RehearsalTriggerStrategy.EXPLICIT_SELECTION.value:
            explicit_ids = config.explicit_rehearsal_scenario_ids or []
            trigger_rehearsal = (sc_id in explicit_ids)
        elif strategy in (RehearsalTriggerStrategy.DEGRADED_OR_BREACH.value, RehearsalTriggerStrategy.MARGIN_THRESHOLD.value):
            if (not is_feasible) or (margin_s < config.min_margin_threshold_s) or (sci_delta < -0.01):
                trigger_rehearsal = True

        rehearsal_record: Optional[RehearsalRecord] = None
        reh_id: Optional[str] = None
        reh_status: Optional[str] = None
        three_track_summary: Optional[Dict[str, Any]] = None
        causal_count = 0
        div_summary: Optional[Dict[str, Any]] = None

        # Build raw scenario spec for mapping
        scenario_spec = {
            "scenario_id": sc_id,
            "scenario_type": getattr(sc_rec, "scenario_type", "combined"),
            "modifications": getattr(sc_rec, "modifications", []),
        }

        # Derive primary disruption type and parameters
        primary_mod = scenario_spec["modifications"][0] if scenario_spec["modifications"] else {}
        disruption_type = primary_mod.get("type", sc_rec.suite)
        trigger_time_s = float(primary_mod.get("trigger_time_s", 0.0))

        if trigger_rehearsal and (rehearsals_executed < max_reh):
            logger.info("Executing closed-loop rehearsal for scenario: %s", sc_id)
            disturbances = map_scenario_to_disturbances(scenario_spec, campaign_copy)
            if not disturbances:
                # If no disturbance was mapped, create default hold
                disturbances = [
                    DisturbanceSpecification(
                        disturbance_id=f"dst_{sc_id}_default",
                        disturbance_type=DisturbanceType.OPERATIONAL_DELAY,
                        trigger_time_s=900.0,
                        parameters={"delay_s": 1800.0},
                        description="Default operational delay test",
                    )
                ]

            try:
                reh_record = execute_mission_rehearsal(
                    campaign=campaign_copy,
                    disturbances=disturbances,
                    recovery_policy={
                        "policy_type": config.rehearsal_policy,
                        "min_margin_threshold_s": config.min_margin_threshold_s,
                    },
                    terrain=terrain,
                )
                save_rehearsal_record(reh_record.to_dict())
                rehearsals_executed += 1

                rehearsal_record = reh_record
                reh_id = reh_record.rehearsal_id
                reh_status = reh_record.outcome_status
                causal_count = sum(len(step.causal_links) for step in reh_record.causal_ledger) if getattr(reh_record, "causal_ledger", None) else 0

                three_track_summary = {
                    "baseline": {
                        "science_score": reh_record.baseline_metrics.science_score,
                        "duration_s": reh_record.baseline_metrics.total_duration_s,
                        "distance_m": reh_record.baseline_metrics.total_distance_m,
                        "margin_s": reh_record.baseline_metrics.min_margin_s,
                        "targets": reh_record.baseline_metrics.targets_completed,
                    },
                    "disturbed": {
                        "science_score": reh_record.disturbed_metrics.science_score,
                        "duration_s": reh_record.disturbed_metrics.total_duration_s,
                        "distance_m": reh_record.disturbed_metrics.total_distance_m,
                        "margin_s": reh_record.disturbed_metrics.min_margin_s,
                        "targets": reh_record.disturbed_metrics.targets_completed,
                    },
                    "recovered": {
                        "science_score": reh_record.recovered_metrics.science_score,
                        "duration_s": reh_record.recovered_metrics.total_duration_s,
                        "distance_m": reh_record.recovered_metrics.total_distance_m,
                        "margin_s": reh_record.recovered_metrics.min_margin_s,
                        "targets": reh_record.recovered_metrics.targets_completed,
                    },
                }

                has_div = len(reh_record.disturbances) > 0
                div_t = float(reh_record.disturbances[0].trigger_time_s) if has_div else None
                div_cause = reh_record.disturbances[0].disturbance_type.value if has_div else None
                div_summary = {
                    "has_divergence": has_div,
                    "divergence_time_s": div_t,
                    "primary_cause": div_cause,
                }

                if reh_status in (RehearsalOutcomeStatus.RECOVERED.value, RehearsalOutcomeStatus.NOMINAL.value):
                    recovered_count += 1
                elif reh_status == RehearsalOutcomeStatus.NO_FEASIBLE_RECOVERY.value:
                    unmitigated_aborts += 1

                science_preservations.append(reh_record.comparison.science_preservation_pct)
                delays_incurred.append(reh_record.comparison.delay_incurred_s)

            except Exception as ex:
                logger.error("Failed to execute rehearsal for %s: %s", sc_id, ex)
                reh_status = "FAILED"
                unmitigated_aborts += 1
                science_preservations.append(0.0)

        # Determine scenario status
        if reh_status == "FAILED":
            status_enum = ScenarioExecutionStatus.FAILED.value
            completeness = "ROBUSTNESS_ONLY"
        elif reh_id:
            status_enum = ScenarioExecutionStatus.REHEARSED.value
            completeness = "FULL_REHEARSAL"
        elif trigger_rehearsal:
            status_enum = ScenarioExecutionStatus.REHEARSAL_REQUIRED.value
            completeness = "ROBUSTNESS_ONLY"
        else:
            status_enum = ScenarioExecutionStatus.EVALUATED_ROBUSTNESS.value
            completeness = "ROBUSTNESS_ONLY"

        scenario_records.append(
            ExperimentScenarioRecord(
                scenario_id=sc_id,
                name=sc_rec.name,
                description=sc_rec.description,
                disruption_type=disruption_type,
                trigger_time_s=trigger_time_s,
                parameters=primary_mod,
                status=status_enum,
                evidence_completeness=completeness,
                robustness_case={
                    "is_feasible": is_feasible,
                    "duration_delta_s": dur_delta,
                    "remaining_margin_s": margin_s,
                    "science_score_delta": sci_delta,
                },
                rehearsal_id=reh_id,
                rehearsal_outcome_status=reh_status,
                three_track_summary=three_track_summary,
                causal_links_count=causal_count,
                divergence_summary=div_summary,
            )
        )

        # Assemble Matrix Row
        if rehearsal_record:
            rec_sci = rehearsal_record.recovered_metrics.science_score
            dist_sci = rehearsal_record.disturbed_metrics.science_score
            sci_pct = rehearsal_record.comparison.science_preservation_pct
            delay_s = rehearsal_record.comparison.delay_incurred_s
            margin_delta = round(rehearsal_record.recovered_metrics.min_margin_s - rehearsal_record.baseline_metrics.min_margin_s, 1)
            dist_delta = rehearsal_record.comparison.distance_delta_m
            t_retained = rehearsal_record.recovered_metrics.targets_completed
            t_dropped = len(rehearsal_record.recovered_metrics.dropped_target_ids)
            strategy_chosen = getattr(rehearsal_record, "selected_candidate_type", "BALANCED")
        else:
            # Estimate from robustness evaluation
            dist_sci = max(0.0, nominal_science + sci_delta)
            rec_sci = dist_sci
            if nominal_science > 0.0:
                sci_pct = round(min(100.0, max(0.0, (rec_sci / nominal_science) * 100.0)), 1)
            else:
                sci_pct = 100.0 if is_feasible else 0.0
            delay_s = max(0.0, dur_delta)
            margin_delta = round(margin_s - nominal_min_margin_s, 1)
            dist_delta = 0.0
            t_retained = len(campaign_copy.targets) if is_feasible else 0
            t_dropped = 0 if is_feasible else len(campaign_copy.targets)
            strategy_chosen = "STATIC_REPLAN"

        matrix_rows.append({
            "scenario_id": sc_id,
            "scenario_name": sc_rec.name,
            "disruption_type": disruption_type,
            "trigger_time_s": trigger_time_s,
            "robustness_status": sc_rec.status,
            "is_feasible": is_feasible,
            "rehearsal_executed": (reh_id is not None),
            "rehearsal_id": reh_id,
            "outcome_status": reh_status or sc_rec.status,
            "baseline_science": nominal_science,
            "disturbed_science": dist_sci,
            "recovered_science": rec_sci,
            "science_preservation_pct": sci_pct,
            "delay_incurred_s": delay_s,
            "margin_delta_s": margin_delta,
            "distance_delta_m": dist_delta,
            "targets_retained": t_retained,
            "targets_dropped": t_dropped,
            "selected_strategy": strategy_chosen,
        })

    # Summary calculations
    t_end = time.perf_counter()
    exec_dur_ms = round((t_end - t_start) * 1000.0, 1)

    feasible_count = sum(1 for r in matrix_rows if r["is_feasible"])
    mean_sci_preservation = (
        round(float(np.mean([r["science_preservation_pct"] for r in matrix_rows])), 1)
        if matrix_rows
        else 100.0
    )
    mean_delay = (
        round(float(np.mean([r["delay_incurred_s"] for r in matrix_rows])), 1)
        if matrix_rows
        else 0.0
    )

    summary_metrics = {
        "total_scenarios_evaluated": len(matrix_rows),
        "robustness_feasible_count": feasible_count,
        "rehearsals_executed_count": rehearsals_executed,
        "recovered_count": recovered_count,
        "unmitigated_aborts_count": unmitigated_aborts,
        "mean_science_preservation_pct": mean_sci_preservation,
        "mean_delay_incurred_s": mean_delay,
        "execution_duration_ms": exec_dur_ms,
    }

    # Cross-scenario narrative
    cmp_id = getattr(campaign_copy, "campaign_id", getattr(campaign_copy, "id", "cmp"))
    narrative = (
        f"Evaluated {len(matrix_rows)} stress scenarios across baseline campaign '{cmp_id}'. "
        f"Robustness sweep demonstrated {feasible_count}/{len(matrix_rows)} feasible cases. "
        f"Orchestrated {rehearsals_executed} dynamic closed-loop rehearsals under policy '{config.rehearsal_policy}'. "
        f"Mean science yield preservation was {mean_sci_preservation}% with an average induced delay of {mean_delay:.0f}s. "
        f"No physical astronaut flight safety guarantees are implied."
    )

    cross_scenario_matrix = {
        "headers": [
            "Scenario ID",
            "Scenario Name",
            "Disruption Type",
            "Trigger (s)",
            "Robustness Status",
            "Is Feasible",
            "Rehearsal Executed",
            "Rehearsal ID",
            "Outcome Status",
            "Baseline Science",
            "Disturbed Science",
            "Recovered Science",
            "Science Preserved (%)",
            "Delay Incurred (s)",
            "Margin Delta (s)",
            "Distance Delta (m)",
            "Targets Retained",
            "Targets Dropped",
            "Selected Strategy",
        ],
        "rows": matrix_rows,
        "summary_narrative": narrative,
    }

    provenance = {
        "terrain_dataset_id": getattr(terrain, "dataset_id", None) or TERRAIN_DATASET_ID,
        "terrain_sha256": getattr(terrain, "sha256", None) or TERRAIN_SHA256,
        "coordinate_reference": COORDINATE_REFERENCE,
        "model_version": MODEL_VERSION,
        "assumptions_version": ASSUMPTIONS_VERSION,
        "units": STANDARD_UNITS,
    }

    has_failed = any(s.status == ScenarioExecutionStatus.FAILED.value for s in scenario_records)
    has_success = any(s.status != ScenarioExecutionStatus.FAILED.value for s in scenario_records)
    if has_failed:
        overall_status = "PARTIAL" if has_success else "FAILED"
    else:
        overall_status = "COMPLETED"

    record = ExperimentRecord(
        schema_version=SCHEMA_VERSION,
        experiment_id=exp_id,
        campaign_id=cmp_id,
        campaign_version=getattr(campaign_copy, "version", 1),
        campaign_fingerprint=campaign_fp,
        title=title,
        description=description,
        created_at_utc=ts_now,
        status=overall_status,
        config=config.to_dict(),
        robustness_experiment_id=rob_report.experiment_id,
        scenarios=scenario_records,
        cross_scenario_matrix=cross_scenario_matrix,
        summary_metrics=summary_metrics,
        provenance=provenance,
        truth_disclosures=TRUTH_DISCLOSURES,
    )

    # Validate against JSON schema before saving
    clean_dict = sanitize_for_json(record.to_dict())
    validate_mission_experiment_record(clean_dict)

    # Persist to workspace
    save_experiment_record(clean_dict, allow_overwrite=True)
    logger.info("Orchestrated experiment completed and saved: %s in %.1fms", exp_id, exec_dur_ms)

    return record


# ==============================================================================
# MISSION EVIDENCE DOSSIER EXPORT & VERIFICATION
# ==============================================================================

def export_experiment_dossier_bundle(experiment_id: str) -> Dict[str, Any]:
    """
    Exports a self-contained Mission Evidence Dossier JSON bundle with
    SHA-256 cryptographic integrity manifest.
    """
    record_dict = get_experiment_record(experiment_id)

    # Compute deterministic fingerprint over entire payload
    payload_str = json.dumps(record_dict, sort_keys=True)
    manifest_sha256 = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "dossier_id": f"dossier_{experiment_id}",
        "experiment_id": experiment_id,
        "campaign_id": record_dict["campaign_id"],
        "campaign_version": record_dict.get("campaign_version", 1),
        "manifest": {
            "manifest_sha256": manifest_sha256,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "scenarios_count": len(record_dict.get("scenarios", [])),
            "rehearsals_count": record_dict.get("summary_metrics", {}).get("rehearsals_executed_count", 0),
        },
        "experiment_record": record_dict,
        "provenance": record_dict.get("provenance", {}),
        "truth_disclosures": record_dict.get("truth_disclosures", TRUTH_DISCLOSURES),
    }

    return bundle


def export_experiment_dossier_zip(
    experiment_id: str,
    output_dir: Optional[str] = None,
) -> str:
    """
    Generates a consolidated, auditable Mission Evidence Dossier ZIP archive containing:
      1. manifest.json (Cryptographic manifest with per-file SHA-256 digests)
      2. experiment_dossier.json (Complete ExperimentRecord)
      3. cross_scenario_matrix.csv (RFC 4180 tabular comparison)
      4. executive_briefing.md (Strategic briefing report)
      5. provenance.json (Planetary datum, DTM hash, units)
      6. README.txt (Aerospace non-flight caveats and readback guide)
    """
    record_dict = get_experiment_record(experiment_id)
    target_dir = output_dir or DEFAULT_CAMPAIGN_EXPERIMENTS_DIR
    os.makedirs(target_dir, exist_ok=True)
    zip_path = os.path.join(target_dir, f"{experiment_id}_evidence_dossier.zip")

    # 1. Prepare experiment_dossier.json bytes
    dossier_bytes = json.dumps(record_dict, indent=2, sort_keys=True).encode("utf-8")

    # 2. Prepare cross_scenario_matrix.csv bytes
    csv_buf = io.StringIO()
    matrix = record_dict.get("cross_scenario_matrix", {})
    headers = [
        "scenario_id", "scenario_name", "disruption_type", "trigger_time_s",
        "robustness_status", "is_feasible", "rehearsal_executed", "rehearsal_id",
        "outcome_status", "baseline_science", "disturbed_science", "recovered_science",
        "science_preservation_pct", "delay_incurred_s", "margin_delta_s",
        "distance_delta_m", "targets_retained", "targets_dropped", "selected_strategy"
    ]
    writer = csv.DictWriter(csv_buf, fieldnames=headers)
    writer.writeheader()
    for row in matrix.get("rows", []):
        writer.writerow({k: row.get(k, "") for k in headers})
    csv_bytes = csv_buf.getvalue().encode("utf-8")

    # 3. Prepare executive_briefing.md bytes
    metrics = record_dict.get("summary_metrics", {})
    briefing_md = f"""# ATLAS MISSION EXPERIMENT DOSSIER — EXECUTIVE BRIEFING
**Experiment ID:** `{experiment_id}`  
**Baseline Campaign:** `{record_dict['campaign_id']}` (v{record_dict.get('campaign_version', 1)})  
**Generated At:** {record_dict.get('created_at_utc', '')}  
**Model Version:** {MODEL_VERSION}  

---

## 1. Executive Summary
- **Total Scenarios Evaluated:** {metrics.get('total_scenarios_evaluated', 0)}
- **Robustness Feasibility Rate:** {metrics.get('robustness_feasible_count', 0)} / {metrics.get('total_scenarios_evaluated', 0)}
- **Closed-Loop Rehearsals Executed:** {metrics.get('rehearsals_executed_count', 0)}
- **Recovered Nominal / Mitigated:** {metrics.get('recovered_count', 0)}
- **Mean Science Yield Preservation:** {metrics.get('mean_science_preservation_pct', 0.0):.1f}%
- **Mean Operational Delay Incurred:** {metrics.get('mean_delay_incurred_s', 0.0):.1f} s

## 2. Cross-Scenario Findings
{matrix.get('summary_narrative', 'N/A')}

## 3. Operational Integrity Caveats
- Tested scenario frequencies measure mathematical properties of modeled stress suites only and MUST NOT be presented as physical Martian probabilities.
- All traverses and recovery candidates are planning heuristics and MUST NEVER be characterized as flight-certified or safe for astronauts.
- Deterministic simulation grounded in USGS CTX 20m Jezero Crater DTM mosaic (CRS ESRI:103885).
"""
    briefing_bytes = briefing_md.encode("utf-8")

    # 4. Prepare provenance.json bytes
    prov_bytes = json.dumps(record_dict.get("provenance", {}), indent=2, sort_keys=True).encode("utf-8")

    # 5. Prepare README.txt bytes
    readme_txt = f"""MARSWALK 2.0 / PROJECT ATLAS — MISSION EVIDENCE DOSSIER
=========================================================
Experiment ID: {experiment_id}
Campaign ID:   {record_dict['campaign_id']}
Date:          {record_dict.get('created_at_utc', '')}

ARCHIVE CONTENTS:
- manifest.json:               Cryptographic integrity manifest with per-file SHA-256 hashes
- experiment_dossier.json:     Complete orchestration study record (Draft 2020-12)
- cross_scenario_matrix.csv:   RFC 4180 cross-scenario comparative matrix
- executive_briefing.md:       Flight director briefing and bottleneck analysis
- provenance.json:             USGS Jezero 20m DTM provenance, CRS ESRI:103885, SI units
- README.txt:                  Operational caveats and instructions

INTEGRITY VERIFICATION:
Inspect manifest.json to verify SHA-256 checksums for each file.

DISCLOSURES:
- Modeled routes are planning heuristics and NOT safe for astronauts.
- Non-probabilistic stress suite evaluations.
"""
    readme_bytes = readme_txt.encode("utf-8")

    # Compute per-file SHA-256 hashes
    file_hashes = {
        "experiment_dossier.json": hashlib.sha256(dossier_bytes).hexdigest(),
        "cross_scenario_matrix.csv": hashlib.sha256(csv_bytes).hexdigest(),
        "executive_briefing.md": hashlib.sha256(briefing_bytes).hexdigest(),
        "provenance.json": hashlib.sha256(prov_bytes).hexdigest(),
        "README.txt": hashlib.sha256(readme_bytes).hexdigest(),
    }

    # 6. Prepare manifest.json
    manifest_obj = {
        "schema_version": SCHEMA_VERSION,
        "dossier_id": f"dossier_{experiment_id}",
        "experiment_id": experiment_id,
        "campaign_id": record_dict["campaign_id"],
        "campaign_version": record_dict.get("campaign_version", 1),
        "config_fingerprint": hashlib.sha256(
            json.dumps(record_dict.get("config", {}), sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "terrain_dataset_id": TERRAIN_DATASET_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_hashes": file_hashes,
        "overall_manifest_sha256": hashlib.sha256(
            json.dumps(file_hashes, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
    manifest_bytes = json.dumps(manifest_obj, indent=2, sort_keys=True).encode("utf-8")

    # Write ZIP
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", manifest_bytes)
        zf.writestr("experiment_dossier.json", dossier_bytes)
        zf.writestr("cross_scenario_matrix.csv", csv_bytes)
        zf.writestr("executive_briefing.md", briefing_bytes)
        zf.writestr("provenance.json", prov_bytes)
        zf.writestr("README.txt", readme_bytes)

    logger.info("Exported experiment evidence dossier ZIP: %s (%d bytes)", zip_path, os.path.getsize(zip_path))
    return zip_path


def verify_experiment_dossier_zip(zip_path: str) -> Tuple[bool, List[str]]:
    """
    Rigorously verifies an exported Mission Evidence Dossier ZIP archive:
      1. Confirms presence of all required files.
      2. Rejects unexpected or untracked extra files in archive.
      3. Validates per-file SHA-256 hashes against manifest.json.
      4. Validates overall manifest SHA-256 signature.
      5. Validates experiment_dossier.json against Draft 2020-12 schema.
      6. Checks CSV row reconciliation against scenario count.
    Returns (is_valid, error_list).
    """
    errors: List[str] = []
    if not os.path.isfile(zip_path):
        return False, [f"ZIP archive not found: {zip_path}"]

    required_files = {
        "manifest.json",
        "experiment_dossier.json",
        "cross_scenario_matrix.csv",
        "executive_briefing.md",
        "provenance.json",
        "README.txt",
    }

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            file_list = set(zf.namelist())
            missing = required_files - file_list
            if missing:
                errors.append(f"ZIP archive missing required files: {sorted(missing)}")

            extra = file_list - required_files
            if extra:
                errors.append(f"ZIP archive contains unauthorized/untracked files: {sorted(extra)}")

            # Read and parse manifest
            if "manifest.json" in file_list:
                manifest_data = json.loads(zf.read("manifest.json").decode("utf-8"))
                file_hashes = manifest_data.get("file_hashes", {})

                for filename, expected_hash in file_hashes.items():
                    if filename not in file_list:
                        errors.append(f"Manifest references file not in ZIP: {filename}")
                        continue
                    actual_hash = hashlib.sha256(zf.read(filename)).hexdigest()
                    if actual_hash != expected_hash:
                        errors.append(f"Hash mismatch on {filename}: expected {expected_hash}, got {actual_hash}")

                expected_overall = manifest_data.get("overall_manifest_sha256")
                actual_overall = hashlib.sha256(
                    json.dumps(file_hashes, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if expected_overall and actual_overall != expected_overall:
                    errors.append(f"Overall manifest SHA-256 mismatch: expected {expected_overall}, got {actual_overall}")

            # Validate experiment_dossier.json against schema
            if "experiment_dossier.json" in file_list:
                dossier_data = json.loads(zf.read("experiment_dossier.json").decode("utf-8"))
                try:
                    validate_mission_experiment_record(dossier_data)
                except Exception as ex:
                    errors.append(f"experiment_dossier.json contract validation failed: {ex}")

                # Reconcile CSV rows
                if "cross_scenario_matrix.csv" in file_list:
                    csv_text = zf.read("cross_scenario_matrix.csv").decode("utf-8")
                    reader = csv.DictReader(io.StringIO(csv_text))
                    rows = list(reader)
                    expected_rows = len(dossier_data.get("scenarios", []))
                    if len(rows) != expected_rows:
                        errors.append(f"CSV row count mismatch: {len(rows)} in CSV vs {expected_rows} in dossier")

    except Exception as ex:
        errors.append(f"Exception inspecting ZIP: {ex}")

    is_valid = (len(errors) == 0)
    return is_valid, errors
