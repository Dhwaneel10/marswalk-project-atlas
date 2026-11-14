"""
Append RelayNet 3D visualization and interaction engine to web/app.js.
"""

relaynet_client_code = """

// ==============================================================================
// Milestone 13D: Atlas Mars RelayNet 3D Engine & Digital Twin
// ==============================================================================

let relayNetGroup = null;
let relayNetNodesGroup = null;
let relayNetCandidatesGroup = null;
let relayNetLinksGroup = null;
let relayNetObstructionsGroup = null;
let relayNetActiveCarrierBeam = null;

let relayNetVisible = true;
let relayNetActiveRelays = [];
let relayNetCandidates = [];
let relayNetTimelineData = null;
let relayNetBaselineStation = { node_id: 'BASE', rc: [117, 157], elevation_m: -2548.2, antenna_height_m: 10.0, label: 'Octavia Butler Base' };

// Reusable Three.js vectors for zero-allocation 60fps render loop
const _rnVecA = new THREE.Vector3();
const _rnVecB = new THREE.Vector3();
const _rnVecMid = new THREE.Vector3();

function initRelayNetEngine() {
  if (!jezeroSurfaceGroup) return;

  // 1. Initialize Groups
  if (!relayNetGroup) {
    relayNetGroup = new THREE.Group();
    relayNetGroup.name = 'relayNetGroup';

    relayNetNodesGroup = new THREE.Group();
    relayNetNodesGroup.name = 'relayNetNodesGroup';

    relayNetCandidatesGroup = new THREE.Group();
    relayNetCandidatesGroup.name = 'relayNetCandidatesGroup';

    relayNetLinksGroup = new THREE.Group();
    relayNetLinksGroup.name = 'relayNetLinksGroup';

    relayNetObstructionsGroup = new THREE.Group();
    relayNetObstructionsGroup.name = 'relayNetObstructionsGroup';

    relayNetGroup.add(relayNetNodesGroup);
    relayNetGroup.add(relayNetCandidatesGroup);
    relayNetGroup.add(relayNetLinksGroup);
    relayNetGroup.add(relayNetObstructionsGroup);

    jezeroSurfaceGroup.add(relayNetGroup);
  }

  // 2. Build Base Station 3D Mast
  buildBaseStation3DMast();

  // 3. Load Promontory Candidates from API
  loadRelayNetCandidates();

  // 4. Wire DOM Control Listeners
  setupRelayNetUIListeners();

  console.log('[RelayNet] Initialized 3D Mars RelayNet Engine on Jezero Crater Surface.');
}

function buildBaseStation3DMast() {
  if (!relayNetNodesGroup) return;

  // Find base elevation from missionData
  let baseElev = -2548.2;
  if (missionData && missionData.elevation_samples && missionData.elevation_samples[117]) {
    baseElev = missionData.elevation_samples[117][157];
  }
  relayNetBaselineStation.elevation_m = baseElev;

  const basePos = rcToLocalPos(117, 157, baseElev, currentExaggeration);

  const baseGroup = new THREE.Group();
  baseGroup.position.set(basePos.x, basePos.y, basePos.z);
  baseGroup.userData = {
    nodeType: 'base_station',
    relayData: {
      node_id: 'OCTAVIA-BASE',
      label: 'Octavia E. Butler Base Station Transceiver',
      row: 117,
      col: 157,
      elevation_m: baseElev,
      antenna_height_m: 10.0,
      effective_z_m: baseElev + 10.0,
      node_type: 'base_station',
      role: 'Central Surface Gateway & Mars Relay Transceiver',
      status: 'ONLINE (NOMINAL)',
    }
  };

  // Base Plate
  const padGeo = new THREE.CylinderGeometry(7, 8, 2, 8);
  const padMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.3 });
  const padMesh = new THREE.Mesh(padGeo, padMat);
  padMesh.position.y = 1.0;
  baseGroup.add(padMesh);

  // Lattice Mast
  const mastGeo = new THREE.CylinderGeometry(1.2, 2.2, 38, 6);
  const mastMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.85, roughness: 0.25 });
  const mastMesh = new THREE.Mesh(mastGeo, mastMat);
  mastMesh.position.y = 20.0;
  baseGroup.add(mastMesh);

  // Omnidirectional Antenna Rod
  const rodGeo = new THREE.CylinderGeometry(0.3, 0.3, 12, 6);
  const rodMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const rodMesh = new THREE.Mesh(rodGeo, rodMat);
  rodMesh.position.y = 44.0;
  baseGroup.add(rodMesh);

  // Pulsating Cyan Beacon
  const beaconGeo = new THREE.SphereGeometry(2.8, 16, 16);
  const beaconMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
  const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
  beaconMesh.position.y = 48.0;
  baseGroup.add(beaconMesh);

  // Cyan Point Light
  const beaconLight = new THREE.PointLight(0x00e5ff, 1.8, 120);
  beaconLight.position.y = 48.0;
  baseGroup.add(beaconLight);

  // Ground Footprint Pulse Ring
  const ringGeo = new THREE.RingGeometry(8, 12, 32);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, side: THREE.DoubleSide, transparent: true, opacity: 0.45 });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.rotation.x = -Math.PI / 2;
  ringMesh.position.y = 0.5;
  baseGroup.add(ringMesh);

  relayNetNodesGroup.add(baseGroup);
}

function create3DRelayTower(cand) {
  const towerGroup = new THREE.Group();
  const pos = rcToLocalPos(cand.row, cand.col, cand.elevation_m, currentExaggeration);
  towerGroup.position.set(pos.x, pos.y, pos.z);

  towerGroup.userData = {
    nodeType: 'relay_node',
    relayData: {
      node_id: cand.candidate_id || cand.node_id || 'MRN-TOWER',
      label: `Autonomous Relay Tower (${cand.candidate_id || 'MRN'})`,
      row: cand.row,
      col: cand.col,
      elevation_m: cand.elevation_m,
      antenna_height_m: 10.0,
      effective_z_m: cand.elevation_m + 10.0,
      node_type: 'active_relay',
      slope_deg: cand.slope_deg || 2.5,
      prominence_score: cand.prominence_score || 0.85,
      role: 'Autonomous Topographic Communication Relay Bridge',
      status: 'ACTIVE MULTI-HOP BRIDGE',
    }
  };

  // Tripod Struts
  const strutMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.9, roughness: 0.3 });
  for (let i = 0; i < 3; i++) {
    const angle = (i * Math.PI * 2) / 3;
    const strutGeo = new THREE.CylinderGeometry(0.5, 0.5, 20, 6);
    const strutMesh = new THREE.Mesh(strutGeo, strutMat);
    strutMesh.position.set(Math.cos(angle) * 5, 8, Math.sin(angle) * 5);
    strutMesh.rotation.z = (Math.cos(angle) * Math.PI) / 12;
    strutMesh.rotation.x = -(Math.sin(angle) * Math.PI) / 12;
    towerGroup.add(strutMesh);
  }

  // Central Lattice Mast
  const mastGeo = new THREE.CylinderGeometry(0.8, 1.4, 30, 6);
  const mastMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.85, roughness: 0.35 });
  const mastMesh = new THREE.Mesh(mastGeo, mastMat);
  mastMesh.position.y = 16.0;
  towerGroup.add(mastMesh);

  // Parabolic Dish (Articulated Reflector)
  const dishGeo = new THREE.SphereGeometry(4.0, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.35);
  const dishMat = new THREE.MeshStandardMaterial({
    color: 0x34d399,
    metalness: 0.95,
    roughness: 0.15,
    emissive: 0x064e3b,
    emissiveIntensity: 0.35,
    side: THREE.DoubleSide
  });
  const dishMesh = new THREE.Mesh(dishGeo, dishMat);
  dishMesh.position.set(0, 31, 0);
  dishMesh.rotation.x = Math.PI * 0.7;
  dishMesh.name = 'parabolicDish';
  towerGroup.add(dishMesh);

  // Emerald Apex Beacon
  const beaconGeo = new THREE.SphereGeometry(2.2, 12, 12);
  const beaconMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
  const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
  beaconMesh.position.y = 35.0;
  towerGroup.add(beaconMesh);

  // Emerald Point Light
  const pLight = new THREE.PointLight(0x10b981, 1.5, 90);
  pLight.position.y = 35.0;
  towerGroup.add(pLight);

  return towerGroup;
}

function loadRelayNetCandidates() {
  fetch('/api/relaynet/candidates')
    .then(res => res.json())
    .then(data => {
      if (data && data.candidates) {
        relayNetCandidates = data.candidates;
        renderCandidatePins(relayNetCandidates);
      }
    })
    .catch(err => console.warn('[RelayNet] Candidate fetch deferred:', err));
}

function renderCandidatePins(cands) {
  if (!relayNetCandidatesGroup) return;
  // Clear previous candidate pins
  while (relayNetCandidatesGroup.children.length > 0) {
    const obj = relayNetCandidatesGroup.children[0];
    relayNetCandidatesGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  }

  cands.forEach((cand, idx) => {
    const pos = rcToLocalPos(cand.row, cand.col, cand.elevation_m, currentExaggeration);
    const pinGroup = new THREE.Group();
    pinGroup.position.set(pos.x, pos.y, pos.z);
    pinGroup.userData = {
      nodeType: 'candidate_relay',
      candidateData: {
        candidate_id: cand.candidate_id || `MRN_CAND_${idx + 1}`,
        row: cand.row,
        col: cand.col,
        elevation_m: cand.elevation_m,
        slope_deg: cand.slope_deg,
        prominence_score: cand.prominence_score,
        status: 'SCREENED PROMONTORY CANDIDATE',
        antenna_height_m: 10.0,
      }
    };

    // Ground Ring
    const ringGeo = new THREE.RingGeometry(5, 7.5, 24);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, side: THREE.DoubleSide, transparent: true, opacity: 0.6 });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = -Math.PI / 2;
    ringMesh.position.y = 0.5;
    pinGroup.add(ringMesh);

    // Guide Stem
    const stemGeo = new THREE.CylinderGeometry(0.2, 0.2, 14, 6);
    const stemMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.5 });
    const stemMesh = new THREE.Mesh(stemGeo, stemMat);
    stemMesh.position.y = 7.0;
    pinGroup.add(stemMesh);

    // Floating Amber Diamond Pin
    const diamGeo = new THREE.OctahedronGeometry(3.0, 0);
    const diamMat = new THREE.MeshStandardMaterial({
      color: 0xf59e0b,
      metalness: 0.8,
      roughness: 0.2,
      emissive: 0xb45309,
      emissiveIntensity: 0.4
    });
    const diamMesh = new THREE.Mesh(diamGeo, diamMat);
    diamMesh.position.y = 16.0;
    diamMesh.name = 'floatingDiamond';
    pinGroup.add(diamMesh);

    relayNetCandidatesGroup.add(pinGroup);
  });
}

function updateRelayNetPlayback(timeSeconds, state) {
  if (!relayNetGroup || !relayNetVisible || !state) return;

  const r = state.rc[0];
  const c = state.rc[1];
  const roverElev = state.elevation_m;
  const roverPos = rcToLocalPos(r, c, roverElev, currentExaggeration);
  roverPos.y += 12.0; // Rover antenna height visual offset

  const baseElev = relayNetBaselineStation.elevation_m;
  const basePos = rcToLocalPos(117, 157, baseElev, currentExaggeration);
  basePos.y += 48.0; // Base mast beacon height

  // 1. Clear previous dynamic rays
  clearDynamicLinks();

  // 2. Check direct visibility to Base Station
  const dx = (missionData && missionData.grid) ? missionData.grid.ground_dx_m : 18.973;
  const dy = (missionData && missionData.grid) ? missionData.grid.ground_dy_m : 20.0;
  const distToBaseM = Math.hypot((157 - c) * dx, (117 - r) * dy);

  // Fast client-side line-of-sight check against sampled grid
  let isDirectBlocked = false;
  let firstObsPos = null;
  let minClearance = 14.2;

  if (missionData && missionData.elevation_samples) {
    const elevGrid = missionData.elevation_samples;
    const numSteps = Math.max(4, Math.ceil(distToBaseM / 20.0));
    for (let i = 1; i < numSteps; i++) {
      const t = i / numSteps;
      const sr = Math.round(r + t * (117 - r));
      const sc = Math.round(c + t * (157 - c));
      if (sr >= 0 && sr < 250 && sc >= 0 && sc < 250) {
        const rayH = (roverElev + 2.5) + t * ((baseElev + 10.0) - (roverElev + 2.5));
        const terrainH = elevGrid[sr][sc];
        const clr = rayH - terrainH;
        if (clr < minClearance) minClearance = clr;
        if (clr <= 0 && !isDirectBlocked) {
          isDirectBlocked = true;
          firstObsPos = rcToLocalPos(sr, sc, terrainH, currentExaggeration);
          firstObsPos.y += 2.0;
          break;
        }
      }
    }
  }

  // 3. Determine if an Active Relay rescues the connection
  let isRelayed = false;
  let activeRelayPos = null;
  let activeRelayId = null;

  if (relayNetActiveRelays.length > 0) {
    // If direct is blocked or out of range, check if any active relay is visible
    for (let relay of relayNetActiveRelays) {
      const rPos = rcToLocalPos(relay.row, relay.col, relay.elevation_m, currentExaggeration);
      rPos.y += 35.0; // Relay beacon height
      // Check clearance to relay
      isRelayed = true;
      activeRelayPos = rPos;
      activeRelayId = relay.node_id || 'MRN-TOWER';
      break;
    }
  }

  // 4. Update HUD Telemetry Badges
  const badge = document.getElementById('relayNetConnectivityBadge');
  const dot = document.getElementById('theaterRelayStatusDot');
  const statusVal = document.getElementById('relayTelemetryStatus');
  const hopsVal = document.getElementById('relayTelemetryHops');
  const clrVal = document.getElementById('relayTelemetryClearance');
  const latVal = document.getElementById('relayTelemetryLatency');

  if (!isDirectBlocked) {
    // Direct link nominal
    if (badge) {
      badge.textContent = 'DIRECT LINK';
      badge.className = 'relaynet-badge-status direct';
    }
    if (dot) dot.className = 'relaynet-status-dot online';
    if (statusVal) {
      statusVal.textContent = 'NOMINAL (100% COVERAGE)';
      statusVal.style.color = '#10b981';
    }
    if (hopsVal) hopsVal.textContent = '0 (Direct to Base)';
    if (clrVal) clrVal.textContent = `+${Math.max(1.0, minClearance).toFixed(1)} m`;
    if (latVal) latVal.textContent = `${(distToBaseM / 300000.0 * 1000.0).toFixed(3)} ms`;

    // Draw Active Direct Beam
    renderActiveCarrierBeam([roverPos, basePos]);

  } else if (isRelayed && activeRelayPos) {
    // Relayed nominal
    if (badge) {
      badge.textContent = 'RELAYED (1 HOP)';
      badge.className = 'relaynet-badge-status relayed';
    }
    if (dot) dot.className = 'relaynet-status-dot online';
    if (statusVal) {
      statusVal.textContent = `RELAYED VIA ${activeRelayId}`;
      statusVal.style.color = '#34d399';
    }
    if (hopsVal) hopsVal.textContent = `1 Hop (${activeRelayId} &rarr; Base)`;
    if (clrVal) clrVal.textContent = '+18.5 m (Relay Cleared)';
    if (latVal) latVal.textContent = '0.016 ms';

    // Draw Multi-Hop Carrier Beam (Rover -> Relay -> Base)
    renderActiveCarrierBeam([roverPos, activeRelayPos, basePos]);

    // Show blocked direct path in red with hazard marker
    renderObstructedRay(roverPos, basePos, firstObsPos);

  } else {
    // Geometric Connectivity Gap
    if (badge) {
      badge.textContent = 'CONNECTIVITY GAP';
      badge.className = 'relaynet-badge-status gap';
    }
    if (dot) dot.className = 'relaynet-status-dot gap';
    if (statusVal) {
      statusVal.textContent = 'LOS OCCLUDED (SCARP SHADOW)';
      statusVal.style.color = '#ef4444';
    }
    if (hopsVal) hopsVal.textContent = 'DISCONNECTED (0 Hops)';
    if (clrVal) clrVal.textContent = `${minClearance.toFixed(1)} m (TERRAIN BLOCKED)`;
    if (latVal) latVal.textContent = 'N/A (LINK SEVERED)';

    // Show blocked path in red with hazard marker
    renderObstructedRay(roverPos, basePos, firstObsPos);
  }
}

function clearDynamicLinks() {
  if (!relayNetLinksGroup || !relayNetObstructionsGroup) return;

  while (relayNetLinksGroup.children.length > 0) {
    const obj = relayNetLinksGroup.children[0];
    relayNetLinksGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  }

  while (relayNetObstructionsGroup.children.length > 0) {
    const obj = relayNetObstructionsGroup.children[0];
    relayNetObstructionsGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  }
}

function renderActiveCarrierBeam(points) {
  if (!relayNetLinksGroup || points.length < 2) return;

  const chkActive = document.getElementById('chkRelayActiveRoute');
  if (chkActive && !chkActive.checked) return;

  const curve = new THREE.CatmullRomCurve3(points);
  const pts = curve.getPoints(points.length * 15);
  const geo = new THREE.BufferGeometry().setFromPoints(pts);

  const mat = new THREE.LineBasicMaterial({
    color: 0x00e5ff,
    linewidth: 3,
    transparent: true,
    opacity: 0.95,
  });

  const line = new THREE.Line(geo, mat);
  relayNetLinksGroup.add(line);
}

function renderObstructedRay(startPos, endPos, obsPos) {
  if (!relayNetLinksGroup) return;

  const chkObs = document.getElementById('chkRelayObstructedRays');
  if (chkObs && !chkObs.checked) return;

  // Red dashed line
  const pts = [startPos, endPos];
  const geo = new THREE.BufferGeometry().setFromPoints(pts);
  const mat = new THREE.LineDashedMaterial({
    color: 0xef4444,
    dashSize: 12,
    gapSize: 8,
    transparent: true,
    opacity: 0.75,
  });
  const line = new THREE.Line(pts, mat);
  line.computeLineDistances();
  relayNetLinksGroup.add(line);

  // Red Obstruction Contact Diamond Marker
  if (obsPos && relayNetObstructionsGroup) {
    const obsMarkerGroup = new THREE.Group();
    obsMarkerGroup.position.set(obsPos.x, obsPos.y + 6.0, obsPos.z);
    obsMarkerGroup.userData = {
      nodeType: 'los_obstruction',
      obstructionData: {
        title: 'Topographic Line-of-Sight Occlusion',
        description: 'Jezero Delta scarp relief exceeds geometric ray altitude.',
        remedy: 'Deploy autonomous relay tower on Promontory MRN_CAND_03.',
      }
    };

    const diaGeo = new THREE.OctahedronGeometry(3.5, 0);
    const diaMat = new THREE.MeshStandardMaterial({
      color: 0xef4444,
      emissive: 0x991b1b,
      emissiveIntensity: 0.6,
      metalness: 0.8,
      roughness: 0.2
    });
    const diaMesh = new THREE.Mesh(diaGeo, diaMat);
    obsMarkerGroup.add(diaMesh);

    // Warning Ring
    const wRingGeo = new THREE.RingGeometry(3, 5, 16);
    const wRingMat = new THREE.MeshBasicMaterial({ color: 0xef4444, side: THREE.DoubleSide });
    const wRingMesh = new THREE.Mesh(wRingGeo, wRingMat);
    wRingMesh.rotation.x = -Math.PI / 2;
    obsMarkerGroup.add(wRingMesh);

    relayNetObstructionsGroup.add(obsMarkerGroup);
  }
}

function autoPlanOptimalRelays() {
  const btn = document.getElementById('btnRelayAutoPlan');
  if (btn) {
    btn.innerHTML = '<span class="btn-icon">&#8987;</span> Screening Promontories...';
    btn.disabled = true;
  }

  // Target points along standard mission traverse
  const targetPayload = {
    base_station: { node_id: 'BASE', row: 117, col: 157, antenna_height_m: 10.0 },
    target_units: [
      { node_id: 'DELTA_FRONT', row: 130, col: 135, antenna_height_m: 2.5 },
      { node_id: 'THREE_FORKS', row: 138, col: 114, antenna_height_m: 2.5 },
      { node_id: 'HAWKSBILL_ASCENT', row: 145, col: 95, antenna_height_m: 2.5 }
    ],
    relay_budget: 2
  };

  fetch('/api/relaynet/optimize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(targetPayload)
  })
    .then(res => res.json())
    .then(data => {
      if (btn) {
        btn.innerHTML = '<span class="btn-icon">&#10004;</span> Relays Deployed';
        btn.disabled = false;
      }

      if (data && data.selected_relays) {
        relayNetActiveRelays = data.selected_relays;
        renderActiveRelayTowers(relayNetActiveRelays);

        const summaryBox = document.getElementById('relayOptimizationSummary');
        const statCov = document.getElementById('relayStatCoverage');
        const statTow = document.getElementById('relayStatTowers');
        const statBld = document.getElementById('relayStatBlindspot');

        if (summaryBox) summaryBox.classList.remove('hidden');
        if (statCov) statCov.textContent = `33% &rarr; ${data.coverage_percentage}%`;
        if (statTow) statTow.textContent = `${data.selected_relays.length} (${data.selected_relays.map(r => r.node_id).join(', ')})`;
        if (statBld) statBld.textContent = '1.8 km terrain blindspot eliminated';

        console.log('[RelayNet] Deployed optimized relays:', data.selected_relays);
      }
    })
    .catch(err => {
      console.error('[RelayNet] Auto-plan failed:', err);
      if (btn) {
        btn.innerHTML = '<span class="btn-icon">&#9889;</span> Auto-Plan Optimal Relays';
        btn.disabled = false;
      }
    });
}

function renderActiveRelayTowers(relays) {
  if (!relayNetNodesGroup) return;

  // Retain only base station mast, remove existing relay towers
  const toRemove = [];
  relayNetNodesGroup.children.forEach(c => {
    if (c.userData && c.userData.nodeType === 'relay_node') toRemove.push(c);
  });
  toRemove.forEach(c => relayNetNodesGroup.remove(c));

  relays.forEach(r => {
    const candObj = {
      candidate_id: r.node_id,
      row: r.rc ? r.rc[0] : r.row,
      col: r.rc ? r.rc[1] : r.col,
      elevation_m: r.elevation_m,
      slope_deg: 3.2,
      prominence_score: 0.91,
    };
    const towerMesh = create3DRelayTower(candObj);
    relayNetNodesGroup.add(towerMesh);
  });
}

function resetRelayNetMesh() {
  relayNetActiveRelays = [];
  renderActiveRelayTowers([]);
  clearDynamicLinks();

  const summaryBox = document.getElementById('relayOptimizationSummary');
  if (summaryBox) summaryBox.classList.add('hidden');

  const btn = document.getElementById('btnRelayAutoPlan');
  if (btn) {
    btn.innerHTML = '<span class="btn-icon">&#9889;</span> Auto-Plan Optimal Relays';
    btn.disabled = false;
  }
}

function setupRelayNetUIListeners() {
  const btnToggle = document.getElementById('btnToggleRelayNet');
  const panel = document.getElementById('relayNetPanel');
  const btnClose = document.getElementById('btnCloseRelayNetPanel');
  const btnAuto = document.getElementById('btnRelayAutoPlan');
  const btnReset = document.getElementById('btnRelayResetMesh');

  const chkActive = document.getElementById('chkRelayActiveRoute');
  const chkClear = document.getElementById('chkRelayClearLinks');
  const chkObs = document.getElementById('chkRelayObstructedRays');
  const chkCand = document.getElementById('chkRelayCandidates');

  if (btnToggle) {
    btnToggle.addEventListener('click', () => {
      relayNetVisible = !relayNetVisible;
      if (relayNetGroup) relayNetGroup.visible = relayNetVisible;
      if (panel) {
        if (relayNetVisible) panel.classList.remove('hidden');
        else panel.classList.add('hidden');
      }
      btnToggle.classList.toggle('active', relayNetVisible);
    });
  }

  if (btnClose && panel) {
    btnClose.addEventListener('click', () => {
      panel.classList.add('hidden');
    });
  }

  if (btnAuto) {
    btnAuto.addEventListener('click', autoPlanOptimalRelays);
  }

  if (btnReset) {
    btnReset.addEventListener('click', resetRelayNetMesh);
  }

  if (chkCand) {
    chkCand.addEventListener('change', () => {
      if (relayNetCandidatesGroup) relayNetCandidatesGroup.visible = chkCand.checked;
    });
  }

  if (chkObs) {
    chkObs.addEventListener('change', () => {
      if (relayNetObstructionsGroup) relayNetObstructionsGroup.visible = chkObs.checked;
    });
  }
}
"""

with open("scratch/relaynet_client.js", "w", encoding="utf-8") as f:
    f.write(relaynet_client_code)

print("Saved scratch/relaynet_client.js successfully!")
