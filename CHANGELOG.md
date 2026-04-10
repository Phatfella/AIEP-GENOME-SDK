# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
`LOCKFILE_VERSION` changes are noted as breaking (Version Fracture per FC §9).

## [Unreleased]

## [1.0.1] — 2026-04-10

### Fixed
- **R5 float normalisation (BRANCH-GENOME-002 follow-through):** `canonical_json` now correctly
  normalises float values before serialisation. Previously `1.0` was emitted as `1.0`; it is now
  emitted as `1`. This closes the cross-language hash divergence between the Python kernel and
  any TypeScript or JavaScript implementation that applies R5 correctly (e.g. the bundled
  `standalone_verify.py`). Records containing float values produced under v1.0.0 will not verify
  against v1.0.1 — no such records exist because no AIEP-VECTORS fixture contained floats.
- `_nfc_object` replaced by `_norm_object` which applies both R3 (NFC) and R5 (number
  normalisation) in a single recursive pass.
- Non-finite numbers (NaN, Infinity) now raise `ValueError` explicitly rather than propagating
  through `json.dumps`.
- `KERNEL_VERSION` incremented to `1.0.1`. `GENOME_LOCKFILE.json` updated to
  `LOCKFILE_VERSION 1.0.1` with new `kernel_bundle_hash` and `kernel/canon/canon.py` hash.

### Migration
Any record committed with `KERNEL_VERSION 1.0.0` that contains float values in its evidence
or reasoning ledger will produce a different `pack_hash` under v1.0.1. No such records are
known to exist. Records containing only strings and integers are unaffected.

## [1.0.0] — 2026-03-08

### Added
- Initial release implementing R1-R8 (AIEP GENOME SDK - Frozen Kernel)
- Deterministic canonical engine (R1–R8, LOCKFILE 1.0.0)
- Full test suite with 0 external runtime dependencies
- GENOME_LOCKFILE.json, LICENSE (Apache 2.0), SHA256SUMS.txt
