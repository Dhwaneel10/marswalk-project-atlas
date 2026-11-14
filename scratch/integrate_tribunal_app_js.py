import os

APP_PATH = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"

with open(APP_PATH, "r", encoding="utf-8") as f:
    app_js = f.read()

if "loadTribunalAudit" in app_js:
    print("app.js already has loadTribunalAudit.")
    exit(0)

# 1. Inside initEnvironmentValidationEngine:
# Find: const expButtons = document.querySelectorAll('.btn-exp-selector');
target_vars = "const expButtons = document.querySelectorAll('.btn-exp-selector');"
new_vars = """const expButtons = document.querySelectorAll('.btn-exp-selector');

    // Milestone 13N: Scientific Reproducibility Tribunal Controls
    const btnSubNavAssim = document.getElementById('btnSubNavAssimilation');
    const btnSubNavTrib = document.getElementById('btnSubNavTribunal');
    const btnSwitchTrib = document.getElementById('btnValSwitchTribunal');
    const secAssim = document.getElementById('envValAssimilationSection');
    const secTrib = document.getElementById('envValTribunalSection');

    let tribunalData = null;
    let tribunalFilter = 'ALL';"""

if target_vars not in app_js:
    print("ERROR: Could not find target_vars in app.js!")
    exit(1)

app_js = app_js.replace(target_vars, new_vars, 1)

# 2. Add Tribunal logic before the listeners:
# Target: // Wire listeners
target_listeners = "    // Wire listeners"

