"""
MarsWalk Core Onboard Data Ledger & Simulated Logistics Engine (Milestone 13G).

Implements deterministic onboard solid-state storage accounting, cryptographic data product tracking,
verified storage release invariants, storage pressure alerting, and communications-aware simulated
data transfer to surface base infrastructure.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class DataCategory(str, Enum):
    """Categories of scientific and engineering data products."""
    ENVIRONMENTAL_TELEMETRY = "ENVIRONMENTAL_TELEMETRY"
    MULTISPECTRAL_IMAGERY = "MULTISPECTRAL_IMAGERY"
    HIGH_RES_PANORAMA = "HIGH_RES_PANORAMA"
    SPECTRAL_CUBE = "SPECTRAL_CUBE"
    SUBSURFACE_RADAR = "SUBSURFACE_RADAR"
    ENGINEERING_LOG = "ENGINEERING_LOG"


class DataProductStorageStatus(str, Enum):
    """Lifecycle status of a data product in onboard solid-state memory."""
    STORED_ONBOARD = "STORED_ONBOARD"
    PARTIALLY_TRANSFERRED = "PARTIALLY_TRANSFERRED"
    TRANSFERRED_AND_RETAINED = "TRANSFERRED_AND_RETAINED"
    TRANSFERRED_AND_RELEASED = "TRANSFERRED_AND_RELEASED"
    PURGED_OVERFLOW = "PURGED_OVERFLOW"


class DataProductTransferStatus(str, Enum):
    """Lifecycle status of a data product relative to simulated transmission."""
    PENDING_TRANSFER = "PENDING_TRANSFER"
    QUEUED = "QUEUED"
    IN_TRANSFER = "IN_TRANSFER"
    TRANSFER_VERIFIED = "TRANSFER_VERIFIED"
    TRANSFER_DEFERRED = "TRANSFER_DEFERRED"
    TRANSFER_FAILED = "TRANSFER_FAILED"


class RetentionPolicy(str, Enum):
    """Policy governing retention and eviction of data products."""
    PROTECTED_PERMANENT = "PROTECTED_PERMANENT"
    TRANSFER_THEN_RELEASE = "TRANSFER_THEN_RELEASE"
    TRANSFER_THEN_RETAIN = "TRANSFER_THEN_RETAIN"
    VOLATILE_SCRATCH = "VOLATILE_SCRATCH"


class StoragePressureState(str, Enum):
    """Rigorous classification of onboard solid-state memory pressure."""
    STORAGE_AVAILABLE = "STORAGE_AVAILABLE"
    STORAGE_PRESSURE = "STORAGE_PRESSURE"
    STORAGE_NEAR_CAPACITY = "STORAGE_NEAR_CAPACITY"
    STORAGE_CAPACITY_REACHED = "STORAGE_CAPACITY_REACHED"
    TRANSFER_QUEUE_BACKLOG = "TRANSFER_QUEUE_BACKLOG"
    HIGH_PRIORITY_DATA_PENDING = "HIGH_PRIORITY_DATA_PENDING"


class PriorityType(str, Enum):
    """Provenance and epistemological classification of science priorities."""
    USER_ASSIGNED_PRIORITY = "USER_ASSIGNED_PRIORITY"
    SOURCE_DERIVED_PRIORITY = "SOURCE_DERIVED_PRIORITY"
    UNASSESSED_PRIORITY = "UNASSESSED_PRIORITY"


class StoragePolicyViolationError(Exception):
    """Raised when an operation violates onboard storage invariants or retention policies."""
    pass


class StorageCapacityExceededError(Exception):
    """Raised when data generation exceeds configured onboard storage capacity."""
    pass


# Synthetic Demonstration Data Volume Profiles (in Bytes)
# Explicitly marked as synthetic planning demonstration models
SYNTHETIC_DATA_PROFILES_BYTES: Dict[str, int] = {
    "MEDA_TELEMETRY": 24_576,           # 24 KB: Environmental atmospheric/thermal sweeps
    "MASTCAM_Z_IMAGE": 12_582_912,       # 12 MB: Multispectral 11-filter narrowband frame
    "MASTCAM_Z_PANO": 83_886_080,        # 80 MB: High-resolution 360-degree panorama mosaic
    "SPECTROMETER_CUBE": 26_214_400,     # 25 MB: Micro-XRF / Raman spectroscopy raster cube
    "RIMFAX_RADAR_SCAN": 36_700_160,     # 35 MB: Ground-penetrating radar sounding profile
    "ENGINEERING_LOG": 1_048_576,        # 1 MB: Avionics bus and thermal telemetry log
}


def compute_product_sha256(
    product_id: str,
    instrument_id: str,
    size_bytes: int,
    created_time_s: float,
    category: str,
) -> str:
    """Compute deterministic SHA-256 fingerprint for data product identity."""
    canonical_repr = f"{product_id}|{instrument_id}|{size_bytes}|{created_time_s:.3f}|{category}"
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


@dataclass
class MissionDataProduct:
    """
    Immutable specification of an individual planetary science or engineering data product.
    """
    product_id: str
    observation_id: str
    target_id: str
    instrument_id: str
    category: DataCategory
    size_bytes: int
    created_mission_time_s: float
    priority_score: float = 50.0
    priority_type: PriorityType = PriorityType.USER_ASSIGNED_PRIORITY
    checksum_sha256: str = ""
    storage_status: DataProductStorageStatus = DataProductStorageStatus.STORED_ONBOARD
    transfer_status: DataProductTransferStatus = DataProductTransferStatus.PENDING_TRANSFER
    retention_policy: RetentionPolicy = RetentionPolicy.TRANSFER_THEN_RELEASE
    transferred_bytes: int = 0
    transfer_completion_time_s: Optional[float] = None
    is_synthetic: bool = True
    is_simulated: bool = True
    is_protected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.checksum_sha256:
            self.checksum_sha256 = compute_product_sha256(
                self.product_id,
                self.instrument_id,
                self.size_bytes,
                self.created_mission_time_s,
                self.category.value if isinstance(self.category, Enum) else str(self.category),
            )
        if self.retention_policy == RetentionPolicy.PROTECTED_PERMANENT:
            self.is_protected = True

    @property
    def is_fully_transferred(self) -> bool:
        """True if all bytes have been simulated as transferred."""
        return self.transferred_bytes >= self.size_bytes

    @property
    def remaining_bytes(self) -> int:
        """Un-transferred bytes remaining."""
        return max(0, self.size_bytes - self.transferred_bytes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert data product to serializable dictionary."""
        return {
            "product_id": self.product_id,
            "observation_id": self.observation_id,
            "target_id": self.target_id,
            "instrument_id": self.instrument_id,
            "category": self.category.value if isinstance(self.category, Enum) else str(self.category),
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / (1024 * 1024), 2),
            "created_mission_time_s": round(self.created_mission_time_s, 2),
            "priority_score": round(self.priority_score, 1),
            "priority_type": self.priority_type.value if isinstance(self.priority_type, Enum) else str(self.priority_type),
            "checksum_sha256": self.checksum_sha256,
            "storage_status": self.storage_status.value if isinstance(self.storage_status, Enum) else str(self.storage_status),
            "transfer_status": self.transfer_status.value if isinstance(self.transfer_status, Enum) else str(self.transfer_status),
            "retention_policy": self.retention_policy.value if isinstance(self.retention_policy, Enum) else str(self.retention_policy),
            "transferred_bytes": self.transferred_bytes,
            "transfer_completion_time_s": round(self.transfer_completion_time_s, 2) if self.transfer_completion_time_s is not None else None,
            "is_synthetic": self.is_synthetic,
            "is_simulated": self.is_simulated,
            "is_protected": self.is_protected,
            "metadata": self.metadata,
        }


