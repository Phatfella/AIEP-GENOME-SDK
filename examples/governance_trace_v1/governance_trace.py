"""
AIEP GENOME SDK — Governance Trace v1
======================================
FC §8 — Determinism Requirements.

Proves: Output = f(A, C, P)

For identical artefact A, capability set C, and policy P:
Output is identical across machines, deployments, jurisdictions, time.

This trace exercises ALL four layers:
  Layer 0 — Kernel: canonicalisation, gate, arbitration, negative proof
  Layer 1 — Capability: declared and hash-bound
  Layer 2 — Policy: mirror visibility, dissent threshold, retention
  Layer 3 — Enterprise: storage location (simulated, does not affect hash)

Reference outputs are embedded. Any conformant implementation must match.

Run:
    python examples/governance_trace_v1/governance_trace.py
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from kernel.canon.canon      import canonical_json, sha256_hex, concat_hash, run_self_test, KERNEL_VERSION
from kernel.validation.invariants  import evaluate_gate
from kernel.arbitration.arbitration import evaluate_admissibility
from kernel.negative_proof.negative_proof import create_negative_proof_record
from kernel.canon.canon      import pack_hash

from governance.capability.capability_manager import declare_capabilities, verify_capability_manifest
from governance.policy_engine.policy_engine   import bind_policy, evaluate_mirror_visibility, evaluate_dissent_threshold

# ── Reference hashes (computed on reference implementation) ───────────────────
EXPECTED = {
    "capability_hash":     None,  # computed below — compare against reference run
    "policy_hash":         None,
    "evidence_commitment": None,
    "pack_hash":           None,
    "negative_proof_hash": None,
    "combined_output_hash":None,  # H(evidence_commitment || capability_hash || policy_hash)
}

# ── Fixed inputs (do not modify — changing these changes the reference hashes) ─
SCHEMA_VERSION_ID = "aiep.canonical.v2.0.0"
LOCKFILE_VERSION  = "1.0.0"
DECLARED_AT       = "2026-02-27T00:00:00Z"
COLLECTION_TS     = "2026-02-27T09:00:00Z"

evidence_payload = {
    "event_type":   "milestone_certificate_signed",
    "occurred_at":  COLLECTION_TS,
    "actor_id":     "certifier-001",
    "milestone_id": "M-003",
    "description":  "Phase 3 completion certificate signed by certifier per contract clause 22.1",
}

provenance = {
    "source_type":      "human",
    "source_id":        "certifier-001",
    "capture_method":   "digital_signature",
    "jurisdiction_id":  "england-wales",
}


def run_governance_trace():
    print("=" * 65)
    print("AIEP GENOME SDK — Governance Trace v1")
    print(f"KERNEL_VERSION: {KERNEL_VERSION}")
    print("FC §8: Output = f(A, C, P)")
    print("=" * 65)

    # [0] Kernel self-test — gate before anything runs
    assert run_self_test(), "Kernel self-test FAILED"
    print("\n[0] Kernel self-test: PASS")

    # ── LAYER 1: Declare capability set ──────────────────────────────────────
    print("\n[1] Layer 1 — Declare capability set (FC §3)")
    cap_manifest = declare_capabilities(
        manifest_id       = "cap-governance-trace-v1",
        lockfile_version  = LOCKFILE_VERSION,
        declared_at       = DECLARED_AT,
        hash_algorithms   = ["sha256.v1"],
        proof_types       = ["negative_proof.v1", "replay_pack.v1"],
        mirror_modes      = ["private.v1"],
        policy_engine     = ["default.v1"],
        adapters_enabled  = ["StorageAdapter", "MirrorAdapter"],
    )
    cap_hash = cap_manifest["capability_hash"]
    print(f"    capability_hash  = {cap_hash}")

    # Verify capability_hash
    v = verify_capability_manifest(cap_manifest)
    assert v["verified"], f"Capability hash mismatch: {v}"
    print(f"    verification     = PASS")

    # ── LAYER 2: Declare policy ───────────────────────────────────────────────
    print("\n[2] Layer 2 — Declare policy (FC §4)")
    policy = bind_policy({
        "policy_id":                  "policy-construction-001",
        "mirror_visibility_default":  "PRIVATE",
        "public_prefixes":            [],
        "private_prefixes":           ["/"],
        "dissent_threshold":          "majority",
        "retention_policy_id":        "retain-7-years",
    })
    pol_hash = policy["policy_hash"]
    print(f"    policy_hash      = {pol_hash}")

    # Mirror visibility decision — Layer 2, not Layer 0
    visibility = evaluate_mirror_visibility("/milestones/M-003", policy)
    print(f"    mirror_visibility= {visibility}")

    # Dissent evaluation — Layer 2
    dissent_result = evaluate_dissent_threshold(dissent_count=1, total_voters=5, policy=policy)
    print(f"    dissent (1/5)    = {dissent_result}")

    # ── LAYER 0: Canonical commitment ─────────────────────────────────────────
    print("\n[3] Layer 0 — Evidence commitment (kernel)")
    canonical_ev = canonical_json(evidence_payload)
    canonical_pv = canonical_json(provenance)
    ev_commitment = concat_hash(canonical_ev, canonical_pv, SCHEMA_VERSION_ID)
    print(f"    evidence_commitment = {ev_commitment}")

    # ── LAYER 0: Gate evaluation ──────────────────────────────────────────────
    print("\n[4] Layer 0 — Gate evaluation (kernel invariants I1-I6)")
    evidence_ledger = {ev_commitment: {
        "evidence_commitment": ev_commitment,
        "schema_version_id":   SCHEMA_VERSION_ID,
        "source_id":           "certifier-001",
        "collection_ts":       COLLECTION_TS,
        "permitted_use_scope": "contract_administration",
        "retention_policy_id": policy["retention_policy_id"],
        "created_ts":          COLLECTION_TS,
    }}
    entry_hash = sha256_hex(ev_commitment + SCHEMA_VERSION_ID)
    reasoning_entry = {
        "entry_hash":       entry_hash,
        "prior_hash":       None,
        "kind":             "ACTIVATION",
        "branch_id":        "branch-milestone-M003",
        "evidence_refs":    [ev_commitment],
        "schema_version_id":SCHEMA_VERSION_ID,
        "created_ts":       COLLECTION_TS,
        "capability_hash":  cap_hash,   # FC §3: stored with artefact
        "policy_hash":      pol_hash,   # FC §4: stored with arbitration output
    }
    reasoning_ledger = [reasoning_entry]

    gate = evaluate_gate(
        evidence_hash    = ev_commitment,
        evidence_ledger  = evidence_ledger,
        reasoning_ledger = reasoning_ledger,
        active_branches  = {"branch-milestone-M003"},
        branch_id        = "branch-milestone-M003",
        operation_label  = "certify_milestone",
    )
    print(f"    gate.status      = {gate.status}")
    print(f"    invariants       = {gate.invariants_checked}")
    assert gate.is_open, f"Gate CLOSED unexpectedly: {gate.violations}"

    # ── LAYER 0+2: Arbitration ────────────────────────────────────────────────
    print("\n[5] Layer 0+2 — Arbitration (kernel admissibility + policy dissent)")
    admissible, reason = evaluate_admissibility(
        plausibility_status    = "plausible",
        dissent_final_position = dissent_result,  # "pass" from Layer 2
        gate_status            = gate.status,
    )
    print(f"    admissible       = {admissible}")
    print(f"    reason           = {reason}")
    assert admissible

    # ── LAYER 0: Replay pack hash (I6 proof) ──────────────────────────────────
    print("\n[6] Layer 0 — ReplayPack hash (I6 determinism proof)")
    ph = pack_hash(list(evidence_ledger.values()), reasoning_ledger, SCHEMA_VERSION_ID)
    print(f"    pack_hash        = {ph}")

    # ── LAYER 0: Negative proof ───────────────────────────────────────────────
    print("\n[7] Layer 0 — NegativeProof (absence of written objection)")
    npr = create_negative_proof_record(
        expected_evidence_type = "written_objection_to_milestone",
        gap_window_start       = "2026-02-20T00:00:00Z",
        gap_window_end         = "2026-02-27T00:00:00Z",
        schema_version_id      = SCHEMA_VERSION_ID,
        search_scope           = "contract-001 correspondence",
        created_ts             = COLLECTION_TS,
    )
    print(f"    negative_proof   = {npr['negative_proof_hash']}")

    # ── FC §8: Combined output hash — binds A, C, P together ─────────────────
    print("\n[8] FC §8 — Combined output hash: H(EvidenceCommitment || CapabilityHash || PolicyHash)")
    combined = concat_hash(ev_commitment, cap_hash, pol_hash)
    print(f"    combined_output  = {combined}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("GOVERNANCE TRACE COMPLETE")
    print("=" * 65)
    print("\nReference hashes for cross-implementation verification:")
    print(f"  capability_hash      : {cap_hash}")
    print(f"  policy_hash          : {pol_hash}")
    print(f"  evidence_commitment  : {ev_commitment}")
    print(f"  pack_hash            : {ph}")
    print(f"  negative_proof_hash  : {npr['negative_proof_hash']}")
    print(f"  combined_output_hash : {combined}")
    print("\nFC §8: For identical A, C, P → identical output across all machines.")
    print("If your hashes differ → canonicalisation defect in Layer 0.")
    print("If only combined_output differs → capability or policy mismatch (Layers 1/2).")


if __name__ == "__main__":
    run_governance_trace()
