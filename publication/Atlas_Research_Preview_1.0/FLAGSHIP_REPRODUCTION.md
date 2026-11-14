# Project Atlas — Flagship Mission Reproduction Guide

Campaign Identifier: ATLAS-MARS-BASE-ALPHA-001
Horizon: 60 Martian Sols across 12 Operational Phases
Target Feature: Jezero Crater Western Delta Outwash

## One-Command Execution
```bash
python scripts/run_flagship_mission.py
```

## Expected Verification Outputs
1. Merkle Root Hash:
   `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`
2. Phase F Readiness Score: 100.0% (QUALIFIED)
3. Net Mass Balance Error: 0.000000 kg (strictly <= 1e-4 kg)
4. Sintered Regolith Blocks: 420 blocks produced
5. Hypotheses Empirically Confirmed: 2 (Delta Scarp & Seitah)

## Offline Verification Mode
```bash
python scripts/run_flagship_mission.py --validate-only
```

## Sensitivity Test (Controlled Power Throttle)
```bash
python scripts/run_flagship_mission.py --perturb-power-kw 20.0 --output-dir data/workspaces/test_perturb
```
Expected Result: Explainable causal divergence to hash `c34011dc536adcbb6562991b5440031919a5bb9dabb6fca1da4e11bd8981b53c` and Readiness 92.0% (DEGRADED).
