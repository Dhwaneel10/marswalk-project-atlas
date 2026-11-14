# Atlas Mission Assurance Lab User Guide

## 1. Accessing the Mission Assurance Lab

1. Launch Atlas: Open `http://127.0.0.1:3000` in Google Chrome or any modern web browser.
2. Direct URL: Navigate directly via `http://127.0.0.1:3000/?tab=assurance`.
3. Navigation Tab: Click the **MISSION ASSURANCE** tab button in the inspector tab bar (`#tabBtnMissionAssurance`). The inspector automatically enters `.cockpit-mode` to display the full analytical workbench.

---

## 2. Navigating the 6 Functional Areas

```
+---------------------------------------------------------------------------------------+
| TOP TOOLBAR: Campaign Selector | Branch Badge | [Audit Invariants] [Stress Test] [Merkle] |
+---------------------------------------------------------------------------------------+
| HUD GRID: Verdict (PASS) | Branch (main) | Robustness (94.8%) | Violations (0) | Digest |
+---------------------------------------------------------------------------------------+
| AREA A: Campaign Branch Tree & Experimental Isolation (Filter Pills & Fork Strip)     |
+---------------------------------------------------------------------------------------+
| AREA B: Counterfactual Scenario & Fault Injection Lab (12 Models & Parameter Row)     |
+---------------------------------------------------------------------------------------+
| AREA C: 3-Way Comparative Workspace (Baseline vs Disturbed vs Candidate Recovery)     |
+---------------------------------------------------------------------------------------+
| AREA D: 20-Rule Invariant Audit Scorecard (Category Pills & Quantitative Breakdown)   |
+---------------------------------------------------------------------------------------+
| AREA E: Recovery Approval & Branch Promotion Drawer (Optimistic Concurrency Guard)    |
+---------------------------------------------------------------------------------------+
| AREA F: Tamper-Evident Cryptographic Dossier (SHA-256 Manifest & Download JSON)       |
+---------------------------------------------------------------------------------------+
```

### Area A: Campaign Branch Tree & Isolation
- **Branch Filter Pills**: Filter branches by All, Active, Candidates, or Archived.
- **Fork Child Branch**: Input a branch name, select the fork sol ($1 - 5$), choose purpose (Counterfactual, Fault Injection, Re-optimization), and click **Fork Child Branch**.
- **Switch Active Branch**: Click any branch card's **Select** button to evaluate its unique state without affecting the parent campaign.

### Area B: Counterfactual Scenario Lab
- **Scenario Selector**: Select any of the 12 disturbance models (e.g., `R1_RELAY_LOSS`, `E1_BATTERY_DEGRADATION`, `M1_WHEEL_DRIVE_ANOMALY`).
- **Parameter Controls**: Adjust Target Sol ($1-5$), Severity (`LOW`, `NOMINAL`, `HIGH`, `CRITICAL`), and Delta Loss percentage.
- **Inject Fault**: Click **Inject Disturbance & Synthesize Recovery**. Atlas automatically creates a disturbed branch, calculates invariant impacts, synthesizes an optimal recovery candidate, and overlays trajectories in 3D.

### Area C: 3-Way Comparative Workspace
- **3D Layer Overlays**: Toggle checkboxes to show/hide:
  - `Baseline Route` (Solid Cyan Polyline)
  - `Disturbed Route` (Dashed Amber Polyline)
  - `Recovery Candidate` (Glowing Emerald Polyline)
  - `Fault Markers` (Rose Divergence Beacon)
- **Comparative Table**: Review side-by-side performance across Invariants, Distance, Energy Margin, Science Yield, Storage Backlog, and LOS Comms Coverage.

### Area D: 20-Rule Invariant Scorecard
- **Category Filter Pills**: Toggle between All, Energy & Power, Data & Memory, Comms & Visibility, Mobility, Science, and Replay.
- **Quantitative Audit Result**: Inspect measured numbers, safety margins, severity flags, and evidence classifications.

### Area E: Recovery Approval & Promotion Drawer
- **Sign-Off**: Enter your Flight Director call-sign and operational rationale.
- **Concurrency Guard**: Verifies parent campaign version ($v_1$).
- **Promote**: Click **Approve & Promote Candidate to Main**. The candidate plan merges into `main`, advancing its version to $v_2$.

### Area F: Tamper-Evident Dossier
- **Manifest Table**: Displays artifact filenames, SHA-256 cryptographic hashes, and byte sizes.
- **Export Package**: Click **Export Verification Package (JSON)** to download the complete audit bundle for offline verification.
