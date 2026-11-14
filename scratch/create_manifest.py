import os, hashlib, json
from datetime import datetime, timezone

raw_files = [
    {
        "product_id": "PDS4_M2020_MEDA_DERIVED_PS_INDEX",
        "path": "data/environment/raw/meda/mars2020_meda_derived_PS.csv",
        "source_url": "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_derived_PS.csv",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (Pressure Sensor PS)",
        "processing_level": "Level 4 Derived In-Situ Surface Pressure",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "Rodriguez-Manfredi et al. (2021), Mars 2020 MEDA PDS4 Bundle, NASA PDS Atmospheres Node"
    },
    {
        "product_id": "PDS4_M2020_MEDA_DERIVED_TRS_INDEX",
        "path": "data/environment/raw/meda/mars2020_meda_derived_TRS.csv",
        "source_url": "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_derived_TRS.csv",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (Thermal Infrared Sensor TIRS)",
        "processing_level": "Level 4 Derived Ground Surface Temperature",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "Rodriguez-Manfredi et al. (2021), Space Science Reviews"
    },
    {
        "product_id": "PDS4_M2020_MEDA_DERIVED_RHS_INDEX",
        "path": "data/environment/raw/meda/mars2020_meda_derived_RHS.csv",
        "source_url": "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_derived_RHS.csv",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (Relative Humidity Sensor RHS)",
        "processing_level": "Level 4 Derived Atmospheric Relative Humidity",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "Rodriguez-Manfredi et al. (2021), NASA PDS Atmospheres Node"
    },
    {
        "product_id": "PDS4_M2020_MEDA_DERIVED_WIND_INDEX",
        "path": "data/environment/raw/meda/mars2020_meda_derived_wind.csv",
        "source_url": "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_derived_wind.csv",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (Wind Sensor WS Booms)",
        "processing_level": "Level 4 Derived Surface Wind Vectors",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "Newman et al. (2022), JGR Planets"
    },
    {
        "product_id": "PDS4_M2020_MEDA_CALIBRATED_ATS_INDEX",
        "path": "data/environment/raw/meda/mars2020_meda_calibrated_ATS.csv",
        "source_url": "https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_calibrated_ATS.csv",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (Air Temperature Sensors ATS1-ATS5)",
        "processing_level": "Level 3 Calibrated Air Temperature at 1.45m",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "Savijarvi et al. (2022), JGR Planets"
    },
    {
        "product_id": "PDS4_M2020_MEDA_SOL0010_TIRS",
        "path": "data/environment/raw/meda/WE__0010___________DER_TIRS________________P04.CSV",
        "source_url": "https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_derived_env/sol_0000_0089/sol_0010/WE__0010___________DER_TIRS________________P04.CSV",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (TIRS Thermopile)",
        "processing_level": "Level 4 High-Frequency Radiometric Flux / Ground Temp",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "NASA PDS Atmospheres Node, Sol 10 Derived Environmental Record"
    },
    {
        "product_id": "PDS4_M2020_MEDA_SOL0010_ATS",
        "path": "data/environment/raw/meda/WE__0010___________CAL_ATS_________________P01.CSV",
        "source_url": "https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_calibrated_env/sol_0000_0089/sol_0010/WE__0010___________CAL_ATS_________________P01.CSV",
        "platform": "NASA Mars 2020 Perseverance Rover",
        "instrument": "MEDA (ATS RTD Sensors)",
        "processing_level": "Level 3 Calibrated Mast Air Temperature",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "NASA PDS Atmospheres Node, Sol 10 Calibrated Air Temperature"
    },
    {
        "product_id": "LMD_CNES_MCD_V6_2_JEZERO",
        "path": "data/environment/raw/mcd/jezero_mcd_v6_2.nc",
        "source_url": "http://www-mars.lmd.jussieu.fr/mcd_python/",
        "platform": "Mars Climate Database (MCD v6.2) Global Climate Model",
        "instrument": "LMD Martian General Circulation Model (GCM)",
        "processing_level": "Climatological Numerical Reanalysis Subgrid Slice",
        "provenance_class": "NUMERICAL_CLIMATE_MODEL",
        "citation": "Forget et al. (1999), Millour et al. (2018)"
    },
    {
        "product_id": "MRO_MCS_LEVEL5_JEZERO_PROFILES",
        "path": "data/environment/raw/mcs/mro_mcs_jezero_profiles.json",
        "source_url": "https://pds-geosciences.wustl.edu/mro/mro-m-mcs-5-ddr-v1/mromcs_1001/",
        "platform": "NASA Mars Reconnaissance Orbiter (MRO)",
        "instrument": "Mars Climate Sounder (MCS)",
        "processing_level": "Level 5 Derived Vertical Atmospheric Sounding",
        "provenance_class": "AUTHENTIC_PLANETARY_ARCHIVE",
        "citation": "Kleinboehl et al. (2009), McCleese et al. (2010), NASA PDS Geosciences Node"
    }
]

manifest_entries = []
for entry in raw_files:
    path = entry["path"]
    if os.path.exists(path):
        with open(path, 'rb') as f:
            content = f.read()
        sha = hashlib.sha256(content).hexdigest()
        size = len(content)
        mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat()
        manifest_entries.append({
            "product_id": entry["product_id"],
            "relative_path": path.replace("\\", "/"),
            "file_size_bytes": size,
            "sha256_checksum": sha,
            "last_modified_utc": mtime,
            "source_url": entry["source_url"],
            "platform": entry["platform"],
            "instrument": entry["instrument"],
            "processing_level": entry["processing_level"],
            "provenance_class": entry["provenance_class"],
            "citation": entry["citation"],
            "verification_status": "VERIFIED_PRESENT"
        })
    else:
        print(f"Warning: missing {path}")

manifest = {
    "manifest_version": "1.0.0",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "provenance_authority": "MarsWalk 2.0 / Project Atlas Planetary Data Assimilation Lab",
    "total_products": len(manifest_entries),
    "total_bytes": sum(e["file_size_bytes"] for e in manifest_entries),
    "products": manifest_entries
}

out_path = 'data/environment/index/source_acquisition_manifest.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2)

print(f"Created source acquisition manifest with {len(manifest_entries)} products ({manifest['total_bytes'] / (1024*1024):.2f} MB) at {out_path}")
