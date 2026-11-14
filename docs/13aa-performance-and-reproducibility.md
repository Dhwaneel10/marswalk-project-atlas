# Project Atlas — Milestone 13AA: Performance, Determinism & Reproducibility Audit
## Latency Benchmarking, Memory Envelope, Clean Replay Verification & Reproducibility Limits

**Document Version:** 1.0.0  
**Classification:** Performance & Numerical Reproducibility Benchmark  
**Milestone:** 13AA — Atlas Assurance Grand Prix  
**Date:** 2026-11-07  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

### 1. Hardware & Execution Benchmark Environment

- **Host Machine**: Windows 11 Home Single Language (Build 10.0.26300, 64-bit).
- **Processor**: Intel x86_64 architecture.
- **Python**: 3.12.4 (Virtual Environment `.venv`).
- **Target Daemon**: Port 3000 local HTTP API.

---

### 2. Service Latency & Throughput Profile

Measured across representative API endpoints:

| Endpoint | Subsystem | Payload Description | Mean Latency ($\text{ms}$) | Throughput Status |
| :--- | :--- | :--- | :---: | :---: |
| **`/api/health`** | Core Server | System state, 24 active endpoints, waypoints | 22.5 | Nominal |
| **`/api/planetary-network/overview`** | RelayNet | Settlement nodes, active links, constellation | 3.1 | High Speed |
| **`/api/planetary-foundry/overview`** | Foundry | 3 settlements, 18 robots, inventory mass | 2.8 | High Speed |
| **`/api/planetary-foundry/catalogue`**| Structures | 12 unpressurized assets with complete BOQ | 6.6 | High Speed |
| **`/api/preflight`** | System Health | Full 12-checkpoint integrity verification | 4,966.4 | Complete Scan |

*Analysis*: Real-time operational data endpoints respond in $\le 7\,\text{ms}$, allowing smooth 60 FPS Three.js viewport synchronization in the browser frontend without dropped frames.

---

### 3. Clean-Environment Determinism & Hash Reproducibility

To evaluate simulation determinism, the flagship 60-sol mission (`ATLAS-MARS-BASE-ALPHA-001`) was executed in two independent, clean memory states:

1. **Run 1 Root Hash**: `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`
2. **Run 2 Root Hash**: `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`
3. **Discrepancy**: Exact bitwise identity ($0$ bit delta across SHA-256 state tree).

#### Floating-Point Determinism Disclosures:
- Exact hash match proves that the deterministic event sequence and state machine transitions executed identically on the same platform and Python build.
- **Disclaimer**: An identical SHA-256 hash proves algorithmic reproducibility of the software artifact; it is **NOT proof of physical ground truth**.
