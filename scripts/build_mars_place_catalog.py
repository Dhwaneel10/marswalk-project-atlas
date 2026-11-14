"""
MarsWalk 2.0 — Mars Planetary Nomenclature & Exploration Place Catalog Generator.
Ingests official USGS / IAU Working Group for Planetary System Nomenclature (WGPSN) GIS data
and merges verified robotic landing site records from NASA PDS mission telemetry.

Outputs:
  web/data/mars_places.json
"""

import os
import sys
import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_KML = os.path.join(PROJECT_ROOT, "data", "raw", "MARS_nomenclature_center_pts.kml")
OUT_JSON = os.path.join(PROJECT_ROOT, "web", "data", "mars_places.json")
OUT_PUBLIC_JSON = os.path.join(PROJECT_ROOT, "web", "public", "data", "mars_places.json")


# High-priority globally iconic Martian landmarks (Tier 1 Global visibility)
GLOBAL_LANDMARK_NAMES = {
    # Giant Shield Volcanoes
    "Olympus Mons",
    "Ascraeus Mons",
    "Pavonis Mons",
    "Arsia Mons",
    "Elysium Mons",
    "Alba Mons",
    "Hecates Tholus",
    "Tharsis Tholus",
    # Giant Canyons & Valleys
    "Valles Marineris",
    "Coprates Chasma",
    "Melas Chasma",
    "Candor Chasma",
    "Ophir Chasma",
    "Kasei Valles",
    "Ares Vallis",
    "Ma'adim Vallis",
    # Major Basins & Plains
    "Hellas Planitia",
    "Argyre Planitia",
    "Isidis Planitia",
    "Utopia Planitia",
    "Acidalia Planitia",
    "Amazonis Planitia",
    "Elysium Planitia",
    "Chryse Planitia",
    # Large Terrae & Plateaus
    "Arabia Terra",
    "Terra Sabaea",
    "Noachis Terra",
    "Tharsis",
    "Syrtis Major Planum",
    # Polar Caps
    "Planum Boreum",
    "Planum Australe",
    # Notable Science Craters
    "Jezero",
    "Gale",
    "Gusev",
    "Victoria",
    "Endeavour",
    "Schiaparelli",
    "Huygens",
    "Cassini",
    "Korolev",
}

