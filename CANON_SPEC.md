# AIEP Canon Specification

**Version:** 1.0.0
**Status:** LOCKED — no changes without incrementing KERNEL_VERSION
**Locked at:** 2026-02-27T00:00:00Z
**Kernel file:** `kernel/canon/canon.py`
**Kernel SHA-256:** `b667eee64b001c6ca0447817f51c8c932361271d23376ed735ddfc9c8b68db6f`

Any deviation from these rules in any implementation is a bug, not a variant.
There are no variants. There is only the canon.

---

## R1 — Key Ordering

JSON object keys MUST be sorted by lexicographic UTF-8 byte order after NFC normalisation.
This is equivalent to Python `json.dumps(sort_keys=True)` on NFC-normalised strings.

**Known vector:**
```
canonical_json({"z": 1, "a": 2})  →  {"a":2,"z":1}
```

---

## R2 — No Whitespace

JSON output MUST use compact separators: `,` between items, `:` between key/value pairs.
No spaces. No newlines. No indentation.

**Known vector:**
```
canonical_json({"k": "v"})  →  {"k":"v"}
```

---

## R3 — Unicode NFC Normalisation

ALL strings (keys and values, recursively) MUST be NFC-normalised before hashing or serialisation.

Precomposed `\u00c5` (Å, NFC) and decomposed `A\u030a` (A + combining ring above, NFD)
MUST produce identical canonical output.

**Known vector:**
```
canonical_json({"n": "\u00c5"})  ==  canonical_json({"n": "A\u030a"})
Both produce: {"n":"Å"}
```

---

## R4 — SHA-256, Lowercase Hex

**Algorithm:** SHA-256
**Output encoding:** Lowercase hexadecimal, exactly 64 characters
**Input encoding:** UTF-8

**Known vectors (independently verifiable):**
```
sha256_hex("")     →  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
sha256_hex("AIEP") →  13f3f3d9594fca34661784a66ff206699284ac5c3ebb048b5654eb05f289ec7e
```

Verification: `echo -n "AIEP" | sha256sum` should produce the same value on any Unix system.

---

## R5 — Number Normalisation

Numbers MUST be serialised with:
- No scientific notation
- Trailing zeros trimmed
- Minus-zero is FORBIDDEN (raises `ValueError`)

```
1.0   →  "1"
1.50  →  "1.5"
-0.0  →  ERROR: AIEP-CANON-R5: minus-zero is forbidden
```

---

## R6 — UTF-8 Unicode Literals (No Escaping)

Unicode characters MUST appear as literal UTF-8 in canonical output.
They MUST NOT be escaped as `\uXXXX`.

This is equivalent to Python `json.dumps(ensure_ascii=False)`.

**Known vector:**
```
canonical_json({"k": "\u00e9"})  →  {"k":"é"}   (NOT {"k":"\u00e9"})
```

---

## R7 — Length-Prefixed Concatenation (`concat_hash`)

When hashing multiple fields together, EACH field MUST be prefixed by its UTF-8 byte length
as an **8-byte big-endian** unsigned integer before concatenation.

```
payload = b""
for field in fields:
    encoded = NFC(field).encode("utf-8")
    payload += len(encoded).to_bytes(8, "big") + encoded
result = sha256(payload).hexdigest()
```

**Boundary safety — all three MUST hold:**
```
concat_hash("ab", "c")  !=  concat_hash("a", "bc")   # prevents boundary collision
concat_hash("", "x")    !=  concat_hash("x", "")     # empty field not transparent
concat_hash("abc")      !=  sha256_hex("abc")         # single-field differs from bare hash
```

---

## R8 — `pack_hash` (Deterministic Replay)

The replay hash commits to the full decision state.
`generated_ts` is **deliberately excluded** — timestamps MUST NOT affect determinism.

```python
state = {
    "evidence_ledger":  <list>,
    "reasoning_ledger": <list>,
    "schema_version_id": <string>
}
pack_hash = sha256_hex(canonical_json(state))
```

Rules applied: R1 (key sort), R2 (no whitespace), R3 (NFC), R4 (SHA-256), R6 (UTF-8 literals).

---

## Commitment Functions

Derived from R1–R8. All inputs are NFC-normalised before processing.

| Function | Formula |
|---|---|
| `evidence_commitment(e, p, s)` | `concat_hash(e, p, s)` |
| `negative_proof_hash(type, start, end, schema)` | `concat_hash(type, start, end, schema)` |
| `lifecycle_hash(ec, scope, policy, expiry, schema)` | `concat_hash(ec, scope, policy, expiry_or_NONE, schema)` |
| `arbitration_hash(branch, conclusion, dissent_resolved, plausibility, schema)` | `concat_hash(branch, conclusion, str(dissent_resolved), plausibility, schema)` |
| `pack_hash(el, rl, schema)` | `sha256_hex(canonical_json({evidence_ledger:el, reasoning_ledger:rl, schema_version_id:schema}))` |

---

## What This Specification Does NOT Cover

- The accuracy or completeness of evidence content
- The behaviour of the underlying AI model or inference engine
- Network transport, storage format, or API design
- Anything above Layer 0 in the AIEP Flexibility Contract
- Cross-version compatibility (different `LOCKFILE_VERSION` → different hash space)

---

## Verification

To verify your implementation matches this specification:

```bash
pip install aiep-genome-sdk
aiep-verify --self-test
```

The `--self-test` flag runs R1–R7 checks against known vectors from this document.
If all pass, your `aiep-verify` binary is canon-compliant.
