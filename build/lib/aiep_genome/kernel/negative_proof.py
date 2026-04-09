"""
AIEP GENOME SDK — Kernel: Negative Proof Record Generator (package copy)
=========================================================================
LOCKED at v1.0.0. Implements P16 deterministic temporal evidence gap commitment.
Absence of evidence is evidence. It must be committed, not ignored.
"""

from aiep_genome.kernel.canon import negative_proof_hash, sha256_hex, canonical_json

KERNEL_VERSION = "1.0.0"


def create_negative_proof_record(
    expected_evidence_type: str,
    gap_window_start: str,
    gap_window_end: str,
    schema_version_id: str,
    search_scope: str = "",
    created_ts: str = "",
) -> dict:
    """
    P16: Create a NegativeProofRecord committed to the ledger as evidence of absence.

    The negative_proof_hash commits to:
      H(expected_evidence_type || gap_window_start || gap_window_end || schema_version_id)

    This record is append-only and immutable once written.
    """
    nph = negative_proof_hash(
        expected_evidence_type, gap_window_start, gap_window_end, schema_version_id
    )
    return {
        "negative_proof_hash": nph,
        "expected_evidence_type": expected_evidence_type,
        "gap_window_start": gap_window_start,
        "gap_window_end": gap_window_end,
        "search_scope": search_scope,
        "created_ts": created_ts,
    }


def verify_negative_proof_record(record: dict, schema_version_id: str) -> bool:
    """Verify that negative_proof_hash matches recomputed value."""
    expected = negative_proof_hash(
        record["expected_evidence_type"],
        record["gap_window_start"],
        record["gap_window_end"],
        schema_version_id,
    )
    return record["negative_proof_hash"] == expected
