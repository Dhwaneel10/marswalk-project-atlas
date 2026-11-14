#!/usr/bin/env python3
"""
scripts/audit_api_security_fuzzing.py
MarsWalk 2.0 / Project Atlas — API Fuzzing, Concurrency, and Security Penetration Audit
"""

import sys
import json
import time
import urllib.request
import urllib.error
import concurrent.futures
import subprocess
from pathlib import Path

TARGET_PORT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3000
BASE_URL = f"http://127.0.0.1:{TARGET_PORT}"

audit_results = {
    "target_url": BASE_URL,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "fuzz_tests": [],
    "injection_tests": [],
    "path_traversal_tests": [],
    "concurrency_stress_test": {},
    "secret_leakage_audit": {},
    "all_passed": True,
}

def make_request(path, method="GET", payload=None, timeout=10.0, raw_data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    data = None
    if raw_data is not None:
        data = raw_data
    elif payload is not None:
        data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body, None
    except Exception as e:
        return 0, "", str(e)


def run_fuzz_tests():
    print(">>> [PHASE 1] Fuzzing Endpoints with Malformed / Negative Payloads...")
    test_cases = [
        # Endpoint, Method, Payload, Expected Code Range, Description
        ("/api/health", "GET", None, [200], "Health check responds 200"),
        ("/api/plan_route", "POST", {}, [400], "Empty payload rejected with 400"),
        ("/api/plan_route", "POST", {"start": [0, 0]}, [400], "Missing goal rejected with 400"),
        ("/api/plan_route", "POST", {"start": {"row": 99999, "col": 99999}, "goal": {"row": 0, "col": 0}}, [400], "Out of bounds start rejected with 400"),
        ("/api/plan_route", "POST", {"start": {"row": "nan", "col": "inf"}, "goal": {"row": 0, "col": 0}}, [400], "NaN/Inf strings rejected with 400"),
        ("/api/plan_route", "POST", {"start": {"row": 50, "col": 50}, "goal": {"row": 50, "col": 50}}, [400], "Identical start and goal rejected with 400"),
        ("/api/gauntlet", "POST", {}, [400], "Empty gauntlet payload rejected with 400"),
        ("/api/gauntlet", "POST", {"scenario": "nonexistent_apocalypse_999"}, [400], "Unknown gauntlet scenario rejected with 400"),
        ("/api/mission/optimize", "POST", {}, [400], "Empty mission optimize payload rejected with 400"),
        ("/api/mission/optimize", "POST", {"start": {"row": "bad", "col": 10}, "goal": {"row": 20, "col": 20}}, [400], "Malformed row coordinate rejected with 400"),
        ("/api/mission/replan", "POST", {}, [400], "Empty mission replan payload rejected with 400"),
        ("/api/pillars/terrain/inspect", "POST", {}, [400], "Empty terrain inspect rejected with 400"),
        ("/api/pillars/terrain/inspect", "POST", {"row": -100, "col": 99999}, [400], "Out of bounds terrain inspect rejected with 400"),
        ("/api/pillars/environment-meda/calibrate", "POST", {"optical_depth_tau": -5.0}, [400], "Negative optical depth rejected with 400"),
        ("/api/pillars/environment-meda/calibrate", "POST", {"air_temp_c": -350.0}, [400], "Sub-absolute-zero temperature rejected with 400"),
        ("/api/pillars/environment-meda/calibrate", "POST", {"pressure_pa": -100.0}, [400], "Negative atmospheric pressure rejected with 400"),
        ("/api/pillars/science-targets/plan", "POST", {"start_rc": "invalid"}, [400], "Invalid start_rc type rejected with 400"),
        ("/api/pillars/science-targets/plan", "POST", {"start_rc": [99999, 99999], "goal_rc": [50, 50]}, [400], "Out of bounds science start rejected with 400"),
        ("/api/pillars/rover-ground-truth", "GET", None, [200], "Rover PLACES query succeeds with 200"),
        ("/api/pillars/rover-ground-truth/query", "GET", None, [200], "Rover PLACES query filter succeeds with 200"),
        ("/api/pillars/science-targets", "GET", None, [200], "Science targets query succeeds with 200"),
        ("/api/pillars/environment-meda", "GET", None, [200], "MEDA observations query succeeds with 200"),
        ("/api/pillars/manifest", "GET", None, [200], "Pillars master manifest query succeeds with 200"),
    ]

    for path, method, payload, expected_codes, desc in test_cases:
        status, body, err = make_request(path, method, payload)
        passed = (status in expected_codes)
        if not passed:
            audit_results["all_passed"] = False
        audit_results["fuzz_tests"].append({
            "test": desc,
            "path": path,
            "method": method,
            "expected_status": expected_codes,
            "actual_status": status,
            "passed": passed,
            "error": err,
        })
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {desc} (Status: {status})")


def run_injection_tests():
    print("\n>>> [PHASE 2] Testing Injection Attacks & Path Traversal...")
    injection_payloads = [
        ("SQL Injection string in profile", {"profile": "balanced'; DROP TABLE missions; --", "start": [117, 157], "goal": [66, 128]}),
        ("Shell command injection in vehicle_mode", {"vehicle_mode": "$(whoami; rm -rf /)", "start": [117, 157], "goal": [66, 128]}),
        ("Path traversal in mission ID", None, "/api/missions/../../../../etc/passwd"),
        ("Script injection in scenario name", {"scenario": "<script>alert('XSS')</script>"}, "/api/gauntlet"),
    ]

    for desc, payload, *custom_path in injection_payloads:
        path = custom_path[0] if custom_path else "/api/plan_route"
        method = "GET" if payload is None else "POST"
        status, body, err = make_request(path, method, payload)
        # Injection attempts must NOT return 500 internal server error or execute code; they must return 400 or 404
        safe = (status in [400, 404, 405])
        # Also ensure /etc/passwd or root: is never leaked
        leaked = "root:" in body or "daemon:" in body
        passed = safe and not leaked
        if not passed:
            audit_results["all_passed"] = False
        audit_results["injection_tests"].append({
            "test": desc,
            "path": path,
            "status": status,
            "safe": safe,
            "leaked_sensitive_data": leaked,
            "passed": passed,
        })
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {desc} -> Safe: {safe}, Leaked: {leaked} (Status: {status})")


def run_concurrency_stress_test():
    print("\n>>> [PHASE 3] Concurrency Stress Testing (20 Parallel Requests)...")
    payload = {
        "start": {"row": 117, "col": 157},
        "goal": {"row": 66, "col": 128},
        "profile": "balanced",
    }
    
    concurrency_n = 20
    start_time = time.time()
    statuses = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_n) as executor:
        futures = [executor.submit(make_request, "/api/plan_route", "POST", payload, timeout=120.0) for _ in range(concurrency_n)]
        for f in concurrent.futures.as_completed(futures):
            status, _, err = f.result()
            statuses.append(status)

    duration = time.time() - start_time
    success_count = sum(1 for s in statuses if s == 200)
    passed = (success_count == concurrency_n)
    if not passed:
        audit_results["all_passed"] = False

    audit_results["concurrency_stress_test"] = {
        "total_requests": concurrency_n,
        "successful_requests": success_count,
        "statuses": statuses,
        "total_duration_s": round(duration, 3),
        "avg_latency_ms": round((duration / concurrency_n) * 1000.0, 1),
        "passed": passed,
    }
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] 20 concurrent requests completed in {duration:.2f}s ({success_count}/20 HTTP 200 OK)")


