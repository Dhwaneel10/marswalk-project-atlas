"""
MarsWalk 2.0 - Jezero Crater CTX Orthomosaic Processor
Downloads and stitches authentic NASA Mars Trek CTX optical mosaic tiles:
JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0
Crops precisely to match the 250x250 USGS CTX DTM grid extent (5.0 x 5.0 km),
saving an aligned, georeferenced texture for the 3D surface mesh.

Data Provenance:
- USGS Astrogeology Science Center / MRO CTX Team (Fergason et al., 2020)
- NASA Mars Trek WMTS (Equirectangular Mars 2000 Sphere)
"""

import os
import io
import math
import urllib.request
from PIL import Image, ImageEnhance, ImageOps

def prepare_jezero_orthomosaic(output_paths=('web/assets/jezero_ctx_orthomosaic.jpg', 'web/public/assets/jezero_ctx_orthomosaic.jpg')):
    lon_min, lon_max = 77.3976662492164, 77.48201944516315
    lat_min, lat_max = 18.39997813204786, 18.484331327994614

    z = 13
    col_min, col_max = 11714, 11718
    row_min, row_max = 3254, 3258

    stitched_lon_min = -180.0 + col_min * (180.0 / (2**z))
    stitched_lon_max = -180.0 + (col_max + 1) * (180.0 / (2**z))
    stitched_lat_max = 90.0 - row_min * (180.0 / (2**z))
    stitched_lat_min = 90.0 - (row_max + 1) * (180.0 / (2**z))

    tile_w, tile_h = 256, 256
    stitched_w = (col_max - col_min + 1) * tile_w
    stitched_h = (row_max - row_min + 1) * tile_h

    stitched_img = Image.new('L', (stitched_w, stitched_h))

    print(f"Downloading {len(range(row_min, row_max+1)) * len(range(col_min, col_max+1))} NASA Mars Trek CTX tiles at Zoom {z}...")
    for r_idx, r in enumerate(range(row_min, row_max + 1)):
        for c_idx, c in enumerate(range(col_min, col_max + 1)):
            url = f"https://trek.nasa.gov/tiles/Mars/EQ/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0/1.0.0/default/default028mm/{z}/{r}/{c}.png"
            req = urllib.request.Request(url, headers={'User-Agent': 'MarsWalk/2.0'})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    tile_bytes = resp.read()
                    tile = Image.open(io.BytesIO(tile_bytes)).convert('L')
                    stitched_img.paste(tile, (c_idx * tile_w, r_idx * tile_h))
            except Exception as e:
                print(f"Failed to fetch tile {r}/{c}: {e}")

    # Compute crop coordinates
    px_left = (lon_min - stitched_lon_min) / (stitched_lon_max - stitched_lon_min) * stitched_w
    px_right = (lon_max - stitched_lon_min) / (stitched_lon_max - stitched_lon_min) * stitched_w
    px_top = (stitched_lat_max - lat_max) / (stitched_lat_max - stitched_lat_min) * stitched_h
    px_bottom = (stitched_lat_max - lat_min) / (stitched_lat_max - stitched_lat_min) * stitched_h

    print(f"Cropping stitched mosaic to bbox: ({px_left:.1f}, {px_top:.1f}, {px_right:.1f}, {px_bottom:.1f})...")
    cropped = stitched_img.crop((px_left, px_top, px_right, px_bottom))
    cropped = cropped.resize((1024, 1024), Image.Resampling.LANCZOS)

    # Enhance contrast slightly to reveal delta scarps and crater floor morphology
    enhancer = ImageEnhance.Contrast(cropped)
    enhanced = enhancer.enhance(1.25)

    # Colorize with realistic Mars Jezero tone (rich ochre / rust tones from Viking MDIM & Perseverance mastcam)
    # Highlight: ~ (225, 160, 115), Shadow: ~ (45, 25, 20)
    colorized = ImageOps.colorize(enhanced, black="#22120C", mid="#99522D", white="#F0AF84")

    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        colorized.save(path, quality=92)
        size_kb = os.path.getsize(path) / 1024
        print(f"Saved georeferenced CTX orthomosaic texture to {path} ({size_kb:.1f} KB)")

if __name__ == '__main__':
    prepare_jezero_orthomosaic()
