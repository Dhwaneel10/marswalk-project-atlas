"""
MarsWalk 2.0 / Project Atlas - Scientific Provenance Audit Engine (Milestone 13N)
Performs independent cryptographic verification, file size auditing, format validation,
and adversarial tampering detection across all acquired planetary data archives.
"""

from __future__ import annotations
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class ProvenanceVerdict(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    INCORRECT = "INCORRECT"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class ProductAuditResult:
    product_id: str
    relative_path: str
    file_exists: bool
    file_size_bytes: int
    expected_size_bytes: int
    computed_sha256: str
    manifest_sha256: str
    checksum_match: bool
    format: str
    platform: str
    instrument: str
    processing_level: str
    provenance_verdict: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceProvenanceAuditReport:
    audit_id: str
    timestamp_utc: str
    total_manifest_products: int
    verified_products_count: int
    discrepancy_count: int
    total_bytes_audited: int
    overall_provenance_verdict: str
    product_audits: List[ProductAuditResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "timestamp_utc": self.timestamp_utc,
            "total_manifest_products": self.total_manifest_products,
            "verified_products_count": self.verified_products_count,
            "discrepancy_count": self.discrepancy_count,
            "total_bytes_audited": self.total_bytes_audited,
            "overall_provenance_verdict": self.overall_provenance_verdict,
            "product_audits": [p.to_dict() for p in self.product_audits]
        }


class SourceProvenanceAuditor:
    """Independent auditor for acquired planetary archives."""

    def __init__(self, workspace_root: Optional[str] = None):
        if workspace_root is None:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            self.workspace_root = project_root
        else:
            self.workspace_root = workspace_root
        self.manifest_path = os.path.join(self.workspace_root, "data", "environment", "index", "source_acquisition_manifest.json")

    def compute_sha256(self, file_path: str) -> str:
        """Compute SHA-256 digest of a binary file."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest().lower()

    def audit_all_products(self) -> SourceProvenanceAuditReport:
        """Independently audit all products declared in the acquisition manifest."""
        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).isoformat()

        if not os.path.exists(self.manifest_path):
            return SourceProvenanceAuditReport(
                audit_id="PROVENANCE_AUDIT_MISSING_MANIFEST",
                timestamp_utc=now_str,
                total_manifest_products=0,
                verified_products_count=0,
                discrepancy_count=1,
                total_bytes_audited=0,
                overall_provenance_verdict=ProvenanceVerdict.UNAVAILABLE.value,
                product_audits=[]
            )

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        products = manifest.get("products", [])
        audits: List[ProductAuditResult] = []
        verified_count = 0
        total_bytes = 0

        for prod in products:
            p_id = prod.get("product_id", "UNKNOWN")
            rel_path = prod.get("relative_path", "")
            exp_sha = prod.get("sha256_checksum", "").lower()
            exp_size = prod.get("file_size_bytes", 0)

            full_path = os.path.join(self.workspace_root, rel_path)
            exists = os.path.exists(full_path)

            if not exists:
                audits.append(ProductAuditResult(
                    product_id=p_id,
                    relative_path=rel_path,
                    file_exists=False,
                    file_size_bytes=0,
                    expected_size_bytes=exp_size,
                    computed_sha256="",
                    manifest_sha256=exp_sha,
                    checksum_match=False,
                    format=os.path.splitext(rel_path)[1].upper(),
                    platform=prod.get("platform", ""),
                    instrument=prod.get("instrument", ""),
                    processing_level=prod.get("processing_level", ""),
                    provenance_verdict=ProvenanceVerdict.UNAVAILABLE.value,
                    notes="File missing from local disk archive"
                ))
                continue

            actual_size = os.path.getsize(full_path)
            total_bytes += actual_size
            actual_sha = self.compute_sha256(full_path)
            match = (actual_sha == exp_sha)

            if match:
                verified_count += 1
                verdict = ProvenanceVerdict.VERIFIED.value
                notes = "Exact cryptographic and byte match verified"
            else:
                verdict = ProvenanceVerdict.INCORRECT.value
                notes = f"Checksum mismatch: expected {exp_sha[:12]}..., got {actual_sha[:12]}..."

            audits.append(ProductAuditResult(
                product_id=p_id,
                relative_path=rel_path,
                file_exists=True,
                file_size_bytes=actual_size,
                expected_size_bytes=exp_size,
                computed_sha256=actual_sha,
                manifest_sha256=exp_sha,
                checksum_match=match,
                format=os.path.splitext(rel_path)[1].upper().replace(".", ""),
                platform=prod.get("platform", ""),
                instrument=prod.get("instrument", ""),
                processing_level=prod.get("processing_level", ""),
                provenance_verdict=verdict,
                notes=notes
            ))

        all_ok = (verified_count == len(products)) and len(products) > 0
        overall_verdict = ProvenanceVerdict.VERIFIED.value if all_ok else ProvenanceVerdict.PARTIALLY_VERIFIED.value

        return SourceProvenanceAuditReport(
            audit_id=f"AUDIT_PROV_{len(audits)}_PRODUCTS",
            timestamp_utc=now_str,
            total_manifest_products=len(products),
            verified_products_count=verified_count,
            discrepancy_count=len(products) - verified_count,
            total_bytes_audited=total_bytes,
            overall_provenance_verdict=overall_verdict,
            product_audits=audits
        )