def run_secret_leakage_audit():
    print("\n>>> [PHASE 4] Secret Leakage & Hardcoded Credentials Audit...")
    import re
    project_root = Path(__file__).resolve().parent.parent
    regex_patterns = [
        re.compile(r"AWS_SECRET_ACCESS_KEY", re.IGNORECASE),
        re.compile(r"aws_secret_key", re.IGNORECASE),
        re.compile(r"BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY", re.IGNORECASE),
        re.compile(r"SECRET_KEY\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
        re.compile(r"api_key\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.IGNORECASE),
        re.compile(r"password\s*=\s*['\"][^'\"]{6,}['\"]", re.IGNORECASE),
    ]

    findings = []
    for dir_name in ["src", "web"]:
        scan_dir = project_root / dir_name
        for p in scan_dir.rglob("*"):
            if p.is_file() and p.suffix in [".py", ".js", ".html", ".css", ".json"]:
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    for line_no, line in enumerate(content.splitlines(), start=1):
                        for pat in regex_patterns:
                            if pat.search(line):
                                findings.append(f"{p.relative_to(project_root)}:{line_no}: {line.strip()[:80]}")
                except Exception:
                    pass

    passed = (len(findings) == 0)
    if not passed:
        audit_results["all_passed"] = False
    audit_results["secret_leakage_audit"] = {
        "searched_patterns": [p.pattern for p in regex_patterns],
        "findings_count": len(findings),
        "findings": findings[:10],
        "passed": passed,
    }
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] Secret scan completed. Hardcoded credentials found: {len(findings)}")


def main():
    print("========================================================================")
    print("  PROJECT ATLAS • MARSWALK 2.0 — API SECURITY & FUZZ AUDIT")
    print(f"  Target: {BASE_URL}")
    print("========================================================================")

    run_fuzz_tests()
    run_injection_tests()
    run_concurrency_stress_test()
    run_secret_leakage_audit()

    output_path = Path(__file__).resolve().parent.parent / "outputs" / "mission_10" / "benchmarks" / "api_security_fuzz_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)

    print("\n========================================================================")
    status_str = "PASSED (100% SECURE)" if audit_results["all_passed"] else "FAILED (DEFECTS DETECTED)"
    print(f"  API SECURITY & RESILIENCE AUDIT: {status_str}")
    print(f"  Report: {output_path}")
    print("========================================================================")
    sys.exit(0 if audit_results["all_passed"] else 1)

if __name__ == "__main__":
    main()
