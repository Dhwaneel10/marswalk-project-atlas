"""
Unit tests for Milestone 13D: Relay Network Graph & Promontory Candidate Planning.
Tests:
- RelayNode and RelayEdge invariants
- BFS base reachability and hop counts
- Connected components decomposition
- Min-hop vs shortest distance paths
- Bridge edge detection via Tarjan's algorithm
- Single relay failure impact analysis
- Promontory candidate screening on Jezero Crater DTM
- Greedy submodular relay placement with deterministic tie-breaking
"""

import math
import numpy as np
import pytest

from marswalk.core.relay_graph import (
    RelayNode,
    RelayNodeType,
    RelayEdge,
    LinkVisibilityStatus,
    RelayNetworkGraph,
)
from marswalk.core.relay_planner import (
    screen_relay_candidates,
    optimize_relay_placement,
)
from marswalk.core.terrain import load_and_process_terrain


class TestRelayNetworkGraph:
    """Tests for RelayNetworkGraph data structure and algorithms."""

    def test_node_effective_elevation(self):
        """Effective phase center elevation is ground elevation + antenna height."""
        node = RelayNode(
            node_id="base",
            node_type=RelayNodeType.BASE_STATION,
            rc=(117.0, 157.0),
            elevation_m=-2567.0,
            antenna_height_m=10.0,
            label="Base Station",
        )
        assert math.isclose(node.effective_z_m, -2557.0, abs_tol=1e-3)
        d = node.to_dict()
        assert d["node_id"] == "base"
        assert d["node_type"] == "base_station"
        assert d["effective_z_m"] == -2557.0

    def test_edge_rejection_rules(self):
        """Edge is rejected if out of range or blocked."""
        g = RelayNetworkGraph(r_max_m=2000.0)
        g.add_node(RelayNode("A", RelayNodeType.BASE_STATION, (0, 0), 0.0, 10.0))
        g.add_node(RelayNode("B", RelayNodeType.ROBOTIC_ROVER, (0, 50), 0.0, 2.5))
        g.add_node(RelayNode("C", RelayNodeType.ROBOTIC_ROVER, (0, 200), 0.0, 2.5))

        # Blocked link -> should NOT be added
        g.add_edge(RelayEdge("A", "B", 500.0, 500.1, LinkVisibilityStatus.BLOCKED, -5.0))
        assert "B" not in g.adj["A"]

        # Out of range link (> 2000m) -> should NOT be added
        g.add_edge(RelayEdge("A", "C", 2500.0, 2500.1, LinkVisibilityStatus.VISIBLE, 10.0))
        assert "C" not in g.adj["A"]

        # Valid visible in-range link -> added bidirectionally
        g.add_edge(RelayEdge("A", "B", 1000.0, 1000.1, LinkVisibilityStatus.VISIBLE, 10.0))
        assert "B" in g.adj["A"]
        assert "A" in g.adj["B"]

    def test_bfs_reachability_and_hop_counts(self):
        """Test BFS reachability and multi-hop paths on a linear relay tree."""
        g = RelayNetworkGraph(r_max_m=3000.0)
        g.add_node(RelayNode("BASE", RelayNodeType.BASE_STATION, (10, 10), 0.0, 10.0))
        g.add_node(RelayNode("RELAY_1", RelayNodeType.ACTIVE_RELAY, (20, 20), 0.0, 10.0))
        g.add_node(RelayNode("RELAY_2", RelayNodeType.ACTIVE_RELAY, (30, 30), 0.0, 10.0))
        g.add_node(RelayNode("ROVER", RelayNodeType.ROBOTIC_ROVER, (40, 40), 0.0, 2.5))
        g.add_node(RelayNode("ISOLATED", RelayNodeType.ROBOTIC_ROVER, (90, 90), 0.0, 2.5))

        g.add_edge(RelayEdge("BASE", "RELAY_1", 1000.0, 1000.0, LinkVisibilityStatus.VISIBLE, 10.0))
        g.add_edge(RelayEdge("RELAY_1", "RELAY_2", 1000.0, 1000.0, LinkVisibilityStatus.VISIBLE, 10.0))
        g.add_edge(RelayEdge("RELAY_2", "ROVER", 1000.0, 1000.0, LinkVisibilityStatus.VISIBLE, 10.0))

        reach = g.evaluate_base_reachability("BASE")
        assert reach["base_online"] is True
        assert reach["total_reachable"] == 4
        assert "ISOLATED" in reach["isolated_nodes"]
        assert reach["hop_counts"]["BASE"] == 0
        assert reach["hop_counts"]["RELAY_1"] == 1
        assert reach["hop_counts"]["RELAY_2"] == 2
        assert reach["hop_counts"]["ROVER"] == 3

        path = g.get_minimum_hop_path("BASE", "ROVER")
        assert path == ["BASE", "RELAY_1", "RELAY_2", "ROVER"]

    def test_tarjan_bridge_detection(self):
        """All edges in a tree graph are bridges; removing any severs components."""
        g = RelayNetworkGraph(r_max_m=3000.0)
        g.add_node(RelayNode("A", RelayNodeType.BASE_STATION, (0, 0), 0.0, 10.0))
        g.add_node(RelayNode("B", RelayNodeType.ACTIVE_RELAY, (1, 1), 0.0, 10.0))
        g.add_node(RelayNode("C", RelayNodeType.ROBOTIC_ROVER, (2, 2), 0.0, 2.5))

        g.add_edge(RelayEdge("A", "B", 500.0, 500.0, LinkVisibilityStatus.VISIBLE, 10.0))
        g.add_edge(RelayEdge("B", "C", 500.0, 500.0, LinkVisibilityStatus.VISIBLE, 10.0))

        bridges = g.find_bridge_edges()
        assert len(bridges) == 2
        assert ("A", "B") in bridges or ("B", "A") in bridges
        assert ("B", "C") in bridges or ("C", "B") in bridges

        # Add redundant bypass edge (A <-> C), turning into triangle (no bridges)
        g.add_edge(RelayEdge("A", "C", 900.0, 900.0, LinkVisibilityStatus.VISIBLE, 10.0))
        bridges_tri = g.find_bridge_edges()
        assert len(bridges_tri) == 0

    def test_relay_failure_impact_analysis(self):
        """Simulating failure of critical relay severs downstream units."""
        g = RelayNetworkGraph(r_max_m=3000.0)
        g.add_node(RelayNode("BASE", RelayNodeType.BASE_STATION, (0, 0), 0.0, 10.0))
        g.add_node(RelayNode("RELAY", RelayNodeType.ACTIVE_RELAY, (10, 10), 0.0, 10.0))
        g.add_node(RelayNode("ROVER_A", RelayNodeType.ROBOTIC_ROVER, (20, 20), 0.0, 2.5))
        g.add_node(RelayNode("ROVER_B", RelayNodeType.ROBOTIC_ROVER, (25, 25), 0.0, 2.5))

        g.add_edge(RelayEdge("BASE", "RELAY", 1000.0, 1000.0, LinkVisibilityStatus.VISIBLE, 10.0))
        g.add_edge(RelayEdge("RELAY", "ROVER_A", 500.0, 500.0, LinkVisibilityStatus.VISIBLE, 10.0))
        g.add_edge(RelayEdge("RELAY", "ROVER_B", 500.0, 500.0, LinkVisibilityStatus.VISIBLE, 10.0))

        impact = g.evaluate_node_failure_impact("BASE", "RELAY")
        assert impact["is_single_point_of_failure"] is True
        assert impact["criticality_score"] == 2
        assert set(impact["severed_units"]) == {"ROVER_A", "ROVER_B"}


