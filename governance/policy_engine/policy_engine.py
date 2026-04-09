"""
AIEP GENOME SDK — Governance: Policy Engine (Layer 2)
======================================================
FC §4 — Policy Layer (Primary Flexibility Engine).

Policies are artefacts. Policies are hashed. Policy version is stored
with arbitration output. Policy evaluation must be deterministic.

Policy changes do not change protocol. They change behaviour within
protocol bounds.
"""

from __future__ import annotations

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from kernel.canon.canon import canonical_json, sha256_hex

GOVERNANCE_VERSION = "1.0.0"


def hash_policy(policy: dict) -> str:
    """
    FC §4: Every policy is an artefact. Compute its canonical hash.
    policy_hash = sha256(canonical_json(policy_without_policy_hash))
    """
    core = {k: v for k, v in policy.items() if k != "policy_hash"}
    return sha256_hex(canonical_json(core))


def bind_policy(policy: dict) -> dict:
    """Return policy with policy_hash field added. Used before storing with arbitration output."""
    return {**policy, "policy_hash": hash_policy(policy)}


def evaluate_mirror_visibility(url_path: str, policy: dict) -> str:
    """
    FC §4: Mirror visibility is a policy concern (Layer 2), not a kernel concern (Layer 0).
    Returns: "PUBLIC", "PRIVATE", or "SELECTIVE"
    """
    private_prefixes = policy.get("private_prefixes", [])
    public_prefixes  = policy.get("public_prefixes", ["/"])
    default          = policy.get("mirror_visibility_default", "PRIVATE")

    for prefix in private_prefixes:
        if url_path.startswith(prefix):
            return "PRIVATE"
    for prefix in public_prefixes:
        if url_path.startswith(prefix):
            return "PUBLIC"
    return default


def evaluate_dissent_threshold(dissent_count: int, total_voters: int, policy: dict) -> str:
    """
    FC §4: Dissent threshold is a policy concern.
    Returns: "pass" | "block" | "escalate"
    """
    threshold_mode = policy.get("dissent_threshold", "majority")

    if threshold_mode == "majority":
        required = (total_voters // 2) + 1
        return "pass" if dissent_count < required else "block"
    elif threshold_mode == "unanimous":
        return "pass" if dissent_count == 0 else "block"
    elif threshold_mode == "any_dissent_escalates":
        return "escalate" if dissent_count > 0 else "pass"
    return "block"  # unknown mode — fail closed


def evaluate_retention(collection_ts: str, policy: dict) -> dict:
    """
    FC §4: Retention is a policy concern, not a kernel concern.
    Returns retention decision: {retain: bool, expiry_ts: str|None, policy_id: str}
    """
    policy_id = policy.get("retention_policy_id", "retain-7-years")
    # Retention logic belongs here, not in kernel
    # In production: parse collection_ts + retention period → expiry_ts
    return {
        "retain": True,
        "expiry_ts": None,  # computed from collection_ts + policy retention period
        "policy_id": policy_id,
    }
