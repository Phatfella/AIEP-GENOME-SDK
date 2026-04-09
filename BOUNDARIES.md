# AIEP GENOME SDK — Boundaries

This document defines what AIEP explicitly does **not** claim. Knowing the boundaries is as important as knowing the claims.

---

## What AIEP Guarantees

AIEP makes the following specific, testable, bounded guarantees:

1. **Deterministic replay** — given identical `evidence_ledger`, `reasoning_ledger`, and `schema_version_id`, any compliant implementation produces an identical `pack_hash`. See `AIEP-TV-DET-001`.

2. **Tamper detection** — any modification to a committed decision record produces a detectable `pack_hash` mismatch. See `AIEP-TV-TAMP-001`.

3. **Negative proof commitment** — evidence gaps are committed as `NegativeProofRecord` entries with their own deterministic hash, preventing silent omission of absence. See `AIEP-TV-NEG-001`.

4. **Fail-closed default** — when `gate_status` is `CLOSED`, no conclusion advances regardless of plausibility or dissent state (CC-005). See `AIEP-TV-ADM-001`.

5. **Dissent preservation** — a conclusion contested by `reject` or `escalate` dissent cannot advance until structurally resolved (CC-004). Conflicting evidence paths are preserved, not collapsed. See `AIEP-TV-ADM-002`.

---

## What AIEP Does Not Claim

### AIEP does not guarantee the accuracy of input evidence

AIEP commits evidence to an immutable ledger and verifies that conclusions are traceable to that evidence. It does not verify that the evidence itself is accurate, complete, or unbiased. A system that feeds false evidence into an AIEP-compliant ledger produces a tamper-evident record of false evidence — not a record of truth.

**Implication:** AIEP is an audit architecture, not a fact-verification system. Evidence quality is the responsibility of the evidence collection layer above AIEP.

---

### AIEP does not prevent a write-access attacker from constructing a false audit trail

An attacker with write access to the evidence ledger can construct evidence entries, compute the correct `pack_hash` for those entries, and produce a record that passes AIEP verification. The record will be internally consistent — verifiably so — but it will not be an accurate account of what actually happened.

**Implication:** AIEP tamper detection assumes the original record was honest. It detects post-commitment modification. It does not detect dishonest original recording. Ledger access control is outside AIEP's scope.

---

### AIEP governs the decision layer, not the underlying AI model

AIEP specifies how decisions are recorded, committed, and verified. It does not govern what the underlying AI model outputs, how it reasons, or whether its reasoning is correct. An AIEP-compliant system can be built on top of any AI model — including models with significant failure modes.

**Implication:** AIEP compliance does not imply model correctness. It implies that whatever the model produces is recorded, committed, and auditable.

---

### `pack_hash` determinism requires identical `LOCKFILE_VERSION`

Two implementations using different `KERNEL_VERSION` values are not required to produce the same `pack_hash` for identical inputs. Version fracture rules in `GENOME_LOCKFILE.json` govern when hash compatibility is preserved across kernel updates.

**Implication:** Long-term replay requires archiving the `LOCKFILE_VERSION` alongside the record. Cross-version replay is defined by the Flexibility Contract, not by this boundary.

---

### Source-resolved queries are not hallucination-free in the general sense

AIEP-compliant systems that use retrieved, hash-committed content cannot produce outputs unsupported by that committed content. They cannot hallucinate *about* the committed content. However:

- The committed content itself may be inaccurate
- Queries that fall outside the committed evidence set trigger negative proof records or fail-closed responses — not automatic model generation

**Precise claim:** *Source-resolved queries return the committed artefact — no interpolation, no model generation. Queries without a committed evidence basis are flagged or rejected.*

---

## Summary

| What AIEP provides | What AIEP does not provide |
|---|---|
| Deterministic, replayable decision records | Verification that those decisions are correct |
| Tamper detection after commitment | Prevention of dishonest original recording |
| Evidence-bound outputs | Evidence accuracy or completeness |
| Fail-closed defaults | Immunity to adversarial evidence injection |
| Dissent preservation | Automatic dissent resolution |
| Audit trail for the decision layer | Governance of the underlying AI model |
