import sys
sys.path.insert(0, 'src')
from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.mars_environment_collocation import EnvironmentCollocationEngine
from marswalk.core.environment_model_validation import ModelEvaluationLab

ingestor = PlanetaryArchiveIngestor()
meda_records = ingestor.ingest_meda_daily_series()
engine = EnvironmentCollocationEngine()
lab = ModelEvaluationLab()

# Collocate with MCD
pairs_mcd = engine.collocate_dataset(meda_records[:500], ingestor, model_target="MCD_6_2_GCM")
report_mcd = lab.evaluate_model(pairs_mcd, model_name="MCD_6_2_GCM")

print("=== MCD 6.2 GCM EVALUATION REPORT ===")
for p, stats in report_mcd.overall_metrics.items():
    print(f"Param: {p:22s} | N={stats.sample_count:4d} | Bias: {stats.mean_bias:7.2f} | MAE: {stats.mae:6.2f} | RMSE: {stats.rmse:6.2f} | Pearson r: {stats.pearson_r:6.3f} | R^2: {stats.r_squared:6.3f}")

print("\n=== TRAIN (60%) vs HELD-OUT (40%) TEST METRICS ===")
for p in report_mcd.overall_metrics:
    tr = report_mcd.train_metrics.get(p)
    ho = report_mcd.held_out_metrics.get(p)
    print(f"Param: {p:22s} | Train RMSE: {tr.rmse if tr else None:6.2f} | Held-Out RMSE: {ho.rmse if ho else None:6.2f}")
