# MarsWalk 2.0 / Project Atlas — 3-Minute Video Pitch Script

**Title:** "When Mars Goes Dark: Resilient Autonomous Planetary Operations"  
**Target Duration:** Exactly 180 seconds (3:00)  
**Target Audience:** NASA Space Apps Challenge Evaluators & Planetary Operations Engineers  
**Production Resolution:** $1920 \times 1080$ @ 60 FPS  

---

## Storyboard Timeline & Voiceover Script

### [0:00 – 0:30] PART 1: THE MARTIAN CHALLENGE
- **Visual on Screen:**
  - Open on the dramatic MarsWalk landing hero overlay (`web/index.html`).
  - Camera pans over the dark, cinematic Jezero crater landscape.
  - Callout text appears: *"One-Way Light Time: 4 to 24 Minutes"*.
- **Voiceover (Confident, measured tone):**
  > "Exploring Mars is an exercise in extreme isolation. When a rover navigates Jezero crater, signals from Earth take up to 24 minutes to arrive.
  > If a sudden dust storm sweeps across the basin, or a boulder falls across a narrow canyon pass, waiting for human commands from Earth isn't just inefficient—it can be fatal to the mission.
  > Today, planetary rovers routinely stall in safe-mode for weeks. We built MarsWalk 2.0 to solve that."

---

### [0:30 – 1:15] PART 2: THE FIVE-PILLAR SCIENTIFIC FOUNDATION
- **Visual on Screen:**
  - Click `Launch Atlas →` to enter the Mission Operations Deck.
  - The 3D Three.js Jezero Crater surface loads smoothly with elevation relief.
  - Click through the Five-Pillar Operations Deck tabs:
    1. **Pillar 1:** Zoom into 20m USGS CTX elevation raster and 1m HiRISE Hawksbill Gap inset.
    2. **Pillar 2:** Toggle cyan Perseverance traverse line (33.2 km) and 10 Three Forks gold sample markers.
    3. **Pillar 3:** Click MEDA weather calibration; show Sol 89 dust storm optical depth $\tau = 2.15$.
    4. **Pillar 4:** Display SHERLOC/PIXL science targets with mineralogy badges.
- **Voiceover:**
  > "MarsWalk is not a synthetic game simulation. It is an operational workstation grounded in authentic NASA and USGS planetary archives.
  > Across five pillars of capability, we combine a 20-meter USGS digital elevation model with 1-meter HiRISE micro-hazard rasters.
  > We ingest 577 ground-truth tactical positions from the Perseverance rover, verify all ten titanium sample tubes at Three Forks, and model atmospheric solar decay using real MEDA in-situ weather data from the Sol 89 regional dust storm.
  > And every calculation distinguishes primary measured data from simulation heuristics."

---

### [1:15 – 2:15] PART 3: THE SIGNATURE CRISIS — "WHEN MARS GOES DARK"
- **Visual on Screen:**
  - Open the **Evaluator Golden Path Tour** (`#btnGoldenPathTour`).
  - Advance to Step 5: Multi-Objective Science Trade-off.
    - Show side-by-side comparison: *High-Science Route* (3.26 km, +160 pts astrobiology yield) vs *Direct-Transit* (2.11 km, minimal science).
  - Advance to Step 6: Flagship Autonomous Resilience.
    - Click `▶ EXECUTE STEP ACTION`.
    - Live animation runs: Rover moves along the floor.
    - Red hazard banner appears: *"SCARP ROCKFALL DETECTED — CORRIDOR CLOSED"*.
    - Rover calculates autonomous alternate vector through Hawksbill Gap.
    - Radio signal drops: *"TOPOGRAPHIC RF OCCULTATION — LOS SEVERED"*.
    - DTN status turns gold: *"RFC 9171 CUSTODY ACTIVATED — 0 KB LOST"*.
    - Rover ascends Ridge Terrace; radio link re-establishes: *"COMMS RESTORED"*.
- **Voiceover (Dynamic, urgent yet reassuring):**
  > "Here is MarsWalk in action during our signature crisis scenario: 'When Mars Goes Dark'.
  > Departing Three Forks, the vehicle trades off energy against astrobiological reward. When an unexpected rockfall collapses the primary ascent corridor, MarsWalk does not wait 24 minutes for Earth. Its on-board A-star engine autonomously recalculates a safe detour through Hawksbill Gap.
  > Moments later, deep crater walls sever line-of-sight communications. Under standard protocols, telemetry would be dropped. But MarsWalk activates Delay-Tolerant Networking custody transfer, buffering every sample spectrum in flash storage.
  > At Ridge Terrace, line-of-sight is restored. All science packages are downlinked intact—with zero bytes lost."

---

### [2:15 – 2:45] PART 4: CRYPTOGRAPHIC VERIFICATION & CLEAN-ROOM REPRODUCTION
- **Visual on Screen:**
  - Advance to Step 7: Cryptographic Proof.
  - Show the green certificate with the SHA-256 Merkle root hash:
    `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`.
  - Cut briefly to terminal split-screen showing `./scripts/release_preflight.sh` passing all 9 quality gates in under 45 seconds.
- **Voiceover:**
  > "How do we prove this outcome is real? MarsWalk records every operational transition into a tamper-evident SHA-256 Merkle tree.
  > Across every run and any compliant computer, the final state generates the exact same certified cryptographic root hash.
  > Our clean-room tests verify that anyone can download the release package, run our setup script, and reproduce this entire demonstration completely offline with zero external dependencies."

---

### [2:45 – 3:00] PART 5: CONCLUSION & VISION
- **Visual on Screen:**
  - Wide pull-back shot of the 3D Mars globe with the illuminated traverse route shining against the red planet.
  - Final title card appears:
    *MARSWALK 2.0 • PROJECT ATLAS*
    *Real Mars Science. Autonomous Resilience.*
    *NASA International Space Apps Challenge 2026*
- **Voiceover (Inspiring, forward-looking):**
  > "As NASA prepares for Mars Sample Return and the next era of robotic and human planetary exploration, autonomous resilience is no longer optional—it is essential.
  > MarsWalk 2.0 brings genuine Mars data, mathematical rigor, and mission survival together.
  > Thank you."

---

## Production Recording Notes
- **Audio Track:** Ambient, subtle sci-fi cinematic synth score at $-22\,\text{dB}$ under voiceover.
- **Mouse Clicks:** Clean, deliberate UI interactions without rapid cursor shaking.
- **Terminal Demonstrations:** Run with clear 14pt monospace font in high contrast.
