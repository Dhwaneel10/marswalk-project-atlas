import sys
sys.path.insert(0, 'src')
from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor

ingestor = PlanetaryArchiveIngestor()
verif = ingestor.load_and_verify_manifest()
print("Manifest check:", verif['all_verified'], "Total products:", verif['total_products'])

mcd = ingestor.ingest_mcd_netcdf()
print("MCD NetCDF:", mcd['title'], "Tsurf mean:", round(mcd['tsurf_mean_k'], 2), "K")

pred = ingestor.get_mcd_model_prediction(ls_deg=45.0, ltst_hours=13.5)
print("MCD prediction at Ls=45, LTST=13.5h:", pred)

mcs = ingestor.ingest_mcs_profiles()
print("MCS profiles ingested:", len(mcs))

meda = ingestor.ingest_meda_daily_series()
print("MEDA records ingested:", len(meda))
if meda:
    print("Sample record 0:", meda[0].observation_id, meda[0].parameter_name, meda[0].observed_value, meda[0].unit)
    print("Sample record 1:", meda[1].observation_id, meda[1].parameter_name, meda[1].observed_value, meda[1].unit)
