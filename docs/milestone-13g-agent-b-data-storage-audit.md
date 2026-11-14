# Milestone 13G — Agent B: Data and Storage Architecture Audit
## Onboard Data Products, Byte Conservation Accounting, Storage Policies & Simulated Transfer Engine

**Milestone:** 13G — Science Return & Data Logistics Co-Design  
**Subagent Role:** Agent B — Data and Storage Specialist  
**System:** MarsWalk 2.0 / Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Target Module:** `src/marswalk/core/mission_data_ledger.py`  
**Execution Environment:** Windows 11 (64-bit), Python 3.12.4 (`.venv`), Vanilla JS / Three.js Frontend, Atlas API on port 3000  
**Audit Date:** 2026-11-01  
**Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary & Problem Formulation

### 1.1 The Operational Data Bottleneck on Mars
In planetary surface exploration, science data collection is strictly bounded not only by instrument electrical power and traverse kinematics (addressed in Milestone 13F), but also by **finite onboard flash memory, radio link throughput, and geometric line-of-sight connectivity windows**. 

On historical Mars missions (e.g., Mars Exploration Rovers Spirit and Opportunity, Mars Science Laboratory Curiosity, Mars 2020 Perseverance), rover solid-state recorders (SSRs) are partition-managed. Science instruments—such as high-resolution multispectral cameras (Mastcam-Z), hyperspectral Raman spectrometers (SHERLOC), micro-XRF analyzers (PIXL), and ground-penetrating radar sounders (RIMFAX)—can generate gigabits of raw observational data during a single intensive contact science campaign. However:
1. **Flash Storage is Finite**: A rover's onboard solid-state storage (typically 128 GB to 512 GB in modern planetary avionics partitions) can rapidly reach saturation if high-resolution panoramas or radar sounding surveys are conducted faster than data can be offloaded.
2. **Data Cannot Be Blithely Overwritten**: In-situ scientific observations often represent irreplaceable exploration opportunities. Overwriting un-offloaded observation data causes irreversible science loss.
3. **Surface Communications Are Intermittent and Bandwidth-Constrained**: Tactical data transfer from a mobile rover to the primary surface base station (or local base habitat) is governed by line-of-sight visibility (direct or via multi-hop surface relay towers like Mars RelayNet, Milestone 13D), configured radio transceiver bitrates, framing protocol overhead, and duty cycle limitations.
4. **Data Must Be Verifiably Acknowledged Before Release**: A fundamental tenet of space flight communications is that onboard storage allocations cannot be reclaimed until an end-to-end receipt verification (cryptographic checksum or block acknowledgment) has been confirmed and logged.

### 1.2 Agent B Mandate
As Subagent B (Data and Storage), our responsibility for Milestone 13G is to audit existing MarsWalk data structures, design the complete architectural blueprint, and formulate the mathematical laws for the new core engine:
`src/marswalk/core/mission_data_ledger.py`.

This audit delivers:
1. **Data Product Identity & Tracking Model**: A robust, immutable tracking specification for every generated data product, including deterministic SHA-256 content fingerprints, direct linkages to `ScienceObservation` records, instrument attribution, physical byte sizing, and complete lifecycle state machines.
2. **Synthetic Data Volume Profiles**: Five calibrated demonstration profiles spanning small environmental telemetry ($10\text{--}50\text{ KB}$) to subsurface radar scans ($20\text{--}60\text{ MB}$), each adhering strictly to planetary science truth disclosures and marked explicitly as synthetic planning demonstrations.
3. **Exact Onboard Storage Accounting & Byte Conservation**: A mathematically rigorous byte conservation law:
   $$S_{\text{used}, t} = S_{\text{used}, t-1} + S_{\text{generated}, t} - S_{\text{released}, t}$$
   with an absolute invariant that $S_{\text{released}, t}$ is zero unless a transfer has been verified and recorded.
4. **Storage Policies & Pressure Alert State Machine**: A 5-tier priority hierarchy (`CRITICAL_SCIENCE` down to `TRANSIENT_LOGS`), protected observation record guarantees, FIFO vs Priority-First transmission queue schedulers, and a six-state pressure alert taxonomy (`STORAGE_AVAILABLE` to `HIGH_PRIORITY_DATA_PENDING`).
5. **Communications-Aware Simulated Data Transfer Engine**: A deterministic link model:
   $$D_{\text{transferred}} = R_{\text{configured}} \cdot (1 - \eta_{\text{overhead}}) \cdot \delta_{\text{comm}} \cdot \Delta t$$
   strictly targeted to a surface base destination, explicitly rejecting Earth DSN downlink claims and prohibiting unphysical RF rate derivation from pure geometric LOS raycasts.
6. **Integration Architecture & JSON Schemas**: Clear API contracts, workspace persistence integration with `src/marswalk/api/workspace.py`, and an implementation roadmap for `src/marswalk/core/mission_data_ledger.py`.

```
+-------------------------------------------------------------------------------------------------------+
|                                  MILESTONE 13G DATA & STORAGE ENGINE                                  |
+-------------------------------------------------------------------------------------------------------+
|  [Science Observation] ---> [Synthetic Volume Profile] ---> [MissionDataProduct] (SHA-256 Fingerprint)|
|                                                                    |                                  |
|                                                                    v                                  |
|         +----------------------------------------------------------+-----------------------+          |
|         | Onboard Flash Storage Partition:  S_used,t = S_used,t-1 + S_gen,t - S_rel,t      |          |
|         | S_used / S_capacity  --->  [Storage Alert Monitor: OK / PRESSURE / CAPACITY]     |          |
|         +----------------------------------------------------------+-----------------------+          |
|                                                                    |                                  |
|                                                                    v                                  |
|                        [Transmission Queue: FIFO or Priority-First]                                   |
|                                                                    |                                  |
|         [Geometric Connectivity Checkpoint] (mission_connectivity: DIRECT / RELAY / GAP)              |
|                                                                    v                                  |
|      +---------------------------------------------------------------------------------------------+  |
|      | Communications-Aware Simulated Data Transfer: D_transferred = R_eff * Delta_t               |  |
|      | Destination: Surface Base Station (Local Tactical Mesh; NO Earth Downlink Claim)            |  |
|      +---------------------------------------------------------------------------------------------+  |
|                                                                    |                                  |
|                                                                    v                                  |
|                  [Transfer Receipt & SHA-256 Verification Logged at Base Station]                     |
|                                                                    |                                  |
|                                                                    v                                  |
|                  [Onboard Storage Release Executed: S_released,t > 0; Memory Freed]                   |
+-------------------------------------------------------------------------------------------------------+
```

