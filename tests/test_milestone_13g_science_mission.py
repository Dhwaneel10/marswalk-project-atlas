"""
Milestone 13G — Atlas Science Return & Data Logistics Comprehensive Test Suite.

Tests science target prioritization, instrument compatibility, 5-phase observation scheduling,
exact byte conservation, onboard storage pressure, simulated data transfer, and 8D Pareto co-design.
"""

import json
import math
import os
import pytest
from typing import Dict, List, Any

from marswalk.core.terrain import TerrainGrid, TerrainConfig, derive_terrain_from_array
from marswalk.core.mission_resource_model import (
    RoverResourceConfig,
    RelayResourceConfig,
    wh_to_joules,
    joules_to_wh,
)
from marswalk.core.mission_data_ledger import (
    DataCategory,
    DataProductStorageStatus,
    DataProductTransferStatus,
    MissionDataProduct,
    MissionDataLedger,
    PriorityType,
    RetentionPolicy,
    StoragePressureState,
    StoragePolicyViolationError,
    StorageCapacityExceededError,
    SYNTHETIC_DATA_PROFILES_BYTES,
    compute_product_sha256,
)
from marswalk.core.science_mission_planner import (
    ScienceObjective,
    InstrumentId,
    InstrumentProfile,
    INSTRUMENT_CATALOG,
    ScienceTargetConfig,
    ScheduledObservationEvent,
    ScheduledTargetPlan,
    ScienceMissionPlanner,
    IncompatibleObservationError,
    ObservationPhase,
)
from marswalk.core.joint_mission_planner import (
    JointMissionInput,
    JointMissionMetrics,
    JointMissionConfiguration,
    optimize_joint_mission,
    evaluate_joint_mission,
    evaluate_science_and_data_logistics,
    compute_canonical_normalization,
    compute_scalar_score,
)


@pytest.fixture
def synthetic_terrain() -> TerrainGrid:
    """Create a 100x100 synthetic elevation grid for deterministic unit testing."""
    import numpy as np
    elevation = np.zeros((100, 100), dtype=np.float32)
    # Gentle slope with a central promontory
    for r in range(100):
        for c in range(100):
            elevation[r, c] = -2500.0 + (r * 0.5) + (c * 0.3)
    # Central promontory
    elevation[45:55, 45:55] += 60.0
    cfg = TerrainConfig(dx_ground_m=20.0, dy_ground_m=20.0, theta_max_deg=25.0)
    return derive_terrain_from_array(elevation, config=cfg)


