# Project MarsWalk — Mission Strategy Comparison & Algorithmic Explainability Report
## Strategy A (Nominal / Static Plan) vs Strategy B (Adaptive / Resilient Plan)

**Document ID:** `MARSWALK-STRATEGY-COMPARE-001`  
**Scenario Name:** `WHEN MARS GOES DARK — Jezero Crater Resilience Traverse`  
**Comparison Engine:** `src/marswalk/core/when_mars_goes_dark.py`  
**API Endpoint:** `GET /api/flagship/when-mars-goes-dark/comparison`  
**Status:** **AUDITED & BENCHMARKED**

---

## 1. Executive Summary

A critical capability of an operational planetary demonstrator is not merely reporting what happened, but providing rigorous causal explanations for **why** a particular decision was made.

This report evaluates two distinct mission planning philosophies subjected to the exact same environmental disruptions (dust storm $\tau = 3.25$, topographic RF shadow, and Hawksbill Gap scarp rockfall):

- **Strategy A — Nominal / Static Mission Execution:** The rover follows pre-planned operational commands, uses standard streaming/FIFO telemetry without delay-tolerant local custody, and does not possess autonomous terrain rerouting.
- **Strategy B — Adaptive / Resilient Mission Execution:** The rover actively senses environmental shifts, buffers packets in a 6-tier RFC 9171 DTN flash queue during carrier loss, triggers autonomous safe hold on rockfall detection, replans a lateral detour via Ridge Terrace, and flushes custody when line-of-sight is restored.

---

## 2. Head-to-Head Performance Audit Matrix

| Metric | Strategy A (Nominal / Static) | Strategy B (Adaptive / Resilient) | Unit | Resilience Advantage & Architectural Insight |
|:---|:---:|:---:|:---:|:---|
| **Mission Completion Status** | **FAILED_TRAPPED** | **COMPLETED_SUCCESS** | Operational Status | Autonomous safe hold and replanning prevented vehicle immobilisation in boulder field. |
| **Total Traverse Distance** | $990.9\,\text{m}$ (Stalled) | $2,509.6\,\text{m}$ (Goal Reached) | meters | $+214.2\,\text{m}$ lateral detour permitted safe ascent of Ridge Terrace without exceeding slope limits. |
| **Scientific Data Preservation** | **40.0%** (2 of 5 generated delivered) | **100.0%** (6 of 6 delivered) | percentage | RFC 9171 DTN local custody preserved SHERLOC Raman discovery throughout the 2.5-hour blackout. Nominal lost 3/5 generated bundles (60%) and failed to generate recovery bundle 6. |
| **Data Dropped / Lost** | **2,944 KB** (3 bundles dropped) | **0 KB** (0 bundles lost) | Kilobytes | Legacy FIFO queue overflows/discards packets when carrier drops; DTN asserts non-volatile custody. |
| **Final Battery Reserve** | **3,400 Wh** (Critical Depletion) | **7,850 Wh** (Safe Margin) | Watt-hours | Trapped vehicle in Strategy A drew continuous current trying to overcome rockfall; Strategy B preserved 4,450 Wh. |
| **Line-of-Sight RF Recovery** | **NEVER** (Remained in scarp shadow) | **RESTORED** (Ridge Terrace Sol 14.95) | Event Status | Detour deliberately routed to high-elevation terrace to clear terrain obstruction ray vector. |
| **Cryptographic Integrity Proof** | **BROKEN** (Incomplete state chain) | **QUALIFIED** (`0380a7...`) | SHA-256 | Complete 7-stage deterministic Merkle tree proves mission execution authenticity. |

---

## 3. Forensic Causal Explanations & Decision Lineage

### Decision 1: Why Was the Primary Hawksbill Ascent Channel Aborted?
- **Root Cause:** A localized scarp collapse deposited boulders across cells `(134..138, 89..93)`.
- **Active Constraint:** Surface slope along the primary channel spiked to $28.5^{\circ}$, exceeding the rover's maximum flight rule safety threshold ($15.0^{\circ}$). Navcam stereo visual odometry detected positive relief obstacles $>0.45\,\text{m}$ in height (exceeding Perseverance $0.35\,\text{m}$ belly clearance).
- **Strategy A Behavior:** Attempted to execute pre-programmed drive sequence. Traction motor current exceeded $12.5\,\text{A}$ stall threshold, triggering thermal trip. Rover became permanently trapped in the hazard zone.
- **Strategy B Behavior:** Autonomous fault engine registered `FAULT_CORRIDOR_OCCLUSION`, halted forward motion within $1.2\,\text{m}$, and triggered an immutable safe hold.

### Decision 2: Why Was the Ridge Terrace Detour Selected Over Alternative Paths?
- **Terrain Options Considered:**
  1. *Direct western assault over delta scarp:* Slope $22.4^{\circ}$ $\rightarrow$ Rejected (Violates $15.0^{\circ}$ flight rule).
  2. *Eastern retreat to crater floor:* Low slope, but adds $+1,400\,\text{m}$ distance $\rightarrow$ Rejected (Exceeds single-sol battery budget).
  3. *Northwest ascent via Ridge Terrace `(102, 110)`:* Maximum slope $14.2^{\circ}$, lateral detour distance $+214.2\,\text{m}$ $\rightarrow$ **SELECTED**.
- **Causal Lineage:** The Ridge Terrace route satisfies all three critical objective functions:
  1. Ground slope strictly within the $15.0^{\circ}$ stability envelope.
  2. Total distance ($2,509.6\,\text{m}$) within the $15\,\text{kWh}$ energy budget ($7,850\,\text{Wh}$ remaining at destination).
  3. Topographic elevation gain ($+42.6\,\text{m}$) clears the intervening terrain shoulder, restoring geometric Line-of-Sight to the Three Forks Base Station.

### Decision 3: Why Were Packets Prioritized in Strict Class Order During Custody Drain?
- **Contact Window Constraints:** Upon cresting Ridge Terrace, the UHF carrier was restored at $128\,\text{kbps}$ with an estimated 45-minute window before the next terrain dip.
- **Priority Ranking:**
  1. *Class 2 Command Sequences & Recovery Confirmation ($96\,\text{KB}$):* Sent first so Mission Operations receives vehicle health confirmation immediately.
  2. *Class 3 High-Priority Science ($768\,\text{KB}$):* SHERLOC Raman deep-UV organic spectra sent second to ensure mission primary science return.
  3. *Class 4 Routine Housekeeping ($128\,\text{KB}$):* Vehicle engineering telemetry sent third.
  4. *Class 5 Bulk Science ($2,048\,\text{KB}$):* Large Mastcam-Z multispectral imaging cubes sent last.
- **Outcome:** Even if the link had terminated prematurely after 15 minutes, 100% of critical telemetry and primary science would have been safely received at base camp. Because the link remained stable for 32 minutes, 100% of all data products were successfully transferred.

---

## 4. Scientific Honesty & Truth Disclosures

Per `marswalk-scientific-integrity` rules:
- **Terrain Data:** Topography is directly derived from USGS CTX Jezero Crater 20m DTM (PDS product ID). No synthetic elevations are fabricated.
- **Weather & Dust:** Dust storm optical depth ($\tau = 3.25$) is calibrated against Mars 2020 MEDA empirical observations during Sol 313 dust storm event, not fictional assumptions.
- **Safety Disclaimer:** While the algorithm proves mathematical and kinematic reachability under the modeled physical constraints, this simulation does **not** constitute operational clearance for actual astronaut extravehicular activity (EVA) or autonomous robotic flight operations without formal NASA mission assurance review.
