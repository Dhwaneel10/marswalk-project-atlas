"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Intent Validation & Normalization
==============================================================================
Validates incoming goal-driven mission intent specifications against physical
boundaries, remote-sensing terrain dimensions, authoritative instrument catalogs,
and fleet capabilities before hierarchical compilation.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.mission_intent import MissionIntent, ScienceObjectiveCategory
from marswalk.core.science_mission_planner import INSTRUMENT_CATALOG
from marswalk.core.fleet_task_allocator import get_default_jezero_targets
from marswalk.core.fleet_operations_director import create_default_fleet_rovers


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationVerdict(str, Enum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"
    UNDER_SPECIFIED = "UNDER_SPECIFIED"


@dataclass
class IntentValidationIssue:
    """Specific diagnostic issue discovered during intent verification."""
    issue_code: str
    severity: str
    message: str
    affected_field: str
    suggested_resolution: str
    assumption_applied: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_code": self.issue_code,
            "severity": self.severity,
            "message": self.message,
            "affected_field": self.affected_field,
            "suggested_resolution": self.suggested_resolution,
            "assumption_applied": self.assumption_applied,
        }


@dataclass
class IntentValidationReport:
    """Consolidated validation verdict, issues, and normalized intent specification."""
    verdict: str
    total_errors: int
    total_warnings: int
    total_infos: int
    issues: List[IntentValidationIssue] = field(default_factory=list)
    normalized_intent: Optional[Dict[str, Any]] = None
    evaluated_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_infos": self.total_infos,
            "issues": [i.to_dict() for i in self.issues],
            "normalized_intent": self.normalized_intent,
            "evaluated_at_utc": self.evaluated_at_utc,
        }


