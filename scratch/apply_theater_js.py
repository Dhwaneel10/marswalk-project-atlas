import re

app_path = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"
with open(app_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update setCameraDirectorMode and updateCameraDirector
old_set_cam = '''  function setCameraDirectorMode(mode) {
    const validModes = ['orbit', 'follow', 'cockpit', 'overhead'];
    if (!validModes.includes(mode)) return;
    cameraDirectorMode = mode;

    cameraDirectorModePills.forEach(pill => {
      pill.classList.toggle('active', pill.dataset.mode === mode);
    });

    if (chkPlaybackFollowCamera) {
      chkPlaybackFollowCamera.checked = (mode !== 'orbit');
    }

    if (cockpitHudOverlay) {
      if (mode === 'cockpit' && currentViewMode === 'jezero') {
        cockpitHudOverlay.classList.remove('hidden');
      } else {
        cockpitHudOverlay.classList.add('hidden');
      }
    }

    if (mode === 'orbit') {
      controls.enabled = true;
    }

    // Immediately update camera if rover mesh exists
    if (playbackVehicleMesh && playbackVehicleMesh.visible) {
      updateCameraDirector(16.0, playbackVehicleMesh.position, roverSmoothedHeadingRad, roverSmoothedPitchRad, isRoverStationary);
    }
  }'''

new_set_cam = '''  function setCameraDirectorMode(mode) {
    const validModes = ['orbit', 'follow', 'cockpit', 'overhead', 'topographic', 'overview', 'focus'];
    if (!validModes.includes(mode)) return;
    cameraDirectorMode = mode;

    cameraDirectorModePills.forEach(pill => {
      pill.classList.toggle('active', pill.dataset.mode === mode);
    });

    const theaterPills = document.querySelectorAll('#theaterCamPills .theater-pill-btn');
    theaterPills.forEach(pill => {
      pill.classList.toggle('active', pill.dataset.mode === mode);
    });

    if (chkPlaybackFollowCamera) {
      chkPlaybackFollowCamera.checked = (mode !== 'orbit');
    }

    if (cockpitHudOverlay) {
      if (mode === 'cockpit' && currentViewMode === 'jezero') {
        cockpitHudOverlay.classList.remove('hidden');
      } else {
        cockpitHudOverlay.classList.add('hidden');
      }
    }

    if (mode === 'orbit') {
      controls.enabled = true;
    }

    // Immediately update camera
    const markerPos = (playbackVehicleMesh && playbackVehicleMesh.visible) ? playbackVehicleMesh.position : new THREE.Vector3(0, 0, 0);
    updateCameraDirector(16.0, markerPos, roverSmoothedHeadingRad, roverSmoothedPitchRad, isRoverStationary);
  }'''

if old_set_cam in code:
    code = code.replace(old_set_cam, new_set_cam, 1)
    print("Updated setCameraDirectorMode successfully.")
else:
    print("Warning: old_set_cam not found directly, checking normalized line endings...")
    old_set_cam_crlf = old_set_cam.replace('\n', '\r\n')
    if old_set_cam_crlf in code:
        code = code.replace(old_set_cam_crlf, new_set_cam.replace('\n', '\r\n'), 1)
        print("Updated setCameraDirectorMode with CRLF successfully.")

# 2. Update updateCameraDirector
old_update_cam = '''  function updateCameraDirector(deltaMs, markerPos, headingRad, pitchRad, isStationary) {
    if (!camera || !controls || currentViewMode !== 'jezero') return;

    // Unit forward horizontal vector from heading yaw
    const forwardX = Math.sin(headingRad);
    const forwardZ = Math.cos(headingRad);

    if (cameraDirectorMode === 'orbit') {
      // Orbit mode: controls handles everything, camera is free to be manipulated by user
      controls.enabled = true;
      return;
    }

    if (cameraDirectorMode === 'follow') {
      // Smooth 3rd-person chase camera positioned behind marker along heading
      const distBehind = 68.0;
      const heightAbove = 34.0;
      targetCamPos.set(
        markerPos.x - forwardX * distBehind,
        markerPos.y + heightAbove,
        markerPos.z - forwardZ * distBehind
      );
      targetCamLookAt.set(
        markerPos.x + forwardX * 18.0,
        markerPos.y + 6.0,
        markerPos.z + forwardZ * 18.0
      );

      camera.position.lerp(targetCamPos, 0.09);
      controls.target.lerp(targetCamLookAt, 0.12);
    } else if (cameraDirectorMode === 'cockpit') {
      // 1st-person forward-facing cockpit view mounted atop rover mast
      const mastHeight = 8.5;
      const forwardNudge = 4.0;
      targetCamPos.set(
        markerPos.x + forwardX * forwardNudge,
        markerPos.y + mastHeight,
        markerPos.z + forwardZ * forwardNudge
      );

      const lookDist = 140.0;
      const pitchOffset = Math.tan(pitchRad || 0) * lookDist;
      targetCamLookAt.set(
        targetCamPos.x + forwardX * lookDist,
        targetCamPos.y + pitchOffset,
        targetCamPos.z + forwardZ * lookDist
      );

      camera.position.lerp(targetCamPos, 0.14);
      controls.target.lerp(targetCamLookAt, 0.18);
    } else if (cameraDirectorMode === 'overhead') {
      // Stabilized top-down nadir view
      const altitude = 460.0;
      targetCamPos.set(
        markerPos.x,
        markerPos.y + altitude,
        markerPos.z + 0.001 // tiny offset to stabilize lookAt matrix
      );
      targetCamLookAt.copy(markerPos);

      camera.position.lerp(targetCamPos, 0.08);
      controls.target.lerp(targetCamLookAt, 0.12);
    }
  }'''

new_update_cam = '''  function updateCameraDirector(deltaMs, markerPos, headingRad, pitchRad, isStationary) {
    if (!camera || !controls || currentViewMode !== 'jezero') return;

    // Unit forward horizontal vector from heading yaw
    const forwardX = Math.sin(headingRad);
    const forwardZ = Math.cos(headingRad);

    if (cameraDirectorMode === 'orbit') {
      // Orbit mode: controls handles everything, camera is free to be manipulated by user
      controls.enabled = true;
      return;
    }

    controls.enabled = false;

    if (cameraDirectorMode === 'topographic') {
      // Oblique surface perspective revealing scarp slopes
      targetCamPos.set(0, 360, 920);
      targetCamLookAt.set(0, -60, 0);
      camera.position.lerp(targetCamPos, 0.08);
      controls.target.lerp(targetCamLookAt, 0.12);
    } else if (cameraDirectorMode === 'overview') {
      // High regional survey overview fitting campaign bounding box
      targetCamPos.set(0, 2600, 3100);
      targetCamLookAt.set(0, 0, 0);
      camera.position.lerp(targetCamPos, 0.08);
      controls.target.lerp(targetCamLookAt, 0.12);
    } else if (cameraDirectorMode === 'focus') {
      // Centers active disturbance or selected target
      let focusTarget = null;
      if (disruptionZoneMesh && disruptionZoneMesh.visible) {
        focusTarget = disruptionZoneMesh.position;
      } else if (selectedWaypoint && waypointBeacons) {
        const beacon = waypointBeacons.find(b => b.userData && b.userData.waypoint && b.userData.waypoint.name === selectedWaypoint.name);
        if (beacon) focusTarget = beacon.position;
      } else if (playbackVehicleMesh && playbackVehicleMesh.visible) {
        focusTarget = playbackVehicleMesh.position;
      }
      if (focusTarget) {
        targetCamPos.set(focusTarget.x, focusTarget.y + 280, focusTarget.z + 420);
        targetCamLookAt.copy(focusTarget);
        camera.position.lerp(targetCamPos, 0.09);
        controls.target.lerp(targetCamLookAt, 0.12);
      }
    } else if (cameraDirectorMode === 'follow') {
      // Smooth 3rd-person chase camera positioned behind marker along heading
      const distBehind = 68.0;
      const heightAbove = 34.0;
      targetCamPos.set(
        markerPos.x - forwardX * distBehind,
        markerPos.y + heightAbove,
        markerPos.z - forwardZ * distBehind
      );
      targetCamLookAt.set(
        markerPos.x + forwardX * 18.0,
        markerPos.y + 6.0,
        markerPos.z + forwardZ * 18.0
      );

      camera.position.lerp(targetCamPos, 0.09);
      controls.target.lerp(targetCamLookAt, 0.12);
    } else if (cameraDirectorMode === 'cockpit') {
      // 1st-person forward-facing cockpit view mounted atop rover mast
      const mastHeight = 8.5;
      const forwardNudge = 4.0;
      targetCamPos.set(
        markerPos.x + forwardX * forwardNudge,
        markerPos.y + mastHeight,
        markerPos.z + forwardZ * forwardNudge
      );

      const lookDist = 140.0;
      const pitchOffset = Math.tan(pitchRad || 0) * lookDist;
      targetCamLookAt.set(
        targetCamPos.x + forwardX * lookDist,
        targetCamPos.y + pitchOffset,
        targetCamPos.z + forwardZ * lookDist
      );

      camera.position.lerp(targetCamPos, 0.14);
      controls.target.lerp(targetCamLookAt, 0.18);
    } else if (cameraDirectorMode === 'overhead') {
      // Stabilized top-down nadir view
      const altitude = 460.0;
      targetCamPos.set(
        markerPos.x,
        markerPos.y + altitude,
        markerPos.z + 0.001 // tiny offset to stabilize lookAt matrix
      );
      targetCamLookAt.copy(markerPos);

      camera.position.lerp(targetCamPos, 0.08);
      controls.target.lerp(targetCamLookAt, 0.12);
    }
  }'''

if old_update_cam in code:
    code = code.replace(old_update_cam, new_update_cam, 1)
    print("Updated updateCameraDirector successfully.")
else:
    old_update_cam_crlf = old_update_cam.replace('\n', '\r\n')
    if old_update_cam_crlf in code:
        code = code.replace(old_update_cam_crlf, new_update_cam.replace('\n', '\r\n'), 1)
        print("Updated updateCameraDirector with CRLF successfully.")

# 3. Update updatePlaybackHUD with Mission Theater HUD synchronization
old_hud_hook = '    updatePlaybackHUD(timeSeconds, model, state);\n  }'
new_hud_hook = '''    updatePlaybackHUD(timeSeconds, model, state);

    // Milestone 13C: Synchronize Mission Theater HUD Telemetry
    const theaterClock = document.getElementById('theaterClockDisplay');
    const theaterElapsed = document.getElementById('theaterTimeElapsed');
    const theaterTotal = document.getElementById('theaterTimeTotal');
    const theaterPhase = document.getElementById('theaterPhaseDisplay');
    const theaterScrubber = document.getElementById('theaterTimelineScrubber');
    const theaterStatus = document.getElementById('theaterPlaybackStatus');

    if (theaterClock) theaterClock.textContent = formatMissionSeconds(timeSeconds);
    if (theaterElapsed) theaterElapsed.textContent = formatMissionSeconds(timeSeconds);
    if (theaterTotal && model) theaterTotal.textContent = formatMissionSeconds(model.total_duration_s);
    if (theaterScrubber && model && model.total_duration_s > 0) {
      theaterScrubber.value = ((timeSeconds / model.total_duration_s) * 100).toFixed(1);
    }
    if (theaterPhase && state) {
      theaterPhase.textContent = state.is_stationary ? 'STATIONARY DWELL' : `LEG ${state.leg_index || 1}`;
    }
    if (theaterStatus && state) {
      theaterStatus.textContent = state.is_stationary ? 'SCIENTIFIC DWELL / SAMPLING HOLD' : 'NOMINAL REHEARSAL TRAVERSE';
      theaterStatus.style.color = state.is_stationary ? '#f59e0b' : '#38bdf8';
    }
  }'''

if old_hud_hook in code:
    code = code.replace(old_hud_hook, new_hud_hook, 1)
    print("Updated updatePlaybackHUD hook successfully.")
else:
    old_hud_hook_crlf = old_hud_hook.replace('\n', '\r\n')
    if old_hud_hook_crlf in code:
        code = code.replace(old_hud_hook_crlf, new_hud_hook.replace('\n', '\r\n'), 1)
        print("Updated updatePlaybackHUD hook with CRLF successfully.")

# 4. Update animate() loop for continuous camera tracking
old_animate = '''    if (flightState.active) {
      updateCameraFlight(frameStart);
    } else {
      controls.update();

      // Gentle planet rotation in orbit view strictly when in idle-orbit state
      if (currentViewMode === 'orbit' && marsGlobeGroup && autoRotationEnabled && navigationState === 'idle-orbit') {
        marsGlobeGroup.rotation.y += 0.00035;
      }
    }'''

new_animate = '''    if (flightState.active) {
      updateCameraFlight(frameStart);
    } else {
      controls.update();

      // Milestone 13C: Continuous smooth camera director tracking for non-orbit modes
      if (currentViewMode === 'jezero' && cameraDirectorMode !== 'orbit') {
        const markerPos = (playbackVehicleMesh && playbackVehicleMesh.visible) ? playbackVehicleMesh.position : new THREE.Vector3(0, 0, 0);
        updateCameraDirector(16.0, markerPos, roverSmoothedHeadingRad, roverSmoothedPitchRad, isRoverStationary);
      }

      // Gentle planet rotation in orbit view strictly when in idle-orbit state
      if (currentViewMode === 'orbit' && marsGlobeGroup && autoRotationEnabled && navigationState === 'idle-orbit') {
        marsGlobeGroup.rotation.y += 0.00035;
      }
    }'''

if old_animate in code:
    code = code.replace(old_animate, new_animate, 1)
    print("Updated animate loop successfully.")
else:
    old_animate_crlf = old_animate.replace('\n', '\r\n')
    if old_animate_crlf in code:
        code = code.replace(old_animate_crlf, new_animate.replace('\n', '\r\n'), 1)
        print("Updated animate loop with CRLF successfully.")

# 5. Add Spatial Inspector and Mission Theater initialization logic
theater_functions = '''
  // ==========================================================================
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

# 6. Add showTheaterSpatialInspector to click handler
old_click = '''      // 2. Otherwise check for Waypoint Beacon selection
      const intersects = raycaster.intersectObjects(waypointBeacons);
      if (intersects.length > 0) {
        const wp = intersects[0].object.userData.waypoint;
        if (wp) openWaypointModal(wp);
      } else if (terrainMesh) {
        // Query terrain coordinates on surface click
        const tHits = raycaster.intersectObject(terrainMesh);
        if (tHits.length > 0) {
          const pt = tHits[0].point;
          const dx = missionData.grid.ground_dx_m;
          const dy = missionData.grid.ground_dy_m;
          const totalW = (missionData.grid.cols - 1) * dx;
          const totalH = (missionData.grid.rows - 1) * dy;
          const halfW = totalW / 2.0;
          const halfH = totalH / 2.0;
          const col = Math.max(0, Math.min(missionData.grid.cols - 1, Math.round((pt.x + halfW) / dx)));
          const row = Math.max(0, Math.min(missionData.grid.rows - 1, Math.round((pt.z + halfH) / dy)));
          const boundsGeo = (missionData.bounds && missionData.bounds.geographic) || {};
          const lonMin = boundsGeo.min_lon_deg !== undefined ? boundsGeo.min_lon_deg : 77.397666;
          const lonMax = boundsGeo.max_lon_deg !== undefined ? boundsGeo.max_lon_deg : 77.482019;
          const latMin = boundsGeo.min_lat_deg !== undefined ? boundsGeo.min_lat_deg : 18.399978;
          const latMax = boundsGeo.max_lat_deg !== undefined ? boundsGeo.max_lat_deg : 18.484331;
          const lon = lonMin + (col / (missionData.grid.cols - 1)) * (lonMax - lonMin);
          const lat = latMax - (row / (missionData.grid.rows - 1)) * (latMax - latMin);
          updateLiveTelemetry(lon, lat, `${(camera.position.y * 1.5).toFixed(0)} m`, '-35°');
        }
      }'''

new_click = '''      // 2. Milestone 13C: 5-Tier Spatial Raycasting Hierarchy
      let hitHandled = false;
      if (playbackVehicleMesh && playbackVehicleMesh.visible) {
        const unitHits = raycaster.intersectObjects(playbackVehicleMesh.children);
        if (unitHits.length > 0) {
          showTheaterSpatialInspector('unit', playbackVehicleMesh, unitHits[0].point);
          hitHandled = true;
        }
      }
      if (!hitHandled && disruptionZoneMesh && disruptionZoneMesh.visible) {
        const hazardHits = raycaster.intersectObjects(disruptionZoneMesh.children);
        if (hazardHits.length > 0) {
          showTheaterSpatialInspector('hazard', disruptionZoneMesh, hazardHits[0].point);
          hitHandled = true;
        }
      }
      if (!hitHandled) {
        const intersects = raycaster.intersectObjects(waypointBeacons);
        if (intersects.length > 0) {
          const wp = intersects[0].object.userData.waypoint;
          if (wp) {
            openWaypointModal(wp);
            showTheaterSpatialInspector('waypoint', wp, intersects[0].point);
            hitHandled = true;
          }
        }
      }
      if (!hitHandled && terrainMesh) {
        const tHits = raycaster.intersectObject(terrainMesh);
        if (tHits.length > 0) {
          const pt = tHits[0].point;
          const dx = missionData.grid.ground_dx_m;
          const dy = missionData.grid.ground_dy_m;
          const totalW = (missionData.grid.cols - 1) * dx;
          const totalH = (missionData.grid.rows - 1) * dy;
          const halfW = totalW / 2.0;
          const halfH = totalH / 2.0;
          const col = Math.max(0, Math.min(missionData.grid.cols - 1, Math.round((pt.x + halfW) / dx)));
          const row = Math.max(0, Math.min(missionData.grid.rows - 1, Math.round((pt.z + halfH) / dy)));
          const boundsGeo = (missionData.bounds && missionData.bounds.geographic) || {};
          const lonMin = boundsGeo.min_lon_deg !== undefined ? boundsGeo.min_lon_deg : 77.397666;
          const lonMax = boundsGeo.max_lon_deg !== undefined ? boundsGeo.max_lon_deg : 77.482019;
          const latMin = boundsGeo.min_lat_deg !== undefined ? boundsGeo.min_lat_deg : 18.399978;
          const latMax = boundsGeo.max_lat_deg !== undefined ? boundsGeo.max_lat_deg : 18.484331;
          const lon = lonMin + (col / (missionData.grid.cols - 1)) * (lonMax - lonMin);
          const lat = latMax - (row / (missionData.grid.rows - 1)) * (latMax - latMin);
          updateLiveTelemetry(lon, lat, `${(camera.position.y * 1.5).toFixed(0)} m`, '-35°');
          showTheaterSpatialInspector('terrain', { row, col, lat, lon }, pt);
        }
      }'''

if old_click in code:
    code = code.replace(old_click, new_click, 1)
    print("Updated click handler successfully.")
else:
    old_click_crlf = old_click.replace('\n', '\r\n')
    if old_click_crlf in code:
        code = code.replace(old_click_crlf, new_click.replace('\n', '\r\n'), 1)
        print("Updated click handler with CRLF successfully.")

# 7. Add theater functions before init()
if 'function showTheaterSpatialInspector' not in code:
    init_marker = '  // Main Initialization Function\n  async function init() {'
    if init_marker in code:
        code = code.replace(init_marker, theater_functions + '\n\n' + init_marker, 1)
        print("Added theater functions successfully.")
    else:
        init_marker_crlf = '  // Main Initialization Function\r\n  async function init() {'
        if init_marker_crlf in code:
            code = code.replace(init_marker_crlf, theater_functions.replace('\n', '\r\n') + '\r\n\r\n' + init_marker_crlf, 1)
            print("Added theater functions with CRLF successfully.")

# 8. Call initMissionTheater() inside init() and expose to window.__atlas
old_init_end = '''      // Milestone 13B: Auto-launch Conference Demo Mode if ?mode=demo or ?demo=1
      if (params.get('mode') === 'demo' || params.get('demo') === '1' || params.get('demo') === 'true') {
        hideLandingPage();
        setTimeout(() => {
          enterDemoMode();
        }, 300);
      }'''

new_init_end = '''      // Milestone 13B: Auto-launch Conference Demo Mode if ?mode=demo or ?demo=1
      if (params.get('mode') === 'demo' || params.get('demo') === '1' || params.get('demo') === 'true') {
        hideLandingPage();
        setTimeout(() => {
          enterDemoMode();
        }, 300);
      }

      // Milestone 13C: Initialize Atlas 3D Mission Theater
      initMissionTheater();'''

if old_init_end in code:
    code = code.replace(old_init_end, new_init_end, 1)
    print("Added initMissionTheater() call successfully.")
else:
    old_init_end_crlf = old_init_end.replace('\n', '\r\n')
    if old_init_end_crlf in code:
        code = code.replace(old_init_end_crlf, new_init_end.replace('\n', '\r\n'), 1)
        print("Added initMissionTheater() call with CRLF successfully.")

# 9. Expose Theater API on window.__atlas
old_atlas_api = '''        // Milestone 12C: Route Decision Workbench API
        refreshTerrainProfile: (r, c) => refreshTerrainProfileAnalysis(r, c),
        getTerrainAnalysis: () => currentTerrainAnalysis,
        getRouteComparison: () => currentComparisonData,
        clearTerrainWorkbench: () => clearTerrainProfileWorkbench()
      };'''

new_atlas_api = '''        // Milestone 12C: Route Decision Workbench API
        refreshTerrainProfile: (r, c) => refreshTerrainProfileAnalysis(r, c),
        getTerrainAnalysis: () => currentTerrainAnalysis,
        getRouteComparison: () => currentComparisonData,
        clearTerrainWorkbench: () => clearTerrainProfileWorkbench(),
        // Milestone 13C: Atlas 3D Mission Theater API
        enterTheaterMode: () => enterMissionTheaterMode(),
        exitTheaterMode: () => exitMissionTheaterMode(),
        setTheaterCameraMode: (m) => setCameraDirectorMode(m),
        getTheaterCameraMode: () => getCameraDirectorMode()
      };'''

if old_atlas_api in code:
    code = code.replace(old_atlas_api, new_atlas_api, 1)
    print("Exposed Theater API in window.__atlas successfully.")
else:
    old_atlas_api_crlf = old_atlas_api.replace('\n', '\r\n')
    if old_atlas_api_crlf in code:
        code = code.replace(old_atlas_api_crlf, new_atlas_api.replace('\n', '\r\n'), 1)
        print("Exposed Theater API in window.__atlas with CRLF successfully.")

with open(app_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Updated web/app.js successfully.")
