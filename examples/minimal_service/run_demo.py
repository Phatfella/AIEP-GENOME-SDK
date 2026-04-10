"""
Demo: run the minimal AIEP service with two example records.

Record 1: URL evidence (fetched from the AIEP Hub /.well-known endpoint)
Record 2: Text evidence (a construction cost estimate)
"""
import json
import subprocess
import sys

# Allow running from the genome-sdk root: python examples/minimal_service/run_demo.py
sys.path.insert(0, "src")

from examples.minimal_service.service import (
    collect_text_evidence,
    make_decision,
    decision_record,
    AiepConstraintError,
)


def demo_record_1():
    """Record 1: Construction cost estimate evidence."""
    print("\n--- Record 1: Construction cost estimate ---")

    evidence = collect_text_evidence(
        text=(
            "Project Alpha — Structural works cost plan Rev 3. "
            "Total: £2,450,000. Labour: 47h × £85/h = £3,995. "
            "Materials: £1,200,000. Plant: £85,000. Prelims: £161,005. "
            "Basis: measured quantities from drawings Rev 3.2, April 2026."
        ),
        label="cost-plan-rev3",
        evidence_id="e1",
    )

    print(f"  evidence_id  : {evidence.evidence_id}")
    print(f"  content_len  : {len(evidence.content)} chars")
    print(f"  collected_ts : {evidence.collected_ts}")

    ev_ledger, r_ledger, plausibility, gate = make_decision([evidence], query="cost-commitment")

    print(f"\n  plausibility : {plausibility}")
    print(f"  gate_status  : {gate}")

    record = decision_record(ev_ledger, r_ledger, plausibility, gate)

    print(f"\n  pack_hash    : {record.pack_hash_val[:20]}...")
    print(f"  verdict      : {record.verdict}")

    return record


def demo_record_2():
    """Record 2: Empty evidence → NegativeProofRecord."""
    print("\n--- Record 2: No evidence available (NegativeProofRecord) ---")

    ev_ledger, r_ledger, plausibility, gate = make_decision([], query="project-alpha-programme")

    print(f"  plausibility : {plausibility}")
    print(f"  gate_status  : {gate}")
    print(f"  reasoning    : {r_ledger[0]['reasoning'][:80]}...")

    try:
        record = decision_record(ev_ledger, r_ledger, plausibility, gate)
    except AiepConstraintError as e:
        print(f"\n  AiepConstraintError (expected — CC-001 or CC-005 violated):")
        print(f"  {e}")
        return None

    print(f"\n  pack_hash    : {record.pack_hash_val[:20]}...")
    print(f"  verdict      : {record.verdict}")
    if record.negative_proof_hash_val:
        print(f"  neg_proof_h  : {record.negative_proof_hash_val[:20]}...")

    return record


def verify_record(record, path: str):
    """Write record to disk and run aiep-verify against it."""
    with open(path, "w") as f:
        json.dump(record.to_dict(), f, indent=2)

    print(f"\n  Written to {path}")
    print(f"  Running: aiep-verify {path}")

    result = subprocess.run(
        [sys.executable, "-m", "aiep_genome.standalone_verify", path],
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    print(f"  → {output}")
    return result.returncode == 0


def main():
    print("=" * 60)
    print("AIEP Minimal Service Demo")
    print("=" * 60)

    record1 = demo_record_1()
    if record1:
        verify_record(record1, "demo-record.json")

    demo_record_2()

    print("\n" + "=" * 60)
    print("Share demo-record.json — any third party can verify it:")
    print("  aiep-verify demo-record.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
