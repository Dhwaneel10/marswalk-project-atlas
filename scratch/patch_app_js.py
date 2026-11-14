path = "web/app.js"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add element references
old_fleet_elem = "  const tabFleetControl = document.getElementById('tabFleetControl');\n  const tabBtnFleetControl = document.getElementById('tabBtnFleetControl');"
new_fleet_elem = """  const tabFleetControl = document.getElementById('tabFleetControl');
  const tabBtnFleetControl = document.getElementById('tabBtnFleetControl');
  const tabMissionDesignStudio = document.getElementById('tabMissionDesignStudio');
  const tabBtnMissionDesignStudio = document.getElementById('tabBtnMissionDesignStudio');"""

if old_fleet_elem not in text:
    old_fleet_elem = old_fleet_elem.replace("\n", "\r\n")
    new_fleet_elem = new_fleet_elem.replace("\n", "\r\n")

assert old_fleet_elem in text, "old_fleet_elem not found"
text = text.replace(old_fleet_elem, new_fleet_elem, 1)

# 2. Update panels in switchInspectorTab
old_panels = "tabFleetControl, tabPlan,"
new_panels = "tabFleetControl, tabMissionDesignStudio, tabPlan,"
assert old_panels in text, "old_panels not found"
text = text.replace(old_panels, new_panels, 1)

# 3. Update cockpit-mode check
old_cockpit = "tabId === 'tabFleetControl'"
new_cockpit = "tabId === 'tabFleetControl' || tabId === 'tabMissionDesignStudio'"
assert old_cockpit in text, "old_cockpit not found"
text = text.replace(old_cockpit, new_cockpit, 1)

# 4. Add boot invocation
old_boot = "      initFleetControlEngine();"
new_boot = """      initFleetControlEngine();
      // Milestone 13K: Initialize Atlas Goal-Driven Mission Design Compiler
      initMissionDesignStudioEngine();
      if (params.get('tab') === 'design_studio' || params.get('tab') === 'compiler' || params.get('tab') === 'tabMissionDesignStudio') {
        switchInspectorTab('tabMissionDesignStudio');
      }"""

if old_boot not in text:
    old_boot = old_boot.replace("\n", "\r\n")
    new_boot = new_boot.replace("\n", "\r\n")

assert old_boot in text, "old_boot not found"
text = text.replace(old_boot, new_boot, 1)

