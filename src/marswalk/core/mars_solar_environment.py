"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Mars Solar Geometry & Terrain Illumination Engine.

Implements rigorous planetary ephemeris equations for Mars solar positioning,
local true solar time (LTST), surface incidence angles over sloped DTM terrain,
and 3D discrete ray-cast terrain horizon cast shadowing over the USGS CTX 20m Jezero Crater grid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Physical planetary constants for Mars IAU 2000
MARS_OBLIQUITY_DEG = 25.19             # Axial tilt of Mars in degrees
MARS_ORBIT_ECCENTRICITY = 0.0934       # Orbital eccentricity
MARS_SEMI_MAJOR_AXIS_AU = 1.52368      # Semi-major axis in Astronomical Units
MARS_SOL_HOURS = 24.65979              # Earth hours per Martian Sol (24h 39m 35.244s)
SOLAR_CONSTANT_1AU_W_M2 = 1361.0       # Solar constant at 1 AU in W/m²
JEZERO_LATITUDE_DEG = 18.442           # Perseverance / Jezero Crater reference latitude
JEZERO_LONGITUDE_DEG = 77.451          # Perseverance landing longitude East

DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi


@dataclass(frozen=True)
class SolarEphemeris:
    """Astronomical solar coordinates for a specific sol and local solar time."""
    sol: int
    ltst_hours: float
    solar_longitude_ls_deg: float
    solar_declination_deg: float
    hour_angle_deg: float
    solar_elevation_deg: float
    solar_zenith_deg: float
    solar_azimuth_deg: float
    sun_distance_au: float
    toa_irradiance_w_m2: float
    is_sun_above_horizon: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol": self.sol,
            "ltst_hours": round(self.ltst_hours, 3),
            "solar_longitude_ls_deg": round(self.solar_longitude_ls_deg, 2),
            "solar_declination_deg": round(self.solar_declination_deg, 2),
            "hour_angle_deg": round(self.hour_angle_deg, 2),
            "solar_elevation_deg": round(self.solar_elevation_deg, 2),
            "solar_zenith_deg": round(self.solar_zenith_deg, 2),
            "solar_azimuth_deg": round(self.solar_azimuth_deg, 2),
            "sun_distance_au": round(self.sun_distance_au, 4),
            "toa_irradiance_w_m2": round(self.toa_irradiance_w_m2, 1),
            "is_sun_above_horizon": self.is_sun_above_horizon,
        }


@dataclass(frozen=True)
class TerrainIlluminationResult:
    """Point-specific evaluation of solar illumination, slope incidence, and terrain shadowing."""
    row: float
    col: float
    elevation_m: float
    slope_deg: float
    aspect_deg: float
    solar_elevation_deg: float
    solar_azimuth_deg: float
    incidence_angle_deg: float
    cos_incidence: float
    is_daylight: bool
    is_self_shadowed: bool
    is_terrain_shadowed: bool
    is_illuminated: bool
    obstruction_distance_m: Optional[float] = None
    direct_flux_w_m2: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": round(self.row, 2),
            "col": round(self.col, 2),
            "elevation_m": round(self.elevation_m, 2),
            "slope_deg": round(self.slope_deg, 2),
            "aspect_deg": round(self.aspect_deg, 2),
            "solar_elevation_deg": round(self.solar_elevation_deg, 2),
            "solar_azimuth_deg": round(self.solar_azimuth_deg, 2),
            "incidence_angle_deg": round(self.incidence_angle_deg, 2),
            "cos_incidence": round(self.cos_incidence, 4),
            "is_daylight": self.is_daylight,
            "is_self_shadowed": self.is_self_shadowed,
            "is_terrain_shadowed": self.is_terrain_shadowed,
            "is_illuminated": self.is_illuminated,
            "obstruction_distance_m": round(self.obstruction_distance_m, 1) if self.obstruction_distance_m is not None else None,
            "direct_flux_w_m2": round(self.direct_flux_w_m2, 1),
        }


