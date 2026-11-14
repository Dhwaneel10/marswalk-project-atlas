"""
MarsWalk 2.0 - Regional CTX Imagery Processor
Fetches authentic NASA Mars Trek CTX optical mosaic tiles for key regional landmarks
(Olympus Mons caldera and Gale Crater / Mount Sharp), stitching lightweight
georeferenced previews for robust offline fallback and instant exploration.

Data Provenance:
- NASA Mars Trek WMTS (Equirectangular Mars 2000 Sphere)
- MRO CTX Science Team (Malin et al., 2007)
"""

import os
import io
import urllib.request
from PIL import Image, ImageEnhance, ImageOps


def fetch_and_stitch_tiles(layer_name: str, z: int, rows: list, cols: list) -> Image.Image:
    """Download and stitch a grid of WMTS tiles."""
    tile_w, tile_h = 256, 256
    stitched_w = len(cols) * tile_w
    stitched_h = len(rows) * tile_h
    stitched = Image.new("L", (stitched_w, stitched_h))

    for r_idx, r in enumerate(rows):
        for c_idx, c in enumerate(cols):
            url = f"https://trek.nasa.gov/tiles/Mars/EQ/{layer_name}/1.0.0/default/default028mm/{z}/{r}/{c}.png"
            req = urllib.request.Request(url, headers={"User-Agent": "MarsWalk/2.0"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    tile_bytes = resp.read()
                    tile = Image.open(io.BytesIO(tile_bytes)).convert("L")
                    stitched.paste(tile, (c_idx * tile_w, r_idx * tile_h))
            except Exception as e:
                print(f"Warning: Failed to fetch tile {layer_name} {z}/{r}/{c}: {e}")

    return stitched


def prepare_regional_previews():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "assets")
    os.makedirs(out_dir, exist_ok=True)

    # 1. Olympus Mons Caldera & Shield (Z=6, rows=[25, 26], cols=[16, 17])
    print("[Regional Imagery] Preparing Olympus Mons CTX preview...")
    olympus_img = fetch_and_stitch_tiles("olympus_mons.eq", 6, [25, 26], [16, 17])
    # Enhance and tint
    enhancer = ImageEnhance.Contrast(olympus_img)
    olympus_enh = enhancer.enhance(1.2)
    olympus_col = ImageOps.colorize(olympus_enh, black="#22120C", mid="#9A5430", white="#EFB287")
    olympus_path = os.path.join(out_dir, "olympus_mons_ctx_preview.jpg")
    olympus_col.save(olympus_path, quality=88)
    print(f"Saved Olympus Mons preview: {olympus_path} ({os.path.getsize(olympus_path) / 1024:.1f} KB)")

    # 2. Gale Crater & Mount Sharp (Z=6, rows=[33, 34], cols=[112, 113])
    print("[Regional Imagery] Preparing Gale Crater CTX preview...")
    gale_img = fetch_and_stitch_tiles("Gale_CTX_BlockAdj_dd", 6, [33, 34], [112, 113])
    enhancer_g = ImageEnhance.Contrast(gale_img)
    gale_enh = enhancer_g.enhance(1.2)
    gale_col = ImageOps.colorize(gale_enh, black="#22120C", mid="#9A5430", white="#EFB287")
    gale_path = os.path.join(out_dir, "gale_crater_ctx_preview.jpg")
    gale_col.save(gale_path, quality=88)
    print(f"Saved Gale Crater preview: {gale_path} ({os.path.getsize(gale_path) / 1024:.1f} KB)")

    # 3. Valles Marineris (Coprates / Capri Chasma) (Z=6, rows=[38, 39], cols=[45, 46])
    print("[Regional Imagery] Preparing Valles Marineris CTX preview...")
    valles_img = fetch_and_stitch_tiles("SE_Marineris_CTX_BlockAdj_dd", 6, [38, 39], [45, 46])
    enhancer_v = ImageEnhance.Contrast(valles_img)
    valles_enh = enhancer_v.enhance(1.25)
    valles_col = ImageOps.colorize(valles_enh, black="#22120C", mid="#9A5430", white="#EFB287")
    valles_path = os.path.join(out_dir, "valles_marineris_ctx_preview.jpg")
    valles_col.save(valles_path, quality=88)
    print(f"Saved Valles Marineris preview: {valles_path} ({os.path.getsize(valles_path) / 1024:.1f} KB)")


if __name__ == "__main__":
    prepare_regional_previews()
