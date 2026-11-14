"""
MarsWalk — Mission Rehearsal: Tactical Mission Control Workstation.
Interactive Streamlit dashboard powered by authentic USGS CTX Mars 2020 topography,
deterministic physics cost modeling, and multi-profile traverse trade-off analysis.
"""

import datetime
import json
import math
import os
import sys
import time
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Ensure repository root is on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    load_and_process_terrain,
    calculate_step_distance,
)
from marswalk.core.planner import (
    PlannerConfig,
    ScienceWaypoint,
    compute_pairwise_leg_cache,
    plan_route,
    RouteResult,
)
from marswalk.core.explainer import (
    generate_route_tradeoff_summary,
    get_blind_spot_disclaimer,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    RegretLedger,
    ScenarioComparison,
    ToughnessReport,
    run_scenario,
    compute_science_regret_ledger,
    evaluate_route_toughness,
    get_curated_gauntlet_scenarios,
)
from marswalk.core.preferences import (
    FEATURE_NAMES,
    LearningState,
    RouteFeatures,
    CandidateOption,
    PreferenceObservation,
    RankedRoute,
    PreferenceModel,
    extract_route_features,
    create_choice_id,
    load_preference_model,
    save_preference_model,
)
from marswalk.data.ingest import query_elevation_at_lonlat
from marswalk.core.science_budget import (
    CandidatePlan,
    FrontierResult,
    evaluate_all_candidate_plans,
    check_dominance_2d,
    check_dominance_3d,
    extract_pareto_frontier,
    analyze_science_budget,
    compare_frontiers,
    generate_science_budget_narrative,
    export_mission_brief_csv,
    export_mission_brief_json,
)

# File Paths
DATA_DIR = os.path.join(REPO_ROOT, "data")
PROCESSED_TIFF = os.path.join(DATA_DIR, "processed", "jezero_ready_20m.tif")
WAYPOINTS_JSON = os.path.join(DATA_DIR, "waypoints_jezero.json")
PREFERENCES_FILE = os.path.join(DATA_DIR, "preferences", "commander_preferences.json")


# ==============================================================================
# Cached Ingestion & Leg Network Memoization
# ==============================================================================
@st.cache_resource(show_spinner=False)
def get_cached_terrain(tiff_path: str, alpha_s: float, alpha_r: float, alpha_up: float) -> TerrainGrid:
    """Load and derive terrain matrices with memoization."""
    cfg = TerrainConfig(
        cell_size_m=20.0,
        ref_lat_deg=18.442,
        alpha_s=alpha_s,
        alpha_r=alpha_r,
        alpha_up=alpha_up,
        theta_crit_deg=10.0,
        theta_max_deg=25.0,
    )
    return load_and_process_terrain(tiff_path, config=cfg)


