# AIEP GENOME SDK — Version Signals

**Document version:** 1.0.0
**Applies to:** `aiep-genome-sdk` (Python)

---

## Four Version Signals

The AIEP GENOME SDK exposes four independent version signals. Downstream consumers
must understand what each one governs before deciding what to pin.

| Signal | Location | Governs | Pin when… |
|--------|----------|---------|-----------|
| `LOCKFILE_VERSION` | `GENOME_LOCKFILE.json` | Protocol hash space | You need stable `pack_hash` values |
| `SDK_VERSION` (pyproject.toml) | `pyproject.toml` → `version` | Python package releases | You install via pip or pnpm |
| `KERNEL_VERSION` | `GENOME_LOCKFILE.json → layer_0_locks.deterministic_engine.version` | Kernel implementation version | You link against kernel internals |
| `Canon Spec Version` | `CANON_SPEC.md` line 3 | Language-agnostic spec document | You implement AIEP in another language |

### When do they change?

- **`LOCKFILE_VERSION`** increments whenever any field in `layer_0_locks` changes.
  This includes new `number_rules`, new kernel file hashes, or any protocol change.
  A `LOCKFILE_VERSION` change means records produced under the old version will not
  verify correctly under the new version — this is a **hash space fracture**.

- **`SDK_VERSION`** (pyproject.toml) increments on any public release, including
  documentation-only releases, new scripts, or API additions. It is independent of
  the protocol version.

- **`KERNEL_VERSION`** increments whenever `kernel/canon/canon.py` or any other
  kernel file changes content. It must stay in sync with `LOCKFILE_VERSION` — any
  kernel change that affects `pack_hash` requires a `LOCKFILE_VERSION` increment too.

- **`Canon Spec Version`** increments whenever `CANON_SPEC.md` is edited. It must
  also be updated in `CANON_SPEC.md` after any kernel change so that the
  `Authority BlobSha` in that document stays current.

### Current values (v1.0.1 release)

```
LOCKFILE_VERSION    = 1.0.1
SDK_VERSION         = 1.0.0   (pyproject.toml)
KERNEL_VERSION      = 1.0.1
Canon Spec Version  = 1.0.1
```

---

## Atomic Relock Requirement

After any edit to a kernel file, run:

```bash
python scripts/relock.py
```

This script atomically updates `GENOME_LOCKFILE.json`, `CANON_SPEC.md` (BlobSha +
version fields), `scripts/generate_vectors.py` (version constants), and
`SHA256SUMS.txt`. **All five artefacts must be updated in a single commit.**
Committing a kernel change without running `relock.py` will leave the lock
artefacts stale — detectable at startup by `kernel_bundle_hash` verification.

---

## REPLAY_VERSION_MISMATCH

### Definition

A replay error raised when an attempt is made to re-execute the deterministic
commitment function against a record that was committed under a different
`LOCKFILE_VERSION`.

### When it is raised

```
record.lockfile_version ≠ current_system.LOCKFILE_VERSION
AND
replay is attempted on record
```

### Behaviour

- **Fail-closed** — do not attempt replay, do not produce any output
- Produce a `NegativeProofRecord` with:
  - `expected_evidence_type = "REPLAY_BLOCKED"`
  - `gap_window_start = original_record.committed_at`
  - `gap_window_end = replay_attempt_ts`
  - `reason = "REPLAY_VERSION_MISMATCH"`

### Resolution

Replay must use the same `LOCKFILE_VERSION` under which the original record was
committed. This may require running an older kernel version in a sandboxed
environment or accepting that the replay is irrecoverable.

### Kernel error code

```
AIEP-REPLAY-VERSION-MISMATCH
```

### Related protocol rule

`AIEP-REPLAY-001` (FC §8): *Any two systems with identical Evidence Ledger,
Reasoning Ledger, capability set C, policy set P, and `LOCKFILE_VERSION` MUST
produce identical `pack_hash`. If they do not, one or both systems are
non-conformant.*

---

## Cross-language implementation guide

If you implement AIEP in a language other than Python, pin to:
- **`LOCKFILE_VERSION`** for `pack_hash` compatibility
- **`Canon Spec Version`** for rule-level specification compliance
- Run the AIEP-VECTORS suite at the matching version tag

Do not pin to `SDK_VERSION` — that is a Python-specific packaging version.
