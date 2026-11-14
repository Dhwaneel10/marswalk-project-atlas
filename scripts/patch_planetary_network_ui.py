"""
Patch script for injecting Milestone 13Y Planetary Network Operations Center into web/index.html and web/app.js.
"""

import os
import sys

def patch_index_html():
    html_path = "web/index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add tab button
    btn_target = '<button class="inspector-tab" data-tab="tabGrandPrix" id="tabBtnGrandPrix" title="Atlas Mission Grand Prix: Strategy Arena, Algorithm Competition, Monte Carlo Experiments &amp; Robustness Benchmarking">&#127942; Grand Prix Arena</button>'
    btn_replacement = btn_target + '\n        <button class="inspector-tab" data-tab="tabPlanetaryNetwork" id="tabBtnPlanetaryNetwork" title="Atlas Planetary Network: Multi-Settlement Communications, Orbital Relay Constellations &amp; DTN">&#128225; Planetary Network</button>'

    if btn_target in content and 'id="tabBtnPlanetaryNetwork"' not in content:
        content = content.replace(btn_target, btn_replacement, 1)
        print("Patched tab button in index.html")
    else:
        print("Tab button already present or target not found.")

    # 2. Add tab panel
    panel_target = '<div id="tabPlan" class="inspector-tab-panel hidden">'
    
    panel_block = """      <!-- ============================================================= -->
      <!-- TAB: PLANETARY NETWORK OPERATIONS CENTER (Milestone 13Y) -->
      <!-- ============================================================= -->
      <div id="tabPlanetaryNetwork" class="inspector-tab-panel hidden planetary-network-panel">
        <div class="control-card pn-header-card" style="border-left: 3px solid #38bdf8; background: linear-gradient(180deg, #071726 0%, #080c14 100%); margin-bottom: 8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div>
              <span style="font-size:12px; font-weight:800; color:#38bdf8; letter-spacing:0.5px;">&#128225; ATLAS PLANETARY NETWORK &bull; OPERATIONS CENTER</span>
              <div style="font-size:10px; color:#94a3b8; margin-top:2px;">Multi-Settlement Backbone &bull; Orbital Constellations &bull; Delay-Tolerant Networking (RFC 9171)</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <span id="pnStatusPill" class="badge" style="background:#0369a1; color:#e0f2fe; font-size:9px; padding:2px 6px; border-radius:3px;">ONLINE &bull; 13 NODES</span>
              <button id="btnPnRefresh" class="action-btn" style="font-size:9px; padding:3px 8px; background:#0284c7; border:none; color:#fff; border-radius:3px; cursor:pointer;">&#8635; Refresh</button>
            </div>
          </div>

          <!-- Quick Controls Bar -->
          <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center; background:#0c1a29; padding:6px; border-radius:4px; border:1px solid #1e293b;">
            <div style="display:flex; align-items:center; gap:4px;">
              <label style="font-size:9px; color:#94a3b8;">Scenario:</label>
              <select id="pnScenarioSelect" style="font-size:9px; background:#1e293b; color:#f8fafc; border:1px solid #334155; border-radius:3px; padding:2px 4px;">
                <option value="SCENARIO-01">01: Baseline Daily Jezero Surface Mesh</option>
                <option value="SCENARIO-02">02: High-Rate Areostationary Backbone</option>
                <option value="SCENARIO-03">03: Fast Rover Traversal Across Rim Block</option>
                <option value="SCENARIO-04">04: Aerial Hexacopter Video Dump</option>
                <option value="SCENARIO-05">05: Outpost Beta Partition &amp; Merkle Sync</option>
                <option value="SCENARIO-06">06: Dust Storm Optical Extinction Fallback</option>
                <option value="SCENARIO-07">07: Cascading Orbital Relay Blackout</option>
                <option value="SCENARIO-08">08: Life-Support Emergency Preemption</option>
                <option value="SCENARIO-09">09: Buffer Saturation &amp; QoS Degradation</option>
                <option value="SCENARIO-10">10: Earth Conjunction 14-Day Blackout</option>
                <option value="SCENARIO-11">11: Multi-Hop Inter-Settlement Sync</option>
                <option value="SCENARIO-12" selected>12: The Planetary Internet (Unified Multi-Sol)</option>
              </select>
            </div>
            <button id="btnPnRunScenario" class="action-btn" style="font-size:9px; padding:3px 8px; background:#2563eb; color:#fff; border:none; border-radius:3px; cursor:pointer;">&#9658; Run Scenario</button>
            <button id="btnPnRunGrandPrix" class="action-btn" style="font-size:9px; padding:3px 8px; background:#d97706; color:#fff; border:none; border-radius:3px; cursor:pointer;">&#127942; Run Network Grand Prix</button>
          </div>

          <!-- Sub-Tab Navigation Pills -->
          <div class="pn-nav-pills" style="display:flex; gap:4px; margin-top:6px; border-bottom:1px solid #1e293b; padding-bottom:6px;">
            <button class="pn-nav-pill active" data-pntab="pnTabTopology" id="pnPillTopology" style="font-size:9px; padding:2px 8px; border-radius:3px; background:#0284c7; color:#fff; border:none; cursor:pointer;">1. Network Topology (13 Nodes)</button>
            <button class="pn-nav-pill" data-pntab="pnTabContacts" id="pnPillContacts" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#94a3b8; border:none; cursor:pointer;">2. Contact Windows &amp; Ephemerides</button>
            <button class="pn-nav-pill" data-pntab="pnTabDTN" id="pnPillDTN" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#94a3b8; border:none; cursor:pointer;">3. DTN Workbench &amp; Buffers</button>
            <button class="pn-nav-pill" data-pntab="pnTabBenchmark" id="pnPillBenchmark" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#94a3b8; border:none; cursor:pointer;">4. Scenarios &amp; Grand Prix</button>
          </div>
        </div>

        <!-- SUB-TAB 1: Network Topology & Node Status -->
        <div id="pnTabTopology" class="pn-subpanel">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#38bdf8; margin-bottom:4px;">PLANETARY COMMUNICATIONS TOPOLOGY</div>
            <div style="overflow-x:auto;">
              <table id="pnTopologyTable" style="width:100%; border-collapse:collapse; font-size:9px; color:#cbd5e1;">
                <thead>
                  <tr style="border-bottom:1px solid #334155; color:#94a3b8; text-align:left;">
                    <th style="padding:3px;">Node ID</th>
                    <th style="padding:3px;">Type</th>
                    <th style="padding:3px;">Coords / Orbit</th>
                    <th style="padding:3px;">Storage Buffer</th>
                    <th style="padding:3px;">Bands</th>
                    <th style="padding:3px;">Battery</th>
                    <th style="padding:3px;">Status</th>
                  </tr>
                </thead>
                <tbody id="pnTopologyTbody">
                  <tr><td colspan="7" style="padding:6px; text-align:center; color:#64748b;">Loading planetary topology...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SUB-TAB 2: Contact Windows & Orbital Schedule -->
        <div id="pnTabContacts" class="pn-subpanel hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <div style="font-size:10px; font-weight:700; color:#38bdf8;">TIME-DEPENDENT CONTACT SCHEDULE (7,200s HORIZON)</div>
              <span id="pnContactsCountBadge" class="badge" style="background:#0f172a; color:#38bdf8; font-size:8px; border:1px solid #0284c7; padding:1px 5px; border-radius:3px;">-- Windows</span>
            </div>
            <div style="max-height:260px; overflow-y:auto;">
              <table id="pnContactsTable" style="width:100%; border-collapse:collapse; font-size:9px; color:#cbd5e1;">
                <thead>
                  <tr style="border-bottom:1px solid #334155; color:#94a3b8; text-align:left;">
                    <th style="padding:3px;">Contact ID</th>
                    <th style="padding:3px;">Source &rarr; Target</th>
                    <th style="padding:3px;">Band</th>
                    <th style="padding:3px;">Start - End (s)</th>
                    <th style="padding:3px;">Range (km)</th>
                    <th style="padding:3px;">Rate (kbps)</th>
                    <th style="padding:3px;">Capacity (MB)</th>
                    <th style="padding:3px;">Light Delay</th>
                  </tr>
                </thead>
                <tbody id="pnContactsTbody">
                  <tr><td colspan="8" style="padding:6px; text-align:center; color:#64748b;">Computing contact geometry...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SUB-TAB 3: DTN Workbench & Buffers -->
        <div id="pnTabDTN" class="pn-subpanel hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#38bdf8; margin-bottom:6px;">DELAY-TOLERANT NETWORKING (RFC 9171) METRICS</div>
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; margin-bottom:8px;">
              <div style="background:#0f172a; padding:6px; border-radius:3px; border:1px solid #1e293b; text-align:center;">
                <div style="font-size:8px; color:#94a3b8;">DELIVERY RATIO</div>
                <div id="pnMetricDeliveryRatio" style="font-size:14px; font-weight:800; color:#10b981;">--%</div>
              </div>
              <div style="background:#0f172a; padding:6px; border-radius:3px; border:1px solid #1e293b; text-align:center;">
                <div style="font-size:8px; color:#94a3b8;">THROUGHPUT</div>
                <div id="pnMetricThroughput" style="font-size:14px; font-weight:800; color:#38bdf8;">-- MB</div>
              </div>
              <div style="background:#0f172a; padding:6px; border-radius:3px; border:1px solid #1e293b; text-align:center;">
                <div style="font-size:8px; color:#94a3b8;">AVG LATENCY</div>
                <div id="pnMetricLatency" style="font-size:14px; font-weight:800; color:#f59e0b;">-- s</div>
              </div>
              <div style="background:#0f172a; padding:6px; border-radius:3px; border:1px solid #1e293b; text-align:center;">
                <div style="font-size:8px; color:#94a3b8;">DROPPED / EXPIRED</div>
                <div id="pnMetricDropped" style="font-size:14px; font-weight:800; color:#ef4444;">0 / 0</div>
              </div>
            </div>

            <div style="font-size:9px; font-weight:700; color:#94a3b8; margin-bottom:4px;">NODE PERSISTENT STORAGE BUFFERS</div>
            <div id="pnBufferBarsContainer" style="display:grid; grid-template-columns: 1fr 1fr; gap:6px;">
              <!-- Populated dynamically -->
            </div>
          </div>
        </div>

        <!-- SUB-TAB 4: Scenarios & Grand Prix Benchmark -->
        <div id="pnTabBenchmark" class="pn-subpanel hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#38bdf8; margin-bottom:4px;">CANONICAL SCENARIO EXECUTION LOG</div>
            <div id="pnScenarioResultCard" style="background:#0f172a; padding:6px; border-radius:3px; border:1px solid #1e293b; font-size:9px; color:#cbd5e1; margin-bottom:8px;">
              <div style="color:#64748b; font-style:italic;">Select a scenario above and click "Run Scenario" to view forensic execution telemetry.</div>
            </div>

            <div style="font-size:10px; font-weight:700; color:#f59e0b; margin-top:8px; margin-bottom:4px;">&#127942; NETWORK GRAND PRIX TOURNAMENT STANDINGS</div>
            <div style="overflow-x:auto;">
              <table id="pnGrandPrixTable" style="width:100%; border-collapse:collapse; font-size:9px; color:#cbd5e1;">
                <thead>
                  <tr style="border-bottom:1px solid #334155; color:#94a3b8; text-align:left;">
                    <th style="padding:3px;">Scheduler</th>
                    <th style="padding:3px;">Delivery %</th>
                    <th style="padding:3px;">Emergency %</th>
                    <th style="padding:3px;">Throughput</th>
                    <th style="padding:3px;">Avg Latency</th>
                    <th style="padding:3px;">Drops</th>
                    <th style="padding:3px;">Grand Prix Score</th>
                  </tr>
                </thead>
                <tbody id="pnGrandPrixTbody">
                  <tr><td colspan="7" style="padding:6px; text-align:center; color:#64748b;">Click "Run Network Grand Prix" to benchmark competing algorithms.</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>\n\n"""

    if panel_target in content and 'id="tabPlanetaryNetwork"' not in content:
        content = content.replace(panel_target, panel_block + panel_target, 1)
        print("Patched tab panel in index.html")
    else:
        print("Tab panel already present or target not found.")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

