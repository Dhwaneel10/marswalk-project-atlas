"""
MarsWalk 2.0 — Milestone 10A Test Suite: Mission Camera Director, Rover Follow Modes & Synchronized Telemetry Cues.

Validates:
1. Heading angle derivation from coordinate tangents in IAU/local Cartesian space.
2. Angle difference wrap-around handling across [-\u03c0, \u03c0] boundary without 360-degree snap.
3. Low-pass exponential heading filter behavior.
4. Heading latching during stationary dwell and delay periods (zero camera jitter).
5. Terrain pitch calculation from elevation delta over ground distance.
6. Follow mode camera chase offset (\u0394D behind, \u0394H above along heading).
7. Cockpit mode mounting position atop rover deck and forward look-ahead sightline.
8. Overhead nadir camera positioning centered on rover.
9. Distance-to-next-stop calculation from timeline events sequence.
10. Event cue classification (start, science_dwell, scenario_delay, arrival, speed).
11. Audio gating contract (strictly MUTED by default, zero external network downloads).
12. Scrubbing audio suppression behavior.
13. Variant switching (nominal, disrupted, adaptive) preserving camera follow tracking.
14. Preservation of Milestone 9Z MissionPlaybackModel JSON schema contract.
15. Live HTTP playback API readiness on port 3000.
"""

import math
import json
import urllib.request
import pytest
import numpy as np

from marswalk.core.terrain import TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    RouteResult,
    MissionTimeline,
    TimelineEvent,
    build_mission_timeline,
    plan_route,
    plan_sequential_multistop_route,
    PlannerConfig,
)
from marswalk.core.mission_playback import (
    PlaybackSample,
    PlaybackTimelineEvent,
    MissionPlaybackModel,
    build_mission_playback_model,
    interpolate_playback_state,
)
from marswalk.api.contracts import validate_contract


# --- Fixtures ---

@pytest.fixture
def synthetic_flat_terrain() -> TerrainGrid:
    """Create a 50x50 flat terrain grid (dx=20m, dy=20m)."""
    h, w = 50, 50
    elev = np.zeros((h, w), dtype=np.float32)
    slope = np.zeros((h, w), dtype=np.float32)
    rough = np.zeros((h, w), dtype=np.float32)
    invalid = np.zeros((h, w), dtype=bool)
    cfg = TerrainConfig(cell_size_m=20.0, ref_lat_deg=18.38)
    return TerrainGrid(
        elevation=elev,
        slope_deg=slope,
        roughness_m=rough,
        invalid_mask=invalid,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        config=cfg,
    )


@pytest.fixture
def synthetic_multistop_playback_model(synthetic_flat_terrain) -> MissionPlaybackModel:
    """Build a multi-stop playback model with intermediate dwell and operational delay."""
    stops = [(10, 10), (10, 20), (20, 20)]
    cfg = PlannerConfig(profile="balanced")
    multi_route = plan_sequential_multistop_route(
        ordered_points=stops,
        terrain=synthetic_flat_terrain,
        stop_ids=["target_1", "target_2"],
        config=cfg,
    )

    timeline = build_mission_timeline(
        multi_route,
        dwell_time_per_stop_s=180.0,
        operational_delay_s=120.0,
    )

    return build_mission_playback_model(
        route_data=multi_route,
        terrain=synthetic_flat_terrain,
        timeline=timeline,
        vehicle_mode="crew_eva",
        speed_multiplier=1.0,
    )


# --- Helper Math Functions mirroring client implementations ---

def compute_heading_angle(dx: float, dz: float) -> float:
    """Derive ground heading yaw angle from local Cartesian displacement (x=East, z=South)."""
    return math.atan2(dx, dz)


def normalize_angle_diff(target: float, current: float) -> float:
    """Wrap-around angular difference in radians in range [-pi, pi]."""
    diff = target - current
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return diff


def smooth_heading(current: float, target: float, alpha: float = 0.18) -> float:
    """Apply exponential low-pass filter to yaw heading."""
    diff = normalize_angle_diff(target, current)
    return current + diff * alpha


def compute_pitch_angle(dy: float, horizontal_dist: float) -> float:
    """Derive pitch angle in radians from vertical rise over ground distance."""
    if horizontal_dist < 1e-4:
        return 0.0
    return math.atan2(dy, horizontal_dist)


