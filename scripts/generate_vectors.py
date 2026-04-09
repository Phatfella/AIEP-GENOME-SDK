#!/usr/bin/env python3
"""
AIEP GENOME â€” AIEP-VECTORS Generator (Phase B2)

Writes all canonical test vectors directly to the AIEP-VECTORS repository.
Files are written atomically; nothing is printed-and-pasted.

Usage (from genome-sdk root, venv active):
    python scripts/generate_vectors.py [--output DIR]

Default output: ../AIEP-VECTORS/v1.0.0/

Generates:
    9 core vectors + 1 extended vector (dissent-preservation)
    MANIFEST.json, SHA256SUMS.txt, CANON_SPEC.md copy (with provenance header)

Cross-check:
    aiep-verify --vectors <OUTPUT>/v1.0.0/     # must report AIEP-COMPLIANT v1.0.0
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

# Make sure we can import the kernel directly
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from aiep_genome.kernel.canon import (
        canonical_json,
        sha256_hex,
        concat_hash,
        pack_hash,
        negative_proof_hash,
    )
except ImportError as exc:
    print(f"ERROR: Cannot import kernel: {exc}", file=sys.stderr)
    print("Run from genome-sdk root with: pip install -e .[dev]", file=sys.stderr)
    sys.exit(1)

KERNEL_VERSION      = "1.0.0"
LOCKFILE_VERSION    = "1.0.0"
CANON_SPEC_VERSION  = "1.0.0"
VECTOR_PACK_VERSION = "1.0.0"
SCHEMA_VERSION_ID   = "aiep.canonical.v2.0.0"
CANON_BLOBSHA       = "3b100b43bf59ce6f6d35397e8c8c173a4447de5d"

# â”€â”€ Shared test data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These are the canonical reference fixtures for AIEP-VECTORS v1.0.0.
# Do NOT change them after release â€” changes require a new vector pack version.

def _entry_hash(label: str) -> str:
    return sha256_hex(label)

EV_1 = [
    {
        "evidence_id":   "00000000-0000-0000-0000-000000000001",
        "evidence_type": "structured_data",
        "content":       "temperature_celsius=72.4",
        "collected_ts":  "2026-01-01T00:00:00Z",
    }
]

RL_1 = [
    {
        "entry_hash":    _entry_hash("entry-det-001"),
        "kind":          "ACTIVATION",
        "reasoning":     "Temperature within safe operating range.",
        "branch_id":     "branch-001",
        "evidence_refs": ["00000000-0000-0000-0000-000000000001"],
    }
]

# NFC test fixtures: Ã… as precomposed U+00C5 vs decomposed A+U+030A
EV_NFC_PRE = [
    {
        "evidence_id":   "00000000-0000-0000-0000-000000000002",
        "evidence_type": "structured_data",
        "content":       "sensor_location=\u00c5rhus_North",   # Ã… precomposed
        "collected_ts":  "2026-01-01T00:00:00Z",
    }
]
EV_NFC_DEC = [
    {
        "evidence_id":   "00000000-0000-0000-0000-000000000002",
        "evidence_type": "structured_data",
        "content":       "sensor_location=A\u030arhus_North",  # A + combining ring above
        "collected_ts":  "2026-01-01T00:00:00Z",
    }
]
RL_NFC = [
    {
        "entry_hash":    _entry_hash("entry-det-002"),
        "kind":          "ACTIVATION",
        "reasoning":     "Location normalised.",
        "branch_id":     "branch-001",
        "evidence_refs": ["00000000-0000-0000-0000-000000000002"],
    }
]

# Tamper fixtures: mutated content / reasoning
EV_TAMP = [
    {
        "evidence_id":   "00000000-0000-0000-0000-000000000001",
        "evidence_type": "structured_data",
        "content":       "temperature_celsius=99.9",   # tampered value
        "collected_ts":  "2026-01-01T00:00:00Z",
    }
]
RL_TAMP = [
    {
        "entry_hash":    _entry_hash("entry-det-001"),  # same entry_hash as RL_1
        "kind":          "ACTIVATION",
        "reasoning":     "Temperature elevated. Alert issued.",  # tampered
        "branch_id":     "branch-001",
        "evidence_refs": ["00000000-0000-0000-0000-000000000001"],
    }
]

# Negative-proof fixtures
NEG_TYPE  = "telemetry_reading"
NEG_START = "2026-01-01T00:00:00Z"
NEG_END   = "2026-01-01T01:00:00Z"

# Dissent-preservation fixtures
RL_HIGH = [
    {
        "entry_hash":    _entry_hash("entry-dis-HIGH"),
        "kind":          "ACTIVATION",
        "reasoning":     "HIGH branch: temperature is critical.",
        "branch_id":     "branch-HIGH",
        "evidence_refs": ["00000000-0000-0000-0000-000000000001"],
    }
]
RL_LOW = [
    {
        "entry_hash":    _entry_hash("entry-dis-LOW"),
        "kind":          "DISSENT",
        "reasoning":     "LOW branch: temperature is within tolerance.",
        "branch_id":     "branch-LOW",
        "evidence_refs": ["00000000-0000-0000-0000-000000000001"],
    }
]


# â”€â”€ Vector definitions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _meta(vid: str, suite: str, description: str, profile: str = "core") -> dict:
    return {
        "vector_id":          vid,
        "suite":              suite,
        "profile":            profile,
        "description":        description,
        "kernel_version":     KERNEL_VERSION,
        "canon_spec_version": CANON_SPEC_VERSION,
    }


def build_vectors() -> list:
    """Returns list of (filename, vector_dict) in generation order."""
    sv = SCHEMA_VERSION_ID
    ph_det001  = pack_hash(EV_1, RL_1, sv)
    ph_nfc     = pack_hash(EV_NFC_PRE, RL_NFC, sv)
    ph_det003  = pack_hash(EV_1, [], sv)
    ph_tamp_ev = pack_hash(EV_TAMP, RL_1, sv)
    ph_tamp_rl = pack_hash(EV_1, RL_TAMP, sv)
    nph        = negative_proof_hash(NEG_TYPE, NEG_START, NEG_END, sv)
    ph_high    = pack_hash(EV_1, RL_HIGH, sv)
    ph_low     = pack_hash(EV_1, RL_LOW, sv)

    return [
        ("det-001.json", {
            **_meta("det-001", "deterministic-replay",
                    "Deterministic replay: identical inputs produce identical pack_hash"),
            "input": {
                "evidence_ledger":   EV_1,
                "reasoning_ledger":  RL_1,
                "schema_version_id": sv,
            },
            "expected": {"pack_hash": ph_det001},
        }),

        ("det-002.json", {
            **_meta("det-002", "deterministic-replay",
                    "R3/NFC: precomposed \u00c5 (U+00C5) and decomposed A+ring (A+U+030A) "
                    "produce identical pack_hash after NFC normalisation"),
            "input": {
                "evidence_ledger_precomposed": EV_NFC_PRE,
                "evidence_ledger_decomposed":  EV_NFC_DEC,
                "reasoning_ledger":            RL_NFC,
                "schema_version_id":           sv,
            },
            "expected": {
                "pack_hash":       ph_nfc,
                "both_must_equal": True,
            },
        }),

        ("det-003.json", {
            **_meta("det-003", "deterministic-replay",
                    "Uniqueness: empty reasoning_ledger produces different pack_hash from det-001"),
            "input": {
                "evidence_ledger":   EV_1,
                "reasoning_ledger":  [],
                "schema_version_id": sv,
            },
            "expected": {
                "pack_hash": ph_det003,
                "must_differ_from": {
                    "vector":    "det-001",
                    "pack_hash": ph_det001,
                },
            },
        }),

        ("tamp-001.json", {
            **_meta("tamp-001", "tamper-detection",
                    "Evidence tamper: mutating evidence content changes pack_hash"),
            "input": {
                "evidence_ledger_original": EV_1,
                "evidence_ledger_tampered": EV_TAMP,
                "reasoning_ledger":         RL_1,
                "schema_version_id":        sv,
            },
            "expected": {
                "original_pack_hash": ph_det001,
                "tampered_pack_hash": ph_tamp_ev,
            },
        }),

        ("tamp-002.json", {
            **_meta("tamp-002", "tamper-detection",
                    "Reasoning tamper: mutating reasoning content changes pack_hash"),
            "input": {
                "evidence_ledger":           EV_1,
                "reasoning_ledger_original": RL_1,
                "reasoning_ledger_tampered": RL_TAMP,
                "schema_version_id":         sv,
            },
            "expected": {
                "original_pack_hash": ph_det001,
                "tampered_pack_hash": ph_tamp_rl,
            },
        }),

        ("neg-001.json", {
            **_meta("neg-001", "negative-proof",
                    "Negative proof: direct negative_proof_hash computation (P16)"),
            "input": {
                "expected_evidence_type": NEG_TYPE,
                "gap_window_start":       NEG_START,
                "gap_window_end":         NEG_END,
                "schema_version_id":      sv,
            },
            "expected": {"negative_proof_hash": nph},
        }),

        ("neg-002.json", {
            **_meta("neg-002", "negative-proof",
                    "Replay: identical negative-proof inputs reproduce identical hash (determinism)"),
            "input": {
                "expected_evidence_type": NEG_TYPE,
                "gap_window_start":       NEG_START,
                "gap_window_end":         NEG_END,
                "schema_version_id":      sv,
            },
            "expected": {
                "negative_proof_hash": nph,
                "assertion":           "must_equal_neg_001",
            },
        }),

        ("adm-001.json", {
            **_meta("adm-001", "admissibility",
                    "CC-005: closed gate is fail-closed \u2014 not admissible"),
            "input": {
                "plausibility_status":    "plausible",
                "dissent_final_position": None,
                "gate_status":            "CLOSED",
            },
            "expected": {
                "admissible":      False,
                "reason_contains": "CC-005",
            },
        }),

        ("adm-002.json", {
            **_meta("adm-002", "admissibility",
                    "Open gate, plausible, accepted dissent \u2014 admissible"),
            "input": {
                "plausibility_status":    "plausible",
                "dissent_final_position": "accept",
                "gate_status":            "OPEN",
            },
            "expected": {
                "admissible":      True,
                "reason_contains": "ADMISSIBLE",
            },
        }),

        # Extended profile \u2014 informative, not required for AIEP-COMPLIANT verdict
        ("dis-001.json", {
            **_meta("dis-001", "dissent-preservation",
                    "Dissent preservation: HIGH and LOW branches produce distinct pack_hashes",
                    profile="extended"),
            "input": {
                "evidence_ledger":              EV_1,
                "reasoning_ledger_branch_HIGH": RL_HIGH,
                "reasoning_ledger_branch_LOW":  RL_LOW,
                "schema_version_id":            sv,
            },
            "expected": {
                "pack_hash_branch_HIGH": ph_high,
                "pack_hash_branch_LOW":  ph_low,
            },
        }),
    ]


# â”€â”€ File writing helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _sha256_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: pathlib.Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _canon_spec_provenance_header() -> str:
    return (
        f"<!-- PROVENANCE: copied from AIEP-GENOME-SDK:CANON_SPEC.md "
        f"BlobSha={CANON_BLOBSHA} "
        f"vector_pack={VECTOR_PACK_VERSION} -->\n\n"
    )


def _write_manifest(out_dir: pathlib.Path, vectors: list) -> None:
    core = [v for _, v in vectors if v.get("profile") == "core"]
    manifest = {
        "vector_pack_version": VECTOR_PACK_VERSION,
        "kernel_version":      KERNEL_VERSION,
        "canon_spec_version":  CANON_SPEC_VERSION,
        "canon_blobsha":       CANON_BLOBSHA,
        "schema_version_id":   SCHEMA_VERSION_ID,
        "core_vector_count":   len(core),
        "total_vector_count":  len(vectors),
        "vectors": [
            {
                "vector_id": v["vector_id"],
                "suite":     v["suite"],
                "profile":   v.get("profile", "core"),
                "file":      fname,
            }
            for fname, v in vectors
        ],
    }
    _write_json(out_dir / "MANIFEST.json", manifest)


def _write_sha256sums(out_dir: pathlib.Path) -> None:
    lines = []
    for f in sorted(out_dir.glob("*.json")):
        digest = _sha256_file(f)
        lines.append(f"{digest}  {f.name}")
    cs = out_dir / "CANON_SPEC.md"
    if cs.exists():
        lines.append(f"{_sha256_file(cs)}  CANON_SPEC.md")
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AIEP-VECTORS v1.0.0 directly into the AIEP-VECTORS repository."
    )
    parser.add_argument(
        "--output", metavar="DIR", default=None,
        help="Output directory (default: ../AIEP-VECTORS relative to genome-sdk root)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written without writing files",
    )
    args = parser.parse_args()

    out_root = pathlib.Path(args.output) if args.output else ROOT.parent / "AIEP-VECTORS"
    out_dir  = out_root / f"v{VECTOR_PACK_VERSION}"

    print(f"AIEP-VECTORS Generator")
    print(f"  output:             {out_dir}")
    print(f"  kernel_version:     {KERNEL_VERSION}")
    print(f"  canon_spec_version: {CANON_SPEC_VERSION}")
    print(f"  vector_pack:        {VECTOR_PACK_VERSION}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would write:")

    vectors = build_vectors()

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for fname, vec in vectors:
        dest = out_dir / fname
        ph_val = str(
            vec.get("expected", {}).get("pack_hash") or
            vec.get("expected", {}).get("negative_proof_hash") or
            "\u2014"
        )
        label = f"[{vec['profile']:<8}]"
        if args.dry_run:
            print(f"  {fname:<20}  {label}  {ph_val[:24]}...")
        else:
            _write_json(dest, vec)
            print(f"  \u2713  {fname:<20}  {label}  {ph_val[:24]}...")

    # Copy CANON_SPEC.md with provenance header
    canon_src = ROOT / "CANON_SPEC.md"
    if canon_src.exists():
        dest_cs = out_dir / "CANON_SPEC.md"
        if args.dry_run:
            print(f"  {'CANON_SPEC.md':<20}  [snapshot]  provenance header prepended")
        else:
            header = _canon_spec_provenance_header()
            dest_cs.write_text(header + canon_src.read_text(encoding="utf-8"),
                               encoding="utf-8")
            print(f"  \u2713  {'CANON_SPEC.md':<20}  [snapshot]  provenance header prepended")
    else:
        print(f"  WARNING: CANON_SPEC.md not found at {canon_src}", file=sys.stderr)

    if not args.dry_run:
        _write_manifest(out_dir, vectors)
        print(f"  \u2713  {'MANIFEST.json':<20}")
        _write_sha256sums(out_dir)
        print(f"  \u2713  {'SHA256SUMS.txt':<20}")
    else:
        print(f"  {'MANIFEST.json':<20}  [generated]")
        print(f"  {'SHA256SUMS.txt':<20}  [generated]")

    core_count = sum(1 for _, v in vectors if v.get("profile") == "core")
    ext_count  = sum(1 for _, v in vectors if v.get("profile") != "core")
    print()
    print(f"  {core_count} core  +  {ext_count} extended  vectors")
    if not args.dry_run:
        print(f"  Verify: aiep-verify --vectors \"{out_dir}\"")
    print("  Done.")


if __name__ == "__main__":
    main()
