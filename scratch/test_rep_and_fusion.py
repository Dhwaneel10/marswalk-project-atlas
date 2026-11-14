import sys
sys.path.insert(0, 'src')
import numpy as np
from marswalk.core.environmental_representativeness import PlanetaryRepresentativenessEngine
from marswalk.core.environment_field_update import EnvironmentFieldFusionEngine
from marswalk.core.mars_environment_collocation import CollocatedObservationModelPair

# Test representativeness
rep_engine = PlanetaryRepresentativenessEngine()
eval1 = rep_engine.evaluate_representativeness(
    obs_id="MEDA_TIRS_SOL_10", obs_lat=18.4447, obs_lon=77.4508, obs_elev_m=-2574.0, obs_ltst_h=13.9, obs_ls_deg=10.5,
    target_id="WP_SEITAH_01", target_lat=18.4450, target_lon=77.4510, target_elev_m=-2570.0, target_ltst_h=14.1, target_ls_deg=10.6
)
print("Representativeness (Close In-Situ):", eval1.classification, "CRI:", eval1.composite_index, eval1.confidence_verdict)

eval2 = rep_engine.evaluate_representativeness(
    obs_id="MEDA_TIRS_SOL_10", obs_lat=18.4447, obs_lon=77.4508, obs_elev_m=-2574.0, obs_ltst_h=13.9, obs_ls_deg=10.5,
    target_id="WP_RIM_SCARP", target_lat=18.5200, target_lon=77.3500, target_elev_m=-2100.0, target_ltst_h=06.0, target_ls_deg=120.0
)
print("Representativeness (Rim at Dawn/Winter):", eval2.classification, "CRI:", eval2.composite_index, eval2.confidence_verdict)

# Test field fusion
fusion_engine = EnvironmentFieldFusionEngine(influence_radius_pixels=20.0)
bg = np.full((50, 50), -35.0, dtype=np.float32)  # small test grid
pair = CollocatedObservationModelPair(
    pair_id="PAIR_01", parameter_name="ground_temperature", unit="C", sol=10, observation_id="OBS_01",
    observed_value=-28.0, observed_uncertainty_1sigma=1.5, model_name="ATLAS_13L", model_value=-35.0,
    residual=-7.0, relative_error_pct=20.0, spatial_separation_km=0.1, delta_ltst_hours=0.0, delta_ls_deg=0.0,
    gate_status="COLLOCATION_QUALIFIED", rejection_reason=None, representativeness_class="DIRECT_LOCAL_MATCH"
)
product = fusion_engine.generate_assimilated_field(
    parameter_name="ground_temperature", unit="C", sol=10, ltst_hours=13.5, ls_deg=10.5,
    background_grid=bg, collocated_pairs=[pair]
)
print("\nField Fusion Product:", product.product_id)
print(f"Background mean: {product.background_mean} C | Assimilated mean: {product.assimilated_mean} C | Max adjustment: {product.max_assimilation_adjustment} C")
print("Provenance:", product.provenance_classification)
