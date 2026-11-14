# MarsWalk 2.0 / Project Atlas — Mission Design Studio 2.0 User Guide

## 1. Getting Started

Navigate to Atlas in your browser:
```
http://127.0.0.1:3000/?tab=design_studio
```
Or click the **🎯 Design Studio** tab in the inspector tab bar.

---

## 2. Step-by-Step Operator Workflow

```mermaid
flowchart TD
    Step1["Step 1: Enter Natural Language Intent or Select Preset"] --> Step2["Step 2: Adjust Fleet & Resource Sliders"]
    Step2 --> Step3["Step 3: Click 'VALIDATE INTENT'"]
    Step3 -->|Verdict VALID| Step4["Step 4: Click 'COMPILE CAMPAIGN'"]
    Step3 -->|Verdict INVALID| Fix["Review Issues & Auto-Normalize"]
    Fix --> Step3
    Step4 --> Step5["Step 5: Explore 8-Candidate Portfolio Deck"]
    Step5 --> Step6["Step 6: Inspect Directed Acyclic Task Graph (DAG)"]
    Step6 --> Step7["Step 7: Compare Trade-Off Delta Scorecard"]
    Step7 --> Step8["Step 8: Click 'PROMOTE PLAN TO FLEET' or '3D THEATER REPLAY'"]
```

### Step 1: Specify Mission Intent
- Type a mission objective brief into the text box, or select one of four calibrated presets:
  - *Western Jezero Delta 2-Rover Reconnaissance*
  - *Distributed Delta Exploration (3 Rovers)*
  - *Energy Conservative Low-Risk Survey*
  - *High-Continuity Communications Mesh*

### Step 2: Configure Physical Bounds
- Set **Rovers Count** (1 to 4 vehicles).
- Set **Duration** (1 to 10 sols).
- Set **Minimum Battery Reserve** (10% to 40% SoC).
- Set **Relay Budget** (0 to 4 relays).

### Step 3: Validate Intent
- Click **🔍 VALIDATE INTENT**.
- Review the verdict badge (`VALID`, `VALID_WITH_WARNINGS`, `INVALID`).

### Step 4: Compile Campaign
- Click **⚡ COMPILE CAMPAIGN**.
- The compiler generates 8 structurally distinct candidate configurations in $<15\text{ ms}$.

### Step 5: Select & Inspect Candidates
- Browse candidate cards (`Balanced`, `Science Maximizing`, `Energy Efficient`, etc.).
- Click any candidate to view its specific Directed Acyclic Task Graph (DAG) and critical path.
- Inspect task node telemetry (duration, energy Wh, data MB, prerequisites).

### Step 6: Promote or Replay
- Click **🚀 PROMOTE PLAN TO FLEET** to deploy to active operational fleet director.
- Click **🎬 3D THEATER TRAVERSE REPLAY** to visualize simultaneous rover traverses in the 3D terrain viewer.
