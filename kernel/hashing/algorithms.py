"""
AIEP GENOME SDK — Kernel: Hash Algorithm Registry
==================================================
LOCKED. Single authoritative source for algorithm identifiers.
Adding a new algorithm requires a new KERNEL_VERSION.
"""

KERNEL_VERSION = "1.0.0"

# Active algorithm — all new records MUST use this
ACTIVE_ALGORITHM = "sha-256"
ACTIVE_ENCODING  = "hex-lower"
ACTIVE_CONCAT    = "length-prefixed-8be"

# Algorithm registry — all historically used algorithms, immutable once added
ALGORITHM_REGISTRY = {
    "sha-256": {
        "digest_bits": 256,
        "digest_hex_chars": 64,
        "encoding": "hex-lower",
        "status": "ACTIVE",
        "activated": "2026-01-01",
    }
}

DIGEST_PATTERN = r"^[a-f0-9]{64}$"  # validates sha-256 hex-lower

COLLISION_POLICY = {
    "policy_id": "AIEP-HASH-COLLISION-001",
    "statement": "SHA-256 preimage resistance assumed. Collision resistance assumed for all current use cases. If SHA-256 is broken: (1) immediately transition to SHA-3-256 via new KERNEL_VERSION; (2) all prior commitments remain valid under prior algorithm version; (3) cross-version commitment comparison requires explicit algorithm version binding.",
    "migration_path": "New algorithm added to registry with status=ACTIVE. Old algorithm transitions to status=LEGACY. All new commits use new algorithm. Old commits remain verifiable under old algorithm via recorded algorithm_version field.",
}

TIMEOUT_POLICY = {
    "policy_id": "AIEP-TIMEOUT-001",
    "statement": "Deterministic operations have no timeout — they complete or fail atomically. Network-dependent operations (registry sync, swarm consensus) carry a schema-defined timeout. Timeout is not a gate state — it produces a rejection record, not a CLOSED gate.",
    "max_deterministic_op_ms": None,  # No timeout for pure deterministic ops
    "default_network_timeout_ms": 30000,
}
