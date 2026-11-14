"""
MarsWalk 2.0 / Project Atlas - Planetary Observation Normalizer
Rigorous spatiotemporal coordinate and calendar transformations for Martian observations.
Supports UTC, Sol, LMST, LTST, Solar Longitude (Ls), Planetocentric/Planetographic coordinates,
and Jezero Crater local metric/DTM projections.
"""

from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional

# Physical and astronomical constants (IAU 2000 Mars Spheroid / Allison & McEwen 2000)
MARS_RADIUS_EQUATORIAL_M = 3_396_190.0
MARS_RADIUS_POLAR_M = 3_376_200.0
MARS_FLATTENING = (MARS_RADIUS_EQUATORIAL_M - MARS_RADIUS_POLAR_M) / MARS_RADIUS_EQUATORIAL_M  # ~0.005886
MARS_SOL_SECONDS = 88775.244  # 24h 39m 35.244s

# Jezero Crater reference origin (USGS CTX DTM Mosaic center)
JEZERO_ORIGIN_LAT_DEG = 18.4447
JEZERO_ORIGIN_LON_DEG = 77.4508
JEZERO_DTM_CELL_SIZE_M = 20.0
JEZERO_DTM_ROWS = 250
JEZERO_DTM_COLS = 250

# Perseverance landing: Sol 0 = 2021-02-18T20:55:00 UTC, Ls ~ 5.6 deg (MY 36)
PERSEVERANCE_LANDING_UTC = datetime(2021, 2, 18, 20, 55, 0, tzinfo=timezone.utc)
PERSEVERANCE_LANDING_SOL = 0


def parse_sol_lmst(lmst_str: str) -> Tuple[int, float]:
    """
    Parse PDS standard LMST string (e.g. '00010M14:31:53.805' or '01619M00:00:06.331').
    Returns (sol_number, decimal_hours).
    """
    clean = lmst_str.strip()
    if 'M' in clean:
        parts = clean.split('M')
        sol = int(parts[0])
        time_part = parts[1]
    elif ' ' in clean:
        parts = clean.split()
        sol = int(parts[0])
        time_part = parts[1]
    else:
        # Default or solitary time
        return 0, 0.0

    t_toks = time_part.split(':')
    h = float(t_toks[0])
    m = float(t_toks[1]) if len(t_toks) > 1 else 0.0
    s = float(t_toks[2]) if len(t_toks) > 2 else 0.0
    decimal_hours = h + m / 60.0 + s / 3600.0
    return sol, decimal_hours


def parse_sol_ltst(ltst_str: str) -> Tuple[int, float]:
    """
    Parse PDS standard LTST string (e.g. '0010 13:57:24' or '1618 23:59:10').
    Returns (sol_number, decimal_hours).
    """
    clean = ltst_str.strip()
    toks = clean.split()
    if len(toks) >= 2:
        sol = int(toks[0])
        time_toks = toks[1].split(':')
        h = float(time_toks[0])
        m = float(time_toks[1]) if len(time_toks) > 1 else 0.0
        s = float(time_toks[2]) if len(time_toks) > 2 else 0.0
        return sol, h + m / 60.0 + s / 3600.0
    elif len(toks) == 1 and ':' in toks[0]:
        time_toks = toks[0].split(':')
        h = float(time_toks[0])
        m = float(time_toks[1]) if len(time_toks) > 1 else 0.0
        s = float(time_toks[2]) if len(time_toks) > 2 else 0.0
        return 0, h + m / 60.0 + s / 3600.0
    return 0, 0.0


def format_sol_ltst(sol: int, decimal_hours: float) -> str:
    """Format sol and decimal hours into PDS LTST string (e.g. '0010 13:57:24')."""
    dh = decimal_hours % 24.0
    h = int(dh)
    rem_m = (dh - h) * 60.0
    m = int(rem_m)
    s = int(round((rem_m - m) * 60.0))
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        h = (h + 1) % 24
    return f"{sol:04d} {h:02d}:{m:02d}:{s:02d}"


def utc_to_sol_and_ls(utc_dt: datetime) -> Tuple[int, float, float]:
    """
    Convert UTC datetime to Mars 2020 Sol number, approximate LTST at Jezero, and Solar Longitude (Ls).
    Uses high-precision Keplerian orbital elements for Mars.
    """
    # Julian Date from epoch 2000 Jan 1.5 (J2000.0 = JD 2451545.0)
    # Unix epoch 1970-01-01 is JD 2440587.5
    timestamp = utc_dt.timestamp()
    jd = 2440587.5 + (timestamp / 86400.0)
    d = jd - 2451545.0

    # Mars Mean Anomaly M
    M = (19.3870 + 0.52402075 * d) % 360.0
    m_rad = math.radians(M)

    # Mars True Anomaly nu and Equation of Center
    # Eccentricity e = 0.09341233
    e = 0.09341233
    eq_center = (2.0 * e - (e**3) / 4.0) * math.sin(m_rad) + (5.0 / 4.0) * (e**2) * math.sin(2.0 * m_rad) + (13.0 / 12.0) * (e**3) * math.sin(3.0 * m_rad)
    nu = (M + math.degrees(eq_center)) % 360.0

    # Solar Longitude Ls = (nu + 250.999) % 360 (perihelion is at Ls = 251.0 deg)
    Ls = (nu + 250.999) % 360.0

    # Elapsed sols since Perseverance landing
    delta_sec = (utc_dt - PERSEVERANCE_LANDING_UTC).total_seconds()
    sol = int(math.floor(delta_sec / MARS_SOL_SECONDS))

    # LTST at Jezero (Lon 77.45 deg)
    # Mars sol fractional phase
    sol_fraction = (delta_sec % MARS_SOL_SECONDS) / MARS_SOL_SECONDS
    # Jezero longitude offset + landing time offset
    ltst_hours = (sol_fraction * 24.0 + 13.9) % 24.0

    return sol, ltst_hours, round(Ls, 2)


