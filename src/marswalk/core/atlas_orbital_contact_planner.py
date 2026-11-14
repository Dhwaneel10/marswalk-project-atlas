"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Orbital Contact Planner
====================================================================
Physics-based orbital mechanics propagator and line-of-sight contact window
planner for Martian orbital constellations, surface settlements, and Earth DSN.
Features:
- Analytical two-body Keplerian propagator with Mars J2 gravitational secular perturbations.
- Exact Mars spherical body occultation detection.
- Elevation mask thresholding for surface ground stations and mobile rovers.
- Earth-Mars planetary geometry, Sun-Mars-Earth conjunction angles, and variable light time.
- Time-bounded contact schedule generation with link budget capacity integration.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_network_link_model import (
    CommunicationBand,
    CommunicationMedium,
    PhysicalLinkBudgetEngine,
    SPEED_OF_LIGHT_M_S,
    ASTRONOMICAL_UNIT_M,
)
from marswalk.core.atlas_planetary_network_architecture import (
    PlanetaryNode,
    PlanetaryNodeType,
    PlanetaryNetworkTopology,
)

# Fundamental Martian Astrodynamics Constants
MARS_RADIUS_M: float = 3_396_190.0
MARS_MU_M3_S2: float = 4.282837e13           # Standard gravitational parameter (G * M_mars)
MARS_ROTATION_PERIOD_S: float = 88_775.244   # 1 Martian Sol in seconds
MARS_ROTATION_RATE_RAD_S: float = (2.0 * math.pi) / MARS_ROTATION_PERIOD_S
MARS_J2: float = 1.96045e-3                  # Second zonal harmonic
MARS_ATMOSPHERE_MASK_M: float = 20_000.0     # 20 km atmospheric extinction boundary


