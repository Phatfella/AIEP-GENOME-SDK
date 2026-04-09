#!/usr/bin/env python3
"""
aiep-verify — AIEP Decision Record & Test Vector Verifier
==========================================================
Standalone. Zero dependencies beyond Python stdlib (3.9+).
Readable in under 10 minutes. Trustable without trusting AIEP.

Usage:
    aiep-verify --self-test                    # validate this verifier against canon
    aiep-verify record.json                    # verify a decision record
    aiep-verify --vectors vectors/v1.0.0/      # run conformance test suite
    aiep-verify record.json --json             # machine-readable output
    cat record.json | aiep-verify -            # stdin

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
    2 — usage error

Self-test guarantee: this verifier runs a canon self-test before processing any
vectors. If the implementation has drifted from CANON_SPEC, it reports that first
and aborts — a drifted verifier cannot be trusted to produce correct results.

See CANON_SPEC.md for the language-agnostic canonical specification.
See CLAIMS.md for the precise bounded claims each vector exercises.

AIEP Kernel v1.0.0 | CANON_SPEC v1.0.0 | AIEP-VECTORS v1.0.0
"""
import sys
import json
import hashlib
import unicodedata
import argparse
from pathlib import Path

VERIFIER_VERSION   = "1.0.0"
KERNEL_VERSION     = "1.0.0"
CANON_SPEC_VERSION = "1.0.0"
LOCKFILE_VERSION   = "1.0.0"
VECTORS_VERSION    = "1.0.0"
VECTOR_PACK_VERSION = "1.0.0"


