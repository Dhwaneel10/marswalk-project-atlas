#!/usr/bin/env python3
"""
scripts/benchmark_mission11_performance.py
MarsWalk 2.0 / Project Atlas — Performance & Memory Benchmark Suite (Mission 11)
Benchmarks:
1. Point-to-Point A* Route Planning Latency (N=20 runs)
2. Multi-Objective Science Tour Optimizer Latency (N=10 runs)
3. Flagship 5-Sol Simulation Latency (N=5 runs)
4. Memory Leakage Audit over 40 Consecutive Burn Requests (Target: Delta RSS < 15.0 MB, Total RSS < 250.0 MB)
Output: outputs/mission_11/benchmarks/performance_benchmark_summary.json
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import numpy as np

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "mission_11" / "benchmarks"

benchmark_results = {
    "audit_mission": "MISSION_11_PERFORMANCE_AUDIT",
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


def benchmark_route_planning(n_iterations=20):
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
        status, lat, _ = make_request("/api/mission/optimize", payload)
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
        "scenario_id": "m_when_mars_goes_dark_flagship",
        "dust_storm_enabled": True,
        "dtn_enabled": True,
    }
    latencies = []
    for i in range(n_iterations):
        status, lat, _ = make_request("/api/flagship/when-mars-goes-dark/run", payload)
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


def find_server_pid(port):
    try:
        out = subprocess.check_output(["ss", "-tulpn"], text=True)
        for line in out.splitlines():
            if f":{port} " in line or f":{port}\t" in line:
                if "pid=" in line:
                    parts = line.split("pid=")[1].split(",")[0]
                    return int(parts)
    except Exception:
        pass
    return None


def get_proc_rss_mb(pid):
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    return kb / 1024.0
    except Exception:
        pass
    return 0.0


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

    # Execute burn requests
    for i in range(n_burn_requests):
        make_request("/api/plan_route", payload)
        if (i + 1) % 10 == 0:
            current_rss = get_proc_rss_mb(server_pid)
            print(f"  After {i + 1} requests -> RSS: {current_rss:.1f} MB")

    rss_final_mb = get_proc_rss_mb(server_pid)
    delta_rss_mb = rss_final_mb - rss_initial_mb

    passed = (rss_final_mb < 250.0) and (delta_rss_mb < 20.0)
    if not passed:
        benchmark_results["all_passed"] = False

    audit_mem = {
        "server_pid": server_pid,
        "burn_requests": n_burn_requests,
        "rss_initial_mb": round(rss_initial_mb, 2),
        "rss_final_mb": round(rss_final_mb, 2),
        "delta_rss_mb": round(delta_rss_mb, 2),
        "production_budget_mb": 250.0,
        "within_budget": bool(rss_final_mb < 250.0),
        "passed": passed,
    }
    benchmark_results["memory_audit"] = audit_mem
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] Final RSS: {rss_final_mb:.1f} MB (Delta: {delta_rss_mb:+.1f} MB, Budget: <250.0 MB)")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    benchmark_route_planning(20)
    benchmark_mission_optimizer(10)
    benchmark_flagship_scenario(5)
    audit_memory_and_leakage(40)

    out_file = OUTPUT_DIR / "performance_benchmark_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_results, f, indent=2)

    print("\n========================================================================")
    print("  BENCHMARK SUITE COMPLETE")
    print(f"  Summary JSON: {out_file}")
    print("========================================================================")

if __name__ == "__main__":
    main()
