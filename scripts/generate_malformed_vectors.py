#!/usr/bin/env python3
"""Generate AIEP-VECTORS malformed-input suite (FIX-027)."""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT.parent / "AIEP-VECTORS" / "v1.0.0-malformed"
OUT.mkdir(parents=True, exist_ok=True)

KV  = "1.0.0"
CSV = "1.0.0"
VPV = "1.0.0-malformed"
SV  = "aiep.canonical.v2.0.0"

def meta(vid: str, desc: str) -> dict:
    return {
        "vector_id":          vid,
        "suite":              "malformed-input",
        "profile":            "malformed",
        "description":        desc,
        "kernel_version":     KV,
        "canon_spec_version": CSV,
    }

vectors = [
    ("mal-001.json", {
        **meta("mal-001",
               "R5: minus-zero (-0.0) is forbidden in canonical records. "
               "canonical_json({'x': float('-0.0')}) MUST raise CanonError."),
        "input": {
            "case": "minus-zero",
            "python_expression": "canonical_json({'x': float('-0.0')})",
            "note": "float(-0.0) cannot be expressed as JSON literal — "
                    "construct programmatically in test code",
        },
        "expected": {
            "must_raise":     "CanonError",
            "error_contains": "minus-zero",
        },
    }),

    ("mal-002.json", {
        **meta("mal-002",
               "R5: NaN is forbidden in canonical records. "
               "canonical_json({'x': float('nan')}) MUST raise CanonError."),
        "input": {
            "case": "NaN",
            "python_expression": "canonical_json({'x': float('nan')})",
            "note": "NaN cannot be expressed as a JSON literal",
        },
        "expected": {
            "must_raise":     "CanonError",
            "error_contains": "non-finite",
        },
    }),

    ("mal-003.json", {
        **meta("mal-003",
               "R5: Infinity is forbidden in canonical records. "
               "canonical_json({'x': float('inf')}) MUST raise CanonError."),
        "input": {
            "case": "Infinity",
            "python_expression": "canonical_json({'x': float('inf')})",
            "note": "Infinity cannot be expressed as a JSON literal",
        },
        "expected": {
            "must_raise":     "CanonError",
            "error_contains": "non-finite",
        },
    }),

    ("mal-004.json", {
        **meta("mal-004",
               "R5: -Infinity is forbidden in canonical records. "
               "canonical_json({'x': float('-inf')}) MUST raise CanonError."),
        "input": {
            "case": "neg-Infinity",
            "python_expression": "canonical_json({'x': float('-inf')})",
            "note": "-Infinity cannot be expressed as a JSON literal",
        },
        "expected": {
            "must_raise":     "CanonError",
            "error_contains": "non-finite",
        },
    }),

    ("mal-005.json", {
        **meta("mal-005",
               "R1: non-string object key is forbidden. "
               "canonical_json({1: 'value'}) MUST raise CanonError. "
               "All JSON object keys must be strings per RFC 8259."),
        "input": {
            "case": "non-string-key",
            "python_expression": "canonical_json({1: 'value'})",
            "note": "Integer keys cannot be expressed as JSON object keys",
        },
        "expected": {
            "must_raise":     "CanonError",
            "error_contains": "object member name must be a string",
        },
    }),

    ("mal-006.json", {
        **meta("mal-006",
               "Tampered pack_hash: a record whose stored pack_hash does not match "
               "recomputation MUST produce a MISMATCH verdict. "
               "Fail-closed: tampered records are never silently accepted."),
        "input": {
            "case": "tampered-pack-hash",
            "evidence_ledger": [
                {
                    "evidence_id":   "00000000-0000-0000-0000-000000000001",
                    "evidence_type": "structured_data",
                    "content":       "temperature_celsius=72.4",
                    "collected_ts":  "2026-01-01T00:00:00Z",
                }
            ],
            "reasoning_ledger":  [],
            "schema_version_id": SV,
            "tampered_pack_hash": "a" * 64,
        },
        "expected": {
            "admissible":     False,
            "verdict":        "record invalid",
            "check_fails":    "PACK_HASH",
            "reason_contains": "MISMATCH",
        },
    }),
]

for fname, vec in vectors:
    p = OUT / fname
    p.write_text(json.dumps(vec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {fname}")

manifest = {
    "vector_pack_version": VPV,
    "kernel_version":      KV,
    "canon_spec_version":  CSV,
    "schema_version_id":   SV,
    "purpose": (
        "Malformed-input rejection suite. "
        "Vectors mal-001 through mal-005 verify that a conformant verifier MUST "
        "raise CanonError for invalid numeric values (minus-zero, NaN, Infinity, "
        "-Infinity) and non-string object keys. "
        "mal-006 verifies that a tampered pack_hash is detected and rejected. "
        "A verifier that silently accepts any of these inputs is NOT conformant."
    ),
    "vectors": [
        {
            "vector_id": f"mal-{str(i+1).zfill(3)}",
            "suite":     "malformed-input",
            "profile":   "malformed",
            "file":      f"mal-{str(i+1).zfill(3)}.json",
        }
        for i in range(6)
    ],
}
(OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print("  wrote MANIFEST.json")
print(f"\nDone. {len(vectors)} malformed vectors in {OUT}")