@dataclass
class KeplerianElements:
    """Classical orbital elements defining a spacecraft orbit around Mars."""
    semi_major_axis_m: float
    eccentricity: float
    inclination_rad: float
    raan_rad: float                 # Right Ascension of Ascending Node (Omega)
    arg_periapsis_rad: float        # Argument of periapsis (omega)
    mean_anomaly_epoch_rad: float   # Mean anomaly at epoch t0 (M0)
    epoch_time_s: float = 0.0

    @classmethod
    def from_degrees(
        cls,
        semi_major_axis_km: float,
        eccentricity: float,
        inclination_deg: float,
        raan_deg: float = 0.0,
        arg_periapsis_deg: float = 0.0,
        mean_anomaly_deg: float = 0.0,
        epoch_time_s: float = 0.0,
    ) -> KeplerianElements:
        return cls(
            semi_major_axis_m=semi_major_axis_km * 1000.0,
            eccentricity=eccentricity,
            inclination_rad=math.radians(inclination_deg),
            raan_rad=math.radians(raan_deg),
            arg_periapsis_rad=math.radians(arg_periapsis_deg),
            mean_anomaly_epoch_rad=math.radians(mean_anomaly_deg),
            epoch_time_s=epoch_time_s,
        )

    @property
    def orbital_period_s(self) -> float:
        return 2.0 * math.pi * math.sqrt((self.semi_major_axis_m ** 3) / MARS_MU_M3_S2)

    @property
    def mean_motion_rad_s(self) -> float:
        return math.sqrt(MARS_MU_M3_S2 / (self.semi_major_axis_m ** 3))

    @property
    def semi_latus_rectum_m(self) -> float:
        return self.semi_major_axis_m * (1.0 - (self.eccentricity ** 2))

    def j2_secular_drift_rates(self) -> Tuple[float, float]:
        """
        Returns (raan_rate_rad_s, arg_periapsis_rate_rad_s) due to Mars J2 harmonic.
        """
        p = self.semi_latus_rectum_m
        if p <= MARS_RADIUS_M:
            return 0.0, 0.0
        n = self.mean_motion_rad_s
        factor = 1.5 * MARS_J2 * ((MARS_RADIUS_M / p) ** 2) * n
        cos_i = math.cos(self.inclination_rad)
        sin_i = math.sin(self.inclination_rad)

        raan_dot = -factor * cos_i
        omega_dot = factor * (2.0 - 2.5 * (sin_i ** 2))
        return raan_dot, omega_dot

    def propagate_to_mcmf_position(self, sim_time_s: float) -> Tuple[float, float, float]:
        """
        Propagates Keplerian orbit with J2 secular drift to cartesian position (X, Y, Z)
        in Mars-Centered Mars-Fixed (MCMF) rotating frame at simulation time `sim_time_s`.
        """
        dt = sim_time_s - self.epoch_time_s
        raan_dot, omega_dot = self.j2_secular_drift_rates()

        current_raan = (self.raan_rad + raan_dot * dt) % (2.0 * math.pi)
        current_omega = (self.arg_periapsis_rad + omega_dot * dt) % (2.0 * math.pi)
        current_mean_anomaly = (self.mean_anomaly_epoch_rad + self.mean_motion_rad_s * dt) % (2.0 * math.pi)

        # Solve Kepler's equation: M = E - e*sin(E) via Newton-Raphson
        E = current_mean_anomaly
        for _ in range(12):
            f = E - self.eccentricity * math.sin(E) - current_mean_anomaly
            f_prime = 1.0 - self.eccentricity * math.cos(E)
            delta = f / f_prime
            E -= delta
            if abs(delta) < 1e-9:
                break

        # True anomaly nu
        sin_half_nu = math.sqrt(max(0.0, 1.0 + self.eccentricity)) * math.sin(E / 2.0)
        cos_half_nu = math.sqrt(max(0.0, 1.0 - self.eccentricity)) * math.cos(E / 2.0)
        nu = 2.0 * math.atan2(sin_half_nu, cos_half_nu)

        r = self.semi_major_axis_m * (1.0 - self.eccentricity * math.cos(E))

        # Perifocal coordinates
        x_peri = r * math.cos(nu)
        y_peri = r * math.sin(nu)
        z_peri = 0.0

        # Rotate to Mars-Centered Inertial (MCI) via Euler angles (current_omega, inc, current_raan)
        # Transformation matrix components:
        cos_o = math.cos(current_omega)
        sin_o = math.sin(current_omega)
        cos_i = math.cos(self.inclination_rad)
        sin_i = math.sin(self.inclination_rad)
        cos_O = math.cos(current_raan)
        sin_O = math.sin(current_raan)

        # Combined rotation P_x, P_y, P_z
        px = cos_O * cos_o - sin_O * sin_o * cos_i
        py = sin_O * cos_o + cos_O * sin_o * cos_i
        pz = sin_o * sin_i

        qx = -cos_O * sin_o - sin_O * cos_o * cos_i
        qy = -sin_O * sin_o + cos_O * cos_o * cos_i
        qz = cos_o * sin_i

        x_mci = x_peri * px + y_peri * qx
        y_mci = x_peri * py + y_peri * qy
        z_mci = x_peri * pz + y_peri * qz

        # Rotate MCI to Mars-Centered Mars-Fixed (MCMF) by Mars rotation angle theta_M
        theta_m = (MARS_ROTATION_RATE_RAD_S * sim_time_s) % (2.0 * math.pi)
        cos_m = math.cos(theta_m)
        sin_m = math.sin(theta_m)

        x_mcmf = x_mci * cos_m + y_mci * sin_m
        y_mcmf = -x_mci * sin_m + y_mci * cos_m
        z_mcmf = z_mci

        return (x_mcmf, y_mcmf, z_mcmf)


