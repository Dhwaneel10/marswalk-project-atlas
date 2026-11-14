"""
MarsWalk 2.0 - Planetary Imagery & Terrain Coverage Registry
Data-driven catalog of authentic global basemaps, regional optical mosaics,
and local high-resolution elevation meshes.

Preserves NASA / USGS provenance, CRS, datum, and strict separation between
imagery coverage and high-resolution elevation coverage.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class GeographicBounds:
    min_lon_deg: float
    max_lon_deg: float
    min_lat_deg: float
    max_lat_deg: float

    def contains(self, lon_deg: float, lat_deg: float) -> bool:
        """Check if point falls within bounds (handling -180..180 and 0..360 longitude)."""
        # Normalize lon to [-180, 180]
        n_lon = ((lon_deg + 180.0) % 360.0) - 180.0
        
        # Check standard bounds
        if self.min_lat_deg <= lat_deg <= self.max_lat_deg:
            if self.min_lon_deg <= self.max_lon_deg:
                return self.min_lon_deg <= n_lon <= self.max_lon_deg
            else:
                # Crosses anti-meridian
                return n_lon >= self.min_lon_deg or n_lon <= self.max_lon_deg
        return False


@dataclass
class ImageryProduct:
    id: str
    title: str
    layer_type: str  # 'global_basemap' | 'regional_mosaic' | 'local_mesh_ortho'
    region_name: str
    target_body: str
    source: str
    attribution: str
    pds_citation: str
    crs: str
    longitude_convention: str
    bounds: GeographicBounds
    nominal_resolution_m: float
    zoom_range: Tuple[int, int]
    wmts_capabilities_url: Optional[str]
    wmts_tile_template: Optional[str]
    local_asset_path: Optional[str]
    has_elevation_data: bool
    elevation_source: Optional[str]
    elevation_resolution_m: Optional[float]
    elevation_bounds: Optional[GeographicBounds]
    planning_supported: bool
    description: str
    fallback_product_id: Optional[str]
    optical_source_resolution_m: Optional[float] = None
    texture_sampling_resolution_m: Optional[float] = None
    texture_bounds: Optional[GeographicBounds] = None
    native_sensor_resolution_m: Optional[float] = None
    display_sampling_m: Optional[float] = None
    color_interpretation: Optional[str] = None
    elevation_capabilities: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageryProduct":
        b_dict = data["bounds"]
        bounds = GeographicBounds(
            min_lon_deg=float(b_dict["min_lon_deg"]),
            max_lon_deg=float(b_dict["max_lon_deg"]),
            min_lat_deg=float(b_dict["min_lat_deg"]),
            max_lat_deg=float(b_dict["max_lat_deg"]),
        )
        elev_bounds = None
        if data.get("elevation_bounds"):
            eb = data["elevation_bounds"]
            elev_bounds = GeographicBounds(
                min_lon_deg=float(eb["min_lon_deg"]),
                max_lon_deg=float(eb["max_lon_deg"]),
                min_lat_deg=float(eb["min_lat_deg"]),
                max_lat_deg=float(eb["max_lat_deg"]),
            )
        tex_bounds = None
        if data.get("texture_bounds"):
            tb = data["texture_bounds"]
            tex_bounds = GeographicBounds(
                min_lon_deg=float(tb["min_lon_deg"]),
                max_lon_deg=float(tb["max_lon_deg"]),
                min_lat_deg=float(tb["min_lat_deg"]),
                max_lat_deg=float(tb["max_lat_deg"]),
            )
        z = data.get("zoom_range", [0, 10])
        return cls(
            id=data["id"],
            title=data["title"],
            layer_type=data["layer_type"],
            region_name=data["region_name"],
            target_body=data.get("target_body", "Mars"),
            source=data["source"],
            attribution=data["attribution"],
            pds_citation=data.get("pds_citation", ""),
            crs=data["crs"],
            longitude_convention=data.get("longitude_convention", "planetocentric_east_180"),
            bounds=bounds,
            nominal_resolution_m=float(data["nominal_resolution_m"]),
            zoom_range=(int(z[0]), int(z[1])),
            wmts_capabilities_url=data.get("wmts_capabilities_url"),
            wmts_tile_template=data.get("wmts_tile_template"),
            local_asset_path=data.get("local_asset_path"),
            has_elevation_data=bool(data.get("has_elevation_data", False)),
            elevation_source=data.get("elevation_source"),
            elevation_resolution_m=float(data["elevation_resolution_m"]) if data.get("elevation_resolution_m") else None,
            elevation_bounds=elev_bounds,
            planning_supported=bool(data.get("planning_supported", False)),
            description=data.get("description", ""),
            fallback_product_id=data.get("fallback_product_id"),
            optical_source_resolution_m=float(data["optical_source_resolution_m"]) if data.get("optical_source_resolution_m") else None,
            texture_sampling_resolution_m=float(data["texture_sampling_resolution_m"]) if data.get("texture_sampling_resolution_m") else None,
            texture_bounds=tex_bounds,
            native_sensor_resolution_m=float(data["native_sensor_resolution_m"]) if data.get("native_sensor_resolution_m") else None,
            display_sampling_m=float(data["display_sampling_m"]) if data.get("display_sampling_m") else None,
            color_interpretation=data.get("color_interpretation"),
            elevation_capabilities=data.get("elevation_capabilities"),
        )


class ImageryRegistry:
    """Registry maintaining verified planetary imagery and elevation layers."""

    def __init__(self, products: List[ImageryProduct], metadata: Optional[Dict[str, Any]] = None):
        self.products = products
        self.metadata = metadata or {}
        self._by_id = {p.id: p for p in products}

    def get_by_id(self, product_id: str) -> Optional[ImageryProduct]:
        return self._by_id.get(product_id)

    def find_best_imagery(self, lon_deg: float, lat_deg: float) -> ImageryProduct:
        """
        Find highest-resolution verified imagery product covering (lon_deg, lat_deg).
        Priority: local_mesh_ortho > regional_mosaic > global_basemap.
        """
        candidates = [p for p in self.products if p.bounds.contains(lon_deg, lat_deg)]
        if not candidates:
            # Default to global fallback
            return self._by_id.get("mars_viking_mdim21_global", self.products[0])

        # Sort by resolution (lower meters/pixel is higher resolution)
        candidates.sort(key=lambda p: (
            0 if p.layer_type == "local_mesh_ortho" else (1 if p.layer_type == "regional_mosaic" else 2),
            p.nominal_resolution_m
        ))
        return candidates[0]

    def has_highres_elevation(self, lon_deg: float, lat_deg: float) -> bool:
        """
        Check if genuine high-resolution elevation data exists at (lon_deg, lat_deg)
        suitable for rover traverse planning (<= 20m grid spacing).
        """
        for p in self.products:
            if p.planning_supported and p.has_elevation_data and p.elevation_bounds:
                if p.elevation_bounds.contains(lon_deg, lat_deg):
                    return True
        return False

    def validate_integrity(self) -> List[str]:
        """Validate logical consistency, non-empty sources, and valid bounding coordinates."""
        errors = []
        if not self.products:
            errors.append("Registry contains no products.")

        seen_ids = set()
        for p in self.products:
            if p.id in seen_ids:
                errors.append(f"Duplicate product ID: '{p.id}'")
            seen_ids.add(p.id)

            if not p.source or not p.attribution:
                errors.append(f"Product '{p.id}' missing source or attribution.")

            if p.bounds.min_lat_deg < -90.0 or p.bounds.max_lat_deg > 90.0:
                errors.append(f"Product '{p.id}' latitude bounds out of range [-90, 90].")

            if p.bounds.min_lat_deg > p.bounds.max_lat_deg:
                errors.append(f"Product '{p.id}' min_lat > max_lat.")

            if p.texture_bounds:
                if p.texture_bounds.min_lat_deg < -90.0 or p.texture_bounds.max_lat_deg > 90.0:
                    errors.append(f"Product '{p.id}' texture latitude bounds out of range [-90, 90].")
                if p.texture_bounds.min_lat_deg > p.texture_bounds.max_lat_deg:
                    errors.append(f"Product '{p.id}' texture min_lat > max_lat.")

            if p.nominal_resolution_m <= 0:
                errors.append(f"Product '{p.id}' nominal resolution must be positive.")

            if p.planning_supported and not p.has_elevation_data:
                errors.append(f"Product '{p.id}' claims planning_supported without elevation data.")

            if p.fallback_product_id and p.fallback_product_id not in self._by_id and p.fallback_product_id != p.id:
                # Check at end after all IDs collected
                pass

        for p in self.products:
            if p.fallback_product_id and p.fallback_product_id not in seen_ids:
                errors.append(f"Product '{p.id}' references unknown fallback '{p.fallback_product_id}'.")

        return errors


def load_imagery_registry(json_path: Optional[str] = None) -> ImageryRegistry:
    """Load and parse the verified imagery registry from JSON."""
    if json_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        json_path = os.path.join(project_root, "web", "data", "mars_imagery_registry.json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = [ImageryProduct.from_dict(p) for p in data.get("products", [])]
    metadata = data.get("metadata", {})
    return ImageryRegistry(products=products, metadata=metadata)
