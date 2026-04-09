#!/usr/bin/env python3
"""
aiep-verify — AIEP Decision Record & Test Vector Verifier
==========================================================
Standalone. Zero dependencies beyond Python stdlib (3.9+).
Readable in under 10 minutes. Trustable without trusting AIEP.

Usage:
    aiep-verify record.json                    # verify a decision record
    aiep-verify --vectors vectors/v1.0.0/      # run conformance test suite
    aiep-verify record.json --json             # machine-readable output
    cat record.json | aiep-verify -            # stdin

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
    2 — usage error

AIEP Kernel v1.0.0 | AIEP-VECTORS v1.0.0
"""
import sys
import json
import hashlib
import unicodedata
import argparse
import os
from pathlib import Path

__version__ = "1.0.0"
KERNEL_VERSION = "1.0.0"
VECTORS_VERSION = "1.0.0"


# ── Canonical primitives (mirror of kernel/canon/canon.py) ────────────────────
# Self-contained duplicates — deliberately inlined so this file has no imports
# outside stdlib. Cross-check these against kernel/canon/canon.py.

def _nfc(s: str) -> str:
    """R3: NFC-normalise all Unicode strings before hashing."""
    return unicodedata.normalize("NFC", s)


def _nfc_object(obj):
    if isinstance(obj, str):
        return _nfc(obj)
    if isinstance(obj, dict):
        return {_nfc(k): _nfc_object(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nfc_object(i) for i in obj]
    return obj


def canonical_json(obj) -> str:
    """R1+R2+R3: sort_keys, compact separators, NFC, no ASCII escaping."""
    return json.dumps(_nfc_object(obj), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def sha256_hex(s: str) -> str:
    """R4: SHA-256 of UTF-8 encoded string → lowercase hex."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def concat_hash(*parts: str) -> str:
    """
    R7: length-prefixed-8be concatenation hash.
    H(len(p0)||p0 || len(p1)||p1 || ...) — each length is 8-byte big-endian.
    Prevents boundary collisions: concat_hash('ab','c') != concat_hash('a','bc').
    """
    buf = b""
    for part in parts:
        encoded = _nfc(part).encode("utf-8")
        buf += len(encoded).to_bytes(8, "big") + encoded
    return hashlib.sha256(buf).hexdigest()


def pack_hash(evidence_ledger: list, reasoning_ledger: list, schema_version_id: str) -> str:
    """P80-I6: Deterministic replay hash. generated_ts excluded by design."""
    state = {
        "evidence_ledger": evidence_ledger,
        "reasoning_ledger": reasoning_ledger,
        "schema_version_id": schema_version_id,
    }
    return sha256_hex(canonical_json(state))


def negative_proof_hash(expected_evidence_type: str, gap_window_start: str,
                         gap_window_end: str, schema_version_id: str) -> str:
    """P16: concat_hash(expected_type, window_start, window_end, schema_version_id)."""
    return concat_hash(expected_evidence_type, gap_window_start, gap_window_end,
                       schema_version_id)


def evaluate_admissibility(plausibility_status: str, dissent_final_position,
                            gate_status: str):
    """Constitutional arbitration — mirrors kernel/arbitration/arbitration.py."""
    if gate_status != "OPEN":
        return False, "CC-005: Gate is CLOSED \u2014 fail-closed constitutional default"
    if plausibility_status == "implausible":
        return False, "CC-001: Plausibility filter rejected \u2014 conclusion is implausible"
    if plausibility_status == "indeterminate":
        return False, "CC-001: Plausibility indeterminate \u2014 cannot advance under uncertainty"
    if dissent_final_position in ("reject", "escalate"):
        return False, "CC-004: Dissent unresolved \u2014 conclusion contested or escalated"
    return True, "ADMISSIBLE"


# ── Record verification ───────────────────────────────────────────────────────

def verify_record(record: dict) -> dict:
    """
    Verify an AIEP decision record.
    Returns {"valid": bool, "checks": [...], "errors": [...]}.
    """
    checks = []
    errors = []

    def ok(name, detail):
        checks.append({"check": name, "result": "PASS", "detail": detail})

    def fail(name, detail):
        checks.append({"check": name, "result": "FAIL", "detail": detail})
        errors.append(f"{name}: {detail}")

    # 1 — Required fields
    required = ["evidence_ledger", "reasoning_ledger", "schema_version_id", "pack_hash"]
    missing = [f for f in required if f not in record]
    if missing:
        fail("STRUCTURE", f"Missing required fields: {missing}")
        return {"valid": False, "checks": checks, "errors": errors}
    ok("STRUCTURE", "All required fields present")

    # 2 — pack_hash integrity
    try:
        recomputed = pack_hash(
            record["evidence_ledger"],
            record["reasoning_ledger"],
            record["schema_version_id"],
        )
        stored = record["pack_hash"]
        if recomputed == stored:
            ok("PACK_HASH", f"Verified: {recomputed[:16]}...")
        else:
            fail("PACK_HASH",
                 f"Mismatch\n  stored:     {stored}\n  recomputed: {recomputed}")
    except Exception as exc:
        fail("PACK_HASH", f"Recomputation error: {exc}")

    # 3 — Evidence not empty
    if not record["evidence_ledger"]:
        fail("EVIDENCE_PRESENT", "Empty evidence_ledger — no evidential basis")
    else:
        ok("EVIDENCE_PRESENT", f"{len(record['evidence_ledger'])} evidence record(s)")

    # 4 — Negative proof records (if any)
    for item in record["evidence_ledger"]:
        if item.get("evidence_type") == "negative_proof":
            needed = ["expected_evidence_type", "gap_window_start", "gap_window_end",
                      "negative_proof_hash"]
            if all(k in item for k in needed):
                expected_nph = negative_proof_hash(
                    item["expected_evidence_type"],
                    item["gap_window_start"],
                    item["gap_window_end"],
                    item.get("schema_version_id", record["schema_version_id"]),
                )
                if item["negative_proof_hash"] == expected_nph:
                    ok("NEGATIVE_PROOF", f"Verified for window {item['gap_window_start']}")
                else:
                    fail("NEGATIVE_PROOF",
                         f"Hash mismatch in NegativeProofRecord {item.get('evidence_id','?')}")
            else:
                missing_np = [k for k in needed if k not in item]
                fail("NEGATIVE_PROOF",
                     f"Incomplete NegativeProofRecord, missing: {missing_np}")

    return {"valid": len(errors) == 0, "checks": checks, "errors": errors}


# ── Test vector runner ────────────────────────────────────────────────────────

def run_vector(vector: dict) -> dict:
    """Run a single test vector. Returns {passed, vector_id, checks, errors}."""
    vid = vector.get("vector_id", "unknown")
    suite = vector.get("suite", "unknown")
    errors = []
    checks = []

    def ok(name, detail):
        checks.append({"check": name, "result": "PASS", "detail": detail})

    def fail(name, detail):
        checks.append({"check": name, "result": "FAIL", "detail": detail})
        errors.append(detail)

    if suite in ("deterministic-replay",):
        inp = vector["input"]
        expected_hash = vector["expected"]["pack_hash"]
        actual = pack_hash(inp["evidence_ledger"], inp["reasoning_ledger"],
                           inp["schema_version_id"])
        if actual == expected_hash:
            ok("PACK_HASH", f"Verified: {actual[:16]}...")
        else:
            fail("PACK_HASH",
                 f"Expected {expected_hash[:16]}... got {actual[:16]}...")

    elif suite == "tamper-detection":
        # Verify that tampered record produces a different hash from stored_pack_hash
        committed = vector["committed_record"]
        tampered = vector["tampered_record"]
        stored = committed["stored_pack_hash"]
        tampered_actual = pack_hash(
            tampered["evidence_ledger"], tampered["reasoning_ledger"],
            tampered["schema_version_id"])
        expected_tampered = vector["expected"]["tampered_pack_hash"]
        if tampered_actual == expected_tampered:
            ok("TAMPERED_HASH", f"Tampered hash consistent: {tampered_actual[:16]}...")
        else:
            fail("TAMPERED_HASH",
                 f"Expected tampered hash {expected_tampered[:16]}... got {tampered_actual[:16]}...")
        if tampered_actual != stored:
            ok("MISMATCH_DETECTED", "Tampered hash != stored hash — tampering detectable")
        else:
            fail("MISMATCH_DETECTED", "Tampered hash == stored hash — tampering NOT detectable")

    elif suite == "negative-proof":
        inp = vector["input"]
        if "expected_evidence_type" in inp:
            # NEG-001 style: verify negative_proof_hash computation
            expected_nph = vector["expected"]["negative_proof_hash"]
            actual_nph = negative_proof_hash(
                inp["expected_evidence_type"], inp["gap_window_start"],
                inp["gap_window_end"], inp["schema_version_id"])
            if actual_nph == expected_nph:
                ok("NEGATIVE_PROOF_HASH", f"Verified: {actual_nph[:16]}...")
            else:
                fail("NEGATIVE_PROOF_HASH",
                     f"Expected {expected_nph[:16]}... got {actual_nph[:16]}...")
        else:
            # NEG-002 style: verify pack_hash of record containing NegativeProofRecord
            expected_ph = vector["expected"]["pack_hash"]
            actual_ph = pack_hash(inp["evidence_ledger"], inp["reasoning_ledger"],
                                  inp["schema_version_id"])
            if actual_ph == expected_ph:
                ok("PACK_HASH_WITH_NEG_PROOF", f"Verified: {actual_ph[:16]}...")
            else:
                fail("PACK_HASH_WITH_NEG_PROOF",
                     f"Expected {expected_ph[:16]}... got {actual_ph[:16]}...")
            # Also verify the embedded negative_proof_hash
            for item in inp["evidence_ledger"]:
                if item.get("evidence_type") == "negative_proof":
                    schema = item.get("schema_version_id", inp["schema_version_id"])
                    expected_nph = negative_proof_hash(
                        item["expected_evidence_type"], item["gap_window_start"],
                        item["gap_window_end"], schema)
                    if item["negative_proof_hash"] == expected_nph:
                        ok("EMBEDDED_NEG_PROOF_HASH", "Embedded NegativeProofRecord hash verified")
                    else:
                        fail("EMBEDDED_NEG_PROOF_HASH", "Embedded NegativeProofRecord hash mismatch")

    elif suite == "admissibility":
        inp = vector["input"]
        expected_admissible = vector["expected"]["admissible"]
        expected_reason = vector["expected"]["reason"]
        actual_admissible, actual_reason = evaluate_admissibility(
            inp["plausibility_status"], inp.get("dissent_final_position"),
            inp["gate_status"])
        if actual_admissible == expected_admissible:
            ok("ADMISSIBLE", f"admissible={actual_admissible}")
        else:
            fail("ADMISSIBLE",
                 f"Expected admissible={expected_admissible}, got {actual_admissible}")
        if actual_reason == expected_reason:
            ok("REASON", f"reason={actual_reason!r}")
        else:
            fail("REASON",
                 f"Expected reason {expected_reason!r}, got {actual_reason!r}")

    else:
        fail("UNKNOWN_SUITE", f"No handler for suite '{suite}'")

    return {"passed": len(errors) == 0, "vector_id": vid, "suite": suite,
            "checks": checks, "errors": errors}


def run_suite(vectors_dir: Path) -> dict:
    """Run all .json vectors under vectors_dir recursively."""
    results = []
    vector_files = sorted(vectors_dir.rglob("case-*.json"))
    if not vector_files:
        return {"total": 0, "passed": 0, "failed": 0, "results": []}
    for vf in vector_files:
        with open(vf) as f:
            vector = json.load(f)
        result = run_vector(vector)
        result["file"] = str(vf.relative_to(vectors_dir))
        results.append(result)
    passed = sum(1 for r in results if r["passed"])
    return {"total": len(results), "passed": passed,
            "failed": len(results) - passed, "results": results}


# ── Output formatting ─────────────────────────────────────────────────────────

def print_record_result(result: dict, path: str) -> None:
    print(f"\nAIEP Verifier v{__version__} — Kernel {KERNEL_VERSION}")
    print(f"Record: {path}")
    print("=" * 56)
    for c in result["checks"]:
        icon = "\u2713" if c["result"] == "PASS" else "\u2717"
        print(f"  {icon} {c['check']}: {c['detail']}")
    print("=" * 56)
    if result["valid"]:
        print("  VERDICT: VALID \u2014 record is cryptographically sound\n")
    else:
        print("  VERDICT: INVALID")
        for e in result["errors"]:
            print(f"    \u2192 {e}")
        print()


def print_suite_result(suite_result: dict) -> None:
    results = suite_result["results"]
    print(f"\nAIEP Conformance Suite v{VECTORS_VERSION} — Kernel {KERNEL_VERSION}")
    print("=" * 56)
    for r in results:
        icon = "\u2713" if r["passed"] else "\u2717"
        print(f"  {icon} {r['vector_id']} ({r['file']})")
        if not r["passed"]:
            for e in r["errors"]:
                print(f"      \u2192 {e}")
    print("=" * 56)
    t, p, f = suite_result["total"], suite_result["passed"], suite_result["failed"]
    if f == 0:
        print(f"  RESULT: {p}/{t} PASS \u2014 CONFORMANT\n")
    else:
        print(f"  RESULT: {p}/{t} PASS, {f} FAIL \u2014 NON-CONFORMANT\n")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="aiep-verify",
        description="AIEP decision record verifier and conformance test runner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("record", nargs="?",
                        help="Path to a decision record JSON, or - for stdin")
    parser.add_argument("--vectors", metavar="DIR",
                        help="Run AIEP conformance test suite from vectors directory")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--version", action="version",
                        version=f"aiep-verify {__version__} (kernel {KERNEL_VERSION})")
    args = parser.parse_args()

    if args.vectors:
        vdir = Path(args.vectors)
        if not vdir.is_dir():
            print(f"error: vectors directory not found: {vdir}", file=sys.stderr)
            return 2
        suite_result = run_suite(vdir)
        if args.as_json:
            print(json.dumps(suite_result, indent=2))
        else:
            print_suite_result(suite_result)
        return 0 if suite_result["failed"] == 0 else 1

    if args.record:
        if args.record == "-":
            data = json.load(sys.stdin)
            path = "<stdin>"
        else:
            record_path = Path(args.record)
            if not record_path.exists():
                print(f"error: file not found: {record_path}", file=sys.stderr)
                return 2
            with open(record_path) as f:
                data = json.load(f)
            path = str(record_path)
        result = verify_record(data)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            print_record_result(result, path)
        return 0 if result["valid"] else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