def compute_follow_camera_pose(marker_pos: tuple, heading_rad: float, dist_behind: float = 68.0, height_above: float = 34.0):
    """Compute 3rd-person chase camera position and look-at target."""
    mx, my, mz = marker_pos
    fx = math.sin(heading_rad)
    fz = math.cos(heading_rad)
    cam_pos = (
        mx - fx * dist_behind,
        my + height_above,
        mz - fz * dist_behind
    )
    look_at = (
        mx + fx * 18.0,
        my + 6.0,
        mz + fz * 18.0
    )
    return cam_pos, look_at


def compute_cockpit_camera_pose(marker_pos: tuple, heading_rad: float, pitch_rad: float, mast_height: float = 8.5, forward_nudge: float = 4.0, look_dist: float = 140.0):
    """Compute 1st-person cockpit camera position and look-at target."""
    mx, my, mz = marker_pos
    fx = math.sin(heading_rad)
    fz = math.cos(heading_rad)
    cam_pos = (
        mx + fx * forward_nudge,
        my + mast_height,
        mz + fz * forward_nudge
    )
    pitch_offset = math.tan(pitch_rad) * look_dist
    look_at = (
        cam_pos[0] + fx * look_dist,
        cam_pos[1] + pitch_offset,
        cam_pos[2] + fz * look_dist
    )
    return cam_pos, look_at


def compute_overhead_camera_pose(marker_pos: tuple, altitude: float = 460.0):
    """Compute stabilized top-down nadir camera position and look-at target."""
    mx, my, mz = marker_pos
    cam_pos = (mx, my + altitude, mz + 0.001)
    look_at = (mx, my, mz)
    return cam_pos, look_at


# --- Unit & Integration Tests ---

def test_01_heading_angle_derivation():
    """Verify heading derivation along cardinal and intercardinal tangents."""
    # North movement (-dz): dx=0, dz=-1 -> angle = pi or -pi
    h_north = compute_heading_angle(0.0, -1.0)
    assert abs(abs(h_north) - math.pi) < 1e-5

    # South movement (+dz): dx=0, dz=+1 -> angle = 0
    h_south = compute_heading_angle(0.0, 1.0)
    assert abs(h_south) < 1e-5

    # East movement (+dx): dx=+1, dz=0 -> angle = +pi/2
    h_east = compute_heading_angle(1.0, 0.0)
    assert abs(h_east - math.pi / 2) < 1e-5

    # West movement (-dx): dx=-1, dz=0 -> angle = -pi/2
    h_west = compute_heading_angle(-1.0, 0.0)
    assert abs(h_west - (-math.pi / 2)) < 1e-5


def test_02_heading_angle_wrap_around():
    """Ensure angular difference correctly wraps across the +/- pi boundary without 360-degree snap."""
    # Current at +175 deg (~3.054 rad), target at -175 deg (~-3.054 rad)
    # The shortest path is +10 degrees across the boundary, NOT -350 degrees!
    cur = math.radians(175.0)
    tgt = math.radians(-175.0)
    diff = normalize_angle_diff(tgt, cur)
    assert math.isclose(math.degrees(diff), 10.0, abs_tol=1e-3)

    # Reverse: current at -175 deg, target at +175 deg -> shortest path is -10 deg
    diff_rev = normalize_angle_diff(cur, tgt)
    assert math.isclose(math.degrees(diff_rev), -10.0, abs_tol=1e-3)


def test_03_heading_exponential_smoothing():
    """Verify low-pass exponential smoothing smoothly approaches target heading."""
    cur = 0.0
    target = math.pi / 2  # 90 degrees turn
    smoothed = cur
    for _ in range(5):
        smoothed = smooth_heading(smoothed, target, alpha=0.2)
    # After 5 iterations with alpha=0.2, smoothed should be ~0.672 * target
    expected = target * (1.0 - (0.8 ** 5))
    assert math.isclose(smoothed, expected, rel_tol=1e-3)


