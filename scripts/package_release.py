#!/usr/bin/env python3
"""
Project MarsWalk 2.0 / Atlas — Official Release Candidate Packaging Engine
Produces outputs/releases/marswalk-v2.0.0-rc1.tar.gz with SHA-256 checksum.
"""

import hashlib
import os
import sys
import tarfile
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "releases")
RELEASE_NAME = sys.argv[1] if len(sys.argv) > 1 else "marswalk-v2.0.0-rc2"
ARCHIVE_PATH = os.path.join(OUTPUTS_DIR, f"{RELEASE_NAME}.tar.gz")
CHECKSUM_PATH = os.path.join(OUTPUTS_DIR, f"{RELEASE_NAME}.sha256")

# Directories and files to include in release archive
INCLUDE_DIRS = [
    "src",
    "web",
    "scripts",
    "tests",
    "docs",
    "submission",
    "data/catalogs",
    "data/manifests",
    "data/processed",
    "data/missions",
    "data/weather",
    "data/preferences",
    "data/environment",
]

INCLUDE_FILES = [
    "pyproject.toml",
    "requirements.txt",
    "requirements-lock.txt",
    "README.md",
    "AGENTS.md",
    "DATA_PROVENANCE_AND_LICENSES.md",
    "THIRD_PARTY_NOTICES.md",
    ".env.example",
    ".gitignore",
    "data/waypoints_jezero.json",
    "data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif",
    "data/raw/pds_places_best_tactical.csv",
    "data/raw/pds_three_forks_sample_drops.csv",
    "data/raw/nasa_m20_traverse.json",
    "data/raw/nasa_m20_waypoints.json",
]

EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".bak", ".tmp"}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".venv", "venv", ".git"}


def should_exclude(path: str) -> bool:
    parts = path.split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return True
    _, ext = os.path.splitext(path)
    if ext in EXCLUDE_EXTENSIONS or ".bak" in path or ext.startswith(".bak"):
        return True
    return False


def build_release_archive():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    print(f"Building Release Candidate Archive: {ARCHIVE_PATH}...")
    t0 = time.time()

    file_count = 0
    with tarfile.open(ARCHIVE_PATH, "w:gz") as tar:
        # Add directories
        for d in INCLUDE_DIRS:
            abs_d = os.path.join(PROJECT_ROOT, d)
            if not os.path.exists(abs_d):
                continue
            for root, dirs, files in os.walk(abs_d):
                # Filter directories in-place
                dirs[:] = [x for x in dirs if not should_exclude(x)]
                for f in files:
                    rel_f = os.path.relpath(os.path.join(root, f), PROJECT_ROOT)
                    if should_exclude(rel_f):
                        continue
                    arcname = os.path.join(RELEASE_NAME, rel_f)
                    tar.add(os.path.join(PROJECT_ROOT, rel_f), arcname=arcname)
                    file_count += 1

        # Add individual files
        for f in INCLUDE_FILES:
            abs_f = os.path.join(PROJECT_ROOT, f)
            if os.path.exists(abs_f):
                arcname = os.path.join(RELEASE_NAME, f)
                tar.add(abs_f, arcname=arcname)
                file_count += 1

    dt = time.time() - t0
    archive_size = os.path.getsize(ARCHIVE_PATH)

    # Calculate SHA-256
    hasher = hashlib.sha256()
    with open(ARCHIVE_PATH, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256_digest = hasher.hexdigest()

    with open(CHECKSUM_PATH, "w") as f:
        f.write(f"{sha256_digest}  {os.path.basename(ARCHIVE_PATH)}\n")

    print("\n=======================================================")
    print("RELEASE CANDIDATE PACKAGE CREATED SUCCESSFULLY")
    print("=======================================================")
    print(f"Archive:       {ARCHIVE_PATH}")
    print(f"Size:          {archive_size:,} bytes ({archive_size / (1024*1024):.2f} MB)")
    print(f"Files Packaged:{file_count}")
    print(f"SHA-256:       {sha256_digest}")
    print(f"Checksum File: {CHECKSUM_PATH}")
    print(f"Build Time:    {dt:.2f} seconds")
    print("=======================================================\n")

    # Verify archive integrity
    with tarfile.open(ARCHIVE_PATH, "r:gz") as tar:
        members = tar.getmembers()
        print(f"Integrity Check: Verified {len(members)} archived members without error.")


if __name__ == "__main__":
    build_release_archive()
