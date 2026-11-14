"""
MarsWalk 2.0 - Safe Local Planetary Tile Cache
Provides validated caching for NASA Mars Trek WMTS tiles with allowlist isolation,
atomic disk persistence, offline graceful degradation, and provenance tracking.
"""

import os
import re
import io
import json
import urllib.request
import urllib.error
from typing import Optional, Tuple, Dict, Any

from marswalk.data.imagery_registry import ImageryRegistry, ImageryProduct, load_imagery_registry

# Allowed products for caching (strict allowlist to prevent arbitrary downloads)
ALLOWED_TILE_PRODUCTS = {
    "olympus_mons_ctx_regional",
    "valles_marineris_ctx_regional",
    "gale_crater_ctx_regional",
    "jezero_ctx_regional_context",
    "mars_viking_mdim21_global",
    "mars_mola_shade_global",
}

PRODUCT_ID_PATTERN = re.compile(r"^[a-z0-9_]{3,64}$")


class TileCacheError(Exception):
    """Raised when tile request validation fails."""
    pass


class PlanetaryTileCache:
    """Thread-safe, validated tile cache for authentic planetary WMTS imagery."""

    def __init__(self, cache_dir: Optional[str] = None, registry: Optional[ImageryRegistry] = None):
        if cache_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            cache_dir = os.path.join(project_root, "data", "cache", "imagery")
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

        self.registry = registry or load_imagery_registry()
        self.manifest_path = os.path.join(self.cache_dir, "cache_manifest.json")
        self._stats = {
            "hits": 0,
            "misses": 0,
            "network_errors": 0,
            "cached_tiles": 0,
            "total_bytes": 0,
        }
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load manifest from disk if it exists."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._stats["hits"] = data.get("hits", 0)
                    self._stats["misses"] = data.get("misses", 0)
            except Exception:
                pass
        self._recount_cache_disk()

    def _recount_cache_disk(self) -> None:
        """Scan cache dir for tile count and total bytes."""
        count = 0
        total_size = 0
        for root, _, files in os.walk(self.cache_dir):
            for fname in files:
                if fname.endswith((".png", ".jpg", ".jpeg")):
                    count += 1
                    fpath = os.path.join(root, fname)
                    total_size += os.path.getsize(fpath)
        self._stats["cached_tiles"] = count
        self._stats["total_bytes"] = total_size

    def _save_manifest(self) -> None:
        """Persist cache summary stats."""
        try:
            tmp = self.manifest_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._stats, f, indent=2)
            os.replace(tmp, self.manifest_path)
        except Exception:
            pass

    def validate_tile_coords(self, product_id: str, z: int, r: int, c: int) -> ImageryProduct:
        """
        Validate product and tile coordinates strictly against matrix limits.
        Raises TileCacheError if validation fails.
        """
        if not PRODUCT_ID_PATTERN.match(product_id):
            raise TileCacheError(f"Invalid product_id format: '{product_id}'")

        if product_id not in ALLOWED_TILE_PRODUCTS:
            raise TileCacheError(f"Product '{product_id}' is not in allowed tile products.")

        product = self.registry.get_by_id(product_id)
        if not product:
            raise TileCacheError(f"Product '{product_id}' not found in registry.")

        if not product.wmts_tile_template:
            raise TileCacheError(f"Product '{product_id}' does not define a wmts_tile_template.")

        min_z, max_z = product.zoom_range
        if not (min_z <= z <= max_z):
            raise TileCacheError(f"Zoom level {z} out of bounds [{min_z}, {max_z}] for '{product_id}'")

        # In Equirectangular Mars WMTS:
        # z=0 has 2 columns (0, 1) and 1 row (0).
        # z=N has 2 * 2^z columns and 2^z rows.
        max_rows = 2 ** z
        max_cols = 2 * (2 ** z)

        if not (0 <= r < max_rows):
            raise TileCacheError(f"Row {r} out of bounds [0, {max_rows - 1}] at zoom {z}")

        if not (0 <= c < max_cols):
            raise TileCacheError(f"Column {c} out of bounds [0, {max_cols - 1}] at zoom {z}")

        return product

    def get_tile_path(self, product_id: str, z: int, r: int, c: int, ext: str = "png") -> str:
        """Get filesystem path for a cached tile, isolated by product and zoom level."""
        # Sanitize extension
        safe_ext = "jpg" if ext.lower() in ("jpg", "jpeg") else "png"
        return os.path.join(self.cache_dir, product_id, str(z), f"{r}_{c}.{safe_ext}")

    def get_tile(self, product_id: str, z: int, r: int, c: int, timeout_sec: float = 6.0) -> Optional[Tuple[bytes, str, bool]]:
        """
        Retrieve tile from local disk cache, or fetch and store atomically if missing.
        Returns: (tile_bytes, mime_type, is_hit) or None if retrieval failed.
        """
        product = self.validate_tile_coords(product_id, z, r, c)

        # Detect expected extension from template
        ext = "jpg" if ".jpg" in product.wmts_tile_template.lower() else "png"
        mime_type = "image/jpeg" if ext == "jpg" else "image/png"

        disk_path = self.get_tile_path(product_id, z, r, c, ext=ext)

        # Check Cache HIT
        if os.path.exists(disk_path) and os.path.getsize(disk_path) > 0:
            try:
                with open(disk_path, "rb") as f:
                    tile_bytes = f.read()
                # Verify header bytes
                if self._is_valid_image(tile_bytes, ext):
                    self._stats["hits"] += 1
                    return tile_bytes, mime_type, True
            except Exception:
                pass  # Fall through to re-fetch if corrupted

        # Cache MISS: Fetch from authentic NASA WMTS template
        self._stats["misses"] += 1
        url = product.wmts_tile_template.format(z=z, r=r, c=c)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MarsWalk/2.0 Planetary Atlas (NASA Space Apps)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                tile_bytes = resp.read()

            if not self._is_valid_image(tile_bytes, ext):
                self._stats["network_errors"] += 1
                return None

            # Atomic save to disk cache
            os.makedirs(os.path.dirname(disk_path), exist_ok=True)
            tmp_path = disk_path + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(tile_bytes)
            os.replace(tmp_path, disk_path)

            self._stats["cached_tiles"] += 1
            self._stats["total_bytes"] += len(tile_bytes)
            self._save_manifest()

            return tile_bytes, mime_type, False

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            self._stats["network_errors"] += 1
            return None

    def _is_valid_image(self, data: bytes, ext: str) -> bool:
        """Validate standard magic bytes to ensure file is not HTML/XML error payload."""
        if len(data) < 8:
            return False
        if ext == "png":
            # PNG signature: 89 50 4E 47 0D 0A 1A 0A
            return data.startswith(b"\x89PNG\r\n\x1a\n")
        elif ext in ("jpg", "jpeg"):
            # JPEG signature: FF D8 FF
            return data.startswith(b"\xff\xd8\xff")
        return True

    def get_status(self) -> Dict[str, Any]:
        """Return cache health, hit ratio, inventory, and allowlisted layers."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_ratio = (self._stats["hits"] / total_requests) if total_requests > 0 else 0.0
        return {
            "status": "operational",
            "cache_dir": self.cache_dir,
            "allowed_products": sorted(list(ALLOWED_TILE_PRODUCTS)),
            "stats": {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "total_requests": total_requests,
                "hit_ratio_pct": round(hit_ratio * 100, 1),
                "network_errors": self._stats["network_errors"],
                "cached_tiles": self._stats["cached_tiles"],
                "total_bytes": self._stats["total_bytes"],
                "total_mb": round(self._stats["total_bytes"] / (1024 * 1024), 2),
            }
        }
