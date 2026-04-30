"""
aiep_genome CLI — AIEP GENOME SDK command-line interface

Commands
--------
  init    Scaffold a new AIEP-compliant project from zero
  adopt   Retrofit an existing project to the genome standard
  verify  Check genome compliance of the current directory
  status  Show configuration and compliance state
  --self-test  Run kernel determinism self-test and exit

Quick start — new project
    aiep-genome init --name my-service
    cd my-service
    pip install -e ".[dev]"
    pytest

Quick start — existing project
    cd my-existing-project
    aiep-genome adopt
    pip install aiep-genome-sdk
    pytest tests/test_genome_compliance.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from aiep_genome import __version__, KERNEL_VERSION
from aiep_genome.kernel import run_self_test

CONFIG_FILENAME = ".aiep-genome.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_config(cwd: Path) -> dict | None:
    p = cwd / CONFIG_FILENAME
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


# ── init command ─────────────────────────────────────────────────────────────

def _cmd_init(args) -> int:
    from aiep_genome.scaffold import scaffold_new_project

    dest = Path(args.dest).resolve()
    if not args.name:
        args.name = dest.name if dest.exists() else "my-aiep-project"

    print(f"Scaffolding '{args.name}' with pattern '{args.pattern}' into {dest}/ ...")

    result = scaffold_new_project(
        dest,
        name=args.name,
        version=args.version,
        description=args.description or "",
        pattern=args.pattern,
        force=args.force,
    )

    for f in result.created:
        print(f"  created  {f}")
    for f in result.skipped:
        print(f"  skipped  {f}  (already exists; use --force to overwrite)")

    print()
    print("Next steps")
    print("----------")
    print(f"  cd {dest}")
    print("  pip install -e \".[dev]\"")
    print("  pytest")
    print()
    print(f"AIEP pattern : {args.pattern}")
    print(f"Kernel       : v{KERNEL_VERSION} (frozen)")
    print(f"SDK          : v{__version__}")
    return 0


# ── adopt command ─────────────────────────────────────────────────────────────

def _cmd_adopt(args) -> int:
    from aiep_genome.adopt import adopt_project

    target = Path(args.target).resolve()

    print(f"Adopting genome SDK into {target}/ ...")
    if args.dry_run:
        print("  (dry-run mode — no files written)")

    result = adopt_project(
        target,
        pattern=args.pattern,
        dry_run=args.dry_run,
        force=args.force,
    )

    print()
    print(f"Package  : {result.package_name}")
    print(f"Pattern  : {result.pattern}")
    print(f"Genome   : {result.genome_dir}/")
    print()

    if result.created:
        print("Created:")
        for f in result.created:
            print(f"  + {f}")

    if result.skipped:
        print("Skipped (already exists; use --force to overwrite):")
        for f in result.skipped:
            print(f"  ~ {f}")

    if result.manual_steps:
        print()
        print("Manual steps required:")
        for i, step in enumerate(result.manual_steps, 1):
            print(f"  {i}. {step}")

    if result.warnings:
        print()
        print("Warnings:")
        for w in result.warnings:
            print(f"  ! {w}")

    print()
    if not args.dry_run:
        print("Adoption complete. Run:  pytest tests/test_genome_compliance.py")
    else:
        print("Dry run complete. Re-run without --dry-run to apply changes.")
    return 0


# ── verify command ────────────────────────────────────────────────────────────

def _cmd_verify(args) -> int:
    from aiep_genome.verify import verify_compliance

    target = Path(args.target).resolve()
    result = verify_compliance(target)

    print(f"Verifying genome compliance: {target}")
    print()
    for c in result.checks:
        icon = "OK" if c.passed else "FAIL"
        print(f"  [{icon}] {c.check_id}  {c.message}")

    print()
    print(f"Result: {result.score} checks passed")

    if result.passed:
        print("COMPLIANT — this project meets the AIEP GENOME standard.")
        return 0
    else:
        print("NOT COMPLIANT — address the FAIL items above.")
        for fc in result.failed_checks:
            print(f"  {fc.check_id}: {fc.message}")
        return 1


# ── status command ────────────────────────────────────────────────────────────

def _cmd_status(args) -> int:
    cwd = Path.cwd()
    cfg = _load_config(cwd)

    print(f"aiep-genome v{__version__}  (kernel v{KERNEL_VERSION})")
    print()

    if cfg:
        print(f"Config:  {CONFIG_FILENAME}")
        print(f"  name        : {cfg.get('name', '?')}")
        print(f"  pattern     : {cfg.get('pattern', '?')}")
        print(f"  genome_dir  : {cfg.get('genome_dir', '?')}")
        print(f"  sdk_version : {cfg.get('genome_sdk_version', '?')}")
        print(f"  mode        : {cfg.get('adoption_mode', '?')}")
    else:
        print(f"No {CONFIG_FILENAME} found in {cwd}")
        print()
        print("To scaffold a new project:")
        print("  aiep-genome init --name my-service")
        print()
        print("To retrofit an existing project:")
        print("  aiep-genome adopt")
        return 1

    # Quick compliance summary
    from aiep_genome.verify import verify_compliance
    vr = verify_compliance(cwd)
    print()
    print(f"Compliance: {vr.score} checks passed")
    if not vr.passed:
        for fc in vr.failed_checks:
            print(f"  FAIL  {fc.check_id}: {fc.message}")
    else:
        print("  All checks passed.")
    return 0


# ── self-test ─────────────────────────────────────────────────────────────────

def _cmd_self_test() -> int:
    ok = run_self_test()
    print(f"Kernel self-test: {'PASS' if ok else 'FAIL'}")
    print(f"SDK version    : {__version__}")
    print(f"Kernel version : {KERNEL_VERSION}")
    return 0 if ok else 1


# ── Argument parser ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aiep-genome",
        description=f"AIEP GENOME SDK v{__version__} — build or adopt AIEP-compliant software.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "New project:\n"
            "  aiep-genome init --name my-service            # scaffold from zero\n"
            "\n"
            "Existing project:\n"
            "  aiep-genome adopt                             # retrofit existing repo\n"
            "  aiep-genome adopt --pattern governance        # choose pattern explicitly\n"
            "  aiep-genome adopt --dry-run                   # preview only\n"
            "\n"
            "Check:\n"
            "  aiep-genome verify                            # compliance check\n"
            "  aiep-genome status                            # config + compliance summary\n"
        ),
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="Run kernel determinism self-test and exit",
    )
    sub = parser.add_subparsers(dest="command")

    # ── init ──────────────────────────────────────────────────────────────────
    ip = sub.add_parser("init", help="Scaffold a new AIEP-compliant project from zero")
    ip.add_argument("dest", nargs="?", default=".", help="Destination directory [.]")
    ip.add_argument("--name", default="", help="Package name")
    ip.add_argument("--version", default="0.1.0", help="Initial version [0.1.0]")
    ip.add_argument("--description", default="", help="Short one-line description")
    ip.add_argument(
        "--pattern",
        default="evidence-ledger",
        choices=("bare", "evidence-ledger", "mirror", "governance"),
        help="Scaffold pattern [evidence-ledger]",
    )
    ip.add_argument("--force", action="store_true", help="Overwrite existing files")

    # ── adopt ─────────────────────────────────────────────────────────────────
    ap = sub.add_parser("adopt", help="Retrofit an existing project to the genome standard")
    ap.add_argument("target", nargs="?", default=".", help="Project root directory [.]")
    ap.add_argument(
        "--pattern",
        default="auto",
        choices=("auto", "bare", "evidence-ledger", "mirror", "governance"),
        help="Integration pattern [auto-detect]",
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    ap.add_argument("--force", action="store_true", help="Overwrite existing genome/ files")

    # ── verify ────────────────────────────────────────────────────────────────
    vp = sub.add_parser("verify", help="Check genome compliance of a project directory")
    vp.add_argument("target", nargs="?", default=".", help="Project directory [.]")

    # ── status ────────────────────────────────────────────────────────────────
    sub.add_parser("status", help="Show configuration and compliance summary")

    args = parser.parse_args()

    if args.self_test:
        sys.exit(_cmd_self_test())

    if args.command == "init":
        sys.exit(_cmd_init(args))
    elif args.command == "adopt":
        sys.exit(_cmd_adopt(args))
    elif args.command == "verify":
        sys.exit(_cmd_verify(args))
    elif args.command == "status":
        sys.exit(_cmd_status(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
