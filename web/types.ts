/**
 * MarsWalk 2.0 TypeScript Data Definitions
 * Precise schemas for planetary geodetics, terrain grids, waypoints, and Python-planned routes.
 */

export interface SourceAttribution {
  elevation: string;
  waypoints: string;
  global_tiles: string;
  disclaimer: string;
}

export interface ProjectedBounds {
  left: number;
  right: number;
  bottom: number;
  top: number;
  width_m: number;
  height_m: number;
}

export interface GeographicBounds {
  min_lon_deg: number;
  max_lon_deg: number;
  min_lat_deg: number;
  max_lat_deg: number;
  center_lon_deg: number;
  center_lat_deg: number;
}

export interface MissionBounds {
  projected: ProjectedBounds;
  geographic: GeographicBounds;
}

export interface TerrainGridMeta {
  rows: number;
  cols: number;
  projected_cell_size_m: number;
  ground_dx_m: number;
  ground_dy_m: number;
  elevation_min_m: number;
  elevation_max_m: number;
  elevation_mean_m: number;
}

export interface Waypoint {
  id: string;
  name: string;
  type: string;
  priority_score: number;
  lon_deg: number;
  lat_deg: number;
  elevation_m: number;
  row: number;
  col: number;
  geological_context: string;
  crism_signature: string;
  pds_citation: string;
}

export interface RouteProfileResult {
  profile: 'conservative' | 'balanced' | 'science_first';
  distance_m: number;
  cost: number;
  science_score: number;
  visited_waypoint_ids: string[];
  num_steps: number;
  num_cells: number;
  is_reachable: boolean;
  cumulative_climb_m: number;
  max_slope_deg: number;
  path_rc: [number, number][];
  coordinates_3d: [number, number, number][]; // [lon_deg, lat_deg, elevation_m]
}

export interface JezeroMissionData {
  schema_version: string;
  target: string;
  crs: string;
  datum: string;
  source_attribution: SourceAttribution;
  bounds: MissionBounds;
  grid: TerrainGridMeta;
  waypoints: Waypoint[];
  routes: Record<string, RouteProfileResult>;
  elevation_samples: number[][];
  slope_samples: number[][];
}

export interface GlobeCameraState {
  longitude_deg: number;
  latitude_deg: number;
  altitude_km: number;
  heading_deg: number;
  pitch_deg: number;
}

export interface EndpointSpec {
  row?: number;
  col?: number;
  lon_deg?: number;
  lat_deg?: number;
}

export interface PlanRouteRequest {
  start: EndpointSpec;
  goal: EndpointSpec;
  profile?: 'conservative' | 'balanced' | 'science_first';
  max_distance_m?: number;
  science_appetite_gamma?: number;
}

export interface PlanRouteResponse {
  is_reachable: boolean;
  is_budget_feasible: boolean;
  profile: string;
  distance_m: number;
  cost: number | null;
  cumulative_climb_m: number;
  max_slope_deg: number;
  science_score: number;
  visited_waypoint_ids: string[];
  num_steps: number;
  num_cells: number;
  path_rc: [number, number][];
  coordinates_3d: [number, number, number][];
  status_message: string;
  execution_time_s: number;
  start_rc: [number, number];
  goal_rc: [number, number];
}

export interface GauntletRequest {
  start: EndpointSpec;
  goal: EndpointSpec;
  profile?: 'conservative' | 'balanced' | 'science_first';
  scenario_id?: string;
  blocked_cells?: [number, number][];
  budget_reduction_pct?: number;
  voice_mode?: 'professional' | 'dry_humour';
  max_distance_m?: number;
}

export interface GauntletScenarioMeta {
  id: string;
  name: string;
  disruption_type: string;
  description: string;
  is_simulated: boolean;
  num_blocked_cells: number;
}

export interface RegretLedgerSummary {
  baseline_visited_ids: string[];
  scenario_visited_ids: string[];
  retained_target_ids: string[];
  dropped_by_optimizer_ids: string[];
  disabled_by_scenario_ids: string[];
  baseline_priority: number;
  retained_priority: number;
  lost_priority: number;
  retention_pct: number;
}

export interface GauntletResponse {
  disclaimer: string;
  scenario: GauntletScenarioMeta;
  baseline_route: PlanRouteResponse;
  scenario_route: PlanRouteResponse;
  delta_distance_m: number | null;
  pct_distance_change: number | null;
  delta_cost: number | null;
  pct_cost_change: number | null;
  is_baseline_reachable: boolean;
  is_scenario_reachable: boolean;
  is_baseline_budget_feasible: boolean;
  is_scenario_budget_feasible: boolean;
  regret_ledger: RegretLedgerSummary;
  headline: string;
  detail: string;
}

export type PlaceCategory =
  | 'mission_site'
  | 'volcano'
  | 'canyon'
  | 'crater'
  | 'plain'
  | 'region'
  | 'chaos'
  | 'ridge'
  | 'other';

export interface MarsPlace {
  id: string;
  name: string;
  feature_type: string;
  category: PlaceCategory;
  lat_deg: number;
  lon_deg: number;
  center_lon_360: number;
  diameter_km: number | null;
  elevation_approx_m: number | null;
  origin?: string;
  approval?: string;
  approval_date?: string;
  quad_name?: string;
  usgs_link?: string;
  dataset_attribution: string;
  is_landing_site: boolean;
  importance_tier: 1 | 2 | 3;
  agency?: string;
  mission?: string;
  host_feature?: string;
  landing_date?: string;
  description?: string;
  pds_citation?: string;
}

export interface MarsPlaceCatalog {
  metadata: {
    title: string;
    datum: string;
    primary_sources: string[];
    total_records: number;
    landing_sites_count: number;
    tier_counts: Record<number, number>;
    category_counts: Record<string, number>;
  };
  featured_destinations: string[];
  places: MarsPlace[];
}

export type NavigationState =
  | 'idle-orbit'
  | 'user-interacting'
  | 'searching'
  | 'camera-flight'
  | 'regional-exploration'
  | 'jezero-workstation';

export type TerrainTextureMode = 'ctx' | 'slope' | 'hypsometric';

export interface ImageryProductBounds {
  min_lon_deg: number;
  max_lon_deg: number;
  min_lat_deg: number;
  max_lat_deg: number;
}

export interface ImageryProductRecord {
  id: string;
  title: string;
  layer_type: 'global_basemap' | 'regional_mosaic' | 'local_mesh_ortho';
  region_name: string;
  target_body: string;
  source: string;
  attribution: string;
  pds_citation: string;
  crs: string;
  longitude_convention: string;
  bounds: ImageryProductBounds;
  nominal_resolution_m: number;
  zoom_range: [number, number];
  wmts_capabilities_url: string | null;
  wmts_tile_template: string | null;
  local_asset_path: string | null;
  has_elevation_data: boolean;
  elevation_source: string | null;
  elevation_resolution_m: number | null;
  elevation_bounds: ImageryProductBounds | null;
  planning_supported: boolean;
  description: string;
  fallback_product_id: string | null;
}

export interface ImageryRegistryData {
  schema_version: string;
  target: string;
  crs: string;
  datum: string;
  metadata: {
    title: string;
    updated: string;
    total_products: number;
    global_basemaps_count: number;
    regional_mosaics_count: number;
    local_elevation_meshes_count: number;
  };
  products: ImageryProductRecord[];
}