# Verified Robotic Landing Sites (NASA PDS / Mission Operations & CNSA)
VERIFIED_LANDING_SITES: List[Dict[str, Any]] = [
    {
        "id": "landing_perseverance",
        "name": "Perseverance Rover (Octavia E. Butler Landing)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 18.4447,
        "lon_deg": 77.4509,
        "center_lon_360": 77.4509,
        "diameter_km": None,
        "elevation_approx_m": -2570.0,
        "landing_date": "2021-02-18",
        "agency": "NASA / JPL-Caltech",
        "mission": "Mars 2020",
        "host_feature": "Jezero Crater",
        "description": "Touching down in Jezero Crater near the ancient river delta, investigating habitable environments and caching rock cores.",
        "pds_citation": "NASA Mars 2020 Mission Telemetry / PDS Geosciences Node (2021)",
        "dataset_attribution": "NASA / JPL-Caltech Mars 2020 Telemetry",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_curiosity",
        "name": "Curiosity Rover (Bradbury Landing)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": -4.5895,
        "lon_deg": 137.4416,
        "center_lon_360": 137.4416,
        "diameter_km": None,
        "elevation_approx_m": -4501.0,
        "landing_date": "2012-08-06",
        "agency": "NASA / JPL-Caltech",
        "mission": "Mars Science Laboratory (MSL)",
        "host_feature": "Gale Crater",
        "description": "Landed inside Gale Crater exploring Mount Sharp (Aeolis Mons) strata to understand ancient lakebed habitability.",
        "pds_citation": "NASA PDS MSL Navigation Archive (2012)",
        "dataset_attribution": "NASA / JPL MSL Navigation Team",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_insight",
        "name": "InSight Lander",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 4.5024,
        "lon_deg": 135.6234,
        "center_lon_360": 135.6234,
        "diameter_km": None,
        "elevation_approx_m": -2613.0,
        "landing_date": "2018-11-26",
        "agency": "NASA / JPL-Caltech / CNES / DLR",
        "mission": "InSight (Interior Exploration using Seismic Investigations)",
        "host_feature": "Elysium Planitia",
        "description": "Geophysical lander placed SEIS seismometer on smooth volcanic plain to measure Marsquakes and core structure.",
        "pds_citation": "Golombek et al., Space Sci Rev (2020)",
        "dataset_attribution": "NASA InSight Science Team / PDS Geosciences",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_spirit",
        "name": "Spirit Rover (Columbia Memorial Station)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": -14.5684,
        "lon_deg": 175.4784,
        "center_lon_360": 175.4784,
        "diameter_km": None,
        "elevation_approx_m": -1930.0,
        "landing_date": "2004-01-04",
        "agency": "NASA / JPL-Caltech",
        "mission": "Mars Exploration Rover A (MER-A)",
        "host_feature": "Gusev Crater",
        "description": "Explored basaltic plains and the Columbia Hills in Gusev Crater, finding silica deposits indicative of ancient hydrothermal activity.",
        "pds_citation": "NASA PDS MER Navigation Data (2004)",
        "dataset_attribution": "NASA MER Science Team / PDS",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_opportunity",
        "name": "Opportunity Rover (Challenger Memorial Station)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": -1.9462,
        "lon_deg": -5.5258,
        "center_lon_360": 354.4742,
        "diameter_km": None,
        "elevation_approx_m": -1440.0,
        "landing_date": "2004-01-25",
        "agency": "NASA / JPL-Caltech",
        "mission": "Mars Exploration Rover B (MER-B)",
        "host_feature": "Meridiani Planum (Eagle Crater)",
        "description": "Hole-in-one landing in Eagle Crater on hematite-rich plains, discovering hematite blueberries and ancient acid-water sediments.",
        "pds_citation": "NASA PDS MER Navigation Data (2004)",
        "dataset_attribution": "NASA MER Science Team / PDS",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_phoenix",
        "name": "Phoenix Mars Lander",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 68.2188,
        "lon_deg": -125.7492,
        "center_lon_360": 234.2508,
        "diameter_km": None,
        "elevation_approx_m": -4120.0,
        "landing_date": "2008-05-25",
        "agency": "NASA / University of Arizona",
        "mission": "Mars Scout Program (Phoenix)",
        "host_feature": "Vastitas Borealis (Green Valley)",
        "description": "Arctic plain lander that trenched polygon terrain, exposing subsurface pure water-ice and perchlorates.",
        "pds_citation": "NASA PDS Phoenix Mission Archive (2008)",
        "dataset_attribution": "NASA / UA Phoenix Mission Team",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_viking1",
        "name": "Viking 1 Lander (Thomas Mutch Memorial Station)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 22.48,
        "lon_deg": -47.95,
        "center_lon_360": 312.05,
        "diameter_km": None,
        "elevation_approx_m": -2690.0,
        "landing_date": "1976-07-20",
        "agency": "NASA / Langley Research Center",
        "mission": "Viking 1",
        "host_feature": "Chryse Planitia",
        "description": "First successful US Mars landing; operated for over six years conducting soil biology experiments and imaging.",
        "pds_citation": "NASA PDS Viking Lander Archive (1976)",
        "dataset_attribution": "NASA Viking Project Team",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_viking2",
        "name": "Viking 2 Lander (Gerald Soffen Memorial Station)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 47.97,
        "lon_deg": 134.28,
        "center_lon_360": 134.28,
        "diameter_km": None,
        "elevation_approx_m": -4230.0,
        "landing_date": "1976-09-03",
        "agency": "NASA / Langley Research Center",
        "mission": "Viking 2",
        "host_feature": "Utopia Planitia",
        "description": "Northern boulder-strewn plain landing; operated seismometer and analyzed frost condensation.",
        "pds_citation": "NASA PDS Viking Lander Archive (1976)",
        "dataset_attribution": "NASA Viking Project Team",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_pathfinder",
        "name": "Mars Pathfinder & Sojourner (Carl Sagan Station)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 19.33,
        "lon_deg": -33.55,
        "center_lon_360": 326.45,
        "diameter_km": None,
        "elevation_approx_m": -3680.0,
        "landing_date": "1997-07-04",
        "agency": "NASA / JPL-Caltech",
        "mission": "Discovery Program (Mars Pathfinder)",
        "host_feature": "Ares Vallis",
        "description": "Cataclysmic outflow floodplain landing, deploying Sojourner, the first wheeled micro-rover on another planet.",
        "pds_citation": "NASA PDS Mars Pathfinder Archive (1997)",
        "dataset_attribution": "NASA / JPL Mars Pathfinder Team",
        "is_landing_site": True,
        "importance_tier": 1,
    },
    {
        "id": "landing_zhurong",
        "name": "Zhurong Rover (Tianwen-1 Lander)",
        "feature_type": "Robotic Mission Landing Site",
        "category": "mission_site",
        "lat_deg": 25.066,
        "lon_deg": 109.925,
        "center_lon_360": 109.925,
        "diameter_km": None,
        "elevation_approx_m": -4100.0,
        "landing_date": "2021-05-15",
        "agency": "CNSA (China National Space Administration)",
        "mission": "Tianwen-1",
        "host_feature": "Southern Utopia Planitia",
        "description": "Subsurface radar exploration across southern Utopia Planitia investigating paleo-oceanic sedimentary structures.",
        "pds_citation": "Liu et al., Nature Geoscience (2022)",
        "dataset_attribution": "CNSA Tianwen-1 Ground Application System",
        "is_landing_site": True,
        "importance_tier": 1,
    },
]


