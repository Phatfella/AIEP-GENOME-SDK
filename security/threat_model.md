# AIEP GENOME SDK — Threat Model v1.1

**Classification:** Public  
**Version:** 1.1.0  
**Applies to:** All four layers per AIEP Flexibility Contract §10.  
**Supersedes:** threat_model.md v1.0.0

---

## Four-Layer Attack Surface

| Layer | Attack surface | Controls in this document |
|-------|---------------|--------------------------|
| Layer 0 — Kernel | Highest value — all hashes, all logic | AV-001 to AV-008 |
| Layer 1 — Capability | Capability manifest forgery, silent override | AV-009 |
| Layer 2 — Policy | Policy hash bypass, non-deterministic evaluation | AV-010 |
| Layer 3 — Enterprise | Auth bypass, tenancy bleed, storage tampering | Out of scope — per-deployment |
| Adapters (FC §6) | Adapter substitution, non-deterministic adapter | AV-011 |

---

## Layer 0 — Kernel Attack Vectors

### AV-001: SHA-256 Collision
**Threat:** Attacker finds two distinct payloads with identical SHA-256 digest.  
**Likelihood:** Negligible (no known SHA-256 collision).  
**Control:** AIEP-HASH-COLLISION-001 migration path defined. `schema_version_id` included in all commitments — even a collision under one schema version produces a distinct hash under another.  
**Residual risk:** Acceptable.

### AV-002: Replay of Old Commitment
**Threat:** Attacker replays a valid old evidence commitment as current.  
**Control:** All commitments include `schema_version_id`, `collection_ts`, and `expiry_ts`. Old-version replay detectable by version mismatch. AIEP-REPLAY-001 requires identical A, C, P, and LOCKFILE_VERSION for output to match — cross-version replay fails.  
**Residual risk:** Low.

### AV-003: Registry Compromise
**Threat:** Attacker substitutes a malicious schema in the registry.  
**Control:** `layer_0_locks.canonical_schema.sha256` in LOCKFILE.json. Verified at startup. Any substitution detected immediately. AIEP-NMR-001 prevents in-place mutation.  
**Residual risk:** Low, assuming LOCKFILE.json integrity maintained.

### AV-004: Silent Kernel Mutation
**Threat:** Developer silently patches `kernel/` without version increment.  
**Control:** `kernel_bundle_hash` in LOCKFILE.json covers all kernel `.py` files. CI verifies at every push. Any mutation causes hash mismatch and deployment refuses to initialise.  
**Residual risk:** Negligible under CI enforcement.

### AV-005: Concat Boundary Collision
**Threat:** `concat_hash("ab","c") == concat_hash("a","bc")` for different splits.  
**Control:** Length-prefixed-8be method. 8-byte big-endian length prefix per part. Algebraically impossible for distinct splits to produce identical byte sequences.  
**Residual risk:** None.

### AV-006: Minus-Zero Injection
**Threat:** `-0.0` treated as `0` in some implementations, hashes differently.  
**Control:** R5 number normalisation. `canon.py` raises `ValueError` on minus-zero before hashing.  
**Residual risk:** None under conformant implementation.

### AV-007: NFC Normalisation Bypass
**Threat:** `"Å"` (U+00C5) and `"A\u030A"` produce different hashes without NFC.  
**Control:** R3 NFC normalisation applied to all strings before hashing. Conformant implementations produce identical canonical form for all Unicode-equivalent inputs.  
**Residual risk:** None under conformant implementation.

### AV-008: Gate Bypass via Exception Handling
**Threat:** Caller catches exception and proceeds as if gate is OPEN.  
**Control:** GateResult dataclass pattern — gate never raises. CLOSED is data, not exception. Cannot be caught or suppressed. Rejection record appended regardless of caller behaviour.  
**Residual risk:** Low (requires intentionally non-conformant caller).

---

## Layer 1 — Capability Attack Vectors

