"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Settlement Site Selection Engine.

Evaluates candidate Martian infrastructure sites across terrain mechanics,
environmental extremes, landing zone access, communications coverage,
and NASA Subsurface Water Ice Mapping (SWIM) resource uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class WaterEvidenceConfidence(str, Enum):
    """Rigorous categorization of planetary water-resource indications.

    Preserves scientific honesty by refusing to equate speculative orbital proxies
    with extractable ground-truth reserves.
    """
    ORBITAL_INDICATION = "ORBITAL_INDICATION"            # Epithermal neutron (MONS) or SHARAD radar dielectric anomaly
    GEOLOGICALLY_INFERRED = "GEOLOGICALLY_INFERRED"      # Periglacial geomorphology, lobate aprons, or layered sulfate beds
    RESOURCE_CANDIDATE = "RESOURCE_CANDIDATE"            # Multi-instrument spatial agreement with bounded overburden
    LOCALLY_CHARACTERIZED = "LOCALLY_CHARACTERIZED"      # In-situ rover ground-penetrating radar (RIMFAX) sounding
    SIMULATED_EXTRACTABLE = "SIMULATED_EXTRACTABLE"      # Engineering model assumption with declared uncertainty bounds


@dataclass
class TerrainSuitability:
    """Quantitative terrain characteristics for surface construction."""
    mean_slope_deg: float
    max_slope_deg: float
    surface_roughness_rms_m: float
    elevation_m: float
    local_relief_m: float
    bearing_capacity_kpa: float
    clearing_difficulty_index: float       # 0.0 (smooth dust) to 1.0 (dense boulder field)
    flat_contiguous_area_m2: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean_slope_deg": round(self.mean_slope_deg, 2),
            "max_slope_deg": round(self.max_slope_deg, 2),
            "surface_roughness_rms_m": round(self.surface_roughness_rms_m, 3),
            "elevation_m": round(self.elevation_m, 1),
            "local_relief_m": round(self.local_relief_m, 2),
            "bearing_capacity_kpa": round(self.bearing_capacity_kpa, 1),
            "clearing_difficulty_index": round(self.clearing_difficulty_index, 3),
            "flat_contiguous_area_m2": round(self.flat_contiguous_area_m2, 0),
        }


@dataclass
class EnvironmentalSuitability:
    """Environmental parameters affecting infrastructure longevity."""
    diurnal_temp_min_c: float
    diurnal_temp_max_c: float
    mean_solar_insolation_wm2: float
    annual_solar_swing_pct: float
    atmospheric_density_g_m3: float
    mean_wind_speed_mps: float
    dust_deposition_rate_um_per_sol: float
    regional_dust_storm_risk: str          # "LOW", "MODERATE", "HIGH", "EXTREME"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diurnal_temp_min_c": round(self.diurnal_temp_min_c, 1),
            "diurnal_temp_max_c": round(self.diurnal_temp_max_c, 1),
            "mean_solar_insolation_wm2": round(self.mean_solar_insolation_wm2, 1),
            "annual_solar_swing_pct": round(self.annual_solar_swing_pct, 1),
            "atmospheric_density_g_m3": round(self.atmospheric_density_g_m3, 3),
            "mean_wind_speed_mps": round(self.mean_wind_speed_mps, 2),
            "dust_deposition_rate_um_per_sol": round(self.dust_deposition_rate_um_per_sol, 3),
            "regional_dust_storm_risk": self.regional_dust_storm_risk,
        }


@dataclass
class ResourcePotential:
    """Scientific evaluation of local in-situ resource deposits."""
    water_evidence_level: WaterEvidenceConfidence
    estimated_water_wt_pct: float          # Mineral hydration wt% or subsurface pore ice wt%
    water_estimate_uncertainty_pct: float  # e.g., 40.0 means 40% relative uncertainty
    overburden_depth_m: float              # Thickness of dry regolith/talus covering deposit
    regolith_usability_grade: str          # "HIGH_SILICA", "BASALTIC_CLAY", "SULFATE_RICH", "AEOLIAN_SAND"
    extraction_energy_kwh_per_kg: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "water_evidence_level": self.water_evidence_level.value,
            "estimated_water_wt_pct": round(self.estimated_water_wt_pct, 2),
            "water_estimate_uncertainty_pct": round(self.water_estimate_uncertainty_pct, 1),
            "overburden_depth_m": round(self.overburden_depth_m, 2),
            "regolith_usability_grade": self.regolith_usability_grade,
            "extraction_energy_kwh_per_kg": round(self.extraction_energy_kwh_per_kg, 3),
        }


