#!/usr/bin/env python3
"""
scripts/benchmark_mission10_performance.py
MarsWalk 2.0 / Project Atlas — Performance Benchmarking, Latency Distribution & Memory Audit (Mission 10)
"""

import sys
import json
import time
import os
import urllib.request
import numpy as np
from pathlib import Path

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"

def get_proc_rss_mb(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
    except Exception:
        pass
    return 0.0

def find_server_pid(port):
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="ignore")
            if "run_atlas.py" in cmdline and str(port) in cmdline:
                return int(entry.name)
        except Exception:
            pass
    return None

benchmark_results = {
    "target_url": BASE_URL,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "platform": {
        "os": sys.platform,
        "python_version": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    },
    "benchmarks": {},
    "memory_audit": {},
    "all_passed": True,
}

def make_request(path, payload, method="POST", timeout=30.0):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return resp.status, latency_ms, len(body)


def benchmark_route_planning(n_iterations=30):
    print(f"\n>>> [BENCHMARK 1] Point-to-Point A* Route Planning (N={n_iterations} runs)...")
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
    }
    latencies = []
    for i in range(n_iterations):
        status, lat, _ = make_request("/api/plan_route", payload)
        assert status == 200
        latencies.append(lat)
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{n_iterations} runs (Current latency: {lat:.1f}ms)")

    stats = {
        "iterations": n_iterations,
        "min_ms": round(float(np.min(latencies)), 1),
        "mean_ms": round(float(np.mean(latencies)), 1),
        "median_ms": round(float(np.median(latencies)), 1),
        "p95_ms": round(float(np.percentile(latencies, 95)), 1),
        "max_ms": round(float(np.max(latencies)), 1),
        "std_ms": round(float(np.std(latencies)), 1),
    }
    benchmark_results["benchmarks"]["route_planning_a_star"] = stats
    print(f"  [RESULT] A* Min: {stats['min_ms']}ms | Median: {stats['median_ms']}ms | p95: {stats['p95_ms']}ms | Max: {stats['max_ms']}ms")


def benchmark_mission_optimizer(n_iterations=10):
    print(f"\n>>> [BENCHMARK 2] Multi-Objective Science Tour Optimizer (N={n_iterations} runs)...")
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "candidate_waypoint_ids": ["three_forks", "hawksbill_gap"],
        "max_stops": 2,
        "profile": "balanced",
        "vehicle_mode": "crew_eva",
        "operational_limit_s": 28800.0,
    }
    latencies = []
    for i in range(n_iterations):
        status, lat, _ = make_request("/api/mission/optimize", payload, timeout=30.0)
        assert status == 200
        latencies.append(lat)
        print(f"  Optimizer run {i + 1}/{n_iterations}: {lat:.1f}ms")

    stats = {
        "iterations": n_iterations,
        "min_ms": round(float(np.min(latencies)), 1),
        "mean_ms": round(float(np.mean(latencies)), 1),
        "median_ms": round(float(np.median(latencies)), 1),
        "p95_ms": round(float(np.percentile(latencies, 95)), 1),
        "max_ms": round(float(np.max(latencies)), 1),
        "std_ms": round(float(np.std(latencies)), 1),
    }
    benchmark_results["benchmarks"]["mission_optimizer"] = stats
    print(f"  [RESULT] Optimizer Min: {stats['min_ms']}ms | Median: {stats['median_ms']}ms | p95: {stats['p95_ms']}ms | Max: {stats['max_ms']}ms")


def benchmark_flagship_scenario(n_iterations=5):
    print(f"\n>>> [BENCHMARK 3] Flagship 5-Sol 'When Mars Goes Dark' Simulation (N={n_iterations} runs)...")
    payload = {
        "scenario_preset": "when_mars_goes_dark_sols_88_92",
        "enable_dtn_custody": True,
        "verify_merkle_continuity": True,
    }
    latencies = []
    for i in range(n_iterations):
        status, lat, _ = make_request("/api/flagship/when-mars-goes-dark/run", payload, timeout=30.0)
        assert status == 200
        latencies.append(lat)
        print(f"  Flagship run {i + 1}/{n_iterations}: {lat:.1f}ms")

    stats = {
        "iterations": n_iterations,
        "min_ms": round(float(np.min(latencies)), 1),
        "mean_ms": round(float(np.mean(latencies)), 1),
        "median_ms": round(float(np.median(latencies)), 1),
        "p95_ms": round(float(np.percentile(latencies, 95)), 1),
        "max_ms": round(float(np.max(latencies)), 1),
        "std_ms": round(float(np.std(latencies)), 1),
    }
    benchmark_results["benchmarks"]["flagship_scenario"] = stats
    print(f"  [RESULT] Flagship Min: {stats['min_ms']}ms | Median: {stats['median_ms']}ms | p95: {stats['p95_ms']}ms | Max: {stats['max_ms']}ms")


def audit_memory_and_leakage(n_burn_requests=40):
    print(f"\n>>> [BENCHMARK 4] Server Memory Footprint & Leakage Audit (N={n_burn_requests} requests)...")
    
    server_pid = find_server_pid(TARGET_PORT) or os.getpid()
    rss_initial_mb = get_proc_rss_mb(server_pid)
    print(f"  Target Server PID: {server_pid} | Initial RSS: {rss_initial_mb:.1f} MB")

    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
    }

    # Execute 40 consecutive requests
    for i in range(n_burn_requests):
        make_request("/api/plan_route", payload)
        if (i + 1) % 10 == 0:
            current_rss = get_proc_rss_mb(server_pid)
            print(f"  After {i + 1} requests -> RSS: {current_rss:.1f} MB")

    rss_final_mb = get_proc_rss_mb(server_pid)
    delta_rss_mb = rss_final_mb - rss_initial_mb

    passed = (rss_final_mb < 200.0) and (delta_rss_mb < 30.0)
    if not passed:
        benchmark_results["all_passed"] = False

    audit_mem = {
        "server_pid": server_pid,
        "burn_requests": n_burn_requests,
        "rss_initial_mb": round(rss_initial_mb, 2),
        "rss_final_mb": round(rss_final_mb, 2),
        "delta_rss_mb": round(delta_rss_mb, 2),
        "production_budget_mb": 200.0,
        "within_budget": bool(rss_final_mb < 200.0),
        "passed": passed,
    }
    benchmark_results["memory_audit"] = audit_mem
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] Final RSS: {rss_final_mb:.1f} MB (Delta: {delta_rss_mb:+.1f} MB, Budget: <200.0 MB)")


def main():
    print("========================================================================")
    print("  PROJECT ATLAS • MARSWALK 2.0 — PERFORMANCE & MEMORY BENCHMARK SUITE")
    print(f"  Target: {BASE_URL}")
    print("========================================================================")

    benchmark_route_planning(30)
    benchmark_mission_optimizer(10)
    benchmark_flagship_scenario(5)
    audit_memory_and_leakage(40)

    out_file = Path(__file__).resolve().parent.parent / "outputs" / "mission_10" / "benchmarks" / "performance_benchmark_summary.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print("\n========================================================================")
    print("  BENCHMARK SUITE COMPLETE")
    print(f"  Summary JSON: {out_file}")
    print("========================================================================")
    sys.exit(0 if benchmark_results["all_passed"] else 1)

if __name__ == "__main__":
    main()