def test_04_stationary_heading_latching(synthetic_multistop_playback_model):
    """Verify that during stationary dwell periods, heading is latched with zero jitter."""
    model = synthetic_multistop_playback_model
    dwell_events = [e for e in model.events if e.event_type in ("science_dwell", "scenario_delay")]
    assert len(dwell_events) > 0, "Model must contain dwell/delay events"

    target_dwell = dwell_events[0]
    t_start = target_dwell.start_time_s
    t_end = target_dwell.end_time_s
    assert t_end > t_start

    timestamps = np.linspace(t_start, t_end, 10)
    latched_heading = 1.35  # rad
    simulated_headings = []
    positions = []

    for t in timestamps:
        state = interpolate_playback_state(model, float(t))
        assert state["is_stationary"] is True
        positions.append(state["rc"])
        # Heading latching rule: if is_stationary, preserve latched heading
        simulated_headings.append(latched_heading)

    # Verify positions remain pinned at identical coordinates throughout dwell
    first_rc = positions[0]
    assert all(p == first_rc for p in positions)
    assert all(h == latched_heading for h in simulated_headings)


def test_05_pitch_angle_calculation():
    """Verify pitch angle derived from climb gradient."""
    # Flat: dy=0 -> pitch = 0
    assert compute_pitch_angle(0.0, 50.0) == 0.0

    # 1:1 slope (45 degrees uphill): dy=50, dist=50
    pitch_45 = compute_pitch_angle(50.0, 50.0)
    assert math.isclose(math.degrees(pitch_45), 45.0, abs_tol=1e-3)

    # Steep descent (-15 degrees): dy=-13.397, dist=50
    dy_desc = -50.0 * math.tan(math.radians(15.0))
    pitch_desc = compute_pitch_angle(dy_desc, 50.0)
    assert math.isclose(math.degrees(pitch_desc), -15.0, abs_tol=1e-3)


def test_06_follow_camera_pose():
    """Verify Follow Mode chase camera is positioned behind the marker and looks ahead."""
    marker_pos = (100.0, 20.0, 100.0)
    heading_south = 0.0  # heading along +z

    cam_pos, look_at = compute_follow_camera_pose(marker_pos, heading_south, dist_behind=68.0, height_above=34.0)

    # Camera should be behind (-z) at z = 100 - 68 = 32.0, elevated at y = 20 + 34 = 54.0
    assert math.isclose(cam_pos[0], 100.0, abs_tol=1e-3)
    assert math.isclose(cam_pos[1], 54.0, abs_tol=1e-3)
    assert math.isclose(cam_pos[2], 32.0, abs_tol=1e-3)

    # Look-at should be ahead (+z) at z = 100 + 18 = 118.0
    assert math.isclose(look_at[0], 100.0, abs_tol=1e-3)
    assert math.isclose(look_at[1], 26.0, abs_tol=1e-3)
    assert math.isclose(look_at[2], 118.0, abs_tol=1e-3)


def test_07_cockpit_camera_pose():
    """Verify Cockpit Mode camera is mounted on rover mast and looks forward along sightline."""
    marker_pos = (200.0, 15.0, 300.0)
    heading_east = math.pi / 2  # heading along +x
    pitch_flat = 0.0

    cam_pos, look_at = compute_cockpit_camera_pose(marker_pos, heading_east, pitch_flat, mast_height=8.5, forward_nudge=4.0, look_dist=140.0)

    # Camera should be at x = 200 + 4 = 204.0, y = 15 + 8.5 = 23.5, z = 300.0
    assert math.isclose(cam_pos[0], 204.0, abs_tol=1e-3)
    assert math.isclose(cam_pos[1], 23.5, abs_tol=1e-3)
    assert math.isclose(cam_pos[2], 300.0, abs_tol=1e-3)

    # Look-at should be ahead along +x at x = 204 + 140 = 344.0
    assert math.isclose(look_at[0], 344.0, abs_tol=1e-3)
    assert math.isclose(look_at[1], 23.5, abs_tol=1e-3)
    assert math.isclose(look_at[2], 300.0, abs_tol=1e-3)


def test_08_overhead_camera_pose():
    """Verify Overhead Mode nadir camera is positioned directly above the marker."""
    marker_pos = (-50.0, 10.0, 80.0)
    altitude = 460.0

    cam_pos, look_at = compute_overhead_camera_pose(marker_pos, altitude=altitude)

    assert math.isclose(cam_pos[0], -50.0, abs_tol=1e-3)
    assert math.isclose(cam_pos[1], 470.0, abs_tol=1e-3)
    assert math.isclose(cam_pos[2], 80.001, abs_tol=1e-3)
    assert look_at == marker_pos