def equation_of_time_hours(ls_deg: float) -> float:
    """
    Martian Equation of Time: EOT = LTST - LMST in hours.
    On Mars, large eccentricity (0.0934) and obliquity (25.19 deg) produce EOT swings up to ~50 minutes (~0.85 hours).
    Ref: Allison & McEwen (2000).
    """
    ls_rad = math.radians(ls_deg)
    # Eccentricity term + Obliquity term
    e = 0.0934
    obliq_rad = math.radians(25.19)
    # EOT approx:
    eot_rad = -2.0 * e * math.sin(ls_rad - math.radians(251.0)) + math.tan(obliq_rad / 2.0)**2 * math.sin(2.0 * ls_rad)
    eot_hours = math.degrees(eot_rad) * (24.0 / 360.0)
    return eot_hours


def lmst_to_ltst(lmst_hours: float, ls_deg: float) -> float:
    """Convert Local Mean Solar Time (LMST) to Local True Solar Time (LTST)."""
    eot = equation_of_time_hours(ls_deg)
    return (lmst_hours + eot) % 24.0


def ltst_to_lmst(ltst_hours: float, ls_deg: float) -> float:
    """Convert Local True Solar Time (LTST) to Local Mean Solar Time (LMST)."""
    eot = equation_of_time_hours(ls_deg)
    return (ltst_hours - eot) % 24.0


def planetocentric_to_planetographic_lat(lat_cen_deg: float) -> float:
    """
    Convert Planetocentric latitude to Planetographic latitude using Mars spheroid flattening.
    tan(phi_graph) = (a/b)^2 * tan(phi_cent)
    """
    ratio_sq = (MARS_RADIUS_EQUATORIAL_M / MARS_RADIUS_POLAR_M) ** 2
    tan_cen = math.tan(math.radians(lat_cen_deg))
    phi_graph_rad = math.atan(ratio_sq * tan_cen)
    return math.degrees(phi_graph_rad)


def planetographic_to_planetocentric_lat(lat_graph_deg: float) -> float:
    """Convert Planetographic latitude to Planetocentric latitude."""
    ratio_sq = (MARS_RADIUS_EQUATORIAL_M / MARS_RADIUS_POLAR_M) ** 2
    tan_graph = math.tan(math.radians(lat_graph_deg))
    phi_cen_rad = math.atan(tan_graph / ratio_sq)
    return math.degrees(phi_cen_rad)


def coordinates_to_jezero_dtm_pixel(lat_deg: float, lon_deg: float) -> Tuple[int, int, float, float]:
    """
    Project Martian spherical coordinates (Lat, Lon in degrees) to Jezero 20m DTM pixel (row, col)
    and metric local coordinates (x_m, y_m) relative to DTM center.
    Returns (row, col, x_meters, y_meters).
    """
    # Equirectangular projection relative to Jezero origin
    d_lat = lat_deg - JEZERO_ORIGIN_LAT_DEG
    d_lon = lon_deg - JEZERO_ORIGIN_LON_DEG

    lat_rad = math.radians(JEZERO_ORIGIN_LAT_DEG)
    # Arc lengths on Mars spheroid
    m_per_deg_lat = (math.pi / 180.0) * MARS_RADIUS_EQUATORIAL_M
    m_per_deg_lon = (math.pi / 180.0) * MARS_RADIUS_EQUATORIAL_M * math.cos(lat_rad)

    x_meters = d_lon * m_per_deg_lon
    y_meters = d_lat * m_per_deg_lat

    # DTM has origin at top-left, centered at (125, 125) with 20m/cell
    center_r = JEZERO_DTM_ROWS / 2.0
    center_c = JEZERO_DTM_COLS / 2.0

    col = int(round(center_c + (x_meters / JEZERO_DTM_CELL_SIZE_M)))
    row = int(round(center_r - (y_meters / JEZERO_DTM_CELL_SIZE_M)))  # row 0 is North

    # Clamping to grid bounds for indexing
    col_clamped = max(0, min(JEZERO_DTM_COLS - 1, col))
    row_clamped = max(0, min(JEZERO_DTM_ROWS - 1, row))

    return row_clamped, col_clamped, x_meters, y_meters


