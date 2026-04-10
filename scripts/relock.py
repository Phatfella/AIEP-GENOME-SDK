#!/usr/bin/env python3
"""
AIEP GENOME SDK — Atomic Kernel Relock (BRANCH-GENOME-003)

Recomputes SHA-256 hashes for all kernel files, updates GENOME_LOCKFILE.json
with the new per-file hashes and kernel_bundle_hash, then regenerates
SHA256SUMS.txt — all in one atomic operation.

This script MUST be run after any kernel file modification, before committing.

Usage (from genome-sdk root, venv active):
    python scripts/relock.py [--dry-run]

Flags:
    --dry-run   Compute and display new hashes without writing anything.

Bundle hash convention:
    kernel_bundle_hash = sha256( concat of sorted kernel file hex digests )
    Sort order: lexicographic by relative file path (UTF-8 bytes).
    This is a deterministic summary of the kernel — any file change
    produces a new bundle hash, detectable by all downstream pinners.

After running:
    1. Review the diff in GENOME_LOCKFILE.json
    2. Bump LOCKFILE_VERSION (and SDK_VERSION if appropriate)
    3. Run: pytest (must be 100% green before committing)
    4. Commit: git add GENOME_LOCKFILE.json SHA256SUMS.txt; git commit -m "..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
LOCKFILE_PATH = ROOT / "GENOME_LOCKFILE.json"

# Kernel files tracked in layer_0_locks.kernel_files, in canonical sort order.
# MUST match the keys in GENOME_LOCKFILE.json exactly.
KERNEL_FILES = sorted([
    "kernel/arbitration/arbitration.py",
    "kernel/canon/canon.py",
    "kernel/hashing/algorithms.py",
    "kernel/negative_proof/negative_proof.py",
    "kernel/validation/invariants.py",
])


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def compute_bundle_hash(file_hashes: dict[str, str]) -> str:
    """
    Bundle hash = SHA-256 over the sorted-by-path concatenation of hex digests.
    Empty separator ensures the concatenation is unambiguous given fixed 64-char hex.
    """
    sorted_hashes = "".join(file_hashes[f] for f in sorted(file_hashes))
    return hashlib.sha256(sorted_hashes.encode("ascii")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Atomic GENOME kernel relock")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    # 1. Verify all kernel files exist
    missing = [f for f in KERNEL_FILES if not (ROOT / f).exists()]
    if missing:
        print("ERROR: Missing kernel files:")
        for f in missing:
            print(f"  {f}")
        return 1

    # 2. Compute new per-file hashes
    new_file_hashes = {f: sha256_file(ROOT / f) for f in KERNEL_FILES}
    new_bundle_hash = compute_bundle_hash(new_file_hashes)

    # 3. Load existing LOCKFILE
    lockfile = json.loads(LOCKFILE_PATH.read_text(encoding="utf-8"))
    layer0 = lockfile["layer_0_locks"]
    old_bundle_hash = layer0.get("kernel_bundle_hash", "<none>")
    old_file_hashes = layer0.get("kernel_files", {})

    # 4. Report changes
    changed = False
    for f in KERNEL_FILES:
        old = old_file_hashes.get(f, "<new>")
        new = new_file_hashes[f]
        status = "  CHANGED" if old != new else "  ok     "
        if old != new:
            changed = True
        print(f"{status}  {f}")
        if old != new:
            print(f"           old: {old}")
            print(f"           new: {new}")

    bundle_changed = old_bundle_hash != new_bundle_hash
    if bundle_changed:
        changed = True
    print()
    print(f"kernel_bundle_hash:")
    print(f"  old: {old_bundle_hash}")
    print(f"  new: {new_bundle_hash}")
    print(f"  {'CHANGED' if bundle_changed else 'no change'}")

    if not changed:
        print("\nAll hashes match — no relock needed.")
        return 0

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return 0

    # 5. Write new hashes into LOCKFILE (layer_0_locks section)
    layer0["kernel_files"] = new_file_hashes
    layer0["kernel_bundle_hash"] = new_bundle_hash

    LOCKFILE_PATH.write_text(
        json.dumps(lockfile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote new hashes to {LOCKFILE_PATH.name}")

    # 6. Regenerate SHA256SUMS.txt
    sha256sums_script = ROOT / "scripts" / "update_sha256sums.py"
    if sha256sums_script.exists():
        result = subprocess.run(
            [sys.executable, str(sha256sums_script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print("WARNING: update_sha256sums.py returned non-zero:", result.stderr)
    else:
        print("WARNING: scripts/update_sha256sums.py not found — SHA256SUMS.txt not updated")

    print()
    print("Next steps:")
    print("  1. Bump LOCKFILE_VERSION in GENOME_LOCKFILE.json")
    print("  2. Run: pytest (must be 100% green)")
    print("  3. Commit: git add GENOME_LOCKFILE.json SHA256SUMS.txt ; git commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
