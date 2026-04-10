"""Tests for aiep_genome.kernel — determinism and invariants."""
import unittest
from aiep_genome.kernel import (
    canonical_json, sha256_hex, sha256_bytes, concat_hash,
    evidence_commitment, lifecycle_hash, normalisation_hash,
    negative_proof_hash, pack_hash, run_self_test,
    evaluate_gate, GateResult, MAX_ACTIVE_FRONTIER,
    arbitration_hash, evaluate_admissibility, CONSTITUTIONAL_CONSTRAINTS,
    create_negative_proof_record, verify_negative_proof_record,
    KERNEL_VERSION, ACTIVE_ALGORITHM, DIGEST_PATTERN,
)
import re


class TestCanonSerialization(unittest.TestCase):

    def test_key_sorting_r1(self):
        self.assertEqual(canonical_json({"z": 1, "a": 2}), '{"a":2,"z":1}')

    def test_no_whitespace_r2(self):
        result = canonical_json({"key": "value", "n": 42})
        self.assertNotIn(" ", result)
        self.assertNotIn("\n", result)

    def test_unicode_nfc_r3_composed_equals_decomposed(self):
        composed = "\u00c5"      # Å precomposed
        decomposed = "A\u030a"  # A + combining ring
        self.assertEqual(canonical_json({"n": composed}), canonical_json({"n": decomposed}))

    def test_unicode_not_ascii_escaped_r3(self):
        result = canonical_json({"n": "\u00c5"})
        self.assertNotIn("\\u", result)
        self.assertIn("\u00c5", result)

    def test_nested_key_sorting(self):
        result = canonical_json({"b": {"z": 1, "a": 2}, "a": 0})
        self.assertEqual(result, '{"a":0,"b":{"a":2,"z":1}}')

    def test_list_preserved(self):
        result = canonical_json({"items": [3, 1, 2]})
        self.assertEqual(result, '{"items":[3,1,2]}')

    def test_none_value(self):
        result = canonical_json({"k": None})
        self.assertEqual(result, '{"k":null}')

    def test_bool_values(self):
        result = canonical_json({"t": True, "f": False})
        self.assertIn('"t":true', result)
        self.assertIn('"f":false', result)

    def test_r5_float_integral_emitted_as_integer(self):
        # R5: 1.0 must emit as 1 (no trailing .0) for cross-language hash parity
        self.assertEqual(canonical_json({"n": 1.0}), '{"n":1}')
        self.assertEqual(canonical_json({"n": 100.0}), '{"n":100}')
        self.assertEqual(canonical_json({"n": 0.0}), '{"n":0}')

    def test_r5_float_fractional_preserved(self):
        self.assertEqual(canonical_json({"n": 1.5}), '{"n":1.5}')
        self.assertEqual(canonical_json({"n": 0.1}), '{"n":0.1}')

    def test_r5_float_matches_verifier(self):
        # Verify canonical_json(1.0) and standalone_verify canonical_json(1.0) produce same hash
        import importlib.util as _ilu, pathlib
        _sv_path = pathlib.Path(__file__).parent.parent / "src" / "aiep_genome" / "standalone_verify.py"
        _spec = _ilu.spec_from_file_location("standalone_verify", _sv_path)
        _sv = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_sv)
        for obj in [{"n": 1.0}, {"n": 1.5}, {"n": 100.0}, {"weight": 0.0}]:
            self.assertEqual(canonical_json(obj), _sv.canonical_json(obj),
                             f"R5 divergence for input {obj!r}")

    def test_r5_minus_zero_forbidden(self):
        import math
        with self.assertRaises(ValueError):
            canonical_json({"n": -0.0})

    def test_r5_nan_forbidden(self):
        import math
        with self.assertRaises(ValueError):
            canonical_json({"n": math.nan})

    def test_r5_inf_forbidden(self):
        import math
        with self.assertRaises(ValueError):
            canonical_json({"n": math.inf})

    def test_r5_bool_not_treated_as_number(self):
        # True/False must remain true/false, not 1/0
        self.assertEqual(canonical_json({"v": True}), '{"v":true}')
        self.assertEqual(canonical_json({"v": False}), '{"v":false}')


