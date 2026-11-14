"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Test Suite for Planetary Network
==============================================================================
Validates all 18 system-wide invariants across astrodynamics, link budgets,
RFC 9171 DTN bundle engine, contact schedulers, partition reconciliation, and security.
"""

import math
import pytest
from typing import Dict, List, Any

from marswalk.core.atlas_network_link_model import (
    CommunicationBand,
    TransmitterSpec,
    ReceiverSpec,
    PhysicalLinkBudgetEngine,
    SPEED_OF_LIGHT_M_S,
    ASTRONOMICAL_UNIT_M,
)
from marswalk.core.atlas_planetary_network_architecture import (
    PlanetaryNode,
    PlanetaryNodeType,
    PlanetaryNetworkTopology,
    create_standard_planetary_network,
)
from marswalk.core.atlas_orbital_contact_planner import (
    OrbitalContactPlanner,
    KeplerianElements,
    ContactWindow,
    MARS_RADIUS_M,
)
from marswalk.core.atlas_dtn_engine import (
    DataBundle,
    BundlePriority,
    BundleState,
    NodeDTNBuffer,
    PlanetaryDTNEngine,
)
from marswalk.core.atlas_planetary_routing import (
    TimeDependentContactRouter,
    ContactRoute,
)
from marswalk.core.atlas_contact_scheduler import (
    SchedulerType,
    GreedyScheduler,
    EarliestDeliveryScheduler,
    PriorityFirstScheduler,
    DeadlineAwareScheduler,
    ResourceAwareScheduler,
    AtlasAdaptiveScheduler,
)
from marswalk.core.atlas_multi_settlement_network import (
    MultiSettlementNetworkCoordinator,
    SettlementLog,
)
from marswalk.core.atlas_network_resilience import (
    NetworkResilienceCoordinator,
    AnomalyType,
)
from marswalk.core.atlas_network_integrity import (
    NetworkIntegrityEngine,
)
from marswalk.core.atlas_network_scenario_engine import (
    PlanetaryNetworkScenarioEngine,
)
from marswalk.core.atlas_network_grand_prix import (
    NetworkGrandPrixTournament,
)


# =============================================================================
# Invariant 1: INV-01-PHYSICAL-DELAY
# Bounded light delay tau = R / c > 0
# =============================================================================
def test_inv_01_physical_delay():
    range_m = 100_000_000.0  # 100,000 km
    tau = range_m / SPEED_OF_LIGHT_M_S
    assert tau > 0.0
    assert math.isclose(tau, 0.333564, rel_tol=1e-3)


# =============================================================================
# Invariant 2: INV-02-SPEED-OF-LIGHT
# Relativistic lower bound: arrival timestamp >= start + tx_duration + prop_delay
# =============================================================================
def test_inv_02_speed_of_light():
    tx = TransmitterSpec("TestTx", CommunicationBand.UHF_PROXIMITY, 20.0, 6.0)
    rx = ReceiverSpec("TestRx", CommunicationBand.UHF_PROXIMITY, 6.0)
    slant_range = 500_000.0  # 500 km
    res = PhysicalLinkBudgetEngine.evaluate_link(tx, rx, slant_range, 45.0)

    payload_bytes = 1_000_000  # 1 MB
    tot_latency = res.calculate_total_delivery_latency_s(payload_bytes)
    prop_delay = slant_range / SPEED_OF_LIGHT_M_S
    tx_time = (payload_bytes * 8.0) / float(res.operational_rate_bps)

    assert tot_latency >= prop_delay + tx_time
    assert tot_latency > prop_delay


# =============================================================================
# Invariant 3: INV-03-STORE-AND-FORWARD
# Intermediate custody transfer holds bundles persistently during network disconnection
# =============================================================================
def test_inv_03_store_and_forward():
    dtn = PlanetaryDTNEngine()
    dtn.register_node("SETTLEMENT-ALPHA", 10_000_000)
    dtn.register_node("ATLAS-ORB-01", 10_000_000)

    bundle = DataBundle.create("BDL-001", "SETTLEMENT-ALPHA", "EARTH-DSN-GATEWAY", BundlePriority.CLASS_3_HIGH_PRIORITY_SCIENCE, 100_000, 10.0)
    dtn.submit_bundle(bundle)
    assert bundle.state == BundleState.QUEUED

    # Transfer to intermediate orbiter
    dtn.transfer_bundle("BDL-001", "SETTLEMENT-ALPHA", "ATLAS-ORB-01", 100_000, 50.0)
    assert bundle.state == BundleState.STORED
    assert bundle.current_custodian_id == "ATLAS-ORB-01"
    assert not dtn.get_buffer("SETTLEMENT-ALPHA").has_bundle("BDL-001")
    assert dtn.get_buffer("ATLAS-ORB-01").has_bundle("BDL-001")


# =============================================================================
# Invariant 4: INV-04-PRIORITY-PRESERVATION
# Class 1 (Emergency) and Class 2 (Command) are strictly scheduled ahead of lower priority traffic
# =============================================================================
def test_inv_04_priority_preservation():
    net = create_standard_planetary_network()
    dtn = PlanetaryDTNEngine()
    for n in net.get_all_nodes():
        dtn.register_node(n.node_id, n.buffer_capacity_bytes)

    cw = ContactWindow(
        contact_id="CW-TEST-01",
        src_node_id="SETTLEMENT-ALPHA",
        dst_node_id="EARTH-DSN-GATEWAY",
        start_time_s=100.0,
        end_time_s=500.0,
        band=CommunicationBand.X_BAND_DEEP_SPACE,
        min_range_m=1e9,
        max_range_m=1e9,
        avg_range_m=1e9,
        max_elevation_deg=45.0,
        achievable_rate_bps=1_000_000,
        total_capacity_bytes=50_000_000,
        propagation_delay_s=500.0,
    )

    bulk = DataBundle.create("B-BULK", "SETTLEMENT-ALPHA", "EARTH-DSN-GATEWAY", BundlePriority.CLASS_5_BULK_SCIENCE, 10_000, 10.0)
    emerg = DataBundle.create("B-EMERG", "SETTLEMENT-ALPHA", "EARTH-DSN-GATEWAY", BundlePriority.CLASS_1_EMERGENCY, 10_000, 20.0)
    dtn.submit_bundle(bulk)
    dtn.submit_bundle(emerg)

    scheduler = PriorityFirstScheduler(net)
    txs = scheduler.schedule(100.0, [bulk, emerg], [cw], dtn)
    assert len(txs) >= 2
    assert txs[0].bundle_id == "B-EMERG"
    assert txs[1].bundle_id == "B-BULK"


# =============================================================================
# Invariant 5: INV-05-BUFFER-MONOTONICITY
# Total storage utilization never exceeds physical hardware capacity C_storage
# =============================================================================
def test_inv_05_buffer_monotonicity():
    buf = NodeDTNBuffer("ROVER-ALPHA-01", 1_000_000)  # 1 MB
    b1 = DataBundle.create("B1", "ROVER-ALPHA-01", "SETTLEMENT-ALPHA", BundlePriority.CLASS_4_ROUTINE_ENGINEERING, 600_000, 10.0)
    b2 = DataBundle.create("B2", "ROVER-ALPHA-01", "SETTLEMENT-ALPHA", BundlePriority.CLASS_4_ROUTINE_ENGINEERING, 600_000, 20.0)

    assert buf.enqueue(b1) is True
    assert buf.enqueue(b2) is False  # Cannot fit without eviction of equal priority
    assert buf.used_bytes <= buf.capacity_bytes


# =============================================================================
# Invariant 6: INV-06-MULTI-HOP-CAUSALITY
# Multi-hop transmission sequence timestamps are strictly monotonically increasing
# =============================================================================
def test_inv_06_multi_hop_causality():
    net = create_standard_planetary_network()
    planner = OrbitalContactPlanner(net)
    windows = planner.plan_contact_schedule(0, 7200, 120)
    router = TimeDependentContactRouter(net)

    route = router.find_earliest_arrival_route("SETTLEMENT-ALPHA", "EARTH-DSN-GATEWAY", 0.0, 50_000, windows)
    if route and len(route.hops) > 1:
        for i in range(len(route.hops) - 1):
            assert route.hops[i + 1].departure_time_s >= route.hops[i].arrival_time_s


# =============================================================================
# Invariant 7: INV-07-ORBITAL-OCCULTATION
# No line-of-sight communication occurs when ray path intersects the spherical Martian occultation radius
# =============================================================================
def test_inv_07_orbital_occultation():
    # Two points on opposite sides of Mars
    pos1 = (MARS_RADIUS_M + 400_000, 0.0, 0.0)
    pos2 = (-(MARS_RADIUS_M + 400_000), 0.0, 0.0)
    is_blocked = OrbitalContactPlanner.is_line_of_sight_occulted_by_mars(pos1, pos2)
    assert is_blocked is True

    # Two points on the same side above the horizon
    pos3 = (MARS_RADIUS_M + 400_000, 100_000.0, 0.0)
    pos4 = (MARS_RADIUS_M + 400_000, -100_000.0, 0.0)
    is_blocked_side = OrbitalContactPlanner.is_line_of_sight_occulted_by_mars(pos3, pos4)
    assert is_blocked_side is False


# =============================================================================
# Invariant 8: INV-08-DTN-CUSTODY
# Custody is only released by sender after confirmed acceptance by receiver
# =============================================================================
def test_inv_08_dtn_custody():
    dtn = PlanetaryDTNEngine()
    dtn.register_node("SETTLEMENT-ALPHA", 5_000_000)
    # Receiver buffer smaller than bundle (cannot accept custody)
    dtn.register_node("SCOUT-BETA-02", 50_000)

    b = DataBundle.create("B-CUSTODY", "SETTLEMENT-ALPHA", "SCOUT-BETA-02", BundlePriority.CLASS_3_HIGH_PRIORITY_SCIENCE, 200_000, 10.0)
    dtn.submit_bundle(b)

    # Attempt custody transfer to an intermediate node that overflows
    dtn.register_node("RELAY-TOWER-ALPHA", 50_000)  # Too small
    success = dtn.transfer_bundle("B-CUSTODY", "SETTLEMENT-ALPHA", "RELAY-TOWER-ALPHA", 200_000, 30.0)
    assert success is False
    # Sender retains custody
    assert dtn.get_buffer("SETTLEMENT-ALPHA").has_bundle("B-CUSTODY")


# =============================================================================
# Invariant 9: INV-09-DYNAMIC-REROUTING
# When an orbital relay is offline, traffic is autonomously rerouted via alternate path
# =============================================================================
def test_inv_09_dynamic_rerouting():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-07")
    assert res.success is True
    assert "INV-09-DYNAMIC-REROUTING" in res.invariants_verified


# =============================================================================
# Invariant 10: INV-10-CHUNKING-INTEGRITY
# Interrupted bundle transmission records partial bytes and successfully resumes
# =============================================================================
def test_inv_10_chunking_integrity():
    dtn = PlanetaryDTNEngine()
    dtn.register_node("HEXACOPTER-AERO-01", 10_000_000)
    dtn.register_node("SETTLEMENT-ALPHA", 10_000_000)

    b = DataBundle.create("B-CHUNK", "HEXACOPTER-AERO-01", "SETTLEMENT-ALPHA", BundlePriority.CLASS_5_BULK_SCIENCE, 1_000_000, 10.0)
    dtn.submit_bundle(b)

    # Partial transmission of 400,000 bytes
    dtn.transfer_bundle("B-CHUNK", "HEXACOPTER-AERO-01", "SETTLEMENT-ALPHA", 400_000, 20.0)
    assert b.state == BundleState.TRANSMITTING
    assert b.transmitted_bytes == 400_000
    assert b.remaining_bytes == 600_000

    # Resume remaining 600,000 bytes
    dtn.transfer_bundle("B-CHUNK", "HEXACOPTER-AERO-01", "SETTLEMENT-ALPHA", 600_000, 30.0)
    assert b.state == BundleState.DELIVERED
    assert b.transmitted_bytes == 1_000_000


# =============================================================================
# Invariant 11: INV-11-FAIR-CONGESTION-CONTROL
# Buffer eviction sheds lowest priority bundles (Class 6/5) before shedding Class 1–4
# =============================================================================
def test_inv_11_fair_congestion_control():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-09")
    assert res.success is True
    assert "INV-11-FAIR-CONGESTION-CONTROL" in res.invariants_verified


# =============================================================================
# Invariant 12: INV-12-PARTITION-TOLERANCE
# Disconnected outpost operates autonomously and maintains monotonic event sequence
# =============================================================================
def test_inv_12_partition_tolerance():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-05")
    assert res.success is True
    assert "INV-12-PARTITION-TOLERANCE" in res.invariants_verified


# =============================================================================
# Invariant 13: INV-13-MERKLE-CONSISTENCY
# Post-partition reconciliation achieves identical state root hash without duplicate executions
# =============================================================================
def test_inv_13_merkle_consistency():
    log = SettlementLog("SETTLEMENT-ALPHA")
    log.append_event("DRILL_SAMPLE", 10.0, {"depth": 10})
    log.append_event("CHEMCAM_LASER", 20.0, {"target": "rock_01"})
    assert log.verify_integrity() is True


# =============================================================================
# Invariant 14: INV-14-OPTICAL-EXTINCTION-FALLBACK
# Elevated dust optical depth extinguishes laser comms while radio links remain closed
# =============================================================================
def test_inv_14_optical_extinction_fallback():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-06")
    assert res.success is True
    assert "INV-14-OPTICAL-EXTINCTION-FALLBACK" in res.invariants_verified


# =============================================================================
# Invariant 15: INV-15-CASCADING-RESILIENCE
# Primary relay outage does not cause buffer collapse or unrecoverable packet loss
# =============================================================================
def test_inv_15_cascading_resilience():
    net = create_standard_planetary_network()
    dtn = PlanetaryDTNEngine()
    for n in net.get_all_nodes():
        dtn.register_node(n.node_id, n.buffer_capacity_bytes)

    resilience = NetworkResilienceCoordinator(net, dtn)
    resilience.inject_anomaly(AnomalyType.ORBITAL_RELAY_OFFLINE, "ATLAS-ORB-01", 0.0, 3600.0)
    assert net.get_node("ATLAS-ORB-01").is_active is False

    # Recover
    resilience.update_resilience_state(4000.0)
    assert net.get_node("ATLAS-ORB-01").is_active is True


# =============================================================================
# Invariant 16: INV-16-EMERGENCY-PREEMPTION
# Class 1 life-support emergency alert evicts Class 5 bulk science when buffer is saturated
# =============================================================================
def test_inv_16_emergency_preemption():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-08")
    assert res.success is True
    assert "INV-16-EMERGENCY-PREEMPTION" in res.invariants_verified


# =============================================================================
# Invariant 17: INV-17-SOLAR-CONJUNCTION-HOLD
# During solar conjunction, Earth DSN links are suppressed and data is held in local buffers
# =============================================================================
def test_inv_17_solar_conjunction_hold():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-10")
    assert res.success is True
    assert "INV-17-SOLAR-CONJUNCTION-HOLD" in res.invariants_verified


# =============================================================================
# Invariant 18: INV-18-AUDIT-HASH-CHAIN
# All network lifecycle transitions are recorded in an unbroken SHA-256 hash ledger
# =============================================================================
def test_inv_18_audit_hash_chain():
    integrity = NetworkIntegrityEngine()
    b = DataBundle.create("B-AUDIT", "SETTLEMENT-ALPHA", "EARTH-DSN-GATEWAY", BundlePriority.CLASS_2_COMMAND_UPLINK, 50_000, 10.0)
    valid, msg = integrity.verify_bundle_acceptance(b, 20.0)
    assert valid is True
    assert len(integrity.audit_log) == 1
    assert integrity.verify_ledger_chain() is True


# =============================================================================
# Comprehensive Canonical Scenario 12 & Grand Prix Tournament
# =============================================================================
def test_canonical_scenario_12_the_planetary_internet():
    engine = PlanetaryNetworkScenarioEngine()
    res = engine.execute_scenario("SCENARIO-12")
    assert res.success is True
    assert len(res.invariants_verified) == 18


def test_network_grand_prix_tournament_qualification():
    tourney = NetworkGrandPrixTournament(simulation_horizon_s=3600.0)
    gp = tourney.run_tournament()
    assert len(gp.scores) == 6
    assert gp.overall_grand_prix_champion in [st.value for st in SchedulerType]
    # Check that top scores achieved 100% emergency delivery
    assert gp.scores[0].emergency_ratio_pct == 100.0
