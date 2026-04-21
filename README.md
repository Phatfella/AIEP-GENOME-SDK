# AIEP — Verifiable AI Outputs

[![CI](https://github.com/Phatfella/AIEP-GENOME-SDK/actions/workflows/ci.yml/badge.svg)](https://github.com/Phatfella/AIEP-GENOME-SDK/actions/workflows/ci.yml)
[![AIEP Conformance](https://img.shields.io/badge/AIEP--VECTORS-v1.0.0%20PASS-green)](CONFORMANCE.md)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](https://github.com/Phatfella/AIEP-GENOME-SDK/releases/tag/v1.0.0)

AIEP produces evidence-bound outputs using real sources and cryptographic proof.

Every response is backed by real, retrievable sources — hash-bound, deterministic, and independently replayable. Not a model. A protocol that governs how any system retrieves evidence, validates it, and produces outputs you can verify.

**→ [aiep.dev](https://aiep.dev)** · **[ADOPTERS.md](ADOPTERS.md)** · **[CONFORMANCE.md](CONFORMANCE.md)**

---

## Try it in 60 seconds

```bash
pip install aiep-genome-sdk
```

```python
from aiep_genome.kernel.canon import pack_hash

h = pack_hash(
    evidence_ledger=[{"evidence_id": "ev-001", "content": "CPI rose 3.2% YoY"}],
    reasoning_ledger=[{"conclusion": "Inflation is rising based on CPI data."}],
    schema_version_id="aiep.canonical.v2.0.0",
)
print(h)  # deterministic SHA-256 hex — identical on any machine
```

Output:

```
cb1a5394a39cb30ad2b9bdeb4afae26d25f7f9afbb4026f74af3b36e7146e3ae
```

---

## Standard AI vs AIEP

| Standard AI | AIEP |
|---|---|
| Generates answers | Produces evidence-bound outputs |
| No guaranteed sources | Real, retrievable sources |
| No audit trail | Cryptographic proof |
| Non-deterministic | Deterministic & replayable |

See [examples/gpt-vs-aiep](https://aiep.dev/examples/gpt-vs-aiep) — same question, two different systems, side by side.

---

## What this SDK is

This is the GENOME SDK — the reference implementation of the AIEP constitutional stack.

Install it, run the conformance suite, get `AIEP-COMPLIANT v1.0.0`. That certificate means every decision your system makes can be independently verified, replayed, and audited — by a regulator, a court, or a machine — at any point in the future.

**Kernel:** FROZEN at v1.0.0 · **Classification:** Protocol Reference Implementation + Production SaaS Foundation

---

## Repository structure

```
│   ├── canon/              ← Canonical serialisation (R1–R8)
│   ├── hashing/            ← Algorithm registry + collision policy
│   ├── validation/         ← Invariants I1–I6, GateResult
│   ├── negative_proof/     ← Temporal gap commitment (P16)
│   ├── arbitration/        ← Constitutional arbitration (Layer 1)
│   └── LOCKFILE.json       ← Kernel checksum. Mutation = version fracture.
│
├── governance/             ← Protocol logic above kernel
│   ├── policy_engine/
│   ├── dissent_registry/
│   ├── replay_engine/      ← Third-party verification (AIEP-REPLAY-001)
│   └── audit_export/
│
├── mirror/                 ← First-class. Not bolt-on.
│   ├── visibility_controller/
│   ├── registry_interface/
│   ├── public_adapter/
│   ├── private_adapter/
│   └── mirror_policy.json  ← All artefacts mirrorable. Visibility governed.
│
├── enterprise/             ← Configuration only. Never logic.
│   ├── auth/
│   ├── tenancy/
│   ├── access_control/
│   └── config/             ← What operators may configure (and what they may not)
│
├── examples/
│   ├── deterministic_trace_v1/  ← Executable conformance proof
│   └── governance_trace_v1/
│
└── security/
    ├── threat_model.md     ← AV-001 through AV-008
    ├── hash_assumptions.md ← SHA-256 assumptions + migration path
    └── attack_surface.md   ← Layer boundary rules
```

---

## The Kernel is Frozen

`kernel/` contains zero UI logic. Zero SaaS configuration. Zero external dependencies beyond Python stdlib.

Any change to any file in `kernel/` requires:
1. New `LOCKFILE_VERSION`
2. New `KERNEL_VERSION` in affected module
3. Registry update
4. All downstream repos re-pin

This is not a feature release. It is a constitutional amendment.

**Check current kernel freeze:** `cat kernel/LOCKFILE.json`

---

## Install and verify

```bash
pip install aiep-genome-sdk

# Verify the canon kernel self-tests pass on this machine
aiep-verify --self-test

# Verify against the canonical conformance vector suite
git clone https://github.com/Phatfella/AIEP-VECTORS
aiep-verify --vectors ./AIEP-VECTORS/vectors/v1.0.0/
```

Expected: `AIEP-COMPLIANT v1.0.0` — 24 vectors across 6 suites, 24/24 PASS.

```bash
# Run the worked example — computes all 8 reference hashes from scratch
python examples/complete_record/build.py
```

---

## Deterministic Replay

Run the conformance proof:

```bash
python examples/deterministic_trace_v1/trace.py
```

Expected output hashes (any conformant implementation must match):

| Step | Expected Hash |
|------|---------------|
| Canonical JSON (step 1) | `7da3d0cf50986a44d34dfd66e46d54b26d6685d508dfdada80f79153c855d7e8` |
| EvidenceCommitment (step 2) | `3bc275ffb68f68e72c9e71c20e1fdf5f924c9b16298426f0bfe29a225a5ad4af` |
| ReplayPack hash (step 5) | `827955f221a3115fe0d58e43f3bacfe9e0490c45d0aed7dbd4d6884a4e8d4075` |
| NegativeProof hash (step 6) | `5309c9344c1bc9af01f46a79dd07ec27975a6dec58509b55b2fdf870093bff56` |

If your run produces different hashes: your implementation has a canonicalisation defect.

---

## Layer Boundary Rules

| Layer | May call | May NOT call | May NOT do |
|-------|----------|--------------|------------|
| `kernel/` | itself | anything outside `kernel/` | network, filesystem, UI, config |
| `governance/` | `kernel/` | `enterprise/`, `mirror/` directly | modify kernel logic |
| `mirror/` | `kernel/`, `governance/` | `enterprise/` | override content_hash |
| `enterprise/` | all layers | — | modify kernel arbitration, inject alternative validation, override deterministic state |

**Violation of layer boundaries is a constitutional violation, not a configuration error.**

---

## What Enterprise Config May Control

✅ Mirror visibility (PUBLIC / PRIVATE / SELECTIVE)  
✅ Storage backend and location  
✅ Authentication provider  
✅ Multi-tenancy mode  

❌ Kernel hash algorithm  
❌ Unicode normalisation mode  
❌ Invariant definitions  
❌ MAX_ACTIVE_FRONTIER  
❌ Constitutional constraints  

---

## Mirror Policy

All artefacts are mirrorable. Visibility is governed, not optional at code level.

Default visibility:
- Hub deployments: `PUBLIC`
- GENOME SaaS deployments: `PRIVATE`
- Per-record override: available under `SELECTIVE` mode

Mirror `content_hash = sha256(canonical_json(data))` is a kernel-level binding. It cannot be overridden.

See `mirror/mirror_policy.json`.

---

## Security

See `security/` for:
- `threat_model.md` — 8 attack vectors, controls, residual risk
- `hash_assumptions.md` — SHA-256 assumptions, migration path
- `attack_surface.md` — Layer boundary rules, per-component surface

---

## Licence

Apache License 2.0. See `LICENSE`.
