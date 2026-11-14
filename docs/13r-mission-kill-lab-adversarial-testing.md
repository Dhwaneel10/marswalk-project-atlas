# ATLAS 13R — MISSION KILL LAB & ADVERSARIAL TESTING
## Red-Team Stress-Testing, Dynamic Profiles, and Counterfactual Safety

**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Milestone:** 13R — Atlas Apocalypse Engine  
**Module:** `src/marswalk/core/mars_fault_injection_engine.py`  

---

### 1. Mission Kill Lab Philosophy

Traditional space software verification relies on nominal regression testing and scripted single-fault injection. However, historical space mission losses (Mars Polar Lander, Phobos 1, Mars Climate Orbiter) demonstrated that missions fail due to unmodeled compound interactions and unexpected timing overlaps.

The **Atlas Mission Kill Lab** functions as an interactive adversarial sandbox, enabling "Red-Team" operators to dynamically stress-test the autonomy system by injecting arbitrarily severe multi-fault scenarios.

---

### 2. Counterfactual Branch Safety

A core principle established in Milestone 13I (`CounterfactualBranchManager`) and strictly adhered to in Milestone 13R is **complete branch isolation**:
- Fault injections and failure cascades NEVER mutate the live master campaign state.
- When a Red-Team operator clicks `Inject Failure` or `Run Project Apocalypse`, the engine clones the current campaign timeline into an isolated counterfactual branch:
  $$\text{Branch}_{\text{eval}} = \text{clone}(\text{Branch}_{\text{master}})$$
- All telemetry perturbations, DAG cascade propagations, and candidate recovery plans execute exclusively inside $\text{Branch}_{\text{eval}}$.
- The master campaign state remains pristine, allowing endless non-destructive what-if experiments.

---

### 3. Adversarial Attack Surfaces

The Mission Kill Lab exposes injection across all 7 operational domains:
1. **Mechanical Attack:** Force motor stalls on critical ascent slopes to test skid-steer fallback.
2. **Power Attack:** Trigger sudden optical tau increases during noon recharge windows to test battery conservation.
3. **Comms Attack:** Sever UHF links during peak science downlink passes to test flash buffer management.
4. **Thermal Attack:** Plunge chassis temperatures below heater thresholds during battery depletion.
5. **Nav Attack:** Inject 40% odometry slip to test visual landmark resection and false-hazard rejection.
6. **Instrument Attack:** Introduce +0.18 keV detector gain drift to test biogenic false-discovery rejection.
7. **Software Attack:** Fragment image processor queues to test watchdog pre-trip warm reboots.
