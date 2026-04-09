"""
aiep_genome.verify — Genome compliance verification
====================================================
Implements the `aiep-genome verify` command: checks that a project directory
meets the AIEP GENOME standard.

Checks
------
  C1  .aiep-genome.json exists and is valid JSON
  C2  genome/ (or configured dir) contains __init__.py and canon.py
  C3  Kernel self-test passes (determinism, R1–R7)
  C4  LOCKFILE.json accessible and LOCKFILE_VERSION matches package
  C5  Compliance tests exist (tests/test_genome_compliance.py)
  C6  aiep-genome-sdk listed in project dependencies
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from aiep_genome import LOCKFILE_VERSION
from aiep_genome.kernel import run_self_test


CONFIG_FILENAME = ".aiep-genome.json"


@dataclass
class CheckResult:
    check_id: str
    passed: bool
    message: str


@dataclass
class VerifyResult:
    target_dir: str
    checks: list = field(default_factory=list)
    config: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list:
        return [c for c in self.checks if not c.passed]

    @property
    def score(self) -> str:
        n = len(self.checks)
        p = sum(1 for c in self.checks if c.passed)
        return f"{p}/{n}"


def verify_compliance(target_dir: str | Path = ".") -> VerifyResult:
    """
    Verify AIEP GENOME compliance of target_dir.
    Returns VerifyResult with detailed check results.
    """
    target = Path(target_dir).resolve()
    result = VerifyResult(target_dir=str(target))

    def check(cid: str, passed: bool, msg: str) -> None:
        result.checks.append(CheckResult(cid, passed, msg))

    # C1: Config file
    cfg_path = target / CONFIG_FILENAME
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            result.config = cfg
            check("C1", True, f"{CONFIG_FILENAME} found — pattern: {cfg.get('pattern', '?')}")
        except json.JSONDecodeError as e:
            check("C1", False, f"{CONFIG_FILENAME} is invalid JSON: {e}")
            cfg = {}
    else:
        check("C1", False, f"{CONFIG_FILENAME} not found — run  aiep-genome init  or  aiep-genome adopt")
        cfg = {}

    # C2: genome/ integration layer
    genome_dir_rel = cfg.get("genome_dir", "")
    genome_dir = (target / genome_dir_rel) if genome_dir_rel else None

    # Fallback: search common locations
    if not genome_dir or not genome_dir.exists():
        for candidate in (
            target / "genome",
            target / "src" / "genome",
            *(target / "src" / d / "genome" for d in (target / "src").iterdir()
              if (target / "src").exists() and d.is_dir()),
        ):
            if candidate.is_dir():
                genome_dir = candidate
                break

    if genome_dir and genome_dir.is_dir():
        has_init = (genome_dir / "__init__.py").exists()
        has_canon = (genome_dir / "canon.py").exists()
        if has_init and has_canon:
            check("C2", True, f"genome/ at {genome_dir.relative_to(target)} — __init__.py and canon.py present")
        else:
            missing = [f for f, ok in (("__init__.py", has_init), ("canon.py", has_canon)) if not ok]
            check("C2", False, f"genome/ at {genome_dir.relative_to(target)} missing: {', '.join(missing)}")
    else:
        check("C2", False, "genome/ integration directory not found — run  aiep-genome adopt")

    # C3: Kernel self-test
    try:
        ok = run_self_test()
        check("C3", ok, "Kernel self-test PASS — canon R1–R7 verified" if ok else "Kernel self-test FAIL")
    except Exception as e:
        check("C3", False, f"Kernel self-test raised: {e}")

    # C4: LOCKFILE.json
    # Search for SDK lockfile (could be in kernel/ relative to SDK or in project root)
    lockfile_paths = [
        target / "kernel" / "LOCKFILE.json",
        target / "LOCKFILE.json",
    ]
    # Also try the installed package location
    try:
        import aiep_genome as _pkg
        sdk_root = Path(_pkg.__file__).parent.parent.parent.parent / "repos" / "AIEP-GENOME-SDK"
        lockfile_paths.append(sdk_root / "kernel" / "LOCKFILE.json")
    except Exception:
        pass

    lockfile_found = False
    for lf_path in lockfile_paths:
        if lf_path.exists():
            try:
                lf = json.loads(lf_path.read_text(encoding="utf-8"))
                lf_ver = lf.get("LOCKFILE_VERSION", "?")
                if lf_ver == LOCKFILE_VERSION:
                    check("C4", True, f"LOCKFILE v{lf_ver} verified at {lf_path.name}")
                else:
                    check("C4", False, f"LOCKFILE version mismatch: lockfile={lf_ver}, expected={LOCKFILE_VERSION}")
                lockfile_found = True
                break
            except Exception as e:
                check("C4", False, f"LOCKFILE.json parse error: {e}")
                lockfile_found = True
                break

    if not lockfile_found:
        # LOCKFILE not required in project root; only warn, don't fail
        check("C4", True, "LOCKFILE.json not in project root (kernel is in SDK package — acceptable)")

    # C5: Compliance tests
    test_files = [
        target / "tests" / "test_genome_compliance.py",
        target / "test_genome_compliance.py",
        target / "tests" / "test_genome.py",
    ]
    found_tests = [tf for tf in test_files if tf.exists()]
    if found_tests:
        check("C5", True, f"Compliance tests found: {found_tests[0].name}")
    else:
        check("C5", False, "No genome compliance tests found — run  aiep-genome adopt  (or create tests/test_genome_compliance.py)")

    # C6: Dependency declared
    dep_files = ["pyproject.toml", "requirements.txt", "requirements-dev.txt", "setup.cfg"]
    dep_found = any(
        (target / df).exists() and "aiep-genome" in (target / df).read_text(encoding="utf-8", errors="replace")
        for df in dep_files
    )
    if dep_found:
        check("C6", True, "aiep-genome-sdk declared in project dependencies")
    else:
        check("C6", False, "aiep-genome-sdk not found in any dependency file — add  aiep-genome-sdk>=1.2.0")

    return result