def patch_app_js():
    js_path = "web/app.js"
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    call_target = "initGrandPrixEngine();"
    call_replacement = """initGrandPrixEngine();
        initPlanetaryNetworkEngine();"""

    if call_target in content and "initPlanetaryNetworkEngine();" not in content:
        content = content.replace(call_target, call_replacement, 1)
        print("Patched initPlanetaryNetworkEngine() call in app.js")

    url_target = "if (params.get('tab') === 'grand_prix'"
    url_replacement = """if (params.get('tab') === 'planetary_network' || params.get('tab') === 'planetary-network' || params.get('tab') === 'network' || params.get('tab') === 'tabPlanetaryNetwork') {
        switchInspectorTab('tabPlanetaryNetwork');
      }
      """ + url_target

    if url_target in content and "tabPlanetaryNetwork" not in content[:content.find(url_target)]:
        content = content.replace(url_target, url_replacement, 1)
        print("Patched tab switch URL param in app.js")

    # Append implementation of initPlanetaryNetworkEngine
    engine_func = """
// =============================================================================
// Milestone 13Y: Atlas Planetary Network Operations Center Engine
// =============================================================================

function initPlanetaryNetworkEngine() {
  console.log('[Atlas 13Y] Initializing Planetary Network Operations Center Engine...');

  const btnRefresh = document.getElementById('btnPnRefresh');
  const btnRunScenario = document.getElementById('btnPnRunScenario');
  const btnRunGrandPrix = document.getElementById('btnPnRunGrandPrix');
  const scenarioSelect = document.getElementById('pnScenarioSelect');

  // Sub-tab navigation
  const navPills = document.querySelectorAll('.pn-nav-pill');
  navPills.forEach(pill => {
    pill.addEventListener('click', (e) => {
      navPills.forEach(p => {
        p.classList.remove('active');
        p.style.background = 'transparent';
        p.style.color = '#94a3b8';
      });
      pill.classList.add('active');
      pill.style.background = '#0284c7';
      pill.style.color = '#fff';

      const targetId = pill.getAttribute('data-pntab');
      document.querySelectorAll('.pn-subpanel').forEach(p => p.classList.add('hidden'));
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.remove('hidden');
    });
  });

  async function loadTopology() {
    try {
      const res = await fetch('/api/planetary-network/topology');
      if (!res.ok) return;
      const data = await res.json();
      const nodes = data.topology?.nodes || {};
      const tbody = document.getElementById('pnTopologyTbody');
      if (!tbody) return;

      tbody.innerHTML = '';
      Object.values(nodes).forEach(n => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #1e293b';

        const bandsStr = (n.supported_bands || []).map(b => `<span style="background:#0f172a; padding:1px 4px; border-radius:2px; font-size:8px; border:1px solid #334155; margin-right:2px;">${b}</span>`).join('');
        const statusBadge = n.is_active 
          ? `<span style="color:#10b981; font-weight:700;">&#9679; ACTIVE</span>`
          : `<span style="color:#ef4444; font-weight:700;">&#9679; OFFLINE</span>`;

        tr.innerHTML = `
          <td style="padding:4px; font-weight:700; color:#f8fafc;">${n.name} <div style="font-size:8px; color:#64748b;">${n.node_id}</div></td>
          <td style="padding:4px; color:#94a3b8;">${n.node_type}</td>
          <td style="padding:4px; color:#cbd5e1;">${n.altitude_m > 10000 ? 'Orbit ' + (n.altitude_m/1000).toFixed(0) + ' km' : n.latitude_deg.toFixed(2) + '°N, ' + n.longitude_deg.toFixed(2) + '°E'}</td>
          <td style="padding:4px;">${n.buffer_used_mb} / ${n.buffer_capacity_mb} MB <span style="color:#94a3b8;">(${n.buffer_utilization_pct}%)</span></td>
          <td style="padding:4px;">${bandsStr}</td>
          <td style="padding:4px; color:#10b981;">${n.battery_level_pct}%</td>
          <td style="padding:4px;">${statusBadge}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.warn('[13Y] loadTopology error:', e);
    }
  }

  async function loadContacts() {
    try {
      const res = await fetch('/api/planetary-network/contacts?horizon_s=7200&step_s=180');
      if (!res.ok) return;
      const data = await res.json();
      const windows = data.windows || [];
      const badge = document.getElementById('pnContactsCountBadge');
      if (badge) badge.innerText = `${windows.length} Windows`;

      const tbody = document.getElementById('pnContactsTbody');
      if (!tbody) return;
      tbody.innerHTML = '';

      windows.slice(0, 30).forEach(w => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #1e293b';
        tr.innerHTML = `
          <td style="padding:4px; font-weight:700; color:#38bdf8;">${w.contact_id}</td>
          <td style="padding:4px; color:#f8fafc;">${w.src} &rarr; ${w.dst}</td>
          <td style="padding:4px; color:#94a3b8;">${w.band}</td>
          <td style="padding:4px; color:#cbd5e1;">${w.start_time_s.toFixed(0)}s &ndash; ${w.end_time_s.toFixed(0)}s <span style="color:#64748b;">(${w.duration_s.toFixed(0)}s)</span></td>
          <td style="padding:4px; color:#cbd5e1;">${w.avg_range_km.toFixed(1)} km</td>
          <td style="padding:4px; color:#10b981; font-weight:700;">${w.rate_kbps.toFixed(0)} kbps</td>
          <td style="padding:4px; color:#cbd5e1;">${w.capacity_mb.toFixed(2)} MB</td>
          <td style="padding:4px; color:#f59e0b;">${(w.propagation_delay_s * 1000).toFixed(1)} ms</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.warn('[13Y] loadContacts error:', e);
    }
  }

  async function loadDTNMetrics() {
    try {
      const res = await fetch('/api/planetary-network/dtn/metrics');
      if (!res.ok) return;
      const data = await res.json();
      const m = data.dtn_metrics || {};
      const buffers = data.buffers || {};

      const dRatio = document.getElementById('pnMetricDeliveryRatio');
      const tPut = document.getElementById('pnMetricThroughput');
      const lat = document.getElementById('pnMetricLatency');
      const drop = document.getElementById('pnMetricDropped');

      if (dRatio) dRatio.innerText = `${m.delivery_ratio_pct ?? 100}%`;
      if (tPut) tPut.innerText = `${m.total_delivered_mbytes ?? 0} MB`;
      if (lat) lat.innerText = `${m.average_delivery_latency_s ?? 0}s`;
      if (drop) drop.innerText = `${m.dropped_bundles ?? 0} / ${m.expired_bundles ?? 0}`;

      const bufContainer = document.getElementById('pnBufferBarsContainer');
      if (bufContainer) {
        bufContainer.innerHTML = '';
        Object.entries(buffers).forEach(([nid, b]) => {
          const div = document.createElement('div');
          div.style.background = '#0f172a';
          div.style.padding = '4px 6px';
          div.style.borderRadius = '3px';
          div.style.border = '1px solid #1e293b';

          const pct = Math.min(100, Math.max(0, b.utilization_pct || 0));
          const barColor = pct > 80 ? '#ef4444' : (pct > 50 ? '#f59e0b' : '#0284c7');

          div.innerHTML = `
            <div style="display:flex; justify-content:space-between; font-size:8px; color:#94a3b8; margin-bottom:2px;">
              <span style="font-weight:700; color:#f8fafc;">${nid}</span>
              <span>${b.used_mb} / ${b.capacity_mb} MB (${pct.toFixed(1)}%)</span>
            </div>
            <div style="width:100%; height:4px; background:#1e293b; border-radius:2px; overflow:hidden;">
              <div style="width:${pct}%; height:100%; background:${barColor};"></div>
            </div>
          `;
          bufContainer.appendChild(div);
        });
      }
    } catch (e) {
      console.warn('[13Y] loadDTNMetrics error:', e);
    }
  }

  async function runScenario() {
    const scenId = scenarioSelect?.value || 'SCENARIO-12';
    const card = document.getElementById('pnScenarioResultCard');
    if (card) card.innerHTML = `<div style="color:#38bdf8;">Executing ${scenId}... simulating space-time contact windows and DTN custody transfers...</div>`;

    try {
      const res = await fetch(`/api/planetary-network/scenarios/run?scenario_id=${scenId}`);
      if (!res.ok) throw new Error('API failed');
      const data = await res.json();
      const r = data.result || {};

      if (card) {
        const invList = (r.invariants_verified || []).map(inv => `<span style="background:#064e3b; color:#6ee7b7; padding:1px 5px; border-radius:2px; font-size:8px; margin-right:4px;">&#10003; ${inv}</span>`).join(' ');
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-weight:800; color:#38bdf8; font-size:11px;">${r.scenario_id}: ${r.scenario_name}</span>
            <span class="badge" style="background:${r.success ? '#065f46' : '#991b1b'}; color:#fff; font-size:9px; padding:2px 6px; border-radius:3px;">
              ${r.success ? '&#10004; QUALIFIED SUCCESS' : '&#10008; FAILED'}
            </span>
          </div>
          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:4px; margin-bottom:6px; font-size:8px;">
            <div style="background:#1e293b; padding:4px; border-radius:2px;">Delivered: <strong style="color:#10b981;">${r.delivered}/${r.total_bundles} (${r.delivery_ratio_pct}%)</strong></div>
            <div style="background:#1e293b; padding:4px; border-radius:2px;">Throughput: <strong style="color:#38bdf8;">${r.delivered_mb} MB</strong></div>
            <div style="background:#1e293b; padding:4px; border-radius:2px;">Avg Latency: <strong style="color:#f59e0b;">${r.avg_latency_s}s</strong></div>
            <div style="background:#1e293b; padding:4px; border-radius:2px;">Transmissions: <strong style="color:#cbd5e1;">${r.transmissions}</strong></div>
          </div>
          <div style="font-size:8px; color:#94a3b8; margin-bottom:4px;"><strong>Forensic Notes:</strong> ${r.forensic_notes}</div>
          <div style="font-size:8px; color:#94a3b8;"><strong>Invariants Qualified:</strong> ${invList}</div>
        `;
      }
      loadDTNMetrics();
    } catch (e) {
      if (card) card.innerHTML = `<div style="color:#ef4444;">Error executing scenario: ${e.message}</div>`;
    }
  }

  async function runGrandPrix() {
    const tbody = document.getElementById('pnGrandPrixTbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="padding:6px; text-align:center; color:#38bdf8;">Running 6-scheduler Network Grand Prix tournament (7,200s simulation)...</td></tr>`;

    try {
      const res = await fetch('/api/planetary-network/grand-prix/run?horizon_s=7200');
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const tourney = data.tournament || {};
      const rankings = tourney.rankings || [];

      if (tbody) {
        tbody.innerHTML = '';
        rankings.forEach((rk, idx) => {
          const isChamp = rk.name === tourney.champions?.overall_grand_prix_champion;
          const tr = document.createElement('tr');
          tr.style.borderBottom = '1px solid #1e293b';
          if (isChamp) tr.style.background = '#1e1b4b';

          tr.innerHTML = `
            <td style="padding:4px; font-weight:700; color:${isChamp ? '#fbbf24' : '#f8fafc'};">
              ${isChamp ? '&#127942; ' : (idx+1) + '. '}${rk.name}
            </td>
            <td style="padding:4px; color:#10b981; font-weight:700;">${rk.delivery_ratio_pct}%</td>
            <td style="padding:4px; color:${rk.emergency_ratio_pct === 100 ? '#10b981' : '#ef4444'}; font-weight:700;">${rk.emergency_ratio_pct}%</td>
            <td style="padding:4px; color:#38bdf8;">${rk.delivered_mb} MB</td>
            <td style="padding:4px; color:#f59e0b;">${rk.avg_latency_s}s</td>
            <td style="padding:4px; color:${rk.dropped > 0 ? '#ef4444' : '#64748b'};">${rk.dropped}</td>
            <td style="padding:4px; font-weight:800; color:#fbbf24;">${rk.grand_prix_score}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (e) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="padding:6px; text-align:center; color:#ef4444;">Error running Grand Prix: ${e.message}</td></tr>`;
    }
  }

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      loadTopology();
      loadContacts();
      loadDTNMetrics();
    });
  }

  if (btnRunScenario) btnRunScenario.addEventListener('click', runScenario);
  if (btnRunGrandPrix) btnRunGrandPrix.addEventListener('click', runGrandPrix);

  // Initial data load
  loadTopology();
  loadContacts();
  loadDTNMetrics();
}
"""

    if "function initPlanetaryNetworkEngine()" not in content:
        content += "\n" + engine_func
        print("Appended initPlanetaryNetworkEngine() to app.js")

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    patch_index_html()
    patch_app_js()
    print("Frontend patch complete.")
