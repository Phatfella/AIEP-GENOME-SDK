# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Yes    |
| < 1.0   | ❌ No     |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security concerns to:  
📧 **security@aiep.protocol** (monitored — response within 72 hours)

Include in your report:
- A description of the vulnerability and its potential impact
- Steps to reproduce or proof-of-concept code
- The affected version(s) and component(s)

## Security Design Principles

AIEP implementations follow a **fail-closed security model**:

1. **Hash integrity** — All reasoning artefacts are bound by SHA-256 hash chains
   (FC v1.0.0). Any tampering causes immediate execution suppression.

2. **Append-only substrate** — Evidence and Reasoning Ledgers are structurally
   immutable. No delete or update operations exist in the API.

3. **Deterministic replay** — Outputs are independently verifiable from stored
   ledger entries without access to runtime internals.

4. **Zero external dependencies** — Reduces supply-chain attack surface.
   All AIEP packages use `stdlib` only at runtime.

5. **Secrecy Layer (P05/GB2519802.9)** — Cryptographic access controls for
   classified substrates are governed by the AIEP Secrecy Layer spec.

## Scope

This policy applies to all Python and TypeScript packages in the AIEP monorepo:

- `aiep-*` Python packages (FC v1.0.0 kernel)
- `aiep-hub-validator` TypeScript package
- `AIEP-GENOME-SDK` reference implementation

Out of scope: the AIEP patent specification documents (`.md` files) — these
are legal/technical documents, not executable software.

SPDX-License-Identifier: Apache-2.0  
© 2025–2026 Neil Grassby. All rights reserved.
