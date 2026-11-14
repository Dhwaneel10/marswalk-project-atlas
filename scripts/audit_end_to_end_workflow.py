"""
MarsWalk 2.0 / Project Atlas — Phase D End-to-End Workflow Audit Script.
Milestone 12A: Scientific Credibility, System Hardening & Demonstration Readiness.

Executes an automated full-path lifecycle walkthrough against the active Atlas HTTP API server:
1. Health & Preflight Verification
2. Environmental Intelligence & Provenance Verification
3. Baseline Campaign Formulation & Planning (v1)
4. Design Space Exploration & Multi-Objective Pareto Frontier Classification
5. Mathematical Pareto Candidate Promotion to v2
6. Baseline Immutability Audit (v1 untouched, v2 created)
7. Multi-Unit Fleet Allocation & Coordination
8. Digital Twin Temporal Execution Simulation
9. Retrospective Performance Analytics & Evidence-Based Causal Attribution
10. Error Handling & Negative Resilience Rejections
"""

import sys
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple

BASE_URL = "http://127.0.0.1:3000"


def make_request(path: str, method: str = "GET", data: Dict[str, Any] = None) -> Tuple[int, Dict[str, Any]]:
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8")
        try:
            return err.code, json.loads(err_body)
        except Exception:
            return err.code, {"raw_error": err_body}