# 5. Implementation of initMissionDesignStudioEngine
engine_code = """
  // ==============================================================================
  // MILESTONE 13K: ATLAS MISSION DESIGN STUDIO 2.0 UI ENGINE
  // ==============================================================================
  function initMissionDesignStudioEngine() {
    console.log('[MissionDesignStudio] Initializing Goal-Driven Mission Compiler UI Engine...');

    const btnSample = document.getElementById('btnCompilerSampleIntent');
    const btnValidate = document.getElementById('btnCompilerValidate');
    const btnCompile = document.getElementById('btnCompilerCompile');
    const btnBenchmark = document.getElementById('btnCompilerBenchmark');
    const btnPromote = document.getElementById('btnCompilerPromote');
    const btnTheater = document.getElementById('btnCompilerTheaterReplay');

    const briefInput = document.getElementById('compilerBriefInput');
    const presetSelect = document.getElementById('compilerBriefPresets');

    const sliderRovers = document.getElementById('compilerSliderRovers');
    const sliderSols = document.getElementById('compilerSliderSols');
    const sliderBattery = document.getElementById('compilerSliderBattery');
    const sliderRelays = document.getElementById('compilerSliderRelays');

    const lblRovers = document.getElementById('lblCompilerRoversCount');
    const lblSols = document.getElementById('lblCompilerDurationSols');
    const lblBattery = document.getElementById('lblCompilerBatteryReserve');
    const lblRelays = document.getElementById('lblCompilerRelayBudget');

    const validationPanel = document.getElementById('compilerValidationPanel');
    const validationBadge = document.getElementById('compilerValidationBadge');
    const validationSummary = document.getElementById('compilerValidationSummary');
    const validationIssues = document.getElementById('compilerValidationIssues');

    const candidatesPanel = document.getElementById('compilerCandidatesDeckPanel');
    const candidatesGrid = document.getElementById('compilerCandidatesGrid');
    const paretoCountBadge = document.getElementById('compilerParetoCountBadge');

    const taskGraphPanel = document.getElementById('compilerTaskGraphPanel');
    const dagSvg = document.getElementById('compilerDagSvg');
    const dagMetricsBadge = document.getElementById('compilerDagMetricsBadge');
    const taskDetailBox = document.getElementById('compilerTaskDetailBox');
    const taskDetailTitle = document.getElementById('compilerTaskDetailTitle');
    const taskDetailBody = document.getElementById('compilerTaskDetailBody');

    const tradeoffPanel = document.getElementById('compilerTradeoffPanel');
    const tradeoffSummaryText = document.getElementById('compilerTradeoffSummaryText');
    const deltaMetricsGrid = document.getElementById('compilerDeltaMetricsGrid');
    const selectedPostBadge = document.getElementById('compilerSelectedPostBadge');

    const debuggerPanel = document.getElementById('compilerDebuggerPanel');
    const failureChainList = document.getElementById('compilerFailureChainList');
    const relaxationList = document.getElementById('compilerRelaxationList');

    const benchmarkPanel = document.getElementById('compilerBenchmarkPanel');
    const benchmarkSummary = document.getElementById('compilerBenchmarkSummary');
    const benchmarkTable = document.getElementById('compilerBenchmarkTable');

    let currentIntent = null;
    let currentCompilation = null;
    let selectedCandidate = null;

    // Presets definition
    const PRESETS = {
      preset_jezero_recon: {
        brief: "Explore the western Jezero delta using two rovers over five sols. Prioritize geological characterization and mineralogical investigation. Preserve at least 20% of each rover's configured energy reserve. Deploy no more than two relays. Minimize data backlog and maximize valid science observations.",
        rovers: 2, sols: 5, battery: 20, relays: 2,
      },
      preset_distributed_3rover: {
        brief: "Conduct distributed multi-rover reconnaissance across western Jezero fan and delta remnant using three rovers over four sols. Maintain line-of-sight reachability >= 90%.",
        rovers: 3, sols: 4, battery: 20, relays: 2,
      },
      preset_resource_conservative: {
        brief: "Conservative exploration sortie with strict power management. Preserve at least 35% battery reserve margin on all units. Limit traverses to safe low-slope corridors.",
        rovers: 2, sols: 5, battery: 35, relays: 1,
      },
      preset_comms_focused: {
        brief: "High-continuity communications campaign with dedicated surface relays and mobile relay escort. Ensure zero signal blackouts during primary science dwell windows.",
        rovers: 3, sols: 5, battery: 20, relays: 2,
      }
    };

    // Sliders event listeners
    if (sliderRovers && lblRovers) {
      sliderRovers.addEventListener('input', (e) => {
        lblRovers.textContent = `${e.target.value} Rover${e.target.value > 1 ? 's' : ''}`;
      });
    }
    if (sliderSols && lblSols) {
      sliderSols.addEventListener('input', (e) => {
        lblSols.textContent = `${e.target.value} Sol${e.target.value > 1 ? 's' : ''}`;
      });
    }
    if (sliderBattery && lblBattery) {
      sliderBattery.addEventListener('input', (e) => {
        lblBattery.textContent = `${e.target.value}% SoC`;
      });
    }
    if (sliderRelays && lblRelays) {
      sliderRelays.addEventListener('input', (e) => {
        lblRelays.textContent = `${e.target.value} Relay${e.target.value > 1 ? 's' : ''}`;
      });
    }

    // Preset selector
    if (presetSelect && briefInput) {
      presetSelect.addEventListener('change', (e) => {
        const p = PRESETS[e.target.value];
        if (p) {
          briefInput.value = p.brief;
          if (sliderRovers) { sliderRovers.value = p.rovers; sliderRovers.dispatchEvent(new Event('input')); }
          if (sliderSols) { sliderSols.value = p.sols; sliderSols.dispatchEvent(new Event('input')); }
          if (sliderBattery) { sliderBattery.value = p.battery; sliderBattery.dispatchEvent(new Event('input')); }
          if (sliderRelays) { sliderRelays.value = p.relays; sliderRelays.dispatchEvent(new Event('input')); }
        }
      });
    }

    // Helper: Build current intent object
    function buildIntentFromUI() {
      const brief = briefInput ? briefInput.value : '';
      const roversCount = sliderRovers ? parseInt(sliderRovers.value) : 2;
      const solsCount = sliderSols ? parseInt(sliderSols.value) : 5;
      const batteryRes = sliderBattery ? parseFloat(sliderBattery.value) : 20.0;
      const relaysCount = sliderRelays ? parseInt(sliderRelays.value) : 2;

      const permitted = ['ATLAS_ROVER_A', 'ATLAS_ROVER_B', 'ATLAS_ROVER_C', 'ATLAS_ROVER_D'].slice(0, roversCount);

      return {
        intent_id: currentIntent ? currentIntent.intent_id : `intent_${Date.now()}`,
        name: currentIntent ? currentIntent.name : 'Western Jezero Delta Cooperative Geological Reconnaissance',
        description: 'Goal-driven multi-rover mission design.',
        campaign_id: 'cmp_jezero_delta_5sol',
        raw_natural_language_brief: brief,
        science: {
          primary_objectives: ['GEOLOGICAL_CHARACTERIZATION', 'MINERALOGICAL_INVESTIGATION', 'ELEMENTAL_CHEMISTRY'],
          mandatory_target_ids: ['TGT_HAWKSBILL_GAP', 'TGT_SKINNER_RIDGE'],
          preferred_target_ids: ['TGT_BELVA_CRATER', 'TGT_ENCHANTED_LAKE'],
          minimum_observations_count: 4,
          maximum_targets_limit: 6,
          required_instruments: ['PIXL', 'MASTCAM_Z'],
          minimum_science_utility_pts: 1200.0,
        },
        fleet: {
          maximum_rovers: roversCount,
          minimum_rovers: 1,
          permitted_rover_ids: permitted,
          allow_mobile_relay_role: roversCount >= 3,
          enforce_zero_energy_pooling: true,
        },
        geography: {
          region_id: 'JEZERO_WESTERN_DELTA',
          starting_location_rc: [128, 128],
          base_station_rc: [128, 128],
          spatial_proximity_margin_m: 40.0,
          maximum_slope_limit_deg: 25.0,
        },
        timeline: {
          maximum_sols: solsCount,
          preferred_sols: solsCount,
          minimum_sol_reserve_soc_pct: batteryRes,
          diurnal_recharge_enabled: true,
        },
        communications: {
          maximum_relays_deployable: relaysCount,
          minimum_geometric_reachability_pct: 85.0,
          enable_peer_mesh_forwarding: true,
        },
        resources: {
          minimum_battery_reserve_pct: batteryRes,
          maximum_flash_storage_utilization_pct: 85.0,
          max_acceptable_data_backlog_mb: 500.0,
          shared_downlink_bandwidth_mbps: 2.0,
        },
        preferences: {
          weight_science_utility: 0.40,
          weight_energy_conservation: 0.25,
          weight_traverse_efficiency: 0.15,
          weight_communications_continuity: 0.15,
          weight_duration_compression: 0.10,
          weight_infrastructure_minimization: 0.05,
          preferred_planning_mode: 'BALANCED',
        }
      };
    }

    // Action 1: Load Sample Intent
    if (btnSample) {
      btnSample.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/compiler/sample-intent');
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          currentIntent = data;
          if (briefInput) briefInput.value = data.raw_natural_language_brief || '';
          if (sliderRovers) { sliderRovers.value = data.fleet.maximum_rovers; sliderRovers.dispatchEvent(new Event('input')); }
          if (sliderSols) { sliderSols.value = data.timeline.maximum_sols; sliderSols.dispatchEvent(new Event('input')); }
          if (sliderBattery) { sliderBattery.value = data.resources.minimum_battery_reserve_pct; sliderBattery.dispatchEvent(new Event('input')); }
          if (sliderRelays) { sliderRelays.value = data.communications.maximum_relays_deployable; sliderRelays.dispatchEvent(new Event('input')); }
          
          if (validationPanel) validationPanel.style.display = 'block';
          if (validationBadge) {
            validationBadge.textContent = 'SAMPLE LOADED';
            validationBadge.style.background = 'rgba(56,189,248,0.2)';
            validationBadge.style.color = '#38bdf8';
          }
          if (validationSummary) validationSummary.textContent = `Loaded '${data.name}' with SHA-256 fingerprint: ${data.fingerprint.substring(0, 16)}...`;
        } catch (err) {
          console.error('[MissionDesignStudio] Failed to load sample intent:', err);
        }
      });
    }

    // Action 2: Validate Intent
    if (btnValidate) {
      btnValidate.addEventListener('click', async () => {
        try {
          const intent = buildIntentFromUI();
          const res = await fetch('/api/compiler/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intent })
          });
          const report = await res.json();
          renderValidationReport(report);
        } catch (err) {
          console.error('[MissionDesignStudio] Validation request failed:', err);
        }
      });
    }

    function renderValidationReport(report) {
      if (!validationPanel) return;
      validationPanel.style.display = 'block';

      const isOk = report.verdict === 'VALID' || report.verdict === 'VALID_WITH_WARNINGS';
      if (validationBadge) {
        validationBadge.textContent = report.verdict;
        validationBadge.style.background = isOk ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)';
        validationBadge.style.color = isOk ? '#10b981' : '#f43f5e';
      }
      if (validationSummary) {
        validationSummary.textContent = `Verdict: ${report.verdict} | Errors: ${report.total_errors} | Warnings: ${report.total_warnings} | Infos: ${report.total_infos}`;
      }

      if (validationIssues) {
        if (!report.issues || report.issues.length === 0) {
          validationIssues.innerHTML = '<div style="color:#10b981;">&#10004; Zero physical constraint violations detected. Intent conforms to Jezero DTM and rover instrument envelopes.</div>';
        } else {
          validationIssues.innerHTML = report.issues.map(iss => `
            <div style="margin-bottom:4px; padding:4px 6px; background:rgba(0,0,0,0.3); border-left:3px solid ${iss.severity === 'ERROR' ? '#f43f5e' : '#f59e0b'};">
              <span style="font-weight:700; color:${iss.severity === 'ERROR' ? '#f43f5e' : '#f59e0b'};">[${iss.issue_code}]</span>
              <span style="color:#cbd5e1;"> ${iss.message}</span>
              <div style="color:#94a3b8; font-size:9px; margin-top:2px;">&#8627; Suggestion: ${iss.suggested_resolution}</div>
            </div>
          `).join('');
        }
      }
    }

    // Action 3: Compile Campaign
    if (btnCompile) {
      btnCompile.addEventListener('click', async () => {
        try {
          btnCompile.textContent = '⚡ COMPILING...';
          const intent = buildIntentFromUI();
          const res = await fetch('/api/compiler/compile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intent })
          });
          const comp = await res.json();
          currentCompilation = comp;
          renderCompilation(comp);
        } catch (err) {
          console.error('[MissionDesignStudio] Compilation failed:', err);
        } finally {
          btnCompile.textContent = '⚡ COMPILE CAMPAIGN';
        }
      });
    }

    function renderCompilation(comp) {
      if (!comp || !comp.candidates) return;

      // Update candidates deck
      if (candidatesPanel) candidatesPanel.style.display = 'block';
      if (paretoCountBadge) paretoCountBadge.textContent = `${comp.pareto_frontier_ids ? comp.pareto_frontier_ids.length : 6} PARETO CHAMPIONS`;

      // Render 8 candidate cards
      if (candidatesGrid) {
        candidatesGrid.innerHTML = comp.candidates.map(cand => {
          const isPareto = cand.is_pareto_champion;
          const isRec = cand.candidate_id === comp.recommended_candidate_id;
          return `
            <div class="compiler-candidate-card ${isRec ? 'active-champion' : ''}" data-cand-id="${cand.candidate_id}">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-weight:700; font-size:11px; color:#38bdf8;">${cand.posture}</span>
                ${isPareto ? '<span class="compiler-pareto-tag">PARETO</span>' : ''}
              </div>
              <div style="font-size:10px; color:#f1f5f9; font-weight:600; margin-bottom:4px;">${cand.name}</div>
              
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-size:9px; color:#94a3b8; margin-bottom:6px;">
                <div>Science: <span style="color:#10b981; font-weight:700;">${cand.total_science_utility} pts</span></div>
                <div>Distance: <span style="color:#f8fafc;">${(cand.total_distance_m / 1000).toFixed(1)} km</span></div>
                <div>Min SoC: <span style="color:#38bdf8; font-weight:700;">${cand.min_battery_reserve_pct}%</span></div>
                <div>Reachability: <span style="color:#f59e0b;">${cand.comms_reachability_pct}%</span></div>
                <div>Duration: <span style="color:#cbd5e1;">${cand.duration_sols} Sols</span></div>
                <div>Relays: <span style="color:#a855f7;">${cand.relays_deployed_count}</span></div>
              </div>

              <div style="background:rgba(255,255,255,0.08); border-radius:3px; height:4px; overflow:hidden;">
                <div style="width:${Math.min(100, (cand.scores.composite_score || 0.8) * 100)}%; background:#38bdf8; height:100%;"></div>
              </div>
            </div>
          `;
        }).join('');

        // Card click handler
        candidatesGrid.querySelectorAll('.compiler-candidate-card').forEach(card => {
          card.addEventListener('click', () => {
            candidatesGrid.querySelectorAll('.compiler-candidate-card').forEach(c => c.classList.remove('active-champion'));
            card.classList.add('active-champion');
            const candId = card.dataset.candId;
            selectCandidate(candId);
          });
        });
      }

      // Default select recommended candidate
      const recId = comp.recommended_candidate_id || (comp.candidates[0] ? comp.candidates[0].candidate_id : null);
      if (recId) selectCandidate(recId);
    }

    function selectCandidate(candId) {
      if (!currentCompilation) return;
      const cand = currentCompilation.candidates.find(c => c.candidate_id === candId) || currentCompilation.candidates[0];
      selectedCandidate = cand;

      // Render Task Graph
      renderTaskGraph(cand.task_graph);

      // Render Trade-off Delta Scorecard
      renderTradeoffScorecard(cand);

      // Render Debugger if infeasible
      if (!cand.constraint_report || !cand.constraint_report.is_feasible) {
        renderDebugger(cand);
      } else if (debuggerPanel) {
        debuggerPanel.style.display = 'none';
      }
    }

    // Render SVG DAG
    function renderTaskGraph(graph) {
      if (!taskGraphPanel || !dagSvg || !graph || !graph.tasks) return;
      taskGraphPanel.style.display = 'block';

      const tasksList = Object.values(graph.tasks);
      if (dagMetricsBadge) dagMetricsBadge.textContent = `${tasksList.length} Tasks | ${graph.edges ? graph.edges.length : 0} Edges`;

      // Layout nodes horizontally across sols
      const solGroups = {};
      tasksList.forEach(t => {
        const sol = t.sol_index || 1;
        if (!solGroups[sol]) solGroups[sol] = [];
        solGroups[sol].push(t);
      });

      const solsCount = Math.max(1, Object.keys(solGroups).length);
      const svgWidth = Math.max(900, solsCount * 180 + 100);
      dagSvg.setAttribute('width', svgWidth);
      dagSvg.setAttribute('height', 200);

      // Color taxonomy per task type
      const TYPE_COLORS = {
        TRAVERSE: '#38bdf8',
        REACH_TARGET: '#0284c7',
        PREPARE_INSTRUMENT: '#eab308',
        OBSERVE: '#10b981',
        DEPLOY_RELAY: '#a855f7',
        SIMULATED_DATA_TRANSFER: '#14b8a6',
        CAMPAIGN_CHECKPOINT: '#f59e0b',
        STANDBY: '#64748b',
      };

      const nodeCoords = {};
      let svgHtml = '';

      // Compute node coordinates
      Object.keys(solGroups).sort((a,b) => parseInt(a) - parseInt(b)).forEach((solStr, solIdx) => {
        const sol = parseInt(solStr);
        const colTasks = solGroups[sol];
        const x = 60 + solIdx * 180;

        colTasks.forEach((task, rowIdx) => {
          const y = 30 + (rowIdx % 5) * 35;
          nodeCoords[task.task_id] = { x, y, task };
        });
      });

      // Draw Edges
      if (graph.edges) {
        graph.edges.forEach(([u, v]) => {
          const p1 = nodeCoords[u];
          const p2 = nodeCoords[v];
          if (p1 && p2) {
            const isCrit = graph.critical_path && graph.critical_path.includes(u) && graph.critical_path.includes(v);
            svgHtml += `
              <line x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}" class="compiler-dag-link ${isCrit ? 'critical' : ''}" />
            `;
          }
        });
      }

      // Draw Nodes
      Object.values(nodeCoords).forEach(({ x, y, task }) => {
        const color = TYPE_COLORS[task.task_type] || '#38bdf8';
        const isCrit = graph.critical_path && graph.critical_path.includes(task.task_id);
        svgHtml += `
          <g class="compiler-dag-node" data-task-id="${task.task_id}" transform="translate(${x}, ${y})">
            <circle r="${isCrit ? 9 : 7}" fill="${color}" stroke="${isCrit ? '#f59e0b' : '#ffffff'}" stroke-width="${isCrit ? 2.5 : 1}" opacity="0.9" />
            <text x="12" y="3" fill="#cbd5e1" font-size="8" font-family="monospace">${task.task_type.substring(0, 8)}</text>
          </g>
        `;
      });

      dagSvg.innerHTML = svgHtml;

      // Bind node clicks
      dagSvg.querySelectorAll('.compiler-dag-node').forEach(node => {
        node.addEventListener('click', () => {
          const tId = node.dataset.taskId;
          const task = graph.tasks[tId];
          if (task && taskDetailBox && taskDetailTitle && taskDetailBody) {
            taskDetailBox.style.display = 'block';
            taskDetailTitle.textContent = `${task.task_type}: ${task.name} (${task.assigned_rover_id || 'FLEET SYNC'})`;
            taskDetailBody.innerHTML = `
              <div><strong>Sol:</strong> ${task.sol_index} | <strong>Duration:</strong> ${task.estimated_duration_s}s | <strong>Energy:</strong> ${task.estimated_energy_wh} Wh | <strong>Data:</strong> ${task.estimated_data_mb} MB</div>
              <div><strong>Prerequisites:</strong> ${task.prerequisite_task_ids && task.prerequisite_task_ids.length > 0 ? task.prerequisite_task_ids.join(', ') : 'None (Root Node)'}</div>
            `;
          }
        });
      });
    }

    // Render Tradeoff Scorecard
    function renderTradeoffScorecard(cand) {
      if (!tradeoffPanel) return;
      tradeoffPanel.style.display = 'block';

      if (selectedPostBadge) selectedPostBadge.textContent = cand.posture;
      if (tradeoffSummaryText) tradeoffSummaryText.textContent = cand.selection_rationale || 'Balanced optimization prioritizing mission durability.';

      if (deltaMetricsGrid) {
        deltaMetricsGrid.innerHTML = `
          <div class="compiler-delta-card">
            <div style="color:#94a3b8; font-size:9px;">SCIENCE UTILITY</div>
            <div class="compiler-delta-val positive">${cand.total_science_utility} pts</div>
          </div>
          <div class="compiler-delta-card">
            <div style="color:#94a3b8; font-size:9px;">TRAVERSE DIST</div>
            <div class="compiler-delta-val">${(cand.total_distance_m / 1000).toFixed(1)} km</div>
          </div>
          <div class="compiler-delta-card">
            <div style="color:#94a3b8; font-size:9px;">TOTAL ENERGY</div>
            <div class="compiler-delta-val">${cand.total_energy_wh.toFixed(1)} Wh</div>
          </div>
          <div class="compiler-delta-card">
            <div style="color:#94a3b8; font-size:9px;">MIN BATTERY SOC</div>
            <div class="compiler-delta-val positive">${cand.min_battery_reserve_pct}%</div>
          </div>
          <div class="compiler-delta-card">
            <div style="color:#94a3b8; font-size:9px;">COMMS REACHABILITY</div>
            <div class="compiler-delta-val positive">${cand.comms_reachability_pct}%</div>
          </div>
          <div class="compiler-delta-card">
            <div style="color:#94a3b8; font-size:9px;">CAMPAIGN SOLS</div>
            <div class="compiler-delta-val">${cand.duration_sols} Sols</div>
          </div>
        `;
      }
    }

    // Render Debugger
    function renderDebugger(cand) {
      if (!debuggerPanel) return;
      debuggerPanel.style.display = 'block';

      const rep = cand.constraint_report;
      const cores = rep ? rep.conflict_cores : [];

      if (failureChainList) {
        if (!cores || cores.length === 0) {
          failureChainList.innerHTML = '<div style="color:#f43f5e;">Constraint violations detected. Reviewing conflict core...</div>';
        } else {
          failureChainList.innerHTML = cores.map(c => `
            <div style="margin-bottom:4px; padding:4px 6px; background:rgba(244,63,94,0.1); border-left:3px solid #f43f5e;">
              <strong>${c.summary}</strong>: ${c.root_cause_explanation}
            </div>
          `).join('');
        }
      }

      if (relaxationList) {
        relaxationList.innerHTML = `
          <button class="btn-secondary" style="font-size:9px; padding:3px 6px; margin-right:4px; margin-bottom:4px;" onclick="window.Atlas.compiler.applyQuickRelaxation('soc', 18)">Relax Battery Reserve to 18%</button>
          <button class="btn-secondary" style="font-size:9px; padding:3px 6px; margin-right:4px; margin-bottom:4px;" onclick="window.Atlas.compiler.applyQuickRelaxation('sols', 6)">Extend to 6 Sols</button>
          <button class="btn-secondary" style="font-size:9px; padding:3px 6px; margin-bottom:4px;" onclick="window.Atlas.compiler.applyQuickRelaxation('rovers', 3)">Add 3rd Rover</button>
        `;
      }
    }

    // Action 4: Benchmark Lab
    if (btnBenchmark) {
      btnBenchmark.addEventListener('click', async () => {
        try {
          btnBenchmark.textContent = '⏳ RUNNING...';
          const res = await fetch('/api/compiler/benchmark');
          const data = await res.json();
          renderBenchmark(data);
        } catch (err) {
          console.error('[MissionDesignStudio] Benchmark failed:', err);
        } finally {
          btnBenchmark.textContent = '📊 BENCHMARK LAB';
        }
      });
    }

    function renderBenchmark(data) {
      if (!benchmarkPanel || !data || !data.summary) return;
      benchmarkPanel.style.display = 'block';

      const s = data.summary;
      if (benchmarkSummary) {
        benchmarkSummary.textContent = `Executed ${s.total_scenarios} benchmark campaigns (A through F) in ${s.mean_compiler_latency_ms}ms mean latency. Mean Utility Gain: +${s.mean_utility_gain_pct}%.`;
      }

      if (benchmarkTable && data.runs) {
        benchmarkTable.innerHTML = `
          <table style="width:100%; border-collapse:collapse; font-size:9px;">
            <tr style="border-bottom:1px solid rgba(255,255,255,0.2); color:#94a3b8;">
              <th style="text-align:left; padding:2px;">SCENARIO</th>
              <th style="padding:2px;">COMPILER</th>
              <th style="padding:2px;">UTILITY</th>
              <th style="padding:2px;">PARETO</th>
              <th style="padding:2px;">GAIN</th>
            </tr>
            ${data.runs.map(r => `
              <tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
                <td style="padding:2px; font-weight:700; color:#38bdf8;">${r.scenario_id}: ${r.name.substring(0, 24)}</td>
                <td style="padding:2px; text-align:center; color:${r.compiler_feasible ? '#10b981' : '#f43f5e'};">${r.compiler_feasible ? 'PASS' : 'FAIL (CORE)'}</td>
                <td style="padding:2px; text-align:center; color:#f8fafc;">${r.compiler_science_utility} pts</td>
                <td style="padding:2px; text-align:center; color:#10b981;">${r.compiler_pareto_count}</td>
                <td style="padding:2px; text-align:center; color:#10b981;">+${r.utility_gain_pct}%</td>
              </tr>
            `).join('')}
          </table>
        `;
      }
    }

    // Action 5: Promote
    if (btnPromote) {
      btnPromote.addEventListener('click', async () => {
        if (!selectedCandidate) return;
        try {
          const res = await fetch('/api/compiler/promote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              compilation_id: currentCompilation ? currentCompilation.compilation_id : null,
              candidate_id: selectedCandidate.candidate_id,
            })
          });
          const data = await res.json();
          alert(`Plan '${selectedCandidate.name}' successfully promoted to active operational fleet campaign!`);
        } catch (err) {
          console.error('[MissionDesignStudio] Promotion failed:', err);
        }
      });
    }

    // Action 6: 3D Theater Replay
    if (btnTheater) {
      btnTheater.addEventListener('click', () => {
        if (selectedCandidate && window.render3DFleetTrajectories) {
          window.render3DFleetTrajectories();
          switchInspectorTab('tabMissionControl');
        } else {
          switchInspectorTab('tabMissionControl');
        }
      });
    }

    // Automation API Export
    const compilerApi = {
      loadSample: () => btnSample && btnSample.click(),
      validate: () => btnValidate && btnValidate.click(),
      compile: () => btnCompile && btnCompile.click(),
      benchmark: () => btnBenchmark && btnBenchmark.click(),
      selectCandidate: (id) => selectCandidate(id),
      applyQuickRelaxation: (type, val) => {
        if (type === 'soc' && sliderBattery) { sliderBattery.value = val; sliderBattery.dispatchEvent(new Event('input')); }
        if (type === 'sols' && sliderSols) { sliderSols.value = val; sliderSols.dispatchEvent(new Event('input')); }
        if (type === 'rovers' && sliderRovers) { sliderRovers.value = val; sliderRovers.dispatchEvent(new Event('input')); }
        if (btnCompile) btnCompile.click();
      },
      getCurrentCompilation: () => currentCompilation,
      getSelectedCandidate: () => selectedCandidate,
    };

    if (!window.Atlas) window.Atlas = {};
    window.Atlas.compiler = compilerApi;
    if (window.__atlas) window.__atlas.compiler = compilerApi;
  }
"""

# Append before the last })();
old_end = "})();"
assert old_end in text, "old_end not found"
text = text[:text.rfind(old_end)] + engine_code + "\n})();"

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched web/app.js with initMissionDesignStudioEngine!")