# Default orbital configurations for standard Atlas orbiters
STANDARD_ORBITER_ELEMENTS: Dict[str, KeplerianElements] = {
    # ATLAS-ORB-01: Ares-SunSync (Polar circular 400 km, ~93.0°)
    "ATLAS-ORB-01": KeplerianElements.from_degrees(
        semi_major_axis_km=3796.19,
        eccentricity=0.001,
        inclination_deg=93.0,
        raan_deg=45.0,
        arg_periapsis_deg=0.0,
        mean_anomaly_deg=0.0,
    ),
    # ATLAS-ORB-02: Hellas-Polar (Elliptical 400x1600 km, 63.4° critical inclination)
    "ATLAS-ORB-02": KeplerianElements.from_degrees(
        semi_major_axis_km=4396.19,
        eccentricity=0.13648,
        inclination_deg=63.4,
        raan_deg=135.0,
        arg_periapsis_deg=270.0,
        mean_anomaly_deg=180.0,
    ),
    # ATLAS-ORB-03: Areostationary (Equatorial synchronous 17,032 km altitude)
    "ATLAS-ORB-03": KeplerianElements.from_degrees(
        semi_major_axis_km=20428.19,
        eccentricity=0.0,
        inclination_deg=0.0,
        raan_deg=0.0,
        arg_periapsis_deg=0.0,
        mean_anomaly_deg=75.0,  # 75°E sub-satellite longitude
    ),
    # ATLAS-ORB-04: Odyssey-UHF (Circular 390 km, 93.5°)
    "ATLAS-ORB-04": KeplerianElements.from_degrees(
        semi_major_axis_km=3786.19,
        eccentricity=0.002,
        inclination_deg=93.5,
        raan_deg=225.0,
        arg_periapsis_deg=90.0,
        mean_anomaly_deg=90.0,
    ),
}


@dataclass
class ContactWindow:
    """A verified, physically feasible communication window between two network nodes."""
    contact_id: str
    src_node_id: str
    dst_node_id: str
    start_time_s: float
    end_time_s: float
    band: CommunicationBand
    min_range_m: float
    max_range_m: float
    avg_range_m: float
    max_elevation_deg: float
    achievable_rate_bps: int
    total_capacity_bytes: int
    propagation_delay_s: float
    is_bidirectional: bool = True

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_time_s - self.start_time_s)

    def is_active_at(self, sim_time_s: float) -> bool:
        return self.start_time_s <= sim_time_s <= self.end_time_s

    def remaining_duration_s(self, sim_time_s: float) -> float:
        if sim_time_s < self.start_time_s:
            return self.duration_s
        if sim_time_s > self.end_time_s:
            return 0.0
        return self.end_time_s - sim_time_s

    def remaining_capacity_bytes(self, sim_time_s: float) -> int:
        rem_dur = self.remaining_duration_s(sim_time_s)
        return int((rem_dur * self.achievable_rate_bps) / 8.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "src": self.src_node_id,
            "dst": self.dst_node_id,
            "start_time_s": round(self.start_time_s, 1),
            "end_time_s": round(self.end_time_s, 1),
            "duration_s": round(self.duration_s, 1),
            "band": self.band.value,
            "avg_range_km": round(self.avg_range_m / 1000.0, 1),
            "max_elevation_deg": round(self.max_elevation_deg, 1),
            "rate_kbps": round(self.achievable_rate_bps / 1000.0, 1),
            "capacity_mb": round(self.total_capacity_bytes / 1e6, 2),
            "propagation_delay_s": round(self.propagation_delay_s, 6),
        }