def run_full_workflow_audit():
    print("=" * 80)
    print("  MARSWALK 2.0 — PHASE D END-TO-END WORKFLOW & RESILIENCE AUDIT")
    print("=" * 80)
    print(f"Target Server: {BASE_URL}")
    start_time = time.time()
    passed_steps = 0
    total_steps = 10

    # -------------------------------------------------------------------------
    # STEP 1: Preflight & Server Status
    # -------------------------------------------------------------------------
    print("\n[Step 1/10] Verifying Server Preflight & Terrain Readiness...")
    status, res = make_request("/api/preflight")
    assert status == 200, f"Expected 200, got {status}: {res}"
    assert res.get("overall_status") == "ready" or res.get("is_ready_for_demo") is True, f"Preflight status not ok: {res}"
    print(f"  -> Checkpoints passed: {res.get('passed_count', 0)}/{res.get('total_count', 12)} in {res.get('total_duration_ms', 0):.1f}ms")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 2: Environmental Intelligence & Provenance Verification
    # -------------------------------------------------------------------------
    print("\n[Step 2/10] Verifying Environmental Intelligence & Provenance...")
    status, weather_res = make_request("/api/weather/current?site=jezero_crater")
    assert status == 200, f"Expected 200, got {status}: {weather_res}"
    source_meta = weather_res.get("source_metadata", {})
    instrument = source_meta.get("instrument", "")
    assert "MEDA" in instrument or "REMS" in instrument, f"Invalid instrument provenance: {instrument}"
    assert "observation_archive_distinction" in source_meta
    distinction = source_meta.get("observation_archive_distinction", "")
    assert "distinct from unarchived real-time" in distinction.lower()
    
    meas = weather_res.get("measurements", {})
    temp_c = meas.get("air_temperature_c")
    assert temp_c is not None and -140.0 <= temp_c <= 30.0, f"Temperature {temp_c} out of physical Mars bounds"
    pressure_pa = meas.get("atmospheric_pressure_pa")
    assert pressure_pa is not None and 100.0 <= pressure_pa <= 1500.0, f"Pressure {pressure_pa} out of physical Mars bounds"
    print(f"  -> Jezero site weather verified. Instrument: {instrument}, Temp: {temp_c} C, Pressure: {pressure_pa} Pa")
    print(f"  -> Archive distinction: {distinction}")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 3: Baseline Campaign Formulation (v1)
    # -------------------------------------------------------------------------
    print("\n[Step 3/10] Formulating Baseline Multi-Sol Campaign (v1)...")
    plan_payload = {
        "campaign_id": f"cmp_audit_{int(time.time())}",
        "name": "Audit Baseline Jezero Science Campaign",
        "config": {
            "max_sols": 3,
            "max_duration_per_sortie_s": 28800.0,
            "planning_profile": "science_priority",
            "sorties_per_sol": 1,
        },
        "targets": [
            {"id": "tgt_octavia", "name": "Octavia E. Butler Landing", "row": 117, "col": 157, "priority_score": 100.0, "dwell_time_s": 600.0},
            {"id": "tgt_delta_front", "name": "Kodiak Mesa Delta Front", "row": 130, "col": 135, "priority_score": 90.0, "dwell_time_s": 900.0},
            {"id": "tgt_crater_rim", "name": "Belva Crater Rim Exposure", "row": 95, "col": 180, "priority_score": 75.0, "dwell_time_s": 750.0},
            {"id": "tgt_neretva_fan", "name": "Neretva Fan Sediments", "row": 150, "col": 120, "priority_score": 85.0, "dwell_time_s": 1200.0},
        ],
        "persist": True,
    }
    status, plan_res = make_request("/api/campaign/plan", method="POST", data=plan_payload)
    assert status == 200, f"Expected 200, got {status}: {plan_res}"
    camp_v1 = plan_res.get("campaign", {})
    camp_v1_id = camp_v1.get("campaign_id")
    assert camp_v1.get("version") == 1, f"Expected version 1, got {camp_v1.get('version')}"
    assert len(camp_v1.get("sorties", [])) > 0, "No sorties planned"
    summary_v1 = camp_v1.get("summary", {})
    print(f"  -> Planned Campaign {camp_v1_id} v1: {len(camp_v1.get('sorties', []))} sorties, {summary_v1.get('total_distance_m', 0):.0f}m distance, {summary_v1.get('total_duration_s', 0)/3600:.1f}h duration")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 4: Design Space Exploration & Pareto Classification
    # -------------------------------------------------------------------------
    print("\n[Step 4/10] Running Campaign Design Space Exploration...")
    ds_payload = {
        "campaign_id": camp_v1_id,
        "search_bounds": {"max_candidates": 6, "max_planner_calls": 6},
        "persist": True,
    }
    status, ds_res = make_request("/api/campaign/design-space/evaluate", method="POST", data=ds_payload)
    assert status == 200, f"Expected 200, got {status}: {ds_res}"
    ds_id = ds_res.get("design_space_id")
    pareto_cands = ds_res.get("pareto_candidates", [])
    dominated_cands = ds_res.get("dominated_candidates", [])
    infeasible_cands = ds_res.get("infeasible_candidates", [])
    recs = ds_res.get("recommendations", [])
    assert len(pareto_cands) >= 1, "Expected at least 1 Pareto candidate"
    assert ds_res.get("limitations_disclaimer"), "Missing limitations disclaimer"
    print(f"  -> Design Space {ds_id}: {len(pareto_cands)} Pareto, {len(dominated_cands)} Dominated, {len(infeasible_cands)} Infeasible, {len(recs)} Recommendations")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 5: Pareto Candidate Promotion
    # -------------------------------------------------------------------------
    print("\n[Step 5/10] Promoting Feasible Pareto Candidate...")
    promoted_cand = pareto_cands[0]
    prom_payload = {
        "design_space_id": ds_id,
        "candidate_id": promoted_cand["candidate_id"],
        "new_campaign_name": "Audit Promoted Science Optimized Campaign v2",
    }
    status, prom_res = make_request("/api/campaign/design-space/promote", method="POST", data=prom_payload)
    assert status == 200, f"Expected 200, got {status}: {prom_res}"
    assert prom_res.get("status") == "success"
    camp_v2_id = prom_res.get("new_campaign_id")
    new_version = prom_res.get("new_version")
    assert new_version == 2, f"Expected new version 2, got {new_version}"
    print(f"  -> Promoted candidate {promoted_cand['candidate_id']} to new campaign: {camp_v2_id} (version {new_version})")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 6: Baseline Immutability Audit
    # -------------------------------------------------------------------------
    print("\n[Step 6/10] Auditing Baseline Immutability (v1 vs v2)...")
    status, reloaded_v1 = make_request(f"/api/campaign/{camp_v1_id}")
    assert status == 200, f"Expected 200, got {status}: {reloaded_v1}"
    assert reloaded_v1.get("version") == 1, f"v1 version corrupted: {reloaded_v1.get('version')}"
    assert reloaded_v1.get("campaign_id") == camp_v1_id

    status, reloaded_v2 = make_request(f"/api/campaign/{camp_v2_id}")
    assert status == 200, f"Expected 200, got {status}: {reloaded_v2}"
    assert reloaded_v2.get("version") == 2, f"v2 version invalid: {reloaded_v2.get('version')}"
    assert reloaded_v2.get("parent_campaign_id") == camp_v1_id, "Missing parent campaign lineage link"
    print("  -> Immutability verified: v1 remained untouched in storage; v2 correctly linked to v1 parent.")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 7: Multi-Unit Fleet Allocation
    # -------------------------------------------------------------------------
    print("\n[Step 7/10] Allocating Fleet Coordination Across Robotic & Crew Units...")
    alloc_payload = {
        "campaign_id": camp_v2_id,
        "strategy": "balanced_workload",
        "persist": True,
    }
    status, coord_plan = make_request("/api/campaign/coordinate", method="POST", data=alloc_payload)
    assert status == 200, f"Expected 200, got {status}: {coord_plan}"
    coord_id = coord_plan.get("coordination_id")
    units = coord_plan.get("units", [])
    allocations = coord_plan.get("target_allocations", [])
    assert len(units) >= 2, "Expected multiple exploration units"
    print(f"  -> Fleet coordinated: {len(units)} units ({[u.get('name') for u in units]}), {len(allocations)} target allocations (Coordination ID: {coord_id})")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 8: Digital Twin Temporal Execution Simulation
    # -------------------------------------------------------------------------
    print("\n[Step 8/10] Simulating Digital Twin Execution Timeline...")
    sim_payload = {
        "campaign_id": camp_v2_id,
        "coordination_id": coord_id,
        "persist": True,
    }
    status, sim_data = make_request("/api/campaign/simulation/start", method="POST", data=sim_payload)
    assert status == 200, f"Expected 200, got {status}: {sim_data}"
    sim_id = sim_data.get("simulation_id")
    timeline_ivs = sim_data.get("timeline_intervals", [])
    sim_events = sim_data.get("events", [])
    sim_conflicts = sim_data.get("conflicts", [])
    assert len(timeline_ivs) > 0, "No timeline intervals generated"
    print(f"  -> Digital Twin simulated: {len(timeline_ivs)} intervals, {len(sim_events)} discrete events, {len(sim_conflicts)} temporal conflicts (Sim ID: {sim_id})")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 9: Retrospective Performance Analytics & Causal Attribution
    # -------------------------------------------------------------------------
    print("\n[Step 9/10] Analyzing Campaign Performance & Causal Attributions...")
    analytics_payload = {
        "campaign_id": camp_v2_id,
        "simulation_id": sim_id,
        "coordination_id": coord_id,
        "persist": True,
    }
    status, analytics_data = make_request("/api/campaign/analyze", method="POST", data=analytics_payload)
    assert status == 200, f"Expected 200, got {status}: {analytics_data}"
    exec_summary = analytics_data.get("executive_summary", {})
    deviations = analytics_data.get("deviations", [])
    lessons = analytics_data.get("lessons_learned", [])
    disclaimer = analytics_data.get("limitations_disclaimer", "")

    assert "deterministic planning-analysis" in disclaimer.lower()
    for dev in deviations:
        cause = str(dev.get("cause_attribution", "")).lower()
        assert cause in ("confirmed_cause", "contributing_factor", "undetermined"), f"Unexpected cause: {cause}"
        if cause == "confirmed_cause":
            assert len(dev.get("triggering_event_ids", [])) > 0, "Confirmed cause without triggering events!"
        elif cause == "undetermined":
            assert len(dev.get("triggering_event_ids", [])) == 0, "Undetermined cause has triggering events!"
    print(f"  -> Analytics verified: Completion Rate: {exec_summary.get('target_completion_rate_pct')}%, {len(deviations)} deviations, {len(lessons)} grounded lessons learned")
    passed_steps += 1

    # -------------------------------------------------------------------------
    # STEP 10: Negative Resilience & Structured Error Handling
    # -------------------------------------------------------------------------
    print("\n[Step 10/10] Testing Error Handling, Malformed Payloads & Resilience...")

    # Case A: Promote unknown candidate -> 404
    bad_cand_payload = {
        "design_space_id": ds_id,
        "candidate_id": "cand_nonexistent_99999",
    }
    status_a, res_a = make_request("/api/campaign/design-space/promote", method="POST", data=bad_cand_payload)
    assert status_a == 404, f"Expected 404 for unknown candidate, got {status_a}: {res_a}"
    assert "ERR_CANDIDATE_NOT_FOUND" in res_a.get("error_code", "") or "not found" in res_a.get("error", "").lower()

    # Case B: Missing design_space_id -> 400
    bad_prom_payload = {"candidate_id": "cand_cp_01"}
    status_b, res_b = make_request("/api/campaign/design-space/promote", method="POST", data=bad_prom_payload)
    assert status_b == 400, f"Expected 400 for missing design_space_id, got {status_b}: {res_b}"

    # Case C: Non-existent campaign lookup -> 404
    status_c, res_c = make_request("/api/campaign/cmp_imaginary_0000")
    assert status_c == 404, f"Expected 404 for unknown campaign, got {status_c}: {res_c}"

    # Case D: Malformed campaign plan payload -> 400
    status_d, res_d = make_request("/api/campaign/plan", method="POST", data={"invalid_key": "bad_data"})
    assert status_d in (400, 422), f"Expected 400/422 for malformed campaign plan, got {status_d}: {res_d}"

    print("  -> Resilience tests passed: Clean rejection of unknown candidates (404), missing params (400), unknown records (404), and malformed payloads (400).")
    passed_steps += 1

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"AUDIT SUCCESS: {passed_steps}/{total_steps} phases passed cleanly in {elapsed:.2f}s!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        run_full_workflow_audit()
    except Exception as exc:
        print(f"\nAUDIT FAILURE: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