# ── Canonical primitives (mirror of kernel/canon/canon.py LOCKED at v1.0.0) ──
# Self-contained duplicates — deliberately inlined so this file has zero imports
# outside stdlib. Cross-check these against kernel/canon/canon.py using the
# SHA-256 of that file recorded in CANON_SPEC.md.

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
    """R1+R2+R3: sort_keys, compact separators, NFC-normalised, no ASCII escaping."""
    return json.dumps(_nfc_object(obj), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def sha256_hex(s: str) -> str:
    """R4: SHA-256 of UTF-8 encoded string → lowercase hex. NFC applied upstream."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def concat_hash(*parts: str) -> str:
    """
    R7: length-prefixed-8be concatenation hash.
    H(len(p0)||p0 || len(p1)||p1 || ...) — each length is 8-byte big-endian.
    Prevents boundary collisions: concat_hash('ab','c') != concat_hash('a','bc').
    NFC normalisation applied per-part.
    """
    buf = b""
    for part in parts:
        encoded = _nfc(part).encode("utf-8")
        buf += len(encoded).to_bytes(8, "big") + encoded
    return hashlib.sha256(buf).hexdigest()


def pack_hash(evidence_ledger: list, reasoning_ledger: list, schema_version_id: str) -> str:
    """R8: Deterministic replay hash. generated_ts excluded by design."""
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
    """Constitutional arbitration — mirrors kernel/arbitration.py CC-001/CC-004/CC-005."""
    if gate_status != "OPEN":
        return False, "CC-005: Gate is CLOSED \u2014 fail-closed constitutional default"
    if plausibility_status == "implausible":
        return False, "CC-001: Plausibility filter rejected \u2014 conclusion is implausible"
    if plausibility_status == "indeterminate":
        return False, "CC-001: Plausibility indeterminate \u2014 cannot advance under uncertainty"
    if dissent_final_position in ("reject", "escalate"):
        return False, "CC-004: Dissent unresolved \u2014 conclusion contested or escalated"
    return True, "ADMISSIBLE"


# ── Canon self-test ───────────────────────────────────────────────────────────
# Runs on every invocation before processing records or vectors.
# If any check fails the verifier aborts — it cannot silently produce wrong results.
# Known values are from CANON_SPEC.md v1.0.0 (verified against the locked kernel).

def _self_test() -> list:
    """
    Verify this implementation against the known vectors in CANON_SPEC.md v1.0.0.
    Returns a list of failure strings. Empty list = all checks passed.
    Must be called before every operation — a drifted verifier must not silently
    produce wrong results.
    """
    failures = []

    # R1 / R2: canonical_json key ordering and compact format
    got = canonical_json({"z": 1, "a": 2})
    if got != '{"a":2,"z":1}':
        failures.append(
            f"R1/R2: canonical_json({{z:1,a:2}}) = {got!r}, expected '{{\"a\":2,\"z\":1}}'"
        )

    # R3: NFC normalisation — precomposed \u00C5 (Å) must equal decomposed A + \u030A (ring above)
    j_comp = canonical_json({"n": "\u00c5"})
    j_dec  = canonical_json({"n": "A\u030a"})
    if j_comp != j_dec:
        failures.append(
            f"R3: NFC failure — precomposed \\u00C5 != decomposed A\\u030A\n"
            f"  composed:   {j_comp!r}\n"
            f"  decomposed: {j_dec!r}"
        )

    # R4: sha256_hex known vectors (verified against locked kernel)
    # sha256_hex operates on raw UTF-8 bytes.
    # NOTE: sha256_hex('AIEP') = 13f3f3d9... — do NOT use d3e20aae... (confirmed wrong)
    h_empty = sha256_hex("")
    if h_empty != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        failures.append(
            f"R4(empty): sha256_hex('') = {h_empty!r}, "
            f"expected 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'"
        )

    h_aiep = sha256_hex("AIEP")
    if h_aiep != "13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e":
        failures.append(
            f"R4(AIEP): sha256_hex('AIEP') = {h_aiep!r}, "
            f"expected '13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e'"
        )

    # R6: ensure_ascii=False — no \uXXXX escaping in output
    j_e = canonical_json({"k": "\u00e9"})
    if "\\u" in j_e:
        failures.append(f"R6: \\uXXXX escaping present in output: {j_e!r}")

    # R7: length-prefix boundary collision safety
    if concat_hash("AB", "CD") == concat_hash("A", "BCD"):
        failures.append(
            f"R7: boundary collision — concat_hash('AB','CD') == concat_hash('A','BCD')"
        )
    # R7: empty-field variant must also be distinct
    if concat_hash("", "x") == concat_hash("x", ""):
        failures.append(
            f"R7: empty-field collision — concat_hash('','x') == concat_hash('x','')"
        )

    # R8: pack_hash DET-001 known vector (the canonical reference record)
    el = [{"collected_ts": "2026-01-01T00:00:00Z",
           "content": "temperature_reading_celsius=72.4",
           "evidence_id": "00000000-0000-0000-0000-000000000001",
           "evidence_type": "structured_data"}]
    rl = [{"conclusion": "Temperature within safe operating range. No action required.",
           "reasoning_id": "00000000-0000-0000-0000-000000000101"}]
    sv = "aiep.canonical.v2.0.0"
    h_det = pack_hash(el, rl, sv)
    if h_det != "cb1a5394a39cb30ad2b9bdeb4afae26d25f7f9afbb4026f74af3b36e7146e3ae":
        failures.append(
            f"R8(DET-001): pack_hash = {h_det!r}, "
            f"expected 'cb1a5394a39cb30ad2b9bdeb4afae26d25f7f9afbb4026f74af3b36e7146e3ae'"
        )

    return failures


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
                         f"Hash mismatch in NegativeProofRecord {item.get('evidence_id', '?')}")
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

    if suite == "deterministic-replay":
        inp = vector["input"]
        if "evidence_ledger_precomposed" in inp:
            # NFC variant: two ledger forms must produce identical pack_hash
            rl = inp.get("reasoning_ledger", [])
            sv = inp.get("schema_version_id", "")
            h_pre = pack_hash(inp["evidence_ledger_precomposed"], rl, sv)
            h_dec = pack_hash(inp["evidence_ledger_decomposed"], rl, sv)
            expected = vector["expected"].get("pack_hash",
                             vector["expected"].get("both_must_equal", ""))
            if h_pre != h_dec:
                fail("NFC_EQUAL",
                     f"precomposed {h_pre[:16]}... != decomposed {h_dec[:16]}...")
            else:
                ok("NFC_EQUAL", "precomposed == decomposed")
            if expected and h_pre != expected:
                fail("PACK_HASH", f"Expected {expected[:16]}... got {h_pre[:16]}...")
            elif expected:
                ok("PACK_HASH", f"Verified: {h_pre[:16]}...")
        else:
            expected_hash = vector["expected"]["pack_hash"]
            actual = pack_hash(inp["evidence_ledger"], inp["reasoning_ledger"],
                               inp["schema_version_id"])
            if actual == expected_hash:
                ok("PACK_HASH", f"Verified: {actual[:16]}...")
            else:
                fail("PACK_HASH",
                     f"Expected {expected_hash[:16]}... got {actual[:16]}...")
            # must_differ_from assertion (uniqueness check)
            mdf = vector["expected"].get("must_differ_from")
            if mdf and actual == mdf.get("pack_hash", ""):
                fail("UNIQUENESS",
                     f"Hash must differ from {mdf.get('vector','?')} but is identical")
            elif mdf:
                ok("UNIQUENESS", f"Differs from {mdf.get('vector','?')}")

    elif suite == "tamper-detection":
        if "committed_record" in vector:
            # Legacy format
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
                     f"Expected tampered hash {expected_tampered[:16]}... "
                     f"got {tampered_actual[:16]}...")
            if tampered_actual != stored:
                ok("MISMATCH_DETECTED",
                   "Tampered hash \u2260 stored hash \u2014 tampering detectable")
            else:
                fail("MISMATCH_DETECTED",
                     "Tampered hash == stored hash \u2014 tampering NOT detectable")
        else:
            # New format: input contains _original / _tampered variants
            inp = vector["input"]
            sv = inp.get("schema_version_id", "")
            el_orig = inp.get("evidence_ledger_original", inp.get("evidence_ledger", []))
            el_tamp = inp.get("evidence_ledger_tampered", inp.get("evidence_ledger", []))
            rl_orig = inp.get("reasoning_ledger_original", inp.get("reasoning_ledger", []))
            rl_tamp = inp.get("reasoning_ledger_tampered", inp.get("reasoning_ledger", []))
            h_orig = pack_hash(el_orig, rl_orig, sv)
            h_tamp = pack_hash(el_tamp, rl_tamp, sv)
            exp_orig = vector["expected"].get("original_pack_hash", "")
            exp_tamp = vector["expected"].get("tampered_pack_hash", "")
            if exp_orig and h_orig != exp_orig:
                fail("ORIGINAL_HASH", f"Expected {exp_orig[:16]}... got {h_orig[:16]}...")
            elif exp_orig:
                ok("ORIGINAL_HASH", f"Verified: {h_orig[:16]}...")
            if exp_tamp and h_tamp != exp_tamp:
                fail("TAMPERED_HASH", f"Expected {exp_tamp[:16]}... got {h_tamp[:16]}...")
            elif exp_tamp:
                ok("TAMPERED_HASH", f"Verified: {h_tamp[:16]}...")
            if h_orig == h_tamp:
                fail("MISMATCH_DETECTED",
                     "original == tampered \u2014 tampering NOT detectable")
            else:
                ok("MISMATCH_DETECTED",
                   "original \u2260 tampered \u2014 tampering detectable")

    elif suite == "negative-proof":
        inp = vector["input"]
        if "expected_evidence_type" in inp:
            # Direct negative_proof_hash test
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
            # Pack-hash-including a NegativeProofRecord in the ledger
            expected_ph = vector["expected"]["pack_hash"]
            actual_ph = pack_hash(inp["evidence_ledger"], inp["reasoning_ledger"],
                                  inp["schema_version_id"])
            if actual_ph == expected_ph:
                ok("PACK_HASH_WITH_NEG_PROOF", f"Verified: {actual_ph[:16]}...")
            else:
                fail("PACK_HASH_WITH_NEG_PROOF",
                     f"Expected {expected_ph[:16]}... got {actual_ph[:16]}...")
            for item in inp["evidence_ledger"]:
                if item.get("evidence_type") == "negative_proof":
                    schema = item.get("schema_version_id", inp["schema_version_id"])
                    expected_nph = negative_proof_hash(
                        item["expected_evidence_type"], item["gap_window_start"],
                        item["gap_window_end"], schema)
                    if item["negative_proof_hash"] == expected_nph:
                        ok("EMBEDDED_NEG_PROOF_HASH",
                           "Embedded NegativeProofRecord hash verified")
                    else:
                        fail("EMBEDDED_NEG_PROOF_HASH",
                             "Embedded NegativeProofRecord hash mismatch")

    elif suite == "admissibility":
        inp = vector["input"]
        expected_admissible = vector["expected"]["admissible"]
        actual_admissible, actual_reason = evaluate_admissibility(
            inp["plausibility_status"], inp.get("dissent_final_position"),
            inp["gate_status"])
        if actual_admissible == expected_admissible:
            ok("ADMISSIBLE", f"admissible={actual_admissible}")
        else:
            fail("ADMISSIBLE",
                 f"Expected admissible={expected_admissible}, got {actual_admissible}")
        # Support reason_contains (substring) and reason (exact match)
        if "reason_contains" in vector["expected"]:
            substr = vector["expected"]["reason_contains"]
            if substr in actual_reason:
                ok("REASON", f"reason contains {substr!r}")
            else:
                fail("REASON",
                     f"Expected reason to contain {substr!r}, got {actual_reason!r}")
        elif "reason" in vector["expected"]:
            expected_reason = vector["expected"]["reason"]
            if actual_reason == expected_reason:
                ok("REASON", f"reason={actual_reason!r}")
            else:
                fail("REASON",
                     f"Expected reason {expected_reason!r}, got {actual_reason!r}")

    elif suite == "dissent-preservation":
        inp = vector["input"]
        sv = inp.get("schema_version_id", "")
        el = inp.get("evidence_ledger", [])
        h_high = pack_hash(el, inp.get("reasoning_ledger_branch_HIGH", []), sv)
        h_low  = pack_hash(el, inp.get("reasoning_ledger_branch_LOW", []), sv)
        exp_high = vector["expected"].get("pack_hash_branch_HIGH", "")
        exp_low  = vector["expected"].get("pack_hash_branch_LOW", "")
        if exp_high and h_high != exp_high:
            fail("BRANCH_HIGH", f"Expected {exp_high[:16]}... got {h_high[:16]}...")
        elif exp_high:
            ok("BRANCH_HIGH", f"Verified: {h_high[:16]}...")
        if exp_low and h_low != exp_low:
            fail("BRANCH_LOW", f"Expected {exp_low[:16]}... got {h_low[:16]}...")
        elif exp_low:
            ok("BRANCH_LOW", f"Verified: {h_low[:16]}...")
        if h_high == h_low:
            fail("BRANCHES_DISTINCT",
                 "HIGH and LOW branches hash identically \u2014 dissent not preserved")
        else:
            ok("BRANCHES_DISTINCT", "HIGH \u2260 LOW")

    else:
        fail("UNKNOWN_SUITE", f"No handler for suite {suite!r}")

    return {"passed": len(errors) == 0, "vector_id": vid, "suite": suite,
            "checks": checks, "errors": errors}


def run_suite(vectors_dir: Path) -> dict:
    """
    Run all vector .json files under vectors_dir recursively.
    Returns compliance_verdict 'AIEP-COMPLIANT vX.Y.Z' or 'NOT COMPLIANT'.
    Only core-profile vectors are required for the compliance verdict.
    """
    results = []
    for vf in sorted(vectors_dir.glob("**/*.json")):
        if vf.name in ("MANIFEST.json", "SHA256SUMS.txt", "vector.schema.json"):
            continue
        try:
            vector = json.loads(vf.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            results.append({
                "passed": False, "vector_id": vf.name,
                "suite": "unknown", "profile": "core",
                "file": str(vf.relative_to(vectors_dir)),
                "checks": [], "errors": [f"JSON parse error: {exc}"],
            })
            continue
        result = run_vector(vector)
        result["file"] = str(vf.relative_to(vectors_dir))
        result["profile"] = vector.get("profile", "core")
        results.append(result)

    if not results:
        return {
            "compliance_verdict": "NOT COMPLIANT",
            "core_compliant": False,
            "core_total": 0, "core_passed": 0,
            "total": 0, "passed": 0, "failed": 0, "results": [],
        }

    core_results = [r for r in results if r.get("profile") == "core"]
    core_passed  = sum(1 for r in core_results if r["passed"])
    all_passed   = sum(1 for r in results if r["passed"])
    core_ok      = (core_passed == len(core_results) and bool(core_results))
    label        = f"AIEP-COMPLIANT v{VECTOR_PACK_VERSION}" if core_ok else "NOT COMPLIANT"

    return {
        "compliance_verdict": label,
        "core_compliant": core_ok,
        "core_total": len(core_results),
        "core_passed": core_passed,
        "total": len(results),
        "passed": all_passed,
        "failed": len(results) - all_passed,
        "results": results,
    }


# ── Output formatting ─────────────────────────────────────────────────────────

def print_self_test_result(failures: list) -> None:
    print(f"\nAIEP Canon Self-Test — CANON_SPEC v{CANON_SPEC_VERSION} | Kernel v{KERNEL_VERSION}")
    print("=" * 58)
    checks = [
        "R1/R2 canonical_json key order + compact format",
        "R3    NFC: precomposed \\u00C5 == decomposed A\\u030A",
        "R4    sha256_hex('') known vector",
        "R4    sha256_hex('AIEP') known vector",
        "R6    ensure_ascii=False (no \\uXXXX escaping)",
        "R7    concat_hash boundary collision safety",
        "R7    concat_hash empty-field collision safety",
        "R8    pack_hash DET-001 known vector",
    ]
    for check in checks:
        icon = "\u2713"
        print(f"  {icon} {check}")
    if failures:
        for f in failures:
            print(f"  \u2717 FAIL: {f}")
    print("=" * 58)
    if not failures:
        print(f"  RESULT: PASS ({len(checks)}/{len(checks)}) \u2014 verifier matches canon\n")
    else:
        print(f"  RESULT: FAIL ({len(failures)} failures) \u2014 verifier has drifted from CANON_SPEC\n")


def print_record_result(result: dict, path: str) -> None:
    print(f"\nAIEP Verifier v{VERIFIER_VERSION} \u2014 Kernel {KERNEL_VERSION}")
    print(f"Record: {path}")
    print("=" * 56)
    for c in result["checks"]:
        icon = "\u2713" if c["result"] == "PASS" else "\u2717"
        print(f"  {icon} {c['check']}: {c['detail']}")
    print("=" * 56)
    if result["valid"]:
        print("  VERDICT: record valid\n")
    else:
        print("  VERDICT: record invalid")
        for e in result["errors"]:
            print(f"    \u2192 {e}")
        print()


def print_suite_result(suite_result: dict) -> None:
    results = suite_result["results"]
    print(f"\nAIEP Conformance Suite v{VECTORS_VERSION} \u2014 Kernel {KERNEL_VERSION}")
    print("=" * 56)
    for r in results:
        icon = "\u2713" if r["passed"] else "\u2717"
        print(f"  {icon} {r['vector_id']} ({r['file']})")
        if not r["passed"]:
            for e in r["errors"]:
                print(f"      \u2192 {e}")
    print("=" * 56)
    c  = suite_result.get("core_passed", suite_result["passed"])
    ct = suite_result.get("core_total",  suite_result["total"])
    t, p, f = suite_result["total"], suite_result["passed"], suite_result["failed"]
    verdict = suite_result.get("compliance_verdict",
                               f"AIEP-COMPLIANT v{VECTOR_PACK_VERSION}" if f == 0
                               else "NOT COMPLIANT")
    print(f"  Core:  {c}/{ct} passed")
    print(f"  Total: {p}/{t} passed")
    print(f"  VERDICT: {verdict}\n")


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
    parser.add_argument("--self-test", dest="self_test", action="store_true",
                        help="Run built-in canon self-test and exit")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--version", action="version",
                        version=(f"aiep-verify {VERIFIER_VERSION} "
                                 f"(kernel={KERNEL_VERSION} "
                                 f"canon_spec={CANON_SPEC_VERSION} "
                                 f"lockfile={LOCKFILE_VERSION})"))
    args = parser.parse_args()

    # Always run self-test first.
    # A verifier that has drifted from CANON_SPEC must not silently produce wrong results.
    canon_failures = _self_test()

    if args.self_test:
        if args.as_json:
            print(json.dumps({"passed": len(canon_failures) == 0,
                              "failures": canon_failures,
                              "canon_spec_version": CANON_SPEC_VERSION,
                              "kernel_version": KERNEL_VERSION}, indent=2))
        else:
            print_self_test_result(canon_failures)
        return 0 if not canon_failures else 1

    if canon_failures:
        print("FATAL: Canon self-test failed — this verifier has drifted from CANON_SPEC.",
              file=sys.stderr)
        for f in canon_failures:
            print(f"  {f}", file=sys.stderr)
        print("See CANON_SPEC.md for the canonical specification.", file=sys.stderr)
        return 2

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
        return 0 if suite_result.get("core_compliant", suite_result["failed"] == 0) else 1

    if args.record:
        if args.record == "-":
            data = json.load(sys.stdin)
            path = "<stdin>"
        else:
            record_path = Path(args.record)
            if not record_path.exists():
                print(f"error: file not found: {record_path}", file=sys.stderr)
                return 2
            with open(record_path, encoding="utf-8") as f:
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
