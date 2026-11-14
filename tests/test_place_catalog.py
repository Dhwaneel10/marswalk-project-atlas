"""
Automated Regression and Validation Tests for MarsWalk 2.0 Place Catalog.
Validates authoritative USGS/IAU gazetteer ingestion, landing sites, coordinate bounds,
schema integrity, and featured destinations.
"""

import json
from pathlib import Path
import pytest

DATA_PATH = Path("web/data/mars_places.json")
PUBLIC_DATA_PATH = Path("web/public/data/mars_places.json")

VALID_CATEGORIES = {
    "mission_site",
    "volcano",
    "canyon",
    "crater",
    "plain",
    "region",
    "chaos",
    "ridge",
    "other",
}


def test_catalog_file_exists_and_parses():
    assert DATA_PATH.exists(), f"Missing catalog file at {DATA_PATH}"
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert "metadata" in data
    assert "featured_destinations" in data
    assert "places" in data


def test_catalog_metadata_and_counts():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    meta = data["metadata"]

    assert meta["total_records"] == 2061
    assert meta["landing_sites_count"] == 10
    assert len(data["places"]) == 2061

    tier_counts = meta["tier_counts"]
    assert tier_counts["1"] == 190
    assert tier_counts["2"] == 602
    assert tier_counts["3"] == 1269
    assert sum(tier_counts.values()) == 2061


def test_place_records_schema_and_bounds():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen_ids = set()
    places = data["places"]

    for p in places:
        pid = p["id"]
        assert pid not in seen_ids, f"Duplicate place ID: {pid}"
        seen_ids.add(pid)

        assert isinstance(p["name"], str) and len(p["name"].strip()) > 0
        assert p["category"] in VALID_CATEGORIES, f"Invalid category {p['category']} in {pid}"

        lat = p["lat_deg"]
        lon = p["lon_deg"]
        lon_360 = p["center_lon_360"]

        assert -90.0 <= lat <= 90.0, f"Latitude {lat} out of bounds for {pid}"
        assert -180.0 <= lon <= 180.0, f"Longitude {lon} out of bounds for {pid}"
        assert 0.0 <= lon_360 <= 360.0, f"Center Lon 360 {lon_360} out of bounds for {pid}"

        assert p["importance_tier"] in {1, 2, 3}
        assert isinstance(p["is_landing_site"], bool)
        assert len(p["dataset_attribution"]) > 0

        if p["diameter_km"] is not None:
            assert p["diameter_km"] >= 0.0


def test_featured_destinations_integrity():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    places_by_id = {p["id"]: p for p in data["places"]}
    featured_ids = data["featured_destinations"]

    assert len(featured_ids) == 24, f"Expected 24 featured destinations, got {len(featured_ids)}"

    for fid in featured_ids:
        assert fid in places_by_id, f"Featured destination {fid} not found in catalog"
        p = places_by_id[fid]
        assert p["importance_tier"] == 1, f"Featured destination {fid} must be Tier 1"

    # Critical landmarks check
    assert "iau_4453" in places_by_id  # Olympus Mons
    assert "iau_6288" in places_by_id  # Valles Marineris
    assert "iau_14300" in places_by_id  # Jezero Crater
    assert "iau_2071" in places_by_id  # Gale Crater
    assert "landing_perseverance" in places_by_id  # Perseverance
    assert "landing_curiosity" in places_by_id  # Curiosity


def test_landing_sites_historical_accuracy():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    landing_sites = [p for p in data["places"] if p["is_landing_site"]]
    assert len(landing_sites) == 10

    landing_ids = {p["id"] for p in landing_sites}
    expected_sites = {
        "landing_perseverance",
        "landing_curiosity",
        "landing_insight",
        "landing_spirit",
        "landing_opportunity",
        "landing_phoenix",
        "landing_viking1",
        "landing_viking2",
        "landing_pathfinder",
        "landing_zhurong",
    }
    assert landing_ids == expected_sites

    # Check Perseverance landing details
    perseverance = next(p for p in landing_sites if p["id"] == "landing_perseverance")
    assert perseverance["agency"] == "NASA / JPL-Caltech"
    assert perseverance["mission"] == "Mars 2020"
    assert perseverance["host_feature"] == "Jezero Crater"
    assert 18.44 <= perseverance["lat_deg"] <= 18.45
    assert 77.44 <= perseverance["lon_deg"] <= 77.46
