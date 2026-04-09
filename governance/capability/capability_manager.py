"""
AIEP GENOME SDK — Governance: Capability Manager (Layer 1)
===========================================================
FC §3 — Capability Negotiation.

Capabilities are versioned. Selection is deterministic. Capability selection
is stored with artefact hash. Kernel output remains reproducible under any
declared capability set.

Capability expansion is allowed. Silent override is forbidden.
"""

from __future__ import annotations

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from kernel.canon.canon import canonical_json, sha256_hex

GOVERNANCE_VERSION = "1.0.0"

# Default capability set bound to LOCKFILE_VERSION 1.0.0
DEFAULT_CAPABILITIES = {
    "hash_algorithms":   ["sha256.v1"],
    "proof_types":       ["negative_proof.v1", "replay_pack.v1"],
    "mirror_modes":      ["public.v1", "private.v1", "selective.v1"],
    "policy_engine":     ["default.v1"],
    "active_frontier_max": 16,
}

# Registry of all known capability versions — immutable once published
CAPABILITY_REGISTRY = {
    "hash_algorithms": {
        "sha256.v1":    {"algorithm": "sha-256", "encoding": "hex-lower", "status": "ACTIVE"},
        "blake3.v1":    {"algorithm": "blake3",  "encoding": "hex-lower", "status": "RESERVED"},
        "sha3_256.v1":  {"algorithm": "sha3-256","encoding": "hex-lower", "status": "RESERVED"},
    },
    "proof_types": {
        "negative_proof.v1":       {"spec": "P16", "status": "ACTIVE"},
        "replay_pack.v1":          {"spec": "P80", "status": "ACTIVE"},
        "merkle_noninclusion.v1":  {"spec": "P103","status": "RESERVED"},
        "quantum_pre_evaluation.v1":{"spec":"P103","status": "RESERVED"},
    },
    "mirror_modes": {
        "public.v1":    {"visibility": "PUBLIC",   "status": "ACTIVE"},
        "private.v1":   {"visibility": "PRIVATE",  "status": "ACTIVE"},
        "selective.v1": {"visibility": "SELECTIVE", "status": "ACTIVE"},
    },
    "policy_engine": {
        "default.v1":   {"engine": "built-in", "status": "ACTIVE"},
        "dsl.v1":       {"engine": "policy-dsl","status": "RESERVED"},
        "composite.v1": {"engine": "composite", "status": "RESERVED"},
    },
}


def declare_capabilities(
    manifest_id: str,
    lockfile_version: str,
    declared_at: str,
    hash_algorithms: list[str] | None = None,
    proof_types: list[str] | None = None,
    mirror_modes: list[str] | None = None,
    policy_engine: list[str] | None = None,
    adapters_enabled: list[str] | None = None,
) -> dict:
    """
    Declare a capability manifest. Returns the manifest with capability_hash.
    This hash must be stored with every artefact produced under this capability set.

    FC §3: Selection is deterministic. capability_hash = sha256(canonical_json(manifest_core)).
    """
    caps = {
        "hash_algorithms": hash_algorithms or DEFAULT_CAPABILITIES["hash_algorithms"],
        "proof_types":     proof_types     or DEFAULT_CAPABILITIES["proof_types"],
        "mirror_modes":    mirror_modes    or DEFAULT_CAPABILITIES["mirror_modes"],
        "policy_engine":   policy_engine   or DEFAULT_CAPABILITIES["policy_engine"],
    }

    # Validate all selections are known
    for category, selected in caps.items():
        known = set(CAPABILITY_REGISTRY.get(category, {}).keys())
        unknown = set(selected) - known
        if unknown:
            raise ValueError(f"Unknown capability {category}: {unknown}. "
                             f"FC §3: capability expansion requires registry entry first.")

    manifest_core = {
        "manifest_id": manifest_id,
        "lockfile_version": lockfile_version,
        "flexibility_contract_version": "1.0.0",
        "hash_algorithms": caps["hash_algorithms"],
        "proof_types":     caps["proof_types"],
        "mirror_modes":    caps["mirror_modes"],
        "policy_engine":   caps["policy_engine"],
        "active_frontier_max": DEFAULT_CAPABILITIES["active_frontier_max"],
        "adapters_enabled": adapters_enabled or [],
        "declared_at": declared_at,
    }

    capability_hash = sha256_hex(canonical_json(manifest_core))
    return {**manifest_core, "capability_hash": capability_hash}


def verify_capability_manifest(manifest: dict) -> dict:
    """
    Verify a capability manifest's capability_hash.
    Returns {"verified": bool, "stored": str, "recomputed": str}.
    """
    stored = manifest.get("capability_hash", "")
    core = {k: v for k, v in manifest.items() if k != "capability_hash"}
    recomputed = sha256_hex(canonical_json(core))
    return {
        "verified": stored == recomputed,
        "stored": stored,
        "recomputed": recomputed,
    }


def active_hash_algorithm(manifest: dict) -> str:
    """Return the active hash algorithm version (first in list). FC §3: selection is deterministic."""
    algorithms = manifest.get("hash_algorithms", DEFAULT_CAPABILITIES["hash_algorithms"])
    return algorithms[0] if algorithms else "sha256.v1"
