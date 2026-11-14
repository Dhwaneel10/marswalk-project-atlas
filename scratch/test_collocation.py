import sys
sys.path.insert(0, 'src')
from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine

ingestor = PlanetaryArchiveIngestor()
meda_records = ingestor.ingest_meda_daily_series()
engine = EnvironmentCollocationEngine()

# Collocate first 100 MEDA observations against MCD 6.2 GCM
pairs_mcd = engine.collocate_dataset(meda_records[:100], ingestor, model_target="MCD_6_2_GCM")
print("Collocated with MCD:", len(pairs_mcd))
qualified_mcd = [p for p in pairs_mcd if p.gate_status == "COLLOCATION_QUALIFIED"]
print("Qualified MCD pairs:", len(qualified_mcd))
if qualified_mcd:
    p0 = qualified_mcd[0]
    print(f"Sample pair 0: {p0.parameter_name} Obs: {p0.observed_value} Model: {p0.model_value} Residual: {p0.residual} {p0.unit}")

# Collocate first 100 MEDA observations against 13L Baseline
pairs_13l = engine.collocate_dataset(meda_records[:100], ingestor, model_target="ATLAS_13L_BASELINE")
print("Collocated with 13L Baseline:", len(pairs_13l))
qualified_13l = [p for p in pairs_13l if p.gate_status == "COLLOCATION_QUALIFIED"]
print("Qualified 13L pairs:", len(qualified_13l))
if qualified_13l:
    p0 = qualified_13l[0]
    print(f"Sample pair 0: {p0.parameter_name} Obs: {p0.observed_value} Model: {p0.model_value} Residual: {p0.residual} {p0.unit}")
