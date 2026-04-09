"""
AIEP GENOME SDK — Kernel: Invariant Validation Engine (package copy)
=====================================================================
LOCKED at v1.0.0. Implements invariants I1–I6.
Returns GateResult — never raises. Callers must check gate.is_open.
"""

from dataclasses import dataclass, field
from typing import List, Optional

KERNEL_VERSION = "1.0.0"
MAX_ACTIVE_FRONTIER = 16


@dataclass
class GateResult:
    status: str                  # "OPEN" or "CLOSED" — never anything else
    invariants_checked: List[str]
    violations: List[str]
    evidence_hash: str
    branch_id: Optional[str] = None
    operation_label: Optional[str] = None

    @property
    def is_open(self) -> bool:
        return self.status == "OPEN"


def evaluate_gate(
    evidence_hash: str,
    evidence_ledger: dict,
    reasoning_ledger: list,
    active_branches: set,
    branch_id: Optional[str] = None,
    operation_label: Optional[str] = None,
) -> GateResult:
    """
    Evaluate all six invariants. All are checked even if earlier ones fail.
    Returns GateResult: OPEN (all pass) or CLOSED (any fail).

    I1  Evidence immutability    — evidence_hash must exist in ledger
    I2  Append-only reasoning    — no duplicate entry_hash in reasoning_ledger
    I3  Activation exclusivity   — at most one ACTIVE per branch_id
    I4  Cross-ledger integrity   — all evidence_refs exist in evidence_ledger
    I5  Bounded active frontier  — active branches <= MAX_ACTIVE_FRONTIER
    I6  Deterministic replay     — caller responsibility via pack_hash comparison
    """
    checked: List[str] = []
    violations: List[str] = []

    # I1
    checked.append("I1")
    if evidence_hash not in evidence_ledger:
        violations.append(f"I1: evidence_hash {evidence_hash[:16]}... not in Evidence Ledger")

    # I2
    checked.append("I2")
    seen_hashes: set = set()
    for entry in reasoning_ledger:
        eh = entry.get("entry_hash", "")
        if eh in seen_hashes:
            violations.append(f"I2: duplicate entry_hash {eh[:16]}... in Reasoning Ledger")
        seen_hashes.add(eh)

    # I3
    checked.append("I3")
    if branch_id and reasoning_ledger:
        demoted = any(
            e.get("branch_id") == branch_id and e.get("kind") in ("DEMOTION", "ARCHIVAL")
            for e in reasoning_ledger
        )
        active_count = sum(
            1 for e in reasoning_ledger
            if e.get("branch_id") == branch_id and e.get("kind") == "ACTIVATION"
        )
        if not demoted and active_count > 1:
            violations.append(
                f"I3: branch {branch_id} has {active_count} ACTIVATION entries (max 1 without demotion)"
            )

    # I4
    checked.append("I4")
    for entry in reasoning_ledger:
        for ref in entry.get("evidence_refs", []):
            if ref not in evidence_ledger:
                violations.append(f"I4: evidence_ref {ref[:16]}... not in Evidence Ledger")

    # I5
    checked.append("I5")
    if len(active_branches) > MAX_ACTIVE_FRONTIER:
        violations.append(
            f"I5: {len(active_branches)} active branches exceeds MAX_ACTIVE_FRONTIER ({MAX_ACTIVE_FRONTIER})"
        )

    # I6 — caller responsibility
    checked.append("I6")

    status = "OPEN" if not violations else "CLOSED"
    return GateResult(
        status=status,
        invariants_checked=checked,
        violations=violations,
        evidence_hash=evidence_hash,
        branch_id=branch_id,
        operation_label=operation_label,
    )