---

## 2. Existing Codebase Audit & Integration Anchor Points

To maintain architectural coherence and adhere to the MarsWalk rule of preserving working functionality, we audited the existing codebase:

### 2.1 `src/marswalk/core/mission_resource_model.py` (Milestone 13F)
- **Role**: Models electrical loads, mechanical mobility work, drivetrain efficiency, and mission timeline events.
- **Key Structs**: `MissionActivityEvent`, `RoverResourceConfig`, `MissionResourceLedger`.
- **Anchor Point**: In `mission_resource_model.py`, activity events include `science_dwell` and `traverse_step`.
  * During a `science_dwell`, the instrument active load $P_{\text{inst, active}}$ draws battery energy over duration $t_{\text{science\_dwell}}$. This is the exact moment when `MissionDataProduct` instances are generated.
  * During active communications, $P_{\text{comm, active}}$ ($85\text{ W}$) is consumed by the rover transceiver. The duration of this load directly bounds the transfer window $\Delta t$ during which simulated data transfer can occur.
- **Requirement for 13G**: `mission_data_ledger.py` must take timeline events from `MissionResourceLedger.timeline_events` and compute data product generation timestamps and transfer durations synchronous with electrical energy drain.

### 2.2 `src/marswalk/core/campaign_progress.py` (Milestone 11B)
- **Role**: Manages campaign execution progress, target completion lifecycle, and scientific observation records.
- **Key Structs**: `ScienceObservation`, `QuantitativeMeasurement`, `ObservationProvenance`, `ObservationType`.
- **Anchor Point**: Every scientific observation captured at a waypoint or target has a unique `observation_id` (e.g. `obs_8f1a2b3c4d5e`), a `target_id`, `instrument_name`, and `quantitative_measurements`.
- **Requirement for 13G**: Every science data product generated in `mission_data_ledger.py` must link to its parent `observation_id`. If an observation is designated as high-value, its associated data products inherit `CRITICAL_SCIENCE` priority and permanent retention protection.

### 2.3 `src/marswalk/core/mission_event_ledger.py` (Milestone 10C)
- **Role**: Sortie Black Box append-only mission event ledger with atomic persistence and strict validation.
- **Key Structs**: `MissionEvent`, `VALID_EVENT_TYPES`.
- **Anchor Point**: High-level lifecycle transitions (`data_product_generated`, `storage_pressure_alert`, `transfer_completed`, `storage_released`) should emit events into the mission black box.
- **Requirement for 13G**: We will propose expanding the validated event types to include data logistics events (`data_product_created`, `data_transfer_verified`, `storage_capacity_alert`, `storage_released`).

### 2.4 `src/marswalk/core/mission_connectivity.py` & `relay_graph.py` (Milestone 13D/13E)
- **Role**: Evaluates instantaneous line-of-sight to Base Station and active RelayNet towers; outputs `DynamicCommState` (`CONNECTED_DIRECT`, `CONNECTED_RELAYED`, `SIMULATED_GEOMETRIC_CONNECTIVITY_GAP`).
- **Anchor Point**: Transfer can only take place when `DynamicCommState != SIMULATED_GEOMETRIC_CONNECTIVITY_GAP`.
- **Requirement for 13G**: `mission_data_ledger.py` must query the connectivity state along the timeline to determine whether the transmission queue can be processed.

### 2.5 `src/marswalk/api/workspace.py`
- **Role**: Central atomic JSON filesystem storage service with path traversal protection and Draft 2020-12 validation.
- **Anchor Point**: Mission definitions, experiments, campaigns, and observations are persisted atomically in `data/workspaces/`.
- **Requirement for 13G**: Add persistence helpers:
  * `DEFAULT_DATA_LEDGER_DIR = data/workspaces/data_ledgers`
  * `save_mission_data_ledger(...)`
  * `load_mission_data_ledger(...)`
  * Strict ID validation using `SAFE_ID_REGEX`.

---

## 3. Data Product Identity, Provenance & Tracking Architecture

### 3.1 Entity Specification: `MissionDataProduct`
Every discrete artifact produced by an onboard instrument, sensor suite, or flight computer is encapsulated in an immutable, validated `MissionDataProduct` dataclass.

```python
@dataclass(frozen=True)
class MissionDataProduct:
    """
    Immutable representation of a discrete data product generated onboard the rover.
    Tracks provenance, physical size, storage state, and verified transfer lifecycle.
    """
    product_id: str                      # Unique ID: dp_<instrument>_<hash> (e.g. dp_mastcamz_7a8b9c)
    observation_id: Optional[str]        # Link to ScienceObservation.observation_id (None for telemetry)
    mission_id: str                      # Parent mission identifier
    target_id: Optional[str]             # Associated science target (e.g. TGT_DELTA_01)
    target_name: str                     # Human-readable target label
    instrument_id: str                   # Recognized instrument identifier (e.g. MASTCAM_Z, RIMFAX)
    data_category: DataCategory          # Category enum
    size_bytes: int                      # Exact size in bytes (strictly positive integer)
    created_mission_time_s: float        # Mission elapsed time in seconds
    created_at_utc: str                  # ISO 8601 UTC timestamp
    storage_status: StorageStatus        # Onboard allocation state
    transfer_status: TransferStatus      # Communications state
    priority_level: DataPriority         # Priority tier (1: Critical to 5: Transient)
    retention_policy: RetentionPolicy    # Protection and release rules
    checksum_sha256: str                 # Cryptographic SHA-256 content verification hash
    provenance: Dict[str, Any]           # Strict planetary science provenance statement
    transferred_bytes: int = 0           # Cumulative acknowledged bytes received by base
    verified_at_mission_time_s: Optional[float] = None  # Timestamp when base verified checksum
    released_at_mission_time_s: Optional[float] = None  # Timestamp when onboard bytes were released
    schema_version: str = "1.0.0"
```

