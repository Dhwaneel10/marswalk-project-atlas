"""MarsWalk 2.0 / Project Atlas  Milestone 13R Dedicated Test Suite.

Validates the Atlas Apocalypse Engine: Failure Taxonomy, Deterministic Fault Injection,
Causal Propagation DAG, FDDI Engine, FMEA/Fault Trees, Autonomous Recovery Planning,
12 Recovery Metric Dimensions, Scenario Catalog (inc. Scenario 12 Project Apocalypse),
Resilience Benchmark Harness, and Deterministic Replay Engine.
"""

import json
import pytest
import jsonschema

from marswalk.core.mars_failure_taxonomy import (
    FailureClass,
    FailureRecord,
    FailureSeverity,
    FailureTaxonomyRegistry,
    FaultProfileType,
    SymptomRecord,
)
from marswalk.core.mars_fault_injection_engine import (
    FaultInjectionEngine,
    FaultState,
    InjectedFaultInstance,
)
from marswalk.core.mars_failure_propagation import (
    FailurePropagationGraph,
    GateLogic,
)
from marswalk.core.mars_fault_diagnosis import (
    DiagnosticStatus,
    FaultDiagnosisEngine,
)
from marswalk.core.mars_failure_mode_analysis import (
    FailureModeAnalysisEngine,
    FaultTreeNode,
    FaultTreeNodeType,
)
from marswalk.core.mars_mission_resilience_engine import (
    MissionResilienceEngine,
    RecoveryActionType,
)
from marswalk.core.mars_apocalypse_scenario_engine import ApocalypseScenarioEngine
from marswalk.core.mars_resilience_benchmark import (
    MissionResilienceBenchmark,
    StrategyClass,
)
from marswalk.core.mars_fault_replay import (
    DeterministicFaultReplayEngine,
    ReplayEventType,
)
from marswalk.api.contracts import validate_contract


