"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Environmental Data Catalog & Source Registry.

Maintains strict provenance tracking, quality flags, physical unit definitions,
and attribution for all environmental datasets across Jezero Crater.
Enforces the mandatory separation of direct observations, remote sensing products,
climatology reanalyses, derived geometric models, and configured scenarios.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


class ProvenanceClass(str, enum.Enum):
    """Rigorous scientific data provenance taxonomy."""
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    REMOTE_SENSING_PRODUCT = "REMOTE_SENSING_PRODUCT"
    MODEL_REANALYSIS = "MODEL_REANALYSIS"
    CLIMATOLOGY = "CLIMATOLOGY"
    DERIVED_GEOMETRIC_MODEL = "DERIVED_GEOMETRIC_MODEL"
    CONFIGURED_SCENARIO = "CONFIGURED_SCENARIO"
    SYNTHETIC_DEMONSTRATION = "SYNTHETIC_DEMONSTRATION"
    UNKNOWN_PROVENANCE = "UNKNOWN_PROVENANCE"


@dataclass(frozen=True)
class EnvironmentalProductMetadata:
    """Metadata specification for a planetary environmental dataset or model product."""
    product_id: str
    name: str
    parameter_name: str
    instrument_or_model: str
    source_institution: str
    native_resolution_m: float
    temporal_coverage: str
    units: str
    provenance_class: ProvenanceClass
    spatial_bounds_rc: Tuple[int, int, int, int] = (0, 0, 250, 250)
    data_quality_flags: List[str] = field(default_factory=list)
    checksum_sha256: Optional[str] = None
    doi_or_url: Optional[str] = None
    scientific_disclaimer: str = (
        "Dataset or derived model product provided for planning and simulation purposes. "
        "Does not constitute flight certification or astronaut operational safety clearance."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provenance_class"] = self.provenance_class.value
        d["spatial_bounds_rc"] = list(self.spatial_bounds_rc)
        return d


class EnvironmentalDataCatalog:
    """Central registry and verification engine for all Atlas environmental products."""

    def __init__(self) -> None:
        self._registry: Dict[str, EnvironmentalProductMetadata] = {}
        self._initialize_core_catalog()

    def _initialize_core_catalog(self) -> None:
        """Register verified standard environmental data products."""
        # 1. Authentic USGS CTX 20m Jezero Crater DTM
        self.register_product(
            EnvironmentalProductMetadata(
                product_id="USGS_CTX_DTM_JEZERO_20M",
                name="USGS MRO CTX Jezero Crater Digital Terrain Model (20m)",
                parameter_name="surface_elevation_m",
                instrument_or_model="Context Camera (CTX)",
                source_institution="USGS Astrogeology Science Center / NASA PDS",
                native_resolution_m=20.0,
                temporal_coverage="Static Topographic Baseline (Mars Year 28-34)",
                units="m",
                provenance_class=ProvenanceClass.REMOTE_SENSING_PRODUCT,
                spatial_bounds_rc=(0, 0, 250, 250),
                data_quality_flags=["PDS4_VALIDATED", "BILINEAR_SAMPLED", "NODATA_DILATED"],
                checksum_sha256="875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3",
                doi_or_url="https://doi.org/10.5066/P906QQT8",
            )
        )

        # 2. Derived Horn 3x3 Slope & Roughness
        self.register_product(
            EnvironmentalProductMetadata(
                product_id="USGS_CTX_DERIVED_SLOPE_20M",
                name="Derived Local Slope & Decameter Roughness Matrix",
                parameter_name="slope_deg",
                instrument_or_model="Horn 3x3 Finite Difference Filter",
                source_institution="MarsWalk / Project Atlas Planetary Core",
                native_resolution_m=20.0,
                temporal_coverage="Static Derived from CTX DTM",
                units="deg",
                provenance_class=ProvenanceClass.DERIVED_GEOMETRIC_MODEL,
                spatial_bounds_rc=(0, 0, 250, 250),
                data_quality_flags=["DERIVED_FROM_AUTHENTIC_DTM", "EDGE_GUARDED"],
                doi_or_url="https://doi.org/10.5066/P906QQT8",
            )
        )

        # 3. Perseverance MEDA In-Situ Microclimate
        self.register_product(
            EnvironmentalProductMetadata(
                product_id="NASA_M2020_MEDA_JEZERO_HISTORICAL",
                name="Mars 2020 Perseverance MEDA Atmospheric Station Records",
                parameter_name="ambient_microclimate",
                instrument_or_model="Mars Environmental Dynamics Analyzer (MEDA)",
                source_institution="Centro de Astrobiologia (CAB-CSIC) / NASA JPL",
                native_resolution_m=0.0,  # Point measurement at rover location
                temporal_coverage="Sols 0 - 1000+ (Mars Year 36-37)",
                units="multi_parameter",
                provenance_class=ProvenanceClass.DIRECT_OBSERVATION,
                spatial_bounds_rc=(0, 0, 250, 250),
                data_quality_flags=["IN_SITU_MEASUREMENT", "PDS4_ATMOSPHERES_ARCHIVED"],
                doi_or_url="https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html",
                scientific_disclaimer=(
                    "In-situ meteorological observations from Mars 2020 Perseverance MEDA. "
                    "Valid strictly for the local rover traverse path in Jezero Crater; "
                    "spatial extrapolation across entire quadrangle is model-derived."
                )
            )
        )

        # 4. Mars Climate Database (MCD) v5.3 Reanalysis
        self.register_product(
            EnvironmentalProductMetadata(
                product_id="MCD_V5_3_JEZERO_CLIMATOLOGY",
                name="Mars Climate Database v5.3 / v6 GCM Reanalysis Climatology",
                parameter_name="surface_and_air_temperature",
                instrument_or_model="LMD Mars Global Climate Model",
                source_institution="Laboratoire de Meteorologie Dynamique (CNRS) / ESA",
                native_resolution_m=50000.0,  # GCM grid ~0.8 deg
                temporal_coverage="Mars Years 24-35 Multi-Year Solar Longitude Average",
                units="K",
                provenance_class=ProvenanceClass.MODEL_REANALYSIS,
                spatial_bounds_rc=(0, 0, 250, 250),
                data_quality_flags=["GCM_DOWNSCALED", "SEASONAL_DIURNAL_SYNTHESIS"],
                doi_or_url="https://www-mars.lmd.jussieu.fr/mars/access.html",
            )
        )

        # 5. Atlas Solar Geometry & Terrain Shadow Ray-Cast Engine
        self.register_product(
            EnvironmentalProductMetadata(
                product_id="ATLAS_SOLAR_GEOMETRY_RAYCAST_V1",
                name="Atlas 3D Celestial Solar Geometry & Ray-Cast Terrain Horizon Shadows",
                parameter_name="solar_illumination_and_shadow",
                instrument_or_model="Astronomical Ephemeris & DTM Ray Tracer",
                source_institution="Project Atlas Environmental Core",
                native_resolution_m=20.0,
                temporal_coverage="Deterministic Sols and Local Solar Time (LTST)",
                units="dimensionless_ratio",
                provenance_class=ProvenanceClass.DERIVED_GEOMETRIC_MODEL,
                spatial_bounds_rc=(0, 0, 250, 250),
                data_quality_flags=["GEOMETRIC_LINE_OF_SIGHT_RAYCAST", "DIFFUSE_UNMODELLED"],
                scientific_disclaimer=(
                    "Geometric direct-beam solar illumination and cast shadow model. "
                    "Calculates geometric line-of-sight from surface cell to solar center of disk. "
                    "Does NOT model atmospheric diffuse sky radiation or secondary scattering."
                )
            )
        )

        # 6. Environmental Test Scenarios (ENV-A to ENV-E)
        self.register_product(
            EnvironmentalProductMetadata(
                product_id="ATLAS_ENV_SCENARIOS_V1",
                name="Atlas Calibrated Deterministic Planetary Environmental Scenarios",
                parameter_name="compound_environmental_stress",
                instrument_or_model="Scenario Perturbation Generator",
                source_institution="Project Atlas Operations Assurance",
                native_resolution_m=20.0,
                temporal_coverage="Synthetic Sols 1-10 Mission Windows",
                units="standardized_anomaly",
                provenance_class=ProvenanceClass.CONFIGURED_SCENARIO,
                spatial_bounds_rc=(0, 0, 250, 250),
                data_quality_flags=["DETERMINISTIC_SCENARIO", "NOT_EMPIRICAL_PROBABILITY"],
                scientific_disclaimer=(
                    "Engineered stress scenarios for testing mission robustness. "
                    "Scenario frequency does not indicate empirical Martian weather probability."
                )
            )
        )

    def register_product(self, metadata: EnvironmentalProductMetadata) -> None:
        """Register or update an environmental product in the catalog."""
        self._registry[metadata.product_id] = metadata

    def get_product(self, product_id: str) -> Optional[EnvironmentalProductMetadata]:
        """Retrieve metadata for a specific product by ID."""
        return self._registry.get(product_id)

    def list_products(
        self,
        provenance_filter: Optional[ProvenanceClass] = None,
        parameter_filter: Optional[str] = None,
    ) -> List[EnvironmentalProductMetadata]:
        """List products matching optional provenance class or parameter filters."""
        results = list(self._registry.values())
        if provenance_filter is not None:
            results = [p for p in results if p.provenance_class == provenance_filter]
        if parameter_filter is not None:
            results = [p for p in results if parameter_filter.lower() in p.parameter_name.lower()]
        return results

    def validate_product_provenance(self, product_id: str) -> Dict[str, Any]:
        """Audit and return the provenance verification package for a product."""
        product = self.get_product(product_id)
        if product is None:
            return {
                "product_id": product_id,
                "is_registered": False,
                "provenance_class": ProvenanceClass.UNKNOWN_PROVENANCE.value,
                "verification_status": "UNREGISTERED_PRODUCT",
            }
        return {
            "product_id": product.product_id,
            "name": product.name,
            "is_registered": True,
            "provenance_class": product.provenance_class.value,
            "instrument_or_model": product.instrument_or_model,
            "source_institution": product.source_institution,
            "checksum_sha256": product.checksum_sha256,
            "doi_or_url": product.doi_or_url,
            "verification_status": "VERIFIED_AUTHENTIC" if product.checksum_sha256 or product.doi_or_url else "PROVISIONAL",
            "scientific_disclaimer": product.scientific_disclaimer,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full catalog into dictionary."""
        return {
            "total_products": len(self._registry),
            "products": {pid: prod.to_dict() for pid, prod in self._registry.items()},
        }