def jezero_dtm_pixel_to_coordinates(row: int, col: int) -> Tuple[float, float]:
    """Convert Jezero 20m DTM pixel (row, col) back to Martian spherical coordinates (Lat, Lon degrees)."""
    center_r = JEZERO_DTM_ROWS / 2.0
    center_c = JEZERO_DTM_COLS / 2.0

    x_meters = (col - center_c) * JEZERO_DTM_CELL_SIZE_M
    y_meters = (center_r - row) * JEZERO_DTM_CELL_SIZE_M

    lat_rad = math.radians(JEZERO_ORIGIN_LAT_DEG)
    m_per_deg_lat = (math.pi / 180.0) * MARS_RADIUS_EQUATORIAL_M
    m_per_deg_lon = (math.pi / 180.0) * MARS_RADIUS_EQUATORIAL_M * math.cos(lat_rad)

    lat_deg = JEZERO_ORIGIN_LAT_DEG + (y_meters / m_per_deg_lat)
    lon_deg = JEZERO_ORIGIN_LON_DEG + (x_meters / m_per_deg_lon)

    return round(lat_deg, 6), round(lon_deg, 6)


def get_perseverance_traverse_position(sol: int) -> Dict[str, Any]:
    """
    Interpolate Perseverance Rover traverse position in Jezero Crater for a given mission Sol.
    Reconstructed from NASA Mars 2020 published traverse milestones (Octavia E. Butler Landing,
    Séítah, Delta Front, Fan Scarp, Margin Unit).
    """
    waypoints = [
        {"sol": 0, "name": "Octavia E. Butler Landing", "lat": 18.4447, "lon": 77.4508, "elev_m": -2574.0},
        {"sol": 150, "name": "Séítah South Incursion", "lat": 18.4350, "lon": 77.4420, "elev_m": -2585.0},
        {"sol": 380, "name": "Three Forks Delta Base", "lat": 18.4485, "lon": 77.4280, "elev_m": -2550.0},
        {"sol": 600, "name": "Delta Scarp Hawksbill Gap", "lat": 18.4550, "lon": 77.4190, "elev_m": -2510.0},
        {"sol": 900, "name": "Tenby Delta Crest", "lat": 18.4620, "lon": 77.4110, "elev_m": -2470.0},
        {"sol": 1200, "name": "Margin Unit Light-Toned Rocks", "lat": 18.4710, "lon": 77.4020, "elev_m": -2430.0},
        {"sol": 1619, "name": "Crater Rim Ascent Path", "lat": 18.4800, "lon": 77.3910, "elev_m": -2380.0}
    ]

    if sol <= waypoints[0]["sol"]:
        wp = waypoints[0]
        r, c, xm, ym = coordinates_to_jezero_dtm_pixel(wp["lat"], wp["lon"])
        return {
            "sol": sol, "waypoint_name": wp["name"],
            "lat_deg": wp["lat"], "lon_deg": wp["lon"], "elev_m": wp["elev_m"],
            "dtm_pixel": {"row": r, "col": c}, "metric_xy_m": {"x": xm, "y": ym}
        }

    if sol >= waypoints[-1]["sol"]:
        wp = waypoints[-1]
        r, c, xm, ym = coordinates_to_jezero_dtm_pixel(wp["lat"], wp["lon"])
        return {
            "sol": sol, "waypoint_name": wp["name"],
            "lat_deg": wp["lat"], "lon_deg": wp["lon"], "elev_m": wp["elev_m"],
            "dtm_pixel": {"row": r, "col": c}, "metric_xy_m": {"x": xm, "y": ym}
        }

    # Linear interpolation between nearest waypoints
    for i in range(len(waypoints) - 1):
        w0 = waypoints[i]
        w1 = waypoints[i + 1]
        if w0["sol"] <= sol <= w1["sol"]:
            frac = (sol - w0["sol"]) / float(w1["sol"] - w0["sol"])
            lat = w0["lat"] + frac * (w1["lat"] - w0["lat"])
            lon = w0["lon"] + frac * (w1["lon"] - w0["lon"])
            elev = w0["elev_m"] + frac * (w1["elev_m"] - w0["elev_m"])
            r, c, xm, ym = coordinates_to_jezero_dtm_pixel(lat, lon)
            return {
                "sol": sol,
                "waypoint_name": f"Segment between {w0['name']} and {w1['name']}",
                "lat_deg": round(lat, 6), "lon_deg": round(lon, 6), "elev_m": round(elev, 1),
                "dtm_pixel": {"row": r, "col": c}, "metric_xy_m": {"x": round(xm, 1), "y": round(ym, 1)}
            }

    # Fallback to landing site
    wp = waypoints[0]
    r, c, xm, ym = coordinates_to_jezero_dtm_pixel(wp["lat"], wp["lon"])
    return {
        "sol": sol, "waypoint_name": wp["name"],
        "lat_deg": wp["lat"], "lon_deg": wp["lon"], "elev_m": wp["elev_m"],
        "dtm_pixel": {"row": r, "col": c}, "metric_xy_m": {"x": xm, "y": ym}
    }
