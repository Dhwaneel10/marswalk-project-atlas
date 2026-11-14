# MARSWALK 2.0 / PROJECT ATLAS
### Planetary Surface Intelligence & Resilient Mission Operations for Mars

**NASA International Space Apps Challenge 2026** | **Release:** `v2.0.0-rc1` (Clean-Room Certified)

---

### The Mission Dilemma
Robotic exploration on Mars cannot rely on real-time Earth guidance: **One-Way Light Time (OWLT) ranges from 4 to 24 minutes**. When sudden environmental hazards strike—such as regional dust storms blocking solar panels or unexpected scarp rockfalls obstructing delta ascents—current rovers enter precautionary safe modes that cost weeks of mission time. Furthermore, line-of-sight RF communications are regularly severed by Martian topography.

### The Innovation
**MarsWalk 2.0 / Project Atlas** transforms planetary operations by coupling **authentic NASA and USGS planetary datasets** with an **autonomous multi-objective resilience engine**. Built on actual 20m CTX regional elevation grids, 1m HiRISE micro-hazard digital terrain models, and Mars 2020 Perseverance telemetry, MarsWalk enables exploration vehicles to self-navigate, trade off energy versus astrobiological reward, survive dust storms, and preserve 100% of collected data through communications blackouts.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 MARSWALK FIVE PILLARS                   │
                  ├────────────────────────────┬────────────────────────────┤
                  │ 1. TERRAIN INTELLIGENCE    │ 2. ROVER GROUND TRUTH      │
                  │ USGS CTX (20m) & HiRISE    │ 577 PDS rover places, 33km │
                  │ (1m) DTMs; 15° roll cutoff │ traverse, 10-tube depot    │
                  ├────────────────────────────┼────────────────────────────┤
                  │ 3. ENVIRONMENTAL INTEL     │ 4. SCIENCE PLANNING        │
                  │ Mars 2020 MEDA Sol 89 dust │ Multi-objective A* Pareto  │
                  │ storm (tau=2.15, -81.2°C)  │ optimizer (+160 pts yield) │
                  ├────────────────────────────┴────────────────────────────┤
                  │ 5. AUTONOMOUS MISSION RESILIENCE ("WHEN MARS GOES DARK")│
                  │ RFC 9171 DTN custody transfer • Autonomous rockfall     │
                  │ detour • Cryptographic Merkle audit chain (0380a7cf...) │
                  └─────────────────────────────────────────────────────────┘
```

### Key Differentiators
- **Real Science, Not Synthetic Games:** Every elevation cell, rover waypoint, and weather measurement is derived from certified USGS and NASA PDS archives with verifiable DOIs and SHA-256 digests.
- **Epistemological Truth Disclosure:** Programmatically distinguishes primary measurements from derived quantities and simulation heuristics.
- **Cryptographic State Integrity:** Every operational state transition is hashed into an immutable Merkle tree, enabling bit-exact replay and verification across any compliant workstation.
- **100% Offline Portability:** Self-contained, lightweight Python 3.10+ engine and Three.js 3D WebGL cockpit with zero external database or cloud dependencies.

### Signature Demonstration: "When Mars Goes Dark"
In a 60-Sol Jezero delta crisis simulation, a rover navigates from Three Forks Base to the Delta Crest:
1. **Sol 89 Dust Storm:** Optical depth spikes to $\tau = 2.15$ ($71.3\%$ solar loss); vehicle shifts to survival power.
2. **Escarpment Rockfall:** Main corridor blocked; on-board A* calculates an autonomous alternate route via Hawksbill Gap.
3. **RF Occultation:** Line-of-sight communications severed by crater walls; DTN engine buffers bundles without data loss.
4. **Relay Recovery:** Vehicle reaches Ridge Terrace; RF connection restored; all science telemetry verified bit-exact.

---
**Quick-Start Command:** `./scripts/setup_atlas.sh && ./scripts/start_atlas.sh --port 3000`  
**Web Cockpit:** `http://localhost:3000` (Launch "★ EVALUATOR TOUR")