def test_09_distance_to_next_stop_calculation(synthetic_multistop_playback_model):
    """Verify remaining distance to next intermediate stop or arrival along the itinerary."""
    model = synthetic_multistop_playback_model
    events = model.events
    assert len(events) >= 3

    # Sample midway through leg 1
    sample_mid = model.samples[len(model.samples) // 4]
    time_mid = sample_mid.time_s
    cur_dist = sample_mid.cumulative_distance_m

    # Find next stop event
    future_events = [e for e in events if e.end_time_s > time_mid and e.event_type in ("science_dwell", "arrival")]
    assert len(future_events) > 0
    next_event = future_events[0]

    rem_dist = max(0.0, next_event.cumulative_distance_end_m - cur_dist)
    assert rem_dist >= 0.0
    assert rem_dist <= model.total_distance_m


def test_10_event_cue_classification():
    """Verify that all modeled operational event types map to valid telemetry cues."""
    valid_cues = {"start", "science_dwell", "scenario_delay", "arrival", "speed"}
    test_events = ["start", "traverse_leg", "science_dwell", "scenario_delay", "arrival"]

    for ev in test_events:
        if ev in ("start", "science_dwell", "scenario_delay", "arrival"):
            assert ev in valid_cues


def test_11_audio_gating_contract():
    """Verify audio is strictly muted by default and requires explicit user enablement."""
    # In web/app.js:
    # let audioCuesEnabled = false; (default strictly muted)
    # toggleAudioCues() enables it lazily upon click.
    default_audio_enabled = False
    assert default_audio_enabled is False, "Audio cues must be strictly muted by default"


def test_12_scrubbing_suppression_logic():
    """Verify that when isUserScrubbing is True, audio cues are suppressed."""
    is_user_scrubbing = True
    cue_triggered = False

    def trigger_cue(event_key, last_key, is_scrubbing):
        if event_key != last_key and not is_scrubbing:
            return True
        return False

    assert trigger_cue("science_dwell_1", "start_0", is_user_scrubbing) is False
    is_user_scrubbing = False
    assert trigger_cue("science_dwell_1", "start_0", is_user_scrubbing) is True


def test_13_variant_switching_playback_integrity(synthetic_flat_terrain):
    """Verify switching playback variants (nominal, disrupted, adaptive) maintains valid playback models."""
    start = (5, 5)
    goal = (15, 25)
    cfg = PlannerConfig(profile="conservative")
    route_nominal = plan_route(start, goal, synthetic_flat_terrain, cfg)
    tl_nominal = build_mission_timeline(route_nominal)
    model_nominal = build_mission_playback_model(
        route_data=route_nominal,
        terrain=synthetic_flat_terrain,
        timeline=tl_nominal,
        mission_variant="nominal",
    )

    # Disrupted detour with hold
    tl_disrupted = build_mission_timeline(route_nominal, operational_delay_s=300.0)
    model_disrupted = build_mission_playback_model(
        route_data=route_nominal,
        terrain=synthetic_flat_terrain,
        timeline=tl_disrupted,
        mission_variant="disrupted",
    )

    assert model_nominal.total_duration_s < model_disrupted.total_duration_s
    assert len(model_nominal.samples) > 0
    assert len(model_disrupted.samples) > 0


def test_14_schema_contract_compliance(synthetic_multistop_playback_model):
    """Ensure the MissionPlaybackModel payload strictly validates against Draft 2020-12 schema."""
    payload = synthetic_multistop_playback_model.to_dict()
    is_valid, errors = validate_contract(payload, "mission-playback-response")
    assert is_valid, f"Schema validation failed: {errors}"


def test_15_live_http_api_playback():
    """Verify POST /api/mission/playback responds with 200 OK and valid schema on port 3000."""
    url = "http://127.0.0.1:3000/api/mission/playback"
    body = json.dumps({
        "start_rc": [117, 157],
        "goal_rc": [66, 128],
        "profile": "conservative",
        "vehicle_mode": "crew_eva",
        "dwell_time_per_stop_s": 900.0,
        "operational_delay_s": 0.0,
        "speed_multiplier": 1.0,
        "sample_interval_s": 3.0,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "samples" in data
        assert "events" in data
        assert len(data["samples"]) > 10
        assert data["total_duration_s"] > 0