@dataclass
class OperationalSuitability:
    """Operational constraints for landing, mobility, and communications."""
    landing_zone_clearance_radius_m: float
    comms_line_of_sight_pct: float         # Percentage of sol with direct line-of-sight to orbiter relays
    dte_visibility_hours_per_sol: float    # Direct-to-Earth elevation > 10 deg
    rover_traverse_connectivity_index: float # 0.0 to 1.0 (ease of rover ingress/egress)
    nuclear_safe_standoff_distance_m: float # Required distance from reactor to crew habitat (e.g., 1000m)
    expansion_corridors_available: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "landing_zone_clearance_radius_m": round(self.landing_zone_clearance_radius_m, 1),
            "comms_line_of_sight_pct": round(self.comms_line_of_sight_pct, 1),
            "dte_visibility_hours_per_sol": round(self.dte_visibility_hours_per_sol, 1),
            "rover_traverse_connectivity_index": round(self.rover_traverse_connectivity_index, 2),
            "nuclear_safe_standoff_distance_m": round(self.nuclear_safe_standoff_distance_m, 1),
            "expansion_corridors_available": self.expansion_corridors_available,
        }


@dataclass
class CandidateSettlementSite:
    """Full multidimensional profile of a candidate Martian settlement location."""
    site_id: str
    name: str
    latitude_deg: float
    longitude_deg: float
    terrain: TerrainSuitability
    environment: EnvironmentalSuitability
    resources: ResourcePotential
    operations: OperationalSuitability
    strengths: List[str]
    weaknesses: List[str]
    missing_data_gaps: List[str]
    primary_risks: List[str]
    recommended_reconnaissance: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "name": self.name,
            "latitude_deg": round(self.latitude_deg, 5),
            "longitude_deg": round(self.longitude_deg, 5),
            "terrain": self.terrain.to_dict(),
            "environment": self.environment.to_dict(),
            "resources": self.resources.to_dict(),
            "operations": self.operations.to_dict(),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "missing_data_gaps": self.missing_data_gaps,
            "primary_risks": self.primary_risks,
            "recommended_reconnaissance": self.recommended_reconnaissance,
        }