def normalize_category(raw_type: str) -> str:
    """Classify IAU Gazetteer feature type into high-level cartographic categories."""
    t = raw_type.lower()
    if "mons" in t or "tholus" in t or "patera" in t:
        return "volcano"
    if "vallis" in t or "chasma" in t or "fossa" in t or "sulci" in t or "catena" in t:
        return "canyon"
    if "crater" in t:
        return "crater"
    if "planitia" in t or "planum" in t or "vastitas" in t:
        return "plain"
    if "terra" in t or "regio" in t:
        return "region"
    if "chaos" in t:
        return "chaos"
    if "mensa" in t or "dorsum" in t or "colles" in t:
        return "ridge"
    return "other"


def normalize_lon_deg(center_lon_360: float) -> float:
    """Normalize 0..360 East longitude into -180..+180 planetocentric degrees."""
    lon = center_lon_360 % 360.0
    if lon > 180.0:
        lon -= 360.0
    return round(lon, 4)


def parse_usgs_gazetteer(kml_path: str) -> List[Dict[str, Any]]:
    """Parse USGS IAU nomenclature KML file into structured records."""
    if not os.path.exists(kml_path):
        raise FileNotFoundError(f"Gazetteer KML file not found: {kml_path}")

    tree = ET.parse(kml_path)
    root = tree.getroot()

    places: List[Dict[str, Any]] = []

    for placemark in root.iter():
        if not placemark.tag.endswith("Placemark"):
            continue

        data: Dict[str, str] = {}
        for sd in placemark.iter():
            if sd.tag.endswith("SimpleData"):
                attr_name = sd.attrib.get("name")
                if attr_name and sd.text:
                    data[attr_name] = sd.text.strip()

        name = data.get("clean_name")
        if not name:
            continue

        # Extract stable feature ID from link
        link = data.get("link", "")
        m = re.search(r"Feature/(\d+)", link)
        fid = f"iau_{m.group(1)}" if m else f"iau_{re.sub(r'[^a-zA-Z0-9]', '_', name).lower()}"

        try:
            c_lat = float(data.get("center_lat", 0.0))
            c_lon = float(data.get("center_lon", 0.0))
        except (ValueError, TypeError):
            continue

        diam_str = data.get("diameter", "0.0")
        try:
            diameter_km = round(float(diam_str), 1) if float(diam_str) > 0.0 else None
        except ValueError:
            diameter_km = None

        raw_type = data.get("type", "Feature")
        category = normalize_category(raw_type)
        lon_180 = normalize_lon_deg(c_lon)

        # Importance Tier Assignment:
        # Tier 1 (Global): Global landmark names, giant features (diam > 500km), or major mons/chasma
        # Tier 2 (Regional): Large craters/plains (diam > 120km)
        # Tier 3 (Local): All other named features
        is_global = name in GLOBAL_LANDMARK_NAMES or (diameter_km is not None and diameter_km >= 600.0)
        is_regional = (
            not is_global
            and (
                category in ("volcano", "canyon")
                or (diameter_km is not None and diameter_km >= 100.0)
                or category in ("plain", "region", "chaos")
            )
        )

        tier = 1 if is_global else (2 if is_regional else 3)

        origin = data.get("origin", "")
        # Clean up any non-ascii artifacts
        origin = re.sub(r"\s+", " ", origin)

        places.append({
            "id": fid,
            "name": name,
            "feature_type": raw_type,
            "category": category,
            "lat_deg": round(c_lat, 4),
            "lon_deg": lon_180,
            "center_lon_360": round(c_lon, 4),
            "diameter_km": diameter_km,
            "elevation_approx_m": None,
            "origin": origin,
            "approval": data.get("approval", "Adopted by IAU"),
            "approval_date": data.get("approvaldt", "")[:10] if data.get("approvaldt") else "",
            "quad_name": data.get("quad_name", ""),
            "usgs_link": link,
            "dataset_attribution": "USGS Gazetteer of Planetary Nomenclature / IAU WGPSN",
            "is_landing_site": False,
            "importance_tier": tier,
        })

    return places


