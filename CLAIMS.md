# AIEP — Defended Claims

Every claim listed here is:
1. Mechanically enforced by the kernel
2. Testable with a specific, machine-readable vector
3. Bounded by explicit conditions

This document is the attack surface on our terms. If you want to challenge AIEP,
start here. Every claim has a test. Run it.

---

## Claim 1 — Deterministic Replay (AIEP-REPLAY-001)

**Exact claim:**
> Any two AIEP-compliant implementations given identical `evidence_ledger`,
> `reasoning_ledger`, and `schema_version_id` with the same `LOCKFILE_VERSION`
> MUST produce identical `pack_hash`.

**Mechanism:** `pack_hash = sha256_hex(canonical_json({evidence_ledger, reasoning_ledger, schema_version_id}))`. Determinism follows from R1–R8 of CANON_SPEC.md — every rule eliminates a source of non-determinism.

**Holds when:** Implementation follows CANON_SPEC v1.0.0 exactly.
**Fails when:** Different `LOCKFILE_VERSION`, or any deviation from R1–R8 (key ordering, NFC, number normalisation, length-prefixed concat, etc.).

**Test vectors:** AIEP-TV-DET-001 (basic), AIEP-TV-DET-002 (NFC edge case), AIEP-TV-DET-003 (empty state)

```bash
aiep-verify --vectors vectors/v1.0.0/
```

---

## Claim 2 — Tamper Detection

**Exact claim:**
> Any modification to a committed decision record — evidence content, reasoning content,
> or schema_version_id — produces a detectable `pack_hash` mismatch against the stored value.

**Mechanism:** Hash of the full state. Any change to any leaf value cascades to a different root hash. Detection requires only: recompute and compare.

**Holds when:** Records are stored with their `pack_hash` intact at or after commitment.
**Fails when:** A write-access attacker modifies both the record AND the stored `pack_hash` simultaneously. See BOUNDARIES.md §B2.

**Test vectors:** AIEP-TV-TAMP-001 (evidence tampered), AIEP-TV-TAMP-002 (reasoning tampered)

---

## Claim 3 — Evidence Boundedness

**Exact claim:**
> The system will not advance a conclusion without committed evidential support.
> Evidence gaps trigger a committed `NegativeProofRecord`, not silent omission.

**Mechanism:** CC-001 (plausibility filter) and the negative proof protocol (P16) together ensure that absence of evidence is itself committed as `negative_proof_hash(type, window_start, window_end, schema)`.

**Holds when:** CC-001 and negative proof protocol are enforced before conclusion advancement.
**Fails when:** Caller bypasses `evaluate_admissibility` (misuse, outside system boundary).

**Test vectors:** AIEP-TV-NEG-001 (absence committed), AIEP-TV-NEG-002 (absence in pack_hash)

---

## Claim 4 — Fail-Closed Default (CC-005)

**Exact claim:**
> `OPEN` is the exception. `CLOSED` is the constitutional default. Any gate not
> explicitly set to `OPEN` blocks conclusion advancement.

**Mechanism:** `evaluate_admissibility` returns `(False, "CC-005: Gate is CLOSED...")` whenever `gate_status != "OPEN"`. There is no fallback output — only block.

**Holds when:** `evaluate_admissibility` is called and its result respected.
**Fails when:** Caller ignores the return value (misuse).

**Test vectors:** AIEP-TV-ADM-001 (gate CLOSED blocks passthrough admissible conclusion)

---

## Claim 5 — Dissent Structurally Blocks Advancement (CC-004)

**Exact claim:**
> A conclusion contested by `reject` or `escalate` dissent cannot advance until
> dissent is structurally resolved. No collapse to a single confident output.

**Mechanism:** `evaluate_admissibility` checks `dissent_final_position` and returns `(False, "CC-004: Dissent unresolved...")` for `reject` or `escalate`.

**Holds when:** `evaluate_admissibility` is called with the resolved dissent position.
**Fails when:** Caller bypasses arbitration (misuse).

**Test vectors:** AIEP-TV-ADM-002 (dissent rejects), AIEP-TV-ADM-003 (dissent accepted — positive case)

---

## What Is NOT Claimed Here

See [BOUNDARIES.md](BOUNDARIES.md) for the full boundary documentation.

Short version: AIEP does not claim that evidence is accurate, that the underlying model is correct, or that write-access attackers cannot construct internally consistent false records. These are explicitly documented non-claims.
