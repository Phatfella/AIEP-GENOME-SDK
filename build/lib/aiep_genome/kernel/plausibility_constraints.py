"""
AIEP GENOME SDK — Kernel: Plausibility Constraints
====================================================
Implements P67: AIEP Plausibility Constraint Format.

Provides a structured, hashable format for plausibility constraint declarations
attached to AIEP machine mirror pages and reasoning artefacts.

Constraint classes (P67 §[0010]):
  structural     — conformance with data/protocol structures
  constitutional — conformance with AIEP constitutional rules
  temporal       — time-bound validity constraints
  domain_specific — domain-knowledge plausibility checks

Result values (P67 §[0011]):
  PASS  — constraint fully satisfied
  FAIL  — constraint violated
  WARN  — constraint conditionally satisfied; agent must note

Fail-closed rule (P67 §[0014]):
  Any constraint with result=FAIL and severity_level >= 4 renders the
  associated mirror page NON-ADMISSIBLE. Agents must treat such a page as
  absent until the constraint is resolved.

Hash contract (P67 §[0013]):
  PlausibilityDeclarationHash = H(CanonicalConstraintArray || schema_id || schema_version)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from aiep_genome.kernel.canon import canonical_json, concat_hash

PLAUSIBILITY_SCHEMA_VERSION = "1.0.0"


class ConstraintResult(str, Enum):
    """P67 §[0011]: possible outcomes for a plausibility constraint evaluation."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"


class ConstraintClass(str, Enum):
    """P67 §[0010]: classification taxonomy for plausibility constraints."""
    STRUCTURAL      = "structural"
    CONSTITUTIONAL  = "constitutional"
    TEMPORAL        = "temporal"
    DOMAIN_SPECIFIC = "domain_specific"


@dataclass
class PlausibilityConstraint:
    """
    P67 §[0012]: An individual plausibility constraint declaration.

    constraint_id    Unique stable identifier for this constraint rule.
    constraint_class Classification from ConstraintClass.
    result           Evaluation outcome from ConstraintResult.
    severity_level   Integer in [1, 5]; 5 = highest severity.
    description      Optional human-readable explanation (not hashed).
    """
    constraint_id:    str
    constraint_class: ConstraintClass
    result:           ConstraintResult
    severity_level:   int               # [1, 5]
    description:      Optional[str] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        if not self.constraint_id:
            return False, "constraint_id is required"
        if not isinstance(self.constraint_class, ConstraintClass):
            return False, f"constraint_class must be a ConstraintClass member"
        if not isinstance(self.result, ConstraintResult):
            return False, f"result must be a ConstraintResult member"
        if not (1 <= self.severity_level <= 5):
            return False, (
                f"severity_level {self.severity_level!r} out of range [1, 5]"
            )
        return True, None

    def to_dict(self) -> dict:
        d = {
            "constraint_id":    self.constraint_id,
            "constraint_class": self.constraint_class.value,
            "result":           self.result.value,
            "severity_level":   self.severity_level,
        }
        if self.description is not None:
            d["description"] = self.description
        return d


def is_non_admissible(constraints: List[PlausibilityConstraint]) -> bool:
    """
    Fail-closed admissibility check (P67 §[0014]).

    Returns True if any constraint has result=FAIL and severity_level >= 4.
    When True, the associated mirror page must be treated as absent by agents.
    """
    return any(
        c.result == ConstraintResult.FAIL and c.severity_level >= 4
        for c in constraints
    )


def compute_declaration_hash(
    constraints: List[PlausibilityConstraint],
    schema_id: str,
    schema_version: str = PLAUSIBILITY_SCHEMA_VERSION,
) -> str:
    """
    PlausibilityDeclarationHash = H(CanonicalConstraintArray || schema_id || schema_version)
    P67 §[0013].

    CanonicalConstraintArray is the canonical JSON of the constraint list
    (each constraint serialised via to_dict(), ordered by constraint_id).
    """
    ordered = sorted([c.to_dict() for c in constraints], key=lambda d: d["constraint_id"])
    canonical_array = canonical_json(ordered)
    return concat_hash(canonical_array, schema_id, schema_version)


def validate_constraint_array(
    constraints: List[PlausibilityConstraint],
) -> Tuple[bool, Optional[str]]:
    """
    Validate all constraints in an array.
    Returns (True, None) if all pass; (False, first_error) otherwise.
    """
    if not constraints:
        return False, "Constraint array must not be empty"
    for i, c in enumerate(constraints):
        valid, err = c.validate()
        if not valid:
            return False, f"Constraint[{i}] ({c.constraint_id!r}): {err}"
    return True, None
