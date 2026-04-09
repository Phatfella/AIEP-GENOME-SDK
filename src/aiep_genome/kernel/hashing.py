"""
AIEP GENOME SDK — Kernel: Hash Algorithm Registry (package copy)
=================================================================
LOCKED at v1.0.0. Do NOT modify.
"""

KERNEL_VERSION = "1.0.0"

ACTIVE_ALGORITHM = "sha-256"
ACTIVE_ENCODING  = "hex-lower"
ACTIVE_CONCAT    = "length-prefixed-8be"

ALGORITHM_REGISTRY = {
    "sha-256": {
        "digest_bits": 256,
        "digest_hex_chars": 64,
        "encoding": "hex-lower",
        "status": "ACTIVE",
        "activated": "2026-01-01",
    }
}

DIGEST_PATTERN = r"^[a-f0-9]{64}$"

COLLISION_POLICY = {
    "policy_id": "AIEP-HASH-COLLISION-001",
    "statement": (
        "SHA-256 preimage resistance assumed. If SHA-256 is broken: "
        "(1) transition to SHA-3-256 via new KERNEL_VERSION; "
        "(2) all prior commitments remain valid under prior algorithm version; "
        "(3) cross-version commitment comparison requires explicit algorithm version binding."
    ),
    "migration_path": (
        "New algorithm added to registry with status=ACTIVE. "
        "Old algorithm transitions to status=LEGACY."
    ),
}

TIMEOUT_POLICY = {
    "policy_id": "AIEP-TIMEOUT-001",
    "statement": (
        "Deterministic operations have no timeout — they complete or fail atomically. "
        "Network-dependent operations carry a schema-defined timeout. "
        "Timeout produces a rejection record, not a CLOSED gate."
    ),
    "max_deterministic_op_ms": None,
    "default_network_timeout_ms": 30000,
}
