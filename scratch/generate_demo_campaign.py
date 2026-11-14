"""
Generate dedicated, deterministic conference demonstration campaign:
cmp_conference_demo_jezero.json
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from marswalk.core.terrain import load_and_process_terrain
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    plan_mission_campaign,
)
from marswalk.api.workspace import save_campaign

def main():
    print("Loading terrain...")
    terrain = load_and_process_terrain("data/processed/jezero_ready_20m.tif")
    print(f"Terrain loaded: {terrain.shape}, SHA-256: {getattr(terrain, 'sha256', None)}")

    targets = [
        CampaignTarget(
            id="tgt_demo_1",
            name="Delta Scarp Lithic Sample",
            row=115,
            col=155,
            priority_score=95.0,
            dwell_time_s=900.0,
            geological_context="Stratified delta front scarp deposits",
            crism_signature="Fe/Mg phyllosilicates"
        ),
        CampaignTarget(
            id="tgt_demo_2",
            name="Crater Floor Regolith Survey",
            row=125,
            col=150,
            priority_score=80.0,
            dwell_time_s=900.0,
            geological_context="Volcanic crater floor olivine unit",
            crism_signature="Olivine and pyroxene"
        ),
        CampaignTarget(
            id="tgt_demo_3",
            name="Carbonate Ridge Exploration",
            row=110,
            col=162,
            priority_score=90.0,
            dwell_time_s=900.0,
            geological_context="Marginal carbonate-bearing sedimentary rocks",
            crism_signature="Mg-carbonates"
        ),
        CampaignTarget(
            id="tgt_demo_4",
            name="Kodiak Butte Promontory",
            row=105,
            col=145,
            priority_score=85.0,
            dwell_time_s=900.0,
            geological_context="Isolated delta remnant butte",
            crism_signature="Deltaic bottomset beds"
        ),
        CampaignTarget(
            id="tgt_demo_5",
            name="Neretva Vallis Inflow Channel",
            row=95,
            col=170,
            priority_score=75.0,
            dwell_time_s=900.0,
            geological_context="Fluvial breach channel wall",
            crism_signature="Hydrated silica and clays"
        ),
        CampaignTarget(
            id="tgt_demo_6",
            name="Belva Crater Ejecta Rim",
            row=130,
            col=165,
            priority_score=70.0,
            dwell_time_s=900.0,
            geological_context="Impact crater ejecta blanket",
            crism_signature="Shocked basaltic breccia"
        )
    ]

    config = CampaignConfig(
        planning_profile="science_priority",
        vehicle_mode="crew_eva",
        speed_multiplier=1.0,
        max_duration_per_sortie_s=6000.0, # ~1.67 hours per sortie
        max_sols=3,
        base_start_rc=(117, 157),
        base_end_rc=(117, 157),
        return_to_base_each_sol=True,
        dwell_time_per_stop_s=900.0
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_conference_demo_jezero",
        name="Jezero Crater Conference Demonstration Campaign",
        config=config,
        targets=targets,
        terrain=terrain,
        description="Standard multi-sol exploration campaign across the Jezero Western Delta Front for conference demonstrations and technical evaluations."
    )

    save_campaign(campaign.to_dict(), allow_overwrite=True)
    print("Demo campaign saved successfully:", campaign.campaign_id)
    print(f"Sorties planned: {len(campaign.sorties)}")
    for s in campaign.sorties:
        print(f" - {s.name}: targets {s.target_ids}, duration {s.total_duration_s:.1f}s ({s.total_duration_s/3600:.2f}h), distance {s.distance_m:.1f}m")

if __name__ == "__main__":
    main()
