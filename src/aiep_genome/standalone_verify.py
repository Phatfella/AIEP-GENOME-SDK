#!/usr/bin/env python3
"""
aiep-verify -- AIEP Decision Record Verifier
============================================
Standalone. Zero dependencies beyond Python stdlib.
Every rule is pinned to CANON_SPEC_VERSION below.

Authority: Phatfella/AIEP-GENOME-SDK
  canon.py        BlobSha 3b100b43bf59ce6f6d35397e8c8c173a4447de5d
  arbitration.py  BlobSha 567e917d544d62691bca7dd95cb3214ddc868cce

Usage:
  aiep-verify record.json              # verdict: "record valid" / "record invalid"
  aiep-verify --vectors ./v1.0.0/      # verdict: "AIEP-COMPLIANT v1.0.0" / "NOT COMPLIANT"
  aiep-verify --self-test              # verify this implementation matches canon
  aiep-verify record.json --json       # machine-readable output
"""
from __future__ import annotations
import sys, json, hashlib, unicodedata, argparse, decimal
from pathlib import Path

VERIFIER_VERSION     = "1.0.0"
CANON_SPEC_VERSION   = "1.0.0"
KERNEL_VERSION       = "1.0.0"
LOCKFILE_VERSION     = "1.0.0"
VECTOR_PACK_VERSION  = "1.0.0"
CANON_BLOBSHA        = "3b100b43bf59ce6f6d35397e8c8c173a4447de5d"
ARBITRATION_BLOBSHA  = "567e917d544d62691bca7dd95cb3214ddc868cce"

# ===============================================================
# CANON IMPLEMENTATION
# Every function cites its rule. No convenience shortcuts.
# ===============================================================

def _nfc(s: str) -> str:
    """R3: NFC-normalise a single string."""
    return unicodedata.normalize("NFC", s)

def _nfc_object(obj):
    """R3: Recursively NFC-normalise all strings in a JSON-compatible structure."""
    if isinstance(obj, str):   return _nfc(obj)
    if isinstance(obj, dict):
        for k in obj.keys():
            if not isinstance(k, str):
                raise CanonError(
                    f"R1: object member name must be a string, "
                    f"got {type(k).__name__} ({k!r})")
        return {_nfc(k): _nfc_object(v) for k, v in obj.items()}
    if isinstance(obj, list):  return [_nfc_object(i) for i in obj]
    if isinstance(obj, bool):  return obj
    if isinstance(obj, (int, float)): return obj
    return obj

# -- R5: Number normalisation ------------------------------------------------

class CanonError(ValueError):
    """Raised when input violates a canon rule."""

def _canon_number(n) -> str:
    """
    R5: Canonical lexical representation of a number.
    Emitted as a bare JSON numeric token -- no quotes.

    Forbidden:
      - Minus-zero    -> CanonError
      - NaN           -> CanonError
      - Infinity      -> CanonError

    Normalised:
      - No scientific notation  (1e5 -> 100000)
      - Trailing zeros trimmed  (1.50 -> 1.5, 1.0 -> 1)
    """
    d = decimal.Decimal(str(n))
    if not d.is_finite():
        raise CanonError(
            f"R5: non-finite number is forbidden in canonical records (got {n!r})")
    if d.is_zero() and d.is_signed():
        raise CanonError(
            f"R5: minus-zero is forbidden in canonical records (got {n!r})")
    return format(d.normalize(), "f")

# _norm_numbers_in_object is intentionally absent.
# Numbers are handled directly in _sort_and_serialise() to avoid converting
# numeric values to Python strings before serialisation, which would cause
# them to be emitted as JSON string literals ("1") instead of JSON numeric
# tokens (1).

# -- R1: Key sort by NFC-normalised UTF-8 byte sequences ---------------------

