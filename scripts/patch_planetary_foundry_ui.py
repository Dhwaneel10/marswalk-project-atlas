"""
Patch script for injecting Milestone 13Z Planetary Foundry UI into web/index.html and web/app.js.
"""

import os
import sys

def patch_index_html():
    html_path = "web/index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add tab button
    btn_target = '<button class="inspector-tab" data-tab="tabPlanetaryNetwork" id="tabBtnPlanetaryNetwork" title="Atlas Planetary Network: Multi-Settlement Communications, Orbital Relay Constellations &amp; DTN">&#128225; Planetary Network</button>'
    btn_replacement = btn_target + '\n        <button class="inspector-tab" data-tab="tabPlanetaryFoundry" id="tabBtnPlanetaryFoundry" title="Atlas Planetary Foundry: Autonomous Robotic Construction, ISRU Manufacturing &amp; Infrastructure">&#127959; Planetary Foundry</button>'

    if btn_target in content and 'id="tabBtnPlanetaryFoundry"' not in content:
        content = content.replace(btn_target, btn_replacement, 1)
        print("Patched Foundry tab button in index.html")
    else:
        print("Foundry tab button already present or target not found.")

    # 2. Add tab panel right above tabPlan
    panel_target = '<div id="tabPlan" class="inspector-tab-panel hidden">'
    
    panel_block = """      <!-- ============================================================= -->
      <!-- TAB: PLANETARY FOUNDRY & ROBOTIC CONSTRUCTION (Milestone 13Z) -->
      <!-- ============================================================= -->
      <div id="tabPlanetaryFoundry" class="inspector-tab-panel hidden planetary-foundry-panel">
        <div class="control-card pf-header-card" style="border-left: 3px solid #f97316; background: linear-gradient(180deg, #1c0f05 0%, #080c14 100%); margin-bottom: 8px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div>
              <span style="font-size:12px; font-weight:800; color:#fb923c; letter-spacing:0.5px;">&#127959; ATLAS PLANETARY FOUNDRY &bull; ROBOTIC CONSTRUCTION</span>
              <div style="font-size:10px; color:#94a3b8; margin-top:2px;">Autonomous Surface Construction &bull; ISRU Manufacturing &bull; Multi-Robot Fleet Logistics</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <span id="pfStatusPill" class="badge" style="background:#c2410c; color:#ffedd5; font-size:9px; padding:2px 6px; border-radius:3px;">ONLINE &bull; 18 ROBOTS &bull; 3 SETTLEMENTS</span>
              <button id="btnPfRefresh" class="action-btn" style="font-size:9px; padding:3px 8px; background:#ea580c; border:none; color:#fff; border-radius:3px; cursor:pointer;">&#8635; Refresh</button>
            </div>
          </div>

          <!-- Quick Controls Bar -->
          <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center; background:#18110b; padding:6px; border-radius:4px; border:1px solid #29180d;">
            <div style="display:flex; align-items:center; gap:4px;">
              <label style="font-size:9px; color:#fdba74;">Campaign:</label>
              <select id="pfCampaignSelect" style="font-size:9px; background:#1c1917; color:#f8fafc; border:1px solid #44403c; border-radius:3px; padding:2px 4px;">
                <option value="CAMPAIGN-01">01: Single Landing Pad Construction</option>
                <option value="CAMPAIGN-02">02: Three-Settlement Highway Network</option>
                <option value="CAMPAIGN-03">03: Reactor Foundation &amp; Utility Trenches</option>
                <option value="CAMPAIGN-04">04: Solar Array Farm &amp; Distribution Hub</option>
                <option value="CAMPAIGN-05">05: Crater-Rim Relay Mast Foundation</option>
                <option value="CAMPAIGN-06">06: Regolith Berm Blast Shielding</option>
                <option value="CAMPAIGN-07">07: Sintering Bottleneck Management</option>
                <option value="CAMPAIGN-08">08: Mechanical Failure &amp; Field Repair</option>
                <option value="CAMPAIGN-09">09: Inspection Rejection &amp; Rework</option>
                <option value="CAMPAIGN-10">10: Dust Storm Autonomous Hold</option>
                <option value="CAMPAIGN-11">11: Inter-Settlement Feedstock Transfer</option>
                <option value="CAMPAIGN-12" selected>12: The Grand Foundry (Full Multi-Settlement)</option>
              </select>
            </div>
            <button id="btnPfRunCampaign" class="action-btn" style="font-size:9px; padding:3px 8px; background:#f97316; color:#fff; border:none; border-radius:3px; cursor:pointer;">&#9658; Run Campaign</button>
            <button id="btnPfRunGrandPrix" class="action-btn" style="font-size:9px; padding:3px 8px; background:#eab308; color:#000; font-weight:700; border:none; border-radius:3px; cursor:pointer;">&#127942; Run Foundry Grand Prix</button>
          </div>

          <!-- Sub-Tab Navigation Pills -->
          <div class="pf-nav-pills" style="display:flex; gap:4px; margin-top:6px; border-bottom:1px solid #29180d; padding-bottom:6px;">
            <button class="pf-nav-pill active" data-pftab="pfTabOverview" id="pfPillOverview" style="font-size:9px; padding:2px 8px; border-radius:3px; background:#ea580c; color:#fff; border:none; cursor:pointer;">1. Industrial Overview &amp; Stocks</button>
            <button class="pf-nav-pill" data-pftab="pfTabCatalogue" id="pfPillCatalogue" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#94a3b8; border:none; cursor:pointer;">2. Construction Catalogue (12 Assets)</button>
            <button class="pf-nav-pill" data-pftab="pfTabFleet" id="pfPillFleet" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#94a3b8; border:none; cursor:pointer;">3. Robotics Fleet (18 Machines)</button>
            <button class="pf-nav-pill" data-pftab="pfTabGrandPrix" id="pfPillGrandPrix" style="font-size:9px; padding:2px 8px; border-radius:3px; background:transparent; color:#94a3b8; border:none; cursor:pointer;">4. Campaigns &amp; Grand Prix</button>
          </div>
        </div>

        <!-- SUB-TAB 1: Industrial Overview & Stocks -->
        <div id="pfTabOverview" class="pf-subpanel">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#fb923c; margin-bottom:6px;">SETTLEMENT MATERIAL INVENTORY &amp; STOCKS</div>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:6px; margin-bottom:8px;">
              <!-- Alpha -->
              <div style="background:#120c08; padding:6px; border-radius:3px; border:1px solid #2e1d10;">
                <div style="font-size:9px; font-weight:700; color:#fed7aa; margin-bottom:4px;">MARS BASE ALPHA (Jezero)</div>
                <div style="font-size:8px; color:#cbd5e1; line-height:1.5;">
                  Raw Regolith: <strong style="color:#fdba74;">150.0 t</strong><br>
                  Screened Fines: <strong style="color:#fdba74;">60.0 t</strong><br>
                  Sintered Pavers: <strong style="color:#fdba74;">45.0 t</strong><br>
                  Compacted Subgrade: <strong style="color:#fdba74;">80.0 t</strong><br>
                  Imported Alloys: <strong style="color:#38bdf8;">10.0 t</strong><br>
                  Fasteners/Spares: <strong style="color:#38bdf8;">5.0 t</strong>
                </div>
              </div>
              <!-- Beta -->
              <div style="background:#120c08; padding:6px; border-radius:3px; border:1px solid #2e1d10;">
                <div style="font-size:9px; font-weight:700; color:#fed7aa; margin-bottom:4px;">SCIENCE OUTPOST BETA (Nili)</div>
                <div style="font-size:8px; color:#cbd5e1; line-height:1.5;">
                  Raw Regolith: <strong style="color:#fdba74;">150.0 t</strong><br>
                  Screened Fines: <strong style="color:#fdba74;">60.0 t</strong><br>
                  Sintered Pavers: <strong style="color:#fdba74;">45.0 t</strong><br>
                  Compacted Subgrade: <strong style="color:#fdba74;">80.0 t</strong><br>
                  Imported Alloys: <strong style="color:#38bdf8;">10.0 t</strong><br>
                  Fasteners/Spares: <strong style="color:#38bdf8;">5.0 t</strong>
                </div>
              </div>
              <!-- Gamma -->
              <div style="background:#120c08; padding:6px; border-radius:3px; border:1px solid #2e1d10;">
                <div style="font-size:9px; font-weight:700; color:#fed7aa; margin-bottom:4px;">RESOURCE OUTPOST GAMMA (Syrtis)</div>
                <div style="font-size:8px; color:#cbd5e1; line-height:1.5;">
                  Raw Regolith: <strong style="color:#fdba74;">150.0 t</strong><br>
                  Screened Fines: <strong style="color:#fdba74;">60.0 t</strong><br>
                  Sintered Pavers: <strong style="color:#fdba74;">45.0 t</strong><br>
                  Compacted Subgrade: <strong style="color:#fdba74;">80.0 t</strong><br>
                  Imported Alloys: <strong style="color:#38bdf8;">10.0 t</strong><br>
                  Fasteners/Spares: <strong style="color:#38bdf8;">5.0 t</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- SUB-TAB 2: Construction Catalogue (12 Assets) -->
        <div id="pfTabCatalogue" class="pf-subpanel hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#fb923c; margin-bottom:4px;">UNPRESSURIZED INFRASTRUCTURE ASSET CATALOGUE</div>
            <div style="max-height:280px; overflow-y:auto;">
              <table id="pfCatalogueTable" style="width:100%; border-collapse:collapse; font-size:9px; color:#cbd5e1;">
                <thead>
                  <tr style="border-bottom:1px solid #29180d; color:#fdba74; text-align:left;">
                    <th style="padding:3px;">Asset Name</th>
                    <th style="padding:3px;">Footprint (m2)</th>
                    <th style="padding:3px;">Total Mass (t)</th>
                    <th style="padding:3px;">ISRU %</th>
                    <th style="padding:3px;">Energy (kWh)</th>
                    <th style="padding:3px;">Duration (h)</th>
                    <th style="padding:3px;">Min Strength</th>
                  </tr>
                </thead>
                <tbody id="pfCatalogueTbody">
                  <tr><td colspan="7" style="padding:6px; text-align:center; color:#64748b;">Loading infrastructure catalogue...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SUB-TAB 3: Robotics Fleet (18 Machines) -->
        <div id="pfTabFleet" class="pf-subpanel hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#fb923c; margin-bottom:4px;">ROBOTIC INDUSTRIAL FLEET TELEMETRY</div>
            <div style="max-height:280px; overflow-y:auto;">
              <table id="pfFleetTable" style="width:100%; border-collapse:collapse; font-size:9px; color:#cbd5e1;">
                <thead>
                  <tr style="border-bottom:1px solid #29180d; color:#fdba74; text-align:left;">
                    <th style="padding:3px;">Asset ID &bull; Name</th>
                    <th style="padding:3px;">Class</th>
                    <th style="padding:3px;">Settlement</th>
                    <th style="padding:3px;">Payload</th>
                    <th style="padding:3px;">Battery</th>
                    <th style="padding:3px;">Health</th>
                    <th style="padding:3px;">State</th>
                  </tr>
                </thead>
                <tbody id="pfFleetTbody">
                  <tr><td colspan="7" style="padding:6px; text-align:center; color:#64748b;">Loading fleet telemetry...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- SUB-TAB 4: Campaigns & Grand Prix -->
        <div id="pfTabGrandPrix" class="pf-subpanel hidden">
          <div class="control-card" style="margin-bottom:8px;">
            <div style="font-size:10px; font-weight:700; color:#fb923c; margin-bottom:4px;">CONSTRUCTION CAMPAIGN EXECUTION LOG</div>
            <div id="pfCampaignResultCard" style="background:#120c08; padding:6px; border-radius:3px; border:1px solid #2e1d10; font-size:9px; color:#cbd5e1; margin-bottom:8px;">
              <div style="color:#78716c; font-style:italic;">Select a campaign above and click "Run Campaign" to execute multi-robot construction.</div>
            </div>

            <div style="font-size:10px; font-weight:700; color:#eab308; margin-top:8px; margin-bottom:4px;">&#127942; FOUNDRY GRAND PRIX TOURNAMENT STANDINGS</div>
            <div style="overflow-x:auto;">
              <table id="pfGrandPrixTable" style="width:100%; border-collapse:collapse; font-size:9px; color:#cbd5e1;">
                <thead>
                  <tr style="border-bottom:1px solid #44403c; color:#fde047; text-align:left;">
                    <th style="padding:3px;">Strategy</th>
                    <th style="padding:3px;">Accepted / Plan</th>
                    <th style="padding:3px;">Duration (h)</th>
                    <th style="padding:3px;">ISRU %</th>
                    <th style="padding:3px;">Imported (kg)</th>
                    <th style="padding:3px;">Energy (kWh)</th>
                    <th style="padding:3px;">Composite Score</th>
                  </tr>
                </thead>
                <tbody id="pfGrandPrixTbody">
                  <tr><td colspan="7" style="padding:6px; text-align:center; color:#78716c;">Click "Run Foundry Grand Prix" to benchmark competing construction algorithms.</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>\n\n"""

    if panel_target in content and 'id="tabPlanetaryFoundry"' not in content:
        content = content.replace(panel_target, panel_block + panel_target, 1)
        print("Patched Foundry tab panel in index.html")
    else:
        print("Foundry tab panel already present or target not found.")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