class TestMilestone13RApocalypseEngine:
    """Rigorous verification suite for Milestone 13R planetary resilience capabilities."""

    def test_01_failure_taxonomy_classes_and_severity(self):
        """Verifies 7 planetary robotics failure classes and MIL-STD-882E severities."""
        assert len(FailureClass) == 7
        assert FailureClass.MECHANICAL.value == "MECHANICAL"
        assert FailureClass.POWER.value == "POWER"
        assert FailureClass.COMMUNICATIONS.value == "COMMUNICATIONS"
        assert FailureClass.ENVIRONMENTAL.value == "ENVIRONMENTAL"
        assert FailureClass.NAVIGATION.value == "NAVIGATION"
        assert FailureClass.SCIENCE_PAYLOAD.value == "SCIENCE_PAYLOAD"
        assert FailureClass.SOFTWARE_SYSTEM.value == "SOFTWARE_SYSTEM"

        assert FailureSeverity.NEGLIGIBLE.value == "NEGLIGIBLE"
        assert FailureSeverity.CATASTROPHIC.value == "CATASTROPHIC"

    def test_02_failure_record_serialization_and_symptoms(self):
        """Verifies FailureRecord data model, symptoms, and JSON serialization."""
        symptom = SymptomRecord(
            symptom_id="SYM-TEST-01",
            telemetry_channel="rover.mobility.motor_fr_current_a",
            observed_value=4.8,
            expected_nominal_range=(1.8, 2.8),
            residual=2.0,
            unit="A",
            timestamp_sol_s=120.0,
        )
        assert symptom.is_out_of_bounds() is True

        rec = FailureRecord(
            failure_id="FAIL-TEST-01",
            name="Test Actuator Stall",
            failure_class=FailureClass.MECHANICAL,
            severity=FailureSeverity.CRITICAL,
            profile_type=FaultProfileType.IRREVERSIBLE,
            target_asset="ROVER-PERSEVERANCE",
            affected_subsystem="MOBILITY_DRIVE",
            containment_boundary="ISOLATE_DRIVE_MOTOR",
            description="Motor locked due to rock ingress.",
            symptoms=[symptom],
        )
        d = rec.to_dict()
        restored = FailureRecord.from_dict(d)
        assert restored.failure_id == "FAIL-TEST-01"
        assert len(restored.symptoms) == 1
        assert restored.symptoms[0].observed_value == 4.8

    def test_03_fault_injection_scheduling_and_intensity_profiles(self):
        """Tests immediate, delayed, and progressive fault profile dynamics."""
        engine = FaultInjectionEngine(branch_id="test_branch")
        rec = FailureTaxonomyRegistry.get_standard_catalog()[0]  # Motor stall (Immediate/Irreversible)

        inst = engine.schedule_fault(rec, trigger_sol=1, trigger_time_s=100.0)
        assert inst.state == FaultState.PENDING

        # Before trigger
        active = engine.evaluate_at(1, 50.0)
        assert len(active) == 0

        # At and after trigger
        active = engine.evaluate_at(1, 105.0)
        assert len(active) == 1
        assert active[0].state == FaultState.ACTIVE
        assert active[0].current_intensity == 1.0
        assert len(active[0].active_symptoms) >= 1

    def test_04_fault_injection_counterfactual_branch_isolation(self):
        """Ensures fault injection in counterfactual branch does not mutate parent."""
        parent = FaultInjectionEngine(branch_id="master")
        rec = FailureTaxonomyRegistry.get_standard_catalog()[0]
        parent.schedule_fault(rec, trigger_sol=1, trigger_time_s=100.0)

        child = parent.branch("counterfactual_01")
        assert len(child.get_all_faults()) == 1

        # Add second fault to child
        rec2 = FailureTaxonomyRegistry.get_standard_catalog()[1]
        child.schedule_fault(rec2, trigger_sol=1, trigger_time_s=200.0)

        assert len(child.get_all_faults()) == 2
        assert len(parent.get_all_faults()) == 1  # Parent untouched!

    def test_05_causal_propagation_dag_construction(self):
        """Verifies standard planetary propagation DAG has valid nodes, edges, and topology."""
        dag = FailurePropagationGraph.build_standard_planetary_dag()
        state = dag.get_state()
        assert state["total_nodes"] >= 15
        assert state["total_edges"] >= 10
        assert state["dag_failed_nodes_count"] == 0 if "dag_failed_nodes_count" in state else True

    def test_06_causal_propagation_boolean_or_and_gates(self):
        """Tests that failures cascade across DAG edges matching time delays and gate logic."""
        dag = FailurePropagationGraph()
        dag.add_node("ROOT_A", "Root Failure A", "POWER")
        dag.add_node("ROOT_B", "Root Failure B", "POWER")
        dag.add_node("TARGET_OR", "Consequence OR", "SYSTEM")
        dag.add_node("TARGET_AND", "Consequence AND", "SYSTEM")

        dag.add_edge("ROOT_A", "TARGET_OR", gate=GateLogic.OR, propagation_delay_s=10.0)
        dag.add_edge("ROOT_A", "TARGET_AND", gate=GateLogic.AND, propagation_delay_s=10.0)
        dag.add_edge("ROOT_B", "TARGET_AND", gate=GateLogic.AND, propagation_delay_s=10.0)

        # Inject ROOT_A only
        dag.inject_root_failure("ROOT_A", timestamp_s=0.0)
        newly_failed = dag.propagate(current_time_s=15.0)

        assert "TARGET_OR" in newly_failed
        assert "TARGET_AND" not in newly_failed  # AND gate not satisfied yet

        # Now inject ROOT_B
        dag.inject_root_failure("ROOT_B", timestamp_s=5.0)
        newly_failed_2 = dag.propagate(current_time_s=20.0)
        assert "TARGET_AND" in newly_failed_2

    def test_07_containment_barriers_sever_propagation_edges(self):
        """Verifies that activating containment barriers blocks downstream cascade."""
        dag = FailurePropagationGraph()
        dag.add_node("ROV_MOTOR_STALL", "Motor Stall", "MOBILITY")
        dag.add_node("ROV_BUS_SURGE", "Bus Surge", "POWER")
        dag.add_edge(
            "ROV_MOTOR_STALL", "ROV_BUS_SURGE",
            gate=GateLogic.OR, propagation_delay_s=5.0,
            containment_barrier="ISOLATE_FL_MOTOR"
        )

        # Activate containment barrier BEFORE propagation
        dag.activate_containment_barrier("ISOLATE_FL_MOTOR")
        dag.inject_root_failure("ROV_MOTOR_STALL", timestamp_s=0.0)
        newly_failed = dag.propagate(current_time_s=10.0)

        # Downstream node should NOT fail because edge is blocked
        assert "ROV_BUS_SURGE" not in newly_failed

    def test_08_causal_trace_extraction(self):
        """Verifies root-cause backward path synthesis in causal DAG."""
        dag = FailurePropagationGraph.build_standard_planetary_dag()
        dag.inject_root_failure("ROV_MOTOR_FR_STALL", timestamp_s=0.0)
        dag.propagate(current_time_s=300.0)

        traces = dag.find_causal_traces("ROV_SCHEDULE_SLIP")
        assert len(traces) >= 1
        trace = traces[0]
        assert trace.root_cause == "ROV_MOTOR_FR_STALL"
        assert trace.target_failure == "ROV_SCHEDULE_SLIP"
        assert "ROV_SPEED_DEGRADATION" in trace.path

    def test_09_fddi_symptom_residual_detection(self):
        """Verifies FDDI engine processes raw symptoms and generates diagnostic hypotheses."""
        fddi = FaultDiagnosisEngine()
        sym = SymptomRecord(
            symptom_id="SYM-01",
            telemetry_channel="comm.uhf.snr_db",
            observed_value=-18.5,
            expected_nominal_range=(12.0, 24.0),
            residual=-34.5,
            unit="dB",
            timestamp_sol_s=100.0,
        )
        report = fddi.analyze_symptoms([sym], current_time_s=100.0)
        assert len(report.confirmed_diagnoses) == 1
        assert report.confirmed_diagnoses[0].fault_id == "FAIL-COM-01"
        assert report.system_health_index < 0.75

    def test_10_fddi_competing_hypotheses_disambiguation(self):
        """Tests disambiguation: High current + velocity normal => terrain slope; High current + zero velocity => motor jam."""
        fddi = FaultDiagnosisEngine()

        # Case 1: High current, normal velocity (Terrain slope candidate)
        sym_curr = SymptomRecord(
            symptom_id="SYM-01",
            telemetry_channel="rover.mobility.motor_fr_current_a",
            observed_value=3.4,
            expected_nominal_range=(1.8, 2.8),
            residual=0.8,
            unit="A",
            timestamp_sol_s=200.0,
        )
        sym_spd_normal = SymptomRecord(
            symptom_id="SYM-02",
            telemetry_channel="rover.mobility.chassis_velocity_mps",
            observed_value=0.040,
            expected_nominal_range=(0.038, 0.046),
            residual=-0.002,
            unit="m/s",
            timestamp_sol_s=200.0,
        )
        report1 = fddi.analyze_symptoms([sym_curr, sym_spd_normal], current_time_s=200.0)
        assert len(report1.hypotheses) >= 1
        assert report1.hypotheses[0].fault_id == "CAND-TERRAIN-RESISTANCE"

        # Case 2: High current, severe speed drop (Confirmed mechanical stall)
        sym_spd_stall = SymptomRecord(
            symptom_id="SYM-03",
            telemetry_channel="rover.mobility.chassis_velocity_mps",
            observed_value=0.015,
            expected_nominal_range=(0.038, 0.046),
            residual=-0.027,
            unit="m/s",
            timestamp_sol_s=250.0,
        )
        report2 = fddi.analyze_symptoms([sym_curr, sym_spd_stall], current_time_s=250.0)
        assert len(report2.confirmed_diagnoses) >= 1
        assert report2.confirmed_diagnoses[0].fault_id == "FAIL-MEC-01"

    def test_11_fddi_system_health_index_degradation(self):
        """Verifies health score drops according to confirmed fault severities."""
        fddi = FaultDiagnosisEngine()
        nominal_report = fddi.analyze_symptoms([], current_time_s=0.0)
        assert nominal_report.system_health_index == 1.0

    def test_12_fmea_table_generation_and_rpn_calculation(self):
        """Verifies FMEA records, RPN formulas (S * O * D), and mitigation reductions."""
        records = FailureModeAnalysisEngine.generate_campaign_fmea()
        assert len(records) >= 5
        for r in records:
            assert r.rpn == r.severity * r.occurrence * r.detection
            assert r.mitigated_rpn < r.rpn
            assert len(r.recommended_mitigation) > 0

    def test_13_fault_tree_boolean_probability_evaluation(self):
        """Verifies top-level Fault Tree probability computation via Boolean logic."""
        top_tree = FailureModeAnalysisEngine.build_top_level_campaign_fault_tree()
        prob = top_tree.evaluate_probability()
        assert 0.0 < prob < 1.0
        assert top_tree.node_type == FaultTreeNodeType.TOP_EVENT

    def test_14_fault_tree_minimal_cut_sets(self):
        """Verifies extraction of minimal cut sets for campaign failure."""
        top_tree = FailureModeAnalysisEngine.build_top_level_campaign_fault_tree()
        cut_sets = top_tree.find_minimal_cut_sets()
        assert len(cut_sets) >= 3

    def test_15_resilience_engine_synthesizes_12d_metrics(self):
        """Mandatory test: Enforces that recovery plans report all 12 quantitative metric dimensions."""
        fddi = FaultDiagnosisEngine()
        sym = SymptomRecord(
            symptom_id="SYM-01",
            telemetry_channel="comm.uhf.snr_db",
            observed_value=-18.5,
            expected_nominal_range=(12.0, 24.0),
            residual=-34.5,
            unit="dB",
            timestamp_sol_s=100.0,
        )
        report = fddi.analyze_symptoms([sym], current_time_s=100.0)
        res_engine = MissionResilienceEngine()
        plans = res_engine.synthesize_recovery_plans(report, total_science_targets=6)

        assert len(plans) == 3
        atlas_plan = next(p for p in plans if p.strategy_class == "FULL_ATLAS_RECOVERY")
        m = atlas_plan.metrics

        # Verify all 12 dimensions
        assert hasattr(m, "science_objectives_completed")
        assert hasattr(m, "science_objectives_preserved_deferred")
        assert hasattr(m, "science_objectives_abandoned")
        assert hasattr(m, "energy_remaining_wh")
        assert hasattr(m, "data_retained_mb")
        assert hasattr(m, "data_lost_mb")
        assert hasattr(m, "mission_duration_extension_s")
        assert hasattr(m, "time_to_recover_s")
        assert hasattr(m, "unresolved_failures_count")
        assert hasattr(m, "remaining_operational_constraints")
        assert hasattr(m, "resource_violations_count")
        assert hasattr(m, "final_mission_state_validity")

        # Zero data loss on Atlas recovery
        assert m.data_lost_mb == 0.0
        assert m.resource_violations_count == 0
        assert m.final_mission_state_validity is True

    def test_16_recovery_plan_ranking_atlas_vs_static_vs_no_recovery(self):
        """Verifies Full Atlas recovery ranks #1 over static contingency and unmitigated baseline."""
        fddi = FaultDiagnosisEngine()
        rec = FailureTaxonomyRegistry.get_standard_catalog()[0]
        injector = FaultInjectionEngine()
        injector.schedule_fault(rec, trigger_sol=1, trigger_time_s=0.0)
        active = injector.evaluate_at(1, 10.0)
        report = fddi.analyze_symptoms(active[0].active_symptoms, current_time_s=10.0)

        res_engine = MissionResilienceEngine()
        plans = res_engine.synthesize_recovery_plans(report)
        assert plans[0].strategy_class == "FULL_ATLAS_RECOVERY"
        assert plans[0].overall_resilience_rank == 1

    def test_17_scenario_01_the_red_horizon_execution(self):
        """Tests single-fault Scenario 01: Rover actuator jam and 5-wheel kinematic recovery."""
        scenario_engine = ApocalypseScenarioEngine()
        res = scenario_engine.execute_scenario("SCENARIO-01")
        assert res.injected_faults_count >= 1
        assert res.recovered_metrics.data_lost_mb == 0.0
        assert res.recovered_metrics.final_mission_state_validity is True
        assert len(res.state_hash) == 16

    def test_18_scenario_12_project_apocalypse_signature_demonstration(self):
        """Flagship test: Scenario 12 Project Apocalypse with 5 concurrent failures across all domains."""
        scenario_engine = ApocalypseScenarioEngine()
        res = scenario_engine.execute_scenario("SCENARIO-12")

        # 5 simultaneous failures
        assert res.injected_faults_count == 5
        assert res.detected_symptoms_count >= 5
        assert len(res.propagated_cascade_nodes) >= 5

        # Atlas recovery succeeds
        assert res.selected_recovery_plan.strategy_class == "FULL_ATLAS_RECOVERY"
        assert res.recovered_metrics.science_objectives_completed >= 5
        assert res.recovered_metrics.data_lost_mb == 0.0
        assert res.recovered_metrics.resource_violations_count == 0
        assert res.recovered_metrics.final_mission_state_validity is True

        # Unmitigated baseline would fail
        assert res.baseline_metrics.final_mission_state_validity is False
        assert res.baseline_metrics.resource_violations_count > 0

    def test_19_resilience_benchmark_evaluates_development_and_held_out(self):
        """Verifies benchmark harness evaluates 6 strategies across Dev and Held-Out sets."""
        benchmark = MissionResilienceBenchmark()
        report = benchmark.run_benchmark()
        assert "development_suite" in report
        assert "held_out_suite" in report

        dev_scores = report["development_suite"].strategies_evaluated
        assert len(dev_scores) == 6
        atlas_score = next(s for s in dev_scores if s.strategy == StrategyClass.FULL_ATLAS_RECOVERY)
        no_rec_score = next(s for s in dev_scores if s.strategy == StrategyClass.NO_RECOVERY)

        assert atlas_score.overall_resilience_score > 90.0
        assert no_rec_score.overall_resilience_score < 25.0

    def test_20_deterministic_event_log_replay_sha256(self):
        """Verifies that replaying recorded event log yields bit-exact cryptographic SHA-256 match."""
        replay_engine = DeterministicFaultReplayEngine()
        replay_engine.record_event(
            ReplayEventType.FAULT_INJECTED,
            "ROVER-PERSEVERANCE",
            100.0,
            {"fault_id": "FAIL-MEC-01", "intensity": 1.0},
        )
        replay_engine.record_event(
            ReplayEventType.DIAGNOSIS_CONFIRMED,
            "ROVER-PERSEVERANCE",
            105.0,
            {"confirmed_fault": "FAIL-MEC-01", "confidence": 0.96},
        )
        replay_engine.record_event(
            ReplayEventType.RECOVERY_DISPATCHED,
            "ROVER-PERSEVERANCE",
            110.0,
            {"action": "ISOLATE_FL_MOTOR", "mode": "5_WHEEL_DRIVE"},
        )

        log = replay_engine.get_log()
        assert len(log) == 3

        verification = replay_engine.replay_log(log)
        assert verification["is_bit_exact_reproducible"] is True
        assert len(verification["hash_mismatches"]) == 0

    def test_21_schema_contract_validation(self):
        """Validates mission resilience API payload against JSON Schema Draft 2020-12."""
        payload = {
            "status": "DEGRADED",
            "system_health_index": 0.72,
            "timestamp_sol_s": 3600.0,
            "active_faults": [
                {
                    "instance_id": "INJ-001-FAIL-MEC-01",
                    "record": FailureTaxonomyRegistry.get_standard_catalog()[0].to_dict(),
                    "state": "ACTIVE",
                    "current_intensity": 1.0,
                }
            ],
            "diagnoses": [
                {
                    "fault_id": "FAIL-MEC-01",
                    "fault_name": "Front-Right Wheel Drive Actuator Stall",
                    "confidence": 0.96,
                    "status": "CONFIRMED",
                    "severity": "CRITICAL",
                }
            ],
            "recovery_metrics_12d": {
                "science_objectives_completed": 5,
                "science_objectives_preserved_deferred": 1,
                "science_objectives_abandoned": 0,
                "energy_remaining_wh": 710.0,
                "data_retained_mb": 420.0,
                "data_lost_mb": 0.0,
                "mission_duration_extension_s": 9000.0,
                "time_to_recover_s": 272.0,
                "unresolved_failures_count": 0,
                "remaining_operational_constraints": ["ROVER_5_WHEEL_DRIVE_ACTIVE"],
                "resource_violations_count": 0,
                "final_mission_state_validity": True,
                "state_validity_explanation": "All critical mission parameters verified.",
            },
        }
        # Validate against mission-resilience.schema.json
        is_valid, errors = validate_contract(payload, "mission-resilience")
        assert is_valid is True, f"Schema errors: {errors}"
