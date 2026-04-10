# Minimal AIEP-Compliant Service

A minimal Python service that demonstrates the complete AIEP decision record cycle:

1. Collect evidence (URL fetch or text input)
2. Hash and commit the evidence
3. Produce a `pack_hash`-signed decision record
4. The record is verifiable by any third party with `aiep-genome-sdk`

This is the starting point for any new AIEP implementation. Copy it, adapt the evidence collection to your domain, and run the conformance suite to verify your implementation is correct.

## Files

| File | Purpose |
|---|---|
| `service.py` | Core service — `collect_evidence()` → `make_decision()` → `decision_record()` |
| `run_demo.py` | Demo: produces two records and verifies them |
| `demo-record.json` | Sample output record |

## Run

```bash
pip install aiep-genome-sdk requests

python run_demo.py
```

Expected output:

```
[1] Collecting evidence...
    evidence_id : e1
    content_len : 312 chars
    collected_ts: 2026-04-10T10:00:00Z

[2] Producing decision record...
    pack_hash   : a3f2...1c9d
    plausibility: plausible
    gate_status : OPEN
    verdict     : admissible

[3] Verifying record...
    aiep-verify decision-record.json
    → record valid

[4] Written to demo-record.json

AIEP decision record complete. Share demo-record.json — any third party
can verify it with: aiep-verify demo-record.json
```

## What this demonstrates

- **Evidence commitment**: content is stored verbatim, not by URL. If the source disappears, the `pack_hash` still verifies.
- **Determinism**: run `run_demo.py` twice — same `pack_hash` if same inputs.
- **Third-party verifiability**: no model weights, no private keys. The hash is the proof.
- **Negative proof**: if evidence collection fails, `make_decision()` produces a `NegativeProofRecord` rather than hallucinating.

## Adapting to your domain

1. Replace `collect_evidence()` with your evidence source (API call, database query, sensor reading)
2. Replace `make_decision()` with your reasoning logic — keep the structure, change the content
3. Add your `ReasoningLedgerEntry` items for each reasoning step
4. Run `aiep-verify --vectors AIEP-VECTORS/vectors/v1.0.0/` to confirm your kernel is conformant
5. Add `CONFORMANCE.md` to your repo

## Constitutional constraints

The service enforces CC-001–CC-005 via `aiep-validator`. A record is only committed if:

- CC-001: `plausibility_status` is `"plausible"` (not speculative or implausible)
- CC-002: `evidence_ledger` is non-empty
- CC-003: no unresolved dissent (`dissent_final_position` is None or `"accept"`)
- CC-004: stored `pack_hash` matches recomputed hash (tamper detection)
- CC-005: `gate_status` is `"OPEN"`

If any constraint is violated, the service raises `AiepConstraintError` and logs the violation. The violation is hash-committed to the monitor audit log — suppression is detectable.
