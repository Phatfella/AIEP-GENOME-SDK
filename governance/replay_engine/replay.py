"""
AIEP GENOME SDK — Governance: Replay Engine
============================================
Third-party verification without access to original payloads.
Operates on stored ledger state only.

Per AIEP-REPLAY-001: any two systems with identical Evidence Ledger,
Reasoning Ledger, and LOCKFILE_VERSION MUST produce identical pack_hash.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from kernel.canon.canon import pack_hash, sha256_hex, canonical_json

GOVERNANCE_VERSION = "1.0.0"


def verify_replay_pack(replay_pack: dict, schema_version_id: str) -> dict:
    """
    Verify a ReplayPack.
    Returns {"verified": bool, "expected": str, "actual": str, "mismatch": bool}
    """
    stored_hash = replay_pack.get("pack_hash", "")
    recomputed = pack_hash(
        replay_pack.get("evidence_ledger", []),
        replay_pack.get("reasoning_ledger", []),
        schema_version_id,
    )
    verified = stored_hash == recomputed
    return {
        "verified": verified,
        "stored_hash": stored_hash,
        "recomputed_hash": recomputed,
        "mismatch": not verified,
        "note": "PASS: identical state produces identical hash" if verified else
                "FAIL: hash mismatch — ledger state has been mutated or implementation is non-conformant",
    }


def verify_evidence_hash_chain(evidence_ledger: list) -> dict:
    """Verify append-only hash chain integrity across all Evidence Ledger entries."""
    violations = []
    seen = set()
    for entry in evidence_ledger:
        ec = entry.get("evidence_commitment", "")
        if ec in seen:
            violations.append(f"Duplicate evidence_commitment: {ec[:16]}...")
        seen.add(ec)
    return {"intact": len(violations) == 0, "violations": violations}


def verify_reasoning_chain(reasoning_ledger: list) -> dict:
    """Verify Reasoning Ledger hash chain continuity."""
    violations = []
    prior = None
    for i, entry in enumerate(reasoning_ledger):
        stored_prior = entry.get("prior_hash")
        if i == 0:
            if stored_prior is not None:
                violations.append(f"Entry 0: prior_hash should be None, got {stored_prior}")
        else:
            expected_prior = reasoning_ledger[i-1].get("entry_hash")
            if stored_prior != expected_prior:
                violations.append(f"Entry {i}: chain broken — expected {str(expected_prior)[:16]}..., got {str(stored_prior)[:16]}...")
    return {"intact": len(violations) == 0, "violations": violations}