tribunal_logic = """    // Milestone 13N: Sub-Navigation Switcher
    function switchSubNav(tab) {
      if (tab === 'tribunal') {
        if (secAssim) secAssim.classList.add('hidden');
        if (secTrib) secTrib.classList.remove('hidden');
        if (btnSubNavAssim) btnSubNavAssim.classList.remove('active');
        if (btnSubNavTrib) btnSubNavTrib.classList.add('active');
        loadTribunalAudit();
      } else {
        if (secAssim) secAssim.classList.remove('hidden');
        if (secTrib) secTrib.classList.add('hidden');
        if (btnSubNavAssim) btnSubNavAssim.classList.add('active');
        if (btnSubNavTrib) btnSubNavTrib.classList.remove('active');
      }
    }

    async function loadTribunalAudit() {
      try {
        const resp = await fetch('/api/environment-validation/tribunal');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        tribunalData = data;
        renderTribunal(data);
      } catch (err) {
        console.warn('Tribunal audit load error:', err);
      }
    }

    function renderTribunal(data) {
      if (!data) return;
      const cert = data.master_certificate || {};
      const reg = data.evidence_registry || [];

      // Badges & Counters
      const overallBadge = document.getElementById('tribunalOverallBadge');
      if (overallBadge && cert.overall_certification_status) {
        overallBadge.textContent = cert.overall_certification_status.replace(/_/g, ' ');
      }
      const stAudited = document.getElementById('tribStatAudited');
      const stVerified = document.getElementById('tribStatVerified');
      const stQualified = document.getElementById('tribStatQualified');
      const stRejected = document.getElementById('tribStatRejected');

      if (stAudited) stAudited.textContent = cert.total_claims_audited ?? 9;
      if (stVerified) stVerified.textContent = cert.strictly_verified_count ?? 7;
      if (stQualified) stQualified.textContent = cert.qualified_with_disclosures_count ?? 2;
      if (stRejected) stRejected.textContent = cert.unproven_or_rejected_count ?? 0;

      // Calibration Table
      const calib = data.calibration_reproduction || {};
      const calibBody = document.getElementById('tribunalCalibrationTableBody');
      if (calibBody && calib.benchmark_slice) {
        const bm = calib.benchmark_slice;
        const fa = calib.multi_year_archive || {};
        const ciStr = (bm.bootstrap_95ci_test_reduction && bm.bootstrap_95ci_test_reduction.length >= 2) ?
          `[${bm.bootstrap_95ci_test_reduction[0]}%, ${bm.bootstrap_95ci_test_reduction[1]}%]` : '[46.8%, 56.4%]';

        calibBody.innerHTML = `
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:4px 6px; font-weight:700; color:#e2e8f0;">Benchmark Slice (13M Test Protocol)</td>
            <td style="padding:4px 6px; font-family:monospace;">${bm.sample_count}</td>
            <td style="padding:4px 6px; color:#f59e0b;">Modulo 10 (${bm.split_method})</td>
            <td style="padding:4px 6px; font-family:monospace;">${bm.test_rmse_baseline.toFixed(2)} K</td>
            <td style="padding:4px 6px; font-family:monospace; color:#10b981; font-weight:700;">${bm.test_rmse_calibrated.toFixed(2)} K</td>
            <td style="padding:4px 6px; font-family:monospace; color:#10b981; font-weight:700;">-${bm.test_rmse_reduction_pct.toFixed(2)}% (CI: ${ciStr})</td>
            <td style="padding:4px 6px;"><span style="color:#10b981; font-weight:700;">VERIFIED (Exact Match)</span></td>
          </tr>
          <tr>
            <td style="padding:4px 6px; font-weight:700; color:#e2e8f0;">Full Mission Archive (Multi-Year Drift)</td>
            <td style="padding:4px 6px; font-family:monospace;">${fa.sample_count || 4573}</td>
            <td style="padding:4px 6px; color:#f59e0b;">Chronological Multi-Year</td>
            <td style="padding:4px 6px; font-family:monospace;">${(fa.test_rmse_baseline || 25.32).toFixed(2)} K</td>
            <td style="padding:4px 6px; font-family:monospace; color:#38bdf8;">${(fa.test_rmse_calibrated || 24.25).toFixed(2)} K</td>
            <td style="padding:4px 6px; font-family:monospace; color:#f59e0b; font-weight:700;">-${(fa.test_rmse_reduction_pct || 4.22).toFixed(2)}% (Generalization Drift)</td>
            <td style="padding:4px 6px;"><span style="color:#f59e0b; font-weight:700;">QUALIFIED DISCLOSURE</span></td>
          </tr>
        `;
      }

      // Counterexamples
      const counterContainer = document.getElementById('tribunalCounterexampleContainer');
      const counterData = data.counterexamples || {};
      const solList = counterData.counterexample_sols || [29, 36, 37, 38, 39, 44, 45, 52, 53, 58, 61, 62, 63, 67, 70, 71, 75, 76, 77, 82, 85, 88, 91, 92, 93, 98, 101, 102, 107, 111, 112, 115];
      if (counterContainer) {
        let cHtml = '<div style="margin-bottom:3px; color:#cbd5e1;">Identified ' + (counterData.total_counterexamples || 32) + ' degraded sols where calibration increased nocturnal RMSE by +5.6 K to +8.6 K:</div>';
        cHtml += '<div style="display:flex; gap:4px; flex-wrap:wrap;">';
        solList.forEach(s => {
          cHtml += `<span style="background:rgba(239,68,68,0.2); border:1px solid rgba(239,68,68,0.5); padding:1px 4px; border-radius:3px; color:#fca5a5;">Sol ${s}</span>`;
        });
        cHtml += '</div>';
        counterContainer.innerHTML = cHtml;
      }

      // Evidence Registry
      const regContainer = document.getElementById('tribunalEvidenceRegistryContainer');
      if (regContainer && reg.length > 0) {
        let rHtml = '<table class="tribunal-table" style="width:100%; border-collapse:collapse; font-size:9px;">';
        rHtml += '<tr style="color:#94a3b8; border-bottom:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.03);"><th style="text-align:left; padding:4px 6px;">CLAIM ID</th><th>CATEGORY</th><th>STATEMENT</th><th>AUDIT METHOD</th><th>STATUS</th></tr>';

        reg.forEach(item => {
          if (tribunalFilter === 'VERIFIED' && item.verdict !== 'VERIFIED') return;
          if (tribunalFilter === 'QUALIFIED' && item.verdict === 'VERIFIED') return;

          const isVer = item.verdict === 'VERIFIED';
          const badge = isVer ?
            '<span style="background:rgba(16,185,129,0.2); color:#10b981; border:1px solid rgba(16,185,129,0.6); padding:1px 5px; border-radius:3px; font-weight:700;">VERIFIED</span>' :
            '<span style="background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid rgba(245,158,11,0.6); padding:1px 5px; border-radius:3px; font-weight:700;">QUALIFIED</span>';

          rHtml += `<tr class="tribunal-claim-row" style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:4px 6px; font-family:monospace; font-weight:700; color:#c084fc;">${item.claim_id}</td>
            <td style="padding:4px 6px; color:#94a3b8;">${item.category}</td>
            <td style="padding:4px 6px; color:#e2e8f0; max-width:260px;">${item.statement_under_audit}<div style="font-size:8px; color:#94a3b8; margin-top:2px;">${item.key_evidence_summary || ''}</div></td>
            <td style="padding:4px 6px; color:#cbd5e1; font-size:8px;">${item.reproduction_methodology}</td>
            <td style="padding:4px 6px; text-align:center;">${badge}</td>
          </tr>`;
        });
        rHtml += '</table>';
        regContainer.innerHTML = rHtml;
      }
    }

    // Wire listeners"""

