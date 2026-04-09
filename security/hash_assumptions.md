# AIEP GENOME SDK — Hash Assumptions

**Version:** 1.0.0

---

## Active Algorithm

| Parameter | Value |
|-----------|-------|
| Algorithm | SHA-256 |
| Output | 256 bits / 64 hex characters |
| Encoding | Lowercase hexadecimal |
| Preimage resistance | 2^256 operations |
| Second preimage resistance | 2^256 operations |
| Collision resistance | 2^128 operations (birthday bound) |

## Assumptions

**A1:** SHA-256 preimage resistance holds for all AIEP use cases. Evidence commitments, lifecycle hashes, and pack hashes are all single-direction — no party needs to invert the hash.

**A2:** SHA-256 second preimage resistance holds. An attacker cannot produce a different payload that hashes to the same commitment as an existing record.

**A3:** Birthday attacks on SHA-256 require 2^128 operations. At current computational capabilities this is infeasible.

**A4:** Length-extension attacks are not possible against AIEP's concat_hash function because it uses length-prefixed concatenation, not raw concatenation. HMAC-style length extension does not apply.

## Dependency on Schema Version ID

Every AIEP commitment includes `schema_version_id` as a hash input. This means:

1. A payload that happens to collide with another payload under the same schema version still produces distinct commitments if the schema versions differ.
2. Cross-version record comparison is impossible without explicit version binding.
3. Breaking the hash algorithm does not break the version binding property.

## Migration Path

If SHA-256 is broken:

1. A new algorithm (e.g., SHA-3-256) is added to `kernel/hashing/algorithms.py` with `status: ACTIVE`.
2. SHA-256 transitions to `status: LEGACY`.
3. LOCKFILE_VERSION increments.
4. All new commits use the new algorithm.
5. All prior commits remain verifiable under their recorded `algorithm_version`.
6. No in-place migration is required or permitted.
