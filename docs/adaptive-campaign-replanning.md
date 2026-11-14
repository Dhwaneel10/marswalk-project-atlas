# Adaptive Campaign Replanning & Contingency Formulation
**MarsWalk 2.0 / Project Atlas • Milestone 13H**

---

## 1. Replanning Triggers & Trigger Detection

The Campaign Operations Director monitors active simulation state against five operational boundary conditions:

1. **`ENERGY_VIOLATION`**: Predicted or active battery State of Charge falls below required reserve margin ($SOC < 20\%$).
2. **`STORAGE_PRESSURE`**: Solid-state buffer fills beyond $90\%$ of physical capacity without an active relay or downlink pass.
3. **`CORRIDOR_BLOCK`**: Geomorphic hazard (rockfall, sand dune trap, excessive slope $> 25^\circ$) renders planned traverse infeasible.
4. **`RELAY_OUTAGE`**: Hardware fault or line-of-sight obstruction severs microwave communications backhaul to base station.
5. **`INSTRUMENT_OFFLINE`**: Thermal or electrical failure renders targeted scientific instrument unavailable.

When any condition is satisfied, the engine transitions the campaign lifecycle state to `REQUIRES_REPLANNING` and issues a replanning directive.

---

## 2. Alternative Plan Generation & Multi-Objective Ranking

The adaptive replanning engine synthesizes bounded alternatives within a guaranteed $< 4.0\text{ s}$ operational latency budget:

- **Alternative A (Detour Route):** Reroutes rover around spatial blockage via alternate CTX 20m DTM grid corridor. Preserves all science targets while accepting modest distance and energy increases ($+5\%$ to $+12\%$).
- **Alternative B (Target Pruning):** Drops lowest-priority scientific target along affected sortie when energy or time margins are constrained. Maximizes safety and guarantees battery recovery.
- **Alternative C (Relay Augmentation):** Deploys an additional promontory relay tower to bridge an RF blindspot caused by topographic shadow.

Each alternative computes signed operational deltas:
$$\Delta = [\Delta\text{Distance},\ \Delta\text{Duration},\ \Delta\text{Science},\ \Delta\text{Energy},\ \Delta\text{Relays}]$$

---

## 3. Plan Lineage & Atomic Promotion

When the human mission flight director selects an alternative via `accept_replanning_alternative(alt_id)`:
1. The alternative is validated against all physical constraints.
2. The campaign version number is incremented ($v_1 \to v_2$).
3. The previous plan configuration is archived in `plan_history` for full forensic traceability.
4. Active schedule and remaining sorties are atomically updated across MOCC Cockpit, 3D Mission Theater, and the API daemon.
