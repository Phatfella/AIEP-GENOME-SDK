# AIEP Protocol — Governance

This document describes how the AIEP protocol specification is governed, how changes are made,
and what the relationship is between the open specification and the underlying patent applications.

---

## Protocol Architect

**Neil Ballantyne** — UKIPO filing author, Protocol Architect.

Neil Ballantyne is the originating filer of all AIEP patent applications and the author of
the open AIEP specification. The Protocol Architect role is the current change authority for
the specification. This document describes the process by which that authority operates.

Contact: via [aiep.protocol](https://aiep.protocol) or the [AIEP Hub contact page](https://aiep.protocol/contact).

---

## What the specification covers

The open specification consists of:

| Document | Authority |
|---|---|
| `CANON_SPEC.md` | Canonical hash rules R1–R8. Language-agnostic. This is the implementable spec. |
| `GENOME_LOCKFILE.json` | Version-pinned trust root. Changing this is a breaking change. |
| `AIEP-VECTORS` (repository) | Test vectors. Conformance is defined by these vectors, not prose descriptions. |

These three documents together define what it means to be `AIEP-COMPLIANT vX.Y.Z`.
Any system that passes the AIEP-VECTORS conformance suite is conformant regardless of
implementation language, operating environment, or commercial relationship.

---

## How the specification changes

### Patch changes (e.g. v1.0.0 → v1.0.1)

Corrections to documentation, typo fixes, clarifications that do not change any hash value.
No new vectors. No change to `GENOME_LOCKFILE.json`.

Made by Protocol Architect directly. No RFC required.

### Minor changes (e.g. v1.0.0 → v1.1.0)

New kernel primitives, new vector suites, new `schema_version_id` values, new `CONFORMANCE.md`
content. Existing vectors must still pass. `pack_hash` for existing records is unaffected.

**Process:**
1. Open a GitHub Discussion in this repository with title `RFC: <description>`
2. Minimum 14-day comment period
3. Protocol Architect reviews feedback and makes a ratification decision
4. If ratified: new vectors added to AIEP-VECTORS, `LOCKFILE_VERSION` bumped, `CHANGELOG.md` updated
5. Announcement via the AIEP Hub

### Major changes (e.g. v1.0.0 → v2.0.0)

Changes that alter the hash output for existing records, change the canonical form (R1–R8),
or change `LOCKFILE_VERSION` in a way that breaks backward compatibility.

**Process:**
1. RFC (as above) with explicit statement that this is a BREAKING CHANGE
2. Minimum 30-day comment period
3. Protocol Architect publishes a formal ratification decision with reasoning
4. Old conformance vectors remain in AIEP-VECTORS under their original tag
5. Systems using the previous version remain conformant to the previous version —
   they are not required to upgrade
6. `GENOME_LOCKFILE.json` updated with new entry; old entry remains

---

## The patent relationship

AIEP patent applications (UKIPO, ~128 applications filed as of April 2026) describe the
inventive concepts underlying the protocol architecture.

The relationship is as follows:

| Layer | Document | Status |
|---|---|---|
| Inventive concepts | UKIPO patent applications | Filed; subject to prosecution |
| Open specification | `CANON_SPEC.md`, `AIEP-VECTORS` | Open, Apache 2.0, freely implementable |
| Commercial products | Forecast, PIEA, Qardl | Proprietary; separate licensing |

**The open specification is always freely implementable regardless of patent prosecution outcome.**
The Apache 2.0 license covers the open specification and reference implementation.
Patent prosecution covers the inventive concepts, not the right to implement the open spec.

The `GENOME_CONSTITUTION_HASH` (published at `/.well-known/aiep/genome_constitution.json`)
is a cryptographic commitment to the specification state at a point in time. It cannot be
retroactively altered.

---

## Lock version discipline

`GENOME_LOCKFILE.json` is the trust root for all AIEP deployments.

- Every entry in the lockfile includes a content hash and a timestamp
- No entry is ever removed — only new entries are added
- A `LOCKFILE_VERSION` bump always accompanies any change that affects hash output
- Systems that pin a specific `LOCKFILE_VERSION` are guaranteed deterministic `pack_hash` values
  for the lifetime of that version

The lockfile is the mechanism that makes long-term auditability possible. A record produced
in 2026 must be replayable in 2036 using the same lockfile version.

---

## How to propose a change

1. Open a [GitHub Discussion](https://github.com/Phatfella/AIEP-GENOME-SDK/discussions)
   with the `RFC` label
2. Describe: what changes, why, what the impact on existing conformant systems is
3. Optionally provide a reference implementation (test vector + kernel change)
4. The 14-day or 30-day comment period begins from the date of the Discussion post
5. The Protocol Architect will post a ratification decision as a reply to the Discussion

If you are implementing the protocol in a new language and discover an ambiguity in
`CANON_SPEC.md`, open a Discussion with the `spec-clarification` label. Ambiguities
in the spec are treated as patch-level bugs.

---

## What governance does not cover

- The commercial products (Forecast, PIEA, Qardl) — those have separate governance
- Patent prosecution strategy — that is private and not subject to open RFC
- The DID Registry (when it exists) — the registry governance will be published separately
- Ecosystem repo development priorities — governed by the individual repo maintainers

---

## Amendment history

| Date | Version | Change | Type |
|---|---|---|---|
| 2025-09-15 | v1.0.0 | Initial release — R1–R8, 10 core vectors | Major |
| 2026-04-10 | v1.1.0 | +5 kernel primitives (dissent/recall/swarm), 15 vectors, TS cross-conformance | Minor |
| 2026-04-10 | v1.0.0-malformed | +6 malformed-input rejection vectors | Minor |