### 3.2 Enumerations and Allowed Values

#### `DataCategory`
```python
class DataCategory(str, Enum):
    ENVIRONMENTAL_TELEMETRY = "ENVIRONMENTAL_TELEMETRY"  # Atmospheric, thermal, power sweeps (10-50 KB)
    MULTISPECTRAL_IMAGERY = "MULTISPECTRAL_IMAGERY"      # Narrowband filter sequences, context images (5-25 MB)
    HIGH_RES_PANORAMA = "HIGH_RES_PANORAMA"              # Gigapixel 360-deg mosaics (50-200 MB)
    SPECTRAL_CUBE = "SPECTRAL_CUBE"                      # Micro-Raman / Luminescence / XRF cubes (15-40 MB)
    SUBSURFACE_RADAR = "SUBSURFACE_RADAR"                # GPR radargram soundings along traverse (20-60 MB)
    ENGINEERING_LOG = "ENGINEERING_LOG"                  # Avionics, motor currents, slip reports (1-10 MB)
```

#### `StorageStatus`
```python
class StorageStatus(str, Enum):
    STORED_ONBOARD = "STORED_ONBOARD"                    # Allocated in flash memory; 100% occupying space
    PARTIALLY_TRANSFERRED = "PARTIALLY_TRANSFERRED"      # Active transfer in flight; still occupies full space
    TRANSFERRED_AND_RETAINED = "TRANSFERRED_AND_RETAINED"# Receipt verified by base, but retained onboard
    TRANSFERRED_AND_RELEASED = "TRANSFERRED_AND_RELEASED"# Receipt verified AND space reclaimed from flash
    PURGED_OVERFLOW = "PURGED_OVERFLOW"                  # Evicted under emergency storage capacity pressure
```

#### `TransferStatus`
```python
class TransferStatus(str, Enum):
    PENDING_TRANSFER = "PENDING_TRANSFER"                # Generated, awaiting insertion into comms queue
    QUEUED = "QUEUED"                                    # Enqueued in transmission queue
    IN_TRANSFER = "IN_TRANSFER"                          # Currently transmitting across active link
    TRANSFER_VERIFIED = "TRANSFER_VERIFIED"              # Completed, verified by base station SHA-256 match
    TRANSFER_FAILED = "TRANSFER_FAILED"                  # Link dropped mid-transfer; bytes discarded
    TRANSFER_DEFERRED = "TRANSFER_DEFERRED"              # Transmission paused due to LOS gap; preserved
```

#### `DataPriority`
```python
class DataPriority(int, Enum):
    CRITICAL_SCIENCE = 1    # Primary mission objectives, sample caching verifications (Never evicted)
    HIGH_SCIENCE = 2        # Detailed spectral/elemental analyses, deep radar profiles
    ROUTINE_SCIENCE = 3     # Contextual stereo imagery, regional surveys
    ENGINEERING_TELEMETRY = 4 # Vehicle health, battery SOC, motor slip, terrain roughness
    TRANSIENT_LOGS = 5      # Detailed debug traces, uncompressed intermediate frames (First to evict)
```

#### `RetentionPolicy`
```python
class RetentionPolicy(str, Enum):
    PROTECTED_PERMANENT = "PROTECTED_PERMANENT"    # Permanent onboard record; CANNOT be released or evicted
    TRANSFER_THEN_RELEASE = "TRANSFER_THEN_RELEASE"# Standard: immediately release storage upon verified receipt
    TRANSFER_THEN_RETAIN = "TRANSFER_THEN_RETAIN"  # Retain in flash after transfer until explicit purge
    VOLATILE_SCRATCH = "VOLATILE_SCRATCH"          # Eligible for immediate release or eviction if pressure rises
```

### 3.3 Deterministic SHA-256 Checksum Fingerprinting
To ensure end-to-end cryptographic integrity without requiring multi-megabyte dummy binary generation in memory, we compute a deterministic SHA-256 fingerprint based on canonical metadata and a pseudorandom content seed:

$$\text{hash\_input} = \text{product\_id} \parallel \text{instrument\_id} \parallel \text{size\_bytes} \parallel \text{created\_mission\_time\_s} \parallel \text{data\_category}$$
$$\text{checksum\_sha256} = \text{SHA-256}(\text{hash\_input.encode('utf-8')})$$

This produces an authentic 64-character hexadecimal checksum that base station reception routines match against upon transfer completion.

### 3.4 Provenance Disclosure & Scientific Boundary
In strict accordance with the `marswalk-scientific-integrity` rules:
```python
"provenance": {
    "is_simulated": True,
    "is_synthetic_demonstration": True,
    "generation_model": "MARSWALK_SYNTHETIC_DATA_PROFILE_V1",
    "compression_applied": "NEAR_LOSSLESS_WAVELET",
    "compression_ratio": 3.2,
    "raw_uncompressed_bytes": 40265318,
    "citation": "Synthetic data volume demonstration model; not authentic flight telemetry."
}
```
**Strict Scientific Boundary**: No synthetic data product shall ever be presented as real Martian telemetry. All volumes represent planning heuristics calibrated against publicly available instrument characteristics.

---

## 4. Synthetic Data Volume Profiles

### 4.1 Calibration & Profile Parameterization
We define five standard demonstration profiles calibrated against published specifications of the Mars 2020 Perseverance instrument payload (Bell et al., 2021; Wiens et al., 2021; Allwood et al., 2020; Beegle et al., 2021; Hamran et al., 2020; Rodriguez-Manfredi et al., 2021):

