"""MarsWalk 2.0 / Project Atlas - Evidence Inspector & Traceability Engine.

Provides authoritative provenance metadata, physical formulations, source citations,
and scientific limitations for any displayed metric or decision in MarsWalk.

Adheres strictly to the Scientific Evidence & Traceability Matrix (docs/scientific-evidence-traceability.md).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Classification constants
CLASS_MEASURED_REMOTE_SENSING = "MEASURED_REMOTE_SENSING"
CLASS_DERIVED_PLANETARY_GEOMETRY = "DERIVED_PLANETARY_GEOMETRY"
CLASS_DETERMINISTIC_GEODESY = "DETERMINISTIC_GEODESY"
CLASS_IN_SITU_ARCHIVAL_OBSERVATION = "IN_SITU_ARCHIVAL_OBSERVATION"
CLASS_MATHEMATICAL_ENERGY_PROXY = "MATHEMATICAL_ENERGY_PROXY"
CLASS_TERRESTRIAL_LUNAR_ANALOGUE = "TERRESTRIAL_LUNAR_ANALOGUE"
CLASS_SOURCED_TECHNICAL_VALUE = "SOURCED_TECHNICAL_VALUE"
CLASS_PLANNING_APPROXIMATION = "PLANNING_APPROXIMATION"
CLASS_NUMERICAL_CLIMATOLOGY = "NUMERICAL_CLIMATOLOGY"
CLASS_MULTI_OBJECTIVE_OPTIMIZATION = "MULTI_OBJECTIVE_OPTIMIZATION"
CLASS_DETERMINISTIC_SIMULATION = "DETERMINISTIC_SIMULATION"
CLASS_EXPLAINABLE_DIAGNOSTIC = "EXPLAINABLE_DIAGNOSTIC"
CLASS_DETERMINISTIC_GATE = "DETERMINISTIC_GATE"

AEROSPACE_DISCLAIMER = (
    "MarsWalk 2.0 (Project Atlas) is a scientific decision-support prototype and mission rehearsal simulator. "
    "Passing software test gates, automated preflight checks, or benchmark scenarios does NOT constitute aerospace "
    "operational safety certification, flight readiness review authorization, or live flight software clearance "
    "for human extravehicular activities or autonomous planetary rovers."
)

EVIDENCE_CATALOG: Dict[str, Dict[str, Any]] = {
    "elevation": {
        "title": "Terrain Elevation & Topography",
        "units": "meters",
        "classification": CLASS_MEASURED_REMOTE_SENSING,
        "classification_label": "Measured Remote Sensing",
        "primary_source": "USGS CTX DTM (data/processed/jezero_ready_20m.tif)",
        "source_archive": "USGS Astrogeology Science Center / NASA PDS Cartography Node",
        "retrieval_or_observation_time": "Processed 2026-10-29 (Surveyed MRO CTX stereo pair)",
        "mathematical_formulation": (
            "250x250 elevation grid, 20.0 m nominal cell spacing. Referenced to IAU 2000 Mars planetocentric sphere "
            "(R = 3,396,190.0 m). Elevation range: -2,623.8 m to -2,445.0 m."
        ),
        "equations": "Z(r, c) = AffineTransform(pixel_coords, georeferenced_matrix)",
        "assumptions": "IAU 2000 Mars Planetocentric Volumetric Mean Sphere Datum (R = 3,396,190.0 m).",
        "limitations": (
            "Derived from optical stereo remote sensing at 20 m/pixel nominal resolution. Sub-pixel hazards "
            "(meter-scale boulders, localized fissures, soft sand ripples) cannot be resolved. Not certified for "
            "autonomous rover landing or astronaut hazard avoidance."
        ),
        "verifying_suite": "tests/test_terrain.py, tests/test_milestone_12c_terrain_intelligence.py",
    },
    "ground_distance": {
        "title": "Ground Metric Distance",
        "units": "meters",
        "classification": CLASS_DETERMINISTIC_GEODESY,
        "classification_label": "Deterministic Geodesy",
        "primary_source": "Raster row/column coordinates & affine transform",
        "source_archive": "Project Atlas Cartographic Projection Subsystem",
        "retrieval_or_observation_time": "Calculated on demand",
        "mathematical_formulation": (
            "Planar metric distance under equirectangular scale for Jezero latitude (phi = 18.442 deg N): "
            "dx = cell_size_m * cos(18.442 deg) ~= 18.973 m/col; dy = cell_size_m = 20.0 m/row. "
            "d = sqrt((delta_c * dx)^2 + (delta_r * dy)^2)."
        ),
        "equations": "d = sqrt((delta_c * 18.973)^2 + (delta_r * 20.0)^2)",
        "assumptions": "Locally conformal approximation valid within the 5.0 x 5.0 km Jezero study boundary.",
        "limitations": "Geodesic distortion increases at higher Martian latitudes. Do not use for global circumnavigation.",
        "verifying_suite": "tests/test_terrain.py",
    },
    "slope": {
        "title": "Local Terrain Slope",
        "units": "degrees",
        "classification": CLASS_DERIVED_PLANETARY_GEOMETRY,
        "classification_label": "Derived Planetary Geometry",
        "primary_source": "USGS CTX DTM Elevation Matrix Z(r, c)",
        "source_archive": "Horn (1981) Finite-Difference Gradient Implementation",
        "retrieval_or_observation_time": "Precomputed with elevation cache",
        "mathematical_formulation": (
            "Horn's 3x3 weighted finite-difference gradient: "
            "dz/dx = ((c22 + 2*c21 + c20) - (c02 + 2*c01 + c00)) / (8 * dx); "
            "dz/dy = ((c00 + 2*c10 + c20) - (c02 + 2*c12 + c22)) / (8 * dy); "
            "theta = arctan(sqrt((dz/dx)^2 + (dz/dy)^2)) * (180 / pi)."
        ),
        "equations": "theta = arctan(sqrt((dz/dx)^2 + (dz/dy)^2)) * (180/pi)",
        "assumptions": "Uniform 3x3 local topographic slope over decameter baseline.",
        "limitations": (
            "Smooths localized sub-pixel scarps and overhangs. Cells with theta >= theta_max "
            "(16 deg conservative, 22 deg balanced, 25 deg science) are treated as impassable cutoff barriers."
        ),
        "verifying_suite": "tests/test_terrain.py, tests/test_milestone_12c_terrain_intelligence.py",
    },
    "roughness": {
        "title": "Decameter Terrain Roughness",
        "units": "meters (RMS residual)",
        "classification": CLASS_DERIVED_PLANETARY_GEOMETRY,
        "classification_label": "Derived Planetary Geometry",
        "primary_source": "USGS CTX DTM Elevation Matrix Z(r, c)",
        "source_archive": "Planetary Surface Roughness Filter Module",
        "retrieval_or_observation_time": "Precomputed with elevation cache",
        "mathematical_formulation": (
            "Root-mean-square (RMS) residual of a 3x3 uniform box filter relative to the central elevation value: "
            "sigma_r = sqrt((1/9) * sum((Z_i - Z_mean)^2))."
        ),
        "equations": "sigma_r = sqrt(mean((Z - Z_mean)^2))",
        "assumptions": "Surface variance over 3x3 cells approximates mechanical traverse resistance.",
        "limitations": "Decameter proxy for ground unevenness; does NOT resolve centimeter rock distributions or wheel sinkage.",
        "verifying_suite": "tests/test_terrain.py",
    },
    "traversal_cost": {
        "title": "Directed Edge Traversal Cost",
        "units": "meters (equivalent flat effort)",
        "classification": CLASS_MATHEMATICAL_ENERGY_PROXY,
        "classification_label": "Mathematical Energy Proxy",
        "primary_source": "Minetti (2002) metabolic expenditure formulation adapted for planetary terrain",
        "source_archive": "MarsWalk Traversal Cost Model",
        "retrieval_or_observation_time": "Evaluated during A* graph search",
        "mathematical_formulation": (
            "C(u -> v) = d * [1 + alpha_s * (theta / theta_c)^2 + alpha_r * (sigma / sigma_0) + alpha_up * max(0, delta_z / d)]. "
            "For crew EVA: alpha_s = 2.0, theta_c = 15.0 deg, alpha_up = 4.0. For rover: alpha_s = 3.0, theta_c = 12.0 deg, alpha_up = 2.5."
        ),
        "equations": "C = d * [1 + alpha_s*(theta/theta_c)^2 + alpha_r*(sigma/sigma_0) + alpha_up*max(0, dz/d)]",
        "assumptions": "Cost proportional to mechanical/metabolic effort. Discontinuous barrier at theta >= theta_max.",
        "limitations": "Planning proxy for comparative route selection; does not model specific battery thermal chemistry.",
        "verifying_suite": "tests/test_terrain.py, tests/test_planner.py",
    },
    "crew_eva": {
        "title": "Suited Astronaut EVA Velocity & Energy",
        "units": "km/h (speed), Wh/km (energy)",
        "classification": CLASS_TERRESTRIAL_LUNAR_ANALOGUE,
        "classification_label": "Terrestrial / Lunar Analogue",
        "primary_source": "Apollo Lunar Surface EVA Traverses (NASA SP-287 / Waligora et al. 1975)",
        "source_archive": "NASA Human Integration Design Handbook (HIDH)",
        "retrieval_or_observation_time": "Configured baseline parameter",
        "mathematical_formulation": (
            "Nominal walking speed v_nom = 2.0 km/h (0.556 m/s). Speed slows inversely with terrain slope: "
            "v(theta) = v_nom / (1 + (theta / 15 deg)^2). Consumables budget limit: 8.0 h (28,800 s) per sortie. "
            "Locomotion metabolic energy rate: 92.0 Wh/km (331.2 kJ/km)."
        ),
        "equations": "v = v_nom / (1 + (theta/15)^2), E = 92.0 Wh/km * d_km",
        "assumptions": "Crew member in pressurized planetary EVA suit walking in 0.38g gravity.",
        "limitations": (
            "Based on Apollo lunar surface data (0.16g) and terrestrial desert analogue tests. "
            "NOT validated with actual Mars-gravity pressurized space suit telemetry."
        ),
        "verifying_suite": "tests/test_planner.py, tests/test_milestone_11f_campaign_simulator.py",
    },
    "rover_drive": {
        "title": "Robotic Rover Velocity & Energy",
        "units": "m/s (speed), Wh/km (energy)",
        "classification": CLASS_SOURCED_TECHNICAL_VALUE,
        "classification_label": "Sourced Technical Value",
        "primary_source": "NASA/JPL Mars 2020 Perseverance / MSL Curiosity Mission Telemetry",
        "source_archive": "NASA JPL Planetary Data System / Flight Operations Logs",
        "retrieval_or_observation_time": "Configured baseline parameter",
        "mathematical_formulation": (
            "Nominal autonomous auto-nav speed v_nom = 0.035 m/s (0.126 km/h). Drive window per sol: 4.0 h (14,400 s). "
            "Locomotion electrical consumption: 18.5 Wh/km (66.6 kJ/km)."
        ),
        "equations": "v = 0.035 m/s, E = 18.5 Wh/km * d_km",
        "assumptions": "Standard multi-wheel rocker-bogie rover operating autonomous hazard avoidance.",
        "limitations": "Does not account for high slip in unconsolidated drift sand or mechanical thermal stalling.",
        "verifying_suite": "tests/test_planner.py, tests/test_milestone_11f_campaign_simulator.py",
    },
    "weather_meda": {
        "title": "Jezero Crater In-Situ Atmospheric Weather",
        "units": "deg C (temp), Pa (pressure), m/s (wind), tau (optical depth)",
        "classification": CLASS_IN_SITU_ARCHIVAL_OBSERVATION,
        "classification_label": "In-Situ Archival Observation",
        "primary_source": "NASA PDS Mars 2020 Perseverance MEDA (Mars Environmental Dynamics Analyzer)",
        "source_archive": "NASA Planetary Data System (PDS) Atmospheres Node",
        "retrieval_or_observation_time": "Perseverance Sol 890 Derived Observation Record",
        "mathematical_formulation": (
            "Direct ingestion of calibrated in-situ sensor logs: T_air = -61.7 deg C, T_gnd = -28.4 deg C, "
            "P = 589.69 Pa, wind_speed = 4.2 m/s, tau = 0.42. Boundary checks enforced by PhysicalRangeGuard."
        ),
        "equations": "Calibrated RTD, capacitive barometer, optical thermal radiometer readings",
        "assumptions": "In-situ Jezero Crater atmospheric conditions around rover landing site.",
        "limitations": (
            "Historical archived PDS4 observation tranche. This is NOT real-time Martian weather telemetry. "
            "Strictly isolated to Jezero Crater; never projected to Gale Crater or Olympus Mons."
        ),
        "verifying_suite": "tests/test_milestone_10d_weather_intelligence.py",
    },
    "weather_rems": {
        "title": "Gale Crater In-Situ Atmospheric Weather",
        "units": "deg C (temp), Pa (pressure), m/s (wind), tau (optical depth)",
        "classification": CLASS_IN_SITU_ARCHIVAL_OBSERVATION,
        "classification_label": "In-Situ Archival Observation",
        "primary_source": "NASA PDS MSL Curiosity REMS (Rover Environmental Monitoring Station)",
        "source_archive": "NASA Planetary Data System (PDS) Atmospheres Node",
        "retrieval_or_observation_time": "Curiosity Sol 3950 Derived Observation Record",
        "mathematical_formulation": (
            "Calibrated surface meteorological sensor logs from Mount Sharp traverse in Gale Crater."
        ),
        "equations": "REMS ground temperature sensor, pressure sensor, Boom 1/2 anemometers",
        "assumptions": "In-situ Gale Crater conditions (latitude 4.6 deg S).",
        "limitations": "Strictly isolated to Gale Crater site; never extrapolated or blended with Jezero Crater data.",
        "verifying_suite": "tests/test_milestone_10d_weather_intelligence.py",
    },
    "readiness_gate": {
        "title": "Mission Readiness & Decision Gate Assessment",
        "units": "categorical (GO / CONDITIONAL / NO-GO)",
        "classification": CLASS_DETERMINISTIC_GATE,
        "classification_label": "Deterministic Gate",
        "primary_source": "MarsWalk Mission Readiness Evaluator (12 Checkpoints)",
        "source_archive": "Project Atlas Mission Readiness Architecture",
        "retrieval_or_observation_time": "Evaluated on demand",
        "mathematical_formulation": (
            "12 deterministic rules evaluating terrain boundary conformance, slope safety cutoff, "
            "energy envelope, duration limits, weather extremes, prerequisite DAG satisfaction, "
            "and black box ledger integrity. Status: GO if 0 warnings/failures; CONDITIONAL if warnings only; NO-GO if any failure."
        ),
        "equations": "Status in {GO, CONDITIONAL, NO_GO} = f(12 deterministic checkpoints)",
        "assumptions": "Planning guidelines enforce conservative safety margins.",
        "limitations": (
            "Software readiness decision gate only. Passing readiness evaluation does NOT authorize flight operations "
            "or guarantee physical astronaut safety."
        ),
        "verifying_suite": "tests/test_milestone_10f_mission_readiness.py",
    },
    "pareto_optimization": {
        "title": "Candidate Pareto Dominance Frontier",
        "units": "multi-objective vector (distance, duration, margin, science)",
        "classification": CLASS_MULTI_OBJECTIVE_OPTIMIZATION,
        "classification_label": "Multi-Objective Optimization",
        "primary_source": "Evaluated campaign objective vectors z(c)",
        "source_archive": "Project Atlas Design Space Explorer",
        "retrieval_or_observation_time": "Evaluated across bounded candidate grid",
        "mathematical_formulation": (
            "Strict Pareto dominance: Candidate A dominates Candidate B iff (forall i: z_i^A >= z_i^B) "
            "and (exists j: z_j^A > z_j^B) and Feasible(A)."
        ),
        "equations": "A dom B <=> (forall i, z_i^A >= z_i^B) and (exists j, z_j^A > z_j^B)",
        "assumptions": "Evaluated over a bounded grid of plausible campaign configurations.",
        "limitations": "Non-dominated candidates are optimal ONLY relative to the evaluated candidate set, not a global analytic optimum.",
        "verifying_suite": "tests/test_milestone_11h_campaign_design_space.py",
    },
    "digital_twin": {
        "title": "Campaign Digital Twin Temporal Simulation",
        "units": "seconds (time), meters (position), Wh (battery)",
        "classification": CLASS_DETERMINISTIC_SIMULATION,
        "classification_label": "Deterministic Simulation",
        "primary_source": "Coordinated campaign plan, A* paths & temporal simulator",
        "source_archive": "Project Atlas Campaign Simulator",
        "retrieval_or_observation_time": "Simulated on demand",
        "mathematical_formulation": (
            "Piecewise linear path traversal interpolation with discrete activity tracking, dwell periods, "
            "battery state-of-charge calculation, and conflict detection."
        ),
        "equations": "pos(t) = interp(path_coords, t / T_travel), SoC(t) = SoC_0 - E_rate * d(t)",
        "assumptions": "Deterministic clock advancement; reproducible timeline execution.",
        "limitations": (
            "Simulated planning rehearsal model. Does not represent live downlink telemetry or certified flight control operations."
        ),
        "verifying_suite": "tests/test_milestone_11f_campaign_simulator.py",
    },
}

# Alias mappings to normalize queries
ALIAS_MAP: Dict[str, str] = {
    "elev": "elevation",
    "alt": "elevation",
    "altitude": "elevation",
    "z": "elevation",
    "topography": "elevation",
    "dtm": "elevation",
    "dist": "ground_distance",
    "distance": "ground_distance",
    "metric_distance": "ground_distance",
    "pitch": "slope",
    "gradient": "slope",
    "terrain_slope": "slope",
    "rough": "roughness",
    "surface_roughness": "roughness",
    "cost": "traversal_cost",
    "energy_proxy": "traversal_cost",
    "effort": "traversal_cost",
    "crew": "crew_eva",
    "astronaut": "crew_eva",
    "eva": "crew_eva",
    "rover": "rover_drive",
    "perseverance": "rover_drive",
    "speed": "rover_drive",
    "weather": "weather_meda",
    "meda": "weather_meda",
    "jezero_weather": "weather_meda",
    "rems": "weather_rems",
    "gale_weather": "weather_rems",
    "readiness": "readiness_gate",
    "gate": "readiness_gate",
    "pareto": "pareto_optimization",
    "design_space": "pareto_optimization",
    "sim": "digital_twin",
    "simulation": "digital_twin",
    "digital_twin_simulation": "digital_twin",
}


def get_metric_evidence(
    metric_key: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Retrieve structured evidence and provenance for a specific metric or decision.

    Args:
        metric_key: Identifier of the metric (e.g., 'elevation', 'slope', 'traversal_cost').
        context: Optional dictionary containing displayed values, campaign ID, route, etc.

    Returns:
        Structured dictionary matching the Scientific Evidence & Traceability Matrix.
    """
    normalized_key = ALIAS_MAP.get(metric_key.lower().strip(), metric_key.lower().strip())
    record = EVIDENCE_CATALOG.get(normalized_key)

    if not record:
        # Graceful handling of unknown metric without fabrication
        return {
            "metric_key": metric_key,
            "status": "UNKNOWN_METRIC",
            "title": f"Uncatalogued Metric: {metric_key}",
            "units": "unknown",
            "classification": "UNCLASSIFIED",
            "classification_label": "Unclassified / Unknown",
            "primary_source": "Not documented in traceability matrix",
            "source_archive": "Unknown Archive",
            "retrieval_or_observation_time": "Unknown",
            "mathematical_formulation": "Formula not registered in system catalog.",
            "equations": "N/A",
            "assumptions": "None documented.",
            "limitations": "No scientific traceability metadata available for this metric key.",
            "aerospace_disclaimer": AEROSPACE_DISCLAIMER,
            "is_flight_certified": False,
        }

    ctx = context or {}
    displayed_value = ctx.get("displayed_value") or ctx.get("value") or ctx.get(normalized_key)

    result = {
        "metric_key": normalized_key,
        "status": "VERIFIED_EVIDENCE",
        "title": record["title"],
        "displayed_value": displayed_value,
        "units": record["units"],
        "classification": record["classification"],
        "classification_label": record["classification_label"],
        "primary_source": record["primary_source"],
        "source_archive": record["source_archive"],
        "retrieval_or_observation_time": record["retrieval_or_observation_time"],
        "mathematical_formulation": record["mathematical_formulation"],
        "equations": record["equations"],
        "assumptions": record["assumptions"],
        "limitations": record["limitations"],
        "verifying_suite": record["verifying_suite"],
        "aerospace_disclaimer": AEROSPACE_DISCLAIMER,
        "is_flight_certified": False,
        "context_identifiers": {
            "campaign_id": ctx.get("campaign_id"),
            "sortie_id": ctx.get("sortie_id"),
            "route_id": ctx.get("route_id"),
            "simulation_id": ctx.get("simulation_id"),
            "sol_index": ctx.get("sol_index"),
        },
    }
    return result


def list_evidence_topics() -> List[Dict[str, str]]:
    """Return a list of all documented evidence topics with descriptions."""
    topics = []
    for key, data in EVIDENCE_CATALOG.items():
        topics.append({
            "metric_key": key,
            "title": data["title"],
            "units": data["units"],
            "classification": data["classification_label"],
            "primary_source": data["primary_source"],
        })
    return sorted(topics, key=lambda t: t["title"])
