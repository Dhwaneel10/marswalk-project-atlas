# Project Atlas: Discrete-Event Model & Simulation Clock

**Document ID:** `ATLAS-DOC-EVT-001`  
**Classification:** Simulation Temporal Engine  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)

---

## 1. Simulation Time Standards

Project Atlas / MarsWalk 2.0 does not utilize non-deterministic wall-clock delays, async sleep functions, or threading timers for simulation state advancement. Instead, all time progression is governed by an exact discrete-event simulation clock indexed by authentic Martian temporal parameters:

1. **Martian Sol Duration:**  
   $$1\text{ Sol} = 88,775.244\text{ SI seconds} \approx 24\text{h } 39\text{m } 35.244\text{s}$$
   The scaling factor between SI seconds and Martian local seconds is:
   $$\kappa_{\text{mars}} = \frac{88,775.244}{86,400.0} \approx 1.02749125$$
2. **Mission Elapsed Time (MET):**  
   Computed as total continuous SI seconds elapsed since mission landing:
   $$MET = (Sol - 1) \cdot 88,775.244 + t_{\text{sol, seconds}}$$
3. **Solar Longitude ($L_s$):**  
   Defines the Martian seasonal position ($0^\circ \le L_s < 360^\circ$):
   $$L_s(t) = \left( L_{s,0} + \frac{360.0}{668.6} \cdot Sol \right) \pmod{360^\circ}$$
   Where $668.6\text{ Sols}$ is the length of one Martian year.

---

## 2. Event Envelope & Min-Heap Priority Ordering

All discrete actions (sensor readings, route legs, power transitions, command arrivals) are encapsulated in an `EventEnvelope`:

```python
@dataclass(order=True)
class EventEnvelope:
    sort_key: Tuple[int, float, int, str]  # (sol, sol_seconds, priority, event_id)
    event_id: str
    event_type: EventType
    sol: int
    sol_seconds: float
    priority: int  # 1 (Highest / Safety-Critical) to 10 (Background)
    parent_event_id: Optional[str]
    payload: Dict[str, Any]
    executed: bool
    execution_result: Optional[str]
```

### Deterministic Tie-Breaking Guarantee
Because `heapq` sorts tuples lexicographically:
1. Primary sort key: Target `sol` (integer).
2. Secondary sort key: Target `sol_seconds` (float, precision to milliseconds).
3. Tertiary sort key: `priority` (integer, 1 precedes 10).
4. Quaternary tie-breaker: `event_id` (deterministic string UUID).

This ensures that events scheduled for the exact same second are always executed in bit-exact, identical order across different runtime environments.
