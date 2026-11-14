import sys
import os

def main():
    with open('scratch/relaynet_client.js', 'r', encoding='utf-8') as f:
        client_code = f.read()

    with open('web/app.js', 'r', encoding='utf-8') as f:
        app_code = f.read()

    # Backup original before modifying
    with open('web/app.js.bak13d_orig', 'w', encoding='utf-8') as f:
        f.write(app_code)

    # 1. Update applyPlaybackFrame
    target1 = """        lastTriggeredEventKey = eventKey;
      }
    }
  }

  function updateMissionPlayback(frameTime) {"""

    repl1 = """        lastTriggeredEventKey = eventKey;
      }

      // Milestone 13D: RelayNet dynamic mission connectivity playback hook
      if (typeof updateRelayNetPlayback === 'function') {
        updateRelayNetPlayback(timeSeconds, state);
      }
    }
  }

  function updateMissionPlayback(frameTime) {"""

    assert target1 in app_code, "Target 1 not found"
    app_code = app_code.replace(target1, repl1, 1)
    print("Step 1 (applyPlaybackFrame) patched.")

    # 2. Update 5-tier raycaster
    target2 = """      if (!hitHandled && disruptionHazardMesh && disruptionHazardMesh.visible) {
        const hazardHits = raycaster.intersectObjects(disruptionHazardMesh.children);
        if (hazardHits.length > 0) {
          showTheaterSpatialInspector('hazard', disruptionHazardMesh, hazardHits[0].point);
          hitHandled = true;
        }
      }
      if (!hitHandled) {"""

    repl2 = """      if (!hitHandled && disruptionHazardMesh && disruptionHazardMesh.visible) {
        const hazardHits = raycaster.intersectObjects(disruptionHazardMesh.children);
        if (hazardHits.length > 0) {
          showTheaterSpatialInspector('hazard', disruptionHazardMesh, hazardHits[0].point);
          hitHandled = true;
        }
      }
      // Milestone 13D: Raycast RelayNet Nodes, Candidate Promontories, and Obstructions
      if (!hitHandled && relayNetNodesGroup && relayNetNodesGroup.visible) {
        const rnHits = raycaster.intersectObjects(relayNetNodesGroup.children, true);
        if (rnHits.length > 0) {
          let topObj = rnHits[0].object;
          while (topObj.parent && topObj.parent !== relayNetNodesGroup) topObj = topObj.parent;
          if (topObj.userData && topObj.userData.relayData) {
            showTheaterSpatialInspector(topObj.userData.nodeType || 'relay_node', topObj.userData.relayData, rnHits[0].point);
            hitHandled = true;
          }
        }
      }
      if (!hitHandled && relayNetCandidatesGroup && relayNetCandidatesGroup.visible) {
        const candHits = raycaster.intersectObjects(relayNetCandidatesGroup.children, true);
        if (candHits.length > 0) {
          let topObj = candHits[0].object;
          while (topObj.parent && topObj.parent !== relayNetCandidatesGroup) topObj = topObj.parent;
          if (topObj.userData && topObj.userData.candidateData) {
            showTheaterSpatialInspector('candidate_relay', topObj.userData.candidateData, candHits[0].point);
            hitHandled = true;
          }
        }
      }
      if (!hitHandled && relayNetObstructionsGroup && relayNetObstructionsGroup.visible) {
        const obsHits = raycaster.intersectObjects(relayNetObstructionsGroup.children, true);
        if (obsHits.length > 0) {
          let topObj = obsHits[0].object;
          while (topObj.parent && topObj.parent !== relayNetObstructionsGroup) topObj = topObj.parent;
          if (topObj.userData && topObj.userData.obstructionData) {
            showTheaterSpatialInspector('los_obstruction', topObj.userData.obstructionData, obsHits[0].point);
            hitHandled = true;
          }
        }
      }
      if (!hitHandled) {"""

    assert target2 in app_code, "Target 2 not found"
    app_code = app_code.replace(target2, repl2, 1)
    print("Step 2 (5-tier raycaster) patched.")

    # 3. Update showTheaterSpatialInspector
    target3 = """      if (citation) citation.textContent = 'Apollo Waligora Metabolic Cost Model (1972)';
    }

    card.classList.remove('hidden');
  }"""

    repl3 = """      if (citation) citation.textContent = 'Apollo Waligora Metabolic Cost Model (1972)';
    } else if (type === 'base_station') {
      if (typeBadge) typeBadge.textContent = 'CENTRAL BASE TRANSCEIVER';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Facility:</span><span class="theater-inspector-val">${data.label || 'Base Station'}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Grid Location:</span><span class="theater-inspector-val">Row ${data.row}, Col ${data.col}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Base Elevation:</span><span class="theater-inspector-val">${Number(data.elevation_m).toFixed(1)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Mast Height:</span><span class="theater-inspector-val">${Number(data.antenna_height_m).toFixed(1)} m (Transceiver Z: ${Number(data.effective_z_m).toFixed(1)} m)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Operating State:</span><span class="theater-inspector-val" style="color:#00e5ff;">ONLINE &bull; DIRECT/RELAY GATEWAY</span></div>
      `;
      if (citation) citation.textContent = 'Octavia E. Butler Base Landing Transceiver (Geometric Model)';
    } else if (type === 'relay_node') {
      if (typeBadge) typeBadge.textContent = 'SURFACE RELAY TOWER';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Relay Identifier:</span><span class="theater-inspector-val">${data.node_id}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Location:</span><span class="theater-inspector-val">Row ${data.row}, Col ${data.col}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Base Elevation:</span><span class="theater-inspector-val">${Number(data.elevation_m).toFixed(1)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Tower Mast:</span><span class="theater-inspector-val">${Number(data.antenna_height_m).toFixed(1)} m (Dish Z: ${Number(data.effective_z_m).toFixed(1)} m)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Backhaul Status:</span><span class="theater-inspector-val" style="color:#10b981;">CONNECTED TO BASE</span></div>
      `;
      if (citation) citation.textContent = 'Mars RelayNet Autonomous Deployment Engine';
    } else if (type === 'candidate_relay') {
      if (typeBadge) typeBadge.textContent = 'CANDIDATE PROMONTORY';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Candidate ID:</span><span class="theater-inspector-val">${data.candidate_id}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Location:</span><span class="theater-inspector-val">Row ${data.row}, Col ${data.col}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">DTM Elevation:</span><span class="theater-inspector-val">${Number(data.elevation_m).toFixed(1)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Local Slope:</span><span class="theater-inspector-val" style="color:#10b981;">${Number(data.slope_deg).toFixed(1)}° (Slope ≤ 12° Traversable)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Topographic Prominence:</span><span class="theater-inspector-val" style="color:#f59e0b;">+${Number(data.prominence_m).toFixed(1)} m above local mean</span></div>
      `;
      if (citation) citation.textContent = 'DTM Promontory Screening (20m Bilinear Grid)';
    } else if (type === 'los_obstruction') {
      if (typeBadge) typeBadge.textContent = 'TERRAIN OCCLUSION';
      body.innerHTML = `
        <div class="theater-inspector-row"><span class="theater-inspector-key">Occlusion Point:</span><span class="theater-inspector-val">Row ${Number(data.row).toFixed(1)}, Col ${Number(data.col).toFixed(1)}</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Terrain Ridge Z:</span><span class="theater-inspector-val">${Number(data.terrain_elevation_m).toFixed(1)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Ray LOS Z:</span><span class="theater-inspector-val">${Number(data.ray_elevation_m).toFixed(1)} m</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Terrain Clearance:</span><span class="theater-inspector-val" style="color:#ef4444;">${Number(data.clearance_m).toFixed(2)} m (BLOCKED)</span></div>
        <div class="theater-inspector-row"><span class="theater-inspector-key">Ray Parameter:</span><span class="theater-inspector-val">t = ${Number(data.t).toFixed(3)} (${Number(data.distance_from_source_m).toFixed(0)} m from Source)</span></div>
      `;
      if (citation) citation.textContent = 'Geometric LOS Raycasting Engine (USGS CTX DTM)';
    }

    card.classList.remove('hidden');
  }"""

    assert target3 in app_code, "Target 3 not found"
    app_code = app_code.replace(target3, repl3, 1)
    print("Step 3 (showTheaterSpatialInspector) patched.")

    # 4. Insert RelayNet Engine Code before Application Lifecycle Boot
    target4 = """  // Application Lifecycle Boot
  async function init() {"""

    repl4 = client_code + """\n\n  // Application Lifecycle Boot
  async function init() {"""

    assert target4 in app_code, "Target 4 not found"
    app_code = app_code.replace(target4, repl4, 1)
    print("Step 4 (RelayNet Engine Code) inserted.")

    # 5. Call initRelayNetEngine() in init()
    target5 = """      // Milestone 13C: Initialize Atlas 3D Mission Theater
      initMissionTheater();

      // Milestone 9H: Expose Atlas Developer & Automation API"""

    repl5 = """      // Milestone 13C: Initialize Atlas 3D Mission Theater
      initMissionTheater();

      // Milestone 13D: Initialize Atlas Mars RelayNet 3D Engine
      initRelayNetEngine();
      if (params.get('relaynet') === '1' || params.get('relaynet') === 'true') {
        const rnPanel = document.getElementById('relayNetPanel');
        if (rnPanel) rnPanel.classList.remove('hidden');
      }

      // Milestone 9H: Expose Atlas Developer & Automation API"""

    assert target5 in app_code, "Target 5 not found"
    app_code = app_code.replace(target5, repl5, 1)
    print("Step 5 (initRelayNetEngine call) patched.")

    # 6. Expose in window.__atlas
    target6 = """        // Milestone 13C: Atlas 3D Mission Theater API
        enterTheaterMode: () => enterMissionTheaterMode(),
        exitTheaterMode: () => exitMissionTheaterMode(),
        setTheaterCameraMode: (m) => setCameraDirectorMode(m),
        getTheaterCameraMode: () => getCameraDirectorMode()
      };"""

    repl6 = """        // Milestone 13C: Atlas 3D Mission Theater API
        enterTheaterMode: () => enterMissionTheaterMode(),
        exitTheaterMode: () => exitMissionTheaterMode(),
        setTheaterCameraMode: (m) => setCameraDirectorMode(m),
        getTheaterCameraMode: () => getCameraDirectorMode(),
        // Milestone 13D: Atlas Mars RelayNet API
        initRelayNetEngine: () => initRelayNetEngine(),
        loadRelayNetCandidates: () => loadRelayNetCandidates(),
        autoPlanOptimalRelays: () => autoPlanOptimalRelays(),
        resetRelayNetMesh: () => resetRelayNetMesh(),
        updateRelayNetPlayback: (t, s) => updateRelayNetPlayback(t, s),
        getRelayNetState: () => ({
          activeRelays: relayNetActiveRelays,
          candidates: relayNetCandidates,
          timeline: relayNetTimelineData
        })
      };"""

    assert target6 in app_code, "Target 6 not found"
    app_code = app_code.replace(target6, repl6, 1)
    print("Step 6 (window.__atlas exposed methods) patched.")

    with open('web/app.js', 'w', encoding='utf-8') as f:
        f.write(app_code)

    print("Successfully integrated RelayNet into web/app.js!")

if __name__ == '__main__':
    main()
