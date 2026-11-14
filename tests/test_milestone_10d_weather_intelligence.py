"""
MarsWalk 2.0 — Milestone 10D: Mars Environmental Intelligence Test Suite.
Validates NASA PDS archival ingestion, physical bounds checking,
freshness-aware caching, multi-site isolation, and schema contracts.
"""

import os
import json
import urllib.error
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from marswalk.core.weather import (
    WeatherSnapshot,
    WeatherManager,
    WeatherStorage,
    PdsMedaProvider,
    PhysicalRangeGuard,
    clean_pds_measurement,
    kelvin_to_celsius,
    validate_physical_ranges,
    WeatherError,
    PRESSURE_MIN_PA,
    PRESSURE_MAX_PA,
)
from marswalk.api.contracts import validate_contract
from marswalk.api.service import (
    get_weather_current_api,
    get_weather_sites_api,
    refresh_weather_api,
    APIError,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEATHER_DIR = PROJECT_ROOT / "data" / "weather"


class TestMilestone10dEnvironmentalIntelligence:
    """Test suite covering Milestone 10D weather intelligence and atmospheric services."""

    def test_01_unit_conversions_and_cleaning(self):
        """Test safe Kelvin to Celsius conversions and PDS sentinel filtering."""
        # 0 K -> -273.15 C
        assert kelvin_to_celsius(0.0) == -273.15
        assert kelvin_to_celsius(273.15) == 0.0
        assert kelvin_to_celsius(211.45) == -61.70
        assert kelvin_to_celsius(None) is None

        # Sentinels
        assert clean_pds_measurement(999999999) is None
        assert clean_pds_measurement(999999999.0) is None
        assert clean_pds_measurement(-9999) is None
        assert clean_pds_measurement(float("nan")) is None
        assert clean_pds_measurement("589.69") == 589.69

    def test_02_physical_range_guard(self):
        """Test Martian atmospheric physical limits guard."""
        # Normal Jezero measurements
        nominal = {
            "atmospheric_pressure_pa": 590.0,
            "air_temperature_k": 210.0,
            "ground_temperature_k": 220.0,
            "wind_speed_m_s": 5.0,
            "optical_depth_tau": 0.4,
        }
        warnings = validate_physical_ranges(nominal)
        assert len(warnings) == 0

        # Out-of-bounds pressure and temperature
        abnormal = {
            "atmospheric_pressure_pa": 50000.0,  # Terrestrial level!
            "air_temperature_k": 50.0,           # Impossibly cold
            "wind_speed_m_s": 150.0,
            "optical_depth_tau": 25.0,
        }
        warnings = validate_physical_ranges(abnormal)
        assert len(warnings) == 4
        assert any("pressure" in w for w in warnings)
        assert any("air temperature" in w for w in warnings)

    def test_03_baseline_jezero_meda_fixture(self):
        """Verify bundled authentic Jezero MEDA baseline snapshot."""
        storage = WeatherStorage()
        snapshot = storage.read_snapshot("jezero_crater")
        assert snapshot is not None
        assert snapshot.site_id == "jezero_crater"
        assert snapshot.data_type == "IN_SITU_OBSERVATION"
        assert snapshot.observation_sol == 1619
        assert snapshot.measurements["atmospheric_pressure_pa"] == 589.69
        assert snapshot.measurements["air_temperature_k"] == 211.45
        assert snapshot.measurements["air_temperature_c"] == -61.70
        assert snapshot.measurements["ground_temperature_c"] == -59.95
        # Wind is null due to grit damage, NOT zero
        assert snapshot.measurements["wind_speed_m_s"] is None
        assert snapshot.coordinates["lat_deg"] == pytest.approx(18.4447, rel=1e-3)
        assert snapshot.coordinates["lon_deg"] == pytest.approx(77.4508, rel=1e-3)

    def test_04_schema_contract_compliance(self):
        """Verify WeatherSnapshot serialization satisfies Draft 2020-12 schema."""
        storage = WeatherStorage()
        snapshot = storage.read_snapshot("jezero_crater")
        data = snapshot.to_dict()
        is_valid, errors = validate_contract(data, "weather-report", raise_on_error=False)
        assert is_valid, f"Contract validation failed: {errors}"
        assert data["schema_version"] == "1.0.0"

    def test_05_site_isolation_gale_rems(self):
        """Verify Gale Crater REMS is strictly isolated from Jezero."""
        storage = WeatherStorage()
        gale = storage.read_snapshot("gale_crater")
        assert gale is not None
        assert gale.site_id == "gale_crater"
        assert gale.data_type == "IN_SITU_OBSERVATION"
        assert gale.coordinates["lat_deg"] < 0  # Southern hemisphere (-4.59)
        assert gale.measurements["atmospheric_pressure_pa"] > 800.0  # Gale is deeper crater
        # Enforce site isolation disclosure
        assert any("SITE ISOLATION ENFORCED" in d for d in gale.disclosures)

    def test_06_climatological_model_distinction(self):
        """Verify Olympus Mons summit report is explicitly labelled as climatological model."""
        storage = WeatherStorage()
        olympus = storage.read_snapshot("olympus_mons")
        assert olympus is not None
        assert olympus.site_id == "olympus_mons"
        assert olympus.data_type == "CLIMATOLOGICAL_MODEL"
        assert olympus.observation_sol is None
        assert olympus.observation_time_utc is None
        # Olympus caldera pressure is very low (~72 Pa)
        assert olympus.measurements["atmospheric_pressure_pa"] < 100.0
        assert any("DATA IS MODELLED CLIMATOLOGY" in w for w in olympus.warnings)

    def test_07_historical_insight_archive_label(self):
        """Verify InSight archive report is explicitly labelled as historical mission."""
        storage = WeatherStorage()
        insight = storage.read_snapshot("elysium_planitia")
        assert insight is not None
        assert insight.site_id == "elysium_planitia"
        assert insight.data_type == "HISTORICAL_MISSION_ARCHIVE"
        assert insight.freshness_status == "HISTORICAL"
        assert insight.observation_sol == 1440
        assert any("HISTORICAL ARCHIVE" in w for w in insight.warnings)

    def test_08_pds_meda_upstream_parsing(self):
        """Test parsing mock upstream PDS MEDA CSV index."""
        csv_sample = (
            ",Midpoint, URN, title, Start Time, Stop Time,start_sol_number,stop_sol_number,LMST,LTST,start_Ls,stop_Ls,Ls,Mars Year,File Size\n"
            "PS,2025-09-09T04:56:36.70Z,urn:nasa:pds:mars2020_meda:data_derived_env:we__1619___________der_ps__________________p,Mars 2020 MEDA PS,2025-09-08T16:36:22.350Z,2025-09-09T17:15:51.056Z,1619,1619,01619M00:00:06.331,1619 00:29:00,136.968,137.473,137.13,38,2.489\n"
        )
        provider = PdsMedaProvider()
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = csv_sample.encode("utf-8")
            mock_open.return_value.__enter__.return_value = mock_resp

            snap = provider.fetch_weather(force_refresh=True)
            assert snap.observation_sol == 1619
            assert snap.solar_longitude_ls_deg == 137.13
            assert snap.freshness_status == "LATEST_AVAILABLE"
            assert snap.measurements["atmospheric_pressure_pa"] == 589.69

    def test_09_upstream_network_failure_cached_fallback(self):
        """Verify network outage falls back gracefully to cached baseline with warning."""
        provider = PdsMedaProvider()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection timed out")):
            snap = provider.fetch_weather(force_refresh=True)
            assert snap is not None
            assert snap.freshness_status == "CACHED_FALLBACK"
            assert any("Upstream PDS connection unavailable" in w for w in snap.warnings)
            assert snap.measurements["atmospheric_pressure_pa"] == 589.69

    def test_10_atomic_cache_write(self, tmp_path):
        """Verify snapshot persistence writes atomically via temp file."""
        storage = WeatherStorage(base_dir=tmp_path)
        base = storage.read_snapshot("jezero_crater")
        assert base is not None
        storage.write_snapshot(base)
        cache_file = tmp_path / "cache_jezero_crater.json"
        assert cache_file.exists()
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["site_id"] == "jezero_crater"
        assert data["observation_sol"] == 1619

    def test_11_weather_manager_supported_sites(self):
        """Verify supported sites registry."""
        wm = WeatherManager()
        sites = wm.get_supported_sites()
        assert len(sites) >= 4
        site_ids = [s["site_id"] for s in sites]
        assert "jezero_crater" in site_ids
        assert "gale_crater" in site_ids
        assert "olympus_mons" in site_ids
        assert "elysium_planitia" in site_ids

    def test_12_weather_manager_unknown_site_error(self):
        """Verify requesting non-existent site raises typed WeatherError."""
        wm = WeatherManager()
        with pytest.raises(WeatherError) as exc:
            wm.get_weather("alpha_centauri")
        assert exc.value.status_code == 400
        assert exc.value.error_code == "ERR_UNKNOWN_WEATHER_SITE"

    def test_13_api_get_weather_current_success(self):
        """Verify GET /api/weather/current service handler."""
        res = get_weather_current_api({"site": "jezero_crater"})
        assert res["status"] == "success"
        assert res["site_id"] == "jezero_crater"
        assert res["observation_sol"] == 1619
        assert "measurements" in res
        assert res["measurements"]["atmospheric_pressure_pa"] == 589.69

    def test_14_api_get_weather_sites_success(self):
        """Verify GET /api/weather/sites service handler."""
        res = get_weather_sites_api()
        assert res["status"] == "success"
        assert res["count"] >= 4
        assert any(s["site_id"] == "jezero_crater" for s in res["sites"])

    def test_15_api_post_weather_refresh_success(self):
        """Verify POST /api/weather/refresh service handler."""
        res = refresh_weather_api({"site_id": "jezero_crater"})
        assert res["status"] == "success"
        assert res["site_id"] == "jezero_crater"
        assert "last_checked_utc" in res

    def test_16_api_weather_validation_errors(self):
        """Verify invalid payloads produce APIError with status 400."""
        with pytest.raises(APIError) as exc:
            get_weather_current_api({"site": "invalid_mars_station"})
        assert exc.value.status_code == 400

        with pytest.raises(APIError) as exc:
            refresh_weather_api("not_a_json_dict")
        assert exc.value.status_code == 400

    def test_17_deduplication_on_repeated_checks(self):
        """Verify repeated checks update last_checked_utc without altering observation."""
        wm = WeatherManager()
        snap1 = wm.get_weather("jezero_crater")
        sol1 = snap1["observation_sol"]
        time1 = snap1["observation_time_utc"]

        snap2 = wm.refresh_weather("jezero_crater")
        assert snap2["observation_sol"] == sol1
        assert snap2["observation_time_utc"] == time1

    def test_18_no_silent_modification_of_routing(self):
        """Verify weather module does not modify A* terrain routing or cost models."""
        from marswalk.core.weather import get_weather_manager
        wm = get_weather_manager()
        snap = wm.get_weather("jezero_crater")
        # Ensure snapshot does not contain executable routing mutations
        assert "route_cost_multiplier" not in snap["measurements"]
        assert "max_speed_override" not in snap["measurements"]

    def test_19_missing_readings_are_null_not_zero(self):
        """Verify missing sensor measurements remain None/null and are never zeroed."""
        storage = WeatherStorage()
        snap = storage.read_snapshot("jezero_crater")
        # Wind is absent
        assert snap.measurements["wind_speed_m_s"] is None
        assert snap.measurements["wind_speed_m_s"] != 0.0

    def test_20_weather_data_provenance_citations(self):
        """Verify source metadata and citation links are populated and valid URLs."""
        storage = WeatherStorage()
        for site in ["jezero_crater", "gale_crater", "olympus_mons", "elysium_planitia"]:
            snap = storage.read_snapshot(site)
            assert snap.source_metadata["archive_url"].startswith("http")
            assert len(snap.source_metadata["archive_citation"]) > 20