def _utf8_sort_key(s: str) -> bytes:
    """
    R1: Sort key for object member names.
    Spec: lexicographic order of NFC-normalised UTF-8 byte sequences.
    NOT Python string ordering -- explicit UTF-8 byte comparison.
    """
    return _nfc(s).encode("utf-8")

def _sort_and_serialise(obj) -> str:
    """
    Recursive canonical serialiser.
    Handles each JSON type explicitly -- no implicit json.dumps fallback on numbers.

    R1: dict keys sorted by NFC UTF-8 byte sequences
    R2: compact separators, no whitespace
    R3: NFC applied to all strings (via _nfc_object at entry)
    R5: numbers emitted as canonical numeric tokens, never as strings
    R6: ensure_ascii=False on string values -- literal UTF-8
    """
    # bool must be checked before int -- isinstance(True, int) is True in Python
    if isinstance(obj, bool):
        return "true" if obj else "false"

    if isinstance(obj, (int, float)):
        # R5: emit canonical numeric token directly -- no quotes
        return _canon_number(obj)

    if isinstance(obj, str):
        # R6: literal UTF-8, no \uXXXX escaping
        return json.dumps(obj, ensure_ascii=False)

    if obj is None:
        return "null"

    if isinstance(obj, list):
        return "[" + ",".join(_sort_and_serialise(i) for i in obj) + "]"

    if isinstance(obj, dict):
        # R1: sort by NFC-normalised UTF-8 byte sequences
        # (non-string key guard is in _nfc_object, called before this)
        sorted_items = sorted(obj.items(), key=lambda kv: _utf8_sort_key(kv[0]))
        inner = ",".join(
            json.dumps(_nfc(k), ensure_ascii=False) + ":" + _sort_and_serialise(v)
            for k, v in sorted_items
        )
        return "{" + inner + "}"

    raise CanonError(
        f"Unhandled type {type(obj).__name__} -- "
        f"cannot produce canonical JSON for value {obj!r}")


def canonical_json(obj) -> str:
    """
    R1+R2+R3+R5+R6: Canonical JSON.
    Entry point. NFC-normalises all strings, then serialises with explicit type dispatch.
    """
    return _sort_and_serialise(_nfc_object(obj))

# -- R4: SHA-256, lowercase hex -----------------------------------------------

