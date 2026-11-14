"""
Project MarsWalk 2.0 / Atlas — Mission 4: NASA Planetary Data Integration & Five Pillars Test Suite.
Verifies authentic planetary data ingestion, coordinate alignment, MEDA replay,
science target collocation, and bit-exact Merkle provenance across all five pillars.
"""

import json
import os
import pytest
import numpy as np
import rasterio

from marswalk.api.service import (
    pillars_terrain_api,
    pillars_rover_ground_truth_api,
    pillars_environment_meda_api,
    pillars_science_targets_api,
    pillars_manifest_api,
)
from marswalk.core.when_mars_goes_dark import WhenMarsGoesDarkEngine
from marswalk.core.terrain import load_and_process_terrain

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")


# ==============================================================================
# PILLAR 1: REAL MARS TERRAIN INTELLIGENCE
# ==============================================================================

def test_pillar1_ctx_20m_dem_integrity():
    """Verify USGS CTX 20m DEM loads with valid resolution, CRS, and non-empty elevations."""
    tif_path = os.path.join(DATA_DIR, "processed", "jezero_ready_20m.tif")
    assert os.path.exists(tif_path), f"Processed CTX DEM missing at {tif_path}"

    with rasterio.open(tif_path) as src:
        assert src.width == 250
        assert src.height == 250
        assert src.res == (20.0, 20.0)
        assert src.crs is not None
        assert "103885" in str(src.crs) or "Equirectangular" in str(src.crs.to_string())

        data = src.read(1)
        valid = data[data != src.nodata]
        assert len(valid) > 0
        assert float(np.min(valid)) >= -2700.0
        assert float(np.max(valid)) <= -2300.0


def test_pillar1_hirise_1m_dtm_integrity():
    """Verify USGS TRN HiRISE 1m DTM window loads with 1.0 m/pixel resolution and nested bounds."""
    hirise_path = os.path.join(DATA_DIR, "processed", "jezero_hirise_hawksbill_1m.tif")
    assert os.path.exists(hirise_path), f"HiRISE 1m DTM missing at {hirise_path}"

    with rasterio.open(hirise_path) as src:
        assert src.width == 600
        assert src.height == 600
        assert src.res == (1.0, 1.0)
        assert "103885" in str(src.crs)

        data = src.read(1)
        valid = data[data != src.nodata]
        assert len(valid) > 0
        assert float(np.min(valid)) >= -2650.0
        assert float(np.max(valid)) <= -2450.0

        # Check bounds are nested within CTX 20m DEM
        ctx_path = os.path.join(DATA_DIR, "processed", "jezero_ready_20m.tif")
        with rasterio.open(ctx_path) as ctx_src:
            assert src.bounds.left >= ctx_src.bounds.left
            assert src.bounds.right <= ctx_src.bounds.right
            assert src.bounds.bottom >= ctx_src.bounds.bottom
            assert src.bounds.top <= ctx_src.bounds.top


# ==============================================================================
# PILLAR 2: REAL ROVER OPERATIONS & GROUND TRUTH
# ==============================================================================