@dataclass
class StorageLedgerEntry:
    """Snapshot entry in the chronological onboard storage accounting ledger."""
    time_s: float
    used_bytes: int
    capacity_bytes: int
    fill_ratio: float
    generated_bytes_cumulative: int
    released_bytes_cumulative: int
    transferred_bytes_cumulative: int
    backlog_bytes: int
    pressure_state: StoragePressureState
    active_event: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_s": round(self.time_s, 2),
            "used_bytes": self.used_bytes,
            "used_mb": round(self.used_bytes / (1024 * 1024), 2),
            "capacity_bytes": self.capacity_bytes,
            "capacity_mb": round(self.capacity_bytes / (1024 * 1024), 2),
            "fill_ratio": round(self.fill_ratio, 4),
            "generated_bytes_cumulative": self.generated_bytes_cumulative,
            "released_bytes_cumulative": self.released_bytes_cumulative,
            "transferred_bytes_cumulative": self.transferred_bytes_cumulative,
            "backlog_bytes": self.backlog_bytes,
            "backlog_mb": round(self.backlog_bytes / (1024 * 1024), 2),
            "pressure_state": self.pressure_state.value if isinstance(self.pressure_state, Enum) else str(self.pressure_state),
            "active_event": self.active_event,
        }


@dataclass
class SimulatedDataTransferRecord:
    """
    Forensic record of a simulated data transfer event from rover to surface base.
    Explicitly labeled as simulated transfer; no Earth downlink claimed.
    """
    transfer_id: str
    product_id: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    bytes_transferred: int
    effective_rate_bps: float
    network_path: List[str]
    hop_count: int = 1
    destination: str = "SURFACE_BASE_STATION"
    verified: bool = True
    receipt_checksum: str = ""
    label: str = "SIMULATED_DATA_TRANSFER"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transfer_id": self.transfer_id,
            "product_id": self.product_id,
            "start_time_s": round(self.start_time_s, 2),
            "end_time_s": round(self.end_time_s, 2),
            "duration_s": round(self.duration_s, 2),
            "bytes_transferred": self.bytes_transferred,
            "bytes_transferred_mb": round(self.bytes_transferred / (1024 * 1024), 2),
            "effective_rate_bps": round(self.effective_rate_bps, 1),
            "network_path": self.network_path,
            "hop_count": self.hop_count,
            "destination": self.destination,
            "verified": self.verified,
            "receipt_checksum": self.receipt_checksum,
            "label": self.label,
        }


