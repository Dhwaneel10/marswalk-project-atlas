# Atlas Mission Assurance Invariant Catalogue (20 Rules)

## Overview

The Mission Assurance Engine audits campaigns against 20 formal invariants spanning seven operational categories. Each rule defines an unambiguous mathematical threshold, severity rating, and evidence classification.

| Rule ID | Category | Rule Title | Severity | Threshold / Condition | Default Evidence |
|:---|:---|:---|:---|:---|:---|
| **ENG-001** | Energy & Power | Minimum Battery SOC Reserve | `CRITICAL` | $\text{SOC}_{\text{min}} \ge 20.0\%$ | `CONFIRMED` |
| **ENG-002** | Energy & Power | Daily Energy Balance Non-Negative | `CRITICAL` | $E_{\text{gen\_sol}} - E_{\text{consumed\_sol}} \ge 0.0\text{ Wh}$ | `CONFIRMED` |
| **ENG-003** | Energy & Power | Peak Thermal / Heater Power Margin | `WARNING` | $P_{\text{avail}} - P_{\text{heater\_peak}} \ge 10.0\%$ | `CONFIRMED` |
| **DATA-001** | Data Logistics | Flash Storage Buffer Non-Overflow | `CRITICAL` | $\text{Storage}_{\text{used}} \le 0.95 \cdot \text{Capacity}$ | `CONFIRMED` |
| **DATA-002** | Data Logistics | Downlink Backlog Clearance Time | `WARNING` | $T_{\text{clear\_backlog}} \le 24.0\text{ h}$ | `CONFIRMED` |
| **DATA-003** | Data Logistics | High-Priority Science Data Preservation | `CRITICAL` | $\text{Loss}_{\text{critical\_frames}} == 0.0\%$ | `CONFIRMED` |
| **COMM-001** | Communications | Geometric LOS to Relay / Direct-to-Earth | `CRITICAL` | $\text{Coverage}_{\text{geometric}} \ge 85.0\%$ | `CONFIRMED` |
| **COMM-002** | Communications | Maximum Communication Blackout Duration | `WARNING` | $T_{\text{blackout\_max}} \le 120.0\text{ min}$ | `CONFIRMED` |
| **COMM-003** | Communications | Relay Deployment Link Verification | `CRITICAL` | $\text{LinkQuality}_{\text{deployed}} \ge 90.0\%$ | `CONFIRMED` |
| **MOB-001** | Mobility | Traverse Slope Limit Adherence | `CRITICAL` | $\text{Slope}_{\text{traversed}} \le 25.0^\circ$ | `CONFIRMED` |
| **MOB-002** | Mobility | Slip Hazard Factor Feasibility | `WARNING` | $\text{SlipFactor}_{\text{terrain}} \le 0.40$ | `CONFIRMED` |
| **MOB-003** | Mobility | Kinematic Speed Budget Verification | `WARNING` | $v_{\text{cruise}} \le 0.12\text{ m/s}$ | `CONFIRMED` |
| **SCI-001** | Science | Minimum Science Utility Threshold | `WARNING` | $U_{\text{achieved}} \ge 300.0\text{ pts}$ | `CONFIRMED` |
| **SCI-002** | Science | Instrument Dwell Duration Compliance | `WARNING` | $T_{\text{dwell\_avg}} \ge 30.0\text{ min}$ | `CONFIRMED` |
| **SCI-003** | Science | Observation Slew Angle Thermal Limit | `INFO` | $\theta_{\text{slew}} \le 45.0^\circ$ | `CONFIRMED` |
| **TIME-001** | Multi-Sol Timing | Multi-Sol Sol Duration Adherence | `CRITICAL` | $T_{\text{sol\_operational}} \le 8.0\text{ h}$ | `CONFIRMED` |
| **TIME-002** | Multi-Sol Timing | Inter-Sol Night Charge Preservation | `WARNING` | $T_{\text{nocturnal\_rest}} \ge 14.0\text{ h}$ | `CONFIRMED` |
| **REP-001** | Replay & Branching | Deterministic Event Log Replay Hash Match | `CRITICAL` | $\text{Hash}(\mathbf{S}_{\text{replayed}}) == \text{Hash}(\mathbf{S}_{\text{live}})$ | `CONFIRMED` |
| **ISO-001** | Replay & Branching | Branch Parent Immutability Invariant | `CRITICAL` | $\text{Hash}(\mathbf{S}_{\text{parent\_pre}}) == \text{Hash}(\mathbf{S}_{\text{parent\_post}})$ | `CONFIRMED` |
| **CONC-001** | Replay & Branching | Optimistic Concurrency Version Monotonicity | `CRITICAL` | $v_{\text{parent\_live}} == v_{\text{expected}}$ | `CONFIRMED` |

---

## Verdict Classifications

1. **`PASS`**: The quantitative parameter strictly satisfies the mathematical threshold with positive margin.
2. **`FAIL`**: The parameter violates the safety or operational boundary. Critical failures block plan promotion.
3. **`WARN`**: The parameter operates within acceptable limits but exhibits degraded margin (e.g., $20\% \le SOC \le 25\%$).
4. **`NOT_APPLICABLE`**: The rule is contextually irrelevant (e.g., relay link verification when no relays are scheduled for deployment).

## Evidence Classifications

- **`CONFIRMED`**: Backed by measured DTM elevation, verified kinematics, or exact replay hash.
- **`DERIVED`**: Computed from empirical proxy models or line-of-sight ray tracing.
- **`UNRESOLVED`**: Parameter requires future sol execution to determine final status.
- **`CONFLICTING`**: Discrepancy observed between competing telemetry sources.
- **`MISSING`**: Required telemetry or observation event absent from the log.
