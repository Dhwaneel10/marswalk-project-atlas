app_path = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"
with open(app_path, "r", encoding="utf-8") as f:
    code = f.read()

theater_functions = '''  // ==========================================================================
  // Milestone 13C: Atlas 3D Mission Theater & Spatial Object Inspector
  // ==========================================================================

  function showTheaterSpatialInspector(type, data, pt) {
    const card = document.getElementById('theaterInspectorCard');
    const typeBadge = document.getElementById('theaterInspectorType');
    const body = document.getElementById('theaterInspectorBody');
    const citation = document.getElementById('theaterInspectorCitation');
    if (!card || !body) return;

    if (type === 'terrain') {
      if (typeBadge) typeBadge.textContent = 'TERRAIN CELL';
      const elev = (missionData && missionData.elevation_samples && missionData.elevation_samples[data.row]) ? missionData.elevation_samples[data.row][data.col] : -2500;
      const slope = (missionData && missionData.slope_samples && missionData.slope_samples[data.row]) ? missionData.slope_samples[data.row][data.col] : 0;
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Grid Cell:</span><span class="theater-inspector-val">Row ${data.row}, Col ${data.col}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Planetocentric:</span><span class="theater-inspector-val">${data.lat.toFixed(5)}° N, ${data.lon.toFixed(5)}° E</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">MOLA Elevation:</span><span class="theater-inspector-val">${elev.toFixed(1)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Horn 3x3 Slope:</span><span class="theater-inspector-val" style="color:${slope > 15 ? '#ef4444' : '#10b981'}">${slope.toFixed(1)}° (${slope > 15 ? 'HAZARD' : 'TRAVERSABLE'})</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Visual Relief:</span><span class="theater-inspector-val">${(elev * currentExaggeration).toFixed(1)} m (${currentExaggeration}x Exagg)</span></div>
      `;
      if (citation) citation.textContent = 'USGS CTX 20m DTM (DOI: 10.5066/P906QQT8)';
    } else if (type === 'waypoint') {
      if (typeBadge) typeBadge.textContent = 'SCIENCE TARGET';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Target Name:</span><span class="theater-inspector-val">${data.name || 'Waypoint'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Type:</span><span class="theater-inspector-val">${data.type || 'Science Site'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Coordinates:</span><span class="theater-inspector-val">(${data.row}, ${data.col}) &bull; ${data.elevation_m || -2500} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Science Priority:</span><span class="theater-inspector-val" style="color:#f59e0b;">${data.priority || 'High (Score 88)'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Sampling Status:</span><span class="theater-inspector-val" style="color:#10b981;">PLANNED CORE</span></div>
      `;
      if (citation) citation.textContent = 'NASA Mars 2020 Science Team / Jezero Database';
    } else if (type === 'unit') {
      if (typeBadge) typeBadge.textContent = 'EXPLORATION UNIT';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Platform:</span><span class="theater-inspector-val">ROVER-1 (Perseverance / Field Unit)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Subsystem Status:</span><span class="theater-inspector-val" style="color:#00e5ff;">AUTONOMOUS TRAVERSE</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Simulated Speed:</span><span class="theater-inspector-val">0.55 m/s (1.98 km/h)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Consumable Margin:</span><span class="theater-inspector-val" style="color:#10b981;">Battery 88.4% &bull; O2 +42m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Provenance:</span><span class="theater-inspector-val">SIMULATION-DERIVED</span></div>
      `;
      if (citation) citation.textContent = 'Digital Twin Kinematic Model (simulated)';
    } else if (type === 'hazard') {
      if (typeBadge) typeBadge.textContent = 'SPATIAL DISTURBANCE';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Disruption:</span><span class="theater-inspector-val" style="color:#ef4444;">ROCKFALL OBSTACLE (60m Barrier)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Injected Timeline:</span><span class="theater-inspector-val">Sol 1619 &bull; MET 01:14:20</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Recovery Triage:</span><span class="theater-inspector-val" style="color:#f59e0b;">Tier 2 Local Conservative Detour</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Autonomous Action:</span><span class="theater-inspector-val">Polyline severed; 420m detour generated</span></div>
      `;
      if (citation) citation.textContent = 'Autonomous Rehearsal Director (Causal Ledger Step 2)';
    } else if (type === 'route') {
      if (typeBadge) typeBadge.textContent = 'ROUTE TRAVERSE LEG';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Traverse Segment:</span><span class="theater-inspector-val">Active Polyline</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Planning Profile:</span><span class="theater-inspector-val">${currentProfile.toUpperCase()}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Apollo Waligora:</span><span class="theater-inspector-val">184.2 W &bull; 92.0 Wh/km</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Safety Rating:</span><span class="theater-inspector-val" style="color:#10b981;">MODEL SATISFIED (Not Flight Certified)</span></div>
      `;
      if (citation) citation.textContent = 'Apollo Waligora Metabolic Cost Model (1972)';
    }

    card.classList.remove('hidden');
  }

  function enterMissionTheaterMode() {
    document.body.classList.add('theater-mode-active');
    const hud = document.getElementById('missionTheaterHUD');
    if (hud) hud.classList.remove('hidden');
    if (currentViewMode !== 'jezero') {
      flyToJezeroView();
    }
    setCameraDirectorMode('overview');
    if (window.dispatchEvent) {
      window.dispatchEvent(new Event('resize'));
    }
  }

  function exitMissionTheaterMode() {
    document.body.classList.remove('theater-mode-active');
    const hud = document.getElementById('missionTheaterHUD');
    if (hud) hud.classList.add('hidden');
    const card = document.getElementById('theaterInspectorCard');
    if (card) card.classList.add('hidden');
    setCameraDirectorMode('orbit');
    if (controls) controls.enabled = true;
    if (window.dispatchEvent) {
      window.dispatchEvent(new Event('resize'));
    }
  }

  function initMissionTheater() {
    const hud = document.getElementById('missionTheaterHUD');
    const btnHeaderTheater = document.getElementById('btnHeaderMissionTheater');
    const btnDemoTheater = document.getElementById('btnDemoMissionTheater');
    const btnExitTheater = document.getElementById('btnExitTheaterMode');
    const btnExplain = document.getElementById('btnTheaterExplain');
    const selectExagg = document.getElementById('theaterExaggerationSelect');
    const camPills = document.querySelectorAll('#theaterCamPills .theater-pill-btn');
    const layerPills = document.querySelectorAll('#theaterLayerPills .theater-pill-btn');
    const chkNominal = document.getElementById('chkTheaterNominal');
    const chkDisturbed = document.getElementById('chkTheaterDisturbed');
    const chkRecovered = document.getElementById('chkTheaterRecovered');
    const btnPlay = document.getElementById('btnTheaterPlayPause');
    const btnReset = document.getElementById('btnTheaterReset');
    const btnStepBack = document.getElementById('btnTheaterStepBack');
    const btnStepForward = document.getElementById('btnTheaterStepForward');
    const scrubber = document.getElementById('theaterTimelineScrubber');
    const speedBtns = document.querySelectorAll('#theaterSpeedPills .theater-speed-btn');
    const btnAudio = document.getElementById('btnTheaterAudio');
    const btnCenterUnit = document.getElementById('btnTheaterCenterUnit');
    const closeInspector = document.getElementById('btnCloseTheaterInspector');
    const btnProvenance = document.getElementById('btnTheaterInspectProvenance');

    if (btnHeaderTheater) btnHeaderTheater.addEventListener('click', enterMissionTheaterMode);
    if (btnDemoTheater) btnDemoTheater.addEventListener('click', enterMissionTheaterMode);
    if (btnExitTheater) btnExitTheater.addEventListener('click', exitMissionTheaterMode);

    // Keybindings: 'T' toggles theater, 'Escape' exits
    window.addEventListener('keydown', (e) => {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT')) return;
      if (e.key === 't' || e.key === 'T') {
        if (document.body.classList.contains('theater-mode-active')) exitMissionTheaterMode();
        else enterMissionTheaterMode();
      } else if (e.key === 'Escape' && document.body.classList.contains('theater-mode-active')) {
        exitMissionTheaterMode();
      }
    });

    // URL query check: ?theater=1
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('theater') === '1') {
      setTimeout(enterMissionTheaterMode, 600);
    }

    // Camera Director Pills
    camPills.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.mode;
        if (mode) setCameraDirectorMode(mode);
        camPills.forEach(b => b.classList.toggle('active', b === btn));
      });
    });

    // Visual Layer Pills
    layerPills.forEach(btn => {
      btn.addEventListener('click', () => {
        const layer = btn.dataset.layer;
        if (layer && typeof setTerrainTexture === 'function') {
          setTerrainTexture(layer);
        }
        layerPills.forEach(b => b.classList.toggle('active', b === btn));
      });
    });

    // Trajectory Layer Toggles
    if (chkNominal) {
      chkNominal.addEventListener('change', () => {
        if (routeLineMesh) routeLineMesh.visible = chkNominal.checked;
      });
    }
    if (chkDisturbed) {
      chkDisturbed.addEventListener('change', () => {
        if (disruptionZoneMesh) disruptionZoneMesh.visible = chkDisturbed.checked;
      });
    }
    if (chkRecovered) {
      chkRecovered.addEventListener('change', () => {
        if (detourRouteMesh) detourRouteMesh.visible = chkRecovered.checked;
      });
    }

    // Exaggeration Select
    if (selectExagg) {
      selectExagg.addEventListener('change', (e) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val > 0) {
          currentExaggeration = val;
          buildTerrainMesh(currentExaggeration, currentTerrainTexture);
          buildWaypointBeacons();
          updatePlanningMarkers();
        }
      });
    }

    // Explain Formulary
    if (btnExplain) {
      btnExplain.addEventListener('click', () => {
        const formularyDrawer = document.getElementById('formularyDrawer');
        if (formularyDrawer) formularyDrawer.classList.toggle('open');
      });
    }

    // Transport Bar Buttons
    if (btnPlay) {
      btnPlay.addEventListener('click', () => {
        if (typeof togglePlaybackPlayPause === 'function') {
          togglePlaybackPlayPause();
        } else {
          playbackState.isPlaying = !playbackState.isPlaying;
          btnPlay.innerHTML = playbackState.isPlaying ? '&#10074;&#10074; PAUSE' : '&#9654; PLAY';
        }
      });
    }
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        if (typeof seekPlaybackTime === 'function') seekPlaybackTime(0);
        else {
          playbackState.currentTime_s = 0;
          if (typeof applyPlaybackFrame === 'function') applyPlaybackFrame(0);
        }
      });
    }
    if (btnStepBack) {
      btnStepBack.addEventListener('click', () => {
        const t = Math.max(0, (playbackState.currentTime_s || 0) - 5);
        if (typeof seekPlaybackTime === 'function') seekPlaybackTime(t);
        else if (typeof applyPlaybackFrame === 'function') applyPlaybackFrame(t);
      });
    }
    if (btnStepForward) {
      btnStepForward.addEventListener('click', () => {
        const t = (playbackState.currentTime_s || 0) + 5;
        if (typeof seekPlaybackTime === 'function') seekPlaybackTime(t);
        else if (typeof applyPlaybackFrame === 'function') applyPlaybackFrame(t);
      });
    }
    if (scrubber) {
      scrubber.addEventListener('input', (e) => {
        const pct = parseFloat(e.target.value) / 100.0;
        const model = playbackModels[playbackState.activeVariant];
        const dur = model ? model.total_duration_s : 100;
        const targetT = pct * dur;
        if (typeof seekPlaybackTime === 'function') seekPlaybackTime(targetT);
        else if (typeof applyPlaybackFrame === 'function') applyPlaybackFrame(targetT);
      });
    }

    // Speed Multipliers
    speedBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const speed = parseFloat(btn.dataset.speed);
        if (!isNaN(speed) && speed > 0) {
          playbackState.speedMultiplier = speed;
          speedBtns.forEach(b => b.classList.toggle('active', b === btn));
        }
      });
    });

    // Audio Toggle
    if (btnAudio) {
      btnAudio.addEventListener('click', () => {
        if (typeof toggleAudioCues === 'function') {
          const active = toggleAudioCues();
          btnAudio.innerHTML = active ? '&#128266;' : '&#128263;';
        }
      });
    }

    // Center Unit
    if (btnCenterUnit) {
      btnCenterUnit.addEventListener('click', () => {
        if (typeof focusPlaybackMarker === 'function') focusPlaybackMarker();
      });
    }

    // Inspector Card Close & Provenance
    if (closeInspector) {
      closeInspector.addEventListener('click', () => {
        const card = document.getElementById('theaterInspectorCard');
        if (card) card.classList.add('hidden');
      });
    }
    if (btnProvenance) {
      btnProvenance.addEventListener('click', () => {
        const modal = document.getElementById('evidenceModal') || document.getElementById('provenanceModal');
        if (modal) modal.classList.remove('hidden');
      });
    }

    // Smooth Interruptibility Protocol: Canvas user interaction cancels flight & switches to orbit
    if (renderer && renderer.domElement) {
      const onInterrupt = () => {
        if (cameraDirectorMode !== 'orbit') {
          setCameraDirectorMode('orbit');
        }
        if (typeof cancelCurrentFlight === 'function') cancelCurrentFlight();
        if (controls) controls.enabled = true;
      };
      renderer.domElement.addEventListener('pointerdown', onInterrupt, { passive: true });
      renderer.domElement.addEventListener('wheel', onInterrupt, { passive: true });
      renderer.domElement.addEventListener('touchstart', onInterrupt, { passive: true });
    }
  }
'''

target = '  // Application Lifecycle Boot'
if target in code and 'function showTheaterSpatialInspector' not in code:
    code = code.replace(target, theater_functions + '\n\n' + target, 1)
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("Inserted theater functions successfully.")
else:
    target_crlf = '  // Application Lifecycle Boot\r\n'
    if target_crlf in code and 'function showTheaterSpatialInspector' not in code:
        code = code.replace(target_crlf, theater_functions.replace('\n', '\r\n') + '\r\n\r\n' + target_crlf, 1)
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(code)
        print("Inserted theater functions with CRLF successfully.")
    else:
        print("Target not found or already inserted.")
