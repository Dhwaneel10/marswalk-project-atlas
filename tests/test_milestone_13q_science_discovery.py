"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q Test Suite
=========================================================
Formal verification of the Atlas Autonomous Science Discovery Engine:
- Hypothesis lifecycle & competing hypothesis registry
- Traceable scientific evidence DAG & evidential authority bounding
- Shannon entropy & Expected Information Gain (EIG)
- Instrument physical wavelength limits & experiment design
- Adversarial hypothesis testing & false discovery prevention
- Multi-strategy benchmark evaluation across development and held-out scenario families
- Deterministic cryptographic replay verification
- REST API and Draft 2020-12 schema validation
"""

import math
import pytest
from typing import Dict, Any, List

from marswalk.core.science_hypothesis_registry import (
    EvidenceRelation,
    HypothesisStatus,
    ScienceHypothesisRegistry,
    ScientificHypothesis,
)
from marswalk.core.science_evidence_graph import (
    EdgeRelation,
    EvidenceClassification,
    EvidenceEdge,
    EvidenceNode,
    EvidenceQuality,
    NodeType,
    ScientificEvidenceGraph,
)
from marswalk.core.science_uncertainty_field import (
    ScienceUncertaintyField,
    SyntheticGroundTruthTarget,
)
from marswalk.core.science_observation_value import (
    CandidateObservationAction,
    ObservationCostProfile,
    ScienceObservationValueEngine,
    SelectionStrategy,
)
from marswalk.core.science_experiment_design import (
    PlatformType,
    ScienceExperimentDesigner,
    SpectralDomain,
    STANDARD_INSTRUMENTS,
)
from marswalk.core.science_hypothesis_tester import (
    ArtifactType,
    ScienceHypothesisTester,
)
from marswalk.core.active_science_planner import (
    ActiveSciencePlanner,
    ExplorationAsset,
)
from marswalk.core.science_campaign_evaluator import (
    ScienceCampaignEvaluator,
)
from marswalk.core.science_discovery_scenario_engine import (
    ScienceDiscoveryScenarioEngine,
)
from marswalk.core.science_discovery_replay import (
    ScienceDiscoveryReplayEngine,
)
from marswalk.api.contracts import validate_contract


class TestMilestone13QScienceDiscovery:

    def test_01_hypothesis_creation_and_competing_linkage(self):
        """Test hypothesis creation, competing links, and self-compete prevention."""
        reg = ScienceHypothesisRegistry()
        specs = [
            {"hypothesis_id": "H1", "title": "Smectite Clay", "description": "Hydrous clay", "prior_probability": 0.5},
            {"hypothesis_id": "H2", "title": "Carbonate Unit", "description": "Carbonate", "prior_probability": 0.5},
        ]
        created = reg.create_competing_hypothesis_set(
            campaign_id="CMP-TEST",
            scientific_question="What mineral is this?",
            target_region={"area": "Jezero"},
            hypotheses_specs=specs,
        )
        assert len(created) == 2
        h1 = reg.get_hypothesis("H1")
        h2 = reg.get_hypothesis("H2")
        assert "H2" in h1.competing_hypothesis_ids
        assert "H1" in h2.competing_hypothesis_ids

        # Self-compete rejection
        with pytest.raises(ValueError, match="Cannot link hypothesis as competing with itself"):
            reg.link_competing("H1", "H1")

    def test_02_hypothesis_state_transition_invariants(self):
        """Invariant: Cannot transition to SUPPORTED without evidence and evaluation method."""
        reg = ScienceHypothesisRegistry()
        hyp = ScientificHypothesis(
            hypothesis_id="HYP-INV",
            campaign_id="CMP-TEST",
            scientific_question="Does this exist?",
            title="Hypothesis Test",
            description="",
            target_region={},
            relevant_variables=[],
            status=HypothesisStatus.ACTIVE,
        )
        reg.register_hypothesis(hyp)

        # Attempt to transition to SUPPORTED without evidence -> must raise ValueError
        with pytest.raises(ValueError, match="Invariant violation: Cannot transition"):
            reg.transition_status(
                "HYP-INV",
                new_status=HypothesisStatus.SUPPORTED_BY_EVIDENCE,
                reason="Premature assertion",
                evidence_ids=[],
                evaluation_method="None",
            )

        # Transition with valid evidence
        reg.transition_status(
            "HYP-INV",
            new_status=HypothesisStatus.SUPPORTED_BY_EVIDENCE,
            reason="Confirmed by PIXL lithochemistry",
            evidence_ids=["OBS-PIXL-001"],
            evaluation_method="In-situ XRF stoichiometry",
        )
        assert hyp.status == HypothesisStatus.SUPPORTED_BY_EVIDENCE
        assert len(hyp.revision_history) == 1

    def test_03_evidence_graph_lineage_and_authority_bounding(self):
        """Invariant: An interpretation cannot inherit higher empirical standing than its supporting data."""
        graph = ScientificEvidenceGraph()

        # Simulated observation (low authority rank = 1)
        sim_obs = EvidenceNode(
            node_id="NODE-SIM-OBS",
            node_type=NodeType.OBSERVATION,
            classification=EvidenceClassification.SIMULATED_OBSERVATION,
            label="Simulated Radar Echo",
            description="",
            payload={"depth_m": 4.2},
            quality=EvidenceQuality(0.8, "UNCALIBRATED", "LOCAL", "SYNTHETIC", "RIMFAX", [0.5]),
            source_hash="abcd",
            scientific_provenance="Synthetic model",
            timestamp_utc=100.0,
        )
        graph.add_node(sim_obs)

        # Derived feature (claims DERIVED_OBSERVATION, rank = 5)
        derived_feat = EvidenceNode(
            node_id="NODE-DERIVED-FEAT",
            node_type=NodeType.FEATURE,
            classification=EvidenceClassification.DERIVED_OBSERVATION,
            label="Layer Interface",
            description="",
            payload={},
            quality=EvidenceQuality(0.8, "UNCALIBRATED", "LOCAL", "SYNTHETIC", "RIMFAX", [0.5]),
            source_hash="ef01",
            scientific_provenance="Derived boundary",
            timestamp_utc=101.0,
        )
        graph.add_node(derived_feat)
        graph.add_edge("NODE-SIM-OBS", "NODE-DERIVED-FEAT", EdgeRelation.DERIVED_FROM)

        # Interpretation claiming DIRECT_OBSERVATION (rank = 7)
        interp = EvidenceNode(
            node_id="NODE-INTERP-CLAIM",
            node_type=NodeType.INTERPRETATION,
            classification=EvidenceClassification.DIRECT_OBSERVATION,
            label="Subsurface Ice Sheet",
            description="",
            payload={},
            quality=EvidenceQuality(0.8, "UNCALIBRATED", "LOCAL", "SYNTHETIC", "RIMFAX", [0.5]),
            source_hash="2345",
            scientific_provenance="Claim",
            timestamp_utc=102.0,
        )
        graph.add_node(interp)
        graph.add_edge("NODE-DERIVED-FEAT", "NODE-INTERP-CLAIM", EdgeRelation.INTERPRETS)

        # Test maximum inherited authority
        auth = graph.get_maximum_inherited_authority("NODE-INTERP-CLAIM")
        # Lineage roots in SIMULATED_OBSERVATION, so max inherited authority is bounded down to SIMULATED_OBSERVATION
        assert auth == EvidenceClassification.SIMULATED_OBSERVATION

    def test_04_orphan_claim_detection(self):
        """Test graph detection of orphan claims lacking supporting observation links."""
        graph = ScientificEvidenceGraph()
        orphan = EvidenceNode(
            node_id="NODE-ORPHAN",
            node_type=NodeType.INTERPRETATION,
            classification=EvidenceClassification.SCIENTIFIC_INTERPRETATION,
            label="Unsupported assertion",
            description="",
            payload={},
            quality=EvidenceQuality(0.5, "UNCALIBRATED", "UNKNOWN", "UNKNOWN", "NONE", [1.0]),
            source_hash="9999",
            scientific_provenance="None",
            timestamp_utc=100.0,
        )
        graph.add_node(orphan)
        orphans = graph.detect_orphan_claims()
        assert "NODE-ORPHAN" in orphans

    def test_05_shannon_entropy_calculation(self):
        """Verify hand-computable entropy math: uniform binary distribution has H = 1.0 bit."""
        val = ScienceObservationValueEngine()
        # Binary equal probabilities [0.5, 0.5] -> - (0.5 * (-1) + 0.5 * (-1)) = 1.0 bit
        h_bin = val.shannon_entropy([0.5, 0.5])
        assert pytest.approx(h_bin, 1e-5) == 1.0

        # Deterministic certainty [1.0, 0.0] -> 0.0 bits
        h_cert = val.shannon_entropy([1.0, 0.0])
        assert pytest.approx(h_cert, 1e-5) == 0.0

        # Three equal hypotheses [1/3, 1/3, 1/3] -> log2(3) = 1.58496 bits
        h_tri = val.shannon_entropy([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0])
        assert pytest.approx(h_tri, 1e-4) == 1.5850

    def test_06_expected_information_gain_discrimination(self):
        """Expected Information Gain (EIG) must be strictly positive for discriminating tests and zero for uninformative tests."""
        val = ScienceObservationValueEngine()
        prior = [0.5, 0.5]

        # Case A: Perfectly discriminating test (outcome 0 if H0, outcome 1 if H1)
        lik_perfect = [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
        eig_perf, prior_h, _ = val.compute_expected_information_gain(prior, lik_perfect)
        assert pytest.approx(prior_h, 1e-4) == 1.0
        assert pytest.approx(eig_perf, 1e-4) == 1.0  # Gains full 1.0 bit of information!

        # Case B: Completely uninformative test (coin flip independent of hypothesis)
        lik_uninformative = [
            [0.5, 0.5],
            [0.5, 0.5],
        ]
        eig_none, _, _ = val.compute_expected_information_gain(prior, lik_uninformative)
        assert pytest.approx(eig_none, 1e-4) == 0.0  # Zero information gain!

    def test_07_cost_aware_utility_ranking(self):
        """Cost-aware discovery ranks actions by information density (EIG / Cost)."""
        val = ScienceObservationValueEngine()
        high_gain_cheap = CandidateObservationAction(
            action_id="A-CHEAP",
            target_id="T1",
            target_name="Nearby Outcrop",
            coordinates_xy_m=(10.0, 10.0),
            required_instrument_id="SUPERCAM_VISIR",
            required_platform="ROVER",
            cost=ObservationCostProfile(15.0, 60.0, 180.0, 5.0, 30.0, 0.1),
            expected_info_gain_bits=1.0,
            discriminating_power=0.8,
        )
        high_gain_expensive = CandidateObservationAction(
            action_id="A-EXPENSIVE",
            target_id="T2",
            target_name="Distant Crater",
            coordinates_xy_m=(800.0, 900.0),
            required_instrument_id="SUPERCAM_VISIR",
            required_platform="ROVER",
            cost=ObservationCostProfile(120.0, 3600.0, 180.0, 50.0, 120.0, 0.8),
            expected_info_gain_bits=1.0,
            discriminating_power=0.8,
        )

        ranked = val.rank_actions([high_gain_expensive, high_gain_cheap], SelectionStrategy.COST_AWARE_DISCOVERY)
        # Cheap nearby action should rank higher due to lower composite cost
        assert ranked[0][0].action_id == "A-CHEAP"

    def test_08_instrument_physical_wavelength_boundary_rejection(self):
        """Enforces that an instrument cannot plan observations outside its physical wavelength range."""
        designer = ScienceExperimentDesigner()

        # AERO_NIR_SPECTROMETER operates in [700, 1050] nm. Requesting 2300 nm (2.3 um) must fail!
        valid, msg = designer.validate_instrument_for_wavelength("AERO_NIR_SPECTROMETER", 2300.0)
        assert not valid
        assert "Physical wavelength violation" in msg

        # SUPERCAM_VISIR operates in [400, 2600] nm. Requesting 2300 nm must succeed!
        valid_sc, msg_sc = designer.validate_instrument_for_wavelength("SUPERCAM_VISIR", 2300.0)
        assert valid_sc
        assert "verified" in msg_sc

    def test_09_experiment_design_environmental_constraint_check(self):
        """Experiment design rejects execution if atmospheric dust tau exceeds instrument tolerance."""
        designer = ScienceExperimentDesigner()

        # AERO_NIR_SPECTROMETER tolerates max dust tau = 0.60. An elevated dust storm with tau = 0.95 must fail!
        with pytest.raises(ValueError, match="Environmental constraint violation"):
            designer.design_experiment(
                scientific_question="Analyze mineral signature",
                target_id="T-01",
                target_name="Dusty Rim",
                target_coordinates_xy_m=(50.0, 50.0),
                target_wavelength_nm=850.0,
                required_domain=SpectralDomain.NEAR_INFRARED,
                selected_instrument_id="AERO_NIR_SPECTROMETER",
                hypotheses_under_test=["HYP-01"],
                expected_dust_tau=0.95,
            )

    def test_10_adversarial_tester_identifies_co2_and_falsification_tests(self):
        """Adversarial tester flags atmospheric CO2 overprint and prescribes companion hydration checks."""
        tester = ScienceHypothesisTester()
        hyp = ScientificHypothesis(
            hypothesis_id="HYP-CLAY-TEST",
            campaign_id="CMP-TEST",
            scientific_question="Is this smectite?",
            title="Smectite Candidate",
            description="",
            target_region={},
            relevant_variables=[],
        )

        fals_rec = tester.analyze_spectral_anomaly(
            hypothesis=hyp,
            observed_band_nm=2300.0,
            band_depth=0.14,
            dust_optical_depth_tau=0.45,
            surface_pressure_pa=610.0,
            instrument_id="AERO_NIR_SPECTROMETER",
        )

        assert ArtifactType.ATMOSPHERIC_CO2_OVERPRINT in fals_rec.potential_artifacts_identified
        assert any("1900 nm" in f for f in fals_rec.mandatory_companion_features)
        assert any(t["test_name"] == "PIXL_ELEMENTAL_STOICHIOMETRY" for t in fals_rec.discriminating_counter_tests)

    def test_11_adversarial_tester_falsifies_clay_on_carbonate_lithochemistry(self):
        """Adversarial evaluation disproves clay hypothesis when PIXL reveals high Ca and zero Al."""
        tester = ScienceHypothesisTester()
        hyp = ScientificHypothesis(
            hypothesis_id="HYP-CLAY",
            campaign_id="CMP-TEST",
            scientific_question="Is this smectite?",
            title="Smectite Candidate",
            description="",
            target_region={},
            relevant_variables=[],
            status=HypothesisStatus.UNDER_INVESTIGATION,
        )

        # Carbonate rock measurements: high Calcium, low Aluminum
        meas = {"al_wt_pct": 0.12, "ca_wt_pct": 26.5, "si_wt_pct": 3.5}
        status, reason, post = tester.evaluate_test_results_against_hypothesis(
            hyp, "PIXL_ELEMENTAL_STOICHIOMETRY", meas
        )
        assert status == HypothesisStatus.REJECTED
        assert "proves carbonate-bearing unit, disproving phyllosilicate" in reason
        assert post <= 0.05

    def test_12_uncertainty_field_unobserved_vs_observed_spatial_gradient(self):
        """Uncertainty field models spatial ignorance increasing with distance from observations."""
        unc = ScienceUncertaintyField(grid_width_m=500.0, grid_height_m=500.0, resolution_m=10.0)
        # Record observation at (50, 50)
        unc.record_observation_event(50.0, 50.0, timestamp_sol=1.0, quality=0.95)

        # Point right next to observation (52, 50)
        p_near = unc.evaluate_point_uncertainty(52.0, 50.0, current_sol=1.0)
        # Point far away from observation (450, 450)
        p_far = unc.evaluate_point_uncertainty(450.0, 450.0, current_sol=1.0)

        assert p_near.spatial_interpolation_uncertainty < p_far.spatial_interpolation_uncertainty
        assert p_near.data_coverage_factor > p_far.data_coverage_factor

    def test_13_closed_loop_active_planner_execution_cycle(self):
        """Executes a full active discovery cycle: action synthesis, ranking, execution, and state update."""
        reg = ScienceHypothesisRegistry()
        graph = ScientificEvidenceGraph()
        unc = ScienceUncertaintyField(500, 500, 10)
        val = ScienceObservationValueEngine()
        des = ScienceExperimentDesigner()
        tester = ScienceHypothesisTester()
        planner = ActiveSciencePlanner(reg, graph, unc, val, des, tester)

        rover = ExplorationAsset(
            "ROVER-1", "Rover", PlatformType.ROVER, (0.0, 0.0), 200.0, 200.0, 1000.0, ["PIXL", "SUPERCAM_VISIR"]
        )
        planner.register_asset(rover)

        reg.create_competing_hypothesis_set(
            "CMP-1", "Question", {},
            [
                {"hypothesis_id": "H-CLAY", "title": "Clay", "description": "", "prior_probability": 0.5},
                {"hypothesis_id": "H-CARB", "title": "Carbonate", "description": "", "prior_probability": 0.5},
            ]
        )

        log = planner.execute_next_best_observation(
            campaign_id="CMP-1",
            target_coords=[(20.0, 20.0, "T-1")],
            strategy=SelectionStrategy.COST_AWARE_DISCOVERY,
            current_sol=1.0,
            synthetic_ground_truth={"al_wt_pct": 3.1, "ca_wt_pct": 1.2, "si_wt_pct": 22.0},
        )

        assert log["step_name"] == "OBSERVATION_CYCLE_COMPLETED"
        h_clay = reg.get_hypothesis("H-CLAY")
        assert h_clay.status == HypothesisStatus.SUPPORTED_BY_EVIDENCE
        assert h_clay.posterior_probability > 0.85

    def test_14_resource_feasibility_enforcement(self):
        """Planner rejects execution when asset battery is below required mission energy."""
        reg = ScienceHypothesisRegistry()
        graph = ScientificEvidenceGraph()
        unc = ScienceUncertaintyField(500, 500, 10)
        val = ScienceObservationValueEngine()
        des = ScienceExperimentDesigner()
        tester = ScienceHypothesisTester()
        planner = ActiveSciencePlanner(reg, graph, unc, val, des, tester)

        # Depleted rover with only 0.5 Wh battery
        rover = ExplorationAsset(
            "ROVER-DEPLETED", "Rover", PlatformType.ROVER, (0.0, 0.0), 0.5, 200.0, 1000.0, ["PIXL"]
        )
        planner.register_asset(rover)

        reg.create_competing_hypothesis_set(
            "CMP-RES", "Q", {},
            [{"hypothesis_id": "H1", "title": "H1", "description": "", "prior_probability": 0.5}]
        )

        with pytest.raises(ValueError, match="Resource constraint violation"):
            planner.execute_next_best_observation(
                campaign_id="CMP-RES",
                target_coords=[(50.0, 50.0, "T-RES")],
                strategy=SelectionStrategy.COST_AWARE_DISCOVERY,
            )

    def test_15_scenario_01_flagship_crater_reveal_six_stages(self):
        """Scenario 01 completes all 6 stages with confirmed smectite clay discovery."""
        engine = ScienceDiscoveryScenarioEngine()
        res = engine.run_scenario("SCENARIO_01")
        assert res["execution_status"] == "SUCCESS"
        assert res["total_stages"] == 6
        stage_names = [s["stage_name"] for s in res["stages"]]
        assert stage_names == [
            "AERIAL_ANOMALY_DETECTION",
            "INSTRUMENT_CAPABILITY_AUDIT",
            "COMPETING_HYPOTHESES_SYNTHESIS",
            "ACTIVE_EXPERIMENT_SELECTION",
            "IN_SITU_LITHOCHEMISTRY_EXECUTION",
            "HYPOTHESIS_STATE_RESOLUTION",
        ]
        final_stage = res["stages"][5]["telemetry"]
        assert final_stage["HYP-01-SMECTITE"]["status"] == "SUPPORTED_BY_EVIDENCE"
        assert final_stage["HYP-02-CARBONATE"]["status"] == "REJECTED"

    def test_16_scenario_02_false_discovery_self_rejection(self):
        """Scenario 02: Engine discovers detector thermal spike and rejects initial clay guess."""
        engine = ScienceDiscoveryScenarioEngine()
        res = engine.run_scenario("SCENARIO_02")
        assert res["execution_status"] == "SUCCESS"
        assert res["total_stages"] == 4
        final_stage = res["stages"][3]["telemetry"]
        assert final_stage["initial_guess_disproved"] is True
        assert final_stage["false_discovery_prevented"] is True

    def test_17_scenario_03_two_mineral_discrimination(self):
        """Scenario 03: Engine uses PIXL elemental chemistry to distinguish smectite from carbonate."""
        engine = ScienceDiscoveryScenarioEngine()
        res = engine.run_scenario("SCENARIO_03")
        assert res["execution_status"] == "SUCCESS"
        final_stage = res["stages"][3]["telemetry"]
        assert final_stage["HYP-CARBONATE"] == "SUPPORTED_BY_EVIDENCE"
        assert final_stage["HYP-SMECTITE"] == "REJECTED"

    def test_18_benchmark_evaluator_held_out_comparison(self):
        """Benchmark evaluator confirms Cost-Aware and EIG strategies outperform greedy anomaly on held-out scenarios."""
        evaluator = ScienceCampaignEvaluator()
        bench = evaluator.run_comprehensive_benchmark()
        assert "development_scenario_benchmark" in bench
        assert "held_out_scenario_benchmark" in bench

        held_out = {r["strategy"]: r for r in bench["held_out_scenario_benchmark"]}
        # Cost-aware discovery must achieve lower false positive rate than greedy anomaly
        assert held_out["COST_AWARE_DISCOVERY"]["false_positive_rate"] < held_out["GREEDY_ANOMALY"]["false_positive_rate"]
        # Cost-aware discovery must achieve higher classification accuracy
        assert held_out["COST_AWARE_DISCOVERY"]["classification_accuracy"] > held_out["GREEDY_ANOMALY"]["classification_accuracy"]

    def test_19_deterministic_cryptographic_replay(self):
        """Deterministic replay produces 100% bit-exact SHA-256 state hashes across multiple runs."""
        replay = ScienceDiscoveryReplayEngine()
        session = replay.verify_deterministic_replay(scenario_id="SCENARIO_01", iterations=5, seed=42)
        assert session.is_bit_exact_match is True
        assert len(session.stage_hashes) == 6
        assert len(session.cumulative_state_hash) == 64  # Valid SHA-256 hex digest length

    def test_20_api_contract_schema_validation(self):
        """Live API status payload strictly conforms to schemas/api/v1/science-discovery.schema.json."""
        from marswalk.api.service import science_discovery_status_api
        payload = science_discovery_status_api()
        # validate_contract raises ContractValidationError if schema is violated
        validate_contract(payload, "science-discovery")
        assert payload["campaign_id"] == "CMP-JEZERO-DISCOVERY"
        assert len(payload["hypotheses"]) >= 3
        assert "scientific_truth_disclosure" in payload
        assert "astronaut_safety_notice" in payload