def patch_app_js():
    js_path = "web/app.js"
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    call_target = "initPlanetaryNetworkEngine();"
    call_replacement = """initPlanetaryNetworkEngine();
        initPlanetaryFoundryEngine();"""

    if call_target in content and "initPlanetaryFoundryEngine();" not in content:
        content = content.replace(call_target, call_replacement, 1)
        print("Patched initPlanetaryFoundryEngine() call in app.js")

    url_target = "if (params.get('tab') === 'planetary_network'"
    url_replacement = """if (params.get('tab') === 'planetary_foundry' || params.get('tab') === 'planetary-foundry' || params.get('tab') === 'foundry' || params.get('tab') === 'tabPlanetaryFoundry') {
        switchInspectorTab('tabPlanetaryFoundry');
      }
      """ + url_target

    if url_target in content and "tabPlanetaryFoundry" not in content:
        content = content.replace(url_target, url_replacement, 1)
        print("Patched Foundry tab switch URL param in app.js")

    engine_func = """
// =============================================================================
// Milestone 13Z: Atlas Planetary Foundry Operations Center Engine
// =============================================================================

function initPlanetaryFoundryEngine() {
  console.log('[Atlas 13Z] Initializing Planetary Foundry Operations Center Engine...');

  const btnRefresh = document.getElementById('btnPfRefresh');
  const btnRunCampaign = document.getElementById('btnPfRunCampaign');
  const btnRunGrandPrix = document.getElementById('btnPfRunGrandPrix');
  const campaignSelect = document.getElementById('pfCampaignSelect');

  // Sub-tab navigation
  const navPills = document.querySelectorAll('.pf-nav-pill');
  navPills.forEach(pill => {
    pill.addEventListener('click', (e) => {
      navPills.forEach(p => {
        p.classList.remove('active');
        p.style.background = 'transparent';
        p.style.color = '#94a3b8';
      });
      pill.classList.add('active');
      pill.style.background = '#ea580c';
      pill.style.color = '#fff';

      const targetId = pill.getAttribute('data-pftab');
      document.querySelectorAll('.pf-subpanel').forEach(p => p.classList.add('hidden'));
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.remove('hidden');
    });
  });

  async function loadCatalogue() {
    try {
      const res = await fetch('/api/planetary-foundry/catalogue');
      if (!res.ok) return;
      const data = await res.json();
      const catalogue = data.catalogue || [];
      const tbody = document.getElementById('pfCatalogueTbody');
      if (!tbody) return;

      tbody.innerHTML = '';
      catalogue.forEach(item => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #29180d';
        tr.innerHTML = `
          <td style="padding:4px; font-weight:700; color:#f8fafc;">${item.name} <div style="font-size:8px; color:#78716c;">${item.type}</div></td>
          <td style="padding:4px; color:#fdba74;">${item.footprint_m2.toFixed(1)} m²</td>
          <td style="padding:4px; color:#fed7aa;">${(item.boq.total_mass_kg / 1000).toFixed(1)} t</td>
          <td style="padding:4px; color:#10b981; font-weight:700;">${item.boq.isru_fraction_pct.toFixed(1)}%</td>
          <td style="padding:4px; color:#f59e0b;">${item.nominal_energy_kwh.toFixed(0)} kWh</td>
          <td style="padding:4px; color:#cbd5e1;">${item.nominal_duration_hours.toFixed(0)} h</td>
          <td style="padding:4px; color:#38bdf8;">${item.min_compressive_strength_mpa} MPa</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.warn('[13Z] loadCatalogue error:', e);
    }
  }

  async function loadFleet() {
    try {
      const res = await fetch('/api/planetary-foundry/fleet');
      if (!res.ok) return;
      const data = await res.json();
      const fleet = data.fleet || {};
      const tbody = document.getElementById('pfFleetTbody');
      if (!tbody) return;

      tbody.innerHTML = '';
      Object.values(fleet).forEach(r => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #29180d';
        const isOk = r.is_available;
        tr.innerHTML = `
          <td style="padding:4px; font-weight:700; color:#f8fafc;">${r.name} <div style="font-size:8px; color:#78716c;">${r.asset_id}</div></td>
          <td style="padding:4px; color:#fdba74;">${r.class}</td>
          <td style="padding:4px; color:#cbd5e1;">${r.settlement}</td>
          <td style="padding:4px; color:#cbd5e1;">${r.max_payload_kg} kg</td>
          <td style="padding:4px; color:#10b981;">${r.battery_pct}%</td>
          <td style="padding:4px; color:#38bdf8;">${r.health_pct}%</td>
          <td style="padding:4px; font-weight:700; color:${isOk ? '#10b981' : '#ef4444'};">${r.state}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.warn('[13Z] loadFleet error:', e);
    }
  }

  async function runCampaign() {
    const campId = campaignSelect?.value || 'CAMPAIGN-12';
    const card = document.getElementById('pfCampaignResultCard');
    if (card) card.innerHTML = `<div style="color:#fdba74;">Executing ${campId}... allocating multi-robot fleet and simulating mass-energy transformations...</div>`;

    try {
      const res = await fetch(`/api/planetary-foundry/scenarios/run?campaign_id=${campId}`);
      if (!res.ok) throw new Error('API failed');
      const data = await res.json();
      const r = data.result || {};

      if (card) {
        const invList = (r.invariants || []).map(inv => `<span style="background:#7c2d12; color:#ffedd5; padding:1px 5px; border-radius:2px; font-size:8px; margin-right:4px;">&#10003; ${inv}</span>`).join(' ');
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-weight:800; color:#fb923c; font-size:11px;">${r.campaign_id}: ${r.campaign_name}</span>
            <span class="badge" style="background:${r.success ? '#065f46' : '#991b1b'}; color:#fff; font-size:9px; padding:2px 6px; border-radius:3px;">
              ${r.success ? '&#10004; QUALIFIED SUCCESS' : '&#10008; FAILED'}
            </span>
          </div>
          <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:4px; margin-bottom:6px; font-size:8px;">
            <div style="background:#1c1917; padding:4px; border-radius:2px;">Accepted: <strong style="color:#10b981;">${r.accepted}/${r.planned}</strong></div>
            <div style="background:#1c1917; padding:4px; border-radius:2px;">ISRU Mass: <strong style="color:#fdba74;">${(r.isru_mass_kg/1000).toFixed(1)} t (${r.isru_fraction_pct}%)</strong></div>
            <div style="background:#1c1917; padding:4px; border-radius:2px;">Duration: <strong style="color:#cbd5e1;">${r.duration_h} h</strong></div>
            <div style="background:#1c1917; padding:4px; border-radius:2px;">Energy: <strong style="color:#f59e0b;">${r.energy_kwh} kWh</strong></div>
          </div>
          <div style="font-size:8px; color:#cbd5e1; margin-bottom:4px;"><strong>Forensic Notes:</strong> ${r.forensic_notes}</div>
          <div style="font-size:8px; color:#fdba74;"><strong>Invariants Qualified:</strong> ${invList}</div>
        `;
      }
      loadFleet();
    } catch (e) {
      if (card) card.innerHTML = `<div style="color:#ef4444;">Error executing campaign: ${e.message}</div>`;
    }
  }

  async function runGrandPrix() {
    const tbody = document.getElementById('pfGrandPrixTbody');
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="padding:6px; text-align:center; color:#fdba74;">Running 5-strategy Foundry Grand Prix tournament across industrial workloads...</td></tr>`;

    try {
      const res = await fetch('/api/planetary-foundry/grand-prix/run');
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const tourney = data.tournament || {};
      const rankings = tourney.rankings || [];

      if (tbody) {
        tbody.innerHTML = '';
        rankings.forEach((rk, idx) => {
          const isChamp = rk.name === tourney.champions?.overall_grand_prix_champion;
          const tr = document.createElement('tr');
          tr.style.borderBottom = '1px solid #29180d';
          if (isChamp) tr.style.background = '#451a03';

          tr.innerHTML = `
            <td style="padding:4px; font-weight:700; color:${isChamp ? '#fde047' : '#f8fafc'};">
              ${isChamp ? '&#127942; ' : (idx+1) + '. '}${rk.name}
            </td>
            <td style="padding:4px; color:#10b981; font-weight:700;">${rk.accepted} / ${rk.planned}</td>
            <td style="padding:4px; color:#cbd5e1;">${rk.duration_h} h</td>
            <td style="padding:4px; color:#fdba74; font-weight:700;">${rk.isru_pct}%</td>
            <td style="padding:4px; color:#38bdf8;">${rk.imported_kg.toFixed(0)} kg</td>
            <td style="padding:4px; color:#f59e0b;">${rk.energy_kwh.toFixed(0)} kWh</td>
            <td style="padding:4px; font-weight:800; color:#fde047;">${rk.score}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (e) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="padding:6px; text-align:center; color:#ef4444;">Error running Foundry Grand Prix: ${e.message}</td></tr>`;
    }
  }

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      loadCatalogue();
      loadFleet();
    });
  }

  if (btnRunCampaign) btnRunCampaign.addEventListener('click', runCampaign);
  if (btnRunGrandPrix) btnRunGrandPrix.addEventListener('click', runGrandPrix);

  // Initial load
  loadCatalogue();
  loadFleet();
}
"""

    if "function initPlanetaryFoundryEngine()" not in content:
        content += "\n" + engine_func
        print("Appended initPlanetaryFoundryEngine() to app.js")

    with open(js_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    patch_index_html()
    patch_app_js()
    print("Foundry UI patch complete.")