class MissionIntentValidator:
    """
    Validates and normalizes goal-driven mission intent specifications.
    Enforces scientific integrity: catches impossible or contradictory requests
    before expensive solver search trees are initiated.
    """

    def __init__(self, terrain_shape: Tuple[int, int] = (250, 250)):
        self.terrain_height, self.terrain_width = terrain_shape
        self.default_targets = {t.target_id: t for t in get_default_jezero_targets()}
        self.default_rovers = {r.rover_id: r for r in create_default_fleet_rovers()}

    def validate_intent(self, intent: MissionIntent) -> IntentValidationReport:
        issues: List[IntentValidationIssue] = []

        # 1. Validate Science Objectives & Instruments
        self._validate_science_intent(intent, issues)

        # 2. Validate Fleet Composition & Capabilities
        self._validate_fleet_intent(intent, issues)

        # 3. Validate Geographic & Spatial Boundaries
        self._validate_geography_intent(intent, issues)

        # 4. Validate Temporal Bounds
        self._validate_temporal_intent(intent, issues)

        # 5. Validate Communications & Relay Parameters
        self._validate_communications_intent(intent, issues)

        # 6. Validate Energy & Storage Constraints
        self._validate_resource_limits_intent(intent, issues)

        # 7. Check for Contradictory Objectives
        self._validate_cross_intent_consistency(intent, issues)

        # Aggregate Verdict
        errors_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR.value)
        warnings_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING.value)
        infos_count = sum(1 for i in issues if i.severity == ValidationSeverity.INFO.value)

        if errors_count > 0:
            verdict = ValidationVerdict.INVALID.value
        elif any(i.issue_code.startswith("MISSING_REQUIRED_") for i in issues):
            verdict = ValidationVerdict.UNDER_SPECIFIED.value
        elif warnings_count > 0:
            verdict = ValidationVerdict.VALID_WITH_WARNINGS.value
        else:
            verdict = ValidationVerdict.VALID.value

        normalized = intent.to_dict() if errors_count == 0 else None

        return IntentValidationReport(
            verdict=verdict,
            total_errors=errors_count,
            total_warnings=warnings_count,
            total_infos=infos_count,
            issues=issues,
            normalized_intent=normalized,
        )

    def _validate_science_intent(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        sci = intent.science

        # Check required instruments against authoritative INSTRUMENT_CATALOG
        known_instruments = {profile.instrument_id.value for profile in INSTRUMENT_CATALOG.values()}
        for inst_id in sci.required_instruments:
            if inst_id not in known_instruments and inst_id not in INSTRUMENT_CATALOG:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNKNOWN_INSTRUMENT",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Required instrument '{inst_id}' does not exist in authoritative catalog.",
                    affected_field="science.required_instruments",
                    suggested_resolution=f"Select from available instruments: {sorted(list(known_instruments))}",
                ))

        # Check if mandatory targets exist in the Jezero catalog
        for tgt_id in sci.mandatory_target_ids:
            if tgt_id not in self.default_targets:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_TARGET_NOT_FOUND",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Mandatory target '{tgt_id}' not found in Jezero target registry.",
                    affected_field="science.mandatory_target_ids",
                    suggested_resolution=f"Select from calibrated targets: {list(self.default_targets.keys())}",
                ))

        # Check observation count limits
        if sci.minimum_observations_count <= 0:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_OBSERVATION_COUNT",
                severity=ValidationSeverity.ERROR.value,
                message="Minimum observation count must be at least 1.",
                affected_field="science.minimum_observations_count",
                suggested_resolution="Specify minimum_observations_count >= 1.",
            ))
        elif sci.minimum_observations_count > sci.maximum_targets_limit:
            issues.append(IntentValidationIssue(
                issue_code="ERR_OBSERVATION_COUNT_EXCEEDS_LIMIT",
                severity=ValidationSeverity.ERROR.value,
                message=(
                    f"Minimum observations ({sci.minimum_observations_count}) cannot exceed "
                    f"maximum targets limit ({sci.maximum_targets_limit})."
                ),
                affected_field="science.minimum_observations_count",
                suggested_resolution="Increase maximum_targets_limit or reduce minimum_observations_count.",
            ))

        OBJECTIVE_SYNONYMS = {
            "GEOLOGIC_MAPPING": ["GEOLOGICAL_CHARACTERIZATION", "SURFACE_MORPHOLOGY"],
            "MINERALOGIC_SPECTROSCOPY": ["MINERALOGICAL_INVESTIGATION"],
            "ELEMENTAL_CHEMISTRY": ["MINERALOGICAL_INVESTIGATION", "GEOLOGICAL_CHARACTERIZATION"],
            "ORGANIC_SPECTROSCOPY": ["ASTROBIOLOGY_BIOSIGNATURE_SURVEY", "MINERALOGICAL_INVESTIGATION"],
            "SUBSURFACE_STRATIGRAPHY": ["GEOLOGICAL_CHARACTERIZATION", "SURFACE_MORPHOLOGY"],
            "ATMOSPHERIC_METEOROLOGY": ["ATMOSPHERIC_OBSERVATION", "ENVIRONMENTAL_MONITORING"],
            "SAMPLE_EXTRACTION": ["GEOLOGICAL_CHARACTERIZATION", "ASTROBIOLOGY_BIOSIGNATURE_SURVEY"],
            "GEOLOGICAL_CHARACTERIZATION": ["GEOLOGICAL_CHARACTERIZATION"],
            "MINERALOGICAL_INVESTIGATION": ["MINERALOGICAL_INVESTIGATION"],
            "SURFACE_MORPHOLOGY": ["SURFACE_MORPHOLOGY"],
            "ATMOSPHERIC_OBSERVATION": ["ATMOSPHERIC_OBSERVATION"],
            "ENVIRONMENTAL_MONITORING": ["ENVIRONMENTAL_MONITORING"],
            "ASTROBIOLOGY_BIOSIGNATURE_SURVEY": ["ASTROBIOLOGY_BIOSIGNATURE_SURVEY"],
        }

        # Check if requested objectives have any matching instrument in catalog
        for obj in sci.primary_objectives:
            synonyms = OBJECTIVE_SYNONYMS.get(obj, [obj])
            matching = [
                i_id for i_id, i_spec in INSTRUMENT_CATALOG.items()
                if any(any(s == comp_obj.value or s in comp_obj.value or comp_obj.value in s for s in synonyms) for comp_obj in i_spec.compatible_objectives)
            ]
            if not matching:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNSUPPORTED_SCIENCE_OBJECTIVE",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Science objective '{obj}' is not supported by any instrument in catalog.",
                    affected_field="science.primary_objectives",
                    suggested_resolution="Select from supported objective categories.",
                ))

    def _validate_fleet_intent(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        flt = intent.fleet

        if flt.maximum_rovers <= 0 or flt.maximum_rovers > 4:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_FLEET_SIZE",
                severity=ValidationSeverity.ERROR.value,
                message=f"Maximum rovers must be between 1 and 4 (provided: {flt.maximum_rovers}).",
                affected_field="fleet.maximum_rovers",
                suggested_resolution="Set fleet.maximum_rovers to an integer in [1, 4].",
            ))

        if flt.minimum_rovers > flt.maximum_rovers:
            issues.append(IntentValidationIssue(
                issue_code="ERR_CONTRADICTORY_FLEET_BOUNDS",
                severity=ValidationSeverity.ERROR.value,
                message=(
                    f"Minimum rovers ({flt.minimum_rovers}) exceeds "
                    f"maximum rovers ({flt.maximum_rovers})."
                ),
                affected_field="fleet.minimum_rovers",
                suggested_resolution="Ensure minimum_rovers <= maximum_rovers.",
            ))

        # Check permitted rovers against catalog
        for r_id in flt.permitted_rover_ids:
            if r_id not in self.default_rovers:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNKNOWN_ROVER_ID",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Permitted rover '{r_id}' is not a registered exploration unit.",
                    affected_field="fleet.permitted_rover_ids",
                    suggested_resolution=f"Select from available units: {list(self.default_rovers.keys())}",
                ))

        if not flt.permitted_rover_ids:
            issues.append(IntentValidationIssue(
                issue_code="ERR_EMPTY_FLEET_PERMITTED",
                severity=ValidationSeverity.ERROR.value,
                message="At least one rover unit must be specified in permitted_rover_ids.",
                affected_field="fleet.permitted_rover_ids",
                suggested_resolution="Add at least one rover (e.g. ATLAS_ROVER_A).",
            ))

    def _validate_geography_intent(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        geo = intent.geography

        # Bounds check on starting and base station coordinates
        sr, sc = geo.starting_location_rc
        if not (0 <= sr < self.terrain_height and 0 <= sc < self.terrain_width):
            issues.append(IntentValidationIssue(
                issue_code="ERR_OUT_OF_BOUNDS_START_COORDINATES",
                severity=ValidationSeverity.ERROR.value,
                message=(
                    f"Starting location [{sr}, {sc}] is out of bounds for the "
                    f"{self.terrain_height}x{self.terrain_width} Jezero DTM."
                ),
                affected_field="geography.starting_location_rc",
                suggested_resolution=f"Set coordinates in range [0..{self.terrain_height-1}, 0..{self.terrain_width-1}].",
            ))

        br, bc = geo.base_station_rc
        if not (0 <= br < self.terrain_height and 0 <= bc < self.terrain_width):
            issues.append(IntentValidationIssue(
                issue_code="ERR_OUT_OF_BOUNDS_BASE_COORDINATES",
                severity=ValidationSeverity.ERROR.value,
                message=f"Base station location [{br}, {bc}] is out of DTM bounds.",
                affected_field="geography.base_station_rc",
                suggested_resolution="Ensure base station coordinates fall within surveyed DTM boundary.",
            ))

        # Slope limits
        if geo.maximum_slope_limit_deg <= 0.0 or geo.maximum_slope_limit_deg > 35.0:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_SLOPE_LIMIT",
                severity=ValidationSeverity.ERROR.value,
                message=f"Maximum slope limit {geo.maximum_slope_limit_deg} deg is physically unrealistic for rovers.",
                affected_field="geography.maximum_slope_limit_deg",
                suggested_resolution="Specify maximum_slope_limit_deg in range (0.0, 30.0].",
            ))
        elif geo.maximum_slope_limit_deg > 25.0:
            issues.append(IntentValidationIssue(
                issue_code="WARN_ELEVATED_SLOPE_RISK",
                severity=ValidationSeverity.WARNING.value,
                message=f"Slope ceiling of {geo.maximum_slope_limit_deg} deg exceeds the nominal 25 deg rover safety margin.",
                affected_field="geography.maximum_slope_limit_deg",
                suggested_resolution="Recommend setting slope ceiling to 25.0 deg to prevent wheel slip hazard.",
            ))

    def _validate_temporal_intent(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        tim = intent.timeline

        if tim.maximum_sols <= 0 or tim.maximum_sols > 10:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_MISSION_DURATION",
                severity=ValidationSeverity.ERROR.value,
                message=f"Maximum sols ({tim.maximum_sols}) must be in range [1, 10].",
                affected_field="timeline.maximum_sols",
                suggested_resolution="Set timeline.maximum_sols between 1 and 10 sols.",
            ))

        if tim.sol_driving_start_hour_ltst < 0.0 or tim.sol_driving_end_hour_ltst > 24.66:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_DRIVING_HOURS",
                severity=ValidationSeverity.ERROR.value,
                message="Driving window hours must fall within Martian sol diurnal cycle (0.0 to 24.66 LTST).",
                affected_field="timeline.sol_driving_start_hour_ltst",
                suggested_resolution="Set driving hours between 06:00 and 18:00 LTST.",
            ))

        if tim.sol_driving_start_hour_ltst >= tim.sol_driving_end_hour_ltst:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVERTED_DRIVING_WINDOW",
                severity=ValidationSeverity.ERROR.value,
                message="Driving start hour must precede driving end hour.",
                affected_field="timeline.sol_driving_start_hour_ltst",
                suggested_resolution="Ensure start_hour < end_hour.",
            ))

    def _validate_communications_intent(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        com = intent.communications

        if com.maximum_relays_deployable < 0 or com.maximum_relays_deployable > 4:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_RELAY_BUDGET",
                severity=ValidationSeverity.ERROR.value,
                message=f"Relays deployable ({com.maximum_relays_deployable}) must be in range [0, 4].",
                affected_field="communications.maximum_relays_deployable",
                suggested_resolution="Set communications.maximum_relays_deployable to an integer in [0, 4].",
            ))

        if not (0.0 <= com.minimum_geometric_reachability_pct <= 100.0):
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_REACHABILITY_PCT",
                severity=ValidationSeverity.ERROR.value,
                message="Geometric reachability percentage must be between 0.0% and 100.0%.",
                affected_field="communications.minimum_geometric_reachability_pct",
                suggested_resolution="Specify reachability in range [50.0, 100.0].",
            ))

    def _validate_resource_limits_intent(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        res = intent.resources

        if res.minimum_battery_reserve_pct < 0.0 or res.minimum_battery_reserve_pct >= 100.0:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_BATTERY_RESERVE",
                severity=ValidationSeverity.ERROR.value,
                message=f"Battery reserve margin ({res.minimum_battery_reserve_pct}%) must be in range [0.0, 99.0).",
                affected_field="resources.minimum_battery_reserve_pct",
                suggested_resolution="Set minimum_battery_reserve_pct to a safe margin (e.g. 20.0%).",
            ))
        elif res.minimum_battery_reserve_pct < 10.0:
            issues.append(IntentValidationIssue(
                issue_code="WARN_CRITICAL_LOW_ENERGY_BUFFER",
                severity=ValidationSeverity.WARNING.value,
                message="Battery reserve margin < 10% risks vehicle loss during diurnal thermal drops.",
                affected_field="resources.minimum_battery_reserve_pct",
                suggested_resolution="Recommend minimum reserve margin >= 20.0%.",
            ))

        if res.maximum_flash_storage_utilization_pct <= 0.0 or res.maximum_flash_storage_utilization_pct > 100.0:
            issues.append(IntentValidationIssue(
                issue_code="ERR_INVALID_STORAGE_UTILIZATION",
                severity=ValidationSeverity.ERROR.value,
                message="Storage utilization ceiling must be in range (0.0, 100.0].",
                affected_field="resources.maximum_flash_storage_utilization_pct",
                suggested_resolution="Set storage ceiling between 70.0% and 95.0%.",
            ))

    def _validate_cross_intent_consistency(self, intent: MissionIntent, issues: List[IntentValidationIssue]):
        """Catches contradictory or physically unsatisfiable multi-subsystem combinations."""
        flt = intent.fleet
        sci = intent.science

        # Check if permitted rovers collectively carry all required instruments
        if sci.required_instruments and flt.permitted_rover_ids:
            available_instruments: Set[str] = set()
            for r_id in flt.permitted_rover_ids:
                if r_id in self.default_rovers:
                    available_instruments.update(self.default_rovers[r_id].instrument_ids)

            for req_inst in sci.required_instruments:
                if req_inst not in available_instruments:
                    issues.append(IntentValidationIssue(
                        issue_code="ERR_REQUIRED_INSTRUMENT_UNAVAILABLE_ON_FLEET",
                        severity=ValidationSeverity.ERROR.value,
                        message=(
                            f"Required instrument '{req_inst}' is not carried by any permitted rover "
                            f"in {flt.permitted_rover_ids}."
                        ),
                        affected_field="science.required_instruments",
                        suggested_resolution=(
                            f"Include a rover carrying '{req_inst}' (e.g. "
                            f"{[r_id for r_id, r in self.default_rovers.items() if req_inst in r.instrument_ids]}) "
                            f"or remove '{req_inst}' from required_instruments."
                        ),
                    ))

        # Check if mandatory targets are compatible with permitted rovers
        for tgt_id in sci.mandatory_target_ids:
            if tgt_id in self.default_targets:
                tgt = self.default_targets[tgt_id]
                can_observe = False
                for r_id in flt.permitted_rover_ids:
                    if r_id in self.default_rovers:
                        r_cfg = self.default_rovers[r_id]
                        # Check if rover has any instrument mode compatible with target objective
                        for mode_key, profile in INSTRUMENT_CATALOG.items():
                            if profile.instrument_id.value in r_cfg.instrument_ids:
                                for comp_obj in profile.compatible_objectives:
                                    if comp_obj.value == tgt.objective or tgt.objective in comp_obj.value or comp_obj.value in tgt.objective:
                                        can_observe = True
                                        break
                            if can_observe:
                                break
                    if can_observe:
                        break

                if not can_observe:
                    issues.append(IntentValidationIssue(
                        issue_code="ERR_MANDATORY_TARGET_INCOMPATIBLE_WITH_FLEET",
                        severity=ValidationSeverity.ERROR.value,
                        message=(
                            f"Mandatory target '{tgt_id}' (objective: {tgt.objective}) cannot be observed "
                            f"by any permitted rover in {flt.permitted_rover_ids}."
                        ),
                        affected_field="science.mandatory_target_ids",
                        suggested_resolution=f"Permit rovers equipped for {tgt.objective} or defer {tgt_id}.",
                    ))