@st.cache_data(show_spinner=False)
def load_raw_waypoints(json_path: str) -> List[Dict[str, Any]]:
    """Load waypoint definitions from JSON."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)["waypoints"]


def compute_hillshade(elevation: np.ndarray, dx: float, dy: float, azimuth_deg: float = 315.0, altitude_deg: float = 45.0) -> np.ndarray:
    """Compute standard 2D analytical hillshade array for visual basemap rendering."""
    azimuth_rad = math.radians(azimuth_deg)
    altitude_rad = math.radians(altitude_deg)

    # Gradients
    dz_dy, dz_dx = np.gradient(elevation, dy, dx)
    slope = np.arctan(np.hypot(dz_dx, dz_dy))
    aspect = np.arctan2(-dz_dy, -dz_dx)

    shaded = (
        np.sin(altitude_rad) * np.cos(slope)
        + np.cos(altitude_rad) * np.sin(slope) * np.cos(azimuth_rad - aspect)
    )
    return np.clip(shaded, 0.0, 1.0)


# ==============================================================================
# UI Styles & Dark Theme Configuration
# ==============================================================================
def inject_custom_css():
    st.markdown(
        """
        <style>
        /* Universal box sizing */
        *, *::before, *::after {
            box-sizing: border-box;
        }

        /* Base obsidian aerospace styling */
        .stApp {
            background-color: #0A0D14;
            color: #E2E8F0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            overflow-x: hidden;
        }

        /* Streamlit main block container responsive padding */
        .block-container {
            padding-top: 3.2rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 100% !important;
        }

        /* Fixed Streamlit header clearance & dark styling */
        header[data-testid="stHeader"] {
            background-color: rgba(10, 13, 20, 0.96) !important;
            backdrop-filter: blur(8px) !important;
            border-bottom: 1px solid #1E2738 !important;
        }
        h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] h5 {
            scroll-margin-top: 4.5rem !important;
        }

        /* Prevent column flex children from overflowing parent width */
        [data-testid="column"] {
            min-width: 0 !important;
        }

        /* Responsive columns for medium and narrow viewports */
        @media (max-width: 1024px) {
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 12px !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: calc(50% - 12px) !important;
                flex: 1 1 calc(50% - 12px) !important;
                margin-bottom: 8px !important;
            }
        }
        @media (max-width: 768px) {
            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }
            .block-container {
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
            }
        }

        /* Plotly responsive container bounds */
        .js-plotly-plot, .plot-container, .plotly, .svg-container {
            max-width: 100% !important;
        }

        /* Mission Control HUD Header */
        .hud-bar {
            background: #111622;
            border: 1px solid #1E2738;
            border-radius: 6px;
            padding: 12px 18px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            width: 100%;
        }
        .hud-title-group {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .hud-title {
            font-size: 1.35rem;
            font-weight: 700;
            color: #F8FAFC;
            letter-spacing: 0.04em;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .hud-brand-tag {
            color: #FF5722;
            font-weight: 800;
        }
        .hud-subtitle {
            font-size: 0.80rem;
            color: #8E9CAE;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .hud-pills {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .hud-pill {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.74rem;
            font-weight: 600;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            font-family: 'JetBrains Mono', Consolas, monospace;
            word-break: break-word;
        }
        .hud-pill-profile {
            background: rgba(255, 87, 34, 0.14);
            border: 1px solid #FF5722;
            color: #FF8A65;
        }
        .hud-pill-sector {
            background: rgba(0, 229, 255, 0.12);
            border: 1px solid #00E5FF;
            color: #00E5FF;
        }
        .hud-pill-prototype {
            background: rgba(255, 23, 68, 0.10);
            border: 1px solid rgba(255, 23, 68, 0.4);
            color: #FF8A80;
        }
        .hud-pill-gauntlet {
            background: rgba(255, 145, 0, 0.15);
            border: 1px solid #FF9100;
            color: #FFB74D;
        }
        
        /* Telemetry Metric Cards */
        .metric-card {
            background: #111622;
            border: 1px solid #1E2738;
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 12px;
            transition: border-color 0.15s ease;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        .metric-card:hover {
            border-color: #2E3E56;
        }
        .metric-title {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #8E9CAE;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 1.55rem;
            font-weight: 700;
            color: #F8FAFC;
            font-family: 'JetBrains Mono', Consolas, monospace;
            letter-spacing: -0.01em;
            word-break: break-word;
        }
        .metric-delta {
            font-size: 0.80rem;
            color: #00E676;
            margin-top: 3px;
            font-weight: 500;
        }
        
        /* Voice / Debrief Cards */
        .debrief-card {
            background: #111622;
            border: 1px solid #1E2738;
            border-left: 3px solid #FF5722;
            border-radius: 6px;
            padding: 14px 16px;
            margin-bottom: 12px;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        .debrief-headline {
            font-size: 0.98rem;
            font-weight: 600;
            color: #FF5722;
            margin-bottom: 6px;
            letter-spacing: 0.02em;
        }
        .debrief-body {
            font-size: 0.88rem;
            color: #CBD5E1;
            line-height: 1.5;
        }
        
        /* Provenance Deck Styling */
        .provenance-deck {
            background: #0E121B;
            border: 1px solid #1E2738;
            border-radius: 6px;
            padding: 14px 18px;
            margin-top: 20px;
            margin-bottom: 10px;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        .provenance-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #1A2232;
        }
        .provenance-title {
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #8E9CAE;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .provenance-badge {
            background: rgba(255, 87, 34, 0.12);
            border: 1px solid rgba(255, 87, 34, 0.4);
            color: #FF8A65;
            font-size: 0.70rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            letter-spacing: 0.04em;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .provenance-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 12px;
        }
        .provenance-item {
            font-size: 0.80rem;
            color: #94A3B8;
            line-height: 1.45;
        }
        .provenance-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            font-weight: 600;
            color: #CBD5E1;
            letter-spacing: 0.04em;
            margin-bottom: 3px;
        }
        .provenance-hazard {
            border-left: 2px solid #FF5722;
            padding-left: 8px;
        }
        .provenance-hazard .provenance-label {
            color: #FF8A65;
        }
        .provenance-footer {
            text-align: center;
            color: #475569;
            font-size: 0.72rem;
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid #141B26;
        }

        /* Persistent Disclaimer Banner (legacy compatibility) */
        .disclaimer-banner {
            background: rgba(255, 23, 68, 0.06);
            border: 1px solid rgba(255, 23, 68, 0.25);
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 0.80rem;
            color: #FF8A80;
            margin-top: 14px;
            line-height: 1.5;
            word-break: break-word;
            overflow-wrap: break-word;
        }

        /* The Gauntlet Alert Banner */
        .gauntlet-banner {
            background: rgba(255, 87, 34, 0.10);
            border: 1px solid #FF5722;
            border-radius: 6px;
            padding: 10px 16px;
            margin-bottom: 14px;
            color: #FFAB91;
            font-size: 0.86rem;
            line-height: 1.45;
            word-break: break-word;
            overflow-wrap: break-word;
        }

        /* Regret Ledger Pills */
        .regret-pill {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.76rem;
            font-weight: 600;
            margin: 2px 4px 2px 0;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .regret-retained {
            background: rgba(0, 230, 118, 0.14);
            border: 1px solid #00E676;
            color: #00E676;
        }
        .regret-dropped {
            background: rgba(255, 179, 0, 0.14);
            border: 1px solid #FFB300;
            color: #FFB300;
        }
        .regret-disabled {
            background: rgba(255, 23, 68, 0.14);
            border: 1px solid #FF1744;
            color: #FF1744;
        }

        /* Mission Commander AI Styling */
        .ai-card {
            background: #111622;
            border: 1px solid #1E2738;
            border-left: 3px solid #7C4DFF;
            border-radius: 6px;
            padding: 14px 16px;
            margin: 10px 0;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        .ai-headline {
            font-size: 0.98rem;
            font-weight: 600;
            color: #B388FF;
            margin-bottom: 6px;
        }
        .ai-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.76rem;
            font-weight: 600;
            margin-right: 6px;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .ai-badge-personalized {
            background: rgba(124, 77, 255, 0.18);
            border: 1px solid #7C4DFF;
            color: #B388FF;
        }
        .ai-badge-learning {
            background: rgba(255, 179, 0, 0.18);
            border: 1px solid #FFB300;
            color: #FFB300;
        }
        .ai-badge-untrained {
            background: rgba(136, 153, 166, 0.18);
            border: 1px solid #8899A6;
            color: #8899A6;
        }

        /* Science Budget Styling */
        .frontier-card {
            background: #111622;
            border: 1px solid #1E2738;
            border-left: 3px solid #00E676;
            border-radius: 6px;
            padding: 14px 16px;
            margin: 10px 0;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        .frontier-badge-optimal {
            background: rgba(0, 230, 118, 0.18);
            border: 1px solid #00E676;
            color: #00E676;
            padding: 2px 8px;
            border-radius: 8px;
            font-size: 0.76rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .frontier-badge-dominated {
            background: rgba(84, 110, 122, 0.2);
            border: 1px solid #546E7A;
            color: #B0BEC5;
            padding: 2px 8px;
            border-radius: 8px;
            font-size: 0.76rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }
        .frontier-badge-infeasible {
            background: rgba(255, 23, 68, 0.18);
            border: 1px solid #FF1744;
            color: #FF5252;
            padding: 2px 8px;
            border-radius: 8px;
            font-size: 0.76rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', Consolas, monospace;
        }

        /* Supporting Tools Tabs Styling */
        div[data-baseweb="tab-list"] {
            flex-wrap: wrap !important;
            gap: 4px !important;
            max-width: 100% !important;
        }
        button[data-baseweb="tab"] {
            background: transparent !important;
            color: #8E9CAE !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
            letter-spacing: 0.04em !important;
            padding: 8px 16px !important;
            border-radius: 4px 4px 0 0 !important;
            white-space: normal !important;
            text-align: center !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #F8FAFC !important;
            border-bottom: 2px solid #FF5722 !important;
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #FF5722 !important;
        }
        div[data-baseweb="tab-border"] {
            background-color: #1E2738 !important;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #0D111A;
            border-right: 1px solid #1A2232;
        }

        /* Streamlit Dataframe table borders */
        [data-testid="stDataFrame"] {
            border: 1px solid #1E2738;
            border-radius: 6px;
            max-width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_regret_ledger_html(ledger: RegretLedger, waypoints: List[ScienceWaypoint]) -> str:
    """Format the Science Regret Ledger into a stylized Obsidian UI breakdown."""
    wp_map = {w.id: w for w in waypoints}

    html = ['<div style="background: #161D2B; border: 1px solid #263345; border-radius: 8px; padding: 12px 16px; margin: 12px 0;">']
    html.append('<div style="font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8899A6; margin-bottom: 8px;"><b>Science Regret Ledger</b></div>')

    # Retained Targets
    html.append('<div style="margin-bottom: 6px;"><span style="font-size: 0.8rem; color: #8899A6;">Preserved Objectives:</span><br>')
    if ledger.retained_target_ids:
        for wid in ledger.retained_target_ids:
            name = wp_map[wid].name if wid in wp_map else wid
            score = wp_map[wid].priority_score if wid in wp_map else 0
            html.append(f'<span class="regret-pill regret-retained">✓ {name} (+{score:.0f} pts)</span>')
    else:
        html.append('<span style="font-size: 0.8rem; color: #8899A6; font-style: italic;">None</span>')
    html.append('</div>')

    # Dropped by Optimizer
    if ledger.dropped_by_optimizer_ids:
        html.append('<div style="margin-bottom: 6px;"><span style="font-size: 0.8rem; color: #8899A6;">Pruned by Optimizer (Budget/Detour):</span><br>')
        for wid in ledger.dropped_by_optimizer_ids:
            name = wp_map[wid].name if wid in wp_map else wid
            score = wp_map[wid].priority_score if wid in wp_map else 0
            html.append(f'<span class="regret-pill regret-dropped">✂ {name} (-{score:.0f} pts)</span>')
        html.append('</div>')

    # Disabled by Disruption
    if ledger.disabled_by_scenario_ids:
        html.append('<div style="margin-bottom: 6px;"><span style="font-size: 0.8rem; color: #8899A6;">Severed by Environmental Hazard:</span><br>')
        for wid in ledger.disabled_by_scenario_ids:
            name = wp_map[wid].name if wid in wp_map else wid
            score = wp_map[wid].priority_score if wid in wp_map else 0
            html.append(f'<span class="regret-pill regret-disabled">✕ {name} (-{score:.0f} pts)</span>')
        html.append('</div>')

    html.append(
        f'<div style="font-size: 0.82rem; color: #CFD8DC; margin-top: 8px; border-top: 1px solid #263345; padding-top: 6px;">'
        f'<b>Net Science Preserved:</b> {ledger.retained_priority:.0f} / {ledger.baseline_priority:.0f} pts '
        f'({ledger.retention_pct:.0f}%)'
        f'</div>'
    )
    html.append('</div>')
    return "".join(html)


# ==============================================================================
# Plotly Map Canvas Construction
# ==============================================================================
def render_tactical_terrain_map(
    terrain: TerrainGrid,
    routes: Dict[str, RouteResult],
    active_profile: str,
    waypoints: List[ScienceWaypoint],
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    show_hazard_overlay: bool = True,
    show_hillshade: bool = True,
    scenario_route: Optional[RouteResult] = None,
    blocked_cells: Optional[List[Tuple[int, int]]] = None,
    scenario_name: Optional[str] = None,
    inspected_candidate_path: Optional[List[Tuple[int, int]]] = None,
    inspected_candidate_label: Optional[str] = None,
) -> go.Figure:
    """Build the high-contrast Plotly 2D tactical map canvas with Gauntlet stress-test overlay support."""
    H, W = terrain.shape
    dx = terrain.dx_ground_m
    dy = terrain.dy_ground_m

    # Compute coordinate extents in meters from top-left (0, 0)
    x_coords = np.arange(W) * dx
    y_coords = np.arange(H) * dy

    fig = go.Figure()

    # 1. Base Layer: Elevation heatmap or Analytical Hillshade
    if show_hillshade:
        # Precompute simple hillshade
        dz_dy, dz_dx = np.gradient(terrain.elevation, dy, dx)
        slope_rad = np.arctan(np.hypot(dz_dx, dz_dy))
        aspect_rad = np.arctan2(-dz_dy, -dz_dx)
        azimuth_rad = np.radians(315.0)
        alt_rad = np.radians(45.0)
        hs = np.clip(
            np.sin(alt_rad) * np.cos(slope_rad)
            + np.cos(alt_rad) * np.sin(slope_rad) * np.cos(azimuth_rad - aspect_rad),
            0.0, 1.0
        )
        fig.add_trace(
            go.Heatmap(
                z=hs,
                x=x_coords,
                y=y_coords,
                colorscale="Gray",
                showscale=False,
                hoverinfo="none",
                name="Hillshade",
            )
        )
    else:
        fig.add_trace(
            go.Heatmap(
                z=terrain.elevation,
                x=x_coords,
                y=y_coords,
                colorscale="Turbo",
                colorbar=dict(title="Elev [m]", len=0.7, x=1.02),
                name="Elevation",
            )
        )

    # 2. Slope Hazard Overlay: semi-transparent layer flagging steep slopes
    if show_hazard_overlay:
        # Create RGB mask: >15° amber, >=25° impassable red
        slope_display = terrain.slope_deg.copy()
        # Custom discrete colored mask for hazards
        amber_mask = (slope_display >= 15.0) & (slope_display < 25.0)
        red_mask = (slope_display >= 25.0)

        hazard_z = np.zeros((H, W), dtype=np.float32)
        hazard_z[amber_mask] = 1.0  # Caution (>15°)
        hazard_z[red_mask] = 2.0    # Impassable Cliff (>=25°)

        # Only draw if hazards exist
        if np.any(hazard_z > 0):
            fig.add_trace(
                go.Heatmap(
                    z=np.where(hazard_z > 0, hazard_z, np.nan),
                    x=x_coords,
                    y=y_coords,
                    colorscale=[
                        [0.0, "rgba(255, 193, 7, 0.45)"],   # Amber
                        [0.5, "rgba(255, 193, 7, 0.45)"],
                        [0.51, "rgba(255, 23, 68, 0.70)"],  # Red
                        [1.0, "rgba(255, 23, 68, 0.70)"],
                    ],
                    showscale=False,
                    hoverinfo="none",
                    name="Slope Hazard (>15°/25°)",
                )
            )

    # 3. Route Polylines
    # Style definitions
    route_styles = {
        "conservative": {"color": "#2196F3", "dash": "dash", "width": 3, "label": "Conservative"},
        "balanced": {"color": "#00E676", "dash": "solid", "width": 4, "label": "Balanced"},
        "science_first": {"color": "#FF5722", "dash": "solid", "width": 3.5, "label": "Science-First"},
    }

    for p_name, r_res in routes.items():
        r_path = getattr(r_res, "path", r_res) if r_res is not None else None
        r_reachable = getattr(r_res, "is_reachable", True)
        if r_path and r_reachable and len(r_path) > 1:
            style = route_styles.get(p_name, {"color": "#FFFFFF", "dash": "solid", "width": 2, "label": p_name})
            is_active = (p_name == active_profile)

            r_rows = [p[0] for p in r_path]
            r_cols = [p[1] for p in r_path]
            r_x = [c * dx for c in r_cols]
            r_y = [r * dy for r in r_rows]

            # In Gauntlet mode, dim other routes and display active route as baseline dashed line
            if scenario_route is not None:
                if is_active:
                    line_color = "#90CAF9"
                    line_dash = "dash"
                    line_width = 3
                    trace_name = f"Baseline {style['label']} (Pre-Disruption)"
                    opacity = 0.65
                else:
                    line_color = style["color"]
                    line_dash = style["dash"]
                    line_width = style["width"]
                    trace_name = style["label"]
                    opacity = 0.25
            else:
                line_color = style["color"]
                line_dash = style["dash"]
                line_width = style["width"] + (2 if is_active else 0)
                trace_name = style["label"] + (" (Active)" if is_active else "")
                opacity = 1.0 if is_active else 0.55

            dist_str = f"{r_res.distance_m:.0f} m" if hasattr(r_res, "distance_m") else ""
            cost_str = f" | Cost: {r_res.cost:.0f}" if hasattr(r_res, "cost") else ""
            hover_line = f"{trace_name}<br>Dist: {dist_str}{cost_str}" if dist_str else trace_name

            fig.add_trace(
                go.Scatter(
                    x=r_x,
                    y=r_y,
                    mode="lines",
                    name=trace_name,
                    line=dict(
                        color=line_color,
                        width=line_width,
                        dash=line_dash,
                    ),
                    opacity=opacity,
                    hoverinfo="text",
                    text=[hover_line] * len(r_x),
                )
            )

    # 3b. Scenario Detour Polyline (if stress test active)
    if scenario_route and scenario_route.is_reachable and len(scenario_route.path) > 1:
        scen_rows = [p[0] for p in scenario_route.path]
        scen_cols = [p[1] for p in scenario_route.path]
        scen_x = [c * dx for c in scen_cols]
        scen_y = [r * dy for r in scen_rows]

        scen_label = f"Stress Detour ({scenario_name})" if scenario_name else "Stress-Test Detour"
        fig.add_trace(
            go.Scatter(
                x=scen_x,
                y=scen_y,
                mode="lines",
                name=scen_label,
                line=dict(
                    color="#FF9100",  # High-visibility neon amber
                    width=5,
                    dash="solid",
                ),
                opacity=1.0,
                hoverinfo="text",
                text=[f"{scen_label}<br>Dist: {scenario_route.distance_m:.0f} m<br>Cost: {scenario_route.cost:.0f}"] * len(scen_x),
            )
        )

    # 3c. Blocked Corridor Cells (if any)
    if blocked_cells:
        b_x = [c * dx for r, c in blocked_cells]
        b_y = [r * dy for r, c in blocked_cells]
        fig.add_trace(
            go.Scatter(
                x=b_x,
                y=b_y,
                mode="markers",
                marker=dict(size=8, color="#FF1744", symbol="x", line=dict(width=1.5, color="#FFFFFF")),
                name="Simulated Obstacle",
                hoverinfo="text",
                text=["Simulated Blocked Zone"] * len(b_x),
            )
        )

    # 3d. Inspected Candidate Polyline (from Science Budget)
    if inspected_candidate_path and len(inspected_candidate_path) > 1:
        ins_rows = [p[0] for p in inspected_candidate_path]
        ins_cols = [p[1] for p in inspected_candidate_path]
        ins_x = [c * dx for c in ins_cols]
        ins_y = [r * dy for r in ins_rows]
        ins_label = inspected_candidate_label or "Inspected Frontier Plan"
        fig.add_trace(
            go.Scatter(
                x=ins_x,
                y=ins_y,
                mode="lines",
                name=ins_label,
                line=dict(
                    color="#00E5FF",  # High-visibility Telemetry Cyan
                    width=4.5,
                    dash="dot",
                ),
                opacity=0.95,
                hoverinfo="text",
                text=[f"<b>{ins_label}</b>"] * len(ins_x),
            )
        )

    # 4. Markers for Waypoints
    wp_x = [w.rc[1] * dx for w in waypoints]
    wp_y = [w.rc[0] * dy for w in waypoints]
    wp_text = [
        f"<b>{w.name}</b><br>Priority: {w.priority_score:.0f} pts<br>{w.geological_context}"
        for w in waypoints
    ]

    fig.add_trace(
        go.Scatter(
            x=wp_x,
            y=wp_y,
            mode="markers+text",
            marker=dict(size=11, color="#00E5FF", symbol="star", line=dict(color="#0B0F19", width=1.5)),
            text=[f" {w.name.split()[0]}" for w in waypoints],
            textposition="top right",
            textfont=dict(color="#00E5FF", size=10),
            hovertext=wp_text,
            hoverinfo="text",
            name="Science Waypoints",
        )
    )

    # 5. Start and Goal Markers
    fig.add_trace(
        go.Scatter(
            x=[start_rc[1] * dx],
            y=[start_rc[0] * dy],
            mode="markers+text",
            marker=dict(size=14, color="#00E676", symbol="circle", line=dict(color="#FFFFFF", width=2)),
            text=[" START"],
            textposition="bottom right",
            textfont=dict(color="#00E676", size=11, family="monospace"),
            name="Landing / Start",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[goal_rc[1] * dx],
            y=[goal_rc[0] * dy],
            mode="markers+text",
            marker=dict(size=14, color="#FF1744", symbol="diamond", line=dict(color="#FFFFFF", width=2)),
            text=[" GOAL"],
            textposition="top left",
            textfont=dict(color="#FF1744", size=11, family="monospace"),
            name="Destination Goal",
        )
    )

    # Layout styling: Maintain true aspect ratio and top-left origin (row 0 at top)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0A0D14",
        plot_bgcolor="#0A0D14",
        autosize=True,
        margin=dict(l=10, r=10, t=32, b=10),
        xaxis=dict(
            title=dict(text="West → East Ground Distance [meters]", font=dict(color="#8E9CAE", size=11)),
            range=[0, W * dx],
            showgrid=False,
            zeroline=False,
            constrain="domain",
            color="#8E9CAE",
        ),
        yaxis=dict(
            title=dict(text="North → South Ground Distance [meters]", font=dict(color="#8E9CAE", size=11)),
            range=[H * dy, 0],  # Inverted so row 0 is at top (North)
            scaleanchor="x",
            scaleratio=1.0,
            constrain="domain",
            showgrid=False,
            zeroline=False,
            color="#8E9CAE",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(17, 22, 34, 0.85)",
            bordercolor="#1E2738",
            borderwidth=1,
            font=dict(size=10, color="#CBD5E1"),
        ),
        height=520,
    )
    return fig


# ==============================================================================
# Elevation & Slope Profile Chart
# ==============================================================================
def render_elevation_slope_profile(route: RouteResult, terrain: TerrainGrid) -> go.Figure:
    """Render synchronized dual-axis Plotly Elevation & Slope profile along active route."""
    if not route or not route.is_reachable or len(route.path) < 2:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B0F19",
            plot_bgcolor="#161D2B",
            height=240,
            annotations=[
                dict(text="No active route path available", showarrow=False, font=dict(size=14, color="#8899A6"))
            ],
        )
        return empty_fig

    dx = terrain.dx_ground_m
    dy = terrain.dy_ground_m

    cum_dist = [0.0]
    elevs = [float(terrain.elevation[route.path[0][0], route.path[0][1]])]
    slopes = [float(terrain.slope_deg[route.path[0][0], route.path[0][1]])]

    total_d = 0.0
    for i in range(len(route.path) - 1):
        u = route.path[i]
        v = route.path[i + 1]
        step_d = calculate_step_distance(u, v, dx, dy)
        total_d += step_d
        cum_dist.append(total_d)
        elevs.append(float(terrain.elevation[v[0], v[1]]))
        slopes.append(float(terrain.slope_deg[v[0], v[1]]))

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Elevation trace (cyan)
    fig.add_trace(
        go.Scatter(
            x=cum_dist,
            y=elevs,
            name="Elevation [m]",
            line=dict(color="#00E5FF", width=2.5),
            mode="lines",
        ),
        secondary_y=False,
    )

    # Slope trace (amber)
    fig.add_trace(
        go.Scatter(
            x=cum_dist,
            y=slopes,
            name="Local Slope [°]",
            line=dict(color="#FFB300", width=1.5, dash="dot"),
            mode="lines",
        ),
        secondary_y=True,
    )

    # 15° slope hazard reference line
    fig.add_hline(
        y=15.0,
        line=dict(color="#FF5722", width=1, dash="dash"),
        secondary_y=True,
        annotation_text="15° Caution Threshold",
        annotation_position="bottom right",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0A0D14",
        plot_bgcolor="#111622",
        margin=dict(l=45, r=45, t=28, b=28),
        height=210,
        legend=dict(
            orientation="h",
            y=1.14,
            x=0.5,
            xanchor="center",
            font=dict(size=10, color="#CBD5E1"),
            bgcolor="rgba(17, 22, 34, 0.75)",
        ),
        xaxis=dict(
            title=dict(text="Traverse Distance [m]", font=dict(color="#8E9CAE", size=10.5)),
            showgrid=True,
            gridcolor="#1E2738",
            color="#8E9CAE",
        ),
    )
    fig.update_yaxes(
        title_text="Elevation [m]",
        title_font=dict(color="#00E5FF", size=10.5),
        showgrid=True,
        gridcolor="#1E2738",
        color="#8E9CAE",
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Slope [deg]",
        title_font=dict(color="#FFB300", size=10.5),
        range=[0, 30],
        showgrid=False,
        color="#8E9CAE",
        secondary_y=True,
    )

    return fig


# ==============================================================================
# Science Budget & Pareto Frontier Interactive Chart
# ==============================================================================
def render_science_budget_chart(
    frontier_result: FrontierResult,
    active_profile: str,
    view_mode: str = "2d",
    scenario_frontier_result: Optional[FrontierResult] = None,
    inspected_candidate_id: Optional[str] = None,
) -> go.Figure:
    """Build the high-contrast Plotly Science Budget & Pareto Frontier chart."""
    fig = go.Figure()

    if view_mode.lower().startswith("3d"):
        # 3D Scatter View: X=Distance, Y=Terrain Cost, Z=Science Points
        dom_cands = frontier_result.dominated_candidates_2d
        if dom_cands:
            fig.add_trace(
                go.Scatter3d(
                    x=[c.distance_m for c in dom_cands],
                    y=[c.cost for c in dom_cands],
                    z=[c.science_score for c in dom_cands],
                    mode="markers",
                    name="Dominated Feasible Plans",
                    marker=dict(size=4, color="#546E7A", opacity=0.6),
                    hoverinfo="text",
                    text=[
                        f"<b>{c.candidate_id}</b><br>Targets: {len(c.visited_waypoint_ids)}<br>"
                        f"Dist: {c.distance_m:.0f} m<br>Cost: {c.cost:.0f}<br>Science: {c.science_score:.0f} pts"
                        for c in dom_cands
                    ],
                )
            )

        pareto_3d = frontier_result.pareto_candidates_3d
        if pareto_3d:
            fig.add_trace(
                go.Scatter3d(
                    x=[c.distance_m for c in pareto_3d],
                    y=[c.cost for c in pareto_3d],
                    z=[c.science_score for c in pareto_3d],
                    mode="markers",
                    name="3D Pareto Frontier",
                    marker=dict(size=7, color="#00E676", symbol="diamond", opacity=0.9),
                    hoverinfo="text",
                    text=[
                        f"<b>[3D Pareto] {c.candidate_id}</b><br>Targets: {len(c.visited_waypoint_ids)}<br>"
                        f"Dist: {c.distance_m:.0f} m<br>Cost: {c.cost:.0f}<br>Science: {c.science_score:.0f} pts"
                        for c in pareto_3d
                    ],
                )
            )

        if inspected_candidate_id:
            ins = next((c for c in frontier_result.candidates if c.candidate_id == inspected_candidate_id), None)
            if ins:
                fig.add_trace(
                    go.Scatter3d(
                        x=[ins.distance_m],
                        y=[ins.cost],
                        z=[ins.science_score],
                        mode="markers",
                        name=f"Inspected: {ins.candidate_id}",
                        marker=dict(size=10, color="#00E5FF", symbol="circle"),
                        hoverinfo="text",
                        text=[f"<b>Inspected Plan: {ins.candidate_id}</b><br>Dist: {ins.distance_m:.0f} m<br>Cost: {ins.cost:.0f}<br>Science: {ins.science_score:.0f} pts"],
                    )
                )

        fig.update_layout(
            title=dict(text="<b>3D Exploration Space: Distance, Cost & Science</b>", font=dict(color="#F8FAFC", size=13)),
            autosize=True,
            scene=dict(
                xaxis=dict(title="Ground Distance [m]", backgroundcolor="#0D111A", gridcolor="#1E2738", color="#8E9CAE"),
                yaxis=dict(title="Modeled Cost", backgroundcolor="#0D111A", gridcolor="#1E2738", color="#8E9CAE"),
                zaxis=dict(title="Science Priority [pts]", backgroundcolor="#0D111A", gridcolor="#1E2738", color="#8E9CAE"),
            ),
            paper_bgcolor="#111622",
            font=dict(color="#CBD5E1", family="sans-serif"),
            margin=dict(l=0, r=0, t=35, b=0),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0.0,
                font=dict(size=10, color="#CBD5E1"),
                bgcolor="rgba(17, 22, 34, 0.85)",
                bordercolor="#1E2738",
                borderwidth=1,
            ),
        )
        return fig

    # 2D Scatter View: X=Distance [m], Y=Science Priority [pts]
    dom_cands = frontier_result.dominated_candidates_2d
    if dom_cands:
        fig.add_trace(
            go.Scatter(
                x=[c.distance_m for c in dom_cands],
                y=[c.science_score for c in dom_cands],
                mode="markers",
                name="Dominated Feasible Plans",
                marker=dict(size=8, color="#546E7A", opacity=0.65),
                hoverinfo="text",
                text=[
                    f"<b>{c.candidate_id}</b><br>Targets: {', '.join(c.visited_waypoint_names) if c.visited_waypoint_names else 'None'}<br>"
                    f"Distance: {c.distance_m:,.0f} m<br>Terrain Cost: {c.cost:,.0f}<br>Science: {c.science_score:.0f} pts<br>Status: Dominated in 2D"
                    for c in dom_cands
                ],
            )
        )

    infeas_cands = frontier_result.infeasible_candidates
    if infeas_cands:
        fig.add_trace(
            go.Scatter(
                x=[c.distance_m for c in infeas_cands],
                y=[c.science_score for c in infeas_cands],
                mode="markers",
                name="Infeasible (Budget Exceeded)",
                marker=dict(size=8, color="#E53935", symbol="x", opacity=0.7),
                hoverinfo="text",
                text=[
                    f"<b>{c.candidate_id} (INFEASIBLE)</b><br>Targets: {len(c.visited_waypoint_ids)}<br>"
                    f"Distance: {c.distance_m:,.0f} m"
                    + (f" (Budget: {frontier_result.max_distance_m:,.0f} m)" if frontier_result.max_distance_m else "")
                    + f"<br>Science: {c.science_score:.0f} pts<br>Reason: {'Budget Exceeded' if not c.is_budget_feasible else 'Unreachable'}"
                    for c in infeas_cands
                ],
            )
        )

    pareto_2d = frontier_result.pareto_candidates_2d
    if pareto_2d:
        p_x = [c.distance_m for c in pareto_2d]
        p_y = [c.science_score for c in pareto_2d]

        fig.add_trace(
            go.Scatter(
                x=p_x,
                y=p_y,
                mode="lines",
                name="2D Pareto Trade-Off Frontier",
                line=dict(color="rgba(0, 230, 118, 0.5)", width=2.5, dash="dash"),
                hoverinfo="none",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=p_x,
                y=p_y,
                mode="markers",
                name="2D Non-Dominated (Pareto Optimal)",
                marker=dict(
                    size=12,
                    color="#00E676",
                    symbol="diamond",
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                hoverinfo="text",
                text=[
                    f"<b>★ Pareto Optimal: {c.candidate_id}</b><br>"
                    f"Targets: {', '.join(c.visited_waypoint_names) if c.visited_waypoint_names else 'Direct Traverse'}<br>"
                    f"Distance: {c.distance_m:,.0f} m<br>Terrain Cost: {c.cost:,.0f}<br>"
                    f"Science: {c.science_score:.0f} pts<br>Marginal Return: Non-Dominated"
                    for c in pareto_2d
                ],
            )
        )

    profile_meta = {
        "conservative": {"name": "Conservative Profile", "color": "#2196F3", "symbol": "square", "size": 13},
        "balanced": {"name": "Balanced Profile", "color": "#00E676", "symbol": "star", "size": 17},
        "science_first": {"name": "Science-First Profile", "color": "#FF5722", "symbol": "triangle-up", "size": 14},
    }

    for p_key, meta in profile_meta.items():
        matched = [c for c in frontier_result.candidates if c.profile_tag and p_key in c.profile_tag.lower()]
        if matched:
            c = matched[0]
            fig.add_trace(
                go.Scatter(
                    x=[c.distance_m],
                    y=[c.science_score],
                    mode="markers",
                    name=meta["name"],
                    marker=dict(
                        size=meta["size"],
                        color=meta["color"],
                        symbol=meta["symbol"],
                        line=dict(color="#FFFFFF", width=1.8),
                    ),
                    hoverinfo="text",
                    text=[
                        f"<b>{meta['name']}</b><br>Targets: {len(c.visited_waypoint_ids)}<br>"
                        f"Distance: {c.distance_m:,.0f} m<br>Terrain Cost: {c.cost:,.0f}<br>"
                        f"Science: {c.science_score:.0f} pts<br>Pareto Optimal: {'Yes' if c.is_pareto_2d else 'Dominated'}"
                    ],
                )
            )

    if scenario_frontier_result and scenario_frontier_result.pareto_candidates_2d:
        scen_p2d = scenario_frontier_result.pareto_candidates_2d
        fig.add_trace(
            go.Scatter(
                x=[c.distance_m for c in scen_p2d],
                y=[c.science_score for c in scen_p2d],
                mode="lines+markers",
                name="Gauntlet Stress-Tested Frontier",
                line=dict(color="#FF9100", width=2.5, dash="dot"),
                marker=dict(size=10, color="#FF9100", symbol="diamond-open", line=dict(width=2)),
                hoverinfo="text",
                text=[
                    f"<b>[Gauntlet Frontier] {c.candidate_id}</b><br>"
                    f"Distance: {c.distance_m:,.0f} m<br>Science: {c.science_score:.0f} pts"
                    for c in scen_p2d
                ],
            )
        )

    if inspected_candidate_id:
        ins = next((c for c in frontier_result.candidates if c.candidate_id == inspected_candidate_id), None)
        if ins:
            fig.add_trace(
                go.Scatter(
                    x=[ins.distance_m],
                    y=[ins.science_score],
                    mode="markers",
                    name=f"Inspected: {ins.candidate_id}",
                    marker=dict(
                        size=18,
                        color="#00E5FF",
                        symbol="circle",
                        line=dict(color="#FFFFFF", width=2.5),
                    ),
                    hoverinfo="text",
                    text=[
                        f"<b>Inspected Candidate: {ins.candidate_id}</b><br>"
                        f"Distance: {ins.distance_m:,.0f} m<br>Science: {ins.science_score:.0f} pts<br>"
                        f"Pareto 2D: {'Optimal' if ins.is_pareto_2d else 'Dominated'}"
                    ],
                )
            )

    fig.update_layout(
        title=dict(
            text="<b>Exploration Trade-Offs: Physical Ground Distance vs. Science Priority Budget</b>",
            font=dict(color="#F8FAFC", size=13),
        ),
        autosize=True,
        xaxis=dict(
            title=dict(text="Physical Ground Distance [m]", font=dict(color="#8E9CAE", size=11)),
            gridcolor="#1E2738",
            zerolinecolor="#263345",
            color="#8E9CAE",
            tickformat=",.0f",
        ),
        yaxis=dict(
            title=dict(text="Scientific Priority Points [pts]", font=dict(color="#8E9CAE", size=11)),
            gridcolor="#1E2738",
            zerolinecolor="#263345",
            color="#8E9CAE",
        ),
        plot_bgcolor="#0A0D14",
        paper_bgcolor="#111622",
        font=dict(color="#CBD5E1", family="sans-serif"),
        height=440,
        margin=dict(l=45, r=20, t=44, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            font=dict(size=10, color="#CBD5E1"),
            bgcolor="rgba(17, 22, 34, 0.85)",
            bordercolor="#1E2738",
            borderwidth=1,
        ),
    )
    return fig


# ==============================================================================
# Main Streamlit Dashboard Application
# ==============================================================================
def main():
    st.set_page_config(
        page_title="MarsWalk — Mission Rehearsal",
        page_icon="🔴",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()

    if "inspected_cand_id" not in st.session_state:
        st.session_state["inspected_cand_id"] = None
    if "show_inspected_on_map" not in st.session_state:
        st.session_state["show_inspected_on_map"] = False

    # --------------------------------------------------------------------------
    # Data Ingestion & Ground Calibration
    # --------------------------------------------------------------------------
    if not os.path.exists(PROCESSED_TIFF) or not os.path.exists(WAYPOINTS_JSON):
        st.error(
            "Processed dataset or waypoint metadata missing. "
            "Please ensure data/processed/jezero_ready_20m.tif exists."
        )
        st.stop()

    raw_wp_data = load_raw_waypoints(WAYPOINTS_JSON)

    # --------------------------------------------------------------------------
    # LEFT MISSION CONTROL PANEL (Sidebar)
    # --------------------------------------------------------------------------
    with st.sidebar:
        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <h2 style="color: #FF5722; margin: 0; font-size: 1.45rem;">MARSWALK</h2>
                <div style="font-size: 0.78rem; color: #8899A6; text-transform: uppercase; letter-spacing: 0.08em;">
                    Mission Rehearsal Station • 2026
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 1. Mission Traversal Endpoints")
        # Build waypoint selector map
        wp_name_map = {f"{w['name']} ({w['id']})": w for w in raw_wp_data}
        wp_names = list(wp_name_map.keys())

        # Presets: Default start = Octavia Butler Landing (index 0); Goal = Delta Rim (index 4)
        start_idx = 0
        goal_idx = 4 if len(wp_names) > 4 else min(1, len(wp_names) - 1)

        sel_start_name = st.selectbox("EVA Start Location", wp_names, index=start_idx)
        sel_goal_name = st.selectbox("EVA Destination Goal", wp_names, index=goal_idx)

        # 2. Scientific Targets Selection
        st.markdown("### 2. Science Target Selection")
        # Other waypoints eligible as stops
        eligible_wp_names = [name for name in wp_names if name not in (sel_start_name, sel_goal_name)]
        selected_candidate_names = st.multiselect(
            "Active Science Targets",
            eligible_wp_names,
            default=eligible_wp_names[:3],
            help="Select up to 6 candidate geological outcrops for traverse optimization."
        )

        # 3. Traversal Profile & Appetite
        st.markdown("### 3. Route Optimization Profile")
        profile = st.radio(
            "Primary Profile",
            ["Balanced", "Conservative", "Science-First"],
            index=0,
            horizontal=True,
        ).lower().replace("-", "_")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            science_appetite = st.slider(
                "Science Appetite (γ)",
                min_value=0.2,
                max_value=3.0,
                value=1.0,
                step=0.1,
                help="Higher γ penalizes terrain detour costs more aggressively in Balanced mode."
            )
        with col_g2:
            max_dist_budget = st.number_input(
                "Max Budget [m]",
                min_value=500,
                max_value=12000,
                value=7000,
                step=250,
                help="Maximum allowable EVA walking distance."
            )

        # 4. Physical Terrain Cost Weights (Expandable)
        with st.expander("Physics Model & Slope Weights", expanded=False):
            alpha_s = st.slider("Slope Penalty (αs)", 0.0, 5.0, 2.0, 0.2)
            alpha_r = st.slider("Roughness Weight (αr)", 0.0, 3.0, 1.0, 0.2)
            alpha_up = st.slider("Uphill Grade (α_up)", 0.0, 4.0, 1.5, 0.2)

        # 5. Mission Control Voice Toggle
        st.markdown("### 4. Co-Pilot Persona")
        voice_mode = st.radio(
            "Mission Control Voice",
            ["Professional", "Dry Humour"],
            index=0,
            horizontal=True,
            help="Dry Humour mode enables space-themed witty commentary without compromising scientific precision."
        ).lower().replace(" ", "_")

        show_hazards = st.checkbox("Show Slope Hazards (>15°/25°)", value=True)
        show_hillshade = st.checkbox("Show Topographic Hillshade", value=True)

        # 6. The Gauntlet (EVA Stress-Testing)
        st.markdown("### 5. The Gauntlet (Stress-Testing)")
        gauntlet_active = st.toggle(
            "Activate The Gauntlet",
            value=False,
            help="Inject hypothetical mission disruptions (corridor closures, life-support drops, target hazards) and compute the Science Regret Ledger."
        )

        gauntlet_mode = None
        scenario_def: Optional[ScenarioDefinition] = None

        if gauntlet_active:
            gauntlet_mode = st.radio(
                "Disruption Type",
                ["Corridor Closure", "Reduced Budget", "Target Unavailable", "Route Toughness Suite"],
                index=0,
            )

            if gauntlet_mode == "Corridor Closure":
                closure_choice = st.selectbox(
                    "Obstacle Preset",
                    [
                        "Hawksbill Gap Scarp Rockfall",
                        "Crater Floor Dune Migration",
                        "Custom Sector Blockage",
                    ],
                )
                if closure_choice == "Hawksbill Gap Scarp Rockfall":
                    blocked_cells = [(r, c) for r in range(134, 139) for c in range(89, 94)]
                    scenario_def = ScenarioDefinition(
                        id="scen_hawksbill_rockfall",
                        name="Hawksbill Gap Scarp Rockfall",
                        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
                        description="Simulated localized regolith collapse in Hawksbill Gap, blocking primary delta ascent channel.",
                        blocked_cells=blocked_cells,
                    )
                elif closure_choice == "Crater Floor Dune Migration":
                    blocked_cells = [(r, c) for r in range(112, 118) for c in range(135, 141)]
                    scenario_def = ScenarioDefinition(
                        id="scen_delta_channel_block",
                        name="Crater Floor Dune Migration",
                        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
                        description="Active aeolian megaripple migration creates untraversable sand sink on crater floor.",
                        blocked_cells=blocked_cells,
                    )
                else:
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        r_min = st.number_input("Row Min", 0, 249, 130)
                        r_max = st.number_input("Row Max", 0, 249, 135)
                    with c_col2:
                        c_min = st.number_input("Col Min", 0, 249, 90)
                        c_max = st.number_input("Col Max", 0, 249, 95)
                    custom_cells = [
                        (r, c)
                        for r in range(min(r_min, r_max), max(r_min, r_max) + 1)
                        for c in range(min(c_min, c_max), max(c_min, c_max) + 1)
                    ]
                    scenario_def = ScenarioDefinition(
                        id="scen_custom_closure",
                        name="Custom Sector Blockage",
                        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
                        description=f"Simulated impassable corridor between R:[{r_min},{r_max}] C:[{c_min},{c_max}].",
                        blocked_cells=custom_cells,
                    )

            elif gauntlet_mode == "Reduced Budget":
                budget_cut_pct = st.slider(
                    "Budget Curtailment (%)",
                    min_value=10,
                    max_value=60,
                    value=25,
                    step=5,
                    help="Simulate life-support endurance drops or consumable reserve margins.",
                )
                scenario_def = ScenarioDefinition(
                    id="scen_reduced_budget",
                    name=f"Consumable Reserve Alert (-{budget_cut_pct}% Budget)",
                    disruption_type=DisruptionType.REDUCED_BUDGET,
                    description=f"Suit life-support consumable margin requires reducing walking ceiling by {budget_cut_pct}%.",
                    budget_reduction_pct=float(budget_cut_pct),
                )

            elif gauntlet_mode == "Target Unavailable":
                if selected_candidate_names:
                    target_chosen = st.selectbox("Inaccessible Outcrop", selected_candidate_names)
                    matching_raw = wp_name_map[target_chosen]
                    scenario_def = ScenarioDefinition(
                        id=f"scen_target_{matching_raw['id']}",
                        name=f"Environmental Hazard at {matching_raw['name']}",
                        disruption_type=DisruptionType.TARGET_UNAVAILABLE,
                        description=f"Surface telemetry flags severe slope instability surrounding outcrop '{matching_raw['name']}'.",
                        unavailable_target_id=matching_raw["id"],
                    )
                else:
                    st.info("No active science targets selected to disable.")

            elif gauntlet_mode == "Route Toughness Suite":
                st.info("Stress-tests the baseline traverse across 5 curated disruptions across Jezero Western Delta.")

            if st.button("Reset / Clear Gauntlet", use_container_width=True):
                st.rerun()

        # 6. Mission Commander AI (Preference Learning)
        st.markdown("### 6. Mission Commander AI")
        enable_commander_ai = st.toggle(
            "Enable Mission Commander AI",
            value=False,
            help="Personalize route recommendations by learning your exploration priorities from explicit choices.",
        )

        pref_model = load_preference_model(PREFERENCES_FILE)

        if enable_commander_ai:
            ai_state = pref_model.get_state()
            if ai_state == LearningState.PERSONALIZED:
                badge_html = f'<span class="ai-badge ai-badge-personalized">🟢 PERSONALIZED ({len(pref_model.observations)} choices)</span>'
            elif ai_state == LearningState.COLLECTING_INITIAL:
                badge_html = f'<span class="ai-badge ai-badge-learning">🟡 CALIBRATING ({len(pref_model.observations)}/{MIN_FEEDBACK_THRESHOLD} choices)</span>'
            elif ai_state == LearningState.RESET:
                badge_html = '<span class="ai-badge ai-badge-untrained">⚪ RESET (0 choices)</span>'
            else:
                badge_html = '<span class="ai-badge ai-badge-untrained">⚪ UNTRAINED (0 choices)</span>'

            st.markdown(f"<div style='margin-bottom: 8px;'>Status: {badge_html}</div>", unsafe_allow_html=True)

            with st.expander("Preference History & Controls", expanded=False):
                st.caption("Review locally stored choices or clear learning history.")
                if pref_model.observations:
                    st.write(f"Total choices recorded: **{len(pref_model.observations)}**")
                    choice_summary = [
                        {
                            "Time": obs.timestamp[11:19] if len(obs.timestamp) > 19 else obs.timestamp,
                            "Selected": obs.selected_profile.upper(),
                            "Dist [m]": f"{obs.selected_features.distance_m:.0f}",
                            "Science [pts]": f"{obs.selected_features.science_score:.0f}",
                        }
                        for obs in pref_model.observations[-5:]
                    ]
                    st.dataframe(choice_summary, use_container_width=True, hide_index=True)

                    # Export button
                    json_str = json.dumps(pref_model.to_dict(), indent=2)
                    st.download_button(
                        label="Export Preference JSON",
                        data=json_str,
                        file_name="commander_preferences.json",
                        mime="application/json",
                        use_container_width=True,
                    )

                if st.button("Reset Commander Profile", use_container_width=True):
                    pref_model.reset()
                    save_preference_model(pref_model, PREFERENCES_FILE)
                    st.rerun()

        if st.button("Restore Default Settings", use_container_width=True):
            st.rerun()

    # --------------------------------------------------------------------------
    # Load Real Terrain & Coordinates
    # --------------------------------------------------------------------------
    terrain = get_cached_terrain(PROCESSED_TIFF, alpha_s=alpha_s, alpha_r=alpha_r, alpha_up=alpha_up)

    # Derive grid coordinates for Start and Goal
    raw_start = wp_name_map[sel_start_name]
    raw_goal = wp_name_map[sel_goal_name]

    _, start_r, start_c = query_elevation_at_lonlat(PROCESSED_TIFF, raw_start["lon_deg"], raw_start["lat_deg"])
    _, goal_r, goal_c = query_elevation_at_lonlat(PROCESSED_TIFF, raw_goal["lon_deg"], raw_goal["lat_deg"])
    start_rc = (start_r, start_c)
    goal_rc = (goal_r, goal_c)

    # Convert candidate science waypoints
    active_waypoints: List[ScienceWaypoint] = []
    for name in selected_candidate_names:
        w_raw = wp_name_map[name]
        _, r, c = query_elevation_at_lonlat(PROCESSED_TIFF, w_raw["lon_deg"], w_raw["lat_deg"])
        active_waypoints.append(
            ScienceWaypoint(
                id=w_raw["id"],
                name=w_raw["name"],
                rc=(r, c),
                priority_score=float(w_raw["priority_score"]),
                geological_context=w_raw.get("geological_context", ""),
                crism_signature=w_raw.get("crism_signature", ""),
                pds_citation=w_raw.get("pds_citation", ""),
            )
        )

    # --------------------------------------------------------------------------
    # Solve Routes (Conservative, Balanced, Science-First)
    # --------------------------------------------------------------------------
    # Precompute pairwise cache between start, goal, and active waypoints
    nodes_for_cache = [start_rc] + [w.rc for w in active_waypoints] + [goal_rc]
    unique_nodes = list(dict.fromkeys(nodes_for_cache))
    leg_cache = compute_pairwise_leg_cache(unique_nodes, terrain)

    p_cfg_cons = PlannerConfig(profile="conservative", max_distance_m=float(max_dist_budget))
    p_cfg_bal = PlannerConfig(profile="balanced", science_appetite_gamma=science_appetite, max_distance_m=float(max_dist_budget))
    p_cfg_sci = PlannerConfig(profile="science_first", max_distance_m=float(max_dist_budget))

    res_cons = plan_route(start_rc, goal_rc, terrain, active_waypoints, p_cfg_cons, leg_cache=leg_cache)
    res_bal = plan_route(start_rc, goal_rc, terrain, active_waypoints, p_cfg_bal, leg_cache=leg_cache)
    res_sci = plan_route(start_rc, goal_rc, terrain, active_waypoints, p_cfg_sci, leg_cache=leg_cache)

    all_routes = {
        "conservative": res_cons,
        "balanced": res_bal,
        "science_first": res_sci,
    }
    primary_route = all_routes[profile]

    active_p_cfg = {
        "conservative": p_cfg_cons,
        "balanced": p_cfg_bal,
        "science_first": p_cfg_sci,
    }[profile]

    # Stress-Test Execution (The Gauntlet)
    scenario_comp: Optional[ScenarioComparison] = None
    toughness_report: Optional[ToughnessReport] = None
    scenario_routes: Dict[str, RouteResult] = {}

    if gauntlet_active:
        if gauntlet_mode == "Route Toughness Suite":
            toughness_report = evaluate_route_toughness(
                baseline_route=primary_route,
                start_rc=start_rc,
                goal_rc=goal_rc,
                waypoints=active_waypoints,
                terrain=terrain,
                planner_config=active_p_cfg,
            )
        elif scenario_def is not None:
            scen_comp_cons = run_scenario(
                baseline_route=res_cons,
                scenario=scenario_def,
                start_rc=start_rc,
                goal_rc=goal_rc,
                waypoints=active_waypoints,
                terrain=terrain,
                planner_config=p_cfg_cons,
                voice_mode=voice_mode,
            )
            scen_comp_bal = run_scenario(
                baseline_route=res_bal,
                scenario=scenario_def,
                start_rc=start_rc,
                goal_rc=goal_rc,
                waypoints=active_waypoints,
                terrain=terrain,
                planner_config=p_cfg_bal,
                voice_mode=voice_mode,
            )
            scen_comp_sci = run_scenario(
                baseline_route=res_sci,
                scenario=scenario_def,
                start_rc=start_rc,
                goal_rc=goal_rc,
                waypoints=active_waypoints,
                terrain=terrain,
                planner_config=p_cfg_sci,
                voice_mode=voice_mode,
            )
            all_scenario_comps = {
                "conservative": scen_comp_cons,
                "balanced": scen_comp_bal,
                "science_first": scen_comp_sci,
            }
            scenario_comp = all_scenario_comps[profile]
            scenario_routes = {
                "conservative": scen_comp_cons.scenario_route,
                "balanced": scen_comp_bal.scenario_route,
                "science_first": scen_comp_sci.scenario_route,
            }

    # Evaluate candidate alternatives for Mission Commander AI
    eval_candidates = scenario_routes if (gauntlet_active and scenario_def is not None) else all_routes
    ranked_routes: List[RankedRoute] = []
    if enable_commander_ai:
        ranked_routes = pref_model.rank_routes(eval_candidates, terrain=terrain)

    # --------------------------------------------------------------------------
    # Science Budget & Pareto Frontier Evaluation
    # --------------------------------------------------------------------------
    active_profile_tags = {
        "conservative": res_cons.visited_waypoint_ids,
        "balanced": res_bal.visited_waypoint_ids,
        "science_first": res_sci.visited_waypoint_ids,
    }

    frontier_res = analyze_science_budget(
        start_rc=start_rc,
        goal_rc=goal_rc,
        terrain=terrain,
        waypoints=active_waypoints,
        planner_config=active_p_cfg,
        leg_cache=leg_cache,
        active_profile_tags=active_profile_tags,
    )

    # Score candidates under learned commander preferences if active
    if enable_commander_ai:
        for c in frontier_res.candidates:
            if c.is_feasible and len(c.path) > 1:
                dummy_r = RouteResult(
                    profile=c.candidate_id,
                    start_rc=start_rc,
                    goal_rc=goal_rc,
                    path=c.path,
                    distance_m=c.distance_m,
                    cost=c.cost,
                    science_score=c.science_score,
                    visited_waypoint_ids=c.visited_waypoint_ids,
                    num_cells=len(c.path),
                    num_steps=max(0, len(c.path) - 1),
                    is_reachable=c.is_reachable,
                    is_budget_feasible=c.is_budget_feasible,
                    max_distance_m=frontier_res.max_distance_m,
                    status_message="",
                )
                feats = extract_route_features(dummy_r, terrain)
                c.utility_score = pref_model.predict_utility(feats)

    # Gauntlet scenario frontier comparison (if stress-test active)
    scen_frontier_res: Optional[FrontierResult] = None
    frontier_comp: Optional[Dict[str, Any]] = None
    if gauntlet_active and scenario_def is not None:
        scen_blocked_mask = None
        if scenario_def.disruption_type == DisruptionType.CORRIDOR_CLOSURE and scenario_def.blocked_cells:
            scen_blocked_mask = np.zeros(terrain.shape, dtype=bool)
            for r, c in scenario_def.blocked_cells:
                if 0 <= r < terrain.height and 0 <= c < terrain.width:
                    scen_blocked_mask[r, c] = True

        scen_wps = list(active_waypoints)
        if scenario_def.disruption_type == DisruptionType.TARGET_UNAVAILABLE and scenario_def.unavailable_target_id:
            scen_wps = [w for w in scen_wps if w.id != scenario_def.unavailable_target_id]

        scen_budget = active_p_cfg.max_distance_m
        if scenario_def.disruption_type == DisruptionType.REDUCED_BUDGET:
            if scenario_def.reduced_max_distance_m is not None:
                scen_budget = float(scenario_def.reduced_max_distance_m)
            elif scenario_def.budget_reduction_pct is not None:
                base_ceiling = active_p_cfg.max_distance_m if active_p_cfg.max_distance_m is not None else primary_route.distance_m
                scen_budget = max(100.0, base_ceiling * (1.0 - float(scenario_def.budget_reduction_pct) / 100.0))

        scen_planner_cfg = PlannerConfig(
            profile=profile,
            science_appetite_gamma=science_appetite,
            max_distance_m=scen_budget,
        )

        scen_frontier_res = analyze_science_budget(
            start_rc=start_rc,
            goal_rc=goal_rc,
            terrain=terrain,
            waypoints=scen_wps,
            planner_config=scen_planner_cfg,
            blocked_mask=scen_blocked_mask,
        )
        frontier_comp = compare_frontiers(frontier_res, scen_frontier_res)

    # Resolve inspected candidate path for map overlay
    inspected_cand_path = None
    inspected_cand_label = None
    if st.session_state.get("show_inspected_on_map") and st.session_state.get("inspected_cand_id"):
        match_c = next((c for c in frontier_res.candidates if c.candidate_id == st.session_state["inspected_cand_id"]), None)
        if match_c and match_c.is_reachable and len(match_c.path) > 1:
            inspected_cand_path = match_c.path
            inspected_cand_label = f"Inspected: {match_c.candidate_id} ({match_c.distance_m:.0f} m, {match_c.science_score:.0f} pts)"

    # --------------------------------------------------------------------------
    # MISSION CONTROL HUD BAR (Compact Workstation Header)
    # --------------------------------------------------------------------------
    st.markdown(
        f"""
        <div class="hud-bar">
            <div class="hud-title-group">
                <div class="hud-title">
                    <span class="hud-brand-tag">MARSWALK</span> // MISSION REHEARSAL STATION
                </div>
                <div class="hud-subtitle">
                    OPERATING AREA: JEZERO CRATER • WESTERN DELTA FRONT (18.44°N, 77.45°E)
                </div>
            </div>
            <div class="hud-pills">
                <span class="hud-pill hud-pill-sector">USGS CTX 20 M/PX</span>
                <span class="hud-pill hud-pill-profile">PROFILE: {profile.upper()}</span>
                {f'<span class="hud-pill hud-pill-gauntlet">⚠️ GAUNTLET ACTIVE: {scenario_def.name.upper() if scenario_def else "TOUGHNESS BENCHMARK"}</span>' if gauntlet_active else ''}
                <span class="hud-pill hud-pill-prototype">SIMULATION PROTOTYPE • NOT FLIGHT CERTIFIED</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # MISSION TELEMETRY KPI ROW (Separate physical, modeled, and science quantities)
    # --------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    if toughness_report:
        with k1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Feasible Traverses</div>
                    <div class="metric-value">{toughness_report.feasible_count} / {toughness_report.total_scenarios_tested}</div>
                    <div class="metric-delta">{toughness_report.feasible_count / toughness_report.total_scenarios_tested * 100:.0f}% completion rate</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Budget Compliant</div>
                    <div class="metric-value">{toughness_report.budget_met_count} / {toughness_report.total_scenarios_tested}</div>
                    <div class="metric-delta">under physical distance limits</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Max Detour Required</div>
                    <div class="metric-value">+{toughness_report.max_distance_increase_m:.0f} m</div>
                    <div class="metric-delta">across tested disruptions</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Mean Science Preserved</div>
                    <div class="metric-value">{toughness_report.avg_retention_pct:.1f}%</div>
                    <div class="metric-delta">min retention {toughness_report.min_retention_pct:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif scenario_comp:
        scen_r = scenario_comp.scenario_route
        with k1:
            if scen_r.is_reachable:
                val_str = f"{scenario_comp.scenario_distance_m:,.0f} m"
                delta_str = f"{scenario_comp.delta_distance_m:+.0f} m ({scenario_comp.pct_distance_change:+.1f}%)"
            else:
                val_str = "SEVERED"
                delta_str = "No traversable path"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Stress-Tested Distance</div>
                    <div class="metric-value">{val_str}</div>
                    <div class="metric-delta">{delta_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k2:
            if scen_r.is_reachable:
                val_str = f"{scenario_comp.scenario_cost:,.0f}"
                delta_str = f"{scenario_comp.delta_cost:+.0f} ({scenario_comp.pct_cost_change:+.1f}%)"
            else:
                val_str = "∞"
                delta_str = "Infinite terrain cost"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Stress-Tested Effort</div>
                    <div class="metric-value">{val_str}</div>
                    <div class="metric-delta">{delta_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k3:
            leg = scenario_comp.regret_ledger
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Science Preserved</div>
                    <div class="metric-value">{leg.retention_pct:.0f}%</div>
                    <div class="metric-delta">{leg.retained_priority:.0f} / {leg.baseline_priority:.0f} pts retained</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k4:
            if not scen_r.is_reachable:
                b_status = "INFEASIBLE"
                b_color = "#FF1744"
                b_sub = "Corridor completely severed"
            elif not scenario_comp.is_scenario_budget_feasible:
                b_status = "EXCEEDED"
                b_color = "#FF1744"
                b_sub = f"Exceeds {scenario_comp.effective_budget_m:.0f} m ceiling"
            else:
                b_status = "CLEARED"
                b_color = "#00E676"
                margin = (scenario_comp.effective_budget_m or 0.0) - scenario_comp.scenario_distance_m
                b_sub = f"{margin:.0f} m reserve margin remaining"

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Disruption Viability</div>
                    <div class="metric-value" style="color: {b_color};">{b_status}</div>
                    <div class="metric-delta">{b_sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        # Standard baseline KPI cards
        with k1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Physical Ground Distance</div>
                    <div class="metric-value">{primary_route.distance_m:,.0f} m</div>
                    <div class="metric-delta">+{primary_route.distance_m - res_cons.distance_m:,.0f} m over direct path</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Modeled Terrain Effort</div>
                    <div class="metric-value">{primary_route.cost:,.0f}</div>
                    <div class="metric-delta">+{primary_route.cost - res_cons.cost:,.0f} equivalent flat meters</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k3:
            pct_sci = (primary_route.science_score / sum(w.priority_score for w in active_waypoints) * 100.0) if active_waypoints else 100.0
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Science Priority Harvested</div>
                    <div class="metric-value">{primary_route.science_score:.0f} pts</div>
                    <div class="metric-delta">{len(primary_route.visited_waypoint_ids)}/{len(active_waypoints)} targets ({pct_sci:.0f}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with k4:
            budget_str = "CLEARED" if primary_route.is_budget_feasible else "EXCEEDED"
            budget_color = "#00E676" if primary_route.is_budget_feasible else "#FF1744"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Distance Budget Status</div>
                    <div class="metric-value" style="color: {budget_color};">{budget_str}</div>
                    <div class="metric-delta">{max_dist_budget - primary_route.distance_m:,.0f} m reserve margin</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------------------------
    # PRIMARY PLANNING WORKSPACE (Tactical Surface Map & Integrated Elevation Deck)
    # --------------------------------------------------------------------------
    col_map, col_debrief = st.columns([1.65, 1.0])

    with col_map:
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 700; font-size: 1.02rem; color: #F8FAFC;">🗺️ Tactical Surface Map (USGS MRO CTX 20 m/px)</span>
                <span style="font-size: 0.76rem; color: #8E9CAE; font-family: monospace;">DATUM: MOLA DELTAGEOID</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        map_fig = render_tactical_terrain_map(
            terrain=terrain,
            routes=all_routes,
            active_profile=profile,
            waypoints=active_waypoints,
            start_rc=start_rc,
            goal_rc=goal_rc,
            show_hazard_overlay=show_hazards,
            show_hillshade=show_hillshade,
            scenario_route=scenario_comp.scenario_route if scenario_comp else None,
            blocked_cells=scenario_def.blocked_cells if (scenario_comp and scenario_def) else None,
            scenario_name=scenario_def.name if (scenario_comp and scenario_def) else None,
            inspected_candidate_path=inspected_cand_path,
            inspected_candidate_label=inspected_cand_label,
        )
        st.plotly_chart(map_fig, use_container_width=True, config={"displayModeBar": False})

        # Elevation & Slope Profile directly beneath the map
        if scenario_comp and scenario_comp.scenario_route.is_reachable:
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0 4px 0;">
                    <span style="font-weight: 700; font-size: 0.95rem; color: #F8FAFC;">📈 Elevation & Slope Profile — Stress Detour ({scenario_def.name})</span>
                    <span style="font-size: 0.74rem; color: #8E9CAE; font-family: monospace;">ELEVATION [CYAN] • SLOPE [AMBER]</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            profile_fig = render_elevation_slope_profile(scenario_comp.scenario_route, terrain)
        else:
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0 4px 0;">
                    <span style="font-weight: 700; font-size: 0.95rem; color: #F8FAFC;">📈 Elevation & Slope Profile — Active Traverse ({profile.replace('_', ' ').title()})</span>
                    <span style="font-size: 0.74rem; color: #8E9CAE; font-family: monospace;">ELEVATION [CYAN] • SLOPE [AMBER] • 15° THRESHOLD</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            profile_fig = render_elevation_slope_profile(primary_route, terrain)
        st.plotly_chart(profile_fig, use_container_width=True, config={"displayModeBar": False})

    with col_debrief:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 1.02rem; color: #F8FAFC; margin-bottom: 6px;">
                📋 Mission Debrief & Trade-Off Telemetry
            </div>
            """,
            unsafe_allow_html=True,
        )

        if toughness_report:
            st.markdown(
                f"""
                <div class="debrief-card">
                    <div class="debrief-headline">Route Resilience Verdict</div>
                    <div class="debrief-body">{toughness_report.summary_narrative}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("##### Route Toughness Disruption Matrix")
            t_data = {
                "Disruption": [r.scenario.name for r in toughness_report.results],
                "Type": [r.scenario.disruption_type.value.replace("_", " ").title() for r in toughness_report.results],
                "Feasible": ["✓ Yes" if r.is_reachable else "✕ Severed" for r in toughness_report.results],
                "Budget": ["✓ Cleared" if r.is_budget_feasible else "✕ Exceeded" for r in toughness_report.results],
                "Detour (+m)": [f"+{r.delta_distance_m:.0f} m" if (r.is_reachable and not math.isnan(r.delta_distance_m)) else "N/A" for r in toughness_report.results],
                "Science Retained": [f"{r.retention_pct:.0f}%" for r in toughness_report.results],
            }
            st.dataframe(t_data, use_container_width=True, hide_index=True)

        elif scenario_comp and scenario_def:
            # Narrative Explainer for Scenario
            st.markdown(
                f"""
                <div class="debrief-card">
                    <div class="debrief-headline">{scenario_comp.headline}</div>
                    <div class="debrief-body">{scenario_comp.detail}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Science Regret Ledger
            st.markdown(format_regret_ledger_html(scenario_comp.regret_ledger, active_waypoints), unsafe_allow_html=True)

            # Comparative Matrix: Baseline vs Stress-Tested Scenario
            st.markdown("##### Baseline vs Stress-Tested Plan")
            scen_r = scenario_comp.scenario_route
            comp_data = {
                "Plan": ["Baseline Plan", f"Gauntlet ({scenario_def.name})"],
                "Distance": [
                    f"{primary_route.distance_m:,.0f} m",
                    f"{scen_r.distance_m:,.0f} m" if scen_r.is_reachable else "Severed",
                ],
                "Cost": [
                    f"{primary_route.cost:,.0f}",
                    f"{scen_r.cost:,.0f}" if scen_r.is_reachable else "∞",
                ],
                "Science": [
                    f"{primary_route.science_score:.0f} pts",
                    f"{scen_r.science_score:.0f} pts" if scen_r.is_reachable else "0 pts",
                ],
                "Targets": [
                    f"{len(primary_route.visited_waypoint_ids)}",
                    f"{len(scen_r.visited_waypoint_ids)}" if scen_r.is_reachable else "0",
                ],
                "Budget Status": [
                    "Cleared" if primary_route.is_budget_feasible else "Exceeded",
                    ("Cleared" if scen_r.is_budget_feasible else "Exceeded") if scen_r.is_reachable else "Infeasible",
                ],
            }
            st.dataframe(comp_data, use_container_width=True, hide_index=True)

        else:
            # Narrative Explainer Card for baseline
            debrief = generate_route_tradeoff_summary(
                primary_route=primary_route,
                conservative_route=res_cons,
                science_first_route=res_sci,
                waypoints=active_waypoints,
                voice_mode=voice_mode,
            )
            st.markdown(
                f"""
                <div class="debrief-card">
                    <div class="debrief-headline">{debrief['headline']}</div>
                    <div class="debrief-body">{debrief['detail']}</div>
                    <div style="font-size: 0.80rem; color: #8E9CAE; margin-top: 8px;">
                        {debrief['budget_note']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Comparative Table
            st.markdown("##### Profile Trade-Off Matrix")
            comp_data = {
                "Profile": ["Conservative", "Balanced", "Science-First"],
                "Distance": [f"{res_cons.distance_m:,.0f} m", f"{res_bal.distance_m:,.0f} m", f"{res_sci.distance_m:,.0f} m"],
                "Cost": [f"{res_cons.cost:,.0f}", f"{res_bal.cost:,.0f}", f"{res_sci.cost:,.0f}"],
                "Science": [f"{res_cons.science_score:.0f} pts", f"{res_bal.science_score:.0f} pts", f"{res_sci.science_score:.0f} pts"],
                "Targets": [
                    f"{len(res_cons.visited_waypoint_ids)}",
                    f"{len(res_bal.visited_waypoint_ids)}",
                    f"{len(res_sci.visited_waypoint_ids)}",
                ],
            }
            st.dataframe(comp_data, use_container_width=True, hide_index=True)

            # Traverse Waypoint Routing Summary
            visited_names = [w.name for w in active_waypoints if w.id in primary_route.visited_waypoint_ids]
            seq_str = " → ".join(visited_names) if visited_names else "Direct Traverse (0 intermediate stops)"
            st.markdown(
                f"""
                <div style="background: #111622; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px; margin-top: 12px;">
                    <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #8E9CAE; font-weight: 600; margin-bottom: 6px;">Traverse Endpoint & Waypoint Routing</div>
                    <div style="font-size: 0.82rem; color: #CBD5E1; margin-bottom: 4px;"><b>Departure:</b> <span style="color: #00E676;">{raw_start['name']}</span></div>
                    <div style="font-size: 0.82rem; color: #CBD5E1; margin-bottom: 4px;"><b>Arrival Goal:</b> <span style="color: #FF1744;">{raw_goal['name']}</span></div>
                    <div style="font-size: 0.82rem; color: #CBD5E1;"><b>Target Sequence:</b> {seq_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------------------------
    # SUPPORTING MISSION TOOLS (Structured Workstations: Science Budget, Gauntlet, AI)
    # --------------------------------------------------------------------------
    st.markdown("---")
    tab_budget, tab_gauntlet, tab_ai = st.tabs([
        "🔬 The Science Budget & Pareto Frontier",
        "🛡️ The Gauntlet (Stress-Testing)",
        "🤖 Mission Commander AI",
    ])

    with tab_budget:
        st.markdown(
            """
            <div style="margin: 4px 0 12px 0;">
                <h3 style="color: #00E676; margin: 0; font-size: 1.25rem;">
                    The Science Budget & Multi-Objective Pareto Frontier
                </h3>
                <div style="font-size: 0.82rem; color: #8E9CAE;">
                    Analytical evaluation of candidate exploration plans balancing physical ground distance, modeled terrain effort, and scientific return.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Narrative Debrief Card
        frontier_narr = generate_science_budget_narrative(frontier_res, voice_mode=voice_mode)
        st.markdown(
            f"""
            <div class="frontier-card">
                <div style="font-weight: 600; font-size: 0.98rem; color: #00E676; margin-bottom: 4px;">{frontier_narr['headline']}</div>
                <div style="font-size: 0.86rem; color: #CBD5E1; line-height: 1.45;">{frontier_narr['detail']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Summary Metrics Row
        sb_c1, sb_c2, sb_c3, sb_c4 = st.columns(4)
        with sb_c1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Subsets Evaluated</div>
                    <div class="metric-value">{frontier_res.total_subsets_evaluated}</div>
                    <div class="metric-delta">2^{len(active_waypoints)} exact combinations</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with sb_c2:
            feas_count = sum(1 for c in frontier_res.candidates if c.is_feasible)
            pct_feas = (feas_count / frontier_res.total_subsets_evaluated * 100.0) if frontier_res.total_subsets_evaluated else 0.0
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Feasible Traverses</div>
                    <div class="metric-value">{feas_count} / {frontier_res.total_subsets_evaluated}</div>
                    <div class="metric-delta">{pct_feas:.0f}% satisfy all constraints</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with sb_c3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">2D Pareto Optimal</div>
                    <div class="metric-value">{len(frontier_res.pareto_candidates_2d)}</div>
                    <div class="metric-delta">non-dominated (dist vs science)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with sb_c4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">3D Pareto Optimal</div>
                    <div class="metric-value">{len(frontier_res.pareto_candidates_3d)}</div>
                    <div class="metric-delta">dist, slope cost & science</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Chart Dimension Selector & Sensitivity Note
        chart_ctrl1, chart_ctrl2 = st.columns([1.5, 3.5])
        with chart_ctrl1:
            frontier_view_mode = st.radio(
                "Frontier Dimensionality:",
                ["2D Frontier (Distance vs. Science)", "3D Space (Distance, Cost, Science)"],
                index=0,
                horizontal=False,
                help="2D space examines physical distance vs science points. 3D space accounts for steep terrain cost.",
            )
        with chart_ctrl2:
            if frontier_res.max_distance_m is not None:
                st.info(
                    f"ℹ️ **Sensitivity Note:** Maximum distance budget is set to **{frontier_res.max_distance_m:,.0f} m**. "
                    f"Traverses exceeding this ceiling are marked infeasible (red crosses) and excluded from the Pareto frontier."
                )
            else:
                st.info("ℹ️ **Sensitivity Note:** No distance budget ceiling enforced. All reachable traverses are evaluated.")

        # Render Plotly Chart
        budget_fig = render_science_budget_chart(
            frontier_result=frontier_res,
            active_profile=profile,
            view_mode="2d" if "2D" in frontier_view_mode else "3d",
            scenario_frontier_result=scen_frontier_res if (gauntlet_active and scenario_def) else None,
            inspected_candidate_id=st.session_state.get("inspected_cand_id"),
        )
        st.plotly_chart(budget_fig, use_container_width=True, config={"displayModeBar": True})

        # Candidate Plan Inspection & Map Sync
        st.markdown("##### 🔍 Candidate Plan Inspection & Tactical Map Sync")
        insp_col1, insp_col2 = st.columns([1.4, 1.6])
        with insp_col1:
            cand_choice_labels = [
                f"{'[★ 2D Frontier] ' if c.is_pareto_2d else ('[3D Frontier] ' if c.is_pareto_3d else '[Dominated] ' if c.is_feasible else '[Infeasible] ')}"
                f"{c.candidate_id} ({c.num_targets} stops, {c.distance_m:.0f} m, {c.science_score:.0f} pts)"
                for c in frontier_res.candidates
            ]
            cand_map_lookup = {label: c for label, c in zip(cand_choice_labels, frontier_res.candidates)}

            # Default selection: recommended plan index or 0
            rec_idx = 0
            if frontier_res.recommended_plan:
                for idx, c in enumerate(frontier_res.candidates):
                    if c.candidate_id == frontier_res.recommended_plan.candidate_id:
                        rec_idx = idx
                        break

            selected_cand_label = st.selectbox(
                "Select Candidate Plan to Inspect:",
                cand_choice_labels,
                index=rec_idx,
                key="science_budget_cand_select",
            )
            selected_cand = cand_map_lookup[selected_cand_label]
            st.session_state["inspected_cand_id"] = selected_cand.candidate_id

            show_map_sync = st.checkbox(
                "Overlay Inspected Plan on Tactical Map (Cyan Polyline)",
                value=st.session_state.get("show_inspected_on_map", False),
                key="cb_show_inspected_on_map",
            )
            if show_map_sync != st.session_state.get("show_inspected_on_map", False):
                st.session_state["show_inspected_on_map"] = show_map_sync
                st.rerun()

        with insp_col2:
            if selected_cand.is_pareto_2d:
                status_badge = '<span class="frontier-badge-optimal">★ 2D PARETO OPTIMAL</span>'
            elif selected_cand.is_pareto_3d:
                status_badge = '<span class="frontier-badge-optimal">3D PARETO OPTIMAL</span>'
            elif selected_cand.is_feasible:
                status_badge = '<span class="frontier-badge-dominated">DOMINATED</span>'
            else:
                status_badge = '<span class="frontier-badge-infeasible">INFEASIBLE</span>'

            st.markdown(
                f"""
                <div style="background: #111622; border: 1px solid #1E2738; border-radius: 6px; padding: 14px 18px; word-break: break-word; overflow-wrap: break-word;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                        <span style="font-weight: 700; color: #00E5FF; font-size: 1.05rem; word-break: break-all; font-family: 'JetBrains Mono', Consolas, monospace;">{selected_cand.candidate_id}</span>
                        {status_badge}
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; margin-bottom: 6px; word-break: break-word;">
                        <b>Targets Visited:</b> {', '.join(selected_cand.visited_waypoint_names) if selected_cand.visited_waypoint_names else 'Direct Traverse (0 science stops)'}
                    </div>
                    <div style="display: flex; gap: 16px; font-size: 0.82rem; color: #8E9CAE; margin-top: 8px; flex-wrap: wrap;">
                        <div>Distance: <b style="color: #F8FAFC;">{selected_cand.distance_m:,.0f} m</b></div>
                        <div>Modeled Cost: <b style="color: #F8FAFC;">{selected_cand.cost:,.0f}</b></div>
                        <div>Science: <b style="color: #00E676;">{selected_cand.science_score:.0f} pts</b></div>
                        <div>Profile: <b style="color: #FF5722;">{selected_cand.profile_tag or 'Custom Subset'}</b></div>
                    </div>
                    {f'<div style="font-size: 0.82rem; color: #B388FF; margin-top: 8px; word-break: break-word;">Mission Commander AI Utility: <b>{selected_cand.utility_score:+.3f}</b></div>' if selected_cand.utility_score is not None else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Gauntlet Disruption Impact on Exploration Frontier (when Gauntlet active)
        if gauntlet_active and frontier_comp:
            st.markdown("##### 🛡️ Gauntlet Disruption Impact on Exploration Frontier")
            g_c1, g_c2, g_c3, g_c4 = st.columns(4)
            with g_c1:
                st.metric("Plans Severed by Obstacle", f"{frontier_comp['num_severed_plans']}", delta=f"-{frontier_comp['num_severed_plans']}", delta_color="inverse")
            with g_c2:
                st.metric("Frontier Plans Retained", f"{frontier_comp['frontier_retained_count']}")
            with g_c3:
                st.metric("Max Science Achievable", f"{frontier_comp['max_science_scenario']:.0f} pts", delta=f"-{frontier_comp['lost_science_ceiling']:.0f} pts" if frontier_comp['lost_science_ceiling'] > 0 else "0 pts", delta_color="inverse")
            with g_c4:
                st.metric("Min Traverse Detour", f"{frontier_comp['min_dist_scenario']:.0f} m", delta=f"+{frontier_comp['delta_min_dist']:.0f} m" if frontier_comp['delta_min_dist'] > 0 else "0 m", delta_color="inverse")

        # Objective Trade-Off vs Learned Commander Preference
        st.markdown(
            """
            <div style="margin-top: 26px; margin-bottom: 12px; padding-top: 6px;">
                <h5 style="color: #F8FAFC; margin: 0; font-size: 1.05rem; letter-spacing: 0.02em;">
                    ⚖️ Objective Trade-Off vs. Learned Commander Preference
                </h5>
                <div style="font-size: 0.80rem; color: #8E9CAE; margin-top: 2px;">
                    Autonomous Pareto policy recommendation vs. human preference utility model
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        rec_col1, rec_col2 = st.columns(2)
        with rec_col1:
            rec_cand = frontier_res.recommended_plan
            rec_cid = rec_cand.candidate_id if rec_cand else 'None'
            rec_tag = rec_cand.profile_tag.upper() if (rec_cand and rec_cand.profile_tag) else 'BALANCED'
            st.markdown(
                f"""
                <div style="background: #111622; border-left: 4px solid #00E676; border: 1px solid #1E2738; border-left-width: 4px; border-radius: 6px; padding: 14px 16px; min-height: 125px; display: flex; flex-direction: column; justify-content: space-between; word-break: break-word;">
                    <div>
                        <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8E9CAE; font-weight: 600; margin-bottom: 4px;">Recommendation A: Science Budget Policy</div>
                        <div style="font-size: 1.0rem; font-weight: 700; color: #00E676; margin: 2px 0 6px 0; word-break: break-word; line-height: 1.35;">
                            <span style="font-family: 'JetBrains Mono', Consolas, monospace;">{rec_cid}</span>
                            <span style="font-size: 0.80rem; color: #8E9CAE; font-weight: 500; margin-left: 6px;">({rec_tag})</span>
                        </div>
                    </div>
                    <div style="font-size: 0.83rem; color: #CBD5E1; line-height: 1.45;">
                        Pareto-optimal plan balancing marginal science points per kilometer of travel under configured appetite (γ = {science_appetite:.1f}).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with rec_col2:
            top_ai = ranked_routes[0] if (enable_commander_ai and ranked_routes) else None
            if top_ai:
                st.markdown(
                    f"""
                    <div style="background: #111622; border-left: 4px solid #7C4DFF; border: 1px solid #1E2738; border-left-width: 4px; border-radius: 6px; padding: 14px 16px; min-height: 125px; display: flex; flex-direction: column; justify-content: space-between; word-break: break-word;">
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8E9CAE; font-weight: 600; margin-bottom: 4px;">Recommendation B: Mission Commander AI</div>
                            <div style="font-size: 1.0rem; font-weight: 700; color: #B388FF; margin: 2px 0 6px 0; word-break: break-word; line-height: 1.35;">
                                {top_ai.profile.replace('_', ' ').title()} Profile <span style="font-size: 0.82rem; font-family: 'JetBrains Mono', Consolas, monospace; color: #D1C4E9;">(Utility: {top_ai.utility_score:+.3f})</span>
                            </div>
                        </div>
                        <div style="font-size: 0.83rem; color: #CBD5E1; line-height: 1.45;">
                            Highest predicted utility based on {len(pref_model.observations)} recorded preference choices.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                num_obs = len(pref_model.observations) if hasattr(pref_model, "observations") else 0
                if not enable_commander_ai:
                    ai_hint = "Enable Mission Commander AI in sidebar Section 6, then record pairwise choices in the 'Mission Commander AI' tab."
                elif num_obs < 3:
                    rem = 3 - num_obs
                    ai_hint = f"Record {rem} more pairwise route choice{'s' if rem > 1 else ''} in the 'Mission Commander AI' tab to activate personalized preferences."
                else:
                    ai_hint = "No feasible routes satisfy current safety and budget constraints."

                st.markdown(
                    f"""
                    <div style="background: #111622; border-left: 4px solid #8899A6; border: 1px solid #1E2738; border-left-width: 4px; border-radius: 6px; padding: 14px 16px; min-height: 125px; display: flex; flex-direction: column; justify-content: space-between; word-break: break-word;">
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: #8E9CAE; font-weight: 600; margin-bottom: 4px;">Recommendation B: Mission Commander AI</div>
                            <div style="font-size: 1.0rem; font-weight: 700; color: #8899A6; margin: 2px 0 6px 0;">
                                Untrained / Initializing
                            </div>
                        </div>
                        <div style="font-size: 0.83rem; color: #8E9CAE; line-height: 1.45;">
                            {ai_hint}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Mission Brief & Exploration Telemetry Export
        st.markdown("##### 📥 Mission Brief & Exploration Telemetry Export")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            csv_data = export_mission_brief_csv(frontier_res)
            st.download_button(
                label="📥 Download Candidate Plans (CSV)",
                data=csv_data,
                file_name=f"marswalk_science_budget_{profile}_{int(time.time())}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with exp_col2:
            meta = {
                "mission_name": "Jezero Western Delta Front EVA Rehearsal",
                "start_location": sel_start_name,
                "goal_location": sel_goal_name,
                "profile": profile,
                "science_appetite_gamma": science_appetite,
                "max_distance_budget_m": max_dist_budget,
                "terrain_weights": {"alpha_s": alpha_s, "alpha_r": alpha_r, "alpha_up": alpha_up},
                "voice_mode": voice_mode,
                "gauntlet_active": gauntlet_active,
                "scenario_name": scenario_def.name if (gauntlet_active and scenario_def) else None,
            }
            json_data = export_mission_brief_json(frontier_res, metadata=meta)
            st.download_button(
                label="📥 Download Full Mission Brief (JSON)",
                data=json_data,
                file_name=f"marswalk_mission_brief_{profile}_{int(time.time())}.json",
                mime="application/json",
                use_container_width=True,
            )

    with tab_gauntlet:
        if gauntlet_active:
            if toughness_report:
                st.markdown(
                    """
                    <div class="gauntlet-banner">
                        <b>🛡️ THE GAUNTLET: ROUTE TOUGHNESS BENCHMARK SUITE ACTIVE</b> — Stress-testing baseline traverse against 5 curated disruptions across Jezero Western Delta Front.<br>
                        <span style="font-size: 0.82rem; color: #CBD5E1;">Evaluates route resilience across corridor rockfalls, dune migration sinks, life-support budget drops, and localized outcrop hazards.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="debrief-card">
                        <div class="debrief-headline">Route Resilience Verdict</div>
                        <div class="debrief-body">{toughness_report.summary_narrative}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("##### Detailed Disruption Benchmark Results")
                t_data_tab = {
                    "Disruption Scenario": [r.scenario.name for r in toughness_report.results],
                    "Disruption Type": [r.scenario.disruption_type.value.replace("_", " ").title() for r in toughness_report.results],
                    "Traverse Feasible": ["✓ Yes" if r.is_reachable else "✕ Severed" for r in toughness_report.results],
                    "Budget Clearance": ["✓ Cleared" if r.is_budget_feasible else "✕ Exceeded" for r in toughness_report.results],
                    "Traverse Distance": [f"{r.distance_m:,.0f} m" if (r.is_reachable and not math.isnan(r.distance_m)) else "N/A" for r in toughness_report.results],
                    "Detour (+m)": [f"+{r.delta_distance_m:,.0f} m" if (r.is_reachable and not math.isnan(r.delta_distance_m)) else "N/A" for r in toughness_report.results],
                    "Science Retained": [f"{r.retention_pct:.0f}%" for r in toughness_report.results],
                }
                st.dataframe(t_data_tab, use_container_width=True, hide_index=True)

            elif scenario_comp and scenario_def:
                st.markdown(
                    f"""
                    <div class="gauntlet-banner">
                        <b>⚠️ THE GAUNTLET ACTIVE — HYPOTHETICAL DISRUPTION:</b> {scenario_def.name}<br>
                        <span style="font-size: 0.84rem; color: #CBD5E1;">{scenario_def.description}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="debrief-card">
                        <div class="debrief-headline">{scenario_comp.headline}</div>
                        <div class="debrief-body">{scenario_comp.detail}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(format_regret_ledger_html(scenario_comp.regret_ledger, active_waypoints), unsafe_allow_html=True)

                st.markdown("##### Comparative Analysis: Baseline vs Stress Detour")
                scen_r = scenario_comp.scenario_route
                comp_data_tab = {
                    "Plan Option": ["Baseline Plan", f"Gauntlet ({scenario_def.name})"],
                    "Physical Distance": [
                        f"{primary_route.distance_m:,.0f} m",
                        f"{scen_r.distance_m:,.0f} m" if scen_r.is_reachable else "Severed",
                    ],
                    "Modeled Cost": [
                        f"{primary_route.cost:,.0f}",
                        f"{scen_r.cost:,.0f}" if scen_r.is_reachable else "∞",
                    ],
                    "Science Harvested": [
                        f"{primary_route.science_score:.0f} pts",
                        f"{scen_r.science_score:.0f} pts" if scen_r.is_reachable else "0 pts",
                    ],
                    "Targets Visited": [
                        f"{len(primary_route.visited_waypoint_ids)}",
                        f"{len(scen_r.visited_waypoint_ids)}" if scen_r.is_reachable else "0",
                    ],
                    "Budget Clearance": [
                        "Cleared" if primary_route.is_budget_feasible else "Exceeded",
                        ("Cleared" if scen_r.is_budget_feasible else "Exceeded") if scen_r.is_reachable else "Infeasible",
                    ],
                }
                st.dataframe(comp_data_tab, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                """
                <div style="background: #111622; border: 1px solid #1E2738; border-radius: 6px; padding: 20px 22px; margin: 12px 0;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #FF5722; margin-bottom: 8px;">
                        🛡️ The Gauntlet — Martian EVA Stress-Testing Instrument
                    </div>
                    <div style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.5; margin-bottom: 12px;">
                        The Gauntlet enables mission planners to inject controlled, hypothetical terrain and operational anomalies to evaluate whether an exploration traverse remains viable when conditions degrade.
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 14px;">
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #FF9100; font-size: 0.88rem; margin-bottom: 4px;">Corridor Closures</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Simulate localized scarp collapses or dune field migration blocking primary delta access passes.</div>
                        </div>
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #FF9100; font-size: 0.88rem; margin-bottom: 4px;">Consumable Curtailment</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Simulate life-support oxygen leaks or battery drops curtailing walking limits by 10% to 60%.</div>
                        </div>
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #FF9100; font-size: 0.88rem; margin-bottom: 4px;">Science Regret Ledger</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Tracks exactly which scientific targets were preserved, pruned for detour budget, or severed by hazards.</div>
                        </div>
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #FF9100; font-size: 0.88rem; margin-bottom: 4px;">Route Toughness Benchmark</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Runs the baseline route through a standardized battery of 5 curated Jezero crater surface anomalies.</div>
                        </div>
                    </div>
                    <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #1E2738; font-size: 0.82rem; color: #00E5FF;">
                        👉 <b>Activation:</b> Toggle <b>"Activate The Gauntlet"</b> in the left sidebar control panel (Section 5) to test anomalies.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_ai:
        if enable_commander_ai:
            st.markdown(
                """
                <div style="margin: 4px 0 12px 0;">
                    <h3 style="color: #B388FF; margin: 0; font-size: 1.25rem;">
                        Mission Commander AI — Adaptive Preference Learning
                    </h3>
                    <div style="font-size: 0.82rem; color: #8E9CAE;">
                        Regularized Bradley-Terry utility model learning operational exploration preferences from pairwise commander selections.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            ai_summary = pref_model.get_preference_summary(voice_mode=voice_mode)
            st.markdown(
                f"""
                <div class="ai-card">
                    <div class="ai-headline">{ai_summary['headline']}</div>
                    <div style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.45;">
                        {ai_summary['detail']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if ranked_routes:
                if pref_model.get_state() == LearningState.PERSONALIZED:
                    top_rec = ranked_routes[0]
                    st.success(
                        f"🎯 **Commander AI Recommendation:** {top_rec.profile.replace('_', ' ').title()} Traverse "
                        f"(Score: {top_rec.utility_score:+.2f})\n\n{top_rec.explanation}"
                    )

                # Show ranking table
                rank_table_data = {
                    "Rank": [f"#{r.rank}" + (" (Recommended)" if r.is_recommended and pref_model.get_state() == LearningState.PERSONALIZED else "") for r in ranked_routes],
                    "Profile": [r.profile.replace("_", " ").title() for r in ranked_routes],
                    "Utility": [f"{r.utility_score:+.2f}" for r in ranked_routes],
                    "Distance": [f"{r.features.distance_m:,.0f} m" for r in ranked_routes],
                    "Effort": [f"{r.features.cost:,.0f}" for r in ranked_routes],
                    "Science": [f"{r.features.science_score:.0f} pts" for r in ranked_routes],
                }
                st.dataframe(rank_table_data, use_container_width=True, hide_index=True)

                # Route Feedback Action Form
                feasible_profs = [r.profile for r in ranked_routes]
                if len(feasible_profs) >= 2:
                    st.markdown("###### 🗳️ Record Commander Route Preference")
                    f_col1, f_col2 = st.columns([1.6, 1.0])
                    chosen_prof = f_col1.selectbox(
                        "Preferred Traverse:",
                        feasible_profs,
                        format_func=lambda x: x.replace("_", " ").title(),
                        key="commander_pref_select",
                    )
                    if f_col2.button("Save Choice", key="save_commander_choice", use_container_width=True):
                        sel_route = eval_candidates[chosen_prof]
                        sel_feats = extract_route_features(sel_route, terrain)
                        rejs = [
                            CandidateOption(p, extract_route_features(eval_candidates[p], terrain))
                            for p in feasible_profs
                            if p != chosen_prof
                        ]
                        cid = create_choice_id(chosen_prof, sel_feats, [c.profile for c in rejs])
                        obs = PreferenceObservation(
                            choice_id=cid,
                            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            selected_profile=chosen_prof,
                            selected_features=sel_feats,
                            rejected_candidates=rejs,
                        )
                        if pref_model.add_observation(obs):
                            save_preference_model(pref_model, PREFERENCES_FILE)
                            st.success(f"Preference saved for {chosen_prof.upper()}! ({len(pref_model.observations)} choices recorded)")
                            st.rerun()
                        else:
                            st.info("This exact preference comparison has already been recorded.")
            else:
                st.warning("⚠️ HARD CONSTRAINTS ENFORCED: No candidate routes satisfy terrain, reachability, and budget limits. Mission Commander AI cannot rank infeasible traverses.")
        else:
            st.markdown(
                """
                <div style="background: #111622; border: 1px solid #1E2738; border-radius: 6px; padding: 20px 22px; margin: 12px 0;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #B388FF; margin-bottom: 8px;">
                        🤖 Mission Commander AI — Adaptive Preference Learning
                    </div>
                    <div style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.5; margin-bottom: 12px;">
                        Mission Commander AI learns human exploration trade-off preferences through explicit pairwise choices between alternative traverses, adjusting regularized Bradley-Terry utility weights without violating hard safety constraints.
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-top: 14px;">
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #B388FF; font-size: 0.88rem; margin-bottom: 4px;">Convex L2 Optimization</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Trains linear utility weights over normalized ground distance, terrain effort, science yield, and cumulative climb.</div>
                        </div>
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #B388FF; font-size: 0.88rem; margin-bottom: 4px;">Hard Constraints Non-Negotiable</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Infeasible traverses (slopes ≥ 25°, severed corridors, budget exceedance) are strictly barred from ranking.</div>
                        </div>
                        <div style="background: #161D2C; border: 1px solid #1E2738; border-radius: 6px; padding: 12px 14px;">
                            <div style="font-weight: 600; color: #B388FF; font-size: 0.88rem; margin-bottom: 4px;">Calibrating Lifecycle</div>
                            <div style="font-size: 0.80rem; color: #8E9CAE;">Transitions from Untrained → Calibrating → Personalized once 3 user choices have been recorded.</div>
                        </div>
                    </div>
                    <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid #1E2738; font-size: 0.82rem; color: #00E5FF;">
                        👉 <b>Activation:</b> Toggle <b>"Enable Mission Commander AI"</b> in the left sidebar control panel (Section 6).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------------------------
    # PERSISTENT DATA PROVENANCE & UNMODELED HAZARD DISCLAIMER
    # --------------------------------------------------------------------------
    disclaimer = get_blind_spot_disclaimer(voice_mode=voice_mode)
    st.markdown(
        f"""
        <div class="provenance-deck">
            <div class="provenance-header">
                <span class="provenance-title">DATA PROVENANCE, RESOLUTION & SENSOR LIMITATIONS</span>
                <span class="provenance-badge">RESEARCH PROTOTYPE • NOT FLIGHT CERTIFIED</span>
            </div>
            <div class="provenance-grid">
                <div class="provenance-item">
                    <div class="provenance-label">Primary Topographic Dataset</div>
                    <div class="provenance-text">{disclaimer['provenance']}</div>
                </div>
                <div class="provenance-item">
                    <div class="provenance-label">Grid Geometry & Ground Spacing</div>
                    <div class="provenance-text">{disclaimer['resolution_limit']}</div>
                </div>
                <div class="provenance-item provenance-hazard">
                    <div class="provenance-label">Sub-Pixel Hazards & Operational Safety</div>
                    <div class="provenance-text"><b>{disclaimer['unmodeled_hazards']}</b></div>
                </div>
            </div>
            <div class="provenance-footer">
                MarsWalk is an independent research prototype developed for the 2026 NASA Space Apps Challenge. 
                Not affiliated with or endorsed by NASA, JPL, or USGS.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