class TestSHA256(unittest.TestCase):

    def test_known_empty_hash(self):
        self.assertEqual(
            sha256_hex(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_known_aiep_hash(self):
        # SHA-256("AIEP") — computed reference vector
        expected = "13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e"
        self.assertEqual(sha256_hex("AIEP"), expected)

    def test_hex_lowercase_only(self):
        h = sha256_hex("test")
        self.assertRegex(h, r'^[a-f0-9]{64}$')

    def test_bytes_variant(self):
        h = sha256_bytes(b"")
        self.assertEqual(h, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_determinism_r4(self):
        h1 = sha256_hex(canonical_json({"b": 2, "a": 1}))
        h2 = sha256_hex(canonical_json({"a": 1, "b": 2}))
        self.assertEqual(h1, h2)


class TestConcatHash(unittest.TestCase):

    def test_boundary_safety_r7(self):
        """concat_hash("ab","c") must not equal concat_hash("a","bc")."""
        self.assertNotEqual(concat_hash("ab", "c"), concat_hash("a", "bc"))

    def test_empty_boundary(self):
        self.assertNotEqual(concat_hash("", "x"), concat_hash("x", ""))

    def test_single_part_equals_sha256(self):
        # One-part concat should equal sha256 of the length-prefixed payload
        import hashlib
        part = "hello"
        enc = part.encode("utf-8")
        expected = hashlib.sha256(len(enc).to_bytes(8, "big") + enc).hexdigest()
        self.assertEqual(concat_hash(part), expected)

    def test_returns_hex64(self):
        self.assertRegex(concat_hash("a", "b"), r'^[a-f0-9]{64}$')


class TestEvidenceCommitment(unittest.TestCase):

    def test_deterministic(self):
        ec1 = evidence_commitment('{"a":1}', "prov-a", "v1")
        ec2 = evidence_commitment('{"a":1}', "prov-a", "v1")
        self.assertEqual(ec1, ec2)

    def test_differs_on_provenance_change(self):
        ec1 = evidence_commitment('{"a":1}', "prov-a", "v1")
        ec2 = evidence_commitment('{"a":1}', "prov-b", "v1")
        self.assertNotEqual(ec1, ec2)

    def test_differs_on_schema_change(self):
        ec1 = evidence_commitment('{"a":1}', "p", "v1")
        ec2 = evidence_commitment('{"a":1}', "p", "v2")
        self.assertNotEqual(ec1, ec2)

    def test_lifecycle_hash_differs_on_scope_change(self):
        lh1 = lifecycle_hash("ec", "UNRESTRICTED", "retain-7-years", "", "v1")
        lh2 = lifecycle_hash("ec", "RESTRICTED", "retain-7-years", "", "v1")
        self.assertNotEqual(lh1, lh2)


class TestNegativeProof(unittest.TestCase):

    SCHEMA = "aiep.np.v1"

    def test_record_creation(self):
        rec = create_negative_proof_record("SENSOR_READING", "2026-01-01T00:00:00Z",
                                            "2026-01-02T00:00:00Z", self.SCHEMA)
        self.assertIn("negative_proof_hash", rec)
        self.assertRegex(rec["negative_proof_hash"], r'^[a-f0-9]{64}$')

    def test_record_verification_passes(self):
        rec = create_negative_proof_record("SENSOR_READING", "2026-01-01T00:00:00Z",
                                            "2026-01-02T00:00:00Z", self.SCHEMA)
        self.assertTrue(verify_negative_proof_record(rec, self.SCHEMA))

    def test_record_verification_fails_on_tamper(self):
        rec = create_negative_proof_record("SENSOR_READING", "2026-01-01T00:00:00Z",
                                            "2026-01-02T00:00:00Z", self.SCHEMA)
        rec["negative_proof_hash"] = "a" * 64
        self.assertFalse(verify_negative_proof_record(rec, self.SCHEMA))


class TestInvariantGate(unittest.TestCase):

    def _make_ec(self, data: dict, prov: str) -> str:
        return evidence_commitment(canonical_json(data), prov, "test-schema-v1")

    def test_gate_open_for_known_evidence(self):
        ec = self._make_ec({"v": 1}, "p")
        ledger = {ec: {"evidence_commitment": ec}}
        gate = evaluate_gate(ec, ledger, [], set())
        self.assertEqual(gate.status, "OPEN")
        self.assertTrue(gate.is_open)

    def test_gate_closed_for_unknown_evidence(self):
        gate = evaluate_gate("a" * 64, {}, [], set())
        self.assertEqual(gate.status, "CLOSED")
        self.assertFalse(gate.is_open)
        self.assertTrue(any("I1" in v for v in gate.violations))

    def test_i2_duplicate_entry_hash(self):
        ec = self._make_ec({"v": 1}, "p")
        ledger = {ec: {}}
        reasoning = [
            {"entry_hash": "abc123", "evidence_refs": [], "kind": "ACTIVATION"},
            {"entry_hash": "abc123", "evidence_refs": [], "kind": "ACTIVATION"},
        ]
        gate = evaluate_gate(ec, ledger, reasoning, set())
        self.assertFalse(gate.is_open)
        self.assertTrue(any("I2" in v for v in gate.violations))

    def test_i4_evidence_ref_not_in_ledger(self):
        ec = self._make_ec({"v": 1}, "p")
        ledger = {ec: {}}
        reasoning = [{"entry_hash": "xyz", "evidence_refs": ["missing_hash"], "kind": "REASONING"}]
        gate = evaluate_gate(ec, ledger, reasoning, set())
        self.assertFalse(gate.is_open)
        self.assertTrue(any("I4" in v for v in gate.violations))

    def test_i5_frontier_exceeded(self):
        ec = self._make_ec({"v": 1}, "p")
        ledger = {ec: {}}
        too_many = {f"branch-{i}" for i in range(MAX_ACTIVE_FRONTIER + 1)}
        gate = evaluate_gate(ec, ledger, [], too_many)
        self.assertFalse(gate.is_open)
        self.assertTrue(any("I5" in v for v in gate.violations))

    def test_gate_result_has_all_invariants_checked(self):
        gate = evaluate_gate("x" * 64, {}, [], set())
        self.assertListEqual(gate.invariants_checked, ["I1", "I2", "I3", "I4", "I5", "I6"])


class TestArbitration(unittest.TestCase):

    def test_admissible_conclusion(self):
        ok, reason = evaluate_admissibility("plausible", "accept", "OPEN")
        self.assertTrue(ok)
        self.assertEqual(reason, "ADMISSIBLE")

    def test_inadmissible_closed_gate(self):
        ok, reason = evaluate_admissibility("plausible", "accept", "CLOSED")
        self.assertFalse(ok)
        self.assertIn("CC-005", reason)

    def test_inadmissible_implausible(self):
        ok, reason = evaluate_admissibility("implausible", "accept", "OPEN")
        self.assertFalse(ok)
        self.assertIn("CC-001", reason)

    def test_inadmissible_unresolved_dissent(self):
        ok, reason = evaluate_admissibility("plausible", "reject", "OPEN")
        self.assertFalse(ok)
        self.assertIn("CC-004", reason)

    def test_arbitration_hash_deterministic(self):
        h1 = arbitration_hash("b1", "c1", True, "plausible", "schema-v1")
        h2 = arbitration_hash("b1", "c1", True, "plausible", "schema-v1")
        self.assertEqual(h1, h2)

    def test_constitutional_constraints_present(self):
        for cc in ("CC-001", "CC-002", "CC-003", "CC-004", "CC-005"):
            self.assertIn(cc, CONSTITUTIONAL_CONSTRAINTS)


class TestPackHash(unittest.TestCase):

    def test_deterministic(self):
        ev = [{"ecv": "abc123"}]
        re_ = [{"entry_hash": "xyz"}]
        h1 = pack_hash(ev, re_, "v1")
        h2 = pack_hash(ev, re_, "v1")
        self.assertEqual(h1, h2)

    def test_different_on_evidence_change(self):
        ev1 = [{"ecv": "abc"}]
        ev2 = [{"ecv": "def"}]
        self.assertNotEqual(pack_hash(ev1, [], "v1"), pack_hash(ev2, [], "v1"))


class TestSelfTest(unittest.TestCase):

    def test_kernel_self_test_passes(self):
        self.assertTrue(run_self_test())

    def test_kernel_version_is_frozen(self):
        self.assertEqual(KERNEL_VERSION, "1.0.1")

    def test_active_algorithm_is_sha256(self):
        self.assertEqual(ACTIVE_ALGORITHM, "sha-256")

    def test_digest_pattern_matches_known_hash(self):
        self.assertRegex(sha256_hex(""), DIGEST_PATTERN)


if __name__ == "__main__":
    unittest.main()