def test_pillar2_pds_places_ground_truth():
    """Verify authentic NASA PDS Rover PLACES records."""
    places_path = os.path.join(DATA_DIR, "catalogs", "perseverance_ground_truth_places.json")
    assert os.path.exists(places_path)

    with open(places_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert doc["total_records"] == 577
    assert doc["sol_range"] == [13, 1896]
    assert doc["source_authority"] == "NASA Planetary Data System (PDS) Geosciences Node"

    records = doc["records"]
    assert len(records) == 577

    # Validate coordinate envelopes
    lats = [r["latitude_planetocentric"] for r in records]
    lons = [r["longitude_east"] for r in records]
    elevs = [r["elevation_m"] for r in records]

    assert 18.35 <= min(lats) <= max(lats) <= 18.55
    assert 77.20 <= min(lons) <= max(lons) <= 77.55
    assert -2700.0 <= min(elevs) <= max(elevs) <= -1700.0


def test_pillar2_three_forks_sample_depot():
    """Verify authentic NASA PDS Three Forks Sample Depot catalog."""
    depot_path = os.path.join(DATA_DIR, "catalogs", "three_forks_sample_depot_catalog.json")
    assert os.path.exists(depot_path)

    with open(depot_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert doc["total_samples"] == 10
    assert "urn:nasa:pds:mars2020" in doc["bundle_urn"]

    samples = doc["samples"]
    assert len(samples) == 10

    # Verify tube names include known published samples (e.g., Amalik Witness, Mageik, Malay)
    sample_names = {s["sample_name"] for s in samples}
    assert "Malay" in sample_names
    assert "Amalik Witness" in sample_names
    assert "Mageik" in sample_names

    # Check depot location is at Three Forks (18.4326 N, 77.4392 E)
    for s in samples:
        assert 18.40 <= s["latitude_deg"] <= 18.46
        assert 77.40 <= s["longitude_deg"] <= 77.46
        assert "SOL-" in s["timestamp_lmst"]


# ==============================================================================
# PILLAR 3: MARS ENVIRONMENT & WEATHER REPLAY
# ==============================================================================

def test_pillar3_meda_in_situ_observations():
    """Verify authentic NASA Mars 2020 MEDA atmospheric measurements."""
    meda_path = os.path.join(DATA_DIR, "catalogs", "meda_environmental_observations.json")
    assert os.path.exists(meda_path)

    with open(meda_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert "NASA Planetary Data System (PDS) Atmospheres Node" in doc["source_authority"]
    assert "Rodriguez-Manfredi" in doc["citation"]

    stats = doc["summary_statistics"]
    assert 680.0 <= stats["pressure_pa"]["min"] < stats["pressure_pa"]["max"] <= 800.0
    assert -100.0 <= stats["air_temperature_c"]["min"] < stats["air_temperature_c"]["max"] <= 0.0
    assert 0.0 <= stats["wind_speed_ms"]["min"] < stats["wind_speed_ms"]["max"] <= 35.0

    # Verify diurnal reference profile
    profile = doc["diurnal_reference_profile"]
    assert len(profile) == 9
    hours = [p["lmst_hour"] for p in profile]
    assert 0.0 in hours and 12.0 in hours and 18.0 in hours

    # Pressure range across sol
    pressures = [p["pressure_pa"] for p in profile]
    assert all(690.0 <= p_val <= 780.0 for p_val in pressures)


# ==============================================================================
# PILLAR 4: SCIENCE-DRIVEN ROVER PLANNING
# ==============================================================================

def test_pillar4_geolocated_science_targets():
    """Verify geolocated astrobiology targets project squarely into Jezero 20m grid."""
    sci_path = os.path.join(DATA_DIR, "catalogs", "geolocated_science_targets.json")
    assert os.path.exists(sci_path)

    with open(sci_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    assert doc["total_targets"] == 5
    targets = doc["targets"]
    target_ids = {t["id"] for t in targets}
    assert "sci_wildcat_ridge" in target_ids
    assert "sci_skinner_ridge" in target_ids
    assert "sci_enchanted_lake" in target_ids
    assert "sci_kodiak_butte" in target_ids
    assert "sci_belva_crater_rim" in target_ids

    # Verify Wildcat Ridge details
    wildcat = next(t for t in targets if t["id"] == "sci_wildcat_ridge")
    assert "SHERLOC" in wildcat["instruments"]
    assert "PIXL" in wildcat["instruments"]
    assert wildcat["sample_tube_name"] == "Hazelton"

    # Collocation into raster grid
    tif_path = os.path.join(DATA_DIR, "processed", "jezero_ready_20m.tif")
    terrain = load_and_process_terrain(tif_path)

    R_mars = 3396190.0
    inv_t = ~terrain.transform
    for t in targets:
        # Convert lon/lat to equirectangular projected coordinates
        x_m = np.radians(t["lon_deg"]) * R_mars
        y_m = np.radians(t["lat_deg"]) * R_mars

        col, row = inv_t @ (x_m, y_m)

        assert 0 <= int(row) < terrain.height, f"Target {t['id']} row {int(row)} out of bounds"
        assert 0 <= int(col) < terrain.width, f"Target {t['id']} col {int(col)} out of bounds"


# ==============================================================================
# PILLAR 5: COMMUNICATIONS & AUTONOMOUS RESILIENCE
# ==============================================================================

def test_pillar5_flagship_resilience_and_merkle_provenance():
    """Verify flagship mission executes, embeds 5 pillars provenance, and validates bit-exact Merkle root."""
    tif_path = os.path.join(DATA_DIR, "processed", "jezero_ready_20m.tif")
    terrain = load_and_process_terrain(tif_path)

    engine = WhenMarsGoesDarkEngine(terrain=terrain)
    dossier = engine.execute_flagship_mission()

    assert dossier["status"] == "QUALIFIED"
    assert dossier["snapshots_count"] == 7
    assert dossier["root_merkle_hash"] == "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8"

    # Verify Five Pillars provenance block is embedded
    assert "five_pillars_provenance" in dossier
    p_meta = dossier["five_pillars_provenance"]
    assert "pillar_1_terrain_intelligence" in p_meta
    assert "USGS CTX" in p_meta["pillar_1_terrain_intelligence"]["base_dtm"]
    assert "HiRISE" in p_meta["pillar_1_terrain_intelligence"]["highres_dtm"]
    assert "pillar_2_rover_ground_truth" in p_meta
    assert "Three Forks" in p_meta["pillar_2_rover_ground_truth"]["sample_depot"]
    assert "pillar_3_environmental_intelligence" in p_meta
    assert "MEDA" in p_meta["pillar_3_environmental_intelligence"]["dataset"]
    assert "pillar_4_science_driven_planning" in p_meta
    assert len(p_meta["pillar_4_science_driven_planning"]["targets_evaluated"]) >= 3
    assert "pillar_5_communications_resilience" in p_meta
    assert "Electra" in p_meta["pillar_5_communications_resilience"]["rf_carrier"]


# ==============================================================================
# LIVE API SERVICE ENDPOINTS
# ==============================================================================

def test_live_pillars_api_services():
    """Verify all 5 Five-Pillar service API handlers return 200 OK contracts."""
    t_res = pillars_terrain_api()
    assert t_res["pillar"] == "PILLAR_1_TERRAIN_INTELLIGENCE"
    assert "ctx_dem" in t_res

    r_res = pillars_rover_ground_truth_api()
    assert r_res["pillar"] == "PILLAR_2_ROVER_OPERATIONS_AND_GROUND_TRUTH"
    assert r_res["rover_places"]["total_records"] == 577
    assert r_res["three_forks_sample_depot"]["total_samples"] == 10

    e_res = pillars_environment_meda_api()
    assert e_res["pillar"] == "PILLAR_3_MARS_ENVIRONMENT_AND_WEATHER_REPLAY"
    assert len(e_res["diurnal_reference_profile"]) == 9

    s_res = pillars_science_targets_api()
    assert s_res["pillar"] == "PILLAR_4_SCIENCE_DRIVEN_ROVER_PLANNING"
    assert s_res["total_targets"] == 5

    m_res = pillars_manifest_api()
    assert m_res["manifest_version"] == "2.0.0"
    assert len(m_res["datasets"]) >= 7
