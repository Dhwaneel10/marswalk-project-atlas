# PROJECT ATLAS — MILESTONE 13Q
# SCIENTIFIC HYPOTHESIS MODEL & LIFECYCLE SPECIFICATION
## Structured Planetary Science Inquiries, Competing Explanations & Transition Invariants

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_hypothesis_registry.py`  
**Standard:** NASA Ames / JPL Planetary Science Campaign Architecture  
**Status:** `QUALIFIED`

---

## 1. Objective and Architectural Rationale

In conventional planetary rover operations, science planners frequently execute predetermined observation sequences without explicit, machine-readable representations of the competing scientific questions being asked. When anomalies appear in downlinked data, manual human interpretation is required to formulate alternative hypotheses and devise follow-up experiments.

Milestone 13Q introduces a formal, computationally traceable **Scientific Hypothesis Management Engine**. Every planetary science investigation begins with an explicit inquiry, formalizes an ensemble of mutually competing hypotheses, attaches supporting or contradictory empirical evidence, and enforces state machine transitions with mandatory cryptographic audit records.

---

## 2. Hypothesis Lifecycle State Machine

A scientific hypothesis transitions through eight discrete states:

```
                  +--------------+
                  |   PROPOSED   |
                  +-------+------+
                          |
             +------------+------------+
             |                         |
             v                         v
     +---------------+         +---------------+
     |    ACTIVE     |         |    REJECTED   |
     +-------+-------+         +-------+-------+
             |                         |
             v                         |
   +--------------------+              |
   | UNDER_INVESTIGATION|              |
   +---------+----------+              |
             |                         |
   +---------+---------+               |
   |         |         |               |
   v         v         v               |
+------+  +------+  +--------+         |
|SUPPOR|  |WEAKEN|  |INCONCLU|         |
|TED   |  |ED    |  |SIVE    |         |
+---+--+  +---+--+  +---+----+         |
    |         |         |              |
    +---------+---------+              |
              |                        |
              v                        v
        +------------+          +--------------+
        | SUPERSEDED |<---------|  SUPERSEDED  |
        +------------+          +--------------+
```

### State Definitions:
1. `PROPOSED`: Newly formulated hypothesis; pending initial triage.
2. `ACTIVE`: Approved for active mission campaign prioritization.
3. `UNDER_INVESTIGATION`: Currently assigned targeted exploration assets (rovers, rotorcraft) or pending observational data.
4. `SUPPORTED_BY_EVIDENCE`: Empirical observations and stoichiometric analyses validate core predictions ($P > 0.85$).
5. `WEAKENED_BY_EVIDENCE`: Observational data contradicts secondary predictions or reveals low compatibility ($P < 0.20$).
6. `REJECTED`: Falsified by discriminating measurements (e.g., elemental lithochemistry, absence of diagnostic companion absorption bands).
7. `INCONCLUSIVE`: Acquired data lacks sufficient signal-to-noise ratio or spatial resolution to discriminate.
8. `SUPERSEDED`: Replaced by a more refined or comprehensive scientific model.

---

## 3. Transition Invariants and Epistemic Integrity

The state machine strictly enforces three epistemic invariants in code:

1. **No Evidence, No Support:** Attempting to transition a hypothesis from any state to `SUPPORTED_BY_EVIDENCE` without linking valid empirical evidence nodes raises a `ValueError`.
2. **Mandatory Falsification Record:** Transitioning to `REJECTED` requires at least one contradictory evidence link or a certified adversarial falsification record.
3. **Competing Hypothesis Mutuality:** Hypotheses formulated to explain the same phenomenon are linked as competing explanations. Supporting one hypothesis dynamically updates the Bayesian priors and posterior distributions of its competitors.