def sha256_hex(s: str) -> str:
    """R4: SHA-256 of UTF-8-encoded string. Returns lowercase hex (64 chars)."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# Known R4 vectors from CANON_SPEC v1.0.0 -- verified against locked kernel.
# NOTE: sha256_hex("AIEP") = 13f3f3d9... -- d3e20aae... is confirmed wrong.
_R4_KNOWN = {
    "":     "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "AIEP": "13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e",
}

# -- R7: Length-prefixed concatenation ----------------------------------------

def concat_hash(*parts: str) -> str:
    """
    R7: Each field prefixed by its UTF-8 byte length as 8-byte big-endian uint.
    R3 applied to each string before encoding.
    """
    buf = b""
    for p in parts:
        enc = _nfc(p).encode("utf-8")
        buf += len(enc).to_bytes(8, "big") + enc
    return hashlib.sha256(buf).hexdigest()

# -- R8: pack_hash ------------------------------------------------------------

def pack_hash(evidence_ledger: list, reasoning_ledger: list,
              schema_version_id: str) -> str:
    """R8: generated_ts deliberately excluded -- time must not affect determinism."""
    return sha256_hex(canonical_json({
        "evidence_ledger": evidence_ledger,
        "reasoning_ledger": reasoning_ledger,
        "schema_version_id": schema_version_id,
    }))

# -- Negative proof hash ------------------------------------------------------

def negative_proof_hash(t: str, s: str, e: str, v: str) -> str:
    """R7: H_concat(expected_evidence_type, gap_start, gap_end, schema_version_id)"""
    return concat_hash(t, s, e, v)

# -- evaluate_admissibility -- verbatim from arbitration.py BlobSha 567e917d --

def _evaluate_admissibility(plausibility_status: str,
                              dissent_final_position,
                              gate_status: str) -> tuple:
    """
    Reimplemented verbatim from kernel/arbitration/arbitration.py.
    BlobSha: 567e917d544d62691bca7dd95cb3214ddc868cce
    DO NOT modify this logic independently of the kernel source.
    """
    if gate_status != "OPEN":
        return False, "CC-005: Gate is CLOSED \u2014 fail-closed constitutional default"
    if plausibility_status == "implausible":
        return False, "CC-001: Plausibility filter rejected \u2014 conclusion is implausible"
    if plausibility_status == "indeterminate":
        return False, "CC-001: Plausibility indeterminate \u2014 cannot advance under uncertainty"
    if dissent_final_position in ("reject", "escalate"):
        return False, "CC-004: Dissent unresolved \u2014 conclusion contested or escalated"
    return True, "ADMISSIBLE"

# ===============================================================
# SELF-TEST -- runs before every operation
# ===============================================================

def _self_test() -> list:
    """
    Verify this verifier matches CANON_SPEC v1.0.0 and arbitration.py.
    Returns list of failure strings. Must be empty before any verification.
    """
    f = []

    # R1 -- member ordering by NFC UTF-8 bytes
    # integers must appear as numeric tokens: {"a":2,"z":1} not {"a":"2","z":"1"}
    got = canonical_json({"z": 1, "a": 2})
    if got != '{"a":2,"z":1}':
        f.append(f'R1: expected \'{{"a":2,"z":1}}\', got {got!r}')

    # R1 -- UTF-8 byte order distinguishes keys that differ after byte 0
    # "\u00e9" (e with acute, 2 bytes: 0xc3 0xa9) vs "f" (1 byte: 0x66)
    # 0x66 < 0xc3, so "f" sorts before "\u00e9"
    got_order = canonical_json({"\u00e9": 1, "f": 2})
    if got_order != '{"f":2,"\u00e9":1}':
        f.append(f'R1: UTF-8 byte sort failed -- got {got_order!r}')

    # R2 -- no whitespace
    if " " in canonical_json({"k": "v"}):
        f.append("R2: whitespace present in canonical output")

    # R3 -- NFC: precomposed == decomposed
    if canonical_json({"n": "\u00c5"}) != canonical_json({"n": "A\u030a"}):
        f.append("R3: NFC failed -- precomposed \\u00C5 != decomposed A\\u030A")

    # R4 -- known SHA-256 vectors
    for s, exp in _R4_KNOWN.items():
        got_h = sha256_hex(s)
        if got_h != exp:
            f.append(f"R4: sha256_hex({s!r}) expected {exp[:16]}... got {got_h[:16]}...")

    # R5 -- numbers as numeric tokens, not strings
    got_num = canonical_json({"v": 1.5})
    if got_num != '{"v":1.5}':
        f.append(f'R5: expected \'{{"v":1.5}}\', got {got_num!r}')

    got_int = canonical_json({"v": 1.0})
    if got_int != '{"v":1}':
        f.append(f'R5: trailing zero -- expected \'{{"v":1}}\', got {got_int!r}')

    got_large = canonical_json({"v": 1e5})
    if "e" in got_large.lower() or got_large != '{"v":100000}':
        f.append(f'R5: scientific notation -- expected \'{{"v":100000}}\', got {got_large!r}')

    # R5 -- minus-zero raises CanonError
    try:
        _canon_number(-0.0)
        f.append("R5: minus-zero should raise CanonError but did not")
    except CanonError:
        pass   # correct

    # R5 -- NaN rejected
    import math
    try:
        _canon_number(math.nan)
        f.append("R5: NaN should raise CanonError but did not")
    except CanonError:
        pass

    # R5 -- Infinity rejected
    try:
        _canon_number(math.inf)
        f.append("R5: Infinity should raise CanonError but did not")
    except CanonError:
        pass

    # R1 -- non-string key rejected
    try:
        canonical_json({1: "x"})
        f.append("R1: non-string key should raise CanonError but did not")
    except CanonError:
        pass

    # R5 -- bool is not a number (True/False must not be R5-treated)
    got_bool = canonical_json({"a": True, "b": False})
    if got_bool != '{"a":true,"b":false}':
        f.append(f'R5: bool serialised incorrectly -- got {got_bool!r}')

    # R6 -- no \uXXXX escaping
    if "\\u" in canonical_json({"k": "\u00e9"}):
        f.append("R6: \\uXXXX escaping present -- ensure_ascii must be False")

    # R7 -- boundary safety
    if concat_hash("ab", "c") == concat_hash("a", "bc"):
        f.append("R7: boundary collision -- concat_hash('ab','c') == concat_hash('a','bc')")
    if concat_hash("", "x") == concat_hash("x", ""):
        f.append("R7: empty boundary -- concat_hash('','x') == concat_hash('x','')")

    # Admissibility -- CC-005 (verbatim from arbitration.py)
    ok, reason = _evaluate_admissibility("plausible", None, "CLOSED")
    if ok or "CC-005" not in reason:
        f.append(f"ADM/CC-005: CLOSED gate should block -- got admissible={ok}, reason={reason!r}")

    # Admissibility -- CC-004
    ok2, reason2 = _evaluate_admissibility("plausible", "reject", "OPEN")
    if ok2 or "CC-004" not in reason2:
        f.append(f"ADM/CC-004: rejected dissent should block -- got admissible={ok2}, reason={reason2!r}")

    # Admissibility -- happy path
    ok3, reason3 = _evaluate_admissibility("plausible", None, "OPEN")
    if not ok3 or reason3 != "ADMISSIBLE":
        f.append(f"ADM: happy path should be ADMISSIBLE -- got {ok3}, {reason3!r}")

    return f

# ===============================================================
# SUITE-SPECIFIC VECTOR HANDLERS
# Each handler knows the exact shape of its vector type.
# No generic fallback that silently passes unknown shapes.
# ===============================================================

def _run_det(v: dict) -> tuple:
    """
    deterministic-replay vectors.
    DET-001/003: input.evidence_ledger + input.reasoning_ledger
    DET-002:     input.evidence_ledger_precomposed + input.evidence_ledger_decomposed
    """
    inp = v["input"]
    exp = v["expected"]

    if "evidence_ledger_precomposed" in inp:
        # DET-002: NFC equivalence test
        h_pre = pack_hash(inp["evidence_ledger_precomposed"],
                          inp["reasoning_ledger"],
                          inp["schema_version_id"])
        h_dec = pack_hash(inp["evidence_ledger_decomposed"],
                          inp["reasoning_ledger"],
                          inp["schema_version_id"])
        target = exp.get("pack_hash", exp.get("both_must_equal", ""))
        if h_pre != h_dec:
            return False, f"R3 NFC FAIL: precomposed {h_pre[:16]}... != decomposed {h_dec[:16]}..."
        if target and h_pre != target:
            return False, f"pack_hash MISMATCH: got {h_pre[:16]}..., expected {target[:16]}..."
        return True, f"NFC equivalence verified + pack_hash {h_pre[:16]}..."
    else:
        got = pack_hash(inp["evidence_ledger"],
                        inp["reasoning_ledger"],
                        inp["schema_version_id"])
        expected_hash = exp["pack_hash"]
        if got != expected_hash:
            return False, (f"pack_hash MISMATCH\n"
                           f"  expected: {expected_hash}\n"
                           f"  got:      {got}")
        return True, f"pack_hash verified {got[:16]}...{got[-8:]}"

def _run_tamp(v: dict) -> tuple:
    """
    tamper-detection vectors.
    TAMP-001: evidence_ledger_original / evidence_ledger_tampered
    TAMP-002: reasoning_ledger_original / reasoning_ledger_tampered
    """
    inp = v["input"]
    exp = v["expected"]

    if "evidence_ledger_tampered" in inp:
        got_orig = pack_hash(inp["evidence_ledger_original"],
                             inp["reasoning_ledger"], inp["schema_version_id"])
        got_tamp = pack_hash(inp["evidence_ledger_tampered"],
                             inp["reasoning_ledger"], inp["schema_version_id"])
    elif "reasoning_ledger_tampered" in inp:
        got_orig = pack_hash(inp["evidence_ledger"],
                             inp["reasoning_ledger_original"], inp["schema_version_id"])
        got_tamp = pack_hash(inp["evidence_ledger"],
                             inp["reasoning_ledger_tampered"], inp["schema_version_id"])
    else:
        return False, "TAMP vector missing tampered ledger field"

    failures = []
    if got_orig != exp["original_pack_hash"]:
        failures.append(f"original_pack_hash MISMATCH: got {got_orig[:16]}..., "
                        f"expected {exp['original_pack_hash'][:16]}...")
    if got_tamp != exp["tampered_pack_hash"]:
        failures.append(f"tampered_pack_hash MISMATCH: got {got_tamp[:16]}..., "
                        f"expected {exp['tampered_pack_hash'][:16]}...")
    if got_orig == got_tamp:
        failures.append("TAMPER NOT DETECTED: original == tampered hash")

    if failures:
        return False, " | ".join(failures)
    return True, (f"tamper detected: "
                  f"original {got_orig[:12]}... != tampered {got_tamp[:12]}...")

def _run_neg(v: dict) -> tuple:
    """negative-proof vectors -- direct negative_proof_hash computation."""
    inp = v["input"]
    exp = v["expected"]
    got = negative_proof_hash(
        inp["expected_evidence_type"],
        inp["gap_window_start"],
        inp["gap_window_end"],
        inp["schema_version_id"],
    )
    expected_hash = exp["negative_proof_hash"]
    if got != expected_hash:
        return False, (f"negative_proof_hash MISMATCH\n"
                       f"  expected: {expected_hash}\n"
                       f"  got:      {got}")
    return True, f"negative_proof_hash verified {got[:16]}...{got[-8:]}"

def _run_adm(v: dict) -> tuple:
    """
    admissibility vectors.
    Calls _evaluate_admissibility() directly -- verbatim from arbitration.py.
    NO placeholder passes. Every vector is actually executed.
    """
    inp = v["input"]
    exp = v["expected"]

    admissible, reason = _evaluate_admissibility(
        inp["plausibility_status"],
        inp.get("dissent_final_position"),
        inp["gate_status"],
    )

    expected_admissible = exp["admissible"]
    reason_contains     = exp.get("reason_contains", "")

    failures = []
    if admissible != expected_admissible:
        failures.append(f"admissible={admissible}, expected {expected_admissible}")
    if reason_contains and reason_contains not in reason:
        failures.append(f"reason {reason!r} does not contain {reason_contains!r}")

    if failures:
        return False, " | ".join(failures)
    return True, f"admissibility={admissible}, reason contains '{reason_contains}'"

def _run_dis(v: dict) -> tuple:
    """
    dissent-preservation vectors.
    DIS-001: two reasoning branches over same evidence -- must produce different hashes.
    """
    inp = v["input"]
    exp = v["expected"]

    h_high = pack_hash(inp["evidence_ledger"],
                       inp["reasoning_ledger_branch_HIGH"],
                       inp["schema_version_id"])
    h_low  = pack_hash(inp["evidence_ledger"],
                       inp["reasoning_ledger_branch_LOW"],
                       inp["schema_version_id"])

    failures = []
    if h_high != exp["pack_hash_branch_HIGH"]:
        failures.append(f"branch_HIGH MISMATCH: got {h_high[:16]}..., "
                        f"expected {exp['pack_hash_branch_HIGH'][:16]}...")
    if h_low != exp["pack_hash_branch_LOW"]:
        failures.append(f"branch_LOW MISMATCH: got {h_low[:16]}..., "
                        f"expected {exp['pack_hash_branch_LOW'][:16]}...")
    if h_high == h_low:
        failures.append("DISSENT NOT PRESERVED: branch_HIGH == branch_LOW hash")

    if failures:
        return False, " | ".join(failures)
    return True, (f"both branches preserved: "
                  f"HIGH {h_high[:12]}... != LOW {h_low[:12]}...")

# Dispatch table -- no fallback, no implicit pass
_SUITE_RUNNERS = {
    "deterministic-replay":  _run_det,
    "tamper-detection":      _run_tamp,
    "negative-proof":        _run_neg,
    "admissibility":         _run_adm,
    "dissent-preservation":  _run_dis,
}

# ===============================================================
# SINGLE RECORD VERIFICATION
# Verdict: "record valid" or "record invalid" -- NOT "compliant"
# ===============================================================

def _result(valid, verdict, checks, errors):
    return {"valid": valid, "verdict": verdict, "checks": checks, "errors": errors,
            "verifier_version": VERIFIER_VERSION,
            "canon_spec_version": CANON_SPEC_VERSION,
            "lockfile_version": LOCKFILE_VERSION}

def verify_record(record: dict, self_test_failures: list) -> dict:
    checks, errors = [], []
    def ok(n, d):   checks.append({"check": n, "result": "PASS", "detail": d})
    def fail(n, d): checks.append({"check": n, "result": "FAIL", "detail": d}); errors.append(f"{n}: {d}")

    if self_test_failures:
        fail("SELF_TEST",
             f"Verifier deviates from CANON_SPEC v{CANON_SPEC_VERSION}: "
             f"{self_test_failures}")
        return _result(False, "record invalid \u2014 verifier canon mismatch", checks, errors)
    ok("SELF_TEST", f"Canon R1\u2013R7 + ADM verified (CANON_SPEC v{CANON_SPEC_VERSION})")

    required = ["pack_hash", "evidence_ledger", "reasoning_ledger", "schema_version_id"]
    missing  = [f for f in required if f not in record]
    if missing:
        fail("STRUCTURE", f"Missing required fields: {missing}")
        return _result(False, "record invalid", checks, errors)
    ok("STRUCTURE", "All required fields present")

    try:
        recomputed = pack_hash(record["evidence_ledger"],
                               record["reasoning_ledger"],
                               record["schema_version_id"])
        if recomputed == record["pack_hash"]:
            ok("PACK_HASH", f"verified {recomputed[:16]}...{recomputed[-8:]}")
        else:
            fail("PACK_HASH",
                 f"MISMATCH\n"
                 f"  stored:     {record['pack_hash']}\n"
                 f"  recomputed: {recomputed}")
    except CanonError as e:
        fail("PACK_HASH", f"Canon violation in record: {e}")
    except Exception as e:
        fail("PACK_HASH", f"Recomputation error: {e}")

    if not record["evidence_ledger"]:
        fail("EVIDENCE_BOUNDEDNESS",
             "Empty evidence_ledger \u2014 no evidential basis (CLAIMS.md Claim 3)")
    else:
        ok("EVIDENCE_BOUNDEDNESS", f"{len(record['evidence_ledger'])} evidence record(s)")

    for i, item in enumerate(record.get("evidence_ledger", [])):
        if item.get("evidence_type") == "negative_proof":
            req = ["expected_evidence_type", "gap_window_start",
                   "gap_window_end", "schema_version_id"]
            if all(k in item for k in req):
                exp = negative_proof_hash(
                    item["expected_evidence_type"],
                    item["gap_window_start"],
                    item["gap_window_end"],
                    item.get("schema_version_id", record["schema_version_id"]),
                )
                stored = item.get("negative_proof_hash", "MISSING")
                if stored == exp:
                    ok(f"NEG_PROOF[{i}]", f"verified {exp[:16]}...")
                else:
                    fail(f"NEG_PROOF[{i}]",
                         f"MISMATCH\n  stored:   {stored}\n  expected: {exp}")

    verdict = "record valid" if not errors else "record invalid"
    return _result(not errors, verdict, checks, errors)

# ===============================================================
# SUITE RUNNER
# Verdict: "AIEP-COMPLIANT v1.0.0" or "NOT COMPLIANT"
# Reads MANIFEST.json, version-checks before running any vectors.
# ===============================================================

def run_suite(vectors_dir: Path, self_test_failures: list) -> dict:
    """
    Run all vectors in vectors_dir.
    Only this mode produces "AIEP-COMPLIANT".
    """
    manifest_path = vectors_dir / "MANIFEST.json"
    if not manifest_path.exists():
        return {"compliance_verdict": "NOT COMPLIANT",
                "core_compliant": False,
                "error": "MANIFEST.json not found in vector directory",
                "results": []}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version_errors = []
    if manifest.get("vector_pack_version") != VECTOR_PACK_VERSION:
        version_errors.append(
            f"vector_pack_version mismatch: "
            f"manifest={manifest.get('vector_pack_version')}, verifier expects={VECTOR_PACK_VERSION}")
    if manifest.get("canon_spec_version") != CANON_SPEC_VERSION:
        version_errors.append(
            f"canon_spec_version mismatch: "
            f"manifest={manifest.get('canon_spec_version')}, verifier={CANON_SPEC_VERSION}")
    if version_errors:
        return {"compliance_verdict": "NOT COMPLIANT",
                "core_compliant": False,
                "version_errors": version_errors,
                "results": []}

    if self_test_failures:
        return {"compliance_verdict": "NOT COMPLIANT",
                "core_compliant": False,
                "error": f"Verifier self-test failed: {self_test_failures}",
                "results": []}

    results = []
    for vf in sorted(vectors_dir.rglob("*.json")):
        if vf.name == "MANIFEST.json":
            continue
        try:
            v     = json.loads(vf.read_text(encoding="utf-8"))
            suite = v.get("suite", "")
            runner = _SUITE_RUNNERS.get(suite)
            if runner is None:
                results.append({
                    "vector_id": v.get("vector_id", vf.name),
                    "profile": v.get("profile", "unknown"),
                    "suite": suite,
                    "passed": False,
                    "detail": f"No handler for suite '{suite}' -- add to _SUITE_RUNNERS",
                    "file": str(vf.relative_to(vectors_dir)),
                })
                continue
            passed, detail = runner(v)
            results.append({
                "vector_id": v.get("vector_id", vf.name),
                "profile": v.get("profile", "unknown"),
                "suite": suite,
                "passed": passed,
                "detail": detail,
                "file": str(vf.relative_to(vectors_dir)),
            })
        except CanonError as e:
            results.append({"vector_id": str(vf.name), "profile": "unknown",
                             "suite": "unknown", "passed": False,
                             "detail": f"Canon violation: {e}",
                             "file": str(vf)})
        except Exception as e:
            results.append({"vector_id": str(vf.name), "profile": "unknown",
                             "suite": "unknown", "passed": False,
                             "detail": f"Error: {e}",
                             "file": str(vf)})

    core    = [r for r in results if r.get("profile") == "core"]
    core_ok = sum(1 for r in core if r["passed"])
    all_ok  = sum(1 for r in results if r["passed"])
    compliant = core_ok == len(core) and bool(core)

    return {
        "compliance_verdict": f"AIEP-COMPLIANT v{VECTOR_PACK_VERSION}" if compliant
                              else "NOT COMPLIANT",
        "core_compliant": compliant,
        "core_passed": core_ok,
        "core_total": len(core),
        "total": len(results),
        "passed": all_ok,
        "failed": len(results) - all_ok,
        "manifest_version": manifest.get("vector_pack_version"),
        "results": results,
    }

# ===============================================================
# OUTPUT + CLI
# ===============================================================

def _print_record(result: dict) -> None:
    print(f"\nAIEP Verifier v{VERIFIER_VERSION}  |  Canon {CANON_SPEC_VERSION}")
    print("\u2500" * 60)
    for c in result["checks"]:
        print(f"  {'✓' if c['result']=='PASS' else '✗'}  {c['check']}: {c['detail']}")
    print("\u2500" * 60)
    print(f"  VERDICT: {result['verdict'].upper()}")
    if not result["valid"]:
        for e in result["errors"]: print(f"    \u2192 {e}")
    print()

def _print_suite(suite: dict) -> None:
    print(f"\nAIEP Conformance Suite  |  Verifier v{VERIFIER_VERSION}  |  Canon {CANON_SPEC_VERSION}")
    print("\u2500" * 60)
    if "version_errors" in suite:
        for e in suite["version_errors"]: print(f"  \u2717 VERSION: {e}")
    elif "error" in suite:
        print(f"  \u2717 {suite['error']}")
    else:
        for r in suite["results"]:
            icon = "\u2713" if r["passed"] else "\u2717"
            print(f"  {icon}  {r['vector_id']}  [{r['profile']}]  {r['detail']}")
    print("\u2500" * 60)
    print(f"  Core:  {suite.get('core_passed','?')}/{suite.get('core_total','?')} passed")
    print(f"  Total: {suite.get('passed','?')}/{suite.get('total','?')} passed")
    print(f"  VERDICT: {suite['compliance_verdict']}")
    print()

def main() -> None:
    p = argparse.ArgumentParser(
        description=f"AIEP Verifier v{VERIFIER_VERSION} | Canon {CANON_SPEC_VERSION}")
    p.add_argument("record", nargs="?",
                   help="Record JSON path, or - for stdin")
    p.add_argument("--vectors", metavar="DIR",
                   help="Run conformance suite -- verdict: AIEP-COMPLIANT or NOT COMPLIANT")
    p.add_argument("--json",      action="store_true", help="JSON output")
    p.add_argument("--self-test", dest="self_test", action="store_true",
                   help="Self-test only -- verify this implementation matches canon")
    args = p.parse_args()

    failures = _self_test()

    if args.self_test:
        out = {"self_test": "PASS" if not failures else "FAIL",
               "failures": failures,
               "canon_spec_version": CANON_SPEC_VERSION,
               "canon_blobsha": CANON_BLOBSHA,
               "arbitration_blobsha": ARBITRATION_BLOBSHA}
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            status = "PASS" if not failures else "FAIL"
            print(f"AIEP self-test  |  Canon {CANON_SPEC_VERSION}  |  {status}")
            for f in failures: print(f"  \u2717 {f}")
        sys.exit(0 if not failures else 1)

    if failures:
        print("FATAL: Canon self-test failed -- verifier has drifted from CANON_SPEC.",
              file=sys.stderr)
        for f in failures: print(f"  {f}", file=sys.stderr)
        sys.exit(2)

    if args.vectors:
        suite = run_suite(Path(args.vectors), failures)
        if args.json: print(json.dumps(suite, indent=2))
        else:         _print_suite(suite)
        sys.exit(0 if suite["core_compliant"] else 1)

    if not args.record:
        p.print_help()
        sys.exit(1)

    data = (json.load(sys.stdin) if args.record == "-"
            else json.loads(Path(args.record).read_text(encoding="utf-8")))
    result = verify_record(data, failures)
    if args.json: print(json.dumps(result, indent=2))
    else:         _print_record(result)
    sys.exit(0 if result["valid"] else 1)

if __name__ == "__main__":
    main()