| Profile Identifier | Analog Instrument | Category | Raw Volume | Nominal Compressed | Range | Typical Generation Context |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PROF_ENV_TELEMETRY` | MEDA (Mars Env. Dynamics) | `ENVIRONMENTAL_TELEMETRY` | $\sim 100\text{ KB}$ | **$24\text{ KB}$** ($24,576\text{ B}$) | $10\text{--}50\text{ KB}$ | Continuous or post-traverse 1-minute atmospheric sweep. |
| `PROF_MULTISPECTRAL` | Mastcam-Z / SuperCam RMI | `MULTISPECTRAL_IMAGERY` | $\sim 42\text{ MB}$ | **$12\text{ MB}$** ($12,582,912\text{ B}$) | $5\text{--}25\text{ MB}$ | 11-filter narrowband sequence at science waypoint. |
| `PROF_HIRES_PANORAMA` | Mastcam-Z 360° Stereo | `HIGH_RES_PANORAMA` | $\sim 200\text{ MB}$ | **$80\text{ MB}$** ($83,886,080\text{ B}$) | $50\text{--}200\text{ MB}$ | Full panoramic mosaic at scenic promontory or goal. |
| `PROF_SPECTRAL_CUBE` | PIXL / SHERLOC | `SPECTRAL_CUBE` | $\sim 45\text{ MB}$ | **$25\text{ MB}$** ($26,214,400\text{ B}$) | $15\text{--}40\text{ MB}$ | Arm contact micro-mapping raster scan during dwell. |
| `PROF_SUBSURFACE_RADAR`| RIMFAX GPR Sounder | `SUBSURFACE_RADAR` | $\sim 60\text{ MB}$ | **$35\text{ MB}$** ($36,700,160\text{ B}$) | $20\text{--}60\text{ MB}$ | Deep sounding profile accumulated over traverse leg. |

### 4.2 Mathematical Formulas for Synthetic Volume Generation

1. **Environmental Telemetry**:
   $$S_{\text{env}} = \text{round}\left(S_{\text{base}} + \Delta S \cdot \sin^2(t_{\text{mission}} / 3600)\right)$$
   Bounded to $[10 \times 1024, 50 \times 1024]\text{ bytes}$.
2. **Multispectral Image Sequence**:
   $$S_{\text{multi}} = N_{\text{filters}} \cdot W_{\text{pixels}} \cdot H_{\text{pixels}} \cdot B_{\text{depth}} / C_{\text{ratio}}$$
   Nominal: $11\text{ filters} \times 1600 \times 1200 \times 2\text{ bytes} / 3.5 \approx 12.05\text{ MB}$.
3. **High-Resolution Panorama**:
   $$S_{\text{pano}} = N_{\text{tiles}} \cdot W_{\text{tile}} \cdot H_{\text{tile}} \cdot B_{\text{depth}} / C_{\text{ratio}}$$
   Nominal: $24\text{ tiles} \times 2048 \times 2048 \times 2\text{ bytes} / 2.4 \approx 83.88\text{ MB}$.
4. **Hyperspectral Cube**:
   $$S_{\text{cube}} = N_{\text{spatial}} \cdot N_{\text{channels}} \cdot 4\text{ bytes} / C_{\text{ratio}}$$
   Nominal: $256\text{ spots} \times 1024\text{ channels} \times 4\text{ bytes} / 1.0 \approx 1.05\text{ MB}$ (raw) up to multi-raster arrays of $25\text{ MB}$.
5. **Subsurface Radar Profile**:
   $$S_{\text{radar}} = d_{\text{traverse}} \cdot \rho_{\text{sounding}} \cdot N_{\text{samples}} \cdot 4\text{ bytes}$$
   Nominal: $500\text{ m} \times 10\text{ soundings/m} \times 1024\text{ depth} \times 4\text{ bytes} / 2.0 \approx 10.24\text{ MB}$ to $35\text{ MB}$.

---

## 5. Onboard Storage Accounting & Exact Byte Conservation

### 5.1 The Byte Conservation Law
Onboard flash memory allocation is governed by strict mass/byte conservation. For any discrete mission time step $t \in \{1 \dots K\}$:

$$S_{\text{used}, t} = S_{\text{used}, t-1} + S_{\text{generated}, t} - S_{\text{released}, t}$$

where:
- $S_{\text{used}, t} \in \mathbb{N}_0$: Total bytes of flash memory occupied at the end of time step $t$.
- $S_{\text{generated}, t} \in \mathbb{N}_0$: Total new bytes written to flash by newly completed observations or telemetry logging during time step $t$:
  $$S_{\text{generated}, t} = \sum_{p \in \mathcal{P}_{\text{created}, t}} p.\text{size\_bytes}$$
- $S_{\text{released}, t} \in \mathbb{N}_0$: Total bytes explicitly reclaimed/freed from flash memory during time step $t$:
  $$S_{\text{released}, t} = \sum_{p \in \mathcal{P}_{\text{released}, t}} p.\text{size\_bytes}$$

### 5.2 The Cumulative Invariant
Summing over the mission timeline from $t=0$ to $t=T$:

$$S_{\text{used}, T} = S_{\text{initial}} + \sum_{t=1}^T S_{\text{generated}, t} - \sum_{t=1}^T S_{\text{released}, t}$$

The ledger engine must compute the absolute conservation discrepancy:
$$\epsilon_{\text{conservation}} = \left| S_{\text{used}, T} - \left(S_{\text{initial}} + \sum_{t=1}^T S_{\text{generated}, t} - \sum_{t=1}^T S_{\text{released}, t}\right)\right|$$
and assert $\epsilon_{\text{conservation}} \equiv 0$ at all times.

### 5.3 The Post-Verification Release Precondition
A critical operational rule enforced by `mission_data_ledger.py` is that **storage is ONLY released AFTER a transfer has been verified and recorded**.

Formally, a data product $p$ is eligible for release at time $t$ if and only if:
1. $p.\text{transfer\_status} == \text{TransferStatus.TRANSFER\_VERIFIED}$
2. $p.\text{storage\_status} == \text{StorageStatus.TRANSFERRED\_AND\_RETAINED}$
3. $p.\text{retention\_policy} \ne \text{RetentionPolicy.PROTECTED\_PERMANENT}$
4. $\text{verified\_at\_mission\_time\_s} \le t$

If an attempt is made to release $p$ while $p.\text{transfer\_status} \ne \text{TRANSFER\_VERIFIED}$, the ledger raises:
`StoragePolicyViolationError("Cannot release data product dp_xxx: transfer has not been verified.")`

### 5.4 Capacity Bounds and Overflow Prevention
Flash memory has a fixed hardware partition size $S_{\text{capacity}}$ (e.g., $256\text{ GB} = 274,877,906,944\text{ bytes}$).
The free storage is:
$$S_{\text{free}, t} = S_{\text{capacity}} - S_{\text{used}, t}$$

**Hard Storage Constraint**:
$$S_{\text{used}, t} \le S_{\text{capacity}} \quad \forall t$$
If a new data product generation would cause $S_{\text{used}, t-1} + S_{\text{generated}, t} > S_{\text{capacity}}$, the ledger acts according to the active storage management policy:
- **Strict Capacity Rejection (Default)**: Rejects the observation write with `ERR_STORAGE_CAPACITY_EXCEEDED` and marks the observation event as blocked.
- **Priority Eviction**: If permitted by policy, the ledger attempts to purge low-priority non-protected products (`TRANSIENT_LOGS`, `VOLATILE_SCRATCH`) whose bytes are already verified or flagged disposable. Under no circumstances may `CRITICAL_SCIENCE` or `PROTECTED_PERMANENT` products be evicted.

---

## 6. Storage Policies, Queueing Strategies & Pressure Alerts

### 6.1 Priority Class Hierarchy

| Priority Level | Classification | Max Retention Window | Purge Eligibility | Typical Data Content |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `CRITICAL_SCIENCE` | Permanent | **IMMUNE** (Never purged) | Core sample site assay, primary mission hypothesis tests. |
| **2** | `HIGH_SCIENCE` | Mission Duration | Protected | High-resolution spectral cubes, deep radar scans. |
| **3** | `ROUTINE_SCIENCE` | Sol-to-Sol | Evictable if unverified & emergency | Context stereo pairs, regional terrain morphology. |
| **4** | `ENGINEERING_TELEMETRY` | Sol-to-Sol | Evictable after verified transfer | Drive motor torque, battery health, thermal logs. |
| **5** | `TRANSIENT_LOGS` | Transient ($< 1\text{ hour}$) | Immediate first eviction candidate | High-rate IMU scratch frames, intermediate point clouds. |

### 6.2 Transfer Queue Schedulers
When entering a communications contact window with the Surface Base Station, data products are drained from the onboard transmission queue according to a configured scheduling strategy:

1. **Oldest-First (FIFO)**:
   Sorts queue strictly by creation timestamp:
   $$\text{sort\_key}(p) = p.\text{created\_mission\_time\_s}$$
   Ensures sequential chronological reporting and prevents starvation of early routine telemetry.
2. **Priority-First (PQ)**:
   Sorts queue primarily by scientific priority tier, breaking ties by creation timestamp:
   $$\text{sort\_key}(p) = (p.\text{priority\_level}, p.\text{created\_mission\_time\_s})$$
   Maximizes immediate science return in short or intermittent contact windows.

### 6.3 Storage Pressure Alert State Machine
The ledger evaluates storage occupancy $\rho_S(t) = \frac{S_{\text{used}, t}}{S_{\text{capacity}}}$ and queue backlog, triggering deterministic operational alerts:

```
               +---------------------------+
               |     STORAGE_AVAILABLE     |  (rho < 0.60)
               +-------------+-------------+
                             | rho >= 0.60
                             v
               +---------------------------+
               |     STORAGE_PRESSURE      |  (0.60 <= rho < 0.80)
               +-------------+-------------+
                             | rho >= 0.80
                             v
               +---------------------------+
               |   STORAGE_NEAR_CAPACITY   |  (0.80 <= rho < 0.95)
               +-------------+-------------+
                             | rho >= 0.95
                             v
               +---------------------------+
               | STORAGE_CAPACITY_REACHED  |  (rho >= 0.95)
               +---------------------------+
