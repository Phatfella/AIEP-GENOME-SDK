#!/usr/bin/env python3
"""Regenerate SHA256SUMS.txt for the GENOME SDK."""
import hashlib
import pathlib

ROOT = pathlib.Path(__file__).parent.parent

FILES = [
    "kernel/canon/canon.py",
    "src/aiep_genome/standalone_verify.py",
    "src/aiep_genome/verify_record.py",
    "CANON_SPEC.md",
    "CLAIMS.md",
    "BOUNDARIES.md",
    "CONFORMANCE.md",
    "vectors/v1.0.0/01-deterministic-replay/case-001.json",
    "vectors/v1.0.0/01-deterministic-replay/case-002.json",
    "vectors/v1.0.0/01-deterministic-replay/case-003.json",
    "vectors/v1.0.0/02-tamper-detection/case-001.json",
    "vectors/v1.0.0/02-tamper-detection/case-002.json",
    "vectors/v1.0.0/03-negative-proof/case-001.json",
    "vectors/v1.0.0/03-negative-proof/case-002.json",
    "vectors/v1.0.0/04-admissibility/case-001.json",
    "vectors/v1.0.0/04-admissibility/case-002.json",
    "vectors/v1.0.0/04-admissibility/case-003.json",
    "vectors/v1.0.0/05-number-normalisation/case-001.json",
    "vectors/v1.0.0/05-number-normalisation/case-002.json",
    "vectors/v1.0.0/05-number-normalisation/case-003.json",
    "vectors/v1.0.0/05-number-normalisation/case-004.json",
    "vectors/v1.0.0/05-number-normalisation/case-005.json",
    "vectors/v1.0.0/05-number-normalisation/case-006.json",
    "vectors/v1.0.0/05-number-normalisation/case-007.json",
    "vectors/v1.0.0/MANIFEST.json",
    "vectors/schema/vector.schema.json",
    "scripts/generate_vectors.py",
    "pyproject.toml",
]

lines = [
    "# AIEP GENOME SDK -- SHA256 checksums",
    "# Generated from CANON_SPEC v1.0.0",
    "",
]

for fp in FILES:
    p = ROOT / fp
    if p.exists():
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {fp}")
    else:
        print(f"MISSING: {fp}")

out = ROOT / "SHA256SUMS.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
count = len([l for l in lines if l and not l.startswith("#")])
print(f"SHA256SUMS.txt written with {count} entries")
