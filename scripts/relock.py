#!/usr/bin/env python3
"""
AIEP GENOME SDK — Atomic Kernel Relock (BRANCH-GENOME-003)

Recomputes SHA-256 hashes for all kernel files, then updates ALL lock
artefacts in a single atomic pass:

  1. GENOME_LOCKFILE.json  — kernel_files hashes + kernel_bundle_hash
  2. CANON_SPEC.md         — Authority BlobSha + Kernel version + LOCKFILE version
  3. scripts/generate_vectors.py  — KERNEL_VERSION, LOCKFILE_VERSION,
                                    CANON_SPEC_VERSION, CANON_BLOBSHA constants
  4. SHA256SUMS.txt        — regenerated via update_sha256sums.py

This script MUST be run after any kernel file modification, before committing.

Usage (from genome-sdk root, venv active):
    python scripts/relock.py [--dry-run]

Flags:
    --dry-run   Compute and display new hashes without writing anything.

Bundle hash convention:
    kernel_bundle_hash = sha256( sorted concat of individual kernel file hex digests )
    Sort order: lexicographic by relative file path (UTF-8 bytes).

After running:
    1. Review the diff in GENOME_LOCKFILE.json and CANON_SPEC.md
    2. Bump LOCKFILE_VERSION in GENOME_LOCKFILE.json
    3. Run: pytest (must be 100% green before committing)
    4. Commit: git add GENOME_LOCKFILE.json CANON_SPEC.md SHA256SUMS.txt scripts/ ; git commit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
LOCKFILE_PATH = ROOT / "GENOME_LOCKFILE.json"
CANON_SPEC_PATH = ROOT / "CANON_SPEC.md"
GEN_VECTORS_PATH = ROOT / "scripts" / "generate_vectors.py"

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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: pathlib.Path) -> str:
    """Compute git blob SHA-1 for a file (matches `git hash-object <file>`)."""
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    import hashlib as hl
    return hl.sha1(header + data).hexdigest()


def compute_bundle_hash(file_hashes: dict[str, str]) -> str:
    """
    Bundle hash = SHA-256 over the sorted-by-path concatenation of hex digests.
    """
    sorted_hashes = "".join(file_hashes[f] for f in sorted(file_hashes))
    return hashlib.sha256(sorted_hashes.encode("ascii")).hexdigest()


def update_canon_spec(canon_blobsha: str, kernel_version: str, lockfile_version: str, dry_run: bool) -> None:
    text = CANON_SPEC_PATH.read_text(encoding="utf-8")
    orig = text
    text = re.sub(
        r"(\*\*Canon Spec Version:\*\* )\S+",
        lambda m: m.group(1) + lockfile_version,
        text,
    )
    text = re.sub(
        r"(\*\*Authority BlobSha:\*\* )`[0-9a-f]{40}`",
        lambda m: m.group(1) + f"`{canon_blobsha}`",
        text,
    )
    text = re.sub(
        r"(\*\*Kernel version:\*\* )\S+",
        lambda m: m.group(1) + kernel_version,
        text,
    )
    text = re.sub(
        r"(\*\*LOCKFILE version:\*\* )\S+",
        lambda m: m.group(1) + lockfile_version,
        text,
    )
    text = re.sub(
        r"(locked at LOCKFILE_VERSION )\S+",
        lambda m: m.group(1) + lockfile_version,
        text,
    )
    changed = text != orig
    if changed and not dry_run:
        CANON_SPEC_PATH.write_text(text, encoding="utf-8")
    return changed


def update_generate_vectors(canon_blobsha: str, kernel_version: str, lockfile_version: str, dry_run: bool) -> bool:
    """Update version constants in scripts/generate_vectors.py."""
    if not GEN_VECTORS_PATH.exists():
        print(f"WARNING: {GEN_VECTORS_PATH} not found — skipping")
        return False
    text = GEN_VECTORS_PATH.read_text(encoding="utf-8")
    orig = text
    text = re.sub(r'(KERNEL_VERSION\s*=\s*)"[^"]+"', f'\\1"{kernel_version}"', text)
    text = re.sub(r'(LOCKFILE_VERSION\s*=\s*)"[^"]+"', f'\\1"{lockfile_version}"', text)
    text = re.sub(r'(CANON_SPEC_VERSION\s*=\s*)"[^"]+"', f'\\1"{lockfile_version}"', text)
    text = re.sub(r'(CANON_BLOBSHA\s*=\s*)"[0-9a-f]{40}"', f'\\1"{canon_blobsha}"', text)
    changed = text != orig
    if changed and not dry_run:
        GEN_VECTORS_PATH.write_text(text, encoding="utf-8")
    return changed


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

    # 2. Compute new per-file sha256 hashes + git blob SHA of canon.py
    new_file_hashes = {f: sha256_file(ROOT / f) for f in KERNEL_FILES}
    new_bundle_hash = compute_bundle_hash(new_file_hashes)
    new_canon_blobsha = git_blob_sha(ROOT / "kernel/canon/canon.py")

    # 3. Load LOCKFILE for comparison
    lockfile = json.loads(LOCKFILE_PATH.read_text(encoding="utf-8"))
    layer0 = lockfile["layer_0_locks"]
    old_bundle_hash = layer0.get("kernel_bundle_hash", "<none>")
    old_file_hashes = layer0.get("kernel_files", {})
    current_lockfile_version = lockfile.get("LOCKFILE_VERSION", "?")
    current_kernel_version = layer0.get("deterministic_engine", {}).get("version", "?")

    # 4. Report per-file changes
    any_changed = False
    for f in KERNEL_FILES:
        old = old_file_hashes.get(f, "<new>")
        new = new_file_hashes[f]
        status = "  CHANGED" if old != new else "  ok     "
        if old != new:
            any_changed = True
        print(f"{status}  {f}")
        if old != new:
            print(f"           old: {old}")
            print(f"           new: {new}")

    bundle_changed = old_bundle_hash != new_bundle_hash
    if bundle_changed:
        any_changed = True
    print()
    print(f"kernel_bundle_hash:")
    print(f"  old: {old_bundle_hash}")
    print(f"  new: {new_bundle_hash}")
    print(f"  {'CHANGED' if bundle_changed else 'no change'}")
    print(f"\ncanon.py git BlobSha (for CANON_SPEC.md): {new_canon_blobsha}")

    if not any_changed:
        print("\nAll hashes match — no relock needed.")
        return 0

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return 0

    # 5. Write new hashes into LOCKFILE
    layer0["kernel_files"] = new_file_hashes
    layer0["kernel_bundle_hash"] = new_bundle_hash
    LOCKFILE_PATH.write_text(
        json.dumps(lockfile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote new hashes to {LOCKFILE_PATH.name}")

    # 6. Update CANON_SPEC.md
    spec_changed = update_canon_spec(new_canon_blobsha, current_kernel_version, current_lockfile_version, dry_run=False)
    print(f"CANON_SPEC.md  {'updated' if spec_changed else 'no change'}")

    # 7. Update generate_vectors.py constants
    gv_changed = update_generate_vectors(new_canon_blobsha, current_kernel_version, current_lockfile_version, dry_run=False)
    print(f"scripts/generate_vectors.py  {'updated' if gv_changed else 'no change'}")

    # 8. Regenerate SHA256SUMS.txt
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
    print("  1. Bump LOCKFILE_VERSION in GENOME_LOCKFILE.json (and CANON_SPEC.md if needed)")
    print("  2. Run: pytest (must be 100% green)")
    print("  3. Commit all changed files atomically")
    return 0


if __name__ == "__main__":
    sys.exit(main())
