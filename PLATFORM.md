# The AIEP Platform — Repository Map

**Protocol:** Architected Instruction and Evidence Protocol  
**Patent:** GB2519711.2 and related applications  
**Kernel:** AIEP-GENOME-SDK `LOCKFILE_VERSION 1.0.2`

---

## Repository Catalogue

### Open Source (public)

| Repo | Purpose |
|------|---------|
| **AIEP-GENOME-SDK** | Protocol kernel, standalone verifier, conformance vectors. The reference implementation of the canonical serialisation engine (Rules R1–R7), all cryptographic commitment primitives, and the AIEP Flexibility Contract. Start here. |
| **AIEP-MINER** | Open-source reference implementation applied to ASIC mining fleet control. Demonstrates a production AIEP-compliant system in a demanding hardware context. |
| **AIEP-VECTORS** | Conformance test vector suite. Any implementation that passes all vectors is conformant. Required by `CONFORMANCE.md`. |

### Specification (private, patent-protected)

| Repo | Purpose |
|------|---------|
| **AIEP-DISSENT** | Dissent protocol specification. Cryptographic commitment of dissent records, resolution chains, and confidence scoring. Proprietary licence. |
| **AIEP-RECALL** | Deterministic replay specification. `recall_scope_hash` commits eligibility criteria at archival time, preventing retroactive manipulation of recall conditions. |
| **AIEP-SWARM** | Distributed coordination specification. `swarm_inclusion_proof` provides verifiable quorum proofs using hash-only commitment, no ZK cryptography required. |
| **AIEP-VALIDATOR** | Instruction validation specification. `validator_verdict_hash` makes the validator's own verdict a committed AIEP record. |

### Product (private, commercial)

| Repo | Purpose |
|------|---------|
| **AIEP-PIEA** | Production SaaS runtime. Evidence rail, worker-agent-kernel architecture, Cloudflare Workers deployment. |
| **AIEP-FORECAST** | Probabilistic forecasting engine. |

---

## Dependency Order

```
AIEP-GENOME-SDK (Layer 0 kernel)
    └── AIEP-DISSENT
    └── AIEP-RECALL
    └── AIEP-SWARM
    └── AIEP-VALIDATOR
            └── AIEP-PIEA
            └── AIEP-FORECAST

AIEP-MINER ──── AIEP-GENOME-SDK
AIEP-VECTORS ── AIEP-GENOME-SDK
```

All repos in the specification and product tiers pin to a specific `LOCKFILE_VERSION`
via their `GENOME_LOCKFILE.json`. A kernel change increments `LOCKFILE_VERSION` and
triggers a version fracture per the AIEP Flexibility Contract §9. Downstream repos
must explicitly adopt the new version — silent inheritance is not permitted.

---

## Conformance

Any implementation of the AIEP canonical serialisation engine is conformant if and
only if it produces identical output to every vector in **AIEP-VECTORS** for the
declared `LOCKFILE_VERSION`. Partial conformance is not defined.

The reference for what "identical output" means is `CANON_SPEC.md` in this repo,
not the kernel source code. The source implements the spec; the spec is the authority.

---

## Licence Summary

| Layer | Licence |
|-------|---------|
| AIEP-GENOME-SDK, AIEP-MINER, AIEP-VECTORS | Apache 2.0 |
| AIEP-DISSENT | Proprietary — patent pending GB2519711.2 |
| AIEP-RECALL, AIEP-SWARM, AIEP-VALIDATOR | Private — patent pending |
| AIEP-PIEA, AIEP-FORECAST | Private — commercial |

Apache 2.0 Section 3 grants a royalty-free patent licence to any recipient of the
open source repos for the patent claims necessarily infringed by that code. This is
the intended design: the protocol primitives are freely usable; the service layer is
commercial.
