# MISSION 11 — MACHINE LEARNING OPPORTUNITY & TRADE-OFF ASSESSMENT

**Project:** MarsWalk 2.0 / Project Atlas  
**Audit Standard:** NASA Technology Readiness Level (TRL) Guidelines & Flight Software Feasibility  
**Companion Document:** [`MISSION_11_ML_AND_AI_AUDIT.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_ML_AND_AI_AUDIT.md)

---

## 1. Executive Summary & Objective

While MarsWalk 2.0 currently utilizes classical deterministic AI, convex preference optimization, and physics-based terramechanics, this assessment investigates **practical, high-value opportunities for integrating modern Machine Learning (ML)** into future iterations of the platform.

Rather than proposing speculative deep learning for features that are already solved with exact analytical algorithms (such as 2D/3D A\* routing), this document identifies specific operational bottlenecks where ML offers demonstrable advantages.

---

## 2. Concrete Machine Learning Opportunities

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MARSWALK 2.0 ML INTEGRATION ROADMAP                  │
└────────────────────────────────────────────────────────────────────────┘
          │                                 │
          ▼                                 ▼
┌───────────────────────────┐     ┌───────────────────────────┐
│       OPPORTUNITY 1       │     │       OPPORTUNITY 2       │
│  Semantic Hazard Vision   │     │ Neural Surrogate Physics  │
│  (NASA AI4Mars / HiRISE)  │     │ (Fast RF Line-of-Sight)   │
└───────────────────────────┘     └───────────────────────────┘
          │                                 │
          └────────────────┬────────────────┘
                           ▼
              ┌───────────────────────────┐
              │       OPPORTUNITY 3       │
              │  Reinforcement Learning   │
              │  (Autonomous Consumables) │
              └───────────────────────────┘
```

---

### Opportunity 1: Semantic Terrain Segmentation & Wheel-Slip Prediction (NASA AI4Mars Integration)
- **Operational Need:** Currently, MarsWalk calculates surface roughness using a spatial window ($3 \times 3$) elevation standard deviation on the 20m CTX raster. However, lethal rover hazards—such as soft wind-blown sand ripples (transverse aeolian ridges / TARs) or sharp ventifact bedrock—often occur at scales beneath 20m resolution.
- **Proposed ML Solution:** Integrate a lightweight semantic segmentation Convolutional Neural Network (e.g., MobileNetV3-UNet or SegFormer-B0) trained on the public **NASA JPL AI4Mars benchmark dataset** (over 326,000 labeled surface terrain patches from Curiosity, Opportunity, and Spirit).
- **Function:** Classifies terrain pixels into 4 operational classes:
  1. *Soil / Compact Regolith* (low slip, safe)
  2. *Bedrock* (high traction, high vibration)
  3. *Sand Dunes / TARs* (high wheel sinkage, extreme entrapment hazard)
  4. *Large Boulders / Escarpments* (impassable geometric obstacles)
- **Data Availability:**
  - **Dataset:** NASA JPL AI4Mars Dataset on NASA PDS / Open Science Data Cloud.
  - **Status:** Publicly available, peer-reviewed (Swan et al., 2021).
  - **Footprint:** Pre-trained ONNX model weight $< 15\,\text{MB}$; CPU inference latency $< 120\,\text{ms}$ per tile.

---

### Opportunity 2: Neural Surrogate Model for Fast Line-of-Sight & RF Coverage Prediction
- **Operational Need:** In multi-rover or astronaut EVA operations, calculating radio frequency (RF) line-of-sight across a $2,000 \times 2,000$ elevation raster requires millions of 3D Bresenham ray-marching operations. This creates a latency bottleneck during real-time interactive UI scrubbing.
- **Proposed ML Solution:** Train a Fourier Neural Operator (FNO) or Physics-Informed Neural Network (PINN) surrogate model that maps a digital elevation patch and transmitter coordinates directly to a 2D RF coverage and diffraction mask.
- **Function:** Replaces expensive ray-tracing loops with a single forward neural tensor evaluation, reducing computation time from $1,800\,\text{ms}$ to $< 15\,\text{ms}$ (a $> 100\times$ speedup).
- **Data Availability:**
  - **Training Data:** Synthesized directly using MarsWalk's existing deterministic raytracer on USGS CTX mosaics (zero external labeling required).
  - **Footprint:** ONNX runtime model $\approx 6\,\text{MB}$; easily runs on CPU in a background WebAssembly or Python worker.

---

### Opportunity 3: Deep Reinforcement Learning for Adaptive EVA Consumable Optimization
- **Operational Need:** In dynamic dust storm emergencies ("When Mars Goes Dark"), crewed EVAs must balance competing non-linear objectives under stochastic weather: battery power, spacesuit oxygen margins, crew metabolic heat production, and rockfall bypass.
- **Proposed ML Solution:** Formulate consumable management as a Partially Observable Markov Decision Process (POMDP) solved via Proximal Policy Optimization (PPO).
- **Function:** The trained policy advises the mission commander on optimal walk/rest cycles, speed throttling, and emergency return trigger points as MEDA sensors register changing atmospheric density and wind resistance.
- **Data Availability:**
  - **Simulation Environment:** MarsWalk's existing `campaign_simulator.py` and `when_mars_goes_dark.py` provide the exact physics environment needed to generate millions of training episodes.

---

## 3. Engineering & Operational Trade-Off Analysis

| Evaluation Dimension | Classical Deterministic AI (Current MarsWalk 2.0) | Deep Learning / Neural Models (Proposed Enhancements) |
| :--- | :--- | :--- |
| **Reproducibility** | **100% Deterministic:** Identical inputs produce bit-exact identical routes across all runs. | **Stochastic / Sensitive:** Small perturbations in input features or floating-point rounding can alter outputs. |
| **Flight Certification** | **High Flight Readiness:** A\* and Horn gradients meet NASA-STD-8739.8B software assurance criteria. | **Low Flight Readiness:** Black-box neural models are extremely difficult to verify for human-rated missions. |
| **Compute & Memory** | **Minimal:** Runs in $< 200\,\text{MB}$ RAM with zero GPU/CUDA dependencies. | **Substantial:** Requires ONNX runtime, libtorch, or TensorFlow C++ runtimes ($+100\,\text{MB}$ to $+500\,\text{MB}$ package size). |
| **Safety Guarantees** | **Hard Constraints:** Impassable cliffs ($> 15^\circ$) are mathematically excluded from the open set. | **Probabilistic:** Requires hard post-processing filters to prevent model hallucination into hazards. |
| **Sub-Resolution Detail** | **Coarse:** Limited to the resolution of the raster ($20\,\text{m}$ CTX or $1\,\text{m}$ HiRISE). | **Superior:** Can infer micro-roughness, sand traps, and rock density from visual texture. |

---

## 4. Architectural Recommendation for MarsWalk Releases

1. **Retain Classical A\* as the Master Safety Gate:** Classical heuristic search must remain the non-negotiable safety spine. No neural model should ever be given unconstrained authority to plot astronaut or rover paths.
2. **Deploy ML as Upstream Feature Generators:** The optimal architecture employs ML strictly as an *upstream perception layer* (e.g., producing a traversability cost raster from imagery) that is then fed into the deterministic A\* pathfinder.
3. **Preserve Offline Self-Containment:** Any future ML models must be packaged as quantized ONNX models running via CPU-optimized runtime without requiring cloud APIs or external network calls.
