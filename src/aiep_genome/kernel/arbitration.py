"""
AIEP GENOME SDK — Kernel: Constitutional Arbitration Engine (package copy)
===========================================================================
LOCKED at v1.0.0. Layer 1 constitutional arbitration.
No conclusion bypasses structured dissent. No fork forms outside constitutional constraints.
"""

from aiep_genome.kernel.canon import concat_hash

KERNEL_VERSION = "1.0.0"

CONSTITUTIONAL_CONSTRAINTS = {
    "CC-001": "No conclusion advances without passing plausibility filter",
    "CC-002": "No branch is deleted without a certificate (archival record)",
    "CC-003": "No inference proceeds under unresolved uncertainty — uncertainty is archived",
    "CC-004": "Dissent must be structurally resolved before a contested conclusion advances",
    "CC-005": "Fail-closed is the constitutional default — OPEN is the exception",
}


def arbitration_hash(
    branch_id: str,
    conclusion_hash: str,
    dissent_resolved: bool,
    plausibility_status: str,
    schema_version_id: str,
) -> str:
    """
    Compute arbitration commitment.
    H(branch_id || conclusion_hash || dissent_resolved || plausibility_status || schema_version_id)
    """
    return concat_hash(
        branch_id, conclusion_hash, str(dissent_resolved),
        plausibility_status, schema_version_id,
    )


def evaluate_admissibility(
    plausibility_status: str,
    dissent_final_position: str,
    gate_status: str,
) -> tuple:
    """
    Returns (admissible: bool, reason: str).
    All three conditions must pass for a conclusion to advance.
    """
    if gate_status != "OPEN":
        return False, "CC-005: Gate is CLOSED — fail-closed constitutional default"
    if plausibility_status == "implausible":
        return False, "CC-001: Plausibility filter rejected — conclusion is implausible"
    if plausibility_status == "indeterminate":
        return False, "CC-001: Plausibility indeterminate — cannot advance under uncertainty"
    if (dissent_final_position or "").lower() in ("reject", "escalate"):
        return False, "CC-004: Dissent unresolved — conclusion contested or escalated"
    return True, "ADMISSIBLE"
