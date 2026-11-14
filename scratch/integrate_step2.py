"""
Step 2 integration for src/marswalk/core/joint_mission_planner.py:
- Updates evaluate_traverse_connectivity_with_relays
- Updates optimize_joint_mission
- Updates evaluate_joint_mission
"""

with open("src/marswalk/core/joint_mission_planner.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update signature of evaluate_traverse_connectivity_with_relays
old_sig = '''def evaluate_traverse_connectivity_with_relays(
    traverse: CandidateTraverse,
    base_node: RelayNode,
    deployed_relays: List[RelayNode],
    terrain: TerrainGrid,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_antenna_h: float = 2.5,
    sampling_interval_s: float = 10.0,
) -> Tuple[JointMissionMetrics, Dict[str, Any], List[Dict[str, Any]]]:'''

new_sig = '''def evaluate_traverse_connectivity_with_relays(
    traverse: CandidateTraverse,
    base_node: RelayNode,
    deployed_relays: List[RelayNode],
    terrain: TerrainGrid,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_antenna_h: float = 2.5,
    sampling_interval_s: float = 10.0,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    relay_resource_config: Optional[Union[RelayResourceConfig, Dict[str, Any]]] = None,
    waypoints: Optional[List[ScienceWaypoint]] = None,
    evaluate_resources: bool = True,
    return_ledger: bool = False,
) -> Union[Tuple[JointMissionMetrics, Dict[str, Any], List[Dict[str, Any]]], Tuple[JointMissionMetrics, Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]]:'''

assert old_sig in code, "Failed to find old signature"
code = code.replace(old_sig, new_sig, 1)

# 2. Update body of evaluate_traverse_connectivity_with_relays right before metrics creation
old_metrics_creation = '''    metrics = JointMissionMetrics(
        distance_m=total_dist,
        travel_time_s=total_dur,
        mean_slope_deg=traverse.mean_slope_deg,
        max_slope_deg=traverse.max_slope_deg,
        elevation_gain_m=traverse.elevation_gain_m,
        elevation_loss_m=traverse.elevation_loss_m,
        terrain_effort_m=traverse.terrain_effort_m,
        connected_distance_m=conn_dist_m,
        gap_distance_m=gap_dist_m,
        gap_duration_s=gap_dur_s,
        availability_pct=avail_pct,
        max_gap_duration_s=max_gap_s,
        gap_count=gap_cnt,
        relay_count=len(deployed_relays),
        mean_hops=mean_hops,
        max_hops=max_hops,
        critical_bridges=len(bridges),
    )

    return metrics, summary, gap_intervals'''

new_metrics_creation = '''    # Milestone 13F Resource Evaluation
    ledger_dict: Dict[str, Any] = {}
    e_tot_wh = 0.0
    e_drv_wh = 0.0
    e_idl_wh = 0.0
    e_com_wh = 0.0
    e_sci_wh = 0.0
    fin_soc = 100.0
    min_soc = 100.0
    res_feas = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"

    if evaluate_resources:
        try:
            if isinstance(rover_resource_config, dict):
                valid_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
                rcfg = RoverResourceConfig(**{k: v for k, v in rover_resource_config.items() if k in valid_keys})
            elif isinstance(rover_resource_config, RoverResourceConfig):
                rcfg = rover_resource_config
            else:
                rcfg = RoverResourceConfig()

            if isinstance(relay_resource_config, dict):
                valid_r_keys = {f.name for f in RelayResourceConfig.__dataclass_fields__.values()}
                rly_cfg = RelayResourceConfig(**{k: v for k, v in relay_resource_config.items() if k in valid_r_keys})
            elif isinstance(relay_resource_config, RelayResourceConfig):
                rly_cfg = relay_resource_config
            else:
                rly_cfg = RelayResourceConfig()

            relays_for_ledger = [
                {"node_id": r.node_id, "rc": (r.rc[0], r.rc[1])}
                for r in deployed_relays
            ]
            wps_for_ledger = [
                {"name": wp.name, "rc": (wp.rc[0], wp.rc[1])}
                for wp in (waypoints or [])
            ]

            active_tx_map: Dict[str, float] = {}
            checkpoints = timeline_res.get("checkpoints", [])
            cp_dt = total_dur / max(len(checkpoints), 1)
            for cp in checkpoints:
                path_nodes = cp.get("active_path", [])
                for r in deployed_relays:
                    if r.node_id in path_nodes:
                        active_tx_map[r.node_id] = active_tx_map.get(r.node_id, 0.0) + cp_dt

            ledger = evaluate_mission_resource_ledger(
                path_rc=path,
                elevation_grid=terrain.elevation,
                slope_grid=terrain.slope_deg,
                invalid_mask=terrain.invalid_mask,
                ground_dx_m=dx,
                ground_dy_m=dy,
                rover_config=rcfg,
                relay_config=rly_cfg,
                relays_deployed=relays_for_ledger,
                intermediate_waypoints=wps_for_ledger,
                active_relay_tx_times_s=active_tx_map,
            )
            ledger_dict = ledger.to_dict()
            traverse.resource_summary = ledger_dict
            e_tot_wh = ledger.total_mission_energy_wh
            e_drv_wh = joules_to_wh(ledger.total_mobility_energy_j)
            e_idl_wh = joules_to_wh(ledger.total_electrical_energy_j)
            e_com_wh = joules_to_wh(ledger.total_relay_energy_j)
            fin_soc = ledger.final_battery_soc_pct
            min_soc = ledger.min_battery_soc_pct
            res_feas = ledger.feasibility_classification.value
        except Exception as err:
            res_feas = "UNKNOWN_RESOURCE_FEASIBILITY"
            ledger_dict = {"error": str(err), "feasibility_classification": res_feas}

    metrics = JointMissionMetrics(
        distance_m=total_dist,
        travel_time_s=total_dur,
        mean_slope_deg=traverse.mean_slope_deg,
        max_slope_deg=traverse.max_slope_deg,
        elevation_gain_m=traverse.elevation_gain_m,
        elevation_loss_m=traverse.elevation_loss_m,
        terrain_effort_m=traverse.terrain_effort_m,
        connected_distance_m=conn_dist_m,
        gap_distance_m=gap_dist_m,
        gap_duration_s=gap_dur_s,
        availability_pct=avail_pct,
        max_gap_duration_s=max_gap_s,
        gap_count=gap_cnt,
        relay_count=len(deployed_relays),
        mean_hops=mean_hops,
        max_hops=max_hops,
        critical_bridges=len(bridges),
        energy_total_wh=e_tot_wh,
        energy_drive_wh=e_drv_wh,
        energy_idle_wh=e_idl_wh,
        energy_comms_wh=e_com_wh,
        energy_science_wh=e_sci_wh,
        final_soc_pct=fin_soc,
        min_soc_pct=min_soc,
        resource_feasibility=res_feas,
    )

    if return_ledger:
        return metrics, summary, gap_intervals, ledger_dict
    return metrics, summary, gap_intervals'''

assert old_metrics_creation in code, "Failed to find old metrics creation"
code = code.replace(old_metrics_creation, new_metrics_creation, 1)

# 3. Update optimize_joint_mission signature
old_opt_sig = '''def optimize_joint_mission(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    base_station: Dict[str, Any],
    waypoints: Optional[List[ScienceWaypoint]] = None,
    relay_budget: int = 2,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_antenna_h: float = 2.5,
    base_antenna_h: float = 10.0,
    relay_antenna_h: float = 10.0,
    objective_profile: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None,
    max_route_candidates: int = 5,
) -> JointMissionOptimizationResult:'''

new_opt_sig = '''def optimize_joint_mission(
    start_rc: Tuple[int, int],
    goal_rc: Tuple[int, int],
    terrain: TerrainGrid,
    base_station: Dict[str, Any],
    waypoints: Optional[List[ScienceWaypoint]] = None,
    relay_budget: int = 2,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_antenna_h: float = 2.5,
    base_antenna_h: float = 10.0,
    relay_antenna_h: float = 10.0,
    objective_profile: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None,
    max_route_candidates: int = 5,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    relay_resource_config: Optional[Union[RelayResourceConfig, Dict[str, Any]]] = None,
    evaluate_resources: bool = True,
) -> JointMissionOptimizationResult:'''

assert old_opt_sig in code, "Failed to find old optimize_joint_mission signature"
code = code.replace(old_opt_sig, new_opt_sig, 1)

# 4. Update call inside optimize_joint_mission
old_opt_call = '''            metrics, t_summary, t_gaps = evaluate_traverse_connectivity_with_relays(
                traverse=trv,
                base_node=base_node,
                deployed_relays=deployed_relays,
                terrain=terrain,
                max_direct_range_m=max_direct_range_m,
                max_relay_range_m=max_relay_range_m,
                rover_antenna_h=rover_antenna_h,
            )'''

new_opt_call = '''            eval_ret = evaluate_traverse_connectivity_with_relays(
                traverse=trv,
                base_node=base_node,
                deployed_relays=deployed_relays,
                terrain=terrain,
                max_direct_range_m=max_direct_range_m,
                max_relay_range_m=max_relay_range_m,
                rover_antenna_h=rover_antenna_h,
                rover_resource_config=rover_resource_config,
                relay_resource_config=relay_resource_config,
                waypoints=waypoints,
                evaluate_resources=evaluate_resources,
                return_ledger=True,
            )
            metrics, t_summary, t_gaps, ledger_data = eval_ret'''

assert old_opt_call in code, "Failed to find old opt call"
code = code.replace(old_opt_call, new_opt_call, 1)

# Update jmc creation inside optimize_joint_mission
old_jmc_creation = '''            jmc = JointMissionConfiguration(
                configuration_id=c_id,
                traverse=trv,
                relays=r_config,
                metrics=metrics,
                timeline_summary=t_summary,
                timeline_gap_intervals=t_gaps,
                is_pareto_optimal=False,
                constraint_violations=[],
            )'''

new_jmc_creation = '''            jmc_violations = list(ledger_data.get("constraint_violations", [])) if ledger_data else []
            jmc = JointMissionConfiguration(
                configuration_id=c_id,
                traverse=trv,
                relays=r_config,
                metrics=metrics,
                timeline_summary=t_summary,
                timeline_gap_intervals=t_gaps,
                is_pareto_optimal=False,
                constraint_violations=jmc_violations,
                resource_ledger=ledger_data if ledger_data else None,
            )'''

assert old_jmc_creation in code, "Failed to find old jmc creation"
code = code.replace(old_jmc_creation, new_jmc_creation, 1)

# 5. Add sensitivity analysis and resource_sensitivity to JointMissionOptimizationResult
old_opt_return = '''    return JointMissionOptimizationResult(
        result_id=result_id,
        timestamp_utc=time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        sha256_fingerprint=sha256_hash,
        input_parameters={
            "start_rc": start_rc,
            "goal_rc": goal_rc,
            "base_station": base_station,
            "relay_budget": relay_budget,
            "max_direct_range_m": max_direct_range_m,
            "max_relay_range_m": max_relay_range_m,
            "rover_antenna_h": rover_antenna_h,
            "objective_profile": objective_profile,
        },
        candidate_traverses=candidate_traverses,
        candidate_relay_pool=candidate_promontories,
        all_configurations=all_configurations,
        pareto_frontier=pareto_frontier,
        recommended_configuration=recommended,
        decision_explanation=explanation,
        search_bounds={
            "candidate_traverses_generated": len(candidate_traverses),
            "promontory_candidates_screened": len(candidate_promontories),
            "configurations_evaluated": len(all_configurations),
            "pareto_configurations_count": len(pareto_frontier),
            "execution_runtime_ms": round(elapsed_ms, 2),
        },
        provenance={
            "terrain_dataset": "USGS_CTX_DTM_JEZERO_20M",
            "doi": "10.5066/P906QQT8",
            "planetary_datum": "IAU 2000 Mars Spheroid (R=3,396,190m)",
            "elevation_interpolation": "Bilinear sub-grid continuous with strict NoData sentinel rejection",
        },
    )'''

new_opt_return = '''    # Milestone 13F: Resource Sensitivity Analysis for recommended route
    res_sens_dict = None
    if evaluate_resources and recommended.traverse.path_rc:
        try:
            if isinstance(rover_resource_config, dict):
                valid_keys = {f.name for f in RoverResourceConfig.__dataclass_fields__.values()}
                rcfg_sens = RoverResourceConfig(**{k: v for k, v in rover_resource_config.items() if k in valid_keys})
            elif isinstance(rover_resource_config, RoverResourceConfig):
                rcfg_sens = rover_resource_config
            else:
                rcfg_sens = RoverResourceConfig()

            sens_res = evaluate_resource_sensitivity(
                path_rc=recommended.traverse.path_rc,
                elevation_grid=terrain.elevation,
                slope_grid=terrain.slope_deg,
                invalid_mask=terrain.invalid_mask,
                ground_dx_m=dx,
                ground_dy_m=dy,
                rover_config=rcfg_sens,
            )
            res_sens_dict = sens_res.to_dict()
        except Exception as e:
            res_sens_dict = {"error": str(e)}

    return JointMissionOptimizationResult(
        result_id=result_id,
        timestamp_utc=time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        sha256_fingerprint=sha256_hash,
        input_parameters={
            "start_rc": start_rc,
            "goal_rc": goal_rc,
            "base_station": base_station,
            "relay_budget": relay_budget,
            "max_direct_range_m": max_direct_range_m,
            "max_relay_range_m": max_relay_range_m,
            "rover_antenna_h": rover_antenna_h,
            "objective_profile": objective_profile,
        },
        candidate_traverses=candidate_traverses,
        candidate_relay_pool=candidate_promontories,
        all_configurations=all_configurations,
        pareto_frontier=pareto_frontier,
        recommended_configuration=recommended,
        decision_explanation=explanation,
        search_bounds={
            "candidate_traverses_generated": len(candidate_traverses),
            "promontory_candidates_screened": len(candidate_promontories),
            "configurations_evaluated": len(all_configurations),
            "pareto_configurations_count": len(pareto_frontier),
            "execution_runtime_ms": round(elapsed_ms, 2),
        },
        provenance={
            "terrain_dataset": "USGS_CTX_DTM_JEZERO_20M",
            "doi": "10.5066/P906QQT8",
            "planetary_datum": "IAU 2000 Mars Spheroid (R=3,396,190m)",
            "elevation_interpolation": "Bilinear sub-grid continuous with strict NoData sentinel rejection",
        },
        resource_sensitivity=res_sens_dict,
    )'''

assert old_opt_return in code, "Failed to find old opt return"
code = code.replace(old_opt_return, new_opt_return, 1)

# 6. Update evaluate_joint_mission
old_eval_sig = '''def evaluate_joint_mission(
    traverse_path: List[Tuple[int, int]],
    terrain: TerrainGrid,
    base_station: Dict[str, Any],
    deployed_relays: Optional[List[Dict[str, Any]]] = None,
    rover_antenna_h: float = 2.5,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
) -> JointMissionConfiguration:'''

new_eval_sig = '''def evaluate_joint_mission(
    traverse_path: List[Tuple[int, int]],
    terrain: TerrainGrid,
    base_station: Dict[str, Any],
    deployed_relays: Optional[List[Dict[str, Any]]] = None,
    rover_antenna_h: float = 2.5,
    max_direct_range_m: float = 2500.0,
    max_relay_range_m: float = 5000.0,
    rover_resource_config: Optional[Union[RoverResourceConfig, Dict[str, Any]]] = None,
    relay_resource_config: Optional[Union[RelayResourceConfig, Dict[str, Any]]] = None,
    evaluate_resources: bool = True,
) -> JointMissionConfiguration:'''

assert old_eval_sig in code, "Failed to find old eval signature"
code = code.replace(old_eval_sig, new_eval_sig, 1)

old_eval_call = '''    metrics, t_summary, t_gaps = evaluate_traverse_connectivity_with_relays(
        traverse=trv,
        base_node=base_node,
        deployed_relays=relay_nodes,
        terrain=terrain,
        max_direct_range_m=max_direct_range_m,
        max_relay_range_m=max_relay_range_m,
        rover_antenna_h=rover_antenna_h,
    )'''

new_eval_call = '''    eval_res = evaluate_traverse_connectivity_with_relays(
        traverse=trv,
        base_node=base_node,
        deployed_relays=relay_nodes,
        terrain=terrain,
        max_direct_range_m=max_direct_range_m,
        max_relay_range_m=max_relay_range_m,
        rover_antenna_h=rover_antenna_h,
        rover_resource_config=rover_resource_config,
        relay_resource_config=relay_resource_config,
        evaluate_resources=evaluate_resources,
        return_ledger=True,
    )
    metrics, t_summary, t_gaps, eval_ledger = eval_res'''

assert old_eval_call in code, "Failed to find old eval call"
code = code.replace(old_eval_call, new_eval_call, 1)

old_eval_return = '''    return JointMissionConfiguration(
        configuration_id="USER_EVALUATION",
        traverse=trv,
        relays=r_config,
        metrics=metrics,
        timeline_summary=t_summary,
        timeline_gap_intervals=t_gaps,
        is_pareto_optimal=True,
        constraint_violations=[],
        recommendation_tier="EVALUATED_USER_CONFIGURATION",
    )'''

new_eval_return = '''    eval_violations = list(eval_ledger.get("constraint_violations", [])) if eval_ledger else []
    return JointMissionConfiguration(
        configuration_id="USER_EVALUATION",
        traverse=trv,
        relays=r_config,
        metrics=metrics,
        timeline_summary=t_summary,
        timeline_gap_intervals=t_gaps,
        is_pareto_optimal=True,
        constraint_violations=eval_violations,
        recommendation_tier="EVALUATED_USER_CONFIGURATION",
        resource_ledger=eval_ledger if eval_ledger else None,
    )'''

assert old_eval_return in code, "Failed to find old eval return"
code = code.replace(old_eval_return, new_eval_return, 1)

with open("src/marswalk/core/joint_mission_planner.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Step 2 integration complete.")
