# Campaign Event Processing & Idempotency Specification
**MarsWalk 2.0 / Project Atlas • Milestone 13H**

---

## 1. Overview & Event Classification

The Atlas Campaign Operations Director processes mission occurrences as discrete, structured events. The engine implements 19 standardized event types:

| Category | Event Types | Description |
| :--- | :--- | :--- |
| **Mobility** | `TRAVERSE_STARTED`, `TRAVERSE_PROGRESS`, `TRAVERSE_COMPLETED` | Rover movement along planned terrain coordinates |
| **Science** | `SCIENCE_DWELL_STARTED`, `INSTRUMENT_OPERATING`, `SCIENCE_DWELL_COMPLETED` | Target sampling, laser spectrometer, core drill |
| **Storage & RF** | `DATA_GENERATED`, `DATA_BUFFERED`, `TRANSFER_STARTED`, `TRANSFER_COMPLETED` | Byte creation, memory buffer queuing, ground pass |
| **Infrastructure** | `RELAY_DEPLOY_STARTED`, `RELAY_DEPLOY_COMPLETED` | Surface tower erection and link verification |
| **Contingency** | `CORRIDOR_BLOCKED`, `RELAY_OUTAGE`, `INSTRUMENT_OFFLINE`, `BATTERY_ANOMALY` | Operational hazards triggering replanning |
| **Operations** | `BIVOUAC_STARTED`, `BIVOUAC_COMPLETED`, `SOL_COMPLETED` | Daily rest, thermal hold, sol boundary rollover |

---

## 2. Idempotency & SHA-256 Event Deduplication

To prevent double-deducting battery energy, corrupting storage registers, or double-visiting scientific targets when network retries occur, every event payload is assigned a deterministic fingerprint:

$$\text{Fingerprint} = \text{SHA256}(\text{campaign\_id} \parallel \text{sol\_index} \parallel \text{event\_type} \parallel \text{seq} \parallel \text{canonical\_json}(\text{payload}))$$

When `record_event(event)` is invoked:
1. The fingerprint is computed using SHA-256.
2. If `fingerprint in self.processed_event_fingerprints`, the engine logs a duplicate warning and returns immediately with `idempotent_cached=True` without mutating state.
3. If new, the event is appended to `self.event_log`, added to the set, and routed to the corresponding state reducer (`apply_event`).

---

## 3. Reducer State Transitions

- **`TRAVERSE_COMPLETED`**: Decrements battery energy by computed segment watt-hours, advances odometer, and updates rover $(x, y, z)$ position.
- **`DATA_GENERATED`**: Increments `storage_used_mb` by data volume. Fails constraints if $S_{\text{used}} > S_{\text{cap}}$.
- **`TRANSFER_COMPLETED`**: Decrements `storage_used_mb` by transferred megabytes and releases data product records.
- **`RELAY_DEPLOY_COMPLETED`**: Adds mast $(x, y, z)$ to active relay visibility set and recomputes network visibility graph.
- **`SOL_COMPLETED`**: Applies overnight battery recharge up to physical ceiling, resets daily clock, and increments active sol index.
