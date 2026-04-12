# AIEP Adopters

Organisations and projects that have implemented the AIEP protocol.

---

## Reference Implementations

These are the canonical first-party implementations — each one uses the GENOME kernel directly and carries a `CONFORMANCE.md` verified against AIEP-VECTORS.

| Implementation | Type | What it demonstrates |
|---|---|---|
| **AIEP Miner** | Open source — Apache 2.0 | AIEP applied to ASIC mining fleet control. Every decision, suppression, and action recorded in an append-only evidence ledger. Real hardware. No black box. [→ GitHub](https://github.com/Phatfella/AIEP-MINER) |
| **AIEP Forecast** | Production SaaS | AIEP applied to construction project management. Multi-tenant. AIEP evidence trail on every cost plan, variation, and valuation. British construction industry. |
| **PIEA** | Production SaaS | Full reference implementation of AIEP reasoning. Every query returns a `CertificateHash`, sourced evidence artefacts, and a confidence tier. Negative Proof on absence. Dissent on disagreement. [→ piea.ai](https://piea.ai) |

---

## Add Your Implementation

If you have built something conformant with the AIEP protocol:

1. Run `aiep-verify --self-test` — confirm `AIEP-COMPLIANT v1.0.0`
2. Add `CONFORMANCE.md` to your repo (see [CONFORMANCE.md](CONFORMANCE.md) for the template)
3. Open a pull request adding a row to this file

There is no fee and no approval process. Conformance is self-certified against the VECTORS suite and auditable by anyone.
