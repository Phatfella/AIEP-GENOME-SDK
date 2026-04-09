# Contributing to AIEP

Thank you for your interest in the Architected Instruction and Evidence Protocol.
All contributions must comply with the AIEP GENOME kernel invariants and the
canonical hash scheme (FC v1.0.0, Schema v2.0.0).

## Getting Started

```bash
git clone <repo-url>
pip install -e ".[dev]"
pytest tests/ -v
```

## Contribution Guidelines

### Code Standards
- All deterministic functions must be **pure** — no side effects, no I/O.
- Every new hash computation **must** be tested with a known replay vector.
- Public API additions require a corresponding test case that verifies the AIEP
  canon rules R1–R8 are satisfied.
- Zero external runtime dependencies. `stdlib` only.

### Commit Conventions
```
feat: short description (max 72 chars)
fix:  short description
test: short description
docs: short description
```

Reference the relevant patent number in the commit body, e.g.:

```
feat: add ReactivationThreshold crossing detection

Implements §[0033] of P94 — Anticipatory Branch Surfacing.
```

### Pull Requests
1. Fork the repository and create a topic branch.
2. Ensure `pytest tests/ -v` passes with zero failures.
3. Regenerate `SHA256SUMS.txt` using the repo's regeneration script.
4. Open a pull request against `main` with a clear description.

### Filing Issues
- Bug reports: include a minimal reproducible test case.
- Feature requests: reference the AIEP specification section (§[XXXX]) that
  motivates the change.

## Governance
All implementations are governed by the AIEP GENOME kernel.  
LOCKFILE_VERSION: 1.0.0 | FC: v1.0.0 | Schema: v2.0.0.

SPDX-License-Identifier: Apache-2.0  
© 2025–2026 Neil Grassby. All rights reserved.