### AV-009: Silent Capability Override (FC §3)
**Threat:** System uses a capability not declared in `capability_hash`. Attacker substitutes a capability manifest to claim a weaker hash algorithm was used.  
**Control:** `capability_hash = sha256(canonical_json(manifest_core))` stored with every artefact. Third parties can verify the declared capability set exactly. Silent override requires forging the capability_hash, which requires SHA-256 preimage attack (AV-001).  
**Detection:** `verify_capability_manifest(manifest)` function in `capability_manager.py`.  
**Residual risk:** Same as AV-001 — negligible.

---

## Layer 2 — Policy Attack Vectors

### AV-010: Policy Hash Bypass (FC §4)
**Threat:** Attacker claims a different (weaker) policy governed an arbitration decision than was actually used.  
**Control:** `policy_hash = sha256(canonical_json(policy_core))` stored with every arbitration output. Policy evaluation is deterministic — identical input produces identical output. Forging a policy_hash requires SHA-256 preimage attack.  
**Detection:** Re-evaluate policy with stored inputs and compare output.  
**Residual risk:** Same as AV-001 — negligible.

---

## Adapter Attack Vectors (FC §6)

### AV-011: Non-Deterministic Adapter
**Threat:** Adapter introduces time-based randomness or non-deterministic output, breaking AIEP-REPLAY-001.  
**Control:** FC §6 adapter invariants: deterministic for given input, no time-based randomness, no kernel state mutation. Violation detectable via pack_hash comparison — identical ledger state must produce identical hash. Non-deterministic adapter produces hash mismatch on replay.  
**Residual risk:** Low (detectable on first replay attempt).

---

## Fail-Closed State Diagram

```
   Operation requested
          │
   Evaluate I1–I6 (all checked, even if earlier fail)
   + Capability set verified (AV-009)
   + Policy determinism verified (AV-010)
          │
   ┌──────────────┐
   │  All pass?   │
   └───┬──────┬───┘
      YES    NO
       │      │
    OPEN   CLOSED
    Proceed  → Append rejection record (with capability_hash, policy_hash)
             → Suppress execution
             → Not an exception — CLOSED is deterministic state
```

**CLOSED cannot be suppressed by any instruction above the kernel.**  
**The rejection record includes `capability_hash` and `policy_hash` for full auditability.**

---

## Hash Algorithm Migration Path

If SHA-256 is broken (affects AV-001, AV-009, AV-010 simultaneously):

1. New algorithm (e.g. SHA-3-256) added to `kernel/hashing/algorithms.py` with `status: ACTIVE`
2. SHA-256 transitions to `status: LEGACY`
3. `LOCKFILE_VERSION` increments — this is a **version fracture** (FC §9)
4. Capability registry gains new entry: `sha3_256.v1`
5. All new commits use new algorithm
6. All prior commits remain verifiable under recorded `algorithm_version`
7. `capability_hash` computation for prior artefacts remains valid under SHA-256

**Migration is a version fracture, not a patch.**

---

## Security Posture Summary

| Property | Status | Reference |
|----------|--------|-----------|
| Preimage resistance | SHA-256 assumed — AV-001 | AIEP-HASH-COLLISION-001 |
| Boundary collision | Eliminated algebraically — AV-005 | R7, length-prefixed-8be |
| Replay attack | Mitigated — schema_version_id + timestamps | AIEP-REPLAY-001 |
| Silent mutation | Eliminated — kernel_bundle_hash | AIEP-NMR-001 |
| Capability forgery | Mitigated — capability_hash on every artefact | FC §3, AV-009 |
| Policy forgery | Mitigated — policy_hash on every arbitration output | FC §4, AV-010 |
| Minus-zero | Eliminated — ValueError in canon.py | R5 |
| NFC bypass | Eliminated — NFC on all strings | R3 |
| Gate bypass | Mitigated — GateResult pattern, data not exception | FC §2 |
| Adapter non-determinism | Detectable — pack_hash replay | AIEP-REPLAY-001, AV-011 |