```

#### Diagnostic Indicators:
- `STORAGE_AVAILABLE`: Normal operations. $\rho_S < 0.60$.
- `STORAGE_PRESSURE`: $\rho_S \in [0.60, 0.80)$. Advisory: Next contact window should prioritize offloading.
- `STORAGE_NEAR_CAPACITY`: $\rho_S \in [0.80, 0.95)$. Warning: Non-essential observation sequences should be throttled or scratch memory purged.
- `STORAGE_CAPACITY_REACHED`: $\rho_S \ge 0.95$. Critical constraint violation: Observation data writes rejected unless storage is freed.
- `TRANSFER_QUEUE_BACKLOG`: Triggered when total untransferred queue volume exceeds threshold $V_{\text{backlog, max}}$ (e.g. $> 100\text{ MB}$ or $> 10$ products).
- `HIGH_PRIORITY_DATA_PENDING`: Triggered when any `CRITICAL_SCIENCE` data product remains un-offloaded in queue for longer than $T_{\text{pending, max}}$ (e.g. $> 3600\text{ s}$).

---

## 7. Communications-Aware Simulated Data Transfer Engine

### 7.1 Mathematical Model of Simulated Data Transfer
Tactical data transfer between the exploration vehicle and the Surface Base Station is modeled deterministically over discrete contact windows:

$$D_{\text{transferred}}(\Delta t) = R_{\text{effective}} \cdot \Delta t$$

where:
- $\Delta t$: Duration of the active contact window in seconds.
- $R_{\text{effective}}$: Effective payload transfer rate in bytes per second:
  $$R_{\text{effective}} = \frac{R_{\text{configured}}}{8} \cdot (1 - \eta_{\text{overhead}}) \cdot \delta_{\text{comm}}$$
  * $R_{\text{configured}}$: Configured raw RF channel bitrate in bits per second ($\text{bps}$).
  * $\eta_{\text{overhead}} \in [0.0, 0.30]$: Protocol, packetization, and framing overhead (default $0.08 = 8\%$).
  * $\delta_{\text{comm}} \in [0.0, 1.0]$: Operational link duty cycle (default $0.85$ during dedicated stationary dwell; $0.40$ during simultaneous traverse).

### 7.2 Link Configuration Profiles
In a Martian tactical surface network, data rates depend on transceiver band and hop topology:

| Link Profile | Carrier Band | Configured Raw Bitrate $R_{\text{configured}}$ | Protocol Overhead $\eta$ | Duty Cycle $\delta$ | Effective Byte Rate $R_{\text{effective}}$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Direct Proximity UHF** | UHF ($400\text{ MHz}$) | $256\text{ kbps}$ | $8\%$ | $0.85$ | **$25.0\text{ KB/s}$** ($1.50\text{ MB/min}$) |
| **Direct Microwave S-Band** | S-Band ($2.2\text{ GHz}$) | $1.0\text{ Mbps}$ | $8\%$ | $0.85$ | **$97.75\text{ KB/s}$** ($5.86\text{ MB/min}$) |
| **Direct High-Rate X-Band** | X-Band ($8.4\text{ GHz}$) | $2.0\text{ Mbps}$ | $8\%$ | $0.85$ | **$195.5\text{ KB/s}$** ($11.73\text{ MB/min}$) |
| **RelayNet Multi-Hop** | UHF / Microwave | $500\text{ kbps}$ | $12\%$ | $0.80$ | **$44.0\text{ KB/s}$** ($2.64\text{ MB/min}$) |

### 7.3 Geometric Line-of-Sight Coupling
Transfer capability is strictly dependent on the instantaneous geometric connectivity state evaluated by `mission_connectivity.py`:
- `CONNECTED_DIRECT`: Full direct transfer rate $R_{\text{direct}}$ applies.
- `CONNECTED_RELAYED`: Relayed multi-hop transfer rate $R_{\text{relayed}}$ applies.
- `SIMULATED_GEOMETRIC_CONNECTIVITY_GAP`: $R_{\text{effective}} = 0.0\text{ bytes/s}$. The transfer engine automatically pauses the current transfer, transitions the active product to `TRANSFER_DEFERRED`, and logs the interruption. When connectivity is restored, transfer resumes from the current byte offset.

### 7.4 Strict Scientific Truth Disclosures & Demarcation
To maintain authentic planetary science standards:
1. **Surface Base Destination Only**: The simulated transfer represents tactical data offload from the rover to the local Surface Base Station (e.g. the Jezero base habitat or primary communications mast).
2. **NO Earth Downlink Claim**: The model does **NOT** claim direct-to-Earth (DTE) downlink to NASA's Deep Space Network (DSN). DTE links require modeling Mars rotation, Earth rise/set, orbital ephemerides, solar conjunction, and 70-meter Goldstone/Madrid/Canberra dish allocations.
3. **NO Inferring RF Bitrate from Pure Geometric LOS**: Geometric line-of-sight raycasting computes topological visibility and obstruction clearance. It does **not** model RF channel propagation, multipath fading, or atmospheric absorption. The bitrate is explicitly configured as an engineering parameter.
4. **Mandatory Label**: All simulated transfer metrics must carry the explicit label `SIMULATED_DATA_TRANSFER`.

### 7.5 Exact Data Backlog Conservation
At any mission elapsed time $t$:
$$D_{\text{backlog}, t} = D_{\text{collected}, t} - D_{\text{transferred}, t} - D_{\text{evicted}, t}$$

where:
- $D_{\text{collected}, t} = \sum_{p \in \mathcal{P}_t} p.\text{size\_bytes}$
- $D_{\text{transferred}, t} = \sum_{p \in \mathcal{P}_t} p.\text{transferred\_bytes}$
- $D_{\text{backlog}, t} = \sum_{p \in \mathcal{P}_{\text{uncompleted}, t}} (p.\text{size\_bytes} - p.\text{transferred\_bytes})$

The ledger verifies this identity at every timeline checkpoint.

---

## 8. Proposed JSON Schemas (Draft 2020-12)

We propose adding three versioned Draft 2020-12 JSON schemas to `schemas/api/v1/`:

### 8.1 `schemas/api/v1/mission-data-product.schema.json`
Validates discrete data product records:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://marswalk.nasa.gov/schemas/api/v1/mission-data-product.schema.json",
  "title": "MissionDataProduct",
  "type": "object",
  "required": [
    "schema_version",
    "product_id",
    "mission_id",
    "instrument_id",
    "data_category",
    "size_bytes",
    "created_mission_time_s",
    "created_at_utc",
    "storage_status",
    "transfer_status",
    "priority_level",
    "retention_policy",
    "checksum_sha256",
    "provenance"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0.0" },
    "product_id": { "type": "string", "pattern": "^dp_[a-zA-Z0-9_-]{3,64}$" },
    "observation_id": { "type": ["string", "null"] },
    "mission_id": { "type": "string", "pattern": "^[a-zA-Z0-9_-]{3,64}$" },
    "target_id": { "type": ["string", "null"] },
    "target_name": { "type": "string" },
    "instrument_id": { "type": "string" },
    "data_category": { 
      "type": "string", 
      "enum": ["ENVIRONMENTAL_TELEMETRY", "MULTISPECTRAL_IMAGERY", "HIGH_RES_PANORAMA", "SPECTRAL_CUBE", "SUBSURFACE_RADAR", "ENGINEERING_LOG"] 
    },
    "size_bytes": { "type": "integer", "minimum": 1 },
    "created_mission_time_s": { "type": "number", "minimum": 0.0 },
    "created_at_utc": { "type": "string", "format": "date-time" },
    "storage_status": { 
      "type": "string", 
      "enum": ["STORED_ONBOARD", "PARTIALLY_TRANSFERRED", "TRANSFERRED_AND_RETAINED", "TRANSFERRED_AND_RELEASED", "PURGED_OVERFLOW"] 
    },
    "transfer_status": { 
      "type": "string", 
      "enum": ["PENDING_TRANSFER", "QUEUED", "IN_TRANSFER", "TRANSFER_VERIFIED", "TRANSFER_FAILED", "TRANSFER_DEFERRED"] 
    },
    "priority_level": { "type": "integer", "enum": [1, 2, 3, 4, 5] },
    "retention_policy": { 
      "type": "string", 
      "enum": ["PROTECTED_PERMANENT", "TRANSFER_THEN_RELEASE", "TRANSFER_THEN_RETAIN", "VOLATILE_SCRATCH"] 
    },
    "checksum_sha256": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
    "transferred_bytes": { "type": "integer", "minimum": 0 },
    "verified_at_mission_time_s": { "type": ["number", "null"] },
    "released_at_mission_time_s": { "type": ["number", "null"] },
    "provenance": {
      "type": "object",
      "required": ["is_simulated", "is_synthetic_demonstration"],
      "properties": {
        "is_simulated": { "type": "boolean", "const": true },
        "is_synthetic_demonstration": { "type": "boolean", "const": true }
      }
    }
  },
  "additionalProperties": false
}
```

