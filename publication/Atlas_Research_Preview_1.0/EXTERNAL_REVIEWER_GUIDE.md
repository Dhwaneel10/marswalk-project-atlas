# Project Atlas: External Research Reviewer Guide & Challenge Kit

**Document ID:** `ATLAS-DOC-REV-001`  
**Classification:** Independent Reviewer Package & Evaluation Handbook  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)  
**Target Audience:** Planetary Scientists, Aerospace Engineers, Research Software Evaluators

---

## 1. The 13 Reviewer Core Questions

### Q1: What is Project Atlas?
Project Atlas (MarsWalk 2.0) is an open-source, modular research simulation framework designed to model multi-sol autonomous surface exploration, multi-agent fleet operations, and robotic settlement systems on Mars.

### Q2: What does it simulate?
It simulates terrain-constrained rover navigation, autonomous rotorcraft flight dynamics, active scientific discovery via Bayesian inference, deep-space communication delays, nuclear and solar power distribution, in-situ resource utilization (ISRU), and autonomous fault recovery.

### Q3: Which data are real?
- USGS Context Camera (CTX) 20 m/pixel Digital Terrain Model (`data/processed/jezero_ready_20m.tif`).
- Mars 2020 Perseverance MEDA atmospheric observations (pressure, temperature, wind, optical depth $\tau$).
- IAU 2000 planetary feature gazetteer (2,061 Martian landmarks).
- USGS Viking MDIM 2.1 global color basemap and MOLA topography.

### Q4: Which outputs are synthetic?
- Rover and rotorcraft trajectories, velocities, and waypoint arrivals.
- Dynamic battery state of charge (SOC %) and Kilopower electrical distributions.
- Quantities of manufactured regolith blocks and extracted water/oxygen.
- Simulated discrete fault occurrences and recovery actions.

### Q5: What is the scientific basis?
Published peer-reviewed literature:
- Horn (1981) for 8-neighborhood terrain slope gradient convolution.
- Balaram et al. (2021) for Martian rotorcraft momentum theory and blade compressibility in $CO_2$.
- Rodriguez-Manfredi et al. (2021) for MEDA atmospheric profiles.
- McClure et al. (2020) for the NASA Kilopower fission reactor baseline.
- Shannon (1948) for information entropy bits in active learning.

### Q6: What are the physical model assumptions?
- Hypsometric atmospheric scale height $H_\rho = 11.1\text{ km}$.
- Speed of sound in Martian $CO_2$ ($a \approx 226.2\text{ m/s}$ at $T = 210\text{ K}$).
- Point-mass 3-DOF aerodynamic drag with empirical subsonic compressibility corrections ($M_{\text{tip}} < 0.75$).
- Stoichiometric chemical reaction conversion for MOXIE ($2CO_2 \to 2CO + O_2$) and Sabatier ($CO_2 + 4H_2 \to CH_4 + 2H_2O$).
- Specific microwave sintering energy requirement: $1.4\text{ kWh per 20 kg block}$ ($70\text{ kWh/tonne}$).

### Q7: How is mission state represented?
Through a 4-tier state twin model within [`UnifiedMissionStateManager`](file:///e:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/atlas_mission_state.py):
1. `PhysicalSimulationState`: True ground reality on Mars.
2. `EarthReportedState`: Delayed telemetry as perceived by Earth Mission Control.
3. `PredictedState`: Forward numerical projections.
4. `PlannedState`: Compiled DAG tasks and active milestones.

### Q8: How are commands delayed?
Via a deterministic discrete-event min-heap priority queue (`MissionEventCoordinator`). Commands dispatched from Earth are delayed by simulated one-way light-time ($OWLT = 3\text{ to }22\text{ min}$) and evaluated against the expected state hash upon arrival.

### Q9: How does the platform deal with uncertainty?
- Sensor readings carry explicit uncertainty standard deviations $\sigma$.
- Scientific discovery uses Bayesian odds updating, measuring epistemic uncertainty reduction in Shannon entropy bits.
- Telemetry drift between Mars ground truth and Earth reported state sets `is_synchronized = False` when thresholds are exceeded.

### Q10: How are failures injected?
The resilience engine injects structured failure envelopes into the discrete-event queue at specified Sols, modifying physical parameters (e.g., setting $\tau = 2.80$ to collapse solar PV power).

### Q11: How is recovery evaluated?
Autonomous Fault Detection, Isolation, and Recovery (FDIR) algorithms detect operational deficits, execute automated load-shedding (e.g. cutting the $28\text{ kWe}$ sintering line), and check that critical life-support baselines (habitat core temperature $294.15\text{ K}$) hold.

### Q12: How can the flagship mission be reproduced?
By executing a single command:
```bash
python scripts/run_flagship_mission.py
```
This executes the 60-Sol campaign, validates conservation ledgers, and generates the bit-exact root hash `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`.

### Q13: What has not been validated?
- No full non-linear aeroelastic rotor flutter or dynamic wake turbulence modeling.
- No catalyst poisoning or thermal degradation modeled in chemical ISRU.
- No human operational life-support certification; computational research heuristics only.

---

## 2. Reviewer Challenge Kit (8 Hands-On Exercises)

External reviewers are invited to execute these controlled technical challenges:

### Exercise 1: Reproduce the Clean Flagship Mission
- **Command:** `python scripts/run_flagship_mission.py`
- **Expected Output:** Root hash `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`, Phase F Readiness $100.0\%$, Mass Discrepancy $0.000000\text{ kg}$.

### Exercise 2: Controlled Reactor Throttle Perturbation
- **Command:** `python scripts/run_flagship_mission.py --perturb-power-kw 20.0 --output-dir data/workspaces/test_perturb`
- **Expected Output:** Root hash diverges explainably to `c34011dc536adcbb6562991b5440031919a5bb9dabb6fca1da4e11bd8981b53c`, Phase F Readiness drops to $92.0\%$ (DEGRADED).

### Exercise 3: Verify Offline Validation Mode
- **Command:** `python scripts/run_flagship_mission.py --validate-only`
- **Expected Output:** Confirms input file presence and SHA-256 hash match without executing simulation steps.

### Exercise 4: Inspect Stale Command Rejection Under Delay
- **Execution:** Dispatch a command tagged with an obsolete state hash while the mission clock is advanced.
- **Expected Output:** Command state transitions to `REJECTED_STALE_HASH`; execution aborted.

### Exercise 5: Test Unsupported Resource Allocation
- **Execution:** Attempt to allocate $5,000\text{ kg}$ of water when storage is $3,440.5\text{ kg}$.
- **Expected Output:** System raises `ResourceExhaustionError`; reserves remain strictly bounded.

### Exercise 6: Bayesian Science Likelihood Stress Test
- **Execution:** Ingest an observation with neutral likelihood ratio ($\Lambda = 1.0$).
- **Expected Output:** Hypothesis posterior probability remains exactly equal to prior; Shannon entropy gain $\Delta I = 0.000\text{ bits}$.

### Exercise 7: Run Full Automated Verification Suite
- **Command:** `pytest -q`
- **Expected Output:** 1,116 passed tests in $\approx 230\text{ seconds}$ with zero failures.

### Exercise 8: Run 12-Point Preflight Diagnostic Check
- **Command:** `python scripts/preflight_check.py --port 3000`
- **Expected Output:** 12/12 checkpoints passed in $< 600\text{ ms}$.
