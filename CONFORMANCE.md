# AIEP GENOME SDK — Conformance

## Status

[![AIEP Conformance](https://img.shields.io/badge/AIEP--VECTORS-v1.0.0%20PASS-green)](CONFORMANCE.md)

**AIEP-VECTORS v1.0.0** — 10/10 core PASS — verdict: AIEP-COMPLIANT v1.0.0  
**Kernel Version** — 1.0.0  
**LOCKFILE Version** — 1.0.0  
**CANON_SPEC Version** — 1.0.0  
**Last verified** — 2026-04-09

## Verdict Semantics

`aiep-verify` issues two distinct verdicts depending on the mode used:

| Mode | Verdict | Meaning |
|---|---|---|
| `aiep-verify record.json` | `record valid` / `record invalid` | The record's `pack_hash` is cryptographically consistent. Does **not** assert implementation compliance. |
| `aiep-verify --vectors DIR` | `AIEP-COMPLIANT v1.0.0` / `NOT COMPLIANT` | All core vectors pass. The implementation matches CANON_SPEC v1.0.0. |

A single-record "record valid" verdict confirms audit integrity, not protocol compliance.
Only the full vector suite run produces the compliance verdict.

## How to Verify

```bash
# Install (no non-stdlib dependencies)
pip install aiep-genome-sdk

# Verify any decision record produced by an AIEP-compliant system
aiep-verify path/to/decision-record.json
# → prints "record valid" or "record invalid"

# Run the full conformance suite (genome-sdk vectors)
aiep-verify --vectors vectors/v1.0.0/
# → prints "AIEP-COMPLIANT v1.0.0" or "NOT COMPLIANT"

# Run the full conformance suite (AIEP-VECTORS repo)
aiep-verify --vectors /path/to/AIEP-VECTORS/v1.0.0/

# Machine-readable output
aiep-verify --vectors vectors/v1.0.0/ --json

# Self-test only (verify the verifier itself against CANON_SPEC)
aiep-verify --self-test
```

The verifier source (`src/aiep_genome/standalone_verify.py`) is self-contained stdlib Python.
Read it in full before trusting it. The self-test checks R1–R8 against CANON_SPEC.md on every invocation.

## Claims and Tests

| Claim | Constitutional Constraint | Core Vectors | Status |
|---|---|---|---|
| Deterministic replay — identical inputs produce identical `pack_hash` | P80-I6 | det-001, det-002, det-003 | ✅ PASS |
| Unicode NFC normalisation — NFD and NFC inputs hash identically | R3 | det-002 | ✅ PASS |
| Uniqueness — changing any input changes the `pack_hash` | R8 | det-003 | ✅ PASS |
| Tamper detection — any modification to evidence or reasoning is detectable | P80-I6 | tamp-001, tamp-002 | ✅ PASS |
| Negative proof commitment — absence of evidence is hash-committed, not ignored | P16 | neg-001, neg-002 | ✅ PASS |
| Fail-closed default — gate CLOSED blocks all conclusions (CC-005) | CC-005 | adm-001 | ✅ PASS |
| Plausibility pass-through — open gate, plausible, accepted → admissible | CC-001/CC-004 | adm-002 | ✅ PASS |

Extended (informative, not required for compliance verdict):

| Claim | Test Vector | Status |
|---|---|---|
| Dissent preservation — HIGH and LOW branch reasoning produce distinct hashes | dis-001 | ✅ PASS |

## What AIEP Does Not Claim

See [BOUNDARIES.md](BOUNDARIES.md) for the full boundary documentation.

Summary:
- AIEP does not guarantee the **accuracy** of input evidence — only that outputs are traceable to committed evidence
- AIEP does not prevent a write-access attacker from constructing a false but internally consistent audit trail
- AIEP governs the **decision layer only** — not the underlying AI model's behaviour or outputs
- `pack_hash` determinism applies when `LOCKFILE_VERSION` is identical — different kernel versions are not required to produce the same hash

## Vector Files

Test vectors are in [`vectors/v1.0.0/`](vectors/v1.0.0/) (genome-sdk) and separately in the
[AIEP-VECTORS repository](https://github.com/Phatfella/AIEP-VECTORS) at tag `v1.0.0`.

Each vector is a self-contained JSON file with `input`, `expected`, `suite`, and `profile` fields.
All expected values are computed by running the locked Python kernel and committed here.

SHA-256 checksums of all vector files are in [`SHA256SUMS.txt`](SHA256SUMS.txt).

The canonical authority for all hash rules is [CANON_SPEC.md](CANON_SPEC.md) —
a language-agnostic specification of R1–R8. The Python kernel implements this spec;
it does not define it.