### 8.2 `schemas/api/v1/mission-storage-ledger.schema.json`
Validates full mission storage ledger output:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://marswalk.nasa.gov/schemas/api/v1/mission-storage-ledger.schema.json",
  "title": "MissionStorageLedger",
  "type": "object",
  "required": [
    "schema_version",
    "mission_id",
    "storage_capacity_bytes",
    "initial_used_bytes",
    "final_used_bytes",
    "peak_used_bytes",
    "total_generated_bytes",
    "total_transferred_bytes",
    "total_released_bytes",
    "conservation_verified",
    "alert_state",
    "data_products_count",
    "data_products",
    "timeline_snapshots"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0.0" },
    "mission_id": { "type": "string" },
    "storage_capacity_bytes": { "type": "integer", "minimum": 1 },
    "initial_used_bytes": { "type": "integer", "minimum": 0 },
    "final_used_bytes": { "type": "integer", "minimum": 0 },
    "peak_used_bytes": { "type": "integer", "minimum": 0 },
    "total_generated_bytes": { "type": "integer", "minimum": 0 },
    "total_transferred_bytes": { "type": "integer", "minimum": 0 },
    "total_released_bytes": { "type": "integer", "minimum": 0 },
    "conservation_verified": { "type": "boolean" },
    "alert_state": { "type": "string" },
    "active_alerts": { "type": "array", "items": { "type": "string" } },
    "data_products_count": { "type": "integer", "minimum": 0 },
    "data_products": { "type": "array", "items": { "$ref": "mission-data-product.schema.json" } },
    "timeline_snapshots": { "type": "array", "items": { "type": "object" } }
  },
  "additionalProperties": false
}
```

### 8.3 `schemas/api/v1/simulated-data-transfer.schema.json`
Validates transfer window and execution logs:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://marswalk.nasa.gov/schemas/api/v1/simulated-data-transfer.schema.json",
  "title": "SimulatedDataTransferRecord",
  "type": "object",
  "required": [
    "transfer_id",
    "product_id",
    "destination",
    "start_time_s",
    "end_time_s",
    "duration_s",
    "link_state",
    "configured_rate_bps",
    "effective_rate_bytes_per_s",
    "bytes_transferred_in_window",
    "status",
    "is_simulated"
  ],
  "properties": {
    "transfer_id": { "type": "string" },
    "product_id": { "type": "string" },
    "destination": { "type": "string", "enum": ["SURFACE_BASE_STATION"] },
    "start_time_s": { "type": "number", "minimum": 0.0 },
    "end_time_s": { "type": "number", "minimum": 0.0 },
    "duration_s": { "type": "number", "minimum": 0.0 },
    "link_state": { "type": "string" },
    "configured_rate_bps": { "type": "number", "minimum": 0.0 },
    "effective_rate_bytes_per_s": { "type": "number", "minimum": 0.0 },
    "bytes_transferred_in_window": { "type": "integer", "minimum": 0 },
    "status": { "type": "string" },
    "is_simulated": { "type": "boolean", "const": true }
  },
  "additionalProperties": false
}
```