class MarsSolarGeometryEngine:
    """Computes solar ephemeris and ray-cast terrain shadows across Jezero Crater."""

    def __init__(self, ref_latitude_deg: float = JEZERO_LATITUDE_DEG) -> None:
        self.ref_lat_deg = ref_latitude_deg
        self.ref_lat_rad = ref_latitude_deg * DEG_TO_RAD

    def compute_solar_longitude_ls(self, sol: int, base_ls_deg: float = 0.0) -> float:
        """Calculate solar longitude Ls (degrees [0, 360)) based on mission sol."""
        # Mars orbital period is ~668.6 sols
        delta_ls = (sol - 1) * (360.0 / 668.6)
        ls = (base_ls_deg + delta_ls) % 360.0
        return float(round(ls, 4))

    def compute_solar_ephemeris(
        self,
        sol: int,
        ltst_hours: float,
        base_ls_deg: float = 0.0,
    ) -> SolarEphemeris:
        """
        Compute rigorous astronomical solar coordinates for given sol and LTST decimal hours [0, 24).
        """
        ls_deg = self.compute_solar_longitude_ls(sol, base_ls_deg)
        ls_rad = ls_deg * DEG_TO_RAD

        # 1. Solar declination
        # sin(delta) = sin(obliquity) * sin(Ls)
        obliquity_rad = MARS_OBLIQUITY_DEG * DEG_TO_RAD
        sin_dec = math.sin(obliquity_rad) * math.sin(ls_rad)
        dec_rad = math.asin(sin_dec)
        dec_deg = dec_rad * RAD_TO_DEG

        # 2. Hour angle h: at 12:00 LTST h = 0°, 15° per hour
        h_deg = (ltst_hours - 12.0) * 15.0
        h_rad = h_deg * DEG_TO_RAD

        # 3. Solar elevation (altitude above local horizontal plane)
        # sin(alpha) = sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(h)
        sin_alpha = (
            math.sin(self.ref_lat_rad) * math.sin(dec_rad)
            + math.cos(self.ref_lat_rad) * math.cos(dec_rad) * math.cos(h_rad)
        )
        sin_alpha = min(max(sin_alpha, -1.0), 1.0)
        alpha_rad = math.asin(sin_alpha)
        alpha_deg = alpha_rad * RAD_TO_DEG
        zenith_deg = max(0.0, 90.0 - alpha_deg)

        # 4. Solar azimuth (clockwise from North: 0° N, 90° E, 180° S, 270° W)
        x_sun = -math.cos(dec_rad) * math.sin(h_rad)
        y_sun = math.cos(self.ref_lat_rad) * math.sin(dec_rad) - math.sin(self.ref_lat_rad) * math.cos(dec_rad) * math.cos(h_rad)
        azimuth_deg = (math.atan2(x_sun, y_sun) * RAD_TO_DEG) % 360.0

        # 5. Mars-Sun orbital distance and Top of Atmosphere (TOA) flux
        # Perihelion at Ls ≈ 251°
        nu = (ls_deg - 251.0) * DEG_TO_RAD
        e = MARS_ORBIT_ECCENTRICITY
        r_au = (MARS_SEMI_MAJOR_AXIS_AU * (1.0 - e**2)) / (1.0 + e * math.cos(nu))
        toa_flux = SOLAR_CONSTANT_1AU_W_M2 / (r_au**2)

        return SolarEphemeris(
            sol=sol,
            ltst_hours=ltst_hours,
            solar_longitude_ls_deg=ls_deg,
            solar_declination_deg=dec_deg,
            hour_angle_deg=h_deg,
            solar_elevation_deg=alpha_deg,
            solar_zenith_deg=zenith_deg,
            solar_azimuth_deg=azimuth_deg,
            sun_distance_au=r_au,
            toa_irradiance_w_m2=toa_flux,
            is_sun_above_horizon=alpha_deg > 0.0,
        )

    def compute_surface_incidence(
        self,
        slope_deg: float,
        aspect_deg: float,
        solar_elevation_deg: float,
        solar_azimuth_deg: float,
    ) -> Tuple[float, float, bool]:
        """
        Calculate solar incidence angle on a sloped surface.
        Returns: (incidence_angle_deg, cos_incidence, is_self_shadowed)
        """
        if solar_elevation_deg <= 0.0:
            return 90.0, 0.0, True

        zenith_rad = (90.0 - solar_elevation_deg) * DEG_TO_RAD
        slope_rad = slope_deg * DEG_TO_RAD
        aspect_rad = aspect_deg * DEG_TO_RAD
        sun_azimuth_rad = solar_azimuth_deg * DEG_TO_RAD

        # Cosine incidence formula:
        # cos(theta_i) = cos(slope)*cos(zenith) + sin(slope)*sin(zenith)*cos(sun_azimuth - aspect)
        cos_i = (
            math.cos(slope_rad) * math.cos(zenith_rad)
            + math.sin(slope_rad) * math.sin(zenith_rad) * math.cos(sun_azimuth_rad - aspect_rad)
        )

        is_self_shadowed = cos_i <= 0.0
        cos_i_clamped = min(max(cos_i, 0.0), 1.0)
        inc_angle_deg = math.acos(cos_i_clamped) * RAD_TO_DEG

        return inc_angle_deg, cos_i_clamped, is_self_shadowed

    def evaluate_point_illumination(
        self,
        row: float,
        col: float,
        elevation_grid: np.ndarray,
        slope_grid: np.ndarray,
        ephemeris: SolarEphemeris,
        aspect_grid: Optional[np.ndarray] = None,
        dx_ground_m: float = 18.972887,
        dy_ground_m: float = 20.000000,
        sensor_height_m: float = 2.0,
        max_ray_steps: int = 80,
        atmospheric_tau: float = 0.45,
    ) -> TerrainIlluminationResult:
        """
        Evaluate full illumination and 3D ray-cast shadow for a single point.
        """
        h_grid, w_grid = elevation_grid.shape
        r_int = int(round(min(max(row, 0), h_grid - 1)))
        c_int = int(round(min(max(col, 0), w_grid - 1)))

        z_pt = float(elevation_grid[r_int, c_int])
        slope = float(slope_grid[r_int, c_int])
        aspect = float(aspect_grid[r_int, c_int]) if aspect_grid is not None else 0.0

        # 1. Nighttime check
        if not ephemeris.is_sun_above_horizon:
            return TerrainIlluminationResult(
                row=row,
                col=col,
                elevation_m=z_pt,
                slope_deg=slope,
                aspect_deg=aspect,
                solar_elevation_deg=ephemeris.solar_elevation_deg,
                solar_azimuth_deg=ephemeris.solar_azimuth_deg,
                incidence_angle_deg=90.0,
                cos_incidence=0.0,
                is_daylight=False,
                is_self_shadowed=True,
                is_terrain_shadowed=False,
                is_illuminated=False,
                obstruction_distance_m=None,
                direct_flux_w_m2=0.0,
            )

        # 2. Surface slope self-shadow check
        inc_deg, cos_inc, is_self_shadow = self.compute_surface_incidence(
            slope_deg=slope,
            aspect_deg=aspect,
            solar_elevation_deg=ephemeris.solar_elevation_deg,
            solar_azimuth_deg=ephemeris.solar_azimuth_deg,
        )

        # 3. 3D Ray-cast horizon shadow check
        is_terrain_shadowed = False
        obs_dist_m: Optional[float] = None

        sun_az_rad = ephemeris.solar_azimuth_deg * DEG_TO_RAD
        tan_elev = math.tan(ephemeris.solar_elevation_deg * DEG_TO_RAD)

        # Vector step towards the sun:
        # Col increases East (+sin(az)), Row increases South (-cos(az))
        step_ground_m = min(dx_ground_m, dy_ground_m)
        d_col = (step_ground_m * math.sin(sun_az_rad)) / dx_ground_m
        d_row = (-step_ground_m * math.cos(sun_az_rad)) / dy_ground_m

        cur_r = row
        cur_c = col
        z_ray_origin = z_pt + sensor_height_m

        for step in range(1, max_ray_steps + 1):
            cur_r += d_row
            cur_c += d_col

            # Check if sampled pixel index clears the edge of the regional terrain grid
            sample_r = int(round(cur_r))
            sample_c = int(round(cur_c))
            if sample_r < 0 or sample_r >= h_grid or sample_c < 0 or sample_c >= w_grid:
                break

            step_ground_dist = step * step_ground_m
            ray_elev = z_ray_origin + (step_ground_dist * tan_elev)

            # Sample terrain elevation
            terrain_z = float(elevation_grid[sample_r, sample_c])

            # If terrain rises above ray, it casts a shadow
            if terrain_z > ray_elev:
                is_terrain_shadowed = True
                obs_dist_m = float(round(step_ground_dist, 1))
                break

        is_illuminated = ephemeris.is_sun_above_horizon and (not is_self_shadow) and (not is_terrain_shadowed)

        # Direct flux calculation with Beer-Lambert attenuation
        direct_flux = 0.0
        if is_illuminated:
            optical_airmass = 1.0 / max(0.05, math.sin(ephemeris.solar_elevation_deg * DEG_TO_RAD))
            attenuation = math.exp(-atmospheric_tau * optical_airmass)
            direct_flux = ephemeris.toa_irradiance_w_m2 * attenuation * cos_inc

        return TerrainIlluminationResult(
            row=row,
            col=col,
            elevation_m=z_pt,
            slope_deg=slope,
            aspect_deg=aspect,
            solar_elevation_deg=ephemeris.solar_elevation_deg,
            solar_azimuth_deg=ephemeris.solar_azimuth_deg,
            incidence_angle_deg=inc_deg,
            cos_incidence=cos_inc,
            is_daylight=ephemeris.is_sun_above_horizon,
            is_self_shadowed=is_self_shadow,
            is_terrain_shadowed=is_terrain_shadowed,
            is_illuminated=is_illuminated,
            obstruction_distance_m=obs_dist_m,
            direct_flux_w_m2=float(round(direct_flux, 1)),
        )

    def generate_illumination_raster(
        self,
        elevation_grid: np.ndarray,
        slope_grid: np.ndarray,
        ephemeris: SolarEphemeris,
        aspect_grid: Optional[np.ndarray] = None,
        stride: int = 2,
    ) -> np.ndarray:
        """
        Generate a downsampled 2D illumination mask (1.0 = illuminated, 0.0 = shadowed or night)
        for rapid frontend spatial visualization.
        """
        h, w = elevation_grid.shape
        out_h = (h + stride - 1) // stride
        out_w = (w + stride - 1) // stride
        mask = np.zeros((out_h, out_w), dtype=np.float32)

        if not ephemeris.is_sun_above_horizon:
            return mask

        for r_idx, r in enumerate(range(0, h, stride)):
            for c_idx, c in enumerate(range(0, w, stride)):
                res = self.evaluate_point_illumination(
                    row=float(r),
                    col=float(c),
                    elevation_grid=elevation_grid,
                    slope_grid=slope_grid,
                    ephemeris=ephemeris,
                    aspect_grid=aspect_grid,
                    max_ray_steps=40,
                )
                if res.is_illuminated:
                    mask[r_idx, c_idx] = 1.0

        return mask
