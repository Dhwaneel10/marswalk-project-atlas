"""Project Atlas / MarsWalk 2.0 — Milestone 13X
Atlas Mission Grand Prix: Martian Scenario Generator.

Generates reproducible planetary mission scenarios across 7 orthogonal dimensions:
  1. Terrain: Real USGS 20m CTX Jezero raster and synthetic terrain fields
  2. Atmosphere: MEDA-grounded diurnal temperature, dust tau, and atmospheric density
  3. Resources: Tight to high energy budgets, battery degradation, and consumables
  4. Comms: OWLT delays (3.2 to 21.8 min), blackouts, and relay dropouts
  5. Fleet: Heterogeneous combinations (Rovers, Hexacopters, Builders)
  6. Science: Competing Bayesian hypotheses (Lacustrine, Volcanic, Hydrothermal)
  7. Compound Faults: Discrete runtime perturbations for resilience benchmarking

Supports partitioned scenario sets:
  - DEVELOPMENT Set (seeds 1000-1199, N=200)
  - TUNING Set (seeds 2000-2299, N=300)
  - HELD-OUT CHALLENGE Set (seeds 5000-9999, N=5,000+)
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import rasterio
    from marswalk.core.terrain import compute_horn_slope
except ImportError:
    rasterio = None
    compute_horn_slope = None

from marswalk.core.atlas_strategy_registry import ScenarioPlanningContext


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DTM_PATHS = [
    REPO_ROOT / "data" / "processed" / "jezero_ready_20m.tif",
    REPO_ROOT / "data" / "terrain" / "usgs_jezero_20m.tif",
]


class ScenarioPartition(str, Enum):
    """Experiment dataset partitions."""
    DEVELOPMENT = "DEVELOPMENT"
    TUNING = "TUNING"
    HELD_OUT = "HELD_OUT"


@dataclass
class ScenarioFaultEvent:
    """A discrete perturbation injected during runtime simulation."""
    fault_id: str
    target_subsystem: str  # POWER, DRIVE, COMMS, INSTRUMENT, DUST
    onset_sol: float
    duration_sols: float
    severity_fraction: float  # 0.0 to 1.0 degradation
    description: str


@dataclass
class GrandPrixScenario:
    """Complete specification of a benchmark scenario."""
    scenario_id: str
    partition: ScenarioPartition
    seed: int
    planning_context: ScenarioPlanningContext
    injected_faults: List[ScenarioFaultEvent]
    is_synthetic_terrain: bool
    source_elevation_sha256: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize scenario metadata for auditing and reproduction."""
        return {
            "scenario_id": self.scenario_id,
            "partition": self.partition.value,
            "seed": self.seed,
            "mission_title": self.planning_context.mission_title,
            "duration_sols": self.planning_context.duration_sols,
            "site_id": self.planning_context.site_id,
            "is_synthetic_terrain": self.is_synthetic_terrain,
            "source_elevation_sha256": self.source_elevation_sha256,
            "science_targets_count": len(self.planning_context.science_targets),
            "fleet_assets_count": len(self.planning_context.fleet_assets),
            "injected_faults_count": len(self.injected_faults),
            "injected_faults": [dataclasses.asdict(f) for f in self.injected_faults],
            "environmental_params": self.planning_context.environmental_params,
            "comms_params": self.planning_context.comms_params,
            "resource_initial": self.planning_context.resource_initial,
            "metadata": self.metadata,
        }