---

## 9. Implementation Blueprint for `src/marswalk/core/mission_data_ledger.py`

### 9.1 Module Layout and Class Structure
The target module will be structured into five clean logical layers:

```python
"""
MarsWalk Core Onboard Data Ledger & Simulated Logistics Engine (Milestone 13G).
Provides transparent, deterministic onboard flash storage accounting, synthetic data product
tracking, byte conservation enforcement, and communications-aware simulated data transfer.
"""

# 1. Imports and Constants
# 2. Enumerations (DataCategory, StorageStatus, TransferStatus, DataPriority, RetentionPolicy, StorageAlertLevel)
# 3. Configuration Dataclasses (MissionStorageConfig, DataProductProfile)
# 4. Core Entity Dataclasses (MissionDataProduct, StorageAccountingStep, SimulatedTransferRecord)
# 5. Ledger Container Dataclass (MissionDataLedger)
# 6. Profile Factory & Data Generation Functions
# 7. Communications Transfer Simulator
# 8. Integrated Mission Data Lifecycle Evaluator
# 9. Verification & Conservation Auditing Functions
# 10. Serialization & Contract Validation Helpers
```

### 9.2 Key Method Signatures

```python
def create_synthetic_data_product(
    profile_id: str,
    mission_id: str,
    observation_id: Optional[str] = None,
    target_id: Optional[str] = None,
    target_name: str = "",
    mission_time_s: float = 0.0,
    priority: Optional[DataPriority] = None,
    retention: Optional[RetentionPolicy] = None,
    override_size_bytes: Optional[int] = None,
) -> MissionDataProduct:
    """Instantiate a validated MissionDataProduct with deterministic SHA-256 hash."""
    ...

def evaluate_simulated_transfer_window(
    product: MissionDataProduct,
    window_duration_s: float,
    comm_state: DynamicCommState,
    config: MissionStorageConfig,
    start_time_s: float,
) -> Tuple[MissionDataProduct, SimulatedTransferRecord]:
    """Execute simulated data transmission over a discrete contact window."""
    ...

def evaluate_mission_data_ledger(
    mission_id: str,
    timeline_events: List[Dict[str, Any]],
    connectivity_checkpoints: List[ConnectivityCheckpoint],
    config: Optional[MissionStorageConfig] = None,
    observations: Optional[List[Dict[str, Any]]] = None,
) -> MissionDataLedger:
    """
    Main entry point: integrates chronological data generation, storage accounting,
    simulated transfers, and verified releases across the entire mission timeline.
    Enforces the exact byte conservation law: S_used,t = S_used,t-1 + S_gen,t - S_rel,t.
    """
    ...

def verify_byte_conservation(ledger: MissionDataLedger) -> Tuple[bool, str]:
    """
    Formally verifies byte conservation across every timeline step:
    S_used,t == S_used,t-1 + S_generated,t - S_released,t.
    """
    ...
```