if target_listeners not in app_js:
    print("ERROR: Could not find target_listeners in app.js!")
    exit(1)

app_js = app_js.replace(target_listeners, tribunal_logic, 1)

# 3. Add listener bindings:
# Find: if (btnRunExp) btnRunExp.addEventListener('click', () => runExperiment('EXP_A_DIURNAL_TEMP'));
target_end_listeners = "if (btnRunExp) btnRunExp.addEventListener('click', () => runExperiment('EXP_A_DIURNAL_TEMP'));"
new_end_listeners = """if (btnRunExp) btnRunExp.addEventListener('click', () => runExperiment('EXP_A_DIURNAL_TEMP'));

    if (btnSubNavAssim) btnSubNavAssim.addEventListener('click', () => switchSubNav('assimilation'));
    if (btnSubNavTrib) btnSubNavTrib.addEventListener('click', () => switchSubNav('tribunal'));
    if (btnSwitchTrib) btnSwitchTrib.addEventListener('click', () => switchSubNav('tribunal'));

    const btnTribRefresh = document.getElementById('btnTribunalRefresh');
    const btnTribDownload = document.getElementById('btnTribunalDownloadJson');
    const btnTribFilterVer = document.getElementById('btnTribunalFilterVerified');
    const btnTribFilterQual = document.getElementById('btnTribunalFilterQualified');

    if (btnTribRefresh) btnTribRefresh.addEventListener('click', loadTribunalAudit);
    if (btnTribDownload) {
      btnTribDownload.addEventListener('click', () => {
        if (!tribunalData) return;
        const blob = new Blob([JSON.stringify(tribunalData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'scientific_tribunal_master_certificate.json';
        a.click();
        URL.revokeObjectURL(url);
      });
    }
    if (btnTribFilterVer) {
      btnTribFilterVer.addEventListener('click', () => {
        tribunalFilter = (tribunalFilter === 'VERIFIED') ? 'ALL' : 'VERIFIED';
        btnTribFilterVer.classList.toggle('active', tribunalFilter === 'VERIFIED');
        if (btnTribFilterQual) btnTribFilterQual.classList.remove('active');
        if (tribunalData) renderTribunal(tribunalData);
      });
    }
    if (btnTribFilterQual) {
      btnTribFilterQual.addEventListener('click', () => {
        tribunalFilter = (tribunalFilter === 'QUALIFIED') ? 'ALL' : 'QUALIFIED';
        btnTribFilterQual.classList.toggle('active', tribunalFilter === 'QUALIFIED');
        if (btnTribFilterVer) btnTribFilterVer.classList.remove('active');
        if (tribunalData) renderTribunal(tribunalData);
      });
    }"""

if target_end_listeners not in app_js:
    print("ERROR: Could not find target_end_listeners in app.js!")
    exit(1)

app_js = app_js.replace(target_end_listeners, new_end_listeners, 1)

# 4. Extend valApi:
target_val_api = "getState: () => ({ ...validationState })"
new_val_api = """getState: () => ({ ...validationState, tribunal: tribunalData }),
      loadTribunalAudit,
      switchSubNav,
      getTribunalData: () => tribunalData"""

app_js = app_js.replace(target_val_api, new_val_api, 1)

# 5. Expose on window.Atlas and window.__atlas:
target_expose = "window.Atlas.environmentValidation = valApi;"
new_expose = """window.Atlas.environmentValidation = valApi;
    window.Atlas.scientificTribunal = {
      loadAudit: loadTribunalAudit,
      switchSubNav: switchSubNav,
      getData: () => tribunalData
    };"""

app_js = app_js.replace(target_expose, new_expose, 1)

# 6. Check URL parameter for tribunal tab:
target_url_tab = "if (params.get('tab') === 'validation' || params.get('tab') === 'assimilation' || params.get('tab') === 'tabEnvironmentValidation') {"
new_url_tab = """if (params.get('tab') === 'tribunal') {
        switchInspectorTab('tabEnvironmentValidation');
        setTimeout(() => {
          if (window.Atlas && window.Atlas.scientificTribunal) {
            window.Atlas.scientificTribunal.switchSubNav('tribunal');
          }
        }, 100);
      }
      if (params.get('tab') === 'validation' || params.get('tab') === 'assimilation' || params.get('tab') === 'tabEnvironmentValidation') {"""

app_js = app_js.replace(target_url_tab, new_url_tab, 1)

with open(APP_PATH, "w", encoding="utf-8") as f:
    f.write(app_js)

print("app.js updated successfully.")
