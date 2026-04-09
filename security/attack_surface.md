# AIEP GENOME SDK — Attack Surface Analysis

**Version:** 1.0.0

---

## Layer Boundary Rules

The kernel/ layer has a strictly minimal attack surface by design:

| Layer | Can call kernel/ | kernel/ can call | Notes |
|-------|-----------------|-----------------|-------|
| kernel/ | ✓ (itself) | Nothing outside kernel/ | Zero external dependencies beyond Python stdlib |
| governance/ | ✓ | kernel/ only | No enterprise/ or mirror/ access |
| mirror/ | ✓ | kernel/ + governance/ | Visibility control at mirror layer |
| enterprise/ | ✓ | kernel/ + governance/ + mirror/ | Config only, never logic |
| examples/ | Read-only | All layers | For demonstration only |

**Violation of layer boundaries is a constitutional violation, not a configuration error.**

## Attack Surface by Component

### kernel/canon/ — Smallest, highest-value target
- Input: any Python object
- Output: deterministic string
- Attack surface: NFC bypass, number normalisation bypass, sort_keys bypass
- Controls: R1–R8 enforced in canon.py; self-test vectors in LOCKFILE

### kernel/validation/ — Gate logic
- Input: ledger state
- Output: GateResult (never raises)
- Attack surface: I1–I6 bypass, active_branches count manipulation
- Controls: MAX_ACTIVE_FRONTIER constant; no mutable state in gate function

### kernel/hashing/ — Algorithm registry
- Input: none (read-only constants)
- Output: algorithm identifiers
- Attack surface: registry substitution
- Controls: LOCKFILE.json pins algorithm version

### kernel/negative_proof/ — Gap commitment
- Input: temporal window, expected evidence type
- Output: NegativeProofRecord with committed hash
- Attack surface: fabricated gap, gap window manipulation
- Controls: hash binds to full window spec; schema_version_id included

### kernel/arbitration/ — Constitutional arbiter
- Input: plausibility status, dissent state, gate status
- Output: (admissible: bool, reason: str)
- Attack surface: plausibility bypass, dissent resolution forgery
- Controls: three independent conditions all required; no partial bypass

## What the Kernel Cannot Do

The kernel layer is **explicitly prohibited** from:

- Accessing the network
- Reading or writing files (except via explicit caller injection)
- Storing state (all functions are pure or accept explicit state parameters)
- Raising exceptions as control flow (GateResult pattern)
- Accepting configuration that modifies deterministic behaviour

**Configuration belongs in enterprise/. Logic belongs in kernel/. These are never the same thing.**
