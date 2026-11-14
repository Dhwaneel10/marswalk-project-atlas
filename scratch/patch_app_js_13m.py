with open("web/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# 1. Add element references around line 855
el_ref_anchor = "  const tabBtnEnvironmentStudio = document.getElementById('tabBtnEnvironmentStudio');"
el_ref_new = """  const tabBtnEnvironmentStudio = document.getElementById('tabBtnEnvironmentStudio');
  const tabEnvironmentValidation = document.getElementById('tabEnvironmentValidation');
  const tabBtnEnvironmentValidation = document.getElementById('tabBtnEnvironmentValidation');"""

if el_ref_anchor in js:
    js = js.replace(el_ref_anchor, el_ref_new, 1)
    print("Patched element references")
else:
    print("Warning: el_ref_anchor not found")

# 2. Add to panels dictionary around line 1172
panels_anchor = "tabEnvironmentStudio, tabPlan,"
panels_new = "tabEnvironmentStudio, tabEnvironmentValidation, tabPlan,"

if panels_anchor in js:
    js = js.replace(panels_anchor, panels_new, 1)
    print("Patched panels dictionary")
else:
    print("Warning: panels_anchor not found")

# 3. Add to cockpit-mode condition
cockpit_anchor = "tabId === 'tabEnvironmentStudio'"
cockpit_new = "tabId === 'tabEnvironmentStudio' || tabId === 'tabEnvironmentValidation'"

if cockpit_anchor in js:
    js = js.replace(cockpit_anchor, cockpit_new, 1)
    print("Patched cockpit condition")
else:
    print("Warning: cockpit_anchor not found")

# 4. Add boot initialization call
boot_anchor = "switchInspectorTab('tabEnvironmentStudio');\n      }"
boot_new = """switchInspectorTab('tabEnvironmentStudio');
      }
      // Milestone 13M: Initialize Mars Climate Data Assimilation & Validation Lab
      initEnvironmentValidationEngine();
      if (params.get('tab') === 'validation' || params.get('tab') === 'assimilation' || params.get('tab') === 'tabEnvironmentValidation') {
        switchInspectorTab('tabEnvironmentValidation');
      }"""

if boot_anchor in js:
    js = js.replace(boot_anchor, boot_new, 1)
    print("Patched boot initializer")
else:
    # Try CRLF
    boot_anchor_crlf = "switchInspectorTab('tabEnvironmentStudio');\r\n      }"
    boot_new_crlf = """switchInspectorTab('tabEnvironmentStudio');\r
      }\r
      // Milestone 13M: Initialize Mars Climate Data Assimilation & Validation Lab\r
      initEnvironmentValidationEngine();\r
      if (params.get('tab') === 'validation' || params.get('tab') === 'assimilation' || params.get('tab') === 'tabEnvironmentValidation') {\r
        switchInspectorTab('tabEnvironmentValidation');\r
      }"""
    if boot_anchor_crlf in js:
        js = js.replace(boot_anchor_crlf, boot_new_crlf, 1)
        print("Patched boot initializer (CRLF)")
    else:
        print("Warning: boot_anchor not found")

# 5. Append initEnvironmentValidationEngine implementation before `})();`
engine_code = """
  // =========================================================================
  // MILESTONE 13M: ATLAS MARS CLIMATE DATA ASSIMILATION & VALIDATION LAB ENGINE
  // =========================================================================
  function initEnvironmentValidationEngine() {
    const btnSyncManifest = document.getElementById('btnValSyncManifest');
    const btnCollocateMCD = document.getElementById('btnValCollocateMCD');
    const btnRunCalib = document.getElementById('btnValRunCalibration');
    const btnRunExp = document.getElementById('btnValRunExperiments');
    const selModel = document.getElementById('envValModelTarget');
    const selParam = document.getElementById('envValParamTarget');
    const manifestContainer = document.getElementById('envValManifestContainer');
    const svgChart = document.getElementById('envValSvgChart');
    const calibDeck = document.getElementById('envValCalibrationDeck');
    const expDisplay = document.getElementById('envValExperimentDisplay');
    const expButtons = document.querySelectorAll('.btn-exp-selector');

    let validationState = {
      manifest: null,
      collocatedPairs: [],
      metrics: null,
      calibrationResult: null,
      activeExperiment: null
    };

    // Load Manifest
    async function loadManifest() {
      try {
        const resp = await fetch('/api/environment-validation/catalog');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        validationState.manifest = data;
        renderManifest(data);
      } catch (err) {
        console.warn('Manifest load error:', err);
      }
    }

    function renderManifest(data) {
      if (!manifestContainer || !data.products) return;
      let html = '<table style="width:100%; border-collapse:collapse; color:#cbd5e1;">';
      html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.1); color:#94a3b8; text-align:left;">' +
        '<th style="padding:2px 4px;">PRODUCT ID</th>' +
        '<th style="padding:2px 4px;">SENSOR / SOURCE</th>' +
        '<th style="padding:2px 4px;">LEVEL</th>' +
        '<th style="padding:2px 4px;">SIZE</th>' +
        '<th style="padding:2px 4px;">SHA-256 DIGEST</th>' +
        '<th style="padding:2px 4px;">PROVENANCE</th>' +
        '</tr>';

      data.products.forEach(p => {
        const shaShort = p.sha256_checksum.substring(0, 10) + '...';
        const sizeKb = (p.file_size_bytes / 1024).toFixed(1) + ' KB';
        const isAuth = p.provenance_class === 'AUTHENTIC_PLANETARY_ARCHIVE';
        const provBadge = isAuth ?
          '<span style="color:#10b981; font-weight:700;">&#10004; AUTHENTIC_PDS</span>' :
          '<span style="color:#38bdf8;">NUMERICAL_GCM</span>';

        html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
          <td style="padding:2px 4px; font-weight:700; color:#e2e8f0;">${p.product_id}</td>
          <td style="padding:2px 4px;">${p.instrument}</td>
          <td style="padding:2px 4px; color:#94a3b8;">${p.processing_level}</td>
          <td style="padding:2px 4px; font-family:monospace;">${sizeKb}</td>
          <td style="padding:2px 4px;"><span class="env-val-sha-badge">${shaShort}</span></td>
          <td style="padding:2px 4px;">${provBadge}</td>
        </tr>`;
      });
      html += '</table>';
      manifestContainer.innerHTML = html;

      const badge = document.getElementById('envManifestCounterBadge');
      if (badge) {
        const totalMb = (data.total_bytes / (1024 * 1024)).toFixed(2);
        badge.textContent = `${data.total_products} PRODUCTS &bull; ${totalMb} MB (VERIFIED)`;
      }
    }

    // Collocation & Chart Rendering
    async function loadCollocationAndEvaluate() {
      const model = selModel ? selModel.value : 'MCD_6_2_GCM';
      const param = selParam ? selParam.value : 'ground_temperature';

      try {
        const collocResp = await fetch(`/api/environment-validation/collocate?model=${model}&limit=100`);
        const evalResp = await fetch(`/api/environment-validation/evaluate?model=${model}&limit=150`);

        if (collocResp.ok && evalResp.ok) {
          const collocData = await collocResp.json();
          const evalData = await evalResp.json();

          validationState.collocatedPairs = collocData.pairs || [];
          validationState.metrics = evalData;

          renderMetricsHUD(evalData, param);
          renderSvgChart(collocData.pairs || [], param, model);
        }
      } catch (err) {
        console.warn('Collocation error:', err);
      }
    }

    function renderMetricsHUD(evalData, param) {
      const stats = (evalData.overall_metrics && evalData.overall_metrics[param]) || null;
      const trStats = (evalData.train_metrics && evalData.train_metrics[param]) || null;
      const hoStats = (evalData.held_out_metrics && evalData.held_out_metrics[param]) || null;

      const elBias = document.getElementById('hudValBias');
      const elRmse = document.getElementById('hudValRmse');
      const elPearson = document.getElementById('hudValPearson');
      const elHoldout = document.getElementById('hudValHoldout');

      if (stats) {
        const u = stats.unit || '';
        if (elBias) elBias.textContent = (stats.mean_bias > 0 ? '+' : '') + stats.mean_bias.toFixed(2) + ' ' + u;
        if (elRmse) elRmse.textContent = stats.rmse.toFixed(2) + ' ' + u;
        if (elPearson) elPearson.textContent = stats.pearson_r.toFixed(3);
        if (elHoldout && hoStats) elHoldout.textContent = hoStats.rmse.toFixed(2) + ' ' + u;
      }
    }

    function renderSvgChart(pairs, param, modelName) {
      if (!svgChart) return;
      const filtered = pairs.filter(p => p.parameter_name === param && p.gate_status === 'COLLOCATION_QUALIFIED');
      if (filtered.length === 0) {
        svgChart.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#94a3b8" font-size="11">No qualified collocated observation pairs for parameter</text>';
        return;
      }

      const w = svgChart.clientWidth || 320;
      const h = svgChart.clientHeight || 180;
      const padL = 35, padR = 15, padT = 15, padB = 25;

      const plotW = w - padL - padR;
      const plotH = (h - padT - padB) * 0.70; // 70% upper, 30% residual lower
      const resH = (h - padT - padB) * 0.25;
      const resY0 = padT + plotH + 8;

      // Extract values
      const hrs = filtered.map(p => p.delta_ltst_hours % 24.0);
      const obs = filtered.map(p => p.observed_value);
      const mod = filtered.map(p => p.model_value);
      const res = filtered.map(p => p.residual);

      const minVal = Math.min(...obs, ...mod);
      const maxVal = Math.max(...obs, ...mod);
      const valSpan = (maxVal - minVal) || 1.0;

      const minRes = Math.min(...res);
      const maxRes = Math.max(...res);
      const resSpan = (Math.max(Math.abs(minRes), Math.abs(maxRes)) * 1.2) || 5.0;

      const scaleX = (hr) => padL + (hr / 24.0) * plotW;
      const scaleY = (v) => padT + plotH - ((v - minVal) / valSpan) * plotH;
      const scaleResY = (r) => resY0 + (resH / 2.0) - (r / resSpan) * (resH / 2.0);

      let svg = '';
      // Grid lines
      [0, 6, 12, 18, 24].forEach(hr => {
        const x = scaleX(hr);
        svg += `<line x1="${x}" y1="${padT}" x2="${x}" y2="${padT + plotH}" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>`;
        svg += `<line x1="${x}" y1="${resY0}" x2="${x}" y2="${resY0 + resH}" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>`;
        svg += `<text x="${x}" y="${h - 4}" fill="#94a3b8" font-size="8" text-anchor="middle">${hr}h</text>`;
      });

      // Zero residual line
      const yZero = scaleResY(0);
      svg += `<line x1="${padL}" y1="${yZero}" x2="${padL + plotW}" y2="${yZero}" stroke="rgba(255,255,255,0.25)" stroke-dasharray="2,2"/>`;

      // Model points & line (sorted by hour)
      const sortedIdx = hrs.map((val, idx) => [val, idx]).sort((a, b) => a[0] - b[0]).map(a => a[1]);
      let modelPath = '';
      sortedIdx.forEach((idx, i) => {
        const x = scaleX(hrs[idx]);
        const y = scaleY(mod[idx]);
        if (i === 0) modelPath += `M ${x} ${y}`;
        else modelPath += ` L ${x} ${y}`;
      });
      svg += `<path d="${modelPath}" fill="none" stroke="#38bdf8" stroke-width="2" opacity="0.85"/>`;

      // Observed points (amber dots)
      filtered.forEach((p, idx) => {
        const x = scaleX(hrs[idx]);
        const y = scaleY(obs[idx]);
        svg += `<circle cx="${x}" cy="${y}" r="3" fill="#f59e0b" stroke="#000" stroke-width="1" opacity="0.9"><title>Sol ${p.sol}: Obs ${p.observed_value} ${p.unit}, Model ${p.model_value} ${p.unit}</title></circle>`;

        // Residual point
        const ry = scaleResY(res[idx]);
        svg += `<circle cx="${x}" cy="${ry}" r="2" fill="${res[idx] >= 0 ? '#10b981' : '#ef4444'}"/>`;
      });

      // Legend
      svg += `<circle cx="${padL + 10}" cy="${padT + 8}" r="3" fill="#f59e0b"/><text x="${padL + 18}" y="${padT + 11}" fill="#f59e0b" font-size="8">Real In-Situ Observation</text>`;
      svg += `<line x1="${padL + 115}" y1="${padT + 8}" x2="${padL + 130}" y2="${padT + 8}" stroke="#38bdf8" stroke-width="2"/><text x="${padL + 134}" y="${padT + 11}" fill="#38bdf8" font-size="8">${modelName}</text>`;
      svg += `<text x="${padL + plotW - 10}" y="${resY0 + 8}" fill="#94a3b8" font-size="8" text-anchor="end">Residuals (Model - Obs)</text>`;

      svgChart.innerHTML = svg;
    }

    // Calibration Runner
    async function runCalibration() {
      const param = selParam ? selParam.value : 'ground_temperature';
      try {
        const resp = await fetch('/api/environment-validation/calibrate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parameter: param })
        });
        if (resp.ok) {
          const res = await resp.json();
          validationState.calibrationResult = res;
          renderCalibration(res);
          loadCollocationAndEvaluate();
        }
      } catch (err) {
        console.warn('Calibration error:', err);
      }
    }

    function renderCalibration(res) {
      if (!calibDeck) return;
      const p = res.parameters;
      let html = `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <strong style="color:#10b981;">&#10004; ${res.qualification_verdict}</strong>
        <span style="font-family:monospace; color:#38bdf8;">Train: -${res.train_rmse_reduction_pct}% | Held-Out: -${res.held_out_rmse_reduction_pct}% RMSE</span>
      </div>`;
      html += `<div style="color:#94a3b8; font-size:9px; margin-bottom:6px;">Method: ${res.calibration_method} &bull; Samples: ${res.train_sample_count} train / ${res.held_out_sample_count} held-out</div>`;

      html += '<table style="width:100%; border-collapse:collapse; font-size:9px;">';
      html += '<tr style="color:#94a3b8; border-bottom:1px solid rgba(255,255,255,0.1);"><th style="text-align:left;">PARAM</th><th>BASELINE</th><th>CALIBRATED</th><th>BOUNDS</th></tr>';
      Object.keys(p.calibrated_values).forEach(k => {
        const u = p.physical_units[k] || '';
        const b = p.parameter_bounds[k] ? `[${p.parameter_bounds[k][0]}, ${p.parameter_bounds[k][1]}]` : '';
        html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05); text-align:center;">
          <td style="text-align:left; font-weight:700; color:#cbd5e1;">${k}</td>
          <td style="color:#f59e0b;">${p.baseline_values[k]} ${u}</td>
          <td style="color:#10b981; font-weight:700;">${p.calibrated_values[k]} ${u}</td>
          <td style="color:#94a3b8;">${b}</td>
        </tr>`;
      });
      html += '</table>';
      calibDeck.innerHTML = html;
    }

    // Science Experiments Runner
    async function runExperiment(expId) {
      try {
        const resp = await fetch(`/api/environment-validation/experiments?experiment_id=${expId}`);
        if (resp.ok) {
          const exp = await resp.json();
          validationState.activeExperiment = exp;
          renderExperiment(exp);
        }
      } catch (err) {
        console.warn('Experiment error:', err);
      }
    }

    function renderExperiment(exp) {
      if (!expDisplay) return;
      let html = `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <strong style="color:#38bdf8; font-size:11px;">${exp.title}</strong>
        <span class="badge" style="background:rgba(56,189,248,0.2); color:#38bdf8; font-size:8px;">N=${exp.sample_size} SOUNDINGS</span>
      </div>`;
      html += `<div style="color:#cbd5e1; font-size:9px; margin-bottom:6px;"><strong>Objective:</strong> ${exp.objective}</div>`;

      // Findings
      html += '<div style="background:rgba(0,0,0,0.3); padding:6px; border-radius:4px; margin-bottom:6px;">';
      html += '<strong style="color:#f59e0b; font-size:9px; display:block; margin-bottom:2px;">QUANTITATIVE FINDINGS</strong>';
      Object.entries(exp.quantitative_findings).forEach(([k, v]) => {
        html += `<div style="display:flex; justify-content:space-between; font-size:9px; color:#cbd5e1;">
          <span style="color:#94a3b8;">${k.replace(/_/g, ' ')}:</span>
          <strong style="font-family:monospace; color:#e2e8f0;">${v}</strong>
        </div>`;
      });
      html += '</div>';

      html += `<div style="font-size:9px; color:#10b981; margin-bottom:4px;"><strong>Scientific Conclusion:</strong> ${exp.scientific_conclusion}</div>`;
      html += `<div style="font-size:9px; color:#f59e0b;"><strong>Operational Mandate:</strong> ${exp.operational_implications}</div>`;

      expDisplay.innerHTML = html;
    }

    // Wire listeners
    if (btnSyncManifest) btnSyncManifest.addEventListener('click', loadManifest);
    if (btnCollocateMCD) btnCollocateMCD.addEventListener('click', () => {
      if (selModel) selModel.value = 'MCD_6_2_GCM';
      loadCollocationAndEvaluate();
    });
    if (btnRunCalib) btnRunCalib.addEventListener('click', runCalibration);
    if (btnRunExp) btnRunExp.addEventListener('click', () => runExperiment('EXP_A_DIURNAL_TEMP'));

    if (selModel) selModel.addEventListener('change', loadCollocationAndEvaluate);
    if (selParam) selParam.addEventListener('change', loadCollocationAndEvaluate);

    expButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        expButtons.forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const expId = e.currentTarget.getAttribute('data-exp');
        if (expId) runExperiment(expId);
      });
    });

    // Initial triggers
    loadManifest();
    loadCollocationAndEvaluate();
    runExperiment('EXP_A_DIURNAL_TEMP');

    // Expose Automation API
    const valApi = {
      loadManifest,
      loadCollocationAndEvaluate,
      runCalibration,
      runExperiment,
      getState: () => ({ ...validationState })
    };

    if (!window.Atlas) window.Atlas = {};
    window.Atlas.environmentValidation = valApi;
    if (window.__atlas) window.__atlas.environmentValidation = valApi;
  }
"""

# Insert before final `})();`
final_anchor = "})();"
if final_anchor in js:
    # Replace only the last occurrence
    idx = js.rfind(final_anchor)
    js = js[:idx] + engine_code + "\n" + js[idx:]
    print("Appended initEnvironmentValidationEngine before final })();")
else:
    print("Warning: final })(); anchor not found")

with open("web/app.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Updated web/app.js")
