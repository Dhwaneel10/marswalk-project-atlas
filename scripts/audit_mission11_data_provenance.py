#!/usr/bin/env python3
"""
MarsWalk 2.0 / Project Atlas — Mission 11 Complete Data Provenance & Cryptographic Audit
Analyzes all project data assets, classifies provenance, computes exact SHA-256,
and outputs complete data inventory and source hashes manifests.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Define directories to audit
AUDIT_DIRS = [
    PROJECT_ROOT / "data" / "raw",
    PROJECT_ROOT / "data" / "processed",
    PROJECT_ROOT / "data" / "catalogs",
    PROJECT_ROOT / "data" / "environment",
    PROJECT_ROOT / "data" / "manifests",
    PROJECT_ROOT / "data" / "weather",
    PROJECT_ROOT / "data" / "missions",
    PROJECT_ROOT / "data" / "cache",
    PROJECT_ROOT / "data" / "preferences",
    PROJECT_ROOT / "web" / "data",
    PROJECT_ROOT / "web" / "assets",
]

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def classify_file(rel_path: str, size: int) -> Dict[str, Any]:
    """
    Classify a file into its primary origin category, publisher, mission/spacecraft,
    instrument, coordinate reference system, and license.
    """
    p = rel_path.lower()
    
    # 1. USGS Astrogeology Science Center
    if "jez_ctx_b_soc_008" in p or "jezero_ready_20m" in p:
        return {
            "origin_class": "USGS_ASTROGEOLOGY",
            "primary_publisher": "USGS Astrogeology Science Center",
            "spacecraft_mission": "NASA Mars Reconnaissance Orbiter (MRO)",
            "instrument": "Context Camera (CTX)",
            "processing_lineage": "Raw NASA PDS stereo pairs -> USGS ISIS3/SOC cartographic photogrammetry -> 20m DTM (Fergason et al., 2020; DOI: 10.5066/P906QQT8)",
            "coordinate_system": "ESRI:103885 (Equirectangular, IAU 2000 Mars Sphere, R=3396190m)",
            "license": "Public Domain (US Government Work)",
            "data_type": "Digital Elevation Model (DEM) Raster"
        }
    if "hawksbill_1m" in p:
        return {
            "origin_class": "USGS_ASTROGEOLOGY",
            "primary_publisher": "USGS Astrogeology Science Center / NASA JPL",
            "spacecraft_mission": "NASA Mars Reconnaissance Orbiter (MRO)",
            "instrument": "High Resolution Imaging Science Experiment (HiRISE)",
            "processing_lineage": "MRO HiRISE stereo pairs -> USGS TRN photogrammetry mosaic -> 1m DTM (Bland et al., 2024; DOI: 10.5066/P13CPYYU)",
            "coordinate_system": "ESRI:103885 (Equirectangular, IAU 2000 Mars Sphere, R=3396190m)",
            "license": "Public Domain (US Government Work)",
            "data_type": "High-Resolution Digital Terrain Model (DTM)"
        }
    if "mars_nomenclature" in p or "mars_places" in p:
        return {
            "origin_class": "USGS_IAU_JOINT",
            "primary_publisher": "USGS Astrogeology Science Center / IAU WGPSN",
            "spacecraft_mission": "Multi-Mission Planetary Mapping",
            "instrument": "Gazetteer of Planetary Nomenclature",
            "processing_lineage": "IAU Working Group for Planetary System Nomenclature official feature database",
            "coordinate_system": "Planetocentric, positive East [0, 360]",
            "license": "Public Domain / Open Data",
            "data_type": "Planetary Feature Nomenclature Catalog"
        }
    if "mars_viking_color" in p or "mdim21" in p:
        return {
            "origin_class": "USGS_ASTROGEOLOGY",
            "primary_publisher": "USGS Astrogeology Science Center / NASA PDS",
            "spacecraft_mission": "NASA Viking 1 & 2 Orbiters",
            "instrument": "Visual Imaging Subsystem (VIS)",
            "processing_lineage": "Viking MDIM 2.1 global mosaic (Archinal et al., 2003)",
            "coordinate_system": "IAU Mars 2000 Sphere",
            "license": "Public Domain (US Government Work)",
            "data_type": "Global Basemap Texture"
        }

    # 2. NASA PDS / JPL (Raw or Calibrated)
    if "pds_places" in p or "perseverance_ground_truth" in p or "nasa_m20_traverse" in p or "nasa_m20_waypoints" in p or "perseverance_curated_waypoints" in p:
        return {
            "origin_class": "NASA_PDS_GEO",
            "primary_publisher": "NASA Planetary Data System (PDS) Geosciences Node / JPL",
            "spacecraft_mission": "NASA Mars 2020 Perseverance Rover",
            "instrument": "Rover Engineering / Tactical Localization (PLACES)",
            "processing_lineage": "Downlink telemetry -> JPL best_tactical solution -> PDS Rover Places archive bundle",
            "coordinate_system": "Site frame / IAU 2000 Planetocentric Lon/Lat",
            "license": "NASA Open Data Policy (Public Domain)",
            "data_type": "Rover Ground Truth Traverse & Waypoint Catalog"
        }
    if "three_forks" in p:
        return {
            "origin_class": "NASA_JPL_CACHING",
            "primary_publisher": "NASA Jet Propulsion Laboratory (JPL) / Mars Sample Return",
            "spacecraft_mission": "NASA Mars 2020 Perseverance Rover",
            "instrument": "Adaptive Caching Assembly (ACA) / Sample Caching System",
            "processing_lineage": "Mars 2020 Sample Depot Three Forks telemetry log -> PDS4 sample drop events",
            "coordinate_system": "IAU 2000 Planetocentric Easting/Northing",
            "license": "NASA Open Data Policy (Public Domain)",
            "data_type": "Sample Depot Tube Placement Catalog"
        }
    if "meda" in p and ("raw" in p or "calibrated" in p or "we__0010" in p or "derived" in p or "meda_environmental_observations" in p or "baseline_jezero_meda" in p):
        return {
            "origin_class": "NASA_PDS_ATM",
            "primary_publisher": "NASA Planetary Data System (PDS) Atmospheres Node / Centro de Astrobiología (CAB)",
            "spacecraft_mission": "NASA Mars 2020 Perseverance Rover",
            "instrument": "Mars Environmental Dynamics Analyzer (MEDA)",
            "processing_lineage": "PDS4 raw/calibrated telemetry (ATS, PS, TIRS, RHS, WS) -> Rodriguez-Manfredi et al. (2021)",
            "coordinate_system": "In-situ Surface Station (18.4447°N, 77.4508°E)",
            "license": "NASA Open Data Policy (Public Domain)",
            "data_type": "In-Situ Atmospheric Observations"
        }
    if "mcs" in p:
        return {
            "origin_class": "NASA_PDS_ATM",
            "primary_publisher": "NASA PDS Atmospheres Node / JPL",
            "spacecraft_mission": "NASA Mars Reconnaissance Orbiter (MRO)",
            "instrument": "Mars Climate Sounder (MCS)",
            "processing_lineage": "MRO MCS limb sounding radiometric profiles over Jezero Crater (Kleinböhl et al., 2009)",
            "coordinate_system": "Atmospheric vertical column profiles",
            "license": "NASA Open Data Policy (Public Domain)",
            "data_type": "Atmospheric Column Profiles"
        }
    if "geolocated_science_targets" in p or "sci_targets" in p:
        return {
            "origin_class": "NASA_SCIENCE_TEAM",
            "primary_publisher": "NASA Mars 2020 Science Team / Peer-Reviewed Astrobiology Publications",
            "spacecraft_mission": "NASA Mars 2020 Perseverance Rover",
            "instrument": "SHERLOC, PIXL, SuperCam, Mastcam-Z, RIMFAX, WATSON",
            "processing_lineage": "In-situ target characterization, rover tactical telemetry, Scheller et al. (2022)",
            "coordinate_system": "IAU 2000 Planetocentric East",
            "license": "NASA Open Data Policy / Academic Open Access",
            "data_type": "Science Target Geological Catalog"
        }

    # 3. International / European Planetary Research
    if "mcd" in p:
        return {
            "origin_class": "CNES_LMD_ESA",
            "primary_publisher": "Laboratoire de Météorologie Dynamique (LMD, CNRS/Sorbonne) / CNES / ESA",
            "spacecraft_mission": "Mars Climate Database (MCD v6.2) General Circulation Model (GCM)",
            "instrument": "Planetary Atmosphere Simulation & Climatology Assimilation",
            "processing_lineage": "LMD Martian Global Climate Model assimilated with multi-spacecraft observations (Forget et al.)",
            "coordinate_system": "Global Climatological Grid",
            "license": "Academic / Non-Commercial Research License",
            "data_type": "Planetary Climate Database Climatology"
        }

    # 4. Planetary Imagery Previews / Regional Context
    if "ctx_preview" in p or "ctx_regional" in p or "jezero_ctx_orthomosaic" in p:
        return {
            "origin_class": "DERIVED_CTX_MOSAIC",
            "primary_publisher": "USGS / NASA MRO Context Camera",
            "spacecraft_mission": "NASA Mars Reconnaissance Orbiter (MRO)",
            "instrument": "Context Camera (CTX)",
            "processing_lineage": "MRO CTX raw radiometrically calibrated bands -> Equirectangular projection tiles",
            "coordinate_system": "ESRI:103885",
            "license": "Public Domain (US Government Work)",
            "data_type": "Context Orthomosaic / Tile"
        }

    # 5. Application Baseline, Manifests, Configurations & Simulated Models
    if "manifest" in p:
        return {
            "origin_class": "APPLICATION_MANIFEST",
            "primary_publisher": "MarsWalk 2.0 / Project Atlas Engineering Team",
            "spacecraft_mission": "Data Integrity & Verification Framework",
            "instrument": "Cryptographic Hash & Lineage Registry",
            "processing_lineage": "Continuous verification and provenance compilation",
            "coordinate_system": "N/A",
            "license": "MIT License (Project MarsWalk)",
            "data_type": "Data Manifest & Registry"
        }
    if "mission_when_mars_goes_dark" in p or "baseline_" in p or "ablations" in p or "collocation" in p or "parameter_identifiability" in p:
        return {
            "origin_class": "SIMULATED_MODEL_PROXY",
            "primary_publisher": "MarsWalk 2.0 Scientific Modeling Group",
            "spacecraft_mission": "MarsWalk 2.0 Resilience Demonstrator",
            "instrument": "Discrete-Event Simulation / Parametric Heuristic Models",
            "processing_lineage": "Synthesized mission scenarios, dust storm tau spike heuristic (Sol 89 MEDA analogy), and RF dust extinction models",
            "coordinate_system": "Local Grid Coordinates (Jezero CTX raster rows/cols)",
            "license": "MIT License (Project MarsWalk)",
            "data_type": "Simulation Scenario & Parametric Model"
        }
    if "preferences" in p:
        return {
            "origin_class": "USER_CONFIGURATION",
            "primary_publisher": "MarsWalk 2.0 User Configuration",
            "spacecraft_mission": "MarsWalk 2.0",
            "instrument": "Operator Weight Preferences",
            "processing_lineage": "Interactive AI preference weighting profile",
            "coordinate_system": "N/A",
            "license": "MIT License",
            "data_type": "Configuration JSON"
        }
    if "waypoints_jezero.json" in p or "jezero_mission_data.json" in p or "mars_imagery_registry.json" in p:
        return {
            "origin_class": "DERIVED_APPLICATION_CATALOG",
            "primary_publisher": "MarsWalk 2.0 / Project Atlas",
            "spacecraft_mission": "Mars 2020 / USGS GIS Integration",
            "instrument": "Curated Mission Overlay",
            "processing_lineage": "Derived from authentic USGS CTX DEM and NASA PDS rover waypoints",
            "coordinate_system": "ESRI:103885",
            "license": "MIT License / Derived Public Domain",
            "data_type": "Application Mission Dataset"
        }

    # Fallback
    return {
        "origin_class": "OTHER_APPLICATION_DATA",
        "primary_publisher": "MarsWalk 2.0",
        "spacecraft_mission": "MarsWalk 2.0",
        "instrument": "Support Data",
        "processing_lineage": "Internal application asset",
        "coordinate_system": "N/A",
        "license": "MIT License",
        "data_type": "Data File"
    }


def main():
    print("=" * 80)
    print("  MARSWALK 2.0 • PROJECT ATLAS — MISSION 11 COMPREHENSIVE DATA AUDIT    ")
    print("=" * 80)

    found_files: List[Path] = []
    for d in AUDIT_DIRS:
        if d.exists():
            for root, _, files in os.walk(d):
                if "workspaces" in root or "__pycache__" in root:
                    continue
                for f in files:
                    if f.endswith(".pyc") or f.endswith(".bak") or f.endswith(".orig"):
                        continue
                    found_files.append(Path(root) / f)

    found_files = sorted(set(found_files))
    print(f"Total candidate data files discovered: {len(found_files)}\n")

    inventory: List[Dict[str, Any]] = []
    source_hashes: Dict[str, str] = {}
    
    class_stats: Dict[str, Dict[str, Any]] = {}
    total_bytes = 0

    for fp in found_files:
        rel_path = str(fp.relative_to(PROJECT_ROOT))
        size_bytes = fp.stat().st_size
        total_bytes += size_bytes
        sha256 = compute_sha256(fp)
        source_hashes[rel_path] = sha256

        meta = classify_file(rel_path, size_bytes)
        origin_class = meta["origin_class"]

        if origin_class not in class_stats:
            class_stats[origin_class] = {"count": 0, "bytes": 0}
        class_stats[origin_class]["count"] += 1
        class_stats[origin_class]["bytes"] += size_bytes

        record = {
            "path": rel_path,
            "filename": fp.name,
            "size_bytes": size_bytes,
            "sha256": sha256,
            **meta
        }
        inventory.append(record)

    # Calculate percentages
    origin_breakdown = {}
    for c, stats in sorted(class_stats.items()):
        count_pct = (stats["count"] / len(inventory)) * 100.0 if inventory else 0.0
        bytes_pct = (stats["bytes"] / total_bytes) * 100.0 if total_bytes else 0.0
        origin_breakdown[c] = {
            "file_count": stats["count"],
            "count_percentage": round(count_pct, 2),
            "size_bytes": stats["bytes"],
            "bytes_percentage": round(bytes_pct, 2)
        }

    # High-level roll-up: Pure NASA vs USGS vs International vs Simulated/Application
    rollup = {
        "NASA_PDS_AND_JPL": {
            "classes": ["NASA_PDS_GEO", "NASA_PDS_ATM", "NASA_JPL_CACHING", "NASA_SCIENCE_TEAM"],
            "count": 0, "bytes": 0
        },
        "USGS_ASTROGEOLOGY_AND_IAU": {
            "classes": ["USGS_ASTROGEOLOGY", "USGS_IAU_JOINT", "DERIVED_CTX_MOSAIC"],
            "count": 0, "bytes": 0
        },
        "INTERNATIONAL_PARTNERS_CNES_LMD_ESA": {
            "classes": ["CNES_LMD_ESA"],
            "count": 0, "bytes": 0
        },
        "APPLICATION_DERIVED_AND_SIMULATED_MODELS": {
            "classes": ["APPLICATION_MANIFEST", "SIMULATED_MODEL_PROXY", "DERIVED_APPLICATION_CATALOG", "USER_CONFIGURATION", "OTHER_APPLICATION_DATA"],
            "count": 0, "bytes": 0
        }
    }

    for c, stats in class_stats.items():
        matched = False
        for r_name, r_data in rollup.items():
            if c in r_data["classes"]:
                r_data["count"] += stats["count"]
                r_data["bytes"] += stats["bytes"]
                matched = True
                break

    for r_name, r_data in rollup.items():
        r_data["count_pct"] = round((r_data["count"] / len(inventory)) * 100.0, 2)
        r_data["bytes_pct"] = round((r_data["bytes"] / total_bytes) * 100.0, 2)

    master_inventory_doc = {
        "manifest_version": "3.0.0",
        "audit_mission": "MISSION_11_CHALLENGE_VALIDATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_files": len(inventory),
        "total_bytes": total_bytes,
        "total_megabytes": round(total_bytes / (1024 * 1024), 2),
        "rollup_provenance_summary": rollup,
        "origin_class_breakdown": origin_breakdown,
        "files": inventory
    }

    # Write manifests
    out_inventory_path = PROJECT_ROOT / "data" / "manifests" / "mission11_complete_data_inventory.json"
    out_hashes_path = PROJECT_ROOT / "data" / "manifests" / "mission11_source_hashes.json"

    with open(out_inventory_path, "w", encoding="utf-8") as f:
        json.dump(master_inventory_doc, f, indent=2)

    with open(out_hashes_path, "w", encoding="utf-8") as f:
        json.dump(source_hashes, f, indent=2)

    print("--- SUMMARY AUDIT ROLLUP ---")
    print(f"Total data volume: {master_inventory_doc['total_megabytes']} MB across {len(inventory)} files\n")
    for r_name, r_data in rollup.items():
        print(f"  {r_name:<42} : {r_data['count']:2d} files ({r_data['count_pct']:5.1f}%) | {r_data['bytes']/(1024*1024):6.2f} MB ({r_data['bytes_pct']:5.1f}%)")

    print("\nManifests generated:")
    print(f"  - {out_inventory_path}")
    print(f"  - {out_hashes_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
