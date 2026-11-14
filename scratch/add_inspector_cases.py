with open('web/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

target = "    } else if (type === 'los_obstruction') {"
replacement = '''    } else if (type === 'joint_candidate_route') {
      if (typeBadge) typeBadge.textContent = 'CO-DESIGN TRAVERSE';
      const c = data;
      const m = c.metrics || {};
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Candidate ID:</span><span class="theater-inspector-val text-cyan">${c.candidate_id} (${c.strategy_name || 'Candidate'})</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Pareto Status:</span><span class="theater-inspector-val" style="color:${c.is_pareto ? '#10b981' : '#94a3b8'};">${c.is_pareto ? 'NON-DOMINATED (RANK 1)' : 'DOMINATED'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Traverse Distance:</span><span class="theater-inspector-val">${Number(m.total_distance_m || 0).toFixed(0)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Comms Coverage:</span><span class="theater-inspector-val" style="color:#10b981;">${Number(m.comms_coverage_pct || 0).toFixed(1)}%</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Relays Deployed:</span><span class="theater-inspector-val">${m.relay_count || 0} towers</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Waligora Metabolic:</span><span class="theater-inspector-val">${Number((m.metabolic_energy_j || 0) / 1000).toFixed(0)} kJ</span></div>
      `;
      if (citation) citation.textContent = 'Atlas Joint Mission Co-Design Engine (USGS CTX 20m DTM)';
    } else if (type === 'joint_gap_segment') {
      if (typeBadge) typeBadge.textContent = 'COMMS BLACKOUT GAP';
      const g = data;
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Gap Identifier:</span><span class="theater-inspector-val text-crimson" style="color:#ef4444;">${g.gap_id || 'GAP-01'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Blackout Distance:</span><span class="theater-inspector-val">${Number(g.gap_distance_m || 0).toFixed(0)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Blackout Duration:</span><span class="theater-inspector-val">${Number(g.duration_s || 0).toFixed(0)} s (${(Number(g.duration_s || 0)/60).toFixed(1)} min)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Occluding Scarp:</span><span class="theater-inspector-val">Delta Front Topographic Ridge</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Mitigation Triage:</span><span class="theater-inspector-val" style="color:#f59e0b;">Deploy Promontory Tower or Detour</span></div>
      `;
      if (citation) citation.textContent = 'Geometric LOS Raycasting Engine (USGS CTX DTM)';
    } else if (type === 'los_obstruction') {'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open('web/app.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully added inspector cases.")
else:
    print("Target still not found!")
