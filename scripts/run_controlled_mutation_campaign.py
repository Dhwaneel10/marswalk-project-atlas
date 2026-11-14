"""
MarsWalk 2.0 / Project Atlas — Milestone 13AB: Controlled Mutation Testing Harness
==================================================================================
Executes a real, controlled mutation campaign across 8 prioritized subsystems:
  1. Terrain distance calculation (Euclidean vs Manhattan distortion)
  2. RF link budget FSPL calculation (20*log10 vs 10*log10 power factor)
  3. DTN bundle expiration logic (is_expired inverted/bypassed)
  4. Autonomous command validation (expected state hash check removed)
  5. Construction material screening (tampered yield fraction / mass loss)
  6. Robot capability validation (capability class match bypassed)
  7. Quality inspection acceptance (crack/strength defect gate removed)
  8. Resource accounting / stock overdraft (negative inventory allowed)

Each mutation is applied temporarily to the live codebase, tested with pytest,
and immediately restored in a guaranteed finally block with SHA-256 verification.
"""

from dataclasses import dataclass
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Any


@dataclass
class MutationSpec:
    mutant_id: str
    subsystem: str
    file_path: str
    target_function: str
    description: str
    target_text: str
    replacement_text: str
    test_command: List[str]
    expected_failing_test: str


