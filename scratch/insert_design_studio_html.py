path = "web/index.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add tab button
old_button = '<button class="inspector-tab" data-tab="tabFleetControl" id="tabBtnFleetControl" title="Atlas Fleet Intelligence: Multi-Rover Operations, Cooperative Traversal &amp; Distributed Science">&#128741; Fleet Control</button>'
new_button = old_button + '\n        <button class="inspector-tab" data-tab="tabMissionDesignStudio" id="tabBtnMissionDesignStudio" title="Atlas Goal-Driven Mission Design Compiler: Natural-Language Intent &times; Autonomous Fleet Synthesis">&#127919; Design Studio</button>'

assert old_button in text or old_button.replace("\n", "\r\n") in text, "old_button not found"
text = text.replace(old_button, new_button).replace(old_button.replace("\n", "\r\n"), new_button.replace("\n", "\r\n"))

# 2. Add tab panel before tabPlan
target_plan = '<div id="tabPlan" class="inspector-tab-panel hidden">'

design_studio_panel = """      <!-- TAB: ATLAS MISSION DESIGN STUDIO 2.0 (Milestone 13K) -->
      <div id="tabMissionDesignStudio" class="inspector-tab-panel hidden">
        <div class="control-card" style="margin-bottom:8px; padding:10px 12px; background:linear-gradient(135deg, rgba(8,16,28,0.95), rgba(14,30,50,0.95)); border:1px solid rgba(56,189,248,0.4); border-radius:6px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <span class="control-label" style="font-size:12px; font-weight:800; color:#38bdf8; letter-spacing:0.5px;">&#127919; ATLAS MISSION DESIGN STUDIO 2.0</span>
              <div style="font-size:10px; color:#94a3b8; margin-top:2px;">Goal-Driven Intent &times; Formal Constraints &times; Autonomous Fleet Synthesis</div>
            </div>
            <span id="compilerEngineBadge" class="badge" style="background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid rgba(56,189,248,0.5); font-size:9px; padding:2px 8px;">COMPILER V2.0 READY</span>
          </div>
          
          <div style="display:flex; gap:6px; margin-top:8px; flex-wrap:wrap;">
            <button id="btnCompilerSampleIntent" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#128196; LOAD SAMPLE INTENT</button>
            <button id="btnCompilerValidate" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#128269; VALIDATE INTENT</button>
            <button id="btnCompilerCompile" class="btn-primary" style="font-size:10px; padding:4px 10px; background:#0284c7; color:#fff; font-weight:700;">&#9889; COMPILE CAMPAIGN</button>
            <button id="btnCompilerBenchmark" class="btn-secondary" style="font-size:10px; padding:4px 8px;">&#128202; BENCHMARK LAB</button>
          </div>
        </div>

        <!-- Intent Builder Deck -->
        <div class="control-card" style="margin-bottom:8px; padding:10px 12px;">
          <div style="font-size:11px; font-weight:700; color:#e2e8f0; margin-bottom:6px; display:flex; justify-content:space-between;">
            <span>1. NATURAL-LANGUAGE MISSION INTENT</span>
            <span style="font-size:9px; color:#64748b;">PRESETS</span>
          </div>
          <div style="margin-bottom:6px;">
            <select id="compilerBriefPresets" class="hud-select" style="width:100%; font-size:10px; margin-bottom:6px;">
              <option value="preset_jezero_recon">Preset: Western Jezero Delta 2-Rover Reconnaissance (5 Sols)</option>
              <option value="preset_distributed_3rover">Preset: Distributed Delta Exploration (3 Rovers, 4 Sols)</option>
              <option value="preset_resource_conservative">Preset: Energy Conservative Low-Risk Survey (35% Reserve)</option>
              <option value="preset_comms_focused">Preset: High-Continuity Communications Mesh (Relay Escort)</option>
            </select>
            <textarea id="compilerBriefInput" class="hud-textarea" rows="3" style="width:100%; font-size:11px; font-family:monospace; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); border-radius:4px; padding:6px; color:#f1f5f9; box-sizing:border-box;" placeholder="Enter natural language mission intent..."></textarea>
          </div>

          <!-- Structured Constraints Accordion Grid -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px;">
            <div style="background:rgba(0,0,0,0.25); padding:8px; border-radius:4px; border:1px solid rgba(255,255,255,0.08);">
              <div style="font-size:10px; font-weight:700; color:#38bdf8; margin-bottom:4px;">FLEET &amp; DURATION</div>
              <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px;">
                <span>Rovers:</span>
                <span id="lblCompilerRoversCount" style="font-weight:700; color:#f8fafc;">2 Rovers</span>
              </div>
              <input type="range" id="compilerSliderRovers" min="1" max="4" value="2" style="width:100%; margin-bottom:6px;">
              
              <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px;">
                <span>Duration (Sols):</span>
                <span id="lblCompilerDurationSols" style="font-weight:700; color:#f8fafc;">5 Sols</span>
              </div>
              <input type="range" id="compilerSliderSols" min="1" max="10" value="5" style="width:100%;">
            </div>

            <div style="background:rgba(0,0,0,0.25); padding:8px; border-radius:4px; border:1px solid rgba(255,255,255,0.08);">
              <div style="font-size:10px; font-weight:700; color:#10b981; margin-bottom:4px;">RESOURCES &amp; COMMS</div>
              <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px;">
                <span>Min Battery Reserve:</span>
                <span id="lblCompilerBatteryReserve" style="font-weight:700; color:#f8fafc;">20% SoC</span>
              </div>
              <input type="range" id="compilerSliderBattery" min="10" max="40" value="20" style="width:100%; margin-bottom:6px;">
              
              <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px;">
                <span>Relay Budget:</span>
                <span id="lblCompilerRelayBudget" style="font-weight:700; color:#f8fafc;">2 Relays</span>
              </div>
              <input type="range" id="compilerSliderRelays" min="0" max="4" value="2" style="width:100%;">
            </div>
          </div>
        </div>

        <!-- Intent Validation Inspector -->
        <div id="compilerValidationPanel" class="control-card" style="margin-bottom:8px; padding:10px 12px; display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">2. INTENT VALIDATION REPORT</span>
            <span id="compilerValidationBadge" class="badge" style="font-size:9px; padding:2px 8px;">VALID</span>
          </div>
          <div id="compilerValidationSummary" style="font-size:10px; color:#94a3b8; margin-bottom:6px;"></div>
          <div id="compilerValidationIssues" style="max-height:120px; overflow-y:auto; font-size:10px;"></div>
        </div>

        <!-- Candidate Comparison Matrix Deck (8 Candidates) -->
        <div id="compilerCandidatesDeckPanel" class="control-card" style="margin-bottom:8px; padding:10px 12px; display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">3. SYNTHESIZED PARETO CANDIDATES (8 PORTFOLIO)</span>
            <span id="compilerParetoCountBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; border:1px solid rgba(16,185,129,0.4); font-size:9px; padding:2px 6px;">6 PARETO CHAMPIONS</span>
          </div>
          
          <div id="compilerCandidatesGrid" style="display:grid; grid-template-columns:1fr 1fr; gap:8px; max-height:280px; overflow-y:auto; padding-right:4px;">
            <!-- Rendered Candidate Cards -->
          </div>
        </div>

        <!-- Interactive Task Graph (DAG) Explorer -->
        <div id="compilerTaskGraphPanel" class="control-card" style="margin-bottom:8px; padding:10px 12px; display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">4. DIRECTED ACYCLIC TASK GRAPH (DAG)</span>
            <span id="compilerDagMetricsBadge" style="font-size:9px; color:#38bdf8;">0 Tasks | 0 Edges</span>
          </div>
          <div style="font-size:9px; color:#94a3b8; margin-bottom:6px;">Strict topological execution ordering &amp; critical path dependency tracing</div>
          
          <!-- SVG DAG Canvas Container -->
          <div id="compilerDagContainer" style="width:100%; height:220px; background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.1); border-radius:4px; overflow:auto; position:relative;">
            <svg id="compilerDagSvg" width="1000" height="200" style="display:block;"></svg>
          </div>

          <!-- Task Node Details Inspector -->
          <div id="compilerTaskDetailBox" style="margin-top:6px; padding:6px 8px; background:rgba(15,23,42,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:4px; font-size:10px; display:none;">
            <div id="compilerTaskDetailTitle" style="font-weight:700; color:#38bdf8;">Select a task node to inspect telemetry</div>
            <div id="compilerTaskDetailBody" style="color:#cbd5e1; margin-top:2px;"></div>
          </div>
        </div>

        <!-- Pairwise Candidate Comparison Scorecard -->
        <div id="compilerTradeoffPanel" class="control-card" style="margin-bottom:8px; padding:10px 12px; display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">5. TRADE-OFF DELTA SCORECARD</span>
            <span id="compilerSelectedPostBadge" class="badge" style="background:rgba(56,189,248,0.2); color:#38bdf8; font-size:9px;">BALANCED</span>
          </div>
          <div id="compilerTradeoffSummaryText" style="font-size:10px; color:#94a3b8; margin-bottom:8px; line-height:1.4;"></div>
          
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; font-size:10px;" id="compilerDeltaMetricsGrid">
            <!-- 6 Delta boxes -->
          </div>
        </div>

        <!-- Plan Compilation Debugger Drawer (Failure Chain & Relaxations) -->
        <div id="compilerDebuggerPanel" class="control-card" style="margin-bottom:8px; padding:10px 12px; display:none; border-left:3px solid #f43f5e;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#f43f5e;">&#9888; COMPILATION DEBUGGER &amp; RELAXATION ADVICE</span>
            <span id="compilerDebugStatusBadge" class="badge" style="background:rgba(244,63,94,0.2); color:#f43f5e; font-size:9px;">INFEASIBLE</span>
          </div>
          
          <div style="font-size:10px; font-weight:700; color:#e2e8f0; margin-bottom:4px;">Causal Failure Chain:</div>
          <div id="compilerFailureChainList" style="margin-bottom:8px; font-size:10px;"></div>
          
          <div style="font-size:10px; font-weight:700; color:#e2e8f0; margin-bottom:4px;">1-Click Relaxation Proposals:</div>
          <div id="compilerRelaxationList" style="font-size:10px;"></div>
        </div>

        <!-- Benchmark Lab Drawer -->
        <div id="compilerBenchmarkPanel" class="control-card" style="margin-bottom:8px; padding:10px 12px; display:none;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:11px; font-weight:700; color:#e2e8f0;">&#128202; 6-SCENARIO BENCHMARK LAB (CAMPAIGNS A&ndash;F)</span>
            <span id="compilerBenchFeasBadge" class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; font-size:9px;">83.3% FEASIBLE</span>
          </div>
          <div id="compilerBenchmarkSummary" style="font-size:10px; color:#94a3b8; margin-bottom:6px;"></div>
          <div id="compilerBenchmarkTable" style="max-height:160px; overflow-y:auto; font-size:9px; font-family:monospace;"></div>
        </div>

        <!-- Execution & Promotion Action Bar -->
        <div class="control-card" style="padding:10px 12px; display:flex; gap:8px;">
          <button id="btnCompilerPromote" class="btn-primary" style="flex:1; font-size:11px; padding:6px; background:#10b981; color:#fff; font-weight:700;">&#128640; PROMOTE PLAN TO FLEET</button>
          <button id="btnCompilerTheaterReplay" class="btn-secondary" style="flex:1; font-size:11px; padding:6px;">&#127916; 3D THEATER TRAVERSE REPLAY</button>
        </div>
      </div>
"""

assert target_plan in text or target_plan.replace("\n", "\r\n") in text, "target_plan not found"
text = text.replace(target_plan, design_studio_panel + "\n      " + target_plan).replace(target_plan.replace("\n", "\r\n"), design_studio_panel.replace("\n", "\r\n") + "\r\n      " + target_plan.replace("\n", "\r\n"))

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Inserted tabMissionDesignStudio successfully into index.html")
