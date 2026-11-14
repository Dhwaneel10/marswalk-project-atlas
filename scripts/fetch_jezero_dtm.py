"""
Download and verify the USGS Mars 2020 Jezero CTX DTM GeoTIFF.
DOI: 10.5066/P906QQT8
Authors: Fergason et al., 2020 (USGS Astrogeology Science Center)
"""
import os
import sys
import urllib.request
import time

URL = "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"
EXPECTED_SIZE = 9662387  # bytes (~9.21 MB)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif")

def download_ctx_dtm(dest_path=OUTPUT_PATH, expected_size=EXPECTED_SIZE, url=URL):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path):
        actual_size = os.path.getsize(dest_path)
        if actual_size == expected_size:
            print(f"File already exists and verified ({actual_size} bytes): {dest_path}")
            return dest_path
        else:
            print(f"Existing file size mismatch ({actual_size} vs expected {expected_size} bytes). Re-downloading...")

    print(f"Downloading CTX DTM from: {url}")
    print(f"Destination: {dest_path}")
    
    start_time = time.time()
    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            sys.stdout.write(f"\rDownloading: {downloaded / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB ({percent:.1f}%)")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
    print()
    elapsed = time.time() - start_time
    actual_size = os.path.getsize(dest_path)
    print(f"Download complete in {elapsed:.2f}s. Size: {actual_size} bytes ({actual_size / (1024*1024):.2f} MB)")
    if actual_size != expected_size:
        raise ValueError(f"Downloaded file size ({actual_size}) does not match expected size ({expected_size})!")
    return dest_path

if __name__ == "__main__":
    download_ctx_dtm()
