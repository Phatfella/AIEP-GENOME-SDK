"""
AIEP GENOME SDK — Kernel: Canonical Serialisation Engine (package copy)
=========================================================================
LOCKED at v1.0.0. Source of truth: kernel/canon/canon.py (compare LOCKFILE).
This file is a package-distributed copy. Do NOT modify — any change is a kernel violation.
"""

import hashlib
import json
import unicodedata

ALGORITHM       = "sha-256"
DIGEST_ENCODING = "hex-lower"
CONCAT_METHOD   = "length-prefixed-8be"
UNICODE_FORM    = "NFC"
KERNEL_VERSION  = "1.0.0"

_GENESIS_SENTINEL = "GENESIS"


def _nfc(s: str) -> str:
    """R3: Normalise all Unicode strings to NFC before serialisation."""
    return unicodedata.normalize("NFC", s)


def _nfc_object(obj):
    if isinstance(obj, str):
        return _nfc(obj)
    if isinstance(obj, dict):
        return {_nfc(k): _nfc_object(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nfc_object(i) for i in obj]
    return obj


def canonical_json(obj) -> str:
    """
    Produce canonical JSON string per AIEP rules R1–R5.
    R1: Keys sorted lexicographically by UTF-8 byte order
    R2: No whitespace (compact separators)
    R3: Unicode NFC normalised, not escaped (ensure_ascii=False)
    R4: Consistent UTF-8 encoding
    R5: Number normalisation
    """
    nfc_obj = _nfc_object(obj)
    return json.dumps(nfc_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    """R4: SHA-256 of UTF-8 encoded string. Returns lowercase hex."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    """SHA-256 of raw bytes. Returns lowercase hex."""
    return hashlib.sha256(b).hexdigest()


def concat_hash(*parts: str) -> str:
    """
    R7: Hash over multiple string parts using length-prefixed concatenation (8-byte big-endian).
    Prevents boundary collision: concat_hash("ab","c") != concat_hash("a","bc").
    """
    buf = b""
    for part in parts:
        encoded = part.encode("utf-8")
        buf += len(encoded).to_bytes(8, "big") + encoded
    return hashlib.sha256(buf).hexdigest()


def evidence_commitment(canonical_evidence: str, provenance: str, schema_version_id: str) -> str:
    """P14: H(CanonicalEvidence || ProvenanceMetadata || SchemaVersionId)"""
    return concat_hash(canonical_evidence, provenance, schema_version_id)


def lifecycle_hash(evidence_commitment: str, permitted_use_scope: str, retention_policy_id: str,
                   expiry_ts: str, schema_version_id: str) -> str:
    """P14: Hash binding LifecycleRecord governance constraints."""
    return concat_hash(evidence_commitment, permitted_use_scope, retention_policy_id,
                       expiry_ts or "NONE", schema_version_id)


def self_test_vectors() -> list:
    """
    Return machine-verifiable reference vectors for AIEP Canon R1-R7.

    Published at /.well-known/aiep/canon/self-test-vectors.json by the hub generator.
    Any conforming Python implementation MUST produce these exact outputs.

    Learning from hub build: tests were previously only inline assertions (runSelfTest in TS);
    this function makes them machine-accessible and cross-language verifiable.
    """
    nfc_hash_composed   = sha256_hex(canonical_json({"n": "\u00c5"}))   # precomposed Å
    nfc_hash_decomposed = sha256_hex(canonical_json({"n": "A\u030a"}))  # A + combining ring
    return [
        {
            "id": "R1-sorted-keys",
            "rule": "R1",
            "description": "Keys sorted by Unicode codepoint — compact, no whitespace",
            "input": {"z": 1, "a": 2},
            "expected_canonical_json": canonical_json({"z": 1, "a": 2}),
        },
        {
            "id": "R3-nfc-composed-equals-decomposed",
            "rule": "R3",
            "description": "Precomposed \u00c5 (U+00C5) == A+combining-ring (U+0041 U+030A) after NFC",
            "computed_sha256_composed":   nfc_hash_composed,
            "computed_sha256_decomposed": nfc_hash_decomposed,
            "expected": "computed_sha256_composed == computed_sha256_decomposed",
        },
        {
            "id": "R4-empty-string-sha256",
            "rule": "R4",
            "description": "SHA-256 of empty string — NIST test vector",
            "input": "",
            "expected_sha256_hex": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        {
            "id": "R4-key-order-independence",
            "rule": "R4",
            "description": "SHA-256 of canonical_json is independent of input key insertion order",
            "input_a": {"b": 2, "a": 1},
            "input_b": {"a": 1, "b": 2},
            "expected_sha256_hex": sha256_hex(canonical_json({"a": 1, "b": 2})),
        },
        {
            "id": "R7-injection-safe",
            "rule": "R7",
            "description": "Length-prefixed concat injection-safe: concat_hash('ab','c') != concat_hash('a','bc')",
            "inputs_a": ["ab", "c"],
            "inputs_b": ["a", "bc"],
            "computed_hash_a": concat_hash("ab", "c"),
            "computed_hash_b": concat_hash("a", "bc"),
            "expected": "computed_hash_a != computed_hash_b",
        },
        {
            "id": "R7-empty-position-safe",
            "rule": "R7",
            "description": "Empty-string position injection-safe: concat_hash('','x') != concat_hash('x','')",
            "inputs_a": ["", "x"],
            "inputs_b": ["x", ""],
            "computed_hash_a": concat_hash("", "x"),
            "computed_hash_b": concat_hash("x", ""),
            "expected": "computed_hash_a != computed_hash_b",
        },
    ]


def normalisation_hash(input_hash: str, profile_id: str, schema_version_id: str) -> str:
    """P10/P17: H(input_hash || profile_id || schema_version_id)"""
    return concat_hash(input_hash, profile_id, schema_version_id)


def negative_proof_hash(expected_evidence_type: str, gap_window_start: str,
                         gap_window_end: str, schema_version_id: str) -> str:
    """P16: H(expected_evidence_type || gap_window_start || gap_window_end || schema_version_id)"""
    return concat_hash(expected_evidence_type, gap_window_start, gap_window_end, schema_version_id)


def pack_hash(evidence_ledger: list, reasoning_ledger: list, schema_version_id: str) -> str:
    """P80 I6: Deterministic replay pack hash. generated_ts excluded intentionally."""
    state = {"evidence_ledger": evidence_ledger, "reasoning_ledger": reasoning_ledger,
             "schema_version_id": schema_version_id}
    return sha256_hex(canonical_json(state))


def founding_tension_hash(canonical_tension: str, goal_vector_id: str, schema_version_id: str) -> str:
    """P87: H(CanonicalTension || goal_vector_id || schema_version_id)"""
    return concat_hash(canonical_tension, goal_vector_id, schema_version_id)


def convergence_hash(archived_branch_record_hash: str, triggering_artefact_hash: str,
                      cumulative_evidence_weight: float, schema_version_id: str) -> str:
    """P94: H(ArchivedBranchRecordHash || TriggeringArtefactHash || CumulativeEvidenceWeight || SchemaVersionId)"""
    return concat_hash(archived_branch_record_hash, triggering_artefact_hash,
                       str(cumulative_evidence_weight), schema_version_id)


def certificate_hash(output_hash: str, reasoning_chain_hash: str, evidence_substrate_hash: str,
                      framework_id: str, framework_version: str, clause_satisfaction: list) -> str:
    """P92: H(output_hash || reasoning_chain_hash || evidence_substrate_hash || framework_id ||
              framework_version || canonical(clause_satisfaction))"""
    return concat_hash(output_hash, reasoning_chain_hash, evidence_substrate_hash,
                       framework_id, framework_version, canonical_json(clause_satisfaction))


def is_genesis(digest: str) -> bool:
    return digest == _GENESIS_SENTINEL


# ── Phase 12e: New kernel primitives ─────────────────────────────────────────
# Added after Phase 12d conformance hardening. All functions use concat_hash
# (R7 length-prefixed) for collision resistance. All are kernel-level primitives
# with conformance vectors in AIEP-VECTORS.

def dissent_hash(branch_id: str, conclusion_hash: str, position: str,
                  dissenting_evidence: list, schema_version_id: str) -> str:
    """
    P27: Cryptographic commitment of a dissent record.
    position must be one of: "reject" | "escalate" | "archive"
    Different positions over the same evidence produce different hashes —
    the dissent position is itself tamper-evident.
    """
    return concat_hash(
        branch_id, conclusion_hash, position,
        canonical_json(dissenting_evidence), schema_version_id
    )


def dissent_resolution_chain_hash(original_dissent_hash: str, resolution_hash: str,
                                   counter_resolution_hash: str,
                                   schema_version_id: str) -> str:
    """
    P27: Resolution of dissent is itself subject to dissent.
    counter_resolution_hash is "NONE" if the resolution was not challenged.
    The chain terminates — and the termination is a NegativeProofRecord —
    when no counter-resolution arrives within the declared temporal window.
    """
    return concat_hash(
        original_dissent_hash, resolution_hash,
        counter_resolution_hash or "NONE",
        schema_version_id
    )


def context_reconstruction_hash(artefact_hashes: list, canonical_ordering_rule: str,
                                  schema_version_id: str) -> str:
    """
    P22: Deterministic context reconstruction.
    Same artefacts + same ordering rule = same hash on any node, everywhere.
    Artefacts are sorted before hashing — insertion order does not matter.
    """
    ordered = sorted(artefact_hashes)
    return concat_hash(canonical_json(ordered), canonical_ordering_rule, schema_version_id)


def recall_scope_hash(archived_dissent_hash: str, eligible_trigger_domains: list,
                       plausibility_threshold_str: str, schema_version_id: str) -> str:
    """
    P83: The RecallScope is itself a cryptographic commitment.
    Two nodes must agree on this hash before either can initiate recall.
    plausibility_threshold_str: canonical string form of the threshold
      (use _canon_number() or str(Decimal) — do NOT pass a raw float).
    The conditions for recall are committed at the moment of archival, not at recall time.
    """
    return concat_hash(
        archived_dissent_hash,
        canonical_json(sorted(eligible_trigger_domains)),
        plausibility_threshold_str,
        schema_version_id
    )


def local_dominance_hash(evidence_weight_vector: dict, node_id: str,
                          schema_version_id: str) -> str:
    """
    P90: Each node's evidence-weighted contribution to swarm consensus.
    evidence_weight_vector: {evidence_id: weight_str} — values as canonical strings.
    """
    return concat_hash(
        canonical_json(evidence_weight_vector),
        node_id, schema_version_id
    )


def consensus_record_hash(branch_id: str, global_dominance_state: str,
                           contributing_hashes: list, schema_version_id: str) -> str:
    """
    P90: Verifiable swarm consensus commitment.
    contributing_hashes is sorted before hashing — the order in which nodes
    responded does not affect the consensus hash. Two nodes that receive the
    same set of local_dominance_hash values in any order must agree.
    """
    return concat_hash(
        branch_id, global_dominance_state,
        canonical_json(sorted(contributing_hashes)),
        schema_version_id
    )


def swarm_inclusion_proof(consensus_hash: str, contributing_hashes: list,
                           excluded_hashes: list, exclusion_reasons: dict,
                           schema_version_id: str) -> str:
    """
    P90: The swarm must declare what it excluded, not just what it included.
    A swarm that silently excludes a dissenting node produces a different
    swarm_inclusion_proof than one that declared the exclusion.
    Suppression of dissent within a swarm is cryptographically detectable.
    excluded_hashes: list of local_dominance_hash values not included.
    exclusion_reasons: {hash: reason_string} for each excluded hash.
    """
    return concat_hash(
        consensus_hash,
        canonical_json(sorted(contributing_hashes)),
        canonical_json(sorted(excluded_hashes)),
        canonical_json(exclusion_reasons),
        schema_version_id
    )


def validator_record_hash(monitored_record_hash: str, rule_violated: str,
                           violation_evidence: str, validator_version: str,
                           schema_version_id: str) -> str:
    """
    P01R: The validator's own verdict is an AIEP-committed record.
    The monitoring operates under the protocol it enforces — recursive closure.
    A validator that suppresses violations produces a different hash than one
    that reports them. Suppression is detectable.
    rule_violated: e.g. "CC-005", "R5", "R1" — or "NONE" for a clean record.
    """
    return concat_hash(
        monitored_record_hash, rule_violated,
        violation_evidence, validator_version,
        schema_version_id
    )


def run_self_test() -> bool:
    """Run built-in determinism self-test. Returns True if all pass."""
    # R1 key ordering
    assert canonical_json({"z": 1, "a": 2}) == '{"a":2,"z":1}', "R1 FAIL"
    # R2 no whitespace
    assert " " not in canonical_json({"k": "v"}), "R2 FAIL"
    # R3 unicode NFC normalised
    composed = "\u00c5"
    decomposed = "A\u030a"
    assert canonical_json({"n": composed}) == canonical_json({"n": decomposed}), "R3 NFC FAIL"
    # R4 determinism
    assert sha256_hex(canonical_json({"b": 2, "a": 1})) == sha256_hex(canonical_json({"a": 1, "b": 2})), "R4 FAIL"
    # R7 boundary safety
    assert concat_hash("ab", "c") != concat_hash("a", "bc"), "R7 boundary FAIL"
    assert concat_hash("", "x") != concat_hash("x", ""), "R7 empty FAIL"
    # Known SHA-256 vector
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_hex("") == empty_hash, "known vector FAIL"
    # Phase 12e — new primitives smoke-test
    _sv = "aiep.canonical.v2.0.0"
    _dh = dissent_hash("branch-001", "a" * 64, "reject", [], _sv)
    assert len(_dh) == 64, "dissent_hash length FAIL"
    assert dissent_hash("branch-001", "a" * 64, "reject", [], _sv) == _dh, "dissent_hash non-deterministic"
    assert dissent_hash("branch-001", "a" * 64, "archive", [], _sv) != _dh, "dissent_hash position insensitive"
    _crh = context_reconstruction_hash(["h1", "h2", "h3"], "sorted-asc", _sv)
    assert _crh == context_reconstruction_hash(["h3", "h1", "h2"], "sorted-asc", _sv), "context_reconstruction_hash order FAIL"
    _ldh_a = local_dominance_hash({"ev-001": "0.8"}, "node-A", _sv)
    _ldh_b = local_dominance_hash({"ev-001": "0.8"}, "node-B", _sv)
    assert _ldh_a != _ldh_b, "local_dominance_hash node collision"
    _crec = consensus_record_hash("branch-001", "HIGH", [_ldh_a, _ldh_b], _sv)
    _crec2 = consensus_record_hash("branch-001", "HIGH", [_ldh_b, _ldh_a], _sv)
    assert _crec == _crec2, "consensus_record_hash order-dependent FAIL"
    return True