class GrandPrixScenarioGenerator:
    """Procedural generator for high-fidelity planetary mission scenarios."""

    _cached_dtm: Optional[np.ndarray] = None
    _cached_slopes: Optional[np.ndarray] = None
    _cached_dtm_hash: str = ""

    @classmethod
    def _load_base_dtm(cls) -> Tuple[np.ndarray, np.ndarray, str]:
        """Load and cache authentic USGS Jezero 20m DTM elevation and slope rasters."""
        if cls._cached_dtm is not None and cls._cached_slopes is not None:
            return cls._cached_dtm, cls._cached_slopes, cls._cached_dtm_hash

        dtm_path = next((p for p in DTM_PATHS if p.exists()), None)
        if dtm_path and rasterio is not None and compute_horn_slope is not None:
            with rasterio.open(dtm_path) as src:
                elev = src.read(1).astype(np.float32)
            slopes = compute_horn_slope(elev, 20.0, 20.0).astype(np.float32)
            hasher = hashlib.sha256()
            with open(dtm_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            cls._cached_dtm = elev
            cls._cached_slopes = slopes
            cls._cached_dtm_hash = hasher.hexdigest()
        else:
            # Fallback synthetic 100x100 grid if rasterio unavailable
            grid_size = 100
            x = np.linspace(-2.0, 2.0, grid_size)
            y = np.linspace(-2.0, 2.0, grid_size)
            xx, yy = np.meshgrid(x, y)
            elev = (-2500.0 + 40.0 * np.sin(xx * 2.0) + 30.0 * np.cos(yy * 2.0)).astype(np.float32)
            slopes = np.clip(np.abs(np.gradient(elev, 20.0)[0]) * 5.0, 0.5, 25.0).astype(np.float32)
            cls._cached_dtm = elev
            cls._cached_slopes = slopes
            cls._cached_dtm_hash = "SYNTHETIC_ELEVATION_FALLBACK_100X100"

        return cls._cached_dtm, cls._cached_slopes, cls._cached_dtm_hash

    @classmethod
    def generate_scenario(
        cls,
        seed: int,
        partition: ScenarioPartition = ScenarioPartition.DEVELOPMENT,
        custom_duration_sols: Optional[int] = None,
        force_synthetic_terrain: bool = False,
    ) -> GrandPrixScenario:
        """Generate a deterministic, scientifically grounded scenario from a random seed."""
        rng = np.random.RandomState(seed)
        base_elev, base_slopes, dtm_hash = cls._load_base_dtm()

        prefix = "DEV" if partition == ScenarioPartition.DEVELOPMENT else ("TUNE" if partition == ScenarioPartition.TUNING else "CHALLENGE")
        scenario_id = f"SCEN-{prefix}-{seed:04d}"

        # ----------------------------------------------------------------------
        # 1. Terrain Window Extraction or Synthesis
        # ----------------------------------------------------------------------
        subgrid_dim = 60  # 60x60 cells = 1.2 km x 1.2 km local operational region
        max_r = max(1, base_elev.shape[0] - subgrid_dim)
        max_c = max(1, base_elev.shape[1] - subgrid_dim)

        row_offset = rng.randint(0, max_r)
        col_offset = rng.randint(0, max_c)

        if not force_synthetic_terrain and dtm_hash != "SYNTHETIC_ELEVATION_FALLBACK_100X100":
            elev_grid = np.copy(base_elev[row_offset : row_offset + subgrid_dim, col_offset : col_offset + subgrid_dim])
            slope_grid = np.copy(base_slopes[row_offset : row_offset + subgrid_dim, col_offset : col_offset + subgrid_dim])
            is_synthetic = False
            terrain_source = "USGS CTX 20m Jezero Crater DTM"
        else:
            # Procedural synthetic crater & fracture field
            x = np.linspace(-3.0, 3.0, subgrid_dim)
            y = np.linspace(-3.0, 3.0, subgrid_dim)
            xx, yy = np.meshgrid(x, y)
            elev_grid = (-2550.0 + 60.0 * np.exp(-(xx**2 + yy**2) / 2.0) + rng.normal(0, 2.0, (subgrid_dim, subgrid_dim))).astype(np.float32)
            slope_grid = np.clip(np.abs(np.gradient(elev_grid, 20.0)[0]) * 57.3, 0.2, 35.0).astype(np.float32)
            is_synthetic = True
            terrain_source = "Synthetic Procedural Martian Scarp"

        # ----------------------------------------------------------------------
        # 2. Environmental Conditions (MEDA Grounded)
        # ----------------------------------------------------------------------
        # Diurnal temp: Jezero min ~185K, max ~260K
        diurnal_min_k = float(rng.uniform(180.0, 195.0))
        diurnal_max_k = float(rng.uniform(250.0, 275.0))
        # Atmospheric dust optical depth tau: nominal 0.35 - 0.7; storm up to 2.2
        is_dusty = bool(rng.rand() < 0.25)
        dust_tau = float(rng.uniform(1.2, 2.5) if is_dusty else rng.uniform(0.35, 0.8))
        wind_speed_mps = float(rng.uniform(3.0, 14.0) if not is_dusty else rng.uniform(12.0, 26.0))
        atmo_density_kg_m3 = float(rng.uniform(0.0135, 0.0165))  # typical Jezero ~0.015 kg/m3

        environmental_params = {
            "temp_min_k": round(diurnal_min_k, 1),
            "temp_max_k": round(diurnal_max_k, 1),
            "dust_optical_depth_tau": round(dust_tau, 2),
            "wind_speed_mps": round(wind_speed_mps, 1),
            "atmospheric_density_kg_m3": round(atmo_density_kg_m3, 5),
            "solar_insolation_w_m2": round(590.0 * math.exp(-dust_tau * 0.7), 1),
            "is_dust_storm": is_dusty,
        }

        # ----------------------------------------------------------------------
        # 3. Communications Profile
        # ----------------------------------------------------------------------
        # Earth-Mars distance varies: OWLT between 3.5 and 21.5 minutes
        owlt_mins = float(rng.uniform(3.8, 20.5))
        comms_reliability = float(rng.uniform(0.92, 0.999))
        comms_params = {
            "owlt_minutes": round(owlt_mins, 2),
            "round_trip_delay_minutes": round(owlt_mins * 2.0, 2),
            "uplink_bandwidth_kbps": int(rng.choice([128, 256, 512, 1024])),
            "packet_delivery_rate": round(comms_reliability, 3),
            "relay_pass_window_hours": round(float(rng.uniform(1.5, 4.0)), 1),
        }

        # ----------------------------------------------------------------------
        # 4. Fleet Assets (Ground Rover + Aircraft + Builder)
        # ----------------------------------------------------------------------
        fleet_assets = [
            {
                "asset_id": "ATLAS-ROVER-01",
                "asset_type": "HEAVY_ROVER",
                "max_speed_mps": 0.045,
                "nominal_power_w": 280.0,
                "max_slope_deg": 15.0,
                "battery_capacity_kwh": 65.0,
                "payload_kg": 120.0,
            }
        ]
        # 60% of scenarios include rotorcraft
        if rng.rand() < 0.60:
            fleet_assets.append({
                "asset_id": "HEXACOPTER-SURVEYOR-02",
                "asset_type": "ROTORCRAFT",
                "max_speed_mps": 8.5,
                "nominal_power_w": 950.0,
                "max_slope_deg": 45.0,
                "battery_capacity_kwh": 3.8,
                "max_range_km": 1.5,
            })
        # 40% include construction bot
        if rng.rand() < 0.40:
            fleet_assets.append({
                "asset_id": "CONSTRUCTION-BOT-01",
                "asset_type": "SETTLEMENT_BUILDER",
                "max_speed_mps": 0.025,
                "nominal_power_w": 450.0,
                "max_slope_deg": 10.0,
                "battery_capacity_kwh": 45.0,
                "payload_kg": 250.0,
            })

        # ----------------------------------------------------------------------
        # 5. Science Targets & Competing Hypotheses
        # ----------------------------------------------------------------------
        num_targets = rng.randint(4, 9)
        science_targets = []
        geological_formations = [
            ("Western Delta Scarp", "Clay / phyllosilicate fine laminations", 1.8),
            ("Neretva Vallis Outwash Apron", "Coarse alluvial conglomerates", 1.4),
            ("Belva Crater Ejecta", "Deep crustal impact breccia", 2.0),
            ("Séítah Layered Olivine Unit", "Igneous cumulate olivine-carbonate", 1.6),
            ("Cape Nukshak Promontory", "Mudstones with potential organics", 2.2),
            ("Skrinkle Haven Channel", "Cross-bedded fluvial sandstones", 1.5),
            ("Kodiak Isolated Butte", "Deltaic topset-foreset bottomset layers", 2.4),
            ("Alagnak Carbonate Splay", "Magnesite-rich margin carbonates", 1.9),
        ]
        rng.shuffle(geological_formations)

        for i in range(num_targets):
            name, desc, base_gain = geological_formations[i % len(geological_formations)]
            tr = int(rng.randint(5, subgrid_dim - 5))
            tc = int(rng.randint(5, subgrid_dim - 5))
            science_targets.append({
                "target_id": f"TGT-{i+1:02d}",
                "name": name,
                "geological_context": desc,
                "location_rc": (tr, tc),
                "expected_gain": round(base_gain + float(rng.uniform(-0.3, 0.4)), 2),
                "prior_entropy": round(float(rng.uniform(0.65, 0.98)), 3),
                "min_dwell_sols": round(float(rng.uniform(0.5, 2.0)), 1),
            })

        # ----------------------------------------------------------------------
        # 6. Resource Initial Inventory
        # ----------------------------------------------------------------------
        duration_sols = custom_duration_sols or int(rng.choice([15, 30, 45, 60]))
        resource_initial = {
            "battery_capacity_kwh": float(rng.uniform(60.0, 100.0)),
            "battery_initial_soc_pct": round(float(rng.uniform(75.0, 100.0)), 1),
            "power_generation_rated_kw": round(float(rng.uniform(2.5, 10.0)), 1),
            "water_reserve_kg": round(float(rng.uniform(1500.0, 3500.0)), 1),
            "oxygen_reserve_kg": round(float(rng.uniform(600.0, 1400.0)), 1),
            "spare_parts_inventory_units": int(rng.randint(4, 12)),
        }

        # ----------------------------------------------------------------------
        # 7. Competing Hypotheses
        # ----------------------------------------------------------------------
        active_hypotheses = [
            {"id": "H-LACUSTRINE", "claim": "Long-lived lacustrine delta deposit with habitable benthic zones.", "prior": 0.45},
            {"id": "H-VOLCANIC", "claim": "Rapid pyroclastic density current ash deposition.", "prior": 0.35},
            {"id": "H-HYDROTHERMAL", "claim": "Post-impact sub-surface hydrothermal mineral alteration.", "prior": 0.20},
        ]

        # ----------------------------------------------------------------------
        # 8. Injected Fault Events (Runtime perturbations)
        # ----------------------------------------------------------------------
        fault_types = ["POWER", "DRIVE", "COMMS", "INSTRUMENT", "DUST"]
        injected_faults = []
        num_faults = rng.choice([0, 1, 2, 3], p=[0.35, 0.40, 0.20, 0.05])

        for f_idx in range(num_faults):
            f_type = str(rng.choice(fault_types))
            onset = float(rng.uniform(3.0, duration_sols * 0.75))
            dur = float(rng.uniform(1.0, 7.0))
            sev = float(rng.uniform(0.20, 0.65))
            desc = f"{f_type} subsystem perturbation: {sev*100:.0f}% capacity reduction"
            injected_faults.append(ScenarioFaultEvent(
                fault_id=f"FLT-{scenario_id}-{f_idx+1:02d}",
                target_subsystem=f_type,
                onset_sol=round(onset, 1),
                duration_sols=round(dur, 1),
                severity_fraction=round(sev, 2),
                description=desc,
            ))

        start_r = int(subgrid_dim // 2)
        start_c = int(subgrid_dim // 2)

        context = ScenarioPlanningContext(
            scenario_id=scenario_id,
            seed=seed,
            site_id="SITE-JEZERO-DELTA-WEST",
            mission_title=f"Grand Prix Campaign {scenario_id}",
            duration_sols=duration_sols,
            start_coord=(start_r, start_c),
            elevation_grid=elev_grid,
            slope_grid=slope_grid,
            resolution_m=20.0,
            science_targets=science_targets,
            fleet_assets=fleet_assets,
            environmental_params=environmental_params,
            comms_params=comms_params,
            resource_initial=resource_initial,
            active_hypotheses=active_hypotheses,
        )

        return GrandPrixScenario(
            scenario_id=scenario_id,
            partition=partition,
            seed=seed,
            planning_context=context,
            injected_faults=injected_faults,
            is_synthetic_terrain=is_synthetic,
            source_elevation_sha256=dtm_hash,
            metadata={
                "terrain_source": terrain_source,
                "subgrid_shape": list(elev_grid.shape),
                "elevation_min_m": float(np.min(elev_grid)),
                "elevation_max_m": float(np.max(elev_grid)),
                "slope_max_deg": float(np.max(slope_grid)),
            },
        )

    @classmethod
    def generate_partition_suite(
        cls,
        partition: ScenarioPartition,
        count: int = 100,
        start_seed: Optional[int] = None,
    ) -> List[GrandPrixScenario]:
        """Generate a complete reproducible batch of scenarios for a given partition."""
        if start_seed is None:
            if partition == ScenarioPartition.DEVELOPMENT:
                start_seed = 1000
            elif partition == ScenarioPartition.TUNING:
                start_seed = 2000
            else:
                start_seed = 5000

        scenarios = []
        for i in range(count):
            scenarios.append(cls.generate_scenario(seed=start_seed + i, partition=partition))
        return scenarios
