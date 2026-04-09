#!/usr/bin/env python3
"""
AIEP GENOME — Canonical Test Vector Generator

Generates pack_hash, negative_proof_hash, and concat_hash values by running
the locked kernel directly. Use this to create new vectors or verify existing ones.

Usage:
    python scripts/generate_vectors.py

Output is printed to stdout as a JSON report you can paste into vector files.

IMPORTANT: This script must be run from the genome-sdk root with the venv active
so it can import from src/. The output is only valid for KERNEL_VERSION=1.0.0.
"""
from __future__ import annotations

import json
import sys
import pathlib

# Make sure we can import the kernel directly
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from aiep_genome.kernel.canon.canon import (
        canonical_json,
        sha256_hex,
        concat_hash,
        pack_hash,
        negative_proof_hash,
    )
except ImportError as e:
    print(f"ERROR: Cannot import kernel: {e}", file=sys.stderr)
    print("Run from genome-sdk root with: pip install -e .[dev]", file=sys.stderr)
    sys.exit(1)

KERNEL_VERSION     = "1.0.0"
LOCKFILE_VERSION   = "1.0.0"
CANON_SPEC_VERSION = "1.0.0"
SCHEMA_VERSION_ID  = "aiep.canonical.v2.0.0"


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _kv(label: str, value: str) -> None:
    print(f"  {label:<40} {value}")


def main() -> None:
    print(f"AIEP Canonical Vector Generator")
    print(f"  kernel_version     = {KERNEL_VERSION}")
    print(f"  lockfile_version   = {LOCKFILE_VERSION}")
    print(f"  canon_spec_version = {CANON_SPEC_VERSION}")

    # -----------------------------------------------------------------------
    # R1 + R2: canonical_json
    # -----------------------------------------------------------------------
    _section("R1 / R2 — canonical_json (key ordering, no whitespace)")
    _kv("canonical_json({'z':1,'a':2})", canonical_json({"z": 1, "a": 2}))
    _kv("canonical_json({'a':2,'z':1})", canonical_json({"a": 2, "z": 1}))
    assert canonical_json({"z": 1, "a": 2}) == canonical_json({"a": 2, "z": 1})
    print("  ✓ R1/R2 identical (key order normalised)")

    # -----------------------------------------------------------------------
    # R3 + R4: sha256_hex with NFC normalisation
    # -----------------------------------------------------------------------
    _section("R3 / R4 — sha256_hex (NFC + SHA-256)")
    _kv('sha256_hex("")', sha256_hex(""))
    _kv('sha256_hex("AIEP")', sha256_hex("AIEP"))
    _kv('sha256_hex("café" NFC)', sha256_hex("caf\u00e9"))
    _kv('sha256_hex("café" NFD)', sha256_hex("cafe\u0301"))
    assert sha256_hex("caf\u00e9") == sha256_hex("cafe\u0301"), "R3 NFC mismatch!"
    print("  ✓ R3 NFC normalisation: NFC == NFD")

    # -----------------------------------------------------------------------
    # R7: concat_hash boundary safety
    # -----------------------------------------------------------------------
    _section("R7 — concat_hash (length-prefixed, boundary safe)")
    _kv('concat_hash("AB", "CD")', concat_hash("AB", "CD"))
    _kv('concat_hash("A", "BCD")', concat_hash("A", "BCD"))
    assert concat_hash("AB", "CD") != concat_hash("A", "BCD"), "R7 boundary collision!"
    print("  ✓ R7 no boundary collision")

    # -----------------------------------------------------------------------
    # R8: pack_hash — DET vectors
    # -----------------------------------------------------------------------
    _section("R8 — pack_hash (DET-001, DET-002, DET-003)")

    # DET-001
    el_001 = [{"collected_ts": "2026-01-01T00:00:00Z",
               "content": "temperature_reading_celsius=72.4",
               "evidence_id": "00000000-0000-0000-0000-000000000001",
               "evidence_type": "structured_data"}]
    rl_001 = [{"conclusion": "Temperature within safe operating range. No action required.",
               "reasoning_id": "00000000-0000-0000-0000-000000000101"}]
    _kv("DET-001 pack_hash", pack_hash(el_001, rl_001, SCHEMA_VERSION_ID))

    # DET-002 (NFC)
    el_002 = [{"collected_ts": "2026-01-01T00:00:00Z",
               "content": "caf\u00e9",
               "evidence_id": "00000000-0000-0000-0000-000000000002",
               "evidence_type": "structured_data"}]
    rl_002 = [{"conclusion": "caf\u00e9 recognised.",
               "reasoning_id": "00000000-0000-0000-0000-000000000102"}]
    _kv("DET-002 pack_hash", pack_hash(el_002, rl_002, SCHEMA_VERSION_ID))

    # DET-003 (empty)
    _kv("DET-003 pack_hash", pack_hash([], [], SCHEMA_VERSION_ID))

    # -----------------------------------------------------------------------
    # TAMP vectors — tampered pack_hash
    # -----------------------------------------------------------------------
    _section("Tamper detection — tampered_pack_hash")

    el_tamp1 = [{"collected_ts": "2026-01-01T00:00:00Z",
                 "content": "temperature_reading_celsius=99.9",
                 "evidence_id": "00000000-0000-0000-0000-000000000001",
                 "evidence_type": "structured_data"}]
    rl_tamp = [{"conclusion": "Temperature within safe operating range. No action required.",
                "reasoning_id": "00000000-0000-0000-0000-000000000101"}]
    _kv("TAMP-001 tampered_pack_hash", pack_hash(el_tamp1, rl_tamp, SCHEMA_VERSION_ID))

    el_tamp2 = [{"collected_ts": "2026-01-01T00:00:00Z",
                 "content": "temperature_reading_celsius=72.4",
                 "evidence_id": "00000000-0000-0000-0000-000000000001",
                 "evidence_type": "structured_data"}]
    rl_tamp2 = [{"conclusion": "Temperature critically elevated. Emergency shutdown initiated.",
                 "reasoning_id": "00000000-0000-0000-0000-000000000101"}]
    _kv("TAMP-002 tampered_pack_hash", pack_hash(el_tamp2, rl_tamp2, SCHEMA_VERSION_ID))

    # -----------------------------------------------------------------------
    # NEG vectors
    # -----------------------------------------------------------------------
    _section("Negative proof — negative_proof_hash + pack_hash")
    nph = negative_proof_hash(
        "sensor_reading",
        "2026-01-01T00:00:00Z",
        "2026-01-01T01:00:00Z",
        SCHEMA_VERSION_ID,
    )
    _kv("NEG-001 negative_proof_hash", nph)

    el_neg2 = [{"collected_ts": "2026-01-01T01:00:00Z",
                "evidence_id": "00000000-0000-0000-0000-000000000003",
                "evidence_type": "negative_proof",
                "expected_evidence_type": "sensor_reading",
                "gap_window_start": "2026-01-01T00:00:00Z",
                "gap_window_end": "2026-01-01T01:00:00Z",
                "negative_proof_hash": nph}]
    rl_neg2 = [{"conclusion": "No sensor data in window. Absence recorded.",
                "reasoning_id": "00000000-0000-0000-0000-000000000103"}]
    _kv("NEG-002 pack_hash", pack_hash(el_neg2, rl_neg2, SCHEMA_VERSION_ID))

    print("\n" + "=" * 60)
    print("  Vector generation complete. Copy hashes into vector JSON files.")
    print(f"  Verify with: aiep-verify --vectors vectors/v1.0.0/")
    print("=" * 60)


if __name__ == "__main__":
    main()
