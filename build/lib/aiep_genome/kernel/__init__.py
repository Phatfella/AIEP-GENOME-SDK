"""
aiep_genome.kernel — AIEP GENOME SDK Kernel (frozen at v1.0.0)
==============================================================
Public re-exports from the kernel modules.

    from aiep_genome.kernel import (
        canonical_json, sha256_hex, concat_hash,
        evidence_commitment, negative_proof_hash, pack_hash,
        evaluate_gate, evaluate_admissibility,
        KERNEL_VERSION, run_self_test,
    )
"""
from aiep_genome.kernel.canon import (
    canonical_json,
    sha256_hex,
    sha256_bytes,
    concat_hash,
    evidence_commitment,
    lifecycle_hash,
    normalisation_hash,
    negative_proof_hash,
    pack_hash,
    founding_tension_hash,
    convergence_hash,
    certificate_hash,
    is_genesis,
    run_self_test,
    self_test_vectors,
    KERNEL_VERSION,
    ALGORITHM,
    DIGEST_ENCODING,
    CONCAT_METHOD,
    UNICODE_FORM,
)
from aiep_genome.kernel.hashing import (
    ACTIVE_ALGORITHM,
    ACTIVE_ENCODING,
    ACTIVE_CONCAT,
    ALGORITHM_REGISTRY,
    DIGEST_PATTERN,
)
from aiep_genome.kernel.invariants import (
    GateResult,
    evaluate_gate,
    MAX_ACTIVE_FRONTIER,
)
from aiep_genome.kernel.arbitration import (
    arbitration_hash,
    evaluate_admissibility,
    CONSTITUTIONAL_CONSTRAINTS,
)
from aiep_genome.kernel.negative_proof import (
    create_negative_proof_record,
    verify_negative_proof_record,
)
from aiep_genome.kernel.divergence_graph import (
    DivergenceGraphBuilder,
    DivergenceNode,
    DIVERGENCE_OPERATORS,
)
from aiep_genome.kernel.feature_extraction import (
    FeatureVector,
    SimilarityRecord,
    extract_feature_vector,
    compute_similarity,
    FEATURE_SCHEMA_VERSION,
    DEFAULT_WEIGHT_REGISTRY,
    DEFAULT_WEIGHT_VERSION,
)
from aiep_genome.kernel.probability_metadata import (
    FreshnessIndicator,
    ProbabilityEnvelope,
    build_probability_envelope,
    VALID_PROVENANCE_TYPES,
)
from aiep_genome.kernel.plausibility_constraints import (
    ConstraintResult,
    ConstraintClass,
    PlausibilityConstraint,
    is_non_admissible,
    compute_declaration_hash,
    validate_constraint_array,
    PLAUSIBILITY_SCHEMA_VERSION,
)

__all__ = [
    # Canon
    "canonical_json", "sha256_hex", "sha256_bytes", "concat_hash",
    "evidence_commitment", "lifecycle_hash", "normalisation_hash",
    "negative_proof_hash", "pack_hash", "founding_tension_hash",
    "convergence_hash", "certificate_hash", "is_genesis", "run_self_test",
    "self_test_vectors",
    "KERNEL_VERSION", "ALGORITHM", "DIGEST_ENCODING", "CONCAT_METHOD", "UNICODE_FORM",
    # Hashing
    "ACTIVE_ALGORITHM", "ACTIVE_ENCODING", "ACTIVE_CONCAT",
    "ALGORITHM_REGISTRY", "DIGEST_PATTERN",
    # Invariants
    "GateResult", "evaluate_gate", "MAX_ACTIVE_FRONTIER",
    # Arbitration
    "arbitration_hash", "evaluate_admissibility", "CONSTITUTIONAL_CONSTRAINTS",
    # Negative proof
    "create_negative_proof_record", "verify_negative_proof_record",
    # DivergenceGraph (P01 core invention)
    "DivergenceGraphBuilder", "DivergenceNode", "DIVERGENCE_OPERATORS",
    # Feature extraction — P55
    "FeatureVector", "SimilarityRecord", "extract_feature_vector",
    "compute_similarity", "FEATURE_SCHEMA_VERSION",
    "DEFAULT_WEIGHT_REGISTRY", "DEFAULT_WEIGHT_VERSION",
    # Probability metadata envelope — P66
    "FreshnessIndicator", "ProbabilityEnvelope", "build_probability_envelope",
    "VALID_PROVENANCE_TYPES",
    # Plausibility constraints — P67
    "ConstraintResult", "ConstraintClass", "PlausibilityConstraint",
    "is_non_admissible", "compute_declaration_hash", "validate_constraint_array",
    "PLAUSIBILITY_SCHEMA_VERSION",
]