class OrbitalContactPlanner:
    """Calculates orbital ephemerides, occultations, and multi-sol contact schedules."""

    def __init__(
        self,
        topology: PlanetaryNetworkTopology,
        orbit_elements: Optional[Dict[str, KeplerianElements]] = None,
        mars_dust_tau: float = 0.5,
        earth_mars_distance_au: float = 1.5,  # Nominal orbital distance ~1.5 AU (~12.5 min light time)
        is_solar_conjunction: bool = False,
    ) -> None:
        self.topology = topology
        self.orbit_elements = orbit_elements or copy.deepcopy(STANDARD_ORBITER_ELEMENTS)
        self.mars_dust_tau = mars_dust_tau
        self.earth_mars_distance_au = earth_mars_distance_au
        self.is_solar_conjunction = is_solar_conjunction

    def get_surface_node_mcmf_position(self, node: PlanetaryNode) -> Tuple[float, float, float]:
        """Calculates 3D cartesian coordinates of a surface node in MCMF frame."""
        lat_rad = math.radians(node.latitude_deg)
        lon_rad = math.radians(node.longitude_deg)
        r = MARS_RADIUS_M + node.altitude_m
        x = r * math.cos(lat_rad) * math.cos(lon_rad)
        y = r * math.cos(lat_rad) * math.sin(lon_rad)
        z = r * math.sin(lat_rad)
        return (x, y, z)

    def get_node_position(self, node_id: str, sim_time_s: float) -> Tuple[float, float, float]:
        """Returns MCMF 3D cartesian position (X, Y, Z) in meters for any node at `sim_time_s`."""
        node = self.topology.get_node(node_id)
        if not node:
            return (0.0, 0.0, 0.0)

        if node.is_orbital:
            if node_id in self.orbit_elements:
                return self.orbit_elements[node_id].propagate_to_mcmf_position(sim_time_s)
            else:
                # Fallback circular equatorial approximation
                r = MARS_RADIUS_M + node.altitude_m
                lon = math.radians(node.longitude_deg)
                return (r * math.cos(lon), r * math.sin(lon), 0.0)
        elif node.is_earth:
            # Model Earth DSN position vector relative to Mars center in MCMF coordinates
            dist_m = self.earth_mars_distance_au * ASTRONOMICAL_UNIT_M
            # Earth moves slowly over solar time scale; approximate line-of-sight along +X axis
            # modulated by Mars rotation
            theta_m = (MARS_ROTATION_RATE_RAD_S * sim_time_s) % (2.0 * math.pi)
            x = dist_m * math.cos(theta_m)
            y = -dist_m * math.sin(theta_m)
            z = dist_m * math.sin(math.radians(25.19))  # Mars obliquity 25.19°
            return (x, y, z)
        else:
            return self.get_surface_node_mcmf_position(node)

    @staticmethod
    def is_line_of_sight_occulted_by_mars(
        pos1: Tuple[float, float, float],
        pos2: Tuple[float, float, float],
        mask_radius_m: float = MARS_RADIUS_M + MARS_ATMOSPHERE_MASK_M,
    ) -> bool:
        """
        Determines whether the straight line segment between pos1 and pos2 intersects
        the spherical Mars occultation horizon.
        Ray: r(t) = pos1 + t * (pos2 - pos1) for t in [0, 1].
        """
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        dz = pos2[2] - pos1[2]
        d_sq = dx * dx + dy * dy + dz * dz
        if d_sq <= 1e-6:
            return False

        # Projection parameter t* of Mars center (0,0,0) onto ray segment
        t_star = -(pos1[0] * dx + pos1[1] * dy + pos1[2] * dz) / d_sq
        if t_star <= 0.0 or t_star >= 1.0:
            # Closest point is outside segment; check endpoints
            r1_sq = pos1[0] ** 2 + pos1[1] ** 2 + pos1[2] ** 2
            r2_sq = pos2[0] ** 2 + pos2[1] ** 2 + pos2[2] ** 2
            return min(r1_sq, r2_sq) < (mask_radius_m ** 2)

        # Closest point along the segment
        cx = pos1[0] + t_star * dx
        cy = pos1[1] + t_star * dy
        cz = pos1[2] + t_star * dz
        min_dist_sq = cx * cx + cy * cy + cz * cz
        return min_dist_sq <= (mask_radius_m ** 2)

    def calculate_surface_elevation_deg(
        self,
        surface_node: PlanetaryNode,
        target_pos: Tuple[float, float, float],
    ) -> float:
        """Calculates elevation angle of target above local horizontal tangent plane."""
        surf_pos = self.get_surface_node_mcmf_position(surface_node)
        rx = target_pos[0] - surf_pos[0]
        ry = target_pos[1] - surf_pos[1]
        rz = target_pos[2] - surf_pos[2]
        slant_range = math.sqrt(rx * rx + ry * ry + rz * rz)
        if slant_range <= 1.0:
            return 90.0

        # Local surface normal (unit vector pointing up from center of spherical Mars)
        surf_mag = math.sqrt(surf_pos[0] ** 2 + surf_pos[1] ** 2 + surf_pos[2] ** 2)
        up_x = surf_pos[0] / surf_mag
        up_y = surf_pos[1] / surf_mag
        up_z = surf_pos[2] / surf_mag

        # dot product = |range| * sin(elevation)
        dot = (rx * up_x + ry * up_y + rz * up_z) / slant_range
        dot = max(-1.0, min(1.0, dot))
        return math.degrees(math.asin(dot))

    def evaluate_instantaneous_contact(
        self,
        src_id: str,
        dst_id: str,
        sim_time_s: float,
    ) -> Optional[Tuple[CommunicationBand, float, float, int]]:
        """
        Tests if a closed communication link exists between src and dst at `sim_time_s`.
        Returns (band, range_m, elevation_deg, operational_rate_bps) if open, or None.
        """
        src = self.topology.get_node(src_id)
        dst = self.topology.get_node(dst_id)
        if not src or not dst or not src.is_active or not dst.is_active:
            return None

        # Solar conjunction blocks Earth links completely
        if self.is_solar_conjunction and (src.is_earth or dst.is_earth):
            return None

        bands = self.topology.get_shared_communication_bands(src_id, dst_id)
        if not bands:
            return None

        pos_src = self.get_node_position(src_id, sim_time_s)
        pos_dst = self.get_node_position(dst_id, sim_time_s)

        rx = pos_dst[0] - pos_src[0]
        ry = pos_dst[1] - pos_src[1]
        rz = pos_dst[2] - pos_src[2]
        slant_range = math.sqrt(rx * rx + ry * ry + rz * rz)

        # 1. Check line-of-sight occultation
        if src.is_orbital and dst.is_orbital:
            # Orbiter-to-orbiter crosslink
            if self.is_line_of_sight_occulted_by_mars(pos_src, pos_dst):
                return None
            elevation = 90.0
        elif src.is_earth or dst.is_earth:
            # Deep space link to Earth
            if src.is_surface or dst.is_surface:
                # Surface DTE: Must face Earth with positive elevation
                surf = src if src.is_surface else dst
                elevation = self.calculate_surface_elevation_deg(surf, pos_dst if src.is_surface else pos_src)
                if elevation < 10.0:
                    return None
            else:
                # Orbiter to Earth: check Mars occultation
                orb_pos = pos_src if src.is_orbital else pos_dst
                earth_pos = pos_dst if src.is_orbital else pos_src
                if self.is_line_of_sight_occulted_by_mars(orb_pos, earth_pos):
                    return None
                elevation = 90.0
        elif src.is_surface and dst.is_surface:
            # Surface-to-surface link: check static backbone connectivity
            if not (self.topology.has_static_surface_link(src_id, dst_id) or self.topology.has_static_surface_link(dst_id, src_id)):
                # Mobile asset direct line of sight within 25 km
                if slant_range > 25_000.0:
                    return None
            elevation = 5.0
        else:
            # Surface to Orbiter proximity pass
            surf = src if src.is_surface else dst
            orb_pos = pos_dst if src.is_surface else pos_src
            elevation = self.calculate_surface_elevation_deg(surf, orb_pos)
            if elevation < 5.0:  # 5° elevation mask
                return None

        # 2. Evaluate physical link budget for preferred communication band
        # Select best band with closed link and highest rate
        best_band: Optional[CommunicationBand] = None
        best_rate: int = 0

        for band in bands:
            tx = src.transmitters[band]
            rx_spec = dst.receivers[band]
            res = PhysicalLinkBudgetEngine.evaluate_link(
                tx=tx,
                rx=rx_spec,
                slant_range_m=slant_range,
                elevation_deg=elevation,
                dust_tau=self.mars_dust_tau,
            )
            if (
                res.is_link_closed
                and res.is_physically_available
                and res.communication_medium in (CommunicationMedium.RF_WIRELESS, CommunicationMedium.OPTICAL_FREE_SPACE)
                and res.operational_rate_bps > best_rate
            ):
                best_rate = res.operational_rate_bps
                best_band = band

        if best_band and best_rate > 0:
            return (best_band, slant_range, elevation, best_rate)
        return None

    def plan_contact_schedule(
        self,
        start_time_s: float,
        end_time_s: float,
        time_step_s: float = 60.0,
    ) -> List[ContactWindow]:
        """
        Samples network geometry at discrete intervals `time_step_s` over `[start_time_s, end_time_s]`
        and stitches continuous intervals into discrete `ContactWindow` instances.
        """
        # Node pairs to evaluate:
        # Settlements <-> Orbiters
        # Rovers/Aero <-> Orbiters
        # Settlements <-> Settlements (static surface)
        # Settlements/Rovers <-> Fixed Relays
        # Orbiters <-> Orbiters (Crosslinks)
        # Orbiters/Settlements <-> Earth DSN
        pairs: List[Tuple[str, str]] = []
        all_nodes = self.topology.get_all_nodes()

        for i, n1 in enumerate(all_nodes):
            for n2 in all_nodes[i + 1 :]:
                # Skip mobile <-> mobile if different regions
                if n1.is_surface and n2.is_surface and not (
                    self.topology.has_static_surface_link(n1.node_id, n2.node_id)
                    or (n1.node_type in (PlanetaryNodeType.MOBILE_ROVER, PlanetaryNodeType.MOBILE_AERIAL) and abs(n1.latitude_deg - n2.latitude_deg) < 1.0)
                ):
                    continue
                pairs.append((n1.node_id, n2.node_id))

        contact_windows: List[ContactWindow] = []
        window_counter = 1

        for src_id, dst_id in pairs:
            active_start: Optional[float] = None
            samples: List[Tuple[float, CommunicationBand, float, float, int]] = []

            curr_t = start_time_s
            while curr_t <= end_time_s:
                res = self.evaluate_instantaneous_contact(src_id, dst_id, curr_t)
                if res is not None:
                    band, slant_range, elevation, rate = res
                    if active_start is None:
                        active_start = curr_t
                    samples.append((curr_t, band, slant_range, elevation, rate))
                else:
                    if active_start is not None and samples:
                        # Close window
                        w = self._create_window_from_samples(
                            window_id=f"CW-{window_counter:04d}",
                            src_id=src_id,
                            dst_id=dst_id,
                            samples=samples,
                        )
                        contact_windows.append(w)
                        window_counter += 1
                        active_start = None
                        samples = []
                curr_t += time_step_s

            if active_start is not None and samples:
                w = self._create_window_from_samples(
                    window_id=f"CW-{window_counter:04d}",
                    src_id=src_id,
                    dst_id=dst_id,
                    samples=samples,
                )
                contact_windows.append(w)
                window_counter += 1

        # Sort contact windows by start time
        contact_windows.sort(key=lambda cw: (cw.start_time_s, cw.src_node_id, cw.dst_node_id))
        return contact_windows

    def _create_window_from_samples(
        self,
        window_id: str,
        src_id: str,
        dst_id: str,
        samples: List[Tuple[float, CommunicationBand, float, float, int]],
    ) -> ContactWindow:
        start_t = samples[0][0]
        end_t = samples[-1][0]
        # Pad end time by 1 step if single sample
        if end_t == start_t:
            end_t += 60.0

        ranges = [s[2] for s in samples]
        elevations = [s[3] for s in samples]
        rates = [s[4] for s in samples]
        band = samples[0][1]

        avg_range = sum(ranges) / len(ranges)
        min_range = min(ranges)
        max_range = max(ranges)
        max_elev = max(elevations)
        achievable_rate = min(rates)  # Conservative bottleneck rate across the pass
        duration = max(1.0, end_t - start_t)
        total_cap_bytes = int((duration * achievable_rate) / 8.0)
        prop_delay = avg_range / SPEED_OF_LIGHT_M_S

        return ContactWindow(
            contact_id=window_id,
            src_node_id=src_id,
            dst_node_id=dst_id,
            start_time_s=start_t,
            end_time_s=end_t,
            band=band,
            min_range_m=min_range,
            max_range_m=max_range,
            avg_range_m=avg_range,
            max_elevation_deg=max_elev,
            achievable_rate_bps=achievable_rate,
            total_capacity_bytes=total_cap_bytes,
            propagation_delay_s=prop_delay,
        )
