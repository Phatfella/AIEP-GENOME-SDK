#!/usr/bin/env python3
"""
AIEP Complete Record — Worked Example Builder

Computes and prints every hash from the README, from scratch.
Run from the genome-sdk root:

    python examples/complete_record/build.py

All values should match the README exactly.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from aiep_genome.kernel.canon import (
        canonical_json,
        sha256_hex,
        pack_hash,
        evidence_commitment,
        negative_proof_hash,
        dissent_hash,
        context_reconstruction_hash,
        consensus_record_hash,
    )
except ImportError as exc:
    print(f"ERROR: Cannot import kernel: {exc}", file=sys.stderr)
    print("Install with: pip install -e .[dev]  (from genome-sdk root)", file=sys.stderr)
    sys.exit(1)

SV = "aiep.canonical.v2.0.0"

# ── Fixtures ─────────────────────────────────────────────────────────────────

EVIDENCE = [
    {
        "evidence_id":   "00000000-0000-0000-0000-000000000001",
        "evidence_type": "structured_data",
        "content":       "temperature_celsius=72.4",
        "collected_ts":  "2026-01-01T00:00:00Z",
    }
]

ENTRY_HASH = sha256_hex("entry-example-001")

REASONING = [
    {
        "entry_hash":    ENTRY_HASH,
        "kind":          "ACTIVATION",
        "reasoning":     "Temperature within safe operating range. No alert required.",
        "branch_id":     "branch-001",
        "evidence_refs": ["00000000-0000-0000-0000-000000000001"],
    }
]

# ── Compute ───────────────────────────────────────────────────────────────────

ph   = pack_hash(EVIDENCE, REASONING, SV)
ec   = evidence_commitment(canonical_json(EVIDENCE), "lab/sensor/v1", SV)
nph  = negative_proof_hash(
    "telemetry_reading",
    "2026-01-01T01:00:00Z",
    "2026-01-01T02:00:00Z",
    SV,
)
dh_reject  = dissent_hash("branch-002", ph, "reject",  EVIDENCE, SV)
dh_archive = dissent_hash("branch-002", ph, "archive", EVIDENCE, SV)
crh  = context_reconstruction_hash([ph, nph], "sorted-asc", SV)
crec = consensus_record_hash("branch-001", "HIGH", [ph, nph], SV)

# ── Expected values (from README) ────────────────────────────────────────────

EXPECTED = {
    "entry_hash":             "727ccdd0e91a3783e4a32f920d57619100be76ada97c38a6f879ca85673f4c65",
    "pack_hash":              "a03f690109af14d6d70b6eac7e600e2a030ebac3558481e9ecd345b566827075",
    "evidence_commitment":    "3a64b676a3fcf24b0c07e0e76147bc7303eba5ceac96b238b6ac048bb0183e7a",
    "negative_proof_hash":    "9c403f333a7dc45636074827ec52211ebb560f0c4ef7cefb1da68c30ea087bd1",
    "dissent_hash_reject":    "841843ebd96db55a08d2677a012777732e3452e9b0178057c65207e587e7962b",
    "dissent_hash_archive":   "4df2260cd54e9f2cc30deb78c880bc2265497a825047e8e302bf36f79a7bf67e",
    "context_reconstruction": "a848defef1e9dea0f8a4f082e8bc80640147be1db1eda143641cfe683f05d549",
    "consensus_record":       "684bc397afb13583b7292db5a132cf26c8a40f9a7c8910b0fac6443d1799fbc4",
}

COMPUTED = {
    "entry_hash":             ENTRY_HASH,
    "pack_hash":              ph,
    "evidence_commitment":    ec,
    "negative_proof_hash":    nph,
    "dissent_hash_reject":    dh_reject,
    "dissent_hash_archive":   dh_archive,
    "context_reconstruction": crh,
    "consensus_record":       crec,
}

# ── Report ────────────────────────────────────────────────────────────────────

failures = []
print()
print("AIEP Complete Record -- Worked Example")
print(f"  schema_version_id: {SV}")
print()

for name, computed in COMPUTED.items():
    expected = EXPECTED[name]
    status   = "PASS" if computed == expected else "FAIL"
    label    = f"{name:<26}"
    if status == "PASS":
        print(f"  {status}  {label}  {computed[:20]}...{computed[-8:]}")
    else:
        failures.append(name)
        print(f"  {status}  {label}")
        print(f"         computed:  {computed}")
        print(f"         expected:  {expected}")

print()
if failures:
    print(f"  {len(failures)} FAILURES -- canon divergence detected")
    sys.exit(1)
else:
    print(f"  All {len(COMPUTED)} hashes match -- canon is deterministic")
    print()
