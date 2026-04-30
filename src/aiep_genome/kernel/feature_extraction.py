"""
AIEP GENOME SDK — Kernel: Feature Extraction and Similarity Computation
========================================================================
Implements P55: AIEP Feature Extraction and Similarity Computation Model.

Provides:
  - FeatureVector: structured decomposition of a reasoning output into five
    normalised sub-vectors (governance, evidence_weight, branch_resolution,
    temporal, jurisdiction).
  - SimilarityRecord: deterministic weighted-Euclidean similarity between
    two FeatureVectors with cryptographic commitment.
  - extract_feature_vector(): derive FeatureVector from a reasoning output.
  - compute_similarity(): compute SimilarityRecord between two FeatureVectors.
  - FEATURE_SCHEMA_VERSION: version-locked feature schema identifier.

Hash contract (P55 §[0011]):
  FeatureVectorHash = H(output_id || feature_values_canonical || schema_version)
  SimilarityHash    = H(fv1_id || fv2_id || similarity_score || weight_version || schema_version)

All hashes use the kernel concat_hash function (length-prefixed-8be, SHA-256).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

from aiep_genome.kernel.canon import canonical_json, concat_hash

FEATURE_SCHEMA_VERSION = "1.0.0"

# Default feature weight registry — version-locked.
# Weights retrieved from here must be treated as immutable during any
# single similarity computation. (P55 §[0012])
DEFAULT_WEIGHT_REGISTRY: Dict[str, float] = {
    "governance_rules_activated":    1.0,
    "fail_closed_rejections":        1.2,
    "constraint_proximity":          0.8,
    "evidence_weight_mean":          1.0,
    "evidence_weight_variance":      0.9,
    "evidence_confidence_ratio":     1.1,
    "active_branch_count":           0.7,
    "dominant_branch_advantage":     0.9,
    "dissent_presence":              1.0,
    "evidence_age_distribution":     0.6,
    "recent_vs_archive_ratio":       0.7,
    "jurisdiction_count":            0.8,
}
DEFAULT_WEIGHT_VERSION = "1.0.0"


@dataclass
class FeatureVector:
    """
    P55 §[0009]: A five-category normalised feature vector derived from a
    single reasoning output.

    All sub-vector values must be normalised to [0.0, 1.0] prior to storage.
    The vector hash binds output_id, all feature values, and schema_version.
    """
    output_id: str
    governance_features: Dict[str, float]       # rules activated, rejections, constraint proximity
    evidence_weight_features: Dict[str, float]  # mean, variance, confidence ratio
    branch_resolution_features: Dict[str, float]  # count, advantage, dissent
    temporal_features: Dict[str, float]         # age distribution, recent ratio
    jurisdiction_features: Dict[str, float]     # profile, jurisdiction count
    schema_version: str = FEATURE_SCHEMA_VERSION

    def compute_hash(self) -> str:
        """
        FeatureVectorHash = H(output_id || canonical(feature_values) || schema_version)
        P55 §[0011].
        """
        all_features = {
            "governance": self.governance_features,
            "evidence_weight": self.evidence_weight_features,
            "branch_resolution": self.branch_resolution_features,
            "temporal": self.temporal_features,
            "jurisdiction": self.jurisdiction_features,
        }
        return concat_hash(
            self.output_id,
            canonical_json(all_features),
            self.schema_version,
        )

    def flat_vector(self) -> Dict[str, float]:
        """Return all feature dimensions as a single flat dict keyed by dimension name."""
        flat: Dict[str, float] = {}
        flat.update(self.governance_features)
        flat.update(self.evidence_weight_features)
        flat.update(self.branch_resolution_features)
        flat.update(self.temporal_features)
        flat.update(self.jurisdiction_features)
        return flat


@dataclass
class SimilarityRecord:
    """
    P55 §[0013]: A deterministic similarity record between two FeatureVectors.

    similarity_score is normalised to [0.0, 1.0] where 1.0 = identical.
    hash binds both vector ids, the score, and the weight/schema versions.
    """
    fv1_id: str
    fv2_id: str
    distance: float
    similarity_score: float          # [0.0, 1.0]
    feature_weight_version: str
    schema_version: str = FEATURE_SCHEMA_VERSION

    def compute_hash(self) -> str:
        """
        SimilarityHash = H(fv1_id || fv2_id || similarity_score || weight_version || schema_version)
        P55 §[0013].
        Score is rounded to 6 decimal places for deterministic hashing.
        """
        return concat_hash(
            self.fv1_id,
            self.fv2_id,
            str(round(self.similarity_score, 6)),
            self.feature_weight_version,
            self.schema_version,
        )


def extract_feature_vector(
    reasoning_output: dict,
    output_id: Optional[str] = None,
    schema_version: str = FEATURE_SCHEMA_VERSION,
) -> FeatureVector:
    """
    Derive a FeatureVector from a reasoning output dict.

    P55 §[0009-0010]: Decompose into the five feature categories and normalise
    each sub-vector. The reasoning_output is expected to contain the fields
    that AIEP agents produce; absent fields default to 0.0.

    output_id defaults to the hash of the canonical reasoning output.
    """
    co = canonical_json(reasoning_output) if reasoning_output else "{}"
    from aiep_genome.kernel.canon import sha256_hex
    oid = output_id or sha256_hex(co)

    # Governance features
    gov = reasoning_output.get("governance", {})
    governance_features = {
        "governance_rules_activated": _normalise(gov.get("rules_activated", 0), 20),
        "fail_closed_rejections":     _normalise(gov.get("fail_closed_rejections", 0), 10),
        "constraint_proximity":       float(gov.get("constraint_proximity", 0.0)),
    }

    # Evidence weight features
    ev = reasoning_output.get("evidence", {})
    evidence_weight_features = {
        "evidence_weight_mean":      float(ev.get("weight_mean", 0.0)),
        "evidence_weight_variance":  float(ev.get("weight_variance", 0.0)),
        "evidence_confidence_ratio": float(ev.get("confidence_ratio", 0.0)),
    }

    # Branch resolution features
    br = reasoning_output.get("branches", {})
    branch_resolution_features = {
        "active_branch_count":        _normalise(br.get("active_count", 0), 16),
        "dominant_branch_advantage":  float(br.get("dominant_advantage", 0.0)),
        "dissent_presence":           1.0 if br.get("dissent_present", False) else 0.0,
    }

    # Temporal features
    te = reasoning_output.get("temporal", {})
    temporal_features = {
        "evidence_age_distribution": float(te.get("age_distribution_score", 0.0)),
        "recent_vs_archive_ratio":   float(te.get("recent_ratio", 0.0)),
    }

    # Jurisdiction features
    ju = reasoning_output.get("jurisdictions", {})
    jurisdiction_features = {
        "jurisdiction_count": _normalise(ju.get("distinct_count", 0), 10),
    }

    return FeatureVector(
        output_id=oid,
        governance_features=governance_features,
        evidence_weight_features=evidence_weight_features,
        branch_resolution_features=branch_resolution_features,
        temporal_features=temporal_features,
        jurisdiction_features=jurisdiction_features,
        schema_version=schema_version,
    )


def compute_similarity(
    v1: FeatureVector,
    v2: FeatureVector,
    weight_registry: Optional[Dict[str, float]] = None,
    weight_version: str = DEFAULT_WEIGHT_VERSION,
) -> SimilarityRecord:
    """
    Compute weighted Euclidean similarity between two FeatureVectors.

    P55 §[0011-0012]:
      distance(V₁, V₂) = sqrt( Σᵢ wᵢ · (V₁ᵢ − V₂ᵢ)² )
      similarity_score  = 1 / (1 + distance)   ∈ [0.0, 1.0]

    Weights are immutable for the duration of the computation and must be
    retrieved from the versioned weight_registry prior to calling this function.
    """
    if weight_registry is None:
        weight_registry = DEFAULT_WEIGHT_REGISTRY

    flat1 = v1.flat_vector()
    flat2 = v2.flat_vector()

    distance_sq = 0.0
    for dim, weight in weight_registry.items():
        val1 = flat1.get(dim, 0.0)
        val2 = flat2.get(dim, 0.0)
        distance_sq += weight * (val1 - val2) ** 2

    distance = math.sqrt(distance_sq)
    similarity_score = 1.0 / (1.0 + distance)

    return SimilarityRecord(
        fv1_id=v1.compute_hash(),
        fv2_id=v2.compute_hash(),
        distance=distance,
        similarity_score=similarity_score,
        feature_weight_version=weight_version,
        schema_version=v1.schema_version,
    )


def _normalise(value: float, max_value: float) -> float:
    """Clamp and normalise a raw count to [0.0, 1.0]."""
    if max_value <= 0:
        return 0.0
    return min(1.0, max(0.0, float(value) / float(max_value)))
