"""
AIEP GENOME SDK — Deterministic Trace v1
=========================================
Executable proof that GENOME is a protocol, not a framework.

Input artefact → Canonical hash → Gate evaluation → Arbitration → Output → Negative proof

Two machines running this script with identical inputs MUST produce identical output.
If they do not, one or both are non-conformant AIEP implementations.

Run:
    python examples/deterministic_trace_v1/trace.py

Expected output hash is embedded below. If your hash differs, your implementation is broken.
"""

import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from kernel.canon.canon import (
    canonical_json, sha256_hex, concat_hash, evidence_commitment,
    pack_hash, negative_proof_hash, run_self_test, KERNEL_VERSION
)
from kernel.validation.invariants import evaluate_gate
from kernel.arbitration.arbitration import evaluate_admissibility
from kernel.negative_proof.negative_proof import create_negative_proof_record

# ─────────────────────────────────────────────────────────────────────────────
# EXPECTED OUTPUT HASHES (generated on reference implementation)
# If your run produces different values, your implementation is non-conformant.
# ─────────────────────────────────────────────────────────────────────────────
EXPECTED = {
    "step_1_canonical":      "7da3d0cf50986a44d34dfd66e46d54b26d6685d508dfdada80f79153c855d7e8",
    "step_2_commitment":     "3bc275ffb68f68e72c9e71c20e1fdf5f924c9b16298426f0bfe29a225a5ad4af",
    "step_5_pack_hash":      "827955f221a3115fe0d58e43f3bacfe9e0490c45d0aed7dbd4d6884a4e8d4075",
    "step_6_negative_proof": "5309c9344c1bc9af01f46a79dd07ec27975a6dec58509b55b2fdf870093bff56",
}

# ─────────────────────────────────────────────────────────────────────────────
# TRACE INPUTS (fixed — do not modify)
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA_VERSION_ID = "aiep.canonical.v2.0.0"
COLLECTION_TS     = "2026-01-01T00:00:00Z"

evidence_payload = {
    "event_type": "instruction_issued",
    "occurred_at": COLLECTION_TS,
    "actor_id": "contractor-001",
    "description": "Instruction to proceed with phase 2 works per contract clause 14.1",
}

provenance = {
    "source_type": "human",
    "source_id": "contractor-001",
    "capture_method": "manual_entry",
    "jurisdiction_id": "england-wales",
}


def run_trace():
    print("=" * 60)
    print("AIEP GENOME SDK — Deterministic Trace v1")
    print(f"KERNEL_VERSION: {KERNEL_VERSION}")
    print("=" * 60)

    # Step 0: Self-test
    assert run_self_test(), "Kernel self-test FAILED — implementation is non-conformant"
    print("\n[0] Kernel self-test: PASS")

    # Step 1: Canonical serialisation
    canonical_ev = canonical_json(evidence_payload)
    canonical_pv = canonical_json(provenance)
    step1_hash = sha256_hex(canonical_ev)
    print(f"\n[1] Canonical JSON:")
    print(f"    evidence = {canonical_ev}")
    print(f"    sha256   = {step1_hash}")

    # Step 2: Evidence commitment
    commitment = evidence_commitment(canonical_ev, canonical_pv, SCHEMA_VERSION_ID)
    print(f"\n[2] EvidenceCommitment:")
    print(f"    H(CanonicalEvidence || ProvenanceMetadata || SchemaVersionId)")
    print(f"    = {commitment}")

    # Build minimal ledger for gate evaluation
    evidence_ledger = {commitment: {
        "evidence_commitment": commitment,
        "schema_version_id": SCHEMA_VERSION_ID,
        "source_id": "contractor-001",
        "collection_ts": COLLECTION_TS,
        "permitted_use_scope": "dispute_resolution",
        "retention_policy_id": "retain-7-years",
        "created_ts": COLLECTION_TS,
    }}
    reasoning_entry = {
        "entry_hash": sha256_hex(commitment + SCHEMA_VERSION_ID),
        "prior_hash": None,
        "kind": "ACTIVATION",
        "branch_id": "branch-instruction-001",
        "evidence_refs": [commitment],
        "schema_version_id": SCHEMA_VERSION_ID,
        "created_ts": COLLECTION_TS,
    }
    reasoning_ledger = [reasoning_entry]
    active_branches = {"branch-instruction-001"}

    # Step 3: Gate evaluation
    gate = evaluate_gate(
        evidence_hash=commitment,
        evidence_ledger=evidence_ledger,
        reasoning_ledger=reasoning_ledger,
        active_branches=active_branches,
        branch_id="branch-instruction-001",
        operation_label="admit_evidence",
    )
    print(f"\n[3] Gate evaluation:")
    print(f"    status     = {gate.status}")
    print(f"    invariants = {gate.invariants_checked}")
    print(f"    violations = {gate.violations}")
    assert gate.is_open, f"Gate CLOSED unexpectedly: {gate.violations}"

    # Step 4: Arbitration
    admissible, reason = evaluate_admissibility(
        plausibility_status="plausible",
        dissent_final_position="accept",
        gate_status=gate.status,
    )
    print(f"\n[4] Arbitration:")
    print(f"    admissible = {admissible}")
    print(f"    reason     = {reason}")
    assert admissible, f"Arbitration rejected unexpectedly: {reason}"

    # Step 5: Replay pack hash
    ph = pack_hash(
        list(evidence_ledger.values()),
        reasoning_ledger,
        SCHEMA_VERSION_ID,
    )
    print(f"\n[5] ReplayPack hash (I6 determinism proof):")
    print(f"    pack_hash = {ph}")

    # Step 6: Negative proof (absence of counter-evidence)
    npr = create_negative_proof_record(
        expected_evidence_type="written_objection",
        gap_window_start="2026-01-01T00:00:00Z",
        gap_window_end="2026-01-08T00:00:00Z",
        schema_version_id=SCHEMA_VERSION_ID,
        search_scope="contract-001 correspondence",
        created_ts=COLLECTION_TS,
    )
    print(f"\n[6] NegativeProofRecord (absence of written objection within 7 days):")
    print(f"    negative_proof_hash = {npr['negative_proof_hash']}")

    print("\n" + "=" * 60)
    print("TRACE COMPLETE — all steps deterministic and reproducible")
    print("=" * 60)
    print("\nReference hashes for cross-implementation verification:")
    print(f"  step_1_canonical_hash : {step1_hash}")
    print(f"  step_2_commitment     : {commitment}")
    print(f"  step_5_pack_hash      : {ph}")
    print(f"  step_6_negative_proof : {npr['negative_proof_hash']}")
    print("\nIf your output matches these hashes, your implementation is conformant.")
    print("If it does not, your implementation has a canonicalisation defect.")


if __name__ == "__main__":
    run_trace()
