"""
AIEP GENOME SDK — Kernel: Probability Metadata Envelope
=========================================================
Implements P66: AIEP Probability Metadata Envelope.

Provides a structured, hashable envelope for probability metadata attached
to AIEP machine mirror pages and evidence artefacts.

Required fields (P66 §[0012]):
  - provenance_type      ("primary_source" | "secondary_source" | "derived" | "synthetic")
  - confidence_score     normalised decimal in [0.0, 1.0]
  - attestation_source   URI or structured identifier of attesting entity
  - freshness_indicator  structured object with as_of (ISO 8601) + optional ttl_seconds

Hash contract (P66 §[0013]):
  ProbabilityEnvelopeHash = H(provenance_type || confidence_score || attestation_source || freshness_canonical)

Fail-closed: validate() must return (True, None) before an envelope may be
included in a mirror page or committed to an evidence record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from aiep_genome.kernel.canon import canonical_json, concat_hash

VALID_PROVENANCE_TYPES = frozenset({
    "primary_source",
    "secondary_source",
    "derived",
    "synthetic",
})


@dataclass
class FreshnessIndicator:
    """
    P66 §[0012d]: Structured freshness indicator.

    as_of       ISO 8601 timestamp — when the source was last confirmed current.
    ttl_seconds Optional TTL in seconds after which the source should be
                considered stale and re-fetched.
    """
    as_of: str                       # ISO 8601 — required
    ttl_seconds: Optional[int] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        if not self.as_of:
            return False, "freshness_indicator.as_of is required"
        return True, None

    def to_dict(self) -> dict:
        d: dict = {"as_of": self.as_of}
        if self.ttl_seconds is not None:
            d["ttl_seconds"] = self.ttl_seconds
        return d


@dataclass
class ProbabilityEnvelope:
    """
    P66 §[0012]: Probability metadata envelope.

    Attaches structured probability/provenance metadata to AIEP artefacts.
    Must be validated before inclusion in mirror pages or evidence records.
    """
    provenance_type: str             # one of VALID_PROVENANCE_TYPES
    confidence_score: float          # [0.0, 1.0]
    attestation_source: str          # URI or structured identifier
    freshness_indicator: FreshnessIndicator

    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate all required fields per P66 §[0015].
        Returns (True, None) on success; (False, error_message) on failure.
        Validation failure means this envelope must not be committed.
        """
        if self.provenance_type not in VALID_PROVENANCE_TYPES:
            return False, (
                f"Invalid provenance_type '{self.provenance_type}'. "
                f"Must be one of: {sorted(VALID_PROVENANCE_TYPES)}"
            )
        if not (0.0 <= self.confidence_score <= 1.0):
            return False, (
                f"confidence_score {self.confidence_score!r} out of range [0.0, 1.0]"
            )
        if not self.attestation_source:
            return False, "attestation_source is required"
        valid_fresh, err = self.freshness_indicator.validate()
        if not valid_fresh:
            return False, err
        return True, None

    def compute_hash(self) -> str:
        """
        ProbabilityEnvelopeHash = H(provenance_type || confidence_score
                                    || attestation_source || freshness_canonical)
        P66 §[0013].
        confidence_score is serialised as a 6-decimal-place string for determinism.
        """
        freshness_canonical = canonical_json(self.freshness_indicator.to_dict())
        return concat_hash(
            self.provenance_type,
            str(round(self.confidence_score, 6)),
            self.attestation_source,
            freshness_canonical,
        )

    def to_dict(self) -> dict:
        """Return as a plain dict suitable for inclusion in a mirror page."""
        return {
            "provenance_type":    self.provenance_type,
            "confidence_score":   self.confidence_score,
            "attestation_source": self.attestation_source,
            "freshness_indicator": self.freshness_indicator.to_dict(),
        }


def build_probability_envelope(
    provenance_type: str,
    confidence_score: float,
    attestation_source: str,
    as_of: str,
    ttl_seconds: Optional[int] = None,
) -> ProbabilityEnvelope:
    """
    Convenience constructor — validates on creation.
    Raises ValueError if validation fails (fail-closed per P66 §[0015]).
    """
    env = ProbabilityEnvelope(
        provenance_type=provenance_type,
        confidence_score=confidence_score,
        attestation_source=attestation_source,
        freshness_indicator=FreshnessIndicator(as_of=as_of, ttl_seconds=ttl_seconds),
    )
    valid, err = env.validate()
    if not valid:
        raise ValueError(f"ProbabilityEnvelope validation failed: {err}")
    return env
