# AIEP GENOME SDK — Conformance

## Status

[![AIEP Conformance](https://img.shields.io/badge/AIEP--VECTORS-v1.1.0%20PASS-green)](CONFORMANCE.md)
[![TS Cross-Conformance](https://img.shields.io/badge/@aiep%2Fverify-15%2F15%20PASS-blue)](packages/verify/)
[![Malformed Input](https://img.shields.io/badge/malformed--input-6%2F6%20REJECT-green)](CONFORMANCE.md)

**AIEP-VECTORS v1.1.0** — 15/15 PASS — verdict: AIEP-COMPLIANT v1.1.0  
**AIEP-VECTORS v1.0.0-malformed** — 6/6 REJECT (all inputs correctly rejected)  
**TypeScript @aiep/verify** — 15/15 core + 6/6 malformed + 7/7 self-test PASS  
**AIEP-VALIDATOR** — 10/10 CC-001–CC-005 self-test PASS  
**Kernel Version** — 1.1.0  
**LOCKFILE Version** — 1.0.0  
**CANON_SPEC Version** — 1.0.0  
**Last verified** — 2026-05-24

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
| Dissent preservation — HIGH and LOW branch reasoning produce distinct hashes | — | dis-001, dis-002 | ✅ PASS |
| Recall integrity — artefact order is canonically sorted, hash is stable | — | rec-001, rec-002 | ✅ PASS |
| Swarm inclusion proof — consensus ordering is reproducible across peers | — | swarm-001, swarm-002 | ✅ PASS |
| Malformed input rejection — NaN, Infinity, −0 are rejected, not silently coerced | R4, R5 | mal-001–mal-006 | ✅ REJECT |

TypeScript cross-conformance (@aiep/verify):

| Suite | Python result | TypeScript result | Status |
|---|---|---|---|
| deterministic-replay | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| tamper-detection | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| negative-proof | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| admissibility | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| dissent-preservation | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| dissent-hash | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| recall | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| swarm | AIEP-COMPLIANT | AIEP-COMPLIANT | ✅ MATCH |
| malformed-input | 6/6 REJECT | 6/6 REJECT | ✅ MATCH |

## What AIEP Does Not Claim

See [BOUNDARIES.md](BOUNDARIES.md) for the full boundary documentation.

Summary:
- AIEP does not guarantee the **accuracy** of input evidence — only that outputs are traceable to committed evidence
- AIEP does not prevent a write-access attacker from constructing a false but internally consistent audit trail
- AIEP governs the **decision layer only** — not the underlying AI model's behaviour or outputs
- `pack_hash` determinism applies when `LOCKFILE_VERSION` is identical — different kernel versions are not required to produce the same hash

## Vector Files

Test vectors are in [`vectors/v1.1.0/`](vectors/v1.1.0/) (genome-sdk) and separately in the
[AIEP-VECTORS repository](https://github.com/Phatfella/AIEP-VECTORS) at tag `v1.1.0`.

Malformed-input rejection vectors are at tag `v1.0.0-malformed`.

Each vector is a self-contained JSON file with `input`, `expected`, `suite`, and `profile` fields.
All expected values are computed by running the locked Python kernel and committed here.

SHA-256 checksums of all vector files are in [`SHA256SUMS.txt`](SHA256SUMS.txt).

The canonical authority for all hash rules is [CANON_SPEC.md](CANON_SPEC.md) —
a language-agnostic specification of R1–R8. The Python kernel implements this spec;
it does not define it.

---

## Downstream Conformance

Systems that consume AIEP decision records (e.g., AIEP-PIEA, AIEP-FORECAST, AIEP-MINER) must
demonstrate conformance before records from those systems may be treated as AIEP-COMPLIANT.

### What conformance means for a downstream repo

A downstream system achieves conformance when it can demonstrate:

1. **Pack hash reproducibility** — Given the same `evidence_ledger`, `reasoning_ledger`, and
   `schema_version_id`, the system produces the same `pack_hash` as the reference Python kernel.
2. **Malformed input rejection** — Inputs containing NaN, Infinity, or −0 are rejected before any
   hash is computed (not silently coerced to 0 or null).
3. **Gate enforcement** — The system never emits a decision record with `gate_status: CLOSED` and
   `verdict: admissible` at the same time (CC-005).

### Minimum CI requirement

Add the following badge and workflow to your repo's conformance statement:

```yaml
# .github/workflows/aiep-verify.yml
name: AIEP Conformance
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install aiep-genome-sdk
      - run: aiep-verify --vectors path/to/AIEP-VECTORS/v1.1.0/ --json
```

### Badge

```markdown
[![AIEP-COMPLIANT](https://img.shields.io/badge/AIEP-v1.1.0-green)](CONFORMANCE.md)
```

### CONFORMANCE.md template

Copy and fill in the following template as `CONFORMANCE.md` in your repo:

```markdown
# <Your System Name> — AIEP Conformance

[![AIEP-COMPLIANT](https://img.shields.io/badge/AIEP-v1.1.0-green)](CONFORMANCE.md)

**AIEP-VECTORS version tested:** v1.1.0  
**Last verified:** <date>  
**Kernel used:** aiep-genome-sdk v1.0.0 / @aiep/verify v1.0.0

## Pack hash cross-check

<date> — ran `aiep-verify --vectors AIEP-VECTORS/v1.1.0/` — result: AIEP-COMPLIANT v1.1.0

## Malformed input

<date> — ran `aiep-verify --vectors AIEP-VECTORS/v1.0.0-malformed/` — result: 6/6 REJECT

## Runtime enforcement

CC-001–CC-005 enforced via aiep-validator v1.0.0.
Validator record hash committed to audit log on every monitored record.

## Known deviations

None.
```

### Rules for cross-language implementations

If your repo implements the hash kernel in a language other than Python, it must additionally:

- Run all 15 AIEP-VECTORS v1.1.0 vectors and report the same `expected.pack_hash` values
- Run all 6 malformed-input vectors and confirm each raises/throws — not returns 0x000...
- Publish its `concatHash` implementation source and confirm the 8-byte big-endian length-prefix
  encoding matches [CANON_SPEC.md § R7](CANON_SPEC.md)

The TypeScript reference implementation is [`packages/verify/`](packages/verify/) in this repo.


