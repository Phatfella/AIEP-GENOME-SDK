"""
AIEP GENOME SDK — Kernel: Canonical Serialisation Engine (package shim)
========================================================================
PATH A: Single-source implementation. All canon logic lives in the Layer 0
locked reference. This file re-exports from that single authority.

Authority:  kernel/canon/canon.py   (Layer 0 locked reference — GENOME_LOCKFILE.json)
This file:  src/aiep_genome/kernel/canon.py  (package shim — no canon logic here)

Do NOT add canonicalisation logic to this file. CANON_SPEC.md governs
kernel/canon/canon.py. The BlobSha in GENOME_LOCKFILE.json covers that file;
this shim is not independently locked.

Path A requires editable install (pip install -e .) so that kernel/ is
resolvable relative to this file's parent tree.
"""

import importlib.util as _ilu
import pathlib as _pl

# Resolve path: src/aiep_genome/kernel/canon.py → parents[3] = genome-sdk root
_CANON_PATH = _pl.Path(__file__).resolve().parents[3] / "kernel" / "canon" / "canon.py"
_spec = _ilu.spec_from_file_location("_aiep_canon_layer0", _CANON_PATH)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

# ── Re-export constants ───────────────────────────────────────────────────────
ALGORITHM         = _mod.ALGORITHM
DIGEST_ENCODING   = _mod.DIGEST_ENCODING
CONCAT_METHOD     = _mod.CONCAT_METHOD
UNICODE_FORM      = _mod.UNICODE_FORM
KERNEL_VERSION    = _mod.KERNEL_VERSION
SELF_TEST_VECTORS = _mod.SELF_TEST_VECTORS

# Private helpers (exposed for internal package use)
_GENESIS_SENTINEL = _mod._GENESIS_SENTINEL
_nfc              = _mod._nfc
_norm_object      = _mod._norm_object
_canon_number_str = _mod._canon_number_str

# ── Re-export public functions ────────────────────────────────────────────────
canonical_json        = _mod.canonical_json
sha256_hex            = _mod.sha256_hex
sha256_bytes          = _mod.sha256_bytes
concat_hash           = _mod.concat_hash
evidence_commitment   = _mod.evidence_commitment
lifecycle_hash        = _mod.lifecycle_hash
normalisation_hash    = _mod.normalisation_hash
negative_proof_hash   = _mod.negative_proof_hash
pack_hash             = _mod.pack_hash
founding_tension_hash = _mod.founding_tension_hash
convergence_hash      = _mod.convergence_hash
certificate_hash      = _mod.certificate_hash
is_genesis            = _mod.is_genesis
run_self_test         = _mod.run_self_test


# ── Package-layer convenience (not in Layer 0) ────────────────────────────────

def self_test_vectors() -> list:
    """
    Return machine-verifiable reference vectors for AIEP Canon R1–R7.

    Package-layer convenience function — not part of the Layer 0 kernel.
    Published at /.well-known/aiep/canon/self-test-vectors.json by the hub generator.
    Any conforming implementation MUST produce these exact outputs.
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
        {
            "id": "R5-float-integral-as-integer",
            "rule": "R5",
            "description": "Float 1.0 serialised as integer 1 — no trailing .0. Cross-language hash parity.",
            "input": {"n": 1.0},
            "expected_canonical_json": '{"n":1}',
            "expected_sha256_hex": sha256_hex(canonical_json({"n": 1.0})),
        },
        {
            "id": "R5-float-fractional-preserved",
            "rule": "R5",
            "description": "Float 1.5 serialised as 1.5 — trailing zeros only stripped (1.50 → 1.5).",
            "input": {"n": 1.5},
            "expected_canonical_json": '{"n":1.5}',
            "expected_sha256_hex": sha256_hex(canonical_json({"n": 1.5})),
        },
    ]
