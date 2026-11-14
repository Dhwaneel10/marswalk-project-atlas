# ATLAS 13R — SCENARIO 01 TO 12 CATALOG
## Comprehensive Benchmark Specifications for Planetary Mission Resilience

**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Milestone:** 13R — Atlas Apocalypse Engine  
**Module:** `src/marswalk/core/mars_apocalypse_scenario_engine.py`  

---

### The 12 Apocalypse Scenarios

#### 1. Scenario 01: The Red Horizon (Tactical)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Fault:** `FAIL-MEC-01` (Front-Right Wheel Drive Motor Stall on 14° Slope).
- **Cascade Triggered:** `ROV_POWER_BUS_SURGE`, `ROV_SPEED_DEGRADATION`.
- **Atlas Recovery:** Electrical isolation of jammed motor; activation of 5-wheel kinematic differential drive; avoidance of slopes $> 11.5^\circ$.

#### 2. Scenario 02: Dust Devil Ambush (Operational)
- **Asset:** `AERO-INGENUITY`
- **Injected Fault:** `FAIL-PWR-01` (Atmospheric optical depth tau spikes from 0.45 to 2.85).
- **Cascade Triggered:** `AERO_SOLAR_DEPLETION`, `AERO_BATTERY_COLLAPSE`.
- **Atlas Recovery:** Immediate flight suspension; sun-aligned surface parking; heater duty cycle clamped to 42%.

#### 3. Scenario 03: Silent Orbiter (Operational)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Fault:** `FAIL-COM-01` (MRO Electra UHF Relay Transceiver Drop during 420 MB pass).
- **Cascade Triggered:** `ROV_BUFFER_OVERFLOW`, `ROV_DATA_PURGE`.
- **Atlas Recovery:** Failover to Direct-To-Earth X-band high-gain antenna; real-time 4:1 wavelet science compression. Zero data loss.

#### 4. Scenario 04: Thermal Abyss (Tactical)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Fault:** `FAIL-ENV-01` (Jezero crater floor nocturnal plunge to -98.5°C).
- **Cascade Triggered:** Thermal bus load surge.
- **Atlas Recovery:** Selective zonal heating prioritizing avionics cold-plates and MMRTG thermoelectric coupling.

#### 5. Scenario 05: Dune Crest Blindness (Tactical)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Fault:** `FAIL-NAV-01` (38% wheel slip on rippled sand crest; gyro heading drift).
- **Cascade Triggered:** Position covariance ellipse expansion.
- **Atlas Recovery:** Immediate slip stop; visual landmark resection against bedrock outcrops; slip-compensated drive commands.

#### 6. Scenario 06: False Mineral Mirage (Operational)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Fault:** `FAIL-SCI-01` (PIXL X-ray detector thermal gain drift +0.18 keV).
- **Cascade Triggered:** `SCI_FALSE_DISCOVERY` (Spurious carbonate peak identification).
- **Atlas Recovery:** Robotic arm slew to onboard titanium calibration disk; recalibration of spectral energy channels before rock drill.

#### 7. Scenario 07: Flight Computer Panic (Severe)
- **Asset:** `AERO-INGENUITY`
- **Injected Fault:** `FAIL-SW-01` (Avionics heap fragmentation approaching 1.8s watchdog timeout).
- **Cascade Triggered:** Watchdog pre-trip alert.
- **Atlas Recovery:** Warm flight software reboot; queue memory flush; flight plan resumption from non-volatile flash.

#### 8. Scenario 08: Aero Stall in Thin Air (Severe)
- **Asset:** `AERO-INGENUITY`
- **Injected Fault:** `FAIL-AER-01` (Rotor blade tip abrasion causing 18.5% lift deficit and motor overheat >85°C).
- **Cascade Triggered:** `AERO_LIFT_DEFICIT`, `AERO_MOTOR_OVERHEAT`, `AERO_EMERGENCY_DESCENT`.
- **Atlas Recovery:** Emergency sortie abort to flat terrain; permanent flight ceiling restriction to 5m; handover of aerial scouting to rover Mastcam-Z.

#### 9. Scenario 09: Dual Rover Pinch (Severe)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Faults:** `FAIL-MEC-01` + `FAIL-NAV-01` (Drive motor jam coinciding with severe sand slip).
- **Cascade Triggered:** `ROV_SPEED_DEGRADATION`, `ROV_SCHEDULE_SLIP`.
- **Atlas Recovery:** 5-wheel skid steering differential control; re-routed path around 1.2m boulder field.

#### 10. Scenario 10: Cascading Dust & Dark (Severe)
- **Assets:** `ROVER-PERSEVERANCE` + `AERO-INGENUITY`
- **Injected Faults:** `FAIL-PWR-01` + `FAIL-ENV-01` (Simultaneous tau spike and severe cold soak).
- **Cascade Triggered:** Fleet-wide power margin collapse.
- **Atlas Recovery:** Coordinated fleet power rationing; rover establishes proximity micro-climate barrier upwind of rotorcraft.

#### 11. Scenario 11: Comm Squeeze & Science Drift (Severe)
- **Asset:** `ROVER-PERSEVERANCE`
- **Injected Faults:** `FAIL-COM-01` + `FAIL-SCI-01` (UHF relay loss coinciding with PIXL calibration drift).
- **Cascade Triggered:** Buffer accumulation of invalid science spectra.
- **Atlas Recovery:** Spectrometer acquisition frozen until calibration target disk scan; flash buffer spooled to DTE.

#### 12. Scenario 12: Project Apocalypse (Flagship Signature Demonstration)
- **Assets:** `ROVER-PERSEVERANCE`, `AERO-INGENUITY`, `ORBITER-MRO`
- **Injected Faults:** **Five simultaneous & sequential failures**:
  1. `FAIL-PWR-01`: Regional dust storm tau surge (Environment / Power).
  2. `FAIL-MEC-01`: Rover front-right drive motor stall (Mobility).
  3. `FAIL-COM-01`: MRO Electra UHF transceiver dropout (Communications).
  4. `FAIL-AER-01`: Rotor blade leading-edge lift deficit (Aircraft).
  5. `FAIL-SCI-01`: PIXL spectrometer thermal calibration drift (Science Payload).
- **Cascades Triggered (9 Nodes):** `ROV_POWER_BUS_SURGE`, `ROV_SPEED_DEGRADATION`, `ROV_SCHEDULE_SLIP`, `ROV_BUFFER_OVERFLOW`, `AERO_LIFT_DEFICIT`, `AERO_MOTOR_OVERHEAT`, `AERO_EMERGENCY_DESCENT`, `AERO_SOLAR_DEPLETION`, `SCI_FALSE_DISCOVERY`.
- **Atlas Multi-Agent Recovery:**
  - 5 of 6 science objectives completed; 1 preserved & deferred; 0 abandoned.
  - Zero MB data lost (420.0 MB retained).
  - Time to recover: 272 seconds.
  - Zero resource violations; 100% mission state validity preserved.
  - Cryptographic state hash verified: `BA87A9EA97A25717`.
