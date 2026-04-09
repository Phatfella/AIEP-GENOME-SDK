# AIEP Complete Record — Worked Example

A self-contained walkthrough of a single AIEP decision cycle using the
`aiep-genome-sdk` kernel. Every hash below is computed by running
`python examples/complete_record/build.py` — you can verify any of them
with `aiep-verify` or by reading the source.

---

## Scenario

A temperature sensor reads **72.4 °C**. The system activates a cooling
response. The decision is recorded, committed, and is permanently
machine-verifiable.

---

## 1 — Evidence Record

```json
{
  "evidence_id":   "00000000-0000-0000-0000-000000000001",
  "evidence_type": "structured_data",
  "content":       "temperature_celsius=72.4",
  "collected_ts":  "2026-01-01T00:00:00Z"
}
```

---

## 2 — Reasoning Entry

```json
{
  "entry_hash":    "727ccdd0e91a3783e4a32f920d57619100be76ada97c38a6f879ca85673f4c65",
  "kind":          "ACTIVATION",
  "reasoning":     "Temperature within safe operating range. No alert required.",
  "branch_id":     "branch-001",
  "evidence_refs": ["00000000-0000-0000-0000-000000000001"]
}
```

`entry_hash` is `sha256_hex("entry-example-001")` — a stable identifier for
this reasoning entry.

---

## 3 — Pack Hash (the core commitment)

`pack_hash(evidence_ledger, reasoning_ledger, schema_version_id)`

```
a03f690109af14d6d70b6eac7e600e2a030ebac3558481e9ecd345b566827075
```

This is the tamper-evident commitment to the complete decision. If any byte
of the evidence or reasoning changes, this hash changes. Two nodes that
independently receive the same evidence and produce the same reasoning
**must** agree on this value.

---

## 4 — Evidence Commitment

`evidence_commitment(canonical_evidence, provenance, schema_version_id)`

```
3a64b676a3fcf24b0c07e0e76147bc7303eba5ceac96b238b6ac048bb0183e7a
```

A commitment to the evidence alone, independent of the reasoning. Useful
for cross-referencing evidence across multiple decisions.

---

## 5 — Negative Proof (gap record)

During 01:00–02:00 UTC, no telemetry was received. The absence is recorded
as a `negative_proof_hash`:

`negative_proof_hash("telemetry_reading", "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z", sv)`

```
9c403f333a7dc45636074827ec52211ebb560f0c4ef7cefb1da68c30ea087bd1
```

An absence that is recorded is not suppressed evidence — it is evidence of
absence. A gap without a NegativeProofRecord is a protocol violation.

---

## 6 — Dissent (P27)

A second branch (`branch-002`) reviews the same evidence and disagrees.
The dissent position is itself tamper-evident:

| Position  | dissent_hash |
|-----------|-------------|
| `reject`  | `841843ebd96db55a08d2677a012777732e3452e9b0178057c65207e587e7962b` |
| `archive` | `4df2260cd54e9f2cc30deb78c880bc2265497a825047e8e302bf36f79a7bf67e` |

Changing `"reject"` to `"archive"` produces a different hash. The position
cannot be silently changed after commitment.

---

## 7 — Context Reconstruction (P22)

`context_reconstruction_hash([pack_hash, negative_proof_hash], "sorted-asc", sv)`

```
a848defef1e9dea0f8a4f082e8bc80640147be1db1eda143641cfe683f05d549
```

Any node given the same set of artefact hashes (in any order) produces the
same context reconstruction hash. Context cannot be selectively excluded.

---

## 8 — Consensus Record (P90)

`consensus_record_hash("branch-001", "HIGH", [pack_hash, negative_proof_hash], sv)`

```
684bc397afb13583b7292db5a132cf26c8a40f9a7c8910b0fac6443d1799fbc4
```

The swarm's consensus commitment. Order-independent: nodes that respond in
different sequence produce the same hash.

---

## Running the example

```bash
cd examples/complete_record
python build.py
```

All hashes are recomputed from scratch and printed. Compare with the values
above — they must match exactly, on any machine, any OS, any Python version
≥ 3.10.

```bash
# Also verify the AIEP-VECTORS suite:
aiep-verify --self-test
aiep-verify --vectors path/to/AIEP-VECTORS/v1.1.0
```
