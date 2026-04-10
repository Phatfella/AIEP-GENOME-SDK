# AIEP Canon Specification

**Canon Spec Version:** 1.0.1
**Locked at:** 2026-02-27T00:00:00Z
**Authority source:** `kernel/canon/canon.py`
**Authority BlobSha:** `ced9bbaab5c9e34c549a4718e8edf33bf0f7ff4e`
**Kernel version:** 1.0.1
**LOCKFILE version:** 1.0.1

This document is the single language-agnostic authority for all AIEP
canonicalisation and hashing behaviour. The Python kernel implements
these rules. This document defines them.

If there is any discrepancy between this document and the kernel source
at the authority BlobSha above, the kernel source is the reference and
this document should be corrected to match it.

Any implementation in any language that claims AIEP conformance MUST
implement these rules exactly and validate against AIEP-VECTORS v1.0.0
before making that claim.

---

## R1 — Member Name Ordering

JSON object member names MUST be ordered by the lexicographic order
of their NFC-normalised UTF-8 byte sequences.

NFC normalisation is applied to member names before byte comparison.
Byte comparison is unsigned, byte-by-byte, from left to right.

**Verification:** Given `{"z":1,"a":2}`, canonical output MUST be `{"a":2,"z":1}`.

---

## R2 — No Whitespace

Canonical JSON MUST use compact separators:
- `,` between array items and between object members
- `:` between member name and value

No space characters, tab characters, or line terminators are permitted
anywhere in canonical output.

**Verification:** `{"k":"v"}` — no spaces present.

---

## R3 — Unicode NFC Normalisation

All string values — both member names and member values — MUST be
Unicode NFC-normalised before any serialisation or hashing.
NFC normalisation is applied recursively through nested structures.

Precomposed and decomposed representations of the same character
MUST produce identical canonical output after NFC normalisation.

**Verification:**
- Input with precomposed `\u00C5` (Å — NFC)
- Input with decomposed `A\u030A` (A + combining ring above — NFD)
- Both MUST produce identical canonical JSON output.

---

## R4 — Hash Algorithm and Encoding

**Algorithm:** SHA-256
**Output encoding:** Lowercase hexadecimal, exactly 64 characters
**Input encoding for string hashing:** UTF-8

**Known vectors (authoritative):**
```
H("")     → e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
H("AIEP") → 13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e
```

Independent verification: `echo -n "AIEP" | sha256sum` on any Unix system.

---

## R5 — Number Normalisation

Numbers in canonical records MUST be serialised as follows:
- No scientific notation (`1e5` is forbidden; use `100000`)
- No trailing zeros after decimal point (`1.50` → `1.5`, `1.0` → `1`)
- Minus-zero (`-0`, `-0.0`) is FORBIDDEN and MUST raise an error
- Non-finite numbers (NaN, Infinity, -Infinity) are FORBIDDEN and MUST raise an error

---

## R6 — Character Encoding in Output

Unicode characters MUST appear as their literal UTF-8 representation
in canonical JSON output. JSON `\uXXXX` escape sequences for
characters that can be represented in UTF-8 are FORBIDDEN.

**Verification:** A string containing `é` (`\u00E9`) MUST appear
as the literal two-byte UTF-8 sequence `0xC3 0xA9`, not as `\u00e9`.

---

## R7 — Length-Prefixed Concatenation

When computing a hash over multiple string fields, each field MUST be
encoded as follows before concatenation:

```
encoded_field = length_prefix || utf8_bytes
length_prefix = byte_length(utf8_bytes) as 8-byte big-endian unsigned integer
```

The SHA-256 hash is then computed over the concatenation of all encoded fields.
NFC normalisation (R3) is applied to each field before UTF-8 encoding.

**Boundary safety — all three MUST produce different hashes:**
- `H_concat(["ab", "c"])` ≠ `H_concat(["a", "bc"])`
- `H_concat(["", "x"])` ≠ `H_concat(["x", ""])`
- A single-field `H_concat(["abc"])` ≠ `SHA256("abc")`

---

## R8 — pack_hash (Deterministic Replay Commitment)

The pack_hash commits to the complete system state for replay purposes.
`generated_ts` and any other timestamp fields are DELIBERATELY EXCLUDED —
time MUST NOT influence the deterministic commitment.

The pack_hash is computed as:

```
state_object = {
    "evidence_ledger":   <array>,
    "reasoning_ledger":  <array>,
    "schema_version_id": <string>
}
pack_hash = SHA256_hex(canonical_json(state_object))
```

where `canonical_json` applies rules R1–R6 recursively.

---

## Commitment Function Signatures

Derived from R1–R8. All string inputs are NFC-normalised per R3
before use in any hash computation.

| Function | Formula |
|---|---|
| `evidence_commitment(e, p, s)` | `H_concat([e, p, s])` |
| `negative_proof_hash(t, s, e, v)` | `H_concat([t, s, e, v])` |
| `lifecycle_hash(ec, scope, policy, expiry, schema)` | `H_concat([ec, scope, policy, expiry_or_NONE, schema])` |
| `arbitration_hash(b, c, d, p, s)` | `H_concat([b, c, str(d), p, s])` |
| `pack_hash(el, rl, s)` | `SHA256_hex(canonical_json({evidence_ledger:el, reasoning_ledger:rl, schema_version_id:s}))` |

where `H_concat` is the length-prefixed concatenation hash defined in R7.

---

## What This Specification Covers

Rules R1–R8 govern canonical serialisation and hashing only.
They are Layer 0 — non-negotiable and locked at LOCKFILE_VERSION 1.0.1.

## What This Specification Does Not Cover

- Evidence accuracy, completeness, or provenance
- Underlying AI model behaviour or inference correctness
- Network transport, storage format, or API design
- Policy evaluation (Layer 2) or capability selection (Layer 1)
- Cross-version compatibility (different LOCKFILE_VERSION = different hash space)
- Anything above Layer 0 in the AIEP Flexibility Contract

---

## Verification

```bash
pip install aiep-genome-sdk
aiep-verify --self-test
```

`--self-test` verifies rules R1–R7 against the known vectors in this document.
If all pass, the verifier implementation is canon-compliant.