def build_catalog(
    kml_path: str = RAW_KML,
    output_path: str = OUT_JSON,
    output_public_path: str = OUT_PUBLIC_JSON,
) -> Dict[str, Any]:
    """Build and export unified Mars place catalog."""
    print(f"[MarsWalk Catalog] Parsing USGS Gazetteer: {kml_path}...")
    gazetteer_places = parse_usgs_gazetteer(kml_path)
    print(f"[MarsWalk Catalog] Extracted {len(gazetteer_places)} authoritative USGS/IAU features.")

    # Deduplicate / merge landing sites
    # Ensure landing sites are placed first as Tier 1
    all_places: List[Dict[str, Any]] = list(VERIFIED_LANDING_SITES)

    # Track IDs to guarantee uniqueness
    seen_ids = {p["id"] for p in all_places}

    for p in gazetteer_places:
        if p["id"] not in seen_ids:
            all_places.append(p)
            seen_ids.add(p["id"])

    # Count stats
    tier_counts = {1: 0, 2: 0, 3: 0}
    cat_counts: Dict[str, int] = {}
    for p in all_places:
        tier_counts[p["importance_tier"]] += 1
        cat = p["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    catalog_data = {
        "metadata": {
            "title": "MarsWalk 2.0 Planetary Exploration Nomenclature & Place Catalog",
            "datum": "IAU Mars 2000 Sphere (R_eq = 3,396,190 m)",
            "primary_sources": [
                "USGS Astrogeology Science Center Gazetteer of Planetary Nomenclature",
                "IAU Working Group for Planetary System Nomenclature (WGPSN)",
                "NASA Planetary Data System (PDS) Mission Archives",
            ],
            "total_records": len(all_places),
            "landing_sites_count": len(VERIFIED_LANDING_SITES),
            "tier_counts": tier_counts,
            "category_counts": cat_counts,
        },
        "featured_destinations": [
            "landing_perseverance",
            "landing_curiosity",
            "landing_insight",
            "landing_opportunity",
            "landing_spirit",
            "landing_zhurong",
            "landing_phoenix",
            "landing_pathfinder",
            "landing_viking1",
            "landing_viking2",
            "iau_4453",  # Olympus Mons
            "iau_6288",  # Valles Marineris
            "iau_14300", # Jezero Crater
            "iau_2071",  # Gale Crater
            "iau_2289",  # Gusev Crater
            "iau_2432",  # Hellas Planitia
            "iau_371",   # Argyre Planitia
            "iau_336",   # Arabia Terra
            "iau_1783",  # Elysium Mons
            "iau_5949",  # Tharsis Tholus
            "iau_6260",  # Utopia Planitia
            "iau_38",    # Acidalia Planitia
            "iau_4754",  # Planum Boreum (North Polar Cap)
            "iau_4753",  # Planum Australe (South Polar Cap)
        ],
        "places": all_places,
    }

    # Write output files
    for path in (output_path, output_public_path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2, ensure_ascii=False)
        print(f"[MarsWalk Catalog] Saved {len(all_places)} places to {path} ({os.path.getsize(path)} bytes).")

    print("[MarsWalk Catalog] Statistics:")
    print(f"  Total records: {len(all_places)}")
    print(f"  Tier 1 (Global): {tier_counts[1]}")
    print(f"  Tier 2 (Regional): {tier_counts[2]}")
    print(f"  Tier 3 (Local): {tier_counts[3]}")
    print("  Categories:", cat_counts)

    return catalog_data


if __name__ == "__main__":
    build_catalog()