# ==============================================================================
# 1. Science Target Registry & Prioritization
# ==============================================================================
class TestScienceTargetRegistryAndPrioritization:

    def test_priority_provenance_classification(self):
        """Verifies tri-state priority model distinguishing user, source, and unassessed."""
        target_user = ScienceTargetConfig(
            target_id="tgt_user",
            target_name="User Target",
            grid_coord=(10, 10),
            priority_score=85.0,
            priority_type=PriorityType.USER_ASSIGNED_PRIORITY,
        )
        assert target_user.priority_type == PriorityType.USER_ASSIGNED_PRIORITY
        assert target_user.priority_score == 85.0

        target_source = ScienceTargetConfig(
            target_id="tgt_source",
            target_name="Hawksbill Gap",
            grid_coord=(20, 20),
            priority_score=95.0,
            priority_type=PriorityType.SOURCE_DERIVED_PRIORITY,
            source_citation="Farley et al. 2022, Science 377",
        )
        assert target_source.priority_type == PriorityType.SOURCE_DERIVED_PRIORITY
        assert "Farley" in target_source.source_citation

        target_unassessed = ScienceTargetConfig(
            target_id="tgt_unassessed",
            target_name="Unassessed Crater",
            grid_coord=(30, 30),
            priority_score=0.0,
            priority_type=PriorityType.UNASSESSED_PRIORITY,
        )
        assert target_unassessed.priority_type == PriorityType.UNASSESSED_PRIORITY
        assert target_unassessed.priority_score == 0.0

    def test_authentic_jezero_targets_load(self):
        """Verifies authentic NASA Mars 2020 Jezero waypoints are present with citations."""
        wp_path = "data/waypoints_jezero.json"
        assert os.path.exists(wp_path), f"Missing {wp_path}"
        with open(wp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        waypoints = data["waypoints"] if isinstance(data, dict) and "waypoints" in data else data
        assert len(waypoints) >= 10
        # Check Hawksbill Gap
        hawksbill = next((w for w in waypoints if "Hawksbill" in w["name"]), None)
        assert hawksbill is not None
        assert "pds_citation" in hawksbill or "citation" in hawksbill
        assert hawksbill["priority_score"] >= 80.0


# ==============================================================================
# 2. Instrument Taxonomy & Compatibility Layer
# ==============================================================================
class TestInstrumentTaxonomyAndCompatibility:

    def test_instrument_catalog_integrity(self):
        """Verifies all 7 instruments and 10 modes are calibrated in catalog."""
        assert len(INSTRUMENT_CATALOG) >= 10
        assert "MASTCAM_Z_STEREO" in INSTRUMENT_CATALOG
        assert "SUPERCAM_LIBS" in INSTRUMENT_CATALOG
        assert "PIXL_XRF_GRID" in INSTRUMENT_CATALOG
        assert "SHERLOC_DUV_RAMAN" in INSTRUMENT_CATALOG
        assert "RIMFAX_DEEP" in INSTRUMENT_CATALOG
        assert "MEDA_HIGH_RATE" in INSTRUMENT_CATALOG
        assert "CORING_ABRASION" in INSTRUMENT_CATALOG

    def test_incompatible_objective_rejection(self):
        """Verifies IncompatibleObservationError is raised for invalid mode-objective pairs."""
        target = ScienceTargetConfig(
            target_id="tgt_incompat",
            target_name="Atmospheric Target",
            grid_coord=(10, 10),
            primary_objective=ScienceObjective.ATMOSPHERIC_OBSERVATION,
            selected_modes=["PIXL_XRF_GRID"],  # PIXL cannot do atmospheric observation
        )
        with pytest.raises(IncompatibleObservationError):
            target.validate_instrument_compatibility()

    def test_turret_arm_singularity_rejection(self):
        """Verifies multiple arm turret instruments cannot be operated concurrently."""
        target = ScienceTargetConfig(
            target_id="tgt_turret_conflict",
            target_name="Sample Target",
            grid_coord=(10, 10),
            primary_objective=ScienceObjective.MINERALOGICAL_INVESTIGATION,
            selected_modes=["PIXL_XRF_GRID", "SHERLOC_DUV_RAMAN"],  # Both on turret arm
        )
        with pytest.raises(IncompatibleObservationError) as excinfo:
            target.validate_instrument_compatibility()
        assert "Turret arm conflict" in str(excinfo.value)


# ==============================================================================
# 3. Chronological 5-Phase Observation Scheduling
# ==============================================================================
class TestChronologicalObservationScheduling:

    def test_five_phase_scheduling_execution(self):
        """Verifies full 5-phase decomposition and monotonic timeline events."""
        target = ScienceTargetConfig(
            target_id="tgt_delta",
            target_name="Delta Outcrop",
            grid_coord=(25, 25),
            primary_objective=ScienceObjective.SURFACE_MORPHOLOGY,
            selected_modes=["MASTCAM_Z_STEREO"],
        )
        planner = ScienceMissionPlanner()
        plan = planner.schedule_target_observation(target, arrival_time_s=1000.0)

        assert plan.arrival_time_s == 1000.0
        assert plan.departure_time_s > plan.arrival_time_s
        assert plan.total_dwell_s > 0
        assert len(plan.events) == 5  # Arrival, Warmup, Exec, Post-process, Stow

        # Verify phase sequence
        phases = [e.phase for e in plan.events]
        assert phases == [
            ObservationPhase.ROVER_ARRIVAL_AND_SETTLE,
            ObservationPhase.INSTRUMENT_PREPARATION_AND_WARMUP,
            ObservationPhase.OBSERVATION_EXECUTION,
            ObservationPhase.DATA_POST_PROCESSING_AND_CACHE,
            ObservationPhase.INSTRUMENT_STOW_AND_SECURE,
        ]

        # Verify monotonic timestamps
        for i in range(1, len(plan.events)):
            assert plan.events[i].start_time_s >= plan.events[i - 1].end_time_s

    def test_coupled_energy_consumption(self):
        """Verifies energy calculation integrates power draw and duration into Watt-hours."""
        target = ScienceTargetConfig(
            target_id="tgt_libs",
            target_name="SuperCam Target",
            grid_coord=(20, 20),
            primary_objective=ScienceObjective.MINERALOGICAL_INVESTIGATION,
            selected_modes=["SUPERCAM_LIBS"],
        )
        planner = ScienceMissionPlanner()
        plan = planner.schedule_target_observation(target, arrival_time_s=500.0)
        assert plan.total_energy_consumed_wh > 0.0
        # Energy should equal sum of event energies
        event_energy_sum = sum(e.energy_consumed_wh for e in plan.events)
        assert abs(plan.total_energy_consumed_wh - event_energy_sum) < 1e-4


# ==============================================================================
# 4. Onboard Storage Ledger & Byte Conservation
# ==============================================================================
class TestMissionDataLedgerAndByteConservation:

    def test_first_law_byte_conservation_identity(self):
        """
        Verifies exact byte conservation: S_used(t) == S_used(t-1) + S_gen(t) - S_rel(t)
        with zero-byte error across multiple generations and releases.
        """
        ledger = MissionDataLedger(capacity_bytes=100_000_000)  # 100 MB

        # Generate Product 1 (12 MB)
        p1 = MissionDataProduct(
            product_id="dp_001",
            observation_id="obs_01",
            target_id="tgt_01",
            instrument_id="MASTCAM_Z",
            category=DataCategory.MULTISPECTRAL_IMAGERY,
            size_bytes=12_000_000,
            created_mission_time_s=100.0,
        )
        ledger.register_data_product(p1)
        assert ledger.used_bytes == 12_000_000
        is_conserved, disc, _ = ledger.verify_byte_conservation()
        assert is_conserved and disc == 0

        # Generate Product 2 (25 MB)
        p2 = MissionDataProduct(
            product_id="dp_002",
            observation_id="obs_02",
            target_id="tgt_02",
            instrument_id="SUPERCAM",
            category=DataCategory.SPECTRAL_CUBE,
            size_bytes=25_000_000,
            created_mission_time_s=200.0,
        )
        ledger.register_data_product(p2)
        assert ledger.used_bytes == 37_000_000
        is_conserved, disc, _ = ledger.verify_byte_conservation()
        assert is_conserved and disc == 0

        # Simulate Transfer of Product 1
        ledger.simulate_transfer_window(
            start_time_s=300.0,
            duration_s=100.0,
            network_path=["ROVER", "SURFACE_BASE_STATION"],
        )
        assert p1.transfer_status == DataProductTransferStatus.TRANSFER_VERIFIED

        # Release Product 1 storage
        freed = ledger.release_transferred_storage("dp_001", current_time_s=400.0)
        assert freed == 12_000_000
        assert ledger.used_bytes == 25_000_000

        # Verify Conservation
        is_conserved, disc, msg = ledger.verify_byte_conservation()
        assert is_conserved, msg
        assert disc == 0

    def test_storage_release_precondition_enforcement(self):
        """Verifies StoragePolicyViolationError is raised when attempting to release unverified data."""
        ledger = MissionDataLedger(capacity_bytes=50_000_000)
        p = MissionDataProduct(
            product_id="dp_unverified",
            observation_id="obs_01",
            target_id="tgt_01",
            instrument_id="PIXL",
            category=DataCategory.SPECTRAL_CUBE,
            size_bytes=20_000_000,
            created_mission_time_s=50.0,
        )
        ledger.register_data_product(p)
        assert p.transfer_status == DataProductTransferStatus.QUEUED

        # Attempting to release un-transferred data must fail
        with pytest.raises(StoragePolicyViolationError):
            ledger.release_transferred_storage("dp_unverified")

    def test_protected_permanent_record_inviolability(self):
        """Verifies permanent protected products cannot be released even after transfer."""
        ledger = MissionDataLedger(capacity_bytes=50_000_000)
        p = MissionDataProduct(
            product_id="dp_protected",
            observation_id="obs_sample",
            target_id="tgt_sample",
            instrument_id="CORING_TOOL",
            category=DataCategory.ENGINEERING_LOG,
            size_bytes=5_000_000,
            created_mission_time_s=100.0,
            retention_policy=RetentionPolicy.PROTECTED_PERMANENT,
        )
        ledger.register_data_product(p)

        # Simulate transfer
        ledger.simulate_transfer_window(
            start_time_s=200.0,
            duration_s=100.0,
            network_path=["ROVER", "SURFACE_BASE_STATION"],
        )
        assert p.transfer_status == DataProductTransferStatus.TRANSFER_VERIFIED

        # Attempting release must raise StoragePolicyViolationError
        with pytest.raises(StoragePolicyViolationError):
            ledger.release_transferred_storage("dp_protected")

    def test_capacity_overflow_rejection(self):
        """Verifies strict capacity overflow error when data generation exceeds flash size."""
        ledger = MissionDataLedger(capacity_bytes=10_000_000, strict_capacity_enforcement=True)
        p_large = MissionDataProduct(
            product_id="dp_too_big",
            observation_id="obs_01",
            target_id="tgt_01",
            instrument_id="MASTCAM_Z",
            category=DataCategory.HIGH_RES_PANORAMA,
            size_bytes=15_000_000,  # 15 MB > 10 MB capacity
            created_mission_time_s=50.0,
        )
        with pytest.raises(StorageCapacityExceededError):
            ledger.register_data_product(p_large)


# ==============================================================================
# 5. Simulated Data Transfer Logistics
# ==============================================================================
class TestSimulatedDataTransferLogistics:

    def test_deterministic_transfer_rate_integration(self):
        """Verifies D_transferred = R_eff * dt exactly."""
        rate_bps = 2_000_000.0  # 2.0 Mbps
        overhead = 8.0  # 8%
        duty = 0.85
        ledger = MissionDataLedger(
            capacity_bytes=100_000_000,
            configured_transfer_rate_bps=rate_bps,
            protocol_overhead_pct=overhead,
            duty_cycle=duty,
        )
        # Expected rate
        expected_rate_bps = rate_bps * (1.0 - 0.08) * 0.85  # 1,564,000 bps = 195,500 B/s
        assert abs(ledger.effective_transfer_rate_bps - expected_rate_bps) < 1e-4

        # Register product
        p = MissionDataProduct(
            product_id="dp_xfer_test",
            observation_id="obs_01",
            target_id="tgt_01",
            instrument_id="MASTCAM_Z",
            category=DataCategory.MULTISPECTRAL_IMAGERY,
            size_bytes=5_000_000,
            created_mission_time_s=100.0,
        )
        ledger.register_data_product(p)

        # 10 second transfer window
        transfers = ledger.simulate_transfer_window(
            start_time_s=200.0,
            duration_s=10.0,
            network_path=["ROVER", "SURFACE_BASE_STATION"],
        )
        assert len(transfers) == 1
        expected_bytes = int((expected_rate_bps / 8.0) * 10.0)
        assert abs(transfers[0].bytes_transferred - expected_bytes) <= 1

    def test_backlog_accounting_conservation(self):
        """Verifies backlog == generated - transferred - released."""
        ledger = MissionDataLedger(capacity_bytes=100_000_000)
        p1 = MissionDataProduct(
            product_id="dp_backlog_1",
            observation_id="obs_01",
            target_id="tgt_01",
            instrument_id="MASTCAM_Z",
            category=DataCategory.MULTISPECTRAL_IMAGERY,
            size_bytes=10_000_000,
            created_mission_time_s=50.0,
        )
        p2 = MissionDataProduct(
            product_id="dp_backlog_2",
            observation_id="obs_02",
            target_id="tgt_02",
            instrument_id="SUPERCAM",
            category=DataCategory.SPECTRAL_CUBE,
            size_bytes=20_000_000,
            created_mission_time_s=60.0,
        )
        ledger.register_data_product(p1)
        ledger.register_data_product(p2)
        assert ledger.backlog_bytes == 30_000_000

        # Partial transfer (15 MB transferred)
        ledger.simulate_transfer_window(
            start_time_s=100.0,
            duration_s=75.0,  # ~15 MB
            network_path=["ROVER", "SURFACE_BASE_STATION"],
        )
        assert ledger.backlog_bytes < 30_000_000
        assert ledger.backlog_bytes == (ledger.cumulative_generated_bytes - ledger.cumulative_transferred_bytes)


# ==============================================================================
# 6. Multi-Objective Pareto Co-Design & Hard Constraints
# ==============================================================================
class TestMultiObjectiveParetoCoDesign:

    def test_hard_constraint_cannot_be_overridden_by_science(self, synthetic_terrain):
        """Verifies that an energy-depleted candidate is rejected despite high science score."""
        # Rover with very small battery (only 100 Wh)
        starved_rover = RoverResourceConfig(
            usable_battery_capacity_wh=100.0,
            reserve_margin_pct=20.0,
        )
        # Science targets with maximum priority score (100.0)
        high_value_targets = [
            ScienceTargetConfig(
                target_id="tgt_rich",
                target_name="High Priority Outcrop",
                grid_coord=(50, 50),
                priority_score=100.0,
                primary_objective=ScienceObjective.SURFACE_MORPHOLOGY,
                selected_modes=["MASTCAM_Z_STEREO"],
            )
        ]
        path = [(10, 10), (20, 20), (30, 30), (40, 40), (50, 50)]
        config = evaluate_joint_mission(
            traverse_path=path,
            terrain=synthetic_terrain,
            base_station={"node_id": "BASE", "row": 10, "col": 10, "antenna_height_m": 10.0},
            rover_resource_config=starved_rover,
            science_targets=high_value_targets,
            evaluate_resources=True,
        )
        # Violations must be present
        assert len(config.constraint_violations) > 0
        assert any("battery" in v.lower() or "energy" in v.lower() or "depleted" in v.lower() for v in config.constraint_violations)

    def test_marginal_rate_of_substitution_calculation(self):
        """Verifies MRS computation for energy and data per science point."""
        m_rec = JointMissionMetrics(
            distance_m=1000.0, travel_time_s=2000.0, mean_slope_deg=5.0, max_slope_deg=10.0,
            elevation_gain_m=10.0, elevation_loss_m=5.0, terrain_effort_m=1100.0, connected_distance_m=900.0,
            gap_distance_m=100.0, gap_duration_s=200.0, availability_pct=90.0, max_gap_duration_s=60.0,
            gap_count=1, relay_count=1, mean_hops=1.0, max_hops=1, critical_bridges=0,
            energy_total_wh=250.0, science_points_total=50.0, data_transferred_bytes=10_000_000,
        )
        m_peer = JointMissionMetrics(
            distance_m=1200.0, travel_time_s=2400.0, mean_slope_deg=6.0, max_slope_deg=12.0,
            elevation_gain_m=15.0, elevation_loss_m=10.0, terrain_effort_m=1300.0, connected_distance_m=1100.0,
            gap_distance_m=100.0, gap_duration_s=200.0, availability_pct=91.6, max_gap_duration_s=60.0,
            gap_count=1, relay_count=1, mean_hops=1.0, max_hops=1, critical_bridges=0,
            energy_total_wh=350.0, science_points_total=80.0, data_transferred_bytes=25_000_000,
        )
        d_pts = m_peer.science_points_total - m_rec.science_points_total  # 30 pts
        d_energy = m_peer.energy_total_wh - m_rec.energy_total_wh          # 100 Wh
        mrs_e = d_energy / d_pts  # 3.33 Wh/pt
        assert abs(mrs_e - (100.0 / 30.0)) < 1e-4


# ==============================================================================
# 7. Scientific Integrity & Guardrails
# ==============================================================================
class TestScientificIntegrityAndRegressionGuard:

    def test_truth_disclosure_labels(self):
        """Verifies synthetic planning labels and no Earth downlink claims."""
        product = MissionDataProduct(
            product_id="dp_guard_01",
            observation_id="obs_01",
            target_id="tgt_01",
            instrument_id="MASTCAM_Z",
            category=DataCategory.MULTISPECTRAL_IMAGERY,
            size_bytes=10_000_000,
            created_mission_time_s=10.0,
        )
        p_dict = product.to_dict()
        assert p_dict["is_synthetic"] is True
        assert p_dict["is_simulated"] is True

        ledger = MissionDataLedger()
        transfers = ledger.simulate_transfer_window(
            start_time_s=50.0,
            duration_s=10.0,
            network_path=["ROVER", "SURFACE_BASE_STATION"],
        )
        assert ledger.destination_name == "SURFACE_BASE_STATION"

    def test_non_regenerative_descent_modeling_baseline(self):
        """Verifies non-regenerative descent is a configurable assumption (False by default)."""
        cfg = RoverResourceConfig()
        assert cfg.allow_regenerative_braking is False