MUTANTS: List[MutationSpec] = [
    MutationSpec(
        mutant_id="MUT-01-TERRAIN-DISTANCE",
        subsystem="Terrain Geometry",
        file_path="src/marswalk/core/terrain.py",
        target_function="calculate_step_distance",
        description="Replace Euclidean ground metric with Manhattan metric (omits sqrt/squares).",
        target_text="return math.sqrt((dc * dx_ground_m) ** 2 + (dr * dy_ground_m) ** 2)",
        replacement_text="return (abs(dc) * dx_ground_m) + (abs(dr) * dy_ground_m)",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_test_quality.py", "-k", "differential_distance"],
        expected_failing_test="test_differential_distance_calculation_step_vs_euclidean_projection",
    ),
    MutationSpec(
        mutant_id="MUT-02-FSPL-POWER-FACTOR",
        subsystem="RF & Optical Link Budget",
        file_path="src/marswalk/core/atlas_network_link_model.py",
        target_function="calculate_free_space_path_loss",
        description="Halve path loss calculation from 20*log10 to 10*log10 (violating spherical wave physics).",
        target_text="return 20.0 * math.log10(ratio)",
        replacement_text="return 10.0 * math.log10(ratio)",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13ab_numerical_and_defect_closure.py", "-k", "exact_free_space"],
        expected_failing_test="test_analytical_exact_free_space_path_loss_value",
    ),
    MutationSpec(
        mutant_id="MUT-03-DTN-EXPIRATION",
        subsystem="Delay-Tolerant Networking",
        file_path="src/marswalk/core/atlas_dtn_engine.py",
        target_function="DataBundle.is_expired",
        description="Disable bundle TTL expiration check (stale bundles never expire).",
        target_text="return current_time_s > self.expiration_time_s",
        replacement_text="return False",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_test_quality.py", "-k", "stale_bundle"],
        expected_failing_test="test_mutation_detector_stale_bundle_expiration",
    ),
    MutationSpec(
        mutant_id="MUT-04-AUTONOMY-HASH-CHECK",
        subsystem="Autonomous Operations",
        file_path="src/marswalk/core/atlas_autonomous_operations.py",
        target_function="DeepSpaceAutonomyManager.process_uplinks_on_mars",
        description="Bypass Mars live state hash verification (allow executing stale Earth commands).",
        target_text="if cmd.expected_state_hash == current_mars_state_hash:",
        replacement_text="if True:  # MUTATION: Bypassed state hash check",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_adversarial.py", "-k", "stale_command"],
        expected_failing_test="test_adversarial_stale_command_rejection",
    ),
    MutationSpec(
        mutant_id="MUT-05-MASS-CONSERVATION",
        subsystem="ISRU Materials",
        file_path="src/marswalk/core/atlas_foundry_materials.py",
        target_function="MaterialSpecification.__post_init__",
        description="Tamper with regolith mass screening yield by artificially destroying 10% mass.",
        target_text="yield_fraction=0.82,  # 82% usable fines, 18% oversized cobbles/rejects\n        waste_fraction=0.18,",
        replacement_text="yield_fraction=0.82,  # 82% usable fines, 18% oversized cobbles/rejects\n        waste_fraction=0.08,  # MUTATION: Destroy 10% waste mass",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_test_quality.py", "-k", "mass_conservation"],
        expected_failing_test="test_property_mass_conservation_under_random_screening",
    ),
    MutationSpec(
        mutant_id="MUT-06-ROBOT-CAPABILITY",
        subsystem="Robotics & Automation",
        file_path="src/marswalk/core/atlas_foundry_robotics.py",
        target_function="IndustrialRobot.can_perform_task",
        description="Bypass robot class verification so any robot class can perform any architectural task.",
        target_text="if self.robot_class != required_class:\n            return False",
        replacement_text="pass  # MUTATION: Bypassed robot class check",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_test_quality.py", "-k", "capability_exclusion"],
        expected_failing_test="test_metamorphic_robot_capability_exclusion",
    ),
    MutationSpec(
        mutant_id="MUT-07-QUALITY-INSPECTION",
        subsystem="Foundry Quality Gate",
        file_path="src/marswalk/core/atlas_foundry_inspection.py",
        target_function="FoundryInspectionEngine.inspect_asset",
        description="Bypass compressive strength and roughness gates (accept defective structures unconditionally).",
        target_text="if strength_passed and roughness_passed and density_compliance >= 90.0:",
        replacement_text="if True:  # MUTATION: Bypassed inspection acceptance gate",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_adversarial.py", "-k", "quality_inspection"],
        expected_failing_test="test_adversarial_quality_inspection_critical_rejection",
    ),
    MutationSpec(
        mutant_id="MUT-08-RESOURCE-OVERDRAFT",
        subsystem="Resource Accounting",
        file_path="src/marswalk/core/atlas_foundry_materials.py",
        target_function="SettlementMaterialInventory.consume_stock",
        description="Remove stock availability check, permitting unbounded negative inventory balances.",
        target_text="if self.stocks_kg[category] < mass_kg:\n            return False  # Insufficient stock",
        replacement_text="pass  # MUTATION: Allow stock overdraft into negative balance",
        test_command=[sys.executable, "-m", "pytest", "-q", "tests/test_milestone_13aa_adversarial.py", "-k", "extreme_payload"],
        expected_failing_test="test_adversarial_extreme_payload_and_overdraft",
    ),
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_campaign():
    print("=" * 80)
    print("  PROJECT ATLAS — MILESTONE 13AB: CONTROLLED MUTATION TESTING CAMPAIGN")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Evaluating {len(MUTANTS)} targeted mutations across 8 high-risk subsystems...\n")

    results: List[Dict[str, Any]] = []
    total_mutants = len(MUTANTS)
    killed_count = 0

    for idx, spec in enumerate(MUTANTS, 1):
        print(f"[{idx}/{total_mutants}] Testing Mutant {spec.mutant_id} ({spec.subsystem})...")
        print(f"  Target File: {spec.file_path}")
        print(f"  Target Function: {spec.target_function}")
        print(f"  Defect: {spec.description}")

        with open(spec.file_path, "r", encoding="utf-8", newline="") as f:
            original_content = f.read()

        orig_hash = sha256_file(spec.file_path)

        if spec.target_text not in original_content:
            print(f"  ERROR: Target snippet not found in {spec.file_path}!")
            results.append({
                "mutant_id": spec.mutant_id,
                "subsystem": spec.subsystem,
                "status": "ERROR_SNIPPET_NOT_FOUND",
                "killed": False,
            })
            continue

        mutated_content = original_content.replace(spec.target_text, spec.replacement_text, 1)

        target_dir = os.path.dirname(spec.file_path)
        pycache_dir = os.path.join(target_dir, "__pycache__")

        t0 = time.time()
        try:
            # Purge cache before mutating
            if os.path.isdir(pycache_dir):
                for pyc in os.listdir(pycache_dir):
                    try:
                        os.remove(os.path.join(pycache_dir, pyc))
                    except OSError:
                        pass

            # Apply mutation
            with open(spec.file_path, "w", encoding="utf-8", newline="") as f:
                f.write(mutated_content)

            # Run test command
            proc = subprocess.run(
                spec.test_command,
                capture_output=True,
                text=True,
                cwd="."
            )
            elapsed = time.time() - t0

            # Exit code != 0 indicates test suite detected the defect and failed (KILLED)
            if proc.returncode != 0:
                status = "KILLED"
                killed_count += 1
                print(f"  ==> RESULT: [KILLED] Exit Code {proc.returncode} in {elapsed:.2f}s (Defect caught by {spec.expected_failing_test})")
            else:
                status = "SURVIVED"
                print(f"  ==> RESULT: [SURVIVED] Exit Code 0 in {elapsed:.2f}s (WARNING: Defect was NOT detected!)")

            results.append({
                "mutant_id": spec.mutant_id,
                "subsystem": spec.subsystem,
                "file_path": spec.file_path,
                "target_function": spec.target_function,
                "description": spec.description,
                "expected_failing_test": spec.expected_failing_test,
                "exit_code": proc.returncode,
                "status": status,
                "killed": (status == "KILLED"),
                "duration_seconds": round(elapsed, 3),
                "output_snippet": proc.stdout[:200].strip(),
            })

        finally:
            # Guarantee restoration
            with open(spec.file_path, "w", encoding="utf-8", newline="") as f:
                f.write(original_content)
            # Force mtime update and purge pycache to prevent stale bytecode
            now = time.time()
            try:
                os.utime(spec.file_path, (now, now))
            except OSError:
                pass
            if os.path.isdir(pycache_dir):
                for pyc in os.listdir(pycache_dir):
                    try:
                        os.remove(os.path.join(pycache_dir, pyc))
                    except OSError:
                        pass

            restored_hash = sha256_file(spec.file_path)
            assert restored_hash == orig_hash, f"CRITICAL: Failed to restore {spec.file_path} to original hash!"

    kill_rate_pct = round((killed_count / total_mutants) * 100.0, 2)
    print("\n" + "=" * 80)
    print(f"  MUTATION CAMPAIGN SUMMARY: {killed_count}/{total_mutants} KILLED ({kill_rate_pct}%)")
    print("=" * 80)

    output_manifest = {
        "milestone": "13AB",
        "campaign": "CONTROLLED_MUTATION_EVALUATION",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_mutants": total_mutants,
        "mutants_killed": killed_count,
        "mutants_survived": total_mutants - killed_count,
        "kill_rate_pct": kill_rate_pct,
        "results": results,
    }

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/13ab_mutation_campaign_results.json", "w", encoding="utf-8") as f:
        json.dump(output_manifest, f, indent=2)
    print("Detailed report saved to: outputs/13ab_mutation_campaign_results.json\n")


if __name__ == "__main__":
    run_campaign()