class MissionDataLedger:
    """
    Onboard Solid-State Storage & Simulated Data Transfer Management Engine.

    Guarantees:
    1. Exact First-Law Byte Conservation: S_used(t) = S_used(t-1) + S_gen(t) - S_rel(t) with zero error.
    2. Verified Release Invariant: Memory is never released until a transfer is verified and logged.
    3. Backlog Tracking: Backlog = Generated - Transferred - Explicitly Released.
    4. Deterministic Simulated Transfer: D = R_eff * dt when line-of-sight connectivity permits.
    """

    def __init__(
        self,
        capacity_bytes: int = 17_179_869_184,  # 16 GiB default
        reserve_margin_pct: float = 20.0,
        configured_transfer_rate_bps: float = 2_000_000.0,  # 2.0 Mbps default
        protocol_overhead_pct: float = 8.0,
        duty_cycle: float = 0.85,
        destination_name: str = "SURFACE_BASE_STATION",
        strict_capacity_enforcement: bool = True,
    ):
        if capacity_bytes <= 0:
            raise ValueError(f"capacity_bytes must be strictly positive, got {capacity_bytes}")
        if configured_transfer_rate_bps <= 0:
            raise ValueError(f"configured_transfer_rate_bps must be positive, got {configured_transfer_rate_bps}")

        self.capacity_bytes: int = int(capacity_bytes)
        self.reserve_margin_pct: float = float(reserve_margin_pct)
        self.configured_transfer_rate_bps: float = float(configured_transfer_rate_bps)
        self.protocol_overhead_pct: float = float(protocol_overhead_pct)
        self.duty_cycle: float = float(duty_cycle)
        self.destination_name: str = destination_name
        self.strict_capacity_enforcement: bool = strict_capacity_enforcement

        # Ledger state
        self.products: Dict[str, MissionDataProduct] = {}
        self.transfer_queue: List[str] = []  # Ordered list of product_ids
        self.completed_transfers: List[SimulatedDataTransferRecord] = []
        self.ledger_history: List[StorageLedgerEntry] = []

        # Current accounting counters
        self.current_time_s: float = 0.0
        self.used_bytes: int = 0
        self.cumulative_generated_bytes: int = 0
        self.cumulative_released_bytes: int = 0
        self.cumulative_transferred_bytes: int = 0

        # Record initial ledger snapshot (t=0)
        self._record_snapshot(event="LEDGER_INITIALIZED")

    @property
    def effective_transfer_rate_bps(self) -> float:
        """Effective net transfer rate accounting for framing overhead and duty cycle."""
        overhead_factor = max(0.0, 1.0 - (self.protocol_overhead_pct / 100.0))
        return self.configured_transfer_rate_bps * overhead_factor * self.duty_cycle

    @property
    def effective_transfer_rate_bytes_per_sec(self) -> float:
        """Effective transfer rate in bytes per second."""
        return self.effective_transfer_rate_bps / 8.0

    @property
    def free_bytes(self) -> int:
        """Unallocated flash memory bytes."""
        return max(0, self.capacity_bytes - self.used_bytes)

    @property
    def fill_ratio(self) -> float:
        """Fraction of onboard storage used (0.0 to 1.0)."""
        if self.capacity_bytes <= 0:
            return 1.0
        return min(1.0, self.used_bytes / float(self.capacity_bytes))

    @property
    def backlog_bytes(self) -> int:
        """Total un-transferred bytes currently stored onboard."""
        total = 0
        for p in self.products.values():
            if p.storage_status in (
                DataProductStorageStatus.STORED_ONBOARD,
                DataProductStorageStatus.PARTIALLY_TRANSFERRED,
            ):
                total += p.remaining_bytes
        return total

    def _record_snapshot(self, event: str = "") -> None:
        """Record current storage state snapshot into ledger history."""
        pressure_state = self.get_storage_pressure_state()
        entry = StorageLedgerEntry(
            time_s=self.current_time_s,
            used_bytes=self.used_bytes,
            capacity_bytes=self.capacity_bytes,
            fill_ratio=self.fill_ratio,
            generated_bytes_cumulative=self.cumulative_generated_bytes,
            released_bytes_cumulative=self.cumulative_released_bytes,
            transferred_bytes_cumulative=self.cumulative_transferred_bytes,
            backlog_bytes=self.backlog_bytes,
            pressure_state=pressure_state,
            active_event=event,
        )
        self.ledger_history.append(entry)

    def get_storage_pressure_state(self) -> StoragePressureState:
        """Determine current storage pressure classification."""
        fill = self.fill_ratio
        if fill >= 0.95:
            return StoragePressureState.STORAGE_CAPACITY_REACHED
        elif fill >= 0.80:
            return StoragePressureState.STORAGE_NEAR_CAPACITY
        elif fill >= 0.60:
            return StoragePressureState.STORAGE_PRESSURE

        # Check queue backlog
        if self.backlog_bytes > 100 * 1024 * 1024:  # > 100 MB backlog
            return StoragePressureState.TRANSFER_QUEUE_BACKLOG

        # Check high priority data pending for > 3600 seconds
        for p in self.products.values():
            if (
                p.priority_score >= 80.0
                and p.transfer_status == DataProductTransferStatus.PENDING_TRANSFER
                and (self.current_time_s - p.created_mission_time_s) > 3600.0
            ):
                return StoragePressureState.HIGH_PRIORITY_DATA_PENDING

        return StoragePressureState.STORAGE_AVAILABLE

    def register_data_product(
        self,
        product: MissionDataProduct,
        current_time_s: Optional[float] = None,
    ) -> MissionDataProduct:
        """
        Record generation of a new data product into onboard solid-state storage.
        Enforces strict capacity checking and updates byte accounting.
        """
        if current_time_s is not None:
            self.current_time_s = float(current_time_s)

        if product.product_id in self.products:
            raise ValueError(f"Product ID '{product.product_id}' is already registered in ledger")

        # Capacity check
        if self.used_bytes + product.size_bytes > self.capacity_bytes:
            if self.strict_capacity_enforcement:
                raise StorageCapacityExceededError(
                    f"Registering product '{product.product_id}' ({product.size_bytes} bytes) "
                    f"exceeds capacity ({self.used_bytes} + {product.size_bytes} > {self.capacity_bytes} bytes)"
                )
            else:
                product.storage_status = DataProductStorageStatus.PURGED_OVERFLOW
                product.transfer_status = DataProductTransferStatus.TRANSFER_FAILED
                self.products[product.product_id] = product
                self._record_snapshot(event=f"PRODUCT_DROPPED_OVERFLOW:{product.product_id}")
                return product

        # Accept product
        product.storage_status = DataProductStorageStatus.STORED_ONBOARD
        product.transfer_status = DataProductTransferStatus.QUEUED
        self.products[product.product_id] = product
        self.transfer_queue.append(product.product_id)

        # Update byte conservation counters
        self.used_bytes += product.size_bytes
        self.cumulative_generated_bytes += product.size_bytes

        self._record_snapshot(event=f"PRODUCT_GENERATED:{product.product_id}")
        return product

    def simulate_transfer_window(
        self,
        start_time_s: float,
        duration_s: float,
        network_path: List[str],
        rate_multiplier: float = 1.0,
        policy: str = "PRIORITY_FIRST",  # "PRIORITY_FIRST" or "FIFO"
    ) -> List[SimulatedDataTransferRecord]:
        """
        Simulate data transfer over an active line-of-sight contact window.
        Transfers data products from queue up to available window throughput capacity.
        """
        if duration_s <= 0:
            return []

        self.current_time_s = float(start_time_s + duration_s)

        # Calculate total transferable bytes in this window
        window_rate_bps = self.effective_transfer_rate_bps * max(0.1, rate_multiplier)
        rate_bytes_per_sec = window_rate_bps / 8.0
        available_window_bytes = int(rate_bytes_per_sec * duration_s)

        if available_window_bytes <= 0:
            return []

        # Sort transfer queue according to policy
        if policy == "PRIORITY_FIRST":
            self.transfer_queue.sort(
                key=lambda pid: (
                    -self.products[pid].priority_score,
                    self.products[pid].created_mission_time_s,
                )
            )
        elif policy == "FIFO":
            self.transfer_queue.sort(
                key=lambda pid: self.products[pid].created_mission_time_s
            )

        transfers_executed: List[SimulatedDataTransferRecord] = []
        bytes_budget = available_window_bytes
        queue_remaining: List[str] = []

        window_elapsed_s = 0.0

        for pid in self.transfer_queue:
            product = self.products[pid]

            if bytes_budget <= 0:
                queue_remaining.append(pid)
                continue

            needed_bytes = product.remaining_bytes
            if needed_bytes <= 0:
                continue

            bytes_to_send = min(needed_bytes, bytes_budget)
            transfer_duration = bytes_to_send / rate_bytes_per_sec if rate_bytes_per_sec > 0 else 0.0
            item_start_time = start_time_s + window_elapsed_s
            item_end_time = item_start_time + transfer_duration
            window_elapsed_s += transfer_duration

            # Update product state
            product.transferred_bytes += bytes_to_send
            bytes_budget -= bytes_to_send
            self.cumulative_transferred_bytes += bytes_to_send

            # Check if fully transferred
            is_complete = product.is_fully_transferred
            if is_complete:
                product.transfer_status = DataProductTransferStatus.TRANSFER_VERIFIED
                product.storage_status = DataProductStorageStatus.TRANSFERRED_AND_RETAINED
                product.transfer_completion_time_s = item_end_time
            else:
                product.transfer_status = DataProductTransferStatus.IN_TRANSFER
                product.storage_status = DataProductStorageStatus.PARTIALLY_TRANSFERRED
                queue_remaining.append(pid)

            # Record transfer event
            transfer_rec = SimulatedDataTransferRecord(
                transfer_id=f"xfer_{len(self.completed_transfers) + len(transfers_executed) + 1:04d}",
                product_id=product.product_id,
                start_time_s=item_start_time,
                end_time_s=item_end_time,
                duration_s=transfer_duration,
                bytes_transferred=bytes_to_send,
                effective_rate_bps=window_rate_bps,
                network_path=list(network_path),
                hop_count=len(network_path),
                destination=self.destination_name,
                verified=True,
                receipt_checksum=product.checksum_sha256 if is_complete else "",
                label="SIMULATED_DATA_TRANSFER",
            )
            transfers_executed.append(transfer_rec)

        self.transfer_queue = queue_remaining
        self.completed_transfers.extend(transfers_executed)

        if transfers_executed:
            self._record_snapshot(event=f"SIMULATED_TRANSFER_WINDOW:{len(transfers_executed)}_PRODUCTS")

        return transfers_executed

    def release_transferred_storage(
        self,
        product_id: str,
        current_time_s: Optional[float] = None,
    ) -> int:
        """
        Releases onboard storage allocated to a verified transferred data product.

        INVARIANT:
        Storage is ONLY released AFTER a transfer has been verified and recorded.
        Attempting to release unverified or protected products raises StoragePolicyViolationError.
        """
        if current_time_s is not None:
            self.current_time_s = float(current_time_s)

        if product_id not in self.products:
            raise KeyError(f"Data product '{product_id}' not found in ledger")

        product = self.products[product_id]

        # Verify release precondition
        if product.retention_policy == RetentionPolicy.PROTECTED_PERMANENT:
            raise StoragePolicyViolationError(
                f"Cannot release protected permanent data product '{product_id}'"
            )

        if product.transfer_status != DataProductTransferStatus.TRANSFER_VERIFIED:
            raise StoragePolicyViolationError(
                f"Cannot release storage for unverified product '{product_id}' "
                f"(current status: {product.transfer_status.value})"
            )

        if product.storage_status == DataProductStorageStatus.TRANSFERRED_AND_RELEASED:
            return 0  # Already released

        # Execute release
        bytes_freed = product.size_bytes
        product.storage_status = DataProductStorageStatus.TRANSFERRED_AND_RELEASED

        self.used_bytes = max(0, self.used_bytes - bytes_freed)
        self.cumulative_released_bytes += bytes_freed

        self._record_snapshot(event=f"STORAGE_RELEASED:{product_id}:{bytes_freed}B")
        return bytes_freed

    def release_all_eligible_storage(
        self,
        current_time_s: Optional[float] = None,
    ) -> int:
        """Releases storage for all verified products adhering to TRANSFER_THEN_RELEASE policy."""
        total_freed = 0
        eligible_ids = [
            pid for pid, p in self.products.items()
            if p.transfer_status == DataProductTransferStatus.TRANSFER_VERIFIED
            and p.storage_status == DataProductStorageStatus.TRANSFERRED_AND_RETAINED
            and p.retention_policy == RetentionPolicy.TRANSFER_THEN_RELEASE
        ]
        for pid in eligible_ids:
            total_freed += self.release_transferred_storage(pid, current_time_s=current_time_s)
        return total_freed

    def verify_byte_conservation(self) -> Tuple[bool, int, str]:
        """
        Verifies the exact First-Law Byte Conservation Identity:
        S_used(t) == S_initial + sum(S_gen) - sum(S_released)

        Returns: (is_conserved: bool, discrepancy_bytes: int, message: str)
        """
        expected_used = self.cumulative_generated_bytes - self.cumulative_released_bytes
        discrepancy = self.used_bytes - expected_used

        # Also verify against itemized stored products
        itemized_used = sum(
            p.size_bytes for p in self.products.values()
            if p.storage_status in (
                DataProductStorageStatus.STORED_ONBOARD,
                DataProductStorageStatus.PARTIALLY_TRANSFERRED,
                DataProductStorageStatus.TRANSFERRED_AND_RETAINED,
            )
        )
        itemized_discrepancy = self.used_bytes - itemized_used

        if discrepancy != 0 or itemized_discrepancy != 0:
            msg = (
                f"Byte conservation violation: used={self.used_bytes}, "
                f"gen-rel={expected_used} (diff={discrepancy}), "
                f"itemized={itemized_used} (diff={itemized_discrepancy})"
            )
            return False, max(abs(discrepancy), abs(itemized_discrepancy)), msg

        return True, 0, "Exact First-Law Byte Conservation verified (0-byte error)"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete mission data ledger state."""
        is_conserved, disc, cons_msg = self.verify_byte_conservation()
        return {
            "capacity_bytes": self.capacity_bytes,
            "capacity_mb": round(self.capacity_bytes / (1024 * 1024), 2),
            "used_bytes": self.used_bytes,
            "used_mb": round(self.used_bytes / (1024 * 1024), 2),
            "free_bytes": self.free_bytes,
            "free_mb": round(self.free_bytes / (1024 * 1024), 2),
            "fill_ratio": round(self.fill_ratio, 4),
            "reserve_margin_pct": self.reserve_margin_pct,
            "configured_transfer_rate_bps": self.configured_transfer_rate_bps,
            "effective_transfer_rate_bps": round(self.effective_transfer_rate_bps, 1),
            "destination_name": self.destination_name,
            "cumulative_generated_bytes": self.cumulative_generated_bytes,
            "cumulative_generated_mb": round(self.cumulative_generated_bytes / (1024 * 1024), 2),
            "cumulative_released_bytes": self.cumulative_released_bytes,
            "cumulative_released_mb": round(self.cumulative_released_bytes / (1024 * 1024), 2),
            "cumulative_transferred_bytes": self.cumulative_transferred_bytes,
            "cumulative_transferred_mb": round(self.cumulative_transferred_bytes / (1024 * 1024), 2),
            "backlog_bytes": self.backlog_bytes,
            "backlog_mb": round(self.backlog_bytes / (1024 * 1024), 2),
            "queue_depth": len(self.transfer_queue),
            "completed_transfers_count": len(self.completed_transfers),
            "current_pressure_state": self.get_storage_pressure_state().value,
            "byte_conservation_verified": is_conserved,
            "byte_conservation_message": cons_msg,
            "products": {pid: p.to_dict() for pid, p in self.products.items()},
            "transfers": [x.to_dict() for x in self.completed_transfers],
            "ledger_history": [e.to_dict() for e in self.ledger_history],
        }