class SettlementSiteSelectionEngine:
    """Multi-criteria planetary settlement site evaluator for the Jezero region."""

    def __init__(self):
        self._candidates: Dict[str, CandidateSettlementSite] = self._build_candidate_catalog()

    def get_candidate_sites(self) -> List[CandidateSettlementSite]:
        return list(self._candidates.values())

    def get_site(self, site_id: str) -> Optional[CandidateSettlementSite]:
        return self._candidates.get(site_id)

    def compare_sites(self, site_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Produces transparent multi-attribute comparative trade study."""
        selected_ids = site_ids or list(self._candidates.keys())
        sites = [self._candidates[sid] for sid in selected_ids if sid in self._candidates]
        return [s.to_dict() for s in sites]

    def _build_candidate_catalog(self) -> Dict[str, CandidateSettlementSite]:
        catalog: Dict[str, CandidateSettlementSite] = {}

        # 1. SITE-DELTA-NORTH: Northern Fan Delta Terrace
        catalog["SITE-DELTA-NORTH"] = CandidateSettlementSite(
            site_id="SITE-DELTA-NORTH",
            name="Jezero Northern Fan Delta Terrace",
            latitude_deg=18.4421,
            longitude_deg=77.4528,
            terrain=TerrainSuitability(
                mean_slope_deg=3.2,
                max_slope_deg=7.5,
                surface_roughness_rms_m=0.18,
                elevation_m=-2540.0,
                local_relief_m=12.0,
                bearing_capacity_kpa=145.0,
                clearing_difficulty_index=0.25,
                flat_contiguous_area_m2=125000.0,
            ),
            environment=EnvironmentalSuitability(
                diurnal_temp_min_c=-88.5,
                diurnal_temp_max_c=-14.2,
                mean_solar_insolation_wm2=575.0,
                annual_solar_swing_pct=28.5,
                atmospheric_density_g_m3=0.0162,
                mean_wind_speed_mps=6.8,
                dust_deposition_rate_um_per_sol=0.042,
                regional_dust_storm_risk="MODERATE",
            ),
            resources=ResourcePotential(
                water_evidence_level=WaterEvidenceConfidence.RESOURCE_CANDIDATE,
                estimated_water_wt_pct=6.8,  # Hydrated smectite clays & carbonate minerals
                water_estimate_uncertainty_pct=25.0,
                overburden_depth_m=0.8,
                regolith_usability_grade="BASALTIC_CLAY",
                extraction_energy_kwh_per_kg=1.85, # Thermal dehydration of phyllosilicates
            ),
            operations=OperationalSuitability(
                landing_zone_clearance_radius_m=650.0,
                comms_line_of_sight_pct=88.5,
                dte_visibility_hours_per_sol=14.2,
                rover_traverse_connectivity_index=0.82,
                nuclear_safe_standoff_distance_m=1200.0,
                expansion_corridors_available=3,
            ),
            strengths=[
                "High concentration of hydrated phyllosilicates (6.8 wt% mineral water equivalent).",
                "Gentle 3.2 degree terrace slope provides natural terrain shielding from crater floor winds.",
                "Direct rover mobility access to ancient lakebed delta sedimentary sequences.",
            ],
            weaknesses=[
                "Excavating clays requires higher thermal dehydration energy than pure water ice.",
                "Moderate boulder coverage requiring robotic clearing before module landing.",
            ],
            missing_data_gaps=[
                "Exact subsurface clay layer thickness (RIMFAX radargram limited to 15m depth).",
                "Presence of corrosive perchlorate salts in local clay matrix.",
            ],
            primary_risks=[
                "Thermal cracking in rigid foundations during winter -88.5C cold-soak.",
                "Erosion of unpaved landing zone plume berms during repeated rocket landings.",
            ],
            recommended_reconnaissance="Autonomous rotorcraft low-altitude hyperspectral swath and drill core sample return.",
        )

        # 2. SITE-CRATER-FLOOR: Jezero Central Crater Floor Plain
        catalog["SITE-CRATER-FLOOR"] = CandidateSettlementSite(
            site_id="SITE-CRATER-FLOOR",
            name="Jezero Central Crater Floor Plain",
            latitude_deg=18.3810,
            longitude_deg=77.5840,
            terrain=TerrainSuitability(
                mean_slope_deg=1.1,
                max_slope_deg=2.8,
                surface_roughness_rms_m=0.08,
                elevation_m=-2580.0,
                local_relief_m=4.5,
                bearing_capacity_kpa=190.0,
                clearing_difficulty_index=0.08,
                flat_contiguous_area_m2=450000.0,
            ),
            environment=EnvironmentalSuitability(
                diurnal_temp_min_c=-94.0,
                diurnal_temp_max_c=-12.0,
                mean_solar_insolation_wm2=588.0,
                annual_solar_swing_pct=26.0,
                atmospheric_density_g_m3=0.0168,
                mean_wind_speed_mps=8.2,
                dust_deposition_rate_um_per_sol=0.065, # Higher aeolian dust deposition on floor
                regional_dust_storm_risk="HIGH",
            ),
            resources=ResourcePotential(
                water_evidence_level=WaterEvidenceConfidence.ORBITAL_INDICATION,
                estimated_water_wt_pct=2.1,  # Dry volcanic basalt with minor olivine alteration
                water_estimate_uncertainty_pct=55.0,
                overburden_depth_m=3.5,
                regolith_usability_grade="AEOLIAN_SAND",
                extraction_energy_kwh_per_kg=3.95,
            ),
            operations=OperationalSuitability(
                landing_zone_clearance_radius_m=1500.0,
                comms_line_of_sight_pct=94.0,
                dte_visibility_hours_per_sol=15.0,
                rover_traverse_connectivity_index=0.95,
                nuclear_safe_standoff_distance_m=2500.0,
                expansion_corridors_available=5,
            ),
            strengths=[
                "Extremely flat, unobstructed landing zone exceeding 1.5 km clear radius.",
                "Highest bearing capacity (190 kPa) on dense basaltic bedrock.",
                "Unconstrained spatial capacity for large nuclear fission reactor standoff.",
            ],
            weaknesses=[
                "Poor in-situ water content (<2.1 wt%); water must be hauled from delta deposits.",
                "High aeolian dust accumulation rapidly degrades solar photovoltaic performance.",
            ],
            missing_data_gaps=[
                "Subsurface basalt fracture porosity and deep groundwater history.",
            ],
            primary_risks=[
                "Synoptic dust storm obscuration starving solar arrays.",
                "High thermal diurnal shock (-94C to -12C swing of 82C per sol).",
            ],
            recommended_reconnaissance="Deep seismic refraction profile to verify bedrock compaction depth.",
        )

        # 3. SITE-NERETVA-VALIS: Neretva Vallis Inflow Channel Outcrop
        catalog["SITE-NERETVA-VALIS"] = CandidateSettlementSite(
            site_id="SITE-NERETVA-VALIS",
            name="Neretva Vallis Inflow Channel Outcrop",
            latitude_deg=18.4890,
            longitude_deg=77.3410,
            terrain=TerrainSuitability(
                mean_slope_deg=5.8,
                max_slope_deg=14.2,
                surface_roughness_rms_m=0.32,
                elevation_m=-2420.0,
                local_relief_m=45.0,
                bearing_capacity_kpa=160.0,
                clearing_difficulty_index=0.48,
                flat_contiguous_area_m2=65000.0,
            ),
            environment=EnvironmentalSuitability(
                diurnal_temp_min_c=-82.0, # Sheltered valley reduces radiative night cooling
                diurnal_temp_max_c=-16.5,
                mean_solar_insolation_wm2=510.0, # Valley walls shadow morning/evening sun
                annual_solar_swing_pct=38.0,
                atmospheric_density_g_m3=0.0158,
                mean_wind_speed_mps=4.5,
                dust_deposition_rate_um_per_sol=0.035,
                regional_dust_storm_risk="LOW",
            ),
            resources=ResourcePotential(
                water_evidence_level=WaterEvidenceConfidence.GEOLOGICALLY_INFERRED,
                estimated_water_wt_pct=8.4,  # Deep hydrated phyllosilicate channel bed
                water_estimate_uncertainty_pct=35.0,
                overburden_depth_m=1.2,
                regolith_usability_grade="SULFATE_RICH",
                extraction_energy_kwh_per_kg=1.65,
            ),
            operations=OperationalSuitability(
                landing_zone_clearance_radius_m=350.0, # Restricted by canyon walls
                comms_line_of_sight_pct=72.0,
                dte_visibility_hours_per_sol=10.5,
                rover_traverse_connectivity_index=0.55,
                nuclear_safe_standoff_distance_m=800.0,
                expansion_corridors_available=1,
            ),
            strengths=[
                "Topographic wind shielding protects surface structures from high-speed dust saltation.",
                "High mineral water concentration (8.4 wt%) in alluvial channel gravels.",
                "Natural regolith berms on valley walls reduce required radiation shielding mass.",
            ],
            weaknesses=[
                "Canyon wall shadowing reduces daily solar photovoltaic energy yield by ~12%.",
                "Restricted landing zone clearance radius (350m) requires high-precision pinpoint landing.",
                "Limited communications line-of-sight during low-elevation orbiter passes.",
            ],
            missing_data_gaps=[
                "Channel wall talus stability and rockfall frequency during micro-seismic events.",
            ],
            primary_risks=[
                "Rockfall impact on habitat utility lines.",
                "Trapping of rovers in steep bottleneck channel exits.",
            ],
            recommended_reconnaissance="High-resolution LiDAR cliff stability survey from aerial rotorcraft.",
        )

        # 4. SITE-DELTA-SCARP: Western Delta Front Base
        catalog["SITE-DELTA-SCARP"] = CandidateSettlementSite(
            site_id="SITE-DELTA-SCARP",
            name="Jezero Western Delta Front Base",
            latitude_deg=18.4230,
            longitude_deg=77.4120,
            terrain=TerrainSuitability(
                mean_slope_deg=4.5,
                max_slope_deg=11.8,
                surface_roughness_rms_m=0.28,
                elevation_m=-2565.0,
                local_relief_m=28.0,
                bearing_capacity_kpa=130.0,
                clearing_difficulty_index=0.38,
                flat_contiguous_area_m2=95000.0,
            ),
            environment=EnvironmentalSuitability(
                diurnal_temp_min_c=-89.0,
                diurnal_temp_max_c=-13.5,
                mean_solar_insolation_wm2=568.0,
                annual_solar_swing_pct=30.0,
                atmospheric_density_g_m3=0.0165,
                mean_wind_speed_mps=7.4,
                dust_deposition_rate_um_per_sol=0.048,
                regional_dust_storm_risk="MODERATE",
            ),
            resources=ResourcePotential(
                water_evidence_level=WaterEvidenceConfidence.RESOURCE_CANDIDATE,
                estimated_water_wt_pct=7.5,  # Carbonate & clay layered delta scarp
                water_estimate_uncertainty_pct=22.0,
                overburden_depth_m=0.6,
                regolith_usability_grade="BASALTIC_CLAY",
                extraction_energy_kwh_per_kg=1.75,
            ),
            operations=OperationalSuitability(
                landing_zone_clearance_radius_m=480.0,
                comms_line_of_sight_pct=84.0,
                dte_visibility_hours_per_sol=13.0,
                rover_traverse_connectivity_index=0.74,
                nuclear_safe_standoff_distance_m=1100.0,
                expansion_corridors_available=2,
            ),
            strengths=[
                "World-class astrobiology science access directly at bottom of stratigraphic delta scarp.",
                "Very thin overburden (0.6m) enables rapid excavation of clay-rich feedstocks.",
            ],
            weaknesses=[
                "Proximity to steep scarp slopes introduces terrain mobility bottlenecks.",
            ],
            missing_data_gaps=[
                "Clay hydration homogeneity across scarp horizontal facies.",
            ],
            primary_risks=[
                "Wheel slippage on unconsolidated scarp debris aprons.",
            ],
            recommended_reconnaissance="Tethered robotic rappelling survey of scarp face.",
        )

        # 5. SITE-RIM-TERRACE: Jezero Western Rim Elevated Plateau
        catalog["SITE-RIM-TERRACE"] = CandidateSettlementSite(
            site_id="SITE-RIM-TERRACE",
            name="Jezero Western Rim Elevated Plateau",
            latitude_deg=18.5200,
            longitude_deg=77.2200,
            terrain=TerrainSuitability(
                mean_slope_deg=2.4,
                max_slope_deg=5.2,
                surface_roughness_rms_m=0.14,
                elevation_m=-2150.0, # 400m higher than crater floor
                local_relief_m=18.0,
                bearing_capacity_kpa=210.0,
                clearing_difficulty_index=0.18,
                flat_contiguous_area_m2=320000.0,
            ),
            environment=EnvironmentalSuitability(
                diurnal_temp_min_c=-96.5, # Colder due to higher elevation
                diurnal_temp_max_c=-18.0,
                mean_solar_insolation_wm2=582.0,
                annual_solar_swing_pct=27.0,
                atmospheric_density_g_m3=0.0142, # 15% thinner air reduces aero lift & cooling
                mean_wind_speed_mps=11.5, # High exposed rim winds
                dust_deposition_rate_um_per_sol=0.028, # High winds scour dust off solar arrays
                regional_dust_storm_risk="MODERATE",
            ),
            resources=ResourcePotential(
                water_evidence_level=WaterEvidenceConfidence.ORBITAL_INDICATION,
                estimated_water_wt_pct=3.2,
                water_estimate_uncertainty_pct=45.0,
                overburden_depth_m=2.4,
                regolith_usability_grade="HIGH_SILICA",
                extraction_energy_kwh_per_kg=2.85,
            ),
            operations=OperationalSuitability(
                landing_zone_clearance_radius_m=1100.0,
                comms_line_of_sight_pct=98.5, # Superior line of sight to orbiters and Earth
                dte_visibility_hours_per_sol=15.8,
                rover_traverse_connectivity_index=0.62, # Traversing down into crater is steep
                nuclear_safe_standoff_distance_m=2000.0,
                expansion_corridors_available=4,
            ),
            strengths=[
                "Superior telecommunications coverage (98.5% LOS to relays; 15.8h DTE visibility).",
                "High wind scouring naturally cleans solar photovoltaic arrays, reducing dust degradation.",
                "Massive flat plateau with high bedrock bearing capacity (210 kPa).",
            ],
            weaknesses=[
                "Extremely cold nocturnal minimums (-96.5 C) increase habitat heating load by 24%.",
                "Lower atmospheric density (0.0142 g/m³) reduces rotorcraft flight payload capacity.",
                "Challenging 400m vertical climb for rovers accessing crater floor science targets.",
            ],
            missing_data_gaps=[
                "Seasonal rim wind gust maxima during southern summer storm season.",
            ],
            primary_risks=[
                "Structural wind fatigue on unshielded habitat external radiators.",
                "Freezing of liquid loop utilities during winter cold-soaks.",
            ],
            recommended_reconnaissance="Long-duration surface meteorological mast deployment on rim crest.",
        )

        return catalog