### 9.3 Storage Release Implementation Detail
```python
def release_transferred_data_product(
    ledger_state: Dict[str, Any],
    product_id: str,
    current_time_s: float,
) -> int:
    """
    Releases storage allocated to a data product if and only if:
    1. Transfer has been completed and verified.
    2. Retention policy permits release.
    Returns the number of bytes released.
    """
    product = ledger_state["products"].get(product_id)
    if product is None:
        raise KeyError(f"Data product '{product_id}' not found in ledger.")
        
    if product.transfer_status != TransferStatus.TRANSFER_VERIFIED:
        raise StoragePolicyViolationError(
            f"Precondition failed: cannot release '{product_id}' with status {product.transfer_status.value}. "
            "Data product must be verified by base station receipt before storage can be released."
        )
        
    if product.retention_policy == RetentionPolicy.PROTECTED_PERMANENT:
        raise StoragePolicyViolationError(
            f"Precondition failed: cannot release '{product_id}' with PROTECTED_PERMANENT retention policy."
        )
        
    if product.storage_status == StorageStatus.TRANSFERRED_AND_RELEASED:
        return 0  # Already released; idempotent
        
    # Reclaim storage
    freed_bytes = product.size_bytes
    product.storage_status = StorageStatus.TRANSFERRED_AND_RELEASED
    product.released_at_mission_time_s = current_time_s
    ledger_state["used_bytes"] -= freed_bytes
    ledger_state["released_bytes"] += freed_bytes
    return freed_bytes
```

---

## 10. Test Matrix & Acceptance Criteria

When Agent B's implementation plan is executed, the test suite `tests/test_milestone_13g_data_ledger.py` must prove the following 10 invariants:

| Test Identifier | Tested Invariant | Acceptance Criteria |
| :--- | :--- | :--- |
| `test_data_product_sha256_reproducibility` | Deterministic content fingerprinting | Identical parameters produce identical SHA-256 hashes; altered size or time produces different hash. |
| `test_synthetic_volume_profiles` | Volume profiles match specifications | All 5 profiles generate sizes within published ranges ($10\text{--}50\text{ KB}$ for telemetry, $50\text{--}200\text{ MB}$ for pano) with explicit synthetic flags. |
| `test_byte_conservation_law_step_by_step` | $S_t = S_{t-1} + S_{\text{gen}} - S_{\text{rel}}$ | At every single discrete event, byte equation balances with 0 discrepancy ($\epsilon = 0$). |
| `test_storage_release_precondition` | Release only after verified transfer | Attempting to release un-transferred or in-flight data product raises `StoragePolicyViolationError`. |
| `test_protected_records_inviolability` | Protected science records cannot be released | Attempting to release or purge `PROTECTED_PERMANENT` record is rejected. |
| `test_storage_capacity_overflow_rejection`| Capacity limit enforcement | Writing data exceeding $S_{\text{capacity}}$ triggers `ERR_STORAGE_CAPACITY_EXCEEDED` and raises alert. |
| `test_storage_pressure_alerts_state_machine`| Alert thresholds | Fill levels $65\%$, $85\%$, $96\%$ trigger `STORAGE_PRESSURE`, `STORAGE_NEAR_CAPACITY`, and `STORAGE_CAPACITY_REACHED`. |
| `test_simulated_transfer_rate_and_overhead` | $D = R \cdot (1 - \eta) \cdot \delta \cdot \Delta t$ | Transferred bytes match configured formula within floating point rounding. |
| `test_connectivity_gap_pauses_transfer` | LOS gap stops data flow | In `SIMULATED_GEOMETRIC_CONNECTIVITY_GAP`, transfer rate is 0 bytes/s; active transfer is deferred. |
| `test_data_backlog_conservation` | $D_{\text{backlog}} = D_{\text{coll}} - D_{\text{xfer}} - D_{\text{rel}}$ | Backlog conservation identity holds across entire mission lifecycle. |

---

## 11. Coordination Notes with Milestone 13G Subagents

- **Agent A (Science Mission Planner)**:
  * Agent A models science targets, observation durations, and instrument energy.
  * Integration: When Agent A schedules an observation at target $T_k$, Agent A will emit an observation event with an assigned profile ID (e.g. `PROF_MULTISPECTRAL`).
  * `mission_data_ledger.py` consumes this event, creates the `MissionDataProduct`, links the `observation_id`, and adds the bytes to $S_{\text{generated}}$.
- **Agent C (Optimization & Joint Planner)**:
  * Agent C optimizes the multi-objective Pareto front: Science Return vs Energy vs Communications vs Data Backlog.
  * Integration: Agent C queries `MissionDataLedger` for:
    1. $D_{\text{total\_transferred}}$ (science return delivered to base).
    2. $D_{\text{backlog}}$ (data at risk remaining on rover).
    3. Peak storage occupancy $\rho_{S, \text{peak}}$.
    4. Storage feasibility boolean ($S_{\text{used}} \le S_{\text{capacity}}$ throughout traverse).
- **Agent D (Validation, API & Cockpit UI)**:
  * Agent D implements the API endpoints (`/api/science-mission/transfers/evaluate`), Three.js telemetry HUD, and storage fill gauges.
  * Integration: Agent D exposes `storage_fill_pct`, `transfer_rate_kbps`, and `queue_backlog_mb` in `web/app.js` using data structures defined in this audit.

---

## 12. Conclusion & Sign-Off

The data and storage architecture outlined above satisfies all scientific, operational, and software integrity standards of the MarsWalk project:
- Mathematical rigor: Strict byte conservation law with zero tolerance for unaccounted bits.
- Scientific credibility: Explicit synthetic profile marking, realistic Mars 2020 payload parameters, and clear demarcation of the local surface tactical link.
- Flight operational reality: Transfer-before-release verification, priority-based queues, and storage pressure alarms.

Agent B stands ready to implement `src/marswalk/core/mission_data_ledger.py` and coordinate with Agents A, C, and D for complete Milestone 13G delivery.