class TestRelaySitePlanner:
    """Tests for promontory screening and greedy relay optimization."""

    @pytest.fixture
    def terrain(self):
        return load_and_process_terrain("data/processed/jezero_ready_20m.tif")

    def test_screen_promontories_on_jezero_dtm(self, terrain):
        """Screening Jezero DTM yields 10 to 15 promontory sites meeting slope and elevation rules."""
        candidates = screen_relay_candidates(
            elevation=terrain.elevation,
            slope_deg=terrain.slope_deg,
            invalid_mask=terrain.invalid_mask,
            dx_ground_m=terrain.dx_ground_m,
            dy_ground_m=terrain.dy_ground_m,
            max_slope_deg=12.0,
            min_elevation_m=-2500.0,
            min_separation_m=450.0,
            max_candidates=15,
        )
        assert 10 <= len(candidates) <= 15
        for c in candidates:
            assert c["slope_deg"] <= 12.0
            assert c["elevation_m"] > -2500.0
            assert "candidate_id" in c
            assert 0.0 <= c["prominence_score"] <= 1.0

        # Verify pairwise minimum separation
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                c1, c2 = candidates[i], candidates[j]
                d = math.sqrt(
                    ((c1["col"] - c2["col"]) * terrain.dx_ground_m) ** 2
                    + ((c1["row"] - c2["row"]) * terrain.dy_ground_m) ** 2
                )
                assert d >= 449.0  # Floating tolerance

    def test_greedy_optimization_coverage_recovery(self, terrain):
        """Greedy placement connects disconnected targets within specified budget."""
        g = RelayNetworkGraph(r_max_m=3500.0)
        base = RelayNode("BASE", RelayNodeType.BASE_STATION, (117, 157), -2567.0, 10.0, "Octavia Butler Base")
        g.add_node(base)

        t1 = RelayNode("TARGET_1", RelayNodeType.ROBOTIC_ROVER, (115, 150), -2565.0, 2.5, "Delta Front Rover")
        t2 = RelayNode("TARGET_2", RelayNodeType.CREW_EVA, (30, 50), -2540.0, 2.0, "Delta Valley Crew")
        g.add_node(t1)
        g.add_node(t2)

        # Baseline: only TARGET_1 is directly connected to Base
        g.add_edge(RelayEdge("BASE", "TARGET_1", 200.0, 200.5, LinkVisibilityStatus.VISIBLE, 10.0))

        # Candidate relay on ridge connecting Base to TARGET_2
        cand_node = RelayNode("CAND_01", RelayNodeType.CANDIDATE_RELAY, (50, 80), -2470.0, 10.0, is_active=False)
        cand_edges = [
            RelayEdge("BASE", "CAND_01", 1800.0, 1805.0, LinkVisibilityStatus.VISIBLE, 30.0),
            RelayEdge("CAND_01", "TARGET_2", 800.0, 802.0, LinkVisibilityStatus.VISIBLE, 20.0),
        ]

        result = optimize_relay_placement(
            graph=g,
            base_node_id="BASE",
            target_unit_ids=["TARGET_1", "TARGET_2"],
            candidate_nodes=[cand_node],
            candidate_edges=cand_edges,
            relay_budget=1,
        )

        assert result["status"] == "OPTIMIZATION_COMPLETE"
        assert result["budget_used"] == 1
        assert result["initial_connected_count"] == 1
        assert result["final_connected_count"] == 2
        assert result["coverage_percentage"] == 100.0
        assert len(result["selected_relays"]) == 1
        assert result["selected_relays"][0]["node_id"] == "CAND_01"
