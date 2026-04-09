"""
AIEP GENOME SDK — Kernel: Invariant Validation Engine
======================================================
LOCKED. Implements invariants I1–I6 as defined in docs/FAIL_CLOSED_RULES.md.
Returns GateResult — never raises. Callers must check gate.status == "OPEN".
"""

from dataclasses import dataclass, field
from typing import List, Optional

KERNEL_VERSION = "1.0.0"
MAX_ACTIVE_FRONTIER = 16


@dataclass
class GateResult:
    status: str          # "OPEN" or "CLOSED" — never anything else
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
    evidence_ledger: dict,          # evidence_hash -> LifecycleRecord
    reasoning_ledger: list,          # append-only list of ReasoningEntry
    active_branches: set,            # set of active branch_ids
    branch_id: Optional[str] = None,
    operation_label: Optional[str] = None,
) -> GateResult:
    """
    Evaluate all six invariants in order. All are checked even if earlier ones fail.
    Returns GateResult with status OPEN (all pass) or CLOSED (any fail).

    Invariants:
      I1 Evidence immutability      — evidence_hash must exist in ledger
      I2 Append-only reasoning      — no mutation of existing entries
      I3 Activation exclusivity     — at most one ACTIVE per branch_id
      I4 Cross-ledger integrity     — all evidence_refs must exist in evidence_ledger
      I5 Bounded active frontier    — active branches <= MAX_ACTIVE_FRONTIER
      I6 Deterministic replay       — checked by caller via pack_hash comparison
    """
    checked = []
    violations = []

    # I1: Evidence commitment must exist
    checked.append("I1")
    if evidence_hash not in evidence_ledger:
        violations.append(f"I1: evidence_hash {evidence_hash[:16]}... not in Evidence Ledger")

    # I2: Reasoning ledger entries are dicts with entry_hash — no mutation possible
    # at runtime; this checks structural integrity only
    checked.append("I2")
    seen_hashes = set()
    for entry in reasoning_ledger:
        eh = entry.get("entry_hash", "")
        if eh in seen_hashes:
            violations.append(f"I2: duplicate entry_hash {eh[:16]}... in Reasoning Ledger")
        seen_hashes.add(eh)

    # I3: At most one ACTIVE branch per branch_id
    checked.append("I3")
    if branch_id and reasoning_ledger:
        active_count = sum(
            1 for e in reasoning_ledger
            if e.get("branch_id") == branch_id and e.get("kind") == "ACTIVATION"
            and not any(
                f.get("branch_id") == branch_id and f.get("kind") in ("DEMOTION","ARCHIVAL")
                for f in reasoning_ledger
            )
        )
        if active_count > 1:
            violations.append(f"I3: branch {branch_id} has {active_count} ACTIVE entries (max 1)")

    # I4: All evidence_refs in reasoning_ledger must exist in evidence_ledger
    checked.append("I4")
    for entry in reasoning_ledger:
        for ref in entry.get("evidence_refs", []):
            if ref not in evidence_ledger:
                violations.append(f"I4: evidence_ref {ref[:16]}... not in Evidence Ledger")

    # I5: Active branches <= MAX_ACTIVE_FRONTIER
    checked.append("I5")
    if len(active_branches) > MAX_ACTIVE_FRONTIER:
        violations.append(f"I5: {len(active_branches)} active branches exceeds MAX_ACTIVE_FRONTIER ({MAX_ACTIVE_FRONTIER})")

    # I6: Deterministic replay — caller responsibility via pack_hash
    # We record the check but cannot verify it here without a stored reference hash
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
