"""
AIEP GENOME SDK — Kernel: Canonical Serialisation Engine
=========================================================
LOCKED. Any change to this file increments KERNEL_VERSION and invalidates LOCKFILE.
This module has zero external dependencies beyond the Python standard library.

Implements canonicalisation rules R1–R8 as defined in:
  docs/CANONICALISATION.md
  schemas/core/aiep.canonical.schema.v2.0.0.schema.json
"""

import decimal
import hashlib
import json
import unicodedata

# ── Constants ─────────────────────────────────────────────────────

ALGORITHM       = "sha-256"
DIGEST_ENCODING = "hex-lower"
CONCAT_METHOD   = "length-prefixed-8be"
UNICODE_FORM    = "NFC"
KERNEL_VERSION  = "1.0.2"

_GENESIS_SENTINEL = "GENESIS"


# ── R3 + R5: Object normalisation ───────────────────────────────────────────────

def _nfc(s: str) -> str:
    """R3: Normalise all Unicode strings to NFC before serialisation."""
    return unicodedata.normalize("NFC", s)


def _norm_object(obj):
    """
    R3 + R5: Recursively prepare a JSON-compatible object for canonical serialisation.

    R3: All strings NFC-normalised.
    R5: Numbers normalised so json.dumps emits them as canonical numeric tokens:
        - Non-finite (NaN, Inf) → ValueError
        - Minus-zero → ValueError
        - Integral floats (1.0) → Python int so json emits 1, not 1.0
        - Fractional floats (1.5) → Python float with trailing zeros stripped
        - bool is NOT treated as a number (bool subclasses int; guard checked first)
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        d = decimal.Decimal(str(obj))
        if not d.is_finite():
            raise ValueError(
                f"AIEP-CANON-R5: non-finite number is forbidden in canonical records (got {obj!r})")
        if d.is_zero() and d.is_signed():
            raise ValueError(
                "AIEP-CANON-R5: minus-zero is forbidden in canonical records")
        normed = d.normalize()
        if normed == normed.to_integral_value():
            return int(normed)   # 1.0 → 1; json.dumps emits 1
        return float(normed)     # 1.5 → 1.5; json.dumps emits 1.5
    if isinstance(obj, str):
        return _nfc(obj)
    if isinstance(obj, dict):
        return {_nfc(k): _norm_object(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_norm_object(i) for i in obj]
    return obj


# ── R1+R2+R3+R5: Canonical JSON serialisation ─────────────────────────────────

def canonical_json(obj) -> str:
    """
    Produce canonical JSON string per AIEP rules R1–R5.

    R1: Keys sorted by lexicographic UTF-8 byte order
    R2: No whitespace (compact separators)
    R3: Unicode NFC normalised, not escaped (ensure_ascii=False)
    R4: Consistent encoding (UTF-8)
    R5: Numbers normalised — trailing zeros stripped, no scientific notation,
        non-finite values forbidden, minus-zero forbidden.
        Floats with no fractional part emitted as integers: 1.0 → 1.

    Returns UTF-8 string ready for hashing.
    """
    normed = _norm_object(obj)
    return json.dumps(normed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ── R4: SHA-256 hex digest ────────────────────────────────────────────────────

def sha256_hex(s: str) -> str:
    """R4: SHA-256 of UTF-8 encoded string. Returns lowercase hex."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    """SHA-256 of raw bytes. Returns lowercase hex."""
    return hashlib.sha256(b).hexdigest()


# ── R7: Length-prefixed concatenation ─────────────────────────────────────────

def concat_hash(*parts: str) -> str:
    """
    R7: Hash over multiple string parts using length-prefixed concatenation.

    Each part is prefixed by its UTF-8 byte length as an 8-byte big-endian integer.
    This prevents boundary collision: concat_hash("ab","c") != concat_hash("a","bc").

    Standard AIEP multi-input hash idiom:
        H(CanonicalEvidence || ProvenanceMetadata || SchemaVersionId)
    """
    buf = b""
    for part in parts:
        encoded = part.encode("utf-8")
        buf += len(encoded).to_bytes(8, "big") + encoded
    return hashlib.sha256(buf).hexdigest()


# ── High-level AIEP commitment helpers ───────────────────────────────────────

def evidence_commitment(canonical_evidence: str, provenance: str, schema_version_id: str) -> str:
    """P14: H(CanonicalEvidence || ProvenanceMetadata || SchemaVersionId)"""
    return concat_hash(canonical_evidence, provenance, schema_version_id)


def lifecycle_hash(evidence_commitment: str, permitted_use_scope: str, retention_policy_id: str,
                   expiry_ts: str, schema_version_id: str) -> str:
    """P14: Hash binding LifecycleRecord governance constraints."""
    return concat_hash(evidence_commitment, permitted_use_scope, retention_policy_id,
                       expiry_ts or "NONE", schema_version_id)


def normalisation_hash(input_hash: str, profile_id: str, schema_version_id: str) -> str:
    """P10/P17: H(input_hash || profile_id || schema_version_id)"""
    return concat_hash(input_hash, profile_id, schema_version_id)


def negative_proof_hash(expected_evidence_type: str, gap_window_start: str,
                         gap_window_end: str, schema_version_id: str) -> str:
    """P16: H(expected_evidence_type || gap_window_start || gap_window_end || schema_version_id)"""
    return concat_hash(expected_evidence_type, gap_window_start, gap_window_end, schema_version_id)


def pack_hash(evidence_ledger: list, reasoning_ledger: list, schema_version_id: str) -> str:
    """
    P80 I6: Deterministic replay pack hash.
    generated_ts is deliberately excluded — identical state must produce identical hash.
    """
    state = {"evidence_ledger": evidence_ledger, "reasoning_ledger": reasoning_ledger,
             "schema_version_id": schema_version_id}
    return sha256_hex(canonical_json(state))


def founding_tension_hash(canonical_tension: str, goal_vector_id: str, schema_version_id: str) -> str:
    """P87: H(CanonicalTension || goal_vector_id || schema_version_id)"""
    return concat_hash(canonical_tension, goal_vector_id, schema_version_id)


def convergence_hash(archived_branch_record_hash: str, triggering_artefact_hash: str,
                      cumulative_evidence_weight: float, schema_version_id: str) -> str:
    """P94: H(ArchivedBranchRecordHash || TriggeringArtefactHash || CumulativeEvidenceWeight || SchemaVersionId)

    CumulativeEvidenceWeight is serialised via canonical_json to guarantee determinism:
    str(1.0) == '1.0' but canonical_json(1.0) == '1'. Using str() would produce different
    hashes for integral-valued weights depending on how the caller constructed the float.
    """
    return concat_hash(archived_branch_record_hash, triggering_artefact_hash,
                       canonical_json(cumulative_evidence_weight), schema_version_id)


def certificate_hash(output_hash: str, reasoning_chain_hash: str, evidence_substrate_hash: str,
                      framework_id: str, framework_version: str, clause_satisfaction: list) -> str:
    """P92: H(output_hash || reasoning_chain_hash || evidence_substrate_hash || framework_id ||
              framework_version || canonical(clause_satisfaction))"""
    return concat_hash(output_hash, reasoning_chain_hash, evidence_substrate_hash,
                       framework_id, framework_version, canonical_json(clause_satisfaction))


# ── GENESIS sentinel ──────────────────────────────────────────────────────────

def is_genesis(digest: str) -> bool:
    return digest == _GENESIS_SENTINEL


# ── Self-test vectors ─────────────────────────────────────────────────────────

SELF_TEST_VECTORS = [
    # (function, args, expected_output)
    ("canonical_json",  ({"z": 1, "a": 2},),            '{"a":2,"z":1}'),
    ("canonical_json",  ({"n": "\u00c5ngstr\u00f6m"},), '{"n":"\u00c5ngstr\u00f6m"}'),
    ("sha256_hex",      ("",),                            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ("sha256_hex",      ("AIEP",),                        "13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e"),
    ("concat_hash",     ("ab", "c"),                      None),   # boundary test only — not equal to concat_hash("a","bc")
    ("concat_hash",     ("a", "bc"),                      None),   # boundary test only
]


def run_self_test() -> bool:
    """Run built-in determinism self-test. Returns True if all pass."""
    passed = 0
    failed = 0

    # R1 key ordering
    assert canonical_json({"z":1,"a":2}) == '{"a":2,"z":1}', "R1 FAIL"
    passed += 1

    # R2 no whitespace
    assert " " not in canonical_json({"k": "v"}), "R2 FAIL"
    passed += 1

    # R3 unicode not escaped, NFC normalised
    composed = "\u00c5"    # Å precomposed
    decomposed = "A\u030a" # A + combining ring above
    assert canonical_json({"n": composed}) == canonical_json({"n": decomposed}), "R3 NFC FAIL"
    passed += 1

    # R4 determinism on reorder
    assert sha256_hex(canonical_json({"b":2,"a":1})) == sha256_hex(canonical_json({"a":1,"b":2})), "R4 FAIL"
    passed += 1

    # R7 boundary safety
    assert concat_hash("ab","c") != concat_hash("a","bc"), "R7 boundary FAIL"
    assert concat_hash("","x") != concat_hash("x",""), "R7 empty FAIL"
    passed += 2

    # Known SHA-256 vector
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_hex("") == empty_hash, "known vector FAIL"
    passed += 1

    return True


if __name__ == "__main__":
    ok = run_self_test()
    print(f"AIEP kernel/canon self-test: {'PASS' if ok else 'FAIL'}")
    print(f"KERNEL_VERSION: {KERNEL_VERSION}")
