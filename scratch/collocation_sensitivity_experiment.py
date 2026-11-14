import json
import math
import os
import sys

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.core.planetary_archive_ingestion import PlanetaryArchiveIngestor
from marswalk.core.mars_environment_collocation import (
    EnvironmentCollocationEngine, CollocationGateStatus
)

ingestor = PlanetaryArchiveIngestor()
print("Ingesting archives...")
norm_obs = ingestor.ingest_meda_daily_series()
ingestor.ingest_mcd_netcdf()
print(f"Total normalized observations: {len(norm_obs)}")

configs = {
    "Strict": {"max_dist": 2.5, "max_time": 0.25, "max_ls": 2.5},
    "Nominal": {"max_dist": 50.0, "max_time": 0.50, "max_ls": 5.0},
    "Permissive": {"max_dist": 150.0, "max_time": 1.00, "max_ls": 15.0},
}

results = {}

for name, cfg in configs.items():
    engine = EnvironmentCollocationEngine(
        max_spatial_separation_km=cfg["max_dist"],
        max_temporal_delta_hours=cfg["max_time"],
        max_seasonal_delta_ls_deg=cfg["max_ls"]
    )
    colloc_pairs = engine.collocate_dataset(norm_obs, ingestor)
    
    qualified = [p for p in colloc_pairs if p.gate_status == CollocationGateStatus.QUALIFIED.value]
    rejections = {}
    for p in colloc_pairs:
        if p.gate_status != CollocationGateStatus.QUALIFIED.value:
            rejections[p.gate_status] = rejections.get(p.gate_status, 0) + 1
            
    d_dists = [p.spatial_separation_km for p in qualified]
    d_residuals = [p.residual for p in qualified]
    
    def stats(arr):
        if not arr: return {"mean": 0, "min": 0, "max": 0, "p50": 0}
        s = sorted(arr)
        return {
            "mean": round(float(sum(s) / len(s)), 3),
            "min": round(float(s[0]), 3),
            "max": round(float(s[-1]), 3),
            "p50": round(float(s[len(s)//2]), 3)
        }
        
    results[name] = {
        "total_evaluated": len(colloc_pairs),
        "qualified_pairs": len(qualified),
        "qualification_rate_pct": round(len(qualified) / max(1, len(colloc_pairs)) * 100, 2),
        "rejected_count": len(colloc_pairs) - len(qualified),
        "rejection_breakdown": rejections,
        "spatial_separation_stats_km": stats(d_dists),
        "residual_stats": stats(d_residuals)
    }
    print(f"\n[{name}] Qualified: {len(qualified)} / {len(colloc_pairs)} ({results[name]['qualification_rate_pct']}%)")
    print(f"  Rejections: {rejections}")
    print(f"  Separation (km): {results[name]['spatial_separation_stats_km']}")
    print(f"  Residual Stats: {results[name]['residual_stats']}")

output_path = os.path.join(REPO_ROOT, "data", "environment", "validation", "collocation_sensitivity_audit.json")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved sensitivity audit to {output_path}")
